"""The separate demo runner: its protocol, the server's client, and what happens when it fails.

The runner here runs in-process, on a real HTTP port, with a ProcessSandbox over temporary
directories and without the process sweep (which only makes sense alone in a container).
What the container adds (no network, no files or variables of the server) is checked
against the real compose setup in test_runner_e2e.py.
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import uvicorn
from mcp import Client
from starlette.testclient import TestClient

from exams_generator.checkers import CheckerRegistry
from exams_generator.config import Settings
from exams_generator.demos import DemoRunner
from exams_generator.remote import PROTOCOL, RemoteDemoRunner
from exams_generator.runner import (
    MAX_REQUEST_BYTES,
    BadRequest,
    cgroup_limits,
    create_app,
    forbidden_env_problem,
    parse_request,
    pid_namespace_problem,
    pids_limit_problem,
)
from exams_generator.sandbox import ProcessSandbox
from exams_generator.server import create_server
from tests.conftest import requires
from tests.test_demos import C_MAIN, PY_FAIL, PY_PASS

REGISTRY = CheckerRegistry(load_plugins=False)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def process_sandbox(tmp_path: Path, timeout: float = 20.0) -> ProcessSandbox:
    roots = [tmp_path / name for name in ("input", "work", "tmp")]
    for root in roots:
        root.mkdir(exist_ok=True)
    return ProcessSandbox(
        input_root=str(roots[0]),
        work_root=str(roots[1]),
        tmp_root=str(roots[2]),
        timeout=timeout,
        # RLIMIT_NPROC counts every process of the user running the tests.
        max_processes=None,
    )


class Serving:
    """A uvicorn server in a thread, stopped on exit."""

    def __init__(self, app) -> None:
        self.port = free_port()
        self.server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="warning")
        )
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self) -> str:
        self.thread.start()
        deadline = time.monotonic() + 10
        while not self.server.started:
            assert time.monotonic() < deadline, "the runner did not start"
            time.sleep(0.02)
        return f"http://127.0.0.1:{self.port}"

    def __exit__(self, *exc) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)


@pytest.fixture
def runner_url(tmp_path):
    app = create_app(DemoRunner(REGISTRY, process_sandbox(tmp_path)), queue_timeout=0.5)
    with Serving(app) as url:
        yield url


def fake_runner(respond):
    """A runner that answers every request with ``respond(handler) -> (code, body)``."""

    class Handler(BaseHTTPRequestHandler):
        def _answer(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            self.rfile.read(length)
            code, body = respond(self)
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = _answer

        def log_message(self, *args) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def remote(url: str, timeout: float = 30.0) -> RemoteDemoRunner:
    return RemoteDemoRunner(REGISTRY, url, timeout=timeout)


def statuses(out) -> list[str]:
    return [r["status"] for r in out["results"]]


# ------------------------------------------------------------- the real runner


def test_remote_python_doctests_pass(runner_url):
    out = remote(runner_url).run_files({"solution.py": PY_PASS})
    assert out["ok"] is True, out["output"]
    assert out["results"][0]["passed"] == 1
    assert out["sandbox"]["mode"] == "remote"


def test_remote_python_doctests_fail(runner_url):
    out = remote(runner_url).run_files({"solution.py": PY_FAIL})
    assert out["ok"] is False
    assert statuses(out) == ["failed"]
    assert "exams-doctest" not in out["output"]


@requires("c")
def test_remote_c_main_runs(runner_url):
    out = remote(runner_url).run_files({"demo.c": C_MAIN})
    assert statuses(out) == ["passed"], out["output"]
    out = remote(runner_url).run_files({"demo.c": C_MAIN.replace("return 0", "return 3")})
    assert statuses(out) == ["failed"]
    assert "exit status 3" in out["output"]


def test_remote_no_demos_is_skipped(runner_url):
    out = remote(runner_url).run_files({"solution.py": "x = 1\n"})
    assert out["ok"] is False
    assert statuses(out) == ["skipped"]


def test_remote_status(runner_url):
    status = remote(runner_url).status()
    assert status["available"] is True
    assert status["mode"] == "remote"
    assert "python" in {row["language"] for row in status["languages"]}


def test_runs_get_an_empty_environment(runner_url, monkeypatch):
    # The runner lives in this test's process here; its variables must not reach a run.
    monkeypatch.setenv("EXAMS_BEARER_TOKEN", "do-not-leak")
    code = (
        '"""\n>>> import os\n>>> sorted(k for k in os.environ if k.startswith("EXAMS_"))\n[]\n'
        '>>> "do-not-leak" in str(os.environ)\nFalse\n"""\n'
    )
    out = remote(runner_url).run_files({"probe.py": code})
    assert out["ok"] is True, out["output"]


def test_run_directories_are_emptied(tmp_path):
    sandbox = process_sandbox(tmp_path)
    run = sandbox.run({"a.txt": "x"}, "sh -c 'echo hi > left.txt; cat a.txt'")
    assert run.started and run.built and run.stdout == "x"
    for name in ("input", "work", "tmp"):
        assert list((tmp_path / name).iterdir()) == [], name


