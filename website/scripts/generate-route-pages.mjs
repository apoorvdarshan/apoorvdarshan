import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { SEO_BY_PATH, SOCIAL_IMAGE, canonicalUrl, structuredData } from '../src/seo.js'

const htmlPath = new URL('../dist/index.html', import.meta.url)
const baseHtml = await readFile(htmlPath, 'utf8')

function escapeAttribute(value) {
  return value.replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
}

function pageHtml(path) {
  const page = SEO_BY_PATH[path]
  const canonical = canonicalUrl(path)
  const jsonLd = JSON.stringify(structuredData(path)).replaceAll('<', '\\u003c')

  return baseHtml
    .replace(/<title>.*?<\/title>/, `<title>${page.title}</title>`)
    .replace(/<meta name="description" content="[^"]*"\s*\/>/, `<meta name="description" content="${escapeAttribute(page.description)}" />`)
    .replace('<!-- SEO:canonical -->', `<link rel="canonical" href="${canonical}" />`)
    .replace('<!-- SEO:social -->', [
      '<meta property="og:type" content="profile" />',
      '<meta property="og:site_name" content="Apoorv Darshan" />',
      `<meta property="og:title" content="${escapeAttribute(page.title)}" />`,
      `<meta property="og:description" content="${escapeAttribute(page.description)}" />`,
      `<meta property="og:url" content="${canonical}" />`,
      `<meta property="og:image" content="${SOCIAL_IMAGE}" />`,
      '<meta property="og:image:width" content="1200" />',
      '<meta property="og:image:height" content="630" />',
      '<meta property="og:image:alt" content="Apoorv Darshan — developer and open-source builder" />',
      '<meta name="twitter:card" content="summary_large_image" />',
      '<meta name="twitter:site" content="@apoorvdarshan" />',
      '<meta name="twitter:creator" content="@apoorvdarshan" />',
      `<meta name="twitter:title" content="${escapeAttribute(page.title)}" />`,
      `<meta name="twitter:description" content="${escapeAttribute(page.description)}" />`,
      `<meta name="twitter:image" content="${SOCIAL_IMAGE}" />`,
      '<meta name="twitter:image:alt" content="Apoorv Darshan — developer and open-source builder" />',
    ].join('\n    '))
    .replace('<!-- SEO:structured-data -->', `<script type="application/ld+json">${jsonLd}</script>`)
}

await writeFile(htmlPath, pageHtml('/'))

for (const path of Object.keys(SEO_BY_PATH).filter((route) => route !== '/')) {
  const directory = new URL(`../dist${path}/`, import.meta.url)
  const html = pageHtml(path)
  await mkdir(directory, { recursive: true })
  await Promise.all([
    writeFile(new URL('index.html', directory), html),
    writeFile(new URL(`../dist${path}.html`, import.meta.url), html),
  ])
}

console.log(`Generated SEO entry pages for ${Object.keys(SEO_BY_PATH).length} routes.`)
