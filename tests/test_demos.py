"""The optional demo runner: what it runs, what it reports, and what it cannot reach."""

import ast
import os
import socket
import time
from pathlib import Path

import pytest

import exams_generator.checkers as checkers_package
from exams_generator.checkers import CheckerRegistry
from exams_generator.demos import DemoRunner, extract_haskell_demos
from exams_generator.sandbox import Sandbox
from tests.conftest import EXAMPLES, make_sandbox, requires, requires_sandbox

PY_PASS = '"""\n>>> add(2, 3)\n5\n"""\n\n\ndef add(a, b):\n    return a + b\n'
PY_FAIL = '"""\n>>> add(2, 3)\n6\n"""\n\n\ndef add(a, b):\n    return a + b\n'
C_MAIN = "int main(void) {\n    return 0;\n}\n"


@pytest.fixture
def runner(tmp_path):
    return DemoRunner(CheckerRegistry(load_plugins=False), make_sandbox(tmp_path))


def run_python(runner, code):
    return runner.run_files({"solution.py": code})


def probe(tmp_path, body, timeout=20.0, memory_mb=4096):
    """Run a Python program in the sandbox; the demo passes if the program exits 0."""
    sandbox = make_sandbox(tmp_path, timeout=timeout, memory_mb=memory_mb)
    return sandbox.run({"probe.py": body}, "python3 -B probe.py")


# ---------------------------------------------------------- what counts as a pass


@requires_sandbox
def test_python_doctests_pass(runner):
    out = run_python(runner, PY_PASS)
    assert out["ok"] is True
    assert out["results"][0]["status"] == "passed"
    assert out["results"][0]["passed"] == 1


@requires_sandbox
def test_python_doctests_fail(runner):
    out = run_python(runner, PY_FAIL)
    assert out["ok"] is False
    assert out["results"][0]["status"] == "failed"
    assert out["results"][0]["failed"] == 1
    assert "exams-doctest" not in out["output"]


@requires_sandbox
def test_python_import_error_fails(runner):
    out = run_python(runner, "import not_a_module\n")
    assert out["results"][0]["status"] == "failed"
    assert "not_a_module" in out["output"]


@requires_sandbox
def test_no_doctests_is_skipped_not_passed(runner):
    out = run_python(runner, "x = 1\n")
    assert out["ok"] is False
    assert out["results"][0]["status"] == "skipped"
    assert out["results"][0]["skipped"] is True


@requires_sandbox
@requires("haskell")
def test_haskell_demo_result(tmp_path, runner):
    code = "double :: Int -> Int\ndouble x = x * 2\n\n{-\n>>> double 2\n4\n>>> double 3\n7\n-}\n"
    out = runner.run_files({"Exam.hs": code})
    result = out["results"][0]
    assert (result["status"], result["passed"], result["failed"]) == ("failed", 1, 1)
    assert "double 3" in out["output"] and "expected" in out["output"]
    assert "exams-demo" not in out["output"]


@requires_sandbox
@requires("haskell")
def test_haskell_runtime_error_fails_a_demo_with_no_expected_output(runner):
    code = 'boom :: Int\nboom = error "nope"\n\n{-\n>>> boom\n-}\n'
    out = runner.run_files({"Exam.hs": code})
    assert out["results"][0]["status"] == "failed"
    assert "nope" in out["output"]


@requires_sandbox
@requires("haskell")
def test_haskell_type_error_is_a_failure(runner):
    out = runner.run_files({"Exam.hs": 'x :: Int\nx = "no"\n\n{-\n>>> x\n1\n-}\n'})
    assert out["ok"] is False
    assert out["results"][0]["status"] == "failed"


def test_extract_haskell_demos():
    src = "{-\n>>> f 1\n2\n3\n\n>>> g\n-}\n-- >>> h\n-- 9\nf = 1\n"
    demos = extract_haskell_demos(src)
    assert [(d.expression, d.expected) for d in demos] == [
        ("f 1", ["2", "3"]),
        ("g", []),
        ("h", ["9"]),
    ]


