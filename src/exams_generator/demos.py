"""Run the demos and doctests of a reference solution, inside the sandbox.

This is separate from the checkers on purpose: checkers only compile, and
this module is the only place that executes a solution. It is reachable only
through the ``run_demos`` tool, which exists only when ``EXAMS_RUN_DEMOS`` is on.

What counts as a demo:

* **Python**: doctests in docstrings, run with :mod:`doctest`.
* **Haskell**: ``>>> expression`` lines in comments, followed by the expected
  output, evaluated with GHCi.
* **C / C++**: a ``main``, linked with every source of the language and run;
  exit status 0 passes. Solutions usually have no ``main``, so pass one with
  the demo, in another file, through ``extra_files``.

Every status other than ``passed`` means nothing has been verified. A missing
toolchain or sandbox and a solution without demos are ``skipped``.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from .checkers import Checker, CheckerRegistry
from .checkers.c_family import _CFamilyChecker
from .sandbox import SandboxRun, SandboxStatus

PASSED, FAILED, TIMEOUT, SKIPPED = "passed", "failed", "timeout", "skipped"
STATUSES = (PASSED, FAILED, TIMEOUT, SKIPPED)

MAX_REPORT_CHARS = 16_000
DEMO_BINARY = ".exams-demo"


@dataclass
class DemoResult:
    language: str
    status: str
    files: list[str] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    note: str = ""
    output: str = ""

    @property
    def ok(self) -> bool:
        return self.status == PASSED

    def as_text(self) -> str:
        if self.status == SKIPPED:
            return f"[{self.language}] SKIPPED: {self.note}"
        head = f"[{self.language}] {self.status.upper()}"
        if self.status != TIMEOUT:
            head += f" ({self.passed} passed, {self.failed} failed)"
        return "\n".join(part for part in (head, self.note, self.output) if part)

    def as_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "status": self.status,
            "ok": self.ok,
            "skipped": self.status == SKIPPED,
            "files": self.files,
            "passed": self.passed,
            "failed": self.failed,
            "output": self.as_text(),
        }

    def to_wire(self) -> dict[str, object]:
        """The fields a remote runner sends back (see ``remote.py``)."""
        return {
            "language": self.language,
            "status": self.status,
            "files": self.files,
            "passed": self.passed,
            "failed": self.failed,
            "note": self.note,
            "output": self.output,
        }

    @classmethod
    def from_wire(cls, data: object) -> DemoResult:
        """Rebuild a result from a runner's answer; ``ValueError`` if it is malformed."""
        if not isinstance(data, dict):
            raise ValueError("a result is not an object")
        language, status = data.get("language"), data.get("status")
        if not isinstance(language, str) or status not in STATUSES:
            raise ValueError(f"bad language or status: {language!r}, {status!r}")
        counts = [data.get("passed", 0), data.get("failed", 0)]
        if not all(isinstance(n, int) and not isinstance(n, bool) and n >= 0 for n in counts):
            raise ValueError("passed and failed must be non-negative integers")
        files = data.get("files", [])
        texts = [data.get("note", ""), data.get("output", "")]
        if not (isinstance(files, list) and all(isinstance(f, str) for f in files)):
            raise ValueError("files must be a list of names")
        if not all(isinstance(t, str) for t in texts):
            raise ValueError("note and output must be strings")
        note, output = (_cap(t) for t in texts)
        return cls(language, status, files, counts[0], counts[1], note, output)


class DemoSandbox(Protocol):
    """What the runner needs from a sandbox: ``Sandbox`` or ``ProcessSandbox``."""

    timeout: float
    input_root: str
    work_root: str

    def status(self) -> SandboxStatus: ...

    def search_path(self) -> str: ...

    def visible(self, path: str) -> bool: ...

    def run(
        self,
        files: Mapping[str, str],
        run: str,
        *,
        build: str | None = None,
        support: Mapping[str, str] | None = None,
    ) -> SandboxRun: ...


@dataclass
class _Plan:
    """How to run one language's demos and read the outcome."""

    run: str
    interpret: Callable[[SandboxRun], tuple[str, int, int, str]]
    build: str | None = None
    support: dict[str, str] = field(default_factory=dict)
    files: dict[str, str] | None = None
    #: Marker lines to hide from the report.
    marker: str | None = None


