/* Release checks for the built HTML. Reads the deck and source project, emits JSON. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

const [input, projectFile, ...extra] = process.argv.slice(2);
if (!input || !projectFile || extra.length) {
  throw Error('Usage: node scripts/check_delivery.mjs Presentation.html project/deck.json');
}
const here = path.dirname(fileURLToPath(import.meta.url));
const project = JSON.parse(await fs.readFile(projectFile, 'utf8'));
const rolesRun=spawnSync('python3',[path.join(here,'presentation_roles.py'),'--project-only',projectFile],{encoding:'utf8'});
if(rolesRun.status!==0)throw Error('Invalid presentation roles: '+rolesRun.stdout);
const roleProof=JSON.parse(rolesRun.stdout).entries;
const pointer=JSON.parse(await fs.readFile(path.join(here,'../assets/current-baseline.json'),'utf8'));
const pkg=JSON.parse(await fs.readFile(path.join(here,'../package.json'),'utf8'));
if(pointer.version!==pkg.version||!/^baseline-release-[a-z0-9-]+\.json$/.test(pointer.file))throw Error('Invalid or mismatched release baseline pointer');
const baseline=JSON.parse(await fs.readFile(path.join(here,'../assets',pointer.file),'utf8'));
const issues = [];
const observations = [];
const checks = [];
const order = project.order ?? project.slides.map(s => s.id);
const selected = new Set(order);
assert(order.length && selected.size === order.length && order.every(id => project.slides.some(s => s.id === id)), 'Invalid project slide order');
const review = project.deliveryReview ?? {};
const supported = new Set(['text', 'table', 'image', 'media']);
const keyOf = (slide, id) => JSON.stringify([slide, id]);
const expected = project.slides.filter(s => selected.has(s.id)).map(slide => ({
  id: slide.id,
  chrome: roleProof.filter(e=>e.slideId===slide.id),
  background: slide.background?.asset,
  blocks: (slide.blocks ?? []).filter(b => supported.has(b.kind) && !(slide.sourceChrome??[]).some(c=>c.sourceId===b.id)),
}));
const expectedKeys = new Set(expected.flatMap(s => s.blocks.map(b => keyOf(s.id, b.id))));
const sourceChanges = new Map();
for (const item of review.sourceChanges ?? []) {
  const key = keyOf(item.slide, item.sourceId);
  assert(expectedKeys.has(key) && !sourceChanges.has(key) && item.reason?.trim(), 'Invalid or duplicate deliveryReview.sourceChanges entry');
  sourceChanges.set(key, item.reason);
}
const frameDecisions = new Map();
for (const item of review.frames ?? []) {
  assert(selected.has(item.slide) && !frameDecisions.has(item.slide) && item.reason?.trim(), 'Invalid or duplicate deliveryReview.frames entry');
  frameDecisions.set(item.slide, item.reason);
}
let config = {};
try {
  config = JSON.parse(await fs.readFile(path.join(here, '../runtime.local.json'), 'utf8'));
} catch (error) {
  if (error.code !== 'ENOENT') throw error;
}
const modules = process.env.HTML_MAKER_NODE_MODULES || config.nodeModules;
const require = modules ? createRequire(path.join(modules, 'package.json')) : createRequire(import.meta.url);
const { chromium } = require('playwright');

function fail(code, message, details = {}) {
  issues.push({ code, message, ...details });
}

const normalized = text => String(text ?? '').replace(/\s+/gu, ' ').trim();
const transparent = color => /^(transparent|rgba\([^)]*[,\s/]\s*0(?:\.0+)?\s*\))$/i.test(String(color??'').trim());
const paragraphText = paragraphs => (paragraphs ?? []).map(p => p.text).join(' ');
function expectedText(block) {
  if (block.kind === 'text') return paragraphText(block.paragraphs);
  return block.rows.flatMap(row => row.map(paragraphText)).join(' ');
}

async function checkShell(page) {
  const ids = Object.keys(baseline.modules).filter(name => name !== 'shell.html');
  const fragments=Object.fromEntries(await Promise.all(ids.filter(name=>name.endsWith('.css')&&!['ui.css','deck.css'].includes(name)).map(async name=>[name,await fs.readFile(path.join(here,'../assets',name),'utf8')])));
  const domIds = ids.map(name => {
    if (name === 'controller.js') return 'sk-controller';
    if (name === 'deck.css') return 'gd-deck-styles';
    if (name === 'ui.css') return 'sk-ui-styles';
    if(name.endsWith('.css'))return 'gd-style-pack';
    return 'gd-' + name.slice(0, -3);
  });
  const parts = await page.evaluate(ids => ({
    marker: document.documentElement.dataset.gdMaker,
    version: window.GigaDevDeck?.shellVersion,
    stages: document.querySelectorAll('#sk-stage > #sk-canvas > #slides').length,
    contents: ids.map(id => {
      const matches = document.querySelectorAll(`#${id}`);
      return matches.length === 1 ? matches[0].textContent : null;
    }),
  }), domIds);
  if (parts.marker !== '1' || parts.version !== 'v18.2' || parts.stages !== 1) {
    fail('shell', 'Expected a running Maker v18.2 shell and its canonical stage.');
  }
  for (const [index, name] of ids.entries()) {
    let content = parts.contents[index];
    if(fragments[name])content=content?.includes(fragments[name])?fragments[name]:null;
    if (content === null || createHash('sha256').update(content).digest('hex') !== baseline.modules[name]) {
      fail('shell-module', 'Missing or modified shell module.', { module: name });
    }
  }
  if (!issues.length) checks.push('pinned shell modules and running stage');
}

async function checkMotion(page) {
  if (order.length < 2) {
    observations.push({ code: 'single-slide', message: 'Transition cannot be exercised in a one-slide deck.' });
    return;
  }
  const enabled = await page.evaluate(() => SalesKitUI.getState().settings.motion);
  if (!enabled) {
    if (typeof review.motionOffReason !== 'string' || !review.motionOffReason.trim()) {
      fail('motion-off', 'Slide motion is disabled by default in the delivered file.');
      return;
    }
    observations.push({code:'reviewed-motion-off',reason:review.motionOffReason});
    await page.locator('#sk-motion').click();
  }
  await page.evaluate(() => { goTo(0); SalesKitMotion.finish(); });
  await page.mouse.move(900, 450);
  await page.mouse.wheel(0, 120);
  const wheel = await page.waitForFunction(() => {
    const state = SalesKitMotion.getState();
    const inner = document.querySelector('#slides > .slide > .slide-inner');
    const css = getComputedStyle(inner);
    const top = document.querySelector('#slides').scrollTop;
    return state.phase === 'scroll' && top > 0 && top < 250 && +css.opacity > 0 && +css.opacity < 1 && /blur\(/.test(css.filter);
  }, undefined, { timeout: 2500 }).then(() => true, () => false);
  if (!wheel) fail('scroll-motion', 'Native scroll did not produce a partial-slide fade and blur.');
  await page.evaluate(() => { goTo(0); SalesKitMotion.finish(); });
  await page.keyboard.press('ArrowRight');
  const keyboard = await page.waitForFunction(() => {
    const state = SalesKitMotion.getState();
    if (!['exit', 'enter'].includes(state.phase)) return false;
    return [...document.querySelectorAll('#slides > .slide .slide-inner')].some(inner =>
      [inner, ...inner.querySelectorAll('.gd-slide-background, .gd-content *')].some(node => {
        const css = getComputedStyle(node);
        return +css.opacity > 0 && +css.opacity < 1 && /blur\(/.test(css.filter);
      })
    );
  }, undefined, { timeout: 2500 }).then(() => true, () => false);
  const settled = await page.waitForFunction(id => {
    const state = SalesKitMotion.getState();
    return state.phase === 'idle' && SalesKitUI.getState().current === id;
  }, order[1], { timeout: 4500 }).then(() => true, () => false);
  if (!keyboard || !settled) fail('keyboard-motion', 'ArrowRight did not fade/blur and settle on the next slide.');
  if (wheel && keyboard && settled) checks.push('actual native scroll and keyboard fade/blur');
}

async function inspectExport(page) {
  const state = await page.evaluate(() => GigaDevDeck.prepareExport());
  if (JSON.stringify(state.order) !== JSON.stringify(order)) fail('order', 'Slide IDs/order differ from the source project.');
  const canvas = project.source?.canvas;
  if (canvas?.widthEMU > 0 && canvas?.heightEMU > 0 && Math.abs(canvas.widthEMU / canvas.heightEMU - 16/9) > 0.01) {
    if (typeof review.sourceAspectReason === 'string' && review.sourceAspectReason.trim()) {
      observations.push({code:'reviewed-source-aspect',reason:review.sourceAspectReason});
    } else fail('source-aspect', 'The source aspect ratio differs from 16:9. Record the agreed adaptation.');
  }
  const result = await page.evaluate(async expected => {
    const meta = JSON.parse(document.querySelector('#sk-deck-state').textContent);
    const issues = [];
    const frames = [];
    const snapshots = [];
    const raster = new Map();
    const visible = node => {
      const r=node.getBoundingClientRect();
      if(node.checkVisibility({visibilityProperty:true,opacityProperty:true}) && r.width>0 && r.height>0)return true;
      if(getComputedStyle(node).display!=='contents')return false;
      return [...node.querySelectorAll('*')].some(child=>{const q=child.getBoundingClientRect();return child.checkVisibility({visibilityProperty:true,opacityProperty:true})&&q.width>0&&q.height>0});
    };
    const transparent=color=>/^(transparent|rgba\([^)]*[,\s/]\s*0(?:\.0+)?\s*\))$/i.test(String(color??'').trim());
    const textEvidence=(node,slide)=>{
      const f=slide.getBoundingClientRect(),walker=document.createTreeWalker(node,NodeFilter.SHOW_TEXT);let invisible=false,clipped=false,uncertain=false;
      while(walker.nextNode()){
        const t=walker.currentNode;if(!t.data.trim()||t.parentElement.closest('svg,script,style,video,audio'))continue;
        let box={left:f.left,top:f.top,right:f.right,bottom:f.bottom},alpha=1;const own=getComputedStyle(t.parentElement);
        if(own.visibility!=='visible'||transparent(own.color)||transparent(own.webkitTextFillColor))invisible=true;
        for(let el=t.parentElement;el;el=el.parentElement){const cs=getComputedStyle(el);alpha*=Number(cs.opacity);
          if(cs.display==='none'||cs.contentVisibility==='hidden')invisible=true;
          if(cs.clipPath!=='none'||cs.maskImage!=='none'||cs.clip!=='auto')uncertain=true;
          if(el!==slide){const r=el.getBoundingClientRect(),x=['hidden','clip','scroll','auto'].includes(cs.overflowX),y=['hidden','clip','scroll','auto'].includes(cs.overflowY);if(x){box.left=Math.max(box.left,r.left);box.right=Math.min(box.right,r.right)}if(y){box.top=Math.max(box.top,r.top);box.bottom=Math.min(box.bottom,r.bottom)}}
          if(el===slide)break;
        }
        if(alpha<=0.001)invisible=true;const range=document.createRange();range.selectNodeContents(t);const rects=[...range.getClientRects()].filter(r=>r.width>0&&r.height>0);if(!rects.length)invisible=true;
        if(rects.some(r=>r.left<box.left-1||r.right>box.right+1||r.top<box.top-1||r.bottom>box.bottom+1))clipped=true;
      }
      return {invisible,clipped,uncertain};
    };
    const markers=(node,slide)=>[...(node.matches('li')?[node]:[]),...node.querySelectorAll('li')].map(li=>{const css=getComputedStyle(li),m=getComputedStyle(li,'::marker'),b=getComputedStyle(li,'::before'),frame=slide.getBoundingClientRect(),rect=li.getBoundingClientRect();let left=frame.left,right=frame.right;for(let el=li;el&&el!==slide;el=el.parentElement){const c=getComputedStyle(el);if(['hidden','clip','scroll','auto'].includes(c.overflowX)){const r=el.getBoundingClientRect();left=Math.max(left,r.left);right=Math.min(right,r.right)}}const gap=css.direction==='rtl'?right-rect.right:rect.left-left;return {markerClipped:css.listStylePosition==='outside'&&gap<=0,markerClipRisk:css.listStylePosition==='outside'&&gap>0&&gap<parseFloat(css.fontSize)*1.5,display:css.display,type:css.listStyleType,image:css.listStyleImage,content:m.content,color:m.color,size:m.fontSize,visibility:m.visibility,opacity:m.opacity,before:b.content,beforeColor:b.color,beforeSize:b.fontSize,beforeVisibility:b.visibility,beforeOpacity:b.opacity}});
    const rasterSize = src => {
      if (!raster.has(src)) {
        const probe = new Image();
        probe.src = src;
        raster.set(src, probe.decode().then(() => [probe.naturalWidth, probe.naturalHeight], () => null));
      }
      return raster.get(src);
    };
    const isVector = src => /^data:image\/svg\+xml[;,]/i.test(src);
    const scoped = '#slides > .slide';
    const svgOrImage = 'svg,img';
    const textValue = node => {
      if (node.nodeType === Node.TEXT_NODE) return node.data;
      if (node.nodeType !== Node.ELEMENT_NODE || node.matches('svg,script,style,video,audio')) return '';
      const css = getComputedStyle(node);
      if (css.display === 'none' || css.visibility === 'hidden' || +css.opacity === 0) return '';
      if (node.matches('br')) return ' ';
      const text = [...node.childNodes].map(textValue).join('');
      return node.matches('p,div,li,tr,td,th') ? ' ' + text + ' ' : text;
    };
    const enlargement = (w, h, iw, ih, fit) => {
      if (fit === 'none') return 1;
      if (fit === 'contain' || fit === 'scale-down') return Math.min(w / iw, h / ih, fit === 'scale-down' ? 1 : Infinity);
      return Math.max(w / iw, h / ih);
    };

    for (const slide of document.querySelectorAll(scoped)) {
      const id = slide.dataset.skId;
      const content = slide.querySelector(':scope > .slide-inner > .gd-content');
      const bg = slide.querySelector(':scope > .slide-inner > .gd-slide-background');
      const frame = slide.getBoundingClientRect();
      if (!content || Math.abs(frame.width - 1920) > 2 || Math.abs(frame.height - 1080) > 2) {
        issues.push({code:'canvas',slide:id,message:'Expected a full 1920 × 1080 Maker slide with a single content area.'});
        continue;
      }
      const inner = content.parentElement.getBoundingClientRect();
      const contentBox = content.getBoundingClientRect();
      const fullMedia = slide.dataset.gdMediaFrame === 'full';
      if (slide.querySelectorAll('.gd-content').length !== 1 ||
          [inner.width - frame.width, inner.height - frame.height, inner.left - frame.left, inner.top - frame.top].some(x => Math.abs(x) > 2) ||
          [contentBox.width - (fullMedia ? 1920 : 1696), contentBox.height - (fullMedia ? 1080 : 874),
           contentBox.left - frame.left - (fullMedia ? 0 : 112), contentBox.top - frame.top - (fullMedia ? 0 : 120)].some(x => Math.abs(x) > 2)) {
        issues.push({code:'canvas',slide:id,message:'Slide paint or content is outside the canonical canvas.'});
      }
      if (content.querySelector('iframe,object,embed,[data-gd-maker],.slide,.slide-inner,.gd-content,#slides,#sk-stage')) {
        issues.push({code:'nested-slide',slide:id,message:'Slide content contains a nested deck, frame or reserved shell structure.'});
      }
      const source = expected.find(entry => entry.id === id);
      for(const entry of source?.chrome??[]){
        const markers=[...slide.querySelectorAll('.gd-export-meta [data-gd-chrome-source]')].filter(n=>n.dataset.gdChromeSource===entry.sourceId&&n.dataset.gdChromeRole===entry.role);
        const duplicates=[...content.querySelectorAll('[data-source-id]')].filter(n=>n.dataset.sourceId===entry.sourceId);
        const enabled=slide.dataset.gdHeader!=='none'&&(entry.role!=='navigation'||slide.dataset.gdHeader==='full');
        const number=String(meta.order.indexOf(id)+1);
        if(markers.length!==1||duplicates.length||!enabled||(entry.role==='page-number'&&(!visible(markers[0])||markers[0].textContent.trim()!==number))){
          issues.push({code:'source-chrome',slide:id,sourceId:entry.sourceId,message:'Reviewed source chrome must map to canonical shell metadata without a body duplicate.'});
        }
      }
      const targets = new Map();
      for (const node of content.querySelectorAll('[data-source-id]')) {
        const list = targets.get(node.dataset.sourceId) ?? [];
        list.push(node);
        targets.set(node.dataset.sourceId, list);
      }
      const actual = [];
      for (const block of source?.blocks ?? []) {
        const nodes = (targets.get(block.id) ?? []).filter(visible);
        const node = nodes[0];
        const graphic = node?.matches(svgOrImage) ? node : [...(node?.querySelectorAll(svgOrImage) ?? [])].find(visible);
        const sourceBackground = block.kind === 'image' && block.asset && source.background === block.asset;
        actual.push({
          id: block.id,
          count: nodes.length,
          text: node ? textValue(node) : '',
          visibility: node ? textEvidence(node,slide) : null,
          markers: node ? markers(node,slide) : [],
          links: node ? [node, ...node.querySelectorAll('a[href]')].filter(el => el.matches('a[href]') && visible(el)).map(el => el.getAttribute('href')) : [],
          vector: Boolean(graphic?.matches('svg') || (graphic?.matches('img') && isVector(graphic.currentSrc))),
          image: Boolean(graphic),
          media: Boolean(node?.matches('video,audio') || node?.querySelector('video,audio')),
          background: sourceBackground && Boolean(bg && visible(bg) && getComputedStyle(bg).backgroundImage !== 'none'),
          backgroundVector: sourceBackground && Boolean(bg && getComputedStyle(bg).backgroundImage.includes('data:image/svg+xml')),
        });
      }
      snapshots.push({ id, actual });

      const imgs = [...content.querySelectorAll('img')].filter(visible);
      const clip = [...content.querySelectorAll('p,h1,h2,h3,h4,li,td,th,img,svg,table,video')].filter(visible).filter(node => {
        const box = node.getBoundingClientRect();
        return box.left < frame.left - 2 || box.right > frame.right + 2 || box.top < frame.top - 2 || box.bottom > frame.bottom + 2;
      }).slice(0, 8);
      for (const node of clip) issues.push({code:'clipped-content',slide:id,sourceId:node.dataset.sourceId,message:'Content element extends beyond the full slide canvas.'});

      for (const img of imgs) {
        const src = img.currentSrc || img.src;
        const size = src && await rasterSize(src);
        if (!size || !size[0] || !size[1]) {
          issues.push({code:'broken-image',slide:id,sourceId:img.dataset.sourceId,message:'Visible image did not decode.'});
          continue;
        }
        const box = img.getBoundingClientRect();
        if (!isVector(src)) {
          const ratio = enlargement(box.width, box.height, ...size, getComputedStyle(img).objectFit);
          if (ratio > 1.25) issues.push({code:'upscaled-image',slide:id,sourceId:img.dataset.sourceId,message:'Raster enlarged beyond 1.25× at 1920 × 1080.',natural:size,display:[Math.round(box.width),Math.round(box.height)],ratio:Math.round(ratio*100)/100});
        }
        const imageIsSlide = Math.abs(size[0] / size[1] - 16/9) < 0.07 &&
          box.width > contentBox.width * 0.82 && box.height > contentBox.height * 0.70 &&
          content.innerText.trim().length < 20;
        if (imageIsSlide) frames.push({slide:id,message:'Slide-sized image is inset inside the content frame.'});
      }
      for (let wrapper = content.firstElementChild; wrapper && wrapper === wrapper.parentElement.lastElementChild; wrapper = wrapper.firstElementChild) {
        const box = wrapper.getBoundingClientRect(), css = getComputedStyle(wrapper);
        if (box.width < contentBox.width * 0.82 || box.height < contentBox.height * 0.75) break;
        if (parseFloat(css.borderRadius) >= 8 || css.boxShadow !== 'none' || parseFloat(css.borderTopWidth) >= 1) {
          frames.push({slide:id,message:'A near-full-size inset wrapper has an outer border, shadow or rounded corners.'});
          break;
        }
      }
      if (bg && visible(bg)) {
        const box = bg.getBoundingClientRect();
        if (Math.abs(box.width - frame.width) > 2 || Math.abs(box.height - frame.height) > 2 ||
            Math.abs(box.left - frame.left) > 2 || Math.abs(box.top - frame.top) > 2) {
          issues.push({code:'background-frame',slide:id,message:'Slide background does not cover the whole canvas.'});
        }
        const css = getComputedStyle(bg);
        const src = css.backgroundImage.match(/^url\("([^"]+)"\)$/)?.[1];
        if (src && !isVector(src)) {
          const size = await rasterSize(src);
          if (!size || !size[0] || !size[1]) issues.push({code:'broken-background',slide:id,message:'Background image did not decode.'});
          else {
            const ratio = enlargement(box.width, box.height, ...size, css.backgroundSize === '100% 100%' ? 'fill' : css.backgroundSize);
            if (ratio > 1.25) issues.push({code:'upscaled-background',slide:id,message:'Full-canvas raster background enlarged beyond 1.25×.',natural:size,ratio:Math.round(ratio*100)/100});
          }
        }
      }
    }
    return { issues, frames, snapshots, changes: meta.preparationChanges ?? [] };
  }, expected);
  issues.push(...result.issues);
  for (const frame of result.frames) {
    if (frameDecisions.has(frame.slide)) observations.push({code:'reviewed-frame',...frame,reason:frameDecisions.get(frame.slide)});
    else fail('inset-frame', frame.message, {slide:frame.slide});
  }
  const snapshots = new Map(result.snapshots.map(s => [s.id, s.actual]));
  for (const slide of expected) {
    const actual = snapshots.get(slide.id);
    if (!actual) {
      fail('missing-slide', 'Slide unavailable for content verification.', {slide:slide.id});
      continue;
    }
    for (const [i, block] of slide.blocks.entries()) {
      const details = {slide:slide.id,sourceId:block.id};
      const target = actual[i];
      const changeReason = sourceChanges.get(keyOf(slide.id, block.id));
      if (changeReason) {
        observations.push({code:'source-change',...details,reason:changeReason});
        continue;
      }
      const isText = block.kind === 'text' || block.kind === 'table';
      let wanted = isText ? normalized(expectedText(block)) : '';
      if (isText && !wanted) continue;
      if (target.count !== 1 && !target.background) {
        fail('source-target', 'Expected exactly one visible target for a source object.', {...details,found:target.count});
        continue;
      }
      if (isText) {
        if(target.visibility?.invisible)fail('source-text-invisible','Source text is hidden or has zero geometry.',details);
        if(target.visibility?.clipped)fail('source-text-clipped','Source text is clipped or outside the slide.',details);
        if(target.visibility?.uncertain)observations.push({code:'source-text-visibility-review',...details,reason:'clip-path or mask requires visual review'});
        if(block.kind==='text'){
          const listKind=para=>{const e=para.effectiveList;if(e?.status==='resolved')return ['ul','ol'].includes(e.kind)?e.kind:null;const xml=para.paragraphPropertiesXml??'';return /<(?:[\w-]+:)?buAutoNum\b/.test(xml)?'ol':/<(?:[\w-]+:)?bu(?:Char|Blip)\b/.test(xml)?'ul':null;};
          const expectedMarkers=(block.paragraphs??[]).filter(p=>listKind(p));
          const approved=(review.customListMarkers??[]).find(x=>x.slide===slide.id&&x.sourceId===block.id&&x.approved===true&&typeof x.reason==='string'&&x.reason.trim());
          const empty=x=>['none','normal','""',"''",''].includes(String(x??'').trim());
          const ordered=new Set(['decimal','decimal-leading-zero','lower-alpha','upper-alpha','lower-latin','upper-latin','lower-roman','upper-roman']);
          for(const [i,para] of expectedMarkers.entries()){
            const m=target.markers[i];if(!m){fail('list-marker-missing','Expected list item or its marker is missing.',{...details,paragraph:i});continue;}
            const markerEmpty=m.content==='none'||m.content==='""'||m.content==="''";
            const suppressed=!m.display.includes('list-item')||markerEmpty||m.visibility==='hidden'||+m.opacity===0||parseFloat(m.size)===0||transparent(m.color)||(m.type==='none'&&m.image==='none'&&m.content==='normal');
            if(!suppressed && m.markerClipped)fail('list-marker-clipped','Outside list marker lies beyond a clipping boundary.',{...details,paragraph:i});
            else if(!suppressed && m.markerClipRisk)observations.push({code:'list-marker-visibility-review',...details,paragraph:i,reason:'Outside marker near clipping boundary.'});
            const custom=!empty(m.before)&&m.beforeVisibility!=='hidden'&&+m.beforeOpacity!==0&&parseFloat(m.beforeSize)!==0&&!transparent(m.beforeColor);
            if(suppressed){if(custom&&approved)observations.push({code:'custom-list-marker-review',...details,paragraph:i,reason:approved.reason});else fail(custom?'custom-list-marker-unapproved':'list-marker-missing','List marker is suppressed or unapproved.',{...details,paragraph:i});}
            else if(m.image!=='none'||(m.content!=='normal'&&!markerEmpty)){if(approved)observations.push({code:'custom-list-marker-review',...details,paragraph:i,reason:approved.reason});else fail('custom-list-marker-unapproved','Custom marker requires explicit approval.',{...details,paragraph:i});}
            else if(listKind(para)==='ol' && (()=>{const style=para.effectiveList?.attributes?.type ?? /buAutoNum\b[^>]*\btype=["']([^"']+)["']/.exec(para.paragraphPropertiesXml??'')?.[1];const map={arabicPeriod:['decimal'],alphaLcPeriod:['lower-alpha','lower-latin'],alphaUcPeriod:['upper-alpha','upper-latin'],romanLcPeriod:['lower-roman'],romanUcPeriod:['upper-roman']};return style&&map[style]&&!map[style].includes(m.type);})())fail('list-marker-type-mismatch','Numbering style does not match the source.',{...details,paragraph:i,actual:m.type});
            else if((listKind(para)==='ol'&&!ordered.has(m.type))||(listKind(para)==='ul'&&ordered.has(m.type)))fail('list-marker-type-mismatch','Marker type does not match the source list.',{...details,paragraph:i,actual:m.type});
          }
        }
        for (const change of result.changes) {
          if (change.slide === slide.id && change.sourceId === block.id && change.status === 'applied' &&
              normalized(change.before) === wanted) wanted = normalized(change.after);
        }
        if (normalized(target.text) !== wanted) fail('source-text', 'Visible text or table values differ from the source.',details);
        const paragraphs = block.kind === 'text' ? block.paragraphs ?? [] : block.rows.flat(2);
        const links = new Set(paragraphs.flatMap(p => (p.runs ?? []).map(run => run.link)).filter(link => /^(https?:\/\/|mailto:|tel:)/.test(link ?? '')));
        if ([...links].some(link => !target.links.includes(link))) fail('source-link', 'A source link is missing or changed.',details);
      } else if (block.kind === 'image') {
        if (!target.image && !target.background) fail('source-graphic', 'Source graphic has no rendered graphic target.',details);
        if (/\.svg$/i.test(block.asset ?? '') && !target.vector && !target.backgroundVector) {
          fail('rasterized-vector', 'Source SVG is rendered as raster or replaced without a documented decision.',details);
        }
      } else if (!target.media) fail('source-media', 'Source media has no video or audio target.',details);
    }
  }
  for(const slide of expected)if(!slide.blocks.length)observations.push({code:'source-blocks-unavailable',slide:slide.id,message:'No source objects for this slide; compare with an independent inventory or approved brief.'});
  checks.push('static frame, visible source targets and graphic sampling');
}

const browser = await chromium.launch({ headless: true, ...(process.env.HTML_MAKER_CHROME === 'bundled' ? {} : { channel: 'chrome' }) });
try {
  const page = await browser.newPage({ viewport:{width:1600,height:900}, reducedMotion:'no-preference', serviceWorkers:'block' });
  await page.route(/^https?:/, route => route.abort());
  page.on('pageerror', error => fail('page-error', error.message));
  await page.goto(pathToFileURL(path.resolve(input)).href, { waitUntil:'domcontentloaded' });
  await checkShell(page);
  if (!issues.length) {
    await page.waitForFunction(() => window.SalesKitUI && SalesKitMotion.getState().phase === 'idle');
    await checkMotion(page);
    await page.setViewportSize({width:1920,height:1080});
    await inspectExport(page);
  }
} finally {
  await browser.close();
}
console.log(JSON.stringify({status:issues.length ? 'fail' : observations.some(x=>['source-blocks-unavailable','source-text-visibility-review','custom-list-marker-review','list-marker-style-review','list-marker-visibility-review'].includes(x.code)) ? 'review' : 'pass',checks,issues,observations,visualApproval:false},null,2));
if (issues.length) process.exitCode = 1;
