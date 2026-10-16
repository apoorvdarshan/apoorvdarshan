import { htmlText, decodeEntities } from './html-text.mjs'
import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const README_URL = 'https://raw.githubusercontent.com/apoorvdarshan/apoorvdarshan/main/README.md'
const OUTPUT_URL = new URL('../src/profileData.generated.json', import.meta.url)

const decode = (value = '') => decodeEntities(value).replaceAll('•', '')

export const plainText = (value = '') => htmlText(value,
  alt => (alt === 'Stars' || alt.startsWith('Downloads:') || alt.startsWith('Users:')) ? '' : alt)
  .replaceAll('•', '')
  .replace(/\s+/g, ' ')
  .trim()

function section(readme, start, end) {
  const startIndex = readme.indexOf(start)
  const endIndex = end ? readme.indexOf(end, startIndex + start.length) : readme.length
  return startIndex === -1 ? '' : readme.slice(startIndex, endIndex === -1 ? readme.length : endIndex)
}

function htmlEntriesFrom(text) {
  return text.split('\n').flatMap((line) => {
    const match = line.match(/<strong><a href="([^"]+)">([^<]+)<\/a><\/strong>(.*?)(?:<\/li>|<\/div>)/)
    if (!match) return []

    const prefix = line.slice(0, line.indexOf('<strong>'))
    const marker = plainText(prefix).replace(/^•\s*/, '').trim()
    const starBadgeUrl = decode(line.match(/<img alt="Stars" src="([^"]+)"/)?.[1] ?? '')
    const rawTail = plainText(match[3])
    const status = rawTail.match(/^\(([^)]+)\)/)?.[1] ?? ''
    let description = rawTail
      .replace(/^\([^)]+\)\s*/, '')
      .replace(/^\s*-\s*/, '')
      .replace(/\(by\s*\)/g, '')
      .replace(/\s+/g, ' ')
      .trim()
    const downloadsFromBadge = line.match(/<img[^>]*alt="Downloads:\s*([^"]+)"[^>]*>/i)?.[1]?.trim() ?? ''
    const usersFromBadge = line.match(/<img[^>]*alt="Users:\s*([^"]+)"[^>]*>/i)?.[1]?.trim() ?? ''
    const downloadsMatch = description.match(/\((\d+[KkMm]?\+?)\s+downloads\)\s*$/i)
    const downloads = downloadsFromBadge || usersFromBadge || (downloadsMatch?.[1] ?? '')
    if (downloadsMatch) {
      description = description.slice(0, downloadsMatch.index).replace(/\s+$/, '').trim()
    }

    return [{
      name: plainText(match[2]),
      url: decode(match[1]),
      description,
      status,
      marker,
      starBadgeUrl,
      ...(downloads ? { downloads, metric: usersFromBadge ? 'users' : 'downloads' } : {}),
    }]
  })
}

function htmlEntries(readme, start, end) {
  return htmlEntriesFrom(section(readme, start, end))
}

function projectSections(readme) {
  const block = section(readme, '## Chrome Extensions', '### Open Source Contributions')
  return block.split(/\n(?=## )/).flatMap((part) => {
    const heading = part.match(/^## (.+)$/m)?.[1]
    if (!heading) return []
    const name = plainText(heading).replace(/^[^A-Za-z0-9]+/, '').trim()
    if (name === 'Chrome Extensions') return []
    return [{ name, items: htmlEntriesFrom(part) }]
  })
}

function markdownBullets(value) {
  return value.split('\n').flatMap((line) => {
    const match = line.match(/^-\s+(.*)$/)
    return match ? [plainText(match[1]).replaceAll('**', '')] : []
  })
}

function badgeLinks(value) {
  return value.split('\n').flatMap((line) => {
    const match = line.match(/^\[!\[([^\]]+)\]\([^)]*\)\]\(([^)]+)\)/)
    if (!match) return []
    const sourceName = plainText(match[1]).replace(/^[-★\s]+$/, 'X')
    return [{ name: sourceName === 'Twitter' ? 'X' : sourceName, url: decode(match[2]) }]
  })
}

function badgeTiles(value) {
  return value.split('\n').flatMap((line) => {
    const match = line.match(/^\[!\[([^\]]+)\]\(([^)]*)\)\]\(([^)]+)\)/)
    if (!match) return []
    const sourceName = plainText(match[1]).replace(/^[-★\s]+$/, 'X')
    return [{
      name: sourceName === 'Twitter' ? 'X' : sourceName,
      badgeUrl: decode(match[2]),
      url: decode(match[3]),
    }]
  })
}

