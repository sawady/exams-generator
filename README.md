# exams-generator

An [MCP](https://modelcontextprotocol.io) server that helps teachers write
programming exams with an AI assistant such as Claude Code. Every exam is
saved with a reference solution that a real compiler has checked, and is
rendered to a printable PDF.

- **Compiler-checked solutions**: Haskell (GHC), C and C++ (GCC/Clang), Python
  (byte-compile + mypy). Languages are plugins; each one reports whether its
  toolchain is installed.
- **PDF output** with pandoc + LaTeX: the student statement and, optionally, an answer
  key with the statement followed by the solution files. PDFs use the exam's language
  for hyphenation (babel).
- **Your exams stay private**: they live in a directory you choose, ideally a clone of
  a separate private git repository. Every change is committed (and optionally pushed).
- **Exams in English or Spanish**, with bundled style guides and templates per
  language, and a *course profile* for the rules of your own course.
- **Guided workflow**: MCP prompts (`write_exam`, `review_exam`) and matching Claude
  Code slash commands.

## Quickstart: Claude Code (stdio)

1. Install the toolchains you need: `ghc`, `gcc`/`g++`, and `pandoc` with a LaTeX
   distribution for PDFs. On Debian/Ubuntu:

   ```bash
   sudo apt install ghc gcc g++ pandoc texlive-latex-recommended \
     texlive-fonts-recommended lmodern texlive-lang-spanish
   ```

   `texlive-lang-spanish` is only needed for Spanish exams (hyphenation and LaTeX
   labels). Without it they still render, with a warning.

2. Install the server (Python 3.10+):

   ```bash
   uv tool install "exams-generator[typecheck] @ git+https://github.com/sawady/exams-generator"
   # or: pipx install "exams-generator[typecheck] @ git+https://github.com/sawady/exams-generator"
   ```

3. Create a place for your exams. A private git repository is a good choice:

   ```bash
   git clone git@github.com:you/my-exams.git ~/my-exams   # or just: mkdir ~/my-exams
   ```

4. Register the server with Claude Code:

   ```bash
   claude mcp add exams \
     -e EXAMS_DIR="$HOME/my-exams" \
     -e EXAMS_DATA_DIR="$HOME/my-exams/.exams-config" \
     -e EXAMS_LOCALE=en \
     -- exams-generator
   ```

   Or add it to a project's `.mcp.json`:

   ```json
   {
     "mcpServers": {
       "exams": {
         "command": "exams-generator",
         "env": { "EXAMS_DIR": "/home/you/my-exams", "EXAMS_LOCALE": "es" }
       }
     }
   }
   ```

5. In Claude Code, ask for an exam, or use the prompt the server exposes:

   ```text
   /mcp__exams__write_exam topic="a library loan system" languages="c" locale="en"
   ```

   To get `/write-exam` and `/review-exam` as plain slash commands, copy
   [`.claude/commands/`](.claude/commands) into `~/.claude/commands/` (or into your
   project's `.claude/commands/`).

To look around first, copy the [example exams](examples/exams) (all invented) and
point `EXAMS_DIR` at the copy:

```bash
cp -r examples/exams /tmp/demo-exams
EXAMS_DIR=/tmp/demo-exams exams-generator   # stdio; normally your MCP client starts it
```

## Remote server (streamable HTTP)

Run it on a server so a whole teaching team shares the same exams and toolchains.
The Docker image includes every toolchain.

```bash
cp .env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'   # put it in EXAMS_BEARER_TOKEN
# EXAMS_HOST_DIR in .env: path of your private exams clone on the host
docker compose up -d --build
curl http://127.0.0.1:8765/healthz   # -> ok
```

The MCP endpoint is `/mcp` and requires `Authorization: Bearer <token>`. Put a TLS
reverse proxy in front of it, for example with Caddy:

```text
exams.example.org {
  reverse_proxy 127.0.0.1:8765
}
```

If the server binds to `127.0.0.1` (outside Docker) behind a proxy, set
`EXAMS_ALLOWED_HOSTS=exams.example.org`: the MCP SDK checks the `Host` header on
local binds.

Connect Claude Code to it:

```bash
claude mcp add --transport http exams https://exams.example.org/mcp \
  --header "Authorization: Bearer $EXAMS_TOKEN"
```

To push every commit to your private repository from the container, set
`EXAMS_GIT_PUSH=true` and mount an SSH deploy key with write access (see
`docker-compose.yml`).

## Keeping exams private

This repository contains **code and invented examples only**. Real exams with their
solutions should never be committed here. The intended setup:

- a separate **private** repository holds your exams;
- `EXAMS_DIR` points at a clone of it;
- with `EXAMS_GIT_BACKUP=true` (default) every save, delete and render is a commit
  there, and with `EXAMS_GIT_PUSH=true` it is pushed to the upstream branch.

If `EXAMS_DIR` is not the root of a git repository, the server creates one there, even
when the directory sits inside another repository, so exams never end up committed to
an unrelated repo. `scripts/backup.sh` makes tarball backups to an rsync target if you
want an extra copy.

## Customising: course profile, style guides, templates

The server ships generic style guides and templates (in `src/exams_generator/assets/`)
for every language, in English and Spanish. Anything in `EXAMS_DATA_DIR` with the same
relative path wins:

```text
$EXAMS_DATA_DIR/
  course.md                               course profile (recommended)
  pandoc-header.tex                       LaTeX header for the PDFs
  style/<locale>/general.md
  style/<locale>/<language>.md            haskell, c, cpp, python
  templates/<language>/<locale>/exam.md
  templates/<language>/<locale>/solution.<ext>
```

The **course profile** is where course-specific rules go: header format, the allowed
subset of each language (the compiler cannot enforce "no classes" or "no higher-order
functions"), the exercise structure, and the auxiliary data types students may use. The
model reads it first and it overrides the generic guides. See
[`examples/course-profile.md`](examples/course-profile.md).

## Languages

| Language | Checker | Files | Environment |
|---|---|---|---|
| `haskell` | `ghc -fno-code` (type-check only) | `.hs` | `EXAMS_GHC`, `EXAMS_GHC_FLAGS` |
| `c` | `gcc -fsyntax-only -std=c11 -Wall -Wextra` + likely-bug warnings as errors | `.c`, `.h` | `EXAMS_CC`, `EXAMS_CFLAGS` |
| `cpp` | `g++ -fsyntax-only -std=c++17 -Wall -Wextra` | `.cpp`, `.cc`, `.hpp`, `.h` | `EXAMS_CXX`, `EXAMS_CXXFLAGS` |
| `python` | `py_compile`, then `mypy --check-untyped-defs` if installed | `.py` | `EXAMS_PYTHON`, `EXAMS_PYTHON_TYPECHECK` (`auto`/`mypy`/`none`), `EXAMS_MYPY_FLAGS` |

A solution can have several files and mix languages (for example a Haskell part and a
C++ part); each file goes to the checker for its extension, and all files share one
directory so headers and imports resolve. Checkers never run the solution. A language
whose toolchain is missing is reported as *skipped*, never as passed.

Other languages can be added from another package through an entry point:

```toml
[project.entry-points."exams_generator.checkers"]
rust = "my_package.rust:RustChecker"   # a subclass of exams_generator.checkers.Checker
```

## Reference

**Tools**

| Tool | What it does |
|---|---|
| `list_languages` | Checkers and toolchain status, PDF toolchain, locales, exams dir and git status. |
| `list_exams` / `load_exam` | Saved exams and their metadata / one exam's statement and solution files. |
| `save_exam` | Save statement + solution files (`{filename: content}`), check them, commit. |
| `delete_exam` | Delete an exam (committed, so history keeps it). |
| `check_snippet` | Check code in a given language without saving. |
| `check_exam` | Check a saved exam's solution. |
| `render_exam` | Render `exam.pdf` (statement) or `solution.pdf` (answer key). |
| `get_exam_pdf` | The PDF as base64, rendering it if needed. |
| `preview_pdf` | Render any Markdown without saving. |
| `get_style_guide` / `get_template` / `get_course_profile` | Writing rules and starting points. |

**Prompts**: `write_exam(topic, languages, locale, kind, exercises, notes)`,
`review_exam(name)`.

**Resources**: `exams://course-profile`, `exams://style-guide/{locale}`,
`exams://template/{language}/{locale}/{kind}`, `exams://exam/{name}/statement`.

**Storage layout** (inside `EXAMS_DIR`):

```text
<name>/
  exam.md          statement
  solution/        reference solution files
  exam.pdf         rendered statement
  solution.pdf     rendered answer key
  metadata.json    title, tags, locale, languages, last check, ...
```

**Environment**

| Variable | Default | Meaning |
|---|---|---|
| `EXAMS_TRANSPORT` | `stdio` | `stdio` or `http` |
| `EXAMS_HTTP_HOST` / `EXAMS_HTTP_PORT` | `127.0.0.1` / `8765` | HTTP bind address |
| `EXAMS_BEARER_TOKEN` | (required for HTTP) | Token for `Authorization: Bearer` |
| `EXAMS_ALLOWED_HOSTS` | (none) | Public host names, comma separated |
| `EXAMS_DIR` | `$EXAMS_DATA_DIR/exams` | Where exams are stored |
| `EXAMS_DATA_DIR` | `./data` | Overrides (course profile, guides, templates) |
| `EXAMS_GIT_BACKUP` / `EXAMS_GIT_PUSH` | `true` / `false` | Commit / push each change |
| `EXAMS_LOCALE` | `en` | Default exam language (`en`, `es`) |
| `EXAMS_CHECK_TIMEOUT` | `60` | Seconds per compiler run |
| `EXAMS_PDF_ENGINE` | `pdflatex` | pandoc `--pdf-engine` |

A `.env` file in the working directory is read too.

## Development

```bash
uv venv && uv pip install -e ".[dev]"
.venv/bin/pytest          # tests needing a missing toolchain are skipped
.venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests
```

CI runs the suite on Python 3.10, 3.12 and 3.13, once more with every toolchain installed, and
builds and smoke-tests the Docker image.

## License

[MIT](LICENSE).
