import base64
import os
import sys
from pathlib import Path

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from starlette.testclient import TestClient

from exams_generator.config import Settings
from exams_generator.server import build_http_app, create_server
from tests.conftest import requires, requires_pdf, requires_sandbox

pytestmark = pytest.mark.anyio

EXPECTED_TOOLS = {
    "list_languages",
    "list_exams",
    "load_exam",
    "save_exam",
    "delete_exam",
    "check_snippet",
    "check_exam",
    "render_exam",
    "get_exam_pdf",
    "preview_pdf",
    "get_style_guide",
    "get_template",
    "get_course_profile",
}


async def call(client, tool, **args):
    result = await client.call_tool(tool, args)
    if result.structured_content is not None:
        data = result.structured_content
        # Non-object returns (str, list) are wrapped as {"result": ...}.
        return data.get("result", data) if set(data) == {"result"} else data
    return result.content[0].text


async def test_lists_tools_prompts_and_templates(settings):
    async with Client(create_server(settings)) as client:
        tools = {t.name for t in (await client.list_tools()).tools}
        assert EXPECTED_TOOLS <= tools
        prompts = {p.name for p in (await client.list_prompts()).prompts}
        assert prompts == {"write_exam", "review_exam"}
        prompt = await client.get_prompt("write_exam", {"topic": "queues", "locale": "es"})
        assert "Spanish" in prompt.messages[0].content.text
        resource = await client.read_resource("exams://template/haskell/es/statement")
        assert "Ejercicio" in resource.contents[0].text


async def test_list_languages(settings):
    async with Client(create_server(settings)) as client:
        info = await call(client, "list_languages")
        langs = {row["language"] for row in info["languages"]}
        assert {"haskell", "c", "cpp", "python"} <= langs
        assert set(info["locales"]) == {"en", "es"}
        assert info["exams_dir"] == str(settings.exams_dir)


async def test_save_load_delete_python(settings):
    async with Client(create_server(settings)) as client:
        saved = await call(
            client,
            "save_exam",
            name="py-1",
            statement="# Exam\n",
            solution={"solution.py": "def f(x: int) -> int:\n    return x\n"},
            title="T",
            locale="es",
        )
        assert saved["ok"] and saved["check"]["ok"], saved
        assert saved["languages"] == ["python"]

        loaded = await call(client, "load_exam", name="py-1")
        assert loaded["locale"] == "es" and loaded["last_check"]["ok"] is True

        listed = await call(client, "list_exams")
        assert [e["name"] for e in listed] == ["py-1"]

        bad = await call(
            client, "save_exam", name="py-2", statement="", solution={"s.py": "def f(:\n"}
        )
        assert bad["ok"] and not bad["check"]["ok"]  # saved, but flagged
        assert not (await call(client, "check_exam", name="py-2"))["ok"]

        assert (await call(client, "delete_exam", name="py-1"))["ok"]
        assert not (await call(client, "load_exam", name="py-1"))["ok"]


async def test_save_rejects_bad_filenames(settings):
    async with Client(create_server(settings)) as client:
        res = await call(client, "save_exam", name="x", statement="", solution={"../a.py": ""})
        assert not res["ok"] and "filename" in res["error"]


async def test_check_snippet_unknown_language(settings):
    async with Client(create_server(settings)) as client:
        res = await call(client, "check_snippet", language="cobol", code="")
        assert not res["ok"] and "Unknown language" in res["error"]


@requires("haskell")
async def test_check_snippet_haskell(settings):
    async with Client(create_server(settings)) as client:
        res = await call(client, "check_snippet", language="hs", code="f :: Int\nf = True\n")
        assert not res["ok"] and "Exam.hs:2" in res["output"]


async def test_content_tools(settings):
    async with Client(create_server(settings)) as client:
        guide = await call(client, "get_style_guide", language="c", locale="es")
        assert "Guía de estilo" in guide and "# C" in guide
        tpl = await call(client, "get_template", language="python", kind="solution")
        assert "Exercise 1" in tpl
        assert "ERROR" in await call(client, "get_template", language="python", kind="nope")
        assert "no course profile" in await call(client, "get_course_profile")


@requires_pdf
async def test_render_and_get_pdf(settings):
    async with Client(create_server(settings)) as client:
        await call(
            client,
            "save_exam",
            name="r",
            statement="# Exam\n\nText.\n",
            solution={"s.py": "x = 1\n"},
            verify=False,
        )
        res = await call(client, "render_exam", name="r", variant="solution")
        assert res["ok"], res
        assert res["page_count"] == 2  # statement + answer key on a new page
        pdf = await call(client, "get_exam_pdf", name="r")  # statement: rendered on demand
        assert base64.b64decode(pdf["pdf_base64"]).startswith(b"%PDF")
        loaded = await call(client, "load_exam", name="r")
        assert loaded["rendered"] == ["solution", "statement"]
        preview = await call(client, "preview_pdf", markdown="# hi", return_bytes=True)
        assert preview["ok"] and preview["pdf_base64"]


