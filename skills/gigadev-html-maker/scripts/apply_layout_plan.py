#!/usr/bin/env python3
"""Apply explicit geometry and paragraph sizes to a reconciled authored slide."""
import argparse,hashlib,json,math,os,pathlib,re,subprocess,tempfile,xml.etree.ElementTree as ET
from html.parser import HTMLParser
from bounded_geometry import sha

class Tags(HTMLParser):
 def __init__(self,html,ids):
  super().__init__(convert_charrefs=False);self.html=html;self.ids=ids;self.stack=[];self.matches={i:[] for i in ids};self.paras={i:[] for i in ids};self.offsets=[0]+[m.end() for m in re.finditer('\n',html)]
 def handle_starttag(self,tag,attrs):
  raw=self.get_starttag_text();pos=self.offsets[self.getpos()[0]-1]+self.getpos()[1];a=dict(attrs);ident=a.get('data-source-id');parent=self.stack[-1][1] if self.stack else None;active=ident if ident in self.ids else parent
  if ident and parent in self.ids:raise ValueError('Nested source target requires a separate operation: '+ident)
  if ident in self.ids:self.matches[ident].append((tag,pos,raw,a))
  if tag=='p' and active in self.ids:self.paras[active].append((tag,pos,raw,a))
  if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.stack.append((tag,active))
 def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs);self.handle_endtag(tag)
 def handle_endtag(self,tag):
  if self.stack and self.stack[-1][0]==tag:self.stack.pop()

def change(raw,changes):
 m=re.search(r'\bstyle\s*=\s*(["\'])(.*?)\1',raw,re.S|re.I)
 if not m:raise ValueError('Target requires a quoted inline style')
 style=m.group(2);pieces=style.split(';');seen={};result=[]
 for piece in pieces:
  if ':' not in piece:result.append(piece);continue
  name,value=piece.split(':',1);key=name.strip().lower()
  if key in changes:
   seen[key]=seen.get(key,0)+1
   if not re.fullmatch(r'\s*-?(?:\d+(?:\.\d*)?|\.\d+)px\s*',value):raise ValueError('Non-pixel or unsupported existing value: '+key)
   value=format(changes[key],'.6f').rstrip('0').rstrip('.')+'px'
  result.append(name+':'+value)
 if set(seen)!=set(changes) or any(x!=1 for x in seen.values()):raise ValueError('Missing or duplicate style property')
 return raw[:m.start(2)]+';'.join(result)+raw[m.end(2):]

