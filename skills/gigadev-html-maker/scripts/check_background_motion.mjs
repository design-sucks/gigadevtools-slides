/* Full-bleed background geometry and native motion regression on the accepted 13-slide demo. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {fileURLToPath, pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';

const here=path.dirname(fileURLToPath(import.meta.url)),out=path.resolve(process.argv[2]||'');
if(!process.argv[2])throw Error('Usage: node scripts/check_background_motion.mjs EMPTY_QA_DIRECTORY');
await fs.mkdir(out,{recursive:true});if((await fs.readdir(out)).length)throw Error('QA directory must be empty');
let config={};try{config=JSON.parse(await fs.readFile(path.join(here,'../runtime.local.json'),'utf8'))}catch(e){if(e.code!=='ENOENT')throw e}
const modules=process.env.HTML_MAKER_NODE_MODULES||config.nodeModules,req=modules?createRequire(path.join(modules,'package.json')):createRequire(import.meta.url),{chromium}=req('playwright');
const assets=path.resolve(here,'../assets'),sourceProject=path.resolve(here,'../../../examples/shell-demo/project'),project=path.join(out,'project');
try {await fs.access(path.join(sourceProject,'deck.json'));await fs.cp(sourceProject,project,{recursive:true})}
catch(e){if(e.code!=='ENOENT')throw e;await fs.mkdir(project,{recursive:true});await fs.copyFile(path.join(assets,'example-deck.json'),path.join(project,'deck.json'));await fs.copyFile(path.join(assets,'example-theme.json'),path.join(project,'theme.json'));await fs.cp(path.join(assets,'fonts'),path.join(project,'fonts'),{recursive:true})}
const deckPath=path.join(project,'deck.json'),deck=JSON.parse(await fs.readFile(deckPath,'utf8'));
assert.equal(deck.slides.length,13,'accepted fixture must contain 13 slides');
deck.slides.forEach((s,i)=>{s.background={type:'color',value:`#${(0x183348+i*0x070503).toString(16).padStart(6,'0')}`}});
await fs.writeFile(deckPath,JSON.stringify(deck));
const built=path.join(out,'Accepted_Demo_Background_QA.html');
const build=spawnSync('python3',[path.join(here,'build.py'),deckPath,built,'--theme',path.join(project,'theme.json')],{encoding:'utf8'});
if(build.status!==0)throw Error(build.stderr||build.stdout||'build.py failed');
const browser=await chromium.launch({headless:true,...(process.env.HTML_MAKER_CHROME==='bundled'?{}:{channel:'chrome'})});
const checks=[],errors=[];
async function open(file,viewport={width:1600,height:900}){const p=await browser.newPage({viewport});p.on('pageerror',e=>errors.push(e.message));await p.goto(pathToFileURL(file).href);await p.waitForFunction(()=>window.GigaDevDeck&&window.SalesKitUI&&window.SalesKitMotion);await p.evaluate(()=>document.fonts.ready);return p}
function close(a,b,tol=1){assert(Math.abs(a-b)<=tol,`${a} differs from ${b} by more than ${tol}px`)}
try{
 const page=await open(built);
 const layer=await page.evaluate(()=>{const slide=slides[0],bg=slide.querySelector('.gd-slide-background'),inner=slide.querySelector('.slide-inner');return{count:slides.length,parent:bg?.parentElement?.className||null,inner:!!bg&&bg.parentElement===inner,stage:document.querySelector('#sk-stage').getBoundingClientRect().toJSON(),bg:bg?.getBoundingClientRect().toJSON()||null,nav:getComputedStyle(document.querySelector('#bread')).display}});
 assert.equal(layer.count,13);assert(layer.bg,'fixture must build a slide background');assert.equal(layer.inner,true,'background must share the native slide motion layer');checks.push('fresh build of accepted 13-slide demo places backgrounds inside .slide-inner');
 for(const viewport of [{width:1600,height:900},{width:1400,height:1330},{width:1280,height:800},{width:390,height:844}]){
  await page.setViewportSize(viewport);await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
  for(const nav of viewport.width>700?[true,false]:[false,true]){
   const navToggle=page.locator('#sk-sidebar-toggle');const shown=await page.evaluate(()=>document.documentElement.dataset.skNav==='on');if(shown!==nav)await navToggle.click();
   await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
   const g=await page.evaluate(()=>{const stage=document.querySelector('#sk-stage'),s=slides[0],b=s.querySelector('.gd-slide-background'),c=s.querySelector('.gd-content'),r=stage.getBoundingClientRect(),br=b.getBoundingClientRect(),cr=c.getBoundingClientRect(),navOn=document.documentElement.dataset.skNav==='on',show=document.documentElement.hasAttribute('data-sk-present'),mobile=innerWidth<=700,navSpace=navOn&&!mobile?Math.max(180,document.querySelector('#bread').offsetWidth+24):0,left=show?0:navSpace||20,right=show?0:mobile?8:20,oldWidth=innerWidth-left-right,top=show?0:mobile?68:72,bottom=show?0:56,scale=Math.max(.01,Math.min(oldWidth/1920,Math.max(1,innerHeight-top-bottom)/1080)),expectedLeft=left+(oldWidth-1920*scale)/2+112*scale,expectedTop=top+(innerHeight-top-bottom-1080*scale)/2+120*scale;return{stage:[r.x,r.y,r.width,r.height],bg:[br.x,br.y,br.width,br.height],content:[cr.x,cr.y],expected:[expectedLeft,expectedTop],navOn,navRect:document.querySelector('#bread').getBoundingClientRect().toJSON()}});
   close(g.stage[0],0);close(g.stage[1],0);close(g.stage[2],viewport.width);close(g.stage[3],viewport.height);close(g.bg[0],0);close(g.bg[1],0);close(g.bg[2],viewport.width);close(g.bg[3],viewport.height);close(g.content[0],g.expected[0],1.1);close(g.content[1],g.expected[1],1.1);
   if(nav){assert(g.navRect.width>0&&g.navRect.height>0,'visible nav rail expected over full-bleed background');assert(g.bg[0]<=g.navRect.x&&g.bg[0]+g.bg[2]>=g.navRect.right)}
   checks.push(`viewport background and prior content anchors ${viewport.width}x${viewport.height}, nav ${nav?'on':'off'}`);
  }
 }
 // Return to desktop and scroll 120px per native wheel event, then reverse.
 await page.setViewportSize({width:1600,height:900});await page.evaluate(()=>{document.documentElement.dataset.skNav='on';goTo(0);SalesKitMotion.finish()});
 const box=await page.locator('#slides').boundingBox();await page.mouse.move(box.x+box.width*.7,box.y+box.height*.5);
 // Use real native wheel events at 120px increments, then reverse one step.
 const samples=[];for(const top of [120,240,360]){await page.mouse.wheel(0,120);await page.waitForFunction(t=>Math.abs(slidesEl.scrollTop-t)<1,top);await page.waitForTimeout(45);samples.push(await page.evaluate(()=>{const s=slides[0],inner=s.querySelector('.slide-inner'),bg=s.querySelector('.gd-slide-background');let opacity=1,filters=[];for(let n=bg;n&&n!==s.parentElement;n=n.parentElement){const c=getComputedStyle(n);opacity*=Number(c.opacity);if(c.filter!=='none')filters.push(c.filter)}return{top:slidesEl.scrollTop,opacity,filters,innerOpacity:+getComputedStyle(inner).opacity,innerFilter:getComputedStyle(inner).filter,bgOpacity:+getComputedStyle(bg).opacity,bgFilter:getComputedStyle(bg).filter}}))}
 const hasBlur=filters=>filters.some(f=>{const m=f.match(/blur\(([\d.]+)px\)/);return m&&Number(m[1])>.05});assert(samples.every(x=>x.opacity>0&&x.opacity<1&&hasBlur(x.filters)),'native partial scroll must give the background effective opacity and blur');assert(samples[0].opacity>samples[1].opacity&&samples[1].opacity>samples[2].opacity,'wheel opacity should progress continuously with distance');
 const forward=await page.evaluate(()=>{const s=slides[0],i=s.querySelector('.slide-inner'),c=s.querySelector('.gd-content');return{opacity:+getComputedStyle(i).opacity,filter:getComputedStyle(i).filter,contentOpacity:+getComputedStyle(c).opacity,contentFilter:getComputedStyle(c).filter}});
 await page.mouse.wheel(0,-120);await page.waitForFunction(()=>Math.abs(slidesEl.scrollTop-240)<1);await page.waitForTimeout(45);const reverse=await page.evaluate(()=>{const s=slides[0],i=s.querySelector('.slide-inner');return{top:slidesEl.scrollTop,opacity:+getComputedStyle(i).opacity,filter:getComputedStyle(i).filter}});
 assert(reverse.opacity>forward.opacity&&/blur\(/.test(forward.filter)&&/blur\(/.test(reverse.filter),'wheel reversal must reverse the background opacity/blur without snapping');checks.push('partial wheel positions 120/240/360 and reversal change effective background opacity/blur continuously');
 // The timed keyboard transition animates both outgoing and incoming background layers.
 await page.evaluate(()=>{slidesEl.scrollTop=0;goTo(0);SalesKitMotion.finish()});await page.keyboard.press('ArrowRight');await page.waitForTimeout(100);
 const arrow100=await page.evaluate(()=>{const b=slides[0].querySelector('.gd-slide-background'),i=slides[0].querySelector('.slide-inner');return{target:cur,opacity:+getComputedStyle(b).opacity,filter:getComputedStyle(b).filter,innerFilter:getComputedStyle(i).filter}});
 await page.waitForTimeout(150);const arrow250=await page.evaluate(()=>{const b=slides[0].querySelector('.gd-slide-background');return{opacity:+getComputedStyle(b).opacity,filter:getComputedStyle(b).filter}});
 await page.waitForTimeout(170);const arrow420=await page.evaluate(()=>{const b=slides[0].querySelector('.gd-slide-background');return{cur,opacity:+getComputedStyle(b).opacity,filter:getComputedStyle(b).filter}});
 await page.waitForTimeout(300);await page.waitForFunction(()=>cur===1&&SalesKitMotion.getState().phase==='enter');await page.waitForTimeout(140);const arrow700=await page.evaluate(()=>{const b=slides[1].querySelector('.gd-slide-background');return{cur,opacity:+getComputedStyle(b).opacity,filter:getComputedStyle(b).filter}});
 assert.equal(arrow100.target,1);assert(arrow100.opacity<1&&/blur\(/.test(arrow100.filter),'ArrowRight outgoing background begins with opacity and blur');assert(arrow250.opacity<arrow100.opacity&&/blur\(/.test(arrow250.filter),'ArrowRight outgoing background continues fading and blurring');assert(arrow420.opacity<arrow250.opacity&&/blur\(/.test(arrow420.filter),'ArrowRight outgoing background retains an intermediate blurred state at 420ms');assert.equal(arrow700.cur,1);assert(arrow700.opacity<1&&arrow700.opacity>0&&/blur\(/.test(arrow700.filter),'incoming background must join the key transition');checks.push('ArrowRight timed transition samples outgoing bg at 100/250/420ms and incoming bg at 700ms');
 // Motion off must leave no WAAPI residue; serialized work must reopen cleanly.
 await page.locator('#sk-motion').click();await page.waitForFunction(()=>document.documentElement.dataset.skMotion==='off');await page.evaluate(()=>SalesKitMotion.finish());
 const staticState=await page.evaluate(()=>{const b=slides[cur].querySelector('.gd-slide-background'),i=slides[cur].querySelector('.slide-inner');return{opacity:getComputedStyle(b).opacity,filter:getComputedStyle(b).filter,innerOpacity:getComputedStyle(i).opacity,innerFilter:getComputedStyle(i).filter,bgStyle:b.getAttribute('style'),innerStyle:i.getAttribute('style')}});
 assert.equal(staticState.opacity,'1');assert.equal(staticState.filter,'none');assert.equal(staticState.innerOpacity,'1');assert.equal(staticState.innerFilter,'none');
 const work=await page.evaluate(()=>SalesKitUI.exportDocument('work',2));const saved=path.join(out,'saved-work.html');await fs.writeFile(saved,work);const reopened=await open(saved,{width:390,height:844});await reopened.setViewportSize({width:1280,height:800});await reopened.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
 const reopenedState=await reopened.evaluate(()=>{const b=slides[0].querySelector('.gd-slide-background'),i=slides[0].querySelector('.slide-inner');return{opacity:getComputedStyle(b).opacity,filter:getComputedStyle(b).filter,innerOpacity:getComputedStyle(i).opacity,innerFilter:getComputedStyle(i).filter,bgStyle:b.getAttribute('style'),innerStyle:i.getAttribute('style'),backgroundInside:b.parentElement===i}});
 assert.equal(reopenedState.opacity,'1');assert.equal(reopenedState.filter,'none');assert.equal(reopenedState.innerOpacity,'1');assert.equal(reopenedState.innerFilter,'none');assert.equal(reopenedState.backgroundInside,true);assert(!/opacity|filter/.test(reopenedState.bgStyle));assert.equal(reopenedState.innerStyle,null);const reopenedGeometry=await reopened.evaluate(()=>{const r=document.querySelector('#sk-stage').getBoundingClientRect(),b=slides[0].querySelector('.gd-slide-background').getBoundingClientRect();return{stage:[r.x,r.y,r.width,r.height],bg:[b.x,b.y,b.width,b.height]}});assert.deepEqual(reopenedGeometry.stage,[0,0,1280,800]);assert.deepEqual(reopenedGeometry.bg,[0,0,1280,800]);checks.push('motion-off is static; save/reopen removes transient styles and refits after mobile-to-desktop resize');
 assert.deepEqual(errors,[]);await fs.writeFile(path.join(out,'report.json'),JSON.stringify({status:'pass',checks,layer,samples,forward,reverse,arrow100,arrow250,arrow420,arrow700,staticState,reopenedState,reopenedGeometry,sourceProject,sourceHtml:built},null,2));console.log(JSON.stringify({status:'pass',checks:checks.length,out}));await reopened.close();await page.close();
}catch(error){await fs.writeFile(path.join(out,'failure.json'),JSON.stringify({error:error.message,checks},null,2));throw error}finally{await browser.close()}
