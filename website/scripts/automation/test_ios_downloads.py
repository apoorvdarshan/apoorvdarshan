import copy
from datetime import date
import gzip
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import ios_downloads as ios

HEADER = 'Date\tApp Apple Identifier\tDownload Type\tCounts\n'

def report(*rows):
    return gzip.compress((HEADER + '\n'.join('\t'.join(map(str, r)) for r in rows) + '\n').encode())

def state():
    return {'history_start': '2026-01-01',
            'baseline': {'through': '2026-09-11', 'counts': {'first_time': 100, 'redownload': 5}},
            'days': {}, 'seen_instances': {}, 'imported_snapshots': []}

class FakeClient:
    def __init__(self, historical=False, fail=False):
        self.historical, self.fail, self.fetched = historical, fail, []

    def listing(self, path):
        if path.startswith('apps/'):
            r = [{'id': 'ongoing', 'attributes': {'accessType': 'ONGOING', 'stoppedDueToInactivity': False}}]
            if self.historical:
                r.append({'id': 'snapshot', 'attributes': {'accessType': 'ONE_TIME_SNAPSHOT'}})
            return r
        if '/reports?' in path:
            return [{'id': path.split('/')[1], 'attributes': {'name': 'App Downloads Standard'}}]
        if '/instances?' in path:
            sid = path.split('/')[1]
            return [{'id': sid, 'attributes': {'granularity': 'DAILY', 'processingDate': '2026-10-11'}}]
        raise AssertionError(path)

    def instance(self, instance, app_id):
        self.fetched.append(instance['id'])
        if self.fail:
            raise RuntimeError('Unavailable segment')
        if instance['id'] == 'snapshot':
            return {'2026-01-01': dict(ios.zero(), first_time=90),
                    '2026-10-09': dict(ios.zero(), first_time=12)}
        return {'2026-10-09': dict(ios.zero(), first_time=12),
                '2026-10-10': dict(ios.zero(), first_time=2)}

