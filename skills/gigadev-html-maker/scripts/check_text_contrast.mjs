/* Detect low contrast where the browser exposes an unambiguous solid background. */
import fs from 'node:fs/promises';import path from 'node:path';import {createHash} from 'node:crypto';import {fileURLToPath,pathToFileURL} from 'node:url';import {createRequire} from 'node:module';
const [html]=process.argv.slice(2);if(!html||process.argv.length!==3)throw Error('Usage: node check_text_contrast.mjs deck.html');const here=path.dirname(fileURLToPath(import.meta.url));let config={};try{config=JSON.parse(await fs.readFile(path.join(here,'../runtime.local.json'),'utf8'));}catch(e){if(e.code!=='ENOENT')throw e;}const modules=process.env.HTML_MAKER_NODE_MODULES||config.nodeModules,require=modules?createRequire(path.join(modules,'package.json')):createRequire(import.meta.url),{chromium}=require('playwright');const browser=await chromium.launch({headless:true,...(process.env.HTML_MAKER_CHROME==='bundled'?{}:{channel:'chrome'})});
try{const page=await browser.newPage({viewport:{width:1920,height:1080},serviceWorkers:'block'});await page.route(/^https?:/,r=>r.abort());await page.goto(pathToFileURL(path.resolve(html)).href);await page.waitForFunction(()=>window.GigaDevDeck&&window.SalesKitMotion);const order=await page.evaluate(()=>GigaDevDeck.getState().order);const slides=[];
for(const [index,id] of order.entries()){await page.evaluate(i=>{goTo(i);SalesKitMotion.finish()},index);await page.waitForFunction(i=>cur===i,index);const rows=await page.evaluate(id=>{
 const slide=document.querySelector(`#slides > [data-sk-id="${CSS.escape(id)}"]`),content=slide.querySelector('.gd-content'),scale=content.getBoundingClientRect().width/(content.offsetWidth||1)||1;
 const parse=s=>{const m=s.match(/^rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:\s*[,/]\s*([\d.]+))?\s*\)$/);return m?[+m[1],+m[2],+m[3],m[4]===undefined?1:+m[4]]:null};
 const luminance=c=>{let v=c.map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);return .2126*v[0]+.7152*v[1]+.0722*v[2]};
 return [...content.querySelectorAll('[data-eid]')].filter(n=>!n.querySelector('[data-eid]')&&n.checkVisibility({opacityProperty:true,visibilityProperty:true})&&n.textContent.trim()).map(node=>{
  const st=getComputedStyle(node),fg=parse(st.color);let out={sourceId:node.dataset.sourceId||null,editorId:node.dataset.eid,text:node.textContent.trim().slice(0,100),fontSize:st.fontSize,fontWeight:st.fontWeight};
  if(!fg)return {...out,status:'review',reason:'unsupported foreground color'};
  let layers=[],unknown=null,opacity=1;
  for(let n=node;n;n=n.parentElement){const css=getComputedStyle(n);opacity*=Number(css.opacity);if(css.filter!=='none'||css.mixBlendMode!=='normal'){unknown='filter or blending';break;}if(css.backgroundImage!=='none'){unknown='image or gradient background';break;}const c=parse(css.backgroundColor);if(!c){unknown='unsupported background color';break;}if(c[3]>0)layers.push(c);if(c[3]===1)break;
   if(n===slide){const bg=slide.querySelector('.gd-slide-background');if(bg){const s=getComputedStyle(bg);if(s.backgroundImage!=='none'){unknown='slide image or gradient';break;}const c=parse(s.backgroundColor);if(c&&c[3])layers.push(c);}}
  }
  if(unknown||opacity<.999)return {...out,status:'review',reason:unknown||'translucent ancestor'};
  let bg=[0,0,0,0];for(const layer of layers){const rest=1-bg[3];for(let i=0;i<3;i++)bg[i]+=layer[i]*layer[3]*rest;bg[3]+=layer[3]*rest;if(bg[3]>=.999)break;}
  if(bg[3]<.999)return {...out,status:'review',reason:'background not known opaque'};
  const rgb=fg.slice(0,3).map((v,i)=>v*fg[3]+bg[i]*(1-fg[3])),a=luminance(rgb),b=luminance(bg.slice(0,3)),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05),size=parseFloat(st.fontSize)*scale,large=size>=24||(size>=18.66&&Number(st.fontWeight)>=700),threshold=large?3:4.5;
  return {...out,status:ratio<threshold?'fail':'pass',ratio:Math.round(ratio*100)/100,threshold,foreground:fg,background:bg.slice(0,3)};
 });
 },id);slides.push({slide:id,blocks:rows});}
const blocks=slides.flatMap(s=>s.blocks),failures=blocks.filter(b=>b.status==='fail').length,unknown=blocks.filter(b=>b.status==='review').length,uninspectedSlides=slides.filter(s=>!s.blocks.length).map(s=>s.slide);console.log(JSON.stringify({status:failures?'fail':unknown||uninspectedSlides.length?'review':'pass',htmlSha256:createHash('sha256').update(await fs.readFile(html)).digest('hex'),failures,unknown,uninspectedSlides,slides,limitations:['Only solid ancestor backgrounds are measured. Images, gradients, filters and translucent layers require visual or pixel sampling review.','Slides without editable text may contain text inside images; they are not automatically accepted.','Results depend on the current Chromium rendering and do not establish design quality.']},null,2));process.exitCode=failures?1:0;
}finally{await browser.close()}
