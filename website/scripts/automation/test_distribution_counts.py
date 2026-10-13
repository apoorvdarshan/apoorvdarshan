import unittest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import distribution_counts as d
from distribution_counts import chrome_count, release_count, update_copy


class DistributionTests(unittest.TestCase):
    def test_chrome_header_only_and_bounds(self):
        html = '<script>999 users</script><h1>Extension</h1>1,000+ users<h2>Overview</h2>500 users'
        result = chrome_count(html)
        self.assertEqual(result['count'], 1000)
        self.assertTrue(result['lower_bound'])
        for bad in ['Sign in', '12 users Overview 45 users'.replace('Overview', ''), '2 users 3 users Overview', '1,2 users Overview']:
            with self.assertRaises(ValueError):
                chrome_count(bad)
        self.assertEqual(chrome_count('4 users Overview')['count'], 4)
        self.assertEqual(chrome_count('0 users Overview')['count'], 0)

    def test_assets_paginate_filter_and_exclude_prereleases(self):
        item = {'repo': 'owner/app', 'asset_pattern': r'.*\.dmg$'}
        def fetch(url, github):
            if '/assets?' not in url:
                return [{'id': 1, 'draft': False, 'prerelease': False, 'tag_name': 'v1'},
                        {'id': 2, 'draft': False, 'prerelease': True, 'tag_name': 'preview'}]
            return [{'id': 1, 'name': 'app.dmg', 'download_count': 7, 'browser_download_url': 'https://example.com/app'},
                    {'id': 2, 'name': 'app.dmg.sha256', 'download_count': 5}]
        self.assertEqual(release_count(item, fetch)['count'], 7)
        def bad(url, github):
            data = fetch(url, github)
            if '/assets?' in url:
                data[0]['download_count'] = -1
            return data
        with self.assertRaises(ValueError):
            release_count(item, bad)

    def test_insert_replace_idempotent_and_keep_description(self):
        item = {'repo': 'owner/app', 'name': 'app'}
        readme = '<li><strong><a href="https://github.com/owner/app">app</a></strong> - Description</li>\n'
        resume = r'\resumeProjectHeading{\textbf{\href{https://github.com/owner/app}{app}} \textnormal{ -- Description}}{}'
        out = update_copy(readme, resume, item, '40+', True)
        self.assertIn('Users: 40+', out[0])
        self.assertIn('40+ users', out[1])
        self.assertEqual(update_copy(*out, item, '40+', True), out)
        changed = update_copy(*out, item, '3', True)
        self.assertIn('Users: 3', changed[0])
        self.assertNotIn('40+', changed[1])
        self.assertIn('Description', changed[1])
        with self.assertRaises(ValueError):
            update_copy(readme + readme, resume, item, '40+')

    def test_daily_cache_failure_preserves_source_and_recomposes_subtotals(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            audit = root / 'profile-automation'
            audit.mkdir()
            item = {'repo': 'owner/app', 'name': 'app', 'npm': 'app', 'asset_pattern': '.*', 'homebrew': 'owner/tap/app'}
            (root / 'distribution-counts.json').write_text(json.dumps({'releases': [item], 'extensions': []}))
            (root / 'ios-downloads.json').write_text(json.dumps({'apps': []}))
            npm = audit / 'npm-downloads.json'
            npm.write_text(json.dumps({'as_of': '2026-10-10', 'packages': {'app': {'downloads': 100}}}))
            readme, resume = root / 'README.md', root / 'resume.tex'
            readme.write_text('<li><strong><a href="https://github.com/owner/app">app</a></strong> - Description</li>')
            resume.write_text(r'\resumeProjectHeading{\textbf{\href{https://github.com/owner/app}{app}} \textnormal{ -- Description}}{}')
            env = {'PROFILE_README_PATH': str(readme), 'PROFILE_RESUME_PATH': str(resume), 'DISTRIBUTION_FORCE': 'true'}
            with patch.object(d, '__file__', str(root / 'distribution_counts.py')), patch.dict(os.environ, env):
                with patch.object(d, 'release_count', return_value={'count': 25}):
                    d.main()
                data = json.loads((audit / 'distribution-counts.json').read_text())
                self.assertEqual(data['sources']['releases:owner/app']['display_total'], 125)
                with patch.dict(os.environ, {'DISTRIBUTION_FORCE': 'false'}), patch.object(d, 'release_count', side_effect=AssertionError('cache not used')):
                    d.main()
                npm.write_text(json.dumps({'as_of': '2026-10-11', 'packages': {'app': {'downloads': 110}}}))
                with patch.object(d, 'release_count', side_effect=ValueError('upstream unavailable')), self.assertRaises(SystemExit):
                    d.main()
                row = json.loads((audit / 'distribution-counts.json').read_text())['sources']['releases:owner/app']
                self.assertEqual(row['count'], 25)
                self.assertEqual(row['display_total'], 135)
                self.assertEqual(row['checked_on'], data['sources']['releases:owner/app']['checked_on'])
                self.assertEqual(row['homebrew']['counted_via'], 'github_release_downloads')


if __name__ == '__main__':
    unittest.main()
