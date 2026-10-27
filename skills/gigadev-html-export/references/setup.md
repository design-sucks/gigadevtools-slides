# Single-command runtime

Use node scripts/run.mjs instead of rewriting environment setup per deck. --doctor reports selected Node modules, font modules, Python imports and browser executable. --compare selects Python visual-QA dependencies. A missing explicit environment override fails visibly. Nothing is downloaded or installed by the launcher.

Resolution: HTML_EXPORT_NODE_MODULES / HTML_EXPORT_FONT_MODULES / HTML_EXPORT_PYTHON overrides, optional runtime.local.json beside SKILL.md, skill-local node_modules / .venv, active Python venv, then available bundled Codex dependencies or normal Python commands. The host-only JSON accepts nodeModules, fontModules, python and optional chrome (bundled). --runtime FILE chooses another host config. Use absolute venv interpreter paths without resolving their symlinks: resolving to the system executable loses venv packages. Keep reusable libraries in a persistent location, not a temporary download folder.

runtime.local.json contains workstation paths and is excluded from portable archives. On another machine, install package.json with npm install and requirements.txt in the skill's .venv once. Raster PDF and compare require requirements-qa.txt. Installed Chrome is default; alternatively install Playwright Chromium and choose HTML_EXPORT_CHROME=bundled. Browser executable detection does not guarantee a launch is permitted by the host sandbox; a denied launch needs the normal local execution permission, not reinstalling everything.

```sh
node scripts/run.mjs --doctor
node scripts/run.mjs --source /absolute/deck.html --out /absolute/viewing --format pdf
node scripts/run.mjs --source /absolute/deck.html --out /absolute/editable --format pptx --groups auto
node scripts/run.mjs --compare --source /absolute/editable --powerpoint-pdf /absolute/native.pdf --out /absolute/review --only-outliers
```

A destination must be new or empty. PDF-only does not reconstruct or inspect PPTX objects. Unknown structures do not automatically select a grouping profile.

## Portable installation

From this skill directory, use installed dependencies if available; otherwise perform one-time setup:

```sh
npm install
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-qa.txt
npx playwright install chromium
HTML_EXPORT_CHROME=bundled node scripts/run.mjs --doctor
```

The example uses a POSIX shell. On Windows use python or py -3, .venv\Scripts\python.exe and set HTML_EXPORT_CHROME=bundled using that shell's environment syntax. Installed Chrome also works without the browser environment override. Package installation requires network access; it is not performed automatically by the converter.

No Codex service or account is required by the converter. The optional Codex runtime discovery is only a local dependency fallback. agents/openai.yaml is client metadata and can be ignored elsewhere. If native skill registration is unavailable, read SKILL.md and run scripts from the extracted folder. The agent needs filesystem and code execution; a text-only conversation cannot execute conversion.
