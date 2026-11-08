# v0.7.0-pilot.1 — navigation and layout update

Maker **0.22.0-rc19**, Export **0.9.1** (unchanged). Release manifest state: **prerelease**. Publication authorized on 2026-11-08.

## User-visible changes

One pencil in the slide organizer opens a raised popover for the short list name and the chosen slide's show section/topic. There is one set of apply/cancel/restore icons, no duplicate preview, and no expansion of the card beneath it. All values are plain text. The list name stays separate from body headings and presentation context; page numbers stay automatic. Hidden/number-only headers retain their mode.

Changes participate in dirty state, local drafts, journal, revision saves and history cleanup. Work saves retain excluded slides; bundles contain selected slides. Saved work can be reconciled into the JSON project with per-field conflict detection, then rebuilt without losing edited navigation. Independent fields can merge; a competing edit to the same field fails without overwriting the project.

This package also includes previously local RC18/RC18.1 improvements: full-viewport decorative backgrounds behind the navigation rail; reviewed source chrome mapped to shell metadata; final-build guards and a current-release delivery baseline; the bundled demo as the experimental default composition reference when none is supplied, with six local previews. Explicit preserve-design/no-reference requests and supplied references take priority. Existing journal highlights, typography and earlier font/graphics/media repairs remain included. No new layout/chart library or Typograf dependency is added.

## Qualification and limits

The bounded acceptance uses three authored slides for navigation UI, keyboard behavior, persistence, excluded records, actual show/static export, saved-work/project round trips, reset and conflict cases. Existing resolver/reconciliation, shell and shortcut checks are relevant regression gates. A small real PPTX source/delivery smoke covers the combined build; it is not a new wave of full-deck tests.

Source/graphics/contrast acceptance may remain **review** where human judgement is required. Automatic tests do not certify universally good design, arbitrary source topology, media playback on every system, native PowerPoint or Windows rendering. The inherited Linux compact-anchor discrepancy remains outside this change. Corporate font scope and MIT exclusions are unchanged.

The [release manifest](../releases.json), source/package checks and non-publishing dry-run define the package. Publication uses the main-branch release workflow; GitHub Pages serves the matching rebuilt demo.

## Local acceptance results

On macOS/Chrome: 12 navigation-editor/round-trip scenarios, 7 override-resolver cases, 9 existing navigation cases, 12 presentation-role cases, 15 shell checks and 7 shortcut checks passed. Existing structured and authored-inline reconciliation suites passed, including guarded failures. Extraction/core regression checks passed. The editor was also inspected in both themes.

A private real three-slide PPTX smoke had delivery **pass**, verified source hash and no source-content issues; aggregate source/graphics/contrast/portability remained **review** with their normal visual limitations. Full-deck tests were not repeated. Source/package checks, archive CRCs and non-publishing dry-run passed. Remote CI and a new Linux/Windows/native PowerPoint run were not performed as part of this preparation.
