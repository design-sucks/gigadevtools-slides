"""Conservative PPTX style evidence and deterministic decision gate; no rendering."""
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from collections import Counter
import argparse, hashlib, json, posixpath, re

A='http://schemas.openxmlformats.org/drawingml/2006/main'
P='http://schemas.openxmlformats.org/presentationml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
N={'a':A,'p':P,'r':R}
def local(tag): return tag.rsplit('}',1)[-1]
def relationships(z, part):
 name=posixpath.join(posixpath.dirname(part),'_rels',posixpath.basename(part)+'.rels')
 if name not in z.namelist(): return {}
 return {x.get('Id'):{'type':x.get('Type','').rsplit('/',1)[-1], 'target':posixpath.normpath(posixpath.join(posixpath.dirname(part),x.get('Target',''))) if not x.get('Target','').startswith('/') else x.get('Target','')[1:], 'external':x.get('TargetMode')=='External'} for x in ET.fromstring(z.read(name))}
def scheme_for(z, part):
 # Follow slide -> layout -> master -> theme; unresolved if relationship chain is absent.
 visited=set()
 while part and part not in visited and part in z.namelist():
  visited.add(part); rels=relationships(z,part)
  if part.startswith('ppt/theme/'):
   tree=ET.fromstring(z.read(part)); colors={}
   for el in tree.findall('.//a:clrScheme/*',N):
    c=next(iter(el),None)
    if c is not None:
     v=c.get('val') if local(c.tag)=='srgbClr' else c.get('lastClr') if local(c.tag)=='sysClr' else None
     if v and re.fullmatch(r'[0-9a-fA-F]{6}',v): colors[local(el.tag)]='#'+v.upper()
   return part,colors
  next_rel=next((r for r in rels.values() if r['type'] in ('slideLayout','slideMaster','theme') and not r['external']),None)
  part=next_rel['target'] if next_rel else None
 return None,{}
def inventory(source,deck):
 evidence=[]; fonts=[]; themes=[]
 with ZipFile(source) as z:
  for part in z.namelist():
   if re.fullmatch(r'ppt/theme/theme\d+\.xml',part):
    _,colors=scheme_for(z,part); tree=ET.fromstring(z.read(part)); theme_fonts=[{'property':local(parent.tag)+'/'+local(child.tag),'typeface':child.get('typeface')} for parent in tree.findall('.//a:fontScheme//*',N) for child in parent if local(child.tag) in ('latin','ea','cs') and child.get('typeface')]; themes.append({'part':part,'colors':colors,'fonts':theme_fonts})
  for slide in deck['slides']:
   part=next((b['source']['part'] for b in slide['blocks'] if b.get('source',{}).get('part','').startswith('ppt/slides/')),f"ppt/slides/slide{slide['sourceNumber']}.xml")
   if part not in z.namelist(): continue
   tree=ET.fromstring(z.read(part)); theme,scheme=scheme_for(z,part)
   def walk(el, ancestors, obj):
    kind=local(el.tag)
    if kind in ('sp','pic','graphicFrame','cxnSp','grpSp'):
     nv=el.find('./p:nvSpPr/p:cNvPr',N) or el.find('./p:nvPicPr/p:cNvPr',N) or el.find('./p:nvGraphicFramePr/p:cNvPr',N) or el.find('./p:nvCxnSpPr/p:cNvPr',N) or el.find('./p:nvGrpSpPr/p:cNvPr',N)
     # Element truthiness depends on children, so find directly if necessary.
     for nvpath in ('./p:nvSpPr/p:cNvPr','./p:nvPicPr/p:cNvPr','./p:nvGraphicFramePr/p:cNvPr','./p:nvCxnSpPr/p:cNvPr','./p:nvGrpSpPr/p:cNvPr'):
      candidate=el.find(nvpath,N)
      if candidate is not None: nv=candidate; break
     if nv is not None: obj=f"{slide['id']}-o{nv.get('id')}"
    path=ancestors+[kind]
    if kind in ('srgbClr','schemeClr','sysClr','prstClr'):
     role='background' if 'bg' in path else 'text' if any(x in path for x in ('rPr','defRPr','endParaRPr')) else 'line' if 'ln' in path else 'fill' if any(x in path for x in ('solidFill','gradFill','pattFill')) else 'other'
     raw=el.get('val',''); value=('#'+raw.upper()) if kind=='srgbClr' and re.fullmatch(r'[0-9a-fA-F]{6}',raw) else scheme.get(raw) if kind=='schemeClr' else ('#'+el.get('lastClr').upper() if kind=='sysClr' and re.fullmatch(r'[0-9a-fA-F]{6}',el.get('lastClr','')) else None)
     # Modifiers cannot safely be called an effective color.
     transforms=[{'type':local(c.tag),'value':c.get('val')} for c in el]
     evidence.append({'slide':slide['sourceNumber'],'part':part,'object':obj,'property':'/'.join(path[-5:]),'role':role,'type':kind,'raw':raw,'resolvedBase':value,'transforms':transforms,'themePart':theme,'resolution':'base-only' if value else 'unresolved'})
    if kind in ('latin','ea','cs') and el.get('typeface'):
     fonts.append({'slide':slide['sourceNumber'],'part':part,'object':obj,'property':'/'.join(path[-5:]),'typeface':el.get('typeface')})
    for child in el: walk(child,path,obj)
   walk(tree,[],None)
 # Coalesce identical evidence, keeping stable identifiers.
 def grouped(items):
  counts=Counter(json.dumps(x,sort_keys=True,ensure_ascii=False) for x in items)
  result=[]
  for key,count in sorted(counts.items()):
   x=json.loads(key);x['count']=count;x['id']='e-'+hashlib.sha256(key.encode()).hexdigest()[:16];result.append(x)
  return result
 images=[]
 for slide in deck['slides']:
  for b in slide['blocks']:
   if b['kind']=='image': images.append({'id':b['id'],'slide':slide['sourceNumber'],'part':b['source']['part'],'objectId':b['source'].get('objectId'),'asset':b['asset'],'fallbackAsset':b.get('fallbackAsset'),'backgroundCandidate':b.get('backgroundCandidate',False)})
  if slide.get('sourceBackground',{}).get('asset'):
   images.append({'id':slide['id']+'-background','slide':slide['sourceNumber'],'part':slide['blocks'][0]['source']['part'] if slide['blocks'] else None,'objectId':None,'asset':slide['sourceBackground']['asset'],'backgroundCandidate':True})
 colors=grouped(evidence); summary={}
 for item in colors:
  key=(item['role'],item.get('resolvedBase'),item['type'],item['raw'])
  row=summary.setdefault(key,{'role':item['role'],'resolvedBase':item.get('resolvedBase'),'type':item['type'],'raw':item['raw'],'count':0,'slides':set(),'evidenceIds':[]})
  row['count']+=item['count'];row['slides'].add(item['slide'])
  if len(row['evidenceIds'])<3:row['evidenceIds'].append(item['id'])
 color_summary=sorted([{**v,'slides':sorted(v['slides'])} for v in summary.values()],key=lambda x:(x['role'],-x['count'],str(x['resolvedBase'])))
 return {'schema':1,'source':deck['source'],'colorSummary':color_summary,'themes':themes,'colors':colors,'fonts':grouped(fonts),'graphics':images,'assets':deck['assets'],'inheritance':{'status':'unresolved','detail':'Effective inherited slide/layout/master styles and color mapping are not computed.'},'limitations':['Explicit slide XML only; master/layout inheritance, theme color maps, modifiers, transparency and effective rendered colors are not calculated.','Scheme values are base colors only, even when a theme is resolved; review actual source rendering.','Graphics are extracted image instances, not a semantic classification of logos or illustrations.']}
