# Accepted composition references 2.0.0

24 anonymized, reviewed examples (accepted v06). These are editable visual references, not a universal renderer or finished content. Use their composition and type hierarchy; source/reference paint and graphics take precedence. The older 18-pattern renderer is a separate compatibility tool, not a faithful implementation of these examples.

## Retrieve only what matters

Run `python3 scripts/reference_pack.py list`. Choose by rhetorical purpose and actual content volume. `show ref-10` returns one example and preview path. Inspect 1–3 matching previews; read only their HTML if geometry needs clarification. Do not load the whole corpus or embedded fonts into context. The catalog is `assets/reference-pack/catalog.json`; exact grid/type details are in `geometry.json`.

- ref-01/02 covers, ref-03 divider, ref-04 agenda.
- ref-05 argument, ref-06 complex process, ref-07 problems, ref-08 node architecture, ref-09 feature map.
- ref-10 complex table, ref-11 metrics, ref-12 bar trend, ref-13 status, ref-14 system and secondary insights.
- ref-15 offers, ref-16 screen, ref-17 gallery, ref-18 scorecard, ref-19 roadmap.
- ref-20 area, ref-21 paired bars, ref-22 distribution, ref-23 three feature cards, ref-24 pipeline.

## Compose, rather than copy a branded slide

1. Inventory exact content and graphics. Resolve primary theme and source paint roles before layout. An explicit restyling reference may replace source style; record that authorization. With no style evidence, choose a coherent neutral palette for the project rather than treating sample green as its brand.
2. Record per slide: selected reference/revision, purpose, adaptation, source IDs and intended graphics. A reference is not a capacity promise. Choose another layout or author a custom variant when full content does not fit; never omit text or shrink all type to force a match.
3. Author ordinary editable slide HTML inside the existing shell. Snapshot examples have full 1920×1080 frames; the Maker body uses its own safe content area. Transform geometry into that coordinate frame. Do not paste another viewer, reference page counter or `ref-nav`: generate navigation once from metadata. Put full-canvas paint in slide.background. Reference snapshots are marked sample-only and rejected by build.py if pasted unchanged.
4. Inherit composition, hierarchy, spacing and relationship logic, not sample wording, numbers, source logos or decorative gradients. Preserve actual source graphics with correct proportions. Connectors sit above the relevant surfaces and really meet their nodes. Keep complex topology when meaningful.
5. Render cover, table and dense examples, then every slide. Compare complete text/data/links, source graphics, real font wraps, contrast, layers, backgrounds and whitespace. Bounds checks are only one gate. A new PPTX additionally needs native PowerPoint acceptance.

## Paint is explicitly separate

**Example colors are inspection-only.** Never apply the sample mint/green, dark green surfaces or chart palette verbatim to a supplied blue/purple/light deck. Use semantic roles: bg, ink, muted, surface, surfaceSecondary, line, accent, accentSoft, onAccent, series2, series3. Map these to source evidence or the user's style reference, retaining source category meaning and contrast. Status colors require their own meaning; do not blindly recolor success/error into one accent. The shell's neutral/mint controls remain independent of slide paint.

For a palette study, provide all 11 roles as #RRGGBB in a JSON object and run:

```sh
python3 scripts/reference_pack.py study ref-14 --palette project-paint.json --out /absolute/new-study
```

This maps all known HTML/CSS/SVG paint literals through the explicit palette and preserves alpha. It deliberately has **no default palette**. The output remains sample-only. Embedded illustrative artwork may contain fixed colors and must be replaced with project graphics; this utility is not an automatic brand or contrast validator. Final project paint still needs source-style.py and actual visual QA.

## Shared geometry, flexible inner alignment

Use a common outer grid: reference content x80..1840 on 1920×1080. Ordinary headings: SB Sans Display600, about56/1.12; Text for body/UI. Extended is selective for covers, section dividers or major figures, never a default on every heading. Respect supplied fonts when style requires them. Optional subtitle is smaller; a title continuation may use muted ink. Do not add decorative separators or a terminal dot automatically. Wrap long titles by meaning.

Adapt tables/grids to the available width. Do not merely shift a narrow centered source page left and leave a vacant right half. Compact diagrams may remain balanced within the shared grid; node captions can be centered. Main and secondary insight bands need different tonal emphasis, readable text and clear grouping. Dense content should show hierarchy rather than repetitive surfaces/dividers. Charts require exact labels, units and honest baselines; reference numbers are synthetic examples only.

## Maintain locally and portably

Keep IDs/revisions stable and patch only the relevant example after review. Update its preview/hash/catalog and any affected paint mapping; record the accepted composition change separately from shell changes. Recheck selected short/long content and alternate project paint. Include only anonymized examples, never raw captures, private inventories or source notes. Font assets retain their separate licensing scope.
