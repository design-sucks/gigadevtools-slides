# Source content, paint and navigation (RC18)

Classify these three roles from the source render **before authoring a slide**. Keep extracted source blocks unchanged. A decorative page image and its washes belong in `background`, not a 1920×1080 wrapper inside `.gd-content`. Source kickers and page counters belong to shell metadata; meaningful headings, body values, tables and links remain editable content. Never hide all headings or all integers using CSS. Short top-edge source text is ambiguous until reviewed, not permission to delete it.

## Decorative background

```json
"background": {
  "type":"image", "asset":"assets/cover.png", "sourceId":"s1-o10",
  "role":"decoration", "size":"cover", "focal":"50% 50%",
  "layers":[
    {"sourceId":"s1-o2", "type":"gradient", "value":"linear-gradient(90deg, #081124 0%, rgba(8,17,36,0) 100%)"}
  ]
}
```

The builder removes only the exact source-bound paint node from authored body markup and puts the source identity on `.gd-slide-background` or its child layer. Layers support color/gradient and an optional bounded `[left,top,width,height]` percentage `box`. Paint follows the full reading viewport, behind the transparent left rail, and shares `.slide-inner` motion. Show/export restore the 1920×1080 canvas. Keep ordinary illustrations, charts and logos inside content. A full-page screenshot containing important baked-in text is **not** decorative: preserve the existing reviewed `content-frame` fallback or reconstruct it, never blindly cover-crop it. Layers do not apply to `content-frame`.

## Reviewed source chrome

```json
"header":"full",
"title":"Actual content heading",
"navigationTopic":"Useful context distinct from that heading",
"sourceChrome":[
  {"sourceId":"s1-o4","role":"navigation","originalText":"01 / Раздел","reviewed":true,"reason":"Small source kicker; useful context is represented in the top shell header."},
  {"sourceId":"s1-o5","role":"page-number","originalText":"01","reviewed":true,"reason":"Source footer; replaced by current selected-order counter."}
]
```

At most one source object per role is supported. For additional repeated objects, resolve the source structure explicitly rather than using an unbounded omission list. Set `title` to the **real main heading**, not a source kicker. Existing section-divider propagation and duplicate-heading suppression remain in effect. The canonical top header keeps regular weight (400), 16px crumb gaps and its established geometry; do not hand-draw another header/footer. Reading hides this slide chrome because the shell already supplies left navigation and counters. Presentation mode shows the canonical top header and number; export uses canonical static metadata. Original source labels are retained in project and saved metadata even when the displayed topic is shortened or deduplicated. Page numbers follow selected order, not source page numbers.

The builder checks unchanged source text, review reason and known header/footer geometry. It refuses links, lists, h1/h2 body targets and nested source targets as removable chrome. If the source main heading is correctly in the top-edge candidate region, keep it and record `sourceChromeDecisions[id] = {"role":"content","reviewed":true,"reason":"Actual main heading, not navigation."}`. If a source full-canvas image genuinely is an illustration, use the equivalent `sourceImageRoles[id]` decision with `role:"illustration"`. These are per-object reviewed decisions, not deck-wide bypasses.

`--final` rejects unresolved full-canvas source images inside content, ambiguous short top-edge text, and obvious source page counters. Detection uses known extracted geometry/flags; grouped or unknown geometry and text painted into images still require visual review. A draft remains backward-compatible. No classifier can determine all authorial intent automatically.

## Verification

```sh
python3 scripts/test_presentation_roles.py
python3 scripts/presentation_roles.py independent/deck.json project/deck.json
node scripts/check_source_dom.mjs Final.html independent/deck.json project/deck.json --source input.pptx
node scripts/check_delivery.mjs Final.html project/deck.json
node scripts/test_presentation_roles.mjs Final.html NEW_QA_DIR
```

Independent source checks report `source-chrome-reviewed`, not missing content or unqualified semantic approval. Delivery validates declarations and actual canonical markers instead of blindly exempting source IDs. Inspect cover at a wide and tall viewport, behind navigation, during partial scroll and in show/export. Verify body headings/data and an ordinary illustration still appear. Reorder, save and reopen: chrome stays absent from reading and counters follow new order.
