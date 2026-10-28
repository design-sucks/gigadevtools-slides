/* Replayable native transitions. WAAPI leaves layout, text and saved HTML untouched. */
(()=>{function init(){
 'use strict';
 const root=document.documentElement,track=document.getElementById('slides');
 const ease='cubic-bezier(.22,.78,.22,1)',owned=new Map(),scrollOwned=new Map(),outside=new Map();
 let printing=false;
 let visible=window.slides[window.cur],phase='idle',direction=1,serial=0;
 const enabled=()=>root.dataset.skMotion!=='off'&&!root.classList.contains('edit-mode')&&!document.hidden&&!!Element.prototype.animate;
 const current=()=>window.slides[window.cur];
 // Whole-slide visibility only: never crop a blur layer or save transient state.
 function neighbors(){
  const list=[...window.slides],compact=root.hasAttribute('data-gd-compact')&&!root.hasAttribute('data-gd-export')&&!root.hasAttribute('data-sk-present')&&!printing;
  let allowed=new Set(list);
  if(compact){const top=track.scrollTop,aligned=list.find(s=>Math.abs(s.offsetTop-top)<1);
   if(aligned)allowed=new Set([aligned]);
   else{const before=list.filter(s=>s.offsetTop<top).at(-1),after=list.find(s=>s.offsetTop>top);allowed=new Set([before,after].filter(Boolean));}
  }
  for(const [slide,a]of outside)if(allowed.has(slide)||!list.includes(slide)){a.cancel();outside.delete(slide);}
  for(const slide of list)if(!allowed.has(slide)&&!outside.has(slide)){
   const a=slide.animate([{visibility:'hidden',opacity:0},{visibility:'hidden',opacity:0}],{duration:1,fill:'both'});a.pause();outside.set(slide,a);
  }
 }

 root.setAttribute('data-sk-motion-ready','');
 const isBackground=el=>el.classList.contains('sk-cover-motion')||el.classList.contains('gd-slide-background');
 const isDeckBackground=el=>el.classList.contains('gd-slide-background');
 function groups(slide){
  const inner=slide?.querySelector('.slide-inner');if(!inner)return [];
  if(slide.hasAttribute('data-sk-live-cover'))return [inner,slide.querySelector('.sk-cover-motion')].filter(Boolean);
  const visibleChildren=parent=>[...parent.children].filter(el=>!el.hidden&&!el.matches('style,script')&&el.getBoundingClientRect().height>0&&getComputedStyle(el).position!=='absolute');
  const nodes=[];
  const background=inner.querySelector(':scope>.gd-slide-background');if(background)nodes.push(background);
  for(const el of visibleChildren(inner.querySelector(':scope>.gd-content')||inner)){
   const split=el.matches('.grid3,.fc,.m-grid,.pricing,.surfaces,.eff-hero,.effect,.profile-cards,.sk-analytics-metrics,.probs,.c-contact-glass');
   const children=split?visibleChildren(el):[];
   nodes.push(...(children.length>1&&children.length<=8?children:[el]));
  }
  const legacyBackground=slide.querySelector('.sk-cover-motion');if(legacyBackground&&!nodes.includes(legacyBackground))nodes.push(legacyBackground);
  return nodes;
 }
 function state(el){const c=getComputedStyle(el);return {opacity:c.opacity,filter:c.filter,translate:c.translate};}
 function shifted(base,y){const t=(base.translate==='none'?'0px 0px':base.translate).split(/\s+/);return `${t[0]} calc(${t[1]||'0px'} + ${y}px)`;}
 function hidden(base,y,blur,el){const gain=el?.classList.contains('slide-inner')?1:(Number(root.style.getPropertyValue('--gd-motion-gain'))||1);y*=gain;blur*=gain;return {opacity:0,filter:`${base.filter==='none'?'':base.filter+' '}blur(${blur}px)`,translate:shifted(base,y)};}
 function cancel(keepScroll=false){for(const {animation}of owned.values())animation.cancel();owned.clear();if(!keepScroll){for(const {animation}of scrollOwned.values())animation.cancel();scrollOwned.clear();}}
 function animate(el,frames,base,duration,delay=0,easing=ease,hold=false){
  const animation=el.animate(frames,{duration,delay,easing,fill:'both'});
  const record={animation,base};owned.set(el,record);
  return animation.finished.then(()=>{if(!hold&&owned.get(el)===record){owned.delete(el);animation.cancel();}},()=>{});
 }
 function reveal(slide,dir=direction,fromCurrent=false){
  // The chart's final comparison is part of the slide, revealed by the shared transition.
  if(slide?.classList.contains('slide--eff'))slide.classList.add('gt-reveal-growth');
  const nodes=groups(slide),states=new Map(nodes.map(el=>[el,{now:state(el),base:owned.get(el)?.base||state(el)}]));
  cancel();visible=slide;phase='enter';const token=++serial;
  if(!enabled()){phase='idle';return;}
  Promise.all(nodes.map((el,i)=>{
   const {now,base}=states.get(el),text=el.matches('h1,h2,.lead,.eyebrow,.hero-tag');
   if(isDeckBackground(el))return animate(el,[fromCurrent?now:{opacity:0,filter:'blur(14px)'},{opacity:base.opacity,filter:base.filter}],base,root.dataset.skTheme==='light'?1000:1300,0,'cubic-bezier(.42,0,.24,1)');
   if(isBackground(el))return animate(el,[fromCurrent?now:{opacity:0},{opacity:base.opacity}],base,root.dataset.skTheme==='light'?1000:1300,0,'cubic-bezier(.42,0,.24,1)');
   // One continuous curve, with >90% overlap between the content groups.
   const cover=slide.hasAttribute('data-sk-live-cover'),shift=dir*(cover?16:text?16:12),blur=cover||text?12:9;
   const contentCount=nodes.filter(n=>!isBackground(n)).length;
   const delay=fromCurrent?0:(cover?(root.dataset.skTheme==='light'?240:140):Math.sin(i/Math.max(1,contentCount-1)*Math.PI/2)*64);
   return animate(el,[fromCurrent?now:hidden(base,shift,blur,el),base],base,760,delay,'cubic-bezier(.28,.08,.2,1)');
  })).then(()=>{if(serial===token)phase='idle';});
 }
 function showTarget(animateEntry=true){
  const target=current();if(!target)return;
  ++serial;cancel();phase='idle';visible=target;
  // Hide the incoming content before moving the scroll position: no intermediate slides flash.
  if(animateEntry&&enabled())reveal(target);
  window.stopAnims();window.lockScroll=true;track.scrollTop=target.offsetTop;
  window.updateUI();window.lockScroll=false;neighbors();if(root.hasAttribute('data-gd-compact'))scrub();
 }
 function navigate(n){
  if(!Number.isInteger(n)||n<0||n>=window.slides.length||n===window.cur)return;
  direction=Math.sign(n-window.cur)||1;window.cur=n;window.stopAnims();
  if(!enabled()){showTarget(false);return;}
  if(current()===visible){
   window.lockScroll=false;track.scrollTop=visible.offsetTop;window.updateUI();reveal(visible,direction,true);return;
  }
  // Repeated clicker presses update the destination without restarting the exit timer.
  if(phase==='exit')return;
  const scrolled=phase==='scroll',inner=visible.querySelector('.slide-inner');
  const nodes=scrolled?[inner,visible.querySelector('.sk-cover-motion')].filter(Boolean):groups(visible);
  const states=nodes.map(el=>({el,now:state(el),base:owned.get(el)?.base||scrollOwned.get(el)?.base||state(el)}));
  ++serial;cancel(root.hasAttribute('data-gd-compact'));phase='exit';window.lockScroll=true;const token=serial;
  Promise.all(states.map(({el,now,base})=>isDeckBackground(el)
   ?animate(el,[now,{opacity:0,filter:'blur(14px)'}],base,520,0,'cubic-bezier(.4,0,.8,.6)',true)
   :isBackground(el)?animate(el,[{opacity:now.opacity},{opacity:0}],base,520,0,'cubic-bezier(.4,0,.8,.6)',true)
   :animate(el,[now,hidden(base,-direction*14,10,el)],base,visible.hasAttribute('data-sk-live-cover')?340:280,0,'cubic-bezier(.4,0,.8,.5)',true)))
   .then(()=>{if(serial===token)showTarget();});
 }
 // Scrub the same soft fade on native trackpad/touch scroll, including the outgoing slide.
 // Paused WAAPI effects avoid writing transient styles into saved HTML.
 function scrub(){
  if(window.lockScroll)return;neighbors();if(!enabled())return;
  const target=current(),top=track.scrollTop,aligned=Math.abs(top-target.offsetTop)<1;
  const compact=root.hasAttribute('data-gd-compact');
  if(aligned&&!compact){
   if(scrollOwned.size){++serial;cancel();phase='idle';visible=target;}
   else if(target!==visible)reveal(target,Math.sign(target.offsetTop-visible.offsetTop)||1);
   return;
  }
  if(!aligned&&phase!=='scroll'){++serial;cancel();phase='scroll';}else if(aligned&&compact&&phase==='scroll'){++serial;cancel();phase='idle';}
  visible=target;
  const near=new Set();
  for(const [index,slide]of [...window.slides].entries()){
   const delta=slide.offsetTop-top,list=window.slides;
   // Each fade reaches zero at the adjacent anchor, even with compact pages.
   const distance=compact?(delta>=0?(slide.offsetTop-(list[index-1]?.offsetTop??slide.offsetTop-track.clientHeight)):((list[index+1]?.offsetTop??slide.offsetTop+slide.offsetHeight)-slide.offsetTop)):slide.offsetHeight,ratio=delta/Math.max(1,distance);
   if(Math.abs(ratio)>=1)continue;
   const inner=slide.querySelector('.slide-inner');if(!inner)continue;
   for(const el of [inner,slide.querySelector('.sk-cover-motion')].filter(Boolean)){
    near.add(el);let record=scrollOwned.get(el);
    if(!record){
     if(slide.classList.contains('slide--eff'))slide.classList.add('gt-reveal-growth');
     const base=state(el),background=isBackground(el),frames=background?[
      {opacity:0},{opacity:base.opacity,offset:.5},{opacity:0}
     ]:[
      {...hidden(base,-18,11,el),easing:'cubic-bezier(.4,0,.2,1)'},
      {...base,offset:.5,easing:'cubic-bezier(.4,0,.2,1)'},hidden(base,18,11,el)
     ];
     const animation=el.animate(frames,{duration:1000,fill:'both'});
     animation.pause();record={animation,base};scrollOwned.set(el,record);
    }
    record.animation.currentTime=(ratio+1)*500;
   }
  }
  for(const [inner,record] of scrollOwned)if(!near.has(inner)){record.animation.cancel();scrollOwned.delete(inner);}
 }
 track.addEventListener('scroll',scrub,{passive:true});
 function finish(){showTarget(false);}
 let wasEnabled=enabled(),theme=root.dataset.skTheme;
 new MutationObserver(()=>{
  const on=enabled(),nextTheme=root.dataset.skTheme;
  if(!on||nextTheme!==theme)finish();else if(!wasEnabled)reveal(current());
  wasEnabled=on;theme=nextTheme;neighbors();if(on&&root.hasAttribute('data-gd-compact'))scrub();
 }).observe(root,{attributes:true,attributeFilter:['data-sk-motion','data-sk-theme','class','data-gd-compact','data-gd-export','data-sk-present']});
 new MutationObserver(()=>{if(current()!==visible||!visible.isConnected)finish();}).observe(track,{childList:true});
 window.addEventListener('beforeprint',()=>{printing=true;finish();});window.addEventListener('afterprint',()=>{printing=false;finish();});
 document.addEventListener('visibilitychange',()=>{if(document.hidden)finish();});
 window.SalesKitMotion={navigate,finish,getState:()=>({phase,active:visible?.dataset.skId,target:current()?.dataset.skId,animations:owned.size+scrollOwned.size})};
 reveal(visible);if(root.hasAttribute('data-gd-compact'))scrub();
 }if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();})();
