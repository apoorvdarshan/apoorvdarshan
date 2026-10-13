import { scorecardBadge } from './scorecard-badge.js'
import { downloadBadge } from './download-badge.js'

const RESUME_ASSET_PATH = '/Apoorv_Darshan_Resume.pdf'
const RESUME_FILENAME = 'Apoorv_Darshan_Resume.pdf'

function isResumePath(pathname) {
  return pathname === '/resume' || pathname === '/resume/'
}

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url)
    const badge = downloadBadge(request, pathname)
    if (badge) return badge
    const scorecard = await scorecardBadge(request, pathname)
    if (scorecard) return scorecard

    if (!isResumePath(pathname)) {
      return env.ASSETS.fetch(request)
    }

    const assetRequest = new Request(new URL(RESUME_ASSET_PATH, request.url), request)
    const assetResponse = await env.ASSETS.fetch(assetRequest)
    if (!assetResponse.ok) return assetResponse

    const headers = new Headers(assetResponse.headers)
    headers.set('Content-Type', 'application/pdf')
    headers.set('Content-Disposition', `inline; filename="${RESUME_FILENAME}"`)
    headers.set('Cache-Control', 'public, max-age=0, must-revalidate')

    return new Response(assetResponse.body, {
      status: assetResponse.status,
      headers,
    })
  },
}
