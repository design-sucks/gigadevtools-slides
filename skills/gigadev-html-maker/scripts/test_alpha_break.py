"""Real AlphaBreak fixture and synthetic paragraph/visibility regression.

Usage: python3 test_alpha_break.py ORIGINAL.pptx ALPHABREAK_REPRO NEW_OUTPUT_DIR
Requires local Playwright/Chrome and HTML_MAKER_NODE_MODULES, as for source DOM QA.
"""
import copy, hashlib, json, os, subprocess, sys
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

source,repro,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=False)
here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2));return p
protected=[source,repro/'repro.html',repro/'project.json',repro/'source-subset.json',repro/'source-alpha.json'];before=[sha(p) for p in protected]
manifest=repro/'source-alpha.json';inventory=repro/'source-subset.json';project=repro/'project.json';original=(repro/'repro.html').read_text()
results=[]
def run(name,html,inv=inventory,proj=project,pptx=source,review=manifest,expected='fail',code=None,count=None):
    path=out/(name+'.html');path.write_text(html)
    cmd=['node',str(here/'check_source_dom.mjs'),str(path),str(inv),str(proj),'--source',str(pptx),'--source-alpha',str(review)]
    r=subprocess.run(cmd,capture_output=True,text=True,env=os.environ,timeout=90);(out/(name+'.json')).write_text(r.stdout or r.stderr)
    try:d=json.loads(r.stdout)
    except Exception:raise AssertionError((name,r.returncode,r.stderr[:2000]))
    assert d['status']==expected,(name,d)
    if code:assert any(x.get('code')==code for x in d.get('issues',[])),(name,d)
    if count is not None:assert sum(x.get('code')=='source-alpha-reviewed' for x in d.get('observations',[]))==count,(name,d)
    results.append({'case':name,'status':d['status'],'issues':[x['code'] for x in d['issues']],'reviews':sum(x.get('code')=='source-alpha-reviewed' for x in d.get('observations',[]))});return d

