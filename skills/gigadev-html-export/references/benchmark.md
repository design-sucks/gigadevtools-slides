# Measured comparison, 2026-10-23

The tested comparator is the unmodified historical Anthropic html2pptx.js at commit 00756142ab04c82a447693cf373c4e0c554d1005, not an independent Claude model run or a test of the entire current PPTX skill. See official sources:
- https://github.com/anthropics/skills/blob/main/skills/pptx/SKILL.md
- https://github.com/anthropics/skills/blob/00756142ab04c82a447693cf373c4e0c554d1005/skills/pptx/html2pptx.md

29 source slides were imported successfully by both exporters and rendered in PowerPoint for Mac. Both used the same measured source scene, prepared graphics and full font embedding. The historical helper received adapted contract-compliant HTML. Font family names containing digits must be quoted in CSS. Unsupported image opacity must be baked into PNG before importing; do not call adapter mistakes vendor limitations.

Final native output: 229 nonempty text frames on both sides; our 29 native slide-number fields versus 0 in the baseline; 16 layout backgrounds versus per-slide backgrounds. Our Meetup retained 53 shapes/paths versus 41, with 6 pictures versus 18. Brand had 45 native shapes and 60 pictures on both sides. Both passed per-frame text completeness checks.

RGB mean absolute pixel differences (0–255; lower means less deviation, not a quality percentage): Brand ours 1.6799, comparator 2.1007; Meetup ours 2.2996, comparator 4.7799. Differences include native numbering without decorative leading zeroes. Inspect individual pages: baseline Brand 1 and Meetup 1, 5, 12, 14 show extra wrapping. Many Brand collages are close in both outputs.

The current Anthropic skill is useful for general authoring, template edits and native charts; it is not a drop-in arbitrary-HTML import engine. Retain its principle of package validation and actual visual review without redistributing proprietary helper code. Generalization here still requires adapters and representative review. Windows was not tested. Do not compare the baseline time after shared capture with our full capture+export time.


## Editable supplement

18 additional slides were tested, default light / warm, 1920×1080; both actual PowerPoint Mac proof PDFs exist. Total comparative coverage is now 47 slides. Editable: 466 nonempty text frames per exporter, exact per-frame text completeness; ours 1398 native geometry objects / 26 pictures / 18 native number fields / 4 layout backgrounds; comparator 1234 / 190 / 0 / 0, with 18 per-slide backgrounds. Pixel MAE: 2.8867 vs 5.6381. File sizes: 5.29 MB vs 7.95 MB. Many geometry objects are repeated dots: counts are not an editing-usability score. No semantic p:grpSp groups are emitted yet.

The literal legacy import stopped on slide 4 due to its >12pt text / 0.5 inch bottom guard. For the adapted run, footer outer paragraph CSS is 16px while explicit span sizes retain the real source font size and unchanged positions/line height. Record this adaptation; do not present it as an unadapted import. Stroke padding was included for rasterized zero-height SVG lines. Both exporters use the same capture, source fonts and font embedding. Current Anthropic SKILL.md remains a broader PPTX authoring/editing workflow, not the tested historical helper or an independent Claude model benchmark.

Our fixes: Grid display detection, zero-height parent traversal, native horizontal SVG paths, CSS generated counters/separators, source QR padding. Reused media reduced 48 parts to 29 by removing 19 duplicate files / 5,998,855 raw bytes. Small text rasterization, rounding and marker-position differences remain. Windows and the other seven Editable style/theme states are unverified.


## Grouping supplement, 2026-10-24

Native grouping is now implemented as an explicit profile option, verified separately from the earlier exporter benchmark. The Editable sample groups slides 2, 5, 6 and 14 (22 native groups: 16 components, 6 nested groups). Its 18 actual PowerPoint Mac PDF page renders are pixel-identical to the accepted flat v04; four saved native text edits retained the expected group ancestry, including a nested chart label. This does not add a new Anthropic run or validate automatic grouping on other decks. See components.md for the working contract and current limits.


