# Build and template interface

Install a FLOSS TeX Live distribution, Python 3 and Poppler (`pdftotext`).

```sh
python3 scripts/validate-template.py
mkdir -p /tmp/rekisei-build
pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode -output-directory=/tmp/rekisei-build resume.tex
pdftotext /tmp/rekisei-build/resume.pdf /tmp/rekisei-build/resume.txt
python3 scripts/validate-template.py /tmp/rekisei-build/resume.txt
```

Input: trusted `resume.tex` with placeholder name, contacts, education, experience
and project content. Output: `resume.pdf` and temporary TeX logs in the output
directory. Failure returns a nonzero process exit. Do not enable shell escape.
Macros and usage are described in AGENTS.md and the commented sample. PDF readers
are never launched by CI. Personal resumes and outreach files stay gitignored.

The Python validator performs static checks for dangerous TeX primitives,
required interfaces and accidental personal-file tracking, then validates text
extraction from the compiled sample. ChkTeX checks the template; stylistic rules
that conflict with intentional resume formatting are disabled in CI.
No memory-unsafe production implementation or network-facing service is shipped;
fuzzing a full TeX engine belongs upstream, not in this template project.

ChkTeX uses `-I0` to lint the project template only; upstream TeX inputs such as
`glyphtounicode` are resolved and checked by the separate pdfLaTeX compile.
CI uploads the compiled public sample PDF for visual verification.
