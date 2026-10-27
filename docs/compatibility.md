# Compatibility and limits

| Area | Evidence / limit |
| --- | --- |
| Accepted HTML shell | Chrome on Mac; 13 slides; two themes; first/last/dense slides |
| HID clicker | Standard PageUp/PageDown/arrow event path checked; no universal hardware claim |
| Text editing | Paragraphs, table text, undo, journal and version saves; no object-layout handles |
| PPTX import | Content/geometry inventory; unsupported effects require review, not a pixel-faithful arbitrary-PPTX renderer |
| HTML export | Fixed-layout profile-driven reconstruction; arbitrary websites require adaptation |
| PowerPoint | Historical Mac proofs described in Export references; this pilot does not add a fresh demo PPTX proof |
| Windows / Safari | Separate verification required |
| Other LLM clients | Standard skill folder; client-specific registration/execution must be checked |
| Fonts | SB Sans corporate profile; separate rights required, not MIT |
| PDF | Browser/raster viewing outputs; editable PDF not promised |

Video, Canvas/WebGL, dynamic UI and unusual paint need explicit static-state or media handling. Links/assets may require connectivity even when the deck shell itself is offline. The bundled shell demo embeds its fonts and vectors.

An open-font profile is planned as a separate option. It must cover UI and slide typography, not merely rename one CSS family. Wrapping, density, contrast and anchors need new visual review and an approved profile baseline. No automatic font substitution or monitoring service is implemented.
