# Third-party notices

## SB Sans — corporate pilot assets, not MIT

This pilot includes SB Sans Text, SB Sans Display and SB Sans Display Extended as OTF files and Base64 data inside generated HTML. Original font names and copyright metadata are preserved.

Copyright notices in the supplied files identify ParaType Inc./ParaType Ltd. (2018/2019). Their license metadata points to https://www.paratype.com/eula.

The publisher requested this public test repository for a corporate workflow and reports that the intended company holds font rights. This statement records the pilot context; it is not an independently verified grant to every visitor. **The repository's MIT license does not license these fonts.** Use the font assets only when your applicable rights cover your use, including hosting, redistribution and editing. Base64 packaging and embedding flags do not grant additional rights.

For a general-audience edition, a separately reviewed open-font profile is planned. There is no automatic fallback or universal font-rights guarantee. Original fonts should not be silently replaced in the accepted corporate demo.

Font locations: skills/gigadev-html-maker/assets/fonts, examples/shell-demo/project/fonts and embedded @font-face data in example HTML. Standalone skill ZIPs also include this notice. Removing only the OTF files does not remove embedded copies.

## Dependencies

Dependencies are installed separately; node_modules and Python environments are not vendored. Their own license files govern their use.

| Dependency | Declared version | License in inspected distribution |
| --- | --- | --- |
| Playwright | 1.62.1 | Apache-2.0 |
| PptxGenJS | 4.0.1 | MIT |
| JSZip | 3.10.1 | MIT OR GPL-3.0-or-later |
| sharp | 0.35.5 | Apache-2.0 |
| fonteditor-core | 2.6.3 | MIT (LICENSE file) |
| svgpath | 2.6.0 | MIT |
| fonttools | 4.67.0 | MIT |
| pypdf | 6.21.2 | BSD-3-Clause |

The historical comparison described in Export references does not bundle Anthropic's historical helper. Internal benchmark source decks and native proof PDFs are not included in this repository. Do not present that private corpus as a fresh, publicly reproducible benchmark.

## Retained upstream notice

The Export package retains the MIT notice for dom-to-pptx, Copyright (c) 2025 Atharva Dharmendra Jagtap and dom-to-pptx contributors, in skills/gigadev-html-export/references/dom-to-pptx-LICENSE.txt (references/dom-to-pptx-LICENSE.txt inside its standalone ZIP). Preserve that notice with applicable redistributed portions. This is separate from the historical Anthropic comparison.
