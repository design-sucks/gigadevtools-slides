/* Maker media lifecycle. No project-specific hooks or wrapped shell functions. */
(() => {
  if (window.__gdMediaInstalled) return;
  window.__gdMediaInstalled = true;
  const root = document.documentElement;
  let wasPresent = root.hasAttribute('data-sk-present');
  const track = document.getElementById('slides');
  const media = () => [...track.querySelectorAll('video,audio')];
  for (const item of media()) {
    const value = Number(item.dataset.gdVolume);
    if (item.hasAttribute('data-gd-volume') && Number.isFinite(value) && value >= 0 && value <= 1) item.volume = value;
    item.addEventListener('volumechange', () => {
      item.dataset.gdVolume = String(item.volume);
      item.toggleAttribute('muted', item.muted);
    });
  }
  const active = () => window.slides?.[window.cur];
  const current = () => active()?.querySelector('video,audio');
  // Keep the shell's visible footer and progress track in place, but stop its
  // invisible hit areas from covering native controls on the current full video.
  // An adopted stylesheet is runtime-only and is not cloned into saved decks.
  let hitSheet=null,passSheet=null,panelSheet=null,hitFrame=0,watchFrame=0,watchSignature='',passRules='',panelRules='',panelSlide=null;
  try {
    if ('adoptedStyleSheets' in document && typeof CSSStyleSheet==='function') {
      hitSheet=new CSSStyleSheet();passSheet=new CSSStyleSheet();panelSheet=new CSSStyleSheet();
      hitSheet.replaceSync(`
        html[data-sk-present] #sk-show-controls{width:12px}
        html[data-sk-present] #sk-footer::after{content:"";position:absolute;left:100%;right:-27px;top:0;bottom:0}
        html[data-sk-present] #sk-progress{pointer-events:none}
        html[data-sk-present] #sk-progress-input{top:auto;bottom:0;height:5px;pointer-events:auto;clip-path:inset(0)}
      `);
    }
  } catch (_) { hitSheet=null;passSheet=null;panelSheet=null; }
  let hitStatus=hitSheet?{state:'inactive',reason:'not-present'}:{state:'rejected',reason:'runtime-stylesheet-unsupported',applied:false};
  const reject=(reason,detail={})=>({state:'rejected',reason,...detail});
  const sameRect=(a,b)=>{
    const tol=Math.max(2,Math.max(b.width,b.height)*.005);
    return a.width>0 && a.height>0 && [a.left-b.left,a.top-b.top,a.right-b.right,a.bottom-b.bottom].every(x=>Number.isFinite(x)&&Math.abs(x)<=tol);
  };
  const plainGeometry=(node,wrapper=false,expectedZoom=1)=>{
    const s=getComputedStyle(node),neutral=v=>!v||v==='none'||v==='normal';
    if(s.transform!=='none'||!neutral(s.translate)||!neutral(s.rotate)||!neutral(s.scale)||!Number.isFinite(Number(s.zoom))||Math.abs(Number(s.zoom)-expectedZoom)>.001)return false;
    if((s.outlineStyle!=='none'&&parseFloat(s.outlineWidth)>0)||parseFloat(s.webkitTextStrokeWidth)>0||s.textDecorationLine!=='none'||!neutral(s.filter)||!neutral(s.backdropFilter)||!neutral(s.clipPath)||!neutral(s.maskImage)||!neutral(s.perspective)||!neutral(s.boxShadow)||!neutral(s.textShadow)||s.mixBlendMode!=='normal'||s.display==='contents'||s.contentVisibility!=='visible'||s.position==='fixed'||s.position==='sticky')return false;
    if([s.overflowX,s.overflowY].some(v=>v!=='visible' && !(['IMG','VIDEO'].includes(node.tagName)&&v==='clip')))return false;
    for(const pseudo of ['::before','::after']){const content=getComputedStyle(node,pseudo).content;if(content!=='none'&&content!=='normal')return false;}
    if(wrapper && (s.backgroundImage!=='none'||!['rgba(0, 0, 0, 0)','transparent'].includes(s.backgroundColor)||[s.borderTopWidth,s.borderRightWidth,s.borderBottomWidth,s.borderLeftWidth].some(v=>parseFloat(v)!==0)))return false;
    return true;
  };
  const hitEligibility=slide=>{
    if(!slide || slide.dataset.gdMediaFrame!=='full')return reject('no-explicit-full-frame');
    const content=slide.querySelector(':scope>.slide-inner>.gd-content');
    if(!content||content.children.length!==1||[...content.childNodes].some(n=>n.nodeType===Node.TEXT_NODE&&n.data.trim()))return reject('ambiguous-content');
    // The shell may scale the composition uniformly. Rotation, skew,
    // translated frames, masks and clipped ancestors have no safe band model.
    const cs=getComputedStyle(content),inner=getComputedStyle(content.parentElement),outer=getComputedStyle(slide);let matrix;
    try{matrix=new DOMMatrixReadOnly(cs.transform==='none'?undefined:cs.transform)}catch(_){return reject('composition-transform-unresolved')}
    const epsilon=.0001,sourceZoom=Number(root.style.getPropertyValue('--gd-motion-zoom'))||1,innerZoom=Number(inner.zoom),neutral=v=>v==='none'||v==='0px';
    if(!matrix.is2D||matrix.a<=0||matrix.d<=0||Math.abs(matrix.b)>epsilon||Math.abs(matrix.c)>epsilon||Math.abs(matrix.a-matrix.d)>epsilon||Math.abs(matrix.e)>epsilon||Math.abs(matrix.f)>epsilon||!neutral(cs.translate)||cs.rotate!=='none'||cs.scale!=='none'||Number(cs.zoom)!==1||cs.filter!=='none'||cs.overflowX!=='visible'||cs.overflowY!=='visible'||cs.clipPath!=='none'||cs.maskImage!=='none'||inner.transform!=='none'||!neutral(inner.translate)||inner.rotate!=='none'||inner.scale!=='none'||!['none','blur(0px)'].includes(inner.filter)||inner.clipPath!=='none'||inner.maskImage!=='none'||Number(inner.opacity)<.999||!Number.isFinite(innerZoom)||(Math.abs(innerZoom-1)>.001&&Math.abs(innerZoom-sourceZoom)>.001)||outer.transform!=='none'||!neutral(outer.translate)||outer.rotate!=='none'||outer.scale!=='none'||outer.filter!=='none'||outer.clipPath!=='none'||outer.maskImage!=='none'||Number(outer.opacity)<.999)return reject('composition-transform-unresolved');
    const videos=content.querySelectorAll('video');
    if(videos.length!==1||content.querySelector('audio')||!videos[0].controls)return reject('video-count-or-controls');
    const video=videos[0],container=content.firstElementChild;
    if(container!==video && (container.tagName!=='DIV'||video.parentElement!==container||!plainGeometry(container,true)||[...container.childNodes].some(n=>n.nodeType===Node.TEXT_NODE&&n.data.trim())))return reject('unsupported-wrapper');
    const videoStyle=getComputedStyle(video);
    if(!plainGeometry(video)||videoStyle.display==='none'||videoStyle.visibility!=='visible'||Number(videoStyle.opacity)<=.001||videoStyle.objectFit!=='contain')return reject('video-geometry-unresolved');
    const box=video.getBoundingClientRect(),canvas=content.getBoundingClientRect();
    if(!sameRect(box,canvas)||container!==video&&!sameRect(container.getBoundingClientRect(),canvas))return reject('video-not-full-frame');
    const bandHeight=Math.min(box.height,Math.max(120,box.height*.25));
    const band={left:box.left,right:box.right,top:box.bottom-bandHeight,bottom:box.bottom};
    if(container!==video){
      if(typeof container.getAnimations!=='function'||container.getAnimations({subtree:true}).some(a=>a.playState!=='idle'))return reject('overlay-animation-unresolved');
      const visit=node=>{
        const s=getComputedStyle(node);if(s.display==='none')return null;
        const expectedZoom=panelSlide===slide&&node.parentElement===container?Number(root.style.getPropertyValue('--gd-view-scale')):1;
        if(!plainGeometry(node,false,expectedZoom)||node.matches('svg,canvas,iframe,object,embed,ul,ol,li'))return 'overlay-geometry-unresolved';
        const r=node.getBoundingClientRect();
        if(![r.left,r.top,r.right,r.bottom,r.width,r.height].every(Number.isFinite))return 'overlay-geometry-unresolved';
        if((r.width<=0||r.height<=0)&&node.textContent?.trim())return 'overlay-geometry-unresolved';
        if(s.visibility==='visible'&&r.width>0&&r.height>0&&r.right>band.left&&r.left<band.right&&r.bottom>band.top&&r.top<band.bottom)return 'overlay-in-control-band';
        for(const child of node.children){const reason=visit(child);if(reason)return reason;}
        return null;
      };
      for(const node of container.children)if(node!==video){const reason=visit(node);if(reason)return reject(reason,{sourceId:node.dataset.sourceId||null});}
    }
    return {state:'eligible',reason:'verified-dom-frame-and-band',sourceId:video.dataset.sourceId||null,band:{top:band.top,bottom:band.bottom,height:bandHeight},video,container};
  };
  let passStatus={state:'inactive',reason:'no-opt-in',accepted:[],rejected:[]};
  const passiveSelector='a,button,input,select,textarea,summary,details,iframe,object,embed,audio,video,[href],[tabindex],[contenteditable],[role],[draggable],[usemap],[onclick],[ondblclick],[onpointerdown],[onpointerup],[onmousedown],[onmouseup],[ontouchstart],[onkeydown],[onkeyup],[onkeypress],[onwheel],[oncontextmenu]';
  const passiveTags=new Set(['DIV','P','SPAN','STRONG','EM','B','I','SMALL','SUB','SUP','BR']);
  const passThrough=(slide,assessment)=>{
    const video=assessment.video,wrapper=assessment.container;
    if(assessment.state!=='eligible'||!video||wrapper===video){
      const marked=slide?[...slide.querySelectorAll('[data-gd-video-pass-through="true"]')]:[];
      return {rules:'',status:marked.length?{state:'review',reason:'frame-or-overlay-unresolved',accepted:[],rejected:marked.map(n=>({sourceId:n.dataset.sourceId||null,reason:assessment.reason}))}:{state:'inactive',reason:'no-eligible-wrapper',accepted:[],rejected:[]}};
    }
    const accepted=[],rejected=[],rules=[];
    if(typeof globalThis.CSS?.escape!=='function'||typeof globalThis.CSS?.supports!=='function'||!globalThis.CSS.supports('selector(:has(*))')){
      const marked=[...wrapper.children].filter(n=>n.getAttribute('data-gd-video-pass-through')==='true');
      return {rules:'',status:marked.length?{state:'review',reason:'selector-support-unavailable',accepted:[],rejected:marked.map(n=>({sourceId:n.dataset.sourceId||null,reason:'selector-support-unavailable'}))}:{state:'inactive',reason:'no-opt-in',accepted:[],rejected:[]}};
    }
    for(const overlay of wrapper.children){
      if(overlay===video||overlay.getAttribute('data-gd-video-pass-through')!=='true')continue;
      const id=overlay.dataset.sourceId||'',all=[overlay,...overlay.querySelectorAll('*')];
      let reason='';
      if(!id||[...slide.querySelectorAll('[data-source-id]')].filter(n=>n.dataset.sourceId===id).length!==1)reason='source-id-missing-or-ambiguous';
      else if(all.some(n=>!passiveTags.has(n.tagName)||n.matches(passiveSelector)||[...n.attributes].some(a=>/^on/i.test(a.name))||n.style.pointerEvents))reason='interactive-or-unsafe-overlay';
      if(reason){rejected.push({sourceId:id||null,reason});continue;}
      const target=`#slides>.slide[data-sk-id="${CSS.escape(slide.dataset.skId)}"]>.slide-inner>.gd-content>div>[data-source-id="${CSS.escape(id)}"][data-gd-video-pass-through="true"]`;
      // The :has guard disables the rule immediately if a descendant becomes interactive.
      const safe=`${target}:not(${passiveSelector}):not(:has(${passiveSelector}))`;
      rules.push(`html:not([data-sk-edit]):not(.edit-mode):not([data-gd-export]) ${safe},html:not([data-sk-edit]):not(.edit-mode):not([data-gd-export]) ${safe} *{pointer-events:none!important}`);accepted.push(id);
    }
    return {rules:rules.join('\n'),status:{state:rejected.length?'review':accepted.length?'eligible':'inactive',reason:rejected.length?'some-overlays-unresolved':accepted.length?'explicit-passive-opt-in':'no-opt-in',accepted,rejected}};
  };
  const setSheet=(sheet,needed)=>{
    if(!sheet)return;const sheets=document.adoptedStyleSheets,installed=sheets.includes(sheet);
    if(needed&&!installed)document.adoptedStyleSheets=[...sheets,sheet];
    else if(!needed&&installed)document.adoptedStyleSheets=sheets.filter(item=>item!==sheet);
  };
  // Chromium sizes native controls in the untransformed layout viewport. A
  // full-frame wrapper with a transformed 1920px canvas can therefore clip
  // the controls even when the video itself visibly fills the viewport.
  // Flatten only a verified frame; each positioned overlay gets the same
  // uniform zoom so its authored coordinates and text remain editable.
  const panelLayout=(slide,assessment)=>{
    if(!panelSheet||assessment.state!=='eligible'||!slide?.dataset.skId||typeof globalThis.CSS?.escape!=='function')return {rules:'',reason:'frame-unresolved'};
    const {video,container}=assessment,scale=Number(root.style.getPropertyValue('--gd-view-scale'));
    if(!Number.isFinite(scale)||scale<=0)return {rules:'',reason:'scale-unresolved'};
    if(container!==video){
      const px=/^-?(?:\d+(?:\.\d*)?|\.\d+)px$/i;
      for(const node of container.children){
        if(node===video)continue;
        const s=getComputedStyle(node),style=node.style;
        if(s.position!=='absolute'||!px.test(style.left)||!px.test(style.top)||style.right||style.bottom||style.inset||style.zoom)return {rules:'',reason:'overlay-position-unresolved'};
      }
    }
    const q=`html:not([data-sk-edit]):not(.edit-mode):not([data-gd-export]) #slides>.slide[data-sk-id="${CSS.escape(slide.dataset.skId)}"][data-gd-media-frame="full"]`,g=`${q}>.slide-inner>.gd-content`;
    return {reason:'verified-full-frame',rules:`
      ${q}>.slide-inner{zoom:1!important;width:100%!important;height:100%!important}
      ${q} .gd-slide-background{width:var(--gd-scroll-width)!important;height:var(--gd-scroll-height)!important}
      ${q} .gd-slide-background--content-frame{background-size:calc(1920px * var(--gd-view-scale)) calc(1080px * var(--gd-view-scale))!important;background-position:calc(var(--gd-content-left) - 112px * var(--gd-view-scale)) calc(var(--gd-content-top) - 120px * var(--gd-view-scale))!important}
      ${g}{left:calc(var(--gd-content-left) - 112px * var(--gd-view-scale))!important;top:calc(var(--gd-content-top) - 120px * var(--gd-view-scale))!important;width:calc(1920px * var(--gd-view-scale))!important;height:calc(1080px * var(--gd-view-scale))!important;transform:none!important}
      ${g}>div{width:100%!important;height:100%!important}
      ${g}>video,${g}>div>video{width:100%!important;height:100%!important}
      ${g}>div>:not(video){zoom:var(--gd-view-scale)!important}
    `};
  };
  let panelStatus={state:'inactive',reason:'not-assessed',applied:false};
  const directCanvasFallback=(slide,assessment)=>{
    // The legacy direct-video portrait rule already unscales the frame. An
    // authored 1920x1080 inline video can then remain 1920px wide. Only the
    // exact full-canvas form is eligible; custom-sized videos stay untouched.
    if(assessment.reason!=='video-not-full-frame'||!slide)return assessment;
    const content=slide.querySelector(':scope>.slide-inner>.gd-content'),video=content?.firstElementChild;
    if(!content||content.children.length!==1||video?.tagName!=='VIDEO'||video.style.width!=='1920px'||video.style.height!=='1080px')return assessment;
    const cs=getComputedStyle(content),s=Number(root.style.getPropertyValue('--gd-view-scale')),a=video.getBoundingClientRect(),b=content.getBoundingClientRect();
    if(cs.transform!=='none'||!Number.isFinite(s)||s<=0||Math.abs(b.width-1920*s)>2||Math.abs(b.height-1080*s)>2||Math.abs(a.left-b.left)>2||Math.abs(a.top-b.top)>2||Math.abs(a.width-1920)>2||Math.abs(a.height-1080)>2)return assessment;
    return {state:'eligible',reason:'verified-inline-full-canvas',video,container:video};
  };
  const syncHitAreas=()=>{
    hitFrame=0;if(!hitSheet)return;
    const slide=active(),present=root.hasAttribute('data-sk-present')&&!root.hasAttribute('data-gd-export');
    const reading=!root.hasAttribute('data-sk-edit')&&!root.classList.contains('edit-mode')&&!root.hasAttribute('data-gd-export');
    const assessment=(present||reading)?hitEligibility(slide):{state:'inactive',reason:'edit-or-export'};
    const layout=reading?panelLayout(slide,directCanvasFallback(slide,assessment)):{rules:'',reason:'edit-or-export'};
    const nextPanelSlide=layout.rules?slide:null;
    const panelChanged=layout.rules!==panelRules||panelSlide!==nextPanelSlide;
    if(layout.rules!==panelRules){panelSheet.replaceSync(layout.rules);panelRules=layout.rules;}
    panelSlide=nextPanelSlide;setSheet(panelSheet,Boolean(layout.rules));
    panelStatus={state:layout.rules?'eligible':'inactive',reason:layout.reason,applied:Boolean(layout.rules),slideId:slide?.dataset.skId||null};
    const video=assessment.video;let needed=false;
    if(video&&present){const box=video.getBoundingClientRect(),w=innerWidth,h=innerHeight;
      needed=(box.right>w-235 && box.left<w && box.bottom>h-85 && box.top<h) ||
             (box.right>0 && box.left<w && box.bottom>h-20 && box.top<h);
    }
    setSheet(hitSheet,needed);
    const pass=reading?passThrough(slide,assessment):{rules:'',status:{state:'inactive',reason:'edit-or-export',accepted:[],rejected:[]}};
    if(pass.rules!==passRules){passSheet.replaceSync(pass.rules);passRules=pass.rules;}
    setSheet(passSheet,Boolean(pass.rules));passStatus=pass.status;
    const {video:_video,container:_container,...publicAssessment}=assessment;
    const next={...publicAssessment,applied:needed,slideId:slide?.dataset.skId||null};
    const changed=next.state!==hitStatus.state||next.reason!==hitStatus.reason||next.applied!==hitStatus.applied||next.slideId!==hitStatus.slideId;
    hitStatus=next;if(changed)document.dispatchEvent(new CustomEvent('gd-media-eligibility',{detail:{...next}}));
    if(panelChanged)scheduleHitAreas();
    scheduleGeometryWatch();
  };
  const scheduleHitAreas=()=>{if(hitSheet&&!hitFrame)hitFrame=requestAnimationFrame(syncHitAreas);};
  const scheduleGeometryWatch=()=>{if(hitSheet&&!watchFrame&&!document.hidden)watchFrame=requestAnimationFrame(watchGeometry);};
  const watchGeometry=()=>{
    watchFrame=0;const slide=active(),content=slide?.querySelector(':scope>.slide-inner>.gd-content');
    const watch=slide?.dataset.gdMediaFrame==='full'&&content&&(root.hasAttribute('data-sk-present')||(!root.hasAttribute('data-sk-edit')&&!root.classList.contains('edit-mode')&&(panelSlide===slide||content.querySelector('[data-gd-video-pass-through="true"]'))))&&!root.hasAttribute('data-gd-export');
    if(!watch){watchSignature='';return;}
    // Rectangles and active animations detect movement even when ResizeObserver
    // cannot see a position change; expensive style inspection is on change.
    if(typeof content.getAnimations!=='function'){watchSignature='';return;}
    const elements=[content,...content.querySelectorAll('*')];
    const signature=elements.map(n=>{const r=n.getBoundingClientRect();return [r.x,r.y,r.width,r.height].map(x=>Math.round(x*100)/100).join(',')}).join(';')+'|'+content.getAnimations({subtree:true}).filter(a=>a.playState!=='idle').length;
    if(signature!==watchSignature){watchSignature=signature;scheduleHitAreas();}
    scheduleGeometryWatch();
  };
  window.GigaDevMedia=Object.assign(window.GigaDevMedia||{},{getHitAreaStatus:()=>({...hitStatus}),getPanelLayoutStatus:()=>({...panelStatus}),getPassThroughStatus:()=>({...passStatus,accepted:[...passStatus.accepted],rejected:passStatus.rejected.map(x=>({...x}))})});
  track.addEventListener('scroll',scheduleHitAreas,{passive:true});
  document.addEventListener('gigadev-slidechange',scheduleHitAreas);
  // A media query may change authored geometry while the override is active.
  window.addEventListener('resize',()=>invalidateGeometry(),{passive:true});
  document.addEventListener('fullscreenchange',scheduleHitAreas);
  document.addEventListener('visibilitychange',scheduleHitAreas);
  // Invalidate synchronously for markup/class/style changes, before the next click.
  const invalidateGeometry=()=>{
    // Inspect authored values without the runtime override after any change;
    // otherwise its !important dimensions could hide a newly unsafe video.
    if(panelSlide){setSheet(panelSheet,false);panelSlide=null;}
    if(hitFrame)cancelAnimationFrame(hitFrame);syncHitAreas();
  };
  new MutationObserver(invalidateGeometry).observe(track,{subtree:true,childList:true,characterData:true,attributes:true});
  new MutationObserver(invalidateGeometry).observe(root,{attributes:true,attributeFilter:['data-sk-present','data-gd-export','data-sk-edit','class']});
  new MutationObserver(invalidateGeometry).observe(document.head,{subtree:true,childList:true,characterData:true,attributes:true});
  document.addEventListener('pointermove',()=>{if(active()?.dataset.gdMediaFrame==='full')scheduleHitAreas();},{passive:true});
  scheduleHitAreas();
  const pauseInactive = () => { for (const item of media()) if (item.closest('.slide') !== active()) item.pause(); };
  const stopAll = () => { for (const item of media()) item.pause(); };
  let noticeTimer;
  const reportError = (item,error) => {
    item.dispatchEvent(new CustomEvent('gd-media-error',{detail:{message:error.message}}));
    const toast=document.getElementById('sk-toast');
    if(toast){toast.textContent='Не удалось воспроизвести медиа. Проверьте файл и разрешения браузера.';toast.hidden=false;clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>{toast.hidden=true},4000);}
  };
  const toggle = item => {
    if (item.paused || item.ended) {
      if (item.ended) item.currentTime = 0;
      const promise = item.play();
      if (promise && typeof promise.catch === 'function') promise.catch(error => reportError(item,error));
    } else item.pause();
  };
  let raf = 0;
  const monitor = () => {
    raf = 0; pauseInactive();
    if (media().some(item => !item.paused)) raf = requestAnimationFrame(monitor);
  };
  document.addEventListener('play', event => {
    if (!event.target.matches?.('#slides video,#slides audio')) return;
    if (event.target.closest('.slide') !== active()) { event.target.pause(); return; }
    if (!raf) raf=requestAnimationFrame(monitor);
  }, true);
  track.addEventListener('scroll', () => requestAnimationFrame(pauseInactive), {passive:true});
  new MutationObserver(records => {
    for (const record of records) for (const node of record.removedNodes) {
      if (node.nodeType!==Node.ELEMENT_NODE) continue;
      if (node.matches('video,audio')) node.pause();
      for (const item of node.querySelectorAll('video,audio')) item.pause();
    }
  }).observe(track,{childList:true});
  document.addEventListener('visibilitychange', () => { if (document.hidden) stopAll(); });
  new MutationObserver(() => {
    const present = root.hasAttribute('data-sk-present');
    if (wasPresent && !present) stopAll();
    wasPresent = present;
    if (root.hasAttribute('data-gd-export')) {
      for (const item of media()) { item.pause(); item.removeAttribute('controls'); if (item.tagName==='VIDEO') item.load(); }
    }
  }).observe(root,{attributes:true,attributeFilter:['data-sk-present','data-gd-export']});
  document.addEventListener('click', event => {
    const item=event.target.closest?.('#slides video');
    if (!item || item.closest('.slide') !== active()) return;
    if (!root.hasAttribute('data-sk-present') && item.controls) {
      const box=item.getBoundingClientRect();
      if(event.clientY >= box.bottom - Math.min(48,box.height*.25)) return;
    }
    event.preventDefault();event.stopPropagation();toggle(item);
  },true);
  window.addEventListener('keydown', event => {
    if (event.code !== 'Space' || event.repeat || event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey || event.shiftKey || document.querySelector('dialog[open],.cc-overlay.open,#wpOv.open')) return;
    if (event.target?.closest?.('input,textarea,select,[contenteditable]:not([contenteditable=false]),a,summary,button')) return;
    const item=current();if(!item)return;
    event.preventDefault();event.stopImmediatePropagation();toggle(item);
  },true);
})();
