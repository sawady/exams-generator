"""Common machinery for language checkers.

A checker turns a set of source files into a verdict: does the solution
compile / type-check? Each checker declares the file extensions it owns,
the external tool it needs, and how to invoke it. Checkers never execute
the exam solution; they only ask the compiler (or an equivalent static
checker) about it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar


@dataclass
class Availability:
    available: bool
    tool: str
    path: str | None = None
    version: str | None = None
    hint: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "available": self.available,
            "tool": self.tool,
            "path": self.path,
            "version": self.version,
            "hint": self.hint,
        }


@dataclass
class CheckResult:
    language: str
    ok: bool
    files: list[str] = field(default_factory=list)
    command: list[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    skipped: bool = False
    note: str = ""

    @property
    def has_diagnostics(self) -> bool:
        return bool(self.stdout.strip() or self.stderr.strip())

    def as_text(self) -> str:
        if self.skipped:
            return f"[{self.language}] SKIPPED: {self.note}"
        head = f"[{self.language}] {'OK' if self.ok else 'FAILED'}"
        if self.files:
            head += f" ({', '.join(self.files)})"
        parts = [head]
        if self.note:
            parts.append(self.note)
        if self.stderr.strip():
            parts.append(self.stderr.rstrip())
        if self.stdout.strip():
            parts.append(self.stdout.rstrip())
        return "\n".join(parts)

    def as_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "ok": self.ok,
            "skipped": self.skipped,
            "files": self.files,
            "output": self.as_text(),
        }


class Checker:
    """Base class. Subclasses set the class attributes and implement ``build_commands``."""

    #: Identifier used in tool calls (``haskell``, ``c``, ...).
    name: ClassVar[str] = ""
    #: Human readable name.
    display_name: ClassVar[str] = ""
    #: Source extensions this checker compiles (lower case, with dot).
    source_extensions: ClassVar[tuple[str, ...]] = ()
    #: Extensions that are only included by sources (headers).
    header_extensions: ClassVar[tuple[str, ...]] = ()
    #: Default filename for a snippet with no filename.
    default_filename: ClassVar[str] = ""
    #: Markdown code-fence tag.
    fence: ClassVar[str] = ""
    #: Environment variable that overrides the executable.
    executable_env: ClassVar[str] = ""
    #: Executables tried in order when the env var is not set.
    default_executables: ClassVar[tuple[str, ...]] = ()
    #: Arguments that print the tool version.
    version_args: ClassVar[tuple[str, ...]] = ("--version",)
    #: What to tell the user when the tool is missing.
    install_hint: ClassVar[str] = ""

    def __init__(self, timeout: float = 60.0) -> None:
        self.timeout = timeout

    # ------------------------------------------------------------ toolchain

    def executable(self) -> str | None:
        override = os.environ.get(self.executable_env) if self.executable_env else None
        candidates = [override] if override else list(self.default_executables)
        for candidate in candidates:
            if candidate and shutil.which(candidate):
                return candidate
        return None

    def availability(self) -> Availability:
        exe = self.executable()
        tool = (os.environ.get(self.executable_env, "") if self.executable_env else "") or (
            self.default_executables[0] if self.default_executables else self.name
        )
        if exe is None:
            return Availability(False, tool, hint=self.install_hint)
        version = None
        try:
            proc = subprocess.run(
                [exe, *self.version_args], capture_output=True, text=True, timeout=15
            )
            out = (proc.stdout or proc.stderr).strip()
            version = out.splitlines()[0] if out else None
        except (OSError, subprocess.SubprocessError):
            pass
        return Availability(True, exe, path=shutil.which(exe), version=version)

    # -------------------------------------------------------------- routing

    def owns(self, filename: str) -> bool:
        return Path(filename).suffix.lower() in self.source_extensions

    def claims_header(self, filename: str) -> bool:
        return Path(filename).suffix.lower() in self.header_extensions

    # ------------------------------------------------------------- checking

    def prepare(
        self, files: Mapping[str, str], targets: Sequence[str]
    ) -> tuple[dict[str, str], list[str]]:
        """Hook to rewrite or rename files before they hit the disk.

        Returns the files to write and the (possibly renamed) targets.
        """
        return dict(files), list(targets)

    def build_commands(self, exe: str, sources: Sequence[str], workdir: Path) -> list[list[str]]:
        """Return the commands to run inside ``workdir``. All must succeed."""
        raise NotImplementedError

    def check_files(
        self, files: Mapping[str, str], targets: Sequence[str] | None = None
    ) -> CheckResult:
        """Check ``targets`` (default: every owned source in ``files``).

        All of ``files`` are written to the same temporary directory so that
        sources can include headers or import sibling modules.
        """
        targets = list(targets) if targets is not None else [f for f in files if self.owns(f)]
        if not targets:
            targets = [f for f in files if self.claims_header(f)]
        if not targets:
            return CheckResult(self.name, ok=True, skipped=True, note="no files for this language")

        exe = self.executable()
        if exe is None:
            return CheckResult(
                self.name,
                ok=False,
                files=sorted(targets),
                skipped=True,
                note=f"toolchain not available. {self.install_hint}".strip(),
            )

        reported = sorted(targets)
        prepared, targets = self.prepare(files, targets)
        with tempfile.TemporaryDirectory(prefix=f"exams-{self.name}-") as tmp:
            workdir = Path(tmp)
            for filename, content in prepared.items():
                path = workdir / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            stdout_parts: list[str] = []
            stderr_parts: list[str] = []
            commands = self.build_commands(exe, sorted(targets), workdir)
            ok = True
            for cmd in commands:
                try:
                    proc = subprocess.run(
                        cmd,
                        cwd=workdir,
                        capture_output=True,
                        text=True,
                        timeout=self.timeout,
                    )
                except subprocess.TimeoutExpired:
                    stderr_parts.append(f"Timed out after {self.timeout:g}s: {' '.join(cmd)}")
                    ok = False
                    break
                stdout_parts.append(proc.stdout)
                stderr_parts.append(proc.stderr)
                if proc.returncode != 0:
                    ok = False
                    break

        return CheckResult(
            self.name,
            ok=ok,
            files=reported,
            command=commands[0] if commands else [],
            stdout=_clean("".join(stdout_parts), workdir),
            stderr=_clean("".join(stderr_parts), workdir),
        )

    def check_snippet(self, code: str, filename: str | None = None) -> CheckResult:
        filename = filename or self.default_filename
        return self.check_files({filename: code}, [filename])


def _clean(text: str, workdir: Path) -> str:
    """Strip the temporary directory from diagnostics so paths read as plain filenames."""
    return text.replace(str(workdir) + os.sep, "").replace(str(workdir), ".")
