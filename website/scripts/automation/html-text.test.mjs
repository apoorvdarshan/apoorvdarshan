import test from 'node:test'
import assert from 'node:assert/strict'
import { htmlText, decodeEntities } from '../html-text.mjs'
import { plainText, liveDownloadsUrl } from '../sync-profile-readme.mjs'

test('only Shields endpoint download tiles get a live JSON count URL', () => {
  assert.equal(
    liveDownloadsUrl('https://img.shields.io/endpoint?url=https://example.com/api/stats/badge&style=flat-square&label=%E2%86%93'),
    'https://img.shields.io/endpoint.json?url=https%3A%2F%2Fexample.com%2Fapi%2Fstats%2Fbadge',
  )
  assert.equal(liveDownloadsUrl('https://apoorvdarshan.com/badges/downloads/v1/1K%2B.svg'), '')
  assert.equal(liveDownloadsUrl('https://img.shields.io/github/downloads/o/r/total'), '')
  assert.equal(liveDownloadsUrl('https://img.shields.io/endpoint?url=http://example.com/badge'), '')
  assert.equal(liveDownloadsUrl('https://evil.example/endpoint?url=https://example.com/badge'), '')
  assert.equal(liveDownloadsUrl('not a url'), '')
})

test('entities decode once and malformed markup is parsed as text', () => {
  assert.equal(decodeEntities('&amp;lt;script&amp;gt;'), '&lt;script&gt;')
  assert.equal(htmlText('&amp;lt;script&amp;gt;'), '&lt;script&gt;')
  assert.equal(htmlText('<b>hello</b><script>alert(1)</script> world'), 'hello world')
  assert.equal(htmlText('<img alt="A &amp; B">'), 'A & B')
  assert.equal(plainText('<img alt="Stars"> <b>hello</b>'), 'hello')
  assert.equal(htmlText('&lt;script&gt;'), '<script>')
})
