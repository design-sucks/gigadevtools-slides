// Real DOM/capture regression: a paragraph gap must not become nominal leading.
import assert from 'node:assert/strict';
import path from 'node:path';
import {createRequire} from 'node:module';
import {installSemanticText} from './semantic-text.mjs';
const req=process.env.HTML_EXPORT_NODE_MODULES?createRequire(path.join(process.env.HTML_EXPORT_NODE_MODULES,'package.json')):createRequire(import.meta.url);
const {chromium}=req('playwright');
const browser=await chromium.launch({headless:true,...(process.env.HTML_EXPORT_CHROME==='bundled'?{}:{channel:'chrome'})});
try {
 const page=await browser.newPage();
 await page.setContent('<style>body{margin:0}.slide{position:relative}p{font:20px/24px Arial;margin:0 0 50px;width:180px}</style><div class="slide"><p id="first">Alpha<br><br>Beta<br>Gamma</p><p id="later">Alpha<br>Beta<br><br>Gamma</p><p id="wrap">Several words wrap across multiple ordinary lines inside this narrow frame.</p><p id="overlap">Alpha<br>Beta<br><span style="position:relative;top:-8px">Gamma</span></p></div>');
 await page.evaluate(installSemanticText);
 const results=await page.evaluate(()=>Object.fromEntries(['first','later','wrap','overlap'].map(id=>{try{return [id,{value:window.SberSemanticText.forNode(document.getElementById(id).firstChild)}]}catch(e){return [id,{error:e.message}]}})));
 for(const id of ['first','later','wrap']){assert(!results[id].error,JSON.stringify(results[id]));assert.equal(results[id].value.lineHeight,24);}
 assert.equal(results.first.value.runs.filter(r=>r.newParagraphBefore).length,1);
 assert.equal(results.later.value.runs.filter(r=>r.newParagraphBefore).length,1);
 assert.equal(results.wrap.value.runs.filter(r=>r.newParagraphBefore).length,0);
 assert(results.wrap.value.lineCount>1);
 assert.match(results.overlap.error,/compressed CSS line gap/);
 console.log(JSON.stringify({status:'pass',cases:Object.keys(results),actualCapture:true}));
} finally {await browser.close();}
