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

## Bind the exact document before automation

Treat open, identity verification, export and close as separate dependent operations. A failed/cancelled open must stop the chain. Never fall back to `active presentation`, and never run a bundled `open; save active; close active saving no` script. A system folder-access dialog requires user interaction; stop dependent commands rather than cancelling it and continuing with another window.

Prefer opening the exact QA copy through Finder when sandbox access through the application's picker is unreliable. Confirm its full window URL/path and filename before export. If scripting, use a stable reference to that exact presentation and verify its path again immediately before save/export/close. If the API cannot expose a reliable identity, use explicit UI verification or leave native acceptance pending; never guess from the frontmost title alone.

Export only the named QA copy to a new native-proof path. After export, record the input PPTX SHA-256, confirmed document URL/path, export method and page count in native-acceptance.json. Verify the PDF belongs to that document before comparison. Close only that same verified temporary copy, and preserve any existing user documents and unknown changes. If a dialog/error changes focus or interrupts the operation, revalidate identity before continuing. The delivered PPTX can still be built and structurally checked while user action for native QA is pending; clearly distinguish those states.

A Mac helper is included at `scripts/native_export.applescript`. It locates a presentation by exact full path, verifies identity around export, refuses an existing PDF output and closes only when explicitly requested and saved. It never uses the active presentation. It does not grant system folder access or prove the exported pixels; confirm those separately. Run it only on an identified QA copy. Prefer Finder opening first where needed; if a file-access dialog blocks the open, leave the dialog for the user and stop dependent operations.

```sh
osascript scripts/native_export.applescript /absolute/QA_Copy.pptx /absolute/New_Native_Proof.pdf
```

By default the identified copy stays open for inspection. The optional final `close` argument is only for a verified, saved temporary copy after acceptance. Do not run it on a user-edited original. A refusal/identity error is a stopping condition, not permission to export another document.

On Mac, the helper needs an application-capable automation context to load the PowerPoint scripting dictionary. A sandbox can report a compilation/property error when that dictionary is unavailable; stop and use the normal permitted executor or verified UI flow. Do not rewrite a failed command to use the frontmost/active document.
