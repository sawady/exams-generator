"""MCP server: tools, resources and prompts for writing exams.

Run ``exams-generator`` (see ``config.py`` for the environment variables).
``EXAMS_TRANSPORT=stdio`` (default) is for a local client such as Claude
Code; ``EXAMS_TRANSPORT=http`` serves streamable HTTP on ``/mcp`` behind a
Bearer token.
"""

from __future__ import annotations

import base64
import hmac
import tempfile
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from . import __version__
from .checkers import CheckerRegistry, UnknownLanguageError
from .config import LOCALE_NAMES, SUPPORTED_LOCALES, Settings
from .content import Content
from .demos import DemoRunner
from .pdf import render_pdf, solution_markdown, toolchain_status
from .remote import RemoteDemoRunner
from .sandbox import Sandbox
from .storage import Storage, StorageError, check_summary, validate_filename, validate_name

INSTRUCTIONS = """\
Tools for writing programming exams whose reference solution is checked by a real
compiler and whose statement is rendered to PDF.

Typical flow: list_languages -> get_course_profile / get_style_guide / get_template ->
draft the solution and use check_snippet until it passes -> save_exam (statement +
solution files; it re-checks them) -> render_exam. Never save an exam whose check fails
without telling the user. Exams live in a private directory: do not copy real exams
into public places.
"""

RUN_DEMOS_INSTRUCTIONS = """\

run_demos executes the solution's demos and doctests in a sandbox. Only status "passed"
verified anything: "skipped" (no sandbox or runner, no toolchain, no demos) is not a pass.
"""

SOLUTION_HEADING = {"en": "Solution", "es": "Solución"}


