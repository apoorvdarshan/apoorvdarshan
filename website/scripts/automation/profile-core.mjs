import { htmlText } from '../html-text.mjs'
import assert from 'node:assert/strict'

export const AUTHOR = 'apoorvdarshan'
const START = '### Open Source Contributions\n'
const END = '## GitHub Activity\n'
const STAR = /\s*<img alt="Stars" src="[^"]*">/g
export const escapeHtml = (s) => s.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;')
export const plain = htmlText
export function boundaries(readme) {
  assert.equal(readme.split(START).length, 2, 'Contribution heading must be unique')
  const start = readme.indexOf(START) + START.length
  const end = readme.indexOf(END, start)
  assert(end > start, 'Missing activity heading')
  return { start, end }
}
export function entries(readme) {
  const { start, end } = boundaries(readme)
  const rows = readme.slice(start, end).split('\n').flatMap((line) => {
    const match = line.match(/^\s*(?:<li>|<div>&bull;\s*)(.*<strong><a href="https:\/\/github\.com\/([^/]+\/[^/"?]+)[^"]*">[^<]+<\/a><\/strong>.*)(?:<\/li>|<\/div>)\s*$/)
    if (!match) return []
    return [{ repo: match[2], html: match[1] }]
  })
  assert(rows.length > 0, 'No contribution entries parsed')
  assert.equal(new Set(rows.map(x => x.repo.toLowerCase())).size, rows.length, 'Duplicate repository entry')
  return rows
}
export function starBadge(repo) {
  assert(/^[\w.-]+\/[\w.-]+$/.test(repo), 'Invalid repository name')
  return `<img alt="Stars" src="https://github-star-badge.apoorvdarshan.com/api/stars?repo=${repo}&amp;v=3">`
}
export function badge(html, repo, stars, minimum = 1) {
  const cleaned = html.replace(STAR, '')
  return stars >= minimum ? cleaned.replace('</strong>', `</strong> ${starBadge(repo)}`) : cleaned
}
function shorten(text, limit) {
  const chars = [...text]
  if (chars.length <= limit) return text
  const head = chars.slice(0, limit - 1).join('')
  const words = head.replace(/\s+\S*$/, '').trimEnd()
  return ([...words].length >= limit / 2 ? words : head.trimEnd()) + '…'
}
export function cleanTitle(title) {
  const cleaned = title.replace(/^(?:fix|feat|docs|chore|refactor|test|ci|build|perf|style)(?:\([^)]*\))?!?:\s*/i, '')
    .replace(/`([^`]+)`/g, '$1')
    .replace(new RegExp(`\\s+by @${AUTHOR}(?![\\w-])`, 'gi'), '')
    .replace(/\s+/g, ' ').trim()
  assert(cleaned, 'Empty PR title')
  return shorten(cleaned, 90)
}
export function recentDescription(prs, limit = 90) {
  assert(prs.length > 0, 'Cannot summarize an empty PR list')
  const prefix = prs.length > 1 ? `${prs.length} merged PRs: ` : ''
  const budget = limit - [...prefix].length
  assert(budget >= 20, 'Not enough room for a contribution description')
  const seen = new Set()
  let titles = [...prs].sort((a,b) => b.mergedAt.localeCompare(a.mergedAt) || b.number-a.number)
    .map(p => cleanTitle(p.title)).filter(title => {
      const key = title.toLowerCase()
      if (seen.has(key)) return false
      seen.add(key)
      return true
    }).slice(0,3)
  // Keep two readable titles instead of squeezing three long ones into fragments.
  if (titles.length === 3 && [...titles.join('; ')].length > budget) titles = titles.slice(0,2)
  if ([...titles.join('; ')].length <= budget) return prefix + titles.join('; ')
  const available = budget - (titles.length-1)*2
  const sizes = titles.map(() => Math.floor(available / titles.length))
  sizes[0] += available % titles.length
  // Give unused room from a short title to the longer one.
  for (let i=0; i<titles.length; i++) {
    const spare = sizes[i] - [...titles[i]].length
    if (spare > 0 && titles.length > 1) { sizes[i] -= spare; sizes[1-i] += spare }
  }
  return prefix + titles.map((title,i) => shorten(title,sizes[i])).join('; ')
}
export function verifiedPRs(pulls) {
  const unique = new Map()
  for (const p of pulls) {
    if (p.author?.login?.toLowerCase() !== AUTHOR || !p.mergedAt || p.repository.isPrivate || p.repository.owner.login.toLowerCase() === AUTHOR) continue
    const repo = p.repository.nameWithOwner
    assert.equal(p.url, `https://github.com/${repo}/pull/${p.number}`)
    assert(Number.isSafeInteger(p.number) && p.number > 0)
    unique.set(`${repo.toLowerCase()}#${p.number}`, { repo, number: p.number, title: p.title, url: p.url, mergedAt: p.mergedAt })
  }
  return [...unique.values()].sort((a, b) => a.repo.toLowerCase().localeCompare(b.repo.toLowerCase()) || a.number - b.number)
}
export function updateReadme(readme, pulls, stars, previous = null) {
  const rows = entries(readme)
  const verified = verifiedPRs(pulls)
  if (previous) {
    assert.equal(previous.author, AUTHOR)
    const ids = new Set(verified.map(p => `${p.repo.toLowerCase()}#${p.number}`))
    for (const p of previous.pullRequests) assert(ids.has(`${p.repo.toLowerCase()}#${p.number}`), `Previously verified PR missing: ${p.repo}#${p.number}; refusing partial API data`)
  }
  const groups = Map.groupBy(verified, p => p.repo.toLowerCase())
  const changes = []
  const warnings = []
  const byRepo = new Map(rows.map(r => [r.repo.toLowerCase(), r]))
  for (const [key, prs] of groups) {
    let row = byRepo.get(key)
    const isNew = !row
    if (!row) {
      const latest = [...prs].sort((a,b) => b.mergedAt.localeCompare(a.mergedAt) || b.number-a.number)[0]
      row = { repo: latest.repo, html: `🔧 <strong><a href="${latest.url}">${escapeHtml(latest.repo.split('/')[1])}</a></strong> - ${escapeHtml(cleanTitle(latest.title))}` }
      rows.push(row)
      changes.push(`Added ${row.repo}`)
    }
    const count = row.html.match(/ - (\d+) merged PRs?: /)
    if (count && Number(count[1]) > prs.length) {
      // Hand-maintained entries may include authored commits or historical credit.
      // Do not silently reduce or reinterpret them as verified authored PRs.
      warnings.push(`${row.repo}: preserved editorial count ${count[1]}; ${prs.length} authored merges verified`)
    } else if (isNew || prs.length > 1 || (previous && !previous.pullRequests.some(p => p.repo.toLowerCase() === key))) {
      const old = row.html
      const href = prs.length > 1 ? `https://github.com/${row.repo}/pulls?q=${encodeURIComponent(`is:pr is:merged author:${AUTHOR}`)}` : prs[0].url
      row.html = row.html.replace(/(<strong><a href=")[^"]+(">)/, `$1${href}$2`)
      const separator = row.html.indexOf(' - ')
      assert(separator >= 0, `Contribution description missing for ${row.repo}`)
      const attribution = row.html.slice(separator).match(/\s+\((?:by|merged by)\s+<a\b[\s\S]*\)$/)?.[0] ?? ''
      row.autoDescription = recentDescription(prs, 90 - [...plain(attribution)].length)
      row.html = row.html.slice(0,separator) + ' - ' + escapeHtml(row.autoDescription) + attribution
      if (row.html !== old) changes.push(`Updated ${row.repo}: ${prs.length} merged PRs and recent descriptions`)
    }
  }
  const getStars = (repo) => {
    const n = stars[repo.toLowerCase()]
    assert(Number.isSafeInteger(n) && n >= 0, `Missing/invalid stars for ${repo}`)
    return n
  }
  for (const row of rows) row.html = badge(row.html, row.repo, getStars(row.repo))
  rows.sort((a,b) => getStars(b.repo)-getStars(a.repo) || a.repo.toLowerCase().localeCompare(b.repo.toLowerCase()))
  const top = rows.slice(0,10).map(r => `  <li>${r.html}</li>`).join('\n')
  const more = rows.length > 10 ? `\n\n  <li>\n    <details>\n      <summary>Show More</summary>\n      <div>\n${rows.slice(10).map(r => `      <div>&bull; ${r.html}</div>`).join('\n')}\n      </div>\n    </details>\n  </li>` : ''
  const { start, end } = boundaries(readme)
  let prefix = readme.slice(0,start)
  prefix = prefix.split('\n').map(line => {
    const repo = line.match(/<strong><a href="https:\/\/github\.com\/([\w.-]+\/[\w.-]+)"/i)?.[1]
    if (!repo || /closed source/i.test(line)) return line
    return badge(line, repo, getStars(repo), repo.toLowerCase().startsWith(`${AUTHOR}/`) ? 5 : 1)
  }).join('\n')
  const updated = prefix + `\n<ul>\n${top}${more}\n</ul>\n\n` + readme.slice(end)
  // Nothing outside the contribution list or project star badges is managed.
  assert.equal(prefix.replace(STAR,''), readme.slice(0,start).replace(STAR,''))
  assert.equal(updated.slice(updated.indexOf(END)), readme.slice(end))
  assert.equal(entries(updated).length, rows.length)
  return { readme: updated, rows, changes, warnings, state: { version: 1, author: AUTHOR, pullRequests: verified, stars: Object.fromEntries(Object.entries(stars).sort(([a],[b]) => a.localeCompare(b))) } }
}
export function formatStars(n) {
  return n >= 10000 ? `${Math.round(n/1000)}k` : n >= 1000 ? `${Number((n/1000).toFixed(1))}k` : String(n)
}
export const texEscape = (s) => s.replace(/[\\{}$&#_%~^]/g, c => ({'\\':'\\textbackslash{}','{':'\\{','}':'\\}','$':'\\$','&':'\\&','#':'\\#','_':'\\_','%':'\\%','~':'\\textasciitilde{}','^':'\\textasciicircum{}'}[c]))
export function updateResume(source, rows, stars) {
  const heading = '\\section{Open Source Contributions}'
  assert.equal(source.split(heading).length, 2, 'Resume OSS heading must be unique')
  const listStart = source.indexOf('\\resumeSubHeadingListStart', source.indexOf(heading))
  assert(listStart > source.indexOf(heading), 'Resume OSS list start missing')
  const start = listStart + '\\resumeSubHeadingListStart'.length
  const end = source.indexOf('\\resumeSubHeadingListEnd', start)
  assert(source.includes(heading) && end > start, 'Resume OSS structure missing')
  const lineRepo = line => line.replace(/\\([_%#&])/g, '$1').match(/\\href\{https:\/\/github\.com\/([\w.-]+\/[\w.-]+)/)?.[1].toLowerCase()
  const existing = source.slice(start,end).split('\n').filter(l => l.includes('\\resumeProjectHeading'))
  const oldLines = new Map(existing.map(l => [lineRepo(l),l.trim()]))
  assert.equal(oldLines.size, existing.length, 'Duplicate resume contribution')
  for (const key of oldLines.keys()) assert(rows.some(r => r.repo.toLowerCase() === key), `Resume-only contribution ${key}; refusing removal`)
  const updateStar = (line, n, minimum = 1) => {
    if (n === undefined) return line
    const value = `${formatStars(n)} ${n === 1 ? 'star' : 'stars'}`
    if (n < minimum) return line.replace(/ \$\|\$ \{\\small \$\\bigstar\$ [\d.]+[kKmM]? stars? \$\|\$/, ' $|$ {\\small').replace(/ \$\|\$ \{\\small \$\\bigstar\$ [\d.]+[kKmM]? stars?\}/, '')
    if (line.includes('\\bigstar')) return line.replace(/(\\bigstar\$ )[\d.]+[kKmM]? stars?/, `$1${value}`)
    return line.replace(/(\\textbf\{\\href\{[^}]+\}\{[^}]+\}\})/, `$1 $|$ {\\small $\\bigstar$ ${value}}`)
  }
  const rendered = rows.map(row => {
    assert(Number.isSafeInteger(stars[row.repo.toLowerCase()]) && stars[row.repo.toLowerCase()] >= 0, `Missing/invalid resume stars for ${row.repo}`)
    const link = row.html.match(/<strong><a href="([^"]+)">([^<]+)<\/a>/)
    const name = plain(link[2])
    const count = row.html.match(/ - (\d+) merged PRs?: /)?.[1]
    let line = oldLines.get(row.repo.toLowerCase())
    if (!line) {
      const description = plain(row.html.slice(row.html.indexOf(' - ')+3))
      line = `\\resumeProjectHeading{\\textbf{\\href{${texEscape(plain(link[1]))}}{${texEscape(name)}}} \\textnormal{ -- ${texEscape(description)}}}{}`
    } else {
      line = line.replace(/\\href\{[^}]+\}/, () => `\\href{${texEscape(plain(link[1]))}}`)
      if (row.autoDescription) {
        const description = /(\\textnormal\{ -- )[\s\S]*(\}\}\{\})$/
        assert(description.test(line), `Resume description structure missing for ${row.repo}`)
        line = line.replace(description, (_,prefix,suffix) => prefix + texEscape(row.autoDescription) + suffix)
      } else if (count) line = / -- \d+ merged PRs?: /.test(line) ? line.replace(/ -- \d+ merged PRs?: /, ` -- ${count} merged PRs: `) : line.replace(' -- ', ` -- ${count} merged PRs: `)
    }
    return '      ' + updateStar(line, stars[row.repo.toLowerCase()])
  }).join('\n')
  const prefix = source.slice(0,start).split('\n').map(line => line.includes('\\resumeProjectHeading{') ? updateStar(line,stars[lineRepo(line)], lineRepo(line)?.startsWith(`${AUTHOR}/`) ? 5 : 1) : line).join('\n')
  return prefix + '\n' + rendered + '\n\n    ' + source.slice(end)
}
