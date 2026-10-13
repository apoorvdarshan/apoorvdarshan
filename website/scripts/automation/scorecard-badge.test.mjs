import test from 'node:test'
import assert from 'node:assert/strict'
import { scorecardBadge } from '../../src/worker/scorecard-badge.js'

test('Scorecard badges validate scores, constrain upstream and cache live values', async () => {
  const path = '/badges/scorecard/v1/profile.svg'
  const request = new Request(`https://example.com${path}`)
  const result = await scorecardBadge(request, path, async url => {
    assert.equal(url, 'https://api.scorecard.dev/projects/github.com/apoorvdarshan/profile')
    return Response.json({score: 7.9})
  })
  assert.match(await result.text(), /Scorecard: 7.9/)
  assert.equal(result.headers.get('Cache-Control'), 'public, max-age=3600')
  for (const score of ['<script>', -1, 11, null]) {
    const bad = await scorecardBadge(request, path, async () => Response.json({score}))
    assert.match(await bad.text(), /Scorecard: unavailable/)
    assert.equal(bad.headers.get('Cache-Control'), 'public, max-age=60')
  }
  const offline = await scorecardBadge(request, path, async () => { throw new Error('offline') })
  assert.match(await offline.text(), /unavailable/)
  const rejected = await scorecardBadge(request, '/badges/scorecard/v1/evil.svg', () => {throw new Error('must not fetch')})
  assert.equal(rejected.status, 404)
  const head = await scorecardBadge(new Request(request, {method:'HEAD'}), path, async()=>Response.json({score:8}))
  assert.equal(await head.text(), '')
})
