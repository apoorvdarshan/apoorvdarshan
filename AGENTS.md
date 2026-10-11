# AGENTS.md

This file provides guidance to coding agents when working with code in this repository.

## Repository Overview

This is primarily a **GitHub profile README** repo (`apoorvdarshan/apoorvdarshan`). `README.md` renders on the GitHub profile page, and most content work involves editing `README.md`.

## Cross-Repository Profile Synchronization

- Treat every GitHub profile content update as a synchronized profile update. Mirror relevant changes in `/Users/apoorvdarshan/profile` so `apoorvdarshan.com` reflects the same projects, open-source contributions, links, and profile facts.
- Mirror relevant project and open-source changes in `/Users/apoorvdarshan/rekisei/Apoorv_Darshan_Resume.tex`, recompile and visually verify the PDF without opening a viewer, and sync the verified source and PDF to `~/Documents/`. Follow the resume repository's `AGENTS.md`.

- After that Documents sync, also refresh `/Users/apoorvdarshan/profile/public/Apoorv_Darshan_Resume.pdf` from the compiled resume, then commit/push/deploy `profile` so https://apoorvdarshan.com/resume stays current (PDF still downloads as `Apoorv_Darshan_Resume.pdf`). Keep this README's **Resume** section and Connect **Resume** badge pointing at that short URL. Never put the resume PDF binary in this repository.
- Keep the private, gitignored resume source and PDF out of this public profile repository. The public share link is `https://apoorvdarshan.com/resume` (hosted on the profile site; file name remains `Apoorv_Darshan_Resume.pdf`). Commit and push each affected tracked repository separately.
## README Section Structure

The README has these sections in order:
1. **Header** — name, location, badges, tagline
2. **Mobile Apps** — Android/iOS apps (HTML format, same `<li>` patterns as Projects)
3. **Games** — games (HTML format, same `<li>` patterns as Projects)
4. **Chrome Extensions** — browser extensions (HTML format, same `<li>` patterns as Projects)
5. **AI & Agents** — AI/agent tooling, MCP servers, skills, automation (HTML `<ul>` of `<li>`)
6. **Apps & Utilities** — native/desktop apps and utilities (HTML `<ul>` of `<li>`)
7. **Web Apps & Tools** — web apps and tools (HTML `<ul>` of `<li>`)
8. **Creative, 3D & Vision** — Blender/3D, gesture and vision experiments (HTML `<ul>` of `<li>`)
9. **Experiments & Fun** — toy UIs, clones, landing pages, games-lite (HTML `<ul>` of `<li>`)
10. **Open Source Contributions** — merged PRs to other repos (HTML format with star badges)
11. **GitHub Activity** — contribution graph
12. **My Agent Setup** — harnesses, workspace, tools, and rules
13. **What I Use** — Hardware + Software shields.io logo tiles (Connect-style); syncs to site `uses` (GitHub + site only — **not** the resume)

14. **Resume** — shields.io View/Download badges + Connect Resume badge → https://apoorvdarshan.com/resume
15. **Connect** — shields.io badge links to social profiles
16. **Recognition** — awards and achievements
17. **Philosophy** — quote + random facts

The five AI/Apps/Web/Creative/Experiments headings are top-level peers to **Mobile Apps**, **Games**, and **Chrome Extensions** — there is no longer a **Projects** heading.

## Section Overflow (Show More)

- **Mobile Apps**, **Games**, **Chrome Extensions**, **AI & Agents**, **Apps & Utilities**, **Web Apps & Tools**, **Creative, 3D & Vision**, **Experiments & Fun**, and **Open Source Contributions** show only the first **10 items**
- Items beyond 10 go inside a `<details><summary>Show More</summary>...</details>` collapsible block
- Inside "Show More", entries use `<div>&bull; ...</div>` format (not markdown or `<li>`)

## Adding New Items — Placement Rules

| Section | Default position |
|---------|-----------------|
| Mobile Apps / Games / Chrome Extensions / AI & Agents / Apps & Utilities / Web Apps & Tools / Creative, 3D & Vision / Experiments & Fun | **Top of the category** unless the user says otherwise. If no category is given, pick the best fit. |
| Open Source | **By star count** (descending). Fetch stars: `gh api repos/OWNER/REPO --jq '.stargazers_count'` |

