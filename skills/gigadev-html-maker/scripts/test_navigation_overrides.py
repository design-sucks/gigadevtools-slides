import copy,unittest
from navigation import resolve
class NavigationOverrides(unittest.TestCase):
 def slide(self):return {'id':'s1','title':'Actual heading','label':'Short','section':'Section','topic':'Topic','html':'<h1>Actual heading</h1>'}
 def test_defaults_unchanged(self):
  r=resolve([self.slide()])['s1'];self.assertEqual((r['label'],r['section'],r['topic']),('Short','Section','Topic'));self.assertEqual(r['overrides'],{})
 def test_all_fields_and_base_preserved(self):
  s=self.slide();s.update(navigationLabelOverride='New name',showNavigationOverride={'section':'New section','topic':'New topic'});before=copy.deepcopy(s);r=resolve([s])['s1'];self.assertEqual((r['label'],r['section'],r['topic']),('New name','New section','New topic'));self.assertEqual((r['baseLabel'],r['baseSection'],r['baseTopic']),('Short','Section','Topic'));self.assertEqual(s,before)
 def test_manual_duplicate_and_empty_are_intentional(self):
  s=self.slide();s['showNavigationOverride']={'section':'','topic':'Actual heading'};r=resolve([s])['s1'];self.assertEqual(r['section'],'');self.assertEqual(r['topic'],'Actual heading')
 def test_invalid_label(self):
  for value in ['', '  ',None,12, 'x'*121, '😀'*61, 'a\x00b']:
   s=self.slide();s['navigationLabelOverride']=value
   with self.assertRaises(ValueError,msg=repr(value)):resolve([s])
 def test_invalid_header(self):
  for value in [None,{}, {'topic':'x'},{'section':'a','topic':'b','extra':'c'},{'section':1,'topic':'b'},{'section':'x'*161,'topic':''}]:
   s=self.slide();s['showNavigationOverride']=value
   with self.assertRaises(ValueError,msg=repr(value)):resolve([s])
 def test_normalizes_whitespace(self):
  s=self.slide();s.update(navigationLabelOverride=' A\n B ',showNavigationOverride={'section':' S ','topic':' T\t U '});r=resolve([s])['s1'];self.assertEqual(r['overrides'],{'navigationLabelOverride':'A B','showNavigationOverride':{'section':'S','topic':'T U'}})
 def test_no_section_propagation_from_override(self):
  a=self.slide();a['navigationRole']='divider';a['showNavigationOverride']={'section':'Manual','topic':'Local'};b={'id':'s2','title':'Other'};r=resolve([a,b]);self.assertEqual(r['s1']['section'],'Manual');self.assertNotEqual(r['s2']['section'],'Manual')
if __name__=='__main__':unittest.main()
