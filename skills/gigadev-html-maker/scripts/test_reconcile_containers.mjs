/* Independent A08: actual editor -> saved work -> project -> rebuild, plus conflict cases. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';

const here=path.dirname(fileURLToPath(import.meta.url));
const output=process.argv[2]&&path.resolve(process.argv[2]);
if(!output)throw Error('Usage: node test_reconcile_containers.mjs NEW_EMPTY_OUTPUT_DIRECTORY');
await fs.mkdir(output,{recursive:true});if((await fs.readdir(output)).length)throw Error('Output directory must be empty');
const modules=process.env.HTML_MAKER_NODE_MODULES;const require=modules?createRequire(path.join(modules,'package.json')):createRequire(import.meta.url);const {chromium}=require('playwright');
const run=(cmd,args)=>spawnSync(cmd,args,{encoding:'utf8',env:process.env,maxBuffer:64*1024*1024,timeout:60000});
const browser=await chromium.launch({headless:true,...(process.env.HTML_MAKER_CHROME==='bundled'?{}:{channel:'chrome'})});
async function freshPage(){const context=await browser.newContext({viewport:{width:1280,height:800},serviceWorkers:'block'});await context.route(/^https?:/,r=>r.abort());return {context,page:await context.newPage()};}
const results=[];
const reconcilePath=path.join(here,'reconcile_edits.mjs');
function digest(v){return createHash('sha256').update(v).digest('hex');}
const initialReconcileHash=digest(await fs.readFile(reconcilePath));
async function content(file,selector){const {context,page:p}=await freshPage();try{await p.goto(pathToFileURL(file).href);await p.waitForFunction(()=>window.SalesKitUI);return await p.locator(selector).evaluate(node=>{const copy=node.cloneNode(true);for(const n of [copy,...copy.querySelectorAll('*')])for(const name of ['data-eid','contenteditable','data-sk-editing','spellcheck'])n.removeAttribute(name);return copy.outerHTML});}finally{await context.close();}}
async function workFromUser(file,selector,out){
 const {context,page}=await freshPage();try{await page.goto(pathToFileURL(file).href);await page.waitForFunction(()=>window.SalesKitUI);await page.evaluate(()=>{goTo(0);SalesKitMotion.finish()});await page.locator('#editBtn').click();const node=page.locator(selector);const before=await node.textContent();await node.click();await node.evaluate(el=>{const r=document.createRange();r.selectNodeContents(el);r.collapse(false);const s=getSelection();s.removeAllRanges();s.addRange(r)});await page.keyboard.insertText(' — проверка');await page.locator('#sk-text-done').click();const after=await node.textContent();assert.equal(after,before+' — проверка');await fs.writeFile(out,await page.evaluate(()=>SalesKitUI.exportDocument('work')));return {before,after};}finally{await context.close();}
}
async function modifiedWork(base,selector,alter,out){const {context,page}=await freshPage();try{await page.goto(pathToFileURL(base).href);await page.waitForFunction(()=>window.SalesKitUI);await page.locator(selector).evaluate((n,what)=>{if(what==='geometry')n.innerHTML='<span style="font-size:4px;position:absolute;left:-2000px">'+n.innerHTML+'</span>';if(what==='extra-li')n.insertAdjacentHTML('beforeend','<li>injected</li>');if(what==='colspan')n.querySelector('td').setAttribute('colspan','2');if(what==='safe-inline')n.innerHTML=n.innerHTML.replace('<strong>cell</strong>','<em><strong>cell</strong></em>');if(what==='fragment-geometry'){const generated=n.querySelector('span.sk-edit-fragment');if(!generated)throw Error('Missing editor-generated span');generated.setAttribute('style','position:absolute;left:-2000px;font-size:4px');}},alter);await fs.writeFile(out,await page.evaluate(()=>SalesKitUI.exportDocument('work')));}finally{await context.close();}}
function merge(base,work,project,out){const r=run(process.execPath,[path.join(here,'reconcile_edits.mjs'),base,work,project,out]);let report;try{report=JSON.parse(r.stdout)}catch{report={stdout:r.stdout,stderr:r.stderr}}return {exit:r.status,report};}
async function exists(file){return fs.access(file).then(()=>true,()=>false)}
const cases=[
 {name:'ul',html:'<ul data-source-id="target" class="bullets" aria-label="List"><li>Alpha <strong>strong</strong> <a href="https://example.com">link</a></li><li>Beta</li></ul>',edit:'[data-source-id="target"] > li:first-child',check:['<strong>strong</strong>','href="https://example.com"','<li>Beta</li>'],text:'Alpha'},
 {name:'ol',html:'<ol data-source-id="target" type="a" start="3"><li>One</li><li>Two</li></ol>',edit:'[data-source-id="target"] > li:last-child',check:['type="a"','start="3"','<li>One</li>'],text:'Two'},
 {name:'nested',html:'<ul data-source-id="target" class="outer"><li>Parent<ol type="I" start="2"><li>Child</li><li>Next</li></ol></li><li>Sibling</li></ul>',edit:'[data-source-id="target"] ol > li:first-child',check:['type="I"','start="2"','<li>Next</li>','<li>Sibling</li>'],text:'Child'},
 {name:'table',html:'<table data-source-id="target"><tbody><tr><th>Title</th><th>Value</th></tr><tr><td><em>First</em> cell</td><td>Seven</td></tr></tbody></table>',edit:'[data-source-id="target"] td:first-child',check:['<em>First</em>','<th>Value</th>','<td>Seven</td>'],text:'First'},
 {name:'cell',html:'<table><tbody><tr><td data-source-id="target">Editable <strong>cell</strong></td><td>Untouched</td></tr></tbody></table>',edit:'[data-source-id="target"]',check:['<strong>cell'],text:'Editable'},
 {name:'caption',html:'<figure><figcaption data-source-id="target">Image <em>caption</em></figcaption></figure>',edit:'[data-source-id="target"]',check:['<em>caption'],text:'Image'},
];
async function synthetic(c){
 const dir=path.join(output,c.name);await fs.mkdir(dir);const f=x=>path.join(dir,x);
 const project={schema:1,title:'A08 test',version:1,slides:[{id:'s1',html:c.html}]};await fs.writeFile(f('project.json'),JSON.stringify(project,null,2));
 let r=run('python3',[path.join(here,'build.py'),f('project.json'),f('base.html')]);assert.equal(r.status,0,r.stderr);
 const user=await workFromUser(f('base.html'),c.edit,f('work.html'));const baselineTarget=await content(f('base.html'),'[data-source-id="target"]');const savedTarget=await content(f('work.html'),'[data-source-id="target"]');assert.notEqual(baselineTarget,savedTarget,'saved UI change must not leak into fresh baseline');
 let m=merge(f('base.html'),f('work.html'),f('project.json'),f('merged.json'));await fs.writeFile(f('merge-report.json'),JSON.stringify(m,null,2));assert.equal(m.exit,0,JSON.stringify(m));assert.equal(m.report.status,'merged');
 r=run('python3',[path.join(here,'build.py'),f('merged.json'),f('rebuilt.html')]);assert.equal(r.status,0,r.stderr);
 const rebuilt=await content(f('rebuilt.html'),'[data-source-id="target"]');assert.equal(rebuilt,savedTarget,'rebuilt content must preserve saved structure and attributes');assert(rebuilt.includes(' — проверка'),rebuilt);for(const token of c.check)assert(rebuilt.includes(token),`${c.name}: missing ${token}: ${rebuilt}`);
 const {context:verifyContext,page:p}=await freshPage();try{await p.goto(pathToFileURL(f('rebuilt.html')).href);await p.waitForFunction(()=>window.SalesKitUI);assert.equal(await p.locator(c.edit).textContent(),user.after);}finally{await verifyContext.close();}
 m=merge(f('base.html'),f('work.html'),f('merged.json'),f('merged-again.json'));await fs.writeFile(f('repeat-report.json'),JSON.stringify(m,null,2));assert.equal(m.exit,0,JSON.stringify(m));assert.deepEqual(JSON.parse(await fs.readFile(f('merged-again.json'))),JSON.parse(await fs.readFile(f('merged.json'))),'repeated merge must be idempotent');
 const concurrent=structuredClone(project);concurrent.slides[0].html=concurrent.slides[0].html.replace(c.text,c.text+' CONCURRENT');assert.notEqual(concurrent.slides[0].html,project.slides[0].html);await fs.writeFile(f('concurrent.json'),JSON.stringify(concurrent));const hash=digest(await fs.readFile(f('concurrent.json')));
 m=merge(f('base.html'),f('work.html'),f('concurrent.json'),f('must-not-exist.json'));await fs.writeFile(f('conflict-report.json'),JSON.stringify(m,null,2));assert.notEqual(m.exit,0,'concurrent change accepted');assert.equal(m.report.status,'conflict');assert.equal(await exists(f('must-not-exist.json')),false);assert.equal(digest(await fs.readFile(f('concurrent.json'))),hash);
 if(c.name==='ul'||c.name==='table'){
  const attack=c.name==='ul'?'extra-li':'colspan';await modifiedWork(f('base.html'),'[data-source-id="target"]',attack,f('structural-attack.html'));m=merge(f('base.html'),f('structural-attack.html'),f('project.json'),f('bad-structure.json'));await fs.writeFile(f('structure-report.json'),JSON.stringify(m,null,2));assert.notEqual(m.exit,0,'structural mutation accepted');assert.equal(m.report.status,'conflict');assert.equal(await exists(f('bad-structure.json')),false);
 }
 if(c.name==='nested'){
  await modifiedWork(f('base.html'),'[data-source-id="target"]','fragment-geometry',f('fragment-attack.html'));m=merge(f('base.html'),f('fragment-attack.html'),f('project.json'),f('bad-fragment.json'));await fs.writeFile(f('fragment-attack-report.json'),JSON.stringify(m,null,2));assert.notEqual(m.exit,0,'editor fragment geometry attack accepted');assert.equal(m.report.status,'conflict');assert.equal(await exists(f('bad-fragment.json')),false);
 }
 if(c.name==='cell'){
  await modifiedWork(f('base.html'),'[data-source-id="target"]','safe-inline',f('inline-work.html'));m=merge(f('base.html'),f('inline-work.html'),f('project.json'),f('inline-merged.json'));await fs.writeFile(f('inline-report.json'),JSON.stringify(m,null,2));assert.equal(m.exit,0,'safe inline formatting should merge: '+JSON.stringify(m));r=run('python3',[path.join(here,'build.py'),f('inline-merged.json'),f('inline-rebuilt.html')]);assert.equal(r.status,0,r.stderr);assert.equal(await content(f('inline-rebuilt.html'),'[data-source-id="target"]'),await content(f('inline-work.html'),'[data-source-id="target"]'));
  await modifiedWork(f('base.html'),'[data-source-id="target"]','geometry',f('geometry-attack.html'));m=merge(f('base.html'),f('geometry-attack.html'),f('project.json'),f('bad-geometry.json'));await fs.writeFile(f('geometry-report.json'),JSON.stringify(m,null,2));assert.notEqual(m.exit,0,'geometry attack accepted');assert.equal(m.report.status,'conflict');assert.equal(await exists(f('bad-geometry.json')),false);
 }
 await fs.writeFile(f('proof.json'),JSON.stringify({baselineTarget,savedTarget,rebuiltTarget:rebuilt,user},null,2));return {case:c.name,status:'pass'};
}
try{
 for(const c of cases){
  try{const result=await synthetic(c);results.push(result);console.log(result.case+' PASS');}
  catch(e){results.push({case:c.name,status:'fail',error:String(e.stack||e)});console.log(c.name+' FAIL: '+String(e.message||e).slice(0,400));}
 }
 const finalReconcileHash=digest(await fs.readFile(reconcilePath));if(initialReconcileHash!==finalReconcileHash)results.push({case:'implementation_stability',status:'fail',error:'reconcile_edits.mjs changed during the run; repeat against one fixed revision',initialReconcileHash,finalReconcileHash});
 await fs.writeFile(path.join(output,'summary.json'),JSON.stringify({reconcileSha256:initialReconcileHash,results},null,2));if(results.some(r=>r.status!=='pass'))process.exitCode=1;
}finally{await browser.close();}
