# Unified-repository automation

Public root: `apoorvdarshan/apoorvdarshan`; run these scripts from `website/`.
The root README and profile-automation snapshots are used locally. The private
resume checkout remains separate. The Mac LaunchAgent points to this directory;
Documents source/PDF symlinks resolve directly to the private checkout. The old
profile and rekisei checkouts are no longer used.

# Automatic profile, contribution, and resume refresh

`Refresh profile and resume` runs at minute 17 every six hours (UTC), and supports manual dispatch. Scheduled Actions can start later than their cron time. It commits directly to `main`; there is no review PR or AI service.

The workflow lives in `apoorvdarshan/apoorvdarshan/.github/workflows/refresh-profile.yml`, where the existing Cloudflare deployment secrets are configured. Its scripts live in this website repository. It:

1. Checks out this unified public repository with its workflow token and `apoorvdarshan/profile-resume-private` with its repository-scoped deploy key.
2. Paginates **all** merged PRs for **apoorvdarshan**, keeping only public repositories owned by other accounts. PR authors, merge timestamps, and API totals are verified. It refuses incomplete responses or loss of previously verified PRs.
3. Saves all verified PR titles/links and current star counts to `profile-automation/contributions.json` in the README repository. The README remains the source of emoji, linked attribution, and personal-project descriptions. Authored-commit entries without matching authored PRs remain intact. Historical editorial counts above API counts are preserved and called out in the run summary.
4. Adds new contribution repositories with escaped, shortened PR titles. Repositories with multiple verified merges always get a current description from the newest distinct PR titles, ordered by merge time (PR number breaks ties). Uses three titles if they fit, otherwise two shortened titles; the full cumulative count and linked attribution share a 90-character description budget. Repeated titles are shown once. Existing single-PR descriptions stay until another merge arrives. Existing multi-PR descriptions are refreshed on the first run of this policy, and later runs also pick up title corrections. This is deterministic title selection/shortening, with no AI or significance ranking. Sorts OSS by stars, with repository name as a stable tie-breaker; shows ten entries and folds the rest into Show More. Own project order is preserved; their star badges are refreshed, and configured iOS, Android and npm download badges are refreshed daily as described below.
5. Mirrors generated OSS descriptions into the resume along with links, counts, ordering, and stars. Preserves the resume header, other sections, and existing single-PR/commit-credit descriptions. Missing OSS entries are added. Project star counts are refreshed in place.
6. Builds changed private LaTeX with pinned Tectonic 0.17.0. Checks page count, text bounds, required entries, and renders pages before copying the PDF to `public/Apoorv_Darshan_Resume.pdf`. No private source or page artifacts are uploaded publicly. Unchanged source reuses the validated PDF.
7. Builds the website from the exact local README and verified star snapshot, avoiding cached GitHub README/badge data.
8. Commits only changed managed files in each repository, with **Apoorv Darshan as author and committer** (`90602809+apoorvdarshan@users.noreply.github.com`) and **github-actions[bot] as co-author**, then deploys the built site with Wrangler. A dedicated SSH signing key registered on Apoorv's account gives automated commits the Verified badge, including with vigilant mode enabled. Signing failures produce warnings and fall back to unsigned commits, as requested; no branch rule blocks unsigned pushes. Pushes never force-update branches. Other failures stop the run; subsequent runs retry deployment even when there are no new commits.

The existing `/resume` and `/Apoorv_Darshan_Resume.pdf` URLs continue serving the updated PDF. The `.tex`, PDF, and their build manifest also live in the **private** resume repository. The legacy `.github/resume-pdf-parts` files are not used by the site or refresh job.

## Credentials

- `GITHUB_TOKEN`: public GitHub reads and commits to the README repository.
- `PROFILE_SITE_DEPLOY_KEY`: write access only to `apoorvdarshan/apoorvdarshan`.
- `RESUME_SOURCE_DEPLOY_KEY`: write access only to the private resume repository.
- `PROFILE_COMMIT_SIGNING_KEY`: dedicated SSH private signing key, registered only for signing on Apoorv's account (not authentication). The corresponding public key is pinned in the README repo's `.github/profile-signing.pub`. The runner writes it with private permissions only for the commit step and removes it afterward, including on failure. To rotate it, register a new signing public key, replace the secret and pinned public key, and confirm GitHub verifies the next automated commit before retiring the old key.
- `ASC_REPORTS_KEY_ID`, `ASC_REPORTS_ISSUER_ID`, `ASC_REPORTS_PRIVATE_KEY`: the dedicated **Profile Download Reporting** ASC team key, with Sales and Reports access. It reads reports for all six configured iOS apps. Only this reporting key is stored here; existing app publishing, notarization and RevenueCat keys remain separate. The issuer is shared with other team keys.
- Existing `CLOUDFLARE_API_KEY` and `CLOUDFLARE_EMAIL`: site deployment.

