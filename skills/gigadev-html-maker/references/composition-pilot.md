# Pilot composition variants

These are authoring candidates based on accepted reference roles, not replacements for supplied source design. Choose the source composition when it is effective. Supply project data, colors and source IDs; no reference sample data is deliverable. Every new slide still requires measured capacity and visual review.

| Family | Renderer and variants | Slots and reading order | Use and limits |
|---|---|---|---|
| Table, ref-10 | `comparison` 1.0.0: `standard`, `wide-labels` | `title`, `columns`, `rows`; optional `lead`, `footer`, `tableSourceId`. Read header then rows. | 3–5 columns, 3–6 rows. Use `wide-labels` for long first-column criteria. Preserve units, values and numeric alignment. Merged cells and distinct per-cell geometry require authored HTML or another layout. |
| Status, ref-13 | `progress` 1.0.0: `standard`, `wide-first` | `title`, 2–3 `items`, each with a title and list of `label`/`status`; optional `lead` and `footer`. Read columns left to right. | Use for current independent workstreams. `wide-first` gives an uneven first stream more width. For chronology, dependencies or very long items use a different layout. |
| Scorecard, ref-18 | `scorecard` 1.0.0: `standard`, `side-by-side` | `title`, two `items` with value, title and explanatory items; optional lead/footer. Read each score and its reasons together. | Use for two comparable assessments and their explanations. Side-by-side favors short explanations; stacked offers more width for unequal text. State the scale and source; do not invent ratings. |

The data fields accept source-bound `{text, sourceId, runs}` where supported by the renderer. Test source binding in final DOM. Rendering in HTML is not evidence of native editable PPTX export. Compare rendered frames at target dimensions and check long and uneven content; character thresholds only help choose candidate spacing and do not prove fit. A project can always use custom authored HTML.

The six candidate variants and short, long and uneven fixtures are in `assets/compositions/pilot/deck.json`, with full-size previews in `assets/compositions/pilot/previews/`. These are sample-only test artifacts, not production content. Visual approval, native PPTX export and final style review remain separate gates. Reference pack revision is 2.0.0; no external code was copied for this pilot.