def create_server(settings: Settings | None = None) -> MCPServer:
    settings = settings or Settings.from_env()
    storage = Storage(
        settings.exams_dir,
        git_backup=settings.git_backup,
        git_push=settings.git_push,
        default_locale=settings.locale,
    )
    content = Content(settings.data_dir, default_locale=settings.locale)
    registry = CheckerRegistry(timeout=settings.check_timeout)

    # run_demos: a separate runner if one is configured, bubblewrap here otherwise.
    # Never both: with a runner configured, this process never executes a solution.
    runner: DemoRunner | RemoteDemoRunner
    if settings.run_runner_url:
        remote = RemoteDemoRunner(
            registry, settings.run_runner_url, timeout=settings.run_runner_timeout
        )
        runner, demos_status = remote, remote.status
    else:
        sandbox = Sandbox(
            bwrap=settings.bwrap,
            timeout=settings.run_timeout,
            memory_mb=settings.run_memory_mb,
            ro_binds=settings.run_ro_binds,
            protected=(settings.exams_dir, settings.data_dir),
        )
        runner = DemoRunner(registry, sandbox)

        def demos_status() -> dict[str, Any]:
            return {"mode": "local", **sandbox.status().as_dict()}

    mcp = MCPServer(
        "exams-generator",
        title="Exams generator",
        instructions=INSTRUCTIONS + (RUN_DEMOS_INSTRUCTIONS if settings.run_demos else ""),
        version=__version__,
    )

    def fences() -> dict[str, str]:
        out: dict[str, str] = {}
        for checker in registry.all():
            for ext in checker.source_extensions + checker.header_extensions:
                out.setdefault(ext, checker.fence)
        return out

    def run_checks(solution: dict[str, str]) -> dict[str, Any]:
        if not solution:
            return {"ok": False, "results": [], "output": "No solution files to check."}
        results = registry.check_files(solution)
        if not results:
            known = ", ".join(registry.names)
            return {
                "ok": False,
                "results": [],
                "output": f"No checker owns these files ({', '.join(solution)}). Known: {known}.",
            }
        dicts = [r.as_dict() for r in results]
        # A skipped language (missing toolchain) is not a pass.
        ok = all(r.ok and not r.skipped for r in results)
        return {"ok": ok, "results": dicts, "output": "\n\n".join(r.as_text() for r in results)}

    # ----------------------------------------------------------- discovery

    @mcp.tool()
    def list_languages() -> dict[str, Any]:
        """Languages that can be checked, whether their toolchain is installed, the PDF
        toolchain status, supported exam locales and where exams are stored."""
        return {
            "languages": registry.describe(),
            "pdf": toolchain_status(settings.pdf_engine),
            "locales": {code: LOCALE_NAMES[code] for code in SUPPORTED_LOCALES},
            "default_locale": settings.locale,
            "exams_dir": str(settings.exams_dir),
            "git": storage.git_status(),
            "course_profile": content.course_profile() is not None,
            "demos": (
                {"enabled": True, **demos_status()} if settings.run_demos else {"enabled": False}
            ),
        }

    # ---------------------------------------------------------------- CRUD

    @mcp.tool()
    def list_exams() -> list[dict[str, Any]]:
        """List saved exams with their metadata."""
        return [
            {
                "name": m.name,
                "title": m.title,
                "description": m.description,
                "tags": m.tags,
                "locale": m.locale,
                "languages": m.languages,
                "solution_files": m.solution_files,
                "updated_at": m.updated_at,
                "rendered": m.rendered,
                "last_check_ok": (m.last_check or {}).get("ok"),
            }
            for m in storage.list_exams()
        ]

    @mcp.tool()
    def load_exam(name: str) -> dict[str, Any]:
        """Load a saved exam: metadata, Markdown statement and solution files."""
        try:
            exam = storage.load_exam(name)
        except StorageError as err:
            return {"ok": False, "error": str(err)}
        meta = exam.metadata
        return {
            "ok": True,
            "name": meta.name,
            "title": meta.title,
            "description": meta.description,
            "tags": meta.tags,
            "locale": meta.locale,
            "languages": meta.languages,
            "statement": exam.statement,
            "solution": exam.solution,
            "rendered": meta.rendered,
            "last_check": meta.last_check,
        }

    @mcp.tool()
    def save_exam(
        name: str,
        statement: str,
        solution: dict[str, str],
        title: str = "",
        description: str = "",
        tags: list[str] | None = None,
        locale: str | None = None,
        verify: bool = True,
    ) -> dict[str, Any]:
        """Save (or overwrite) an exam and commit it to the exams git repository.

        - name: identifier, 1-64 chars of [A-Za-z0-9_-] (e.g. "2026-midterm-trees").
        - statement: the Markdown handed to students (no solutions in it).
        - solution: reference solution as {filename: content}, e.g. {"Exam.hs": "..."} or
          {"queue.h": "...", "queue.c": "..."}. The extension selects the checker.
        - locale: language the exam is written in ("en" or "es").
        - verify: run the checkers on the solution and store the verdict (default true).

        Saving replaces the previous solution files and discards rendered PDFs.
        """
        solution = solution or {}
        try:
            validate_name(name)
            for filename in solution:
                validate_filename(filename)
        except StorageError as err:
            return {"ok": False, "error": str(err)}
        languages = registry.languages_for(solution)
        check = run_checks(solution) if verify else None
        try:
            storage.save_exam(
                name,
                statement,
                solution,
                title=title,
                description=description,
                tags=tags,
                locale=content.locale(locale) if locale else None,
                languages=languages,
                last_check=check_summary(check["ok"], check["results"]) if check else None,
            )
        except StorageError as err:
            return {"ok": False, "error": str(err)}
        payload: dict[str, Any] = {"ok": True, "name": name, "languages": languages}
        if check:
            payload["check"] = {"ok": check["ok"], "output": check["output"]}
        if storage.last_git_error:
            payload["git_warning"] = storage.last_git_error
        return payload

    @mcp.tool()
    def delete_exam(name: str) -> dict[str, Any]:
        """Delete a saved exam (the deletion is committed, so git history keeps it)."""
        try:
            storage.delete_exam(name)
        except StorageError as err:
            return {"ok": False, "error": str(err)}
        return {"ok": True, "name": name}

    # ------------------------------------------------------------ checking

    @mcp.tool()
    def check_snippet(language: str, code: str, filename: str | None = None) -> dict[str, Any]:
        """Type-check / compile a piece of code without saving it.

        language: one of the names from list_languages ("haskell", "c", "cpp", "python").
        filename: optional; matters for Haskell module names or C headers.
        """
        try:
            checker = registry.get(language)
        except UnknownLanguageError as err:
            return {"ok": False, "error": str(err)}
        result = checker.check_snippet(code, filename)
        return {"ok": result.ok and not result.skipped, **result.as_dict()}

    @mcp.tool()
    def check_exam(name: str) -> dict[str, Any]:
        """Check every solution file of a saved exam with the matching checker."""
        try:
            exam = storage.load_exam(name)
        except StorageError as err:
            return {"ok": False, "error": str(err)}
        check = run_checks(exam.solution)
        storage.record_check(name, check["ok"], check["results"])
        return {"name": name, **check}

    # ---------------------------------------------------------------- demos

    # Opt-in: without EXAMS_RUN_DEMOS this tool does not exist. It is the only way
    # the server executes a solution; the checkers above never do.
    if settings.run_demos:

        @mcp.tool()
        def run_demos(name: str = "", extra_files: dict[str, str] | None = None) -> dict[str, Any]:
            """Execute a solution's demos and doctests in a sandbox, here or in a separate
            runner (no network, no access to the exams, killed at a timeout).

            - name: a saved exam, whose solution files are used. Optional.
            - extra_files: {filename: content} added on top of them, or run on their own
              if there is no name. Use it to supply a main() for C/C++ solutions.

            Python runs doctests from docstrings, Haskell runs `>>> expr` comment lines
            against the expected output below them, C/C++ build and run a main() (exit 0
            passes). "ok" is true only if every language has status "passed"; "skipped"
            (no sandbox or runner, no toolchain, no demos) has not verified anything. Nothing
            is saved.
            """
            files: dict[str, str] = {}
            try:
                if name:
                    files.update(storage.load_exam(name).solution)
                for filename in extra_files or {}:
                    validate_filename(filename)
            except StorageError as err:
                return {"ok": False, "error": str(err)}
            files.update(extra_files or {})
            return {"name": name, **runner.run_files(files)} if name else runner.run_files(files)

    # ----------------------------------------------------------- rendering

    def _render(name: str, variant: str) -> dict[str, Any]:
        try:
            exam = storage.load_exam(name)
            out = storage.pdf_path(name, variant)
        except StorageError as err:
            return {"ok": False, "error": str(err)}
        if variant == "statement":
            markdown = exam.statement
        else:
            heading = SOLUTION_HEADING.get(exam.metadata.locale, "Solution")
            markdown = solution_markdown(
                exam.metadata.title, exam.solution, fences(), exam.statement, heading
            )
        result = render_pdf(
            markdown,
            out,
            content.pandoc_header(),
            pdf_engine=settings.pdf_engine,
            lang=content.locale(exam.metadata.locale or None),
        )
        if not result.ok:
            return {"ok": False, "error": result.log}
        storage.mark_rendered(name, variant)
        payload: dict[str, Any] = {
            "ok": True,
            "path": str(out),
            "page_count": result.page_count,
            "size_bytes": result.size_bytes,
            "lang": result.lang,
        }
        if result.warning:
            payload["warning"] = result.warning
        return payload

    @mcp.tool()
    def render_exam(name: str, variant: str = "statement") -> dict[str, Any]:
        """Render a saved exam to PDF next to it.

        variant: "statement" (exam.pdf, for students) or "solution" (solution.pdf: the
        statement followed by every solution file, for teachers).
        """
        return _render(name, variant)

    @mcp.tool()
    def get_exam_pdf(name: str, variant: str = "statement") -> dict[str, Any]:
        """Return an exam PDF as base64, rendering it first if needed."""
        try:
            pdf_path = storage.pdf_path(name, variant)
        except StorageError as err:
            return {"ok": False, "error": str(err)}
        if not storage.exists(name):
            return {"ok": False, "error": f"Exam {name!r} not found."}
        if not pdf_path.exists():
            rendered = _render(name, variant)
            if not rendered.get("ok"):
                return rendered
        return {
            "ok": True,
            "name": name,
            "variant": variant,
            "size_bytes": pdf_path.stat().st_size,
            "pdf_base64": base64.b64encode(pdf_path.read_bytes()).decode("ascii"),
        }

    @mcp.tool()
    def preview_pdf(
        markdown: str, return_bytes: bool = False, locale: str | None = None
    ) -> dict[str, Any]:
        """Render arbitrary Markdown to PDF without saving (page count and size; with
        return_bytes=true also the PDF as base64). locale: "en" or "es" (hyphenation and
        LaTeX labels); defaults to the server's."""
        with tempfile.TemporaryDirectory(prefix="exams-preview-") as tmp:
            out = Path(tmp) / "preview.pdf"
            result = render_pdf(
                markdown,
                out,
                content.pandoc_header(),
                pdf_engine=settings.pdf_engine,
                lang=content.locale(locale),
            )
            if not result.ok:
                return {"ok": False, "error": result.log}
            payload: dict[str, Any] = {
                "ok": True,
                "page_count": result.page_count,
                "size_bytes": result.size_bytes,
                "lang": result.lang,
            }
            if result.warning:
                payload["warning"] = result.warning
            if return_bytes:
                payload["pdf_base64"] = base64.b64encode(out.read_bytes()).decode("ascii")
            return payload

    # -------------------------------------------------------------- content

    @mcp.tool()
    def get_style_guide(language: str | None = None, locale: str | None = None) -> str:
        """Writing conventions for exams: the general guide plus the language-specific one."""
        lang = None
        if language:
            try:
                lang = registry.get(language).name
            except UnknownLanguageError:
                lang = language
        return content.style_guide(lang, locale)

    @mcp.tool()
    def get_template(language: str, kind: str = "statement", locale: str | None = None) -> str:
        """Starting point for a new exam. kind: "statement" (Markdown) or "solution" (code)."""
        try:
            lang = registry.get(language).name
            text = content.template(lang, kind, locale)
        except (UnknownLanguageError, ValueError) as err:
            return f"ERROR: {err}"
        return text or f"(no {kind} template for {lang!r} in locale {content.locale(locale)!r})"

    @mcp.tool()
    def get_course_profile() -> str:
        """The course profile: course-specific rules (allowed language subset, exercise
        structure, header). Takes precedence over the generic style guide."""
        return content.course_profile() or (
            "(no course profile configured: create course.md in EXAMS_DATA_DIR; "
            "see examples/course-profile.md in the exams-generator repository)"
        )

    # ------------------------------------------------------------ resources

    @mcp.resource("exams://course-profile", mime_type="text/markdown")
    def resource_course_profile() -> str:
        return get_course_profile()

    @mcp.resource("exams://style-guide/{locale}", mime_type="text/markdown")
    def resource_style_guide(locale: str) -> str:
        return content.style_guide(None, locale)

    @mcp.resource("exams://template/{language}/{locale}/{kind}", mime_type="text/plain")
    def resource_template(language: str, locale: str, kind: str) -> str:
        return get_template(language, kind, locale)

    @mcp.resource("exams://exam/{name}/statement", mime_type="text/markdown")
    def resource_exam_statement(name: str) -> str:
        return storage.load_exam(name).statement

    # -------------------------------------------------------------- prompts

    @mcp.prompt(title="Write an exam")
    def write_exam(
        topic: str,
        languages: str = "haskell",
        locale: str = "",
        kind: str = "exam",
        exercises: str = "4",
        notes: str = "",
    ) -> str:
        """Guide the model through drafting, checking, saving and rendering a new exam."""
        loc = content.locale(locale or None)
        return content.prompt("write_exam").format(
            topic=topic,
            languages=languages,
            locale=loc,
            locale_name=LOCALE_NAMES[loc],
            kind=kind,
            exercises=exercises,
            notes=notes or "(none)",
        )

    @mcp.prompt(title="Review an exam")
    def review_exam(name: str) -> str:
        """Review a saved exam against the course profile and the style guide."""
        return content.prompt("review_exam").format(name=name)

    return mcp


