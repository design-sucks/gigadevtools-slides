# v0.6.0-pilot.1 — corporate prerelease

Maker 0.22.0-rc17 / Export 0.9.1. This repository snapshot packages the bounded, qualified RC17 update as a corporate prerelease. releases.json selects releaseState:prerelease; the main-branch publishing workflow builds and uploads the immutable release assets.

## User-visible changes

Journal Before/After highlights exact changed fragments, including punctuation and whitespace. Deletion and insertion use both color and text decoration; the same comparison appears in preparation proposals, current user edits and saved history. Source strings and review semantics are unchanged. Long differences have a bounded fallback.

The update consolidates earlier RCs: content/list/source-style checks; exact-source guards for edits and reconciliation; targeted font readiness/face mapping and approved shell-font fallback; explicit diagram relationships and static source effects; offline media controls; translucent shell surfaces, single-theme controls and section-aware navigation with repeated headings removed. Layout remains authored per slide; no universal typography or design optimizer is claimed.

## Retained and excluded

Existing 24-reference pack and legacy 18-pattern renderer plus already-present composition variants are retained. The separate six-slide donor pilot, Typograf and new chart/template dependencies are excluded. Export remains0.9.1. No private PPTX, company presentation, local runtime configuration or personal path is included. SB Sans remains under its separately documented corporate rights basis.

## Validation scope

Historical: three selected real mini PPTX inputs,16 slides, accepted on RC13; RC14–RC16 focused text/UI/navigation checks. RC17: twelve journal difference cases, both themes and views, exact source acceptance/rejection and save/reopen; public 13-slide demo with15 shell checks at desktop/small/narrow widths; source/package/version/font-baseline checks and existing source/core/composition/reference/text/navigation tests. Release-specific runtime hashes include the intended RC11–RC17 module changes while keeping all old baselines unchanged.

Full 78 slides, other browsers, hardware clickers and new native PowerPoint/PDF export qualification are deferred. A passing bounds check is not visual design approval. Source animations and unusual effects retain their disclosed approximation limits.

## Review before publication

Review CHANGELOG.md, releases.json, the new runtime snapshot and package hashes. Open examples/shell-demo/index.html and the journal's demo correction. Run scripts/check_release.py, scripts/build_demo.py --check and scripts/package_release.py. Local publish_release.py --dry-run prepares the command plan without network writes.
