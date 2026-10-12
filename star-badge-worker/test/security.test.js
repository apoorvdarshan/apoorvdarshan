import test from 'node:test'
import assert from 'node:assert/strict'
import worker from '../src/index.js'
import fc from 'fast-check'

// Reproducible generated identifiers exercise URL encoding and origin containment.
test('generated repository names cannot redirect upstream requests', async () => {
  const oldFetch = globalThis.fetch
  const oldCaches = globalThis.caches
  let calls = 0
  globalThis.caches = {default: {match: async () => null, put: async () => {}}}
  try {
    const name = fc.string({unit: fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz0123456789-'), maxLength: 38})
    await fc.assert(fc.asyncProperty(name, fc.nat(), async (suffix, id) => {
        const repo = `a${suffix}/repo_${id}`
        globalThis.fetch = async url => {
          calls++
          assert.equal(url, `https://api.github.com/repos/${repo}`)
          return Response.json({stargazers_count: 0})
        }
        const request = value => new Request(`https://example.com/api/stars?format=json&repo=${encodeURIComponent(value)}`)
        assert.equal((await worker.fetch(request(repo), {}, {waitUntil() {}})).status, 200)
        const before = calls
        for (const invalid of [`${repo}/..`, `//evil.test/${repo}`, `${repo}?redirect=evil`, `${repo}\u0000`, `${repo}💥`]) {
          assert.equal((await worker.fetch(request(invalid), {}, {waitUntil() {}})).status, 400)
        }
        assert.equal(calls, before, 'Rejected identifiers must not reach the network')
    }), {numRuns: 1000})
  } finally {
    globalThis.fetch = oldFetch
    globalThis.caches = oldCaches
  }
})
