#!/usr/bin/env node
/** Narrow image background wash contract: reading, narrow, export, save/reopen. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require('playwright');

const here=path.dirname(fileURLToPath(import.meta.url));
const out=path.resolve(process.argv[2]||'/private/tmp/rc11-image-wash-check');
await fs.mkdir(path.join(out,'assets'),{recursive:true});
await fs.writeFile(path.join(out,'assets','background.png'),Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+XcHkAAAAASUVORK5CYII=','base64'));
const wash='radial-gradient(ellipse at 100% 100%,rgba(0,0,0,0) 0%,rgba(0,0,0,.96) 70%)';
const deck={schema:1,title:'Image wash QA',version:1,cssIsolation:'strict',order:['s1'],slides:[{id:'s1',label:'Image wash QA',sourceNumber:1,header:'none',background:{type:'image',asset:'assets/background.png',size:'cover',wash},html:'<p data-source-id="s1-o1">Editable text</p>',blocks:[]}]};
const run=(file,destination)=>spawnSync(process.env.PYTHON||'python3',[path.join(here,'build.py'),file,destination],{encoding:'utf8'});
const deckPath=path.join(out,'deck.json'),htmlPath=path.join(out,'built.html');
await fs.writeFile(deckPath,JSON.stringify(deck));
let result=run(deckPath,htmlPath);assert.equal(result.status,0,result.stderr);
for(const [name,invalid] of [['url','url(https://example.invalid/x)'],['non-image',wash]]){
 const bad=structuredClone(deck);if(name==='url')bad.slides[0].background.wash=invalid;else bad.slides[0].background={type:'color',value:'#000000',wash:invalid};
 const file=path.join(out,name+'.json');await fs.writeFile(file,JSON.stringify(bad));result=run(file,path.join(out,name+'.html'));assert.notEqual(result.status,0,`unsupported wash accepted: ${name}`);
}
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const observed=[];
async function open(file,viewport){const page=await browser.newPage({viewport,serviceWorkers:'block'});await page.route(/^https?:/,route=>route.abort());await page.goto(pathToFileURL(file).href);await page.waitForFunction(()=>window.SalesKitUI);return page;}
async function measure(page,label){const value=await page.evaluate(()=>{const e=document.querySelector('#slides>.slide[data-sk-id="s1"]>.slide-inner>.gd-slide-background');const r=e.getBoundingClientRect();const pseudo=getComputedStyle(e,'::before');return{x:r.x,y:r.y,width:r.width,height:r.height,content:pseudo.content,wash:pseudo.backgroundImage,duplicate:!!document.querySelector('.gd-content [style*="radial-gradient"]')}});assert.equal(value.content,'""');assert.match(value.wash,/radial-gradient/);assert.equal(value.duplicate,false);observed.push({label,...value});return value;}
try{
 const page=await open(htmlPath,{width:1280,height:800});let box=await measure(page,'reading');assert.equal(Math.round(box.width),1280);assert.equal(Math.round(box.height),800);
 await page.setViewportSize({width:390,height:844});await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));box=await measure(page,'narrow');assert.equal(Math.round(box.width),390);assert.equal(Math.round(box.height),844);
 const saved=path.join(out,'saved-work.html');await fs.writeFile(saved,await page.evaluate(()=>SalesKitUI.exportDocument('work',2)));await page.close();
 const reopened=await open(saved,{width:1280,height:800});box=await measure(reopened,'reopened');assert.equal(Math.round(box.width),1280);assert.equal(Math.round(box.height),800);
 await reopened.setViewportSize({width:1920,height:1080});await reopened.evaluate(async()=>GigaDevDeck.prepareExport());box=await measure(reopened,'export');assert.equal(Math.round(box.width),1920);assert.equal(Math.round(box.height),1080);await reopened.close();
}finally{await browser.close();}
await fs.writeFile(path.join(out,'result.json'),JSON.stringify({status:'pass',checks:['reading','narrow','export','save-reopen','reject-url','reject-non-image'],observed},null,2)+'\n');
console.log(JSON.stringify({status:'pass',out,checks:6}));
