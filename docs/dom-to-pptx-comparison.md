# HTML Export and dom-to-pptx

Reviewed 2026-10-28 against dom-to-pptx 2.1.2. This is a documentation/source comparison, not a head-to-head rendering, performance or cost benchmark. No universal fidelity winner has been established.

Both engines measure a browser DOM and use PptxGenJS plus OOXML work. Editable text and embedded fonts are not unique to GigaDevTools. [dom-to-pptx source](https://github.com/atharva9167j/dom-to-pptx/blob/master/src/index.js) contains rich-text handling, native addTable, font auto-detection, weight-slot collision warnings and font-embedding error reporting. Its current font path catches individual embedding errors and reports them; this differs from a strict delivery gate that rejects incomplete required coverage.

| Concern | GigaDevTools HTML Export | dom-to-pptx |
|---|---|---|
| Primary fit | Offline presentation pipeline with measured semantic paragraphs and corpus-specific adapters | Browser library/CLI for exporting selected DOM elements |
| Editable text | Browser-measured line breaks and paragraph spacing; source text and font coverage checks | Native text/rich text; actual wrapping fidelity needs the same-deck test |
| Font portability | Full permitted faces, Unicode/packaging verification, explicit failure/warning boundary | Auto/manual font discovery and embedding; also supports embedding alongside a PPTX template |
| Tables | Current generic path emits editable text/shapes, not native PowerPoint tables | Explicit native addTable path; a meaningful capability advantage for table editing |
| Backgrounds/templates | Promotes reusable captured backgrounds/layouts; no general corporate-template importer | Can inherit chosen layouts from an existing PPTX package |
| Motion | Freezes HTML into reviewed static slide states; video has specific adapter support | Declared native entrance/exit animations and slide transitions |
| Integration | Separate viewing PDF / editable PPTX; preparation contract, selected order, native counters, font/paint cache, grouping profiles and native-QA workflow | Client-side export button and headless CLI; more convenient for application embedding |
| Quality assurance | Source completeness, structural/font/layout/group checks and all-page native PowerPoint comparison | Library capabilities and tests do not by themselves establish equivalent acceptance of a specific deck; not experimentally assessed here |

The animation and browser-button capabilities are documented in the [project README](https://github.com/atharva9167j/dom-to-pptx). We have not run them in this comparison. Its [template design](https://github.com/atharva9167j/dom-to-pptx/blob/master/docs/template-support.md) preserves template masters/layouts and attaches generated slides to selected layouts. It explicitly excludes placeholder filling and automatic layout selection. This is stronger template inheritance than our current generated-background promotion, while remaining distinct from automatic slide design.

Our practical advantage is the maintained preparation/validation workflow around the renderer, especially for known deck families. It is not evidence that our DOM renderer is generally better. Our current limitations include generic tables as shapes, profile-dependent grouping and untested CSS/input families. Poorly authored HTML is reproduced by either approach; a different converter cannot fix wrong background roles or weak composition by itself.

Before replacing or adding a backend, run the same small corpus through both: paragraph-rich text, mixed styles, full background, table, SVG, overlapping paint and unavailable fonts. Match dimensions/fonts/theme/selected slides; inspect actual PowerPoint renders and editing behavior. Measure engine time separately from model authoring and debugging. Keep an optional backend only if it wins a concrete case without weakening the delivery checks.
