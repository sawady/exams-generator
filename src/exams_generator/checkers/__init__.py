"""Language checkers, discovered as plugins.

Built-in checkers are registered here. Other packages can add languages by
declaring an entry point in the ``exams_generator.checkers`` group that
points to a :class:`~exams_generator.checkers.base.Checker` subclass::

    [project.entry-points."exams_generator.checkers"]
    rust = "my_package.rust:RustChecker"
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from importlib.metadata import entry_points

from .base import Availability, Checker, CheckResult
from .c_family import CChecker, CppChecker
from .haskell import HaskellChecker
from .python import PythonChecker

__all__ = [
    "Availability",
    "CheckResult",
    "Checker",
    "CheckerRegistry",
    "UnknownLanguageError",
]

log = logging.getLogger(__name__)

BUILTIN_CHECKERS: tuple[type[Checker], ...] = (HaskellChecker, CChecker, CppChecker, PythonChecker)

# Common spellings people (and models) use for the language argument.
_ALIASES = {
    "hs": "haskell",
    "ghc": "haskell",
    "c++": "cpp",
    "cxx": "cpp",
    "cc": "cpp",
    "py": "python",
    "python3": "python",
}


class UnknownLanguageError(ValueError):
    pass


class CheckerRegistry:
    def __init__(self, timeout: float = 60.0, load_plugins: bool = True) -> None:
        self.timeout = timeout
        self._classes: dict[str, type[Checker]] = {}
        for cls in BUILTIN_CHECKERS:
            self.register(cls)
        if load_plugins:
            self._load_entry_points()

    def register(self, cls: type[Checker]) -> None:
        if not cls.name:
            raise ValueError(f"{cls!r} has no name")
        self._classes[cls.name] = cls

    def _load_entry_points(self) -> None:
        for ep in entry_points(group="exams_generator.checkers"):
            try:
                cls = ep.load()
                if isinstance(cls, type) and issubclass(cls, Checker):
                    self.register(cls)
                else:
                    log.warning("Entry point %s is not a Checker subclass", ep.name)
            except Exception:  # a broken plugin must not take the server down
                log.exception("Could not load checker plugin %s", ep.name)

    # -------------------------------------------------------------- lookup

    @property
    def names(self) -> list[str]:
        return list(self._classes)

    def get(self, language: str) -> Checker:
        key = language.strip().lower()
        key = _ALIASES.get(key, key)
        if key not in self._classes:
            raise UnknownLanguageError(
                f"Unknown language {language!r}. Known: {', '.join(self.names)}."
            )
        return self._classes[key](timeout=self.timeout)

    def all(self) -> list[Checker]:
        return [cls(timeout=self.timeout) for cls in self._classes.values()]

    def describe(self) -> list[dict[str, object]]:
        rows = []
        for checker in self.all():
            rows.append(
                {
                    "language": checker.name,
                    "display_name": checker.display_name,
                    "extensions": list(checker.source_extensions + checker.header_extensions),
                    "fence": checker.fence,
                    **checker.availability().as_dict(),
                }
            )
        return rows

    # ------------------------------------------------------------- routing

    def languages_for(self, files: Mapping[str, str] | list[str]) -> list[str]:
        """Languages that own at least one source file in ``files``."""
        names = list(files)
        found = []
        for checker in self.all():
            if any(checker.owns(f) for f in names):
                found.append(checker.name)
        return found

    def check_files(self, files: Mapping[str, str]) -> list[CheckResult]:
        """Run every checker that owns a file. Headers go to the language that uses them."""
        results = []
        langs = self.languages_for(files)
        if not langs:
            # Header-only exams: give headers to whoever claims them first.
            for checker in self.all():
                if any(checker.claims_header(f) for f in files):
                    langs = [checker.name]
                    break
        for lang in langs:
            results.append(self.get(lang).check_files(files))
        return results