def source_radial(raw,block,options):
 """Restore a centered two-stop circular gradient with validated source colors."""
 root=ET.fromstring(block.get('shapePropertiesXml',''));grad=next((x for x in root.iter() if x.tag.endswith('}gradFill')),None)
 if grad is None or not any(x.tag.endswith('}path') and x.get('path')=='circle' for x in grad):raise ValueError('Source is not a circular gradient')
 if grad.get('flip','none')!='none' or grad.get('rotWithShape','1') not in ('1','true'):raise ValueError('Unsupported gradient flip or rotation mode')
 tiles=[x for x in grad.iter() if x.tag.endswith('}tileRect')]
 if len(tiles)>1 or any(x.attrib for x in tiles):raise ValueError('Non-default source tile rectangle is unsupported')
 transform=next((x for x in root if x.tag.endswith('}xfrm')),None)
 ext=next((x for x in transform if x.tag.endswith('}ext')),None) if transform is not None else None
 if ext is None:raise ValueError('Source dimensions are unresolved')
 cx,cy=int(ext.get('cx','0')),int(ext.get('cy','0'))
 if min(cx,cy)<=0 or abs(cx-cy)>max(cx,cy)*.001:raise ValueError('Only circular source bounds are supported')
 fill=next((x for x in grad.iter() if x.tag.endswith('}fillToRect')),None)
 if fill is None or any(fill.get(k)!='50000' for k in ('l','t','r','b')):raise ValueError('Only centered circular source fills are supported')
 stops=[x for x in grad.iter() if x.tag.endswith('}gs')]
 if len(stops)!=2:raise ValueError('Only two-stop sRGB gradients are supported')
 src=[]
 for stop in stops:
  color=next((x for x in stop if x.tag.endswith('}srgbClr')),None)
  if color is not None:
   if not re.fullmatch(r'[0-9A-Fa-f]{6}',color.get('val','')) or any(not x.tag.endswith('}alpha') for x in color) or len(color)>1:raise ValueError('Unsupported source sRGB modifiers')
   rgb=tuple(int(color.get('val')[i:i+2],16) for i in (0,2,4))
  else:
   color=next((x for x in stop if x.tag.endswith('}schemeClr')),None);base=options.get('bg1') if isinstance(options,dict) else None
   if color is None or color.get('val')!='bg1' or not isinstance(base,str) or not re.fullmatch(r'[0-9A-Fa-f]{6}',base):raise ValueError('Theme bg1 requires an explicitly resolved six-digit source color')
   modifiers=[x.tag.rsplit('}',1)[-1] for x in color]
   if any(x not in ('lumMod','alpha') for x in modifiers) or len(modifiers)!=len(set(modifiers)):raise ValueError('Unsupported theme color modifiers')
   lum=next((int(x.get('val'))/100000 for x in color if x.tag.endswith('}lumMod')),1.0)
   if not 0<=lum<=1:raise ValueError('Unsupported luminance')
   rgb=tuple(round(int(base[i:i+2],16)*lum) for i in (0,2,4))
  if len(stop)!=1:raise ValueError('Unsupported source stop')
  alpha=next((int(x.get('val'))/100000 for x in color if x.tag.endswith('}alpha')),1.0);src.append((rgb,alpha,int(stop.get('pos'))/1000))
 if not (0<=src[0][2]<src[1][2]<=100) or any(not 0<=x[1]<=1 for x in src):raise ValueError('Invalid source stops')
 pattern=r'background\s*:\s*linear-gradient\(135deg,\s*rgba\((\d+),(\d+),(\d+),([\d.]+)\),\s*rgba\((\d+),(\d+),(\d+),([\d.]+)\)\)'
 matches=list(re.finditer(pattern,raw,re.I))
 if len(matches)!=1:raise ValueError('Existing gradient form is unsupported')
 m=matches[0];v=m.groups()
 for i in range(2):
  if tuple(map(int,v[i*4:i*4+3]))!=src[i][0] or abs(float(v[i*4+3])-src[i][1])>.001:raise ValueError('Authored gradient differs from source colors')
 colors=[f'rgba({rgb[0]},{rgb[1]},{rgb[2]},{alpha:.5f}) {pos:g}%' for rgb,alpha,pos in src]
 geometry='circle farthest-corner at center'
 shape=next((x for x in root if x.tag.endswith('}prstGeom')),None)
 if shape is not None and shape.get('prst')=='pie' and not (isinstance(options,dict) and options.get('domain')=='authored-clip-bounds'):raise ValueError('Source pie requires reviewed authored clip bounds')
 if isinstance(options,dict) and options.get('domain')=='authored-clip-bounds':
  if shape is None or shape.get('prst')!='pie':raise ValueError('Clip-bounds mode requires a source pie shape')
  clip=re.search(r'clip-path\s*:\s*polygon\(([^)]*)\)',raw,re.I)
  width=re.search(r'(?:^|;)\s*width\s*:\s*([\d.]+)px',raw,re.I);height=re.search(r'(?:^|;)\s*height\s*:\s*([\d.]+)px',raw,re.I)
  if not clip or not width or not height:raise ValueError('Clip-bounds mode requires explicit authored polygon and dimensions')
  points=re.findall(r'([\d.]+)%\s+([\d.]+)%',clip.group(1));rest=re.sub(r'([\d.]+)%\s+([\d.]+)%|[\s,]','',clip.group(1))
  if len(points)<4 or rest:raise ValueError('Unsupported polygon')
  xs=[float(x) for x,y in points];ys=[float(y) for x,y in points]
  if any(not 0<=n<=100 for n in xs+ys):raise ValueError('Polygon is outside the source box')
  w,h=float(width.group(1)),float(height.group(1));radius=math.hypot((max(xs)-min(xs))*w/200,(max(ys)-min(ys))*h/200)
  if not math.isfinite(radius) or radius<=0:raise ValueError('Invalid polygon bounds')
  geometry=f'circle {radius:.5f}px at {(min(xs)+max(xs))/2:.5f}% {(min(ys)+max(ys))/2:.5f}%'
 return raw[:m.start()]+'background:radial-gradient('+geometry+','+','.join(colors)+')'+raw[m.end():]

