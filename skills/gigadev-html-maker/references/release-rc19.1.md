# RC19.1 — mobile fitting and compact regression

Maker **0.22.0-rc19.1** packages the reviewed RC19 follow-up. Shell **v18.2**, Export **0.9.1**, navigation editing and the composition reference library remain unchanged.

At reading widths up to 700 px, use the original 8 px left margin alongside the 8 px right margin. The accidental 20 px desktop fallback reduced the fitted width by 12 px at 390 px, shifting headings and body anchors. Background paint still spans the full viewport; desktop/show/export fitting is preserved. This was reproduced on Linux and current macOS Chrome.

The compact checker now saves measured geometry, loaded-font and runtime diagnostics before assertions. The historical `demo-anchors-v02.json` and every 0.7 CSS-pixel anchor tolerance are unchanged. A stale navigation assertion now checks all four intended properties: heading text «Хоткеи», original `sourceTopic`, `topic-repeats-heading` disposition and suppressed duplicate runtime topic.

## Verification scope

The included runtime passed [Linux browser CI](https://github.com/design-sucks/gigadevtools-slides/actions/runs/42516574061) and [source CI](https://github.com/design-sucks/gigadevtools-slides/actions/runs/42516574087) before this packaging-only version bump. The full compact fixture covers 13 slides, both themes, four viewport sizes, 104 original anchor comparisons, 208 settled motion states, partial scroll, show/export, thumbnails, editing/undo and N/M. Independently inspected Linux measurements had a maximum absolute anchor difference of 0.00048828125 CSS px; narrow cover anchors exactly matched. An injected 8 px heading displacement failed the checker as intended.

No new chart/template/typography library or broad real-deck/native PowerPoint qualification is included. Historical RC19 runtime and anchor snapshots remain unchanged. See [RC19 features](release-rc19.md) and [compact reading](compact-reading.md).
