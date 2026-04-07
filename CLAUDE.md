# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a **GitHub profile README** repo (`apoorvdarshan/apoorvdarshan`). It contains a single `README.md` that renders on the GitHub profile page. All work involves editing this file.

## README Section Structure

The README has these sections in order:
1. **Header** — name, location, badges, tagline
2. **Current Projects** — active work (markdown format)
3. **Open Source Contributions** — merged PRs to other repos (HTML format with star badges)
4. **Legacy Work** — older/archived projects (HTML format)
5. **GitHub Activity** — contribution graph
6. **What I'm Doing** — current focus areas
7. **Writing** — blog, newsletter, articles
8. **Connect** — shields.io badge links to social profiles
9. **Recognition** — awards and achievements
10. **Philosophy** — quote + random facts

## Section Overflow (Show More)

- **Current Projects**, **Open Source Contributions**, and **Legacy Work** show only the first **10 items**
- Items beyond 10 go inside a `<details><summary>Show More</summary>...</details>` collapsible block
- Inside "Show More", entries use `<div>&bull; ...</div>` format (not markdown or `<li>`)

## Adding New Items — Placement Rules

| Section | Default position | Exception |
|---------|-----------------|-----------|
| Current Projects | **Top** of list | Only if user specifies otherwise |
| Legacy Work | **Top** of list | Only if user specifies otherwise |
| Open Source | **By star count** (descending) | Fetch stars: `gh api repos/OWNER/REPO --jq '.stargazers_count'` |

## Formatting Patterns

### Current Projects (markdown)
```
- EMOJI **[name](github-url)** - short description
- EMOJI **[name](url)** / **[name-web](url)** - description (for app + website combos)
- EMOJI **[name](url)** *(closed source)* - description (for private repos)
```

### Open Source Contributions (HTML, inside `<ul>`)
Top 10 as `<li>`, rest inside `<details>` as `<div>&bull; ...`:
```html
<li>EMOJI <strong><a href="PR-URL">repo-name</a></strong> <img alt="Stars" src="https://img.shields.io/github/stars/OWNER/REPO?v=2&amp;style=flat-square&amp;label=%E2%98%85&amp;color=0D7C37"> - description</li>
```
For multiple PRs to same repo, link to author's PR list and say "N merged PRs: ...".

### Legacy Work (HTML, inside `<ul>`)
Same `<li>` / `<div>&bull;` pattern as Open Source but without star badges.

### Connect Section (shields.io badges)
```
[![Name](https://img.shields.io/badge/-Name-COLOR?style=flat-square&logo=LOGO&logoColor=white)](URL)
```

## Commit Rules

- Always commit and push after every change — do not batch or wait to be asked
- No co-author lines in commits
- Keep commit messages concise (one line)
