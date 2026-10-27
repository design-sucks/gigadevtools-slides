
/* SalesKit v25. One small rail for viewing; a separate visual slide organizer. */
(() => {
  function init() {
    'use strict';
    const $ = id => document.getElementById(id), root = document.documentElement;
    const meta = JSON.parse($('sk-deck-state').textContent), palette = JSON.parse($('sk-color-registry').textContent);
    const master = [...$('slides').children].filter(n => n.classList.contains('slide'));
    const byId = new Map(master.map(n => [n.dataset.skId, n])), records = new Map(meta.slides.map(s => [s.id,s]));
    const all = [...byId.keys()], key = `gigadev-html-maker-v01:${root.dataset.skDoc}`, clone = value => JSON.parse(JSON.stringify(value));
    const defaults = {contrast:100,shadows:100,muted:0,saturation:100};
    const finalStates='';
    let staticStyle=$('sk-final-states');if(!staticStyle){staticStyle=document.createElement('style');staticStyle.id='sk-final-states';document.head.append(staticStyle);}staticStyle.textContent='html[data-sk-motion=off] '+finalStates;
    const presets = {original:defaults,projector:{contrast:112,shadows:125,muted:25,saturation:105},tv:{contrast:120,shadows:110,muted:35,saturation:100}};
    const bounds = {contrast:[80,135],shadows:[100,160],muted:[0,60],saturation:[50,120]};
    const clamp = (v,a,b) => Math.max(a,Math.min(b,v));
    function validSettings(value={}) {
      const screen = {};for(const n in defaults)screen[n]=Number.isFinite(value.screen?.[n])?clamp(value.screen[n],...bounds[n]):defaults[n];
      return {theme:(meta.themes||['dark']).includes(value.theme)?value.theme:(meta.themes||['dark'])[0],motion:typeof value.motion==='boolean'?value.motion:!matchMedia('(prefers-reduced-motion: reduce)').matches,screen};
    }
    let settings=validSettings(meta.settings),order=(meta.order||all).filter(id=>byId.has(id));
    let version=meta.version||1,nav=innerWidth>700,nativeShow=false,currentId='',dragId='',toastTimer,thumbURL='',thumbObserver;
    let preparation=clone(meta.preparationChanges||[]);
    let presentationTitle=meta.title||'Презентация',fileStem=meta.fileStem||presentationTitle,organizerDocked=false;
    const opened={title:presentationTitle,fileStem,order:order.slice(),settings:clone(settings),edits:{},preparation:clone(preparation)};
    let saved=clone(opened);
    const label=id=>records.get(id)?.label||'Слайд';
    const current=()=>window.slides?.[window.cur];
    const detail=id=>(byId.get(id)?.querySelector('h1,h2')?.textContent||label(id)).replace(/\s+/g,' ').trim();
    const snapshot=()=>({title:presentationTitle,fileStem,order:order.slice(),settings:clone(settings),edits:window.SalesKitText.snapshot(),preparation:clone(preparation)});
    const signature=value=>JSON.stringify([value.title,value.fileStem,value.order,value.settings,Object.entries(value.edits).sort(([a],[b])=>a.localeCompare(b)),value.preparation||[]]);
    function notice(text) {$('sk-toast').textContent=text;$('sk-toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('sk-toast').hidden=true,2800);}
    function syncDirty() {
      const state=snapshot(),dirty=signature(state)!==signature(saved);
      root.toggleAttribute('data-sk-dirty',dirty);$('sk-status').hidden=!dirty;
      $('sk-reset').disabled=signature(state)===signature(opened);
      return dirty;
    }
    // Net differences between saved snapshots, not a log of every keystroke.
    const originalHTML=new Map(master.flatMap(s=>[...s.querySelectorAll('[data-eid]')].map(n=>[n.dataset.eid,n.innerHTML])));
    const openedHistory=clone(Array.isArray(meta.history)?meta.history:[]);let history=clone(openedHistory);
    function plain(html){const t=document.createElement('template');t.innerHTML=html||'';t.content.querySelectorAll('br').forEach(n=>n.replaceWith('\n'));return t.content.textContent.trim();}
    function diffChanges(base=saved,now=snapshot()){
      const changes=[],names=ids=>ids.map(id=>`${String(records.get(id)?.number||'').padStart(2,'0')} · ${label(id)}`).join('\n');
      for(const id of new Set([...Object.keys(base.edits),...Object.keys(now.edits)])){
        const before=plain(base.edits[id]??originalHTML.get(id)),after=plain(now.edits[id]??originalHTML.get(id));
        if(before!==after){const slide=master.find(s=>[...s.querySelectorAll('[data-eid]')].some(n=>n.dataset.eid===id))?.dataset.skId||'';changes.push({type:'text',slide,field:id,title:`${String(records.get(slide)?.number||'').padStart(2,'0')} · ${label(slide)}`,before,after});}
      }
      const excluded=base.order.filter(id=>!now.order.includes(id)),restored=now.order.filter(id=>!base.order.includes(id));
      if(excluded.length)changes.push({type:'exclude',title:`Убрано из показа: ${excluded.length}`,after:names(excluded)});
      if(restored.length)changes.push({type:'restore',title:`Возвращено в сборку: ${restored.length}`,after:names(restored)});
      const beforeCommon=base.order.filter(id=>now.order.includes(id)),afterCommon=now.order.filter(id=>base.order.includes(id));
      if(JSON.stringify(beforeCommon)!==JSON.stringify(afterCommon)){const moved=afterCommon.filter((id,i)=>beforeCommon[i]!==id),positions=ids=>moved.map(id=>`${String(ids.indexOf(id)+1).padStart(2,'0')} · ${label(id)}`).join('\n');changes.push({type:'order',title:'Изменён порядок слайдов',before:positions(base.order),after:positions(now.order)});}
      for(const [key,title,format] of [['theme','Тема',v=>v==='light'?'Светлая':'Тёмная'],['motion','Анимации',v=>v?'Включены':'Выключены']])if(base.settings[key]!==now.settings[key])changes.push({type:'setting',title,before:format(base.settings[key]),after:format(now.settings[key])});
      const screenNames={contrast:'Контраст',shadows:'Детали в тенях',muted:'Вторичный текст',saturation:'Насыщенность'};
      for(const key in screenNames)if(base.settings.screen[key]!==now.settings.screen[key])changes.push({type:'setting',title:screenNames[key],before:base.settings.screen[key]+'%',after:now.settings.screen[key]+'%'});
      for(const item of now.preparation||[]){const before=(base.preparation||[]).find(p=>p.id===item.id);if(before&&reviewState(before)!==reviewState(item))changes.push({type:'review',slide:item.slide,actor:'user',title:'Решение по автоправке · '+label(item.slide),before:({pending:'На проверке',accepted:'Принято',rejected:'Отклонено'})[reviewState(before)]||'История',after:item.status==='applied'?'Принято':'Отклонено'});}
      return changes;
    }
    function reviewState(item){
      if(!item.sourceId||item.kind==='layout')return 'reference';
      return item.status==='rejected'?'rejected':item.decidedBy==='user'?'accepted':'pending';
    }
    function journalSnapshot(){return {preparation:preparation.map(p=>{const target=[...(byId.get(p.slide)?.querySelectorAll('[data-source-id]')||[])].find(n=>n.dataset.sourceId===p.sourceId),expected=p.status==='applied'?p.after:p.before;return {...clone(p),reviewState:reviewState(p),currentDiffers:target?plain(target.innerHTML)!==String(expected??'').trim():false};}),revisions:clone(history),unsaved:diffChanges(),version,order:order.slice(),slides:all.map(id=>({id,label:label(id),included:order.includes(id)}))};}
    function decidePreparation(id,decision){
      SalesKitText.commit();const item=preparation.find(p=>p.id===id);
      if(!item||reviewState(item)==='reference')return {ok:false,error:'Эта запись доступна только для просмотра'};
      if(!['accept','reject'].includes(decision))return {ok:false,error:'Неизвестное действие'};
      const desired=decision==='accept'?'accepted':'rejected';if(reviewState(item)===desired)return {ok:true,unchanged:true};
      if(!order.includes(item.slide))return {ok:false,error:'Сначала верните слайд в сборку'};
      const target=[...byId.get(item.slide).querySelectorAll('[data-source-id]')].find(n=>n.dataset.sourceId===item.sourceId);
      const wasApplied=item.status==='applied';
      if(decision==='accept'||wasApplied){
        if(!target?.dataset.eid)return {ok:false,error:'Блок правки не найден'};
        const expected=wasApplied?item.after:item.before,next=decision==='accept'?item.after:item.before;
        const result=SalesKitText.apply(target.dataset.eid,expected,next);if(!result.ok)return result;
      }
      item.resolution=decision==='accept'?(wasApplied?'confirmed':'applied'):(wasApplied?'reverted':'kept');
      item.status=decision==='accept'?'applied':'rejected';item.decidedBy='user';item.decidedAt=Date.now();changed();return {ok:true};
    }
    const validVersion=n=>Number.isSafeInteger(n)&&n>0&&n<=999999;
    const nextSaveVersion=()=>Math.max(version,...history.map(r=>r.version).filter(validVersion))+1;
    const cleanStem=text=>(text||'Presentation').trim().replace(/[\\/:*?"<>|\x00-\x1f]/g,'_');
    function reflectIdentity(scope=root,title=presentationTitle,value=version){scope.querySelector('#gd-title').textContent=title;scope.querySelector('#gd-title').title=title;scope.querySelector('.sk-global-section').textContent=title;scope.querySelector('#sk-version').textContent='v'+String(value).padStart(2,'0');scope.querySelector('title').textContent=title+' · v'+String(value).padStart(2,'0');}
    function createRevision(kind,nextVersion,name,identity={}){const title=identity.title||presentationTitle,changes=diffChanges();if(title!==presentationTitle)changes.push({type:'title',title:'Название презентации',before:presentationTitle,after:title});return {version:nextVersion,parentVersion:version,at:Date.now(),name,presentationTitle:title,kind,stage:'editor',actor:'user',note:$('sk-version-note').value.trim(),changes};}
    function saveReview(){const changes=diffChanges();$('sk-save-review-count').textContent=changes.length?`Изменения: ${changes.length}`:'Без новых правок';const host=$('sk-save-review-list');host.replaceChildren();const list=document.createElement('ul');changes.forEach(c=>{const li=document.createElement('li');li.textContent=(c.type==='text'?'Текст: ':'')+c.title;list.append(li);});host.append(list);}

    function changed() {
      syncDirty();
      try{localStorage.setItem(key,JSON.stringify({...snapshot(),updatedAt:Date.now()}));}catch(_){notice('Для сохранения правок создайте новую версию');}
      document.dispatchEvent(new Event('gigadev-journalchange'));
    }
    try {
      const draft=JSON.parse(localStorage.getItem(key)||'null');
      if(draft?.updatedAt>(meta.savedAt||0)&&Array.isArray(draft.order)) {
        const ids=[...new Set(draft.order)].filter(id=>byId.has(id));
        if(ids.length){order=ids;settings=validSettings(draft.settings);SalesKitText.restore(draft.edits||{},false);
          if(Array.isArray(draft.preparation))preparation=preparation.map(p=>{const prior=draft.preparation.find(x=>x.id===p.id);return prior&&['pending','applied','rejected'].includes(prior.status)?{...p,status:prior.status,...(prior.decidedAt?{decidedAt:prior.decidedAt,decidedBy:'user'}:{}),...(['confirmed','applied','reverted','kept'].includes(prior.resolution)?{resolution:prior.resolution}:{})}:p;});}
      }
    } catch(_) {}
    if(!order.length)order=all.slice();

    // The ambient video stays full bleed; only the source composition is fitted.
    if($('slides').parentElement!==$('sk-canvas'))$('sk-canvas').append($('slides'));

    function fit() {
      if(root.hasAttribute('data-gd-export'))return;
      const stage=$('sk-stage'),canvas=$('sk-canvas'),show=root.hasAttribute('data-sk-present');
      if(!show&&nav&&innerWidth>700)root.style.setProperty('--gd-nav-space',Math.max(180,$('bread').offsetWidth+24)+'px');
      const safeTop=show?0:innerWidth<=700?68:72,safeBottom=show?0:56;
      const scale=Math.max(.01,Math.min(stage.clientWidth/1920,Math.max(1,stage.clientHeight-safeTop-safeBottom)/1080));
      // Native scroll distances stay in viewport pixels. Only the content is
      // scaled; scaling the scrollport would slow wheel input and its fade.
      const contentLeft=(stage.clientWidth-1920*scale)/2+112*scale;
      const contentTop=safeTop+(stage.clientHeight-safeTop-safeBottom-1080*scale)/2+120*scale;
      root.style.setProperty('--gd-scroll-height',stage.clientHeight+'px');
      root.style.setProperty('--gd-content-left',contentLeft+'px');
      root.style.setProperty('--gd-content-top',contentTop+'px');
      root.style.setProperty('--gd-view-scale',String(scale));
      // v25's responsive content zoom determines the visible blur/translate.
      const sourceZoom=innerWidth>700?Math.max(.25,Math.floor(Math.min(1.1,(innerWidth-224)/1120,(innerHeight-104)/840)*1000)/1000):1;
      root.style.setProperty('--gd-motion-gain',String(sourceZoom/scale));
      root.style.setProperty('--gd-motion-zoom',String(sourceZoom));
      root.style.setProperty('--gd-content-scale',String(scale/sourceZoom));
      canvas.style.width=stage.clientWidth+'px';canvas.style.height=stage.clientHeight+'px';
      canvas.style.transform='none';
      window.GigaDevFlow.apply({scale,viewportHeight:stage.clientHeight,sourceZoom,safeTop,contentTop});
      if(!window.lockScroll&&current())$('slides').scrollTop=current().offsetTop;
      window.positionBubble?.();window.SalesKitMotion?.finish();
    }
    let fitFrame=0;
    function fitContent(){fit();}
    function scheduleFit(){if(!fitFrame)fitFrame=requestAnimationFrame(()=>{fitFrame=0;fitContent();});}
    function setNav(value){nav=value;root.dataset.skNav=nav?'on':'off';$('sk-sidebar-toggle').setAttribute('aria-pressed',String(nav));$('sk-sidebar-toggle').querySelector('.sk-nav-slash').toggleAttribute('hidden',nav);$('sk-sidebar-toggle').dataset.tip=(nav?'Скрыть список слайдов':'Показать список слайдов')+' · N';$('sk-sidebar-toggle').setAttribute('aria-label',$('sk-sidebar-toggle').dataset.tip);scheduleFit();}
    function editorMode(){root.toggleAttribute('data-sk-edit',root.classList.contains('edit-mode'));fit();}
    function updateLabel(id,value){if($(id).textContent!==value)$(id).textContent=value;}
    function syncCurrent() {
      currentId=current()?.dataset.skId||'';
      if(document.activeElement!==$('sk-page'))$('sk-page').value=window.cur+1;
      $('sk-page').max=order.length;$('sk-page-total').textContent='/ '+order.length;
      $('sk-prev').disabled=window.cur<=0;$('sk-next').disabled=window.cur>=order.length-1;
      const slide=current();
      if(slide){updateLabel('sk-show-section',slide.dataset.skSection||'');updateLabel('sk-show-topic',slide.dataset.skTopic||label(currentId));const mode=slide.dataset.gdHeader||'full';$('sk-show-meta').hidden=!root.hasAttribute('data-sk-present')||mode==='none';$('sk-show-meta').querySelector('.sk-slide-crumbs').hidden=mode==='number';$('sk-show-section').hidden=!slide.dataset.skSection;$('sk-show-section').nextElementSibling.hidden=!slide.dataset.skSection;}
      updateLabel('sk-show-count',String(window.cur+1).padStart(2,'0'));
      const progress=$('sk-progress'),input=$('sk-progress-input');input.max=String(Math.max(0,order.length-1));input.value=String(window.cur);input.disabled=order.length<2;input.setAttribute('aria-valuetext',`Слайд ${window.cur+1} из ${order.length}`);progress.style.setProperty('--sk-progress',`${order.length<2?100:window.cur/(order.length-1)*100}%`);
      $('sk-grid').querySelectorAll('.sk-card').forEach(n=>n.toggleAttribute('data-active',n.dataset.id===currentId));
    }
    function rebuildNav() {
      window.slides=$('slides').querySelectorAll(':scope>.slide');window.total=window.slides.length;
      window.breadLabels=order.map(label);window.breadLabelsCopy=window.breadLabels;
      $('navbar').replaceChildren();$('bread').querySelectorAll('.bread-item').forEach(n=>n.remove());$('mobmenu')?.replaceChildren();
      order.forEach((id,index)=>{
        const dot=document.createElement('button');dot.className='nav-dot';dot.onclick=()=>goTo(index);$('navbar').append(dot);
        const b=document.createElement('button');b.type='button';b.className='bread-item';b.title=detail(id);
        const num=document.createElement('span');num.className='bd-num';num.textContent=String(index+1).padStart(2,'0');
        const text=document.createElement('span');text.className='bd-label';text.textContent=label(id);b.append(num,text);b.onclick=()=>goTo(index);$('bread').append(b);
      });
      scheduleFit();
    }
    const originalGoTo=window.goTo;window.goTo=function(n){SalesKitText.commit();return originalGoTo(n);};
    const originalUpdate=window.updateUI;
    window.updateUI=function(){originalUpdate();syncCurrent();document.dispatchEvent(new Event('gigadev-slidechange'));};
    function applyOrder(keep=current()?.dataset.skId) {
      stopAnims();window.lockScroll=false;master.forEach(n=>n.remove());order.forEach(id=>$('slides').append(byId.get(id)));
      rebuildNav();window.cur=Math.max(0,order.indexOf(keep));$('slides').scrollTop=window.slides[window.cur].offsetTop;updateUI();setInitialVidFrame();
    }
    function setOrder(next){order=next;applyOrder();renderGrid();changed();}
    function include(id,on){if(!on&&order.length===1){notice('Оставьте хотя бы один слайд');return;}setOrder(on?[...order,id]:order.filter(x=>x!==id));}
    function move(id,delta){const i=order.indexOf(id),j=i+delta;if(i<0||j<0||j>=order.length)return;const next=order.slice();[next[i],next[j]]=[next[j],next[i]];setOrder(next);$('sk-grid').querySelector(`[data-id="${id}"] .sk-card-select input`)?.focus();}

    function adjusted(color,muted) {
      const s=settings.screen,rgba=(settings.theme==='light'?color.light:color.dark).slice(),ink=settings.theme==='light'?[.09,.12,.08]:[.92,.94,.91];
      let rgb=rgba.slice(0,3).map(v=>v/255),l=rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722;
      rgb=rgb.map(v=>clamp(l+(v-l)*s.saturation/100,0,1));
      rgb=rgb.map(v=>clamp((Math.pow(v,100/s.shadows)-.5)*s.contrast/100+.5,0,1));
      if(muted)rgb=rgb.map((v,i)=>v*(1-s.muted/100)+ink[i]*s.muted/100);
      return `rgba(${rgb.map(v=>Math.round(v*255)).join(',')},${rgba[3]})`;
    }
    function applySettings() {
      $('sk-theme').hidden=(meta.themes||['dark']).length<2;root.dataset.skTheme=settings.theme;root.dataset.skMotion=settings.motion?'on':'off';root.classList.toggle('js-anim',settings.motion);
      $('sk-colors').textContent=':root{'+palette.map(c=>`${c.name}:${adjusted(c,c.muted)};`).join('')+'}';
      const light=settings.theme==='light';$('sk-theme').setAttribute('aria-pressed',String(light));
      $('sk-theme').setAttribute('aria-label',light?'Тёмная тема слайдов':'Светлая тема слайдов');$('sk-theme').dataset.tip=(light?'Тёмная тема':'Светлая тема')+' · T';
      $('sk-theme').querySelector('.sk-sun').toggleAttribute('hidden',light);$('sk-theme').querySelector('.sk-moon').toggleAttribute('hidden',!light);
      $('sk-motion').setAttribute('aria-pressed',String(settings.motion));$('sk-motion').setAttribute('aria-label',settings.motion?'Анимации включены':'Анимации выключены');$('sk-motion').dataset.tip=(settings.motion?'Анимации включены':'Анимации выключены')+' · M';
      $('sk-motion').querySelector('.sk-motion-slash').toggleAttribute('hidden',settings.motion);
      if(!settings.motion){stopAnims();window.lockScroll=false;document.querySelectorAll('.gt-num[data-sk-final]').forEach(n=>n.textContent=n.dataset.skFinal);if(current())$('slides').scrollTop=current().offsetTop;}
      const active=Object.keys(defaults).some(n=>settings.screen[n]!==defaults[n]);$('sk-screen-open').querySelector('.sk-active-dot').hidden=!active;
      for(const n in defaults){$('sk-screen-panel').querySelector(`[name="${n}"]`).value=settings.screen[n];$('sk-screen-panel').querySelector(`[data-screen-value="${n}"]`).textContent=settings.screen[n]+'%';}
      $('sk-screen-panel').querySelectorAll('[data-screen-preset]').forEach(b=>b.setAttribute('aria-pressed',String(JSON.stringify(settings.screen)===JSON.stringify(presets[b.dataset.screenPreset]))));
      if(thumbURL){URL.revokeObjectURL(thumbURL);thumbURL='';}
    }

    const picked=new Set();let selectionAnchor='';
    function syncSelection(){
      const visible=[...$('sk-grid').querySelectorAll('.sk-card')],visiblePicked=visible.filter(n=>picked.has(n.dataset.id));
      visible.forEach(n=>{const on=picked.has(n.dataset.id);n.toggleAttribute('data-picked',on);n.querySelector('.sk-card-select input').checked=on;});
      $('sk-select-all').checked=!!visible.length&&visiblePicked.length===visible.length;$('sk-select-all').indeterminate=visiblePicked.length>0&&visiblePicked.length<visible.length;$('sk-select-all').disabled=!visible.length;
      $('sk-selection-label').textContent=picked.size?`Выбрано: ${picked.size}`:($('sk-search').value?'Выбрать найденные':'Выбрать все');$('sk-bulk-actions').hidden=!picked.size;
      const included=[...picked].filter(id=>order.includes(id)).length,excluded=picked.size-included;
      $('sk-bulk-exclude').textContent=`Убрать ${included}`;$('sk-bulk-exclude').disabled=!included;$('sk-bulk-exclude').hidden=!included;$('sk-bulk-restore').textContent=`Вернуть ${excluded} в конец`;$('sk-bulk-restore').disabled=!excluded;$('sk-bulk-restore').hidden=!excluded;
    }
    function selectCard(id,on,range=false){const visible=[...$('sk-grid').querySelectorAll('.sk-card')].map(n=>n.dataset.id),a=visible.indexOf(selectionAnchor),b=visible.indexOf(id);const ids=range&&a>=0?visible.slice(Math.min(a,b),Math.max(a,b)+1):[id];ids.forEach(x=>on?picked.add(x):picked.delete(x));selectionAnchor=id;syncSelection();}
    function bulk(on){const ids=all.filter(id=>picked.has(id)&&order.includes(id)!==on);if(!ids.length)return;const next=on?[...order,...ids]:order.filter(id=>!ids.includes(id));if(!next.length){notice('Оставьте хотя бы один слайд');return;}picked.clear();setOrder(next);notice(on?`В конец сборки добавлено: ${ids.length}`:`Убрано из показа: ${ids.length}`);}
    $('sk-select-all').onchange=()=>{const on=$('sk-select-all').checked;$('sk-grid').querySelectorAll('.sk-card').forEach(n=>on?picked.add(n.dataset.id):picked.delete(n.dataset.id));syncSelection();};
    $('sk-selection-clear').onclick=()=>{picked.clear();syncSelection();};$('sk-bulk-exclude').onclick=()=>bulk(false);$('sk-bulk-restore').onclick=()=>bulk(true);

    function thumbStyles() {
      if(thumbURL)return thumbURL;
      let css='';for(const sheet of document.styleSheets){if(sheet.ownerNode.id==='sk-ui-styles')continue;try{css+=[...sheet.cssRules].map(r=>r.cssText).join('\n');}catch(_){}}
      css+='\nhtml,body,.slides{margin:0!important;width:1600px!important;height:900px!important;overflow:hidden!important}.slide{width:1920px!important;height:1080px!important;min-height:1080px!important;padding:0!important}.slides{width:1920px!important;height:1080px!important}html,body{width:1920px!important;height:1080px!important}.slide *{animation:none!important;transition:none!important}.sk-slide-meta{display:none!important}.hitl-wrap .ln path{stroke-dasharray:none!important;stroke-dashoffset:0!important;opacity:1!important}video,audio,iframe{display:none!important}.proto-preview{display:block!important}.prot-tour .call{opacity:0!important}';
      thumbURL=URL.createObjectURL(new Blob([css],{type:'text/css'}));return thumbURL;
    }
    function loadThumb(box) {
      if(box.querySelector('iframe'))return;
      const id=box.closest('.sk-card').dataset.id,node=byId.get(id).cloneNode(true);
      node.querySelectorAll('.gt-num[data-sk-final]').forEach(n=>n.textContent=n.dataset.skFinal);
      node.querySelectorAll('iframe').forEach(n=>n.remove());
      node.style.removeProperty('--gd-page-height');node.style.removeProperty('--gd-flow-top');node.removeAttribute('data-gd-flow-page');const inner=node.querySelector('.slide-inner');inner.style.zoom='1';
      const frame=document.createElement('iframe');frame.title='Превью: '+label(id);frame.tabIndex=-1;frame.setAttribute('aria-hidden','true');frame.setAttribute('sandbox','allow-same-origin');
      frame.style.transform=`scale(${box.clientWidth/1920})`;
      frame.srcdoc=`<!doctype html><html lang="ru" data-sk-theme="${settings.theme}" data-sk-motion="off"><head><meta charset="UTF-8"><link rel="stylesheet" href="${thumbStyles()}"></head><body><div class="bg-grid"></div><div class="bg-glow"></div><div class="slides">${id==='s1'?'':'<i hidden></i>'}${node.outerHTML}</div></body></html>`;
      box.append(frame);
    }
    function renderGrid() {
      if(!$('sk-organizer').open)return;
      thumbObserver?.disconnect();const query=$('sk-search').value.trim().toLocaleLowerCase('ru'),included=new Set(order),grid=$('sk-grid');grid.replaceChildren();
      thumbObserver=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){loadThumb(e.target);thumbObserver.unobserve(e.target);}}),{root:$('sk-grid-scroll'),rootMargin:'150px'});
      let excluded=false,shown=0;
      for(const id of [...order,...all.filter(x=>!included.has(x))]) {
        if(query&&!`${label(id)} ${detail(id)} ${records.get(id)?.number}`.toLocaleLowerCase('ru').includes(query))continue;
        const selected=included.has(id),index=order.indexOf(id);
        if(!selected&&!excluded){const h=document.createElement('div');h.className='sk-excluded-label';h.textContent='Исключены из показа';grid.append(h);excluded=true;}
        shown++;const card=document.createElement('article');card.className='sk-card';card.dataset.id=id;card.setAttribute('role','listitem');if(!selected)card.dataset.excluded='';
        const checkLabel=document.createElement('label');checkLabel.className='sk-card-select';const check=document.createElement('input');check.type='checkbox';check.setAttribute('aria-label','Выбрать: '+label(id));check.onclick=e=>{e.stopPropagation();selectCard(id,check.checked,e.shiftKey);};checkLabel.append(check);card.append(checkLabel);
        const box=document.createElement('div');box.className='sk-thumb';box.setAttribute('aria-hidden','true');
        const placeholder=document.createElement('span');placeholder.className='sk-thumb-placeholder';placeholder.textContent=String(records.get(id)?.number).padStart(2,'0');box.append(placeholder);
        card.onclick=e=>{if(e.target.closest('.sk-card-select,.sk-card-tools'))return;if(organizerDocked&&selected){goTo(order.indexOf(id));return;}selectCard(id,!picked.has(id),e.shiftKey);check.focus({preventScroll:true});};
        card.onkeydown=e=>{if(e.altKey&&['ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();move(id,e.key==='ArrowUp'?-1:1);}};
        card.append(box);const row=document.createElement('div');row.className='sk-card-meta';
        const number=document.createElement('span');number.className='sk-card-number';number.textContent=selected?String(index+1).padStart(2,'0'):'—';
        const name=document.createElement('span');name.className='sk-card-label';name.textContent=label(id);name.title=detail(id);const copy=document.createElement('div');copy.className='sk-card-copy';const subtitle=document.createElement('span');subtitle.className='sk-card-detail';subtitle.textContent=(byId.get(id).dataset.skSection||'')+' · '+detail(id);copy.append(name,subtitle);row.append(number,copy);
        const tools=document.createElement('div');tools.className='sk-card-tools';
        for(const delta of [-1,1]){const b=document.createElement('button');b.type='button';b.className='sk-button';b.setAttribute('aria-label',`${delta<0?'Выше':'Ниже'}: ${label(id)}`);b.title=delta<0?'Выше · Alt+↑':'Ниже · Alt+↓';b.disabled=!selected||(delta<0?index===0:index===order.length-1);b.innerHTML=`<svg viewBox="0 0 24 24"><path d="${delta<0?'m6 14 6-6 6 6':'m6 10 6 6 6-6'}"/></svg>`;b.onclick=()=>move(id,delta);tools.append(b);}
        const toggle=document.createElement('button');toggle.type='button';toggle.className=selected?'sk-button sk-danger':'sk-button';toggle.dataset.action='include';toggle.setAttribute('aria-label',`${selected?'Исключить':'Вернуть в конец сборки'}: ${label(id)}`);toggle.title=selected?'Убрать из показа':'Вернуть в конец сборки';toggle.innerHTML=`<svg viewBox="0 0 24 24">${selected?'<path d="m6 6 12 12M6 18 18 6"/>':'<path d="M12 5v14M5 12h14"/>'}</svg>`;toggle.onclick=()=>include(id,!selected);tools.append(toggle);row.append(tools);card.append(row);
        card.draggable=selected;card.ondragstart=e=>{if(!selected||e.target.closest('input,button')){e.preventDefault();return;}dragId=id;e.dataTransfer.setData('text/plain',id);e.dataTransfer.effectAllowed='move';};
        card.ondragover=e=>{if(dragId&&selected&&dragId!==id){e.preventDefault();card.dataset.drop=e.clientY<card.getBoundingClientRect().top+card.offsetHeight/2?'before':'after';}};card.ondragleave=e=>{if(!card.contains(e.relatedTarget))card.removeAttribute('data-drop');};
        card.ondrop=e=>{e.preventDefault();if(!dragId||!selected||dragId===id)return;const next=order.filter(x=>x!==dragId);next.splice(next.indexOf(id)+(card.dataset.drop==='after'?1:0),0,dragId);dragId='';setOrder(next);};
        card.ondragend=()=>{dragId='';grid.querySelectorAll('[data-drop]').forEach(n=>n.removeAttribute('data-drop'));};
        grid.append(card);thumbObserver.observe(box);
      }
      $('sk-empty').hidden=shown>0;$('sk-slide-count').textContent=`${order.length} / ${master.length}`;syncCurrent();syncSelection();
    }
    let organizerView='list';try{if(localStorage.getItem('saleskit-organizer-view')==='grid')organizerView='grid';}catch(_){}
    function resizeThumbs(){$('sk-grid').querySelectorAll('.sk-thumb iframe').forEach(frame=>frame.style.transform=`scale(${frame.parentElement.clientWidth/1920})`);}
    function setView(view,remember=true){
      const scroll=$('sk-grid-scroll'),top=scroll.getBoundingClientRect().top;
      const anchor=[...$('sk-grid').querySelectorAll('.sk-card')].find(n=>n.getBoundingClientRect().bottom>top+2),offset=anchor?anchor.getBoundingClientRect().top-top:0;
      if(!organizerDocked)organizerView=view;$('sk-grid').dataset.view=organizerDocked?'list':view;document.querySelectorAll('[data-sk-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.skView===view)));
      resizeThumbs();if(anchor)scroll.scrollTop+=anchor.getBoundingClientRect().top-top-offset;
      if(remember)try{localStorage.setItem('saleskit-organizer-view',view);}catch(_){}
    }
    document.querySelectorAll('[data-sk-view]').forEach(b=>b.onclick=()=>setView(b.dataset.skView));
    setView(organizerView,false);
    function syncOrganizer(){const open=$('sk-organizer').open;$('sk-build-open').setAttribute('aria-expanded',String(open));$('sk-build-open').dataset.tip=(open?'Закрыть порядок слайдов':'Порядок слайдов')+' · O';$('sk-build-beside').setAttribute('aria-pressed',String(organizerDocked));$('sk-build-expand').setAttribute('aria-pressed',String(!organizerDocked));$('sk-organizer').querySelector('.sk-organizer-footer>span').textContent=organizerDocked?'Карточка — просмотр · ↑/↓ — порядок':'Карточка — выбор · Shift — диапазон · Alt + ↑/↓ — порядок';}
    function releaseOrganizer(){organizerDocked=false;root.removeAttribute('data-sk-organizer-dock');$('sk-organizer').classList.remove('sk-organizer-docked');syncOrganizer();fit();}
    function closeOrganizer(){closeScreen();closeWindow('sk-organizer','sk-build-open');releaseOrganizer();}
    function openOrganizer(mode='slide'){
      SalesKitText.commit();closeScreen();window.GigaDevJournal?.close();const dialog=$('sk-organizer'),wasOpen=dialog.open;
      if(wasOpen)dialog.close();else{picked.clear();selectionAnchor='';}
      organizerDocked=mode!=='full';root.toggleAttribute('data-sk-organizer-dock',organizerDocked);dialog.classList.toggle('sk-organizer-docked',organizerDocked);
      organizerDocked?dialog.show():dialog.showModal();syncToolbarLayer();syncOrganizer();fit();renderGrid();setView(organizerView,false);
    }
    $('sk-organizer').addEventListener('close',()=>{if($('sk-organizer').open)return;releaseOrganizer();thumbObserver?.disconnect();$('sk-grid').replaceChildren();if(thumbURL){URL.revokeObjectURL(thumbURL);thumbURL='';}});
    // Keep the single existing toolbar interactive in a native modal workspace.
    const toolbar=$('sk-header'),toolbarHome=document.createComment('toolbar-home');toolbar.before(toolbarHome);
    function syncToolbarLayer(){const host=document.querySelector('#sk-journal:modal,#sk-organizer:modal');root.toggleAttribute('data-sk-toolbar-workspace',!!host);if(host){if(toolbar.parentElement!==host)host.append(toolbar);root.style.setProperty('--sk-workspace-top',(toolbar.getBoundingClientRect().bottom+12)+'px');}else{if(toolbar.previousSibling!==toolbarHome)toolbarHome.after(toolbar);root.style.removeProperty('--sk-workspace-top');}}
    for(const id of['sk-journal','sk-organizer'])$(id).addEventListener('close',syncToolbarLayer);
    const screenPanel=$('sk-screen-panel'),screenHome=document.createComment('screen-panel-home');screenPanel.before(screenHome);let screenOwner=null;
    function placeScreen(){if(!screenOwner||screenPanel.hidden)return;const r=screenOwner.getBoundingClientRect(),w=screenPanel.offsetWidth,h=screenPanel.offsetHeight;screenPanel.style.left=Math.max(12,Math.min(innerWidth-w-12,r.right-w))+'px';screenPanel.style.top=Math.max(12,Math.min(innerHeight-h-12,r.bottom+10))+'px';}
    function closeWindow(id,trigger){const dialog=$(id),hadFocus=dialog.contains(document.activeElement);dialog.close();syncToolbarLayer();if(hadFocus){const button=$(trigger);(button&&!button.disabled&&!button.hidden?button:$('sk-save-open')).focus({preventScroll:true});}}
    function closeScreen(){if(screenPanel.matches(':popover-open'))screenPanel.hidePopover();screenPanel.hidden=true;screenHome.after(screenPanel);screenOwner=null;document.querySelectorAll('[data-sk-screen-open]').forEach(b=>b.setAttribute('aria-expanded','false'));}
    function openScreen(button){if(!screenPanel.hidden){closeScreen();return;}screenOwner=button;const host=button.closest('dialog:modal');if(host)host.append(screenPanel);screenPanel.hidden=false;if(screenPanel.showPopover)screenPanel.showPopover();document.querySelectorAll('[data-sk-screen-open]').forEach(b=>b.setAttribute('aria-expanded','true'));placeScreen();}
    for(const id of['sk-journal','sk-organizer'])$(id).addEventListener('close',()=>{if(screenPanel.closest('dialog')?.id===id)closeScreen();});
    window.addEventListener('resize',()=>{syncToolbarLayer();placeScreen();});
    function resetOpened(){SalesKitText.close();SalesKitText.restore(opened.edits,false);order=opened.order.slice();settings=clone(opened.settings);version=meta.version||1;presentationTitle=meta.title||'Презентация';fileStem=meta.fileStem||presentationTitle;reflectIdentity();history=clone(openedHistory);preparation=clone(opened.preparation);picked.clear();saved=clone(opened);applyOrder();applySettings();$('sk-version').textContent='v'+String(version).padStart(2,'0');try{localStorage.removeItem(key);}catch(_){}syncDirty();closeWindow('sk-reset-dialog','sk-reset');document.dispatchEvent(new Event('gigadev-journalchange'));notice('Открытая версия восстановлена');}

    async function exitPresent(){root.removeAttribute('data-sk-present');$('sk-exit-present').hidden=true;$('sk-show-meta').hidden=true;$('sk-progress').hidden=true;nativeShow=false;fit();if(document.fullscreenElement||document.webkitFullscreenElement)try{await(document.exitFullscreen||document.webkitExitFullscreen).call(document);}catch(_){} }
    async function present(){if(root.hasAttribute('data-sk-present'))return exitPresent();if(root.classList.contains('edit-mode'))$('editBtn').click();closeScreen();closeOrganizer();window.GigaDevJournal?.close();root.setAttribute('data-sk-present','');$('sk-exit-present').hidden=false;$('sk-show-meta').hidden=false;$('sk-progress').hidden=false;syncCurrent();document.activeElement?.blur();fit();try{const enter=root.requestFullscreen||root.webkitRequestFullscreen;if(enter){await enter.call(root);nativeShow=true;}}catch(_){}fit();}
    const fullscreen=()=>{if(nativeShow&&!(document.fullscreenElement||document.webkitFullscreenElement))exitPresent();fit();};document.addEventListener('fullscreenchange',fullscreen);document.addEventListener('webkitfullscreenchange',fullscreen);
    function exportDocument(kind,nextVersion=nextSaveVersion(),revision=null,identity={}) {
      SalesKitText.commit();if(!['work','bundle'].includes(kind)||!validVersion(nextVersion)||nextVersion<nextSaveVersion())throw Error('Укажите следующий номер версии');const outputTitle=identity.title||presentationTitle,outputStem=identity.fileStem||fileStem;revision??=createRevision(kind,nextVersion,outputStem+'_v'+String(nextVersion).padStart(2,'0')+'.html',{title:outputTitle});
      const ids=kind==='bundle'?order.slice():all.slice(),copy=root.cloneNode(true),box=copy.querySelector('#slides');box.replaceChildren();ids.forEach(id=>box.append(byId.get(id).cloneNode(true)));
      copy.querySelector('body').prepend(copy.querySelector('#sk-header'));copy.querySelector('body').prepend(copy.querySelector('#sk-stage'));copy.querySelector('body').append(copy.querySelector('#sk-screen-panel'));copy.querySelector('#sk-screen-panel').removeAttribute('style');copy.querySelectorAll('[data-sk-screen-open]').forEach(b=>b.setAttribute('aria-expanded','false'));copy.dataset.skDoc='sk-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,7);
      copy.style.removeProperty('--sk-deck-zoom');copy.style.removeProperty('--sk-workspace-top');copy.style.removeProperty('--gd-motion-distance');copy.style.removeProperty('--gd-scroll-tail');copy.querySelectorAll('#slides>.slide').forEach(s=>{s.style.removeProperty('--gd-page-height');s.style.removeProperty('--gd-flow-top');s.removeAttribute('data-gd-flow-page');});copy.classList.remove('edit-mode');for(const attr of ['data-sk-edit','data-sk-present','data-sk-dirty','data-sk-fit','data-sk-motion-ready','data-sk-journal-dock','data-sk-organizer-dock','data-sk-toolbar-workspace','data-gd-compact'])copy.removeAttribute(attr);
      copy.querySelectorAll('dialog[open]').forEach(n=>n.removeAttribute('open'));copy.querySelector('#sk-organizer').classList.remove('sk-organizer-docked');copy.querySelector('#sk-build-beside').setAttribute('aria-pressed','true');copy.querySelector('#sk-build-expand').setAttribute('aria-pressed','false');for(const id of ['sk-build-open','sk-journal-open'])copy.querySelector('#'+id).setAttribute('aria-expanded','false');copy.querySelector('#sk-tooltip').textContent='';copy.querySelectorAll('[aria-describedby=sk-tooltip]').forEach(n=>n.removeAttribute('aria-describedby'));copy.querySelector('#sk-journal').classList.remove('sk-journal-docked');copy.querySelector('#sk-journal-beside').setAttribute('aria-pressed','true');copy.querySelector('#sk-journal-expand').setAttribute('aria-pressed','false');copy.querySelector('#sk-journal-context').hidden=true;copy.querySelector('#sk-grid').replaceChildren();copy.querySelector('#sk-current-changes').replaceChildren();copy.querySelector('#sk-preparation-changes').replaceChildren();copy.querySelector('#sk-saved-history').replaceChildren();copy.querySelector('#sk-save-review-list').replaceChildren();copy.querySelector('#sk-canvas').removeAttribute('style');
      for(const id of ['sk-show-meta','sk-progress','sk-progress-preview','sk-bulk-actions','sk-text-tools','sk-screen-panel','sk-status','sk-toast','sk-exit-present'])copy.querySelector('#'+id).hidden=true;
      copy.querySelector('#sk-reset').disabled=true;copy.querySelector('#editBtn').setAttribute('aria-pressed','false');copy.querySelector('#sk-screen-open').setAttribute('aria-expanded','false');
      copy.querySelectorAll('.slide-inner').forEach(n=>{n.style.removeProperty('--sk-slide-zoom');n.style.removeProperty('--sk-layout-width');});
      copy.querySelectorAll('[contenteditable],[data-sk-editing]').forEach(n=>{n.removeAttribute('contenteditable');n.removeAttribute('data-sk-editing');n.removeAttribute('spellcheck');});copy.querySelector('#navbar').replaceChildren();copy.querySelector('#bread').querySelectorAll('.bread-item').forEach(n=>n.remove());
      copy.querySelectorAll('.gt-num[data-sk-final]').forEach(n=>n.textContent=n.dataset.skFinal);copy.querySelectorAll('#slides iframe[srcdoc]').forEach(n=>n.removeAttribute('srcdoc'));
      copy.querySelector('#prottour')?.classList.remove('off');for(const selector of ['#protLegend','#protopreview','#protctamob']){const n=copy.querySelector(selector);if(n){n.style.removeProperty('display');n.hidden=false;}}
      copy.querySelectorAll('.cc-overlay,#wpOv').forEach(n=>n.classList.remove('open'));
      const safe=value=>JSON.stringify(value).replace(/</g,'\\u003c');
      const cleanHistory=identity.clearHistory===true,retainedRevision=cleanHistory?{...revision,changes:[],historyCleared:true}:revision;
      const journalHistory=(cleanHistory?[retainedRevision]:[...history,revision]).map(r=>({...r,changes:kind==='bundle'?(r.changes||[]).filter(c=>c.slide?ids.includes(c.slide):['setting','title'].includes(c.type)):(r.changes||[])}));
      copy.querySelector('#sk-deck-state').textContent=safe({...meta,title:outputTitle,fileStem:outputStem,slides:ids.map(id=>records.get(id)),order:order.slice(),settings:clone(settings),version:nextVersion,savedAt:Date.now(),history:journalHistory,preparationChanges:cleanHistory?[]:clone(preparation.filter(p=>ids.includes(p.slide)))});
      reflectIdentity(copy,outputTitle,nextVersion);
      copy.querySelectorAll('script').forEach(script=>{if(script.id==='sk-controller'||script.type==='application/json')return;if(script.textContent.includes('var breadLabels=['))script.textContent=script.textContent.replace(/var breadLabels=\[[\s\S]*?\];/,'var breadLabels='+JSON.stringify(ids.map(label))+';');});
      return '<!DOCTYPE html>\n'+copy.outerHTML;
    }
    let suggestedFile='';
    function suggestFile(){const field=$('sk-file-name'),auto=!field.value.trim()||field.value===suggestedFile;const title=$('sk-presentation-title').value.trim(),value=Number($('sk-save-version').value);suggestedFile=cleanStem(title||presentationTitle)+'_v'+String(validVersion(value)?value:nextSaveVersion()).padStart(2,'0');if(auto)field.value=suggestedFile;}
    function openSave(){SalesKitText.commit();closeScreen();$('sk-presentation-title').value=presentationTitle;$('sk-presentation-title').setCustomValidity('');$('sk-save-version').min=String(nextSaveVersion());$('sk-save-version').value=String(nextSaveVersion());$('sk-save-version').setCustomValidity('');syncVersionStepper();suggestedFile=cleanStem(fileStem)+'_v'+String(nextSaveVersion()).padStart(2,'0');$('sk-file-name').value=suggestedFile;$('sk-save-selected').textContent=`${order.length} из ${master.length} слайдов`;$('sk-version-note').value='';$('sk-clear-history').checked=false;const journalBytes=new TextEncoder().encode(JSON.stringify({preparationChanges:preparation,history})).length;$('sk-history-size').textContent='≈ '+(journalBytes<1024?journalBytes+' Б':(journalBytes/1024).toLocaleString('ru-RU',{maximumFractionDigits:1})+' КБ');saveReview();$('sk-save-dialog').showModal();const name=$('sk-file-name');name.focus({preventScroll:true});name.select();}
    $('sk-presentation-title').oninput=()=>{$('sk-presentation-title').setCustomValidity('');suggestFile();};$('sk-save-version').oninput=()=>{$('sk-save-version').setCustomValidity('');syncVersionStepper();suggestFile();};
    function syncVersionStepper(){const f=$('sk-save-version'),v=Number(f.value);$('sk-version-down').disabled=!!f.value&&v<=Number(f.min);$('sk-version-up').disabled=!!f.value&&v>=Number(f.max);}
    for(const [id,delta]of[['sk-version-down',-1],['sk-version-up',1]])$(id).onclick=()=>{const f=$('sk-save-version');f.stepUp(delta);f.dispatchEvent(new Event('input',{bubbles:true}));};
    $('sk-save-form').onsubmit=event=>{
      event.preventDefault();try{
        const title=$('sk-presentation-title').value.trim(),next=Number($('sk-save-version').value);if(!title){$('sk-presentation-title').setCustomValidity('Введите название презентации');$('sk-presentation-title').reportValidity();return;}if(!validVersion(next)||next<nextSaveVersion()){$('sk-save-version').setCustomValidity('Следующая версия — '+nextSaveVersion()+' или выше');$('sk-save-version').reportValidity();return;}
        const name=(cleanStem($('sk-file-name').value||fileStem)).replace(/\.html?$/i,'')+'.html',kind=$('sk-save-form').querySelector('[name=save-kind]:checked').value,identity={title,fileStem:name.replace(/\.html?$/i,'').replace(/[_ -]v\d+$/i,'')||cleanStem(title)};
        identity.clearHistory=$('sk-clear-history').checked;const revision=createRevision(kind,next,name,identity);if(identity.clearHistory){revision.changes=[];revision.historyCleared=true;}const text=exportDocument(kind,next,revision,identity),url=URL.createObjectURL(new Blob([text],{type:'text/html;charset=utf-8'})),link=document.createElement('a');link.href=url;link.download=name;document.body.append(link);link.click();setTimeout(()=>{URL.revokeObjectURL(url);link.remove();},1000);
        closeWindow('sk-save-dialog','sk-save-open');if(kind==='work'){if(identity.clearHistory){history=[revision];preparation=[];}else history.push(revision);version=next;presentationTitle=title;fileStem=identity.fileStem;reflectIdentity();saved=snapshot();syncDirty();document.dispatchEvent(new Event('gigadev-journalchange'));}$('sk-version-note').value='';notice('v'+String(next).padStart(2,'0')+' передана в загрузки');
      }catch(error){notice('Не удалось создать версию: '+error.message);}
    };

    function progressPreview(index,x){const preview=$('sk-progress-preview');preview.textContent=String(index+1).padStart(2,'0')+' · '+(byId.get(order[index])?.dataset.skTopic||label(order[index]));preview.hidden=false;const half=preview.offsetWidth/2+12;$('sk-progress').style.setProperty('--sk-preview-x',clamp(x??(index/Math.max(1,order.length-1)*innerWidth),half,innerWidth-half)+'px');}
    $('sk-progress').onpointermove=e=>progressPreview(clamp(Math.round(e.clientX/innerWidth*(order.length-1)),0,order.length-1),e.clientX);
    $('sk-progress').onpointerleave=()=>{if(document.activeElement!==$('sk-progress-input'))$('sk-progress-preview').hidden=true;};
    $('sk-progress-input').onfocus=()=>progressPreview(Number($('sk-progress-input').value));$('sk-progress-input').onblur=()=>$('sk-progress-preview').hidden=true;
    $('sk-progress-input').addEventListener('pointerup',()=>requestAnimationFrame(()=>$('sk-progress-input').blur()));
    $('sk-progress-input').oninput=()=>progressPreview(Number($('sk-progress-input').value));$('sk-progress-input').onchange=()=>goTo(Number($('sk-progress-input').value));
    $('sk-build-open').onclick=()=>{$('sk-organizer').open?closeOrganizer():openOrganizer();};$('sk-build-close').onclick=$('sk-build-done').onclick=closeOrganizer;$('sk-build-beside').onclick=()=>{if(!organizerDocked)openOrganizer();};$('sk-build-expand').onclick=()=>{if(organizerDocked)openOrganizer('full');};$('sk-search').oninput=renderGrid;$('sk-reset-order').onclick=()=>{picked.clear();setOrder(all.slice());};
    $('sk-sidebar-toggle').onclick=()=>setNav(!nav);document.addEventListener('saleskit-editmode',editorMode);
    document.addEventListener('saleskit-textchange',()=>{changed();scheduleFit();const item=$('bread').querySelectorAll('.bread-item')[window.cur];if(item)item.title=detail(current()?.dataset.skId);});
    $('sk-theme').onclick=()=>{settings.theme=settings.theme==='dark'?'light':'dark';applySettings();changed();};$('sk-motion').onclick=()=>{settings.motion=!settings.motion;applySettings();changed();};
    document.querySelectorAll('[data-sk-screen-open]').forEach(button=>button.onclick=()=>openScreen(button));$('sk-screen-close').onclick=closeScreen;
    $('sk-screen-panel').querySelectorAll('[data-screen-preset]').forEach(b=>b.onclick=()=>{settings.screen=clone(presets[b.dataset.screenPreset]);applySettings();changed();});
    $('sk-screen-panel').querySelectorAll('input[type=range]').forEach(input=>input.oninput=()=>{settings.screen[input.name]=Number(input.value);applySettings();changed();});
    $('sk-save-open').onclick=openSave;$('sk-save-close').onclick=$('sk-save-cancel').onclick=()=>closeWindow('sk-save-dialog','sk-save-open');
    $('sk-reset').onclick=()=>{$('sk-reset-dialog').showModal();};$('sk-reset-cancel').onclick=()=>closeWindow('sk-reset-dialog','sk-reset');$('sk-reset-confirm').onclick=resetOpened;
    $('sk-prev').onclick=()=>goTo(window.cur-1);$('sk-next').onclick=()=>goTo(window.cur+1);$('sk-present').onclick=present;$('sk-exit-present').onclick=exitPresent;
    $('sk-page').onchange=()=>{const n=Number($('sk-page').value);if(Number.isInteger(n)&&n>=1&&n<=order.length)goTo(n-1);else syncCurrent();};$('sk-page').onkeydown=e=>{if(e.key==='Enter'){$('sk-page').dispatchEvent(new Event('change'));$('sk-page').blur();}};
    for(const[id,trigger]of[['sk-save-dialog','sk-save-open'],['sk-reset-dialog','sk-reset']])$(id).addEventListener('cancel',e=>{e.preventDefault();closeWindow(id,trigger);});
    $('sk-organizer').addEventListener('cancel',e=>{e.preventDefault();closeOrganizer();});
    $('sk-journal').addEventListener('cancel',e=>{e.preventDefault();window.GigaDevJournal.close();});
    document.addEventListener('pointerdown',e=>{if(!$('sk-screen-panel').hidden&&!e.target.closest('#sk-screen-panel,[data-sk-screen-open]'))closeScreen();});
    document.addEventListener('keydown',e=>{
      if(e.isComposing||e.defaultPrevented||e.altKey)return;
      // Explicit save opens the existing version form; ordinary typing keeps its keys.
      const blockingForm=document.querySelector('dialog[open]:not(#sk-journal):not(#sk-organizer),.cc-overlay.open,#wpOv.open');
      if(e.ctrlKey||e.metaKey){if(e.code==='KeyS'&&!e.shiftKey&&!root.hasAttribute('data-sk-present')){if($('sk-save-dialog').open){e.preventDefault();return;}if(!blockingForm){e.preventDefault();e.stopPropagation();if(!e.repeat)$('sk-save-open').click();}}return;}
      const typing=e.target.closest?.('input,textarea,select,video,audio,[contenteditable]:not([contenteditable=false])');
      if(!typing&&!e.shiftKey&&!blockingForm&&(!root.hasAttribute('data-sk-present')||e.code==='KeyM')){
        const button=$(({KeyS:'sk-save-open',KeyO:'sk-build-open',KeyJ:'sk-journal-open',KeyC:'sk-screen-open',KeyT:'sk-theme',KeyN:'sk-sidebar-toggle',KeyM:'sk-motion'})[e.code]);
        if(button&&!button.hidden&&!button.disabled){e.preventDefault();e.stopPropagation();if(!e.repeat)button.click();return;}
      }
      if(e.key==='Escape'&&!screenPanel.hidden){e.preventDefault();e.stopImmediatePropagation();closeScreen();return;}
      if(document.querySelector('dialog[open]:not(#sk-journal.sk-journal-docked):not(#sk-organizer.sk-organizer-docked),.cc-overlay.open,#wpOv.open'))return;
      if(e.key==='Escape'&&organizerDocked&&$('sk-organizer').open&&!document.querySelector('[data-sk-editing]')){e.preventDefault();closeOrganizer();return;}
      if(e.key==='Escape'&&document.querySelector('#sk-journal.sk-journal-docked[open]')&&!document.querySelector('[data-sk-editing]'))return;
      if(e.key==='Escape'){if(root.hasAttribute('data-sk-present')){exitPresent();return;}if(root.classList.contains('edit-mode')){if(document.querySelector('[data-sk-editing]')){SalesKitText.cancel();return;}$('editBtn').click();return;}}
      if(e.target.closest?.('input,textarea,select,video,audio,[contenteditable]:not([contenteditable=false]),#sk-text-tools,#sk-screen-panel,#sk-journal,#sk-organizer'))return;
      if([' ','Enter'].includes(e.key)&&e.target.closest?.('button,a,summary,[role=button]'))return;
      const actions={ArrowRight:()=>goTo(window.cur+1),ArrowDown:()=>goTo(window.cur+1),PageDown:()=>goTo(window.cur+1),ArrowLeft:()=>goTo(window.cur-1),ArrowUp:()=>goTo(window.cur-1),PageUp:()=>goTo(window.cur-1),' ':()=>goTo(window.cur+1),Enter:()=>goTo(window.cur+1),Home:()=>goTo(0),End:()=>goTo(order.length-1)};
      if(e.code==='KeyE'&&!root.hasAttribute('data-sk-present')){e.preventDefault();$('editBtn').click();return;}
      if(e.code==='KeyG'){e.preventDefault();$('sk-page').focus();$('sk-page').select();return;}
      const action=e.code==='KeyF'?present:actions[e.key];if(action){e.preventDefault();e.stopPropagation();if(!e.repeat)action();}
    },true);
    window.addEventListener('resize',()=>{fit();resizeThumbs();});
    window.addEventListener('load',()=>{applyOrder(currentId);fit();});
    document.fonts?.ready.then(scheduleFit);
    setNav(nav);applySettings();applyOrder();editorMode();syncDirty();syncSelection();reflectIdentity();
    window.SalesKitUI={version:'shell-v17-preview',fit,closeScreen,closeWindow,syncToolbarLayer,exportDocument,openOrganizer,closeOrganizer,journalSnapshot,journalPending:()=>preparation.filter(p=>reviewState(p)==='pending').length,decidePreparation,setOrder:next=>{if(!Array.isArray(next)||!next.length||new Set(next).size!==next.length||next.some(id=>!byId.has(id)))throw Error('Invalid slide order');setOrder(next);},getState:()=>({...snapshot(),all:all.slice(),history:clone(history),version,changes:diffChanges(),current:current()?.dataset.skId,dirty:syncDirty()}),reset:resetOpened};
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();

