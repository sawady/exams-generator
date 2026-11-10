# exams-generator

[![Sponsor](https://img.shields.io/github/sponsors/sawady?label=Sponsor&logo=GitHub)](https://github.com/sponsors/sawady)

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

## Quickstart: Claude Code plugin

The plugin installs the MCP server, the `/exams-generator:write-exam` and
`/exams-generator:review-exam` commands, and an `exam-writing` skill. It needs
[uv](https://docs.astral.sh/uv/) and the toolchains from step 1 above. Inside Claude Code:

```text
/plugin marketplace add sawady/exams-generator
/plugin install exams-generator@exams-generator
```

It asks for your exams directory (use a clone of a private repository, as above), the default
exam language and whether to allow demos to run (off by default; see
[Running demos](#running-demos-optional)). Course profile and overrides go in `.exams-config`
inside the exams directory. Without an exams directory the server does not start: run
`/plugin configure exams-generator@exams-generator` to set it later.

To try a local checkout: `claude --plugin-dir /path/to/exams-generator`. The server is built
from the plugin's own copy of the source, so it always matches the plugin's version.

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

## Running demos (optional)

The checkers only compile. The optional `run_demos` tool goes further: it **executes**
the solution's demos, which also catches a solution that compiles but gives the wrong
answer. Because it runs code, it does not exist unless you turn it on:

```bash
sudo apt install bubblewrap         # 0.8 or newer also limits the size of its tmpfs
export EXAMS_RUN_DEMOS=true
export EXAMS_RUN_RO_BINDS="$HOME/.ghcup"   # only for toolchains outside /usr
```

| Language | What counts as a demo | How it passes |
|---|---|---|
| `python` | doctests in docstrings | every example matches |
| `haskell` | `>>> expr` lines in comments, with the expected output below | GHCi's output matches, line by line |
| `c`, `cpp` | a `main` in a solution file or in `extra_files` | it builds and exits with status 0 |

Solutions in C and C++ usually have no `main`; pass the demo as another file:
`run_demos(name="my-exam", extra_files={"demo_main.c": "..."})`. Nothing is saved.

Status is one of `passed`, `failed`, `timeout` or `skipped`. A missing sandbox, a missing
toolchain, a language without a runner and a solution without demos are all *skipped*,
and `ok` is true only if every language really passed. Python `>>>` lines in comments are
not doctests and do not run; only docstrings count, so check the counts in the report.

**What the sandbox gives you.** Every run is a throwaway [bubblewrap](https://github.com/containers/bubblewrap)
sandbox, for the build as well as the run (compilers can run code too: Template Haskell,
for one):

- new user, PID, network, IPC, UTS and cgroup namespaces, all capabilities dropped: no
  network (only a private loopback) and no other process in sight;
- the file system is `/usr`, `/bin`, `/lib*`, `/etc/ld.so.cache`, `/etc/alternatives` and
  `EXAMS_RUN_RO_BINDS`, read-only, plus a private tmpfs for `/work`, `/tmp` and `/dev/shm`.
  No home, no `EXAMS_DIR`, no other solution. Only the files of this run are copied in;
- an empty environment (no token or credential of the server gets in);
- a wall-clock limit (`EXAMS_RUN_TIMEOUT`, 30 s, for build and run together) that kills
  the whole process tree, plus limits on address space (`EXAMS_RUN_MEMORY_MB`, 4096),
  processes (128), file size (32 MiB) and open files (256).

**What it does not give you.** It is meant for a teacher's own drafts, including ones an
assistant wrote, not for hostile code from strangers:

- it shares the host's kernel and has no seccomp filter, so a kernel bug can break out of it.
  For untrusted input, use a VM;
- memory is limited per process, by address space: there is no cgroup limit, and several
  processes can use more in total. CPU is limited only by the timeout;
- with bubblewrap older than 0.8 (for example on Ubuntu 22.04) the tmpfs cannot be limited,
  so a run can take up to half of the RAM until the timeout;
- it is Linux only and needs unprivileged user namespaces. Ubuntu 24.04 restricts them
  through AppArmor (allow them with an AppArmor profile for `bwrap`, or with
  `sysctl kernel.apparmor_restrict_unprivileged_userns=0`), and the stock Docker image has
  no bubblewrap. In both cases the tool reports *skipped*; `list_languages` shows why,
  under `demos`;
- binding a directory with `EXAMS_RUN_RO_BINDS` exposes it to the code. The server refuses
  binds that would expose the home directory or the exams, but check any other you add.

On a shared HTTP server, anyone holding the Bearer token can run code through this tool.

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
| `run_demos` | Optional, off by default: execute demos in a sandbox (see above). |
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
| `EXAMS_RUN_DEMOS` | `false` | Register the `run_demos` tool |
| `EXAMS_RUN_TIMEOUT` | `30` | Seconds per demo run, build included |
| `EXAMS_RUN_MEMORY_MB` | `4096` | Address-space limit of a demo run |
| `EXAMS_RUN_RO_BINDS` | (none) | Extra read-only directories in the sandbox, `:` separated |
| `EXAMS_BWRAP` | `bwrap` | bubblewrap executable |

A `.env` file in the working directory is read too.

## Development

```bash
uv venv && uv pip install -e ".[dev]"
.venv/bin/pytest          # tests needing a missing toolchain are skipped
.venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests
```

CI runs the suite on Python 3.10, 3.12 and 3.13, once more with every toolchain installed, and
builds and smoke-tests the Docker image.

## Sponsoring

exams-generator is free software. If it is useful to you, you can support its development through
[GitHub Sponsors](https://github.com/sponsors/sawady).

## License

[MIT](LICENSE).
