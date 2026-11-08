/* Compare independent source inventory against the rendered final Maker DOM. */
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
const [html, inventory, projectFile, ...args] = process.argv.slice(2);
if (!html || !inventory || !projectFile || args.length % 2 || args.some((x,i) => i % 2 === 0 && !['--mode','--transformations','--source','--off-canvas','--source-alpha'].includes(x))) throw Error('Usage: node check_source_dom.mjs deck.html source-inventory.json project.json [--mode editable|viewing] [--transformations changes.json] [--source source.pptx] [--off-canvas reviewed-omissions.json] [--source-alpha reviewed-runs.json]');
const here=path.dirname(fileURLToPath(import.meta.url));
let config={};try { config=JSON.parse(await fs.readFile(path.join(here,'../runtime.local.json'),'utf8')); } catch(e) { if(e.code!=='ENOENT')throw e; }
const modules=process.env.HTML_MAKER_NODE_MODULES || config.nodeModules;
const require=modules ? createRequire(path.join(modules,'package.json')) : createRequire(import.meta.url);
const {chromium}=require('playwright');
const project=JSON.parse(await fs.readFile(projectFile,'utf8'));
const roleRun=spawnSync('python3',[path.join(here,'presentation_roles.py'),inventory,projectFile],{encoding:'utf8'});
if(roleRun.status!==0)throw Error('Invalid source chrome: '+roleRun.stdout);
const chromeProof=JSON.parse(roleRun.stdout).entries;
const inputHtmlSha=createHash('sha256').update(await fs.readFile(html)).digest('hex');
const alphaArg=args.indexOf('--source-alpha'),sourceArg=args.indexOf('--source');
const inventoryArgs=args.filter((_,i)=>alphaArg<0 || (i!==alphaArg && i!==alphaArg+1));
let alphaProof=null;
if(alphaArg>=0){
 if(sourceArg<0)alphaProof={status:'fail',error:'original PPTX is required'};
 else {const r=spawnSync('python3',[path.join(here,'source_alpha.py'),args[sourceArg+1],inventory,projectFile,args[alphaArg+1]],{encoding:'utf8',maxBuffer:16*1024*1024});
  try{alphaProof=JSON.parse(r.stdout)}catch{alphaProof={status:'fail',error:r.stderr||'source alpha verifier failed'}}}
}

