import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import os from 'node:os';
import {ExportCache,digest,hasExternalPaint} from './cache.mjs';
import {assessCompatibility,checkGroupSelectors} from './preflight.mjs';
import {installSemanticText} from './semantic-text.mjs';
import {installSceneCapture} from './scene.mjs';
import {embedFonts,normalizeParagraphs,nativePaths,promoteLayouts,deduplicateMedia,color} from './package.mjs';
const here=path.dirname(fileURLToPath(import.meta.url));
const req=process.env.HTML_EXPORT_NODE_MODULES?createRequire(path.join(process.env.HTML_EXPORT_NODE_MODULES,'package.json')):createRequire(import.meta.url);
const {chromium}=req('playwright'),Pptx=req('pptxgenjs'),Zip=req('jszip');
const fontReq=process.env.HTML_EXPORT_FONT_MODULES?createRequire(path.join(process.env.HTML_EXPORT_FONT_MODULES,'package.json')):req;
const sharp=req('sharp');
const arg=n=>{const i=process.argv.indexOf(n);return i<0?undefined:process.argv[i+1]};
if(process.argv.includes('--help')){console.log('Usage: node scripts/export.mjs --source deck.html --out NEW_DIRECTORY [--format pptx|pdf|both] [--pdf-mode browser|raster] [--groups auto|profile.json] [--inspect] [--verbose] [--cache-dir DIRECTORY] [--no-cache] [--no-slide-cache]');process.exit(0);}
const format=arg('--format')||'pptx',pdfMode=arg('--pdf-mode')||'browser',inspect=process.argv.includes('--inspect'),verbose=process.argv.includes('--verbose');
if(!['pptx','pdf','both'].includes(format)||!['browser','raster'].includes(pdfMode))throw Error('Invalid --format or --pdf-mode');
if(format==='pdf'&&arg('--groups'))throw Error('PDF viewing mode does not use native PPTX groups');
const wantPptx=format!=='pdf',wantPdf=format!=='pptx';
const autoGroups=arg('--groups')==='auto';
let groupProfile=arg('--groups')&&!autoGroups?JSON.parse(await fs.readFile(path.resolve(arg('--groups')))):null;
if(groupProfile){if(groupProfile.version!==1||(!Array.isArray(groupProfile.rules)||!groupProfile.rules.length))throw Error('Invalid group profile');for(const r of groupProfile.rules)if(!Array.isArray(r.slides)||!r.slides.length||r.slides.some(n=>!Number.isInteger(n)||n<1)||typeof r.selector!=='string'||!r.selector||typeof r.name!=='string'||!r.name||!Number.isInteger(r.expected)||r.expected<1)throw Error('Invalid grouping rule');}
const version=arg('--version')||'v01';if(!/^v[0-9]{2,}$/.test(version))throw Error('Version must be v01, v02, ...');
if(!process.argv.includes('--source')||!process.argv.includes('--out'))throw Error('Usage: node scripts/export.mjs --source input.html --out NEW_OUTPUT_DIRECTORY');
const source=path.resolve(arg('--source')),out=path.resolve(arg('--out'));
await fs.mkdir(out,{recursive:true});if((await fs.readdir(out)).length)throw Error('Output directory must be empty: use a new directory for each run');await fs.mkdir(path.join(out,'assets'),{recursive:true});
const started=performance.now(),report={source,engineVersion:'v08',format,pdfMode:wantPdf?pdfMode:null,timings:{},mode:wantPptx?'native-editable-v08':'viewing-pdf-v08',warnings:[],slides:[],fonts:[]};
const assets=path.join(out,'assets');
const cache=new ExportCache(path.resolve(arg('--cache-dir')||process.env.HTML_EXPORT_CACHE_DIR||path.join(path.dirname(out),'.html-export-cache')),wantPptx&&!process.argv.includes('--no-cache'));
report.cache=cache.stats;
const engineHash=digest(Buffer.concat(await Promise.all((await fs.readdir(here)).filter(n=>/\.(mjs|py)$/.test(n)).sort().map(n=>fs.readFile(path.join(here,n))))));
const fontRuntime=wantPptx?spawnSync(process.env.HTML_EXPORT_PYTHON||'python3',['-c','import sys,fontTools;print(sys.version,fontTools.version)'],{encoding:'utf8'}):null;
if(fontRuntime&&fontRuntime.status)throw Error(fontRuntime.stderr);
const fontSalt=wantPptx?digest(Buffer.concat([await fs.readFile(path.join(here,'font_pack.py')),await fs.readFile(fontReq.resolve('fonteditor-core')),await fs.readFile(path.join(here,'../package.json')),Buffer.from(process.version+fontRuntime.stdout)])):null;
async function run(){
const browser=await chromium.launch({headless:true,...(process.env.HTML_EXPORT_CHROME==='bundled'?{}:{channel:'chrome'})});
try{
 const page=await browser.newPage({viewport:{width:1920,height:1080},reducedMotion:'reduce'});
 await page.route(/^https?:/,r=>r.abort());
 await page.emulateMedia({media:'screen'});
 await page.addInitScript(rules=>{window.__HTML_EXPORT_GROUP_RULES=rules},groupProfile?.rules||[]);
 page.on('pageerror',e=>report.warnings.push({type:'page-error',message:e.message}));
 await page.goto(pathToFileURL(source).href,{waitUntil:'load',timeout:60000});
 await page.evaluate(async()=>{if(window.GigaDevDeck){if(window.GigaDevDeck.schema!==1)throw Error('Unsupported GigaDev HTML Maker schema');await window.GigaDevDeck.prepareExport();}});
 await page.evaluate(async()=>{await Promise.allSettled([...document.fonts].map(f=>f.load()));await document.fonts.ready;});
 await page.evaluate(()=>{window.GigaMotion?.setEnabled(false);window.GigaReveal?.stop();});
 const info=await page.evaluate(()=>{
  const roots=[...document.querySelectorAll('.slide')].filter(e=>!e.parentElement.closest('.slide'));
  if(!roots.length)throw Error('No top-level .slide elements; provide a deck adapter.');
  const stage=document.querySelector('#stage')||document.querySelector('[data-gd-stage]');
  const activeRoot=roots.find(e=>getComputedStyle(e).display!=='none')||roots[0];let display=getComputedStyle(activeRoot).display;
  if(display==='none'){const old=activeRoot.className,hidden=activeRoot.hidden;activeRoot.hidden=false;activeRoot.classList.add('active','is-active');display=getComputedStyle(activeRoot).display;activeRoot.className=old;activeRoot.hidden=hidden;if(display==='none')throw Error('Cannot determine visible slide display; add a deck adapter.');}
  const canvas=[...roots[0].querySelectorAll('svg')].find(e=>e.viewBox.baseVal.width>=640&&e.viewBox.baseVal.height>=360);
  const w=canvas?canvas.viewBox.baseVal.width:stage?parseFloat(getComputedStyle(stage).width):1920,h=canvas?canvas.viewBox.baseVal.height:stage?parseFloat(getComputedStyle(stage).height):1080;
  const sizeBasis=canvas?'intrinsic-svg-viewBox':stage?'stage-design-size':'default-16:9';
  const faces=[];for(const sheet of document.styleSheets){try{for(const r of sheet.cssRules)if(r.type===CSSRule.FONT_FACE_RULE)faces.push({family:r.style.getPropertyValue('font-family').replace(/["']/g,'').trim(),weight:parseInt(r.style.getPropertyValue('font-weight'))||400,src:r.style.getPropertyValue('src')});}catch{}}
  return {count:roots.length,w,h,sizeBasis,display,faces,nested:(window.GIGA_EMBEDDED_DECKS||[]).filter(x=>x.href||x.html||x.src||x.file).length,canvases:document.querySelectorAll('canvas').length,theme:document.documentElement.dataset.theme,style:document.documentElement.dataset.style,animationState:'disabled-complete'};
 });
 const registry=JSON.parse(await fs.readFile(path.join(here,'../profiles/registry.json'),'utf8'));
 if(registry.version!==1||!Array.isArray(registry.profiles))throw Error('Invalid profile registry');
 const assessment=await assessCompatibility(page,info,registry,{wantPptx,groupProfile,autoGroups});
 if(autoGroups&&assessment.selected?.groups)groupProfile=JSON.parse(await fs.readFile(path.join(here,'../profiles',assessment.selected.groups),'utf8'));
 assessment.publicResult.issues.push(...await checkGroupSelectors(page,groupProfile));
 assessment.publicResult.status=assessment.publicResult.issues.some(i=>i.severity==='blocker')?'blocked':assessment.publicResult.issues.length?'review':'ready';
 report.preflight=assessment.publicResult;report.selectedProfile=assessment.publicResult.selectedProfile;
 await fs.writeFile(path.join(out,'preflight.json'),JSON.stringify(assessment.publicResult,null,2));
 if(!inspect&&assessment.publicResult.status==='blocked')throw Error('Preflight blocked export; see '+path.join(out,'preflight.json'));
 await page.evaluate(rules=>{window.__HTML_EXPORT_GROUP_RULES=rules},groupProfile?.rules||[]);
 if(groupProfile?.rules.some(r=>r.slides.some(n=>n>info.count)))throw Error('Group profile references a slide outside this deck');
 if(wantPptx&&!info.faces.length)report.warnings.push({type:'font-embedding-not-provided',message:'System fonts referenced; no cross-device font embedding claim.'});
 report.input={...info,faces:info.faces.map(({src,...face})=>({...face,embeddedSource:src.includes('data:')}))};if(info.nested)report.warnings.push({type:'nested-decks',message:'Only top-level slides exported. Nested interactive presentations remain separate.',count:info.nested});
 if(info.canvases)report.warnings.push({type:'canvas',message:'Canvas/WebGL is captured as a static visual state; animation is not editable.'});
 await page.setViewportSize({width:info.w,height:info.h});
 const paint=wantPptx?await browser.newPage({viewport:{width:info.w,height:info.h},deviceScaleFactor:2}):null;
 if(paint)await paint.setContent('<html><body style="margin:0;background:transparent"></body></html>');
 await page.addStyleTag({content:`html,body{width:${info.w}px!important;height:${info.h}px!important;overflow:hidden!important;margin:0!important}.presentation{display:block!important;height:100%!important}.stage,#stage,#slide-deck{position:absolute!important;inset:0!important;left:0!important;top:0!important;width:${info.w}px!important;height:${info.h}px!important;transform:none!important}.slide{display:none!important}.slide[data-export-current]{display:${info.display}!important;opacity:1!important;visibility:visible!important;position:absolute!important;inset:0!important;width:${info.w}px!important;height:${info.h}px!important}#viewer{position:absolute!important;inset:0!important;width:100%!important;height:100%!important}.controls,.app-bar,.load-status,dialog,#hint{display:none!important}*,*::before,*::after{animation:none!important;transition:none!important}[data-export-hide-before]::before,[data-export-hide-after]::after{content:none!important;display:none!important}.motion-item{transform:none!important;opacity:1!important}@page{size:${info.w}px ${info.h}px;margin:0}`});
 const inventory=await page.evaluate(()=>[...document.querySelectorAll('.slide')].filter(e=>!e.parentElement.closest('.slide')).map((e,i)=>({slide:i+1,id:e.id,classes:[...e.classList],textCharacters:e.textContent.length,images:e.querySelectorAll('img').length,videos:e.querySelectorAll('video').length,svg:e.querySelectorAll('svg').length,links:e.querySelectorAll('a[href]').length})));
 await fs.writeFile(path.join(out,'inventory.json'),JSON.stringify({source,input:report.input,slides:inventory,warnings:report.warnings,preflight:assessment.publicResult},null,2));
 if(inspect){console.log(JSON.stringify({status:'inspected',compatibility:assessment.publicResult.status,selectedProfile:assessment.publicResult.selectedProfile,preflight:path.join(out,'preflight.json'),slides:info.count,size:[info.w,info.h],fonts:report.input.faces,inventory:path.join(out,'inventory.json')}));return;}
 report.timings.initializeSeconds=(performance.now()-started)/1000;
 const fontStarted=performance.now(),fonts=[];
 const {Font}=wantPptx?fontReq('fonteditor-core'):{},svgpath=wantPptx?fontReq('svgpath'):null;
 for(const [i,f] of (wantPptx?info.faces:[]).entries()){
  const m=f.src.match(/url\(["']?(data:[^"')]+)["']?\)/);if(!m){report.warnings.push({type:'font-external',family:f.family});continue;}
  const b=Buffer.from(m[1].split(',')[1],'base64'),type=m[1].includes('otf')?'otf':m[1].includes('woff')?'woff':'ttf',alias='HTML Export Font '+(i+1);
  const raw=path.join(assets,`font-${i+1}.raw`),final=path.join(assets,`font-${i+1}.fntdata`);
  const fontKey=digest(Buffer.concat([Buffer.from(JSON.stringify({fontSalt,alias,type,family:f.family,weight:f.weight})),b]));
  const fontFiles=[`font-${i+1}.source`,`font-${i+1}.raw`,`font-${i+1}.fntdata`,`font-${i+1}.ttf`];
  const fontHit=await cache.restore('fonts',fontKey,assets,fontFiles);
  if(!fontHit){
   const font=Font.create(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),{type,hinting:true,compound2simple:true});font.compound2simple();
   await fs.writeFile(path.join(assets,`font-${i+1}.source`),b);
   await fs.writeFile(raw,Buffer.from(font.write({type:'eot',toBuffer:true})));
   const py=spawnSync(process.env.HTML_EXPORT_PYTHON||'python3',['-c','import sys;sys.path.insert(0,sys.argv[1]);from font_pack import font_copy;from pathlib import Path;Path(sys.argv[3]).write_bytes(font_copy(Path(sys.argv[2]).read_bytes(),sys.argv[4]))',here,raw,final,alias],{encoding:'utf8'});if(py.status)throw Error(py.stderr);
   const packed=await fs.readFile(final);await fs.writeFile(path.join(assets,`font-${i+1}.ttf`),packed.subarray(packed.length-packed.readUInt32LE(4)));
   await cache.store('fonts',fontKey,assets,fontFiles);
  }
  const data=await fs.readFile(final);fonts.push({...f,alias,data});await fs.writeFile(path.join(out,'assets',`font-${i+1}.ttf`),data.subarray(data.length-data.readUInt32LE(4)));
  await page.addStyleTag({content:`@font-face{font-family:"${alias}";src:url(data:font/ttf;base64,${data.subarray(data.length-data.readUInt32LE(4)).toString('base64')})}`});report.fonts.push({family:f.family,weight:f.weight,alias,embedded:true});
 }
 report.timings.fontSeconds=(performance.now()-fontStarted)/1000;
 const fontFingerprint=digest(Buffer.concat(fonts.map(f=>f.data)));
 const slideSalt={engineHash,fontFingerprint,browser:browser.version(),node:process.version,os:[process.platform,process.arch,os.release()],python:fontRuntime?.stdout||'',format,pdfMode,groups:groupProfile};
 const captureStarted=performance.now();
 const pptx=wantPptx?new Pptx():null;if(pptx){pptx.defineLayout({name:'HTML',width:info.w/96,height:info.h/96});pptx.layout='HTML';pptx.title=path.basename(source,'.html');}
 const face=(family,weight)=>{const first=family.split(',')[0].replace(/["']/g,'').trim(),matches=fonts.filter(f=>f.family===first);return matches.sort((a,b)=>Math.abs(a.weight-weight)-Math.abs(b.weight-weight))[0]?.alias||first;};
 const paths=[],numberNames=[],scenes=[],pdfLinks=[];
 for(let n=0;n<info.count;n++){
  if(await page.evaluate(()=>!!window.GigaDevPreview?.showSlide))await page.evaluate(n=>window.GigaDevPreview.showSlide(n,false),n);else await page.keyboard.press(n===0?'Home':'ArrowRight');
  await page.evaluate(async n=>{for(const e of document.querySelectorAll('[data-export-current]'))e.removeAttribute('data-export-current');const e=[...document.querySelectorAll('.slide')].filter(e=>!e.parentElement.closest('.slide'))[n];e.setAttribute('data-export-current','');e.dataset.exportNumber=String(n+1);e.hidden=false;e.classList.add('active','is-active');e.removeAttribute('aria-hidden');for(const a of document.getAnimations())try{a.finish()}catch{};window.dispatchEvent(new Event('resize'));await Promise.all([...e.querySelectorAll('img')].map(i=>i.decode().catch(()=>{})));await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));},n);
  const num=String(n+1).padStart(3,'0'),reference=path.join(out,'assets',`reference-${num}.png`);
  const referencePixels=await page.screenshot({path:reference});
  if(!wantPptx){
   pdfLinks.push(await page.locator('[data-export-current] a[href]').evaluateAll(es=>es.map(e=>{const r=e.getBoundingClientRect();return {href:e.href,x:r.x,y:r.y,w:r.width,h:r.height}})));
   if(pdfMode==='browser')await page.pdf({path:path.join(out,'assets',`page-${num}.pdf`),width:info.w+'px',height:info.h+'px',printBackground:true,preferCSSPageSize:true});
   report.slides.push({number:n+1});continue;
  }
  await page.evaluate(()=>{
   // Turn generated CSS content into measurable DOM, retaining its computed style.
   // Static +/- prefixes already belong to their semantic paragraph.
   const root=document.querySelector('[data-export-current]');
   for(const e of [root,...root.querySelectorAll('*')]){if(e.closest('svg'))continue;for(const which of ['before','after']){const cs=getComputedStyle(e,'::'+which);let content=cs.content;const counter=content.match(/^counter\(([-\w]+)\)$/);if(counter){const key=counter[1];let scope=e.parentElement;while(scope&&!(getComputedStyle(scope).counterReset.split(/\s+/).includes(key)))scope=scope.parentElement;if(scope){const reset=getComputedStyle(scope).counterReset.split(/\s+/),ri=reset.indexOf(key);let value=Number(reset[ri+1])||0;for(const n of scope.querySelectorAll('*')){const inc=getComputedStyle(n).counterIncrement.split(/\s+/),ii=inc.indexOf(key);if(ii>=0)value+=Number(inc[ii+1])||1;if(n===e)break;}content=JSON.stringify(String(value));}}if(['none','normal'].includes(content)||cs.display==='none'||(/^[\"']?[+−-][\"']?$/.test(content)&&cs.position==='static'))continue;if(!/^([\"']).*\1$/.test(content))continue;const span=document.createElement('span');span.dataset.exportGenerated=which;for(const k of cs)span.style.setProperty(k,cs.getPropertyValue(k),'important');span.style.setProperty('content','normal','important');span.textContent=content.slice(1,-1);e.setAttribute('data-export-hide-'+which,'');if(which==='before')e.prepend(span);else e.append(span);}}
  });
  await page.evaluate(installSemanticText);const scene=await page.evaluate(installSceneCapture);scene.number=n+1;scene.size={w:info.w,h:info.h};
  // Source cover intentionally hides its existing counter; keep an invisible native field.
  if(!scene.items.some(it=>it.isNumber)&&await page.locator('[data-export-current] .slide-page').count()){
   const counter=await page.locator('[data-export-current] .slide-page').evaluate(e=>{const s=getComputedStyle(e);return {font:s.fontFamily,size:parseFloat(s.fontSize),color:s.color,weight:parseInt(s.fontWeight)||400}});
   scene.items.push({kind:'text',id:'hidden-native-number',source:'hidden-native-number',x:1740,y:64,w:100,h:32,lineHeight:24,align:'right',numberAlign:'right',isNumber:true,hiddenNumber:true,groupIds:[],runs:[{text:String(n+1),font:counter.font,size:counter.size,weight:counter.weight,color:counter.color,spacing:0,opacity:0}],expectedText:''});
  }

  if(wantPdf&&pdfMode==='browser')await page.pdf({path:path.join(out,'assets',`page-${num}.pdf`),width:info.w+'px',height:info.h+'px',printBackground:true,preferCSSPageSize:true});
  const links=await page.locator('[data-export-current] a[href]').evaluateAll(es=>es.map(e=>{const r=e.getBoundingClientRect();return {href:e.href,x:r.x,y:r.y,w:r.width,h:r.height};}));
  const canCache=cache.enabled&&!process.argv.includes('--no-slide-cache')&&!info.canvases&&!hasExternalPaint(scene.items)&&await page.locator('[data-export-current] video').evaluateAll(vs=>vs.every(v=>v.paused&&v.currentTime===0&&!!v.poster));
  // Player chrome is transient. Hash an independent fresh paused cover and mask
  // only that video rectangle in the key; keep the actual source reference intact.
  const preparedVideos=new Map(),videoKeys=[],masks=[];
  if(canCache)for(const [i,it] of scene.items.entries())if(it.tag==='VIDEO'){
   const video=page.locator('[data-export-current] [data-export-object-id="'+it.id+'"]');
   const controls=await video.evaluate(v=>{const old=v.controls;v.controls=false;v.pause();return old});
   const file=path.join(assets,`object-${num}-${i}.png`);const pixels=await video.screenshot({path:file,omitBackground:true});
   await video.evaluate((v,old)=>{v.controls=old},controls);preparedVideos.set(i,file);videoKeys.push({i,sha256:digest(pixels)});
   const left=Math.max(0,Math.floor(it.x)),top=Math.max(0,Math.floor(it.y)),width=Math.min(info.w-left,Math.ceil(it.x+it.w)-left),height=Math.min(info.h-top,Math.ceil(it.y+it.h)-top);
   if(width>0&&height>0)masks.push({input:await sharp({create:{width,height,channels:4,background:'#000000'}}).png().toBuffer(),left,top});
  }
  const referenceKey=masks.length?await sharp(referencePixels).composite(masks).png().toBuffer():referencePixels;
  // Blob addresses change at every browser launch; the paused cover is checked
  // above and the native MP4 is always read anew during package assembly.
  const keyScene={...scene,items:scene.items.map(it=>it.tag==='VIDEO'&&it.src?.startsWith('blob:')?{...it,src:'fresh-native-video-blob'}:it)};
  const slideKey=canCache?digest(JSON.stringify({salt:slideSalt,slide:n+1,reference:digest(referenceKey),videoKeys,scene:keyScene,links})):null;
  const expectedPaint=[`background-${num}.png`,...scene.items.flatMap((it,i)=>['text','shape'].includes(it.kind)?[]:[`object-${num}-${i}.png`])];
  const slideHit=canCache&&await cache.restore('slides',slideKey,assets,expectedPaint);
  if(cache.enabled&&!canCache)cache.stats.slideBypasses++;
  let base;
  if(!slideHit){const hidden=await page.addStyleTag({content:'.slide[data-export-current],#hud{visibility:hidden!important}'});base=await page.screenshot({omitBackground:false});await hidden.evaluate(e=>e.remove());}
  let pictures=0,shapes=0,textBlocks=0;const bgLayers=[];
  const paintFiles=[];
  for(const [i,it] of scene.items.entries()){
   if(it.kind==='text'){for(const r of it.runs)r.exportFont=face(r.font,r.weight);continue;}
   if(it.kind==='shape')continue;
   const asset=path.join(out,'assets',`object-${num}-${i}.png`);it.asset=asset;paintFiles.push(path.basename(asset));
   if(slideHit||preparedVideos.has(i)){if(it.tag==='VIDEO')it.posterSource='paused-video-without-browser-controls';continue;}
   if(it.kind==='dom-image'){
    if(it.tag==='IMG'&&it.src){await paint.evaluate(async it=>{document.body.innerHTML='';const e=new Image();e.id='export-paint';e.src=it.src;Object.assign(e.style,{display:'block',width:it.w+'px',height:it.h+'px',boxSizing:'border-box',borderStyle:'solid',borderColor:'transparent',...it.props});document.body.append(e);await e.decode();},it);await paint.locator('#export-paint').screenshot({path:asset,omitBackground:true});}
    else if(it.tag==='VIDEO'){
     const video=page.locator('[data-export-current] [data-export-object-id="'+it.id+'"]');
     const controls=await video.evaluate(v=>{const old=v.controls;v.controls=false;v.pause();return old});
     // Capture in the original DOM to preserve ancestor clipping and CSS. Native
     // player chrome is transient and must not be baked into a PowerPoint cover.
     await video.screenshot({path:asset,omitBackground:true});
     await video.evaluate((v,old)=>{v.controls=old},controls);it.posterSource='paused-video-without-browser-controls';
    }else await page.locator('[data-export-current] [data-export-object-id="'+it.id+'"]').screenshot({path:asset,omitBackground:true});
   }else if(it.kind==='svg-image'){
    await paint.evaluate(it=>{document.body.innerHTML=it.svg;const e=document.body.firstElementChild;e.id='export-paint';e.style.display='block';},it);await paint.locator('#export-paint').screenshot({path:asset,omitBackground:true});
   }else{
    await paint.evaluate(async it=>{document.body.innerHTML='';const e=document.createElement('div');e.id='export-paint';Object.assign(e.style,{width:it.w+'px',height:it.h+'px',...it.props});document.body.append(e);await Promise.all([...getComputedStyle(e).backgroundImage.matchAll(/url\(["']?([^"')]+)["']?\)/g)].map(m=>new Promise(r=>{const im=new Image();im.onload=im.onerror=r;im.src=m[1]})));},it);await paint.locator('#export-paint').screenshot({path:asset,omitBackground:true});
   }
  }
  // Only a leading full-slide paint prefix becomes a background. Content is
  // never moved to a layout based solely on its size.
  const prefix=[];for(const it of scene.items){if(it.kind==='text'||Math.abs(it.x)>.2||Math.abs(it.y)>.2||Math.abs(it.w-info.w)>.5||Math.abs(it.h-info.h)>.5)break;prefix.push(it);}
  if(!slideHit)for(const it of prefix){if(it.asset)bgLayers.push({input:await sharp(it.asset).resize(info.w,info.h).png().toBuffer(),left:0,top:0});else{const c=color(it.fill,it.opacity*(it.fillOpacity??1));if(c.transparency<100)bgLayers.push({input:await sharp({create:{width:info.w,height:info.h,channels:4,background:{r:parseInt(c.color.slice(0,2),16),g:parseInt(c.color.slice(2,4),16),b:parseInt(c.color.slice(4,6),16),alpha:1-c.transparency/100}}}).png().toBuffer(),left:0,top:0});}}
  const background=path.join(out,'assets',`background-${num}.png`);if(!slideHit)await sharp(base).composite(bgLayers).png().toFile(background);scene.background=background;scene.backgroundItems=prefix.length;
  paintFiles.push(path.basename(background));if(canCache&&!slideHit)await cache.store('slides',slideKey,assets,paintFiles);
  const slide=pptx.addSlide();slide.background={path:background};let numberName;
  for(const [i,it] of scene.items.entries()){
   if(prefix.includes(it)||it.w<0||it.h<0)continue;
   const name=`HTML ${n+1} ${i} ${it.kind}`,pos={x:it.x/96,y:it.y/96,w:Math.max(.01,it.w)/96,h:Math.max(.01,it.h)/96};it.objectName=name;
   if(it.kind==='text'){
    if(!it.runs.length)continue;let para=0;const runs=[];
    for(const r of it.runs){if(r.newParagraphBefore&&runs.length){runs.at(-1).options.breakLine=true;para=r.paragraphSpaceBefore;}const c=color(r.color,r.opacity??1);runs.push({text:it.isNumber?String(n+1):r.text,options:{fontFace:r.exportFont,fontSize:r.size*.75,charSpacing:r.spacing*.75,...c,bold:!fonts.some(f=>f.alias===r.exportFont)&&r.weight>=600,italic:r.italic,underline:r.underline,softBreakBefore:r.softBreakBefore&&!r.newParagraphBefore,paraSpaceBefore:para*.75,hyperlink:r.href?{url:r.href}:undefined}});}
    if(it.isNumber){pos.x=((it.source==='hud'||it.numberAlign==='right')?it.x+it.w-100:it.x)/96;pos.w=100/96;it.align=(it.source==='hud'||it.numberAlign==='right')?'right':'left';if(numberName)throw Error('Ambiguous slide number on '+(n+1));numberName=name;}
    slide.addText(runs,{...pos,margin:0,wrap:false,fit:'none',valign:'top',align:it.align,lineSpacing:it.lineHeight*.75,paraSpaceAfterPt:0,objectName:name});textBlocks++;continue;
   }
   if(it.kind==='shape'){
    const fill=color(it.fill,it.opacity*(it.fillOpacity??1)),stroke=color(it.stroke,it.opacity*(it.strokeOpacity??1)),custom=it.d||it.points;
    const type=custom?pptx.ShapeType.rect:['circle','ellipse'].includes(it.tag)?pptx.ShapeType.ellipse:it.radius?pptx.ShapeType.roundRect:pptx.ShapeType.rect;
    slide.addShape(type,{...pos,rectRadius:it.radius?it.radius/96:undefined,fill,line:{...stroke,width:(it.strokeWidth||0)*.75},objectName:name});if(custom)paths.push({slide:n+1,name,item:it});shapes++;continue;
   }
   if(it.kind==='dom-image'&&it.tag==='VIDEO'){
    const data=await page.evaluate(()=>{const state=window.QBRDeck?.exportState(),uid=state?.order[Number(document.querySelector('[data-export-current]').dataset.exportNumber)-1],item=state?.slides.find(s=>s.uid===uid);return item?.video?window.QBR_VIDEO_ASSETS?.[item.video.assetId]:null;});
    if(data?.startsWith('data:video/')){slide.addMedia({...pos,type:'video',extn:'mp4',data,cover:'data:image/png;base64,'+(await fs.readFile(it.asset)).toString('base64'),objectName:name});it.nativeVideo=true;pictures++;continue;}
   }
   slide.addImage({...pos,path:it.asset,transparency:Math.round((1-it.opacity)*100),objectName:name});pictures++;
  }
  if(!numberName)report.warnings.push({type:'number-missing',slide:n+1});numberNames.push(numberName);

  for(const l of links)if(/^https?:/.test(l.href)&&l.w&&l.h)slide.addShape(pptx.ShapeType.rect,{x:l.x/96,y:l.y/96,w:l.w/96,h:l.h/96,fill:{color:'FFFFFF',transparency:100},line:{transparency:100},hyperlink:{url:l.href}});
  slide.addNotes('Source: '+path.basename(source)+'; slide '+(n+1)+'; native shapes/text, per-object picture fallback for complex paint.');
  for(const g of scene.groups)g.members=scene.items.filter(it=>g.members.includes(it.id)&&it.objectName).map(it=>it.objectName);
  scene.links=links;pdfLinks.push(links);scenes.push(scene);report.slides.push({number:n+1,textBlocks,shapes,pictures,backgroundObjects:prefix.length,characters:scene.items.filter(x=>x.kind==='text').reduce((v,m)=>v+m.runs.map(r=>r.text).join('').replace(/\s/g,'').length,0),nativeNumber:!!numberName,warnings:scene.warnings});
  if(verbose)console.log(path.basename(source),n+1+'/'+info.count,'texts',textBlocks,'shapes',shapes,'pictures',pictures);
 }
 report.timings.captureSeconds=(performance.now()-captureStarted)/1000;
 const packageStarted=performance.now();
 let output;
 if(wantPptx){
 output=path.join(out,path.basename(source,'.html')+'_Editable_'+version+'.pptx');await pptx.writeFile({fileName:output});
 const z=await Zip.loadAsync(await fs.readFile(output));
 const checkpoint=async name=>{if(!process.env.HTML_EXPORT_DIAGNOSTICS)return;let ct=await z.file('[Content_Types].xml').async('string');ct=ct.replace(/<Override\b[^>]*\/>/g,r=>{const p=r.match(/PartName="\/?([^"]+)"/)?.[1];return !p||z.file(p)?r:'';});z.file('[Content_Types].xml',ct);await fs.writeFile(path.join(process.env.HTML_EXPORT_DIAGNOSTICS,name+'.pptx'),await z.generateAsync({type:'nodebuffer',compression:'DEFLATE'}));};
 // PptxGenJS media uses relationship-derived ids; separate them from shape ids.
 for(const file of Object.keys(z.files).filter(n=>/^ppt\/slides\/slide\d+\.xml$/.test(n))){
  let xml=await z.file(file).async('string');let next=Math.max(...[...xml.matchAll(/<p:cNvPr\b[^>]*id="(\d+)"/g)].map(m=>Number(m[1])))+1;
  xml=xml.replace(/<p:pic>[\s\S]*?<\/p:pic>/g,pic=>pic.includes('<a:videoFile')?pic.replace(/(<p:cNvPr\b[^>]*id=")\d+/,(_,prefix)=>prefix+(next++)):pic);z.file(file,xml);
 }
 await normalizeParagraphs(z);await checkpoint('raw');await embedFonts(z,fonts);await checkpoint('fonts');await nativePaths(z,paths,svgpath);await checkpoint('paths');report.structure=await promoteLayouts(z,{count:info.count,numberNames});report.structure.mediaReuse=await deduplicateMedia(z);
 await fs.writeFile(output,await z.generateAsync({type:'nodebuffer',compression:'DEFLATE'}));
 await fs.writeFile(path.join(out,'scene.json'),JSON.stringify(scenes,null,2));
 if(process.env.HTML_EXPORT_FLAT_PROOF)await fs.copyFile(output,process.env.HTML_EXPORT_FLAT_PROOF);
 if(groupProfile){const grouped=spawnSync(process.env.HTML_EXPORT_PYTHON||'python3',[path.join(here,'group_shapes.py'),'--input',output,'--scene',path.join(out,'scene.json'),'--output',output],{encoding:'utf8'});if(grouped.status)throw Error('Grouping failed: '+grouped.stderr);report.grouping=JSON.parse(grouped.stdout);}
 }
 report.timings.packageSeconds=(performance.now()-packageStarted)/1000;
 const pdfStarted=performance.now();
 if(wantPdf){
  report.pdf=path.join(out,path.basename(source,'.html')+'_Viewing_'+version+'.pdf');
  await fs.writeFile(path.join(out,'pdf-links.json'),JSON.stringify(pdfLinks));
  const merged=spawnSync(process.env.HTML_EXPORT_PYTHON||'python3',[path.join(here,'view_pdf.py'),out,report.pdf,pdfMode,String(info.w),String(info.h),String(info.count)],{encoding:'utf8'});
  if(merged.status)throw Error('Viewing PDF failed: '+merged.stderr);
 }
 report.timings.pdfSeconds=(performance.now()-pdfStarted)/1000;
 report.seconds=(performance.now()-started)/1000;report.output=output||report.pdf;
 await fs.writeFile(path.join(out,'report.json'),JSON.stringify(report,null,2));
 const verifyStarted=performance.now();
 const verified=spawnSync(process.env.HTML_EXPORT_PYTHON||'python3',[path.join(here,'verify.py'),out],{encoding:'utf8'});
 if(verified.status)throw Error('Verification failed: '+verified.stderr);
 report.timings.verifySeconds=(performance.now()-verifyStarted)/1000;report.timings.totalSeconds=(performance.now()-started)/1000;
 report.verification=JSON.parse(verified.stdout.trim());
 await fs.writeFile(path.join(out,'report.json'),JSON.stringify(report,null,2));
 const summary={status:'pass',engineVersion:'v08',format,slides:info.count,pptx:output||null,pdf:report.pdf||null,fonts:fonts.length,fontEmbeddingVerified:fonts.length>0,groups:scenes.reduce((n,s)=>n+s.groups.length,0),seconds:report.timings.totalSeconds,timings:report.timings,cache:report.cache,warnings:report.warnings,compatibility:assessment.publicResult.status,selectedProfile:assessment.publicResult.selectedProfile,preflight:path.join(out,'preflight.json'),report:path.join(out,'report.json'),nativePowerPointVerified:false};
 await fs.writeFile(path.join(out,'summary.json'),JSON.stringify(summary,null,2));console.log(JSON.stringify(summary));
}finally{await browser.close();}

}
await run();
