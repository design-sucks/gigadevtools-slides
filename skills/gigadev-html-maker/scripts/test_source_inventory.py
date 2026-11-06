import json,subprocess,tempfile,pathlib
script=pathlib.Path(__file__).with_name('check_source_inventory.py').resolve()
source={'source':{'sha256':'abc'},'slides':[{'sourceNumber':1,'blocks':[{'id':'s1-o1','kind':'text','paragraphs':[{'text':'Проверка текста'}]}]}]}
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);(p/'source.json').write_text(json.dumps(source)); target={'slides':[{'sourceNumber':1,'blocks':[{'id':'s1-o1'}],'html':'<p data-source-id="s1-o1">Проверка текста</p>'}]};(p/'project.json').write_text(json.dumps(target))
 def run():return subprocess.run(['python3',str(script),str(p/'source.json'),str(p/'project.json')],capture_output=True,text=True)
 r=run();assert r.returncode==0 and json.loads(r.stdout)['status']=='pass'
 target['slides'][0]['html']='';target['slides'][0]['blocks']=[];(p/'project.json').write_text(json.dumps(target));r=run();assert r.returncode==1 and json.loads(r.stdout)['issues'][0]['code']=='missing-editable-target'
 source['slides'][0]['blocks'][0]['paragraphs']=[{'text':'Один','paragraphPropertiesXml':'<pPr><buChar char="•"/></pPr>'},{'text':'Два','paragraphPropertiesXml':'<pPr><buChar char="•"/></pPr>'}];(p/'source.json').write_text(json.dumps(source))
 target['slides'][0]['html']='<p data-source-id="s1-o1">Один<br>Два</p>';(p/'project.json').write_text(json.dumps(target));r=run();assert r.returncode==1 and any(x['code']=='list-structure-mismatch' for x in json.loads(r.stdout)['issues'])
 target['slides'][0]['html']='<div data-source-id="s1-o1"><ul><li>Один</li><li>Два</li></ul></div>';(p/'project.json').write_text(json.dumps(target));r=run();assert r.returncode==0, r.stdout
 print('positive, deleted-target and list structure cases passed')
