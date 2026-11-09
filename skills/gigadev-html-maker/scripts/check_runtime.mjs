/* HTML-only shell identity inspection, including one-step navigation and project order. */
import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { checkShellIdentity } from './shell_identity.mjs';

const [input, projectPath, ...extra] = process.argv.slice(2);
const issues = [];
const checks = [];
let browser;
try {
  if (!input || extra.length) throw Error('Usage: node check_runtime.mjs Presentation.html [project/deck.json]');
  const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
  const pointer = JSON.parse(await fs.readFile(path.join(root, 'assets/current-baseline.json'), 'utf8'));
  const pkg = JSON.parse(await fs.readFile(path.join(root, 'package.json'), 'utf8'));
  if (pointer.version !== pkg.version || !/^baseline-release-[a-z0-9-]+\.json$/.test(pointer.file)) {
    throw Error('Invalid or mismatched release baseline pointer');
  }
  const baseline = JSON.parse(await fs.readFile(path.join(root, 'assets', pointer.file), 'utf8'));
  let config = {};
  try { config = JSON.parse(await fs.readFile(path.join(root, 'runtime.local.json'), 'utf8')); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  const modules = process.env.HTML_MAKER_NODE_MODULES || config.nodeModules;
  const require = modules ? createRequire(path.join(modules, 'package.json')) : createRequire(import.meta.url);
  const { chromium } = require('playwright');
  browser = await chromium.launch({
    channel: process.env.HTML_MAKER_CHROME === 'bundled' ? undefined : 'chrome',
    headless: true,
  });
  const page = await browser.newPage({viewport: {width: 1440, height: 900}});
  await page.route(/^https?:/, route => route.abort());
  page.on('pageerror', error => issues.push({code: 'page-error', message: error.message}));
  await page.goto(pathToFileURL(path.resolve(input)).href, {waitUntil: 'domcontentloaded'});
  issues.push(...await checkShellIdentity(page, baseline, path.join(root, 'assets')));
  if (!issues.length) {
    checks.push('pinned shell modules and running stage');
    const state = await page.evaluate(() => SalesKitUI.getState());
    const domOrder = await page.locator('#slides > .slide').evaluateAll(nodes => nodes.map(n => n.dataset.skId));
    if (new Set(domOrder).size !== domOrder.length || state.order.some(id => !domOrder.includes(id))) {
      issues.push({code: 'slide-state', message: 'Slide state has duplicate or missing DOM IDs.'});
    }
    if (projectPath) {
      const project = JSON.parse(await fs.readFile(projectPath, 'utf8'));
      const expected = project.order ?? project.slides.map(slide => slide.id);
      if (JSON.stringify(expected) !== JSON.stringify(state.order)) {
        issues.push({code: 'order', message: 'Slide IDs/order differ from the project.'});
      }
    }
    if (state.order.length > 1) {
      await page.evaluate(id => { goTo(id); SalesKitMotion.finish(); }, 0);
      await page.keyboard.press('ArrowRight');
      await page.waitForFunction(() => SalesKitMotion.getState().phase === 'idle');
      const current = await page.evaluate(() => SalesKitUI.getState().current);
      if (current !== state.order[1]) issues.push({code: 'keyboard-step', message: 'One ArrowRight must select exactly the next slide.'});
      else checks.push('one key selects one next slide');
    }
  }
} catch (error) {
  issues.push({code: 'runtime-check', message: error.message});
} finally {
  if (browser) await browser.close();
}
console.log(JSON.stringify({status: issues.length ? 'fail' : 'pass', checks, issues, scope: 'runtime identity and navigation only', visualApproval: false}, null, 2));
if (issues.length) process.exitCode = 1;
