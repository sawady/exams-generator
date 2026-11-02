"""Filesystem storage for exams, with optional git auto-commit.

Layout under ``exams_dir``::

    <name>/
      exam.md              statement given to students (Markdown)
      solution/            reference solution, any number of files
        Exam.hs
        queue.h  queue.c
      exam.pdf             after rendering the statement
      solution.pdf         after rendering the answer key
      metadata.json

``exams_dir`` is meant to be content you keep private, for example a clone
of a private git repository. When git backup is enabled:

* if ``exams_dir`` is the root of a git repository (it has a ``.git``),
  that repository is used as is, with its remotes and identity;
* otherwise a new repository is initialised there, even when ``exams_dir``
  sits inside another work tree, so exams never leak into an unrelated repo.

Every save, delete and render becomes one commit, scoped to ``exams_dir``.
With ``git_push`` the commit is pushed to the current branch's upstream.
Git failures never fail the operation; they are reported in ``last_git_error``.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]{0,63}$")
_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-.]{0,99}$")

STATEMENT_FILE = "exam.md"
SOLUTION_DIR = "solution"
METADATA_FILE = "metadata.json"
PDF_FILES = {"statement": "exam.pdf", "solution": "solution.pdf"}


def check_summary(ok: bool, results: list[dict[str, Any]]) -> dict[str, Any]:
    """What metadata.json keeps of a check run."""
    return {
        "ok": ok,
        "at": time.time(),
        "languages": {r["language"]: r["ok"] for r in results if not r.get("skipped")},
    }


class StorageError(Exception):
    """User-facing storage error (bad name, missing exam, ...)."""


def validate_name(name: str) -> str:
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise StorageError(
            f"Invalid exam name {name!r}. Use 1-64 characters from [A-Za-z0-9_-], "
            "starting with a letter or digit."
        )
    return name


def validate_filename(filename: str) -> str:
    if not isinstance(filename, str) or not _FILENAME_RE.match(filename) or ".." in filename:
        raise StorageError(
            f"Invalid solution filename {filename!r}. Use a plain file name "
            "(no directories) of [A-Za-z0-9_-.], e.g. 'Exam.hs' or 'queue.c'."
        )
    return filename


@dataclass
class ExamMetadata:
    name: str
    title: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    locale: str = "en"
    languages: list[str] = field(default_factory=list)
    solution_files: list[str] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0
    rendered: list[str] = field(default_factory=list)
    last_check: dict[str, Any] | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False) + "\n"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ExamMetadata:
        known = {f for f in cls.__dataclass_fields__}
        clean = {k: v for k, v in data.items() if k in known}
        clean.setdefault("name", "")
        return cls(**clean)


@dataclass
class Exam:
    metadata: ExamMetadata
    statement: str
    solution: dict[str, str]


class Storage:
    def __init__(
        self,
        exams_dir: Path,
        git_backup: bool = True,
        git_push: bool = False,
        default_locale: str = "en",
    ) -> None:
        self.exams_dir = Path(exams_dir)
        self.git_backup = git_backup
        self.git_push = git_push
        self.default_locale = default_locale
        self.last_git_error: str | None = None

        self.exams_dir.mkdir(parents=True, exist_ok=True)
        if self.git_backup:
            self._init_git_repo()

    # --------------------------------------------------------------- paths

    def exam_dir(self, name: str) -> Path:
        return self.exams_dir / validate_name(name)

    def statement_path(self, name: str) -> Path:
        return self.exam_dir(name) / STATEMENT_FILE

    def solution_dir(self, name: str) -> Path:
        return self.exam_dir(name) / SOLUTION_DIR

    def metadata_path(self, name: str) -> Path:
        return self.exam_dir(name) / METADATA_FILE

    def pdf_path(self, name: str, variant: str = "statement") -> Path:
        if variant not in PDF_FILES:
            raise StorageError(f"Unknown PDF variant {variant!r}. Use 'statement' or 'solution'.")
        return self.exam_dir(name) / PDF_FILES[variant]

    # ---------------------------------------------------------------- CRUD

    def exists(self, name: str) -> bool:
        return self.exam_dir(name).is_dir()

    def list_exams(self) -> list[ExamMetadata]:
        result: list[ExamMetadata] = []
        for child in sorted(self.exams_dir.iterdir()):
            if not child.is_dir() or child.name.startswith(".") or not _NAME_RE.match(child.name):
                continue
            if not (child / STATEMENT_FILE).exists() and not (child / METADATA_FILE).exists():
                continue
            result.append(self._load_metadata(child.name))
        return result

    def save_exam(
        self,
        name: str,
        statement: str,
        solution: Mapping[str, str] | None = None,
        *,
        title: str = "",
        description: str = "",
        tags: Iterable[str] | None = None,
        locale: str | None = None,
        languages: Iterable[str] | None = None,
        last_check: dict[str, Any] | None = None,
    ) -> ExamMetadata:
        name = validate_name(name)
        solution = dict(solution or {})
        for filename in solution:
            validate_filename(filename)

        now = time.time()
        edir = self.exam_dir(name)
        edir.mkdir(parents=True, exist_ok=True)

        previous = self._load_metadata(name) if self.metadata_path(name).exists() else None

        self.statement_path(name).write_text(statement, encoding="utf-8")
        sdir = self.solution_dir(name)
        if sdir.exists():
            shutil.rmtree(sdir)  # the new solution replaces the old one entirely
        if solution:
            sdir.mkdir()
            for filename, content in solution.items():
                (sdir / filename).write_text(content, encoding="utf-8")

        # Rendered PDFs describe the previous content; drop them.
        for pdf in PDF_FILES.values():
            (edir / pdf).unlink(missing_ok=True)

        meta = ExamMetadata(
            name=name,
            title=title or (previous.title if previous else ""),
            description=description or (previous.description if previous else ""),
            tags=list(tags) if tags is not None else (previous.tags if previous else []),
            locale=locale or (previous.locale if previous else self.default_locale),
            languages=list(languages or []),
            solution_files=sorted(solution),
            created_at=(previous.created_at if previous and previous.created_at else now),
            updated_at=now,
            rendered=[],
            last_check=last_check,
        )
        self.metadata_path(name).write_text(meta.to_json(), encoding="utf-8")
        self._commit(f"save exam: {name}")
        return meta

    def load_exam(self, name: str) -> Exam:
        if not self.exists(name):
            raise StorageError(f"Exam {name!r} not found.")
        meta = self._load_metadata(name)
        stmt_path = self.statement_path(name)
        statement = stmt_path.read_text("utf-8") if stmt_path.exists() else ""
        solution: dict[str, str] = {}
        sdir = self.solution_dir(name)
        if sdir.is_dir():
            for path in sorted(sdir.iterdir()):
                if path.is_file():
                    solution[path.name] = path.read_text("utf-8")
        return Exam(metadata=meta, statement=statement, solution=solution)

    def delete_exam(self, name: str) -> None:
        if not self.exists(name):
            raise StorageError(f"Exam {name!r} not found.")
        shutil.rmtree(self.exam_dir(name))
        self._commit(f"delete exam: {name}")

    def update_metadata(
        self, name: str, message: str | None = None, **changes: Any
    ) -> ExamMetadata:
        if not self.exists(name):
            raise StorageError(f"Exam {name!r} not found.")
        meta = self._load_metadata(name)
        for key, value in changes.items():
            setattr(meta, key, value)
        self.metadata_path(name).write_text(meta.to_json(), encoding="utf-8")
        if message:
            self._commit(message)
        return meta

    def record_check(self, name: str, ok: bool, results: list[dict[str, Any]]) -> ExamMetadata:
        return self.update_metadata(
            name, message=f"check exam: {name}", last_check=check_summary(ok, results)
        )

    def mark_rendered(self, name: str, variant: str) -> ExamMetadata:
        meta = self._load_metadata(name)
        rendered = sorted(set(meta.rendered) | {variant})
        return self.update_metadata(
            name, message=f"render {variant} pdf: {name}", rendered=rendered
        )

    # ----------------------------------------------------------------- git

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.exams_dir,
            check=check,
            capture_output=True,
            text=True,
            timeout=120,
        )

    def _init_git_repo(self) -> None:
        if shutil.which("git") is None:
            self.git_backup = False
            self.last_git_error = "git not found; backup disabled"
            return
        if (self.exams_dir / ".git").exists():
            return  # reuse the existing repository (e.g. a clone of a private content repo)
        # Anything else gets its own repository, even when nested inside another
        # work tree: exams must never end up committed to an unrelated repo
        # (such as a clone of this tool).
        try:
            self._git("init", "-q", "-b", "main")
            # Local identity so commits work on fresh machines and containers.
            if self._git("config", "user.email", check=False).returncode != 0:
                self._git("config", "user.email", "exams-generator@localhost")
            if self._git("config", "user.name", check=False).returncode != 0:
                self._git("config", "user.name", "exams-generator")
        except subprocess.CalledProcessError as err:
            self.git_backup = False
            self.last_git_error = (err.stderr or str(err)).strip()

    def _commit(self, message: str) -> None:
        if not self.git_backup:
            return
        try:
            self._git("add", "-A", "--", ".")
            staged = self._git("diff", "--cached", "--quiet", "--", ".", check=False)
            if staged.returncode == 0:
                return  # nothing changed
            self._git("commit", "-q", "-m", message, "--", ".")
            if self.git_push:
                self._git("push", "-q")
            self.last_git_error = None
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as err:
            # Backup is best effort: never fail a save because git is unhappy.
            stderr = getattr(err, "stderr", None) or str(err)
            self.last_git_error = stderr.strip() if isinstance(stderr, str) else str(stderr)

    def git_status(self) -> dict[str, Any]:
        info: dict[str, Any] = {
            "enabled": self.git_backup,
            "push": self.git_push,
            "last_error": self.last_git_error,
        }
        if not self.git_backup:
            return info
        top = self._git("rev-parse", "--show-toplevel", check=False)
        info["repository"] = top.stdout.strip() or None
        head = self._git("log", "-1", "--format=%h %s", check=False)
        info["last_commit"] = head.stdout.strip() or None
        remote = self._git("remote", check=False)
        info["remotes"] = remote.stdout.split()
        return info

    # ------------------------------------------------------------- private

    def _load_metadata(self, name: str) -> ExamMetadata:
        path = self.metadata_path(name)
        meta: ExamMetadata
        if path.exists():
            try:
                meta = ExamMetadata.from_dict(json.loads(path.read_text("utf-8")))
            except (ValueError, TypeError):
                meta = ExamMetadata(name=name)
        else:
            meta = ExamMetadata(name=name, locale=self.default_locale)
        meta.name = name
        sdir = self.solution_dir(name)
        if not meta.solution_files and sdir.is_dir():
            meta.solution_files = sorted(p.name for p in sdir.iterdir() if p.is_file())
        return meta