@requires_pdf
async def test_render_spanish_exam(settings):
    """A Spanish exam renders with babel-spanish, or without it plus a warning."""
    async with Client(create_server(settings)) as client:
        await call(
            client,
            "save_exam",
            name="es",
            statement="# Examen\n\nTexto con acentos: árbol, ñandú.\n",
            solution={"s.py": "x = 1\n"},
            locale="es",
            verify=False,
        )
        res = await call(client, "render_exam", name="es")
        assert res["ok"], res
        assert res["lang"] == "es" or "texlive-lang-spanish" in res["warning"]
        preview = await call(client, "preview_pdf", markdown="# hola", locale="es")
        assert preview["ok"] and (preview["lang"] == "es" or preview["warning"])


def test_http_requires_token(settings):
    with pytest.raises(SystemExit):
        build_http_app(create_server(settings), settings)


def test_http_bearer_auth(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "d",
        exams_dir=tmp_path / "e",
        bearer_token="s3cret",
        allowed_hosts=("testserver",),  # the Host header TestClient sends
    )
    app = build_http_app(create_server(settings), settings)
    with TestClient(app) as http:
        assert http.get("/healthz").text == "ok"
        assert http.post("/mcp", json={}).status_code == 401
        wrong = http.post("/mcp", json={}, headers={"Authorization": "Bearer nope"})
        assert wrong.status_code == 401
        ok = http.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "t", "version": "0"},
                },
            },
            headers={
                "Authorization": "Bearer s3cret",
                "Accept": "application/json, text/event-stream",
            },
        )
        assert ok.status_code == 200, ok.text


async def test_stdio_end_to_end(tmp_path):
    """Start the real entry point over stdio, as Claude Code does."""
    env = {
        **os.environ,
        "EXAMS_TRANSPORT": "stdio",
        "EXAMS_DATA_DIR": str(tmp_path / "data"),
        "EXAMS_DIR": str(tmp_path / "exams"),
        "EXAMS_GIT_BACKUP": "false",
    }
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "exams_generator.server"],
        env=env,
        cwd=str(Path(__file__).parent),
    )
    async with Client(params) as client:
        tools = {t.name for t in (await client.list_tools()).tools}
        assert EXPECTED_TOOLS <= tools
        res = await call(client, "check_snippet", language="python", code="x: int = 1\n")
        assert res["ok"], res


async def test_run_demos_is_off_by_default(settings):
    async with Client(create_server(settings)) as client:
        names = {t.name for t in (await client.list_tools()).tools}
        assert "run_demos" not in names
        info = await call(client, "list_languages")
        assert info["demos"] == {"enabled": False}


async def test_run_demos_appears_only_when_enabled(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        exams_dir=tmp_path / "exams",
        run_demos=True,
        bwrap=str(tmp_path / "no-bwrap"),
    )
    async with Client(create_server(settings)) as client:
        names = {t.name for t in (await client.list_tools()).tools}
        assert "run_demos" in names
        info = await call(client, "list_languages")
        assert info["demos"]["enabled"] is True
        assert info["demos"]["available"] is False
        code = '"""\n>>> 1\n1\n"""\n'
        out = await call(client, "run_demos", extra_files={"solution.py": code})
        assert out["ok"] is False
        assert out["results"][0]["status"] == "skipped"


async def test_run_demos_rejects_bad_filenames_and_unknown_exams(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        exams_dir=tmp_path / "exams",
        run_demos=True,
        bwrap=str(tmp_path / "no-bwrap"),
    )
    async with Client(create_server(settings)) as client:
        out = await call(client, "run_demos", extra_files={"../evil.py": "x = 1\n"})
        assert out["ok"] is False
        assert "error" in out
        out = await call(client, "run_demos", name="does-not-exist")
        assert out["ok"] is False
        assert "error" in out


@requires_sandbox
async def test_run_demos_end_to_end_on_a_saved_exam(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        exams_dir=tmp_path / "exams",
        run_demos=True,
        bwrap=Settings.from_env().bwrap,
    )
    code = '"""\n>>> add(1, 2)\n3\n"""\n\n\ndef add(a, b):\n    return a + b\n'
    async with Client(create_server(settings)) as client:
        await call(client, "save_exam", name="demo", statement="# Demo\n", solution={"s.py": code})
        out = await call(client, "run_demos", name="demo")
        assert out["ok"] is True, out["output"]
        assert out["results"][0]["passed"] == 1
        assert out["name"] == "demo"
