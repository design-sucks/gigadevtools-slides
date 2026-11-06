"""Repeatable SourceAlpha regression using the real repro plus synthetic PPTX variants.

Usage: python3 test_source_alpha.py ORIGINAL.pptx REPRO_DIR EMPTY_OUTPUT_DIR
Requires local Playwright/Chrome, as do the Maker DOM checks.
"""
import copy, hashlib, json, os, subprocess, sys
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED
from source_alpha import verify
from source_dispositions import A, NS

source,repro,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=False)
here=Path(__file__).resolve().parent
inv=json.loads((repro/'source-subset.json').read_text());project=json.loads((repro/'project.json').read_text())
render=repro.parent.parent/'PPTXProof/page-02.png'
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
original_html=(repro/'repro.html').read_text(); old='<span style="color:rgba(255,255,255,0)">02</span>'
assert original_html.count(old)==1
mark='<span data-source-alpha-run="0:0" style="color:rgba(255,255,255,0)">02</span>'
base_entry={'slide':2,'sourceId':'s2-o64','sourcePart':'ppt/slides/slide2.xml','paragraphIndex':0,'runIndex':0,'sourceText':'02','disposition':'preserve-transparent','reviewed':True,'reason':'Review source frame and following stage','sourceRender':str(render),'sourceRenderSha256':sha(render)}
results=[]
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2));return path

def create(case,mutate=None,entry_mutate=None,html_mutate=None):
    folder=out/case;folder.mkdir(); i=copy.deepcopy(inv); p=copy.deepcopy(project); e=copy.deepcopy(base_entry)
    with ZipFile(source) as original, ZipFile(folder/'source.pptx','w',ZIP_DEFLATED) as z:
        for name in ['ppt/presentation.xml','ppt/_rels/presentation.xml.rels','ppt/slides/slide2.xml','ppt/slides/_rels/slide2.xml.rels','ppt/slideLayouts/_rels/slideLayout6.xml.rels','ppt/slideMasters/slideMaster1.xml']:
            data=original.read(name)
            if name.endswith('slide2.xml'):
                root=ET.fromstring(data);shape=next(x for x in root.findall('.//p:sp',NS) if (x.find('p:nvSpPr/p:cNvPr',NS) is not None and x.find('p:nvSpPr/p:cNvPr',NS).get('id')=='64'))
                para=shape.find('p:txBody/a:p',NS);run=para.find('a:r',NS)
                # Real alpha=0 run plus a distinct, originally visible run.
                extra=ET.Element(f'{{{A}}}r');ET.SubElement(extra,f'{{{A}}}rPr');ET.SubElement(extra,f'{{{A}}}t').text='VISIBLE'
                para.insert(list(para).index(run)+1,extra)
                if mutate:mutate(root,shape,run,extra)
                data=ET.tostring(root,encoding='utf-8',xml_declaration=True)
            z.writestr(name,data)
    for o in (i,p):
        o['source']['sha256']=sha(folder/'source.pptx')
        para=o['slides'][0]['blocks'][0]['paragraphs'][0];para['text']='02VISIBLE';para['runs'].append({'text':'VISIBLE'})
    p['slides'][0]['html']=p['slides'][0]['html'].replace(old,mark+'<span>VISIBLE</span>')
    html=original_html.replace(old,mark+'<span>VISIBLE</span>')
    if html_mutate:html=html_mutate(html)
    if entry_mutate:entry_mutate(e)
    m={'sourceSha256':sha(folder/'source.pptx'),'dispositions':[e]}
    write(folder/'inventory.json',i);write(folder/'project.json',p);write(folder/'review.json',m);(folder/'deck.html').write_text(html)
    return folder,i,p

def verify_case(name,expect,**kwargs):
    folder,i,p=create(name,**kwargs)
    try:verify(folder/'source.pptx',i,p,folder/'review.json');actual=True
    except (ValueError,IndexError,KeyError) as err:actual=False;(folder/'rejection.txt').write_text(str(err))
    assert actual==expect,(name,actual);results.append({'case':name,'sourceVerifier':actual});return folder

positive=verify_case('mixed-positive',True)
verify_case('alpha-positive',False,mutate=lambda r,s,run,x:run.find('a:rPr/a:solidFill/*/a:alpha',NS).set('val','1'))
verify_case('alpha-inherited-unknown',False,mutate=lambda r,s,run,x:run.find('a:rPr',NS).remove(run.find('a:rPr/a:solidFill',NS)))
verify_case('original-visible-run',False,entry_mutate=lambda e:e.update(runIndex=1,sourceText='VISIBLE'))
verify_case('wrong-text',False,entry_mutate=lambda e:e.update(sourceText='03'))
verify_case('wrong-index',False,entry_mutate=lambda e:e.update(runIndex=7))
verify_case('neighbor-slide',False,entry_mutate=lambda e:e.update(slide=3,sourceId='s3-o64',sourcePart='ppt/slides/slide3.xml'))
verify_case('timing-unresolved',False,mutate=lambda r,s,run,x:ET.SubElement(r,'{http://schemas.openxmlformats.org/presentationml/2006/main}timing'))
verify_case('transition-unresolved',False,mutate=lambda r,s,run,x:ET.SubElement(r,'{http://schemas.openxmlformats.org/presentationml/2006/main}transition'))
verify_case('shape-effect-unresolved',False,mutate=lambda r,s,run,x:ET.SubElement(s.find('p:spPr',NS),f'{{{A}}}effectLst'))
verify_case('forged-render',False,entry_mutate=lambda e:e.update(sourceRenderSha256='0'*64))

