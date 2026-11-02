from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from exams_generator.checkers import CheckerRegistry
from exams_generator.config import Settings
from exams_generator.pdf import toolchain_status

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
requires_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", exams_dir=tmp_path / "exams")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