const browser=await chromium.launch({headless:true,...(process.env.HTML_MAKER_CHROME==='bundled'?{}:{channel:'chrome'})});
const temp=path.join(os.tmpdir(),`gd-source-dom-${randomUUID()}.json`);
try {
 const page=await browser.newPage({serviceWorkers:'block'});
 await page.route(/^https?:/,r=>r.abort());
 await page.goto(pathToFileURL(path.resolve(html)).href);
 await page.waitForFunction(()=>window.GigaDevDeck && document.querySelector('#slides'));
 const offCanvasArg=args.indexOf('--off-canvas');let rawOffCanvasTargets=[],offCanvasEntries=[];
 if(offCanvasArg>=0){
  const manifest=JSON.parse(await fs.readFile(args[offCanvasArg+1],'utf8'));
  offCanvasEntries=manifest.dispositions??[];
  // Runtime detaches excluded slides. Stream the original inert HTML separately;
  // do not clone a potentially hundreds-of-megabytes deck into browser memory.
  const scanned=spawnSync('python3',[path.join(here,'source_dispositions.py'),html,args[offCanvasArg+1]],{encoding:'utf8',maxBuffer:16*1024*1024});
  if(scanned.status!==0||!scanned.stdout)throw Error(scanned.stderr||'Saved HTML source-ID scan failed');
  rawOffCanvasTargets=JSON.parse(scanned.stdout);
 }
 await page.setViewportSize({width:1920,height:1080});
 await page.evaluate(async()=>{await GigaDevDeck.prepareExport();await document.fonts.ready});
 const order=await page.evaluate(()=>SalesKitUI.getState().order);
 const rendered=[];
 for (const [index,slideId] of order.entries()) {
  await page.evaluate(i=>{goTo(i);SalesKitMotion.finish()},index);
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  const shapeIds=(alphaProof?.observations??[]).filter(x=>x.slideId===slideId&&x.shapeProof).map(x=>x.sourceId);
  const gradientSvgs=Object.fromEntries((alphaProof?.observations??[]).filter(x=>x.slideId===slideId&&x.shapeProof?.kind==='source-gradient-svg-v1').map(x=>[x.sourceId,x.shapeProof.expectedSvg]));
  rendered.push(await page.evaluate(({id,shapeIds,gradientSvgs})=>{
   const slide=document.querySelector(`#slides > .slide[data-sk-id="${CSS.escape(id)}"]`);
   if(!slide)return {id,html:'',targets:[]};
   const frame=slide.getBoundingClientRect();
   const transparent=color=>/^(transparent|rgba\([^)]*[,\s/]\s*0(?:\.0+)?\s*\))$/i.test(color.trim());
   const intersect=(a,b)=>({left:Math.max(a.left,b.left),top:Math.max(a.top,b.top),right:Math.min(a.right,b.right),bottom:Math.min(a.bottom,b.bottom)});
   const textEvidence=node=>{
    let invisible=false,clipped=false,uncertain=false,offset=0;const nodes=[],nodeMap=new Map();
    const walker=document.createTreeWalker(node,NodeFilter.SHOW_TEXT);
    while(walker.nextNode()){
     const t=walker.currentNode;const start=offset;offset+=t.data.length;if(t.parentElement.closest('script,style,svg,video,audio'))continue;const substantive=Boolean(t.data.trim());
     let nodeInvisible=false,nodeClipped=false,nodeUncertain=false,onlyColor=false,hiddenLayout=false;
     const parent=t.parentElement;let clip={left:frame.left,top:frame.top,right:frame.right,bottom:frame.bottom};let alpha=1;
     const own=getComputedStyle(parent);
     if(own.visibility!=='visible'&&substantive)nodeInvisible=true;
     onlyColor=transparent(own.color)||transparent(own.webkitTextFillColor);if(onlyColor&&substantive)nodeInvisible=true;
     for(let el=parent;el;el=el.parentElement){
      const cs=getComputedStyle(el);alpha*=Number(cs.opacity);
      if(cs.display==='none'||cs.contentVisibility==='hidden'||cs.visibility!=='visible'||Number(cs.opacity)<=0.001){if(substantive)nodeInvisible=true;onlyColor=false;hiddenLayout=true;}
      if(cs.clipPath!=='none'||cs.maskImage!=='none'||cs.clip!=='auto')nodeUncertain=true;
      if(el!==slide && ['hidden','clip','scroll','auto'].some(v=>cs.overflowX===v||cs.overflowY===v)){
       const r=el.getBoundingClientRect();const x=['hidden','clip','scroll','auto'].includes(cs.overflowX);const y=['hidden','clip','scroll','auto'].includes(cs.overflowY);
       clip=intersect(clip,{left:x?r.left:-Infinity,right:x?r.right:Infinity,top:y?r.top:-Infinity,bottom:y?r.bottom:Infinity});
      }
      if(el===slide)break;
     }
     if(alpha<=0.001){if(substantive)nodeInvisible=true;onlyColor=false;hiddenLayout=true;}
     const range=document.createRange();range.selectNodeContents(t);const rects=[...range.getClientRects()].filter(r=>r.width>0&&r.height>0);
     if(!rects.length&&substantive){nodeInvisible=true;onlyColor=false;}
     for(const r of substantive?rects:[])if(r.left<clip.left-1||r.right>clip.right+1||r.top<clip.top-1||r.bottom>clip.bottom+1)nodeClipped=true;
     const mark=parent.closest('[data-source-alpha-run]');
     const marker=mark && node.contains(mark) && mark===parent && mark.tagName==='SPAN' && mark.childNodes.length===1 ? mark.dataset.sourceAlphaRun : null;
     const record={start,end:offset,text:t.data,marker,invisible:nodeInvisible,clipped:nodeClipped,uncertain:nodeUncertain,onlyColor,hiddenLayout,zeroFont:parseFloat(own.fontSize)===0};nodes.push(record);nodeMap.set(t,record);
     invisible ||= nodeInvisible;clipped ||= nodeClipped;uncertain ||= nodeUncertain;
    }
    // Canonical source stream: explicit paragraph elements are boundaries; BR
    // is a line break, not missing text; text whitespace is kept verbatim.
    let streamSafe=true;let roots=[];
    if(node.matches('p,li'))roots=[node];
    else {
     const paragraphs=[...node.children].filter(e=>e.matches('p,li'));
     if(paragraphs.length){
      if([...node.childNodes].some(c=>c.nodeType===Node.ELEMENT_NODE?!c.matches('p,li'):c.nodeType===Node.TEXT_NODE&&Boolean(c.data.trim())))streamSafe=false;
      roots=paragraphs;
     } else {roots=[node];if(node.querySelector('p,li'))streamSafe=false;}
    }
    const stream=roots.map((root,paragraph)=>{
     let text='';
     const walk=n=>{
      if(n.nodeType===Node.TEXT_NODE){
       const record=nodeMap.get(n);if(!record){streamSafe=false;return;}
       record.paragraph=paragraph;record.start=text.length;record.end=text.length+n.data.length;
       if(!n.data.trim()&&(record.hiddenLayout||record.zeroFont))streamSafe=false;
       if(/[\r\n]/.test(n.data)&&!['pre','pre-wrap','pre-line','break-spaces'].includes(getComputedStyle(n.parentElement).whiteSpace))streamSafe=false;
       text+=n.data;return;
      }
      if(n.nodeType!==Node.ELEMENT_NODE)return;
      if(n.matches('script,style,svg,video,audio')||(n!==root&&n.matches('p,li'))){streamSafe=false;return;}
      if(n.tagName==='BR'){
       for(let e=n;e;e=e.parentElement){const c=getComputedStyle(e);if(c.display==='none'||c.visibility!=='visible'||c.contentVisibility==='hidden'||Number(c.opacity)<=.001)streamSafe=false;if(e===slide)break;}
       text+='\n';return;
      }
      for(const child of n.childNodes)walk(child);
     };walk(root);return text;
    });
    return {invisible,clipped,uncertain,nodes,stream,streamSafe,markerCount:node.querySelectorAll('[data-source-alpha-run]').length};
   };
   const markers=node=>[...(node.matches('li')?[node]:[]),...node.querySelectorAll('li')].map(li=>{
    const css=getComputedStyle(li),m=getComputedStyle(li,'::marker'),before=getComputedStyle(li,'::before');
    const rect=li.getBoundingClientRect();let left=frame.left,right=frame.right;
    for(let el=li;el&&el!==slide;el=el.parentElement){const c=getComputedStyle(el);if(['hidden','clip','scroll','auto'].includes(c.overflowX)){const r=el.getBoundingClientRect();left=Math.max(left,r.left);right=Math.min(right,r.right)}}
    const gap=css.direction==='rtl'?right-rect.right:rect.left-left;
    const markerClipped=css.listStylePosition==='outside'&&gap<=0;
    const markerClipRisk=css.listStylePosition==='outside'&&gap>0&&gap<parseFloat(css.fontSize)*1.5;
    return {markerClipped,markerClipRisk,display:css.display,listStyleType:css.listStyleType,listStyleImage:css.listStyleImage,
      content:m.content,markerColor:m.color,markerFontSize:m.fontSize,markerVisibility:m.visibility,markerOpacity:m.opacity,
      customBefore:before.content,customBeforeColor:before.color,customBeforeFontSize:before.fontSize,customBeforeVisibility:before.visibility,customBeforeOpacity:before.opacity};
   });
   // textContent joins words across BR and paragraph elements; preserve visible text boundaries.
   const cellText=root=>{const blocks=new Set(['P','DIV','LI','UL','OL','SECTION','ARTICLE','BLOCKQUOTE']);const walk=node=>{if(node.nodeType===Node.TEXT_NODE)return node.data;if(node.nodeType!==Node.ELEMENT_NODE)return '';if(node.tagName==='BR')return ' ';const body=[...node.childNodes].map(walk).join('');return blocks.has(node.tagName)?' '+body+' ':body;};return [...root.childNodes].map(walk).join('');};
   const targets=[...slide.querySelectorAll('.gd-content [data-source-id]')].map(node=>{
    const walker=document.createTreeWalker(node,NodeFilter.SHOW_TEXT);let bold='',italic='';
    while(walker.nextNode()){const text=walker.currentNode,parent=text.parentElement;if(!parent)continue;const style=getComputedStyle(parent);if(Number(style.fontWeight)>=600)bold+=text.data;if(/italic|oblique/.test(style.fontStyle))italic+=text.data;}
    let shape=null;if(shapeIds.includes(node.dataset.sourceId)){
    const content=slide.querySelector(':scope>.slide-inner>.gd-content'),r=node.getBoundingClientRect(),cs=getComputedStyle(node),sx=frame.width/1920,sy=frame.height/1080;let shapeSafe=sx>0&&sy>0&&Math.abs(sx-sy)<.001;
    for(let el=node;el&&el!==content;el=el.parentElement){const c=getComputedStyle(el);const neutralScale=c.scale==='none'||/^(?:1(?:\s+1){0,2})$/.test(c.scale);const neutralRotate=c.rotate==='none'||c.rotate==='0deg';const neutralTranslate=c.translate==='none'||/^(?:0px(?:\s+0px){0,2})$/.test(c.translate);if(c.display==='none'||c.visibility!=='visible'||c.contentVisibility==='hidden'||Number(c.opacity)!==1||c.transform!=='none'||!neutralScale||!neutralRotate||!neutralTranslate||c.filter!=='none'||c.backdropFilter!=='none'||c.clipPath!=='none'||c.clip!=='auto'||c.maskImage!=='none'||c.mixBlendMode!=='normal')shapeSafe=false;if(el!==node&&(['hidden','clip','auto','scroll'].includes(c.overflowX)||['hidden','clip','auto','scroll'].includes(c.overflowY)))shapeSafe=false;}
    const border=['Top','Right','Bottom','Left'].map(side=>({width:parseFloat(cs['border'+side+'Width']),style:cs['border'+side+'Style'],color:cs['border'+side+'Color']}));
    const radius=['TopLeft','TopRight','BottomRight','BottomLeft'].map(side=>cs['border'+side+'Radius']);
    const pseudo=['::before','::after'].some(p=>!['none','normal',''].includes(getComputedStyle(node,p).content));
    shape={safe:shapeSafe&&!pseudo&&r.width>0&&r.height>0&&cs.backgroundImage==='none'&&cs.backgroundBlendMode==='normal'&&cs.borderImageSource==='none'&&cs.boxShadow==='none'&&cs.outlineStyle==='none'&&r.left>=frame.left-1&&r.right<=frame.right+1&&r.top>=frame.top-1&&r.bottom<=frame.bottom+1,box:[(r.left-frame.left)/sx,(r.top-frame.top)/sy,r.width/sx,r.height/sy],background:cs.backgroundColor,border,radius};
    if(gradientSvgs[node.dataset.sourceId]){
     const sid=node.dataset.sourceId,svgs=[...slide.querySelectorAll('[data-source-shape-for]')].filter(e=>e.getAttribute('data-source-shape-for')===sid),svg=svgs[0],template=document.createElement('template');template.innerHTML=gradientSvgs[sid];const expected=template.content.firstElementChild,copy=svg?.cloneNode(true);copy?.removeAttribute('style');
     let safe=svgs.length===1&&svg?.tagName.toLowerCase()==='svg'&&svg.parentElement===node.parentElement&&svg.nextElementSibling===node&&copy?.isEqualNode(expected);
     const goodStyle=el=>{const c=getComputedStyle(el);return c.display!=='none'&&c.visibility==='visible'&&c.contentVisibility!=='hidden'&&Number(c.opacity)===1&&c.transform==='none'&&c.scale==='none'&&c.rotate==='none'&&c.translate==='none'&&c.filter==='none'&&c.clipPath==='none'&&c.maskImage==='none'&&c.mixBlendMode==='normal'&&c.animationName==='none'&&c.transitionDuration.split(',').every(x=>parseFloat(x)===0)};
     if(svg){const s=getComputedStyle(svg),sr=svg.getBoundingClientRect(),rect=svg.querySelector('rect'),gradient=svg.querySelector('radialGradient'),stops=[...svg.querySelectorAll('stop')],rectStyle=rect&&getComputedStyle(rect),gid=gradient?.id;
      safe=!!safe&&goodStyle(svg)&&s.position==='absolute'&&s.pointerEvents==='none'&&s.overflow==='visible'&&s.zIndex==='auto'&&cs.zIndex==='auto'&&[...svg.querySelectorAll('*')].every(goodStyle)&&!!gid&&document.querySelectorAll(`[id="${CSS.escape(gid)}"]`).length===1;
      const rgb=value=>{const m=value?.match(/^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d.]+))?\s*\)$/i);return m?[+m[1],+m[2],+m[3],m[4]===undefined?1:+m[4]]:null};const near=(a,b)=>Number.isFinite(a)&&Math.abs(a-b)<.00001;
      const stroke=rectStyle&&rgb(rectStyle.stroke),hex=rect?.getAttribute('stroke')?.match(/^#([0-9a-f]{6})$/i)?.[1],expectedStroke=hex&&[0,2,4].map(i=>parseInt(hex.slice(i,i+2),16));
      safe=!!safe&&!!rectStyle&&!!stroke&&!!expectedStroke&&expectedStroke.every((n,i)=>n===stroke[i])&&rectStyle.fill.replace(/["']/g,'')===`url(#${gid})`&&near(+rectStyle.strokeOpacity,+rect.getAttribute('stroke-opacity'))&&near(parseFloat(rectStyle.strokeWidth),+rect.getAttribute('stroke-width'));
      const geometryNear=(value,attr)=>Number.isFinite(parseFloat(value))&&Math.abs(parseFloat(value)-Number(attr))<=10;
      safe=!!safe&&geometryNear(rectStyle.x,rect.getAttribute('x'))&&geometryNear(rectStyle.y,rect.getAttribute('y'))&&geometryNear(rectStyle.width,rect.getAttribute('width'))&&geometryNear(rectStyle.height,rect.getAttribute('height'))&&geometryNear(rectStyle.rx,rect.getAttribute('rx'))&&rectStyle.ry==='auto'&&rectStyle.fillOpacity==='1'&&rectStyle.strokeDasharray==='none'&&parseFloat(rectStyle.strokeDashoffset)===0&&rectStyle.strokeLinecap==='butt'&&rectStyle.strokeLinejoin==='miter'&&rectStyle.vectorEffect==='none'&&rectStyle.paintOrder==='normal'&&getComputedStyle(gradient).colorInterpolation==='srgb';
      safe=!!safe&&stops.length>0&&stops.every(stop=>{const c=getComputedStyle(stop),a=rgb(stop.getAttribute('stop-color')),b=rgb(c.stopColor);return a&&b&&a.every((x,i)=>x===b[i])&&near(+c.stopOpacity,+stop.getAttribute('stop-opacity'))});
      shape.gradient={safe,box:[(sr.left-frame.left)/sx,(sr.top-frame.top)/sy,sr.width/sx,sr.height/sy],svgCount:svgs.length};
     }else shape.gradient={safe:false,svgCount:svgs.length};
    }}
    return {id:node.dataset.sourceId,editable:Boolean(node.hasAttribute('data-eid') || node.querySelector('[data-eid]')),bold,italic,shape,visibility:textEvidence(node),markers:markers(node),links:[node,...node.querySelectorAll('a[href]')].filter(n=>n.matches('a[href]')).map(n=>({text:n.textContent,href:n.getAttribute('href')})),rows:node.tagName==='TABLE'?[...node.querySelectorAll('tr')].map(row=>[...row.children].filter(c=>['TD','TH'].includes(c.tagName)).map(c=>cellText(c))):null};
   });
   return {id,html:slide.querySelector('.gd-content')?.innerHTML ?? '',targets,chrome:[...slide.querySelectorAll('.gd-export-meta [data-gd-chrome-source]')].map(n=>({id:n.dataset.gdChromeSource,role:n.dataset.gdChromeRole,text:n.textContent,visible:n.checkVisibility({visibilityProperty:true,opacityProperty:true}),header:slide.dataset.gdHeader,bodyCount:slide.querySelectorAll('.gd-content [data-source-id="'+CSS.escape(n.dataset.gdChromeSource)+'"]').length})),number:SalesKitUI.getState().order.indexOf(id)+1};
  },{id:slideId,shapeIds,gradientSvgs}));
 }

 const byId=new Map(rendered.map(s=>[s.id,s.html]));
 const domProject={...project,slides:project.slides.filter(s=>byId.has(s.id)).map(s=>({...s,html:byId.get(s.id)}))};
 await fs.writeFile(temp,JSON.stringify(domProject));
 const result=spawnSync('python3',[path.join(here,'check_source_inventory.py'),inventory,temp,...inventoryArgs],{encoding:'utf8',maxBuffer:64*1024*1024});
 if(!result.stdout)throw Error(result.stderr||'Source audit failed without report');
 const report=JSON.parse(result.stdout);
 const source=JSON.parse(await fs.readFile(inventory,'utf8'));
 if(alphaProof?.status==='fail')report.issues.push({code:'source-alpha-unverified',reason:alphaProof.error});
 report.sourceAlphaManifestSha256=alphaProof?.manifestSha256??null;

 if(offCanvasArg>=0){
  // The project is independent evidence as well as the selected rendered DOM:
  // a hidden or excluded target in the project cannot become an omission.
  const projectCheck=spawnSync('python3',[path.join(here,'check_source_inventory.py'),inventory,projectFile,...inventoryArgs],{encoding:'utf8',maxBuffer:64*1024*1024});
  if(!projectCheck.stdout)throw Error(projectCheck.stderr||'Off-canvas project check failed without report');
  const projectReport=JSON.parse(projectCheck.stdout);
  const conflicts=projectReport.issues.filter(x=>x.code.startsWith('off-canvas-disposition-'));
  for(const conflict of conflicts){
   if(!report.issues.some(x=>x.code===conflict.code&&x.slide===conflict.slide&&x.sourceId===conflict.sourceId))report.issues.push({...conflict,evidence:'project'});
  }
  for(const raw of rawOffCanvasTargets){
   const entry=offCanvasEntries.find(x=>x.sourceId===raw.sourceId);
   if(entry&&!report.issues.some(x=>x.code==='off-canvas-disposition-unverified'&&x.slide===entry.slide&&x.sourceId===entry.sourceId))
    report.issues.push({code:'off-canvas-disposition-unverified',slide:entry.slide,sourceId:entry.sourceId,evidence:'saved-html',reason:'source ID is present in saved HTML, including excluded slides',targetTag:raw.tag});
  }
  const bad=new Set(report.issues.filter(x=>x.code.startsWith('off-canvas-disposition-')).map(x=>JSON.stringify([x.slide,x.sourceId])));
  report.observations=report.observations.filter(x=>x.code!=='source-off-canvas-reviewed'||!bad.has(JSON.stringify([x.slide,x.sourceId])));
 }
 const transformArg=args.indexOf('--transformations');
 const transforms=transformArg<0?[]:JSON.parse(await fs.readFile(args[transformArg+1],'utf8')).transformations ?? [];
 const renderedBySlide=new Map(rendered.map(s=>[s.id,s]));
 for(const slide of source.slides) {
  const destination=project.slides.find(s=>s.sourceNumber===slide.sourceNumber);
  const dom=renderedBySlide.get(destination?.id);
  if(!dom)continue;
  for(const block of slide.blocks ?? []) {
   if(!['text','table'].includes(block.kind))continue;
   const chrome=chromeProof.find(e=>e.slide===slide.sourceNumber&&e.sourceId===block.id);
   if(chrome){const matches=dom.chrome.filter(x=>x.id===block.id&&x.role===chrome.role);const value=matches[0];
    if(matches.length!==1||value.bodyCount||value.header==='none'||(chrome.role==='page-number'&&(!value.visible||value.text!==String(dom.number))))report.issues.push({code:'source-chrome-runtime',slide:slide.sourceNumber,sourceId:block.id});
    else report.observations.push({code:'source-chrome-reviewed',slide:slide.sourceNumber,sourceId:block.id,role:chrome.role,originalText:chrome.originalText,reason:chrome.reason});
    continue;
   }
   const targetId=transforms.find(t=>t.slide===slide.sourceNumber && t.sourceId===block.id)?.targetId ?? block.id;
   const matches=dom.targets.filter(t=>t.id===targetId);
   if(matches.length===1 && !matches[0].editable)report.issues.push({code:'missing-editor-binding',slide:slide.sourceNumber,sourceId:block.id,targetId});
   if(matches.length===1) {
    const v=matches[0].visibility;
    const proofs=(alphaProof?.observations??[]).filter(x=>x.slide===slide.sourceNumber&&x.sourceId===block.id);
    let alphaNodes=[];
    if(proofs.length){
     const paras=block.paragraphs??[];
     const expected=paras.map(p=>(p.runs??[]).map(r=>r.text??'').join(''));
     let valid=v.streamSafe && JSON.stringify(v.stream)===JSON.stringify(expected) && v.markerCount===proofs.length && !transforms.some(t=>t.slide===slide.sourceNumber&&t.sourceId===block.id);const shapeDiagnostics=[];
     for(const proof of proofs){
      let start=0;for(let i=0;i<proof.runIndex;i++)start+=(paras[proof.paragraphIndex].runs[i].text??'').length;
      const ms=v.nodes.filter(x=>x.marker===`${proof.paragraphIndex}:${proof.runIndex}`);
      if(ms.length!==1 || ms[0].paragraph!==proof.paragraphIndex || ms[0].start!==start || ms[0].end!==start+proof.sourceText.length || ms[0].text!==proof.sourceText || !ms[0].onlyColor || ms[0].clipped || ms[0].uncertain)valid=false;
      else alphaNodes.push(ms[0]);
      if(proof.shapeProof){
       const shape=matches[0].shape;
       if(proof.shapeProof.kind==='source-gradient-svg-v1'){
        const src=proof.shapeProof.sourceGradient,[x,y,w,h]=src.box_emu,[cw,ch]=src.canvas_emu,box=[x/cw*1920,y/ch*1080,w/cw*1920,h/ch*1080],near=(a,b)=>Number.isFinite(a)&&Math.abs(a-b)<=1.5;
        const bg=shape.background.replace(/\s/g,'');const validShape=proof.shapeProof.htmlSha256===inputHtmlSha&&shape.safe&&shape.gradient?.safe&&['rgba(0,0,0,0)','transparent'].includes(bg)&&shape.border.every(b=>b.width===0||b.style==='none')&&!shape.box.some((x,i)=>!near(x,box[i]))&&!shape.gradient.box.some((x,i)=>!near(x,box[i]));
        if(!validShape){valid=false;shapeDiagnostics.push({actual:shape,expectedBox:box,htmlHashMatches:proof.shapeProof.htmlSha256===inputHtmlSha});}
        continue;
       }
       const src=proof.shapeProof.sourceAppearance,b=src.geometryEMU,c=src.canvasEMU;
       const expectedBox=[b.x/c.width*1920,b.y/c.height*1080,b.width/c.width*1920,b.height/c.height*1080],expectedRadius=src.cornerRadiusEMU/c.width*1920;
       const parseColor=value=>{const m=value.match(/^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d.]+))?\s*\)$/i);return m?[+m[1],+m[2],+m[3],m[4]===undefined?1:+m[4]]:null};const actual=parseColor(shape.background);
       const expectedColor=src.fillRGBA??[0,0,0,0],near=(a,b,t)=>Number.isFinite(a)&&Math.abs(a-b)<=t;
       const lineBad=src.line==='none'?shape.border.some(x=>x.width>0&&x.style!=='none'&&x.style!=='hidden'):shape.border.some(x=>{const rgba=parseColor(x.color),width=src.line.widthEMU/c.width*1920;return x.style!=='solid'||!near(x.width,width,.5)||!rgba||rgba.some((v,i)=>!near(v,src.line.rgba[i],i===3?.005:1))});
       const shapeValid=proof.shapeProof.htmlSha256===inputHtmlSha&&shape.safe&&!shape.box.some((v,i)=>!near(v,expectedBox[i],1.5))&&!!actual&&!actual.some((v,i)=>!near(v,expectedColor[i],i===3?.005:1))&&!lineBad&&!shape.radius.some(v=>!/^\d+(?:\.\d+)?px$/.test(v)||!near(parseFloat(v),expectedRadius,1.5));
       if(!shapeValid){valid=false;shapeDiagnostics.push({actual:shape,expectedBox,expectedColor,expectedRadius,htmlHashMatches:proof.shapeProof.htmlSha256===inputHtmlSha});}
      }
     }
     if(valid){const shaped=proofs.find(x=>x.shapeProof);if(shaped)report.observations.push({code:'source-shape-appearance-reviewed',slide:shaped.slide,sourceId:shaped.sourceId,shape:shaped.shapeProof,review:'Computed geometry and paint matched narrowly supported source properties; screenshot provenance, occlusion and visual fidelity remain review.'});for(const proof of proofs)report.observations.push({...proof,code:'source-alpha-reviewed'});}
     else {alphaNodes=[];report.issues.push({code:'source-alpha-unverified',slide:slide.sourceNumber,sourceId:block.id,reason:'run mapping, text order, marker, transparent rendering or source shape is ambiguous',...(shapeDiagnostics.length?{shapeDiagnostics}:{}),streamSafe:v.streamSafe,streamMatches:JSON.stringify(v.stream)===JSON.stringify(expected),markerCount:v.markerCount,expectedMarkerCount:proofs.length});}
    }
    if(v.nodes.some(n=>n.invisible&&!alphaNodes.includes(n)))report.issues.push({code:'source-text-invisible',slide:slide.sourceNumber,sourceId:block.id,targetId});
    if(v.clipped)report.issues.push({code:'source-text-clipped',slide:slide.sourceNumber,sourceId:block.id,targetId});
    if(v.uncertain)report.observations.push({code:'source-text-visibility-review',slide:slide.sourceNumber,sourceId:block.id,targetId,reason:'clip-path or mask requires visual review'});
   }
   if(matches.length===1 && block.kind==='text') {
    const target=matches[0], normalized=s=>String(s??'').replace(/\s+/gu,' ').trim();
    const listKind=para=>{
     const e=para.effectiveList;
     if(e?.status==='resolved')return e.kind==='ul'||e.kind==='ol'?e.kind:null;
     const xml=para.paragraphPropertiesXml??'';
     if(/<(?:[\w-]+:)?buAutoNum\b/.test(xml))return 'ol';
     if(/<(?:[\w-]+:)?bu(?:Char|Blip)\b/.test(xml))return 'ul';
     return null;
    };
    const expected=(block.paragraphs??[]).filter(p=>listKind(p));
    const approval=(project.deliveryReview?.customListMarkers??[]).find(x=>x.slide===destination.id&&x.sourceId===targetId&&x.approved===true&&typeof x.reason==='string'&&x.reason.trim());
    const empty=value=>['none','normal','""',"''",''].includes(String(value??'').trim());
    const transparent=value=>/^(transparent|rgba\([^)]*[,\s/]\s*0(?:\.0+)?\s*\))$/i.test(String(value??'').trim());
    const orderedTypes=new Set(['decimal','decimal-leading-zero','lower-alpha','upper-alpha','lower-latin','upper-latin','lower-roman','upper-roman']);
    for(const [i,para] of expected.entries()){
     const marker=target.markers[i];if(!marker)continue; // Missing li is handled by structural audit.
     const listType=marker.listStyleType, kind=listKind(para), markerEmpty=marker.content==='none'||marker.content==='""'||marker.content==="''";
     const suppressed=!marker.display.includes('list-item')||markerEmpty||marker.markerVisibility==='hidden'||+marker.markerOpacity===0||parseFloat(marker.markerFontSize)===0||transparent(marker.markerColor)||(listType==='none'&&marker.listStyleImage==='none'&&marker.content==='normal');
     if(!suppressed && !target.visibility.invisible && marker.markerClipped)report.issues.push({code:'list-marker-clipped',slide:slide.sourceNumber,sourceId:block.id,paragraph:i});
     else if(!suppressed && !target.visibility.invisible && marker.markerClipRisk)report.observations.push({code:'list-marker-visibility-review',slide:slide.sourceNumber,sourceId:block.id,paragraph:i,reason:'outside marker near clipping boundary'});
     const customBefore=!empty(marker.customBefore)&&marker.customBeforeVisibility!=='hidden'&&+marker.customBeforeOpacity!==0&&parseFloat(marker.customBeforeFontSize)!==0&&!transparent(marker.customBeforeColor);
     if(suppressed){
      if(customBefore && approval)report.observations.push({code:'custom-list-marker-review',slide:slide.sourceNumber,sourceId:block.id,paragraph:i,reason:approval.reason});
      else report.issues.push({code:customBefore?'custom-list-marker-unapproved':'list-marker-missing',slide:slide.sourceNumber,sourceId:block.id,paragraph:i});
     }else if(marker.listStyleImage!=='none'||(marker.content!=='normal'&&!markerEmpty)){
      if(approval)report.observations.push({code:'custom-list-marker-review',slide:slide.sourceNumber,sourceId:block.id,paragraph:i,reason:approval.reason});
      else report.issues.push({code:'custom-list-marker-unapproved',slide:slide.sourceNumber,sourceId:block.id,paragraph:i});
     }else if(kind==='ol' && (()=>{const style=para.effectiveList?.attributes?.type ?? /buAutoNum\b[^>]*\btype=["']([^"']+)["']/.exec(para.paragraphPropertiesXml??'')?.[1];const map={arabicPeriod:['decimal'],alphaLcPeriod:['lower-alpha','lower-latin'],alphaUcPeriod:['upper-alpha','upper-latin'],romanLcPeriod:['lower-roman'],romanUcPeriod:['upper-roman']};return style && map[style] && !map[style].includes(listType);})()){
      report.issues.push({code:'list-marker-type-mismatch',slide:slide.sourceNumber,sourceId:block.id,paragraph:i,expected:para.effectiveList?.attributes?.type??'source numbering',actual:listType});
     }else if((kind==='ol'&&!orderedTypes.has(listType))||(kind==='ul'&&orderedTypes.has(listType))){
      report.issues.push({code:'list-marker-type-mismatch',slide:slide.sourceNumber,sourceId:block.id,paragraph:i,expected:kind,actual:listType});
     }
    }
    for(const para of block.paragraphs??[])for(const run of para.runs??[]) {
     const text=normalized(run.text);if(!text)continue;
     for(const [key,field] of [['bold','bold'],['italic','italic']])if(run[key] && !normalized(target[field]).includes(text))report.issues.push({code:'inline-format-mismatch',slide:slide.sourceNumber,sourceId:block.id,feature:key,text});
     if(run.link && !target.links.some(a=>a.href===run.link && normalized(a.text).includes(text)))report.issues.push({code:'link-mismatch',slide:slide.sourceNumber,sourceId:block.id,href:run.link,text});
    }
   }
   if(matches.length===1 && block.kind==='table' && matches[0].rows) {
    const norm=s=>String(s??'').replace(/\s+/gu,' ').trim();
    const expected=(block.rows??[]).map(row=>row.map(cell=>norm(cell.map(p=>p.text).join(' '))));
    const actual=matches[0].rows.map(row=>row.map(norm));
    if(JSON.stringify(expected)!==JSON.stringify(actual))report.issues.push({code:'table-cell-structure-mismatch',slide:slide.sourceNumber,sourceId:block.id});
   }
  }
 }
 if(alphaProof?.observations){
  for(const proof of alphaProof.observations)if(!report.observations.some(x=>x.code==='source-alpha-reviewed'&&x.slide===proof.slide&&x.sourceId===proof.sourceId&&x.paragraphIndex===proof.paragraphIndex&&x.runIndex===proof.runIndex))
   report.issues.push({code:'source-alpha-unmatched',slide:proof.slide,sourceId:proof.sourceId,paragraphIndex:proof.paragraphIndex,runIndex:proof.runIndex});
 }
 if(report.issues.length)report.status=report.mode==='editable'?'fail':'review';
 else if(report.observations.length)report.status='review';
 report.evidence='rendered DOM';
 report.htmlSha256=createHash('sha256').update(await fs.readFile(html)).digest('hex');
 const contentFailure=report.issues.some(x=>['missing-slide','missing-editable-target','ambiguous-target','text-mismatch','transformation-precondition-mismatch','link-mismatch','table-cell-structure-mismatch','source-text-invisible','source-text-clipped','off-canvas-disposition-unverified','off-canvas-disposition-unmatched','source-alpha-unverified','source-alpha-unmatched'].includes(x.code));
 const structureFailure=report.issues.some(x=>/structure|paragraph|numbering|inline-format|link-mismatch|list-marker/.test(x.code));
 report.acceptance={sourceHash:report.sourceHashVerified?'pass':'not_checked',content:contentFailure?'fail':report.observations.length?'review':'pass',structure:structureFailure?'fail':'review',editability:report.issues.some(x=>/missing-slide|missing-editable|missing-editor|ambiguous-target/.test(x.code))?'fail':'review',visual:'not_checked',shell:'not_checked',media:'not_checked',portability:'not_checked'};
 report.limitations=['Static export frames are inspected; occlusion by other layers, contrast, arbitrary masks, actual edit/undo, save/reopen, fonts and visual fidelity require separate checks.'];
 console.log(JSON.stringify(report,null,2));
 process.exitCode=report.status==='fail'?1:(result.status === 2 ? 2 : 0);
} finally { await browser.close();await fs.rm(temp,{force:true}); }
