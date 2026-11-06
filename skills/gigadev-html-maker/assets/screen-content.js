/* Apply the viewer's contrast control to authored content and its graphics. */
(() => {
 const init=()=>{
  if(window.__gdContentScreenInstalled)return;window.__gdContentScreenInstalled=true;
  const root=document.documentElement,registry=document.getElementById('sk-color-registry');
  const palette=JSON.parse(registry.textContent),sheet=document.getElementById('gd-screen-calibration-style')||document.head.appendChild(Object.assign(document.createElement('style'),{id:'gd-screen-calibration-style'}));let queued=false;
  const clamp=(v,min,max)=>Math.max(min,Math.min(max,v));
  const update=()=>{
   queued=false;const state=window.SalesKitUI?.getState();if(!state)return;
   const theme=state.settings.theme,screen=state.settings.screen||{},s={shadows:screen.shadows??100,saturation:screen.saturation??100,muted:screen.muted??0,contrast:screen.contrast??100};
   if(s.contrast===100){sheet.textContent='';return;}
   const ink=theme==='light'?[.09,.12,.08]:[.92,.94,.91];
   const properties=palette.map(color=>{const rgba=(theme==='light'?color.light:color.dark).slice(),base=rgba.slice(0,3).map(v=>v/255),l=base[0]*.2126+base[1]*.7152+base[2]*.0722;let rgb=base.map(v=>clamp(l+(v-l)*s.saturation/100,0,1)).map(v=>clamp(Math.pow(v,100/s.shadows),0,1));if(color.muted)rgb=rgb.map((v,i)=>v*(1-s.muted/100)+ink[i]*s.muted/100);return `${color.name}:rgba(${rgb.map(v=>Math.round(v*255)).join(',')},${rgba[3]});`}).join('');
   sheet.textContent='';
   const rules=[];
   for(const slide of document.querySelectorAll('#slides>.slide[data-sk-id]')){
    const id=JSON.stringify(slide.dataset.skId);
    for(const cls of ['gd-content','gd-slide-background']){
     const node=slide.querySelector('.'+cls);if(!node)continue;
     const previous=getComputedStyle(node).filter;
     const filter=(previous==='none'?'':previous+' ')+`contrast(${s.contrast}%)`;
     rules.push(`#slides>.slide[data-sk-id=${id}] .${cls}{${properties}filter:${filter}!important}`);
    }
   }
   sheet.textContent=rules.join('\n');
  };
  const schedule=()=>{if(!queued){queued=true;requestAnimationFrame(update)}};
  new MutationObserver(schedule).observe(document.getElementById('sk-colors'),{childList:true,characterData:true,subtree:true});
  new MutationObserver(schedule).observe(document.getElementById('slides'),{childList:true});
  document.addEventListener('input',schedule);document.addEventListener('change',schedule);document.addEventListener('click',schedule);update();
 };
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
