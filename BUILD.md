# Build, test and interfaces

The README needs no build. Node.js 24 runs Worker tests without dependencies:

```sh
node --check star-badge-worker/src/index.js
node --test star-badge-worker/test/*.test.mjs
python3 scripts/validate-profile.py
```

Deploy the Worker with the pinned Wrangler version in its workflow; deployment
credentials are maintainer-only. Tests use mocked API/cache objects, never tokens.
The website/PDF pipeline lives in [profile](https://github.com/apoorvdarshan/profile)
and runs from the scheduled refresh workflow in this repository.

## Worker interface
GET `/health` returns plain text. `/api/stars?repo=OWNER/REPO&format=svg|json`
returns an SVG or JSON `{repo, stars, formatted}`. Invalid identifiers/formats
return 400; an unavailable upstream returns 502 (SVG requests may use a validated
Shields fallback). Unknown paths return 404. Counts are cached for an hour.
Identifiers cannot supply a host, query or path traversal; credentials are sent
only to GitHub. JSON is public, with permissive CORS for embedding.

Tests include generated hostile identifiers and failure responses. CodeQL checks
JavaScript; the profile validator checks managed content and file exposure.