def test_process_sandbox_timeout_kills_the_group(tmp_path):
    sandbox = process_sandbox(tmp_path, timeout=1)
    marker = tmp_path / "survivor"
    started = time.monotonic()
    run = sandbox.run({}, f"sh -c '(sleep 3; touch {marker}) & sleep 30'")
    assert run.timed_out and time.monotonic() - started < 10
    time.sleep(3.5)
    assert not marker.exists()


# ------------------------------------------------------------ through the server


@pytest.mark.anyio
async def test_server_uses_the_runner(tmp_path, runner_url):
    settings = Settings(
        data_dir=tmp_path / "data",
        exams_dir=tmp_path / "exams",
        run_demos=True,
        run_runner_url=runner_url,
        bwrap=str(tmp_path / "no-bwrap"),  # a local run would be skipped
    )
    async with Client(create_server(settings)) as client:
        result = await client.call_tool("run_demos", {"extra_files": {"solution.py": PY_PASS}})
        out = result.structured_content
        assert out["ok"] is True, out
        info = (await client.call_tool("list_languages", {})).structured_content
        assert info["demos"]["mode"] == "remote" and info["demos"]["available"] is True


@pytest.mark.anyio
async def test_server_without_a_runner_url_stays_local(tmp_path):
    settings = Settings(data_dir=tmp_path / "d", exams_dir=tmp_path / "e", run_demos=True)
    async with Client(create_server(settings)) as client:
        info = (await client.call_tool("list_languages", {})).structured_content
        assert info["demos"]["mode"] == "local"
        assert info["demos"]["tool"] == settings.bwrap


@pytest.mark.anyio
async def test_server_with_runner_down_reports_skipped(tmp_path):
    url = f"http://127.0.0.1:{free_port()}"
    settings = Settings(
        data_dir=tmp_path / "d", exams_dir=tmp_path / "e", run_demos=True, run_runner_url=url
    )
    async with Client(create_server(settings)) as client:
        result = await client.call_tool("run_demos", {"extra_files": {"solution.py": PY_PASS}})
        out = result.structured_content
        assert out["ok"] is False
        assert out["results"][0]["status"] == "skipped"
        assert "did not answer" in out["output"]
        info = (await client.call_tool("list_languages", {})).structured_content
        assert info["demos"]["available"] is False


def test_default_timeout_is_a_minute():
    assert RemoteDemoRunner(REGISTRY, "http://runner:8766").timeout == 60


def test_invalid_runner_url_is_refused(tmp_path):
    settings = Settings(data_dir=tmp_path, exams_dir=tmp_path / "e", run_runner_url="runner:8766")
    with pytest.raises(ValueError, match="http"):
        create_server(settings)


# -------------------------------------------- whatever goes wrong is skipped


def test_unreachable_runner_is_skipped_for_every_language():
    out = remote(f"http://127.0.0.1:{free_port()}").run_files(
        {"solution.py": PY_PASS, "demo.c": C_MAIN}
    )
    assert out["ok"] is False
    assert statuses(out) == ["skipped", "skipped"]
    assert out["sandbox"]["available"] is False


def test_slow_runner_is_skipped():
    def respond(handler):
        time.sleep(2)
        return 200, {"protocol": PROTOCOL, "results": []}

    server, url = fake_runner(respond)
    try:
        out = remote(url, timeout=0.5).run_files({"solution.py": PY_PASS})
    finally:
        server.shutdown()
    assert statuses(out) == ["skipped"]
    assert "did not answer" in out["output"]


GOOD = {"language": "python", "status": "passed", "files": ["s.py"], "passed": 1, "failed": 0}


@pytest.mark.parametrize(
    ("code", "body", "why"),
    [
        (500, {"error": "boom"}, "HTTP 500: boom"),
        (503, {"protocol": PROTOCOL, "error": "the runner is busy"}, "busy"),
        (200, b"<html>not json</html>", "not JSON"),
        (200, {"protocol": 99, "results": [GOOD]}, "protocol"),
        (200, {"protocol": PROTOCOL}, "no results"),
        (200, {"protocol": PROTOCOL, "results": [{**GOOD, "status": "PASSED"}]}, "malformed"),
        (200, {"protocol": PROTOCOL, "results": [{**GOOD, "passed": -1}]}, "malformed"),
        (200, {"protocol": PROTOCOL, "results": [{**GOOD, "passed": True}]}, "malformed"),
        (200, {"protocol": PROTOCOL, "results": ["passed"]}, "malformed"),
    ],
)
def test_bad_answers_are_skipped(code, body, why):
    server, url = fake_runner(lambda handler: (code, body))
    try:
        out = remote(url).run_files({"solution.py": PY_PASS})
    finally:
        server.shutdown()
    assert out["ok"] is False
    assert statuses(out) == ["skipped"]
    assert why in out["output"]


