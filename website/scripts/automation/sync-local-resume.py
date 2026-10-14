"""Pull the cloud-built resume into local copies, without overwriting local edits."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HOME_DIR = Path.home()
STATE_DIR = HOME_DIR / '.local/share/profile-automation'
STATE_FILE = STATE_DIR / 'local-resume-state.json'
BACKUP_DIR = STATE_DIR / 'resume-backups'
REPO = HOME_DIR / 'apoorvdarshan'
RESUME = REPO / 'resume'
NAME = 'Apoorv_Darshan_Resume'
# Documents files link into this checkout's resume/ folder. Background Python cannot
# access the TCC-protected Documents directory, so it never reads or writes through it.
TARGETS = []  # Documents symlinks point directly to the verified checkout.

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def snapshot():
    return {str(folder / (NAME + ext)): digest(folder / (NAME + ext))
            for folder in TARGETS for ext in ['.tex', '.pdf'] if (folder / (NAME + ext)).exists()}

def atomic_copy(source, target):
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.resume-', delete=False) as temp:
        pending = Path(temp.name)
    try:
        shutil.copy2(source, pending)
        os.replace(pending, target)
    finally:
        pending.unlink(missing_ok=True)

def main():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if '--initialize' in sys.argv:
        if STATE_FILE.exists():
            raise RuntimeError('Already initialized; will not discard local-edit protection')
        STATE_FILE.write_text(json.dumps(snapshot(), indent=2) + '\n')
        print('Recorded existing local resume hashes')
        return
    # flock is available on macOS through Python even though the shell utility is absent.
    import fcntl
    with (STATE_DIR / 'sync.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        previous = json.loads(STATE_FILE.read_text())
        # Shared working checkout: only fast-forward a clean main, never a feature branch.
        if subprocess.check_output(['git', '-C', str(REPO), 'branch', '--show-current'], text=True).strip() != 'main':
            raise RuntimeError('Profile checkout is not on main; sync skipped')
        if subprocess.check_output(['git', '-C', str(REPO), 'status', '--porcelain'], text=True).strip():
            raise RuntimeError('Profile checkout has local edits; sync skipped')
        subprocess.run(['git', '-C', str(REPO), 'pull', '--ff-only'], check=True, timeout=90)
        manifest = json.loads((RESUME / 'build.json').read_text())
        for ext, key in [('.tex', 'sourceSha256'), ('.pdf', 'pdfSha256')]:
            if digest(RESUME / (NAME + ext)) != manifest[key]:
                raise RuntimeError('Cloud source/PDF pair does not match its build manifest')
        changed=[]
        for folder in TARGETS:
            for ext in ['.tex', '.pdf']:
                target=folder / (NAME + ext)
                source=RESUME / (NAME + ext)
                if target.exists() and digest(target)==digest(source):
                    continue
                if target.exists() and digest(target)!=previous.get(str(target)):
                    raise RuntimeError(f'Local edits detected in {target}; keeping local files intact')
                changed.append((source,target))
        if changed:
            stamp=datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')
            backup=BACKUP_DIR / stamp
            for source,target in changed:
                if target.exists():
                    old=backup / target.parent.name / target.name
                    old.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(target,old)
                atomic_copy(source,target)
            print(f'Synced {len(changed)} local resume files; previous copies in {backup}')
        else:
            print('Local resume copies already current')
        STATE_FILE.write_text(json.dumps(snapshot(),indent=2)+'\n')

if __name__ == '__main__':
    main()
