import { readFile, writeFile, mkdir, appendFile } from 'node:fs/promises'
import { resolve, dirname } from 'node:path'
import { execFileSync } from 'node:child_process'
import assert from 'node:assert/strict'
import { AUTHOR, entries, verifiedPRs, updateReadme, updateResume } from './profile-core.mjs'

const readmePath = resolve(process.env.PROFILE_README_PATH ?? '../README.md')
const statePath = resolve(dirname(readmePath), 'profile-automation/contributions.json')
const resumePath = process.env.PROFILE_RESUME_PATH && resolve(process.env.PROFILE_RESUME_PATH)
const token = process.env.GH_TOKEN || process.env.GITHUB_TOKEN || execFileSync('gh', ['auth','token'], {encoding:'utf8'}).trim()
async function graphql(query, variables = {}) {
  for (let attempt=0; attempt<3; attempt++) {
    const r = await fetch('https://api.github.com/graphql', {method:'POST', headers:{Authorization:`Bearer ${token}`, 'Content-Type':'application/json','User-Agent':'apoorvdarshan-profile-automation'}, body:JSON.stringify({query,variables}), signal:AbortSignal.timeout(60000)})
    if (r.status >= 500 && attempt < 2) { await new Promise(r=>setTimeout(r,1000*(attempt+1))); continue }
    assert(r.ok, `GitHub API returned ${r.status}; nothing written`)
    const json = await r.json()
    assert(!json.errors, `GitHub GraphQL failed: ${json.errors?.map(e=>e.message || e.type || 'error').join(', ')}; nothing written`)
    return json.data
  }
}
const readme = await readFile(readmePath,'utf8')
let previous = null
try { previous=JSON.parse(await readFile(statePath,'utf8')) } catch(e) { if(e.code!=='ENOENT')throw e }
const pulls=[]
let after=null
let total
do {
  const data = await graphql(`query($after:String){user(login:"${AUTHOR}"){pullRequests(first:100,after:$after,states:MERGED){totalCount pageInfo{hasNextPage endCursor} nodes{number title url mergedAt author{login} repository{nameWithOwner isPrivate stargazerCount owner{login}}}}}}`, {after})
  const page=data.user.pullRequests
  if(total===undefined)total=page.totalCount
  assert.equal(page.totalCount,total,'PR list changed during pagination; retry next run')
  pulls.push(...page.nodes)
  after=page.pageInfo.hasNextPage ? page.pageInfo.endCursor : null
} while(after)
assert.equal(pulls.length,total,'Incomplete PR pagination')
const rows=entries(readme)
const repos=new Set([...rows.map(r=>r.repo.toLowerCase()), ...verifiedPRs(pulls).map(p=>p.repo.toLowerCase())])
for(const m of readme.split('### Open Source Contributions')[0].matchAll(/<strong><a href="https:\/\/github\.com\/([\w.-]+\/[\w.-]+)"/g))repos.add(m[1].toLowerCase())
let source
if(resumePath) {
  source=await readFile(resumePath,'utf8')
  for(const m of source.replace(/\\([_%#&])/g, '$1').matchAll(/\\resumeProjectHeading\{\\textbf\{\\href\{https:\/\/github\.com\/([\w.-]+\/[\w.-]+)/g))repos.add(m[1].toLowerCase())
}
const stars={}
const list=[...repos].sort()
for(let i=0;i<list.length;i+=40) {
  const batch=list.slice(i,i+40)
  const fields=batch.map((repo,j)=>{const [owner,name]=repo.split('/');return `r${j}:repository(owner:${JSON.stringify(owner)},name:${JSON.stringify(name)}){stargazerCount isPrivate}`}).join(' ')
  const data=await graphql(`query{${fields}}`)
  batch.forEach((repo,j)=>{assert(data[`r${j}`] && !data[`r${j}`].isPrivate,`Public repo unavailable: ${repo}`);stars[repo]=data[`r${j}`].stargazerCount})
}
const result=updateReadme(readme,pulls,stars,previous)
const resume=source && updateResume(source,result.rows,stars)
// All API fetches, validation and rendering finish before touching any output.
await mkdir(dirname(statePath),{recursive:true})
await writeFile(readmePath,result.readme)
await writeFile(statePath,JSON.stringify(result.state,null,2)+'\n')
if(resumePath && resume!==source)await writeFile(resumePath,resume)
const summary=`## Automatic profile refresh\n\n- Account: ${AUTHOR}\n- Verified public external merged PRs: ${result.state.pullRequests.length}\n- Contribution repositories listed: ${result.rows.length}\n- Repository stars checked: ${list.length}\n- README changed: ${readme!==result.readme}\n- Resume source changed: ${Boolean(source && resume!==source)}\n${result.changes.map(s=>`- ${s}`).join('\n')}\n${result.warnings.length?'\nPreserved historical editorial counts:\n'+result.warnings.map(s=>`- ${s}`).join('\n'):''}\n`
console.log(summary)
if(process.env.GITHUB_STEP_SUMMARY)await appendFile(process.env.GITHUB_STEP_SUMMARY,summary)
