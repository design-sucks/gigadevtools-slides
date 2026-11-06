/* Inspect actual slide text in the Maker browser runtime. Output is a review aid. */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';

const [input, ...args] = process.argv.slice(2);
if (!input || args.some(arg => arg !== '--export' && arg !== '--actual-fonts' && !/^--viewport=\d+x\d+$/.test(arg) && !/^--screenshots=.+/.test(arg) && !/^--inventory=.+/.test(arg) && !/^--min-screen-font=\d+(?:\.\d+)?$/.test(arg))) {
  throw Error('Usage: node scripts/check_text_layout.mjs Presentation.html [--export] [--actual-fonts] [--viewport=WIDTHxHEIGHT] [--screenshots=EMPTY_DIR] [--inventory=EXTRACTED_DECK] [--min-screen-font=PX]');
}
const inventoryArg=args.find(arg=>arg.startsWith('--inventory='));
const inventory=inventoryArg?JSON.parse(await fs.readFile(inventoryArg.slice('--inventory='.length),'utf8')):null;
const sourceBlocks=new Map();
if(inventory)for(const slide of inventory.slides??[])for(const block of slide.blocks??[])sourceBlocks.set(block.id,block);
const minFontArg=args.find(arg=>arg.startsWith('--min-screen-font='));
const minScreenFont=minFontArg?Number(minFontArg.slice('--min-screen-font='.length)):null;
if(minScreenFont!==null && (minScreenFont<=0 || minScreenFont>200))throw Error('Invalid minimum screen font size');
const viewportArg = args.find(arg => arg.startsWith('--viewport='));
const viewport = viewportArg ? (() => { const [width,height] = viewportArg.slice(11).split('x').map(Number); if (width < 200 || height < 200 || width > 10000 || height > 10000) throw Error('Invalid viewport'); return {width,height}; })() : null;
const inputHash = createHash('sha256').update(await fs.readFile(input)).digest('hex');
const screenshotArg=args.find(arg=>arg.startsWith('--screenshots='));
const screenshotDir=screenshotArg?path.resolve(screenshotArg.slice('--screenshots='.length)):null;
if(screenshotDir){await fs.mkdir(screenshotDir,{recursive:true});if((await fs.readdir(screenshotDir)).length)throw Error('Screenshot directory must be empty');}
const here = path.dirname(fileURLToPath(import.meta.url));
let config = {};
try {
  config = JSON.parse(await fs.readFile(path.join(here, '../runtime.local.json'), 'utf8'));
} catch (error) {
  if (error.code !== 'ENOENT') throw error;
}
const modules = process.env.HTML_MAKER_NODE_MODULES || config.nodeModules;
const require = modules ? createRequire(path.join(modules, 'package.json')) : createRequire(import.meta.url);
const { chromium } = require('playwright');
const frozen = args.includes('--export');
const browser = await chromium.launch({ headless: true, ...(process.env.HTML_MAKER_CHROME === 'bundled' ? {} : { channel: 'chrome' }) });

