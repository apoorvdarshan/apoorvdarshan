"""Daily lifetime npm package downloads using public, unauthenticated APIs."""
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from download_badges import badge, check, update_download_copy

API = 'https://api.npmjs.org/downloads/point/'
EARLIEST = date(2015, 1, 10)


def read_json(url):
    parsed = urlparse(url)
    check(parsed.scheme == 'https' and parsed.hostname in ('registry.npmjs.org', 'api.npmjs.org'), 'Unexpected npm API URL')
    # Never load npmrc or send a publishing token. Both endpoints are public.
    for attempt in range(3):
        try:
            request = Request(url, headers={'User-Agent': 'apoorvdarshan-profile-downloads', 'Accept': 'application/json'})
            with urlopen(request, timeout=30) as response:  # nosec B310 # fixed HTTPS hosts checked above
                return json.load(response)
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)


def point_url(package, period):
    # Scoped packages are requested individually; bulk requests do not support them.
    return API + period + '/' + quote(package, safe='@')


def point(data, package):
    check(data.get('package') == package, 'npm returned a different package')
    check(type(data.get('downloads')) is int and data['downloads'] >= 0, 'Invalid npm download count')
    start, end = date.fromisoformat(data['start']), date.fromisoformat(data['end'])
    check(start <= end, 'Invalid npm reporting interval')
    return start, end, data['downloads']


def windows(start, end):
    # Inclusive, non-overlapping intervals stay below npm's 18-month API limit.
    while start <= end:
        stop = min(end, start + timedelta(days=364))
        yield start, stop
        start = stop + timedelta(days=1)


def repository_url(value):
    if isinstance(value, dict):
        value = value.get('url', '')
    return str(value).removeprefix('git+').removesuffix('.git').rstrip('/').lower()


def refresh(config, today, fetch=read_json):
    packages = config['packages']
    latest = []
    for item in packages:
        package = item['package']
        check(re.fullmatch(r'(?:@[a-z0-9._-]+/)?[a-z0-9._-]+', package), 'Invalid configured npm name')
        metadata = fetch('https://registry.npmjs.org/' + quote(package, safe='@'))
        check(metadata.get('name') == package, 'npm registry name mismatch')
        check(repository_url(metadata.get('repository')) == repository_url(item['link']), 'npm repository mismatch')
        check(config['maintainer'] in [m.get('name') for m in metadata.get('maintainers', [])], 'npm maintainer mismatch')
        created = date.fromisoformat(metadata['time']['created'][:10])
        check(created.isoformat() == item['created'], 'npm creation date changed; retain verified counts')
        check(EARLIEST <= created < today, 'Lifetime npm history is unavailable for this creation date')
        start, end, _ = point(fetch(point_url(package, 'last-day')), package)
        check(start == end and created <= end < today, 'npm last-day report is not complete')
        latest.append(end)
    # All projects use the same available cutoff, even if npm is still processing yesterday.
    through = min(latest)
    result = {'version': 1, 'metric': 'lifetime npm package downloads',
              'checked_on': today.isoformat(), 'as_of': through.isoformat(), 'packages': {}}
    for item in packages:
        package, total, reports = item['package'], 0, []
        for start, end in windows(date.fromisoformat(item['created']), through):
            url = point_url(package, f'{start}:{end}')
            reported_start, reported_end, count = point(fetch(url), package)
            check((reported_start, reported_end) == (start, end), 'npm truncated the requested lifetime interval')
            total += count
            reports.append({'start': str(start), 'end': str(end), 'downloads': count, 'url': url})
        check(reports, 'No complete npm history available')
        result['packages'][package] = {'name': item['name'], 'created': item['created'],
                                       'downloads': total, 'badge': badge(total), 'reports': reports}
    return result


def main():
    today = datetime.now(timezone.utc).date()
    config = json.loads(Path(__file__).with_name('npm-downloads.json').read_text())
    fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    readme_path = Path(os.environ.get('PROFILE_README_PATH', '../README.md'))
    resume_path = Path(os.environ['PROFILE_RESUME_PATH'])
    snapshot_path = readme_path.parent / 'profile-automation/npm-downloads.json'
    saved = json.loads(snapshot_path.read_text()) if snapshot_path.exists() else {}
    if (saved.get('version') == 1 and saved.get('checked_on') == str(today)
            and saved.get('config_sha256') == fingerprint and os.environ.get('NPM_DOWNLOADS_FORCE') != 'true'):
        result = saved
        print('npm downloads already checked today; using verified totals.')
    else:
        result = refresh(config, today)
        result['config_sha256'] = fingerprint
        check(not saved.get('as_of') or result['as_of'] >= saved['as_of'], 'npm reporting cutoff moved backwards')
    check(set(result['packages']) == {p['package'] for p in config['packages']}, 'Incomplete npm snapshot')
    entries = [{**p, 'badge': badge(result['packages'][p['package']]['downloads'])} for p in config['packages']]
    readme, resume = update_download_copy(readme_path.read_text(), resume_path.read_text(), entries)
    # Validate every API response and both outputs before replacing any managed files.
    outputs = {readme_path: readme, resume_path: resume, snapshot_path: json.dumps(result, indent=2) + '\n'}
    for path, content in outputs.items():
        if not path.exists() or path.read_text() != content:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + '.tmp')
            temporary.write_text(content)
            temporary.replace(path)
    lines = [f'## npm lifetime downloads through {result["as_of"]}', '',
             '| Package | Downloads | Badge |', '| --- | ---: | --- |']
    for package, item in result['packages'].items():
        lines.append(f'| {package} | {item["downloads"]} | {item["badge"]} |')
    lines += ['', 'npm package downloads include repeat/automated downloads; these are not unique users.', '']
    summary = '\n'.join(lines)
    print(summary)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as output:
            output.write(summary)


if __name__ == '__main__':
    main()
