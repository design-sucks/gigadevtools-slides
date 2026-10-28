# Legacy composition renderer 1.0.0

For new design work use the accepted [24-reference pack](reference-pack.md). This simplified renderer remains for existing pinned projects; it is not a rendering implementation of the accepted v06 references.

18 clean, editable HTML patterns rebuilt from reviewed presentation compositions. They supply hierarchy, geometry and content roles, not source facts, logos, screenshots or a mandatory brand palette. The library is a first vocabulary, not a universal design generator or a pixel copy of every reference slide.

## Choose before authoring

1. Resolve preserve / improve / change mode. Preserve-design follows the source; do not force it into this library. A mandatory template outranks these defaults.
2. Inventory exact text, data, links and graphic instances. Read source-style.md. Map source colors/fonts/images to semantic project tokens first; library defaults fill missing evidence only.
3. List each slide's purpose, evidence type and volume. Read only the catalog summary, then 1–3 matching JSON examples and previews. Never load all source HTML, fonts/base64, examples or screenshots into LLM context.
4. Choose by reading task: claim→thesis-evidence; comparable criteria→comparison; participants→role-process; system layers→architecture; exact values→metrics/trend; plan→roadmap; image evidence→demo/gallery. Containers are useful only when grouping meaning. Vary hierarchy across the deck; do not alternate random layouts or make every slide three cards.
5. Fill all content slots from stable source records. Preserve source IDs/runs/links and every retained graphic. Put full-slide paint in slide.background; content images stay in media slots. The comparison column is highlighted only with explicit highlightColumn and a reason; factual model columns are not automatically ranked. Optional index labels must not compete with page numbers.
6. Read required/optional fields, collection ranges and character envelopes. These are approximate capacity guards, not a text-fit guarantee. Use actual font-loaded renders. If content exceeds capacity, choose another pattern or author slide HTML. Do not drop words, shrink all body text, hide overflow or split slides without authorization.
7. Review cover/data/dense samples before propagation when the request requires a checkpoint. Then render every slide and check completeness, links, contrast, whitespace, media, overflow and themes separately. A passing geometry checker does not grade design.

## Use

```sh
python3 scripts/build_composition_demo.py /absolute/new-library-demo
python3 scripts/build_composition_demo.py /absolute/new-heading-fixture --variant headings
python3 scripts/build_composition_demo.py /absolute/new-uneven-fixture --variant uneven
python3 scripts/compositions.py list --intent compare
python3 scripts/compositions.py render comparison content.json fragment.html --version 1.0.0
```

Prefer structured slide.composition in deck.json over pasting an example. It automatically includes scoped composition CSS. Copy only chosen example media into the project. Replace every instructional placeholder; examples carry sampleOnly:true and are rejected in ordinary deliveries. The dedicated library-demo purpose is only for presenting the library itself.

Text can be a string or {text, sourceId, runs, href}. Each source-bound text element has one unique ID. Runs support text/bold/italic/link. Paragraph arrays are supported for card bodies and footer; text remains ordinary editable HTML. Card icons support icon, iconAlt, iconSourceId and an optional #RRGGBB accent. Supplied source IDs/graphics that a pattern cannot render are rejected; use another pattern or explicit authored HTML. Extraction blocks remain in the project for completeness checks; they do not render twice.

Assets/compositions/catalog.json is the machine-readable index. Each record points to its example, rendered fragment and preview, rhetorical uses, source geometry references and capacity. Theme tokens: --gd-bg/ink/muted/accent/line/font/display-font; optional --cp-heading-font. Existing shell/UI tokens are independent. New themes/fonts require their own visual QA; the included neutral dark/light examples are not universal contrast certification.

## Update a pattern

Keep stable IDs. Patch a slot/CSS rule in scripts/compositions.py and assets/compositions/compositions.css, bump the affected record's version, regenerate its fragment and preview, and record why in CHANGELOG.md. Keep prior published revisions in Git tags; never silently reinterpret a pinned version. Add an ID only for a different reading/composition task, not a recolored duplicate. Old projects with pinned versions should be migrated explicitly; this renderer rejects mismatches rather than silently changing layout.

Run scripts/test_compositions.py and build the demo. Run node scripts/check_compositions.mjs DEMO.html NEW_QA_DIR; inspect actual dark/light renders. Recheck short, long Russian headings and uneven bodies on affected patterns. Keep a real-content probe with a table, links and graphics. Re-run scripts/build_demo.py --check at repository level to verify the accepted shell demo is unchanged. A new PPTX delivery additionally needs native PowerPoint acceptance via HTML Export; this library release is HTML/PDF verified, not a new PPTX qualification.

See assets/compositions/PROVENANCE.md for selection/dedup scope. Keep private source inventories/screenshots outside distributed assets.
