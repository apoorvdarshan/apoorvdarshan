"""Validate public profile structure and prevent private-source tracking."""
import json
from pathlib import Path
import subprocess
s=Path('README.md').read_text()
for section in ['My Agent Setup', 'Mobile Apps', 'Open Source Contributions']:
    assert s.count('## ' + section) == 1, 'Invalid profile section'
for p in Path('profile-automation').glob('*.json'):
    json.loads(p.read_text())
tracked=subprocess.check_output(['git','ls-files'],text=True).splitlines()
assert not any((p.endswith('.tex') and p != 'resume/template/resume.tex') or 'private_key' in p.lower() for p in tracked)
print('Public profile structure and snapshots validated.')
