# Neutral base style kit

The primary composition vocabulary is the accepted [24-reference pack](reference-pack.md), revision 2.0.0 (v06 review). It supplies geometry, hierarchy and examples; map paint to the actual input palette. The older [18-pattern renderer](compositions.md) is retained for pinned projects, not the default for new designed decks.

The legacy kit in `assets/base-style.css`, `assets/base-theme.json`, and `assets/style-starter-deck.json` remains available for old projects and supplies six small archetypes: cover, split, sequence, comparison matrix, decision frame, and sources. It is intentionally neutral and deidentified. Replace sample copy before delivery.

Use explicit semantic classes in authored slide HTML: `.gd-base` for the page frame, `.gd-kicker` for a short eyebrow, `.gd-split` for asymmetric framing plus evidence, `.gd-rows` / `.gd-row` for ordered points, and `.gd-matrix` for readable comparisons. The dark and light token sets are authored palettes, not automatic inversion. The starter theme enables dark only; enable light deliberately in a project when the authored slide content has been checked for it. `base-theme.json` points to the CSS asset with `cssFile` for a project that copies the kit assets alongside its deck.

For a brand adaptation, change tokens and type scale first, then selectively override archetype classes. Keep table text readable, use rows when content is prose, and avoid adding card containers or decorative marks without a content reason. This kit is a starting point; it does not impose a second theme or replace slide-specific composition work.

The kit is a fallback vocabulary. With a source PPTX or mandatory style reference, map its evidenced palette/graphics onto these compositions first. Do not import the kit’s mint accent or remove source illustration instances merely because that shortens authoring. See source-style.md.
