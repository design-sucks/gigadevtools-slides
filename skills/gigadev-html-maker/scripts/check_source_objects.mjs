/* Conservative coverage of non-text PPTX objects in deterministic static frames. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';

const [html,inventory,projectFile]=process.argv.slice(2);
if(!html||!inventory||!projectFile)throw Error('Usage: node check_source_objects.mjs deck.html source-deck.json project.json');
const source=JSON.parse(await fs.readFile(inventory,'utf8'));
const project=JSON.parse(await fs.readFile(projectFile,'utf8'));
if(!source.source?.sha256||!Array.isArray(source.slides))throw Error('Independent extracted PPTX deck.json with source hash required');
const here=path.dirname(fileURLToPath(import.meta.url));let config={};
try{config=JSON.parse(await fs.readFile(path.join(here,'../runtime.local.json'),'utf8'));}catch(e){if(e.code!=='ENOENT')throw e;}
const modules=process.env.HTML_MAKER_NODE_MODULES||config.nodeModules;
const require=modules?createRequire(path.join(modules,'package.json')):createRequire(import.meta.url);
const {chromium}=require('playwright');
const browser=await chromium.launch({headless:true,...(process.env.HTML_MAKER_CHROME==='bundled'?{}:{channel:'chrome'})});
try{
 const page=await browser.newPage({viewport:{width:1920,height:1080},reducedMotion:'reduce',serviceWorkers:'block'});
 await page.route(/^https?:/,r=>r.abort());
 await page.goto(pathToFileURL(path.resolve(html)).href);
 await page.waitForFunction(()=>window.GigaDevDeck&&window.SalesKitUI&&window.SalesKitMotion);
 const order=await page.evaluate(async()=>{await GigaDevDeck.prepareExport();return SalesKitUI.getState().order});
 const slides=[];
 for(const [index,id] of order.entries()){
  await page.evaluate(i=>{goTo(i);SalesKitMotion.finish()},index);
  await page.waitForFunction(({i,id})=>SalesKitUI.getState().current===id && Math.abs(slidesEl.scrollTop-slides[i].offsetTop)<2,{i:index,id});
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  slides.push(await page.evaluate(async id=>{
   const slide=document.querySelector(`#slides>.slide[data-sk-id="${CSS.escape(id)}"]`);
   if(!slide)return {id,objects:[]};
   const frame=slide.getBoundingClientRect();
   const visibility=node=>{
    const box=node.getBoundingClientRect();
    if(!node.getClientRects().length||box.width<=0||box.height<=0)return {visible:false,reason:'zero-geometry'};
    let clip={left:frame.left,right:frame.right,top:frame.top,bottom:frame.bottom},opacity=1;
    for(let el=node;el;el=el.parentElement){
     const style=getComputedStyle(el);opacity*=Number(style.opacity);
     if(style.display==='none'||style.contentVisibility==='hidden')return {visible:false,reason:'display-hidden'};
     if(el===node&&style.visibility!=='visible')return {visible:false,reason:'visibility-hidden'};
     if(el!==slide){const r=el.getBoundingClientRect();
      if(['hidden','clip','auto','scroll'].includes(style.overflowX)){clip.left=Math.max(clip.left,r.left);clip.right=Math.min(clip.right,r.right)}
      if(['hidden','clip','auto','scroll'].includes(style.overflowY)){clip.top=Math.max(clip.top,r.top);clip.bottom=Math.min(clip.bottom,r.bottom)}
     }
     if(el===slide)break;
    }
    if(opacity<=0.001)return {visible:false,reason:'transparent'};
    if(Math.min(box.right,clip.right)<=Math.max(box.left,clip.left)||Math.min(box.bottom,clip.bottom)<=Math.max(box.top,clip.top))return {visible:false,reason:'fully-clipped'};
    return {visible:true,reason:null};
   };
   const decode=async image=>{
    image.loading='eager';
    let timer;
    try{
     const task=image.decode?image.decode():new Promise((resolve,reject)=>{
      if(image.complete)return image.naturalWidth>0?resolve():reject(new Error('image failed to load'));
      image.addEventListener('load',resolve,{once:true});image.addEventListener('error',()=>reject(new Error('image failed to load')),{once:true});
     });
     await Promise.race([task,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('decode timeout')),4000)})]);
     return image.naturalWidth>0&&image.naturalHeight>0?'decoded':'failed';
    }catch(e){return String(e.message).includes('timeout')?'timeout':'failed';}
    finally{clearTimeout(timer);}
   };
   const nodes=[...slide.querySelectorAll('[data-source-id]')];
   const images=[...new Set(nodes.flatMap(n=>[...(n.matches('img')?[n]:[]),...n.querySelectorAll('img')]))];
   const loaded=new Map(await Promise.all(images.map(async img=>[img,await decode(img)])));
   return {id,objects:nodes.map(node=>{
    const own=visibility(node),imgs=[...(node.matches('img')?[node]:[]),...node.querySelectorAll('img')];
    const media=[...(node.matches('video,audio')?[node]:[]),...node.querySelectorAll('video,audio')];
    return {id:node.dataset.sourceId,tag:node.tagName.toLowerCase(),...own,
            images:imgs.map(img=>({status:loaded.get(img),...visibility(img)})),
            media:media.length>0,mediaVisible:media.some(m=>visibility(m).visible)};
   })};
  },id));
 }
 const rows=[],bySlide=new Map(slides.map(s=>[s.id,s]));
 for(const slide of source.slides){
  const dest=project.slides.find(s=>s.sourceNumber===slide.sourceNumber),dom=bySlide.get(dest?.id);
  for(const b of slide.blocks||[]){
   if(!['image','geometry','group','chart','media'].includes(b.kind))continue;
   const matches=(dom?.objects||[]).filter(x=>x.id===b.id),target=matches[0];
   let status=!dom?'slide_missing':matches.length===0?'unmapped':matches.length>1?'ambiguous':!target.visible?'hidden':'mapped_review';
   if(status==='mapped_review'&&b.kind==='image'&&target.images.length){
    if(!target.images.some(img=>img.visible))status='hidden';
    else if(target.images.some(img=>img.visible&&img.status==='failed'))status='image_load_failed';
    else if(target.images.some(img=>img.visible&&img.status==='timeout'))status='image_load_unverified';
   }
   if(status==='mapped_review'&&b.kind==='media'){
    if(!target.media)status='media_not_detected';
    else if(!target.mediaVisible)status='hidden';
   }
   rows.push({slide:slide.sourceNumber,sourceId:b.id,kind:b.kind,status,...(matches.length===1?{target}:{})});
  }
 }
 const counts={};for(const row of rows)counts[row.status]=(counts[row.status]||0)+1;
 console.log(JSON.stringify({status:'review',sourceSha256:source.source.sha256,counts,objects:rows,limitations:[
  'Each selected slide is inspected in static export state; image decoding is awaited, with timeouts reported separately.',
  'A source-ID match is traceability, not proof of visual appearance, semantic equivalence, image sharpness, arbitrary masks, occlusion or media playback.',
  'Unmapped geometry/group objects may have been intentionally rebuilt or omitted; inspect source and record decisions.'
 ]},null,2));
}finally{await browser.close()}
