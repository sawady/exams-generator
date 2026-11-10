"""Run code that is not trusted in a throwaway bubblewrap sandbox.

Used only by the optional ``run_demos`` tool (see ``demos.py``); the checkers
never come near it, because they do not execute anything.

The sandbox is `bubblewrap <https://github.com/containers/bubblewrap>`_ with
every namespace unshared. Inside it the code sees:

* the system directories (``/usr``, ``/bin``, ``/lib*``) and any directory in
  ``EXAMS_RUN_RO_BINDS``, all read-only;
* its own files in ``/work``, a size-limited tmpfs, and an empty ``/tmp``;
* no network (only a private loopback), no other process, no host environment
  variable, no home directory, no ``EXAMS_DIR``.

Inside, ``prlimit`` caps address space, processes, file size and open files,
and the caller enforces a wall-clock timeout by killing the whole tree.

There is no unsandboxed fallback: if the sandbox cannot start, the caller is
told so, and reports the run as skipped.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

SYSTEM_ROOTS = ("/usr", "/bin", "/sbin", "/lib", "/lib32", "/lib64", "/libx32")
#: Single files and directories compilers need; the rest of ``/etc`` stays out.
SYSTEM_EXTRAS = ("/etc/ld.so.cache", "/etc/alternatives", "/var/lib/ghc")
SYSTEM_PATH = "/usr/local/bin:/usr/bin:/bin"

WORK_DIR = "/work"
MAX_TMPFS_BYTES = 128 * 1024 * 1024
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_PROCESSES = 128
MAX_OPEN_FILES = 256
#: How much of each output stream is read back into the server.
MAX_CAPTURE_BYTES = 1024 * 1024

INSTALL_HINT = "Install bubblewrap 0.6 or newer (`apt install bubblewrap`). Linux only."

# bwrap gets only this; --clearenv and --setenv then define the inside.
_HOST_ENV = {"PATH": SYSTEM_PATH}


@dataclass(frozen=True)
class SandboxStatus:
    available: bool
    tool: str
    path: str | None = None
    version: str | None = None
    hint: str = ""
    limits: Mapping[str, object] | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "available": self.available,
            "tool": self.tool,
            "path": self.path,
            "version": self.version,
            "hint": self.hint,
            "limits": dict(self.limits or {}),
        }


@dataclass
class SandboxRun:
    #: False when the sandbox never got to run the code; nothing was tested.
    started: bool
    #: False when the build step failed (or never ran).
    built: bool
    exit_code: int
    timed_out: bool = False
    truncated: bool = False
    build_log: str = ""
    stdout: str = ""
    stderr: str = ""


class Sandbox:
    def __init__(
        self,
        *,
        bwrap: str = "bwrap",
        timeout: float = 30.0,
        memory_mb: int = 4096,
        ro_binds: Sequence[Path] = (),
        protected: Sequence[Path] = (),
    ) -> None:
        self.bwrap = bwrap
        self.timeout = timeout
        self.memory_mb = memory_mb
        self.ro_binds = [os.path.realpath(p) for p in ro_binds]
        self.protected = [os.path.realpath(p) for p in protected]

    # ----------------------------------------------------------- visibility

    def _roots(self) -> list[str]:
        roots = [os.path.realpath(r) for r in SYSTEM_ROOTS if os.path.exists(r)]
        return roots + self.ro_binds

    def visible(self, path: str) -> bool:
        """Whether ``path`` and what it points to both exist inside the sandbox."""
        roots = self._roots()
        return all(
            any(_within(candidate, root) for root in roots)
            for candidate in (os.path.abspath(path), os.path.realpath(path))
        )

    def search_path(self) -> str:
        """``PATH`` inside the sandbox; the read-only binds win over the system."""
        extra = [os.path.join(bind, "bin") for bind in self.ro_binds]
        return ":".join([*extra, SYSTEM_PATH])

    def _bind_problem(self) -> str | None:
        """A reason not to start: a configured path would expose private data."""
        home = os.path.realpath(os.path.expanduser("~"))
        for bind in self.ro_binds:
            if bind == "/" or _within(home, bind):
                return f"EXAMS_RUN_RO_BINDS would expose the home directory: {bind}"
        for root in self._roots():
            for private in self.protected:
                if _within(private, root) or _within(root, private):
                    return f"The sandbox would expose {private} through {root}."
        return None

    # --------------------------------------------------------------- status

    def _limits(self) -> dict[str, object]:
        return {
            "timeout_seconds": self.timeout,
            "memory_mb": self.memory_mb,
            "max_processes": MAX_PROCESSES,
            "max_file_mb": MAX_FILE_BYTES // (1024 * 1024),
            "work_tmpfs_mb": MAX_TMPFS_BYTES // (1024 * 1024)
            if self._supports_size()
            else "half of RAM (bubblewrap older than 0.8 cannot limit it)",
        }

    def _supports_size(self) -> bool:
        exe = shutil.which(self.bwrap)
        if exe is None:
            return False
        try:
            proc = subprocess.run([exe, "--help"], capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.SubprocessError):
            return False
        return "--size" in proc.stdout

    def status(self) -> SandboxStatus:
        """Check that the sandbox really starts here, with the real configuration."""
        exe = shutil.which(self.bwrap)
        if exe is None:
            return SandboxStatus(False, self.bwrap, hint=INSTALL_HINT)
        limits = self._limits()
        problem = self._bind_problem()
        if problem:
            return SandboxStatus(False, self.bwrap, path=exe, hint=problem, limits=limits)
        version = None
        try:
            proc = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=15)
            version = proc.stdout.strip() or None
            with tempfile.TemporaryDirectory(prefix="exams-sandbox-probe-") as tmp:
                probe = subprocess.run(
                    [*self._argv(exe, Path(tmp)), "/bin/sh", "-c", "exit 0"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    stdin=subprocess.DEVNULL,
                    env=_HOST_ENV,
                )
        except (OSError, subprocess.SubprocessError) as err:
            return SandboxStatus(False, self.bwrap, exe, version, f"{err}", limits)
        if probe.returncode != 0:
            detail = (probe.stderr.strip().splitlines() or [""])[0]
            hint = f"bubblewrap cannot start here: {detail}".strip()
            return SandboxStatus(False, self.bwrap, exe, version, hint, limits)
        return SandboxStatus(True, self.bwrap, exe, version, limits=limits)

    # -------------------------------------------------------------- running

    def _argv(self, exe: str, input_dir: Path) -> list[str]:
        size = ["--size", str(MAX_TMPFS_BYTES)] if self._supports_size() else []
        argv = [
            exe,
            "--unshare-all",
            "--unshare-user",
            "--die-with-parent",
            "--new-session",
            "--cap-drop",
            "ALL",
            "--hostname",
            "sandbox",
            "--clearenv",
            "--setenv",
            "PATH",
            self.search_path(),
            "--setenv",
            "HOME",
            WORK_DIR,
            "--setenv",
            "TMPDIR",
            "/tmp",
            "--setenv",
            "LANG",
            "C.UTF-8",
            "--setenv",
            "PYTHONDONTWRITEBYTECODE",
            "1",
        ]
        for path in (*SYSTEM_ROOTS, *SYSTEM_EXTRAS):
            argv += ["--ro-bind-try", path, path]
        for bind in self.ro_binds:
            argv += ["--ro-bind", bind, bind]
        argv += ["--proc", "/proc", "--dev", "/dev", *size, "--tmpfs", "/dev/shm"]
        argv += [*size, "--tmpfs", "/tmp", *size, "--tmpfs", WORK_DIR]
        argv += ["--ro-bind", str(input_dir), "/input", "--chdir", WORK_DIR]
        argv += [
            "prlimit",
            f"--as={self.memory_mb * 1024 * 1024}",
            f"--nproc={MAX_PROCESSES}",
            f"--fsize={MAX_FILE_BYTES}",
            f"--nofile={MAX_OPEN_FILES}",
            "--core=0",
            "--",
        ]
        return argv

    def run(
        self,
        files: Mapping[str, str],
        run: str,
        *,
        build: str | None = None,
        support: Mapping[str, str] | None = None,
    ) -> SandboxRun:
        """Copy ``files`` into ``/work``, run the ``build`` then ``run`` shell lines.

        ``support`` files are visible read-only in ``/input/support``. Markers
        written by the driver tell apart a sandbox that never started and a
        build that failed from a program that ran and failed.
        """
        exe = shutil.which(self.bwrap)
        if exe is None:
            return SandboxRun(started=False, built=False, exit_code=-1, stderr=INSTALL_HINT)
        nonce = os.urandom(8).hex()
        setup_mark, build_mark = f"{nonce}:setup", f"{nonce}:build"
        with tempfile.TemporaryDirectory(prefix="exams-sandbox-") as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            (input_dir / "files").mkdir(parents=True)
            (input_dir / "support").mkdir()
            for filename, content in files.items():
                target = input_dir / "files" / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            for filename, content in (support or {}).items():
                (input_dir / "support" / filename).write_text(content, encoding="utf-8")
            driver = input_dir / "support" / "driver.sh"
            driver.write_text(
                "\n".join(
                    [
                        "cp -R /input/files/. . || exit 125",
                        f"echo {setup_mark} >&2",
                        *([f"{build} 1>&2 || exit $?"] if build else []),
                        f"echo {build_mark} >&2",
                        f"exec {run}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            argv = [*self._argv(exe, input_dir), "/bin/sh", "/input/support/driver.sh"]
            out_path, err_path = root / "stdout", root / "stderr"
            with open(out_path, "wb") as out, open(err_path, "wb") as err:
                proc = subprocess.Popen(
                    argv,
                    stdin=subprocess.DEVNULL,
                    stdout=out,
                    stderr=err,
                    start_new_session=True,
                    env=_HOST_ENV,
                )
                timed_out = False
                try:
                    proc.wait(timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    _kill_tree(proc)
                    proc.wait()
            stdout, out_cut = _read_capped(out_path)
            stderr, err_cut = _read_capped(err_path)

        setup_log, sep, rest = stderr.partition(setup_mark + "\n")
        if not sep:
            # Nothing of the caller's ran; report bwrap's own complaint.
            return SandboxRun(
                started=False,
                built=False,
                exit_code=proc.returncode,
                timed_out=timed_out,
                stderr=setup_log.strip(),
            )
        build_log, sep, after = rest.partition(build_mark + "\n")
        built = bool(sep)
        return SandboxRun(
            started=True,
            built=built,
            exit_code=proc.returncode,
            timed_out=timed_out,
            truncated=out_cut or err_cut,
            build_log=build_log if built else rest,
            stdout=stdout,
            stderr=after if built else "",
        )


def _within(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")


def _kill_tree(proc: subprocess.Popen[bytes]) -> None:
    # bwrap dies here, and --die-with-parent then takes the PID namespace with it.
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        proc.kill()


def _read_capped(path: Path) -> tuple[str, bool]:
    with open(path, "rb") as handle:
        data = handle.read(MAX_CAPTURE_BYTES + 1)
    truncated = len(data) > MAX_CAPTURE_BYTES
    return data[:MAX_CAPTURE_BYTES].decode("utf-8", errors="replace"), truncated