class DownloadTests(unittest.TestCase):
    def test_all_segments_and_identical_rows_are_added_within_one_instance(self):
        rows = [('2026-10-09', '123', 'First-time download', 2)]
        blobs = [report(*rows), report(*rows, ('2026-10-09', '123', 'Redownload', 3),
                                       ('2026-10-09', '123', 'Auto-update', 500))]
        self.assertEqual(ios.read_segments(blobs, '123')['2026-10-09'],
                         {'first_time': 4, 'redownload': 3})

    def test_newest_whole_date_partition_wins_in_any_order(self):
        days = {}
        newer = {'2026-10-09': dict(ios.zero(), first_time=3)}
        older = {'2026-10-09': dict(ios.zero(), first_time=7, redownload=8)}
        ios.merge_instance(days, newer, '2026-10-11', 'new')
        ios.merge_instance(days, older, '2026-10-10', 'old')
        ios.merge_instance(days, newer, '2026-10-11', 'new')
        self.assertEqual(days['2026-10-09']['counts'], newer['2026-10-09'])
        # Corrections can reduce a first-time count to zero.
        ios.merge_instance(days, {'2026-10-09': dict(ios.zero(), updates=5)}, '2026-10-12', 'correction')
        self.assertEqual(days['2026-10-09']['counts']['first_time'], 0)

    def test_baseline_not_double_counted_and_incomplete_day_excluded(self):
        app = state()
        for day, n in [('2026-09-11', 99), ('2026-09-12', 10), ('2026-10-10', 88)]:
            ios.merge_instance(app['days'], {day: dict(ios.zero(), first_time=n)}, '2026-10-11', day)
        self.assertEqual(ios.totals(app, '2026-10-09')['first_time'], 110)

    def test_badge_floors_and_separate_android_count(self):
        for count, label in [(0, '0'), (9, '9'), (19, '10+'), (35, '30+'), (188, '100+'),
                             (999, '900+'), (1358, '1K+'), (9712, '9K+'), (10001, '10K+')]:
            self.assertEqual(ios.badge(count), label)
        snap = ios.publish_snapshot({'apps': {'123': state()}},
                                    [{'id':'123','name':'example','other_platform_downloads':2000}],
                                    '2026-10-09', date(2026,10,11))
        self.assertEqual(snap['apps']['123']['display_total'], 2100)
        self.assertEqual(snap['apps']['123']['ios_total_downloads'], 105)

    def test_delayed_reports_do_not_publish_incomplete_next_day(self):
        app = state()
        app['complete_through'] = '2026-10-08'
        ios.merge_instance(app['days'], {'2026-10-09': dict(ios.zero(), first_time=99)}, '2026-10-10', 'late')
        snap = ios.publish_snapshot({'apps': {'123': app}}, [{'id':'123','name':'example'}],
                                    '2026-10-09', date(2026,10,11))
        self.assertEqual(snap['apps']['123']['first_time'], 100)
        self.assertEqual(snap['apps']['123']['as_of'], '2026-10-08')

    def test_wrong_app_unknown_type_negative_and_bad_schema_rejected(self):
        for rows in [[('2026-10-09', 'other', 'First-time download', 1)],
                     [('2026-10-09', '123', 'Unknown', 1)],
                     [('2026-10-09', '123', 'First-time download', -1)]]:
            with self.assertRaises(ValueError): ios.read_segments([report(*rows)], '123')
        with self.assertRaises(ValueError): ios.read_segments([b'Date\tUnits\n'], '123')

    def test_configured_copy_only_and_exactly_one_match(self):
        app = {'id':'123','name':'example','link':'https://example.com'}
        readme = 'Header\n<li><strong><a href="https://example.com">example</a></strong> <img alt="Downloads: 1K+" src="old"> - Leave prose</li>\nOther row\n'
        resume = 'Header\n' + r'\resumeProjectHeading{\textbf{\href{https://example.com}{example}} \textcolor{Maroon}{$\downarrow$ 1K+} -- Leave prose}{}' + '\nFooter\n'
        new, tex = ios.update_copy(readme, resume, [app], {'apps':{'123':{'badge':'2K+'}}})
        self.assertIn('Downloads: 2K+', new)
        self.assertIn('https://apoorvdarshan.com/badges/downloads/v1/2K%2B.svg', new)
        self.assertEqual(tex, resume.replace('1K+', '2K+'))
        self.assertIn('Leave prose', new)
        with self.assertRaises(ValueError): ios.update_copy(readme+readme, resume, [app], {'apps':{'123':{'badge':'2K+'}}})

    def test_rerun_does_not_fetch_or_count_instance_twice(self):
        client = FakeClient()
        result = ios.refresh_app(client, '123', state(), date(2026,10,11))
        again = ios.refresh_app(client, '123', result, date(2026,10,12))
        self.assertEqual(client.fetched, ['ongoing'])
        self.assertEqual(ios.totals(again, '2026-10-09')['first_time'], 112)

    def test_full_snapshot_replaces_legacy_baseline_without_adding_it(self):
        result = ios.refresh_app(FakeClient(historical=True), '123', state(), date(2026,10,11))
        self.assertEqual(result['baseline']['through'], '2023-12-31')
        self.assertEqual(ios.totals(result, '2026-10-09')['first_time'], 102)
        self.assertEqual(result['imported_snapshots'], ['snapshot'])

    def test_gap_requires_full_history_and_snapshot_can_recover_it(self):
        old = state()
        old['checked_on'] = '2026-08-01'
        with self.assertRaisesRegex(ValueError, 'retention gap'):
            ios.refresh_app(FakeClient(), '123', old, date(2026,10,11))
        result = ios.refresh_app(FakeClient(historical=True), '123', old, date(2026,10,11))
        self.assertEqual(ios.totals(result, '2026-10-09')['first_time'], 102)

    def test_failed_segment_keeps_previous_history(self):
        old = state()
        original = copy.deepcopy(old)
        with self.assertRaises(RuntimeError):
            ios.refresh_app(FakeClient(fail=True), '123', old, date(2026,10,11))
        self.assertEqual(old, original)

    def test_incomplete_pagination_is_not_treated_as_no_new_data(self):
        client = object.__new__(ios.Client)
        with patch.object(client, 'request', return_value=json.dumps({'data':[], 'meta':{'paging':{'total':1}}}).encode()):
            with self.assertRaisesRegex(ValueError, 'Incomplete ASC pagination'):
                client.listing('apps')

    def test_later_app_failure_writes_none_of_the_managed_files(self):
        config = json.loads(Path(ios.__file__).with_name('ios-downloads.json').read_text())
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            history = {'version': 1, 'apps': {a['id']: state() for a in config['apps']}}
            originals = {'ios-download-history.json': json.dumps(history),
                         'ios-downloads.json': '{}', 'README.md': 'unchanged readme',
                         'resume.tex': 'unchanged resume'}
            for name, content in originals.items():
                (root / name).write_text(content)
            with patch.dict(os.environ, {'PROFILE_README_PATH': str(root / 'README.md'),
                                         'PROFILE_RESUME_PATH': str(root / 'resume.tex')}), \
                 patch.object(ios, 'Client'), \
                 patch.object(ios, 'refresh_app', side_effect=[state(), RuntimeError('Apple unavailable')]):
                with self.assertRaises(RuntimeError): ios.main()
            for name, content in originals.items():
                self.assertEqual((root / name).read_text(), content)

if __name__ == '__main__':
    unittest.main()
