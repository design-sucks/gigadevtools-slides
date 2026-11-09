# Runtime

Extraction and assembly use Python 3.10+ standard library; no pip packages. check.mjs needs Node 20+, Playwright and Chrome. Use installed dependencies where possible. `npm install` in the skill folder installs package.json on a new machine; it is not run automatically. Playwright's bundled Chromium can be selected with HTML_MAKER_CHROME=bundled after installing it through Playwright. Default uses installed Chrome.

The checker resolves HTML_MAKER_NODE_MODULES, a host-only runtime.local.json {nodeModules}, then skill-local/normal Node resolution. Host config, node_modules, caches and temporary probes are excluded from portable archives. A browser launch denied by a host sandbox needs normal execution permission; reinstalling dependencies does not fix that permission.

For actual exported PPTX/PDF use the separate gigadev-html-export skill. HTML Export's own dependencies/config remain separate.

## Another agent environment

The core is a standard Agent Skills folder; agents/openai.yaml is optional client metadata. An agent that cannot register skills can read SKILL.md, resolve relative resources from this directory and execute the scripts. A text-only chat cannot run this pipeline by reading instructions alone. Do not regenerate the supplied shell as a workaround for unavailable execution.

One-time setup from this folder, only when browser QA dependencies are absent:

```sh
npm install
npx playwright install chromium
```

Then select the installed browser with HTML_MAKER_CHROME=bundled (shell environment syntax varies by OS). Extraction/build needs only Python 3.10+; use python on systems where python3 is not the executable name. Native PowerPoint and other-LLM behavior require their own verification; they are not established by this portable package.


## Guarded workflow

From the complete local skill directory, run:

```sh
python3 scripts/maker.py ready --report /absolute/readiness-v01.json
```

This checks Python and Node versions, pinned shell assets and the baseline pointer. It builds a temporary one-slide project through build.py and opens it in the actual browser to exercise the runtime. The temporary smoke files are removed. The JSON report identifies the failed stage when the package, dependencies or browser execution are unavailable. Use the setup steps above to resolve the actual error.

Readiness is needed before authoring in a new session/environment. The guarded final build repeats it. Reading individual GitHub files does not establish that the local package and execution environment are ready.
