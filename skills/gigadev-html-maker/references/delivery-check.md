# Required checks before HTML delivery

Build with `--final` and the approved composition plan. Check the exact HTML that will be handed off, including any newly saved version. Use the authored project that retains the original extracted source blocks and the expected order.

```sh
node scripts/check_delivery.mjs /absolute/Presentation.html /absolute/project/deck.json > /absolute/delivery-report.json
node scripts/check.mjs /absolute/Presentation.html --out /absolute/new-shell-qa
node scripts/check_text_layout.mjs /absolute/Presentation.html --export > /absolute/text-layout.json
```

Fix each delivery failure and rerun on the new output. Complete the existing PPTX [source-style check](source-style.md) for graphics and palette. The shell and text checkers write separate evidence.

## What the delivery check verifies

- Pinned Maker v18.2 runtime and styles, a working stage and matching slide order. An alternate viewer or an edited runtime fails. Motion must be active by default on normal systems. A partial native wheel scroll and ArrowRight must exercise actual blur and opacity. The shell's reduced-motion and motion-off controls remain available. If the user explicitly requested static playback by default, record `deliveryReview.motionOffReason`. The checker will enable motion in its test copy and exercise both transitions.
- One full 1920×1080 slide frame with the standard content safe area. Background paint covers the canvas. A nested viewer or shell inside slide content fails. Inset slide-sized images and near-full-size framed wrappers are flagged. Use an actual full-canvas background for slide paint. For a non-16:9 PPTX, agree how to adapt its layout and record the decision in `deliveryReview.sourceAspectReason`.
- Visible source targets for supported text, tables, images and media. Wording and table values are compared after normalizing whitespace. Supported source link destinations must remain present. Applied journal changes are recognized when their before text matches. The checker verifies the presence of video and audio elements; playback and triggers still require their own tests.
- Image decoding, original SVG retained as vector, and raster size at 1920×1080. The check flags visible bitmap images and full-canvas raster backgrounds enlarged above 1.25×. Correct the asset, crop or layout. Review icons, gradients, masks and illustration edges at 100% even when the resolution passes.

## Record approved source transformations

When source elements move into navigation metadata, are deliberately replaced or are omitted by agreement, record each affected source object with its reason. Use the existing graphic decision manifest for asset dispositions. The delivery review records only exceptions to target matching. It does not disable the independent image, canvas or motion checks.

```json
{
  "deliveryReview": {
    "sourceChanges": [{"slide":"s2","sourceId":"s2-o14","reason":"Original page number is now the Maker counter."}],
    "frames": [{"slide":"s8","reason":"User approved the border of the slide-sized diagram shown in the sample."}]
  }
}
```

Use `frames` only after visually confirming that the detected wrapper is intentional content. A real nested shell remains a failure. Keep the source records unchanged. If a slide has no source blocks, the delivery check reports `review`, not content `pass`; verify against an independent source inventory or approved brief. The separate independent DOM check must always be run for PPTX-derived content, including when derivative blocks are missing.

## Visual release review

Compare every slide with the source render and the approved sample direction. Check that layout fills the intended frame, meaningful objects and text are present, and image crops, transparency and vector shapes are intact. Check slide transitions in reading and presentation. When a rendered frame is wrong, resolve the cause and regenerate before delivery. The JSON report records automated checks and leaves visual approval separate. It cannot assess aesthetic layout, source graphics already pixelated at native size, all CSS effects, or content fidelity of diagrams and charts.

## Independent source inventory (project-level audit)

For a frozen subset made from a PPTX, retain the original and mini inventories unchanged. `python3 scripts/check_pptx_subset.py MANIFEST.json --case CASE > subset.json` verifies both package hashes, each selected slide XML and its direct relationships/parts and records original/mini object IDs; `python3 scripts/compare_subset_inventory.py ORIGINAL_DECK MINI_DECK subset.json` compares source records through that mapping. These structural checks do not establish rendered completeness or transitive package integrity. The aggregate acceptance report's `matrix` distinguishes `fail`, `review`, `pass` and `not-run`; source checks alone leave design, shell and media `not-run` and never certify final editing or aesthetic quality.

