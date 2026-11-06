"""Exercise final review guard: draft, absent, stale and accepted evidence."""
import base64,hashlib,json,tempfile
from pathlib import Path
from build import build

with tempfile.TemporaryDirectory() as d:
 p=Path(d);deck=p/'deck.json';plan=p/'plan.json';frame=p/'frame.png'
 deck.write_text(json.dumps({'title':'guard','slides':[{'id':'s1','html':'<p>Example</p>'}]}))
 frame.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/WtkAAAAASUVORK5CYII='))
 row={k:'reviewed' for k in ('sourceId','purpose','emphasis','readingOrder','groups','density','editability','works','problem','capacity','technicalRisk')}
 row.update(slideId='s1',decision='adapt',sourceRender='frame.png');data={'slides':[row]}
 def attempt(name,final=True):
  try:build(deck,p/(name+'.html'),final=final,composition_plan=plan);return True
  except ValueError:return False
 plan.write_text(json.dumps(data));assert attempt('draft',False);assert not attempt('missing')
 row['visualReview']={'reviewed':True,'observation':'inspected','candidateRender':'frame.png','candidateRenderSha256':hashlib.sha256(frame.read_bytes()).hexdigest(),'projectSha256':hashlib.sha256(deck.read_bytes()).hexdigest()};plan.write_text(json.dumps(data));assert attempt('valid')
 row['visualReview']['candidateRenderSha256']='0'*64;plan.write_text(json.dumps(data));assert not attempt('stale_frame')
 row['visualReview']['candidateRenderSha256']=hashlib.sha256(frame.read_bytes()).hexdigest();row['visualReview']['projectSha256']='0'*64;plan.write_text(json.dumps(data));assert not attempt('stale_project')
 row['visualReview']['projectSha256']=hashlib.sha256(deck.read_bytes()).hexdigest();row['visualReview']['reviewed']=False;plan.write_text(json.dumps(data));assert not attempt('unreviewed')
print('PASS: draft, final evidence, missing/stale/unreviewed negatives')