## v05 output/resource regression, 2026-10-24

AI PDLC Status v04 adds eleven slides with 69 groups, 4 full fonts, 2 layouts and 1 native MP4. Shared core now includes the local ID/video/path-marker fixes. PowerPoint Mac proof: 10 pages pixel-identical to the accepted native proof; page 9 intentionally replaces Chromium controls/spinner with a clean paused cover, preserving geometry and source video. This is not an additional Anthropic comparison.

Final local runs: PPTX-only 9.518s; both 10.271s (old both 10.955s excluding final verify); browser viewing PDF 3.677s; raster viewing PDF 3.256s. Different output modes and timer boundaries must be stated. No CPU/RAM or statistically repeated cold-start benchmark. Fresh Luna medium testing used fewer aggregate tokens than the earlier Sol6.1 xhigh adaptation, but the stages and parent/native UI work differ; do not claim a controlled model/cost win.


## v06 compatibility/runtime/diagnostics regression, 2026-10-24

The renderer is unchanged. Four families /58slides were replayed; normalised native slides/layouts/masters, relationships, media/fonts and reference pixels matched v05. Known grouping counts69and22 selected through structural profiles, not filenames. Renamed, changed-container, counter, missing-image and unsupported-marker fixtures exercise the preflight gates; PDF-only keeps separate requirements. Regional diagnostics detected a removed small label at whole-page MAE0.0223; unchanged accepted-baseline pages produced no new candidates. These are diagnostic regression tests, not an additional Anthropic comparison or new Windows/native-app run. Known accepted proofs were reused after package-content equivalence. Last11-slide export8.32s is a warm local observation, not a controlled performance/model-token benchmark.


## v07 cache benchmark, 2026-10-24

Three independent rounds, eleven AI PDLC Status v04 slides, identical final engine/runtime: disabled cache, empty cache, warm unchanged, warm with only slide 9 metric 5 180 to 5 181. Median wall times from launch through clean process exit (full package checks included): 8.659s / 8.682s / 4.273s / 4.574s. Warm savings against disabled: 50.7% unchanged, 47.2% single-slide edit. Warm hits: all four fonts and 11/11 paint entries; edit: four fonts and 10/11 entries. Font stage median cold 0.180s versus warm 0.033s. Cache size for this sample: 11,642,628 bytes. Three local repeats are not a hardware-independent performance guarantee. No model token, CPU or RAM measurement.

All three replay rounds matched normalised native PPTX XML/relationships and byte-identical font/media data. The single-slide edit changed only slide9 XML and matched a fresh uncached edited export. Unchanged v07 output also matched the package behind the accepted v05 PowerPoint Mac proof. A new edited Mac proof was attempted but the file picker kept Open disabled; no new native visual/editability or Windows claim is made. These timings exclude native QA.

Additional replay: Editable 18/18 hits; Brand 12/15 hits, with three genuinely different current source reference PNGs triggering regeneration (final PPTX content nevertheless matched cold). Meetup's Canvas causes intentional slide-cache bypass. PDF-only remains fresh with no cache; both mode regenerates PDF pages. Corrupted font/slide entries regenerated independently; a non-directory cache path disabled caching and still produced a verified export. Every scenario retained current source capture, text/geometry measurement and full package checks. See cache.md for invalidation and limitations. This is a cache regression, not another Anthropic/model benchmark.


### v07 native follow-up

The prior Open-dialog blocker was bypassed through Finder, then both actual cached PPTX files were opened in PowerPoint Mac without repair prompts and exported locally to PDF. At 1920×1080, all eleven unchanged pages are pixel-identical to the accepted v05 proof. With the single metric edit, ten pages are identical and page9 differs only in the intended final digit 5 180 to 5 181 (difference box [1478,277,1580,370], inside its text block). All-page contact sheet and metric crop reviewed. The Office picker also disables accepted v05 and remains so after ordinary restart; exact internal cause unconfirmed. No renderer/cache code changed for this follow-up. Previous timings remain converter-only, excluding native QA. Windows remains untested.
