# GigaDevTools Slides

**Build editable HTML presentations. Export HTML decks to editable PowerPoint or viewing PDF.**

A corporate pilot with two portable Agent Skills and an interactive, offline-ready example.

[Русский](README.ru.md) · [Try the demo](https://design-sucks.github.io/gigadevtools-slides/) · [Download packages](https://github.com/design-sucks/gigadevtools-slides/releases) · [Quick start](docs/quickstart.md)

![HTML Maker demo](examples/shell-demo/previews/cover.png)

## Choose a skill

| Skill | Use it for | Output |
| --- | --- | --- |
| [HTML Maker](skills/gigadev-html-maker/SKILL.md) | Turn PPTX or supplied content into a styled web deck | Editable standalone HTML |
| [HTML Export](skills/gigadev-html-export/SKILL.md) | Convert a measured HTML presentation | Editable PPTX or viewing PDF |

The HTML shell includes native free scrolling, soft transitions, keyboard/clicker navigation, text editing and undo, slide organization, a change journal, version saves and deliberately prepared themes. Slide styling is separate from the UI shell. The editor edits text; it is not a drag-and-drop layout editor.

## Start in three steps

1. Download a skill ZIP from Releases, or clone this repository.
2. Put the corresponding skills folder in your agent client's skill directory. A client without skill registration can read SKILL.md and execute its scripts.
3. Attach your source and a style reference, then invoke the appropriate skill. The agent needs filesystem and code execution; a text-only conversation cannot run the converter.

Example prompts:

> Use $gigadev-html-maker. Turn the attached deck into an editable offline HTML presentation using the supplied style reference. Preserve all source text and numbers, use the bundled shell, and start the deck at v01. Check every slide in a browser.

> Use $gigadev-html-export. Export the attached HTML as editable PPTX. Preserve layout, links and typography, and report what was verified in the target PowerPoint.

[Installation](docs/installation.md) has the runtime setup and commands. Source files remain unchanged. After browser edits, save a new HTML version and use that file as the current source.

## Try the example

[Open the live shell demo](https://design-sucks.github.io/gigadevtools-slides/) or download examples/shell-demo/index.html and open it locally. It is one file with embedded fonts/graphics. The demo starts at **v01**; saving proposes **v02**. Slide 03 explains the hotkeys, including **N** for the slide list and **M** for motion. HID clickers emitting PageUp/PageDown or arrows use the navigation path; hardware compatibility is not claimed for every remote.

The example teaches the shell. A source-to-result case study will be added after a separate user-provided test; it is not fabricated from this tutorial deck.

## Corporate font scope

**Original code and documentation: MIT. SB Sans font assets: separate third-party terms.**

This public pilot targets a company workflow whose publisher reports font rights. It is not a general license grant for SB Sans. The OTF files and embedded copies are excluded from MIT. Check [third-party notices](THIRD_PARTY_NOTICES.md) before using or redistributing them. An independently reviewed open-font profile is planned for broader use.

## What is verified

The accepted shell was checked in Chrome on Mac: 13 slides, both themes, preserved content anchors, 208 settled visibility states with motion on/off, text edit/undo, save/reopen and 16:9 show/export-adapter geometry. Package versions and inherited evidence are described in [testing](docs/testing.md).

Arbitrary PPTX effects may need raster fallbacks or adaptation. Browser appearance does not prove PowerPoint fidelity. Real target PowerPoint review remains part of PPTX delivery; Windows, Safari and each new client require their own verification. The exporter is a profile-driven pipeline, not a universal arbitrary-HTML renderer.

## Development

```sh
python3 scripts/check_release.py
python3 skills/gigadev-html-maker/scripts/self_test.py
python3 scripts/build_demo.py --check
python3 scripts/package_release.py
```

See [contributing](CONTRIBUTING.md), [release process](docs/release-process.md), [compatibility](docs/compatibility.md) and [changelog](CHANGELOG.md). Versioned ZIPs are generated from one repository state; local runtimes, caches and client presentations are excluded.
