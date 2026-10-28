# Runtime baseline

Maker package0.19.1 retains the accepted shellv18.2 runtime and adds source-style/graphics inventory, decision checks and QA resize synchronization. Runtime module hashes stay in `baseline-v18_2.json`; this update does not change slide motion or UI paint.

Shell v18.2 / package 0.18.2 uses translucent neutral title/active-navigation surfaces and divider colors in both themes. Text and icons remain fully opaque; solid dialog/field surfaces are separate. `baseline-v18_2.json` records this scoped UI update.

Shell v18.1 / package 0.18.1 fixes the v18.0 background-motion regression: full-viewport paint behind transparent navigation, preserved content anchors, shared wheel/keyboard blur and opacity, and explicit static print/export dimensions. `baseline-v18_1.json` records the reviewed modules. The background regression also runs from the standalone skill archive.

Shell v18.0 / package 0.18.0 is a browser-verified update candidate. Full-canvas backgrounds and safe content are independent, metadata show/export share 48/30 Display20 geometry, navigation prefixes are separated from page counters, and preparation status/targets are explicit. New core cases, the existing 15-check shell suite and 8-check compact suite passed in Chrome on Mac. `baseline-v18.json` records the reviewed candidate modules. This does not approve every new slide design, arbitrary PPTX effects, native Windows rendering or an unexecuted PowerPoint export.

Shell v15 was accepted by the user on 2026-10-27. `assets/baseline-v15.json` remains its immutable ancestor; `baseline.json` retains v06. The user accepted shell v17.2 on 2026-10-27; demo v05 was reset to v01 without runtime changes.

Shell v17.2 fixes the shifted v17 reading origin and v17.1 neighboring-slide tails; it adds the requested keyboard commands, focus return and compact reading on top of that UI. `baseline-v17_2.json` records tested module hashes; it is a verified release, not a claim that every future deck is visually accepted.

Default demonstration v01 has 13 slides, including «Хоткеи» on slide 03. New decks start at v01 independently of the shell version. Compact free reading is separate from 16:9 showing/export; see compact-reading.md. Motion orchestration changes for visible neighbors, while source curves, keyboard timing and native wheel distance remain the reference. Compact fade progress is normalized to adjacent anchors, so neighbors fully disappear at rest.

Retain continuous #050709 dark background, embedded SB Sans Text/Display/Extended, transparent navigation rail with content-fitted selector, edit/undo/redo, organizer/exclusion, journal, save/reopen/versioning and optional intentionally prepared themes. Preserve the single original toolbar, including its screen control. Never depend on the large source SalesKit file or author's machine. Scope browser, platform and hardware verification honestly.
