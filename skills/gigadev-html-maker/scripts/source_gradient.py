"""Inspect a narrow PPTX radial gradient and stroke without approving its rendering."""
import argparse,copy,hashlib,json
from pathlib import Path
from xml.etree import ElementTree as ET
from source_dispositions import SourceVerifier,NS,file_digest,A
from source_shape import appearance,related,need,local

def inspect(verifier,n,oid):
 part,shape=verifier.shape(n,oid);sp=shape.find('p:spPr',NS);gradient=sp.find('a:gradFill',NS) if sp is not None else None
 need(gradient is not None,'no explicit source gradient');path=gradient.find('a:path',NS);need(path is not None and path.get('path')=='circle','unsupported gradient path')
 need(all(local(x) in ('gsLst','path','tileRect') for x in gradient),'unsupported gradient component')
 focus=path.find('a:fillToRect',NS);need(focus is not None and len(path)==1,'gradient focus unresolved')
 tile=gradient.find('a:tileRect',NS);layout=related(verifier.zip,part,'slideLayout');master=related(verifier.zip,layout,'slideMaster');theme=related(verifier.zip,master,'theme');theme_xml=ET.fromstring(verifier.zip.read(theme));scheme=theme_xml.find('.//a:clrScheme',NS);cmap=ET.fromstring(verifier.zip.read(master)).find('p:clrMap',NS)
 need(scheme is not None and cmap is not None,'gradient theme unresolved');stops=[]
 for stop in gradient.findall('a:gsLst/a:gs',NS):
  need(len(stop)==1,'gradient stop color invalid');color=stop[0];kind=local(color);value=color.get('val')
  if kind=='schemeClr':
   entry=scheme.find('a:'+cmap.get(value,value),NS);need(entry is not None and len(entry)==1 and local(entry[0])=='srgbClr' and len(entry[0])==0,'gradient scheme color unresolved');rgb=entry[0].get('val')
  elif kind=='srgbClr':rgb=value
  else:raise ValueError('gradient stop color unsupported')
  alpha=1.
  for mod in color:
   need(local(mod)=='alpha','gradient stop transform unsupported');alpha=int(mod.get('val'))/100000;need(0<=alpha<=1,'gradient alpha invalid')
  stops.append({'position':int(stop.get('pos')),'color':'#'+rgb.upper(),'alpha':alpha,'sourceType':kind,'sourceValue':value})
 need(len(stops)>=2,'gradient stops incomplete')
 # Resolve the same source shape's geometry, outline and effect separately;
 # the noFill replacement is temporary and never written into the PPTX.
 clone=copy.deepcopy(shape);clone_sp=clone.find('p:spPr',NS);g=clone_sp.find('a:gradFill',NS);index=list(clone_sp).index(g);clone_sp.remove(g);clone_sp.insert(index,ET.Element('{'+A+'}noFill'));shape_evidence=appearance(verifier,part,clone);shape_evidence.pop('fillRGBA',None)
 return {'slide':n,'sourceId':f's{n}-o{oid}','sourcePart':part,'sourcePartSha256':hashlib.sha256(verifier.zip.read(part)).hexdigest(),'shapeAndStroke':shape_evidence,'gradient':{'path':'circle','focusRect':dict(focus.attrib),'tileRect':dict(tile.attrib) if tile is not None else None,'stopsInSourceOrder':stops,'xml':ET.tostring(gradient,encoding='unicode')},'status':'review','limitations':['Typed source evidence only: this does not establish SVG/CSS equivalence, rendered appearance, source alpha eligibility or PowerPoint animation.','Tile rectangle, path focus geometry and renderer differences need independent frame review.']}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('pptx',type=Path);p.add_argument('slide',type=int);p.add_argument('object_id');a=p.parse_args();v=SourceVerifier(a.pptx)
 try:r=inspect(v,a.slide,a.object_id);r['sourceSha256']=file_digest(a.pptx);print(json.dumps(r,ensure_ascii=False,indent=2))
 except (ValueError,KeyError,OSError,ET.ParseError) as e:print(json.dumps({'status':'unresolved','error':str(e)}));raise SystemExit(1)
 finally:v.close()
