"""Daily lifetime PyPI downloads from public, keyless sources.

Source: pepy.tech's documented public badge endpoint, /personalized-badge/<project>
with period=total and units=none, returns the exact all-time total of PyPI's
BigQuery download logs (every file and version, mirrors and CI included) without
a key. pepy's JSON API needs an API key, so it is not used. pypistats.org's keyless
API has the same daily counts (its with_mirrors rows) but keeps only 180 days, so
its sum would undercount any project older than that. PyPI's own JSON and Index
APIs pin each project's name, repository and owner before a count is accepted.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from defusedxml import ElementTree

from download_badges import badge, check, upsert_download_copy

CONFIG = Path(__file__).with_name('pypi-downloads.json')
PYPI = 'https://pypi.org'
PEPY = 'https://api.pepy.tech/personalized-badge/'
INDEX = 'application/vnd.pypi.simple.v1+json'
LABEL = 'downloads'
SVG = '{http://www.w3.org/2000/svg}'
# pepy imports the previous day's downloads once a day, so a new project gets a week to appear there.
PEPY_GRACE = timedelta(days=7)
LIMIT = 4_000_000
METRIC = 'lifetime PyPI downloads'
NOTE = ('pepy.tech all-time totals of PyPI download logs: every file and version, including mirrors, CI and '
        'repeat downloads, so not unique users. pepy imports the previous day once a day and caches badges '
        'for 12 hours, so a total trails PyPI by about one to two days.')


class NotFound(Exception):
    """The source has no such project (HTTP 404)."""


def read(url, accept):
    parsed = urlparse(url)
    check(parsed.scheme == 'https' and parsed.hostname in ('pypi.org', 'api.pepy.tech'), 'Unexpected PyPI source URL')
    # Public endpoints only: no PyPI token, pepy API key, cookie or other credential is ever sent.
    request = Request(url, headers={'User-Agent': 'apoorvdarshan-profile-downloads', 'Accept': accept})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:  # nosec B310 # fixed HTTPS hosts checked above
                kind = response.headers.get('Content-Type', '')
                body = response.read(LIMIT + 1)
            check(len(body) <= LIMIT, 'Oversized PyPI source response')
            return kind, body.decode('utf-8')
        except HTTPError as error:
            if error.code == 404:
                raise NotFound(url) from None
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (URLError, TimeoutError, ConnectionError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)


def normalize(name):
    # PEP 503: names are case-insensitive and runs of '-', '_' and '.' are equivalent.
    return re.sub(r'[-_.]+', '-', name).lower()


def same_link(url, link):
    return isinstance(url, str) and url.strip().removesuffix('.git').rstrip('/').lower() == link.rstrip('/').lower()


def document(fetch, url, accept='application/json'):
    kind, text = fetch(url, accept)
    check(kind.split(';')[0].strip().lower() == accept, 'Unexpected PyPI response type')
    data = json.loads(text)
    check(isinstance(data, dict), 'Unexpected PyPI response')
    return data


def first_upload(index, project):
    check(normalize(str(index.get('name', ''))) == project, 'PyPI index returned a different project')
    files = index.get('files')
    check(isinstance(files, list) and files, 'PyPI lists no files for ' + project)
    dates = []
    for item in files:
        value = item.get('upload-time') if isinstance(item, dict) else None
        check(isinstance(value, str), 'PyPI file without an upload time')
        moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
        check(moment.tzinfo is not None, 'PyPI upload time without a time zone')
        dates.append(moment.astimezone(timezone.utc).date())
    return min(dates)


def pepy_total(kind, text):
    check(kind.split(';')[0].strip().lower() == 'image/svg+xml', 'Unexpected pepy badge type')
    root = ElementTree.fromstring(text)
    check(root.tag == SVG + 'svg', 'Unexpected pepy badge')
    values = [''.join(node.itertext()).strip() for node in root.iter(SVG + 'text')]
    numbers = {value for value in values if value != LABEL}
    # The label and the count are each drawn twice (shadow and text); anything else is a format change.
    check(LABEL in values and len(numbers) == 1, 'Unexpected pepy badge text')
    number = numbers.pop()
    check(re.fullmatch(r'0|[1-9][0-9]{0,15}', number), 'pepy badge total is not an exact integer')
    return int(number)


def refresh(item, today, verified, fetch=read):
    """(row, None) for a verified count, or (None, reason) while the project is not countable yet."""
    project = normalize(item['project'])
    check(re.fullmatch(r'[a-z0-9]([a-z0-9-]*[a-z0-9])?', project), 'Invalid configured PyPI name')
    try:
        data = document(fetch, f'{PYPI}/pypi/{project}/json')
    except NotFound:
        # A pending trusted publisher creates the project only at the first upload.
        check(not verified, f'PyPI no longer lists {project}; retain verified count')
        return None, 'not on PyPI yet'
    info = data.get('info') or {}
    check(normalize(str(info.get('name', ''))) == project, 'PyPI returned a different project')
    urls = info.get('project_urls') or {}
    check(isinstance(urls, dict) and any(same_link(url, item['link']) for url in urls.values()),
          'PyPI project URLs do not name the configured repository')
    roles = (data.get('ownership') or {}).get('roles') or []
    check(any(isinstance(role, dict) and role.get('role') == 'Owner' and
              str(role.get('user', '')).lower() == item['owner'].lower() for role in roles), 'PyPI owner mismatch')
    first = first_upload(document(fetch, f'{PYPI}/simple/{project}/', INDEX), project)
    check(first <= today, 'PyPI upload time is in the future')
    url = f'{PEPY}{project}?period=total&units=none&left_text={LABEL}'
    waiting = f'on PyPI since {first}; waiting for pepy.tech to add its downloads'
    try:
        total = pepy_total(*fetch(url, 'image/svg+xml'))
    except NotFound:
        check(not verified and today - first <= PEPY_GRACE, f'pepy.tech has no downloads for {project}')
        return None, waiting
    if total == 0:
        # Never show a 0 badge: it appears with the first download (pepy also lists new projects before
        # importing their first day).
        return None, waiting if not verified and today - first <= PEPY_GRACE else 'no downloads yet'
    return {'name': item['name'], 'link': item['link'], 'owner': item['owner'], 'first_upload': str(first),
            'downloads': total, 'badge': badge(total), 'checked_on': str(today), 'source': url,
            'pypi': f'{PYPI}/project/{project}/'}, None


def utc_today():
    return datetime.now(timezone.utc).date()


def main():
    today = utc_today()
    config = json.loads(CONFIG.read_text())
    readme_path = Path(os.environ.get('PROFILE_README_PATH', '../README.md'))
    resume_path = Path(os.environ['PROFILE_RESUME_PATH'])
    snapshot_path = readme_path.parent / 'profile-automation/pypi-downloads.json'
    saved = json.loads(snapshot_path.read_text()) if snapshot_path.exists() else {'version': 1}
    check(saved.get('version') == 1, 'Unknown PyPI snapshot version')
    force = os.environ.get('PYPI_DOWNLOADS_FORCE') == 'true'
    keys = [normalize(item['project']) for item in config['projects']]
    check(len(keys) == len(set(keys)), 'Duplicate configured PyPI project')
    readme, resume = readme_path.read_text(), resume_path.read_text()
    projects, pending, errors = {}, {}, []
    for key, item in zip(keys, config['projects']):
        fingerprint = hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()
        previous = saved.get('projects', {}).get(key)
        if (previous and previous.get('checked_on') == str(today) and previous.get('config_sha256') == fingerprint
                and not force):
            row = previous
        else:
            try:
                row, reason = refresh(item, today, bool(previous), fetch=read)
            except Exception as error:
                # Keep the last verified count (and its README tile); the final health check reports this.
                errors.append(f'{key}: {type(error).__name__}: {error}')
                if previous:
                    projects[key] = previous
                continue
            if not row:
                # Nothing to count yet: no tile is added, and the run is not a failure.
                pending[key] = reason
                continue
            row['config_sha256'] = fingerprint
        projects[key] = row
        readme, resume = upsert_download_copy(readme, resume, item, badge(row['downloads']))
    result = {'version': 1, 'metric': METRIC, 'note': NOTE, 'projects': projects}
    if pending:
        result['pending'] = pending
    # Every response and both outputs are validated before any managed file is replaced.
    outputs = {readme_path: readme, resume_path: resume, snapshot_path: json.dumps(result, indent=2) + '\n'}
    for path, content in outputs.items():
        if not path.exists() or path.read_text() != content:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + '.tmp')
            temporary.write_text(content)
            temporary.replace(path)
    lines = [f'## PyPI lifetime downloads, checked {today}', '',
             '| Project | Downloads | Badge | Status |', '| --- | ---: | --- | --- |']
    failed = {error.split(':', 1)[0] for error in errors}
    for key, row in projects.items():
        status = f'check failed; kept the count verified {row["checked_on"]}' if key in failed else f'verified {row["checked_on"]}'
        lines.append(f'| {key} | {row["downloads"]} | {row["badge"]} | {status} |')
    for key in sorted(failed - set(projects)):
        lines.append(f'| {key} | - | - | check failed; no verified count yet |')
    for key, reason in pending.items():
        lines.append(f'| {key} | - | - | pending, no badge: {reason} |')
    lines += ['', NOTE, '']
    summary = '\n'.join(lines)
    print(summary)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as output:
            output.write(summary)
    for key, reason in pending.items():
        print(f'::notice::{key}: {reason}. Its profile badge appears once pepy.tech reports a total.')
    if errors:
        for error in errors:
            print('::warning::' + error)
        raise SystemExit('Some PyPI download checks failed; retained verified values where available.')


if __name__ == '__main__':
    main()
