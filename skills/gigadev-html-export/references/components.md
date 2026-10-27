# Native groups and the design-library extension

Native grouping is implemented for explicit component profiles. The tested Editable sample creates 22 p:grpSp groups on slides 2, 5, 6 and 14: 16 top-level components and 6 nested matrix/chart groups. All 18 actual PowerPoint Mac PDF page renders matched the accepted pre-grouping v04 pixel-for-pixel. Four native text edits were saved successfully without ungrouping; one was inside Tool Card 3 → Usage Chart 3. Windows has not been verified.

## Run with a source component profile

Append this to the normal export command:

```sh
--groups /path/gigadev-html-export/profiles/gigadev-editable-sample.json
```

The portable JSON contract is version 1 with a rules array. Each rule has `slides` (one-based numbers), `selector` (CSS relative to each slide root), `name` (English base name), and `expected` (number of matching instances per selected slide). Matching elements must be structural component containers, not arbitrary inline fragments. For multiple instances, names get 1…N suffixes. The exporter records memberships from the actual source ancestry; it does not group by visual proximity. Text membership uses the full semantic paragraph owner, so a partial span cannot take ownership of a whole paragraph.

For an already accepted export, reuse its scene.json only after validating object names/content and the source version. Add verified `groups` entries to each applicable scene (`id`, `name`, `selector`, `members` as exact emitted object names), then write a new file:

```sh
python scripts/group_shapes.py --input ACCEPTED.pptx --scene GROUPED_SCENE.json --output NEW_GROUPED.pptx
```

Keep the accepted input intact. Grouping changes only the selected slide XML parts; images, fonts, layouts, numbers and relationships remain unchanged. The postprocessor checks leaf drawing XML and order before/after wrapping. It uses identity transforms with off == chOff and ext == chExt in the original coordinate system, and unique shape ids. It preserves native text runs, geometry and pictures rather than rasterizing them. Inner groups are built before outer groups.

Run `python scripts/group_shapes.py --self-test` for nested/unsafe-order checks. The normal verify.py also validates the requested group membership and identity transforms. Missing selectors, wrong counts, nonexistent slides, one-object groups, crossing memberships, interleaved paint order and placeholders fail explicitly. Rotated drawing bounds require an adapter. Existing flat exports remain flat unless a group profile is requested.

## Native review

Open one QA copy in PowerPoint, export its unedited PDF locally and compare all pages with the accepted proof. Then select a child text object through the Selection Pane, press Return to edit, replace text and save. Confirm in the saved PPTX that the text still sits under the expected group chain and that groups remain present. Use a separate copy for these mutations, and close it afterward. A p:txBody tag alone is not proof of usable in-app editing.

The sample supports a card plus a nested dot matrix, card plus nested chart, multi-part competency shapes, and loop role/validation/governance cards. Cross-node connectors remain outside card groups. Groups containing hundreds of editable dots still contain those dots; grouping improves selection/movement, not object count or live component linking.

## Further design-library work

Media byte deduplication, native groups and shared layout backgrounds are implemented. Linked component instances, universal PDF/PPTX input, automatic restyling and design-library inference remain proposals.

When asked to design this extension, prefer explicit source DOM containers, existing PPTX groups or an approved template over proximity guesses. Preserve source ids, children, paint order, bounds, content slots, asset hashes, variants, style references and confidence. A candidate group must not reorder interleaved objects or absorb unrelated overlays. Keep cross-node connectors outside each node group. Keep content on the slide when ordinary editing matters; stable backgrounds/numbers belong in layouts. Native PowerPoint groups have a shared transform, not live linked-instance behavior. Reusing a definition in our intermediate model does not imply that editing one PPTX instance updates all others.

The Editable source already supplies GIGA_MODEL with 299 token descriptors, 79 asset metadata entries, 18 slides, 4 styles × 2 themes, and 4 font faces. Its 492 embedded resource records are a different catalog and not 492 components. Treat extracted style as observed source evidence, not an approved brand guideline. Filter editor-only and unused styles before publishing a design library. Repeated containers include 3 metric cards, 6 skill cards, 3 platform columns, 3 usage charts and 10 mini pie charts.

A practical future representation separates tokens/typography/assets/components/layouts, content values/paragraphs/chart data/links, and slide instances with exact geometry and overrides. Use DTCG-compatible typed tokens where conversion is actually valid; retain original CSS expressions as extensions, not falsely valid token values. Component definitions and slide content need their own small schema. Keep faithful conversion separate from reflow/restyling.

HTML can supply DOM/CSS/model semantics; PPTX can supply themes/layouts/groups/chart data; PDF often loses those semantics and scans require OCR. Shared representation cannot recover information absent from the source. For new import modes, distinguish direct extraction, inferred structure and image fallback, and validate a representative sample before propagation.

Sources: https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.presentation.groupshape?view=openxml-3.0.1 ; https://www.designtokens.org/tr/2025.10/format/