For PPTX deliveries with editable content, extract the original PPTX separately with `extract_pptx.py` into a new directory and retain its unmodified `deck.json` as evidence. Run `python3 scripts/check_source_inventory.py /path/to/extracted/deck.json /path/to/project/deck.json > source-audit.json`. An absent or changed source text/table target fails editable mode, including when the derivative project omitted the source block. Resolved direct or inherited source bullets and numbered lists are checked for paragraph count, HTML list type and nesting level. Unresolved inheritance is reported as review, not treated as a verified plain paragraph. `--mode viewing` reports these as review rather than declaring editability. The report records the source and inventory hashes. This project check does not inspect final browser DOM, actual editing and reopening, unresolved inheritance, run formatting or visual fidelity. It also cannot yet resolve structured composition source bindings or authorized redesign mappings; inspect these manually and do not interpret its result alone as delivery acceptance. Preserve the independent inventory separately from the edited project.

For the assembled HTML, run `node scripts/check_source_dom.mjs deck.html independent/deck.json project/deck.json`. This audits rendered DOM targets, including structured compositions, in each slide’s static export state and emits separate provisional content, structure and editability statuses. It checks text-node visibility, opacity, nonzero geometry and rectangular clipping against the slide and clipping ancestors, and inspects computed list markers. Hidden or clipped source text and absent/mismatched markers fail. Arbitrary masks and clipping paths receive review; occlusion by other elements and contrast require separate visual checks. Editor bindings alone do not prove interactive editing or save/reopen; run those checks separately. Optional `--transformations file.json` records an approved transformation with `slide`, `sourceId`, `targetId`, exact `before`, exact `after`, `reason` and `approved: true`; mismatched preconditions fail, and an accepted transformation remains a review item. Keep the independent inventory and transformation record outside the derivative project and review the evidence for approval.

For annotated SVG diagrams, `node scripts/check_graphic_layout.mjs deck.html` checks declared node references, path endpoints, label-to-node offsets and sampled edge/label collisions. Mark nodes with `data-diagram-node`, SVG geometry with `data-diagram-edge-from`, `data-diagram-edge-to` and an optional `data-endpoint-tolerance` in slide units. Mark labels with `data-diagram-label-for`, `data-anchor-dx`, `data-anchor-dy` and `data-anchor-tolerance`; the offset is between node and label centres. Explicitly justified overlaps can be listed by node ID in `data-allow-label-overlap` on an edge. An unannotated diagram cannot pass this relationship check. Sampling can miss intersections and does not check diagram meaning, source values or style; compare full frames visually.

For a PPTX-derived delivery use `node scripts/check_acceptance.mjs deck.html independent/deck.json project/deck.json NEW_QA_DIR --source original.pptx --kind editable` to collect shell delivery, independent DOM/source, solid-background contrast and portability reports. Use `--kind viewing` only for an explicitly accepted viewing result; missing editable targets then remain unverified rather than becoming editable content. The aggregator deliberately cannot return complete final acceptance: visual quality, media playback, interactive editing, broader shell regression and native PowerPoint are separate checks. A source hash proves identity, not correctness or independence of an inventory; retain the original extraction.

## Custom list markers

When a source list uses an intentionally custom marker, record the user-approved decision in `deliveryReview.customListMarkers`, with `slide`, `sourceId`, `approved: true` and a specific `reason`. The checker currently recognizes a visible CSS `::before` marker when native list markers are suppressed, or a custom `::marker`; it reports `review` even when approved because placement and actual painted glyphs still need visual confirmation. An unapproved custom replacement fails. Marker images, unusual numbering systems, arbitrary clip/mask geometry, overlapping objects and contrast need separate visual review; computed CSS alone cannot prove pixels or semantic equivalence.

```json
{"deliveryReview":{"customListMarkers":[{"slide":"s2","sourceId":"s2-o14","approved":true,"reason":"User approved the arrow marker in this list."}]}}
```

Table cell comparisons preserve word boundaries at `<br>` and block elements; they still compare each source row and cell and separately flag hidden or clipped text. `scripts/test_table_boundaries.mjs` exercises line breaks, missing words, reordered cells/rows and hidden content.

## Reviewed source text outside the slide

