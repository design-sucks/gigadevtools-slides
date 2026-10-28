"""PPTX -> auditable content/asset project. Standard library only; no slide rendering."""
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as E
from collections import Counter
import argparse, hashlib, json, posixpath, re, mimetypes
from source_style import inventory as style_inventory

NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'c':'http://schemas.openxmlformats.org/drawingml/2006/chart',
    'asvg':'http://schemas.microsoft.com/office/drawing/2016/SVG/main'}
def text(node):return ''.join(e.text or '' for e in node.findall('.//a:t',NS))
def extract(source,out):
 source=Path(source);out=Path(out)
 if out.exists() and any(out.iterdir()):raise ValueError('Output must be new or empty')
 out.mkdir(parents=True,exist_ok=True);(out/'assets').mkdir(exist_ok=True)
 warnings=[];assets={};slides=[]
 with ZipFile(source) as z:
  def xml(name):return E.fromstring(z.read(name))
  def rels(part):
   rp=posixpath.join(posixpath.dirname(part),'_rels',posixpath.basename(part)+'.rels')
   if rp not in z.namelist():return {}
   result={}
   for e in xml(rp):
    external=e.get('TargetMode')=='External';target=e.get('Target','')
    target=target if external else posixpath.normpath(posixpath.join(posixpath.dirname(part),target.lstrip('/'))) if not target.startswith('/') else target[1:]
    result[e.get('Id')]={'target':target,'external':external,'type':e.get('Type','').rsplit('/',1)[-1]}
   return result
  def asset(part):
   data=z.read(part);key=hashlib.sha256(data).hexdigest();suffix=Path(part).suffix.lower() or '.bin';name=f'assets/{key[:20]}{suffix}'
   if key not in assets:(out/name).write_bytes(data);assets[key]={'path':name,'source':part,'sha256':key,'bytes':len(data),'mime':mimetypes.guess_type(part)[0] or 'application/octet-stream'}
   return name
  pres=xml('ppt/presentation.xml');pr=rels('ppt/presentation.xml');size=pres.find('p:sldSz',NS)
  source_size={'widthEMU':int(size.get('cx')),'heightEMU':int(size.get('cy'))}
  parts=[pr[e.get('{'+NS['r']+'}id')]['target'] for e in pres.findall('p:sldIdLst/p:sldId',NS)]
  for number,part in enumerate(parts,1):
   tree=xml(part);rr=rels(part);seen=set();sid=f's{number}';blocks=[];meta=[]
   source_bg=tree.find('p:cSld/p:bg',NS);background_evidence=None
   if source_bg is not None:
    evidence={'kind':'native-background','xml':E.tostring(source_bg,encoding='unicode')}
    blip=source_bg.find('.//a:blip',NS)
    if blip is not None:
     rid=blip.get('{'+NS['r']+'}embed');rel=rr.get(rid,{})
     if rel and not rel.get('external') and rel['target'] in z.namelist():evidence.update(asset=asset(rel['target']),relationshipId=rid)
    background_evidence=evidence
   def paragraphs(node):
    result=[]
    for p in node.findall('.//a:p',NS):
     ts=p.findall('.//a:t',NS)
     for t in ts:seen.add(id(t))
     runs=[]
     for child in p:
      if child.tag=='{'+NS['a']+'}br':runs.append({'text':'\n'});continue
      t=child.find('a:t',NS)
      if t is None:continue
      rp=child.find('a:rPr',NS);run={'text':t.text or ''}
      if rp is not None:
       if rp.get('sz'):run['size']=float(rp.get('sz'))/100
       if rp.get('b'):run['bold']=rp.get('b')=='1'
       if rp.get('i'):run['italic']=rp.get('i')=='1'
       for font in ['latin','ea','cs']:
        f=rp.find('a:'+font,NS)
        if f is not None:run['font']=f.get('typeface')
       link=rp.find('a:hlinkClick',NS)
       if link is not None:run['link']=rr.get(link.get('{'+NS['r']+'}id'),{}).get('target')
      runs.append(run)
     pp=p.find('a:pPr',NS)
     if ts:result.append({'text':''.join(r['text'] for r in runs),'runs':runs,'level':int(pp.get('lvl','0')) if pp is not None else 0})
    return result
   def walk(parent,group=None):
    for node in parent:
     kind=node.tag.rsplit('}',1)[-1]
     if kind in ['nvGrpSpPr','grpSpPr']:continue
     nv=node.find('.//p:cNvPr',NS);oid=(nv.get('id') if nv is not None else str(len(blocks)+1));bid=f'{sid}-o{oid}'
     item={'id':bid,'source':{'slide':number,'part':part,'objectId':oid},'name':nv.get('name','') if nv is not None else kind,'group':group}
     # Transform ownership differs for graphic frames and drawing shapes.
     xf=node.find('p:xfrm',NS) if kind=='graphicFrame' else node.find('p:grpSpPr/a:xfrm',NS) if kind=='grpSp' else node.find('p:spPr/a:xfrm',NS)
     if xf is not None:item['transform']={'attributes':xf.attrib,'children':[{e.tag.rsplit('}',1)[-1]:e.attrib} for e in xf]}
     if kind=='grpSp':
      item['kind']='group';blocks.append(item);walk(node,bid);continue
     ph=node.find('.//p:ph',NS);ph_type=ph.get('type') if ph is not None else None
     if ph_type in ['sldNum','dt','ftr','hdr'] or node.find('.//a:fld[@type="slidenum"]',NS) is not None:
      item.update(kind='metadata',role=ph_type or 'sldNum',paragraphs=paragraphs(node));meta.append(item);continue
     table=node.find('.//a:tbl',NS);chart=node.find('.//c:chart',NS)
     if table is not None:
      item.update(kind='table',rows=[[paragraphs(tc) for tc in row.findall('a:tc',NS)] for row in table.findall('a:tr',NS)]);blocks.append(item);continue
     if chart is not None:
      cp=rr.get(chart.get('{'+NS['r']+'}id'),{}).get('target');series=[]
      if cp:
       ct=xml(cp)
       for se in ct.findall('.//c:ser',NS):
        values=lambda name:[e.text or '' for e in se.findall('.//c:'+name+'//c:pt/c:v',NS)]
        series.append({'name':''.join(e.text or '' for e in se.findall('c:tx//c:v',NS)),'categories':values('cat') or values('xVal'),'values':values('val') or values('yVal')})
       item.update(kind='chart',series=series,chartTypes=sorted({e.tag.rsplit('}',1)[-1] for e in ct.iter() if e.tag.endswith('Chart')}),chartPart=cp)
      else:item.update(kind='unsupported',reason='missing chart relationship')
      blocks.append(item);continue
     if kind=='pic':
      blip=node.find('.//a:blip',NS);rid=blip.get('{'+NS['r']+'}embed') if blip is not None else None;rel=rr.get(rid,{})
      svg_blip=node.find('.//asvg:svgBlip',NS);svg_rid=svg_blip.get('{'+NS['r']+'}embed') if svg_blip is not None else None;svg_rel=rr.get(svg_rid,{})
      if rel and not rel.get('external'):
       fallback=asset(rel['target'])
       preferred=asset(svg_rel['target']) if svg_rel and not svg_rel.get('external') and svg_rel['target'] in z.namelist() else fallback
       item.update(kind='image',asset=preferred,alt=nv.get('descr','') if nv is not None else '')
       if preferred!=fallback:item.update(fallbackAsset=fallback,assetPreference='svg',assetProvenance={'preferredRelationship':svg_rid,'fallbackRelationship':rid})
       crop=node.find('.//a:srcRect',NS)
       if crop is not None:item['crop']=crop.attrib
       if xf is not None:
        off=xf.find('a:off',NS);ext=xf.find('a:ext',NS)
        if off is not None and ext is not None:
         geometry={'xEMU':int(off.get('x','0')),'yEMU':int(off.get('y','0')),'widthEMU':int(ext.get('cx','0')),'heightEMU':int(ext.get('cy','0'))}
         item['rawGeometryEMU']=geometry
         if geometry=={'xEMU':0,'yEMU':0,'widthEMU':source_size['widthEMU'],'heightEMU':source_size['heightEMU']}:
          item['backgroundCandidate']=True;warnings.append({'slide':number,'object':bid,'code':'background-candidate','message':'Full-slide-sized picture; review before using as slide background'})
       if Path(item['asset']).suffix in ['.emf','.wmf','.tif','.tiff']:warnings.append({'slide':number,'object':bid,'code':'browser-image-adapter','asset':item['asset']})
      else:item.update(kind='unsupported',reason='external or missing image')
      blocks.append(item);continue
     ps=paragraphs(node)
     if ps:item.update(kind='text',paragraphs=ps,title=ph_type in ['title','ctrTitle']);blocks.append(item)
     elif kind in ['sp','cxnSp']:item['kind']='geometry';blocks.append(item)
     elif kind not in ['extLst']:item.update(kind='unsupported',reason=kind);blocks.append(item)
   walk(tree.find('p:cSld/p:spTree',NS))
   for t in tree.findall('.//a:t',NS):
    if id(t) not in seen and t.text:
     blocks.append({'id':f'{sid}-unmapped-{len(blocks)}','kind':'text','paragraphs':[{'text':t.text,'runs':[{'text':t.text}]}],'source':{'slide':number,'part':part},'review':True});warnings.append({'slide':number,'code':'unmapped-text-recovered'})
   notes=''
   for rel in rr.values():
    if rel['type'] in ['video','audio']:
     if rel['external']:warnings.append({'slide':number,'code':'external-media','target':rel['target']})
     elif rel['target'] in z.namelist():
      media_asset=asset(rel['target']);blocks.append({'id':f'{sid}-media-{len(blocks)}','kind':'media','mediaType':rel['type'],'asset':media_asset,'source':{'slide':number,'part':rel['target']}});warnings.append({'slide':number,'code':'media-placement-review','asset':media_asset})
   for rel in rr.values():
    if rel['type']=='notesSlide' and not rel['external']:
     notes='\n'.join(text(n) for n in xml(rel['target']).findall('.//p:sp',NS) if n.find('.//p:ph[@type="sldNum"]',NS) is None)
   title=next((' '.join(p['text'] for p in b['paragraphs']) for b in blocks if b['kind']=='text' and b.get('title')),None)
   if not title:title=next((' '.join(p['text'] for p in b['paragraphs']) for b in blocks if b['kind']=='text'),f'Слайд {number}')
   title=title.strip()[:180]
   for b in blocks:
    if b['kind']=='unsupported':warnings.append({'slide':number,'object':b['id'],'code':'unsupported-object','reason':b['reason']})
   # Audit visible XML strings without trusting the inferred semantic roles.
   source_strings=Counter(t.text or '' for t in tree.findall('.//a:t',NS));assert all(id(t) in seen or any(b.get('review') and b['paragraphs'][0]['text']==t.text for b in blocks) for t in tree.findall('.//a:t',NS))
   record={'id':sid,'label':title,'title':title,'sourceNumber':number,'section':'','topic':title,'header':'full','blocks':blocks,'metadata':meta,'notes':notes,'sourceTextStrings':sum(source_strings.values())}
   if background_evidence is not None:record['sourceBackground']=background_evidence
   slides.append(record)
  themes=[]
  for part in z.namelist():
   if re.fullmatch(r'ppt/theme/theme\d+\.xml',part):
    tr=xml(part);themes.append({'part':part,'colors':[{e.tag.rsplit('}',1)[-1]:[c.attrib for c in e]} for e in tr.findall('.//a:clrScheme/*',NS)],'fonts':[e.attrib for e in tr.findall('.//a:fontScheme//a:latin',NS)]})
 result={'schema':1,'title':source.stem,'version':1,'source':{'name':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'canvas':source_size},'order':[s['id'] for s in slides],'slides':slides,'assets':list(assets.values()),'sourceThemes':themes,'warnings':warnings}
 (out/'deck.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out/'inventory.json').write_text(json.dumps({'slides':len(slides),'objects':dict(Counter(b['kind'] for s in slides for b in s['blocks'])),'assets':len(assets),'warnings':warnings},ensure_ascii=False,indent=2))
 (out/'style-inventory.json').write_text(json.dumps(style_inventory(source,result),ensure_ascii=False,indent=2))
 print(json.dumps({'status':'extracted','slides':len(slides),'assets':len(assets),'reviewItems':len(warnings),'project':str((out/'deck.json').resolve())},ensure_ascii=False))
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('out');a=p.parse_args();extract(a.source,a.out)