def check(project,manifest,html,theme=None):
 project=Path(project); inv=json.loads((project/'style-inventory.json').read_text()); dec=json.loads(Path(manifest).read_text()); errors=[]; warnings=[]
 mode=dec.get('mode')
 if mode not in ('preserve-design','improve-layout','change-style'): errors.append('mode must be preserve-design, improve-layout or change-style')
 if mode=='change-style' and not str(dec.get('changeStyleAuthorization','')).strip(): errors.append('change-style requires explicit changeStyleAuthorization')
 html_text=Path(html).read_text(); deck=json.loads((project/'deck.json').read_text()); theme_data=json.loads(Path(theme).read_text()) if theme else {}
 # Only authored markup/style sources, not the extracted source records.
 authored=html_text+'\n'+'\n'.join(str(slide.get('html','')) for slide in deck.get('slides',[]))+'\n'+str(theme_data.get('css',''))
 css='\n'.join(re.findall(r'<style\b[^>]*>(.*?)</style\s*>',authored,re.I|re.S))+'\n'+str(theme_data.get('css',''))
 css+='\n'+'\n'.join(re.findall(r'style\s*=\s*["\']([^"\']*)["\']',authored,re.I))
 def normalized(value):
  value=str(value).strip()
  if re.fullmatch(r'#[a-fA-F0-9]{3}',value): return '#'+''.join(c*2 for c in value[1:]).upper()
  return value.upper() if re.fullmatch(r'#[a-fA-F0-9]{6}',value) else None
 def chromatic(value):
  value=normalized(value)
  if not value:return False
  rgb=[int(value[i:i+2],16) for i in (1,3,5)]; high=max(rgb)
  return high>0 and (high-min(rgb))/high>=.1
 def declarations(target):
  return [normalized(x) for x in re.findall(r'(?:^|[;{])\s*'+re.escape(target)+r'\s*:\s*([^;}]+)',css,re.I)]
 evidence={x['id']:x for x in inv['colors']}; mappings=dec.get('palette',[]); covered=set(); inherited_chromatic=False
 required_roles={c['role'] for c in inv['colors'] if c['role'] in ('text','fill','line','background') and c.get('resolvedBase')}
 for m in mappings:
  ident=m.get('sourceEvidence'); src=evidence.get(ident); role=m.get('role'); target=m.get('target',''); disposition=m.get('decision'); color=normalized(m.get('targetColor',''))
  if not src: errors.append('palette sourceEvidence does not exist: '+str(ident));continue
  if role!=src['role']: errors.append('palette role differs from source evidence: '+str(ident))
  else: covered.add(role)
  if disposition not in ('retained','adjusted','replaced'): errors.append('palette decision must be retained, adjusted or replaced: '+str(ident))
  if disposition in ('adjusted','replaced') and not str(m.get('reason','')).strip(): errors.append('palette adjusted/replaced reason required: '+str(ident))
  if not color: errors.append('palette targetColor must be #RRGGBB: '+str(ident))
  if disposition=='retained' and (not src.get('resolvedBase') or color!=normalized(src['resolvedBase'])): errors.append('retained color must equal source resolvedBase: '+str(ident))
  if not target: errors.append('palette target required: '+str(ident))
  elif target.startswith('--'):
   if color not in declarations(target): errors.append('palette targetColor not declared for CSS token: '+target)
   if not re.search(r'var\(\s*'+re.escape(target)+r'\s*[,)]',css): errors.append('palette token is not used through var(): '+target)
  elif normalized(target):
   if normalized(target)!=color or not re.search(r':\s*'+re.escape(target)+r'(?=\s*[;}])',css,re.I): errors.append('palette targetColor not used in CSS declaration: '+str(target))
  else: errors.append('palette target must be CSS variable or hex: '+str(target))
  if src.get('resolvedBase') and chromatic(src['resolvedBase']) and chromatic(color) and disposition in ('retained','adjusted') and (disposition=='retained' or str(m.get('reason','')).strip()): inherited_chromatic=True
 for role in sorted(required_roles-covered): errors.append('missing palette mapping for source role: '+role)
 if not mappings: errors.append('palette decisions are required')
 if mode in ('preserve-design','improve-layout') and any(chromatic(c.get('resolvedBase')) for c in inv['colors'] if c['role'] in ('text','fill','line','background')) and not inherited_chromatic:
  errors.append('no chromatic source color retained or adjusted to a chromatic target')
 decisions=dec.get('graphics',[]); by_id={}
 for d in decisions:
  ident=d.get('sourceId');by_id.setdefault(ident,[]).append(d)
  if d.get('disposition') not in ('retained','reworked','replaced','omitted'): errors.append('invalid graphic disposition: '+str(ident))
  if not str(d.get('reason','')).strip(): errors.append('graphic reason required: '+str(ident))
  target=d.get('target','')
  if d.get('disposition')!='omitted' and (not target or target not in authored): errors.append('graphic target not present in authored HTML/deck/theme: '+str(ident))
  if d.get('disposition')=='omitted' and target: errors.append('omitted graphic must have empty target: '+str(ident))
 graphics=inv['graphics']; known={g['id'] for g in graphics}
 for g in graphics:
  if len(by_id.get(g['id'],[]))!=1: errors.append('exactly one decision required for graphic: '+g['id'])
 for ident in by_id:
  if ident not in known: errors.append('unknown graphic sourceId: '+str(ident))
 nongraphics=[g for g in graphics if not g.get('backgroundCandidate')]; counts=Counter(d.get('disposition') for d in decisions if d.get('sourceId') in known)
 noncounts=Counter(by_id[g['id']][0].get('disposition') for g in nongraphics if len(by_id.get(g['id'],[]))==1)
 if nongraphics and mode in ('preserve-design','improve-layout') and not (noncounts['retained']+noncounts['reworked']): errors.append('all non-background graphics discarded; retain or rework source graphical language, or explicitly authorize change-style')
 if nongraphics and noncounts['replaced']+noncounts['omitted']>len(nongraphics)/2: warnings.append('majority of non-background graphics replaced or omitted; review source graphical language')
 result={'schema':1,'status':'fail' if errors else 'pass','errors':errors,'warnings':warnings,'graphicsSummary':{'total':len(graphics),'counts':{k:counts[k] for k in ('retained','reworked','replaced','omitted')},'shares':{k:round(counts[k]/len(graphics),4) if graphics else 0 for k in ('retained','reworked','replaced','omitted')},'nonBackgroundTotal':len(nongraphics),'nonBackgroundCounts':{k:noncounts[k] for k in ('retained','reworked','replaced','omitted')}},'paletteSummary':{'requiredRoles':sorted(required_roles),'coveredRoles':sorted(covered),'chromaticSourceRetainedOrAdjusted':inherited_chromatic},'limitations':['Checks literal evidence, CSS declarations and references, not actual visual contribution, effective colors, faithful reproduction or whether reasons justify decisions.','Only explicit slide colors with resolved base are required; inherited styles, color maps, modifiers and rendered pixels remain unresolved.','RGB saturation threshold is a heuristic; chromatic retention or adjustment is not a design-quality guarantee.']}
 return result
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('project');parser.add_argument('manifest');parser.add_argument('--html',required=True);parser.add_argument('--theme');parser.add_argument('--report');args=parser.parse_args()
 report=check(args.project,args.manifest,args.html,args.theme); output=json.dumps(report,ensure_ascii=False,indent=2)
 if args.report: Path(args.report).write_text(output)
 print(output);raise SystemExit(0 if report['status']=='pass' else 1)
