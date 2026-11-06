# RC12 — targeted corrections after the three mini-PPTX trial

Compared with RC11:

- List extraction accounts for ordinary shape/presentation defPPr defaults. A complete supported ordinary level-zero shape with an exhausted marker chain gets an explicitly inferred terminal no-bullet result. Explicit markers retain priority. Placeholder/table/nonzero-level and ambiguous or incomplete contexts remain unresolved. In the three real mini sources the previous108object observations (77/30/21paragraphs) disappear while nine actual AI bullet paragraphs remain protected.
- The source-style literal gate recognizes supported inline CSS, shorthand/full hex, rgb/rgba, gradient paint values and inline SVG paint attributes. Comments, script/text, URLs and source records are excluded. A literal paint pass does not establish cascade, effective visibility or per-object fidelity.
- A decorative image background can declare background.wash with a supported linear/radial gradient. The builder paints it on the moving full-viewport background layer and preserves it through save/reopen and1920×1080export. It requires no author CSS aimed at the shell; do not duplicate the wash in the content frame. See project.md.

The real AI14 external-line correction is ordinary source-derived authoring, not a general SVG/PPTX renderer added to this package. Source data, private QA/fix helpers and test-deck media are not bundled. Fresh final qualification of the three compact decks remains separate from these bounded code checks. RC11 reference notes retain the earlier component scope and limits.
