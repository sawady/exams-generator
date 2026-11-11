"""The demo runner: a separate service that only executes ``run_demos`` runs.

Start it with ``exams-generator-runner``, inside its own container (see
``Dockerfile.runner`` and ``compose.yaml``). The server sends it the files of
a run (protocol in ``remote.py``) and gets one result per language back.

The container is the sandbox: no network but an internal one to the server,
read-only root, tmpfs for ``/input``, ``/work`` and ``/tmp``, a non-root user,
no capabilities, cgroup limits on CPU, memory and processes, and optionally
gVisor (``runsc``) as its runtime. Inside it each run is a plain child
process (:class:`~exams_generator.sandbox.ProcessSandbox`): empty environment,
``prlimit`` limits, a timeout, fresh directories, and after it every leftover
process is killed. Runs are serialized, so one run never sees another.

The number of processes is limited by the container's pids cgroup, not by
``RLIMIT_NPROC``: that one counts every process of the same UID on the host,
other containers included, so it is not a limit of this container at all. The
runner refuses to start without a pids limit it can see. Under gVisor the
container's cgroups are applied outside the sandbox and are not visible inside
(and gVisor does not enforce ``RLIMIT_NPROC``), so ``compose.gvisor.yaml`` sets
``EXAMS_RUNNER_PIDS_LIMIT_OUTSIDE=true`` to vouch for it. There, a run that
reaches the limit takes the whole sandbox down; Docker restarts the runner and
the server reports that run as skipped.

Because that sweep kills every process of the container, the runner refuses to
start unless it is alone in its PID namespace, which is also a sign that it
really is in a container. It refuses as well if it was given the server's
token, which it never needs.

=====================  ==========================================  ===========
Variable               Meaning                                     Default
=====================  ==========================================  ===========
EXAMS_RUNNER_HOST      Bind address                                ``127.0.0.1``
EXAMS_RUNNER_PORT      Port                                        ``8766``
EXAMS_RUN_TIMEOUT      Seconds per language, build included        ``30``
EXAMS_RUN_MEMORY_MB    Address-space limit of each process         ``4096``
EXAMS_RUNNER_QUEUE     Seconds a request waits for a busy runner   ``120``
EXAMS_RUNNER_PIDS_     ``true``: the pids limit is applied where   ``false``
LIMIT_OUTSIDE          the runner cannot see it (gVisor)
=====================  ==========================================  ===========
"""

from __future__ import annotations

import ctypes
import json
import os
import threading
from collections.abc import Mapping
from typing import Any

from . import __version__
from .checkers import CheckerRegistry
from .demos import DemoRunner, languages_or_error
from .remote import PROTOCOL
from .sandbox import ProcessSandbox
from .storage import StorageError, validate_filename

MAX_REQUEST_BYTES = 4 * 1024 * 1024
MAX_FILES = 64
INPUT_ROOT, WORK_ROOT, TMP_ROOT = "/input", "/work", "/tmp"
#: Variables the runner must never hold: they belong to the server.
FORBIDDEN_ENV = ("EXAMS_BEARER_TOKEN",)


class BadRequest(Exception):
    pass


def parse_request(body: bytes) -> dict[str, str]:
    """The files of a run request; :class:`BadRequest` if anything is off."""
    try:
        payload = json.loads(body)
    except ValueError as err:
        raise BadRequest("the body is not JSON") from err
    if not isinstance(payload, dict):
        raise BadRequest("the body is not an object")
    if payload.get("protocol") != PROTOCOL:
        raise BadRequest(f"unsupported protocol {payload.get('protocol')!r}; this is {PROTOCOL}")
    files = payload.get("files")
    if not isinstance(files, dict) or not files:
        raise BadRequest("files must be a non-empty object")
    if len(files) > MAX_FILES:
        raise BadRequest(f"at most {MAX_FILES} files")
    for name, content in files.items():
        try:
            validate_filename(name)
        except StorageError as err:
            raise BadRequest(str(err)) from err
        if not isinstance(content, str):
            raise BadRequest(f"the content of {name} is not a string")
    return files


