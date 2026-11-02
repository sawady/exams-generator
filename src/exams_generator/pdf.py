"""Render Markdown to PDF with pandoc (+ a LaTeX engine, pdflatex by default).

The defaults are tuned for printed exams: 1.5 cm margins, 11 pt, and a
LaTeX header that tightens section and list spacing. The header comes from
``Content.pandoc_header`` so it can be overridden per installation.

With ``lang`` set, pandoc loads babel (pdflatex) or polyglossia (xelatex) for that
language, which gives correct hyphenation and localised names. If the LaTeX
installation lacks the language files (e.g. ``texlive-lang-spanish`` on Debian), the
PDF is rendered again without ``lang`` and the result carries a warning.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PdfRenderResult:
    ok: bool
    output_path: Path | None
    page_count: int | None
    size_bytes: int | None
    log: str
    lang: str | None = None
    warning: str = ""


LANGUAGE_PACKAGES = {"es": "texlive-lang-spanish", "en": "texlive-latex-base"}

# Messages LaTeX prints when babel/polyglossia cannot load a language.
_LANGUAGE_ERRORS = re.compile(
    r"Package (babel|polyglossia) Error|\.ldf'? (was )?not found|language definition file",
    re.IGNORECASE,
)


def language_unsupported(log: str) -> bool:
    """Whether a failed LaTeX run failed because a language is not installed."""
    return bool(_LANGUAGE_ERRORS.search(log))


def toolchain_status(pdf_engine: str = "pdflatex") -> dict[str, object]:
    pandoc = shutil.which("pandoc")
    engine = shutil.which(pdf_engine)
    hint = ""
    if not pandoc or not engine:
        hint = (
            "Install pandoc and a LaTeX distribution, e.g. `apt install pandoc "
            "texlive-latex-recommended texlive-fonts-recommended lmodern`."
        )
    return {
        "available": bool(pandoc and engine),
        "pandoc": pandoc,
        "pdf_engine": pdf_engine,
        "pdf_engine_path": engine,
        "hint": hint,
    }


def page_count(pdf_path: Path) -> int | None:
    """Count pages, with ghostscript if present, else by scanning the PDF objects."""
    if shutil.which("gs"):
        try:
            proc = subprocess.run(
                [
                    "gs",
                    "-q",
                    "-dNODISPLAY",
                    "-dNOSAFER",
                    "-c",
                    f"({pdf_path}) (r) file runpdfbegin pdfpagecount = quit",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode == 0:
                return int(proc.stdout.strip())
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
    try:
        raw = pdf_path.read_bytes()
    except OSError:
        return None
    count = len(re.findall(rb"/Type\s*/Page(?![s\w])", raw))
    return count or None


def render_pdf(
    md_content: str,
    output_path: Path,
    header_tex: str = "",
    *,
    pdf_engine: str = "pdflatex",
    margin: str = "1.5cm",
    fontsize: str = "11pt",
    linestretch: str = "0.95",
    timeout: float = 120.0,
    lang: str | None = None,
) -> PdfRenderResult:
    """Render ``md_content`` to ``output_path``, in language ``lang`` (BCP 47, e.g.
    ``"es"``) when given and supported by the LaTeX installation."""
    status = toolchain_status(pdf_engine)
    if not status["available"]:
        return PdfRenderResult(False, None, None, None, str(status["hint"]))

    def attempt(language: str | None) -> PdfRenderResult:
        return _render(
            md_content,
            output_path,
            header_tex,
            pdf_engine=pdf_engine,
            margin=margin,
            fontsize=fontsize,
            linestretch=linestretch,
            timeout=timeout,
            lang=language,
        )

    result = attempt(lang)
    if lang and not result.ok and language_unsupported(result.log):
        result = attempt(None)
        package = LANGUAGE_PACKAGES.get(lang.split("-")[0], "the LaTeX support for it")
        result.warning = (
            f"LaTeX has no support for language {lang!r}: rendered without it (default "
            f"hyphenation and English labels). Install {package} to fix this."
        )
    return result


def _render(
    md_content: str,
    output_path: Path,
    header_tex: str,
    *,
    pdf_engine: str,
    margin: str,
    fontsize: str,
    linestretch: str,
    timeout: float,
    lang: str | None,
) -> PdfRenderResult:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="exams-pdf-") as tmp:
        md_path = Path(tmp) / "exam.md"
        md_path.write_text(md_content, encoding="utf-8")
        tmp_pdf = Path(tmp) / "exam.pdf"
        args = [
            "pandoc",
            str(md_path),
            "-o",
            str(tmp_pdf),
            f"--pdf-engine={pdf_engine}",
            "-V",
            f"geometry:margin={margin}",
            "-V",
            f"fontsize={fontsize}",
            "-V",
            f"linestretch={linestretch}",
            "-V",
            "colorlinks=true",
        ]
        if lang:
            args.extend(["-V", f"lang={lang}"])
        if header_tex.strip():
            header_path = Path(tmp) / "header.tex"
            header_path.write_text(header_tex, encoding="utf-8")
            args.extend(["-H", str(header_path)])

        try:
            proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=tmp)
        except subprocess.TimeoutExpired:
            return PdfRenderResult(False, None, None, None, f"pandoc timed out after {timeout:g}s")

        log = (proc.stdout + proc.stderr).strip()
        if proc.returncode != 0 or not tmp_pdf.exists():
            return PdfRenderResult(False, None, None, None, log or "pandoc failed without output.")
        # Move into place only on success so a failed render keeps the old PDF.
        shutil.move(str(tmp_pdf), output_path)

    return PdfRenderResult(
        ok=True,
        output_path=output_path,
        page_count=page_count(output_path),
        size_bytes=output_path.stat().st_size,
        log=log,
        lang=lang,
    )


def solution_markdown(
    title: str,
    solution: dict[str, str],
    fences: dict[str, str],
    statement: str = "",
    heading: str = "Solution",
) -> str:
    """Build the answer-key document: optional statement, then every solution file."""
    parts = []
    if statement.strip():
        parts.append(statement.rstrip())
        parts.append("\\newpage")
    parts.append(f"# {heading}{': ' + title if title else ''}")
    for filename, code in solution.items():
        fence = fences.get(Path(filename).suffix.lower(), "")
        ticks = "````" if "```" in code else "```"
        parts.append(f"## `{filename}`\n\n{ticks}{fence}\n{code.rstrip()}\n{ticks}")
    return "\n\n".join(parts) + "\n"