def one(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
run('real-all-runs-br',original,expected='review',count=10)
run('real-nonblank-br',(repro/'repro-nonblank-br.html').read_text(),proj=repro/'project-nonblank-br.json',review=repro/'source-alpha-nonblank.json',expected='review',count=6)
run('real-all-runs-newline',(repro/'repro-literal-newline.html').read_text(),proj=repro/'project-literal-newline.json',expected='review',count=10)
nonblank=(repro/'repro-nonblank-br.html').read_text()
space='<span style="color:rgba(117,126,152,0.000);"> </span>'
assert space in nonblank
run('hidden-unmarked-whitespace',nonblank.replace(space,'<span style="display:none;color:rgba(117,126,152,0.000);"> </span>',1),proj=repro/'project-nonblank-br.json',review=repro/'source-alpha-nonblank.json',code='source-alpha-unverified')
run('missingword',one(original,'>контрагенты</span>','></span>'),code='source-alpha-unverified')
run('missingspace',one(original,'> </span><br>','></span><br>'),code='source-alpha-unverified')
run('missingbr',one(original,'</span><br><span data-source-alpha-run="0:6"','</span><span data-source-alpha-run="0:6"'),code='source-alpha-unverified')
run('hiddenbr',one(original,'</span><br><span data-source-alpha-run="0:6"','</span><br style="display:none"><span data-source-alpha-run="0:6"'),code='source-alpha-unverified')
run('unrendered-newline',one(original,'</span><br><span data-source-alpha-run="0:6"','</span>\n<span data-source-alpha-run="0:6"'),code='source-alpha-unverified')
run('duplicate-marker',one(original,'data-source-alpha-run="0:1"','data-source-alpha-run="0:0"'),code='source-alpha-unverified')
s=one(original,'data-source-alpha-run="0:0"','data-source-alpha-run="TEMP"');s=one(s,'data-source-alpha-run="0:1"','data-source-alpha-run="0:0"');s=one(s,'data-source-alpha-run="TEMP"','data-source-alpha-run="0:1"')
run('moved-marker',s,code='source-alpha-unverified')
run('hidden-whitespace-marker',one(original,'data-source-alpha-run="0:2" style="color:rgba(117,126,152,0.000);"','data-source-alpha-run="0:2" style="display:none;color:rgba(117,126,152,0.000);"'),code='source-alpha-unverified')

# Build a minimal XML-only synthetic PPTX based on the real slide 14. Add a
# second visible paragraph; it exercises cross-paragraph mapping and A01.
P='http://schemas.openxmlformats.org/presentationml/2006/main';A='http://schemas.openxmlformats.org/drawingml/2006/main';ns={'p':P,'a':A};ppt=out/'synthetic-two-paragraph.pptx'
with ZipFile(source) as src,ZipFile(ppt,'w',ZIP_DEFLATED) as dst:
    for name in src.namelist():
        if not (name.endswith('.xml') or name.endswith('.rels')):continue
        data=src.read(name)
        if name=='ppt/slides/slide14.xml':
            root=ET.fromstring(data);shape=next(x for x in root.findall('.//p:sp',ns) if x.find('p:nvSpPr/p:cNvPr',ns) is not None and x.find('p:nvSpPr/p:cNvPr',ns).get('id')=='56')
            body=shape.find('p:txBody',ns);p=body.find('a:p',ns);second=copy.deepcopy(p)
            for c in list(second):
                if c.tag in (f'{{{A}}}r',f'{{{A}}}fld',f'{{{A}}}br'):second.remove(c)
            end=second.find('a:endParaRPr',ns);run_node=ET.Element(f'{{{A}}}r');ET.SubElement(run_node,f'{{{A}}}rPr');ET.SubElement(run_node,f'{{{A}}}t').text='VISIBLE'
            second.insert(list(second).index(end) if end is not None else len(second),run_node)
            hidden=copy.deepcopy(p.find('a:r',ns));hidden.find('a:t',ns).text='HIDDEN';second.insert(list(second).index(end) if end is not None else len(second),hidden)
            body.append(second);data=ET.tostring(root,encoding='utf-8',xml_declaration=True)
        dst.writestr(name,data)
i=read(inventory);p=read(project);m=read(manifest);digest=sha(ppt)
for d in (i,p):
    d['source']['sha256']=digest; para=d['slides'][0]['blocks'][0]['paragraphs'][0];other=copy.deepcopy(para);other['text']='VISIBLEHIDDEN';other['runs']=[{'text':'VISIBLE'},{'text':'HIDDEN'}];d['slides'][0]['blocks'][0]['paragraphs'].append(other)
p['slides'][0]['html']=p['slides'][0]['html'].replace('</p></div>','</p><p>VISIBLE<span data-source-alpha-run="1:1" style="color:rgba(117,126,152,0)">HIDDEN</span></p></div>')
m['sourceSha256']=digest
extra=copy.deepcopy(m['dispositions'][0]);extra.update(paragraphIndex=1,runIndex=1,sourceText='HIDDEN');m['dispositions'].append(extra)
ip=write(out/'synthetic-inventory.json',i);pp=write(out/'synthetic-project.json',p);mp=write(out/'synthetic-review.json',m);deck=out/'synthetic-deck.html'
r=subprocess.run(['python3',str(here/'build.py'),str(pp),str(deck)],capture_output=True,text=True,timeout=90);assert r.returncode==0,r.stderr
s=deck.read_text();assert '>VISIBLE<span data-source-alpha-run="1:1"' in s
run('paragraphboundary-positive',s,ip,pp,ppt,mp,expected='review',count=11)
run('paragraphboundary-merged',one(s,'</p><p>VISIBLE<span data-source-alpha-run="1:1"','<br>VISIBLE<span data-source-alpha-run="1:1"'),ip,pp,ppt,mp,code='source-alpha-unverified')
run('hiddenvisiblesibling',one(s,'>VISIBLE<span data-source-alpha-run="1:1"','><span style="opacity:0">VISIBLE</span><span data-source-alpha-run="1:1"'),ip,pp,ppt,mp,code='source-text-invisible')
assert [sha(p) for p in protected]==before,'original input changed'
write(out/'summary.json',{'status':'pass','sourceSha256':sha(source),'results':results,'limitations':['Synthetic two-paragraph PPTX is not a source render proof.','Unchanged style/border restrictions and other unsupported cases remain unresolved.']})
print(json.dumps({'status':'pass','cases':len(results)}))