Only scheduled/manual runs execute this workflow. Secrets are not exposed to pull-request code. GitHub-hosted runners do the cloud work, so the Mac can be off. GitHub's normal Actions/account limits still apply.

## Mac copies and manual resume edits

`sync-local-resume.py` pulls the private repo and verifies the source/PDF hashes. The two `~/Documents/Apoorv_Darshan_Resume.*` files are symlinks to the private checkout, so they follow each pull immediately. A user LaunchAgent (`com.apoorvdarshan.profile-resume-sync`) runs at login and every six hours while the Mac is awake (`StartInterval = 21600`). The Mac initiates the GitHub pull; the cloud never connects to the Mac or sends it a command. The PDF is built in the cloud, so this local job only downloads and verifies the files. It creates dated backups before replacing files and refuses to overwrite files changed locally since the last sync. Backups live in `~/.local/share/profile-automation/resume-backups`, also linked from `~/Documents/resume-backups`. This keeps background access out of macOS's protected Documents directory without changing privacy permissions. Editing a Documents source link edits the private checkout; the dirty-check then pauses automatic pulls.

For a manual resume edit, edit the private checkout, run `build-resume.py` with `PROFILE_RESUME_PATH` pointing at its LaTeX file, inspect the PDF, and commit/push the source, PDF and build manifest there. Commit the verified public PDF in `website/public/` and deploy this repository. Preserve Documents symlinks. The local sync never publishes edits automatically and refuses to pull over a dirty private checkout.

## Local verification

```sh
node --test scripts/automation/*.test.mjs
PROFILE_README_PATH=/path/to/README.md PROFILE_RESUME_PATH=/private/path/Apoorv_Darshan_Resume.tex node scripts/automation/update-profile.mjs
PROFILE_RESUME_PATH=/private/path/Apoorv_Darshan_Resume.tex python3 scripts/automation/build-resume.py
PROFILE_README_PATH=/path/to/README.md PROFILE_STARS_PATH=/path/to/profile-automation/contributions.json npm run build
```

All API validation completes before source files are written. There is no automatic deletion of contributions and no automatic discovery of new personal projects. New personal projects still go at the top of their selected category when requested.

## Daily App Store downloads

`ios_downloads.py` checks Apple once per UTC day during the first successful six-hour refresh (normally the 00:17 UTC run / 05:47 IST). Later runs reuse that day's verified totals. Failed checks retry on the next run. Manual dispatch can set `refresh_ios_downloads` to force another check.

The managed apps/links are in `ios-downloads.json`: Fud AI, Verceltics, Scowld, Quit All, PCM Notes (iitjee), and ABYSM. Adding an app requires an explicit config entry, an existing README/resume download badge, and an Admin-created ONGOING report request. The daily reporting key cannot create requests or publish app releases.

The updater reads **App Downloads Standard**, DAILY instances only, paginates all API lists, verifies every compressed segment's size/checksum, and aggregates all rows/segments within each instance. For an event date repeated across instances, the latest `processingDate` replaces the entire date partition; it never sums overlapping instances or deduplicates legitimate identical rows. Badges use **lifetime first-time downloads**, excluding redownloads, restores and updates. Exact first-time counts, redownloads, and first-time + redownload totals are retained privately. Apple completes this report after two days. Each app's cutoff is the latest observed report processing date minus two days, capped at UTC today minus two days; a previously verified later cutoff is retained. Delayed reports never promote a partially reported day. Quiet apps may keep an older data-through date until another report arrives. The private snapshot and run summary show each app's date.

`ios-download-history.json` in **private** `profile-resume-private` stores per-day aggregates, processed-instance IDs, and the complete daily lifetime history verified against the App Store Connect Analytics UI on 2026-10-11 (through 2026-10-09). This survives Apple's 35-day report retention and runner/cache resets. Fresh ONE_TIME_SNAPSHOT requests were made on 2026-10-11 for all six apps; once generated, the job automatically imports the full report history and reconciles the bootstrapped UI history. It validates the snapshot covers the known app history. The checked daily totals are saved as private `ios-downloads.json`. Raw reports, signed download URLs and credentials are never committed.

