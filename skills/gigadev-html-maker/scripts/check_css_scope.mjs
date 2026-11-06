/* Diagnose authored theme CSS against the actual Maker shell. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
const [html,themeFile]=process.argv.slice(2);
if (!html || !themeFile || process.argv.length!==4) throw Error('Usage: node check_css_scope.mjs deck.html theme.json');
const here=path.dirname(fileURLToPath(import.meta.url));
let config={};try{config=JSON.parse(await fs.readFile(path.join(here,'../runtime.local.json'),'utf8'));}catch(e){if(e.code!=='ENOENT')throw e;}
const modules=process.env.HTML_MAKER_NODE_MODULES||config.nodeModules;
const require=modules?createRequire(path.join(modules,'package.json')):createRequire(import.meta.url);
const {chromium}=require('playwright');
const theme=JSON.parse(await fs.readFile(themeFile,'utf8'));
let css=theme.css || '';
if(theme.cssFile){const root=path.dirname(path.resolve(themeFile)),file=path.resolve(root,theme.cssFile);if(file!==root&&!file.startsWith(root+path.sep))throw Error('cssFile must stay inside theme directory');css+='\n'+await fs.readFile(file,'utf8');}
const browser=await chromium.launch({headless:true,...(process.env.HTML_MAKER_CHROME==='bundled'?{}:{channel:'chrome'})});
try {
 const page=await browser.newPage({serviceWorkers:'block'});await page.route(/^https?:/,route=>route.abort());
 await page.goto(pathToFileURL(path.resolve(html)).href);await page.waitForFunction(()=>window.GigaDevDeck);
 const findings=await page.evaluate(css=>{
  const rules=[];const issues=[];const observations=[];const sheet=new CSSStyleSheet();
  if(/@import\b/i.test(css))issues.push({code:'external-or-unresolved-import',message:'Review or embed imported styles before offline delivery.'});
  try {sheet.replaceSync(css);} catch(e){return {rules,issues:[{code:'css-parse-error',message:e.message}],observations};}
  const walk=list=>{for(const rule of list){
   if(rule instanceof CSSStyleRule){
    const selector=rule.selectorText;rules.push(selector);
    try {const outside=[...document.querySelectorAll(selector)].filter(n=>!n.closest('.gd-content')&&!n.closest('.gd-slide-background')).slice(0,8).map(n=>n.id?'#'+n.id:n.tagName.toLowerCase()+(n.className && typeof n.className==='string'?'.'+n.className.trim().split(/\s+/).join('.') : ''));
     if(outside.length)issues.push({code:'shell-selector-conflict',selector,matches:outside});
     if(!/(^|[\s>+~,(])\.gd-content(?:[\s.#:[>+~,) ]|$)/.test(selector))observations.push({code:'unproven-scope',selector});
    } catch(e){observations.push({code:'selector-review',selector,message:e.message});}
   } else if (rule instanceof CSSKeyframesRule) {observations.push({code:'global-keyframes',name:rule.name});}
   else if(rule instanceof CSSFontFaceRule) {observations.push({code:'global-font-face',family:rule.style.fontFamily});}
   else if(rule.cssRules)walk(rule.cssRules);
   else observations.push({code:'unsupported-rule-review',rule:rule.cssText.slice(0,200)});
  }};walk(sheet.cssRules);return {rules,issues,observations};
 },css);
 console.log(JSON.stringify({status:findings.issues.length?'fail':findings.observations.length?'review':'pass',htmlSha256:createHash('sha256').update(await fs.readFile(html)).digest('hex'),themeSha256:createHash('sha256').update(await fs.readFile(themeFile)).digest('hex'),cssSha256:createHash('sha256').update(css).digest('hex'),...findings,limitations:['Legacy css and cssFile are checked against the current DOM and state only; hidden or future shell elements and dynamic pseudo-classes require review.','This is diagnosis, not automatic selector rewriting or CSS isolation.']},null,2));
 process.exitCode=findings.issues.length?1:0;
} finally {await browser.close();}
