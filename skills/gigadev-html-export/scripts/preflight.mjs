import {createHash} from 'node:crypto';

// Metadata only: never return embedded assets, font sources or full source text.
export function collectCompatibility(){
 const roots=[...document.querySelectorAll('.slide')].filter(e=>!e.parentElement.closest('.slide'));
 const runtime=window.QBRDeck?'qbr':window.GigaDevPreview?'gigadev-preview':'keyboard';
 const qbr=window.QBRDeck?.exportState?.();
 const slides=roots.map((root,i)=>{
  const nodes=[root,...root.querySelectorAll('*')],structure=nodes.map(e=>[e.tagName,[...e.classList].filter(c=>!['active','is-active'].includes(c)).sort().join('.')]);
  const images=[...root.querySelectorAll('img')];
  const counter=!!root.querySelector('.slide-page')||!!document.querySelector('#hud #cn')||[...root.querySelectorAll('svg text')].some(e=>/^\d{1,2}$/.test(e.textContent.trim())&&Number(e.textContent.trim())===i+1);
  const videos=[...root.querySelectorAll('video')].map(v=>({hasSource:!!(v.currentSrc||v.src||v.querySelector('source[src]')),nativeAdapter:runtime==='qbr'&&!!window.QBR_VIDEO_ASSETS?.[qbr?.slides?.find(s=>s.uid===qbr.order?.[i])?.video?.assetId]?.startsWith('data:video/'),hasPoster:!!v.poster}));
  const markers=[...root.querySelectorAll('marker')].map(m=>({id:m.id,supported:m.viewBox.baseVal.width>0&&m.viewBox.baseVal.height>0&&m.querySelectorAll('path').length===1&&!m.querySelector('circle,rect,ellipse,polygon,polyline,line,text,image,use')&&!m.querySelector('path[transform],g[transform]')&&['auto','auto-start-reverse'].includes(m.getAttribute('orient')||'0')}));
  const usedRefs=[...root.querySelectorAll('[marker-start],[marker-end],path,line,polyline')].flatMap(e=>{const c=getComputedStyle(e);return [c.markerStart,c.markerEnd].flatMap(s=>[...s.matchAll(/#([^)'"\s]+)/g)].map(m=>m[1]));});
  const missingMarkers=usedRefs.filter(id=>!document.getElementById(id));
  return {slide:i+1,id:root.id,structure,counter,videos,missingMarkers,unsupportedMarkers:markers.filter(m=>usedRefs.includes(m.id)&&!m.supported).map(m=>m.id),brokenImages:images.filter(e=>e.complete&&!e.naturalWidth&&e.getAttribute('src')&&e.loading!=='lazy').length,remoteImages:images.filter(e=>/^https?:/.test(e.currentSrc||e.src)).length,complexSvg:root.querySelectorAll('filter,mask,clipPath').length,canvas:root.querySelectorAll('canvas').length};
 });
 return {runtime,slides,fontErrors:[...document.fonts].filter(f=>f.status==='error').map(f=>({family:f.family,weight:f.weight}))};
}
export function fingerprint(raw,info){
 return {runtime:raw.runtime,size:[info.w,info.h],orderedSlideIds:raw.slides.map(s=>s.id),structures:raw.slides.map(s=>createHash('sha256').update(JSON.stringify(s.structure)).digest('hex'))};
}
export function matchProfiles(signature,registry){
 return registry.profiles.filter(p=>['runtime','size','orderedSlideIds','structures'].every(k=>JSON.stringify(p.fingerprint?.[k])===JSON.stringify(signature[k])));
}
export async function assessCompatibility(page,info,registry,{wantPptx,groupProfile,autoGroups}){
 const raw=await page.evaluate(collectCompatibility),signature=fingerprint(raw,info),matches=matchProfiles(signature,registry);
 const issues=[],issue=(severity,code,slide,detail)=>issues.push({severity,code,...(slide?{slide}:{}),detail});
 if(matches.length>1)issue('blocker','ambiguous-profile',null,'More than one tested profile matches; fix the registry.');
 const selected=matches.length===1?matches[0]:null;
 if(!selected)issue('review','unknown-structure',null,'No tested profile matches this structure/order. Inspect inventory and adapt if needed.');
 if(!Number.isFinite(info.w)||!Number.isFinite(info.h)||info.w<=0||info.h<=0)issue('blocker','invalid-canvas',null,'Intrinsic canvas dimensions are invalid.');
 if(info.sizeBasis==='default-16:9')issue('review','assumed-canvas',null,'No intrinsic canvas detected; explicitly verify the assumed 1920x1080 size.');
 for(const f of raw.fontErrors)issue('blocker','font-load-error',null,`${f.family} ${f.weight}`);
 if(wantPptx&&!info.faces.length)issue('review','no-embedded-font-source',null,'No embedded font faces detected; cross-device typography may depend on installed fonts.');
 if(wantPptx)for(const f of info.faces)if(!f.src.includes('data:'))issue('blocker','font-pack-adapter-needed',null,`${f.family}: font packing currently needs an embedded data URI; prepare an authorized local working copy.`);
 for(const s of raw.slides){
  if(s.brokenImages)issue('blocker','broken-image',s.slide,`${s.brokenImages} failed image(s).`);
  if(s.remoteImages)issue('review','remote-image',s.slide,'Network capture is blocked; prepare authorized assets locally.');
  if(s.complexSvg)issue('review','complex-svg',s.slide,'Filters/masks/clipping may use per-object raster fallback; inspect the native proof.');
  if(s.canvas)issue('review','static-canvas',s.slide,'Canvas/WebGL is a static capture.');
  if(wantPptx&&!s.counter)issue('blocker','counter-adapter-needed',s.slide,'No supported native-counter candidate; add an explicit adapter.');
  if(wantPptx&&(s.unsupportedMarkers.length||s.missingMarkers.length))issue('blocker','marker-adapter-needed',s.slide,`Unsupported or missing SVG marker(s): ${[...s.unsupportedMarkers,...s.missingMarkers].join(', ')}`);
  for(const v of s.videos){
   if(!v.hasSource)issue('review','video-without-source',s.slide,'Only its visible static state can be captured.');
   if(wantPptx&&!v.nativeAdapter)issue('review','video-static-fallback',s.slide,'No native-video adapter; visible state remains a picture.');
  }
 }
 if(autoGroups&&!selected?.groups)issue('blocker','group-profile-needed',null,'No tested grouping profile for this structure. Supply --groups PROFILE.json after inspection.');
 const publicResult={status:issues.some(i=>i.severity==='blocker')?'blocked':issues.length?'review':'ready',selectedProfile:selected?{id:selected.id,label:selected.label,groups:selected.groups||null}:null,fingerprint:signature,issues};
 return {publicResult,selected,raw,groupProfile};
}
export async function checkGroupSelectors(page,profile){
 if(!profile)return [];
 return await page.evaluate(rules=>{
  const roots=[...document.querySelectorAll('.slide')].filter(e=>!e.parentElement.closest('.slide')),issues=[];
  for(const r of rules)for(const slide of r.slides){let count;try{count=roots[slide-1]?.querySelectorAll(r.selector).length??0}catch{count=-1}
   if(count!==r.expected)issues.push({severity:'blocker',code:'group-selector-count',slide,detail:`${r.name}: ${r.selector}, expected ${r.expected}, found ${count}`});
  }return issues;
 },profile.rules);
}
