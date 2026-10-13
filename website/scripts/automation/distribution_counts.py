"""Daily public distribution events and Chrome users, with independent cached sources.

npm + release assets count requests, not unique installs. Homebrew casks fetch
these same release assets, so Homebrew is attribution, never an additional sum.
"""
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse

from download_badges import badge, check


def fetch(url, github=False):
    parsed = urlparse(url)
    check(parsed.scheme == 'https' and parsed.hostname in ('api.github.com', 'chromewebstore.google.com'), 'Unexpected distribution API URL')
    headers = {'User-Agent': 'apoorvdarshan-profile-metrics', 'Accept-Language': 'en-US,en;q=0.9'}
    if github:
        check(url.startswith('https://api.github.com/'), 'Unexpected authenticated host')
        headers['Accept'] = 'application/vnd.github+json'
        if os.environ.get('GH_TOKEN'):
            headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    for attempt in range(4):
        try:
            with urlopen(Request(url, headers=headers), timeout=30) as response:  # nosec B310 # fixed HTTPS hosts checked above
                text = response.read().decode('utf-8')
            return json.loads(text) if github else text
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
        except (URLError, TimeoutError, ConnectionError):
            if attempt == 3:
                raise
        time.sleep(2 ** attempt)


def release_count(item, request=fetch):
    assets, seen = [], set()
    for page in range(1, 1001):
        url = f'https://api.github.com/repos/{item["repo"]}/releases?per_page=100&page={page}'
        releases = request(url, github=True)
        check(isinstance(releases, list), 'Invalid release response')
        for release in releases:
            if release['draft'] or release['prerelease']:
                continue
            # GitHub's embedded assets list can be paginated separately.
            for asset_page in range(1, 1001):
                endpoint = f'https://api.github.com/repos/{item["repo"]}/releases/{release["id"]}/assets?per_page=100&page={asset_page}'
                batch = request(endpoint, github=True)
                check(isinstance(batch, list), 'Invalid asset response')
                for asset in batch:
                    if not re.fullmatch(item['asset_pattern'], asset['name']):
                        continue
                    check(asset['id'] not in seen, 'Duplicate release asset')
                    seen.add(asset['id'])
                    count = asset['download_count']
                    check(type(count) is int and count >= 0, 'Invalid asset download count')
                    assets.append({'id': asset['id'], 'name': asset['name'], 'tag': release['tag_name'],
                                   'downloads': count, 'url': asset['browser_download_url']})
                if len(batch) < 100:
                    break
            else:
                raise ValueError('Asset pagination limit exceeded')
        if len(releases) < 100:
            break
    else:
        raise ValueError('Release pagination limit exceeded')
    return {'count': sum(a['downloads'] for a in assets), 'assets': assets,
            'metric': 'downloads of available stable release assets',
            'url': f'https://github.com/{item["repo"]}/releases'}


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
    def handle_data(self, text):
        if not self.hidden:
            self.parts.append(text)


def chrome_count(html):
    parser = VisibleText()
    parser.feed(html)
    text = ' '.join(parser.parts)
    # Only listing header, not recommendations/reviews/description prose.
    check('Overview' in text, 'Missing public listing overview')
    header = text.split('Overview', 1)[0]
    matches = re.findall(r'(?<![\w.,])([0-9][0-9,]*)(\+?)\s+users\b', header)
    check(len(matches) == 1, 'Missing or ambiguous public Chrome user count')
    number, lower_bound = matches[0]
    check(re.fullmatch(r'\d+|\d{1,3}(,\d{3})+', number), 'Invalid Chrome count formatting')
    return {'count': int(number.replace(',', '')), 'lower_bound': bool(lower_bound), 'metric': 'Chrome Web Store users'}


def update_copy(readme, resume, item, label, users=False):
    link = 'https://github.com/' + item['repo']
    kind = 'Users' if users else 'Downloads'
    image_url = (f'https://apoorvdarshan.com/badges/users/v1/{quote(label, safe="")}.svg'
                 if users else f'https://apoorvdarshan.com/badges/downloads/v1/{quote(label, safe="")}.svg')
    image = f'<img alt="{kind}: {label}" src="{image_url}">'
    rows = readme.splitlines(keepends=True)
    indices = [i for i, row in enumerate(rows) if f'<strong><a href="{link}">' in row]
    check(len(indices) == 1, 'Expected one README project: ' + item['name'])
    i = indices[0]
    pattern = r'<img\b[^>]*alt="(?:Downloads|Users): [^"]*"[^>]*>'
    if re.search(pattern, rows[i]):
        rows[i], count = re.subn(pattern, lambda _: image, rows[i])
        check(count == 1, 'Duplicate metric badge')
    else:
        check(' - ' in rows[i], 'Missing project description boundary')
        rows[i] = rows[i].replace(' - ', ' ' + image + ' - ', 1)
    readme = ''.join(rows)
    rows = resume.splitlines(keepends=True)
    indices = [i for i, row in enumerate(rows) if row.lstrip().startswith(r'\resumeProjectHeading') and '\\href{' + link + '}' in row]
    check(len(indices) == 1, 'Expected one resume project: ' + item['name'])
    i = indices[0]
    display = label + (' users' if users else '')
    pattern = r'(\\textcolor\{Maroon\}\{\$\\downarrow\$ )[^}]+'
    if re.search(pattern, rows[i]):
        rows[i], count = re.subn(pattern, lambda m: m[1] + display, rows[i])
        check(count == 1, 'Duplicate resume metric')
    else:
        check(r' \textnormal{' in rows[i], 'Missing resume description boundary')
        rows[i] = rows[i].replace(r' \textnormal{', r' $|$ {\small \textcolor{Maroon}{$\downarrow$ ' + display + r'}} \textnormal{', 1)
    return readme, ''.join(rows)