Fud AI adds **the latest verified Android first-time install total** from private `android-downloads.json`; `android_package` in the iOS config maps the two platforms. The Android and iOS reporting dates are retained separately. All other configured badges use iOS alone. Milestones round down (35 → 30+, 188 → 100+, 1,358 → 1K+). Project descriptions and order remain curated; the final distribution step refreshes mapped release downloads and Chrome users.

The exact same labels update the GitHub README and private resume source before the existing PDF build/site sync. Both public PDF URLs therefore follow automatically. The Mac's existing six-hour pull brings the private history, source and PDF down; Documents resume symlinks follow. `~/Documents/asc_downloads.json` is a symlink to the current private aggregate file after its original snapshot was archived; read the current `apps` mapping rather than the legacy array format.

Managed mobile and npm README badges use `https://apoorvdarshan.com/badges/downloads/v1/<encoded-label>.svg`. The Cloudflare Worker renders the same maroon tile directly, without calling Shields or Apple when an image loads. Each milestone has its own immutable URL, so count changes bypass older image caches. GitHub still proxies external images through Camo. The website parses the unchanged `Downloads:` alt text and the resume uses text, so neither depends on badge images. Other curated badges remain unchanged.

On an API, schema, checksum, or pagination failure, no download outputs are written. The workflow warns and continues the other profile updates using previous verified download badges. A gap longer than 32 days requires a fresh full historical snapshot so missing report history is never silently treated as zero. Use an Admin key **locally** to POST `/v1/analyticsReportRequests` with `accessType: ONE_TIME_SNAPSHOT` for the affected app; do not grant Admin to the scheduled reporting key. The next successful run imports the generated history and recovers automatically. ONGOING requests stopped for inactivity also require Admin reactivation. Apple may take time to prepare new reports.

Local check (keep credentials in the environment or a private key file):

```sh
ASC_REPORTS_KEY_ID=... ASC_REPORTS_ISSUER_ID=... \
ASC_REPORTS_PRIVATE_KEY_PATH=/private/path/AuthKey.p8 \
PROFILE_README_PATH=/path/to/README.md \
PROFILE_RESUME_PATH=/private/path/Apoorv_Darshan_Resume.tex \
python3 scripts/automation/ios_downloads.py
```

