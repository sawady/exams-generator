# Contributing to exams-generator

Thanks for your interest! Bug reports, questions and ideas are as welcome as code.

## Issues

Open a GitHub issue for bugs, confusing behaviour, or a language or workflow you would
like supported. If you want to work on something larger (a new checker, a new tool),
open an issue first so we can agree on the approach.

**Never attach real exams or their solutions** to issues or pull requests: use an
invented example, as the ones in [`examples/exams/`](examples/exams) are.

## Running and testing

```bash
uv venv && uv pip install -e ".[dev]"
.venv/bin/pytest -rs        # tests needing a missing toolchain are skipped, with the reason
.venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests
```

Install `ghc`, `gcc`/`g++`, `pandoc` and LaTeX (see the [README](README.md)) to run every
test. CI runs the suite on several Python versions, once more with every toolchain, and
builds the Docker image.

## Style and rules

- Code, comments and docs in English. The bundled style guides and templates exist in
  English and Spanish and mirror each other: change both.
- Checkers only compile or type-check: they never run the solution. A missing toolchain
  is *skipped*, never *passed*.
- Bundled style guides, templates and examples stay generic: no real courses,
  institutions, people or exams. Course-specific rules belong in a course profile.
- New behaviour comes with tests; example solutions must keep passing their checker.

## License

By contributing you agree that your contributions are licensed under the
[MIT License](LICENSE).