def test_a_language_the_runner_leaves_out_is_skipped():
    body = {"protocol": PROTOCOL, "ok": True, "results": [GOOD]}
    server, url = fake_runner(lambda handler: (200, body))
    try:
        out = remote(url).run_files({"solution.py": PY_PASS, "demo.c": C_MAIN})
    finally:
        server.shutdown()
    # The runner's own "ok" is ignored; the server computes it.
    assert out["ok"] is False
    by_language = {r["language"]: r["status"] for r in out["results"]}
    assert by_language == {"python": "passed", "c": "skipped"}
    assert "did not report" in out["output"]


def test_huge_answers_are_refused(monkeypatch):
    import exams_generator.remote as remote_module

    monkeypatch.setattr(remote_module, "MAX_RESPONSE_BYTES", 100)
    body = {"protocol": PROTOCOL, "results": [{**GOOD, "output": "x" * 1000}]}
    server, url = fake_runner(lambda handler: (200, body))
    try:
        out = remote(url).run_files({"solution.py": PY_PASS})
    finally:
        server.shutdown()
    assert statuses(out) == ["skipped"] and "too large" in out["output"]


def test_long_output_from_the_runner_is_capped():
    body = {"protocol": PROTOCOL, "results": [{**GOOD, "output": "x" * 100_000}]}
    server, url = fake_runner(lambda handler: (200, body))
    try:
        out = remote(url).run_files({"solution.py": PY_PASS})
    finally:
        server.shutdown()
    assert len(out["output"]) < 20_000


# ----------------------------------------------------------- the runner's API


def test_parse_request():
    files = parse_request(json.dumps({"protocol": PROTOCOL, "files": {"a.py": "x"}}).encode())
    assert files == {"a.py": "x"}
    bad = [
        b"nope",
        b"[]",
        json.dumps({"protocol": 2, "files": {"a.py": ""}}).encode(),
        json.dumps({"protocol": PROTOCOL, "files": {}}).encode(),
        json.dumps({"protocol": PROTOCOL, "files": {"../a.py": ""}}).encode(),
        json.dumps({"protocol": PROTOCOL, "files": {"/etc/a.py": ""}}).encode(),
        json.dumps({"protocol": PROTOCOL, "files": {"a.py": 1}}).encode(),
        json.dumps({"protocol": PROTOCOL, "files": {f"f{i}.py": "" for i in range(65)}}).encode(),
    ]
    for body in bad:
        with pytest.raises(BadRequest):
            parse_request(body)


def test_runner_http_errors(tmp_path):
    app = create_app(DemoRunner(REGISTRY, process_sandbox(tmp_path)))
    with TestClient(app) as http:
        assert http.get("/healthz").text == "ok"
        assert http.post("/v1/run", content=b"{}").status_code == 400
        big = b"x" * (MAX_REQUEST_BYTES + 1)
        assert http.post("/v1/run", content=big).status_code == 413
        assert http.get("/v1/run").status_code == 405
        unknown = http.post("/v1/run", json={"protocol": PROTOCOL, "files": {"notes.txt": "hi"}})
        assert unknown.status_code == 200 and unknown.json()["results"] == []


def test_busy_runner_answers_503(runner_url):
    slow = '"""\n>>> import time; time.sleep(3)\n"""\n'
    first = threading.Thread(target=lambda: remote(runner_url).run_files({"slow.py": slow}))
    first.start()
    time.sleep(1)
    out = remote(runner_url).run_files({"solution.py": PY_PASS})
    first.join()
    assert statuses(out) == ["skipped"]
    assert "busy" in out["output"]


# ------------------------------------------------------------ startup checks


def test_runner_refuses_to_start_next_to_other_processes():
    # This test runs among other processes, as the runner would outside a container.
    assert pid_namespace_problem() is not None


def test_runner_starts_alone_in_its_namespace(tmp_path):
    for pid in (1, os.getpid(), os.getppid()):
        (tmp_path / str(pid)).mkdir(exist_ok=True)
    (tmp_path / "self").mkdir()
    assert pid_namespace_problem(str(tmp_path)) is None
    (tmp_path / "4242424").mkdir()
    assert "other processes" in (pid_namespace_problem(str(tmp_path)) or "")


def test_runner_refuses_the_servers_token():
    assert forbidden_env_problem({"EXAMS_BEARER_TOKEN": "x"})
    assert forbidden_env_problem({"EXAMS_RUN_TIMEOUT": "30"}) is None


def test_runner_refuses_a_container_without_a_pids_limit(tmp_path):
    (tmp_path / "pids.max").write_text("max\n")
    (tmp_path / "memory.max").write_text("2147483648\n")
    limits = cgroup_limits(str(tmp_path))
    assert limits == {"pids": "max", "memory": "2147483648"}
    assert "pids_limit" in (pids_limit_problem(limits) or "")
    assert pids_limit_problem(limits, outside=True) is None  # gVisor: applied outside
    (tmp_path / "pids.max").write_text("256\n")
    assert pids_limit_problem(cgroup_limits(str(tmp_path))) is None