@requires_sandbox
@requires("c")
def test_c_main_runs(runner):
    out = runner.run_files({"demo.c": C_MAIN})
    assert out["ok"] is True
    assert out["results"][0]["passed"] == 1


@requires_sandbox
@requires("c")
def test_c_nonzero_exit_fails(runner):
    out = runner.run_files({"demo.c": "int main(void) { return 3; }\n"})
    assert out["ok"] is False
    assert "exit status 3" in out["output"]


@requires_sandbox
@requires("c")
def test_c_compile_error_is_a_build_failure(runner):
    out = runner.run_files({"demo.c": "int main(void) { return x; }\n"})
    assert out["results"][0]["status"] == "failed"
    assert "build failed" in out["output"]


@requires_sandbox
@requires("c")
def test_c_without_main_is_skipped(runner):
    out = runner.run_files({"lib.c": "int f(void) { return 1; }\n"})
    assert out["ok"] is False
    assert out["results"][0]["status"] == "skipped"


@requires_sandbox
@requires("cpp")
def test_cpp_main_runs(runner):
    out = runner.run_files({"demo.cpp": "#include <vector>\nint main() { return 0; }\n"})
    assert out["ok"] is True


@requires_sandbox
def test_example_python_exam_passes(runner):
    directory = EXAMPLES / "gradebook-python-en" / "solution"
    files = {p.name: p.read_text(encoding="utf-8") for p in directory.iterdir()}
    assert runner.run_files(files)["ok"] is True


@requires_sandbox
@requires("haskell")
def test_example_haskell_exam_passes(runner):
    directory = EXAMPLES / "toll-roads-haskell-es" / "solution"
    files = {p.name: p.read_text(encoding="utf-8") for p in directory.iterdir()}
    out = runner.run_files(files)
    assert out["ok"] is True, out["output"]
    assert out["results"][0]["passed"] >= 1


# ----------------------------------------------- nothing available means skipped


def test_missing_sandbox_is_skipped_not_passed(tmp_path):
    sandbox = Sandbox(bwrap=str(tmp_path / "no-bwrap"))
    runner = DemoRunner(CheckerRegistry(load_plugins=False), sandbox)
    out = run_python(runner, PY_PASS)
    assert out["ok"] is False
    assert out["results"][0]["status"] == "skipped"
    assert "sandbox not available" in out["output"]
    assert out["sandbox"]["available"] is False


def test_broken_sandbox_is_skipped_not_passed(tmp_path):
    fake = tmp_path / "bwrap"
    fake.write_text("#!/bin/sh\necho 'bwrap: No permissions' >&2\nexit 1\n")
    fake.chmod(0o755)
    runner = DemoRunner(CheckerRegistry(load_plugins=False), Sandbox(bwrap=str(fake)))
    out = run_python(runner, PY_PASS)
    assert out["ok"] is False
    assert out["results"][0]["status"] == "skipped"
    assert "No permissions" in out["output"]


def test_sandbox_dying_during_a_run_is_skipped(tmp_path, monkeypatch):
    fake = tmp_path / "bwrap"
    fake.write_text("#!/bin/sh\nexit 1\n")
    fake.chmod(0o755)
    sandbox = Sandbox(bwrap=str(fake))
    runner = DemoRunner(CheckerRegistry(load_plugins=False), sandbox)
    # The probe is passed; the real run still has to be reported as not having run.
    status = type("S", (), {"available": True, "as_dict": lambda self: {}})()
    monkeypatch.setattr(sandbox, "status", lambda: status)
    result = run_python(runner, PY_PASS)
    assert result["ok"] is False
    assert result["results"][0]["status"] == "skipped"


@requires_sandbox
def test_missing_toolchain_is_skipped_not_passed(tmp_path, runner, monkeypatch):
    monkeypatch.setenv("EXAMS_CC", str(tmp_path / "no-such-cc"))
    out = runner.run_files({"demo.c": C_MAIN})
    assert out["ok"] is False
    assert out["results"][0]["status"] == "skipped"
    assert "toolchain" in out["output"]


