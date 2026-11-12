"""Client for a separate demo runner (``EXAMS_RUN_RUNNER_URL``).

With a runner configured, ``run_demos`` sends the files of a run to it instead
of starting bubblewrap here. The runner (``runner.py``) lives in its own
container, with the toolchains but without the exams, the server's token or
network access, and answers with one result per language.

Protocol, version 1 (JSON over HTTP, no authentication: the runner must be
reachable only from this server, on an internal network):

* ``GET  /healthz``   -> ``ok``
* ``GET  /v1/status`` -> ``{"protocol": 1, "version", "sandbox": {...}, "languages": [...]}``
* ``POST /v1/run``    ``{"protocol": 1, "files": {name: content}}``
  -> ``{"protocol": 1, "results": [{"language", "status", "files", "passed",
  "failed", "note", "output"}], "sandbox": {...}}``

The server trusts nothing it cannot check: ``ok`` is computed here from the
statuses, a language the runner does not report is *skipped*, and a runner
that is down, slow, busy or answers anything malformed makes every language
*skipped*. Never passed.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any

from .checkers import CheckerRegistry
from .demos import SKIPPED, DemoResult, languages_or_error, summarize

PROTOCOL = 1
#: Larger answers are refused: results are capped well below this on the runner.
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
STATUS_TIMEOUT = 10.0
#: Seconds to wait for a run's answer (EXAMS_RUN_RUNNER_TIMEOUT). Also what a run waits
#: when the runner dies mid-run and the connection hangs.
DEFAULT_TIMEOUT = 60.0


class RunnerError(Exception):
    """The runner could not be reached or gave an unusable answer."""


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


# No proxies from the environment (the runner is on an internal network) and no redirects.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirects())


class RemoteDemoRunner:
    def __init__(
        self, registry: CheckerRegistry, url: str, *, timeout: float = DEFAULT_TIMEOUT
    ) -> None:
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"EXAMS_RUN_RUNNER_URL must be an http(s) URL, not {url!r}")
        self.registry = registry
        self.url = url.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------- transport

    def _request(self, path: str, body: dict[str, Any] | None, timeout: float) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            self.url + path,
            data=data,
            method="GET" if body is None else "POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with _opener.open(request, timeout=timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as err:
            detail = _error_detail(err)
            raise RunnerError(f"the runner answered HTTP {err.code}{detail}") from err
        except (OSError, ValueError) as err:  # URLError, timeouts, refused connections
            reason = getattr(err, "reason", None) or err
            raise RunnerError(f"the runner at {self.url} did not answer: {reason}") from err
        if len(raw) > MAX_RESPONSE_BYTES:
            raise RunnerError("the runner's answer is too large")
        try:
            payload = json.loads(raw)
        except ValueError as err:
            raise RunnerError("the runner's answer is not JSON") from err
        if not isinstance(payload, dict) or payload.get("protocol") != PROTOCOL:
            raise RunnerError(f"the runner does not speak protocol {PROTOCOL}")
        return payload

    # ---------------------------------------------------------------- status

    def status(self) -> dict[str, Any]:
        """What ``list_languages`` shows under ``demos``."""
        base: dict[str, Any] = {"mode": "remote", "runner_url": self.url, "tool": "runner"}
        try:
            payload = self._request("/v1/status", None, STATUS_TIMEOUT)
        except RunnerError as err:
            return {**base, "available": False, "hint": str(err)}
        sandbox = payload.get("sandbox")
        sandbox = sandbox if isinstance(sandbox, dict) else {}
        available = sandbox.get("available") is True
        hint = sandbox.get("hint") if isinstance(sandbox.get("hint"), str) else ""
        return {
            **base,
            "available": available,
            "hint": hint if available or hint else "the runner reports its sandbox unavailable",
            "runner_version": payload.get("version"),
            "limits": sandbox.get("limits") if isinstance(sandbox.get("limits"), dict) else {},
            "languages": payload.get("languages")
            if isinstance(payload.get("languages"), list)
            else [],
        }

    # ------------------------------------------------------------------- run

    def run_files(self, files: Mapping[str, str]) -> dict[str, Any]:
        languages, problem = languages_or_error(self.registry, files)
        if problem is not None:
            return problem
        where = {"mode": "remote", "runner_url": self.url, "tool": "runner"}
        try:
            payload = self._request(
                "/v1/run", {"protocol": PROTOCOL, "files": dict(files)}, self.timeout
            )
            reported = _results(payload)
        except RunnerError as err:
            note = f"{err}. Nothing ran."
            results = [DemoResult(language, SKIPPED, note=note) for language in languages]
            return summarize(results, {**where, "available": False, "hint": str(err)})
        results = []
        for language in languages:
            result = reported.get(language)
            if result is None:
                note = "the runner did not report this language"
                result = DemoResult(language, SKIPPED, note=note)
            results.append(result)
        sandbox = payload.get("sandbox")
        runner_sandbox = sandbox if isinstance(sandbox, dict) else {}
        return summarize(results, {**where, "available": True, "runner_sandbox": runner_sandbox})


def _results(payload: Mapping[str, Any]) -> dict[str, DemoResult]:
    raw = payload.get("results")
    if not isinstance(raw, list):
        raise RunnerError("the runner's answer has no results")
    out: dict[str, DemoResult] = {}
    for item in raw:
        try:
            result = DemoResult.from_wire(item)
        except ValueError as err:
            raise RunnerError(f"the runner's answer is malformed: {err}") from err
        out.setdefault(result.language, result)
    return out


def _error_detail(err: urllib.error.HTTPError) -> str:
    try:
        payload = json.loads(err.read(64 * 1024))
    except (OSError, ValueError):
        return ""
    message = payload.get("error") if isinstance(payload, dict) else None
    return f": {message[:500]}" if isinstance(message, str) else ""
