/* Focused shell regression. Probe edits are saved only inside the new QA folder. */
import fs from'node:fs/promises';import path from'node:path';import{fileURLToPath,pathToFileURL}from'node:url';import{createRequire}from'node:module';import assert from'node:assert/strict';
const here=path.dirname(fileURLToPath(import.meta.url)),source=path.resolve(process.argv[2]||''),oi=process.argv.indexOf('--out'),out=oi>=0?path.resolve(process.argv[oi+1]):null;
if(!out||!process.argv[2])throw Error('Usage: node scripts/check.mjs deck.html --out NEW_QA_DIRECTORY');
await fs.mkdir(out,{recursive:true});if((await fs.readdir(out)).length)throw Error('QA directory must be empty');
let config={};try{config=JSON.parse(await fs.readFile(path.join(here,'../runtime.local.json'),'utf8'))}catch(e){if(e.code!=='ENOENT')throw e}
const modules=process.env.HTML_MAKER_NODE_MODULES||config.nodeModules,req=modules?createRequire(path.join(modules,'package.json')):createRequire(import.meta.url),{chromium}=req('playwright');
const browser=await chromium.launch({headless:true,...(process.env.HTML_MAKER_CHROME==='bundled'?{}:{channel:'chrome'})});
const checks=[],errors=[],screens=[];let original,page;
try{
 const context=await browser.newContext({viewport:{width:1600,height:900}});await context.route(/^https?:/,r=>r.abort());
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(source).href);await page.waitForFunction(()=>window.GigaDevDeck&&window.SalesKitMotion?.getState().phase==='idle');
 const initialVersion=await page.locator('#sk-deck-state').evaluate(e=>JSON.parse(e.textContent).version);
 original=await page.evaluate(()=>SalesKitUI.getState());assert(original.order.length);const themes=await page.locator('#sk-deck-state').evaluate(e=>JSON.parse(e.textContent).themes);
 assert.equal(await page.locator('#sk-theme').isVisible(),themes.length>1);checks.push('theme availability and clean initialization');
 assert.equal(await page.locator('#sk-header .sk-logo').count(),0);assert.equal(await page.locator('#sk-version').textContent(),'v'+String(await page.locator('#sk-deck-state').evaluate(e=>JSON.parse(e.textContent).version)).padStart(2,'0'));checks.push('generic title/version and no default logo');
 const rail=await page.locator('#bread').evaluate(e=>({background:getComputedStyle(e).backgroundImage,shadow:getComputedStyle(e).boxShadow}));assert.deepEqual(rail,{background:'none',shadow:'none'});
 for(const viewport of [{width:1600,height:900},{width:1280,height:800},{width:390,height:844}]){
  await page.setViewportSize(viewport);
  for(const theme of themes){
   if((await page.evaluate(()=>SalesKitUI.getState().settings.theme))!==theme)await page.locator('#sk-theme').click();
   await page.evaluate(()=>SalesKitMotion.finish());
   for(let i=0;i<original.order.length;i++){
    await page.evaluate(i=>{goTo(i);SalesKitMotion.finish();},i);
    await page.waitForFunction(()=>Math.abs(slidesEl.scrollTop-slides[cur].offsetTop)<1);await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
    const bad=await page.evaluate(()=>{const s=window.slides[window.cur],r=(s.hasAttribute('data-gd-flow-page')?s.querySelector('.gd-content'):s).getBoundingClientRect();return [...s.querySelectorAll('.gd-content *')].filter(e=>{const c=getComputedStyle(e),b=e.getBoundingClientRect();return c.display!=='none'&&c.visibility!=='hidden'&&Number(c.opacity)>0&&b.width&&b.height&&(b.left<r.left-2||b.right>r.right+2||b.top<r.top-2||b.bottom>r.bottom+2)}).slice(0,8).map(e=>({tag:e.tagName,text:e.textContent.slice(0,100)}))});
    assert.deepEqual(bad,[],`overflow ${viewport.width} ${theme} slide${i+1}`);
    if(viewport.width===1600){const file=`${theme}-${i+1}.png`;await page.screenshot({path:path.join(out,file)});screens.push(file)}
   }
  }
 }
 checks.push('all-slide bounds at desktop, small desktop and narrow viewport in every supplied theme');
 await page.setViewportSize({width:1600,height:900});
 await page.evaluate(()=>{goTo(0);SalesKitMotion.finish()});
 const loaded=await page.evaluate(async()=>{await Promise.all([...document.fonts].map(f=>f.load()));await document.fonts.ready;return [...document.fonts].map(f=>({family:f.family.replaceAll('"',''),weight:f.weight,status:f.status}));});
 if(loaded.some(f=>f.family==='SB Sans Text')){
  for(const family of ['SB Sans Text','SB Sans Display'])for(const weight of ['400','600'])assert(loaded.some(f=>f.family===family&&f.weight===weight&&f.status==='loaded'));
  const faces=await page.evaluate(()=>({body:getComputedStyle(slides[0].querySelector('.slide-inner')).fontFamily,heading:getComputedStyle(slides[0].querySelector('h1,h2')).fontFamily}));
  assert(faces.body.includes('SB Sans Text')&&faces.heading.includes('SB Sans Display'));checks.push('offline SB Sans Text/Display regular and semibold loaded and used');
 }
 if(original.order.length>=2){
  const stage=await page.locator('#sk-canvas').boundingBox();await page.mouse.move(stage.x+stage.width/2,stage.y+stage.height/2);
  assert.equal(await page.locator('#slides').evaluate(e=>getComputedStyle(e).scrollSnapType),'none');
  for(const viewport of [{width:1600,height:900},{width:1400,height:1330},{width:390,height:844}]){
   await page.setViewportSize(viewport);await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
   const clip=await page.locator('#slides').evaluate(e=>({top:e.getBoundingClientRect().top,bottom:e.getBoundingClientRect().bottom,height:innerHeight,scale:e.getBoundingClientRect().height/e.clientHeight}));
   assert(Math.abs(clip.top)<1&&Math.abs(clip.bottom-clip.height)<1&&Math.abs(clip.scale-1)<.0001,'scroll paint must span the full window without scaling native distances');
  }
  await page.setViewportSize({width:1600,height:900});await page.evaluate(()=>{goTo(0);SalesKitMotion.finish()});
  // Native wheel hit-testing can lag the layout after the narrow-to-wide resize.
  await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
  await page.waitForTimeout(100);
  const wheelBox=await page.locator('#slides').boundingBox();await page.mouse.move(wheelBox.x+wheelBox.width/2,wheelBox.y+wheelBox.height/2);
  await page.evaluate(()=>{window.__wheelFrames=[];window.__recordWheel=true;function tick(){if(!window.__recordWheel)return;const c=getComputedStyle(slides[0].querySelector('.slide-inner'));window.__wheelFrames.push({top:slidesEl.scrollTop,phase:SalesKitMotion.getState().phase,opacity:+c.opacity,filter:c.filter,cur});requestAnimationFrame(tick)}tick()});
  const sample=()=>page.evaluate(()=>({top:slidesEl.scrollTop,phase:SalesKitMotion.getState().phase,cur,opacity:+getComputedStyle(slides[0].querySelector('.slide-inner')).opacity}));
  await page.mouse.wheel(0,120);await page.waitForFunction(()=>slidesEl.scrollTop>0);await page.waitForTimeout(100);const first=await sample();
  assert(Math.abs(first.top-120)<1&&first.top<await page.evaluate(()=>slides[0].offsetHeight/2)&&first.phase==='scroll'&&first.cur===0&&first.opacity<1&&first.opacity>0,'small wheel must scrub, not jump');
  await page.mouse.wheel(0,120);await page.waitForFunction(top=>slidesEl.scrollTop>top,first.top);await page.waitForTimeout(80);const second=await sample();assert(Math.abs(second.top-first.top-120)<1,'continued wheel must advance at native speed');
  await page.mouse.wheel(0,-60);await page.waitForFunction(top=>slidesEl.scrollTop<top,second.top);await page.waitForTimeout(80);const reverse=await sample();
  assert(Math.abs(second.top-reverse.top-60)<1&&reverse.opacity>second.opacity,'wheel reversal must immediately reverse the fade');
  const distance=await page.evaluate(()=>Math.min(slidesEl.scrollHeight-slidesEl.clientHeight,slides[0].offsetHeight*2+.25*slides[0].offsetHeight)-slidesEl.scrollTop);
  await page.mouse.wheel(0,distance);await page.waitForFunction(()=>cur>=1);await page.waitForTimeout(100);const many=await sample();
  if(original.order.length>=3)assert(many.cur>=2,'large wheel stream must be free to cross multiple slides');
  assert(!['exit','enter'].includes(many.phase),'wheel must not run the timed clicker transition');
  await page.mouse.wheel(0,-100000);await page.waitForFunction(()=>slidesEl.scrollTop===0);await page.waitForTimeout(80);
  assert.equal((await sample()).opacity,1,'aligned scroll restores full content');
  const frames=await page.evaluate(()=>{window.__recordWheel=false;return window.__wheelFrames});
  assert(frames.some(f=>f.top>0&&f.top<first.top*2)&&frames.every(f=>!['exit','enter'].includes(f.phase)));
  await fs.writeFile(path.join(out,'wheel-frames.json'),JSON.stringify({first,second,reverse,many,frames},null,2));checks.push('native wheel: partial scroll, position-driven blur/opacity, immediate reversal, multi-slide motion and full reset');
 }
 await page.locator('#sk-present').click();
 for(let i=0;i<original.order.length;i++){
  await page.evaluate(i=>{goTo(i);SalesKitMotion.finish()},i);
  const header=await page.evaluate(()=>{const s=slides[cur],m=document.querySelector('#sk-show-meta'),n=document.querySelector('#sk-show-count');return {mode:s.dataset.gdHeader||'full',hidden:m.hidden,meta:m.getBoundingClientRect().toJSON(),number:n.getBoundingClientRect().toJSON(),text:n.textContent}});
  assert.equal(header.hidden,header.mode==='none');
  if(header.mode!=='none'){assert.equal(header.text,String(i+1).padStart(2,'0'));assert(Math.abs(header.number.right-header.meta.right)<2,'number must remain right-aligned with or without breadcrumbs');}
 }
 await page.screenshot({path:path.join(out,'presentation-last-number.png')});
 await page.locator('#sk-show-controls').hover({position:{x:10,y:10}});await page.locator('#sk-exit-present').click();
 await page.evaluate(()=>{goTo(0);SalesKitMotion.finish()});checks.push('presentation headers full/number/none and last-slide counter right edge');
 if(original.order.length>=3){
  await page.evaluate(()=>{goTo(1);goTo(2);goTo(0)});await page.waitForFunction(()=>SalesKitMotion.getState().phase==='idle');assert.equal(await page.evaluate(()=>SalesKitUI.getState().current),original.order[0]);checks.push('rapid navigation settles on latest target');
  const order=[original.order[2],original.order[0]];await page.evaluate(order=>SalesKitUI.setOrder(order),order);await page.evaluate(()=>{goTo(0);SalesKitMotion.finish()});
  assert.deepEqual(await page.evaluate(()=>SalesKitUI.getState().order),order);await page.locator('#sk-build-open').click();assert.equal(await page.locator('#sk-grid .sk-card').count(),original.all.length);await page.locator('#sk-build-close').click();checks.push('reorder/exclude retain organizer records');
  await page.locator('#editBtn').click();const h=page.locator(`#slides>.slide[data-sk-id="${order[0]}"] .slide-inner`).locator('h1,h2,p').first();const before=await h.textContent();await h.click();await page.keyboard.press('ControlOrMeta+a');await page.keyboard.insertText(before+' · QA');await page.locator('#sk-text-done').click();
  assert((await page.evaluate(()=>SalesKitUI.getState().edits))&&await h.textContent()===before+' · QA');
  await page.locator('#editBtn').click();await page.locator('#editUndo').click();assert.equal(await h.textContent(),before);await page.locator('#editRedo').click();assert.equal(await h.textContent(),before+' · QA');await page.locator('#sk-text-done').click();checks.push('real text edit and undo/redo');
  await page.locator('#sk-present').click();assert.equal(await page.locator('#sk-show-count').textContent(),'01');assert.equal(await page.locator('#sk-show-section').textContent(),await page.locator('#slides>.slide').first().getAttribute('data-sk-section'));await page.locator('#sk-show-controls').hover({position:{x:10,y:10}});await page.locator('#sk-exit-present').click();checks.push('presentation mode metadata follows selected slide');
  await page.locator('#sk-screen-open').click();for(const[name,value]of Object.entries({contrast:123,shadows:127,muted:32,saturation:91}))await page.locator(`#sk-screen-panel input[name=${name}]`).evaluate((e,value)=>{e.value=String(value);e.dispatchEvent(new Event('input',{bubbles:true}));},value);await page.locator('#sk-screen-close').click();const calibration=await page.evaluate(()=>({screen:SalesKitUI.getState().settings.screen,colors:document.getElementById('sk-colors').textContent}));
  const saved=await page.evaluate(()=>SalesKitUI.exportDocument('work'));const bundle=await page.evaluate(()=>SalesKitUI.exportDocument('bundle'));
  await fs.writeFile(path.join(out,'Probe_Work_v'+String(initialVersion+1).padStart(2,'0')+'.html'),saved);await fs.writeFile(path.join(out,'Probe_Bundle_v'+String(initialVersion+1).padStart(2,'0')+'.html'),bundle);
  const reopen=await context.newPage();reopen.on('pageerror',e=>errors.push(e.message));await reopen.goto(pathToFileURL(path.join(out,'Probe_Work_v'+String(initialVersion+1).padStart(2,'0')+'.html')).href);await reopen.waitForFunction(()=>window.GigaDevDeck&&window.SalesKitUI);assert.deepEqual(await reopen.evaluate(()=>SalesKitUI.getState().order),order);assert.equal(await reopen.locator('#sk-version').textContent(),'v'+String(initialVersion+1).padStart(2,'0'));assert.equal(await reopen.locator(`#slides>.slide[data-sk-id="${order[0]}"] .slide-inner`).locator('h1,h2,p').first().textContent(),before+' · QA');
  assert.deepEqual(await reopen.evaluate(()=>SalesKitUI.getState().settings.screen),calibration.screen);assert.equal(await reopen.locator('#sk-colors').textContent(),calibration.colors);
  await reopen.evaluate(()=>GigaDevDeck.prepareExport());assert.equal(await reopen.locator('[data-gd-chrome]:visible').count(),0);assert.deepEqual(await reopen.locator('#slides>.slide .slide-page').allTextContents(),['1','2']);await fs.writeFile(path.join(out,'Selected_Export_v'+String(initialVersion+1).padStart(2,'0')+'.html'),await reopen.content());await reopen.close();
  const bundled=await context.newPage();await bundled.goto(pathToFileURL(path.join(out,'Probe_Bundle_v'+String(initialVersion+1).padStart(2,'0')+'.html')).href);await bundled.waitForFunction(()=>window.SalesKitUI);assert.equal((await bundled.evaluate(()=>SalesKitUI.getState().all)).length,2);assert.deepEqual(await bundled.evaluate(()=>SalesKitUI.getState().settings.screen),calibration.screen);assert.equal(await bundled.locator('#sk-colors').textContent(),calibration.colors);checks.push('non-default screen calibration and palette survive work/bundle save and reopen');await bundled.close();checks.push('save/reopen and bundle retain edits/order/version; static export has selected counters and no UI');
 }
 for(const[kind,dialog]of[['journal','sk-journal'],['build','sk-organizer']]){await page.locator('#sk-'+kind+'-open').click();await page.locator('#sk-screen-open').click();assert.equal(await page.locator('#sk-screen-panel').evaluate(e=>e.matches(':popover-open')),true);await page.keyboard.press('Escape');assert.equal(await page.locator('#'+dialog).evaluate(e=>e.open),true);assert.equal(await page.locator('#sk-screen-panel').isVisible(),false);await page.locator('#sk-'+kind+'-expand').click();await page.locator('#sk-screen-open').click();assert.equal(await page.locator('#sk-screen-panel').evaluate(e=>!!e.closest('dialog:modal')),true);assert.equal(await page.locator('#sk-screen-panel input[name=contrast]').evaluate(e=>{const r=e.getBoundingClientRect();return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)===e;}),true);await page.keyboard.press('Escape');assert.equal(await page.locator('#'+dialog).evaluate(e=>e.open),true);await page.locator('#sk-'+kind+'-close').click();}assert.equal(await page.locator('[data-sk-screen-open]').count(),1);assert.equal(await page.locator('#sk-header').evaluate(e=>e.parentElement.tagName),'BODY');checks.push('screen controls stay topmost in docked/full journal and organizer; Escape preserves the workspace');
 await page.evaluate(()=>GigaDevDeck.prepareExport());assert.equal(await page.locator('[data-gd-chrome]:visible').count(),0);assert.deepEqual(await page.locator('#slides>.slide').first().evaluate(e=>{const inner=e.querySelector('.slide-inner'),c=e.querySelector('.gd-content'),bg=e.querySelector('.gd-slide-background');return{width:e.offsetWidth,height:e.offsetHeight,innerLeft:inner.offsetLeft,innerTop:inner.offsetTop,innerWidth:inner.offsetWidth,innerHeight:inner.offsetHeight,contentLeft:c.offsetLeft,contentTop:c.offsetTop,contentWidth:c.offsetWidth,contentHeight:c.offsetHeight,backgroundFull:!bg||(bg.offsetWidth===1920&&bg.offsetHeight===1080)};}),{width:1920,height:1080,innerLeft:0,innerTop:0,innerWidth:1920,innerHeight:1080,contentLeft:112,contentTop:120,contentWidth:1696,contentHeight:874,backgroundFull:true});checks.push('static export keeps full 1920x1080 moving frame and optional full-bleed background, with 1696x874 safe content at 112,120');
 const reduced=await browser.newContext({viewport:{width:1280,height:800},reducedMotion:'reduce'}),rp=await reduced.newPage();await rp.goto(pathToFileURL(source).href);await rp.waitForFunction(()=>window.SalesKitUI);const respectsDefault=await rp.locator('#sk-deck-state').evaluate(e=>JSON.parse(e.textContent).settings.motion==null);if(respectsDefault){assert.equal(await rp.evaluate(()=>SalesKitUI.getState().settings.motion),false);checks.push('OS reduced-motion respected by default');}await reduced.close();
 assert.deepEqual(errors,[]);const report={status:'pass',source,checks,screens,errors,scope:'Chromium on Mac; shell regression only, not arbitrary content/style or PowerPoint acceptance'};await fs.writeFile(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({status:'pass',checks:checks.length,report:path.join(out,'report.json')}));
}catch(error){
 const state=page?await page.evaluate(()=>({viewport:[innerWidth,innerHeight],scrollTop:window.slidesEl?.scrollTop,scrollHeight:window.slidesEl?.scrollHeight,clientHeight:window.slidesEl?.clientHeight,hit:document.elementFromPoint(innerWidth/2,innerHeight/2)?.outerHTML.slice(0,400),lockScroll:typeof lockScroll==='undefined'?null:lockScroll,motion:window.SalesKitMotion?.getState()})).catch(e=>({error:String(e)})):null;
 await fs.writeFile(path.join(out,'failure.json'),JSON.stringify({error:String(error),checks,state},null,2));
 if(page)await page.screenshot({path:path.join(out,'failure.png')}).catch(()=>{});throw error;
}finally{await browser.close()}
