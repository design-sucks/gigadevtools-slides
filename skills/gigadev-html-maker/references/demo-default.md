# Experimental default: bundled shell demo (v1)

When authoring a new or improved composition **without a supplied composition reference**, start from the bundled shell demo. This is an authoring default, not a renderer that fills template slots. Review the input's purpose, complete content and actual volume, then adapt a suitable demo structure. Do not simply keep weak source coordinates and label them demo-inspired.

## Priority and scope

1. Follow an explicit preserve-design request, mandatory template or no-reference request. Retain an already effective source composition when no redesign is needed.
2. Use a user-supplied design/composition reference in its assigned role. A palette-only reference controls paint; it does not replace the default composition reference.
3. Otherwise use this demo default. Source or supplied style still determines colors, fonts, images and category meanings. With no style evidence, use the skill's neutral base style. Do not impose demo green, Extended on every heading, tutorial copy, keyboard controls, logos, extra theme variants or sample data.
4. If the task or full content exceeds the demo's vocabulary, consult the [24-reference pack](reference-pack.md) for the missing structure, or author a reasoned custom layout. Do not fit complex charts/diagrams into unrelated cards, delete content, or globally shrink type to match a preview.

## Choose only relevant slides

Catalog and local previews: `assets/shell-demo-reference/catalog.json`. Original editable HTML: `assets/example-deck.json`, with scoped slide CSS in `assets/example-theme.json`. These are the same bundled sources used by the public shell demo. Inspect only 1–3 applicable previews and corresponding HTML/CSS, not the entire corpus.

| Reading task | Demo slide IDs | Apply |
|---|---|---|
| Cover / main promise | `cover` | Dominant title, restrained lead, supporting detail separated below. |
| Three comparable groups / principles | `view`, `principles` | Common column grid, aligned hierarchy, open space between groups; boxes only when meaningful. |
| Comparison / exact table values | `save` | Quiet native table, consistent row rhythm, readable labels and subordinate note. |
| Ordered steps / checklist | `source` | Clear sequence and stable heading/body alignment; retain actual item count. |
| Simple process / format relationships | `formats` | Distinguish stages and outputs; preserve actual source edges and labels. This is not a general graph engine. |

Use the demo's larger type hierarchy, shared outer alignment, purposeful whitespace and consistent group spacing as a starting point. Adapt widths and line endings to actual text; verify the resulting reading groups at the intended window size. Derive only the CSS rules used by the selected structure and scope them to the project slide class. Ordinary content remains in the Maker safe area; full-page decorative paint and source chrome follow [presentation roles](presentation-roles.md). Never paste the demo viewer, slide counters or navigation into body content.

To inspect selected editable fragments cheaply:

```sh
python3 - <<'PY'
import json
from pathlib import Path
# Run from the installed skill folder; choose IDs from the catalog.
selected = {'cover', 'save'}
deck = json.loads(Path('assets/example-deck.json').read_text())
for slide in deck['slides']:
    if slide['id'] in selected:
        print(slide['id'], slide['html'])
PY
```

Record the actual choice in the composition plan, e.g. `reference: "shell-demo-default/v1#view"`, and state what changed for the real content. For a preserved source or explicit no-reference request, record that reason instead. A selected reference is not visual acceptance: keep the normal source, line-layout, graphics and final HTML checks. Existing presentations are not automatically restyled by installing this pilot.
