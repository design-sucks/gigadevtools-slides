# Conversion invariants and observed failures

## Text

Capture semantic paragraphs, not one text box per visual line. Retain measured soft line breaks in rich runs inside a frame. Avoid synthetic bold when the source font face already contains its weight. Preserve explicit paragraph spacing. SVG `<text>` stays an editable frame; text baked into source photos or outlined paths stays artwork.

PowerPoint PDF extraction can reorder text or omit text clipped by the canvas even when the glyphs visibly render. Use independent DOM inventory → per-frame OOXML checks for completeness and actual rendered pages for clipping. A PDF string diff alone is not evidence of loss.

## Fonts

The script extracts embedded data-URL font faces, converts full glyph sets through fonteditor-core, then prepares EOT and SFNT naming with font_pack.py. It assigns separate family aliases for each face and retains full Unicode coverage. Check fsType permissions before claiming editable embedding. Do not override source embedding restrictions. External font URLs and WOFF2/variable fonts may require additional preparation; report unresolved faces rather than silently substituting.

EOT name strings use UTF-16LE. SFNT name strings use UTF-16BE. Retain correct checksums, lengths and full glyph counts. Set embedTrueTypeFonts and disable subset saving. Embedding metadata plus glyph checks still require an actual app render.

## Geometry and backgrounds

Browser pixels map to 96 px per inch; type sizes map to 0.75 pt per px. Use transformed SVG paths converted to native custom geometry for flat paint. Keep object-level raster fallbacks for patterns, gradients and filters. Only a leading full-canvas paint prefix becomes a layout background. A large content rectangle later in the DOM is content, not automatically a background.

Deduplicate layouts by background bytes and native counter style/geometry. Keep counter placeholders and actual fields linked through idx. A correct group transform is `<a:chOff x="0" y="0"/>`; using `cy` in place of `y` caused PowerPoint repair despite well-formed XML. Also remove dangling Content_Types overrides produced by PptxGenJS and normalize duplicate a:pPr nodes.

The GIGA Brand design is 1920×1080. Its stage can measure 1920×1016 when a toolbar consumes 64 px. Export the intrinsic SVG viewBox, not that stage height. This rule also prevents composition shifts caused by preserving aspect ratio inside a wrong canvas.

SVG elements may have CSS backgrounds, borders and padding outside their inner paths. Capture container paint before walking the paths; skipping it removed the three icon tiles on Meetup slide 5.

## New decks

Inspect CSS pseudo-elements, clipping, transforms, stacking, text orientation, tables/charts, nested interactive states, dynamic canvases and link targets. The current capture handles the tested fixed layouts, not every CSS effect. Add representative acceptance fixtures for unsupported constructs before broad export. Preserve existing hyperlink relationships and add overlays only at observed link rectangles; do not invent links from visible text. If an HTML table/chart contains underlying data, use native data objects where requested; source screenshots cannot reveal data that is absent from the HTML.

## Review

Use actual PowerPoint PDF output for native evidence; choose the local print-optimized PDF option rather than a cloud conversion service. Render all pages at source dimensions. Compare each against the saved browser reference, checking detailed pages after contact sheets. Keep reference, output and benchmark adaptation labels distinct. Disclose untested platforms and raster fallbacks.

Use a fresh output directory for each version; stale page PDFs in a reused directory can contaminate merges. Keep private diagnostic packages out of delivery. Package only original engine code and required open-source attribution, not proprietary vendor benchmark helpers, user decks or fonts.


## Editable / CSS Grid regression

The 18-slide Editable deck uses CSS Grid, not the flex display previously guessed from SECTION. Preserve computed display and the 1920×1080 stage; hide its app bar and normalize #viewer. Use its showSlide API and disable reveal/motion for a stable complete state. The default tested state was light / warm; do not claim all 8 style/theme combinations were tested.

Zero-height containers can have visible absolutely positioned children. Recurse through them; do not drop descendants based on the parent rectangle. SVG stroked lines can also have zero geometric height/width. Retain them and include stroke thickness in any raster fallback bounds.

CSS generated content is not part of DOM text ranges. Simple quoted pseudo-content and scoped simple counter() values are materialized from computed styles for measurement. Existing static +/- semantic prefixes stay inside their paragraph. Save browser reference images before this adaptation so it cannot redefine source truth. Complex nested counters, transformed content and unsupported CSS need an explicit adapter and visual review. Disc markers are separate editable geometry with approximate browser placement; disclose small residual marker differences.

Image border boxes include padding. When painting an IMG object, preserve padding, transparent border widths, box-sizing and object-fit/object-position; dropping padding enlarged the Editable QR. Do not silently turn source-image text into editable text.

After layouts are promoted, deduplicate identical ppt/media bytes and rewrite package relationships. Verify every target after rewriting. Do not claim this makes groups or component instances. Keep original accepted deliveries unchanged when validating a new engine version.


## Source PDF screen-media gate

HTML may define its own @media print rules that reveal hidden slides, apply zoom and paginate a whole deck. Force Playwright screen media before per-slide PDF capture. Require exactly one PDF page per captured slide, then require the merged page count and aspect ratio to match the source slide inventory. Without this, Editable produced repeated multi-slide printouts despite correct PPTX/reference PNGs. A successful PPTX gate alone does not verify the separate source PDF.


## Native component groups, tested 2026-10-24

Use explicit DOM container membership and preserve full paragraph ownership. Native group transforms retain the original slide-coordinate system (off == chOff, ext == chExt), so leaf shape coordinates and text runs stay unchanged. Nest groups only for laminar, contiguous drawing ranges; reject crossing/interleaved members. Exclude native slide-number/layout placeholders. The postprocessor verifies leaf content/order and unique ids; the independent verifier checks group membership/transforms.

The Editable sample created 22 groups on slides 2, 5, 6, 14. Actual PowerPoint PDF comparison against the accepted flat v04 was pixel-identical on all 18 pages. A separate QA file was edited and saved in PowerPoint; all four test text objects remained in their groups, including one nested chart label. The deliverable is the clean grouped file. Do not mark unrelated profiles or Windows as verified from this test.


## v05 shared adapters and output modes

The AI PDLC adapter now retains hidden .slide-page counters as invisible native fields, embeds QBRDeck/QBR_VIDEO_ASSETS data-URI MP4s with source poster geometry, and assigns unique cNvPr IDs to videos before grouping. This avoids the media/shape-ID collision found in the eleven-slide run. Hidden-counter geometry currently follows the tested 1920x1080 QBR convention; adapt another canvas explicitly rather than treating this as universal counter inference. SVG path markers are emitted as editable transformed geometry for the tested viewBox/path marker form. Other marker child types and untested markerUnits/orient combinations need an adapter; do not assume all SVG markers are supported.

--format pptx is now the default and does not create a source PDF. --format pdf skips semantic scene construction and font embedding; --format both requests both. Browser PDF stays the default viewing format, raster PDF reuses source reference PNGs and carries external URL annotations. report.input.faces contains font metadata only, never base64. --inspect writes small inventory.json without scene or font conversion. Source PDF page gates are conditional on the requested output, while every native PPTX gate remains mandatory.

Video covers are captured while paused in their original DOM with browser controls temporarily hidden. This preserves ancestor clipping/CSS and avoids baking a rotating Chromium loading indicator or browser transport bar into the native PowerPoint video cover. The actual embedded MP4 is unchanged; PowerPoint supplies its own playback UI. Source/browser PDF can retain browser controls, so the cover region is an intentional comparison exception, not a claim of pixel identity.
