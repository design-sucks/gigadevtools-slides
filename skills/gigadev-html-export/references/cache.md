# Cache contract

Caching is on for PPTX/both. Default location is .html-export-cache beside the output directory; use --cache-dir DIR or HTML_EXPORT_CACHE_DIR for a persistent shared location. --no-cache does no cache reads/writes. --no-slide-cache retains only font caching. PDF-only stays fresh and creates no cache entries. In both mode browser PDF pages are regenerated, even when PPTX paint is reused.

## What is reused

Font keys cover source bytes, family/weight/type, alias, the font packer, fonteditor-core entrypoint, package version, Node and Python/fontTools versions. The cached bundle contains source/raw/packed font and TTF. Source glyph coverage, embedding permissions and full font inclusion are still independently verified on every export.

Slide entries contain only per-object PNGs and the composed background. The engine always activates each slide, takes a current source PNG, materialises generated text, measures all text/geometry/groups and reads links. It builds all PPTX objects anew from that fresh scene; it does not reuse old text blocks or whole slide XML. Keys cover source pixels, fresh scene/links, fonts, grouping rules, mode, canvas, converter script hashes, Chrome/Node/Python and OS versions. Content changes affect that slide; changes to shared inputs may invalidate more entries.

A video blob URL changes every browser launch and is not useful as a visual identifier. For a paused video with a poster, an independent fresh cover capture without browser controls is hashed. Only that rectangle is masked in the key's reference image; the user's actual source reference PNG is not changed. Native video data is read from the current source and packaged anew. Moving/seeking video, missing posters, Canvas/WebGL and paint with external/non-data URLs bypass slide caching. This conservative first implementation does not track local file dependencies by bytes.

## Integrity and scope

Every entry has a committed manifest with the exact expected artifact names and SHA-256 of every file. Missing, corrupted or mismatched bundles are misses and are rebuilt. Temporary files are renamed and the manifest is committed last. Concurrent/incomplete writes can cause misses, never accepted mixtures. A cache write failure disables caching for the rest of the run and reports disabledReason; it does not discard an otherwise valid export.

summary.json/report.json expose font/slide hits, misses, bypasses, invalid entries, bytes and lookup time. Small values are observations, not guarantees of performance. The cache contains derived presentation graphics and fonts; keep it local and exclude it from skill/delivery archives. --no-cache bypasses it but does not remove it. There is no automatic eviction in v07; remove the specifically identified managed cache folder manually when it is no longer needed. Do not delete unrelated parent directories.

The eleven-slide benchmark compares three independent rounds of disabled/cold/warm/one-slide-edit runs, with full wall time and core stage time. Source reference/DOM checks and final package verification remain in every timing. A warm hit is not a reason to skip a new native proof when delivered content changes. Token use and CPU/RAM were not measured by these converter timings.
