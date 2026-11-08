"""Regression probes for content/paint/chrome separation; no browser required."""
import copy, unittest
from presentation_roles import prepare, audit
C={'widthEMU':1920,'heightEMU':1080}
def block(sid,text,y=10,x=20):
 return {'id':sid,'kind':'text','paragraphs':[{'text':text}], 'shapePropertiesXml':f'<sp xmlns:a="urn:test"><a:off x="{x}" y="{y}"/><a:ext cx="300" cy="40"/></sp>'}
def slide():
 return {'id':'s1','sourceNumber':1,'blocks':[block('nav','01 / Раздел'),block('page','01',1000,1800),block('heading','Содержательный заголовок',150),{'id':'image','kind':'image','asset':'assets/a.png','backgroundCandidate':True}], 'sourceChrome':[{'sourceId':'nav','role':'navigation','originalText':'01 / Раздел','reviewed':True,'reason':'Source kicker repeated in shell'}, {'sourceId':'page','role':'page-number','originalText':'01','reviewed':True,'reason':'Source footer replaced by current order'}], 'background':{'type':'image','sourceId':'image','asset':'assets/a.png'}}
BODY='<img data-source-id="image" src="assets/a.png"><p data-source-id="nav">01 / Раздел</p><h1 data-source-id="heading">Содержательный заголовок</h1><p data-source-id="page">01</p>'
class Roles(unittest.TestCase):
 def test_promotes_only_reviewed_roles(self):
  s=slide();original=copy.deepcopy(s);result=prepare(s,BODY,C,True);self.assertEqual(result,'<h1 data-source-id="heading">Содержательный заголовок</h1>');self.assertEqual(s,original)
 def test_body_already_omits_roles(self): self.assertIn('heading',prepare(slide(),'<h1 data-source-id="heading">Содержательный заголовок</h1>',C,True))
 def test_nested_target_protected(self):
  with self.assertRaises(ValueError):prepare(slide(),'<div data-source-id="nav">01 / Раздел<span data-source-id="other"></span></div>',C)
 def test_heading_protected(self):
  with self.assertRaises(ValueError):prepare(slide(),'<h1 data-source-id="nav">01 / Раздел</h1>',C)
 def test_unreviewed_or_changed_original_rejected(self):
  for key,value in [('reviewed',False),('originalText','Не то'),('role','content')]:
   s=slide();s['sourceChrome'][0][key]=value
   with self.assertRaises(ValueError):prepare(s,BODY,C)
 def test_body_value_or_long_prose_protected(self):
  for change in ['body','long','link','list','duplicate']:
   s=slide()
   if change=='body':s['blocks'][0]=block('nav','01 / Раздел',400)
   if change=='long':s['blocks'][0]['paragraphs'][0]['text']='a'*181;s['sourceChrome'][0]['originalText']='a'*181
   if change=='link':s['blocks'][0]['paragraphs'][0]['runs']=[{'text':'01 / Раздел','link':'https://example.com'}]
   if change=='list':s['blocks'][0]['paragraphs'][0]['effectiveList']={'kind':'ul'}
   if change=='duplicate':s['sourceChrome'].append(copy.deepcopy(s['sourceChrome'][0]))
   with self.assertRaises(ValueError,msg=change):prepare(s,BODY,C)
 def test_background_asset_must_match(self):
  s=slide();s['background']['asset']='assets/other.png'
  with self.assertRaises(ValueError):prepare(s,BODY,C)
 def test_final_gate_handles_single_quote(self):
  s=slide();s.pop('background')
  with self.assertRaisesRegex(ValueError,'full-canvas'):prepare(s,BODY.replace('"',"'"),C,True)
 def test_reviewed_illustration_escape(self):
  s=slide();s.pop('background');s['sourceImageRoles']={'image':{'role':'illustration','reviewed':True,'reason':'Reviewed screenshot of software'}};self.assertIn('<img',prepare(s,BODY,C,True))
 def test_source_footer_cannot_be_accidentally_retained(self):
  s=slide();s['sourceChrome']=s['sourceChrome'][:1]
  with self.assertRaisesRegex(ValueError,'header/footer'):prepare(s,BODY,C,True)
  s['sourceChromeDecisions']={'page':{'role':'content','reviewed':True,'reason':'This number is an actual body value'}};self.assertIn('data-source-id="page"',prepare(s,BODY,C,True))
 def test_independent_inventory_is_required(self):
  s=slide();src={'source':{'canvas':C},'slides':[copy.deepcopy(s)]};p={'slides':[s]};self.assertEqual(len(audit(src,p)),2);src['slides'][0]['blocks'][0]['paragraphs'][0]['text']='changed'
  with self.assertRaises(ValueError):audit(src,p)
  with self.assertRaises(ValueError):audit({'slides':[]},p)
 def test_independent_geometry_cannot_be_reclassified_by_project(self):
  s=slide();original=copy.deepcopy(s);original['blocks'][0]=block('nav','01 / Раздел',400)
  with self.assertRaises(ValueError):audit({'source':{'canvas':C},'slides':[original]},{'slides':[s]})
if __name__=='__main__':unittest.main()
