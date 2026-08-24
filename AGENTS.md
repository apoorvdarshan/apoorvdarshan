# AGENTS.md

This file provides guidance to coding agents when working with code in this repository.

## Repository Overview

This is primarily a **GitHub profile README** repo (`apoorvdarshan/apoorvdarshan`). `README.md` renders on the GitHub profile page, and most content work involves editing `README.md`.

## Cross-Repository Profile Synchronization

- Treat every GitHub profile content update as a synchronized profile update. Mirror relevant changes in `/Users/apoorvdarshan/profile` so `apoorvdarshan.com` reflects the same projects, open-source contributions, links, and profile facts.
- Mirror relevant project and open-source changes in `/Users/apoorvdarshan/rekisei/Apoorv_Darshan_Resume.tex`, recompile and visually verify the PDF without opening a viewer, and sync the verified source and PDF to `~/Documents/`. Follow the resume repository's `AGENTS.md` and `CLAUDE.md`.
- Keep the private, gitignored resume source and PDF out of this public profile repository. Commit and push each affected tracked repository separately.
- When a profile update changes resume data, follow the resume instructions for updating LinkedIn's saved resume without asking for separate permission. Do not open foreground apps unexpectedly.

## README Section Structure

The README has these sections in order:
1. **Header** — name, location, badges, tagline
2. **Apps** — mobile apps (HTML format, same `<li>` patterns as Projects)
3. **Games** — games (HTML format, same `<li>` patterns as Projects)
4. **Chrome Extensions** — browser extensions (HTML format, same `<li>` patterns as Projects)
5. **Projects** — everything else: web apps, tools, bots, experiments (HTML format)
6. **Open Source Contributions** — merged PRs to other repos (HTML format with star badges)
7. **GitHub Activity** — contribution graph
8. **What I'm Doing** — current focus areas
9. **Connect** — shields.io badge links to social profiles
10. **Recognition** — awards and achievements
11. **Philosophy** — quote + random facts

## Section Overflow (Show More)

- **Apps**, **Games**, **Chrome Extensions**, **Projects**, and **Open Source Contributions** show only the first **15 items**
- Items beyond 15 go inside a `<details><summary>Show More</summary>...</details>` collapsible block
- Inside "Show More", entries use `<div>&bull; ...</div>` format (not markdown or `<li>`)

## Adding New Items — Placement Rules

| Section | Default position |
|---------|-----------------|
| Apps | **Ask user where to place** — no automatic top/bottom default |
| Games | **Ask user where to place** — no automatic top/bottom default |
| Chrome Extensions | **Ask user where to place** — no automatic top/bottom default |
| Projects | **Ask user where to place** — no automatic top/bottom default |
| Open Source | **By star count** (descending). Fetch stars: `gh api repos/OWNER/REPO --jq '.stargazers_count'` |

## Profile Update Star Audit

- Whenever the user says **update profile** (or asks for any GitHub profile content change), audit every GitHub-hosted entry in **Apps**, **Games**, **Chrome Extensions**, and **Projects** — not only the item being edited.
- Fetch each repository's current star count with `gh api repos/OWNER/REPO --jq '.stargazers_count'`.
- If the count is **greater than 0**, ensure the entry includes this live badge immediately after the linked project name:
  ```html
  <img alt="Stars" src="https://github-star-badge.apoorvdarshan.com/api/stars?repo=OWNER/REPO&amp;v=3">
  ```
- If the count is **0**, do not show a star badge; remove any stale badge already present.
- Closed-source and non-GitHub entries do not receive GitHub star badges.
- Before finishing, verify that every positive-star work entry has a badge and every zero-star work entry has none.

## Description Length

- Descriptions in **Apps**, **Games**, **Chrome Extensions**, **Projects**, and **Open Source Contributions** must be one rendered line maximum at normal GitHub desktop width
- If a description wraps, shorten it rather than preserving extra detail

## Formatting Patterns

### Projects (HTML, inside `<ul>`)
Top 15 as `<li>`, rest inside `<details>` as `<div>&bull; ...`:
```html
<li>EMOJI <strong><a href="URL">name</a></strong> - description</li>
<li>EMOJI <strong><a href="URL">name</a></strong> <em>(closed source)</em> - description</li>
<li>EMOJI <strong>name</strong> <em>(closed source)</em> - description</li>  <!-- private, no link -->
<li>EMOJI <strong><a href="URL">name</a></strong> <img alt="Stars" src="..."> - description</li>  <!-- with star badge -->
```

### Open Source Contributions (HTML, inside `<ul>`)
Top 15 as `<li>`, rest inside `<details>` as `<div>&bull; ...`:
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
- No co-author lines in commits
- Keep commit messages concise (one line)
- Keep `AGENTS.md` and `CLAUDE.md` parallel: when changing repository guidance, update both files together so their instructions stay in sync
