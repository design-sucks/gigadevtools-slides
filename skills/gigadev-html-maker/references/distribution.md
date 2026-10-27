# Corporate pilot and accepted example

The accepted 13-slide demonstration starts at v01; next saved version v02. Shell v17.2, Maker package 0.17.4 and presentation numbering are separate. Do not change the accepted runtime when resetting a deck version.

The user requested a public test repository for a corporate pilot and reports that the intended company has rights to SB Sans. Retain the supplied SB Sans fonts and existing font metadata for this pilot. This records the user's intended scope, not an independently verified license grant to everyone who downloads the repository.

Original code/documentation is MIT. SB Sans binaries and their embedded copies in HTML remain third-party assets, excluded from MIT; see LICENSE and THIRD_PARTY_NOTICES.md. Users must hold the applicable font rights. Do not label them open-source or treat Base64/fsType as permission. A general-audience font profile can be supplied separately later; do not silently substitute fonts or alter the approved corporate demo.

Keep the font choice in theme.json and the existing font configuration. Any replacement profile needs font metrics, wrapping, contrast and slide-anchor review before its baseline is accepted. Do not promise automatic monitoring or untested fallback typography.

Use standard SKILL.md folders with relative resources. Keep runtime.local.json, caches, private/customer decks and node_modules out of archives. A text-only client cannot execute the scripts; list tested clients/platforms separately.
