const fs = require('fs');
const https = require('https');

const username = 'apoorvdarshan';
const readmePath = 'README.md';

function fetchLatestRepos(username, count = 3) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.github.com',
      path: `/users/${username}/repos?sort=updated&per_page=${count}`,
      headers: { 'User-Agent': 'node.js' }
    };

    https.get(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(JSON.parse(data)));
    }).on('error', reject);
  });
}

function updateReadme(repos) {
  const readme = fs.readFileSync(readmePath, 'utf8');
  const startMarker = '<!-- LATEST_REPOS_START -->';
  const endMarker = '<!-- LATEST_REPOS_END -->';

  const repoList = repos.map(repo => `- [${repo.name}](${repo.html_url})`).join('\n');
  const newContent = `${startMarker}\n${repoList}\n${endMarker}`;
  const updatedReadme = readme.replace(
    new RegExp(`${startMarker}[\\s\\S]*?${endMarker}`, 'm'),
    newContent
  );

  fs.writeFileSync(readmePath, updatedReadme, 'utf8');
  console.log('✅ README updated with latest repos.');
}

(async () => {
  const repos = await fetchLatestRepos(username);
  updateReadme(repos);
})();
