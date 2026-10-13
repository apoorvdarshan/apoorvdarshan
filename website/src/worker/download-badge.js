const PREFIXES = ['/badges/downloads/', '/badges/users/']

export function downloadBadge(request, pathname) {
  if (!PREFIXES.some(prefix => pathname.startsWith(prefix))) return null
  if (!['GET', 'HEAD'].includes(request.method)) {
    return new Response('Method not allowed', { status: 405, headers: { Allow: 'GET, HEAD' } })
  }

  let match
  try {
    match = decodeURIComponent(pathname).match(/^\/badges\/(downloads|users)\/v1\/(\d{1,6}[KM]?\+?)\.svg$/)
  } catch { /* Malformed paths return 404 instead of the SPA. */ }
  if (!match) return new Response('Badge not found', { status: 404 })

  // Only a bounded numeric milestone reaches the SVG. No upstream requests or credentials.
  const users = match[1] === 'users'
  const label = match[2]
  const kind = users ? 'Users' : 'Downloads'
  const leftWidth = users ? 39 : 15
  const textWidth = Math.ceil(label.length * 7.2)
  const rightWidth = textWidth + 10
  const width = leftWidth + rightWidth
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="20" role="img" aria-label="${kind}: ${label}">
<title>${kind}: ${label}</title>
<path fill="#555" d="M0 0h${leftWidth}v20H0z"/><path fill="#8B1A1A" d="M${leftWidth} 0h${rightWidth}v20H${leftWidth}z"/>
<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
<text x="${leftWidth / 2}" y="14">${users ? 'users' : '↓'}</text><text x="${leftWidth + rightWidth / 2}" y="14" textLength="${textWidth}" lengthAdjust="spacingAndGlyphs">${label}</text>
</g></svg>`
  return new Response(request.method === 'HEAD' ? null : svg, { headers: {
    'Content-Type': 'image/svg+xml; charset=utf-8',
    // The version and displayed count are in the URL; a new milestone gets a new URL.
    'Cache-Control': 'public, max-age=31536000, immutable',
    'X-Content-Type-Options': 'nosniff',
  } })
}
