# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
