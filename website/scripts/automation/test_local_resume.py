"""Exercise backup and conflict behavior without touching the user's files."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('local_sync', Path(__file__).with_name('sync-local-resume.py'))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class LocalResumeSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        state = root / 'state'
        repo = root / 'profile' / 'resume'
        targets = [root / 'rekisei', root / 'Documents']
        for folder in [state, repo, *targets]:
            folder.mkdir(parents=True)
        for ext in ['.tex', '.pdf']:
            (repo / (sync.NAME + ext)).write_bytes(b'cloud-' + ext.encode())
            for folder in targets:
                (folder / (sync.NAME + ext)).write_bytes(b'previous-' + ext.encode())
        self.patches = [
            patch.object(sync, 'HOME_DIR', root),
            patch.object(sync, 'STATE_DIR', state),
            patch.object(sync, 'STATE_FILE', state / 'state.json'),
            patch.object(sync, 'BACKUP_DIR', state / 'resume-backups'),
            patch.object(sync, 'REPO', repo.parent),
            patch.object(sync, 'RESUME', repo),
            patch.object(sync, 'TARGETS', targets),
            patch.object(sync.subprocess, 'check_output', side_effect=self.git_output),
            patch.object(sync.subprocess, 'run'),
            patch.object(sync.sys, 'argv', ['sync-local-resume.py']),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.branch, self.status = 'main\n', ''
        sync.STATE_FILE.write_text(json.dumps(sync.snapshot()))
        self.original = sync.snapshot()
        (repo / 'build.json').write_text(json.dumps({
            'sourceSha256': sync.digest(repo / (sync.NAME + '.tex')),
            'pdfSha256': sync.digest(repo / (sync.NAME + '.pdf')),
        }))

    def git_output(self, args, **_):
        return self.branch if 'branch' in args else self.status

    def test_updates_all_copies_with_dated_backups_and_is_idempotent(self):
        sync.main()
        for folder in sync.TARGETS:
            for ext in ['.tex', '.pdf']:
                self.assertEqual(sync.digest(folder / (sync.NAME + ext)), sync.digest(sync.RESUME / (sync.NAME + ext)))
        backup_root = sync.BACKUP_DIR
        backups = list(backup_root.iterdir())
        self.assertEqual(len(backups), 1)
        for original, digest in self.original.items():
            path = Path(original)
            self.assertEqual(sync.digest(backups[0] / path.parent.name / path.name), digest)
        sync.main()
        self.assertEqual(len(list(backup_root.iterdir())), 1)

    def test_local_edit_stops_all_destination_writes(self):
        edited = sync.TARGETS[-1] / (sync.NAME + '.pdf')
        edited.write_bytes(b'local edit')
        before = sync.snapshot()
        with self.assertRaisesRegex(RuntimeError, 'Local edits'):
            sync.main()
        self.assertEqual(sync.snapshot(), before)
        self.assertFalse(sync.BACKUP_DIR.exists())

    def test_bad_manifest_stops_all_destination_writes(self):
        (sync.RESUME / (sync.NAME + '.pdf')).write_bytes(b'unverified output')
        with self.assertRaisesRegex(RuntimeError, 'build manifest'):
            sync.main()
        self.assertEqual(sync.snapshot(), self.original)

    def test_dirty_checkout_stops_before_pull(self):
        self.status = ' M resume/Apoorv_Darshan_Resume.tex'
        with self.assertRaisesRegex(RuntimeError, 'local edits'):
            sync.main()
        sync.subprocess.run.assert_not_called()

    def test_feature_branch_checkout_stops_before_pull(self):
        self.branch = 'feature\n'
        with self.assertRaisesRegex(RuntimeError, 'not on main'):
            sync.main()
        sync.subprocess.run.assert_not_called()
        self.assertEqual(sync.snapshot(), self.original)


if __name__ == '__main__':
    unittest.main()
