"""Compare two independently extracted source inventories using verified subset mapping."""
import argparse, hashlib, json
from pathlib import Path

FIELDS=('kind','paragraphs','rows','series','connectorEnds','tableLayout','mediaType','mediaPart')

def compare(original,mini,mapping):
 issues=[]; rows=[]
 if mapping.get('status')!='pass' or original.get('source',{}).get('sha256')!=mapping.get('sourceSha256') or mini.get('source',{}).get('sha256')!=mapping.get('miniSha256'):
  raise ValueError('Verified subset mapping and matching independent source hashes required')
 for row in mapping['slides']:
  a=[s for s in original['slides'] if s['sourceNumber']==row['originalSlide']]; b=[s for s in mini['slides'] if s['sourceNumber']==row['miniSlide']]
  if len(a)!=1 or len(b)!=1:issues.append({'code':'slide-missing-or-ambiguous','map':row});continue
  def objects(slide):
   result={}
   for obj in slide.get('blocks',[]):
    oid=obj.get('source',{}).get('objectId')
    if not oid or oid in result:raise ValueError('Missing or duplicate source object ID')
    result[oid]=obj
   return result
  left,right=objects(a[0]),objects(b[0]);same=0
  for oid in left.keys()|right.keys():
   if oid not in left or oid not in right:issues.append({'code':'object-missing','originalSlide':row['originalSlide'],'objectId':oid});continue
   for field in FIELDS:
    if left[oid].get(field)!=right[oid].get(field):issues.append({'code':'source-field-differs','originalSlide':row['originalSlide'],'objectId':oid,'field':field})
   same+=1
  rows.append({'miniSlide':row['miniSlide'],'originalSlide':row['originalSlide'],'comparedObjects':same})
 return {'status':'fail' if issues else 'pass','slides':rows,'issues':issues,'fieldsCompared':FIELDS,'limitations':['Compares extracted source records, not authored HTML, visible objects or visual fidelity.','Differences in extraction versions or unsupported PPTX features require review; identical extractor omissions are not detected.']}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('original',type=Path);p.add_argument('mini',type=Path);p.add_argument('mapping',type=Path);a=p.parse_args()
 try:r=compare(*(json.loads(x.read_text()) for x in (a.original,a.mini,a.mapping)))
 except (ValueError,KeyError,OSError) as e:p.exit(2,str(e)+'\n')
 print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['status']=='pass' else 1)
