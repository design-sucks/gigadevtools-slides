/* One export contract for browser view, saved order, and native PPTX numbering. */
(()=>{function init(){
 const root=document.documentElement,meta=JSON.parse(document.getElementById('sk-deck-state').textContent);
 const refresh=()=>{
  [...document.querySelectorAll('#slides>.slide')].forEach((s,i)=>{
   s.querySelector('.slide-page').textContent=String(i+1);
   s.dataset.gdNumber=String(i+1);
  });
 };
 new MutationObserver(refresh).observe(document.getElementById('slides'),{childList:true});refresh();
 window.GigaDevDeck={schema:1,shellVersion:'v18.2',canvas:{width:1920,height:1080},getState:()=>SalesKitUI.getState(),
  prepareExport:async({theme='current'}={})=>{
   const availableThemes=meta.themes||['dark'],primaryTheme=meta.primaryTheme||availableThemes[0],currentTheme=SalesKitUI.getState().settings.theme;
   const selected=theme==='current'?currentTheme:theme==='primary'?primaryTheme:theme;
   if(!availableThemes.includes(selected))throw new Error(`Theme ${selected} is not available in this deck`);
   SalesKitUI.setTheme(selected);
   SalesKitText.commit();SalesKitMotion.finish();window.GigaDevTooltip?.hide();window.SalesKitUI.closeOrganizer();window.GigaDevJournal?.close();
   document.querySelectorAll('dialog[open]').forEach(d=>d.close());
   root.removeAttribute('data-sk-present');root.classList.remove('edit-mode');root.dataset.skMotion='off';root.dataset.gdExport='';root.removeAttribute('data-gd-compact');
   document.getElementById('sk-show-meta').hidden=true;refresh();
   await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
   return {order:SalesKitUI.getState().order,canvas:{width:1920,height:1080},title:SalesKitUI.getState().title,theme:selected,primaryTheme,availableThemes};
  }
 };
 document.querySelectorAll('.sk-ui,#navbar,#bread,#sk-show-meta,#sk-progress,#sk-show-controls').forEach(e=>e.dataset.gdChrome='');
}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();})();