def browser(name,folder,expected,issue=None,aggregate=False):
    args=['--source',str(folder/'source.pptx'),'--source-alpha',str(folder/'review.json')]
    if aggregate:args=['node',str(here/'check_acceptance.mjs'),str(folder/'deck.html'),str(folder/'inventory.json'),str(folder/'project.json'),str(folder/'qa'),*args]
    else:args=['node',str(here/'check_source_dom.mjs'),str(folder/'deck.html'),str(folder/'inventory.json'),str(folder/'project.json'),*args]
    r=subprocess.run(args,capture_output=True,text=True,env=os.environ,timeout=90)
    (folder/(name+'.json')).write_text(r.stdout or r.stderr)
    try:data=json.loads(r.stdout)
    except Exception:raise AssertionError((name,r.returncode,r.stderr[:2000]))
    assert data['status']==expected,(name,data)
    if issue:assert any(x['code']==issue for x in data.get('issues',[])),(name,data)
    results.append({'case':name,'status':data['status']});return data
browser('mixed-visible-dom',positive,'review')
r=browser('mixed-aggregate',positive,'review',aggregate=True);assert r['rawDeliveryCheck']=='fail' and r['deliveryCheck']=='review' and len(r['reviewedDeliveryAdjustments'])==1
hidden=verify_case('visible-neighbor-hidden',True,html_mutate=lambda h:h.replace('<span>VISIBLE</span>','<span style="opacity:0">VISIBLE</span>'))
browser('visible-neighbor-hidden-dom',hidden,'fail','source-text-invisible')
r=browser('visible-neighbor-hidden-aggregate',hidden,'fail',aggregate=True);assert r['deliveryCheck']=='fail' and not r['reviewedDeliveryAdjustments']
wrong=verify_case('wrong-dom-marker',True,html_mutate=lambda h:h.replace('data-source-alpha-run="0:0"','data-source-alpha-run="0:1"'))
browser('wrong-dom-marker-check',wrong,'fail','source-alpha-unverified')
opacity=verify_case('output-only-opacity',True,html_mutate=lambda h:h.replace('color:rgba(255,255,255,0)','opacity:0'))
browser('output-only-opacity-check',opacity,'fail','source-alpha-unverified')
r=browser('positive-alpha-positive-dom',out/'alpha-positive','fail','source-alpha-unverified')
# Exact original source and original repro; retain complete source ID and text.
real=out/'real';real.mkdir();write(real/'inventory.json',inv);write(real/'project.json',project)
(real/'deck.html').write_text(original_html.replace(old,mark));write(real/'review.json',{'sourceSha256':sha(source),'dispositions':[base_entry]})
# Avoid copying the 97 MB original PPTX.
(real/'source.pptx').symlink_to(source)
r=browser('real-source-dom',real,'review');assert r['sourceHashVerified'] and r['observations'][0]['sourceText']=='02'
r=browser('real-source-aggregate',real,'review',aggregate=True);assert r['rawDeliveryCheck']=='fail' and r['deliveryCheck']=='review'
# Real neighboring slide 3 has the same text and object number, but no explicit zero alpha.
full=json.loads((repro.parent.parent/'Extract/deck.json').read_text())
s3=next(s for s in full['slides'] if s.get('sourceNumber')==3)
b3=next(b for b in s3['blocks'] if b.get('id')=='s3-o64')
i3={'source':inv['source'],'slides':[{'id':s3['id'],'sourceNumber':3,'blocks':[b3]}]}
p3={'source':inv['source'],'slides':[{'id':s3['id'],'sourceNumber':3,'blocks':[b3]}]}
e3=dict(base_entry,slide=3,sourceId='s3-o64',sourcePart='ppt/slides/slide3.xml')
m3=write(out/'real-slide3-review.json',{'sourceSha256':sha(source),'dispositions':[e3]})
try:verify(source,i3,p3,m3);raise AssertionError('visible neighboring run accepted')
except ValueError as err:
    assert 'alpha' in str(err) or 'fill' in str(err),str(err)
    results.append({'case':'real-neighbor-slide3-visible','sourceVerifier':False,'reason':str(err)})
# Manifest hash must agree with both the original file and independent inventory.
bad=copy.deepcopy(inv);bad['source']['sha256']='0'*64
try:verify(source,bad,project,real/'review.json');raise AssertionError('source hash mismatch accepted')
except ValueError as err:results.append({'case':'real-source-hash-mismatch','sourceVerifier':False,'reason':str(err)})
write(out/'summary.json',{'status':'pass','cases':results,'renderSha256':sha(render),'realSourceSha256':sha(source),'limitations':['Original shape effects, text and direct alpha are checked; inherited effects and visual provenance/reveal remain manual review.','Synthetic frame is a test fixture, not a rendered source proof.']})
print(json.dumps({'status':'pass','cases':len(results)}))