Keep the complete independent PPTX inventory. A source-bound text target normally remains required. If manual source review establishes that an ungrouped text shape is entirely below its original slide, record an explicit omission in a separate `--off-canvas` manifest; never silently delete the source record. Inspect the actual source-page render and the surrounding slide sequence, and state what happens to the text. The current implementation accepts only direct, unrotated/unflipped, top-anchored horizontal text shapes with known geometry wholly below the canvas. Groups, rotations, other directions, partial intersections, unknown transforms and effects are unresolved and cannot receive this exception.

Each entry must record the original slide and source ID, **exact inventory text**, source bounding box and canvas in EMU, `disposition: "omit"`, `reviewed: true`, a specific reason, and the source render path plus SHA-256. The top-level `sourceSha256` must identify the original PPTX. The project must retain the identical source block and identity; the target must be absent everywhere in the project and saved HTML, including excluded slides. If text is present but hidden, clipped or moved, resolve that as a separate mapping/visibility issue; an omission cannot waive it.

```json
{
  "sourceSha256": "<64-character SHA-256 of original PPTX>",
  "dispositions": [{
    "slide": 1, "sourceId": "s1-o20", "sourceText": "Exact source text",
    "geometryEMU": {"x": 100, "y": 1200, "width": 400, "height": 200},
    "canvasEMU": {"width": 1000, "height": 1000},
    "disposition": "omit", "reviewed": true, "reason": "Observed off-slide in the source render; context reviewed.",
    "sourceRender": "source/page-01.png", "sourceRenderSha256": "<64-character SHA-256 of render>"
  }]
}
```

```sh
python3 scripts/check_source_inventory.py full-source/deck.json project/deck.json --source original.pptx --off-canvas omissions.json
node scripts/check_source_dom.mjs Presentation.html full-source/deck.json project/deck.json --source original.pptx --off-canvas omissions.json
node scripts/check_acceptance.mjs Presentation.html full-source/deck.json project/deck.json NEW_QA_DIR --source original.pptx --off-canvas omissions.json
```

The source checker verifies the PPTX hash, source slide/object identity, source text and transform directly against the original OOXML, and matches the independently supplied inventory, project block and recorded geometry. A render hash verifies only file identity, not that the image was produced from the PPTX or that omission is appropriate: the declared review must inspect it. An accepted entry is reported as `source-off-canvas-reviewed` with source text, geometry, omission mapping and reason; overall content/acceptance cannot become `pass` from that entry. The aggregate preserves the raw delivery report and reclassifies only its matching missing-target issue to review after independent source, project and actual/saved HTML checks. Every other issue and missing slide remains a failure. Incomplete or unverified evidence is never a confirmed omission. Inventory completeness is a separate responsibility; a matching PPTX hash alone does not establish that an inventory was fully extracted.

### Reviewed transparent source runs

For a static PPTX source frame, an explicitly transparent source **run** may be preserved as transparent in the HTML with a reviewed disposition. Keep the complete source block, text and run order in the independent inventory and project; the HTML target must retain all source text. Add a plain single-text-node `<span data-source-alpha-run="0:0">` around the specific run, with zero text fill color alpha. The marker value is the zero-based `paragraphIndex:runIndex` in the original text shape, counting run, field and line-break entries. Do not use `display:none`, zero opacity, omit text, or apply this disposition to visible siblings.

Pass `--source original.pptx --source-alpha reviewed-runs.json` to `check_source_dom.mjs` or `check_acceptance.mjs`. Example manifest:

```json
{"sourceSha256":"<original PPTX SHA-256>","dispositions":[{"slide":2,"sourceId":"s2-o64","sourcePart":"ppt/slides/slide2.xml","paragraphIndex":0,"runIndex":0,"sourceText":"02","disposition":"preserve-transparent","reviewed":true,"reason":"Reviewed initial frame and subsequent state","sourceRender":"/absolute/path/to/source-slide.png","sourceRenderSha256":"<render SHA-256>"}]}
```

The verifier checks the actual PPTX hash, slide and shape, exact paragraph/run stream, direct `a:rPr/a:solidFill/*/a:alpha val="0"`, non-placeholder default text styles and local effects, marker location, full text order, target visibility and render-file hash. It rejects timing/transition, unsupported shape styles, ambiguous mapping, nonzero or inherited fill alpha, unverified render and hidden visible text. Other source and delivery errors remain errors; the raw delivery report is preserved. A reviewed disposition yields at most `review`, never visual or animation acceptance. The operator must inspect the source render, verify its provenance and expected subsequent reveal state; a render hash alone proves neither. Unsupported groups, placeholders, alternate or complex inheritance, transformations and actual PPTX animation remain unresolved. This contract does not authorize removing transparent runs or entire mixed blocks.

