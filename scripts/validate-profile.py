"""Validate public profile structure, the resume build manifest and tracked files."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
s=Path('README.md').read_text()
# Sections documented in AGENTS.md that must appear exactly once. Matched at
# '##' or '###' so a heading level change does not break the check.
for section in [
    'Mobile Apps', 'Games', 'Chrome Extensions', 'AI & Agents',
    'Apps & Utilities', 'Web Apps & Tools', 'Creative, 3D & Vision',
    'Experiments & Fun', 'Open Source Contributions', 'What I Use', 'Connect',
]:
    pattern = r'^#{2,3} ' + re.escape(section) + r'\s*$'
    assert len(re.findall(pattern, s, re.M)) == 1, f'Invalid profile section: {section}'
for p in [*Path('profile-automation').glob('*.json'), *Path('resume').glob('*.json')]:
    json.loads(p.read_text())
manifest=json.loads(Path('resume/build.json').read_text())
for ext,key in [('tex','sourceSha256'),('pdf','pdfSha256')]:
    assert hashlib.sha256(Path('resume/Apoorv_Darshan_Resume.'+ext).read_bytes()).hexdigest()==manifest[key], 'Resume build manifest mismatch'
assert Path('resume/Apoorv_Darshan_Resume.pdf').read_bytes()==Path('website/public/Apoorv_Darshan_Resume.pdf').read_bytes(), 'Published resume PDF is not the verified build'
tracked=subprocess.check_output(['git','ls-files'],text=True).splitlines()
allowed_tex={'resume/template/resume.tex','resume/Apoorv_Darshan_Resume.tex'}
assert not any((p.endswith('.tex') and p not in allowed_tex) or 'private_key' in p.lower() or 'outreach' in p.lower() for p in tracked), 'Unexpected private file tracked'
for name in tracked:
    if Path(name).suffix in {'.md','.tex','.json','.yml','.yaml','.py','.mjs','.js'} and Path(name).is_file():
        text=Path(name).read_text(errors='ignore')
        assert '-----BEGIN '+'PRIVATE KEY-----' not in text and '-----BEGIN '+'RSA PRIVATE KEY-----' not in text and '-----BEGIN '+'OPENSSH PRIVATE KEY-----' not in text, 'Committed private key'
print('Public profile structure and snapshots validated.')
