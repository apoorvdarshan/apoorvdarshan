# CLAUDE.md

## README Structure Rules

### Section Overflow (Show More)
- **Current Projects**, **Open Source Contributions**, and **Legacy Work** sections show only the first **10 items** visibly
- Items beyond 10 go inside a `<details><summary>Show More</summary>...</details>` collapsible section
- The "Show More" section uses HTML `<div>` elements with `&bull;` prefix, not markdown list items

### Adding New Items
- **Current Projects**: Always add to the **top** of the list
- **Legacy Work**: Always add to the **top** of the list
- **Open Source Contributions**: Add in **star count order** (descending) — fetch the repo's star count and place it in the correct position
- Only place items elsewhere if the user explicitly specifies a position

### Open Source Star Ordering
- All open source entries are ordered by the parent repo's GitHub star count, highest first
- When adding a new entry, use `gh api repos/OWNER/REPO --jq '.stargazers_count'` to get the count
- Place the entry between repos with higher and lower star counts

### Formatting Patterns
- Current Projects use markdown: `- EMOJI **[name](url)** - description`
- Combined repos use: `- EMOJI **[name](url)** / **[name-web](url)** - description`
- Closed source projects add: `*(closed source)*` after the link
- Open Source and Legacy use HTML `<li>` format inside `<ul>` tags
- Open Source entries include a shields.io star badge after the repo name

### Commit Rules
- Always commit and push after changes — no co-author line
