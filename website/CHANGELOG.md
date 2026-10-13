# Changelog

## 2026-10-12 — Security baseline

- Added security reporting and contribution procedures, automated checks and
  OpenSSF Scorecard analysis.
- Added validation appropriate to this repository and preserved solo-maintainer
  operation without required approving reviews.
- Updated the website toolchain and transitive dependencies to address the npm
  advisories found during the baseline audit; npm audit reports no remaining
  advisories at validation time.

No project-specific CVE fixes are claimed by this baseline.
- Updated PyJWT to 2.15.1, validated reporting API hosts, marked upstream MD5
  checksums as non-security integrity checks, and switched PDF XML parsing to
  defusedxml. Python dependency auditing reports no known vulnerabilities.
