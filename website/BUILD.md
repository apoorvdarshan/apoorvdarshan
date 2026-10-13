# Build and interfaces

Node.js 24 and Python 3.12 are used in CI.

```sh
npm ci
python3 -m pip install -r scripts/automation/requirements.txt
npm run lint
node --test scripts/automation/*.test.mjs
python3 -m unittest discover -s scripts/automation -p 'test_*.py'
npm audit --audit-level=moderate
npm run build
```

The build produces `dist/`; `npm run dev` serves a local preview. No credentials
are required for tests. CI never deploys pull requests. Build reads public profile
metadata; a network failure may require a retry.

## Interfaces
- `/`: HTML SPA and generated routes, with public profile data.
- `/resume`, `/Apoorv_Darshan_Resume.pdf`: published PDF, never private LaTeX.
- `/badges/downloads/v1/<label>.svg` and `/badges/users/v1/<label>.svg`: GET/HEAD,
  bounded numeric labels (`4`, `40+`, `1K+`), SVG on success, 404 malformed,
  405 unsupported method. No upstream API call per badge request.
- Automation configuration, input/output files, credentials and failure handling:
  [automation operations](scripts/automation/README.md).

The fuzz test exercises 2000 generated hostile badge/LaTeX inputs with assertions.
Bandit and ESLint run in CI; CodeQL runs for JavaScript and Python. Review all
findings and fix confirmed exploitable vulnerabilities before major releases.
