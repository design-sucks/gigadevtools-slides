/* Shared release identity check for full delivery and HTML-only inspection. */
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';

export async function checkShellIdentity(page, baseline, assets) {
  const issues = [];
  const names = Object.keys(baseline.modules).filter(name => name !== 'shell.html');
  const fragments = Object.fromEntries(await Promise.all(
    names.filter(name => name.endsWith('.css') && !['ui.css', 'deck.css'].includes(name))
      .map(async name => [name, await fs.readFile(path.join(assets, name), 'utf8')])
  ));
  const domIds = names.map(name => {
    if (name === 'controller.js') return 'sk-controller';
    if (name === 'deck.css') return 'gd-deck-styles';
    if (name === 'ui.css') return 'sk-ui-styles';
    if (name.endsWith('.css')) return 'gd-style-pack';
    return 'gd-' + name.slice(0, -3);
  });
  const parts = await page.evaluate(ids => ({
    marker: document.documentElement.dataset.gdMaker,
    version: window.GigaDevDeck?.shellVersion,
    stages: document.querySelectorAll('#sk-stage > #sk-canvas > #slides').length,
    contents: ids.map(id => {
      const matches = document.querySelectorAll('#' + id);
      return matches.length === 1 ? matches[0].textContent : null;
    }),
  }), domIds);
  if (parts.marker !== '1' || parts.version !== 'v18.2' || parts.stages !== 1) {
    issues.push({code: 'shell', message: 'Expected a running Maker v18.2 shell and its canonical stage.'});
  }
  for (const [index, name] of names.entries()) {
    let content = parts.contents[index];
    if (fragments[name]) content = content?.includes(fragments[name]) ? fragments[name] : null;
    if (content === null || createHash('sha256').update(content).digest('hex') !== baseline.modules[name]) {
      issues.push({code: 'shell-module', message: 'Missing or modified shell module.', module: name});
    }
  }
  return issues;
}