If the source text belongs to a painted shape, preserve and inspect the **shape independently** from its text. A narrowly supported ungrouped shape may add to each relevant run entry `"shapeReview":{"reviewed":true,"targetId":"s28-o21","reason":"specific source and candidate shape observation","candidateRender":"/path/candidate.png","candidateRenderSha256":"<SHA-256>","htmlSha256":"<exact HTML SHA-256>"}`. Use the actual source ID, not this example. The verifier resolves supported theme relationships, master color mapping, solid fill (including selected color transforms), simple solid/no-fill line, an empty referenced effect, and rect/roundRect geometry; unsupported properties remain unresolved. The independent rendered DOM check compares the target's position, size, radius, color, alpha, border and effects to source-derived values before accepting the run mapping. It also requires editable, ordered source text and the existing run-level checks. A direct `source_alpha.py` result is `source-alpha-shape-conditional` until this DOM comparison succeeds. Source and candidate render hashes establish file identity only: visually inspect their provenance, occlusion, shape appearance and subsequent reveal. A changed exact HTML invalidates the review. Unknown gradients, system colors, group/placeholder transforms, timing/transition, complex effects and unknown inheritance remain unresolved except for the explicit narrow contracts below.

The same explicit shape review applies to an ungrouped, non-placeholder text box only when its source has no style, explicit `noFill`, and a strictly empty line element; other inheritance remains unresolved. The empty line's default is `noFill` under the [Office implementation note for line defaults](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oi29500/c0c046ec-a61d-405d-88fe-74d8487a37d7). Preserve empty source paragraphs as well as visible and transparent runs.

For a deliberately static frame after any transition, a reviewed run may additionally declare `"staticReview":{"reviewed":true,"mode":"static-frame-after-transition","systemColorPolicy":"lastClr","animationNotVerified":true,"reason":"specific source-frame review"}`. This is accepted only with the separate shape review above and the narrow video-only timing classifier; it rejects unknown timing trees, other object targets, unresolved dependencies and unsupported transitions. A resolved `sysClr` records its name and declared `lastClr` fallback explicitly: it is not proof of the live OS system color. The exact source and candidate frame still require inspection; the outcome remains at most `review`, and no transition, reveal, playback or trigger behavior is certified. For other timing or system-color cases the contract fails closed.

An explicitly reviewed `shapeReview.kind` of `source-gradient-svg-v1` supports only the source circle-gradient patterns resolved by `scripts/source_gradient_svg.py`. Place the source-derived SVG immediately before the editable text target as its sibling, with `data-source-shape-for` equal to that target's `data-source-id`, absolute source geometry and `pointer-events:none`. The source target itself remains transparent and keeps every run and marker; the SVG has no duplicate `data-source-id`. The DOM check compares source-derived SVG structure, shape bounds and computed paint, and rejects unsupported geometry, checked CSS overrides, timing combinations and ambiguous association. Independent audit is still needed for other CSS and dynamic changes. Native source and exact candidate frames remain manual review evidence; interior-pixel comparisons and this narrow path do not establish arbitrary gradients, animations or whole-slide parity.

For reviewed alpha runs, the DOM/source comparison keeps an ordered stream per paragraph. Each `<br>` corresponds to one source line break; a literal newline is accepted only with a whitespace mode that renders it as a line break (`pre`, `pre-wrap`, `pre-line` or `break-spaces`). Keep whitespace-only runs as exact text nodes; a reviewed whitespace run also needs its own plain marked span. Paragraphs must be explicit sibling `<p>` or `<li>` elements for multi-paragraph targets; a single paragraph may itself be the target. Hidden breaks, hidden or zero-font whitespace, missing/reordered text, ambiguous or duplicate markers, and merged paragraph boundaries remain failures. More complex paragraph nesting and browser-specific layout still require review or a supported representation. Shape, outline, style and effect checks remain mandatory.
