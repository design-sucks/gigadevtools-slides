# Source style and graphic decisions

For PPTX input, extraction writes `style-inventory.json` alongside deck.json. Read `colorSummary`, themes/fonts and the graphics list first; use the referenced evidence IDs only when needed. Avoid dumping the detailed colors array. Evidence carries part/slide/object/property and base-color resolution, not certified PowerPoint pixels. Actual use on slides matters more than an unused theme accent.

For preserve-design/improve-layout, inherit source backgrounds, ink and accents where viable, then adapt hierarchy/composition. Multiple meaningful accents (for example model categories) should keep their roles; passing one chromatic-color check is not enough to claim fidelity. The neutral kit fills gaps. Keep the viewer UI palette separate from the slide palette. Declare font substitution independently; authorized SB Sans can be a requested typography choice while the source palette and imagery remain.

Preserve/rework each icon or illustration according to its role. Full-canvas background candidates are handled independently. Do not classify every SVG as dispensable decoration. A replacement states what visual/semantic role it keeps; omissions need specific reasons. A supplied logo or meaningful illustration is not generic filler.

Before delivery write `visual-decisions.json`:

```json
{
  "mode": "improve-layout",
  "palette": [
    {
      "role": "text",
      "sourceEvidence": "e-ID-FROM-INVENTORY",
      "decision": "retained",
      "target": "--brand-accent",
      "targetColor": "#0055AA",
      "reason": "Use the source accent for the same category heading"
    }
  ],
  "graphics": [
    {
      "sourceId": "s1-o3",
      "disposition": "retained",
      "target": "s1-o3",
      "reason": "Source diagram retained with a larger readable placement"
    }
  ]
}
```

The snippets are illustrative, not defaults. Use real evidence/IDs/colors from this input. Palette decisions are `retained|adjusted|replaced`; adjusted/replaced require a reason, and targetColor must match an actual authored CSS declaration or used token. Map every detected role text/fill/line/background with resolved evidence; keep the important individual accents, not only one representative. A retained color equals the resolved base, whose transforms/inheritance remain a review limitation. Graphics dispositions are `retained|reworked|replaced|omitted`; each extracted instance needs one entry and a reason, with a target in authored markup for non-omitted entries. For omitted, target is empty.

```sh
python3 scripts/source_style.py /absolute/Project /absolute/Project/visual-decisions.json --html /absolute/Presentation.html --theme /absolute/Project/theme.json --report /absolute/QA/source-style-gate.json
```

The gate rejects unknown/missing decisions, unused/mismatched palette targets, a white-only mapping when chromatic source colors exist, and discard of all non-background graphics in preserve/improve mode even if a cover is retained. It warns when the majority are replaced/omitted. For an explicitly requested change of style, `mode:change-style` plus `changeStyleAuthorization` records the actual user instruction; do not invent that authorization to silence a failure.

This is an evidence/coverage guard, not a visual-quality score: a hidden target or weak composition can still pass. Inspect actual cover/data/dense slides, color roles, visible artwork and all-slide bounds. Master/layout inheritance, color maps and modifiers are not fully rendered by the analyzer. A source without useful explicit evidence needs source renders/manual review, not invented confidence. Shape-only drawings are not all captured as image instances; inspect extraction's geometry/unsupported objects separately.
