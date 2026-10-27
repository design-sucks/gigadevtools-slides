/* Plain inline editing; write back only the text delta to preserve original inline markup. */
(() => {
  function init() {
    const $ = id => document.getElementById(id), root = document.documentElement;
    const originals = new Map(), nodes = new Map();
    const selector = 'h1,h2,h3,h4,p,.num,.delta,.eco7-val b,.eh-num,.fb-num,.pprice,.h-pct,.pn,.eyebrow,.lead,.val,.tag,.ah-headline,.ah-sub,.lbl,.ef-tag,.lc-title,.vs-title,.hc-name,.eh-txt';
    let seq = 0, edits = {}, undo = [], redo = [], active = null, beforeHTML = '', beforeText = '', beforeEdits = {}, composing = false;
    const skip='script,style,textarea,input,select,option,svg,iframe,canvas,video,audio,.sk-slide-meta,.gd-export-meta';
    const meaningful=text=>/[\p{L}\p{N}]/u.test(text);
    function register(node,slide){
      if(!node.dataset.eid){do{node.dataset.eid=`${slide.dataset.skId}-t${++seq}`;}while(nodes.has(node.dataset.eid));}
      nodes.set(node.dataset.eid,node);if(!originals.has(node.dataset.eid))originals.set(node.dataset.eid,node.innerHTML);
    }
    function discover(){
      document.querySelectorAll('#slides>.slide').forEach(slide=>{
        slide.querySelectorAll('[data-eid]').forEach(n=>register(n,slide));
        // Keep semantic text blocks intact, including tables and list items.
        slide.querySelectorAll(selector+',li,td,th,figcaption,blockquote,button,a').forEach(node=>{
          if(node.closest(skip)||node.closest('[data-eid]')||node.querySelector('[data-eid],input,textarea,select,iframe,canvas,video,audio,table,ul,ol'))return;
          if(meaningful(node.textContent))register(node,slide);
        });
        // Cover the presentation's custom div/span labels and captions.
        slide.querySelectorAll('*').forEach(node=>{
          if(node.namespaceURI!=='http://www.w3.org/1999/xhtml'||node.closest(skip)||node.closest('[data-eid]')||node.querySelector('[data-eid]'))return;
          if(![...node.childNodes].some(n=>n.nodeType===Node.TEXT_NODE&&meaningful(n.textContent)))return;
          if([...node.children].some(n=>!n.matches('svg,br,wbr')&&!['inline','inline-block','inline-flex','none','contents'].includes(getComputedStyle(n).display)))return;
          register(node,slide);
        });
        // Mixed layout containers can have free text beside a separate heading.
        const walk=document.createTreeWalker(slide,NodeFilter.SHOW_TEXT),remaining=[];
        while(walk.nextNode()){const n=walk.currentNode;if(meaningful(n.textContent)&&!n.parentElement.closest(skip+', [data-eid]'))remaining.push(n);}
        remaining.forEach(n=>{const span=document.createElement('span');span.className='sk-edit-fragment';n.replaceWith(span);span.append(n);register(span,slide);});
      });
    }
    discover();
    const snapshot = () => ({...edits});
    const notify = () => document.dispatchEvent(new Event('saleskit-textchange'));
    function textParts(node) {
      const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT), parts = [];
      while (walker.nextNode()) {
        const n = walker.currentNode;
        if (n.nodeType === Node.TEXT_NODE) parts.push({node:n, text:n.data});
        else if (n.tagName === 'BR') parts.push({node:n, text:'\n'});
      }
      return parts;
    }
    function writeText(node, text) {
      const parts = textParts(node), old = parts.map(p => p.text).join('');
      if (old === text) return;
      if (!parts.length) {node.textContent = text; return;}
      let start = 0, tail = 0;
      while (start < Math.min(old.length,text.length) && old[start] === text[start]) start++;
      while (tail < Math.min(old.length,text.length)-start && old[old.length-tail-1] === text[text.length-tail-1]) tail++;
      const end = old.length-tail, range = document.createRange();
      function boundary(offset) {
        let position = 0;
        for (const part of parts) {
          const length = part.text.length;
          if (offset <= position+length) {
            if (part.node.nodeType === Node.TEXT_NODE) return [part.node, offset-position];
            const parent = part.node.parentNode, index = [...parent.childNodes].indexOf(part.node);
            return [parent, index+(offset>position?1:0)];
          }
          position += length;
        }
        return [node,node.childNodes.length];
      }
      range.setStart(...boundary(start)); range.setEnd(...boundary(end)); range.deleteContents();
      const fragment = document.createDocumentFragment();
      text.slice(start,text.length-tail).split('\n').forEach((line,index) => {
        if (index) fragment.append(document.createElement('br'));
        fragment.append(document.createTextNode(line));
      });
      range.insertNode(fragment);node.normalize();
    }
    function canonical() {
      const text=active.innerText.replace(/\r\n?/g,'\n');if(text===beforeText)return beforeHTML;
      const clone = active.cloneNode(false);clone.innerHTML = beforeHTML;
      writeText(clone,text);return clone.innerHTML;
    }
    function update() {
      $('editUndo').disabled = !undo.length && !(active && active.innerHTML !== beforeHTML);
      $('editRedo').disabled = !redo.length;
      $('editReset').disabled = !active || !Object.hasOwn(edits,active.dataset.eid);
      $('sk-text-hint').textContent = active ? 'Esc — отменить' : 'Нажмите на текст';
    }
    function detach() {
      if (!active) return;
      active.removeAttribute('contenteditable');active.removeAttribute('data-sk-editing');active.removeAttribute('spellcheck');
      active = null;document.getSelection()?.removeAllRanges();update();
    }
    function commit() {
      if (!active || composing) return;
      const node = active, html = canonical(), id = node.dataset.eid;
      if (!node.innerText.trim()) {cancel();return;}
      node.innerHTML = html;
      if (html === originals.get(id)) delete edits[id]; else edits[id] = html;
      if (html !== beforeHTML) {undo.push(beforeEdits);if (undo.length>30) undo.shift();redo=[];}
      detach();notify();
    }
    // Apply an approved text proposal through the same markup-preserving undo path.
    function apply(id,expected,text) {
      commit();const node=nodes.get(id);
      if(!node)return {ok:false,error:'Текстовый блок не найден'};
      const current=textParts(node).map(p=>p.text).join('');
      if(current!==expected)return {ok:false,error:'Текст уже изменён. Сравните предложение с текущим блоком.'};
      if(current===text)return {ok:true,unchanged:true};
      if(!text.trim())return {ok:false,error:'Предложение не может удалить весь блок'};
      const before=snapshot();writeText(node,text);
      if(node.innerHTML===originals.get(id))delete edits[id];else edits[id]=node.innerHTML;
      undo.push(before);if(undo.length>30)undo.shift();redo=[];update();notify();return {ok:true};
    }
    function cancel() {
      if (!active) return;
      active.innerHTML = beforeHTML;edits = {...beforeEdits};detach();notify();
    }
    function restore(next, emit = true) {
      detach();edits = {...next};
      nodes.forEach((node,id) => node.innerHTML = edits[id] ?? originals.get(id));
      update();if (emit) notify();
    }
    function select(node) {
      if (active === node) return;
      commit();
      node.querySelectorAll('.gt-num[data-sk-final]').forEach(num=>num.textContent=num.dataset.skFinal);
      node.querySelectorAll('.gt-holder').forEach(holder => holder.replaceWith(document.createTextNode(holder.textContent)));
      active=node;beforeHTML=node.innerHTML;beforeText=node.innerText.replace(/\r\n?/g,'\n');beforeEdits=snapshot();
      node.setAttribute('contenteditable','plaintext-only');node.setAttribute('spellcheck','false');node.dataset.skEditing='';node.focus();update();
    }
    function mode(on) {
      commit();if(on)discover();root.classList.toggle('edit-mode',on);$('sk-text-tools').hidden=!on;
      $('editBtn').setAttribute('aria-pressed',String(on));document.dispatchEvent(new Event('saleskit-editmode'));
    }
    function undoEdit() {commit();if (undo.length) {redo.push(snapshot());restore(undo.pop());}}
    function redoEdit() {commit();if (redo.length) {undo.push(snapshot());restore(redo.pop());}}
    $('editBtn').onclick=()=>mode(!root.classList.contains('edit-mode'));
    $('sk-text-done').onclick=()=>mode(false);
    $('editUndo').onclick=undoEdit;$('editRedo').onclick=redoEdit;
    $('editReset').onclick=()=>{
      if (!active) return;const id=active.dataset.eid;commit();undo.push(snapshot());redo=[];delete edits[id];restore(edits);
    };
    // Keep the selection while a contextual toolbar button is pressed.
    $('sk-text-tools').addEventListener('pointerdown',e=>{if (e.target.closest('button')) e.preventDefault();});
    document.addEventListener('pointerdown',event=>{
      if (!root.classList.contains('edit-mode') || event.target.closest('#sk-text-tools')) return;
      if (active && !active.contains(event.target)) commit();
    },true);
    document.addEventListener('click',event=>{
      if (!root.classList.contains('edit-mode') || event.target.closest('.sk-ui')) return;
      const node=event.target.closest('[data-eid]');
      if (node?.closest('#slides')) {event.preventDefault();event.stopPropagation();const first=active!==node;select(node);if(first&&document.caretRangeFromPoint){const range=document.caretRangeFromPoint(event.clientX,event.clientY);if(range&&node.contains(range.startContainer)){const selection=document.getSelection();selection.removeAllRanges();selection.addRange(range);}}}
    },true);
    document.addEventListener('input',event=>{
      if (!active || event.target !== active || composing) return;
      const html=canonical(),id=active.dataset.eid;
      if (html===originals.get(id)) delete edits[id]; else edits[id]=html;
      update();notify();
    });
    document.addEventListener('compositionstart',event=>{if(event.target===active)composing=true;});
    document.addEventListener('compositionend',event=>{composing=false;if(event.target===active)active.dispatchEvent(new Event('input',{bubbles:true}));});
    document.addEventListener('keydown',event=>{
      if (!root.classList.contains('edit-mode') || event.isComposing) return;
      if (active?.contains(event.target)) {
        if (event.key==='Escape') {event.preventDefault();event.stopImmediatePropagation();cancel();}
        else if ((event.ctrlKey||event.metaKey) && event.key==='Enter') {event.preventDefault();event.stopImmediatePropagation();commit();}
        else if (event.key==='Tab') {event.preventDefault();commit();}
        return; // Arrow keys and native text undo belong to the editable field.
      }
      if ((event.ctrlKey||event.metaKey) && event.key.toLowerCase()==='z' && !event.target.closest('input,textarea')) {
        event.preventDefault();event.shiftKey?redoEdit():undoEdit();
      }
    },true);
    window.addEventListener('blur',()=>{if (!composing) commit();});
    window.SalesKitText={snapshot,restore,discover,commit,apply,close:cancel,cancel,mode,reset(){undo=[];redo=[];restore({});}};update();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
