# Quick start

## Content/PPTX → HTML

Provide the source, audience and a style reference. For a close style match, prefer a filled PPTX/HTML example plus actual font files you can use. Image-only references do not define exact font metrics.

```sh
python3 skills/gigadev-html-maker/scripts/maker.py ready --report build/readiness-v01.json
python3 skills/gigadev-html-maker/scripts/extract_pptx.py input.pptx build/project
python3 skills/gigadev-html-maker/scripts/build.py build/project/deck.json build/Draft_v01.html --theme examples/shell-demo/project/theme.json
```

Extraction is an inventory and assembly draft. The agent authors slide HTML from source blocks, preserves text/numbers and checks the result. Do not deliver an overflowing assembly draft as a finished design.

After reviewing the authored draft and recording its composition plan, build the delivery file through the guarded command:

```sh
python3 skills/gigadev-html-maker/scripts/maker.py build build/project/deck.json build/Presentation_v01.html --theme build/project/theme.json --composition-plan build/project/composition-plan.json --report build/final-check-v01.json
```

Use new output/report paths. A failure or review result requires resolving or reporting its underlying findings. Inspect the exact saved HTML with maker.py verify and a synchronized project. See [delivery checks](../skills/gigadev-html-maker/references/delivery-check.md).

To rebuild the included example:

```sh
python3 scripts/build_demo.py
```

## HTML → PPTX/PDF

```sh
node skills/gigadev-html-export/scripts/run.mjs --source examples/shell-demo/index.html --out build/pptx --format pptx
node skills/gigadev-html-export/scripts/run.mjs --source examples/shell-demo/index.html --out build/pdf --format pdf
```

Each output directory must be new/empty. Preflight may require review or a profile for new structures. Keep source files unchanged. PPTX acceptance includes text/font checks and actual target PowerPoint review; these commands are not a pre-existing proof for every deck. PDF defaults to viewing, not promised editable PDF.

## In the HTML shell

N toggles the list, M motion, E text editing, O organization, J journal, S version save. Slide 03 has the full overview. Ordinary letter commands do not interrupt typing. After edits, save a new HTML file and give that file to the agent for future work. Title/version in the save form become the new file's identity.