# --------------------------------------------------------------------- C/C++

_MAIN_RE = re.compile(r"^\s*(?:int|void)\s+main\s*\(", re.MULTILINE)


def _plan_c_family(
    checker: Checker, files: Mapping[str, str], exe: str, support_dir: str
) -> _Plan | str:
    assert isinstance(checker, _CFamilyChecker)
    sources = sorted(f for f in files if checker.owns(f))
    if not any(_MAIN_RE.search(files[f]) for f in sources):
        return "no main() to run; pass one in extra_files to demonstrate the solution"

    def interpret(run: SandboxRun) -> tuple[str, int, int, str]:
        if run.exit_code == 0:
            return PASSED, 1, 0, "exit status 0"
        return FAILED, 0, 1, _describe_exit(run.exit_code)

    build = shlex.join([exe, "-I.", *checker.flags(), "-o", DEMO_BINARY, *sources, "-lm"])
    return _Plan(run=f"./{DEMO_BINARY}", build=build, interpret=interpret)


def _describe_exit(code: int) -> str:
    return f"killed by signal {code - 128}" if code > 128 else f"exit status {code}"


# -------------------------------------------------------------------- Python

_DOCTEST_HARNESS = """\
import doctest
import importlib.util
import pathlib
import sys

marker, *paths = sys.argv[1:]
sys.path.insert(0, ".")
attempted = failed = 0
for raw in paths:
    name = pathlib.Path(raw).stem
    spec = importlib.util.spec_from_file_location(name, raw)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses and friends look themselves up here
    spec.loader.exec_module(module)
    result = doctest.testmod(module, verbose=False)
    attempted += result.attempted
    failed += result.failed
print(f"{marker} {attempted} {failed}", flush=True)
sys.exit(1 if failed else 0)
"""


def _plan_python(
    checker: Checker, files: Mapping[str, str], exe: str, support_dir: str
) -> _Plan | str:
    marker = f"exams-doctest-{os.urandom(8).hex()}"
    sources = sorted(f for f in files if f.endswith(".py"))
    if not sources:
        return "no Python source files"

    def interpret(run: SandboxRun) -> tuple[str, int, int, str]:
        found = re.findall(rf"^{marker} (\d+) (\d+)$", run.stdout, re.MULTILINE)
        if not found:
            return FAILED, 0, 0, "the program stopped before finishing its doctests"
        attempted, failed = (int(n) for n in found[-1])
        if attempted == 0:
            return SKIPPED, 0, 0, "no doctests found (only docstrings are searched)"
        status = PASSED if failed == 0 else FAILED
        return status, attempted - failed, failed, ""

    cmd = [exe, "-B", f"{support_dir}/doctest_harness.py", marker, *sources]
    return _Plan(
        run=shlex.join(cmd),
        support={"doctest_harness.py": _DOCTEST_HARNESS},
        interpret=interpret,
        marker=marker,
    )


# ------------------------------------------------------------------- Haskell

_DEMO_LINE_RE = re.compile(r"^\s*(?:--\s?)?>>> ?(.*)$")
_COMMENT_END_RE = re.compile(r"^\s*-\}")
_LINE_COMMENT_RE = re.compile(r"^\s*--\s?")


@dataclass
class _HaskellDemo:
    expression: str
    expected: list[str]


def extract_haskell_demos(source: str) -> list[_HaskellDemo]:
    """``>>> expr`` lines; the lines right below are the expected output."""
    demos: list[_HaskellDemo] = []
    current: _HaskellDemo | None = None
    in_line_comment = False
    for line in source.splitlines():
        match = _DEMO_LINE_RE.match(line)
        if match:
            current = _HaskellDemo(match.group(1).strip(), [])
            demos.append(current)
            in_line_comment = bool(_LINE_COMMENT_RE.match(line))
        elif current is not None:
            ended = (
                not line.strip()
                or _COMMENT_END_RE.match(line)
                or (in_line_comment and not _LINE_COMMENT_RE.match(line))
            )
            if ended:
                current = None
            else:
                expected = _LINE_COMMENT_RE.sub("", line, count=1) if in_line_comment else line
                current.expected.append(expected)
    return demos


