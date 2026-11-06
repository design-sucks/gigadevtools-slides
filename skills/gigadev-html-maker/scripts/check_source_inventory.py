"""Compare an independently extracted PPTX inventory with a derivative project.

This is a conservative project-level audit, not a browser or visual acceptance test.
Run extract_pptx.py on the original PPTX in a separate directory first.
"""
import argparse, hashlib, json, re, sys
from xml.etree import ElementTree as ET
from pathlib import Path
from html.parser import HTMLParser
import importlib.util
_list_spec=importlib.util.spec_from_file_location('gd_list_levels',Path(__file__).resolve().parent/'list_levels.py')
_list_module=importlib.util.module_from_spec(_list_spec);_list_spec.loader.exec_module(_list_module)
normalize_list_levels=_list_module.normalize_list_levels
_disposition_spec=importlib.util.spec_from_file_location('gd_source_dispositions',Path(__file__).resolve().parent/'source_dispositions.py')
_disposition_module=importlib.util.module_from_spec(_disposition_spec);_disposition_spec.loader.exec_module(_disposition_module)

class Targets(HTMLParser):
 VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
 def __init__(self):
  super().__init__(); self.stack=[]; self.targets={}
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs); sid=attrs.get('data-source-id')
  if tag in ('p','li','td','th'):self.handle_data(' ')
  for _,parent,_attrs in self.stack:
   if parent and tag in ('p','li'):
    containers=[(name,a) for name,_,a in self.stack if name in ('ul','ol')]
    self.targets[parent][-1]['units'].append({'tag':tag,'list':containers[-1][0] if containers else None,'listAttrs':containers[-1][1] if containers else {},'level':len(containers)-1})
  if sid:self.targets.setdefault(sid,[]).append({'tag':tag,'text':'','units':[]})
  if tag=='br':self.handle_data(' ')
  if tag not in self.VOID:self.stack.append((tag,sid,attrs))
 def handle_endtag(self,tag):
  for i in range(len(self.stack)-1,-1,-1):
   if self.stack[i][0]==tag:del self.stack[i:];break
 def handle_data(self,data):
  for _,sid,_attrs in self.stack:
   if sid:self.targets[sid][-1]['text']+=data

def norm(s):return re.sub(r'\s+',' ',s or '').strip()
def list_type(p):
 effective=p.get('effectiveList',{})
 if effective.get('status')=='resolved':return effective.get('kind') if effective.get('kind') in ('ul','ol') else None
 try:
  root=ET.fromstring(p.get('paragraphPropertiesXml',''))
 except ET.ParseError:return None
 names={e.tag.rsplit('}',1)[-1] for e in root}
 if 'buAutoNum' in names:return 'ol'
 if names.intersection(('buChar','buBlip')):return 'ul'
 return None
def numbering(p):
 effective=p.get('effectiveList',{})
 if effective.get('status')=='resolved' and effective.get('kind')=='ol':
  kinds={'arabicPeriod':'1','alphaLcPeriod':'a','alphaUcPeriod':'A','romanLcPeriod':'i','romanUcPeriod':'I'}
  attrs=effective.get('attributes',{})
  return {'type':kinds.get(attrs.get('type')),'start':attrs.get('startAt','1')}
 try:root=ET.fromstring(p.get('paragraphPropertiesXml',''))
 except ET.ParseError:return None
 bullet=next((e for e in root if e.tag.rsplit('}',1)[-1]=='buAutoNum'),None)
 if bullet is None:return None
 kinds={'arabicPeriod':'1','alphaLcPeriod':'a','alphaUcPeriod':'A','romanLcPeriod':'i','romanUcPeriod':'I'}
 return {'type':kinds.get(bullet.get('type')),'start':bullet.get('startAt','1')}
