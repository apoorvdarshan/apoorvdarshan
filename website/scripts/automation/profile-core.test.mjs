import test from 'node:test'
import assert from 'node:assert/strict'
import { updateReadme, updateResume, entries, verifiedPRs, texEscape, recentDescription, cleanTitle } from './profile-core.mjs'
import { plainText } from '../sync-profile-readme.mjs'

function readme(rows) {return `# Hello\n## Mobile Apps\n<ul>\n<li>📱 <strong><a href="https://github.com/apoorvdarshan/app">app</a></strong> - my app</li>\n</ul>\n### Open Source Contributions\n\n<ul>\n${rows.map(([repo,desc='my custom fix'])=>`  <li>🔧 <strong><a href="https://github.com/${repo}/pull/1">${repo.split('/')[1]}</a></strong> - ${desc}</li>`).join('\n')}\n</ul>\n\n## GitHub Activity\nPRIVATE-SENTINEL-DO-NOT-EDIT\n`}
function pr(repo,number,extra={}) { return {number,title:'fix(ui): Correct <script> & $value',url:`https://github.com/${repo}/pull/${number}`,mergedAt:'2026-10-10T00:00:00Z',author:{login:'apoorvdarshan'},repository:{nameWithOwner:repo,isPrivate:false,owner:{login:repo.split('/')[0]}},...extra} }
test('filters own/private/other-author/unmerged PRs, deduplicates',()=>{
  const good=pr('org/one',1)
  assert.equal(verifiedPRs([good,good,pr('apoorvdarshan/app',1),pr('org/two',2,{author:{login:'elsewhere'}}),pr('org/two',3,{mergedAt:null}),pr('org/secret',1,{repository:{nameWithOwner:'org/secret',owner:{login:'org'},isPrivate:true}})]).length,1)
})
test('new merges refresh summaries and counts while sorting and overflow stay stable',()=>{
  const repos=Array.from({length:12},(_,i)=>`org/repo${i}`)
  const stars=Object.fromEntries(repos.map((r,i)=>[r,i]));stars['apoorvdarshan/app']=1
  const before=readme(repos.map(r=>[r]))
  const prs=[pr(repos[0],1,{title:'fix: Login bug'}),pr(repos[0],2,{title:'feat: Offline mode'})]
  const first=updateReadme(before,prs,stars)
  assert(first.readme.includes('2 merged PRs: Offline mode; Login bug'))
  assert.equal(entries(first.readme)[0].repo,'org/repo11')
  const oss=first.readme.split('### Open Source Contributions')[1]
  assert.equal((oss.match(/<li>.*<strong>/g)||[]).length,10)
  assert.equal((oss.match(/<div>&bull;/g)||[]).length,2)
  assert(first.readme.endsWith('PRIVATE-SENTINEL-DO-NOT-EDIT\n'))
  assert.equal(updateReadme(first.readme,prs,stars,first.state).readme,first.readme)
  const next=updateReadme(first.readme,[...prs,pr(repos[0],3,{title:'feat: Export CSV'})],stars,first.state)
  assert(next.readme.includes('3 merged PRs: Export CSV; Offline mode; Login bug'))
  assert(next.rows.find(r=>r.repo===repos[0]).html.includes('author%3Aapoorvdarshan'))
  assert(next.rows.find(r=>r.repo===repos[1]).html.includes('my custom fix'))
  assert.throws(()=>updateReadme(first.readme,[],stars,first.state),/Previously verified PR missing/)
})
test('title is escaped as text, star badges added and removed',()=>{
  const initial=readme([['org/old']]);const stars={'apoorvdarshan/app':5,'org/old':0,'org/new':10}
  const a=updateReadme(initial,[pr('org/new',1)],stars)
  assert(a.readme.includes('Correct &lt;script&gt; &amp; $value'))
  assert(!a.readme.includes('<script>'))
  assert(a.readme.includes('repo=apoorvdarshan/app'))
  const b=updateReadme(a.readme,[pr('org/new',1)],{...stars,'apoorvdarshan/app':4})
  assert(!b.readme.includes('repo=apoorvdarshan/app'))
  assert.throws(()=>updateReadme(initial,[],{}),/Missing\/invalid stars/)
})
test('manual authored-commit credits and higher editorial counts survive',()=>{
  const a=updateReadme(readme([['org/credit','fix bug (authored commit)'],['org/old','3 merged PRs: hand-written summary']]),[pr('org/old',1)],{'apoorvdarshan/app':0,'org/credit':1,'org/old':2})
  assert(a.readme.includes('(authored commit)'))
  assert(a.readme.includes('3 merged PRs: hand-written summary'))
  assert.equal(a.warnings.length,1)
})
test('resume reorders contributions without moving projects or altering header',()=>{
  const source=String.raw`HEADER-SENTINEL
\section{Apps}
\resumeProjectHeading{\textbf{\href{https://github.com/apoorvdarshan/app}{app}} $|$ {\small $\bigstar$ 1 star $|$ \textcolor{Maroon}{$\downarrow$ 9K+}} \textnormal{ -- my app}}{}
\section{Open Source Contributions}
\resumeSubHeadingListStart
\resumeProjectHeading{\textbf{\href{https://github.com/org/old/pull/1}{old}} $|$ {\small $\bigstar$ 1 star} \textnormal{ -- resume custom description}}{}
\resumeSubHeadingListEnd
FOOTER-SENTINEL`
  const stars={'apoorvdarshan/app':4,'org/old':1,'org/new':50000}
  const r=updateReadme(readme([['org/old']]),[pr('org/new',1),pr('org/old',1),pr('org/old',2)],stars)
  const tex=updateResume(source,r.rows,stars)
  assert(tex.startsWith('HEADER-SENTINEL'))
  assert(tex.endsWith('FOOTER-SENTINEL'))
  assert(tex.includes('9K+'))
  assert(!tex.split('\\section{Open Source Contributions}')[0].includes('\\bigstar'))
  assert(tex.split('\\section{Open Source Contributions}')[1].includes('1 star'))
  const five = updateResume(tex,r.rows,{...stars,'apoorvdarshan/app':5})
  assert(five.split('\\section{Open Source Contributions}')[0].includes('5 stars'))
  assert(tex.includes(String.raw`2 merged PRs: Correct <script> \& \$value`))
  assert(!tex.includes('resume custom description'))
  assert(tex.indexOf('org/new')<tex.indexOf('org/old'))
  for (const line of tex.split('\n').filter(l=>l.includes('\\resumeProjectHeading{'))) {
    const braces = line.replace(/\\[{}]/g, '').match(/[{}]/g)
    assert.equal(braces.filter(c=>c==='{').length, braces.filter(c=>c==='}').length, 'balanced LaTeX groups')
  }
  assert.equal(updateResume(tex,r.rows,stars),tex)
  assert.equal(texEscape('a_%\\input{x}'),String.raw`a\_\%\textbackslash{}input\{x\}`)
  assert.throws(()=>updateResume(source.replace('\\resumeSubHeadingListStart',''),r.rows,stars),/list start missing/)
  assert.throws(()=>updateResume(source,r.rows,{}),/resume stars/)
})
test('resume recognizes escaped repository names and preserves their prose',()=>{
  const source=String.raw`\section{Open Source Contributions}
\resumeSubHeadingListStart
\resumeProjectHeading{\textbf{\href{https://github.com/org/curl\_cffi/pull/1}{curl\_cffi}} \textnormal{ -- keep this custom wording}}{}
\resumeSubHeadingListEnd`
  const stars={'apoorvdarshan/app':0,'org/curl_cffi':20000}
  const r=updateReadme(readme([['org/curl_cffi']]),[pr('org/curl_cffi',1)],stars)
  const tex=updateResume(source,r.rows,stars)
  assert(tex.includes('keep this custom wording'))
  assert(tex.includes('20k stars'))
  assert.equal(updateResume(tex,r.rows,stars),tex)
})
test('recent summaries use merge time, up to three distinct titles, and the full count',()=>{
  const pulls=[
    pr('org/r',10,{title:'feat: Offline mode',mergedAt:'2026-10-10T03:00:00Z'}),
    pr('org/r',20,{title:'fix: Login bug',mergedAt:'2026-10-10T01:00:00Z'}),
    pr('org/r',30,{title:'docs: Login bug',mergedAt:'2026-10-10T02:00:00Z'}),
    pr('org/r',40,{title:'feat: Export CSV',mergedAt:'2026-10-09T00:00:00Z'}),
    pr('org/r',50,{title:'chore: Older work',mergedAt:'2026-10-08T00:00:00Z'}),
  ]
  assert.equal(recentDescription(pulls),'5 merged PRs: Offline mode; Login bug; Export CSV')
  assert.equal(recentDescription([...pulls].reverse()),recentDescription(pulls))
})
test('long summaries keep the two newest titles inside the one-line budget',()=>{
  const summary=recentDescription([
    pr('org/r',1,{title:'feat: Older feature that should not displace the latest work'}),
    pr('org/r',2,{title:'fix: Restore compatibility for encoded UTF-8 characters in exported filenames'}),
    pr('org/r',3,{title:'feat: Add offline synchronization for encrypted local document collections'}),
  ])
  assert([...summary].length<=90)
  assert(summary.startsWith('3 merged PRs: Add offline'))
  assert(summary.includes('; Restore compatibility'))
  assert(!summary.includes('Older feature'))
  assert.equal(summary.split('; ').length,2)
  const withShort=recentDescription([pr('org/r',1,{title:'feat: '+ '😀'.repeat(100)}),pr('org/r',2,{title:'fix: Login'})])
  assert([...withShort].length<=90)
  assert(withShort.includes('Login; 😀'))
  assert(!withShort.includes('\uFFFD'))
})
test('brand attribution survives description replacement and counts toward the limit',()=>{
  const attribution=' (by <a href="https://github.com/org"><img alt="Brand" src="brand.svg"></a>)'
  const before=readme([['org/r','old wording'+attribution]])
  const stars={'apoorvdarshan/app':0,'org/r':1}
  const first=updateReadme(before,[pr('org/r',1),pr('org/r',2,{title:'feat: A new feature'})],stars)
  assert(first.readme.includes(attribution))
  assert(first.readme.includes('A new feature; Correct &lt;script&gt; &amp; $value'))
  assert(!first.readme.includes('old wording'))
  assert.equal(updateReadme(first.readme,[pr('org/r',1),pr('org/r',2,{title:'feat: A new feature'})],stars,first.state).readme,first.readme)
})
test('title cleanup removes redundant author and code markup without inventing wording',()=>{
  assert.equal(cleanTitle('feat(app): Add `Verceltics` by @apoorvdarshan'),'Add Verceltics')
  assert.equal(cleanTitle('Add project by @someone-else'),'Add project by @someone-else')
  assert.equal(cleanTitle('Add project by @apoorvdarshan-other'),'Add project by @apoorvdarshan-other')
  const stars={'apoorvdarshan/app':0,'org/r':1}
  const prs=[pr('org/r',1),pr('org/r',2,{title:'fix: Handle retries (by design)'})]
  const first=updateReadme(readme([['org/r']]),prs,stars)
  assert.equal(updateReadme(first.readme,prs,stars,first.state).readme,first.readme)
})
test('website descriptions preserve literal code symbols from escaped PR titles',()=>{
  const r=updateReadme(readme([['org/r']]),[pr('org/r',1),pr('org/r',2,{title:'feat: Add List<T> support'})],{'apoorvdarshan/app':0,'org/r':1})
  const row=r.rows.find(r=>r.repo==='org/r')
  assert.equal(plainText(row.html.slice(row.html.indexOf(' - ')+3)), '2 merged PRs: Add List<T> support; Correct <script> & $value')
  assert.equal(plainText('<img alt="Stars" src="x"> hello <a href="x">world</a>'), 'hello world')
})
