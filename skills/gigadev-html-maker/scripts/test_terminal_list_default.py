"""Bounded terminal-list inference and negative inheritance controls."""
import unittest
from xml.etree import ElementTree as E
from pptx_text_styles import A,P,N,styles,list_chain,infer_plain_text_default,resolve_list,build_context

def parse(s):return E.fromstring(f'<root xmlns:a="{A}" xmlns:p="{P}">{s}</root>')[0]
class TerminalDefaultTests(unittest.TestCase):
 def setUp(self):
  self.ctx={'layout':parse('<p:sldLayout/>'),'master':parse('<p:sldMaster/>'),'theme':parse('<a:theme/>'),'presentation':parse('<p:presentation/>'),'themeOverride':False}
  self.shape=parse('<p:sp><p:nvSpPr><p:nvPr/></p:nvSpPr><p:txBody><a:lstStyle/><a:p/></p:txBody></p:sp>')
 def resolve(self,level=0,shape=None):
  shape=shape if shape is not None else self.shape;p=shape.find('p:txBody/a:p/a:pPr',N)
  return resolve_list(list_chain(self.ctx,shape,styles(self.ctx,shape,p,level),level),level,infer_plain_text_default(self.ctx,shape,level))
 def test_terminal_default_and_provenance(self):
  self.assertEqual(self.resolve(),{'kind':'none','level':0,'source':'inferred.terminalDefault','status':'resolved','inferred':True})
 def test_direct_and_inherited_bullets_override_default(self):
  self.shape.find('p:txBody/a:lstStyle',N).append(parse('<a:lvl1pPr><a:buChar char="•"/></a:lvl1pPr>'))
  self.assertEqual((self.resolve()['kind'],self.resolve()['source']),('ul','slide.textBody'))
  self.shape.find('p:txBody/a:p',N).append(parse('<a:pPr><a:buNone/></a:pPr>'))
  self.assertEqual((self.resolve()['kind'],self.resolve()['source']),('none','slide.paragraph'))
 def test_default_bullets_and_precedence(self):
  self.ctx['presentation']=parse('<p:presentation><p:defaultTextStyle><a:defPPr><a:buChar char="•"/></a:defPPr></p:defaultTextStyle></p:presentation>')
  self.assertEqual((self.resolve()['kind'],self.resolve()['source']),('ul','presentation.defaultTextStyle.default'))
  self.shape.find('p:txBody/a:lstStyle',N).append(parse('<a:defPPr><a:buAutoNum type="arabicPeriod"/></a:defPPr>'))
  self.assertEqual((self.resolve()['kind'],self.resolve()['source']),('ol','slide.textBody.default'))
 def test_shape_default_precedes_more_distant_level(self):
  self.shape.find('p:txBody/a:lstStyle',N).append(parse('<a:defPPr><a:buNone/></a:defPPr>'))
  self.ctx['presentation']=parse('<p:presentation><p:defaultTextStyle><a:lvl1pPr><a:buChar char="•"/></a:lvl1pPr></p:defaultTextStyle></p:presentation>')
  self.assertEqual((self.resolve()['kind'],self.resolve()['source']),('none','slide.textBody.default'))
 def test_slide_override_relationship_is_guarded(self):
  from io import BytesIO
  from zipfile import ZipFile
  data=BytesIO()
  with ZipFile(data,'w') as z:
   for name,xml in [('layout','<p:sldLayout/>'),('master','<p:sldMaster/>'),('theme','<a:theme/>')]:z.writestr(name,E.tostring(parse(xml)))
  with ZipFile(data) as z:
   def rels(part):return {'m':{'type':'slideMaster','target':'master','external':False}} if part=='layout' else {'t':{'type':'theme','target':'theme','external':False}}
   slide={'l':{'type':'slideLayout','target':'layout','external':False},'override':{'type':'themeOverride','target':'ignored','external':False}}
   context=build_context(z,slide,rels,self.ctx['presentation'])
   self.assertTrue(context['themeOverride'])
   self.assertFalse(infer_plain_text_default(context,self.shape,0))
 def test_ambiguous_context_remains_unresolved(self):
  self.assertEqual(self.resolve(1)['status'],'unresolved')
  self.ctx['master']=None;self.assertEqual(self.resolve()['status'],'unresolved');self.ctx['master']=parse('<p:sldMaster/>')
  self.ctx['themeOverride']=True;self.assertEqual(self.resolve()['status'],'unresolved');self.ctx['themeOverride']=False
  self.ctx['theme']=parse('<a:theme><a:objectDefaults><a:spDef><a:lstStyle><a:defPPr><a:buChar char="•"/></a:defPPr></a:lstStyle></a:spDef></a:objectDefaults></a:theme>')
  self.assertEqual(self.resolve()['status'],'unresolved')
 def test_placeholder_and_table_remain_unresolved(self):
  ph=parse('<p:sp><p:nvSpPr><p:nvPr><p:ph idx="99" type="body"/></p:nvPr></p:nvSpPr><p:txBody><a:lstStyle/><a:p/></p:txBody></p:sp>')
  self.assertEqual(self.resolve(shape=ph)['status'],'unresolved')
  self.assertFalse(infer_plain_text_default(self.ctx,parse('<a:tc/>'),0))
if __name__=='__main__':unittest.main()
