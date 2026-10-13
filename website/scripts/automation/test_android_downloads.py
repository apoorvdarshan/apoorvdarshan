import base64
import copy
from datetime import date, datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError, URLError
from http.client import IncompleteRead
import io
from unittest.mock import call, patch

import android_downloads as android
from mobile_downloads import combine

PACKAGE = 'com.example.app'
TODAY = date(2026, 10, 11)
CONFIG = {'bucket': 'pubsite_prod_123', 'apps': [
    {'package': PACKAGE, 'name': 'example', 'history_start': '2026-10-01',
     'metric_validation': 'Verified against cumulative new users'}]}


def report(rows, encoding='utf-16'):
    header = 'Date,Package name,Daily User Installs,Install events,Total User Installs\n'
    return gzip.compress((header + '\n'.join(','.join(map(str, r)) for r in rows) + '\n').encode(encoding))


class FakeClient:
    def __init__(self, rows=None):
        self.blob = report(rows if rows is not None else [
            ('2026-10-01', PACKAGE, 12, 15, 0), ('2026-10-02', PACKAGE, 8, 11, 0)])
        self.item = {'name': f'stats/installs/installs_{PACKAGE}_202610_overview.csv',
                     'generation': '1', 'size': str(len(self.blob)),
                     'md5Hash': base64.b64encode(hashlib.md5(self.blob).digest()).decode()}

    def listing(self):
        return [self.item, {**self.item, 'name': self.item['name'].replace('_overview', '_country')}]

    def report(self, item):
        return self.blob


