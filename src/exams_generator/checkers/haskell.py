"""Haskell checker: type-check with ``ghc -fno-code``.

Environment:

* ``EXAMS_GHC``: executable (default ``ghc``).
* ``EXAMS_GHC_FLAGS``: extra flags, shell-split (e.g. ``-XLambdaCase -Wall``).

Files without a ``module`` header get one injected (named after the file),
followed by a ``LINE`` pragma so GHC still reports the original line
numbers. Without it GHC treats the file as ``Main`` and asks for ``main``.
"""

from __future__ import annotations

import os
import re
import shlex
from collections.abc import Mapping, Sequence
from pathlib import Path

from .base import Checker

_MODULE_RE = re.compile(r"^module\s+([A-Z][A-Za-z0-9_']*(?:\.[A-Z][A-Za-z0-9_']*)*)", re.MULTILINE)
_HEADER_LINE_RE = re.compile(r"^\s*(--.*|\{-#.*#-\}\s*)?$")


def module_name_for(filename: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_]", "_", Path(filename).stem) or "Exam"
    if not stem[0].isalpha():
        stem = "M" + stem
    return stem[0].upper() + stem[1:]


def _inject_module_header(source: str, module: str, filename: str) -> str:
    """Insert ``module X where`` after leading pragmas/comments, keeping line numbers."""
    lines = source.splitlines(keepends=True)
    cut = 0
    while cut < len(lines) and _HEADER_LINE_RE.match(lines[cut]):
        cut += 1
    head, rest = lines[:cut], lines[cut:]
    pragma = f'{{-# LINE {cut + 1} "{filename}" #-}}\n'
    return "".join(head) + f"module {module} where\n" + pragma + "".join(rest)


class HaskellChecker(Checker):
    name = "haskell"
    display_name = "Haskell (GHC)"
    source_extensions = (".hs", ".lhs")
    default_filename = "Exam.hs"
    fence = "haskell"
    executable_env = "EXAMS_GHC"
    default_executables = ("ghc",)
    version_args = ("--numeric-version",)
    install_hint = "Install GHC (https://www.haskell.org/ghcup/ or `apt install ghc`)."

    def prepare(
        self, files: Mapping[str, str], targets: Sequence[str]
    ) -> tuple[dict[str, str], list[str]]:
        out: dict[str, str] = {}
        renamed: dict[str, str] = {}
        self._injected = False
        for filename, content in files.items():
            if not self.owns(filename) or filename.endswith(".lhs"):
                out[filename] = content
                continue
            match = _MODULE_RE.search(content)
            if match:
                module = match.group(1)
            else:
                module = module_name_for(filename)
                content = _inject_module_header(content, module, filename)
                self._injected = True
            # GHC finds imported modules by path, so the file must match its module.
            new_name = module.replace(".", "/") + ".hs"
            out[new_name] = content
            renamed[filename] = new_name
        return out, [renamed.get(t, t) for t in targets]

    def build_commands(self, exe: str, sources: Sequence[str], workdir: Path) -> list[list[str]]:
        extra = shlex.split(os.environ.get("EXAMS_GHC_FLAGS", ""))
        # The caret excerpt would show the rewritten file, not the user's.
        caret = ["-fno-diagnostics-show-caret"] if getattr(self, "_injected", False) else []
        return [
            [
                exe,
                "-v0",
                "-fno-code",
                "-fforce-recomp",
                "-fno-warn-unused-imports",
                "-outputdir",
                ".ghc-out",
                "-i.",
                *caret,
                *extra,
                *sources,
            ]
        ]