When a new top item pushes a section past 10 `<li>` entries, move the last `<li>` into the top of its **Show More** block as a `<div>&bull; ...</div>`.

## Profile Update Star Audit

- Whenever the user says **update profile** (or asks for any GitHub profile content change), audit every GitHub-hosted entry in **Mobile Apps**, **Games**, **Chrome Extensions**, and the project sections (**AI & Agents**, **Apps & Utilities**, **Web Apps & Tools**, **Creative, 3D & Vision**, **Experiments & Fun**) — not only the item being edited.
- Fetch each repository's current star count with `gh api repos/OWNER/REPO --jq '.stargazers_count'`.
- If the count is **greater than 0**, ensure the entry includes this live badge immediately after the linked project name:
  ```html
  <img alt="Stars" src="https://github-star-badge.apoorvdarshan.com/api/stars?repo=OWNER/REPO&amp;v=3">
  ```
- If the count is **0**, do not show a star badge; remove any stale badge already present.
- Closed-source and non-GitHub entries do not receive GitHub star badges.
- Before finishing, verify that every positive-star work entry has a badge and every zero-star work entry has none.

## Download counts

- The current App Store Connect snapshot is private `~/profile-resume-private/ios-downloads.json`, also linked from `~/Documents/asc_downloads.json`. The cloud checker updates the six configured iOS apps once per UTC day; see `~/profile/scripts/automation/README.md`. Marketing download figures use **first-time** downloads only (not all-events totals that include auto/manual updates).
- **Fud AI** combines automated ASC first-time downloads with daily verified Google Play first-time installs from private `~/profile-resume-private/android-downloads.json`. Never substitute the all-events total. Exact download history stays in the private resume repo; public badges round down.
- In this README, show download counts as **maroon/blood-red flat-square tiles** beside the star badges (or right after `</strong>` / status if no stars). Automated iOS and npm badges use the site's Cloudflare Worker directly, e.g. `<img alt="Downloads: 9K+" src="https://apoorvdarshan.com/badges/downloads/v1/9K%2B.svg">` (encode `+` as `%2B`, color `8B1A1A`). Preserve these URLs in automation; other curated download badges may retain Shields URLs.
- Chrome Web Store extensions use **`Users: N`** Cloudflare-served maroon tiles (public user count, not installs), e.g. `<img alt="Users: 10+" src="https://apoorvdarshan.com/badges/users/v1/10%2B.svg">`. Only add when the extension is listed publicly. Under 10 users, show the exact count (e.g. `Users: 4`); at 10+ use a floor like `10+`.
- Do **not** keep trailing `(Nk+ downloads)` parentheticals in README descriptions once download badges exist — the profile site parses `alt="Downloads: …"` and renders plain `↓` text beside ★ (same look as `.star-count`, not a maroon pill).

- npm counts are lifetime package downloads from publication through the latest completed reporting date, including repeat/CI downloads. Five packages are explicitly mapped in `~/profile/scripts/automation/npm-downloads.json`; audit totals and source URLs live in `profile-automation/npm-downloads.json`. No npm key or 2FA bypass is needed. The final distribution step combines npm with configured stable GitHub asset download events; do not add Homebrew again when its cask uses those same assets.

- Android reporting uses a dedicated read-only service account with GitHub OIDC, covering current/future Play Console apps without per-app keys. Discovery remains private; explicitly validate lifetime history/metric and map a production app before publishing its count. Sum Daily User Installs once per overview date; never use the zero-filled legacy Total User Installs column or add device/country dimensions. Preserve old verified counts on failure. See `~/profile/scripts/automation/README.md`.

## Description Length

- Descriptions in **Mobile Apps**, **Games**, **Chrome Extensions**, the five project sections, and **Open Source Contributions** must stay on **one rendered line** at normal desktop width (GitHub README profile view and apoorvdarshan.com).
- Never let a description wrap to a second line on desktop. If it would wrap, **shorten the wording** (keep download shield badges when present).
- Prefer ~90 characters or fewer for the plain description text after the name/badge.
- On apoorvdarshan.com, desktop list rows also use CSS ellipsis as a backstop (`white-space: nowrap; overflow: hidden; text-overflow: ellipsis`) — still shorten the source text; do not rely on clipping alone.


## Formatting Patterns

