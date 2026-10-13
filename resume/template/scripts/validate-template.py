"""Static TeX security/interface checks and compiled PDF regression validation."""
from pathlib import Path
import re
import subprocess
import sys
text=Path('resume.tex').read_text()
assert r'\begin{document}' in text and r'\end{document}' in text
for primitive in [r'\write18', r'\openout', r'\readline', r'\immediate\write']:
    assert primitive not in text, 'Unexpected file/command primitive'
for macro in ['resumeProjectHeading','resumeSubheading','resumeItem']:
    assert '\\newcommand{\\'+macro+'}' in text, 'Missing template interface'
tracked=subprocess.check_output(['git','ls-files'],text=True).splitlines()
assert not any(p.endswith('Apoorv_Darshan_Resume.tex') or Path(p).name.startswith('outreach-') for p in tracked)
if len(sys.argv)>1:
    output=Path(sys.argv[1]).read_text()
    for expected in ['Your Name','Education','Experience']:
        assert expected in output, 'Compiled PDF missing required text'
    assert len(output.strip())>300, 'Compiled PDF unexpectedly empty'
print('Template security and regression checks passed.')
