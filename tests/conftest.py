from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from exams_generator.checkers import CheckerRegistry
from exams_generator.config import Settings
from exams_generator.pdf import toolchain_status
from exams_generator.sandbox import Sandbox

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples" / "exams"

_registry = CheckerRegistry(load_plugins=False)


def has_toolchain(language: str) -> bool:
    return _registry.get(language).availability().available


def requires(language: str) -> pytest.MarkDecorator:
    """Skip a test when the toolchain for ``language`` is not installed."""
    return pytest.mark.skipif(
        not has_toolchain(language), reason=f"{language} toolchain not installed"
    )


requires_pdf = pytest.mark.skipif(
    not toolchain_status()["available"], reason="pandoc/pdflatex not installed"
)
_env = Settings.from_env()


def make_sandbox(tmp_path: Path, timeout: float = 20.0, memory_mb: int = 4096) -> Sandbox:
    """A sandbox for tests, honouring EXAMS_BWRAP and EXAMS_RUN_RO_BINDS from the environment."""
    return Sandbox(
        bwrap=_env.bwrap,
        timeout=timeout,
        memory_mb=memory_mb,
        ro_binds=_env.run_ro_binds,
        protected=(tmp_path / "exams", tmp_path / "data"),
    )


# Without bubblewrap only the tests for the "skipped" paths run. CI installs it and
# checks that it works, so that these do run there.
requires_sandbox = pytest.mark.skipif(
    not make_sandbox(Path("/nonexistent")).status().available, reason="bubblewrap not usable here"
)
requires_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", exams_dir=tmp_path / "exams")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
