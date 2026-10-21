from datetime import date, timedelta
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import pypi_downloads as pypi

TODAY = date(2026, 10, 25)
ITEM = {'name': 'example-tool', 'project': 'Example_Tool', 'owner': 'apoorvdarshan',
        'link': 'https://github.com/apoorvdarshan/example-tool'}
# pepy.tech's personalized badge (period=total, units=none) as served on 2026-10-21, with its count replaced.
BADGE = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="150" height="20">'
         '<linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
         '<stop offset="1" stop-opacity=".1"/></linearGradient><clipPath id="r"><rect width="150" height="20" rx="3" '
         'fill="#fff"/></clipPath><g clip-path="url(#r)" transform="scale(1)"><rect width="69" height="20" '
         'fill="000000"/><rect x="69" width="81" height="20" fill="#97ca00"/><rect width="150" height="20" '
         'fill="url(#s)"/></g><g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" '
         'text-rendering="geometricPrecision" font-size="110" transform="scale(1)"><image '
         'xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" visibility="hidden" x="5" '
         'y="3" width="14" height="14" xlink:href=""/><text x="355" y="150" fill="#010101" fill-opacity=".3" '
         'transform="scale(.1)" textLength="590">{label}</text><text x="355" y="140" transform="scale(.1)" '
         'textLength="590">{label}</text><text x="1085" y="150" fill="#010101" fill-opacity=".3" '
         'transform="scale(.1)" textLength="710">{shadow}</text><text x="1085" y="140" transform="scale(.1)" '
         'textLength="710">{count}</text></g></svg>')


def svg(count, shadow=None, label='downloads'):
    return BADGE.format(count=count, shadow=count if shadow is None else shadow, label=label)


class FakeAPI:
    def __init__(self, downloads=1234, published=True, on_pepy=True, owner='ApoorvDarshan', role='Owner',
                 urls=None, uploads=('2026-10-22T09:30:00.123456Z', '2026-10-24T10:00:00Z'), name='Example-Tool'):
        self.downloads, self.published, self.on_pepy = downloads, published, on_pepy
        self.owner, self.role, self.uploads, self.name = owner, role, uploads, name
        self.urls = {'Source': ITEM['link'] + '/'} if urls is None else urls
        self.calls = []

    def __call__(self, url, accept):
        self.calls.append(url)
        if url == 'https://pypi.org/pypi/example-tool/json':
            if not self.published:
                raise pypi.NotFound(url)
            return 'application/json', json.dumps({
                'info': {'name': self.name, 'project_urls': self.urls},
                'ownership': {'organization': None, 'roles': [{'role': self.role, 'user': self.owner}]}})
        if url == 'https://pypi.org/simple/example-tool/':
            assert accept == pypi.INDEX
            return pypi.INDEX + '; charset=utf-8', json.dumps({'meta': {'api-version': '1.4'}, 'name': 'example-tool',
                'files': [{'filename': f'example_tool-0.{i}.tar.gz', 'upload-time': moment}
                          for i, moment in enumerate(self.uploads)]})
        if url == 'https://api.pepy.tech/personalized-badge/example-tool?period=total&units=none&left_text=downloads':
            if not self.on_pepy:
                raise pypi.NotFound(url)
            return 'image/svg+xml', svg(self.downloads)
        raise AssertionError('Unexpected URL ' + url)


class Response:
    def __init__(self, body, kind):
        self.body, self.headers = body, {'Content-Type': kind}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.body[:limit]