def _lines(text: str) -> list[str]:
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return lines


def _plan_haskell(
    checker: Checker, files: Mapping[str, str], exe: str, support_dir: str
) -> _Plan | str:
    originals = sorted(f for f in files if checker.owns(f) and not f.endswith(".lhs"))
    per_file = {f: extract_haskell_demos(files[f]) for f in originals}
    if not any(per_file.values()):
        return "no `>>>` demo lines found"

    prepared, targets = checker.prepare(files, originals)
    modules = {
        original: target.removesuffix(".hs").replace("/", ".")
        for original, target in zip(originals, targets, strict=True)
    }
    marker = f"exams-demo-{os.urandom(8).hex()}"
    script = [':set prompt ""', ':set prompt-cont ""']
    demos: list[_HaskellDemo] = []
    for original, found in per_file.items():
        if found:
            script.append(f":module *{modules[original]}")
        for demo in found:
            script.append(f'putStrLn "{marker}:{len(demos)}"')
            script.append(demo.expression)
            demos.append(demo)
    script.append(f'putStrLn "{marker}:end"')

    def interpret(run: SandboxRun) -> tuple[str, int, int, str]:
        parts = re.split(rf"{marker}:(\d+|end)\r?\n", run.stdout)
        load_output = parts[0].strip()
        blocks = dict(zip(parts[1::2], parts[2::2], strict=True))
        passed, problems = 0, []
        for index, demo in enumerate(demos):
            got = blocks.get(str(index))
            if got is not None and _lines(got) == _lines("\n".join(demo.expected)):
                passed += 1
                continue
            shown = "(GHCi stopped before this demo)" if got is None else got.rstrip()
            expected = "\n".join(demo.expected) or "(no output)"
            problems.append(f">>> {demo.expression}\nexpected:\n{expected}\ngot:\n{shown}")
        failed = len(demos) - passed
        notes = [load_output] if load_output and failed else []
        status = PASSED if failed == 0 else FAILED
        return status, passed, failed, "\n\n".join(notes + problems)

    argv = [exe, "--interactive", "-v0", "-ignore-dot-ghci", "-i."]
    argv += [*_ghc_flags(), *sorted(modules.values())]
    return _Plan(
        run=f"{shlex.join(argv)} < {shlex.quote(support_dir + '/demos.ghci')} 2>&1",
        support={"demos.ghci": "\n".join(script) + "\n"},
        files=prepared,
        interpret=interpret,
        marker=marker,
    )


def _ghc_flags() -> list[str]:
    return shlex.split(os.environ.get("EXAMS_GHC_FLAGS", ""))


_PLANNERS: dict[str, Callable[[Checker, Mapping[str, str], str, str], _Plan | str]] = {
    "python": _plan_python,
    "haskell": _plan_haskell,
    "c": _plan_c_family,
    "cpp": _plan_c_family,
}


# ------------------------------------------------------------------ running


def languages_or_error(
    registry: CheckerRegistry, files: Mapping[str, str]
) -> tuple[list[str], dict[str, Any] | None]:
    """The languages to run, or the reply for a request with nothing to run."""
    if not files:
        return [], {"ok": False, "results": [], "output": "No files to run."}
    languages = registry.languages_for(files)
    if not languages:
        known = ", ".join(registry.names)
        message = f"No language owns these files ({', '.join(files)}). Known: {known}."
        return [], {"ok": False, "results": [], "output": message}
    return languages, None


def summarize(results: Sequence[DemoResult], sandbox: Mapping[str, object]) -> dict[str, Any]:
    return {
        # Skipped is not passed: every language has to have really run.
        "ok": bool(results) and all(r.ok for r in results),
        "results": [r.as_dict() for r in results],
        "output": "\n\n".join(r.as_text() for r in results),
        "sandbox": dict(sandbox),
    }


