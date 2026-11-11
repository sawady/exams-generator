"""End to end against compose.yaml: the server over HTTP, the runner in its own container.

Skipped unless EXAMS_E2E_URL (the server's /mcp URL) and EXAMS_E2E_TOKEN are set. CI starts
`docker compose --profile demos up`, runs this with EXAMS_E2E_RUNNER=up, stops the runner
and runs it again with EXAMS_E2E_RUNNER=down. To run it locally:

    printf 'EXAMS_BEARER_TOKEN=%s\\nEXAMS_RUN_DEMOS=true\\n' "$TOKEN" > .env
    docker compose --profile demos up -d --build --wait
    EXAMS_E2E_URL=http://127.0.0.1:8765/mcp EXAMS_E2E_TOKEN="$TOKEN" pytest tests/test_runner_e2e.py
"""

from __future__ import annotations

import os
import time

import anyio
import pytest
from mcp import Client
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

URL = os.environ.get("EXAMS_E2E_URL", "")
TOKEN = os.environ.get("EXAMS_E2E_TOKEN", "")
RUNNER = os.environ.get("EXAMS_E2E_RUNNER", "up")
#: Under gVisor, reaching the process limit takes the runner's sandbox down (it restarts).
GVISOR = os.environ.get("EXAMS_E2E_GVISOR", "") == "1"

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.skipif(
        not (URL and TOKEN), reason="end-to-end: set EXAMS_E2E_URL and EXAMS_E2E_TOKEN"
    ),
]
runner_up = pytest.mark.skipif(RUNNER != "up", reason="the runner is stopped in this pass")
runner_down = pytest.mark.skipif(RUNNER != "down", reason="the runner is up in this pass")

# Written into a saved exam on the server; the runner must not find it anywhere.
EXAM_MARKER = "e2e-exam-marker-" + "4f1c9a"


def client() -> Client:
    http = create_mcp_http_client(headers={"Authorization": f"Bearer {TOKEN}"})
    return Client(streamable_http_client(URL, http_client=http))


async def runner_available() -> bool:
    async with client() as c:
        info = (await c.call_tool("list_languages", {})).structured_content
    return bool(info["demos"].get("available"))


async def wait_for_runner(seconds: float = 180) -> None:
    deadline = time.monotonic() + seconds
    while not await runner_available():
        assert time.monotonic() < deadline, "the runner did not come back"
        await anyio.sleep(3)


async def run_demos(**files: str) -> dict:
    async with client() as c:
        result = await c.call_tool("run_demos", {"extra_files": files})
        assert result.structured_content is not None, result.content
        return result.structured_content


def doctest_module(*lines: str) -> str:
    """A Python file whose doctests are ``lines`` (each ``>>>`` line and its expected output)."""
    return '"""\n' + "\n".join(lines) + '\n"""\n'


def pieces(text: str) -> str:
    """``text`` as a Python expression that does not contain it literally."""
    middle = len(text) // 2
    return f"{text[:middle]!r} + {text[middle:]!r}"


@runner_up
async def test_list_languages_shows_the_runner():
    async with client() as c:
        info = (await c.call_tool("list_languages", {})).structured_content
    demos = info["demos"]
    assert demos["enabled"] and demos["mode"] == "remote" and demos["available"], demos
    available = {row["language"] for row in demos["languages"] if row["available"]}
    assert {"python", "haskell", "c", "cpp"} <= available


@runner_up
async def test_every_toolchain_runs_in_the_runner():
    out = await run_demos(
        **{
            "solution.py": doctest_module(">>> 2 + 3", "5"),
            "Exam.hs": "double :: Int -> Int\ndouble x = x * 2\n\n-- >>> double 21\n-- 42\n",
            "demo.c": "int main(void) { return 0; }\n",
            "demo.cpp": "#include <vector>\nint main() { std::vector<int> v{0}; return v[0]; }\n",
        }
    )
    assert out["ok"] is True, out["output"]
    assert sorted(r["language"] for r in out["results"]) == ["c", "cpp", "haskell", "python"]


@runner_up
async def test_failures_are_failures():
    out = await run_demos(**{"solution.py": doctest_module(">>> 2 + 3", "6")})
    assert out["ok"] is False and out["results"][0]["status"] == "failed"


