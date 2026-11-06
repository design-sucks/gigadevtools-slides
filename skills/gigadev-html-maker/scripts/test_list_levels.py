"""Regression: normalize PPTX list levels without fabricating list items."""
import json
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from build import build

HERE=Path(__file__).resolve().parent

class ListReader(HTMLParser):
 def __init__(self):
  super().__init__();self.active=False;self.stack=[];self.lists=[];self.items=[]
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs);sid=attrs.get('data-source-id')
  if not self.active:
   if sid=='s1-o1':self.active=True;self.stack.append((tag,None));return
   return
  if tag in ('ul','ol'):self.lists.append((tag,attrs))
  item=None
  if sid and sid.startswith('s1-o1-p'):
   item={'id':sid,'tag':tag,'kind':self.lists[-1][0] if tag=='li' and self.lists else None,
         'depth':len(self.lists)-1 if tag=='li' else None,'text':'',
         'type':self.lists[-1][1].get('type') if tag=='li' and self.lists else None,
         'start':self.lists[-1][1].get('start') if tag=='li' and self.lists else None}
   self.items.append(item)
  if tag not in ('br','img','input','hr','meta','link','wbr'):self.stack.append((tag,item))
 def handle_endtag(self,tag):
  if not self.active:return
  if tag in ('ul','ol'):
   assert self.lists and self.lists[-1][0]==tag,'list nesting mismatch'
   self.lists.pop()
  if self.stack and self.stack[-1][0]==tag:self.stack.pop()
  if not self.stack:self.active=False
 def handle_data(self,text):
  if not self.active:return
  for _,item in reversed(self.stack):
   if item is not None:item['text']+=text;break

class ListLevelsTests(unittest.TestCase):
 def run_case(self, items):
  paragraphs=[]
  for index,(kind,level,depth,*rest) in enumerate(items,1):
   detail=rest[0] if rest else {}
   p={'text':f'Item {index}','runs':[{'text':f'Item {index}'}],'level':level,
      'effectiveList':{'status':'resolved','kind':kind or 'none','attributes':detail}}
   paragraphs.append(p)
  block={'id':'s1-o1','kind':'text','paragraphs':paragraphs}
  deck={'title':'List levels','source':{'sha256':'abc'},'slides':[{'id':'s1','sourceNumber':1,'blocks':[block]}]}
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'deck.json').write_text(json.dumps(deck));html=build(root/'deck.json',root/'deck.html')
   parser=ListReader();parser.feed(html)
   expected=[{'id':f's1-o1-p{i}','tag':'li' if kind else 'p','kind':kind,'depth':depth,'text':f'Item {i}'} for i,(kind,_level,depth,*_) in enumerate(items,1)]
   self.assertEqual([{k:r[k] for k in ('id','tag','kind','depth','text')} for r in parser.items],expected)
   target={'slides':[{'id':'s1','sourceNumber':1,'html':html,'blocks':[block]}]}
   (root/'target.json').write_text(json.dumps(target))
   result=subprocess.run(['python3',str(HERE/'check_source_inventory.py'),str(root/'deck.json'),str(root/'target.json')],capture_output=True,text=True)
   report=json.loads(result.stdout)
   self.assertEqual(result.returncode,0,report)
   self.assertFalse([issue for issue in report['issues'] if issue['code'] in ('list-structure-mismatch','numbering-mismatch')],report)
   return parser.items
 def test_initial_nonzero_equal(self):self.run_case([('ul',1,0),('ul',1,0)])
 def test_ascending_and_return(self):self.run_case([('ul',0,0),('ul',1,1),('ul',1,1),('ul',0,0)])
 def test_nonzero_ascending_and_lower_root(self):self.run_case([('ul',2,0),('ul',2,0),('ul',3,1),('ul',3,1),('ul',2,0),('ul',1,0),('ul',1,0),('ul',2,1)])
 def test_equal_type_switch_and_numbering(self):
  got=self.run_case([('ul',1,0),('ol',1,0,{'type':'alphaLcPeriod','startAt':'3'}),('ul',1,0)])
  self.assertEqual((got[1]['type'],got[1]['start']),('a','3'))
 def test_nested_type_switch(self):self.run_case([('ul',1,0),('ul',2,1),('ol',2,1),('ul',1,0),('ol',0,0)])
 def test_skipped_levels_and_plain_reset(self):self.run_case([('ul',0,0),('ul',3,1),('ul',2,1),('ul',3,2),('ul',0,0),(None,0,None),('ul',4,0),('ul',4,0)])
 def test_rejects_equal_level_items_in_wrong_nested_list(self):
  paragraphs=[{'text':'First','level':1,'effectiveList':{'status':'resolved','kind':'ul'}},
              {'text':'Second','level':1,'effectiveList':{'status':'resolved','kind':'ul'}}]
  block={'id':'s1-o1','kind':'text','paragraphs':paragraphs}
  source={'source':{'sha256':'abc'},'slides':[{'sourceNumber':1,'blocks':[block]}]}
  target={'slides':[{'sourceNumber':1,'html':'<div data-source-id="s1-o1"><ul><li>First<ul><li>Second</li></ul></li></ul></div>'}]}
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'source.json').write_text(json.dumps(source));(root/'target.json').write_text(json.dumps(target))
   result=subprocess.run(['python3',str(HERE/'check_source_inventory.py'),str(root/'source.json'),str(root/'target.json')],capture_output=True,text=True)
   report=json.loads(result.stdout);self.assertEqual(result.returncode,1)
   self.assertTrue(any(i['code']=='list-structure-mismatch' and i['paragraph']==1 for i in report['issues']))
 def test_unresolved_inheritance_stays_review(self):
  paragraphs=[{'text':'First','level':1,'effectiveList':{'status':'resolved','kind':'ul'}},
              {'text':'Uncertain','level':2,'effectiveList':{'status':'unresolved','kind':'unresolved'}},
              {'text':'Second','level':1,'effectiveList':{'status':'resolved','kind':'ul'}}]
  block={'id':'s1-o1','kind':'text','paragraphs':paragraphs}
  source={'source':{'sha256':'abc'},'slides':[{'sourceNumber':1,'blocks':[block]}]}
  target={'slides':[{'sourceNumber':1,'html':'<div data-source-id="s1-o1"><ul><li>First</li></ul><p>Uncertain</p><ul><li>Second</li></ul></div>'}]}
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'source.json').write_text(json.dumps(source));(root/'target.json').write_text(json.dumps(target))
   result=subprocess.run(['python3',str(HERE/'check_source_inventory.py'),str(root/'source.json'),str(root/'target.json')],capture_output=True,text=True)
   report=json.loads(result.stdout);self.assertEqual(result.returncode,0);self.assertEqual(report['status'],'review')
   self.assertTrue(any(i['code']=='list-inheritance-unresolved' for i in report['observations']))
 def test_numbered_parent_continues_after_child(self):
  got=self.run_case([('ol',0,0,{'type':'alphaLcPeriod','startAt':'3'}),('ul',1,1),('ol',0,0,{'type':'alphaLcPeriod','startAt':'3'})])
  self.assertEqual((got[0]['type'],got[0]['start'],got[2]['type'],got[2]['start']),('a','3','a','3'))

if __name__=='__main__':unittest.main()
