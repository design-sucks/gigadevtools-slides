// Browser DOM semantics, not reconstruction from arbitrary word coordinates.
export function installSemanticText(){
 const inline=new Set(['SPAN','BR','B','STRONG','EM','I','U','S','A','CODE','MARK','SMALL']);
 const cache=new WeakMap(),flowCache=new WeakMap();let sequence=0;
 const number=v=>parseFloat(v)||0,content=s=>['none','normal','""',"''"].includes(s)?'':s.replace(/^['"]|['"]$/g,'');
 function prefix(e){const s=getComputedStyle(e,'::before'),text=content(s.content);return /^[+−-]$/.test(text)&&s.position==='static'?{text,style:s}:null;}
 function flow(e){
  if(flowCache.has(e))return flowCache.get(e);
  const s=getComputedStyle(e),sign=prefix(e);
  let good=!['flex','inline-flex','grid','inline-grid'].includes(s.display)||(!!sign&&e.children.length===0);
  for(const child of e.children){
   const cs=getComputedStyle(child);if(cs.display==='none')continue;
   if(!inline.has(child.tagName)||!['inline','inline-block','contents'].includes(cs.display)||['absolute','fixed'].includes(cs.position)||cs.transform!=='none'||!['baseline','normal'].includes(cs.verticalAlign)||number(cs.paddingLeft)+number(cs.paddingRight)+number(cs.marginLeft)+number(cs.marginRight)>0||cs.backgroundImage!=='none'||cs.backgroundColor!=='rgba(0, 0, 0, 0)'||!flow(child)){good=false;break;}
  }
  flowCache.set(e,good);return good;
 }
 function owner(node){
  if(node.parentElement.closest('.qbr-slide-number,svg'))return null;
  let result=node;
  for(let e=node.parentElement;e&&!e.classList.contains('slide');e=e.parentElement){
   if(!flow(e))break;result=e;
   if(/^(P|H[1-6]|LI|TD|TH|BUTTON|CAPTION)$/.test(e.tagName))break;
  }
  return result;
 }
 function style(e,override){
  const cs=override||getComputedStyle(e);let opacity=1;
  for(let p=e;p;p=p.parentElement){const s=getComputedStyle(p);if(s.display==='none'||s.visibility==='hidden')opacity=0;opacity*=Number(s.opacity);if(p.classList.contains('slide'))break;}
  return {font:cs.fontFamily,size:parseFloat(cs.fontSize),weight:parseInt(cs.fontWeight),spacing:number(cs.letterSpacing),color:cs.color,italic:cs.fontStyle==='italic',underline:cs.textDecorationLine.includes('underline'),opacity,href:e.closest('a')?.href};
 }
 const metricCache=new Map();
 function metrics(style){
  const key=[style.font,style.weight,style.size,style.italic].join('|');if(metricCache.has(key))return metricCache.get(key);
  const ctx=document.createElement('canvas').getContext('2d');ctx.font=`${style.italic?'italic ':''}${style.weight} ${style.size}px ${style.font}`;
  const m=ctx.measureText('Hg0123456789'),value={ascent:m.fontBoundingBoxAscent,descent:m.fontBoundingBoxDescent,space:ctx.measureText(' ').width};metricCache.set(key,value);return value;
 }
 function metadata(root){
  if(cache.has(root))return cache.get(root);
  const element=root.nodeType===3?root.parentElement:root,cs=getComputedStyle(element),slide=element.closest('.slide'),origin=slide.getBoundingClientRect(),lines=[];
  function visit(node){
   if(node.nodeType===3){
    const parent=node.parentElement,computed=getComputedStyle(parent),opts=style(parent);if(!opts.opacity)return;
    const metric=metrics(opts),range=document.createRange();
    for(let i=0;i<node.nodeValue.length;i++){
     let char=node.nodeValue[i];if(!computed.whiteSpace.startsWith('pre')&&/[\t\n\r\f ]/.test(char))char=' ';
     range.setStart(node,i);range.setEnd(node,i+1);const r=range.getBoundingClientRect();if(!r.height||!r.width)continue;
     if(computed.textTransform==='uppercase')char=char.toUpperCase();if(computed.textTransform==='lowercase')char=char.toLowerCase();
     const baseline=r.top+metric.ascent;let line=lines.find(l=>Math.abs(l.baseline-baseline)<1.6);
     if(!line){line={baseline,tokens:[],left:r.left,right:r.right,top:r.top,bottom:r.bottom};lines.push(line);}
     if(char===' '&&line.tokens.at(-1)?.text===' ')continue;
     line.tokens.push({text:char,style:opts});line.left=Math.min(line.left,r.left);line.right=Math.max(line.right,r.right);line.top=Math.min(line.top,r.top);line.bottom=Math.max(line.bottom,r.bottom);
    }return;
   }
   if(node.nodeType!==1||getComputedStyle(node).display==='none'||getComputedStyle(node).visibility==='hidden')return;
   if(node.tagName==='BR')return;
   for(const child of node.childNodes)visit(child);
  }
  visit(root);
  lines.sort((a,b)=>a.baseline-b.baseline);
  for(const l of lines){while(l.tokens[0]?.text===' ')l.tokens.shift();while(l.tokens.at(-1)?.text===' ')l.tokens.pop();}
  const visible=lines.filter(l=>l.tokens.length);if(!visible.length){cache.set(root,null);return null;}
  const runs=[];
  const lineIndexes=[];
  visible.forEach((line,lineIndex)=>{
   let previous=null;
   for(const token of line.tokens){const signature=JSON.stringify(token.style);if(previous&&previous.signature===signature)previous.run.text+=token.text;
    else{const run={text:token.text,...token.style,softBreakBefore:lineIndex>0&&!previous};runs.push(run);lineIndexes.push(lineIndex);previous={signature,run};}}
  });
  const sign=root.nodeType===1?prefix(root):null;
  if(sign){const st=style(element,sign.style),margin=number(sign.style.marginRight);const before=[{text:sign.text,...st}];if(margin)before.push({text:' ',...st,spacing:margin-metrics(st).space});runs.unshift(...before);}
  const fonts=runs.filter(r=>r.text.trim()),maxFont=Math.max(...fonts.map(r=>r.size)),naturalHeight=Math.max(...fonts.map(r=>metrics(r).ascent+metrics(r).descent));
  const deltas=visible.slice(1).map((l,i)=>l.baseline-visible[i].baseline);
  const declaredPitch=cs.lineHeight==='normal'?NaN:number(cs.lineHeight);
  const pitch=Number.isFinite(declaredPitch)&&declaredPitch>0?declaredPitch:(deltas.length?deltas[0]:naturalHeight);
  const irregular=deltas.some(d=>Math.abs(d-pitch)>1.6);
  // Office treats nonzero rPr.baseline as sub/superscript and shrinks glyphs.
  // Extra CSS line gaps therefore become paragraph spacing inside the same textbox.
  if(irregular&&!sign){const seen=new Set();runs.forEach((run,i)=>{const k=lineIndexes[i];if(!k||seen.has(k))return;seen.add(k);const extra=visible[k].baseline-visible[k-1].baseline-pitch;if(Math.abs(extra)>1.6){if(extra<0)throw Error('Unsupported compressed CSS line gap; review this paragraph before export.');run.newParagraphBefore=true;run.paragraphSpaceBefore=extra;}});}
  const r=element.getBoundingClientRect(),isBlock=root.nodeType===1&&!['inline','contents'].includes(cs.display),px=number(cs.paddingLeft)+number(cs.borderLeftWidth);
  const x=isBlock?r.left+px:Math.min(...visible.map(l=>l.left)),w=isBlock?r.width-px-number(cs.paddingRight)-number(cs.borderRightWidth):Math.max(...visible.map(l=>l.right))-x;
  // The first baseline in Office's exact-spacing paragraph sits at 3/4 of its line pitch.
  // Map the measured browser baseline, rather than inheriting an unrelated container line-height.
  const firstBaseline=visible[0].baseline-origin.top,y=firstBaseline-pitch*.75;
  const result={key:'semantic-'+(++sequence),tag:element.tagName,source:element.getAttribute('data-source-id')||element.className||element.tagName,x:x-origin.left,y,w:Math.max(1,w),h:visible.at(-1).baseline-visible[0].baseline+Math.max(naturalHeight,pitch)+maxFont*.3,align:['right','end'].includes(cs.textAlign)?'right':cs.textAlign==='center'?'center':'left',lineHeight:pitch,whiteSpace:cs.whiteSpace,runs,prefix:!!sign,wrapPolicy:'measured-browser-lines',lineCount:visible.length,baselines:visible.map(l=>l.baseline-origin.top),irregularPitch:irregular};
  cache.set(root,result);return result;
 }
 window.SberSemanticText={ownerForNode:owner,forNode(node){const e=owner(node);return e?metadata(e):null;},forPseudo(e){return prefix(e)&&flow(e)?metadata(e):null;}};
}
