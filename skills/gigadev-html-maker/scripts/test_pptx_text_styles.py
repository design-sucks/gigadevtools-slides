"""Exercise inheritance, list semantics and reversible draft structure on a tiny PPTX."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from extract_pptx import extract
from build import build
from check_source_inventory import Targets, list_type

P='http://schemas.openxmlformats.org/presentationml/2006/main'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL='http://schemas.openxmlformats.org/package/2006/relationships'

def relationships(items):
 return '<Relationships xmlns="'+REL+'">'+''.join(f'<Relationship Id="{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/{typ}" Target="{target}"'+(' TargetMode="External"' if target.startswith('https:') else '')+'/>' for i,typ,target in items)+'</Relationships>'

def fixture(path):
 pres=f'<p:presentation xmlns:p="{P}" xmlns:a="{A}" xmlns:r="{R}"><p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst><p:sldSz cx="12192000" cy="6858000"/><p:defaultTextStyle><a:lvl1pPr><a:defRPr sz="1800"/></a:lvl1pPr></p:defaultTextStyle></p:presentation>'
 run=lambda text,pr='':f'<a:r>{pr}<a:t>{text}</a:t></a:r>'
 slide=f'''<p:sld xmlns:p="{P}" xmlns:a="{A}" xmlns:r="{R}"><p:cSld><p:spTree><p:sp><p:nvSpPr><p:cNvPr id="2" name="body"/><p:cNvSpPr/><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:txBody><a:bodyPr/><a:lstStyle/><a:p>{run('First ', '<a:rPr b="1"/>')}{run('link', '<a:rPr><a:hlinkClick r:id="link"/></a:rPr>')}</a:p><a:p><a:pPr lvl="1"/>{run('Nested numbered')}</a:p><a:p>{run('Second')}</a:p><a:p><a:pPr><a:buNone/></a:pPr>{run('Plain')}</a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>'''
 layout=f'''<p:sldLayout xmlns:p="{P}" xmlns:a="{A}"><p:cSld><p:spTree><p:sp><p:nvSpPr><p:cNvPr id="2"/><p:cNvSpPr/><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:txBody><a:bodyPr/><a:lstStyle><a:lvl1pPr><a:buChar char="•"/><a:defRPr sz="2400"><a:latin typeface="+mn-lt"/></a:defRPr></a:lvl1pPr></a:lstStyle><a:p/></p:txBody></p:sp></p:spTree></p:cSld></p:sldLayout>'''
 master=f'''<p:sldMaster xmlns:p="{P}" xmlns:a="{A}"><p:cSld><p:spTree/></p:cSld><p:txStyles><p:bodyStyle><a:lvl2pPr><a:buAutoNum type="alphaLcPeriod" startAt="3"/><a:defRPr sz="2000"><a:latin typeface="+mn-lt"/></a:defRPr></a:lvl2pPr></p:bodyStyle></p:txStyles></p:sldMaster>'''
 theme=f'<a:theme xmlns:a="{A}" name="test"><a:themeElements><a:fontScheme name="test"><a:majorFont><a:latin typeface="Test Display"/></a:majorFont><a:minorFont><a:latin typeface="Test Text"/></a:minorFont></a:fontScheme></a:themeElements></a:theme>'
 with ZipFile(path,'w') as z:
  for name,data in {'ppt/presentation.xml':pres,'ppt/_rels/presentation.xml.rels':relationships([('rId1','slide','slides/slide1.xml')]),
   'ppt/slides/slide1.xml':slide,'ppt/slides/_rels/slide1.xml.rels':relationships([('layout','slideLayout','../slideLayouts/slideLayout1.xml'),('link','hyperlink','https://example.com')]),
   'ppt/slideLayouts/slideLayout1.xml':layout,'ppt/slideLayouts/_rels/slideLayout1.xml.rels':relationships([('master','slideMaster','../slideMasters/slideMaster1.xml')]),
   'ppt/slideMasters/slideMaster1.xml':master,'ppt/slideMasters/_rels/slideMaster1.xml.rels':relationships([('theme','theme','../theme/theme1.xml')]),'ppt/theme/theme1.xml':theme}.items():z.writestr(name,data)

class InheritanceTests(unittest.TestCase):
 def test_empty_paragraph_boundaries_and_empty_geometry(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);src=root/'base.pptx';fixture(src);changed=root/'changed.pptx'
   with ZipFile(src) as zin,ZipFile(changed,'w') as zout:
    for name in zin.namelist():
     data=zin.read(name)
     if name=='ppt/slides/slide1.xml':
      data=data.replace(b'</p:txBody></p:sp></p:spTree>',b'<a:p/><a:p><a:endParaRPr/></a:p></p:txBody></p:sp><p:sp><p:nvSpPr><p:cNvPr id="3"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:txBody><a:bodyPr/><a:p/></p:txBody></p:sp></p:spTree>')
     zout.writestr(name,data)
   deck=extract(changed,root/'extracted');blocks=deck['slides'][0]['blocks'];body=next(x for x in blocks if x['id']=='s1-o2');empty=next(x for x in blocks if x['id']=='s1-o3')
   self.assertEqual([p['text'] for p in body['paragraphs']][-2:],['','']);self.assertEqual([p['runs'] for p in body['paragraphs']][-2:],[[],[]]);self.assertEqual(empty['kind'],'geometry')
 def test_inherited_lists_fonts_and_negative_structure(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'source.pptx';fixture(source);project=root/'project';deck=extract(source,project);block=deck['slides'][0]['blocks'][0];p=block['paragraphs']
   self.assertEqual([(x['effectiveList']['kind'],x['effectiveList']['source']) for x in p],[('ul','layout.placeholder'),('ol','master.bodyStyle'),('ul','layout.placeholder'),('none','slide.paragraph')])
   self.assertEqual(p[0]['runs'][0]['effectiveTypography']['properties']['latin']['family'],'Test Text')
   self.assertEqual(p[0]['runs'][0]['effectiveTypography']['properties']['sizePt']['value'],24)
   self.assertEqual(p[1]['runs'][0]['effectiveTypography']['properties']['sizePt']['value'],20)
   self.assertEqual(p[0]['runs'][1]['link'],'https://example.com')
   self.assertTrue(p[0]['runs'][0]['bold'])
   output=build(project/'deck.json',root/'draft.html')
   parser=Targets();parser.feed(output);units=parser.targets['s1-o2'][0]['units']
   self.assertEqual([(u['tag'],u['list'],u['level']) for u in units],[('li','ul',0),('li','ol',1),('li','ul',0),('p',None,-1)])
   self.assertIn('<ol type="a" start="3">',output);self.assertIn('<strong>First </strong>',output);self.assertIn('href="https://example.com"',output)
   bad={'slides':[{'sourceNumber':1,'blocks':block and [block], 'html':'<p data-source-id="s1-o2">First link Nested numbered Second Plain</p>'}]}
   (root/'bad.json').write_text(json.dumps(bad));check=Path(__file__).with_name('check_source_inventory.py')
   r=subprocess.run(['python3',str(check),str(project/'deck.json'),str(root/'bad.json')],capture_output=True,text=True)
   self.assertEqual(r.returncode,1);codes={i['code'] for i in json.loads(r.stdout)['issues']};self.assertIn('list-structure-mismatch',codes);self.assertIn('paragraph-count-mismatch',codes)

if __name__=='__main__':unittest.main()
