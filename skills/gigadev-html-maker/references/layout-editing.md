# Targeted layout editing

Start from the latest saved work, not an older JSON. Compare baseline, current project and saved HTML using [journal](journal.md); resolve conflicts and preserve untouched order, metadata, inline runs and user changes. Identify the affected slide and source IDs, inspect the source and a full-size render, then record purpose, focal point, reading order, good source decisions, concrete problem and intervention in the composition plan. Choose `preserve`, `adapt` or `redesign`; do not silently merge or split slides.

| Observation | Targeted intervention | Why |
|---|---|---|
| A long headline ends in an isolated word | Widen its frame or adjust its meaningful break; remeasure | Preserves wording and one editable heading. |
| One column contains much more text than its neighbor | Assign it more grid width or choose a stacked layout | Content, rather than equal boxes, determines space. |
| A conclusion overlaps a footnote | Give each a distinct row and check their line boxes | Preserves both source items and their reading order. |
| The table has long labels and short numbers | Widen the label column, align numeric cells and retain units | Improves scanning without changing values or column associations. |
| A label is detached from a diagram node | Use shared SVG/HTML coordinates; annotate node and expected label offset | The label follows its object at each scale. |
| A connector crosses a label | Move the label or route the connector, then recheck endpoints and collision | Preserves diagram topology and avoids illegible crossings. |
| A logo is stretched or a screenshot loses important edges | Use intrinsic proportions and `contain`; check the crop against source | Maintains recognizable marks and meaningful content. |
| Several elements compete for attention | Assign one primary focal point and reduce competing size or contrast | The slide's intended reading order becomes clear without deleting content. |

When space is tight, first test frame width, neighbor spacing and grouping, then compare a different grid or a suitable reference variant. Adjust type only within the intended viewing profile; inspect actual fonts and rendered line breaks. Ask before changing wording, removing information or splitting a slide unless that change was already authorized. Two composition candidates are useful for an ambiguous structure or a confirmed capacity problem, not for routine alignment.

For a local geometry edit preserve source and current text, record the affected IDs and before/after geometry in the journal, render the slide and neighboring slides, and rerun source/structure, text and relevant graphic checks. The current layout journal is read-only history, not interactive geometry undo. Keep unresolved inherited source styles, unsupported diagram geometry, fallback graphics and user-dependent choices explicit. A bounded measurement pass does not replace full-frame visual judgment or a PowerPoint-native test.

## Guarded authored geometry

For an authored slide with direct positioned siblings, `bounded_geometry.py` reconciles the latest saved HTML first, then applies one shared translation and optional explicit pixel widths. It writes a new project beside the original, never overwrites it, and emits a JSON record to stdout. Inputs must be immutable for the operation. Record the exact SHA-256 of the project, its baseline HTML, and latest saved HTML in the operation file; the baseline must be the build of that project before the user's saved edits. This provenance is the caller's responsibility: hashes detect later changes, not an incorrectly paired baseline. Resolve any reconciliation conflict before proceeding.

```sh
node scripts/check_text_layout.mjs /absolute/latest.html --viewport=1280x800 --actual-fonts --inventory=/absolute/deck.json > /absolute/text-measurements.json
python3 scripts/font_readiness.py /absolute/text-measurements.json --source-id s7-o8 --resource-manifest assets/fonts/manifest.json > /absolute/font-readiness.json
python3 scripts/bounded_geometry.py /absolute/project/deck.json /absolute/baseline.html /absolute/saved.html /absolute/operation.json /absolute/project/edited.json > /absolute/geometry-log.json
python3 scripts/build.py /absolute/project/edited.json /absolute/rebuilt.html
```

Example operation (replace all hashes, IDs and numbers with measured values):

```json
{"projectSha256":"PROJECT_SHA256","baselineSha256":"BASELINE_SHA256","savedSha256":"SAVED_SHA256","slide":"s7","problem":"Widen the text frame after measuring the isolated line","targets":["s7-o8"],"dx":0,"dy":0,"widths":{"s7-o8":390.9},"relations":[]}
```

`targets` are unique `data-source-id` values on direct siblings under the same authored parent. For a linked diagram, include every affected node, label and connector in `targets` and record each relevant pair in `relations`, e.g. `[["node","label"],["node","connector"]]`; the log records each pair's offsets before and after. The tool does not discover relationships, validate topology or infer whether every connector was included. It supports translation in parent CSS pixels, plus a width for an unlinked target; it refuses resize of a linked target, nesting, missing/duplicate IDs, transforms, non-pixel positions and other unsupported requests. It also checks the saved document's computed target and ancestor transforms, individual scale/rotate/translate, zoom and containing block in Chromium, including class-based rules. This is a snapshot, not a guarantee about other browser states or later CSS changes. SVG inside a selected rigid wrapper is translated intact, not edited or scaled. Do not use it on arbitrary SVG/PPTX geometry or as interactive undo. Verify content and actual browser geometry and inspect full-size before/after frames; a recorded offset alone is not a visual acceptance.

## A measured multi-target adaptation

`apply_layout_plan.py PROJECT BASELINE SAVED PLAN NEW_PROJECT` extends the guarded workflow for independently positioned siblings: each source-ID target may set explicit `left`, `top`, `width`, `height` and/or a uniform `fontSize` for its authored paragraphs, all in CSS px. The original baseline must be the build of that project; its provenance must be established by the caller. The helper hashes all three inputs, reconciles saved UI edits, checks the current Chromium coordinate context, refuses ambiguous IDs, unsupported values and nested source targets, and creates a new output atomically. It does not choose a layout, detect every text collision or validate a graphic automatically. Use the measured decision pass and render the resulting build.

The plan is a JSON object with `projectSha256`, `baselineSha256`, `savedSha256`, `slide`, `problem`, `decision` (`adapt` or `redesign`) and `targets`, for example `{"s7-o8":{"width":430,"fontSize":27}}`. For a specific source shape, `{"sourceRadial":true}` restores a centered two-stop circular gradient only for the supported source OOXML and matching authored colors/alpha. A `bg1` stop also permits `{"sourceRadial":{"bg1":"FFFFFF"}}` with a caller-resolved source color; verify its master color-map and theme provenance separately. A source `pie` requires an explicit `{"sourceRadial":{"domain":"authored-clip-bounds"}}` and derives the focal point and farthest-corner radius from the authored polygon's own bounds; this assumes those bounds match the source and must be checked against the source render. Only near-circular source extents, centered fill rectangles, two supported stops and validated existing colors are accepted. Unsupported themes, modifiers, geometry or authored forms fail. These are narrow visual approximations, not a general OOXML gradient renderer; compare the actual source frame and document soft-edge differences.

For graphics, `node scripts/check_graphic_contract.mjs BASELINE.html CANDIDATE.html CONTRACT.json` requires a reviewed list of every source ID on the slide, excluded IDs with reasons, selected members, independently stated `requiredLinks` and supplied `links`. A missing link/member, a changed relation offset or an unapproved graphic paint/path/size change fails. An explicit expected paint can be allowed with provenance. Mark resized text boxes with `allowResize`; the checker uses their horizontal centers and top edges for relative positions. The result is only relative to the reviewed baseline and declared inventory: it cannot discover a source object omitted from both baseline and inventory, infer semantic links, prove path crossings absent, or verify unrendered states. Review source render, topology, fills, crop, scale and frame visually, and keep uncertain links as review. Run this check after rebuilding; do not call an operation safe solely because the geometry helper returned success.