@runner_up
async def test_the_runner_cannot_see_the_server():
    # Save an exam on the server first, so there is something to look for.
    async with client() as c:
        saved = await c.call_tool(
            "save_exam",
            {
                "name": "e2e-private",
                "title": "Private",
                "statement": f"# Private\n\n{EXAM_MARKER}\n",
                "solution": {"solution.py": "x: int = 1\n"},
                "verify": False,
            },
        )
        assert saved.structured_content and saved.structured_content.get("ok"), saved
    probe = doctest_module(
        ">>> import os, socket",
        ">>> TOKEN = " + pieces(TOKEN),
        ">>> MARKER = " + pieces(EXAM_MARKER),
        # No variable of the server, in this process or any other it can read.
        ">>> sorted(k for k in os.environ if k.startswith('EXAMS_'))",
        "[]",
        ">>> def environs():",
        "...     for pid in filter(str.isdigit, os.listdir('/proc')):",
        "...         try:",
        "...             yield open(f'/proc/{pid}/environ', 'rb').read()",
        "...         except OSError:",
        "...             pass",
        ">>> any(TOKEN.encode() in e for e in environs())",
        "False",
        # None of the server's files: no exams, no data, no home.
        ">>> [p for p in ('/exams', '/data', '/home/exams', '/app') if os.path.exists(p)]",
        "[]",
        ">>> def files_with(text):",
        "...     found = []",
        "...     for top in ('/etc', '/home', '/root', '/opt', '/srv', '/mnt', '/var', '/tmp'):",
        "...         for root, dirs, names in os.walk(top):",
        "...             for name in names:",
        "...                 path = os.path.join(root, name)",
        "...                 try:",
        "...                     if text.encode() in open(path, 'rb').read(1 << 20):",
        "...                         found.append(path)",
        "...                 except OSError:",
        "...                     pass",
        "...     return found",
        ">>> files_with(MARKER) + files_with(TOKEN)",
        "[]",
        # Not root, and the system is read-only.
        ">>> os.getuid() != 0 and not os.access('/usr/bin', os.W_OK)",
        "True",
        # No way out: no DNS and no outbound connection.
        ">>> def reaches(host, port):",
        "...     try:",
        "...         socket.create_connection((host, port), timeout=3).close()",
        "...         return True",
        "...     except OSError:",
        "...         return False",
        ">>> reaches('1.1.1.1', 443) or reaches('8.8.8.8', 53) or reaches('example.org', 80)",
        "False",
    )
    out = await run_demos(**{"probe.py": probe})
    assert out["ok"] is True, out["output"]


@runner_up
async def test_nothing_survives_a_run():
    # A run leaves a detached process behind; the next run must not see it.
    leave = doctest_module(
        ">>> import subprocess",
        ">>> _ = subprocess.Popen(['sh', '-c', 'sleep 600 &'], start_new_session=True)",
        ">>> open('/tmp/left-behind', 'w').write('x')",
        "1",
    )
    out = await run_demos(**{"leave.py": leave})
    assert out["ok"] is True, out["output"]
    check = doctest_module(
        ">>> import os",
        ">>> mine = {os.getpid(), os.getppid()}",
        ">>> cmdlines = []",
        ">>> for pid in filter(str.isdigit, os.listdir('/proc')):",
        "...     try:",
        "...         cmdlines.append(open(f'/proc/{pid}/cmdline', 'rb').read())",
        "...     except OSError:",
        "...         pass",
        ">>> [c for c in cmdlines if c.startswith(b'sleep')]",
        "[]",
        ">>> os.path.exists('/tmp/left-behind')",
        "False",
    )
    out = await run_demos(**{"check.py": check})
    assert out["ok"] is True, out["output"]


@runner_up
async def test_a_fork_bomb_stays_inside():
    bomb = doctest_module(
        ">>> import os",
        ">>> for _ in range(100000):",
        "...     try:",
        "...         _ = os.fork()",
        "...     except OSError:",
        "...         pass",
    )
    out = await run_demos(**{"bomb.py": bomb})
    assert out["ok"] is False
    # With runc the run times out and the runner carries on. Under gVisor the bomb takes
    # the sandbox down, Docker restarts it, and the server reports the run as skipped.
    expected = {"timeout", "failed", "skipped"} if GVISOR else {"timeout", "failed"}
    assert out["results"][0]["status"] in expected, out["output"]
    await wait_for_runner()
    # The runner is there, and clean, for the next run.
    out = await run_demos(**{"solution.py": doctest_module(">>> 2 + 3", "5")})
    assert out["ok"] is True, out["output"]


@runner_up
@pytest.mark.skipif(GVISOR, reason="gVisor: the limit is outside; the fork bomb test covers it")
async def test_the_process_limit_holds():
    probe = doctest_module(
        ">>> import os, signal, time",
        ">>> children = []",
        ">>> for _ in range(400):",
        "...     try:",
        "...         pid = os.fork()",
        "...     except OSError:",
        "...         break",
        "...     if pid == 0:",
        "...         time.sleep(60)",
        "...         os._exit(0)",
        "...     children.append(pid)",
        ">>> for pid in children:",
        "...     os.kill(pid, signal.SIGKILL)",
        ">>> 0 < len(children) < 300",
        "True",
    )
    out = await run_demos(**{"forks.py": probe})
    assert out["ok"] is True, out["output"]


@runner_down
async def test_a_stopped_runner_means_skipped():
    out = await run_demos(**{"solution.py": doctest_module(">>> 2 + 3", "5")})
    assert out["ok"] is False
    assert out["results"][0]["status"] == "skipped"
    assert "did not answer" in out["output"]
    async with client() as c:
        info = (await c.call_tool("list_languages", {})).structured_content
    assert info["demos"]["available"] is False
