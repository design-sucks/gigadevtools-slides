# Testing

## Fast checks

```sh
python3 scripts/check_release.py
python3 skills/gigadev-html-maker/scripts/self_test.py
python3 scripts/build_demo.py --check
```

## Browser checks for shell changes

After installing Maker dependencies and Chromium:

```sh
HTML_MAKER_CHROME=bundled node skills/gigadev-html-maker/scripts/check.mjs examples/shell-demo/index.html --out build/shell-qa
HTML_MAKER_CHROME=bundled node skills/gigadev-html-maker/scripts/check_compact.mjs examples/shell-demo/index.html build/compact-qa
HTML_MAKER_CHROME=bundled node skills/gigadev-html-maker/scripts/check_shortcuts.mjs examples/shell-demo/index.html build/keys-qa
```

Use new/empty QA directories. The compact checker is the bundled 13-slide fixture: 104 original heading/body anchor comparisons and 208 settled visibility states, motion on/off, both themes, four windows. It also exercises editing, final-slide reachability, thumbnail/show/export geometry. It does not grade arbitrary authored content.

The accepted working v05 supplied that full baseline; the reset to demo v01 ran a focused real save v02/reopen and all-page export handoff. Pilot packaging leaves runtime module hashes unchanged. Historical evidence is not claimed as a newly executed public benchmark.

Use check_ui_contrast.mjs when controls/colors change. The optional live reference comparator uses --anchor-progress for compact pages and needs a legally available reference; private SalesKit files are not required by CI. Compare raw native wheel travel separately. Matching curves does not prove absence of clipped/stray content, so review screenshots.

## PPTX

The converter checks page count, text/font coverage, counters/layouts/groups and package relationships. Actual PowerPoint proof and representative native edits are separate. Browser screenshots, PDF-only output or LibreOffice do not establish that proof. [Native QA](../skills/gigadev-html-export/references/native-qa.md).

Baseline changes require a reviewed intentional design change. Do not replace expected values just to make a regression pass.