class PypiDownloadTests(unittest.TestCase):
    def test_exact_lifetime_total_after_pinning_name_repository_and_owner(self):
        api = FakeAPI()
        row, reason = pypi.refresh(ITEM, TODAY, False, api)
        self.assertIsNone(reason)
        self.assertEqual((row['downloads'], row['badge'], row['first_upload']), (1234, '1K+', '2026-10-22'))
        self.assertEqual(row['pypi'], 'https://pypi.org/project/example-tool/')
        self.assertIn('period=total&units=none', row['source'])
        self.assertEqual(len(api.calls), 3)
        self.assertEqual(pypi.refresh(ITEM, TODAY, True, FakeAPI(downloads=0)), (None, 'no downloads yet'))

    def test_another_owner_repository_or_project_is_rejected(self):
        for change in [{'owner': 'someone-else'}, {'role': 'Maintainer'}, {'name': 'other-tool'},
                       {'urls': {'Source': 'https://github.com/someone/example-tool'}}, {'urls': {}},
                       {'uploads': ()}, {'uploads': ('2026-10-22T09:30:00',)}, {'uploads': ('2026-10-26T00:00:00Z',)}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                pypi.refresh(ITEM, TODAY, False, FakeAPI(**change))

    def test_unpublished_project_waits_but_a_vanished_one_fails(self):
        self.assertEqual(pypi.refresh(ITEM, TODAY, False, FakeAPI(published=False)), (None, 'not on PyPI yet'))
        with self.assertRaises(ValueError):
            pypi.refresh(ITEM, TODAY, True, FakeAPI(published=False))

    def test_pepy_gets_one_week_to_add_a_new_project(self):
        row, reason = pypi.refresh(ITEM, TODAY, False, FakeAPI(on_pepy=False))
        self.assertIsNone(row)
        self.assertIn('since 2026-10-22', reason)
        for today, verified in [(date(2026, 10, 22) + timedelta(days=8), False), (TODAY, True)]:
            with self.subTest(today=today, verified=verified), self.assertRaises(ValueError):
                pypi.refresh(ITEM, today, verified, FakeAPI(on_pepy=False))
        # A zero is never published as a badge: before pepy's first import it waits, later it has no downloads yet.
        self.assertEqual(pypi.refresh(ITEM, TODAY, False, FakeAPI(downloads=0)), (None, reason))
        self.assertEqual(pypi.refresh(ITEM, date(2026, 10, 30), False, FakeAPI(downloads=0)), (None, 'no downloads yet'))

    def test_badge_must_hold_one_exact_integer(self):
        self.assertEqual(pypi.pepy_total('image/svg+xml', svg(4463106311)), 4463106311)
        self.assertEqual(pypi.pepy_total('image/svg+xml; charset=utf-8', svg(0)), 0)
        bad = [svg('1.2k'), svg('4,463'), svg('12', shadow='13'), svg('12', label='downloads/month'), svg('012'),
               '<svg xmlns="http://www.w3.org/2000/svg"/>', '<html><text>12</text></html>',
               '<!DOCTYPE svg [<!ENTITY n "12">]><svg xmlns="http://www.w3.org/2000/svg"><text>&n;</text></svg>']
        for text in bad:
            with self.subTest(text=text[-80:]), self.assertRaises(ValueError):
                pypi.pepy_total('image/svg+xml', text)
        with self.assertRaises(ValueError):
            pypi.pepy_total('application/json', svg(12))

    def test_requests_stay_public_retry_temporary_errors_and_report_missing_projects(self):
        seen = []
        def respond(request, **kwargs):
            seen.append(request)
            if len(seen) == 1:
                raise HTTPError(request.full_url, 503, 'unavailable', {}, None)
            if 'missing' in request.full_url:
                raise HTTPError(request.full_url, 404, 'not found', {}, None)
            return Response(b'{"ok": true}', 'application/json')
        with patch.object(pypi, 'urlopen', side_effect=respond), patch.object(pypi.time, 'sleep'):
            self.assertEqual(pypi.read('https://pypi.org/pypi/example-tool/json', 'application/json'),
                             ('application/json', '{"ok": true}'))
            with self.assertRaises(pypi.NotFound):
                pypi.read('https://api.pepy.tech/personalized-badge/missing', 'image/svg+xml')
        self.assertEqual(len(seen), 3)
        self.assertTrue(all(not r.has_header('Authorization') and not r.has_header('Cookie') for r in seen))
        for url in ['http://pypi.org/pypi/x/json', 'https://api.pepy.tech.example.com/x', 'https://pepy.tech/api/v2/projects/x']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                pypi.read(url, 'application/json')
        with patch.object(pypi, 'urlopen', return_value=Response(b'x' * (pypi.LIMIT + 1), 'application/json')):
            with self.assertRaises(ValueError):
                pypi.read('https://pypi.org/pypi/example-tool/json', 'application/json')

    def test_tile_goes_after_stars_and_resume_count_is_optional(self):
        readme = ('<li>🚀 <strong><a href="https://github.com/apoorvdarshan/example-tool">example-tool</a></strong> '
                  '<img alt="Stars" src="stars"> - Ship - apps</li>\n<li>Other - entry</li>\n')
        resume = r'\resumeProjectHeading{\textbf{\href{https://github.com/apoorvdarshan/other}{other}} \textnormal{ -- x}}{}'
        out = pypi.upsert_download_copy(readme, resume, ITEM, '10+')
        self.assertIn('<img alt="Stars" src="stars"> <img alt="Downloads: 10+" '
                      'src="https://apoorvdarshan.com/badges/downloads/v1/10%2B.svg"> - Ship - apps</li>', out[0])
        self.assertEqual(out[1], resume)
        self.assertEqual(pypi.upsert_download_copy(*out, ITEM, '10+'), out)
        self.assertEqual(pypi.upsert_download_copy(*out, ITEM, '20+')[0].count('Downloads: 20+'), 1)
        listed = resume + '\n' + r'\resumeProjectHeading{\textbf{\href{' + ITEM['link'] + r'}{example-tool}} \textnormal{ -- Ship}}{}'
        changed = pypi.upsert_download_copy(readme, listed, ITEM, '10+')[1]
        self.assertIn(r'{example-tool}} $|$ {\small \textcolor{Maroon}{$\downarrow$ 10+}} \textnormal{ -- Ship}', changed)
        self.assertIn(r'$\downarrow$ 20+}', pypi.upsert_download_copy(readme, changed, ITEM, '20+')[1])
        for text, other in [(readme + readme, resume), (readme, listed + '\n' + listed),
                            (readme.replace(' - Ship - apps', ' Ship apps'), resume)]:
            with self.subTest(text=text[:40]), self.assertRaises(ValueError):
                pypi.upsert_download_copy(text, other, ITEM, '10+')

    def test_configured_projects_are_explicit(self):
        config = json.loads(pypi.CONFIG.read_text())
        self.assertTrue(config['projects'])
        for item in config['projects']:
            self.assertEqual(set(item), {'name', 'project', 'owner', 'link'})
            self.assertEqual(pypi.normalize(item['project']), item['project'])
            self.assertTrue(item['link'].startswith('https://github.com/apoorvdarshan/'))

    def run_main(self, root, api, today=TODAY, force='false'):
        env = {'PROFILE_README_PATH': str(root / 'README.md'), 'PROFILE_RESUME_PATH': str(root / 'resume.tex'),
               'PYPI_DOWNLOADS_FORCE': force, 'GITHUB_STEP_SUMMARY': ''}
        config = root / 'pypi-downloads.json'
        config.write_text(json.dumps({'projects': [ITEM]}))
        with patch.dict(os.environ, env), patch.object(pypi, 'read', api), patch.object(pypi, 'CONFIG', config), \
             patch.object(pypi, 'utc_today', return_value=today):
            pypi.main()

    def test_main_adds_the_tile_once_published_and_keeps_counts_on_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            readme, resume = root / 'README.md', root / 'resume.tex'
            readme.write_text(f'<li><strong><a href="{ITEM["link"]}">example-tool</a></strong> - Keep description</li>\n')
            resume.write_text(r'\resumeProjectHeading{\textbf{\href{https://github.com/apoorvdarshan/other}{other}} \textnormal{ -- x}}{}' + '\n')
            snapshot = root / 'profile-automation/pypi-downloads.json'
            before = [readme.read_text(), resume.read_text()]
            # A first check that fails adds nothing and fails the step.
            with self.assertRaises(SystemExit):
                self.run_main(root, FakeAPI(owner='someone-else'))
            self.assertEqual([readme.read_text(), resume.read_text()], before)
            self.assertEqual(json.loads(snapshot.read_text())['projects'], {})
            # Not uploaded yet: a successful run that changes no copy and records why.
            self.run_main(root, FakeAPI(published=False))
            self.assertEqual([readme.read_text(), resume.read_text()], before)
            self.assertEqual(json.loads(snapshot.read_text())['pending'], {'example-tool': 'not on PyPI yet'})
            self.assertEqual(json.loads(snapshot.read_text())['projects'], {})
            self.run_main(root, FakeAPI(downloads=57))
            self.assertIn('<img alt="Downloads: 50+" src="https://apoorvdarshan.com/badges/downloads/v1/50%2B.svg"> - Keep description', readme.read_text())
            self.assertEqual(resume.read_text(), before[1])
            saved = json.loads(snapshot.read_text())
            self.assertNotIn('pending', saved)
            self.assertEqual(saved['projects']['example-tool']['downloads'], 57)
            outputs = [p.read_text() for p in (readme, resume, snapshot)]
            # The same UTC day reuses the verified check without any request.
            unused = FakeAPI(published=False)
            self.run_main(root, unused)
            self.assertEqual(unused.calls, [])
            self.assertEqual([p.read_text() for p in (readme, resume, snapshot)], outputs)
            # Forced or next-day failures retain the last verified count and tile, then fail the step.
            for api, today, force in [(FakeAPI(published=False), TODAY, 'true'), (FakeAPI(on_pepy=False), TODAY + timedelta(days=1), 'false'),
                                      (FakeAPI(owner='someone-else'), TODAY + timedelta(days=1), 'false')]:
                with self.subTest(today=today, force=force), self.assertRaises(SystemExit):
                    self.run_main(root, api, today, force)
                self.assertEqual([p.read_text() for p in (readme, resume, snapshot)], outputs)
            self.run_main(root, FakeAPI(downloads=140), TODAY + timedelta(days=1))
            self.assertIn('Downloads: 100+', readme.read_text())
            self.assertEqual(readme.read_text().count('alt="Downloads:'), 1)


if __name__ == '__main__':
    unittest.main()
