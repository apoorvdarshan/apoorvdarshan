> Public sample template preserved from Rekisei. Personal resume source is maintained separately and is not included here.

# rekisei


A reusable agent skill for editing a **clean, concise LaTeX resume (1–2 pages preferred — your call)** by chatting — works with [Claude Code](https://claude.com/claude-code) and [Codex](https://github.com/openai/codex) via `AGENTS.md`.

Built on the [Jake's Resume](https://github.com/jakegut/resume) base, plus a skill file that teaches the agent how to add projects, update star counts, manage honors, optionally make project / open-source names clickable (linking to repos and merged PRs), and keep the layout tight — and a workflow that recompiles + renders and verifies the PDF after every edit.

## Quick start

1. Clone the repo:
   ```bash
   git clone https://github.com/apoorvdarshan/apoorvdarshan.git
   cd apoorvdarshan/resume/template
   ```

2. Install a LaTeX toolchain. macOS:
   ```bash
   brew install --cask basictex
   # open a new terminal so /Library/TeX/texbin lands on PATH
   sudo tlmgr install enumitem titlesec marvosym preprint cm-super collection-fontsrecommended
   ```

3. Open the folder in your agent of choice:
   ```bash
   claude   # Claude Code
   # or
   codex    # OpenAI Codex CLI
   ```

4. Edit `resume.tex` directly, or chat with the agent — *"replace the placeholders with my info: name X, email Y, projects A/B/C..."*. After every change the agent will recompile and inspect the rendered PDF without opening a viewer.

## What's in the box
- **`AGENTS.md`** — the skill: instructions for the agent on file structure, formatting patterns, common tasks, and workflow.
- **`resume.tex`** — sample template with placeholder content. Customize freely.
- **`resume.pdf`** — compiled sample output.
- **`.gitignore`** — keeps personal-named resume files (e.g. `Your_Name_Resume.tex`) out of git if you fork this.

## Why "rekisei"?
歴世 — a Japanese word meaning *"successive generations"* / *"the passage of years"* — what a resume captures.

## License

MIT. LaTeX base from [jakegut/resume](https://github.com/jakegut/resume) (also MIT).

## Repository maintenance

[Build and interfaces](BUILD.md) · [Contributing](CONTRIBUTING.md) · [Security policy](SECURITY.md) · [Changes](CHANGELOG.md)
