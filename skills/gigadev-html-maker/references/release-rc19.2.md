# Maker RC19.2 · Guarded workflow

Maker 0.22.0-rc19.2 uses the same v18.2 runtime modules and compact baseline as RC19.1.

Use scripts/maker.py ready before authoring in a new environment. It checks the full pinned package, dependencies, canonical build and an actual browser startup. The final build repeats readiness, invokes build.py with --final and the composition plan, then verifies the exact HTML with runtime identity, check_delivery.mjs and check.mjs.

Use verify with a synchronized project for saved HTML. HTML-only verification identifies the runtime and checks navigation. Its runtime-only scope does not certify source completeness.

Reports preserve underlying errors and review dispositions and bind a successful verification to the HTML/project hashes. Interactive probe files live beside the report. Resolve errors before delivery and disclose skipped scenarios.

Qualification includes synthetic guarded-workflow regressions, the existing browser suite and private negative examples of alternate viewers. Those private presentations are excluded from this package. Graphical composition, source completeness and actual PowerPoint output retain separate review. Instructions can be bypassed by an external agent outside this command path.

See [setup](setup.md#guarded-workflow) and [delivery checks](delivery-check.md).
