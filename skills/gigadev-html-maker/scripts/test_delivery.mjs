/* Local browser regression for failure modes seen in Maker deliveries. */
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const temp = await fs.mkdtemp(path.join(os.tmpdir(), 'maker-delivery-'));
const python = process.env.HTML_MAKER_PYTHON || 'python3';
const vector = '<svg data-source-id="icon" width="100" height="100" viewBox="0 0 10 10"><circle cx="5" cy="5" r="4" fill="white"/></svg>';
const pixel = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aVaUAAAAASUVORK5CYII=';
const fixture = '<h1 data-source-id="title">Проверка слайда</h1><p data-source-id="body">Точный исходный текст.</p>' + vector;
const cases = [
  { name:'valid', html:fixture, codes:[] },
  { name:'foreign', html:fixture, foreign:true, codes:['shell','shell-module'] },
  { name:'nested', html:'<div class="slide">' + fixture + '</div>', codes:['nested-slide'] },
  { name:'inset', html:'<div style="width:100%;height:100%;border:2px solid white;border-radius:16px">' + fixture + '</div>', codes:['inset-frame'] },
  { name:'raster', html:fixture.replace(vector, `<img data-source-id="icon" src="${pixel}" width="100" height="100">`), codes:['rasterized-vector','upscaled-image'] },
  { name:'text', html:fixture.replace('Точный исходный текст.', 'Подмена.'), codes:['source-text'] },
  { name:'motion', html:fixture, motion:false, codes:['motion-off'] },
  { name:'painted-static', html:fixture, css:'.slide *{opacity:1!important;filter:none!important}', codes:['scroll-motion','keyboard-motion'] },
  { name:'aspect', html:fixture, canvas:{widthEMU:4,heightEMU:3}, codes:['source-aspect'] },
];
function run(command, args) {
  const result = spawnSync(command, args, { encoding:'utf8', maxBuffer:1024*1024 });
  if (result.error) throw result.error;
  return result;
}

try {
  for (const item of cases) {
    const deck = {
      title:'Контроль выдачи',
      slides:[
        { id:'s1', html:item.html, blocks:[
          { id:'title', kind:'text', paragraphs:[{text:'Проверка слайда'}] },
          { id:'body', kind:'text', paragraphs:[{text:'Точный исходный текст.'}] },
          { id:'icon', kind:'image', asset:'source.svg' },
        ] },
        { id:'s2', html:'<h1>Следующий слайд</h1>' },
      ],
    };
    if (item.motion !== undefined) deck.motion = item.motion;
    if (item.canvas) deck.source = {canvas:item.canvas};
    const project = path.join(temp, item.name + '.json');
    const output = path.join(temp, item.name + '.html');
    await fs.writeFile(project, JSON.stringify(deck));
    if (item.foreign) await fs.writeFile(output, '<!doctype html><main>Foreign shell</main>');
    else {
      const args = [path.join(here, 'build.py'), project, output];
      if (item.css) {
        const theme = path.join(temp, item.name + '-theme.json');
        await fs.writeFile(theme, JSON.stringify({css:item.css}));
        args.push('--theme', theme);
      }
      const built = run(python, args);
      assert.equal(built.status, 0, built.stderr);
    }
    const result = run(process.execPath, [path.join(here, 'check_delivery.mjs'), output, project]);
    assert.equal(result.status, item.codes.length ? 1 : 0, result.stderr || result.stdout);
    const report = JSON.parse(result.stdout);
    assert.deepEqual([...new Set(report.issues.map(issue => issue.code))].sort(), [...item.codes].sort(), item.name);
    console.log(item.name + ' PASS');
  }
} finally {
  await fs.rm(temp, {recursive:true,force:true});
}
