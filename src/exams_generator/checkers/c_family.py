"""C and C++ checkers: ``-fsyntax-only`` with GCC or Clang.

``-fsyntax-only`` runs the full front end (parsing and type checking) without
generating code or linking, so a solution does not need a ``main``.

Environment:

* ``EXAMS_CC`` / ``EXAMS_CXX``: compiler (default ``gcc``/``clang``/``cc`` and
  ``g++``/``clang++``/``c++``).
* ``EXAMS_CFLAGS`` / ``EXAMS_CXXFLAGS``: replace the default flags below.

The defaults turn the warnings that are almost always real bugs in exam
code into errors and leave the rest as warnings, which are reported but do
not fail the check.
"""

from __future__ import annotations

import os
import shlex
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

from .base import Checker

_BUG_WARNINGS = [
    "-Werror=return-type",
    "-Werror=implicit-function-declaration",
    "-Werror=int-conversion",
    "-Werror=incompatible-pointer-types",
    "-Werror=uninitialized",
]

DEFAULT_CFLAGS = ["-std=c11", "-Wall", "-Wextra", *_BUG_WARNINGS]
# The C-only warnings are not valid for C++ and would print noise.
DEFAULT_CXXFLAGS = [
    "-std=c++17",
    "-Wall",
    "-Wextra",
    "-Werror=return-type",
    "-Werror=uninitialized",
]


class _CFamilyChecker(Checker):
    flags_env: ClassVar[str] = ""
    default_flags: ClassVar[list[str]] = []

    def flags(self) -> list[str]:
        raw = os.environ.get(self.flags_env)
        return shlex.split(raw) if raw is not None else list(self.default_flags)

    def build_commands(self, exe: str, sources: Sequence[str], workdir: Path) -> list[list[str]]:
        return [[exe, "-fsyntax-only", "-I.", *self.flags(), *sources]]


class CChecker(_CFamilyChecker):
    name = "c"
    display_name = "C"
    source_extensions = (".c",)
    header_extensions = (".h",)
    default_filename = "solution.c"
    fence = "c"
    executable_env = "EXAMS_CC"
    default_executables = ("gcc", "clang", "cc")
    install_hint = "Install a C compiler (`apt install gcc` or `apt install clang`)."
    flags_env = "EXAMS_CFLAGS"
    default_flags = DEFAULT_CFLAGS


class CppChecker(_CFamilyChecker):
    name = "cpp"
    display_name = "C++"
    source_extensions = (".cpp", ".cc", ".cxx", ".c++")
    header_extensions = (".hpp", ".hh", ".hxx", ".h")
    default_filename = "solution.cpp"
    fence = "cpp"
    executable_env = "EXAMS_CXX"
    default_executables = ("g++", "clang++", "c++")
    install_hint = "Install a C++ compiler (`apt install g++` or `apt install clang`)."
    flags_env = "EXAMS_CXXFLAGS"
    default_flags = DEFAULT_CXXFLAGS

    def build_commands(self, exe: str, sources: Sequence[str], workdir: Path) -> list[list[str]]:
        # A lone ``.h`` is C to the compiler unless we say otherwise.
        lang = ["-x", "c++"] if all(Path(s).suffix == ".h" for s in sources) else []
        return [[exe, "-fsyntax-only", "-I.", *self.flags(), *lang, *sources]]
