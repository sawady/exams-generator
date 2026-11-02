"""The bundled example exams must stay valid: they are what new users try first."""

import json

import pytest

from exams_generator.checkers import CheckerRegistry
from exams_generator.storage import Storage
from tests.conftest import EXAMPLES, has_toolchain

NAMES = sorted(p.name for p in EXAMPLES.iterdir() if p.is_dir())


def test_there_are_examples():
    assert len(NAMES) >= 3


@pytest.mark.parametrize("name", NAMES)
def test_example_loads(name):
    storage = Storage(EXAMPLES, git_backup=False)
    exam = storage.load_exam(name)
    meta = json.loads((EXAMPLES / name / "metadata.json").read_text())
    assert exam.statement.strip()
    assert sorted(exam.solution) == meta["solution_files"]
    assert "Invented example" in exam.statement or "inventado" in exam.statement


@pytest.mark.parametrize("name", NAMES)
def test_example_solution_checks(name):
    exam = Storage(EXAMPLES, git_backup=False).load_exam(name)
    registry = CheckerRegistry(timeout=120, load_plugins=False)
    for language in registry.languages_for(exam.solution):
        if not has_toolchain(language):
            pytest.skip(f"{language} toolchain not installed")
    for result in registry.check_files(exam.solution):
        assert result.ok, result.as_text()
