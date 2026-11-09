"""Portable browser regressions for guarded Maker delivery."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

SKILL = Path(__file__).resolve().parent.parent


def write_json(file, value):
    file.write_text(json.dumps(value, ensure_ascii=False, indent=2))


def run(command, expected=0, env=None):
    result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=240)
    if result.returncode != expected:
        raise AssertionError(result.stdout + result.stderr)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError('Use an empty test directory')
    maker = [sys.executable, '-B', str(SKILL / 'scripts/maker.py')]
    checks = []
    run(maker + ['ready', '--report', str(out / 'ready.json')])
    checks.append('complete package executes builder and browser')

    foreign = out / 'foreign.html'
    foreign.write_text('<!doctype html><html data-gd-maker="1"><body><article class="slide">'
                       '<h1 contenteditable="true">Alternate viewer</h1>'
                       '<button>Save</button></article></body></html>')
    run(maker + ['verify', str(foreign), '--report', str(out / 'foreign.json')], expected=1)
    rejected = json.loads((out / 'foreign.json').read_text())
    assert any(i['code'] == 'shell-module' for i in rejected['failure']['result']['issues'])
    checks.append('alternate viewer with editable text and Maker marker is rejected')

    missing_env = dict(os.environ, HTML_MAKER_NODE_MODULES=str(out / 'missing-node-modules'))
    run(maker + ['ready', '--report', str(out / 'missing-dependency.json')],
        expected=1, env=missing_env)
    assert json.loads((out / 'missing-dependency.json').read_text())['status'] == 'fail'
    checks.append('unavailable browser dependency is reported as failure')

    partial = out / 'partial-skill'
    shutil.copytree(SKILL, partial, ignore=shutil.ignore_patterns('node_modules', '__pycache__'))
    (partial / 'assets/controller.js').unlink()
    run([sys.executable, '-B', str(partial / 'scripts/maker.py'), 'ready',
         '--report', str(out / 'partial.json')], expected=1)
    checks.append('incomplete pinned package is rejected')

    slides = []
    for i in range(1, 4):
        title, body = 'Slide ' + str(i), 'Exact editable source paragraph ' + str(i) + '.'
        slides.append({'id': 's' + str(i), 'label': title, 'header': 'none',
                       'blocks': [{'id': 'title', 'kind': 'text',
                                   'paragraphs': [{'text': title, 'runs': [{'text': title}]}]},
                                  {'id': 'body', 'kind': 'text',
                                   'paragraphs': [{'text': body, 'runs': [{'text': body}]}]}],
                       'html': '<h2 data-source-id="title">' + title + '</h2>'
                               '<p data-source-id="body">' + body + '</p>'})
    project = out / 'deck.json'
    write_json(project, {'title': 'Guarded regression', 'cssIsolation': 'strict', 'slides': slides})
    (out / 'outline.txt').write_text('Three source-bound text slides for a technical regression.')
    draft = out / 'draft.html'
    run([sys.executable, '-B', str(SKILL / 'scripts/build.py'), str(project), str(draft)])
    capture = out / 'capture.mjs'
    capture.write_text("""
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const [skill, folder] = process.argv.slice(2);
let config = {};
try { config = JSON.parse(await fs.readFile(path.join(skill, 'runtime.local.json'), 'utf8')); }
catch (error) { if (error.code !== 'ENOENT') throw error; }
const modules = process.env.HTML_MAKER_NODE_MODULES || config.nodeModules;
const require = createRequire(path.join(modules || skill, 'package.json'));
const {chromium} = require('playwright');
const browser = await chromium.launch({headless:true,
  ...(process.env.HTML_MAKER_CHROME === 'bundled' ? {} : {channel:'chrome'})});
try {
  const page = await browser.newPage({viewport:{width:1920,height:1080}});
  await page.goto(pathToFileURL(path.join(folder, 'draft.html')).href);
  await page.evaluate(async()=>{await GigaDevDeck.prepareExport(); await document.fonts.ready;});
  for (let i=0;i<3;i++) {
    const slide=page.locator('#slides>.slide').nth(i);
    await slide.scrollIntoViewIfNeeded();
    await slide.screenshot({path:path.join(folder,'slide-'+i+'.png')});
  }
} finally { await browser.close(); }
""")
    run(['node', str(capture), str(SKILL), str(out)])
    project_hash = hashlib.sha256(project.read_bytes()).hexdigest()
    plan = []
    for i, slide in enumerate(slides):
        frame = out / ('slide-' + str(i) + '.png')
        plan.append({'slideId': slide['id'], 'sourceId': slide['id'], 'decision': 'preserve',
                     'sourceOutline': 'outline.txt',
                     **{field: 'Synthetic technical regression fixture' for field in
                        ['purpose', 'emphasis', 'readingOrder', 'groups', 'density',
                         'editability', 'works', 'problem', 'capacity', 'technicalRisk']},
                     'visualReview': {'reviewed': True,
                                      'observation': 'Technical test fixture with captured source-bound text.',
                                      'candidateRender': frame.name,
                                      'candidateRenderSha256': hashlib.sha256(frame.read_bytes()).hexdigest(),
                                      'projectSha256': project_hash}})
    plan_file = out / 'plan.json'
    write_json(plan_file, {'inputKind': 'outline', 'slides': plan})
    final = out / 'final.html'
    run(maker + ['build', str(project), str(final), '--composition-plan', str(plan_file),
                 '--report', str(out / 'final.json')])
    report = json.loads((out / 'final.json').read_text())
    assert report['verification']['hashes']['html'] == hashlib.sha256(final.read_bytes()).hexdigest()
    ui_report = json.loads((out / 'final.shell-qa/report.json').read_text())
    assert ui_report['status'] == 'pass' and not ui_report.get('notRun')
    checks.append('canonical final build passes identity, delivery, edit/save/reopen and binds exact hash')

    for name, before, after, expected_code in [
        ('changed-runtime', '<script id="sk-controller">', '<script id="sk-controller">\n/* altered */',
         'shell-module'),
        ('changed-text', 'Exact editable source paragraph 1.', 'Changed source content.', 'source-text')
    ]:
        changed = out / (name + '.html')
        original = final.read_text()
        assert before in original
        changed.write_text(original.replace(before, after, 1))
        proof = out / (name + '.json')
        run(maker + ['verify', str(changed), '--project', str(project), '--report', str(proof)],
            expected=1)
        issues = json.loads(proof.read_text())['failure']['result']['issues']
        assert any(issue['code'] == expected_code for issue in issues)
        checks.append(name + ' rejected')

    write_json(out / 'report.json', {'status': 'pass', 'checks': checks,
                                     'visualApproval': False})
    print(json.dumps({'status': 'pass', 'checks': len(checks), 'output': str(out)}))


if __name__ == '__main__':
    main()
