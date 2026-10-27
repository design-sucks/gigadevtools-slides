/* Compact native reading flow; scroll paint and 16:9 composition are independent. */
(()=>{
 const root=document.documentElement,track=document.getElementById('slides');let last=[];
 function apply({scale,viewportHeight,sourceZoom,safeTop,contentTop}){
  const compact=!root.hasAttribute('data-sk-present')&&!root.hasAttribute('data-gd-export');root.toggleAttribute('data-gd-compact',compact);
  root.style.setProperty('--gd-motion-distance',viewportHeight+'px');root.style.setProperty('--gd-scroll-tail','0px');
  const slides=[...track.querySelectorAll(':scope>.slide')];
  for(const s of slides){s.style.removeProperty('--gd-page-height');s.style.removeProperty('--gd-flow-top');s.removeAttribute('data-gd-flow-page');}
  if(!compact){last=[];return;}
  // Preserve the original composition anchor; compact only the page pitch.
  const top=contentTop;
  // v26 body (~742px) plus the shared 18px incoming travel.
  const gap=Math.max(96,Math.round(viewportHeight-sourceZoom*760)),minPitch=viewportHeight*.55;
  const metrics=slides.map(s=>{const box=s.querySelector('.gd-content'),flow=box?.querySelector(':scope>[data-gd-flow]');
   if(!flow)return{slide:s,flow:false,top:contentTop,bottom:contentTop+874*scale,fullBottom:contentTop+874*scale};
   s.setAttribute('data-gd-flow-page','');s.style.setProperty('--gd-flow-top',top+'px');
   const children=[...flow.children].filter(e=>!e.hidden&&getComputedStyle(e).display!=='none'&&e.offsetHeight>0&&!e.hasAttribute('data-gd-tail'));
   const first=children.length?Math.min(...children.map(e=>e.offsetTop)):0,end=children.length?Math.max(...children.map(e=>e.offsetTop+e.offsetHeight)):flow.offsetHeight;
   return{slide:s,flow:true,top:top+first*scale,bottom:top+end*scale,fullBottom:top+Math.max(flow.offsetHeight,flow.scrollHeight)*scale};
  });
  last=metrics.map((m,i)=>{const next=metrics[i+1];let height=viewportHeight;
   if(m.flow)height=Math.ceil(Math.max(minPitch,next?m.bottom+gap-next.top:m.fullBottom+40,next?m.fullBottom+40-next.top:0));
   m.slide.style.setProperty('--gd-page-height',height+'px');return{id:m.slide.dataset.skId,height,primaryTop:m.top,primaryBottom:m.bottom,fullBottom:m.fullBottom,targetGap:gap,flow:m.flow};
  });
  root.style.setProperty('--gd-scroll-tail',Math.max(0,viewportHeight-(last.at(-1)?.height||viewportHeight))+'px');
 }
 window.GigaDevFlow={apply,getState:()=>last.map(x=>({...x}))};
})();
