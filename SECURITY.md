# Security policy

## Supported versions
The current `main` branch is supported. Update to its latest tested commit.
Older snapshots do not receive separate security backports.

## Reporting a vulnerability
Report suspected vulnerabilities privately to **apoorv@fud-ai.app**, or use
GitHub's private vulnerability reporting option when available. Do not post
credentials, personal resume data or exploitable details in public issues.
Include the affected commit, impact, reproduction steps and a suggested fix.
Reports are triaged by Apoorv Darshan, the sole maintainer. The response target is
14 days; critical issues are prioritized immediately. Coordinate disclosure
until a fix is available. These are response targets, not a historical attestation.

## Trust boundaries
The public README and star Worker contain public data. The Worker restricts GitHub lookups to validated owner/repository identifiers and escapes SVG text. Tokens stay server-side. The scheduled refresh is privileged and is restricted to the default branch; untrusted pull requests must not run it or receive its secrets. Store and resume source histories stay in the separate private repository. TLS is delegated to Cloudflare/GitHub; there is no password store or custom cryptography.

## Development and release checks
Use least privilege, validate external input, and review dependency advisories.
Every major change needs automated tests and static analysis before publishing.
Fix confirmed exploitable findings of medium or higher severity promptly; do not
leave known medium/high vulnerabilities unresolved for 60 days. Document security
fixes in CHANGELOG.md, including CVE identifiers when applicable. Dependencies
are monitored with Dependabot and CI audits where a package manifest exists.

Solo-maintainer policy: zero required approving reviews. Do not require code-owner
approval or last-push approval. Force pushes/deletions are blocked where the GitHub
plan supports protections. Automated profile commits must remain possible.
