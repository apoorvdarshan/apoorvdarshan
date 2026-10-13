import copy
from datetime import date, datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import unquote, urlparse

import npm_downloads as npm

TODAY = date(2026, 10, 11)
CONFIG = {'maintainer': 'apoorvdarshan', 'packages': [
    {'name': 'one', 'package': 'one', 'created': '2026-09-01', 'link': 'https://github.com/apoorvdarshan/one'},
    {'name': 'two', 'package': '@apoorvdarshan/two', 'created': '2026-09-15', 'link': 'https://github.com/apoorvdarshan/two'},
]}


class FakeAPI:
    def __init__(self, config=CONFIG):
        self.items = {p['package']: p for p in config['packages']}
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        if url.startswith('https://registry.npmjs.org/'):
            package = unquote(url.split('https://registry.npmjs.org/')[1])
            item = self.items[package]
            return {'name': package, 'repository': {'url': 'git+' + item['link'] + '.git'},
                    'maintainers': [{'name': 'apoorvdarshan'}], 'time': {'created': item['created'] + 'T12:00:00Z'}}
        period, package = url.removeprefix(npm.API).split('/', 1)
        package = unquote(package)
        start, end = ('2026-10-10', '2026-10-10') if period == 'last-day' else period.split(':')
        count = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
        return {'package': package, 'start': start, 'end': end, 'downloads': count}


class NpmDownloadTests(unittest.TestCase):
    def test_total_starts_at_publication_and_handles_scoped_packages(self):
        api = FakeAPI()
        result = npm.refresh(CONFIG, TODAY, api)
        self.assertEqual(result['packages']['one']['downloads'], 40)
        self.assertEqual(result['packages']['@apoorvdarshan/two']['downloads'], 26)
        self.assertEqual(result['packages']['one']['badge'], '40+')
        self.assertTrue(any('@apoorvdarshan%2Ftwo' in url for url in api.calls))
        # A second refresh recomputes totals rather than adding to yesterday's totals.
        self.assertEqual(npm.refresh(CONFIG, TODAY, api), result)

    def test_long_history_windows_cover_every_day_once_including_leap_day(self):
        start, end = date(2023, 1, 1), date(2026, 10, 10)
        days = []
        for first, last in npm.windows(start, end):
            self.assertLessEqual((last - first).days + 1, 365)
            days += [first + timedelta(days=i) for i in range((last - first).days + 1)]
        self.assertEqual(len(days), len(set(days)))
        self.assertEqual(days, [start + timedelta(days=i) for i in range((end - start).days + 1)])
        config = copy.deepcopy(CONFIG)
        config['packages'][0]['created'] = str(start)
        result = npm.refresh(config, TODAY, FakeAPI(config))
        self.assertEqual(result['packages']['one']['downloads'], len(days))

    def test_delayed_data_uses_a_common_completed_cutoff(self):
        api = FakeAPI()
        def delayed(url):
            data = api(url)
            if '/last-day/@' in url:
                data['start'] = data['end'] = '2026-10-09'
            return data
        result = npm.refresh(CONFIG, TODAY, delayed)
        self.assertEqual(result['as_of'], '2026-10-09')
        self.assertEqual(result['packages']['one']['downloads'], 39)

    def test_truncated_ranges_wrong_package_and_invalid_counts_are_rejected(self):
        for change in [{'end': '2026-10-09'}, {'package': 'other'}, {'downloads': -1}, {'downloads': True}, {'downloads': 1.5}]:
            api = FakeAPI()
            def broken(url):
                data = api(url)
                if '/point/2026' in url:
                    data.update(change)
                return data
            with self.subTest(change=change), self.assertRaises(ValueError):
                npm.refresh(CONFIG, TODAY, broken)

    def test_package_identity_and_creation_date_are_pinned(self):
        for change in [{'repository': 'https://github.com/another/one'}, {'maintainers': []},
                       {'time': {'created': '2026-09-02T12:00:00Z'}}]:
            api = FakeAPI()
            def broken(url):
                data = api(url)
                if urlparse(url).hostname == 'registry.npmjs.org':
                    data.update(change)
                return data
            with self.subTest(change=change), self.assertRaises(ValueError):
                npm.refresh(CONFIG, TODAY, broken)

    def test_public_requests_retry_temporary_errors_without_credentials(self):
        seen = []
        def respond(request, **kwargs):
            seen.append(request)
            if len(seen) == 1:
                raise HTTPError(request.full_url, 429, 'rate limited', {}, None)
            return io.StringIO('{"ok": true}')
        with patch.object(npm, 'urlopen', side_effect=respond), patch.object(npm.time, 'sleep'):
            self.assertEqual(npm.read_json(npm.point_url('one', 'last-day')), {'ok': True})
        self.assertEqual(len(seen), 2)
        self.assertTrue(all(not r.has_header('Authorization') for r in seen))

    def fixture(self, root, config):
        readme = root / 'README.md'
        resume = root / 'resume.tex'
        readme.write_text('\n'.join(f'<li><strong><a href="{p["link"]}">{p["name"]}</a></strong> <img alt="Downloads: 1K+" src="old"> - Keep description</li>' for p in config['packages']))
        resume.write_text('\n'.join(r'\resumeProjectHeading{\textbf{\href{' + p['link'] + r'}{example}} \textcolor{Maroon}{$\downarrow$ 1K+} -- Keep description}{}' for p in config['packages']))
        return readme, resume

    def test_main_daily_cache_updates_only_configured_copy_and_failure_is_atomic(self):
        config = json.loads(Path(npm.__file__).with_name('npm-downloads.json').read_text())
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            readme, resume = self.fixture(root, config)
            before = [readme.read_text(), resume.read_text()]
            env = {'PROFILE_README_PATH': str(readme), 'PROFILE_RESUME_PATH': str(resume),
                   'NPM_DOWNLOADS_FORCE': 'false', 'GITHUB_STEP_SUMMARY': ''}
            with patch.dict(os.environ, env), patch.object(npm, 'datetime') as clock:
                clock.now.return_value = datetime(2026, 10, 11, tzinfo=timezone.utc)
                with patch.object(npm, 'refresh', side_effect=RuntimeError('last package unavailable')):
                    with self.assertRaises(RuntimeError): npm.main()
                self.assertEqual([readme.read_text(), resume.read_text()], before)
                self.assertFalse((root / 'profile-automation/npm-downloads.json').exists())
                with patch.object(npm, 'refresh', return_value=npm.refresh(config, TODAY, FakeAPI(config))):
                    npm.main()
                paths = [readme, resume, root / 'profile-automation/npm-downloads.json']
                saved = [p.read_text() for p in paths]
                with patch.object(npm, 'refresh', side_effect=AssertionError('Unexpected repeat API fetch')):
                    npm.main()
                self.assertEqual([p.read_text() for p in paths], saved)
                self.assertIn('https://apoorvdarshan.com/badges/downloads/v1/', saved[0])
                self.assertEqual(saved[0].count('Keep description'), len(config['packages']))
                with patch.dict(os.environ, {'NPM_DOWNLOADS_FORCE': 'true'}), \
                     patch.object(npm, 'refresh', side_effect=RuntimeError('offline')):
                    with self.assertRaises(RuntimeError): npm.main()
                self.assertEqual([p.read_text() for p in paths], saved)


if __name__ == '__main__':
    unittest.main()
