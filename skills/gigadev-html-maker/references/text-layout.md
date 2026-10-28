# Text layout: review, not an automatic guarantee

The current engine does not automatically optimize paragraph density, line endings or visual rhythm. Its source/bounds tests detect missing content and some overflow; a long monotonous line, an isolated final word or a cramped group can still pass. The 24-reference pack helps choose structure but does not certify a generated design.

For each actual rendered slide, review these decisions:

- Give each reading group one clear entry point and keep related text together. Check the combined density of title, lead, labels, cards and footnotes, not only whether each box fits. Different content volume needs different composition; do not force everything into equal cards.
- Constrain prose width according to the actual font and content. Avoid page-wide sentences where a narrower paragraph or a paired structure reads better. Conversely, do not make a short paragraph an unnecessarily tall narrow strip.
- Inspect title breaks by meaning, isolated last words and short stranded endings. Adjust the text frame or layout before reducing type. Explicit visual line breaks can preserve wording; retain editable paragraphs and source IDs. Never split every line into a separate editing object.
- Keep short prepositions with their following word where this improves a specific Russian line. Do not run a broad replacement over URLs, identifiers, model names, code or factual numbers. Layout whitespace changes and real editorial changes need different records.
- Browser text-wrap:balance/pretty can assist HTML composition, but are not portable PowerPoint guarantees. Inspect the frozen export state and actual PowerPoint wraps; embedded fonts alone do not make layout engines identical.
- When exact content cannot fit with readable hierarchy, change composition and re-render. Condensing, deleting, splitting/merging slides or adding claims needs the user's request. Do not silently shorten copy or shrink all text.

Use cover, prose, dense table and mixed-graphic slides as representative reviews, then inspect every slide. Record unresolved visible problems honestly. New deterministic typography lint/optimization needs a varied corpus and quality criteria; this release adds no claim that such automation is complete.