@requires_sandbox
def test_toolchain_outside_the_sandbox_is_skipped(tmp_path, runner, monkeypatch):
    compiler = tmp_path / "gcc"
    compiler.write_text("#!/bin/sh\nexit 0\n")
    compiler.chmod(0o755)
    monkeypatch.setenv("EXAMS_CC", str(compiler))
    out = runner.run_files({"demo.c": C_MAIN})
    assert out["results"][0]["status"] == "skipped"
    assert "EXAMS_RUN_RO_BINDS" in out["output"]


def test_one_skipped_language_makes_the_whole_run_not_ok(tmp_path, monkeypatch):
    runner = DemoRunner(CheckerRegistry(load_plugins=False), Sandbox(bwrap=str(tmp_path / "none")))
    assert run_python(runner, PY_PASS)["ok"] is False


def test_no_files_is_not_ok(runner):
    assert runner.run_files({})["ok"] is False


def test_unknown_files_are_not_ok(runner):
    out = runner.run_files({"notes.txt": "hello"})
    assert out["ok"] is False
    assert "No language owns" in out["output"]


# ----------------------------------------------------------- the sandbox's walls


@requires_sandbox
def test_cannot_read_host_files(tmp_path):
    secret = Path.home() / ".exams-generator-test-secret"
    secret.write_text("top secret")
    try:
        run = probe(tmp_path, f"import os\nos._exit(0 if os.path.exists({str(secret)!r}) else 7)\n")
        assert run.started and run.exit_code == 7
    finally:
        secret.unlink()


@requires_sandbox
def test_cannot_see_exams_dir_or_the_tmp_it_lives_in(tmp_path):
    (tmp_path / "exams").mkdir()
    (tmp_path / "exams" / "real.md").write_text("real exam")
    code = f"import os\nos._exit(0 if os.path.exists({str(tmp_path)!r}) else 7)\n"
    assert probe(tmp_path, code).exit_code == 7


@requires_sandbox
def test_no_network(tmp_path):
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        code = (
            "import socket, os\n"
            "s = socket.socket()\n"
            "s.settimeout(3)\n"
            "try:\n"
            f"    s.connect(('127.0.0.1', {port}))\n"
            "except OSError:\n"
            "    os._exit(7)\n"
            "os._exit(0)\n"
        )
        assert probe(tmp_path, code).exit_code == 7


@requires_sandbox
def test_no_host_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("EXAMS_BEARER_TOKEN", "hunter2")
    code = "import os\nos._exit(7 if 'EXAMS_BEARER_TOKEN' not in os.environ else 0)\n"
    assert probe(tmp_path, code).exit_code == 7


@requires_sandbox
def test_cannot_see_host_processes(tmp_path):
    code = (
        "import os\n"
        "pids = [p for p in os.listdir('/proc') if p.isdigit()]\n"
        f"os._exit(7 if {os.getpid()} not in map(int, pids) and len(pids) < 10 else 0)\n"
    )
    assert probe(tmp_path, code).exit_code == 7


@requires_sandbox
def test_system_directories_are_read_only(tmp_path):
    code = (
        "import os\n"
        "try:\n"
        "    open('/usr/exams-test', 'w')\n"
        "except OSError:\n"
        "    os._exit(7)\n"
        "os._exit(0)\n"
    )
    assert probe(tmp_path, code).exit_code == 7


@requires_sandbox
def test_timeout_kills_the_whole_process_tree(tmp_path):
    marker = f"exams-sandbox-test-{os.getpid()}-{time.time_ns()}"
    code = (
        "import subprocess, time\n"
        f"subprocess.Popen(['/bin/sh', '-c', 'sleep 300 # {marker}'])\n"
        "time.sleep(300)\n"
    )
    started = time.monotonic()
    run = probe(tmp_path, code, timeout=1.0)
    assert run.timed_out
    assert time.monotonic() - started < 10
    # No orphan survives: nothing on the host matches the marker.
    time.sleep(0.2)
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            try:
                assert marker not in (entry / "cmdline").read_bytes().decode(errors="ignore")
            except OSError:
                pass


