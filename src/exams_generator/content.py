"""Style guides, templates, course profile and the pandoc header.

Every piece of content is looked up first in ``EXAMS_DATA_DIR`` and then in
the defaults bundled with the package (``exams_generator/assets``). To
customise something, copy the bundled file to the same relative path under
your data dir and edit it::

    $EXAMS_DATA_DIR/
      course.md                       course profile (not bundled; optional)
      pandoc-header.tex
      style/<locale>/general.md
      style/<locale>/<language>.md
      templates/<language>/<locale>/exam.md
      templates/<language>/<locale>/solution.<ext>
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

from .config import SUPPORTED_LOCALES, normalize_locale

if TYPE_CHECKING:  # importlib.resources.abc only exists from Python 3.11
    from importlib.resources.abc import Traversable

ASSETS: Traversable = files("exams_generator") / "assets"

TEMPLATE_KINDS = ("statement", "solution")


class Content:
    def __init__(self, data_dir: Path, default_locale: str = "en") -> None:
        self.data_dir = Path(data_dir)
        self.default_locale = default_locale

    # ------------------------------------------------------------ lookup

    def _read(self, *parts: str) -> str | None:
        override = self.data_dir.joinpath(*parts)
        if override.is_file():
            return override.read_text("utf-8")
        bundled = ASSETS.joinpath(*parts)
        if bundled.is_file():
            return bundled.read_text("utf-8")
        return None

    def locale(self, locale: str | None) -> str:
        return normalize_locale(locale, self.default_locale)

    # ------------------------------------------------------------ public

    def style_guide(self, language: str | None = None, locale: str | None = None) -> str:
        """General guide, followed by the language-specific one when given."""
        loc = self.locale(locale)
        parts = [self._read("style", loc, "general.md") or ""]
        if language:
            specific = self._read("style", loc, f"{language}.md")
            if specific:
                parts.append(specific)
        return "\n\n".join(p.strip() for p in parts if p.strip()) + "\n"

    def template(self, language: str, kind: str, locale: str | None = None) -> str | None:
        if kind not in TEMPLATE_KINDS:
            raise ValueError(f"Unknown template kind {kind!r}. Use one of {TEMPLATE_KINDS}.")
        loc = self.locale(locale)
        if kind == "statement":
            return self._read("templates", language, loc, "exam.md")
        for base in (
            self.data_dir / "templates" / language / loc,
            ASSETS / "templates" / language / loc,
        ):
            if base.is_dir():
                for entry in sorted(base.iterdir(), key=lambda e: e.name):
                    if entry.name.startswith("solution."):
                        return entry.read_text("utf-8")
        return None

    def template_languages(self) -> list[str]:
        langs = set()
        for base in (self.data_dir / "templates", ASSETS / "templates"):
            if base.is_dir():
                langs |= {e.name for e in base.iterdir() if e.is_dir()}
        return sorted(langs)

    def course_profile(self) -> str | None:
        path = self.data_dir / "course.md"
        return path.read_text("utf-8") if path.is_file() else None

    def pandoc_header(self) -> str:
        return self._read("pandoc-header.tex") or ""

    def prompt(self, name: str) -> str:
        text = self._read("prompts", f"{name}.md")
        if text is None:
            raise FileNotFoundError(f"prompt {name!r} not found")
        return text

    @staticmethod
    def locales() -> tuple[str, ...]:
        return SUPPORTED_LOCALES