class AndroidTests(unittest.TestCase):
    def test_utf16_and_utf8_sum_daily_users_not_legacy_zero_or_install_events(self):
        rows = [('2026-10-01', PACKAGE, 12, 15, 0), ('2026-10-02', PACKAGE, 8, 11, 0)]
        for encoding in ('utf-16', 'utf-8-sig'):
            days = android.read_report(report(rows, encoding), PACKAGE, '202610', TODAY)
            self.assertEqual(sum(r['user_installs'] for r in days.values()), 20)
        result = android.refresh(FakeClient(), CONFIG, {}, TODAY)['apps'][PACKAGE]
        self.assertEqual(result['first_time'], 20)
        self.assertEqual(result['install_events'], 26)
        self.assertEqual(len(result['reports']), 1)  # Never add a second dimension.

    def test_bad_rows_rejected(self):
        for row in [('2026-10-01', 'wrong.app', 1, 2, 0),
                    ('2026-09-30', PACKAGE, 1, 2, 0),
                    ('2026-10-11', PACKAGE, 1, 2, 0),
                    ('2026-10-01', PACKAGE, -1, 2, 0),
                    ('2026-10-01', PACKAGE, '', 2, 0)]:
            with self.assertRaises(ValueError):
                android.read_report(report([row]), PACKAGE, '202610', TODAY)
        row = ('2026-10-01', PACKAGE, 1, 2, 0)
        with self.assertRaisesRegex(ValueError, 'Duplicate day'):
            android.read_report(report([row, row]), PACKAGE, '202610', TODAY)
        with self.assertRaises(ValueError):
            android.read_report(b'Date,Units\n', PACKAGE, '202610', TODAY)

    def test_missing_start_gap_regressed_cutoff_and_missing_app_fail(self):
        for days in [['2026-10-02'], ['2026-10-01', '2026-10-03']]:
            with self.assertRaises(ValueError):
                android.refresh(FakeClient([(d, PACKAGE, 1, 2, 0) for d in days]), CONFIG, {}, TODAY)
        saved = android.refresh(FakeClient(), CONFIG, {}, TODAY)
        saved['apps'][PACKAGE]['as_of'] = '2026-10-03'
        with self.assertRaisesRegex(ValueError, 'regressed'):
            android.refresh(FakeClient(), CONFIG, saved, TODAY)
        with patch.object(FakeClient, 'listing', return_value=[]):
            with self.assertRaisesRegex(ValueError, 'Missing reports'):
                android.refresh(FakeClient(), CONFIG, {}, TODAY)

    def test_repeat_refresh_replaces_history_and_accepts_corrections(self):
        saved = android.refresh(FakeClient(), CONFIG, {}, TODAY)
        self.assertEqual(android.refresh(FakeClient(), CONFIG, saved, TODAY), saved)
        corrected = android.refresh(FakeClient([
            ('2026-10-01', PACKAGE, 5, 15, 0), ('2026-10-02', PACKAGE, 8, 11, 0)]), CONFIG, saved, TODAY)
        self.assertEqual(corrected['apps'][PACKAGE]['first_time'], 13)
        self.assertEqual(saved['apps'][PACKAGE]['first_time'], 20)

    def test_future_apps_discovered_privately_without_claiming_first_time_or_publication(self):
        result = android.refresh(FakeClient(), {**CONFIG, 'apps': []}, {}, TODAY)
        self.assertEqual(result['apps'][PACKAGE]['user_installs'], 20)
        self.assertNotIn('first_time', result['apps'][PACKAGE])
        self.assertNotIn('name', result['apps'][PACKAGE])
        self.assertEqual(android.refresh(FakeClient([]), {**CONFIG, 'apps': []}, {}, TODAY)['apps'], {})

    def test_pagination_and_repeated_cursors(self):
        client = object.__new__(android.Client)
        client.base = 'https://storage.googleapis.com/storage/v1/b/pubsite_prod_123/o'
        pages = [{'kind': 'storage#objects', 'items': [{'name': 'one'}], 'nextPageToken': 'next'},
                 {'kind': 'storage#objects', 'items': [{'name': 'two'}]}]
        with patch.object(client, 'request', side_effect=[json.dumps(p).encode() for p in pages]):
            self.assertEqual(len(client.listing()), 2)
        with patch.object(client, 'request', return_value=json.dumps(pages[0]).encode()):
            with self.assertRaisesRegex(ValueError, 'Repeated GCS'):
                client.listing()

    def test_size_and_checksum_rejected_before_parsing(self):
        client = object.__new__(android.Client)
        client.base = 'https://storage.googleapis.com/storage/v1/b/pubsite_prod_123/o'
        fake = FakeClient()
        for blob in (fake.blob[:-1], b'x' * len(fake.blob)):
            with patch.object(client, 'request', return_value=blob):
                with self.assertRaises(ValueError):
                    client.report(fake.item)

    def test_permission_diagnostic_does_not_expose_private_object_or_token(self):
        with patch.dict(os.environ, {'PLAY_REPORTS_ACCESS_TOKEN': 'secret-token'}):
            client = android.Client('pubsite_prod_123')
        body = {'error': {'message': 'secret-token lacks storage.objects.list on private-app-object',
                          'errors': [{'reason': 'forbidden'}]}}
        error = HTTPError(client.base, 403, 'Forbidden', {}, io.BytesIO(json.dumps(body).encode()))
        with patch.object(android, 'urlopen', side_effect=error) as request, \
             patch.object(android.time, 'sleep') as sleep:
            with self.assertRaises(RuntimeError) as caught:
                client.listing()
            request.assert_called_once()
            sleep.assert_not_called()  # Missing access will not heal in a few seconds.
        self.assertIn('403 forbidden storage.objects.list', str(caught.exception))
        self.assertNotIn('secret-token', str(caught.exception))
        self.assertNotIn('private-app-object', str(caught.exception))

    def test_temporary_errors_recover_without_accepting_partial_data(self):
        with patch.dict(os.environ, {'PLAY_REPORTS_ACCESS_TOKEN': 'test-token'}):
            client = android.Client('pubsite_prod_123')
        errors = [HTTPError(client.base, 429, 'Rate limited', {'Retry-After': '5'}, None),
                  HTTPError(client.base, 503, 'Unavailable', {}, None),
                  URLError('Offline'), TimeoutError(), ConnectionResetError(),
                  IncompleteRead(b'partial', 200)]
        for error in errors:
            with self.subTest(error=type(error).__name__), \
                 patch.object(android, 'urlopen', side_effect=[error, io.BytesIO(b'complete')]) as request, \
                 patch.object(android.time, 'sleep') as sleep:
                self.assertEqual(client.request(client.base), b'complete')
                self.assertEqual(request.call_count, 2)
                sleep.assert_called_once_with(5 if isinstance(error, HTTPError) and error.code == 429 else 2)

        # A connection can also break after headers, while reading the report body.
        class InterruptedBody(io.BytesIO):
            def read(self):
                raise IncompleteRead(b'partial', 200)

        with patch.object(android, 'urlopen', side_effect=[InterruptedBody(), io.BytesIO(b'complete')]), \
             patch.object(android.time, 'sleep'):
            self.assertEqual(client.request(client.base), b'complete')

    def test_retry_after_date_invalid_and_excessive_values_are_bounded(self):
        with patch.object(android, 'datetime') as clock:
            clock.now.return_value = datetime(2026, 10, 11, tzinfo=timezone.utc)
            self.assertEqual(android.retry_delay(0, {'Retry-After': 'Sun, 11 Oct 2026 00:00:30 GMT'}), 30)
        self.assertEqual(android.retry_delay(0, {'Retry-After': '999999'}), 60)
        self.assertEqual(android.retry_delay(0, {'Retry-After': 'invalid'}), 2)
        self.assertEqual(android.retry_delay(0, {'Retry-After': '-1'}), 2)

    def test_exhausted_network_retries_preserve_snapshot_and_allow_next_run_recovery(self):
        config = json.loads(Path(android.__file__).with_name('android-downloads.json').read_text())
        package = config['apps'][0]['package']
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'android-downloads.json'
            saved = {'version': 1, 'checked_on': '2026-10-10', 'config_sha256': android.fingerprint(config),
                     'apps': {package: {'first_time': 2579, 'as_of': '2026-10-07'}}}
            original = json.dumps(saved)
            path.write_text(original)
            env = {'PROFILE_RESUME_PATH': str(Path(folder) / 'resume.tex'),
                   'PLAY_REPORTS_ACCESS_TOKEN': 'test-token', 'PLAY_DOWNLOADS_FORCE': 'true'}
            with patch.dict(os.environ, env), \
                 patch.object(android, 'urlopen', side_effect=URLError('Offline')) as request, \
                 patch.object(android.time, 'sleep') as sleep:
                with self.assertRaisesRegex(RuntimeError, 'network request failed'):
                    android.main()
                self.assertEqual(request.call_count, 4)
                self.assertEqual(sleep.call_args_list, [call(2), call(4), call(8)])
            self.assertEqual(path.read_text(), original)
            self.assertFalse(path.with_name(path.name + '.tmp').exists())

            recovered = copy.deepcopy(saved)
            recovered['checked_on'] = android.datetime.now(android.timezone.utc).date().isoformat()
            recovered['apps'][package]['first_time'] = 2600
            with patch.dict(os.environ, env), patch.object(android, 'refresh', return_value=recovered):
                android.main()
            self.assertEqual(json.loads(path.read_text())['apps'][package]['first_time'], 2600)

    def test_api_failure_preserves_private_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'android-downloads.json'
            original = '{"version":1,"apps":{}}'
            path.write_text(original)
            with patch.dict(os.environ, {'PROFILE_RESUME_PATH': str(Path(folder) / 'resume.tex')}), \
                 patch.object(android, 'Client', side_effect=RuntimeError('API unavailable')):
                with self.assertRaises(RuntimeError): android.main()
            self.assertEqual(path.read_text(), original)

    def test_daily_cache_needs_no_token_and_force_retries(self):
        config = json.loads(Path(android.__file__).with_name('android-downloads.json').read_text())
        package = config['apps'][0]['package']
        with tempfile.TemporaryDirectory() as folder:
            saved = {'version': 1, 'checked_on': android.datetime.now(android.timezone.utc).date().isoformat(),
                     'config_sha256': android.fingerprint(config),
                     'apps': {package: {'first_time': 20, 'as_of': TODAY.isoformat()}}}
            (Path(folder) / 'android-downloads.json').write_text(json.dumps(saved))
            with patch.dict(os.environ, {'PROFILE_RESUME_PATH': str(Path(folder) / 'resume.tex'),
                                         'PLAY_DOWNLOADS_FORCE': 'false'}), \
                 patch.object(android, 'Client', side_effect=RuntimeError('No token')) as client:
                android.main()
                client.assert_not_called()
                # Owner-bootstrapped counts must not hide failures of the new cloud identity.
                with patch.dict(os.environ, {'PLAY_REPORTS_IDENTITY': 'reporting@example.com'}):
                    with self.assertRaises(RuntimeError): android.main()
                with patch.dict(os.environ, {'PLAY_DOWNLOADS_FORCE': 'true'}):
                    with self.assertRaises(RuntimeError): android.main()

    def test_combined_cached_ios_and_fresh_android_never_adds_redownloads(self):
        ios = {'apps': {'1': {'first_time': 7200, 'redownload': 358, 'as_of': '2026-10-09',
                              'other_platform_downloads': 2512},
                        '2': {'first_time': 1358, 'redownload': 99}}}
        original = copy.deepcopy(ios)
        configs = [{'id': '1', 'android_package': PACKAGE}, {'id': '2'}]
        play = {'version': 1, 'apps': {PACKAGE: {'first_time': 2579, 'as_of': '2026-10-07'}}}
        result = combine(ios, configs, play)
        self.assertEqual(result['apps']['1']['display_total'], 9779)
        self.assertEqual(result['apps']['1']['badge'], '9K+')
        self.assertEqual(result['apps']['1']['android_as_of'], '2026-10-07')
        self.assertEqual(result['apps']['2']['display_total'], 1358)
        self.assertEqual(combine(result, configs, play), result)
        self.assertEqual(ios, original)
        with self.assertRaises(ValueError): combine(ios, configs, {})


if __name__ == '__main__':
    unittest.main()