Apple references: [Analytics Reports](https://developer.apple.com/documentation/analytics-reports), [App Downloads](https://developer.apple.com/documentation/analytics-reports/app-download), [Data Completeness and Corrections](https://developer.apple.com/documentation/analytics-reports/data-completeness-corrections).

## Daily npm downloads

`npm_downloads.py` refreshes the five explicitly configured packages in `npm-downloads.json` once per UTC day during the six-hour workflow. No npm token, npmrc, publishing permission, or 2FA bypass is used. It reads the public registry metadata and public download-count API. `refresh_npm_downloads` in manual dispatch (or local `NPM_DOWNLOADS_FORCE=true`) forces a fresh check.

The metric is **lifetime npm package downloads**, across all versions from each package's creation date through the latest completed date available for all five packages. Downloads include repeat installs and automated/CI requests; they are not unique users, GitHub release downloads, or Homebrew installs. This step writes the npm subtotal; the final distribution step adds configured GitHub asset events and publishes a combined badge with the same floor rounding. Fud AI and extension user counts are managed separately.

Each daily refresh verifies the exact package name, maintainer, repository, and pinned creation date. Scoped packages are queried individually. Full history is fetched again in non-overlapping inclusive windows of at most 365 days, below npm's 18-month request limit. Responses must cover the exact requested interval with a nonnegative integer count. This incorporates corrected statistics without incrementally double-counting downloads. Packages created before npm's available history (2015-01-10) require an explicit historical policy before being added.

The public audit snapshot is `profile-automation/npm-downloads.json` in the profile README repository. It records exact totals, dates, milestone labels, configuration fingerprint, and source URLs for every interval. Normal later runs that day reuse that snapshot. Config changes force a refresh. API/identity/schema failures leave the previous npm counts and snapshot intact, show a workflow warning, and retry next run while other updates continue.

The same run updates the five existing README and private resume labels, rebuilds the PDF, syncs the website, signs commits, and deploys. Badges use the existing Cloudflare SVG route. Both resume URLs and the Mac's six-hour pull follow the same existing process.

Local check: `PROFILE_README_PATH=/path/to/README.md PROFILE_RESUME_PATH=/private/path/resume.tex python3 scripts/automation/npm_downloads.py`.

Source: [npm download-count API](https://github.com/npm/registry/blob/main/docs/download-counts.md).

## Daily Android downloads and future apps

`android_downloads.py` checks the account's private Google Play Cloud Storage reports once per UTC day, with `refresh_android_downloads` / `PLAY_DOWNLOADS_FORCE=true` for a forced refresh. Config is `android-downloads.json`; the exact snapshot and report provenance stay in private `profile-resume-private/android-downloads.json`. All existing and future packages with overview reports are discovered privately. An empty report for a new app is skipped until it has data. Discovery never creates public project entries, counts a test app toward an iOS badge, or assumes a new package has complete lifetime history.

For public counts, explicitly add the package, verified first report date and metric validation to the Android config, then map `android_package` on its iOS entry. Verify production availability and compare the exported metric with Play Console **New user acquisitions > Cumulative** before publication. Verceltics Android is currently in closed testing and has no published Android count; its existing badge remains iOS-only. A future Android-only public project needs an explicit README/resume mapping as well, without another credential.

For Fud AI, sum **Daily User Installs** across one overview row per date from 2026-04-25. This matches the Console's cumulative new users: **2,579 through 2026-10-07**, verified on 2026-10-11. The legacy `Total User Installs` column is zero in these reports and is never used. Install events (including repeat installs) are recorded separately and never added to the first-time badge. Active devices, updates, and multiple country/device/app-version dimensions are never added. Do not assume an unvalidated new package's exported metric is first-time users merely because its report exists.

Every daily check refetches all monthly overview files, pins object generations, verifies stored size and MD5, decodes gzip/UTF-16 or UTF-8, validates package/month/dates/counts, and replaces the full aggregate. Daily coverage must be continuous from the configured first date through the latest available date. Missing apps, history gaps, backward reporting dates or malformed responses preserve the previous snapshot and cause a warning/retry. Corrected counts can decrease without being inflated by the prior snapshot. Google posts reports with a typical 3–7 day lag; data over eight days old is explicitly warned about. The data-through date is never relabeled as the check date.

`mobile_downloads.py` combines the latest successful platform snapshots after both checks. Fresh Android data can update the badge even if ASC fails, and fresh ASC data can use the previous Android snapshot if Google fails. iOS redownloads are never included. The README, site, private resume and both public PDF URLs share the same floor-rounded combined label. An unchanged milestone reuses the existing verified PDF. The Mac retains its existing six-hour pull schedule.

### Read-only authentication

- Existing Cloud project: `fudai-play-publisher-2026` (945540252044).
- Dedicated service account: `profile-reporting@fudai-play-publisher-2026.iam.gserviceaccount.com` (**Profile Download Reporting**).
- Play Console account permission: **View app information and download bulk reports (read-only)**, including future apps; Google also selects its dependent read-only app-quality permission. No publishing, financial or order-management permissions were granted.
- GitHub OIDC provider: `projects/945540252044/locations/global/workloadIdentityPools/profile-automation/providers/github`. Its condition requires repository ID `985987367`, owner ID `90602809`, `refs/heads/main`, and the exact `apoorvdarshan/apoorvdarshan/.github/workflows/refresh-profile.yml@refs/heads/main` workflow ref. The repository principal alone receives `roles/iam.workloadIdentityUser` on the reporting service account.
- Pinned `google-github-actions/auth` creates a short-lived OAuth access token scoped to `https://www.googleapis.com/auth/devstorage.read_only`. No JSON key, refresh token, credentials file or additional Actions secret is stored. The account's existing publishing service account and JSON key remain separate.
- Enabled IAM, IAM Credentials and Security Token Service APIs in this project; the Mac's default gcloud project stays unchanged. No bucket ACL changes or project-wide storage roles are needed: Play Console controls access to its report bucket.

Local checks can pass a short-lived owner or appropriately authorized reporting token as `PLAY_REPORTS_ACCESS_TOKEN` with `PROFILE_RESUME_PATH`; never print it or commit it. The daily cache needs no token, but is tied to the reporting identity: an owner-bootstrapped snapshot cannot suppress a failed cloud-identity retry later the same day. To revoke cloud access, remove the reporting user in Play Console or disable the WIF provider. To extend this to another repository, add a separate narrowly scoped identity policy deliberately; the existing trust does not cover arbitrary repositories.

References: [Google Play monthly reports and service-account access](https://support.google.com/googleplay/android-developer/answer/6135870), [metric definitions](https://support.google.com/googleplay/android-developer/answer/139628), [GitHub Google authentication](https://github.com/google-github-actions/auth).

### Initial reporting-account access status (2026-10-11)

The first snapshot was fetched with the existing owner's authorized gcloud login and matched the Play Console UI. GitHub OIDC successfully authenticated as the dedicated service account, but Google still denied `storage.objects.list` and `storage.objects.get` on the Play-managed report bucket during setup. Its global read-only Play Console permissions were saved and the user is Active. This may be permission propagation; do not claim cloud report fetching has succeeded until a run skips the Google fallback and records the service-account email in `reporting_identity`.

The workflow retries every six hours until a successful daily check. A snapshot fetched by the owner is not considered a successful service-account check. If the error persists after permission propagation, recheck global Play Console access and contact Play support with the developer account, service-account email, bucket and redacted failing request details. Do not grant publishing/financial/admin permissions or store the existing publishing key as a workaround. Temporary owner impersonation grants used to diagnose setup were removed; the permanent service-account IAM policy contains only the narrowly scoped GitHub workload-identity grant.

A follow-up probe confirmed that adding the email identity scope does not resolve the denial. A [matching issue in Google's client repository](https://github.com/googleapis/google-cloud-python/issues/17521) reports access starting after about 24 hours; this is evidence for propagation delay, not a guaranteed Google SLA. Leave the correctly saved permissions in place while scheduled checks retry.

### Failure and recovery behavior

- Android retries HTTP 429/5xx, timeouts, interrupted response bodies and connection failures up to four total attempts. Backoff starts at 2, 4 and 8 seconds; a valid `Retry-After` can extend the wait, capped at 60 seconds per retry. HTTP 401/403 fails immediately for that run, since retrying a permission problem seconds later is unhelpful.
- A failed fetch or validation never replaces the saved count with zero, marks it fresh, or writes a partial history. The last verified snapshot stays intact; the next six-hour run retries. Once access recovers, the normal fetch replaces the snapshot automatically. A valid reporting response showing no new installs is handled separately from a failed request.
- Android, ASC and npm fetch failures allow other valid updates, signed commits, the resume build and deployment to proceed with the previous verified counts. **After publishing**, a final health step marks the workflow failed and adds an explicit summary if any download source or Play authentication failed. A fallback run must not appear entirely green. Earlier build/deployment failures remain visible too; retained data does not imply a successful deployment.
- Reporting dates stay attached to the private snapshots; old totals are never described as freshly fetched. No switch to public Play Store milestone estimates, new API key, publishing key or owner credential happens automatically.


## Public release downloads, Homebrew and Chrome users

`distribution_counts.py` runs daily after mobile/npm composition. Configuration is
`distribution-counts.json`; audit snapshots are committed to the README repository
at `profile-automation/distribution-counts.json`. `DISTRIBUTION_FORCE=true` bypasses
the daily cache. The GitHub token is sent only to api.github.com; store pages need
no credentials. Chrome requests fix `hl=en` and parse only the listing header.
Only Country Filter and Streaming Auto-Pause are published; no counts are invented
for local-only extensions. Publicly readable unlisted pages can also be configured.
Restricted/private listings are not accessed with personal cookies.

Six repositories have stable release assets: Fud AI (APK only), LithosAI Bar,
DesktopWorm, Browser Cookie Bridge, Hash Harbor, and TetherShot. Both releases and
assets are paginated. Allowlisted distributables exclude signatures/checksums,
source auto-archives, draft/prerelease assets and publishing-only Android AAB files.
Counts cover assets still available on GitHub; deleted assets cannot be recovered.

For mapped projects, npm downloads plus GitHub asset requests form a **download
event total**, not unique users or successful installs. A single npm installation
can fetch a release binary too (for example Hash Harbor); both are file downloads.
Fud AI adds APK download events to its independently verified iOS + Android
first-time store subtotal. The private store snapshots keep their original metric.
Chrome users are never added to downloads and may decrease.

TetherShot and Browser Cookie Bridge are in `apoorvdarshan/homebrew-tap`. Their
casks fetch the same GitHub release DMGs, so those fetches are already represented
in GitHub counts. There is no extra Homebrew total to add. Homebrew analytics
are optional reporting over rolling windows, not a complete lifetime counter:
https://docs.brew.sh/Analytics . Crossposter's README mentions brew, but the tap
currently has no corresponding formula; do not treat that command as proof of
an available package or invent its usage.

Sources refresh independently. On failure, retain that source's last verified
snapshot (including its original date), compose against current saved subtotals,
and let other sources publish. A first-time failure leaves that project's badge
alone. The workflow publishes valid changes, then fails its final health check.
This avoids silently green stale-source runs. No source count is clamped upwards.
