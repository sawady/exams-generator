"""Runtime configuration, read from environment variables.

Every setting has an ``EXAMS_`` prefix. A ``.env`` file in the working
directory is loaded first (see ``server.main``), so the same variables can
live there.

=========================  ===========================================  ==================
Variable                   Meaning                                      Default
=========================  ===========================================  ==================
EXAMS_TRANSPORT            ``stdio`` or ``http`` (streamable HTTP)      ``stdio``
EXAMS_HTTP_HOST            Bind address in HTTP mode                    ``127.0.0.1``
EXAMS_HTTP_PORT            Port in HTTP mode                            ``8765``
EXAMS_BEARER_TOKEN         Token required in HTTP mode                  (none; required)
EXAMS_ALLOWED_HOSTS        Extra ``Host`` headers accepted in HTTP      (none)
                           mode, comma separated (``exams.example.org``)
EXAMS_DATA_DIR             Overrides for style guides, templates,       ``./data``
                           course profile and the pandoc header
EXAMS_DIR                  Where exams are stored. Can be a clone of a  ``$EXAMS_DATA_DIR/exams``
                           separate private git repository.
EXAMS_GIT_BACKUP           Commit every change in ``EXAMS_DIR``         ``true``
EXAMS_GIT_PUSH             Also ``git push`` after each commit          ``false``
EXAMS_LOCALE               Default exam language: ``en`` or ``es``      ``en``
EXAMS_CHECK_TIMEOUT        Seconds before a compiler run is killed      ``60``
EXAMS_PDF_ENGINE           pandoc ``--pdf-engine``                      ``pdflatex``
=========================  ===========================================  ==================

Checker-specific variables (``EXAMS_GHC``, ``EXAMS_CC``, ``EXAMS_CFLAGS``,
...) are documented in each checker module.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

SUPPORTED_LOCALES = ("en", "es")
LOCALE_NAMES = {"en": "English", "es": "Spanish (Español)"}

_TRUE = {"1", "true", "yes", "on"}


def _bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in _TRUE


def normalize_locale(value: str | None, default: str = "en") -> str:
    """Return a supported locale code (``es-AR`` -> ``es``); fall back to ``default``."""
    if not value:
        return default
    code = value.strip().lower().replace("_", "-").split("-")[0]
    return code if code in SUPPORTED_LOCALES else default


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path("data")
    exams_dir: Path = Path("data/exams")
    git_backup: bool = True
    git_push: bool = False
    locale: str = "en"
    transport: str = "stdio"
    http_host: str = "127.0.0.1"
    http_port: int = 8765
    bearer_token: str = ""
    allowed_hosts: tuple[str, ...] = field(default_factory=tuple)
    check_timeout: float = 60.0
    pdf_engine: str = "pdflatex"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env
        data_dir = Path(env.get("EXAMS_DATA_DIR") or "data").expanduser()
        exams_dir_raw = env.get("EXAMS_DIR")
        exams_dir = Path(exams_dir_raw).expanduser() if exams_dir_raw else data_dir / "exams"
        hosts = tuple(h.strip() for h in env.get("EXAMS_ALLOWED_HOSTS", "").split(",") if h.strip())
        return cls(
            data_dir=data_dir,
            exams_dir=exams_dir,
            git_backup=_bool(env.get("EXAMS_GIT_BACKUP"), True),
            git_push=_bool(env.get("EXAMS_GIT_PUSH"), False),
            locale=normalize_locale(env.get("EXAMS_LOCALE"), "en"),
            transport=(env.get("EXAMS_TRANSPORT") or "stdio").strip().lower(),
            http_host=env.get("EXAMS_HTTP_HOST") or "127.0.0.1",
            http_port=int(env.get("EXAMS_HTTP_PORT") or 8765),
            bearer_token=(env.get("EXAMS_BEARER_TOKEN") or "").strip(),
            allowed_hosts=hosts,
            check_timeout=float(env.get("EXAMS_CHECK_TIMEOUT") or 60),
            pdf_engine=env.get("EXAMS_PDF_ENGINE") or "pdflatex",
        )
