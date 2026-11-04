import shutil
import subprocess

import pytest

from exams_generator.content import Content
from exams_generator.pdf import (
    language_unsupported,
    page_count,
    render_pdf,
    solution_markdown,
    toolchain_status,
)
from tests.conftest import requires_pdf


def test_toolchain_status_shape():
    status = toolchain_status()
    assert set(status) >= {"available", "pandoc", "pdf_engine", "hint"}


def test_missing_engine_reports_hint(tmp_path):
    result = render_pdf("# x", tmp_path / "x.pdf", pdf_engine="no-such-latex-engine")
    assert not result.ok and "pandoc" in result.log


def test_solution_markdown():
    md = solution_markdown(
        "Trees", {"Exam.hs": "f = 1", "a.c": "```"}, {".hs": "haskell"}, "# Stmt", "Solución"
    )
    assert md.startswith("# Stmt")
    assert "\\newpage" in md
    assert "# Solución: Trees" in md
    assert "```haskell\nf = 1\n```" in md
    assert "````\n```\n````" in md  # fences that contain ``` get a longer fence


@requires_pdf
def test_render_statement(tmp_path):
    header = Content(tmp_path).pandoc_header()
    md = (
        "# Exam — Ñandú\n\nSome **bold** text, `code` and $x^2$.\n\n"
        "```haskell\nf :: Int\nf = 1\n```\n"
    )
    result = render_pdf(md, tmp_path / "out" / "exam.pdf", header)
    assert result.ok, result.log
    assert result.output_path.read_bytes().startswith(b"%PDF")
    assert result.page_count == 1
    assert page_count(result.output_path) == 1


@requires_pdf
def test_render_failure_keeps_previous_pdf(tmp_path):
    out = tmp_path / "exam.pdf"
    out.write_bytes(b"%PDF-old")
    result = render_pdf("\\undefinedcontrolsequencexyz", out)
    assert not result.ok and result.log
    assert out.read_bytes() == b"%PDF-old"


def test_language_unsupported_detects_babel_errors():
    assert language_unsupported(
        "! Package babel Error: Unknown option 'spanish'. Either you misspelled it\n"
        "(babel) or the language definition file spanish.ldf was not found."
    )
    assert language_unsupported("! Package polyglossia Error: The current roman font ...")
    assert not language_unsupported("! Undefined control sequence.")


def _babel_has(language: str) -> bool:
    if not shutil.which("kpsewhich"):
        pytest.skip("kpsewhich not installed")
    out = subprocess.run(["kpsewhich", f"{language}.ldf"], capture_output=True, text=True)
    return bool(out.stdout.strip())


@requires_pdf
def test_render_in_spanish(tmp_path):
    """With babel-spanish installed the PDF uses it; without it, it falls back with a
    warning. Either way a PDF comes out."""
    md = "# Ejercicio 1\n\nUna oración con **separación** en sílabas: ¿anduvo?\n"
    result = render_pdf(md, tmp_path / "es.pdf", lang="es")
    assert result.ok, result.log
    if _babel_has("spanish"):
        assert result.lang == "es" and not result.warning
    else:
        assert result.lang is None and "texlive-lang-spanish" in result.warning


@requires_pdf
def test_render_in_english(tmp_path):
    result = render_pdf("# Exercise 1\n\nSome text.\n", tmp_path / "en.pdf", lang="en")
    assert result.ok, result.log
    if _babel_has("english"):
        assert result.lang == "en" and not result.warning


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc not installed")
def test_br_in_table_cells_becomes_line_break(tmp_path):
    # The style guides put one line of code per <br> in two-column tables; without
    # the filter pandoc drops the <br> and the lines run together in the PDF.
    from exams_generator.pdf import LINE_BREAK_FILTER

    filter_path = tmp_path / "line-breaks.lua"
    filter_path.write_text(LINE_BREAK_FILTER, encoding="utf-8")
    md = (
        "| `a.h` | `a.c` |\n|---|---|\n"
        "| `struct S;`<br>`typedef struct S* T;` | `int x;`<br/>`int y;` |\n"
    )
    latex = subprocess.run(
        ["pandoc", "-f", "markdown", "-t", "latex", "--lua-filter", str(filter_path)],
        input=md,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    flat = "".join(latex.split())
    assert "<br" not in latex
    # Without the filter both lines end up glued: \texttt{struct\ S;}\texttt{typedef...}
    assert "S;}\\texttt{typedef" not in flat, latex
    assert "x;}\\texttt{int" not in flat, latex
