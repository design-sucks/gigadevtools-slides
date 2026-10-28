"""Focused Maker regressions for slide backgrounds, metadata and journal targets."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json, re
from build import build

def run():
 with TemporaryDirectory(prefix='gd-maker-core-') as tmp:
  root=Path(tmp);project=root/'project';project.mkdir();(project/'bg.png').write_bytes(b'background')
  deck={'title':'Core regression','proofreadingStatus':'reviewed','slides':[
   {'id':'a','label':'01 / Original topic','section':'Topic 1','topic':'01 / Problem','sourceNumber':2,'header':'full','background':{'type':'image','asset':'bg.png','focal':'25% 75%','size':'cover'},'html':'<p data-source-id="heading" data-eid="e1">Before <span>accepted</span><br> text</p><h1>A meaningful step 1</h1><ol><li>01 / 01</li></ol><figure><img src="bg.png" alt=""></figure>'},
   {'id':'b','label':'02. Other','section':'Topic 2','topic':'Other','sourceNumber':2,'header':'number','html':'<p>Body 2 remains</p>'},
   {'id':'c','label':'03. No header','navigationLabel':'01 / Explicit section','header':'none','html':'<p>Text</p>'}]}
  deck['preparationChanges']=[{'id':'change1','slide':'a','sourceId':'heading','actor':'llm','kind':'text','status':'pending','title':'Proposal','before':'Before accepted\n text','after':'Before accepted text'}]
  path=project/'deck.json';path.write_text(json.dumps(deck));out=root/'deck.html';built=build(path,out)
  assert '.gd-base{' in built
  assert 'background-image:url(data:image/png;base64,YmFja2dyb3VuZA==)' in built
  assert re.search(r'<div class="slide-inner"><div class="gd-slide-background"[^>]*></div><div class="gd-content">',built), 'background must be inside the shared scroll/keyboard motion layer'
  assert 'data-gd-source-number="2"' in built and 'data-sk-topic="Problem"' in built and 'Body 2 remains' in built and '01 / 01' in built
  assert '.gd-slide-background{position:absolute;left:0;top:0;right:auto;bottom:auto;width:calc(var(--gd-scroll-width,100vw) / var(--gd-motion-zoom,1));height:calc(var(--gd-scroll-height,100vh) / var(--gd-motion-zoom,1))' in built and 'background-size:cover' in built and '.slide img{max-width:100%;max-height:650px' in built
  state=json.loads(re.search(r'id="sk-deck-state">(.*?)</script>',built).group(1))
  assert state['slides'][0]['label']=='Original topic' and state['slides'][0]['sourceLabel']=='01 / Original topic' and state['slides'][0]['topic']=='01 / Problem' and state['slides'][0]['sourceTopic']=='01 / Problem' and state['slides'][0]['navigationTopic']=='Problem'
  assert state['slides'][1]['label']=='Other' and state['slides'][1]['sourceLabel']=='02. Other'
  assert state['slides'][2]['label']=='01 / Explicit section'
  assert state['proofreadingStatus']=='has_proposals'
  for mode, expected in [('full','data-header="full"'),('number','data-header="number"'),('none','data-header="none"')]:assert expected in built
  def rejected(change,needle,duplicate=False):
   deck['slides'][0]['html']=('<p data-source-id="heading" data-eid="e1">Before <span>accepted</span><br> text</p><p data-source-id="heading" data-eid="e2">Duplicate</p>' if duplicate else '<p data-source-id="heading" data-eid="e1">Before <span>accepted</span><br> text</p><figure><img src="bg.png" alt=""></figure>')
   deck['preparationChanges']=[change];path.write_text(json.dumps(deck))
   try:build(path,root/'invalid.html')
   except ValueError as e:assert needle in str(e)
   else:raise AssertionError('Invalid journal target accepted')
  canonical={'id':'change1','slide':'a','sourceId':'heading','actor':'llm','kind':'text','status':'pending','title':'Proposal','before':'Before accepted\n text','after':'Before accepted text'}
  change=dict(canonical);change['sourceId']='missing';rejected(change,'must target exactly one')
  change=dict(canonical);change['before']='Different';rejected(change,'does not match expected before')
  change=dict(canonical);change['before']='Before accepted\ntext';rejected(change,'does not match expected before')
  rejected(dict(canonical),'found 2',True)
  try:build(path,root/'missing-theme.html',root/'missing-theme.json')
  except FileNotFoundError:pass
  else:raise AssertionError('Missing explicit theme silently fell back')
 print('PASS full-slide offline background, ordinary illustration, 16:9 content/export styles, navigation labels, header modes, meaningful numbers, proofreading metadata and journal target validation')

if __name__=='__main__':run()
