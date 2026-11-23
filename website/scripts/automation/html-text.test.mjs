import test from 'node:test'
import assert from 'node:assert/strict'
import { htmlText, decodeEntities } from '../html-text.mjs'
import { plainText, liveDownloadsUrl, parseReadme } from '../sync-profile-readme.mjs'

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

test('currently reading preserves the book title and link and excludes adjacent sections', () => {
  const readme = `
## What I Use
### Hardware
### Software
[![Reader](https://img.shields.io/badge/reader)](https://example.com/reader)
## Currently Reading
<ul>
  <li><strong><a href="https://example.com/kindle?a=1&amp;b=2">A Reader's Book</a></strong> - An Author (Kindle edition)</li>
</ul>
## Resume
<ul>
  <li><strong><a href="https://example.com/resume">Resume</a></strong></li>
</ul>
`
  const profile = parseReadme(readme)
  assert.deepEqual(profile.uses.software.map(({ name }) => name), ['Reader'])
  assert.deepEqual(profile.currentlyReading, [{
    name: "A Reader's Book",
    url: 'https://example.com/kindle?a=1&b=2',
    description: 'An Author (Kindle edition)',
  }])
  assert.deepEqual(parseReadme(readme.slice(readme.indexOf('## Resume'))).currentlyReading, [])
})