def create_app(runner: DemoRunner, *, queue_timeout: float = 120.0) -> Any:
    from starlette.applications import Starlette
    from starlette.concurrency import run_in_threadpool
    from starlette.requests import Request
    from starlette.responses import JSONResponse, PlainTextResponse
    from starlette.routing import Route

    lock = threading.Lock()
    # Once, now: a toolchain probe during a run would be killed by the sweep.
    languages = runner.registry.describe()

    def error(status: int, message: str) -> JSONResponse:
        return JSONResponse({"protocol": PROTOCOL, "error": message}, status_code=status)

    def run_locked(files: Mapping[str, str]) -> dict[str, Any] | None:
        if not lock.acquire(timeout=queue_timeout):
            return None
        try:
            languages, problem = languages_or_error(runner.registry, files)
            if problem is not None:
                status = runner.sandbox.status()
                return {"results": [], "sandbox": status.as_dict(), "note": problem["output"]}
            results, status = runner.results(files, languages)
            return {"results": [r.to_wire() for r in results], "sandbox": status.as_dict()}
        finally:
            lock.release()

    async def healthz(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    async def status(request: Request) -> JSONResponse:
        sandbox = await run_in_threadpool(runner.sandbox.status)
        return JSONResponse(
            {
                "protocol": PROTOCOL,
                "version": __version__,
                "sandbox": sandbox.as_dict(),
                "languages": languages,
            }
        )

    async def run(request: Request) -> JSONResponse:
        body = bytearray()
        async for chunk in request.stream():
            body += chunk
            if len(body) > MAX_REQUEST_BYTES:
                return error(413, f"the request is larger than {MAX_REQUEST_BYTES} bytes")
        try:
            files = parse_request(bytes(body))
        except BadRequest as err:
            return error(400, str(err))
        answer = await run_in_threadpool(run_locked, files)
        if answer is None:
            return error(503, "the runner is busy; try again later")
        return JSONResponse({"protocol": PROTOCOL, **answer})

    return Starlette(
        routes=[
            Route("/healthz", healthz),
            Route("/v1/status", status),
            Route("/v1/run", run, methods=["POST"]),
        ]
    )


# ------------------------------------------------------------------ startup


def pid_namespace_problem(proc: str = "/proc") -> str | None:
    """Why this process is not alone in its PID namespace, or None.

    Allowed: PID 1 (an init such as ``docker run --init``), this process and its
    parent. Anything else would be killed by the sweep after each run.
    """
    allowed = {1, os.getpid(), os.getppid()}
    try:
        others = sorted(int(e) for e in os.listdir(proc) if e.isdigit() and int(e) not in allowed)
    except OSError as err:
        return f"cannot list processes in {proc}: {err}"
    if others:
        return (
            f"{len(others)} other processes are visible (PID {others[0]}, ...). The runner "
            "kills every process of its container after each run, so it only starts alone "
            "in its own container. See Dockerfile.runner and compose.yaml."
        )
    return None


def cgroup_limits(root: str = "/sys/fs/cgroup") -> dict[str, str]:
    """The container's cgroup limits that can be read (cgroup v2, or v1 for pids)."""
    files = {
        "pids": ("pids.max", "pids/pids.max"),
        "memory": ("memory.max", "memory/memory.limit_in_bytes"),
        "cpu": ("cpu.max", "cpu/cpu.cfs_quota_us"),
    }
    limits = {}
    for name, candidates in files.items():
        for candidate in candidates:
            try:
                with open(os.path.join(root, candidate), encoding="ascii") as handle:
                    limits[name] = handle.read().strip()
                break
            except (OSError, UnicodeDecodeError):
                continue
    return limits


def pids_limit_problem(limits: Mapping[str, str], outside: bool = False) -> str | None:
    if limits.get("pids") == "max" and not outside:
        return (
            "the container has no process limit (pids.max is max); set pids_limit, "
            "as compose.yaml does, so that a fork bomb stays inside it (under gVisor, "
            "where it is not visible, also set EXAMS_RUNNER_PIDS_LIMIT_OUTSIDE=true, "
            "as compose.gvisor.yaml does)"
        )
    return None


def forbidden_env_problem(env: Mapping[str, str]) -> str | None:
    found = [name for name in FORBIDDEN_ENV if env.get(name)]
    if found:
        return f"{', '.join(found)} is set: the runner must not hold the server's secrets."
    return None


def _make_undumpable() -> None:
    """Keep the runs (same user) from attaching to this process or reading its memory."""
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        pr_set_dumpable = 4
        libc.prctl(pr_set_dumpable, 0, 0, 0, 0)
    except (OSError, AttributeError):
        pass


def main() -> None:
    import uvicorn

    env = os.environ
    limits = cgroup_limits()
    outside = (env.get("EXAMS_RUNNER_PIDS_LIMIT_OUTSIDE") or "").strip().lower() == "true"
    problems = (
        forbidden_env_problem(env),
        pid_namespace_problem(),
        pids_limit_problem(limits, outside),
    )
    for problem in problems:
        if problem:
            raise SystemExit(f"exams-generator-runner: {problem}")
    _make_undumpable()
    sandbox = ProcessSandbox(
        input_root=INPUT_ROOT,
        work_root=WORK_ROOT,
        tmp_root=TMP_ROOT,
        timeout=float(env.get("EXAMS_RUN_TIMEOUT") or 30),
        memory_mb=int(env.get("EXAMS_RUN_MEMORY_MB") or 4096),
        max_processes=None,
        container_limits=limits,
        sweep=True,
    )
    runner = DemoRunner(CheckerRegistry(load_plugins=False), sandbox)
    app = create_app(runner, queue_timeout=float(env.get("EXAMS_RUNNER_QUEUE") or 120))
    host = env.get("EXAMS_RUNNER_HOST") or "127.0.0.1"
    port = int(env.get("EXAMS_RUNNER_PORT") or 8766)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