### Project sections (HTML, inside `<ul>`)
**AI & Agents**, **Apps & Utilities**, **Web Apps & Tools**, **Creative, 3D & Vision**, and **Experiments & Fun** are top-level `##` sections (peers to Mobile Apps/Games/Chrome Extensions); first 10 as `<li>`, rest inside `<details>` as `<div>&bull; ...`:
```html
<li>EMOJI <strong><a href="URL">name</a></strong> - description</li>
<li>EMOJI <strong><a href="URL">name</a></strong> <em>(closed source)</em> - description</li>
<li>EMOJI <strong>name</strong> <em>(closed source)</em> - description</li>  <!-- private, no link -->
<li>EMOJI <strong><a href="URL">name</a></strong> <img alt="Stars" src="..."> - description</li>  <!-- with star badge -->
```

### Open Source Contributions (HTML, inside `<ul>`)
Top 10 as `<li>`, rest inside `<details>` as `<div>&bull; ...`:
```html
<li>EMOJI <strong><a href="PR-URL">repo-name</a></strong> <img alt="Stars" src="https://img.shields.io/github/stars/OWNER/REPO?v=2&amp;style=flat-square&amp;label=%E2%98%85&amp;color=0D7C37"> - description</li>
```
For multiple PRs to same repo, link to author's PR list and say "N merged PRs: ...".

### Connect Section (shields.io badges)
```
[![Name](https://img.shields.io/badge/-Name-COLOR?style=flat-square&logo=LOGO&logoColor=white)](URL)
```

## Commit Rules

- Always commit and push after every change — do not batch or wait to be asked
- No co-author lines in manual commits. Automatic profile refresh commits credit `github-actions[bot]` as co-author.
- Automatic profile refresh commits use Apoorv Darshan as both author and committer with `90602809+apoorvdarshan@users.noreply.github.com`, signed with the dedicated `PROFILE_COMMIT_SIGNING_KEY` Actions secret. The registered public key is `.github/profile-signing.pub`. Commit only when managed files change. Keep signing optional with visible workflow warnings if unavailable; the user does not want unsigned pushes blocked. Do not enable a required-signatures branch rule.
- Keep commit messages concise (one line)

## Merge checks and automation

- Check merged PRs only for `apoorvdarshan`. Use only this account for contribution discovery and future merge-check automation.
- `.github/workflows/refresh-profile.yml` runs every six hours or manually, commits directly without review PRs, and deploys the website after validation. Implementation lives in `apoorvdarshan/profile/scripts/automation/`; verified public data lives in `profile-automation/contributions.json` here.
- Preserve personal-project prose and authored-commit credits. New merged contribution repositories get shortened PR titles; multi-PR repositories refresh their descriptions from the newest 2–3 distinct PR titles (by merge time), shortened to the one-line limit. Keep total merged counts and linked attribution, and mirror generated descriptions into the resume. OSS sorts by current stars. Personal project order remains editorial. The six configured iOS download badges update daily from ASC, Fud AI Android from authenticated Google Play overview reports, and five npm package totals through the public npm API; configured Chrome Web Store user badges refresh daily.
- The same run updates/reorders resume OSS, rebuilds and validates its PDF, and publishes both existing resume URLs. Personal source/PDF/build manifest live in private `apoorvdarshan/profile-resume-private`; keep manual edits synchronized there so the next cloud run preserves them. The Mac sync keeps dated backups and refuses to overwrite local edits.

- `distribution_counts.py` runs after mobile/npm refresh: six explicitly mapped release repositories and two public Chrome store listings. GitHub assets are allowlisted (no checksums, signatures, AABs, drafts or prereleases), paginated and summed once per asset. Combined download events are not unique installs; Fud AI adds APK events to the unchanged first-time store subtotal. Homebrew casks for TetherShot and Browser Cookie Bridge use GitHub assets: never sum those installs again. Chrome users remain a separate metric and may decrease. Public audit: `profile-automation/distribution-counts.json`. Failed sources keep their previous verified snapshot; missing first snapshots leave existing copy untouched and fail the health check. Newest YouTube Search and Streaming Indian Filter have no store listings or release assets; do not invent counts.

- Chrome user badges use `/badges/users/v1/<encoded-label>.svg` on apoorvdarshan.com, with a `users` label; never restore Shields URLs. The Worker serves these independently, just like download tiles. New count URLs avoid reusing a previously broken image URL.
