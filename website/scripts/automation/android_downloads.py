"""Daily account-wide Google Play install reports, using a short-lived OAuth token.

Only overview reports are summed, once per date. Detailed dimensions, the legacy
zero-filled Total User Installs column, updates and active audience are not totals.
The snapshot is public, so only validated, configured apps are read or saved;
other packages in the account are ignored without being logged.
"""
import base64
import csv
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import gzip
import hashlib
from http.client import IncompleteRead
import io
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from download_badges import check

OBJECT = re.compile(r'^stats/installs/installs_([A-Za-z0-9_.]+)_(\d{6})_overview\.csv$')
FIELDS = {'Daily User Installs': 'user_installs', 'Install events': 'install_events'}


def fingerprint(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def retry_delay(attempt, headers=None):
    delay = 2 ** (attempt + 1)
    retry_after = (headers or {}).get('Retry-After', '')
    try:
        if retry_after.isdigit():
            delay = max(delay, int(retry_after))
        elif retry_after:
            when = parsedate_to_datetime(retry_after)
            delay = max(delay, (when - datetime.now(timezone.utc)).total_seconds())
    except (ValueError, TypeError, OverflowError):
        pass
    return min(delay, 60)


def read_report(blob, package, month, today):
    if blob[:2] == b'\x1f\x8b':
        blob = gzip.decompress(blob)
    encoding = 'utf-16' if blob[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8-sig'
    reader = csv.DictReader(io.StringIO(blob.decode(encoding)))
    names = {n.strip().casefold(): n for n in reader.fieldnames or []}
    required = ['date', 'package name', *[n.casefold() for n in FIELDS]]
    check(all(n in names for n in required), 'Play install report columns changed')
    check(len(names) == len(reader.fieldnames), 'Duplicate Play report columns')
    days = {}
    for raw in reader:
        check(None not in raw and all(v is not None for v in raw.values()), 'Malformed Play CSV row')
        row = {k: raw[v].strip() for k, v in names.items()}
        check(row['package name'] == package, 'Unexpected package in Play report')
        day = date.fromisoformat(row['date'])
        check(day.strftime('%Y%m') == month and day < today, 'Unexpected Play report date')
        check(day.isoformat() not in days, 'Duplicate day in overview report')
        counts = {}
        for column, key in FIELDS.items():
            value = row[column.casefold()]
            check(re.fullmatch(r'\d+', value) is not None, 'Invalid Play install count')
            counts[key] = int(value)
        days[day.isoformat()] = counts
    return days


class Client:
    def __init__(self, bucket):
        check(re.fullmatch(r'pubsite_prod_(?:rev_)?\d+', bucket), 'Invalid Play report bucket')
        self.base = f'https://storage.googleapis.com/storage/v1/b/{bucket}/o'
        self.token = os.environ.get('PLAY_REPORTS_ACCESS_TOKEN')
        check(self.token, 'Missing short-lived Play reporting access token')

    def request(self, url):
        check(url.startswith(self.base), 'Unexpected report API URL')
        for attempt in range(4):
            try:
                headers = {'Authorization': 'Bearer ' + self.token, 'Accept-Encoding': 'gzip',
                           'User-Agent': 'apoorvdarshan-profile-downloads'}
                with urlopen(Request(url, headers=headers), timeout=60) as response:  # nosec B310 # HTTPS and API host validated above
                    return response.read()
            except HTTPError as error:
                if (error.code == 429 or error.code >= 500) and attempt < 3:
                    time.sleep(retry_delay(attempt, error.headers))
                    continue
                # Log only structured reasons and permission names, never the raw
                # response (which may contain private object names or signed URLs).
                detail = ''
                try:
                    payload = json.loads(error.read()).get('error', {})
                    reason = payload.get('errors', [{}])[0].get('reason', '')
                    if re.fullmatch(r'[A-Za-z0-9_]+', reason):
                        detail += ' ' + reason
                    denied = re.search(r'storage\.objects\.(?:list|get)', payload.get('message', ''))
                    if denied:
                        detail += ' ' + denied[0]
                except (ValueError, KeyError, IndexError, TypeError):
                    pass
                raise RuntimeError(f'Play reports HTTP {error.code}{detail}; keeping previous totals') from None
            except (URLError, TimeoutError, ConnectionError, IncompleteRead):
                if attempt < 3:
                    time.sleep(retry_delay(attempt))
                    continue
                raise RuntimeError('Play report network request failed') from None

    def listing(self):
        result, visited, token = [], set(), None
        while True:
            params = {'prefix': 'stats/installs/', 'maxResults': 1000}
            if token:
                params['pageToken'] = token
            blob = self.request(self.base + '?' + urlencode(params))
            if blob[:2] == b'\x1f\x8b':
                blob = gzip.decompress(blob)
            payload = json.loads(blob)
            check(payload.get('kind') == 'storage#objects' and not payload.get('error'), 'Invalid GCS listing')
            check(isinstance(payload.get('items', []), list), 'Invalid GCS objects')
            result.extend(payload.get('items', []))
            token = payload.get('nextPageToken')
            if not token:
                break
            check(token not in visited, 'Repeated GCS pagination cursor')
            visited.add(token)
        check(len({o['name'] for o in result}) == len(result), 'Duplicate GCS objects')
        return result

    def report(self, item):
        blob = self.request(self.base + '/' + quote(item['name'], safe='') + '?' +
                            urlencode({'alt': 'media', 'generation': item['generation']}))
        check(len(blob) == int(item['size']), 'Truncated Play report')
        check(base64.b64encode(hashlib.md5(blob, usedforsecurity=False).digest()).decode() == item['md5Hash'],
              'Play report checksum mismatch')
        return blob


def refresh(client, config, previous, today):
    objects = client.listing()
    packages = {}
    for item in objects:
        match = OBJECT.fullmatch(item['name'])
        if match:
            packages.setdefault(match[1], []).append((match[2], item))
    managed = {a['package']: a for a in config['apps']}
    check(len(managed) == len(config['apps']), 'Duplicate configured Android package')
    check(set(managed) <= packages.keys(), 'Missing reports for a configured Android app')
    check(set(previous.get('apps', {})) <= packages.keys(), 'Previously reported Android app disappeared')
    result = {'version': 1, 'checked_on': today.isoformat(), 'config_sha256': fingerprint(config),
              'metric': 'sum of Daily User Installs in complete overview report history', 'apps': {}}
    for package, reports in sorted(packages.items()):
        if package not in managed:
            continue  # Unconfigured (future/test) apps never enter the public snapshot.
        days, sources = {}, []
        for month, item in sorted(reports):
            incoming = read_report(client.report(item), package, month, today)
            check(not days.keys() & incoming.keys(), 'Overlapping Play report days')
            days.update(incoming)
            sources.append({'object': item['name'], 'generation': item['generation'],
                            'md5': item['md5Hash'], 'rows': len(incoming)})
        check(days, 'Android overview history is empty')
        first, last = min(days), max(days)
        expected_start = managed.get(package, {}).get('history_start', first)
        check(first == expected_start, 'Android history starts after/before the verified first report')
        check(len(days) == (date.fromisoformat(last) - date.fromisoformat(first)).days + 1,
              'Gap in Android daily history; retain previous totals')
        old = previous.get('apps', {}).get(package, {})
        check(not old or (first == old['history_start'] and last >= old['as_of']),
              'Android history regressed; retain previous totals')
        totals = {key: sum(row[key] for row in days.values()) for key in FIELDS.values()}
        entry = {'history_start': first, 'as_of': last, 'days': len(days), **totals, 'reports': sources,
                 'name': managed[package]['name'], 'first_time': totals['user_installs'],
                 'metric_validation': managed[package]['metric_validation']}
        result['apps'][package] = entry
    return result


def main():
    today = datetime.now(timezone.utc).date()
    config = json.loads(Path(__file__).with_name('android-downloads.json').read_text())
    path = Path(os.environ['PROFILE_RESUME_PATH']).parent / 'android-downloads.json'
    saved = json.loads(path.read_text()) if path.exists() else {}
    check(not saved or saved.get('version') == 1, 'Unsupported Android snapshot version')
    identity = os.environ.get('PLAY_REPORTS_IDENTITY', 'local-authorized-account')
    if (saved.get('checked_on') == today.isoformat() and saved.get('config_sha256') == fingerprint(config)
            and saved.get('reporting_identity', 'local-authorized-account') == identity
            and os.environ.get('PLAY_DOWNLOADS_FORCE') != 'true'):
        result = saved
        print('Android reports already checked today; using verified counts.')
    else:
        result = refresh(Client(config['bucket']), config, saved, today)
        result['reporting_identity'] = identity
    content = json.dumps(result, indent=2) + '\n'
    if not path.exists() or path.read_text() != content:
        temporary = path.with_name(path.name + '.tmp')
        temporary.write_text(content)
        temporary.replace(path)
    # Report configured apps only; never log other package identities.
    lines = ['## Android download reports', '', '| App | Data through | First-time installs |',
             '| --- | --- | ---: |']
    for app in config['apps']:
        row = result['apps'][app['package']]
        lines.append(f'| {app["name"]} | {row["as_of"]} | {row["first_time"]} |')
        if today - date.fromisoformat(row['as_of']) > timedelta(days=8):
            print(f'::warning::Play reports for {app["name"]} are over eight days old; keeping dated totals.')
    summary = '\n'.join(lines) + '\n'
    print(summary)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
            stream.write(summary)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'::error::Android download refresh failed ({type(error).__name__}): {error}')
        raise SystemExit(1)
