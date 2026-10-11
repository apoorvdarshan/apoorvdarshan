import test from 'node:test'
import assert from 'node:assert/strict'
import worker from '../src/index.js'

test('valid counts, invalid upstream values and hostile identifiers', async () => {
  let calls = 0
  globalThis.caches = {default: {match: async () => null, put: async () => {}}}
  const oldFetch = globalThis.fetch
  const ctx = {waitUntil() {}}
  try {
    globalThis.fetch = async url => {calls++; assert.equal(url, 'https://api.github.com/repos/owner/repo'); return Response.json({stargazers_count: 42})}
    const r = await worker.fetch(new Request('https://example.com/api/stars?repo=owner/repo&format=json'), {}, ctx)
    assert.equal((await r.json()).stars, 42)
    const before = calls
    let seed=3421
    for (let i=0; i<1500; i++) {
      seed=(seed*1664525+1013904223)>>>0
      const repo=['../','<script>','a/b/c','https://evil.test/', 'owner/repo?x='][seed%5]+String(seed)
      const r=await worker.fetch(new Request('https://example.com/api/stars?repo='+encodeURIComponent(repo)+'&format=json'), {}, ctx)
      assert.equal(r.status,400)
    }
    assert.equal(calls,before,'Invalid input must never reach the network')
    for (const value of [-1, null, '5', 1.5]) {
      globalThis.fetch = async () => Response.json({stargazers_count:value})
      const saved=console.error; console.error=()=>{}
      try {assert.equal((await worker.fetch(new Request('https://example.com/api/stars?repo=owner/repo&format=json'),{},ctx)).status,502)} finally {console.error=saved}
    }
  } finally {globalThis.fetch=oldFetch}
})
