# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `run_demos` can send runs to a separate runner instead of starting bubblewrap on the
  server: set `EXAMS_RUN_RUNNER_URL`. The runner (`exams-generator-runner`, built from
  `Dockerfile.runner`) has the toolchains and nothing else: no token, no exams, no
  network but an internal one to the server, a read-only root, tmpfs work directories and
  limits on CPU, memory and processes. A runner that is down, slow or answers anything
  malformed makes the run *skipped*, never passed; the server waits up to
  `EXAMS_RUN_RUNNER_TIMEOUT` (60 s) for an answer. Without the variable nothing changes.
- `compose.yaml` runs the runner under the `demos` profile, and `compose.gvisor.yaml`
  runs it under gVisor (`runsc`).
- End-to-end tests of the server and the runner through compose, in CI with runc and with
  gVisor: the run cannot see the server's variables or files, nor the network, and nothing
  survives from one run to the next.
- Listing details for Anthropic's plugin directory: an icon (`.claude-plugin/icon.png`, drawn for
  this project), documentation, support and privacy policy links in `plugin.json`, and
  `PRIVACY.md`.
- README: where the plugin works (Claude Code only, because the server is a local process),
  example requests, and what the plugin runs and sends.

### Changed

- `docker-compose.yml` is now `compose.yaml`. `docker compose up` still starts only the
  server.

## [0.2.0] - Pending

### Added

- Optional `run_demos` tool that executes a solution's demos in a sandbox: doctests
  (Python), `>>>` demos checked against their expected output (Haskell) and a `main`
  (C/C++). Off by default; set `EXAMS_RUN_DEMOS=true` to register it. It runs in
  bubblewrap with no network and no access to the exams, under a timeout and resource
  limits. A missing sandbox or toolchain, or a solution with no demos, is reported as
  *skipped*, never as passed. The checkers still never execute anything.
- Claude Code plugin (`.claude-plugin/`): MCP server configured from the plugin's options,
  the `write-exam` and `review-exam` commands, and an `exam-writing` skill.
- Two more invented example exams, with solutions that pass their checkers: an irrigation
  network in Haskell (algebraic types, recursion and folds, in English) and a priority queue
  on a binary heap in C (invariants, implementation and client code, in Spanish). The README
  now lists all the examples.

### Changed

- Packaging ready for PyPI: complete metadata, a source distribution with only what it
  needs, a CI job that builds it and checks it with twine, and absolute links in the README.
- Releases are published to PyPI from a `v*` tag by a workflow that uses Trusted Publishing,
  with no API tokens.

## [0.1.0] - 2026-11-04

First public release.

### Added

- MCP server (`exams-generator`, MCP Python SDK 2.x) over stdio and streamable HTTP
  with Bearer authentication, configured with `EXAMS_*` variables or a `.env` file.
- Tools to save, load, list, delete, check and render exams, check snippets, preview
  PDFs, and read style guides, templates and the course profile; `write_exam` and
  `review_exam` prompts; resources for the profile, guides, templates and statements.
- Checkers as plugins: Haskell (`ghc -fno-code`), C (`gcc -fsyntax-only`, likely-bug
  warnings as errors), C++ (`g++ -fsyntax-only`) and Python (`py_compile` + mypy). A
  solution can span several files and languages. Third-party checkers load through the
  `exams_generator.checkers` entry point. A missing toolchain is reported as skipped.
- Exam storage in `EXAMS_DIR`, meant as a clone of a separate private repository: every
  save, delete and render is a commit, optionally pushed.
- PDF rendering with pandoc + LaTeX: the statement and an answer key. PDFs use the
  exam's language through babel/polyglossia, and fall back to rendering without it,
  with a warning, when the LaTeX language files are missing.
- Generic style guides and templates for Haskell, C, C++ and Python in English and
  Spanish, all overridable from `EXAMS_DATA_DIR`, and the *course profile* for
  course-specific rules (with a fictional example).
- Invented example exams: Haskell (Spanish), C (English), Python (English) and C++
  (Spanish), with solutions that pass their checkers.
- Claude Code slash commands `/write-exam` and `/review-exam`.
- Dockerfile with every toolchain, `docker-compose.yml`, `scripts/backup.sh`.
- Test suite (pytest) and CI on GitHub Actions: Python 3.10/3.12/3.13, a job with every
  toolchain, and a Docker build with a smoke test.
- `CONTRIBUTING.md`, MIT license.

### Fixed

- Line breaks (`<br>`) inside table cells, used by the C and C++ style guides to show a
  header next to its private struct, are kept in the PDF (pandoc drops raw HTML when it
  writes LaTeX; a small Lua filter turns them into line breaks).

[Unreleased]: https://github.com/sawady/exams-generator/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/sawady/exams-generator/releases/tag/v0.2.0
[0.1.0]: https://github.com/sawady/exams-generator/releases/tag/v0.1.0
