# Release v0.7.2-pilot.1

Maker **0.22.0-rc19.2**, shell **v18.2**, Export **0.9.1**.

The guarded workflow makes the supported entry point explicit. It checks environment readiness, builds through the included builder and checks the exact HTML before reporting technical success.

- ready validates Python/Node, pinned assets, the actual builder and browser execution.
- build invokes the final builder and runtime, content and interactive checks.
- verify checks a delivered/saved HTML, with runtime-only scope when no project is supplied.
- Reports include errors, scope and hashes. Interactive edit/save/reopen probes are retained separately.

The prior runtime and design capabilities are preserved. The control does not force a third-party agent to invoke it. Visual design, independent source comparison and native exports need their documented acceptance.

Synthetic regression cases avoid including private inputs in the public package. The browser workflow runs these cases on Linux with Chromium.
