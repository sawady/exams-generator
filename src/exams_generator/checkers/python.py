"""Python checker: byte-compile, then type-check with mypy when present.

Python has no compiler that rejects type errors, so this checker does the
closest equivalent:

1. ``python -m py_compile`` on every file (syntax errors), always.
2. ``python -m mypy`` (type errors) when ``EXAMS_PYTHON_TYPECHECK`` is
   ``auto`` (default, only if mypy is importable) or ``mypy`` (required).
   ``none`` skips it.

Environment:

* ``EXAMS_PYTHON``: interpreter (default: the one running the server).
* ``EXAMS_PYTHON_TYPECHECK``: ``auto`` | ``mypy`` | ``none``.
* ``EXAMS_MYPY_FLAGS``: extra mypy flags (default ``--strict``-lite below).
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from .base import Checker

DEFAULT_MYPY_FLAGS = [
    "--check-untyped-defs",
    "--no-error-summary",
    "--no-incremental",
    "--cache-dir=/dev/null",
]


def _has_mypy(exe: str) -> bool:
    try:
        proc = subprocess.run(
            [exe, "-c", "import mypy"], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


class PythonChecker(Checker):
    name = "python"
    display_name = "Python"
    source_extensions = (".py", ".pyi")
    default_filename = "solution.py"
    fence = "python"
    executable_env = "EXAMS_PYTHON"
    default_executables = (sys.executable, "python3", "python")
    install_hint = "Install Python 3 (and `pip install mypy` for type checking)."

    def executable(self) -> str | None:
        override = os.environ.get(self.executable_env)
        for candidate in [override] if override else self.default_executables:
            if candidate and (shutil.which(candidate) or Path(candidate).is_file()):
                return candidate
        return None

    def typecheck_mode(self) -> str:
        mode = os.environ.get("EXAMS_PYTHON_TYPECHECK", "auto").strip().lower()
        return mode if mode in {"auto", "mypy", "none"} else "auto"

    def build_commands(self, exe: str, sources: Sequence[str], workdir: Path) -> list[list[str]]:
        commands = [[exe, "-m", "py_compile", *sources]]
        mode = self.typecheck_mode()
        if mode == "mypy" or (mode == "auto" and _has_mypy(exe)):
            raw = os.environ.get("EXAMS_MYPY_FLAGS")
            flags = shlex.split(raw) if raw is not None else DEFAULT_MYPY_FLAGS
            commands.append([exe, "-m", "mypy", *flags, *sources])
        return commands

    def availability(self):  # type: ignore[override]
        info = super().availability()
        if info.available and info.path:
            mode = self.typecheck_mode()
            mypy = _has_mypy(self.executable() or "")
            info.version = f"{info.version} (mypy: {'yes' if mypy else 'no'}, typecheck={mode})"
            if mode == "mypy" and not mypy:
                info.available = False
                info.hint = (
                    "EXAMS_PYTHON_TYPECHECK=mypy but mypy is not installed: pip install mypy"
                )
        return info