class DemoRunner:
    def __init__(self, registry: CheckerRegistry, sandbox: DemoSandbox) -> None:
        self.registry = registry
        self.sandbox = sandbox

    def _executable(self, checker: Checker) -> tuple[str | None, str]:
        """The toolchain as seen inside the sandbox, or why there is none."""
        override = os.environ.get(checker.executable_env) if checker.executable_env else None
        candidates = [override] if override else list(checker.default_executables)
        search = self.sandbox.search_path()
        hidden = []
        for candidate in candidates:
            found = shutil.which(candidate, path=search) if candidate else None
            if found and self.sandbox.visible(found):
                return found, ""
            if candidate and shutil.which(candidate):
                hidden.append(candidate)
        if hidden:
            return None, (
                f"{hidden[0]} is outside the sandbox; add its installation directory to "
                "EXAMS_RUN_RO_BINDS"
            )
        return None, f"toolchain not available. {checker.install_hint}".strip()

    def run_language(self, language: str, files: Mapping[str, str]) -> DemoResult:
        checker = self.registry.get(language)
        owned = sorted(f for f in files if checker.owns(f))
        planner = _PLANNERS.get(checker.name)
        if planner is None:
            return DemoResult(checker.name, SKIPPED, owned, note="this language has no demo runner")
        exe, why = self._executable(checker)
        if exe is None:
            return DemoResult(checker.name, SKIPPED, owned, note=why)
        plan = planner(checker, files, exe, f"{self.sandbox.input_root}/support")
        if isinstance(plan, str):
            return DemoResult(checker.name, SKIPPED, owned, note=plan)
        run = self.sandbox.run(
            plan.files if plan.files is not None else files,
            plan.run,
            build=plan.build,
            support=plan.support,
        )
        return self._outcome(checker.name, owned, plan, run)

    def _outcome(self, language: str, owned: list[str], plan: _Plan, run: SandboxRun) -> DemoResult:
        if run.timed_out:
            note = f"timed out after {self.sandbox.timeout:g}s and was killed"
            output = _report(run, plan, self.sandbox.work_root)
            return DemoResult(language, TIMEOUT, owned, note=note, output=output)
        if not run.started:
            note = f"the sandbox could not start: {run.stderr or 'unknown error'}"
            return DemoResult(language, SKIPPED, owned, note=note)
        if not run.built:
            note = f"build failed ({_describe_exit(run.exit_code)})"
            output = _report(run, plan, self.sandbox.work_root)
            return DemoResult(language, FAILED, owned, failed=1, note=note, output=output)
        status, passed, failed, note = plan.interpret(run)
        output = "" if status == SKIPPED else _report(run, plan, self.sandbox.work_root)
        return DemoResult(language, status, owned, passed, failed, note, output)

    def results(
        self, files: Mapping[str, str], languages: Sequence[str]
    ) -> tuple[list[DemoResult], SandboxStatus]:
        status = self.sandbox.status()
        if status.available:
            results = [self.run_language(language, files) for language in languages]
        else:
            note = f"sandbox not available. {status.hint}".strip()
            results = [DemoResult(language, SKIPPED, note=note) for language in languages]
        return results, status

    def run_files(self, files: Mapping[str, str]) -> dict[str, Any]:
        languages, problem = languages_or_error(self.registry, files)
        if problem is not None:
            return problem
        results, status = self.results(files, languages)
        return summarize(results, status.as_dict())


def _cap(text: str) -> str:
    if len(text) > MAX_REPORT_CHARS:
        return text[:MAX_REPORT_CHARS] + "\n... (output truncated)"
    return text


def _report(run: SandboxRun, plan: _Plan, work_root: str) -> str:
    text = "\n".join(s.rstrip() for s in (run.build_log, run.stdout, run.stderr) if s.strip())
    text = text.replace(work_root.rstrip("/") + "/", "")
    if plan.marker:
        text = re.sub(rf"^{plan.marker}.*\n?", "", text, flags=re.MULTILINE).rstrip()
    if len(text) > MAX_REPORT_CHARS:
        text = text[:MAX_REPORT_CHARS] + "\n... (output truncated)"
    elif run.truncated:
        text += "\n... (output truncated)"
    return text
