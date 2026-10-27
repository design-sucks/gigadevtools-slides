# HTML Maker handoff

Accepted example: 13-slide HTML Maker demo v01, shell v17.2, Maker package 0.17.4. Presentation versions, engine/package versions and source numbering are separate.

Always consume the actual saved HTML supplied by the user. Await GigaDevDeck.prepareExport() for schema 1 before capture. It exposes selected order and static headers, freezes motion and releases whole-slide visibility effects used by compact reading. Export every selected slide, not only the visible slide/editor viewport; verify computed visibility as well as page count. The export adapter retains 1920×1080 independently of free-view page pitch.

Do not capture reading navigation, tooltips, editor or journal. Do not infer successful PPTX conversion from HTML/export-adapter screenshots. A fresh deck/style still needs preflight, text/font checks, and real target PowerPoint proof.

Exporter package 0.8.3 is a documentation/packaging update. Converter modules are byte-identical to 0.8.1. No fresh conversion or native PowerPoint proof is claimed by this update.

Public example/source rights are separate from font embedding permission. Exclude runtime.local.json, caches and real customer presentations from GitHub and public ZIPs. The public corporate-pilot sample contains third-party SB Sans assets excluded from MIT; users need their applicable font rights. The user requested this pilot and reports company rights.
