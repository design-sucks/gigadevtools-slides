# Native PowerPoint acceptance

1. The converter automatically runs verify.py across all slides; this structural gate does not prove visual fidelity. For viewing PDF, verify its rendered pages and links; no PowerPoint roundtrip is needed.
2. For editable PPTX, open one QA copy in the actual target PowerPoint. Export PDF locally (Mac: PDF → Optimize for printing); do not upload to Microsoft's conversion service. Run compare.py --source OUTPUT --powerpoint-pdf ACTUAL.pdf --out REVIEW. Read the compact JSON and inspect outliers first; account for every page before accepting. Pixel MAE alone can hide a small missing arrow.
3. Check wrapping, baselines, clipping, images, stacking, opacity, numbering and semantic paragraphs. When adapting, fix the shared adapter and repeat affected checks, not the whole investigation.
4. For a newly introduced grouping profile, compare with the accepted flat native proof. Save real text edits in an ordinary and a nested group in a separate QA copy; verify text and group ancestry after saving. Never deliver probe edits. Reuse this evidence for an unchanged profile only when structural/render regression checks show no change.
5. Close each temporary document after checking its exact path. Preserve user documents and unknown unsaved changes. Mac and Windows are separate acceptance targets.

A source/browser PDF is a viewing deliverable. A PDF exported by PowerPoint is a PPTX test artifact. Never substitute one for the other. Previous accepted proofs can be reused as the baseline only after the actual new PPTX is compared.


v06 diagnostics: the unified --compare command reports whole-page difference plus semantic text regions, small paths and 64px tiles. Text estimates nominate possible loss/wrapping; neighbours, font metrics and PDF text extraction can cause false positives. --only-outliers limits image-pair output, not computation. All-page/OOXML gates remain.

When a genuinely accepted native proof exists, --baseline-pdf ACCEPTED.pdf prioritises changes against that proof and suppresses unchanged accepted regions. Keep source HTML MAE visible separately. Never call an arbitrary or newly generated PDF an accepted baseline to silence warnings. If a maintenance update emits identical slide/layout/master XML after normalising only field UUIDs and source asset descriptions, identical relationships/fonts/media and identical references, prior native evidence can be reused explicitly; do not label it as a new PowerPoint opening.


Mac opening fallback: if PowerPoint's Open picker disables a valid PPTX, test the accepted control file in that same picker. A picker failure is not a corrupt-file diagnosis. Open the exact file through Finder (Go to Folder → absolute file → Cmd+O), verify the PowerPoint window URL and watch for repair prompts. Export the actual native proof as usual. Record observations and the unresolved cause separately; do not remove quarantine/security settings or rewrite the PPTX merely to fix the picker. In the v07 test the accepted v05 and cached v07 were both disabled by the picker, but opened normally via Recent/Finder; an ordinary restart did not fix the picker.

HTML Maker v01: use HTML Export v08+, which prepares the selected deck through GigaDevDeck.prepareExport(). UI is excluded and static headers are materialized per slide. A source with no embedded faces is explicitly marked fontEmbeddingVerified:false. System-font weight is emitted as native bold for weight >=600; weight-specific embedded aliases keep their original behavior. A neutral demo is a shell compatibility fixture, not evidence for arbitrary PPTX-to-HTML fidelity.
