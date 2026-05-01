# AGENTS.md

This file provides guidance to coding agents when working with code in this repository.

## Repository Overview

This is a **GitHub profile README** repo (`apoorvdarshan/apoorvdarshan`). It contains a single `README.md` that renders on the GitHub profile page. All work involves editing this file.

## README Section Structure

The README has these sections in order:
1. **Header** — name, location, badges, tagline
2. **Projects** — combined active and legacy work (HTML format)
3. **Open Source Contributions** — merged PRs to other repos (HTML format with star badges)
4. **GitHub Activity** — contribution graph
5. **What I'm Doing** — current focus areas
6. **Writing** — blog, newsletter, articles
7. **Connect** — shields.io badge links to social profiles
8. **Recognition** — awards and achievements
9. **Philosophy** — quote + random facts

## Section Overflow (Show More)

- **Projects** and **Open Source Contributions** show only the first **15 items**
- Items beyond 10 go inside a `<details><summary>Show More</summary>...</details>` collapsible block
- Inside "Show More", entries use `<div>&bull; ...</div>` format (not markdown or `<li>`)

## Adding New Items — Placement Rules

| Section | Default position |
|---------|-----------------|
| Projects | **Ask user where to place** — no automatic top/bottom default |
| Open Source | **By star count** (descending). Fetch stars: `gh api repos/OWNER/REPO --jq '.stargazers_count'` |

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