def main():
    config = json.loads(Path(__file__).with_name('distribution-counts.json').read_text())
    readme_path = Path(os.environ.get('PROFILE_README_PATH', '../README.md'))
    resume_path = Path(os.environ['PROFILE_RESUME_PATH'])
    snapshot_path = readme_path.parent / 'profile-automation/distribution-counts.json'
    saved = json.loads(snapshot_path.read_text()) if snapshot_path.exists() else {'version': 1, 'sources': {}}
    today = datetime.now(timezone.utc).date().isoformat()
    npm = json.loads((snapshot_path.parent / 'npm-downloads.json').read_text())
    ios = json.loads((resume_path.parent / 'ios-downloads.json').read_text())
    mobile_configs = json.loads(Path(__file__).with_name('ios-downloads.json').read_text())['apps']
    readme, resume = readme_path.read_text(), resume_path.read_text()
    errors = []
    for kind, items in [('releases', config['releases']), ('extensions', config['extensions'])]:
        for item in items:
            key = kind + ':' + item['repo']
            previous = saved['sources'].get(key)
            fingerprint = hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()
            try:
                if (previous and previous.get('checked_on') == today and previous.get('config_sha256') == fingerprint
                        and os.environ.get('DISTRIBUTION_FORCE') != 'true'):
                    result = dict(previous)
                else:
                    if kind == 'releases':
                        result = release_count(item)
                    else:
                        check(re.fullmatch('[a-p]{32}', item['id']), 'Invalid store ID')
                        check(re.fullmatch('[a-z0-9-]+', item['slug']), 'Invalid store slug')
                        url = 'https://chromewebstore.google.com/detail/' + item['slug'] + '/' + item['id'] + '?hl=en'
                        result = {**chrome_count(fetch(url)), 'url': url}
                    result.update(checked_on=today, config_sha256=fingerprint)
            except Exception as error:
                errors.append(f'{key}: {type(error).__name__}: {error}')
                if not previous or previous.get('config_sha256') != fingerprint:
                    continue
                result = dict(previous)
            total = result['count']
            breakdown = {'github_release_downloads': total} if kind == 'releases' else {'chrome_users': total}
            if item.get('npm'):
                number = npm['packages'][item['npm']]['downloads']
                check(type(number) is int and number >= 0, 'Invalid saved npm count')
                total += number
                breakdown['npm_downloads'] = number
                result['npm_as_of'] = npm['as_of']
            if item.get('mobile'):
                c = next(c for c in mobile_configs if c['name'] == item['name'])
                row = ios['apps'][c['id']]
                number = row['display_total']
                check(type(number) is int and number >= 0, 'Invalid saved mobile count')
                total += number
                breakdown['store_first_time_downloads'] = number
            if item.get('homebrew'):
                result['homebrew'] = {'package': item['homebrew'], 'counted_via': 'github_release_downloads',
                                      'note': 'Cask fetches the same GitHub assets; never add Homebrew installs again.'}
            label = badge(total)
            result.update(display_total=total, badge=label, breakdown=breakdown)
            readme, resume = update_copy(readme, resume, item, label, kind == 'extensions')
            saved['sources'][key] = result
    saved['note'] = 'Download events include repeat, CI and updater requests, not unique users. npm installers may fetch GitHub assets too. Homebrew is included only via shared GitHub assets. Deleted releases cannot be reconstructed. Chrome users are separate.'
    for path, text in [(readme_path, readme), (resume_path, resume), (snapshot_path, json.dumps(saved, indent=2) + '\n')]:
        if not path.exists() or path.read_text() != text:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_name(path.name + '.tmp')
            temp.write_text(text)
            temp.replace(path)
    for key, row in saved['sources'].items():
        print(key, row['breakdown'], '=>', row['badge'], 'checked', row['checked_on'])
    if errors:
        for error in errors:
            print('::warning::' + error)
        raise SystemExit('Some distribution sources failed; retained verified values where available.')


if __name__ == '__main__':
    main()
