# Testing

## Fast checks

```sh
python3 scripts/check_release.py
python3 skills/gigadev-html-maker/scripts/self_test.py
python3 skills/gigadev-html-maker/scripts/check_core_regression.py
python3 skills/gigadev-html-maker/scripts/test_source_style.py
python3 skills/gigadev-html-maker/scripts/test_compositions.py
python3 skills/gigadev-html-maker/scripts/test_reference_pack.py
python3 scripts/build_demo.py --check
```

## Browser checks for shell changes

After installing Maker dependencies and Chromium:

```sh
HTML_MAKER_CHROME=bundled node skills/gigadev-html-maker/scripts/check.mjs examples/shell-demo/index.html --out build/shell-qa
HTML_MAKER_CHROME=bundled node skills/gigadev-html-maker/scripts/check_compact.mjs examples/shell-demo/index.html build/compact-qa
HTML_MAKER_CHROME=bundled node skills/gigadev-html-maker/scripts/check_shortcuts.mjs examples/shell-demo/index.html build/keys-qa
HTML_MAKER_CHROME=bundled node skills/gigadev-html-maker/scripts/check_core_browser.mjs build/core-qa
HTML_MAKER_CHROME=bundled node skills/gigadev-html-maker/scripts/check_background_motion.mjs build/background-qa
```

Use new/empty QA directories. The compact checker is the bundled 13-slide fixture: 104 original heading/body anchor comparisons and 208 settled visibility states, motion on/off, both themes, four windows. It also exercises editing, final-slide reachability, thumbnail/show/export geometry. It does not grade arbitrary authored content.

The accepted working v05 supplied the historical baseline. The v0.2 local candidate runs the same shell/compact suites against a fresh demo build and adds 9 core browser checks: offline CSS assets, background coverage, journal decisions/save/reopen, review status, header modes and theme selection. The module hashes intentionally differ; old snapshots remain for provenance. Historical evidence is not claimed as a newly executed public benchmark.

For the Export paragraph regression run `node skills/gigadev-html-export/scripts/check_text_pitch.mjs` after resolving its normal Playwright dependency. It exercises real DOM capture for ordinary wrap, initial/later paragraph spacing and genuine negative-gap rejection. PDF theme smoke tests should check actual selected pixels, a single output page set and absence of speculative PPTX; do not infer native PPTX fidelity from them.

Use check_ui_contrast.mjs when controls/colors change. The optional live reference comparator uses --anchor-progress for compact pages and needs a legally available reference; private SalesKit files are not required by CI. Compare raw native wheel travel separately. Matching curves does not prove absence of clipped/stray content, so review screenshots.

## PPTX

The converter checks page count, text/font coverage, counters/layouts/groups and package relationships. Actual PowerPoint proof and representative native edits are separate. Browser screenshots, PDF-only output or LibreOffice do not establish that proof. [Native QA](../skills/gigadev-html-export/references/native-qa.md).

Baseline changes require a reviewed intentional design change. Do not replace expected values just to make a regression pass.

The background suite checks full-viewport coverage with navigation on/off, content anchors, wide/tall/mobile windows, native wheel travel and reversal, timed key fades, motion-off and save/reopen. It reproduces the v18.0 layer bug before the repair. Inspect image/gradient backgrounds too: a uniform slide color can hide stage gutters.

For PPTX import changes, read compact style-inventory colorSummary and test visual-decisions.json with source_style.py. The negative fixture includes a retained cover plus17 omitted SVGs; it must fail. Native proof must identify the exact QA-copy path before every dependent save/export/close; a denied open stops the chain. The optional AppleScript helper needs the normal Mac application/automation context; sandbox dictionary errors are not permission to fall back to another document.

## Composition library 1.0.0

Build neutral normal/headings/uneven fixtures with Maker scripts/build_composition_demo.py, then run check_compositions.mjs on each HTML and inspect their renders. Release evidence: 36 normal states, 108 heading states, 12 uneven-body states; three private real-content slides additionally preserve 45 source text objects, a table, links and three icons (counts confirmed in the release QA report). The accepted shell demo stays byte-identical. These bounded checks are not a general design-quality score or PPTX acceptance.

## Accepted references 2.0.0 and Maker 0.21.1

All 24 anonymized v06 reference pages were pixel-compared in Chrome after common-font deduplication: 24 identical. The fresh 10-slide GLM/DeepSeek/Qwen retest retained 124 exact content text objects, 2 tables, 18 graphic instances and8 links; 20 original navigation/count objects moved into metadata and 9 decorative indices were deliberately removed. HTML and native PowerPoint Mac renders were reviewed. Manual native edit-save and Windows were not tested in this run. Private deck content and proofs are not included in the public repository.

The user still found the resulting design too primitive, with density, line-length and wrap weaknesses. Those remain open quality issues despite successful structural/export checks. The 0.21.1 patch documents this boundary; it does not introduce an automatic text-balancing algorithm or claim a new design-quality pass.
