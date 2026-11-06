# Composition decisions and sample review

For PPTX, inspect actual rendered slides in presentation order after preflight. For a new deck from an outline, review the supplied outline in order and note proposed hierarchy and capacity before authoring. For each slide identify its purpose, main emphasis, reading order, meaningful groups and data, density and editability constraints. Describe what already works and what impairs reading. Compare each sequence of reveals together and state what changes between steps. Work from the requested boundary: exact preservation and mandatory templates take precedence. For «make this presentation tidy / ready to present», retain good compositions, adapt near-ready slides, redesign structurally weak ones. Preserve wording, values, relationships, slide order/count and logical editable paragraphs; flag unsupported geometry, masks, links, tables or media and agree consequential fallbacks before propagation.

Choose `preserve`, `adapt` or `redesign` for each slide. Adapt width, grid, scale or emphasis only when it resolves a concrete problem. For redesign, first inspect any supplied composition references in their assigned role, then the [24 accepted examples](reference-pack.md) and base style. Choose by purpose and actual text/data volume; cite the exact reference and why it fits. If none fits, record a custom approach and a candidate for the library. The sample's colors and text are never a palette or content source. Record evidence of actual capacity after rendering; choosing a reference is not a fit test. If the content cannot fit, choose another structure, not silent omissions or universal font reduction.

For a complex deck, select five diverse samples by observed risks, including one good source to preserve, one dense text slide to adapt/redesign, and the strongest remaining risks such as table, meaningful graphic, media or adjacent reveal steps. With fewer than five slides use those available. Produce these samples in the bundled shell and compare source / previous HTML when available / candidate; review desktop and narrow frames and record differences and residual risks. Verify source words, data, labels, links and editing; render each paragraph as one editable source target with inline runs. Use [text-layout](text-layout.md) for contextual proofreading, typography and rendered line QA, including static export state. Fix objective issues before sharing. In an ordinary complex request pause after the samples for direction; if autonomous work was explicitly authorized, perform the same review internally and continue. Do not present old captures as new.

## Record and check

Keep a `composition-plan.json` next to the project. Each slide in the intended build order needs one record:

```json
{"slides":[{"slideId":"s1","sourceId":"s1","decision":"adapt","purpose":"explain the choice","emphasis":"decision criterion","readingOrder":"title, thesis, three criteria","groups":"three labelled criteria","density":"moderate","editability":"paragraphs and links editable","works":"source hierarchy is clear","problem":"lead wraps awkwardly","capacity":"actual text checked at desktop and narrow; no overflow","technicalRisk":"none observed","sourceRender":"source/slide-01.png","reference":"ref-05 / argument"}]}
```

`sourceRender` points to an actual local source-page render, relative to this JSON or absolute; it is evidence of inspection, not a promise of identical fonts or fidelity. `reference` is required for `redesign` and can identify an external reference, Maker ref/version or a documented custom design. For a reveal series, put differences in `groups` or add a project note. Inspect every source slide before recording a PPTX decision. For an outline-only project, save the supplied plan as a local project file, set top-level `inputKind: "outline"`, and use `sourceOutline` in each row instead of `sourceRender`. Point each row to the plan and use `sourceId` to identify its corresponding slide or section. Review the newly rendered sample after building. Evidence records are authoring observations.

```sh
python3 scripts/composition_plan.py project/deck.json project/composition-plan.json
python3 scripts/build.py project/deck.json draft.html --theme project/theme.json
# Capture and inspect the draft; put the PNG/JPEG path, these hashes, and your
# specific visual observation in each slide's visualReview in composition-plan.json.
shasum -a 256 project/deck.json project/candidate/s1.png
python3 scripts/build.py project/deck.json result.html --theme project/theme.json --final --composition-plan project/composition-plan.json
```

For `--final`, first build a draft, capture and inspect each current candidate slide, and add `visualReview` to every ordered slide record: `{"reviewed":true,"observation":"specific inspection outcome","candidateRender":"candidate/s1.png","candidateRenderSha256":"<SHA-256>","projectSha256":"<SHA-256 of current deck.json>"}`. Paths are relative to the plan. Repeat the affected review after project changes. This is an explicit author attestation and a structural/hash check, not proof that the frame depicts the candidate or that the reviewer judged it correctly. Inspect the exact final HTML again, especially after changing theme, assets or build settings, which the project hash does not cover.

The explicit `--final` mode requires this visual-review record and a complete plan, and rejects unrendered block assembly for ordered slides. The existing default remains available for drafts and older projects. HTML/composition and a complete plan do not prove visual quality, content preservation, editability, shell QA or final acceptance. An authored fallback needs the agreed scope and per-slide disclosure. PDF production conversion, source-object reconstruction, animations/media triggers, calibration and export verification remain separate work; this check does not implement them.

Run the [required HTML delivery checks](delivery-check.md) on the candidate before delivery.

For concrete issue → minimal correction examples, the order of capacity remedies and preservation of current edits, read [targeted layout editing](layout-editing.md).

## Measured decision pass

For each reviewed slide use the actual intended window, source inventory and `check_text_layout.mjs --actual-fonts`; record the source ID, role, observed screen size/line breaks, available frame, existing strengths, concrete problem and `preserve`, `adapt` or `redesign`. At 1280×800 a useful **review profile**, not a universal deck rule, is body ≥14 screen px, table ≥13, labels ≥12 and footnotes ≥10. Assign exceptions to identified objects with a visual reason; do not mark an entire deck exempt. Fixed-stage scaling, mixed inline font sizes and substituted fonts can invalidate a simple CSS-size estimate. Read the resulting frame and inspect overflow and line-box overlap rather than treating the profile as automatic approval.

For a dense slide compare at least one feasible structure against the current one: first use the available width and group spacing, then adjust selected typography. Preserve factual wording, links, color roles, object identity and the user’s last saved edits. Record rejected alternatives and the measured reason when they expose clipping or collision. Review neighboring groups, not only the edited paragraphs. For source graphics, make a source-ID inventory including explicitly excluded IDs, describe each meaningful relation and verify the full declared contract with `check_graphic_contract.mjs` before declaring the change safe; its pass is relative to the reviewed inventory, never proof of the original PPTX topology.