# ------------------------------------------------------------------- HTTP


class BearerAuth:
    """ASGI middleware: require ``Authorization: Bearer <token>`` except on /healthz."""

    def __init__(self, app: Any, token: str) -> None:
        self.app = app
        self.token = token.encode()

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        from starlette.responses import JSONResponse, PlainTextResponse

        if scope.get("path") == "/healthz":
            await PlainTextResponse("ok")(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        auth = headers.get(b"authorization", b"")
        prefix = b"Bearer "
        if not (auth.startswith(prefix) and hmac.compare_digest(auth[len(prefix) :], self.token)):
            await JSONResponse({"error": "unauthorized"}, status_code=401)(scope, receive, send)
            return
        await self.app(scope, receive, send)


def build_http_app(mcp: MCPServer, settings: Settings) -> Any:
    if not settings.bearer_token:
        raise SystemExit("EXAMS_BEARER_TOKEN is empty; refusing to serve HTTP without auth.")
    security = None
    if settings.allowed_hosts:
        from mcp.server.transport_security import TransportSecuritySettings

        hosts = list(settings.allowed_hosts) + ["127.0.0.1:*", "localhost:*"]
        security = TransportSecuritySettings(
            allowed_hosts=hosts,
            allowed_origins=[f"https://{h}" for h in settings.allowed_hosts]
            + ["http://127.0.0.1:*", "http://localhost:*"],
        )
    inner = mcp.streamable_http_app(transport_security=security, host=settings.http_host)
    return BearerAuth(inner, settings.bearer_token)


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()
    settings = Settings.from_env()
    mcp = create_server(settings)
    if settings.transport == "stdio":
        mcp.run(transport="stdio")
    elif settings.transport in {"http", "streamable-http"}:
        import uvicorn

        app = build_http_app(mcp, settings)
        uvicorn.run(app, host=settings.http_host, port=settings.http_port, log_level="info")
    else:
        raise SystemExit(f"Unknown EXAMS_TRANSPORT {settings.transport!r}. Use stdio or http.")


if __name__ == "__main__":
    main()
