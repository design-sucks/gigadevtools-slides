"""Conservative independent-source checks for reviewed off-canvas omissions."""
import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
P='http://schemas.openxmlformats.org/presentationml/2006/main'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL='http://schemas.openxmlformats.org/package/2006/relationships'

class DispositionTests(unittest.TestCase):
 def fixture(self,root,*,y=1200,rotation=None,grouped=False,missing_transform=False,anchor='t',duplicate=False):
  attrs={} if rotation is None else {'rot':str(rotation)}
  xfrm='' if missing_transform else '<a:xfrm'+(' rot="'+str(rotation)+'"' if rotation is not None else '')+'><a:off x="30" y="'+str(y)+'"/><a:ext cx="200" cy="100"/></a:xfrm>'
  shape=f'<p:sp><p:nvSpPr><p:cNvPr id="2" name="Text"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr>{xfrm}</p:spPr><p:txBody><a:bodyPr anchor="{anchor}"/><a:lstStyle/><a:p><a:r><a:t>Source text</a:t></a:r></a:p></p:txBody></p:sp>'
  if grouped:shape='<p:grpSp><p:nvGrpSpPr/><p:grpSpPr/>'+shape+'</p:grpSp>'
  if duplicate:shape=shape+'<p:grpSp><p:nvGrpSpPr/><p:grpSpPr/>'+shape+'</p:grpSp>'
  ppt=root/'source.pptx'
  parts={'ppt/presentation.xml':f'<p:presentation xmlns:p="{P}" xmlns:r="{R}"><p:sldIdLst><p:sldId id="256" r:id="r1"/></p:sldIdLst><p:sldSz cx="1000" cy="1000"/></p:presentation>',
         'ppt/_rels/presentation.xml.rels':f'<Relationships xmlns="{REL}"><Relationship Id="r1" Target="slides/slide1.xml" Type="{R}/slide"/></Relationships>',
         'ppt/slides/slide1.xml':f'<p:sld xmlns:p="{P}" xmlns:a="{A}"><p:cSld><p:spTree>{shape}</p:spTree></p:cSld></p:sld>'}
  with ZipFile(ppt,'w') as z:
   for name,value in parts.items():z.writestr(name,value)
  digest=hashlib.sha256(ppt.read_bytes()).hexdigest();render=root/'page.png';render.write_bytes(b'\x89PNG\r\n synthetic-proof')
  transform={'attributes':attrs,'children':[{'off':{'x':'30','y':str(y)}},{'ext':{'cx':'200','cy':'100'}}]}
  block={'id':'s1-o2','kind':'text','source':{'slide':1,'part':'ppt/slides/slide1.xml','objectId':'2'},'group':None,'transform':transform,'paragraphs':[{'text':'Source text'}]}
  src={'source':{'sha256':digest,'canvas':{'widthEMU':1000,'heightEMU':1000}},'slides':[{'id':'s1','sourceNumber':1,'blocks':[block]}]}
  dst=copy.deepcopy(src);dst['slides'][0]['html']='<p>Other content</p>'
  entry={'slide':1,'sourceId':'s1-o2','sourceText':'Source text','geometryEMU':{'x':30,'y':y,'width':200,'height':100},'canvasEMU':{'width':1000,'height':1000},'disposition':'omit','reviewed':True,'reason':'Inspected source proof','sourceRender':str(render),'sourceRenderSha256':hashlib.sha256(render.read_bytes()).hexdigest()}
  manifest={'sourceSha256':digest,'dispositions':[entry]}
  return src,dst,manifest,ppt
 def run_case(self,root,src,dst,manifest,ppt,*,with_source=True):
  for name,value in [('source.json',src),('project.json',dst),('manifest.json',manifest)]:
   (root/name).write_text(json.dumps(value,ensure_ascii=False))
  args=['python3',str(HERE/'check_source_inventory.py'),str(root/'source.json'),str(root/'project.json'),'--off-canvas',str(root/'manifest.json')]
  if with_source:args+=['--source',str(ppt)]
  result=subprocess.run(args,capture_output=True,text=True)
  return result, json.loads(result.stdout) if result.stdout else None
 def test_valid_review_and_independent_inventory_retained(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);src,dst,manifest,ppt=self.fixture(root);result,report=self.run_case(root,src,dst,manifest,ppt)
   self.assertEqual(result.returncode,0);self.assertEqual(report['status'],'review');self.assertTrue(report['sourceHashVerified']);self.assertEqual(report['issues'],[])
   obs=report['observations'][0];self.assertEqual(obs['sourceId'],'s1-o2');self.assertEqual(obs['geometryEMU']['y'],1200);self.assertEqual(obs['mapping'],{'disposition':'omit','targetId':None});self.assertEqual(len(src['slides'][0]['blocks']),1)
 def test_invalid_or_unproven_dispositions_never_waive_source(self):
  for case in ('no_source','manifest_hash','text','geometry','canvas','render_hash','unreviewed','wrong_disposition','project_missing','project_altered','project_hash','target_present','target_other_slide','unrelated_missing','partial','group','duplicate_source','rotation','bottom_anchor','unknown_geometry','independent_geometry_faked','independent_text_faked'):
   with self.subTest(case=case),tempfile.TemporaryDirectory() as d:
    root=Path(d);opts={'y':950} if case=='partial' else {'grouped':True} if case=='group' else {'duplicate':True} if case=='duplicate_source' else {'rotation':5400000} if case=='rotation' else {'anchor':'b'} if case=='bottom_anchor' else {'missing_transform':True} if case=='unknown_geometry' else {}
    src,dst,manifest,ppt=self.fixture(root,**opts);e=manifest['dispositions'][0];block=src['slides'][0]['blocks'][0];target=dst['slides'][0]
    if case=='manifest_hash':manifest['sourceSha256']='0'*64
    if case=='text':e['sourceText']='Different text'
    if case=='geometry':e['geometryEMU']['y']+=1
    if case=='canvas':e['canvasEMU']['height']+=1
    if case=='render_hash':e['sourceRenderSha256']='0'*64
    if case=='unreviewed':e['reviewed']=False
    if case=='wrong_disposition':e['disposition']='relocate'
    if case=='project_missing':target['blocks']=[]
    if case=='project_altered':target['blocks'][0]['paragraphs'][0]['text']='Changed'
    if case=='project_hash':dst['source']['sha256']='1'*64
    if case=='target_present':target['html']='<p data-source-id="s1-o2" style="transform:translateY(4000px)">Source text</p>'
    if case=='target_other_slide':dst['slides'].append({'id':'s2','sourceNumber':2,'blocks':[],'html':'<p data-source-id="s1-o2">Source text</p>'})
    if case=='unrelated_missing':src['slides'][0]['blocks'].append({'id':'s1-o3','kind':'text','paragraphs':[{'text':'Other'}]})
    if case=='independent_geometry_faked':
     # Pretend both inventory and project have a different off-canvas transform.
     block['transform']['children'][0]['off']['y']='1300';target['blocks'][0]=copy.deepcopy(block);e['geometryEMU']['y']=1300
    if case=='independent_text_faked':
     block['paragraphs'][0]['text']='Forged';target['blocks'][0]=copy.deepcopy(block);e['sourceText']='Forged'
    result,report=self.run_case(root,src,dst,manifest,ppt,with_source=case!='no_source')
    self.assertEqual(result.returncode,1,case+': '+result.stdout+result.stderr);self.assertEqual(report['status'],'fail')
    self.assertTrue(report['issues'],case)
    if case!='unrelated_missing':self.assertFalse(any(o['code']=='source-off-canvas-reviewed' for o in report['observations']),case)
 def test_inert_stream_scan_excludes_script_and_decodes_entities(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);html=root/'saved.html'
   # Put a large attribute across stream chunks; script/comment text is not DOM.
   html.write_text('<script>const x=\'<p data-source-id="s1-o2">\';</script><!-- <p data-source-id="s1-o2"> --><div title="'+('x'*300000)+'" data-source-id="s1-o&#50;"></div>')
   from source_dispositions import scan_saved_html
   self.assertEqual(scan_saved_html(html,{'s1-o2'}),[{'sourceId':'s1-o2','tag':'div'}])
 def test_unverified_source_viewing_remains_review(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);src,dst,manifest,ppt=self.fixture(root)
   for name,value in [('source.json',src),('project.json',dst),('manifest.json',manifest)]:
    (root/name).write_text(json.dumps(value))
   result=subprocess.run(['python3',str(HERE/'check_source_inventory.py'),str(root/'source.json'),str(root/'project.json'),'--mode','viewing','--off-canvas',str(root/'manifest.json')],capture_output=True,text=True)
   report=json.loads(result.stdout);self.assertEqual(report['status'],'review');self.assertFalse(report['sourceHashVerified'])
   self.assertTrue(any(x['code']=='off-canvas-disposition-unverified' for x in report['issues']))
   self.assertFalse(any(x['code']=='source-off-canvas-reviewed' for x in report['observations']))
 def test_incorrect_actual_source_hash_is_error(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);src,dst,manifest,ppt=self.fixture(root);ppt.write_bytes(ppt.read_bytes()+b'changed')
   result,report=self.run_case(root,src,dst,manifest,ppt)
   self.assertNotEqual(result.returncode,0);self.assertIsNone(report);self.assertIn('hash does not match',result.stderr)

if __name__=='__main__':unittest.main()
