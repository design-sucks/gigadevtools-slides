# RC13 — final checker corrections for the compact three-deck trial

The presentation runtime, builder, extraction and assets match RC12. The three final HTML decks produced by RC12 are qualified with these corrected checkers without a new design/conversion cycle.

- Source-palette literal evidence excludes bundled interface CSS and markup. It uses authored slide HTML, supported project background values/washes, final slide content/background markup and an explicitly provided theme JSON for stylesheet-only authoring. A shell-only accent no longer certifies slide color. This still does not solve cascade, effective visibility or per-object color fidelity.
- The shell regression selects an available nonempty text target instead of assuming the third slide contains text. It preserves reorder, metadata, calibration, save/reopen and export checks. A deck with no text, or insufficient slides for that scenario, reports explicit not-run and partial rather than waiting for a nonexistent target or claiming a complete pass.

RC12 reference notes describe the earlier list, paint-format and image-wash fixes. No private source decks, font files, media or slide-specific repair helper are included.
