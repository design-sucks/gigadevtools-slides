/* One native top-layer tooltip for toolbar and dialog controls. */
(()=>{function init(){
 const tip=document.getElementById('sk-tooltip');let owner=null;
 function hide(){if(tip.matches(':popover-open'))tip.hidePopover();if(owner){owner.removeAttribute('aria-describedby');owner=null;}}
 function place(){if(!owner)return;const r=owner.getBoundingClientRect(),w=tip.offsetWidth,h=tip.offsetHeight;tip.style.left=Math.max(8,Math.min(innerWidth-w-8,r.left+r.width/2-w/2))+'px';tip.style.top=(r.bottom+h+20<innerHeight?r.bottom+12:Math.max(8,r.top-h-12))+'px';}
 function show(button){if(!button?.dataset.tip||button.disabled)return;hide();owner=button;tip.textContent=button.dataset.tip;button.setAttribute('aria-describedby','sk-tooltip');tip.showPopover();place();}
 document.addEventListener('pointerover',e=>{const b=e.target.closest('[data-tip]');if(b!==owner)show(b);});
 document.addEventListener('pointerout',e=>{if(owner&&!owner.contains(e.relatedTarget))hide();});
 document.addEventListener('focusin',e=>{const b=e.target.closest('[data-tip]');if(b?.matches(':focus-visible'))show(b);});
 document.addEventListener('focusout',hide);document.addEventListener('pointerdown',hide,true);document.addEventListener('keydown',hide,true);window.addEventListener('resize',hide);window.addEventListener('blur',hide);
 window.GigaDevTooltip={hide};
 }if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();})();