try {
  const page = await browser.newPage({
    viewport: viewport || (frozen ? { width: 1920, height: 1080 } : { width: 1600, height: 900 }),
    reducedMotion: 'reduce',
    serviceWorkers: 'block',
  });
  await page.route(/^https?:/, route => route.abort());
  await page.goto(pathToFileURL(path.resolve(input)).href);
  await page.waitForFunction(() => window.GigaDevDeck && window.SalesKitMotion);
  const cdp = args.includes('--actual-fonts') ? await page.context().newCDPSession(page) : null;
  let documentRoot;
  if (cdp) {
    await cdp.send('DOM.enable'); await cdp.send('CSS.enable');
    documentRoot = (await cdp.send('DOM.getDocument', {depth: -1})).root.nodeId;
  }
  const slides = await page.evaluate(async frozen => {
    await document.fonts.ready;
    if (frozen) await GigaDevDeck.prepareExport();
    return GigaDevDeck.getState().order;
  }, frozen);
  const report = [];
  for (const [index, id] of slides.entries()) {
    if (!frozen) {
      await page.evaluate(index => { goTo(index); SalesKitMotion.finish(); }, index);
      await page.waitForFunction(index => window.cur === index && Math.abs(slidesEl.scrollTop - slides[index].offsetTop) < 2, index);
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(resolve)));
    }
    if(frozen && screenshotDir)await page.evaluate(index=>{goTo(index);SalesKitMotion.finish()},index);
    const blocks = await page.evaluate(id => {
      const slide = document.querySelector(`#slides > [data-sk-id="${CSS.escape(id)}"]`);
      const content = slide.querySelector('.gd-content');
      const frame = slide.getBoundingClientRect();
      const contentScale = content.getBoundingClientRect().width / (content.offsetWidth || 1) || 1;
      const scale = contentScale;
      const segmenter = new Intl.Segmenter(undefined, { granularity: 'grapheme' });
      const skip = 'svg,canvas,video,audio,code,pre,script,style';
      const nodes = [...content.querySelectorAll('[data-eid]')];
      const targets = nodes.filter(node => !node.closest(skip) && !node.querySelector('[data-eid]'));
      const result = [];
      for (const block of targets) {
        if (!block.checkVisibility({ opacityProperty: true, visibilityProperty: true })) continue;
        const styles = getComputedStyle(block);
        if (styles.writingMode !== 'horizontal-tb') continue;
        const range = document.createRange();
        const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
        const lines = [];
        let clipped = false;
        const clip = { left: frame.left, right: frame.right, top: frame.top, bottom: frame.bottom };
        for (let parent = block; parent && parent !== slide; parent = parent.parentElement) {
          const css = getComputedStyle(parent), box = parent.getBoundingClientRect();
          if (['hidden', 'clip', 'scroll', 'auto'].includes(css.overflowX)) {
            clip.left = Math.max(clip.left, box.left);
            clip.right = Math.min(clip.right, box.right);
          }
          if (['hidden', 'clip', 'scroll', 'auto'].includes(css.overflowY)) {
            clip.top = Math.max(clip.top, box.top);
            clip.bottom = Math.min(clip.bottom, box.bottom);
          }
        }
        while (walker.nextNode()) {
          const text = walker.currentNode;
          if (text.parentElement.closest(skip) || !text.parentElement.checkVisibility({ opacityProperty: true, visibilityProperty: true })) continue;
          for (const { segment, index } of segmenter.segment(text.data)) {
            range.setStart(text, index);
            range.setEnd(text, index + segment.length);
            const rect = range.getBoundingClientRect();
            if (!rect.height || !rect.width) continue;
            if (!/^\s+$/u.test(segment) && (rect.left < clip.left - 2 || rect.right > clip.right + 2 ||
                rect.top < clip.top - 2 || rect.bottom > clip.bottom + 2)) clipped = true;
            const middle = (rect.top + rect.bottom) / 2;
            let line = lines.find(line => Math.abs(line.middle - middle) <= Math.min(line.height, rect.height) / 3);
            if (!line) {
              line = { middle, height: rect.height, left: rect.left, right: rect.right, text: '' };
              lines.push(line);
            }
            line.left = Math.min(line.left, rect.left);
            line.right = Math.max(line.right, rect.right);
            line.text += segment;
          }
        }
        const measured = lines.sort((a, b) => a.middle - b.middle).map(line => ({
          text: line.text.trim(), width: Math.round((line.right - line.left) / scale),
        })).filter(line => line.text);
        if (!measured.length) continue;
        const heading = /^H[1-6]$/.test(block.tagName);
        const prose = block.matches('p,li,blockquote');
        const flags = [];
        if (clipped) flags.push('clipping');
        if (prose && measured.some(line => [...line.text].length > 85)) flags.push('long-prose-line');
        if ((heading || prose) && measured.length > 1) {
          const tail = measured.at(-1);
          if (!/\s/u.test(tail.text) && tail.width < Math.max(...measured.map(line => line.width)) * 0.35) {
            flags.push('short-final-line');
          }
        }
        const unscaledWidth = block.offsetWidth;
        const elementScale = unscaledWidth > 0 ? block.getBoundingClientRect().width / unscaledWidth : contentScale;
        const effectiveScale = Number.isFinite(elementScale) && elementScale > 0 ? elementScale : contentScale;
        result.push({
          sourceId: block.dataset.sourceId || null,
          sourceAncestorId: block.closest('[data-source-id]')?.dataset.sourceId || null,
          tableCell: (() => {const c=block.closest('td,th');const table=c?.closest('table[data-source-id]');return table ? {row:c.parentElement.rowIndex,column:c.cellIndex} : null;})(),
          editorId: block.dataset.eid,
          tag: block.tagName.toLowerCase(),
          role: block.getAttribute('data-layout-role') || block.tagName.toLowerCase(),
          slot: block.getAttribute('data-layout-slot') || null,
          alignGroup: block.getAttribute('data-layout-align-group') || null,
          alignTolerance: Number(block.getAttribute('data-layout-align-tolerance') || 4),
          blockLeft: (block.getBoundingClientRect().left-content.getBoundingClientRect().left)/scale,
          fontFamily: styles.fontFamily,
          fontWeight: styles.fontWeight,
          fontSizeCSS: parseFloat(styles.fontSize),
          fontSizeScreen: Math.round(parseFloat(styles.fontSize) * effectiveScale * 100) / 100,
          lineHeightCSS: styles.lineHeight,
          screenScale: Math.round(effectiveScale * 10000) / 10000,
          contentScale: Math.round(contentScale * 10000) / 10000,
          nestedScaleEstimate: Math.round((effectiveScale / contentScale) * 10000) / 10000,
          blockWidth: Math.round(block.getBoundingClientRect().width / scale),
          lines: measured,
          lineBoxes: lines.map(line => ({left:(line.left-frame.left)/scale,top:(line.middle-line.height/2-frame.top)/scale,right:(line.right-frame.left)/scale,bottom:(line.middle+line.height/2-frame.top)/scale})),
          allowOverlap: (block.dataset.layoutAllowOverlap || '').split(/\s+/).filter(Boolean),
          flags,
        });
      }
      return result;
    }, id);
    if (cdp) for (const block of blocks) {
      const selector = `#slides > [data-sk-id=${JSON.stringify(id)}] [data-eid=${JSON.stringify(block.editorId)}]`;
      try {
        const {nodeId} = await cdp.send('DOM.querySelector', {nodeId: documentRoot, selector});
        if (!nodeId) throw Error('DOM node not found');
        block.renderedFonts = (await cdp.send('CSS.getPlatformFontsForNode', {nodeId})).fonts;
      } catch (e) { block.renderedFonts = null; block.fontInspectionError = e.message; }
    }
    if(minScreenFont!==null)for(const block of blocks)if(block.fontSizeScreen<minScreenFont)block.flags.push('small-screen-font-review');
    if(inventory)for(const block of blocks){
      const source=sourceBlocks.get(block.sourceId || block.sourceAncestorId);if(!source)continue;
      const merged=source.kind==='table' && (source.tableLayout?.rows??[]).some(row=>(row.cells??[]).some(cell=>['hMerge','vMerge'].some(k=>['1','true'].includes(cell.attributes?.[k])) || ['gridSpan','rowSpan'].some(k=>Number(cell.attributes?.[k]||1)>1)));
      const cell=source.kind==='table' && block.tableCell && !merged ? source.rows?.[block.tableCell.row]?.[block.tableCell.column] : null;
      const paragraphs=source.kind==='table'?(cell??(source.rows??[]).flat(2)):source.paragraphs??[];
      const runs=paragraphs.flatMap(p=>p.runs??[]).filter(r=>r.text && r.text.trim());
      const sizes=[...new Set(runs.map(r=>r.effectiveTypography?.properties?.sizePt?.value ?? r.size).filter(Number.isFinite))].sort((a,b)=>a-b);
      const families=[...new Set(runs.map(r=>r.effectiveTypography?.properties?.latin?.family ?? r.font).filter(Boolean))].sort();
      const sources=[...new Set(runs.map(r=>r.effectiveTypography?.properties?.sizePt?.source).filter(Boolean))].sort();
      const width=inventory.source?.canvas?.widthEMU;
      const faces=[...new Map(runs.map(r=>{const p=r.effectiveTypography?.properties??{};const face={family:p.latin?.family??r.font??null,bold:p.bold?.value??r.bold??null,italic:p.italic?.value??r.italic??null};return [JSON.stringify(face),face]})).values()];
      block.sourceTypography={sourceId:source.id,tableCellMatched:Boolean(cell),nominalPt:sizes,normalizedCanvasPx:width?sizes.map(size=>Math.round(size*12700*1920/width*100)/100):null,families,faces,sizeSources:sources,unresolvedRuns:runs.filter(r=>!r.effectiveTypography?.properties?.sizePt || !r.effectiveTypography?.properties?.latin?.family).length,limitation:'Partial inheritance; Latin names and nominal sizes are source evidence, not proof of actual rendered glyphs.'};
      if(cdp && families.length && block.renderedFonts?.length){const normalize=x=>String(x).toLowerCase().replace(/[^\p{L}\p{N}]+/gu,'');const actual=block.renderedFonts.flatMap(f=>[f.familyName,f.postScriptName]).map(normalize);if(families.some(f=>!actual.includes(normalize(f))))block.flags.push('source-font-difference-review');}
    }
    const overlaps=[];
    for(let i=0;i<blocks.length;i++)for(let j=i+1;j<blocks.length;j++){
      const a=blocks[i],b=blocks[j];
      if(a.allowOverlap.includes(b.editorId)||a.allowOverlap.includes(b.sourceId)||b.allowOverlap.includes(a.editorId)||b.allowOverlap.includes(a.sourceId))continue;
      let area=0;for(const x of a.lineBoxes)for(const y of b.lineBoxes){const w=Math.min(x.right,y.right)-Math.max(x.left,y.left),h=Math.min(x.bottom,y.bottom)-Math.max(x.top,y.top);if(w>1&&h>1)area+=w*h;}
      if(area>4)overlaps.push({code:'text-overlap-candidate',severity:'review',slide:id,targets:[{sourceId:a.sourceId,editorId:a.editorId},{sourceId:b.sourceId,editorId:b.editorId}],overlapArea:Math.round(area)});
    }
    const alignment=[];const groups=new Map();
    for(const block of blocks)if(block.alignGroup){const group=groups.get(block.alignGroup)||[];group.push(block);groups.set(block.alignGroup,group);}
    for(const [group,items] of groups){if(items.length<2)continue;const lefts=items.map(x=>x.blockLeft).sort((a,b)=>a-b),reference=lefts[Math.floor(lefts.length/2)];for(const item of items){const deviation=Math.abs(item.blockLeft-reference);if(!Number.isFinite(item.alignTolerance)||item.alignTolerance<0)alignment.push({code:'invalid-alignment-tolerance',severity:'review',slide:id,group,editorId:item.editorId});else if(deviation>item.alignTolerance)alignment.push({code:'alignment-review',severity:'review',slide:id,group,sourceId:item.sourceId,editorId:item.editorId,deviation,tolerance:item.alignTolerance});}}
    let framePath=null;
    if(screenshotDir){framePath=path.join(screenshotDir,`${String(index+1).padStart(3,'0')}-${id}.png`);await page.screenshot({path:framePath});}
    report.push({ slide: id, number: index + 1, framePath, blocks, overlaps, alignment });
  }
  console.log(JSON.stringify({ mode: frozen ? 'export' : 'reading', htmlPath:path.resolve(input),viewport: page.viewportSize(), minScreenFont, inputSha256: inputHash,sourceSha256:inventory?.source?.sha256??null, limitations: [cdp ? 'Rendered font evidence is limited to glyphs painted in the current browser and frame.' : 'Computed font-family does not prove the actual font face used; rerun with --actual-fonts.', 'Screen font size estimates total element scale using rendered/unscaled width; rotation, nonuniform transforms and mixed inline sizes require visual review.', 'Minimum size is supplied by the reviewer and flags candidates; it is not an automatic design verdict.'], slides: report }, null, 2));
} finally {
  await browser.close();
}
