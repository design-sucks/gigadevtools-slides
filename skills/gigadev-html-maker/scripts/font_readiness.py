#!/usr/bin/env python3
"""Summarize check_text_layout --actual-fonts --inventory for a scoped pre-edit decision."""
import argparse,json,pathlib,re,unicodedata
p=argparse.ArgumentParser(description=__doc__);p.add_argument('report');p.add_argument('--source-id',action='append',default=[]);p.add_argument('--resource-manifest',action='append',default=[]);a=p.parse_args()
d=json.loads(pathlib.Path(a.report).read_text()); resources=[]
for filename in a.resource_manifest:
 f=pathlib.Path(filename).resolve();m=json.loads(f.read_text())
 for x in m.get('faces',[]):
  candidate=(f.parent.parent/x['path']).resolve() if x.get('path','').startswith('fonts/') else (f.parent/x['path']).resolve()
  resources.append({'family':x.get('family'),'weight':str(x.get('weight')),'path':str(candidate),'exists':candidate.is_file(),'sha256':x.get('sha256')})
def norm(x):return ''.join(c for c in unicodedata.normalize('NFKC',str(x)).casefold() if c.isalnum())
out=[]
for slide in d.get('slides',[]):
 for b in slide['blocks']:
  sid=b.get('sourceId') or b.get('sourceAncestorId')
  if a.source_id and sid not in a.source_id:continue
  required=b.get('sourceTypography',{}).get('families',[]);actual=b.get('renderedFonts');names=[norm(f.get('familyName','')) for f in actual or []];candidates=[r for r in resources if any(norm(r['family'])==norm(n) for n in required) and r['exists']]
  if actual is None or not actual or not required:status='unresolved'
  elif all(norm(n) in names for n in required):status='family-match-review-weight-and-glyphs'
  else:status='substitution-or-alias-review'
  out.append({'slide':slide['slide'],'sourceId':sid,'editorId':b['editorId'],'requiredFamilies':required,'requiredFaces':b.get('sourceTypography',{}).get('faces',[]),'requiredSizePoints':b.get('sourceTypography',{}).get('nominalPt'),'sourceUnresolvedRuns':b.get('sourceTypography',{}).get('unresolvedRuns'),'authoredCssFamily':b['fontFamily'],'authoredCssWeight':b['fontWeight'],'renderedFonts':actual,'localResourceCandidates':candidates,'status':status})
if a.source_id and set(a.source_id)-{x['sourceId'] for x in out}:raise SystemExit('Requested source ID missing from rendered report')
print(json.dumps({'htmlSha256':d.get('inputSha256'),'viewport':d.get('viewport'),'scope':'rendered glyphs in this browser frame','limitations':['Local resource candidates are catalog entries, not proof that the browser used a file.','Source family aliases, inherited/complex styles and weight equivalence require manual review; unresolved is not a match.','System font paths are not inferred.'], 'targets':out},ensure_ascii=False,indent=2))
