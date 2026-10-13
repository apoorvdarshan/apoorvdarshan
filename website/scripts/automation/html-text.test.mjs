import test from 'node:test'
import assert from 'node:assert/strict'
import { htmlText, decodeEntities } from '../html-text.mjs'
import { plainText } from '../sync-profile-readme.mjs'

test('entities decode once and malformed markup is parsed as text', () => {
  assert.equal(decodeEntities('&amp;lt;script&amp;gt;'), '&lt;script&gt;')
  assert.equal(htmlText('&amp;lt;script&amp;gt;'), '&lt;script&gt;')
  assert.equal(htmlText('<b>hello</b><script>alert(1)</script> world'), 'hello world')
  assert.equal(htmlText('<img alt="A &amp; B">'), 'A & B')
  assert.equal(plainText('<img alt="Stars"> <b>hello</b>'), 'hello')
  assert.equal(htmlText('&lt;script&gt;'), '<script>')
})
