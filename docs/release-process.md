# Release process

1. Make a narrow branch and fix the shared source, not copies of built HTML.
2. Run the checks relevant to the change. Pure documentation edits need static checks; runtime/style changes need browser review. New PPTX handling needs native proof as applicable.
3. Bump the affected skill's package.json and SKILL.md metadata together; update releases.json and CHANGELOG.md. Deck/shell versions remain separate.
4. Rebuild the demo only if its project/runtime changed. Run python3 scripts/build_demo.py --check.
5. Run python3 scripts/package_release.py. This validates sources, creates two standalone ZIPs plus a bundle and SHA256SUMS in dist, and tests ZIP CRCs. Never upload local configs/caches/private inputs.
6. Create a GitHub draft Release at the exact releases.json tag and attach the dist files. Check downloads, folder roots and the font notice; publish the approved pilot release as a prerelease.
7. GitHub Pages serves docs/index.html from main /docs. It must match the generated example exactly. It is a viewing demo, not a conversion backend.

The initial tag is v0.1.0-pilot.1; Maker 0.17.4 and Export 0.8.3 are packaging/documentation updates over the accepted implementation. GitHub's source archive is not a replacement for the convenient standalone skill ZIPs.

Use patch for a compatible fix, minor for a new feature, major for an incompatible contract. A release workflow collects validated packages as an artifact; it does not silently publish a new Release or change access.
