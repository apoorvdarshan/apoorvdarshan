import assert from 'node:assert/strict'
import { test } from 'node:test'
import worker from '../../src/worker/index.js'

const origin = 'https://apoorvdarshan.com'
const noAssets = { ASSETS: { fetch() { throw new Error('Badge must not depend on assets or external services') } } }

test('download milestones render as independently served, cacheable SVGs', async () => {
  for (const label of ['0', '9', '10+', '40+', '70+', '100+', '400+', '1K+', '9K+', '10K+', '1M+']) {
    const url = `${origin}/badges/downloads/v1/${encodeURIComponent(label)}.svg`
    const response = await worker.fetch(new Request(url), noAssets)
    assert.equal(response.status, 200)
    assert.match(response.headers.get('Content-Type'), /^image\/svg\+xml/)
    assert.match(response.headers.get('Cache-Control'), /immutable/)
    const svg = await response.text()
    assert.ok(svg.includes(`<title>Downloads: ${label}</title>`))
    assert.ok(svg.includes('fill="#8B1A1A"'))
    const head = await worker.fetch(new Request(url, { method: 'HEAD' }), noAssets)
    assert.equal(head.status, 200)
    assert.equal(await head.text(), '')
    assert.equal(head.headers.get('Content-Type'), response.headers.get('Content-Type'))
  }
})

test('malformed badge paths never return HTML or inject untrusted SVG content', async () => {
  for (const value of ['bad', '%3Cscript%3E', '%E0%A4%A', '1234567890', '-1']) {
    const response = await worker.fetch(new Request(`${origin}/badges/downloads/v1/${value}.svg`), noAssets)
    assert.equal(response.status, 404)
    assert.equal(await response.text(), 'Badge not found')
  }
  const response = await worker.fetch(new Request(`${origin}/badges/downloads/v1/400%2B.svg`, { method: 'POST' }), noAssets)
  assert.equal(response.status, 405)
})

test('badge routing preserves normal assets and the resume PDF response', async () => {
  const seen = []
  const env = { ASSETS: { fetch(request) {
    seen.push(new URL(request.url).pathname)
    return new Response('asset', { headers: { 'Content-Type': 'application/octet-stream' } })
  } } }
  assert.equal(await (await worker.fetch(new Request(`${origin}/`), env)).text(), 'asset')
  for (const path of ['/resume', '/resume/']) {
    const response = await worker.fetch(new Request(`${origin}${path}`), env)
    assert.equal(response.headers.get('Content-Type'), 'application/pdf')
    assert.equal(response.headers.get('Content-Disposition'), 'inline; filename="Apoorv_Darshan_Resume.pdf"')
  }
  assert.deepEqual(seen, ['/', '/Apoorv_Darshan_Resume.pdf', '/Apoorv_Darshan_Resume.pdf'])
})


test('user badges preserve the metric and reject invalid input', async () => {
  for (const label of ['4', '40+', '1K+']) {
    const response = await worker.fetch(new Request(`${origin}/badges/users/v1/${encodeURIComponent(label)}.svg`), noAssets)
    assert.equal(response.status, 200)
    assert.match(await response.text(), new RegExp(`<title>Users: ${label.replace('+', '\\+')}</title>`))
  }
  const response = await worker.fetch(new Request(`${origin}/badges/users/v1/bad.svg`), noAssets)
  assert.equal(response.status, 404)
})
