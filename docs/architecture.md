# Architecture

The Maker keeps three separate concerns: source content/project data, slide visual style, and the reusable UI shell. Build.py assembles a self-contained HTML. Browser edits are saved into a new HTML version; they do not silently sync an older project JSON.

The accepted shell is v17.2. Reading uses compact page pitch while keeping content anchors. Fade reaches the next adjacent anchor; whole-slide temporary visibility hides nonparticipating slides without cropping blur. Show/print/export release that state and use the original 1920×1080 layout.

The Export skill consumes the actual HTML and awaits GigaDevDeck.prepareExport() for schema 1. It measures static selected slides and creates PPTX geometry/text plus image fallbacks, or a separate viewing PDF. Native PowerPoint verification remains outside browser QA.

Package versions (Maker 0.17.4, Export 0.8.3), shell version and deck version v01 are independent. [releases.json](../releases.json) records the bundle. The examples/shell-demo/project directory is the authoring source; index.html and docs/index.html are generated copies checked for freshness.
