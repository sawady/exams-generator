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
test. The demo tests also need bubblewrap and a toolchain the sandbox can see: with GHC
from GHCup, run them with `EXAMS_RUN_RO_BINDS="$HOME/.ghcup"`, or the Haskell ones skip.
CI runs the suite on several Python versions, once more with every toolchain, and builds
the Docker image.

`tests/test_runner_e2e.py` checks the separate demo runner through `compose.yaml` and skips
unless you point it at a running stack; its docstring has the commands. CI runs it with
runc and with gVisor.

## Style and rules

- Code, comments and docs in English. The bundled style guides and templates exist in
  English and Spanish and mirror each other: change both.
- Checkers only compile or type-check: they never run the solution. A missing toolchain
  is *skipped*, never *passed*.
- Bundled style guides, templates and examples stay generic: no real courses,
  institutions, people or exams. Course-specific rules belong in a course profile.
- New behaviour comes with tests; example solutions must keep passing their checker.

## Publishing a release to PyPI (maintainers)

Releases are published by [`.github/workflows/publish.yml`](.github/workflows/publish.yml)
when a `v*` tag is pushed. It uses
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC), so there are no API
tokens or secrets to manage.

### One-time setup on PyPI

Before the first tag, register a *pending publisher* at
<https://pypi.org/manage/account/publishing/>, with exactly these values:

| Field | Value |
|---|---|
| PyPI Project Name | `exams-generator` |
| Owner | `sawady` |
| Repository name | `exams-generator` |
| Workflow name | `publish.yml` |
| Environment name | `pypi` |

Without it, the publish job fails with an authentication error and nothing is uploaded. The
first successful publish creates the project on PyPI and turns the pending publisher into a
regular one. GitHub creates the `pypi` environment the first time the workflow uses it; to
require an approval before each upload, add reviewers to it under
*Settings > Environments*.

### Cutting a release

1. Move the `[Unreleased]` notes of `CHANGELOG.md` to a new version with today's date (or, if
   they are already there, set the date), and update the links at the bottom. Set that version
   in `pyproject.toml`, `src/exams_generator/__init__.py` and `.claude-plugin/plugin.json` (a
   test checks that they agree).
2. Commit, and wait for CI to be green.
3. Optionally, build from a clean tree and check the result:

   ```bash
   rm -rf dist && uv build
   uvx twine check --strict dist/*
   uv venv /tmp/eg-check && uv pip install --python /tmp/eg-check/bin/python dist/*.whl
   EXAMS_DATA_DIR=/tmp/eg-check/data /tmp/eg-check/bin/python -c \
     "from exams_generator.server import create_server; create_server()"
   ```

4. Tag the commit and push the tag, which starts the publish workflow:

   ```bash
   git tag vX.Y.Z && git push origin vX.Y.Z
   ```

   The workflow stops if the tag does not match the version in `pyproject.toml`. A version
   number can never be reused on PyPI.

5. Create the GitHub release from the changelog.
6. Change the install lines in the README to `uv tool install "exams-generator[typecheck]"`
   once the first release is on PyPI.

## License

By contributing you agree that your contributions are licensed under the
[MIT License](LICENSE).