@requires_sandbox
def test_timeout_reported(tmp_path):
    runner = DemoRunner(CheckerRegistry(load_plugins=False), make_sandbox(tmp_path, timeout=1.0))
    code = '"""\n>>> 1\n1\n"""\nimport time\ntime.sleep(60)\n'
    out = run_python(runner, code)
    assert out["ok"] is False
    assert out["results"][0]["status"] == "timeout"


@requires_sandbox
def test_memory_limit(tmp_path):
    code = (
        "import os\n"
        "try:\n"
        "    x = bytearray(8 * 1024 * 1024 * 1024)\n"
        "except MemoryError:\n"
        "    os._exit(7)\n"
        "os._exit(0)\n"
    )
    assert probe(tmp_path, code, memory_mb=256).exit_code == 7


@requires_sandbox
def test_process_limit_stops_fork_bombs(tmp_path):
    code = (
        "import os, time\n"
        "children = 0\n"
        "try:\n"
        "    for _ in range(2000):\n"
        "        if os.fork() == 0:\n"
        "            time.sleep(30)\n"
        "            os._exit(0)\n"
        "        children += 1\n"
        "except OSError:\n"
        "    os._exit(7)\n"
        "os._exit(0)\n"
    )
    assert probe(tmp_path, code).exit_code == 7


@requires_sandbox
def test_big_files_are_cut_off(tmp_path):
    code = (
        "import os\n"
        "try:\n"
        "    with open('big', 'wb') as f:\n"
        "        for _ in range(400):\n"
        "            f.write(b'x' * 1024 * 1024)\n"
        "except OSError:\n"
        "    os._exit(7)\n"
        "os._exit(0)\n"
    )
    run = probe(tmp_path, code)
    # SIGXFSZ (128 + 25) or, with the signal ignored, EFBIG from write().
    assert run.exit_code in {7, 153}


@requires_sandbox
def test_output_flood_is_capped(tmp_path):
    code = "import sys\nfor _ in range(200):\n    sys.stdout.write('y' * (1 << 20))\n"
    run = probe(tmp_path, code)
    assert len(run.stdout) <= 1024 * 1024
    assert run.truncated or run.exit_code != 0


@requires_sandbox
def test_solution_files_cannot_reach_the_input_dir_for_writing(tmp_path):
    code = (
        "import os\n"
        "try:\n"
        "    open('/input/files/x', 'w')\n"
        "except OSError:\n"
        "    os._exit(7)\n"
        "os._exit(0)\n"
    )
    assert probe(tmp_path, code).exit_code == 7


# ----------------------------------------------------- refusing bad configuration


@pytest.mark.parametrize("bind", ["/", "home"])
def test_binds_exposing_home_are_refused(tmp_path, bind):
    path = Path.home() if bind == "home" else Path(bind)
    fake = tmp_path / "bwrap"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o755)
    status = Sandbox(bwrap=str(fake), ro_binds=[path]).status()
    assert status.available is False
    assert "home" in status.hint


def test_binds_exposing_exams_are_refused(tmp_path):
    fake = tmp_path / "bwrap"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o755)
    exams = tmp_path / "exams"
    exams.mkdir()
    status = Sandbox(bwrap=str(fake), ro_binds=[tmp_path], protected=[exams]).status()
    assert status.available is False
    assert str(exams) in status.hint


# --------------------------------------------------------- checkers do not execute


def test_checkers_do_not_use_the_runner():
    package_dir = Path(checkers_package.__file__).parent
    forbidden = {"exams_generator.demos", "exams_generator.sandbox", "demos", "sandbox"}
    for module in package_dir.glob("*.py"):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[-1] not in forbidden, module
                assert not {alias.name for alias in node.names} & forbidden, module
            elif isinstance(node, ast.Import):
                assert not {alias.name for alias in node.names} & forbidden, module
