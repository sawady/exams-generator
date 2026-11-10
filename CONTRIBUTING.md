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

## Publishing a release to PyPI (maintainers)

Nothing here runs by itself: CI only builds the package and checks its metadata.

1. Move the `[Unreleased]` notes of `CHANGELOG.md` to a new version, and update the links at
   the bottom. Set that version in `pyproject.toml`, `src/exams_generator/__init__.py` and
   `.claude-plugin/plugin.json` (a test checks that they agree).
2. Commit, and wait for CI to be green.
3. Build from a clean tree and check the result:

   ```bash
   rm -rf dist && uv build
   uvx twine check --strict dist/*
   uv venv /tmp/eg-check && uv pip install --python /tmp/eg-check/bin/python dist/*.whl
   EXAMS_DATA_DIR=/tmp/eg-check/data /tmp/eg-check/bin/python -c \
     "from exams_generator.server import create_server; create_server()"
   ```

4. Publish, with an API token for the `exams-generator` project (or with
   [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) from a workflow):

   ```bash
   UV_PUBLISH_TOKEN=pypi-... uv publish dist/*
   ```

   Upload to TestPyPI first with `uv publish --publish-url https://test.pypi.org/legacy/`
   if the release changes the packaging. A version number can never be reused on PyPI.

5. Tag `vX.Y.Z` and create the GitHub release from the changelog.
6. Change the install lines in the README to `uv tool install "exams-generator[typecheck]"`
   once the first release is on PyPI.

## License

By contributing you agree that your contributions are licensed under the
[MIT License](LICENSE).
