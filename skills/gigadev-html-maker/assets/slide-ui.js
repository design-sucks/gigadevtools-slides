/* Per-slide UI contrast follows the active slide's stable ID. */
(() => {
 if(window.__gdSlideUiInstalled)return;window.__gdSlideUiInstalled=true;
 const root=document.documentElement,track=document.getElementById('slides');let queued=false;
 const update=()=>{queued=false;const slide=window.slides?.[window.cur];const mode=slide?.dataset.gdShellInk;if(mode==='light'||mode==='dark')root.dataset.gdShellInk=mode;else delete root.dataset.gdShellInk;};
 const schedule=()=>{if(!queued){queued=true;requestAnimationFrame(update)}};
 track.addEventListener('scroll',schedule,{passive:true});new MutationObserver(schedule).observe(track,{childList:true});window.addEventListener('resize',schedule);update();
})();
