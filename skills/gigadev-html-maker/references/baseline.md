# Runtime baseline

Shell v15 was accepted by the user on 2026-10-27. `assets/baseline-v15.json` remains its immutable ancestor; `baseline.json` retains v06. The user accepted shell v17.2 on 2026-10-27; demo v05 was reset to v01 without runtime changes.

Shell v17.2 fixes the shifted v17 reading origin and v17.1 neighboring-slide tails; it adds the requested keyboard commands, focus return and compact reading on top of that UI. `baseline-v17_2.json` records tested module hashes; it is a verified release, not a claim that every future deck is visually accepted.

Default demonstration v01 has 13 slides, including «Хоткеи» on slide 03. New decks start at v01 independently of the shell version. Compact free reading is separate from 16:9 showing/export; see compact-reading.md. Motion orchestration changes for visible neighbors, while source curves, keyboard timing and native wheel distance remain the reference. Compact fade progress is normalized to adjacent anchors, so neighbors fully disappear at rest.

Retain continuous #050709 dark background, embedded SB Sans Text/Display/Extended, transparent navigation rail with content-fitted selector, edit/undo/redo, organizer/exclusion, journal, save/reopen/versioning and optional intentionally prepared themes. Preserve the single original toolbar, including its screen control. Never depend on the large source SalesKit file or author's machine. Scope browser, platform and hardware verification honestly.
