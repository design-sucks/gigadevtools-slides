# HTML Maker Linux compact anchor correction

## Cause

The compact-reading regression came from the runtime fit calculation in `controller.js`. At viewport widths up to 700 px, the navigation rail does not reserve width, and the bundled v02 layout uses 8 px side margins. The current fit calculation nevertheless kept a 20 px left gutter while reserving 8 px on the right. At 390 px this reduced the fitted width by 12 px, from 374 px to 362 px, changing the content scale and moving the original heading and body anchors.

The original failure is recorded in [GitHub Actions run 42464585360](https://github.com/design-sucks/gigadevtools-slides/actions/runs/42464585360). The failure was deterministic on Linux and independently reproduced in Chrome on macOS with all bundled fonts loaded.

## Change

For compact reading at widths up to 700 px, use the same 8 px left gutter as the right gutter. Desktop navigation reservation, dock behavior, presentation mode, original anchor data, and the strict 0.7 CSS-pixel comparison tolerance are unchanged.

The RC19 historical runtime snapshot stays immutable. `current-baseline.json` and `releases.json` now select a new follow-up snapshot derived from RC19 and containing the corrected `controller.js` digest.

## Verification

**Local checks pass; Linux CI is pending.** The focused compact browser suite passed in Chrome 157 on macOS with Node 24.12.0. It covers both themes at 1600×900, 1400×1330, 1280×800, and 390×844; all 13 slides; compact and presentation states; motion on/off; partial scroll; organizer thumbnails; edit/undo; navigation shortcuts; and export geometry. It completed 104 comparisons against the checked-in v02 heading/body anchors with the unchanged 0.7 CSS-pixel tolerance. The independent +8 px title-shift negative test still exits with the expected anchor failure.

`python3 scripts/check_release.py`, `python3 scripts/build_demo.py --check`, and JavaScript syntax checks passed. The source demo and Pages copy were regenerated from the updated runtime and match the builder. The compact check also verifies that the authored `sourceTopic` remains «Хоткеи», while the resolver records `topic-repeats-heading` and suppresses the duplicate runtime topic. No large authored presentation decks are included. Linux CI is still required before release.
