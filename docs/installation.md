# Installation

Use a complete skill directory, including scripts, references and assets. agents/openai.yaml is optional client metadata; the portable entrypoint is SKILL.md. A language model alone is not the execution environment.

## HTML Maker

Python 3.10+ builds/extracts using its standard library. Browser QA requires Node 20+, Playwright and Chrome/Chromium.

```sh
cd skills/gigadev-html-maker
npm ci
npx playwright install chromium
```

Set HTML_MAKER_CHROME=bundled when using Playwright's Chromium. Installed Chrome is the default. [Runtime details](../skills/gigadev-html-maker/references/setup.md).

## HTML Export

```sh
cd skills/gigadev-html-export
npm ci
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-qa.txt
npx playwright install chromium
HTML_EXPORT_CHROME=bundled node scripts/run.mjs --doctor
```

On Windows use the executable names appropriate to the shell, such as py -3 and .venv\Scripts\python.exe. This is setup guidance, not a claim of native Windows PowerPoint validation. [Runtime details](../skills/gigadev-html-export/references/setup.md).

Host-only runtime.local.json may point to an existing installation. It is not committed or packaged. No dependency installation runs automatically in the converter. Neither skill requires a Codex service/account; an agent client supplies filesystem/code access.

Keep your existing skill directory backed up when installing an update. Preserve your host-only runtime config; replace the versioned package contents.