def block_text(b):
 if b['kind']=='text':return ' '.join(p.get('text','') for p in b.get('paragraphs',[]))
 return ' '.join(p.get('text','') for row in b.get('rows',[]) for cell in row for p in cell)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('inventory');p.add_argument('project');p.add_argument('--mode',choices=['editable','viewing'],default='editable');p.add_argument('--transformations');p.add_argument('--source',type=Path);p.add_argument('--off-canvas',type=Path);a=p.parse_args()
 src=json.loads(Path(a.inventory).read_text());dst=json.loads(Path(a.project).read_text())
 if not src.get('source',{}).get('sha256'):p.error('Inventory must be an independent PPTX extraction with source.sha256')
 source_verified=False
 if a.source:
  digest=hashlib.sha256()
  with a.source.open('rb') as stream:
   for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
  if digest.hexdigest()!=src['source']['sha256']:p.error('PPTX hash does not match the independent inventory')
  source_verified=True
 transformations={}
 if a.transformations:
  for entry in json.loads(Path(a.transformations).read_text()).get('transformations',[]):
   key=(entry.get('slide'),entry.get('sourceId'))
   if key in transformations or not isinstance(key[0],int) or not key[1] or not entry.get('targetId') or not entry.get('reason','').strip() or entry.get('approved') is not True or not isinstance(entry.get('before'),str) or not isinstance(entry.get('after'),str):p.error('Each transformation needs unique slide/sourceId, targetId, reason, approved=true and exact before/after')
   transformations[key]=entry
 dispositions={};seen_dispositions=set();verifier=None;manifest_reason=None
 if a.off_canvas:
  manifest=json.loads(a.off_canvas.read_text());entries=manifest.get('dispositions')
  if not isinstance(entries,list):p.error('Off-canvas manifest must contain a dispositions list')
  for entry in entries:
   if not isinstance(entry,dict) or not isinstance(entry.get('slide'),int) or not isinstance(entry.get('sourceId'),str):p.error('Invalid off-canvas slide/source ID')
   key=(entry['slide'],entry['sourceId'])
   if key in dispositions:p.error('Duplicate off-canvas disposition')
   dispositions[key]=entry
  if not source_verified:manifest_reason='original PPTX source and verified hash required'
  elif manifest.get('sourceSha256')!=src['source']['sha256']:manifest_reason='manifest source hash differs from independent inventory'
  else:
   try:verifier=_disposition_module.SourceVerifier(a.source)
   except (OSError,ValueError,KeyError,ET.ParseError) as e:manifest_reason='cannot inspect original PPTX: '+str(e)
 slide_map={s.get('sourceNumber'):s for s in dst['slides'] if s.get('sourceNumber') is not None}; issues=[]; observations=[]; total=0
 parsers={};global_targets={}
 for candidate in dst['slides']:
  parsed=Targets();parsed.feed(candidate.get('html',''));parsers[id(candidate)]=parsed
  for target_id,values in parsed.targets.items():
   if values:global_targets.setdefault(target_id,[]).append(candidate.get('id'))
 for slide in src['slides']:
  n=slide['sourceNumber']; target=slide_map.get(n)
  if target is None:issues.append({'code':'missing-slide','slide':n});continue
  parser=parsers[id(target)]
  blocks={b['id']:b for b in target.get('blocks',[])}
  for b in slide.get('blocks',[]):
   if b['kind'] not in ('text','table') or not norm(block_text(b)):continue
   total+=1; sid=b['id']; transform=transformations.get((n,sid)); target_id=transform['targetId'] if transform else sid; values=parser.targets.get(target_id,[])
   disposition=dispositions.get((n,sid))
   if disposition is not None:
    seen_dispositions.add((n,sid))
    try:
     if b['kind']!='text':raise ValueError('only source text shapes are supported')
     if transform:raise ValueError('disposition conflicts with a source transformation')
     if values or global_targets.get(sid):raise ValueError('target exists in output, possibly on another slide; omission is not applicable')
     if manifest_reason or verifier is None:raise ValueError(manifest_reason or 'original PPTX unavailable')
     evidence=_disposition_module.validate_disposition(disposition,slide,b,dst,target,verifier,a.off_canvas.resolve().parent,src['source']['sha256'],src['source'].get('canvas'))
     observations.append(evidence)
     continue
    except (OSError,ValueError,KeyError,ET.ParseError) as e:
     issues.append({'code':'off-canvas-disposition-unverified','slide':n,'sourceId':sid,'reason':str(e)})
   if not values:
    issues.append({'code':'missing-editable-target','slide':n,'sourceId':sid,'kind':b['kind'],'retainedInProject':sid in blocks});continue
   if len(values)!=1:issues.append({'code':'ambiguous-target','slide':n,'sourceId':sid,'count':len(values)});continue
   actual=norm(values[0]['text']); original=norm(block_text(b))
   if transform and original==norm(transform['before']) and actual==norm(transform['after']):observations.append({'code':'approved-transformation','slide':n,'sourceId':sid,'targetId':target_id,'reason':transform['reason']})
   elif transform:issues.append({'code':'transformation-precondition-mismatch','slide':n,'sourceId':sid,'targetId':target_id})
   elif actual!=original:issues.append({'code':'text-mismatch','slide':n,'sourceId':sid})
   if b['kind']=='table' and values[0]['tag']!='table':issues.append({'code':'table-structure-unverified','slide':n,'sourceId':sid})
   if b['kind']=='text':
    paragraphs=b.get('paragraphs',[]); units=values[0]['units'];levels=normalize_list_levels(paragraphs,list_type)
    unresolved=sum(p.get('effectiveList',{}).get('status')=='unresolved' for p in paragraphs)
    if unresolved:observations.append({'code':'list-inheritance-unresolved','slide':n,'sourceId':sid,'paragraphs':unresolved})
    if len(paragraphs)>1 and len(units)!=len(paragraphs):issues.append({'code':'paragraph-count-mismatch','slide':n,'sourceId':sid,'expected':len(paragraphs),'actual':len(units)})
    for i,para in enumerate(paragraphs):
     kind=list_type(para)
     if kind and (i>=len(units) or units[i]['tag']!='li' or units[i]['list']!=kind or units[i]['level']!=levels[i][0]):
      issues.append({'code':'list-structure-mismatch','slide':n,'sourceId':sid,'paragraph':i,'expectedList':kind,'expectedLevel':levels[i][0],'sourceLevel':para.get('level',0)})
     numbers=numbering(para)
     first=bool(levels[i] and levels[i][1])
     if numbers and first and i<len(units):
      attrs=units[i]['listAttrs'];actual_type=attrs.get('type','1');actual_start=attrs.get('start','1')
      if numbers['type'] is None:observations.append({'code':'numbering-style-unresolved','slide':n,'sourceId':sid,'paragraph':i})
      elif actual_type!=numbers['type'] or actual_start!=numbers['start']:issues.append({'code':'numbering-mismatch','slide':n,'sourceId':sid,'paragraph':i,'expected':numbers,'actual':{'type':actual_type,'start':actual_start}})
 if verifier is not None:verifier.close()
 for key in dispositions.keys()-seen_dispositions:issues.append({'code':'off-canvas-disposition-unmatched','slide':key[0],'sourceId':key[1]})
 status='fail' if issues and a.mode=='editable' else 'review' if issues or observations else 'pass'
 print(json.dumps({'status':status,'mode':a.mode,'sourceSha256':src['source']['sha256'],'sourceHashVerified':source_verified,'inventorySha256':hashlib.sha256(Path(a.inventory).read_bytes()).hexdigest(),'offCanvasManifestSha256':_disposition_module.file_digest(a.off_canvas) if a.off_canvas else None,'sourceTextObjects':total,'issues':issues,'observations':observations,'limitations':['Project markup only: saved HTML, browser editability and visual fidelity require separate checks; unresolved PPTX inheritance requires review.','Composition renderer and explicit transformations require manual source mapping review.','Even a matching PPTX hash does not prove an inventory was independently or correctly extracted.']},ensure_ascii=False,indent=2))
 return 1 if status=='fail' else 0
if __name__=='__main__':sys.exit(main())
