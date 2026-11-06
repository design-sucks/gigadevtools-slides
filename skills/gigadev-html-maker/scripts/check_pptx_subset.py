"""Verify a PPTX slide subset and report original-to-subset source IDs.

Does not modify inventories; source hash/numbering remain those of each PPTX.
"""
import argparse, hashlib, json, posixpath
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

P='http://schemas.openxmlformats.org/presentationml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL='http://schemas.openxmlformats.org/package/2006/relationships'

def digest_file(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def rels(z,part):
 name=posixpath.join(posixpath.dirname(part),'_rels',posixpath.basename(part)+'.rels')
 if name not in z.namelist():return {}
 return {e.get('Id'):(e.get('Type'),e.get('Target'),e.get('TargetMode')) for e in ET.fromstring(z.read(name))}

def slide_parts(z):
 root=ET.fromstring(z.read('ppt/presentation.xml')); rel=rels(z,'ppt/presentation.xml')
 def target(x):
  value=rel[x.get('{%s}id'%R)][1]
  return value[1:] if value.startswith('/') else posixpath.normpath(posixpath.join('ppt',value))
 return [target(x) for x in root.findall('{%s}sldIdLst/{%s}sldId'%(P,P))]

def check(manifest, base):
 original=Path(manifest['sourcePptx']); mini=(base/manifest['miniPptx']).resolve(); issues=[]; mappings=[]
 for path,key in ((original,'sourceSha256'),(mini,'miniSha256')):
  if digest_file(path)!=manifest[key]:issues.append({'code':'package-hash-mismatch','path':str(path)})
 with ZipFile(original) as src,ZipFile(mini) as dst:
  source_parts=slide_parts(src);mini_parts=slide_parts(dst);seen=set()
  for row in manifest['slides']:
   n=row['miniSlide'];o=row['originalSlide'];part=row['sourcePart']
   if n in seen or n<1 or n>len(mini_parts) or o<1 or o>len(source_parts):
    issues.append({'code':'invalid-slide-map','miniSlide':n,'originalSlide':o});continue
   seen.add(n)
   if source_parts[o-1]!=part or mini_parts[n-1]!=part:
    issues.append({'code':'slide-part-mismatch','miniSlide':n,'originalSlide':o});continue
   a=src.read(part); b=dst.read(part);sha=hashlib.sha256(a).hexdigest()
   if a!=b or sha!=row['slideXmlSha256']:issues.append({'code':'slide-xml-mismatch','part':part})
   sr,dr=rels(src,part),rels(dst,part)
   if sr!=dr:issues.append({'code':'slide-relationships-mismatch','part':part})
   for rid,(typ,target,mode) in sr.items():
    if mode=='External':continue
    resolved=posixpath.normpath(posixpath.join(posixpath.dirname(part),target)) if not target.startswith('/') else target[1:]
    if resolved not in src.namelist() or resolved not in dst.namelist() or hashlib.sha256(src.read(resolved)).digest()!=hashlib.sha256(dst.read(resolved)).digest():
     issues.append({'code':'slide-related-part-mismatch','part':part,'relationshipId':rid,'target':resolved})
   root=ET.fromstring(a);ids=[]
   for e in root.iter():
    if e.tag=='{%s}cNvPr'%P and e.get('id'):
     oid=e.get('id');ids.append({'objectId':oid,'miniId':f's{n}-o{oid}','originalId':f's{o}-o{oid}'})
   mappings.append({'miniSlide':n,'originalSlide':o,'part':part,'xmlSha256':sha,'objects':ids})
  if len(seen)!=len(mini_parts):issues.append({'code':'unmapped-mini-slides','expected':len(mini_parts),'mapped':len(seen)})
 return {'status':'fail' if issues else 'pass','sourceSha256':manifest['sourceSha256'],'miniSha256':manifest['miniSha256'],'slides':mappings,'issues':issues,'limitations':['Package/slide and direct relationship byte identity only; not proof of rendering, semantic completeness or all transitive package dependencies.','IDs are an explicit correspondence, not a replacement for the independently extracted inventory or its source numbering.']}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest',type=Path);p.add_argument('--case',required=True);a=p.parse_args()
 d=json.loads(a.manifest.read_text());case=next(x for x in d['cases'] if x['case']==a.case)
 result=check(case,a.manifest.parent);print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['status']=='pass' else 1)