def main():
 p=argparse.ArgumentParser(description=__doc__);[p.add_argument(x) for x in ('project','baseline','saved','plan','out')];a=p.parse_args();plan=json.loads(pathlib.Path(a.plan).read_text());project=pathlib.Path(a.project).resolve();out=pathlib.Path(a.out).resolve()
 if out.parent!=project.parent or out.exists():raise ValueError('Output must be new and beside project')
 required={'projectSha256','baselineSha256','savedSha256','slide','problem','decision','targets'}
 if set(plan)!=required or plan['decision'] not in ('adapt','redesign') or not isinstance(plan['problem'],str) or not plan['problem'].strip():raise ValueError('Invalid plan')
 targets=plan['targets'];ids=list(targets) if isinstance(targets,dict) else []
 if not ids or any(not re.fullmatch(r'[A-Za-z0-9_-]+',x) for x in ids):raise ValueError('Invalid target IDs')
 for ident,v in targets.items():
  if not isinstance(v,dict) or not v or set(v)-{'left','top','width','height','fontSize','sourceRadial'}:raise ValueError('Unsupported operation '+ident)
  for k,n in v.items():
   if k=='sourceRadial':
    if n is not True:
     if not isinstance(n,dict) or not n or set(n)-{'bg1','domain'} or ('bg1' in n and (not isinstance(n['bg1'],str) or not re.fullmatch(r'[0-9A-Fa-f]{6}',n['bg1']))) or ('domain' in n and n['domain']!='authored-clip-bounds'):raise ValueError('Invalid sourceRadial assertion')
     if n.get('domain')=='authored-clip-bounds' and any(x in v for x in ('width','height')):raise ValueError('Do not resize a source clip while deriving its gradient')
    continue
   if isinstance(n,bool) or not isinstance(n,(int,float)) or not math.isfinite(n) or abs(n)>2500 or (k in ('width','height','fontSize') and n<=0) or (k=='fontSize' and not 10<=n<=100):raise ValueError('Invalid value '+ident+' '+k)
 def unchanged():return all(sha(f)==plan[k] for f,k in [(project,'projectSha256'),(a.baseline,'baselineSha256'),(a.saved,'savedSha256')])
 if not unchanged():raise ValueError('Stale baseline or input hash')
 fd,tmp=tempfile.mkstemp(prefix='.layout-sync-',suffix='.json',dir=project.parent);os.close(fd);os.unlink(tmp)
 try:
  here=pathlib.Path(__file__).parent
  def run(args):
   r=subprocess.run(args,text=True,capture_output=True)
   if r.returncode:raise ValueError('Guard refused: '+(r.stdout+r.stderr)[-3000:])
   return r.stdout
  sync=json.loads(run(['node',str(here/'reconcile_edits.mjs'),str(pathlib.Path(a.baseline).resolve()),str(pathlib.Path(a.saved).resolve()),str(project),tmp]))
  geometry_ids=[i for i in ids if set(targets[i])!={'sourceRadial'}]
  if geometry_ids:run(['node',str(here/'check_geometry_context.mjs'),str(pathlib.Path(a.saved).resolve()),plan['slide'],*geometry_ids])
  data=json.loads(pathlib.Path(tmp).read_text());slides=[s for s in data['slides'] if s['id']==plan['slide']]
  if len(slides)!=1 or not isinstance(slides[0].get('html'),str):raise ValueError('Missing or unsupported authored slide')
  slide=slides[0];source=slide['html'];scan=Tags(source,ids);scan.feed(source);edits=[];journal=[]
  for ident,operation in targets.items():
   if len(scan.matches[ident])!=1:raise ValueError('Missing or ambiguous target '+ident)
   tag,pos,raw,attr=scan.matches[ident][0];geom={k:v for k,v in operation.items() if k not in ('fontSize','sourceRadial')}
   if tag not in ('div','p','table','img'):raise ValueError('Unsupported target type '+tag)
   if 'sourceRadial' in operation:
    blocks=[b for b in slide.get('blocks',[]) if b.get('id')==ident]
    if len(blocks)!=1:raise ValueError('Source gradient block missing or ambiguous')
    raw=source_radial(raw,blocks[0],operation['sourceRadial'])
   if geom or 'sourceRadial' in operation:edits.append((pos,pos+len(scan.matches[ident][0][2]),change(raw,geom) if geom else raw))
   if 'fontSize' in operation:
    paras=scan.paras[ident]
    if not paras:raise ValueError('No paragraph for '+ident)
    for _,start,markup,_ in paras:
     if start==pos:raise ValueError('Paragraph root font edit unsupported')
     edits.append((start,start+len(markup),change(markup,{'font-size':operation['fontSize']})))
   journal.append({'sourceId':ident,'set':operation})
  if len({x[0] for x in edits})!=len(edits):raise ValueError('Overlapping target edits')
  for start,end,replacement in sorted(edits,reverse=True):source=source[:start]+replacement+source[end:]
  slide['html']=source
  if not unchanged():raise ValueError('Input changed during operation')
  payload=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode();fd,staged=tempfile.mkstemp(prefix='.layout-write-',dir=out.parent)
  try:
   with os.fdopen(fd,'wb') as f:f.write(payload);f.flush();os.fsync(f.fileno())
   os.link(staged,out)
  finally:os.unlink(staged)
  print(json.dumps({'status':'applied','decision':plan['decision'],'problem':plan['problem'],'slide':plan['slide'],'targets':journal,'projectAfter':hashlib.sha256(payload).hexdigest(),'reconciledChanges':sync.get('changes',[])},ensure_ascii=False,indent=2))
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
if __name__=='__main__':
 try:main()
 except Exception as e:
  import sys
  print(json.dumps({'status':'refused','reason':str(e)},ensure_ascii=False),file=sys.stderr);sys.exit(1)
