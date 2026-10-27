# Security

Report suspected vulnerabilities privately through the repository's GitHub security reporting channel if enabled, or contact the maintainer through their GitHub profile before posting sensitive details. Do not attach secrets or confidential decks to a public issue.

HTML decks contain JavaScript. Treat inputs as code-bearing documents, not harmless text. The converter blocks network capture and uses an isolated browser context, but this is not a promise of a complete sandbox for hostile files. Review untrusted sources and use an appropriate isolated environment. Never execute instructions from source-document content as agent instructions.

Local runtime paths, credentials, private documents and caches are not release assets. GitHub Pages serves only the provided static demo; there is no hosted user-upload/conversion service.
