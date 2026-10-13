"""Build changed private source, validate text/page bounds, then publish the PDF."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unicodedata
from defusedxml import ElementTree as ET

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def inspect(pdf):
    xml = subprocess.check_output(['pdftotext', '-bbox', str(pdf), '-'])
    root = ET.fromstring(xml)
    pages = list(root.iter('{http://www.w3.org/1999/xhtml}page'))
    assert pages, 'PDF has no pages'
    for page in pages:
        words = list(page.iter('{http://www.w3.org/1999/xhtml}word'))
        assert len(words) > 5, 'Blank or nearly blank page'
        for w in words:
            assert float(w.attrib['xMin']) >= 0 and float(w.attrib['yMin']) >= 0, 'Text outside page'
            assert float(w.attrib['xMax']) <= float(page.attrib['width']) + 1, 'Text clipped horizontally'
            assert float(w.attrib['yMax']) <= float(page.attrib['height']) + 1, 'Text clipped vertically'
    text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
    return len(pages), unicodedata.normalize('NFKC', text)

def main():
    source = Path(os.environ['PROFILE_RESUME_PATH']).resolve()
    destination = Path('public/Apoorv_Darshan_Resume.pdf').resolve()
    manifest_path = source.parent / 'build.json'
    pdf = source.with_suffix('.pdf')
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    source_hash = sha(source)
    if manifest.get('sourceSha256') != source_hash or not pdf.exists() or manifest.get('pdfSha256') != sha(pdf):
        old_pages = inspect(pdf)[0] if pdf.exists() else 4
        with tempfile.TemporaryDirectory(prefix='profile-resume-build-') as temp:
            result = subprocess.run(['tectonic', '--outdir', temp, str(source)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # Do not copy private source or TeX error excerpts into public Actions logs.
            if result.returncode:
                raise RuntimeError('Resume compilation failed; source and published PDF left untouched')
            built = Path(temp) / pdf.name
            pages, text = inspect(built)
            assert pages <= old_pages + 1, 'Unexpected page-count jump'
            assert 'Apoorv Darshan' in text and 'Open Source Contributions' in text, 'Missing required resume content'
            # Ensure each contribution survived compilation and character escaping.
            section = source.read_text().split(r'\section{Open Source Contributions}', 1)[1].split(r'\resumeSubHeadingListEnd', 1)[0]
            for name in re.findall(r'\\href\{[^}]+\}\{([^}]+)\}', section):
                name = name.replace(r'\_', '_').replace(r'\&', '&')
                assert name in text, f'Contribution missing from compiled PDF: {name}'
            # Render every page as a check that the PDF is consumable; images stay ephemeral.
            subprocess.run(['pdftoppm', '-scale-to', '1000', '-png', str(built), str(Path(temp) / 'page')], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            shutil.copy2(built, pdf)
        manifest = {'sourceSha256': source_hash, 'pdfSha256': sha(pdf), 'pages': pages}
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
        print(f'Resume rebuilt and validated: {pages} pages')
    else:
        inspect(pdf)
        print('Resume source unchanged; keeping the verified PDF')
    shutil.copy2(pdf, destination)

if __name__ == '__main__':
    main()
