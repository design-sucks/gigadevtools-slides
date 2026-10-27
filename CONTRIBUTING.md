# Contributing

Start with a small reproducible issue and the skill version, OS/browser, viewport and expected/actual behavior. Share only material you can publish; remove confidential text, identifiers and assets. The minimal example should show the defect without a private customer deck.

Keep changes scoped. Reuse the existing builder/export entrypoints and preserve source text, stable IDs, accepted geometry, native wheel input, 16:9 show/export and browser save/reopen. Add a meaningful regression check for a runtime fix. Do not mirror implementation details with a test that cannot detect the original defect.

Run python3 scripts/check_release.py and the appropriate checks from [testing](docs/testing.md). Include affected screenshots for a visual change and state untested platforms. Native PPTX acceptance needs actual target PowerPoint proof.

Original contributions are made under the repository code license; third-party font/assets keep their own terms. Do not add new proprietary assets or private runtime configuration to a pull request.
