from pathlib import Path
from tempfile import TemporaryDirectory
import json,copy
from compositions import catalog,render,ROOT
from build import build

def run():
 rows=catalog()['compositions'];assert len(rows)==18 and len({r['id']for r in rows})==18
 for row in rows:
  data=json.loads((ROOT/row['example']).read_text());s=render(row['id'],data,row['version']);assert s+'\n'==(ROOT/row['fragment']).read_text();assert 'data-composition-sample="true"'in s
 data=json.loads((ROOT/'examples/problem-cards.json').read_text());data['items']=data['items'][:3];data['items'][0]['icon']='media/icon.svg';data['items'][0]['iconSourceId']='source-icon';data['items'][0]['title']={'text':'<script>unsafe</script>','sourceId':'source-title'};s=render('problem-cards',data);assert '<script>'not in s and '&lt;script&gt;'in s and 'data-source-id="source-title"'in s and 'data-source-id="source-icon"'in s
 def rejected(ident,value):
  try:render(ident,value)
  except (ValueError,KeyError):return
  raise AssertionError('Invalid composition accepted')
 rejected('not-a-layout',data);bad=copy.deepcopy(data);bad['unknownField']='must not be ignored';rejected('problem-cards',bad);bad=copy.deepcopy(data);bad['items'][0]['body']='x'*1000;rejected('problem-cards',bad)
 bad=json.loads((ROOT/'examples/comparison.json').read_text());bad['rows'][0].pop();rejected('comparison',bad)
 bad=json.loads((ROOT/'examples/thesis-evidence.json').read_text());bad['items'][0]['icon']='invisible.svg';rejected('thesis-evidence',bad)
 with TemporaryDirectory()as tmp:
  r=Path(tmp);source=r/'deck.json';source.write_text(json.dumps({'title':'Guard','slides':[{'id':'test','composition':{'id':'problem-cards','data':data}}]}))
  try:build(source,r/'bad.html')
  except ValueError as e:assert 'sample content'in str(e)
  else:raise AssertionError('Sample content accepted for an ordinary delivery')
 print('PASS18 versioned fragments, escaped text/source IDs/icons, invalid/missing/oversized fields, unrendered graphics and sample-content delivery guard')
if __name__=='__main__':run()
