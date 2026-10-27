// Browser-side scene capture. Native primitives are retained; complex paint is
// rasterized per object, never by flattening the slide.
export function installSceneCapture(){
 const root=document.querySelector('[data-export-current]'),origin=root.getBoundingClientRect(),items=[],warnings=[];
 const candidates=[];
 for(const [ruleIndex,rule] of (window.__HTML_EXPORT_GROUP_RULES||[]).entries()){
  if(!rule.slides.includes(Number(root.dataset.exportNumber)))continue;
  const es=[...root.querySelectorAll(rule.selector)];
  if(es.length!==rule.expected)throw Error(`Group selector ${rule.selector}: expected ${rule.expected}, got ${es.length}`);
  es.forEach((element,i)=>candidates.push({element,id:`group-${ruleIndex+1}-${i+1}`,name:rule.name+(es.length>1?' '+(i+1):''),selector:rule.selector,members:[]}));
 }
 function emit(e,item){const element=e.nodeType===3?e.parentElement:e;item.groupIds=candidates.filter(g=>g.element.contains(element)).map(g=>g.id);items.push(item);}
 let sequence=0;
 const rect=r=>({x:r.x-origin.x,y:r.y-origin.y,w:r.width,h:r.height});
 const visible=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&+s.opacity!==0&&(r.width>0&&r.height>0||e.children.length>0||((r.width>0||r.height>0)&&parseFloat(s.strokeWidth)>0&&s.stroke!=='none'));};
 const opacity=e=>{let a=1;for(let p=e;p;p=p.parentElement){a*=+getComputedStyle(p).opacity;if(p===root)break;}return a;};
 function id(e){return e.dataset.exportObjectId??=(++sequence)+'';}
 const paintProps=['fill','fill-opacity','stroke','stroke-opacity','stroke-width','stroke-dasharray','stroke-linecap','stroke-linejoin','color','opacity','font-family','font-size','font-weight','font-style','letter-spacing','text-anchor','dominant-baseline','paint-order','filter','clip-path','mask','stop-color','stop-opacity','flood-color','flood-opacity'];
 function scopedSvg(e){
  const r=e.getBoundingClientRect(),svg=document.createElementNS('http://www.w3.org/2000/svg','svg'),defs=document.createElementNS(svg.namespaceURI,'defs');
  const pad=getComputedStyle(e).filter!=='none'?40:0;
  svg.setAttribute('xmlns',svg.namespaceURI);svg.setAttribute('width',r.width+pad*2);svg.setAttribute('height',r.height+pad*2);svg.setAttribute('viewBox',`${r.x-pad} ${r.y-pad} ${r.width+pad*2} ${r.height+pad*2}`);svg.append(defs);
  function freeze(a,b){const aa=[a,...a.querySelectorAll('*')],bb=[b,...b.querySelectorAll('*')];for(let i=0;i<aa.length;i++){const s=getComputedStyle(aa[i]);for(const k of paintProps){let v=s.getPropertyValue(k);if(v)v=v.replace(/url\(["']?[^)'"#]*#([^)'"\s]+)["']?\)/g,'url(#$1)');if(v)bb[i].setAttribute(k,v);}bb[i].removeAttribute('class');bb[i].removeAttribute('style');}}
  const copy=e.cloneNode(true);freeze(e,copy);copy.removeAttribute('opacity');
  const m=e.parentElement.getScreenCTM?.()||new DOMMatrix();const g=document.createElementNS(svg.namespaceURI,'g');g.setAttribute('transform',`matrix(${m.a} ${m.b} ${m.c} ${m.d} ${m.e} ${m.f})`);g.append(copy);svg.append(g);
  const owner=e.ownerSVGElement,done=new Set();
  for(let pass=0;pass<20;pass++){
   const refs=new Set();for(const n of [svg,...svg.querySelectorAll('*')])for(const a of n.attributes){for(const x of a.value.matchAll(/url\(#([^)]+)\)/g))refs.add(x[1]);if(['href','xlink:href'].includes(a.name)&&a.value.startsWith('#'))refs.add(a.value.slice(1));}
   let changed=false;for(const ref of refs){if(done.has(ref)||svg.querySelector('[id="'+CSS.escape(ref)+'"]'))continue;const original=owner.querySelector('[id="'+CSS.escape(ref)+'"]')||document.getElementById(ref);if(!original){warnings.push({type:'missing-svg-resource',ref});continue;}done.add(ref);const c=original.cloneNode(true);freeze(original,c);defs.append(c);changed=true;}if(!changed)break;
  }
  return {svg:new XMLSerializer().serializeToString(svg),x:r.x-origin.x-pad,y:r.y-origin.y-pad,w:r.width+pad*2,h:r.height+pad*2};
 }
 function textSvg(e){
  const cs=getComputedStyle(e),r=e.getBoundingClientRect(),matrix=e.getScreenCTM(),n=e.getNumberOfChars(),lines=[];
  // SVG indexes address rendered characters, while DOM textContent can contain
  // indentation/newline nodes omitted by SVG layout. Character text is obtained
  // from leaf tspans, normalizing only according to xml:space/white-space.
  let raw=e.textContent;if(!e.closest('[xml\\:space="preserve"]')&&!cs.whiteSpace.startsWith('pre'))raw=raw.replace(/[\t\r\n]/g,' ').replace(/ +/g,' ').trim();
  const chars=Array.from(raw);if(chars.length!==n)warnings.push({type:'svg-char-index',text:raw,dom:chars.length,rendered:n});
  for(let i=0;i<n;i++){
   const point=e.getStartPositionOfChar(i),extent=e.getExtentOfChar(i),p=new DOMPoint(point.x,point.y).matrixTransform(matrix);
   let l=lines.find(l=>Math.abs(l.baseline-p.y)<1.5);if(!l){l={baseline:p.y,left:p.x,right:p.x,tokens:[]};lines.push(l);}const a=new DOMPoint(extent.x,extent.y).matrixTransform(matrix),b=new DOMPoint(extent.x+extent.width,extent.y+extent.height).matrixTransform(matrix);
   l.left=Math.min(l.left,a.x);l.right=Math.max(l.right,b.x);l.tokens.push(chars[i]??'');
  }
  if(!lines.length)return null;lines.sort((a,b)=>a.baseline-b.baseline);const scale=Math.hypot(matrix.a,matrix.b),size=parseFloat(cs.fontSize)*scale,pitch=lines.length>1?lines[1].baseline-lines[0].baseline:size*1.2;
  const runs=lines.map((l,i)=>({text:l.tokens.join(''),font:cs.fontFamily,weight:parseInt(cs.fontWeight)||400,size,spacing:(parseFloat(cs.letterSpacing)||0)*scale,color:cs.fill,opacity:opacity(e)*Number(cs.fillOpacity),italic:cs.fontStyle==='italic',softBreakBefore:i>0}));
  const item={kind:'text',id:id(e),x:Math.min(...lines.map(l=>l.left))-origin.x,y:lines[0].baseline-origin.y-pitch*.75,w:Math.max(...lines.map(l=>l.right))-Math.min(...lines.map(l=>l.left))+2,h:r.height+size,lineHeight:pitch,align:'left',runs,source:'svg-text',expectedText:raw,lineCount:lines.length,baselines:lines.map(l=>l.baseline-origin.y)};
  item.isNumber=/^\d{1,2}$/.test(raw.trim())&&item.x<200&&item.y>=0&&item.y<140&&Number(raw.trim())===Number(root.dataset.exportNumber||root.dataset.slide);return item;
 }
 function emitMarkers(e){
  if(!e.getTotalLength)return;
  const css=getComputedStyle(e),length=e.getTotalLength();
  for(const side of ['start','end']){
   const ref=css[side==='start'?'markerStart':'markerEnd'].match(/#([^)'"\s]+)/)?.[1];
   const marker=ref&&document.getElementById(ref);if(!marker)continue;
   const end=side==='end',point=e.getPointAtLength(end?length:0),near=e.getPointAtLength(end?Math.max(0,length-.1):Math.min(length,.1));
   let angle=Math.atan2(end?point.y-near.y:near.y-point.y,end?point.x-near.x:near.x-point.x)*180/Math.PI;
   if(!end&&marker.getAttribute('orient')==='auto-start-reverse')angle+=180;
   const units=marker.getAttribute('markerUnits')==='userSpaceOnUse'?1:parseFloat(css.strokeWidth),vb=marker.viewBox.baseVal;
   const matrix=e.getScreenCTM().translate(point.x,point.y).rotate(angle).scale(units*marker.markerWidth.baseVal.value/vb.width,units*marker.markerHeight.baseVal.value/vb.height).translate(-marker.refX.baseVal.value,-marker.refY.baseVal.value);
   for(const path of marker.querySelectorAll('path')){
    const box=path.getBBox(),points=[[box.x,box.y],[box.x+box.width,box.y],[box.x,box.y+box.height],[box.x+box.width,box.y+box.height]].map(([x,y])=>new DOMPoint(x,y).matrixTransform(matrix)),style=getComputedStyle(path),x=Math.min(...points.map(p=>p.x)),y=Math.min(...points.map(p=>p.y));
    emit(e,{kind:'shape',id:id(e)+'-marker-'+side,tag:'path',x:x-origin.x,y:y-origin.y,w:Math.max(...points.map(p=>p.x))-x,h:Math.max(...points.map(p=>p.y))-y,d:path.getAttribute('d'),matrix:[matrix.a,matrix.b,matrix.c,matrix.d,matrix.e-origin.x,matrix.f-origin.y],fill:style.fill,stroke:style.stroke,strokeWidth:parseFloat(style.strokeWidth)||0,opacity:opacity(e)});
   }
  }
 }
 function svgWalk(e){
  if(['defs','clipPath','mask','filter','pattern','linearGradient','radialGradient','stop','title','desc'].includes(e.tagName)||!visible(e))return;
  const tag=e.tagName,cs=getComputedStyle(e),r=e.getBoundingClientRect(),box=rect(r),alpha=opacity(e);
  if(tag==='text'){const t=textSvg(e);if(t)emit(e,t);return;}
  if(['svg','g','a'].includes(tag)){
   if(cs.filter!=='none'||(cs.mask!=='none'&&cs.maskImage!=='none')){if(!e.querySelector('text')){emit(e,{kind:'svg-image',id:id(e),...scopedSvg(e),opacity:alpha});return;}}
   for(const child of e.children)svgWalk(child);return;
  }
  const flat=!cs.fill.startsWith('url(')&&!cs.stroke.startsWith('url(')&&cs.filter==='none'&&cs.maskImage==='none';
  if(['rect','circle','ellipse','line','path','polygon','polyline'].includes(tag)&&flat){
   const item={kind:'shape',id:id(e),...box,tag,fill:cs.fill,fillOpacity:Number(cs.fillOpacity),stroke:cs.stroke,strokeOpacity:Number(cs.strokeOpacity),strokeWidth:parseFloat(cs.strokeWidth)||0,opacity:alpha,radius:parseFloat(e.getAttribute('rx'))||0};
   if(tag==='path'||tag==='polygon'||tag==='polyline'||tag==='line'){
    const m=e.getScreenCTM();
    // Keep SVG subpaths separate. Native DrawingML custom paths accept the same
    // commands after SVGPathElement normalization supplied by the browser API.
    if(tag==='path'){item.d=e.getAttribute('d');item.matrix=[m.a,m.b,m.c,m.d,m.e-origin.x,m.f-origin.y];}
    else if(tag==='line')item.points=[[+e.getAttribute('x1'),+e.getAttribute('y1')],[+e.getAttribute('x2'),+e.getAttribute('y2')]].map(([x,y])=>{const p=new DOMPoint(x,y).matrixTransform(m);return [p.x-origin.x,p.y-origin.y];});
    else item.points=[...e.points].map(v=>{const p=new DOMPoint(v.x,v.y).matrixTransform(m);return [p.x-origin.x,p.y-origin.y];});
   }
   emit(e,item);emitMarkers(e);return;
  }
  emit(e,{kind:'svg-image',id:id(e),...scopedSvg(e),opacity:alpha});
 }
 const seen=new Set();
 function htmlWalk(e){
  if(!visible(e)||['SCRIPT','STYLE','TEMPLATE'].includes(e.tagName))return;
  const cs=getComputedStyle(e),r=e.getBoundingClientRect(),box=rect(r),alpha=opacity(e),radius=parseFloat(cs.borderTopLeftRadius)||0;
  if(cs.backgroundImage!=='none')emit(e,{kind:'css-image',id:id(e),...box,opacity:alpha,props:Object.fromEntries(['backgroundImage','backgroundColor','backgroundSize','backgroundPosition','backgroundRepeat','backgroundBlendMode','borderRadius'].map(k=>[k,cs[k]]))});
  else if(cs.backgroundColor!=='rgba(0, 0, 0, 0)')emit(e,{kind:'shape',id:id(e)+'-fill',...box,tag:'rect',fill:cs.backgroundColor,radius,opacity:alpha});
  const bs=['Top','Right','Bottom','Left'].map(side=>({side,width:parseFloat(cs['border'+side+'Width'])||0,color:cs['border'+side+'Color']})).filter(b=>b.width>0);
  if(bs.length===4&&bs.every(b=>b.width===bs[0].width&&b.color===bs[0].color))emit(e,{kind:'shape',id:id(e)+'-border',...box,tag:'rect',fill:'none',stroke:bs[0].color,strokeWidth:bs[0].width,radius,opacity:alpha});
  else for(const b of bs){const p=b.side==='Top'?[[box.x,box.y],[box.x+box.w,box.y]]:b.side==='Bottom'?[[box.x,box.y+box.h],[box.x+box.w,box.y+box.h]]:b.side==='Left'?[[box.x,box.y],[box.x,box.y+box.h]]:[[box.x+box.w,box.y],[box.x+box.w,box.y+box.h]];emit(e,{kind:'shape',id:id(e)+'-'+b.side,...box,tag:'line',fill:'none',stroke:b.color,strokeWidth:b.width,points:p,opacity:alpha});}
  if(e.tagName.toLowerCase()==='svg'){svgWalk(e);return;}
  if(['IMG','VIDEO','CANVAS'].includes(e.tagName)){emit(e,{kind:'dom-image',id:id(e),...box,opacity:alpha,tag:e.tagName,src:e.currentSrc||e.src||e.poster,props:Object.fromEntries(['objectFit','objectPosition','borderRadius','filter','padding','borderWidth'].map(k=>[k,cs[k]]))});return;}
  // Outside disc markers are generated paint, absent from DOM text ranges.
  if(cs.display==='list-item'&&cs.listStyleType==='disc'){
   const textNode=[...e.childNodes].find(n=>n.nodeType===3&&n.textContent.trim());
   if(textNode){const m=window.SberSemanticText.forNode(textNode),size=parseFloat(cs.fontSize),d=size*.22;if(m)emit(e,{kind:'shape',id:id(e)+'-marker',tag:'circle',x:box.x-size*.55-d/2,y:m.baselines[0]-size*.35-d/2,w:d,h:d,fill:cs.color,opacity:alpha});}
  }
  const entries=[...e.childNodes].map((node,i)=>({node,i,z:node.nodeType===1?(parseInt(getComputedStyle(node).zIndex)||0):0}));
  for(const which of ['::before','::after']){const s=getComputedStyle(e,which);if(!['none','normal','""',"''"].includes(s.content)&&s.display!=='none')warnings.push({type:'pseudo-text',id:id(e),content:s.content});if(s.content==='""'&&s.position==='absolute'&&s.backgroundColor!=='rgba(0, 0, 0, 0)'){emit(e,{kind:'shape',id:id(e)+which,tag:'rect',x:box.x+(parseFloat(s.left)||0),y:box.y+(parseFloat(s.top)||0),w:parseFloat(s.width)||0,h:parseFloat(s.height)||0,radius:parseFloat(s.borderRadius)||0,fill:s.backgroundColor,opacity:alpha});}}
  entries.sort((a,b)=>a.z-b.z||a.i-b.i);
  for(const {node} of entries){if(node.nodeType===1)htmlWalk(node);else if(node.nodeType===3&&node.textContent.trim()){
   const m=window.SberSemanticText.forNode(node);if(m&&!seen.has(m.key)){seen.add(m.key);emit(window.SberSemanticText.ownerForNode(node)||e,{kind:'text',id:m.key,...m,expectedText:m.runs.map(r=>r.text).join(''),source:'html-text',isNumber:!!node.parentElement.closest('.slide-page')&&Number(m.runs.map(r=>r.text).join(''))===Number(root.dataset.exportNumber),numberAlign:node.parentElement.closest('.slide-page')?'right':undefined});}
  }}
 }
 htmlWalk(root);
 // The source HUD sits outside .slide; include only its persistent content,
 // excluding keyboard hints. Its counter is converted to a native field.
 const hud=document.querySelector('#hud');if(hud&&getComputedStyle(hud).display!=='none')for(const e of hud.querySelectorAll('.l,#cn,#ct')){
  if(!visible(e))continue;const cs=getComputedStyle(e),r=e.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(e);const tr=range.getBoundingClientRect(),size=parseFloat(cs.fontSize),ctx=document.createElement('canvas').getContext('2d');ctx.font=`${cs.fontWeight} ${size}px ${cs.fontFamily}`;const mt=ctx.measureText('Hg'),baseline=tr.top+mt.fontBoundingBoxAscent,pitch=mt.fontBoundingBoxAscent+mt.fontBoundingBoxDescent;
  emit(e,{kind:'text',id:'hud-'+e.id+'-'+e.className,...rect(r),x:tr.x-origin.x,y:baseline-origin.y-pitch*.75,w:tr.width+3,h:pitch+3,lineHeight:pitch,align:'left',source:'hud',isNumber:e.id==='cn',runs:[{text:e.textContent,font:cs.fontFamily,size,weight:parseInt(cs.fontWeight)||400,color:cs.color,spacing:parseFloat(cs.letterSpacing)||0,opacity:opacity(e)}],expectedText:e.textContent,lineCount:1,baselines:[baseline-origin.y]});
 }
 // Persistent HUD separators are text nodes outside semantic slide roots.
 if(hud)for(const e of hud.querySelectorAll('.r'))for(const node of e.childNodes){if(node.nodeType!==3||!node.textContent.trim())continue;const range=document.createRange();range.selectNodeContents(node);const r=range.getBoundingClientRect(),cs=getComputedStyle(e),size=parseFloat(cs.fontSize),ctx=document.createElement('canvas').getContext('2d');ctx.font=`${cs.fontWeight} ${size}px ${cs.fontFamily}`;const mt=ctx.measureText('Hg'),pitch=mt.fontBoundingBoxAscent+mt.fontBoundingBoxDescent;emit(e,{kind:'text',id:'hud-separator',...rect(r),y:r.top+mt.fontBoundingBoxAscent-origin.y-pitch*.75,h:pitch+3,lineHeight:pitch,align:'left',source:'hud',runs:[{text:node.textContent,font:cs.fontFamily,size,weight:parseInt(cs.fontWeight)||400,color:cs.color,spacing:parseFloat(cs.letterSpacing)||0,opacity:opacity(e)}],expectedText:node.textContent,lineCount:1});}
 // Independent visible text inventory: no use of emitted runs or font metrics.
 const inventory=[];const tw=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let node;
 while(node=tw.nextNode()){const e=node.parentElement;if(e.closest('script,style,defs,clipPath,mask,filter')||!node.textContent.trim())continue;const s=getComputedStyle(e);if(s.display==='none'||s.visibility==='hidden'||opacity(e)===0)continue;const range=document.createRange();range.selectNodeContents(node);if(![...range.getClientRects()].some(r=>r.width&&r.height))continue;let value=node.textContent;if(s.textTransform==='uppercase')value=value.toUpperCase();if(s.textTransform==='lowercase')value=value.toLowerCase();inventory.push({text:value,tag:e.tagName});}
 return {items,warnings,inventory,groups:candidates.map(({element,...g})=>({...g,members:items.filter(it=>it.groupIds.includes(g.id)).map(it=>it.id)})),rootBackground:getComputedStyle(root).backgroundColor};
}
