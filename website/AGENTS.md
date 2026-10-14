# Profile site — AGENTS.md

Guidance for agents working on `apoorvdarshan/apoorvdarshan` (https://apoorvdarshan.com): a Vite React SPA on Cloudflare Workers static assets, with a small Worker for `/resume`.

## Resume public download

- Canonical share URL: `https://apoorvdarshan.com/resume` (serves the PDF; downloads/views as `Apoorv_Darshan_Resume.pdf`).
- Source file in this repo: `public/Apoorv_Darshan_Resume.pdf` (fallback also at `/Apoorv_Darshan_Resume.pdf` after build).
- After every manual resume rebuild: copy the compiled PDF into `public/Apoorv_Darshan_Resume.pdf`, commit, push, and `npm run deploy` so GitHub + site View/Download stay current.
- Keep site header / Resume section links pointing at `/resume`. Do **not** put a Resume badge in Connect (Resume has its own section).

## Other content

- Automatic profile refresh runs every six hours from `apoorvdarshan/apoorvdarshan/.github/workflows/refresh-profile.yml`, using this repo's `scripts/automation/`. It updates verified merges/stars for `apoorvdarshan` only, commits directly, rebuilds the resume, syncs this site, and deploys to Cloudflare. No review PR or AI service. See `scripts/automation/README.md` for operations.
- For manual resume edits, commit the verified source, PDF and `build.json` in the root `resume/` folder together with `public/Apoorv_Darshan_Resume.pdf`. Local Documents links follow `~/apoorvdarshan/resume/`, which the sync job fast-forwards at login and every six hours while the Mac is awake (only when the checkout is clean and on `main`).
- Preserve curated project order, personal-project descriptions, and the resume header. Configured iOS counts update daily from ASC, Android counts from authenticated Google Play reports, and npm counts from the public npm API; configured Chrome Web Store user counts refresh daily. Only OSS entries sort by stars automatically. Multi-PR OSS descriptions refresh from the newest 2–3 distinct merged PR titles within the one-line limit, retaining cumulative counts and linked attribution; mirror generated descriptions into the resume.
- Preserve the Documents resume symlinks to `~/apoorvdarshan/resume/`. Background sync updates that checkout; backups live in `~/.local/share/profile-automation/resume-backups` (linked from Documents). Do not make background Python access the protected Documents folder.

- GitHub profile README syncs into `src/profileData.generated.json` via `scripts/sync-profile-readme.mjs` on build/dev. Cloudflare Workers `prebuild` re-runs that sync so a redeploy picks up the current README.
- `## What I Use` `### Hardware` / `### Software` shields.io logo tiles on GitHub README; sync → `uses.hardware` / `uses.software` (`name`, `badgeUrl`, `url`). **Site renders text links like Connect** (not badge images). Never the resume.
- LinkedIn experience/education are hand-maintained in `src/linkedinExperience.js` and `src/linkedinEducation.js`.

## Download counts (ASC)

- Current snapshot: `~/apoorvdarshan/resume/ios-downloads.json`, linked from `~/Documents/asc_downloads.json`. `scripts/automation/ios_downloads.py` refreshes the six configured iOS apps once per UTC day, then updates the README/resume before site/PDF builds. See the automation README for the reporting key, historical baseline, deduplication and recovery rules.
- For badges/copy use **first-time** downloads, never the all-events `total` (updates inflate all-events totals).
- Site/resume **Fud AI** = ASC lifetime first-time downloads + the latest verified Android first-time installs from `resume/android-downloads.json`, refreshed daily from Google Play reports. Round badges down; do not use the ASC all-events total.
- GitHub README uses maroon download tiles (`alt="Downloads: N"`); managed iOS and npm badges are served directly by the Cloudflare Worker at `/badges/downloads/v1/<encoded-label>.svg`, without Shields/API calls on image load. Preserve that URL in the updater. The site sync parses the alt text (fallback: trailing `(Nk+ downloads)`) into a `downloads` field and renders plain `↓ {count}` text beside ★ — same `.star-count` look (secondary color), **not** a maroon pill/tile.

- Chrome Web Store public listings may use README `Users: N` shields; sync maps those into the same `downloads` / ↓ chip on the site.

## npm downloads

- `scripts/automation/npm-downloads.json` explicitly maps five projects to npm packages. Their lifetime package downloads refresh daily without a token or 2FA bypass; public audit data lives in `~/apoorvdarshan/apoorvdarshan-automation/npm-downloads.json`. The npm snapshot remains npm-only. The final distribution step adds configured stable release asset events; Homebrew fetches of the same assets are already included. README, website and resume share the same rounded labels. Preserve the ASC/Android and extension counts independently. See `scripts/automation/README.md`.

- Android reporting uses a dedicated read-only service account with GitHub OIDC, covering current/future Play Console apps without per-app keys. Only configured packages are read or saved; explicitly validate lifetime history/metric and map a production app before adding it. Sum Daily User Installs once per overview date; never use the zero-filled legacy Total User Installs column or add device/country dimensions. Preserve old verified counts on failure. See `~/apoorvdarshan/website/scripts/automation/README.md`.

## Description Length

- Descriptions in **Apps**, **Games**, **Chrome Extensions**, **Projects**, and **Open Source Contributions** must stay on **one rendered line** at normal desktop width (GitHub README profile view and apoorvdarshan.com).
- Never let a description wrap to a second line on desktop. If it would wrap, **shorten the wording** (keep download shield badges in the GitHub README when present).
- Prefer ~90 characters or fewer for the plain description text after the name/badge.
- On apoorvdarshan.com, desktop list rows also use CSS ellipsis as a backstop (`white-space: nowrap; overflow: hidden; text-overflow: ellipsis`) — still shorten the source text; do not rely on clipping alone.

- `distribution_counts.py` runs after mobile/npm refresh: six explicitly mapped release repositories and two public Chrome store listings. GitHub assets are allowlisted (no checksums, signatures, AABs, drafts or prereleases), paginated and summed once per asset. Combined download events are not unique installs; Fud AI adds APK events to the unchanged first-time store subtotal. Homebrew casks for TetherShot and Browser Cookie Bridge use GitHub assets: never sum those installs again. Chrome users remain a separate metric and may decrease. Public audit: `profile-automation/distribution-counts.json`. Failed sources keep their previous verified snapshot; missing first snapshots leave existing copy untouched and fail the health check. Newest YouTube Search and Streaming Indian Filter have no store listings or release assets; do not invent counts.

- Chrome user badges use `/badges/users/v1/<encoded-label>.svg` on apoorvdarshan.com, with a `users` label; never restore Shields URLs. The Worker serves these independently, just like download tiles. New count URLs avoid reusing a previously broken image URL.

- Own projects (`apoorvdarshan/*`) show stars only at **5 or more** across README, site and resume. Keep exact counts in the audit snapshot even when hidden. External OSS contribution star display and descending sorting stay unchanged. The updater must preserve this threshold on every refresh.