async function attachStarCounts(data, previousStarCounts = new Map(), verifiedStars) {
  const queue = ['apps', 'games', 'extensions', 'projects', 'openSource']
    .flatMap((key) => data[key])
    .filter((item) => item.starBadgeUrl)

  const workers = Array.from({ length: Math.min(8, queue.length) }, async () => {
    while (queue.length) {
      const item = queue.shift()
      try {
        if (verifiedStars) {
          const repo = new URL(item.starBadgeUrl).searchParams.get('repo')?.toLowerCase()
          const stars = verifiedStars[repo]
          if (!Number.isSafeInteger(stars) || stars < 0) throw new Error(`Missing verified stars for ${repo}`)
          item.starCount = stars >= 10000 ? `${Math.round(stars / 1000)}k` : stars >= 1000 ? `${Number((stars / 1000).toFixed(1))}k` : String(stars)
          continue
        }
        const response = await fetch(item.starBadgeUrl, { headers: { 'User-Agent': 'apoorv-profile-build' } })
        if (!response.ok) throw new Error(`badge returned ${response.status}`)
        const svg = await response.text()
        item.starCount = svg.match(/aria-label="★:\s*([^"]+)"/)?.[1]
          || previousStarCounts.get(item.starBadgeUrl)
          || ''
      } catch (error) {
        if (verifiedStars) throw error
        item.starCount = previousStarCounts.get(item.starBadgeUrl) ?? ''
        console.warn(`Star count unavailable for ${item.name}: ${error.message}`)
      }
    }
  })

  await Promise.all(workers)
}

function parseReadme(readme) {
  const beforeApps = section(readme, '# Hi,', '## Mobile Apps')
  const technologyMatches = [...beforeApps.matchAll(/!\[([^\]]+)\]\(https:\/\/img\.shields\.io\/badge/g)]
  const technologies = technologyMatches.map((match) => match[1])
  const tagline = readme.split('\n').find((line) => line.startsWith('📍')) ?? ''
  const statement = beforeApps.split('\n').find((line) => line.startsWith('> '))?.slice(2) ?? ''
  const activitySection = section(readme, '## GitHub Activity', '## What I Use')
  const activityImage = activitySection.match(/<img src="([^"]+)"/)?.[1] ?? ''
  const philosophySection = section(readme, '### Philosophy')
  const philosophy = philosophySection.split('\n').find((line) => line.startsWith('> '))?.slice(2) ?? ''
  const randomFactsPart = philosophySection.split('<summary>Random Facts</summary>')[1]?.split('</details>')[0] ?? ''

  return {
    source: {
      label: 'GitHub profile README',
      url: 'https://github.com/apoorvdarshan',
      rawUrl: README_URL,
    },
    intro: {
      title: "Hi, I'm Apoorv 👋",
      location: 'Delhi',
      tagline: plainText(tagline).replaceAll('**', ''),
      statement: plainText(statement),
    },
    technologies,
    apps: htmlEntries(readme, '## Mobile Apps', '## Games'),
    games: htmlEntries(readme, '## Games', '## Chrome Extensions'),
    extensions: htmlEntries(readme, '## Chrome Extensions', '## AI & Agents'),
    projects: projectSections(readme).flatMap((section) => section.items),
    projectSections: projectSections(readme),
    openSource: htmlEntries(readme, '### Open Source Contributions', '## GitHub Activity'),
    activityImage,
    uses: (() => {
      const usesSection = section(readme, '## What I Use', '## Resume')
      return {
        hardware: badgeTiles(section(usesSection, '### Hardware', '### Software')),
        software: badgeTiles(section(usesSection, '### Software')),
      }
    })(),
    connect: badgeLinks(section(readme, '## Connect', '### Recognition')),
    recognition: markdownBullets(section(readme, '### Recognition', '### Philosophy')),
    philosophy: plainText(philosophy),
    randomFacts: markdownBullets(randomFactsPart),
  }
}

async function main() {
  const readmePath = process.env.PROFILE_README_PATH || fileURLToPath(new URL('../../README.md', import.meta.url))
  const readme = await readFile(readmePath, 'utf8')

  const data = parseReadme(readme)
  let previousStarCounts = new Map()
  try {
    const previous = JSON.parse(await readFile(OUTPUT_URL, 'utf8'))
    previousStarCounts = new Map(
      ['apps', 'games', 'extensions', 'projects', 'openSource']
        .flatMap((key) => previous[key] ?? [])
        .filter((item) => item.starBadgeUrl && item.starCount)
        .map((item) => [item.starBadgeUrl, item.starCount]),
    )
  } catch {
    // The first sync has no committed snapshot to fall back to.
  }
  for (const item of data.connect) {
    if (item.name === 'Resume') item.url = 'https://apoorvdarshan.com/resume'
  }

  const starsPath = process.env.PROFILE_STARS_PATH || new URL('../../profile-automation/contributions.json', import.meta.url)
  const verifiedStars = JSON.parse(await readFile(starsPath, 'utf8')).stars
  if ((!data.apps.length || !data.openSource.length || !data.activityImage)) {
    throw new Error('Incomplete local README; refusing to overwrite profile snapshot')
  }
  await attachStarCounts(data, previousStarCounts, verifiedStars)
  await writeFile(fileURLToPath(OUTPUT_URL), `${JSON.stringify(data, null, 2)}\n`)
  console.log(`Synced GitHub README: ${data.apps.length} apps, ${data.games.length} games, ${data.extensions.length} extensions, ${data.projects.length} projects, ${data.openSource.length} open-source contributions.`)
}

if (process.argv[1] === fileURLToPath(import.meta.url)) await main()
