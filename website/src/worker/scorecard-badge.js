const REPOS = new Set(['profile', 'apoorvdarshan', 'rekisei'])

export async function scorecardBadge(request, pathname, fetcher = fetch) {
  if (!pathname.startsWith('/badges/scorecard/')) return null
  if (!['GET', 'HEAD'].includes(request.method)) return new Response('Method not allowed', { status: 405, headers: { Allow: 'GET, HEAD' } })
  const repo = pathname.match(/^\/badges\/scorecard\/v1\/([a-z]+)\.svg$/)?.[1]
  if (!REPOS.has(repo)) return new Response('Badge not found', { status: 404 })
  let label = 'unavailable'
  let valid = false
  try {
    const response = await fetcher(`https://api.scorecard.dev/projects/github.com/apoorvdarshan/${repo}`, {
      headers: { Accept: 'application/json' },
      cf: { cacheTtl: 3600, cacheEverything: true },
      signal: AbortSignal.timeout(8000),
    })
    if (!response.ok) throw new Error('Scorecard unavailable')
    const data = await response.json()
    if (typeof data.score !== 'number' || !Number.isFinite(data.score) || data.score < 0 || data.score > 10) throw new Error('Invalid score')
    label = data.score.toFixed(1)
    valid = true
  } catch { /* Show an honest unavailable badge on upstream failures, never a made-up score. */ }
  const right = valid ? 36 : 80
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${120 + right}" height="20" role="img" aria-label="OpenSSF Scorecard: ${label}"><title>OpenSSF Scorecard: ${label}</title><path fill="#555" d="M0 0h120v20H0z"/><path fill="${valid ? '#4c1' : '#777'}" d="M120 0h${right}v20H120z"/><g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11"><text x="60" y="14">openssf scorecard</text><text x="${120 + right / 2}" y="14">${label}</text></g></svg>`
  return new Response(request.method === 'HEAD' ? null : svg, { headers: {
    'Content-Type': 'image/svg+xml; charset=utf-8',
    'Cache-Control': valid ? 'public, max-age=3600' : 'public, max-age=60',
    'X-Content-Type-Options': 'nosniff',
  } })
}
