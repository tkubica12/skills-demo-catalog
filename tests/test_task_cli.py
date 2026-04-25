from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import ssl
import subprocess
import sys
from pathlib import Path

import pytest


CLI_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "task-api-helper"
    / "scripts"
    / "task_cli.py"
)
SKILL_ENV_PATH = CLI_PATH.parent.parent / ".env"
CLI_SPEC = importlib.util.spec_from_file_location("task_cli_module", CLI_PATH)
assert CLI_SPEC is not None and CLI_SPEC.loader is not None
task_cli = importlib.util.module_from_spec(CLI_SPEC)
CLI_SPEC.loader.exec_module(task_cli)


def run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env is not None:
        merged_env = env
    env = os.environ.copy()
    if "TASK_API_URL" in os.environ and "TASK_API_URL" not in merged_env:
        merged_env["TASK_API_URL"] = os.environ["TASK_API_URL"]
    return subprocess.run(
        [sys.executable, str(CLI_PATH), *args],
        capture_output=True,
        text=True,
        check=False,
        env=merged_env,
    )


def test_list_tasks_returns_json() -> None:
    result = run_cli("list-tasks")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert len(payload) >= 1


def test_list_tasks_status_filter() -> None:
    result = run_cli("list-tasks", "--status", "waiting-for-response")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert all(t["status"] == "waiting-for-response" for t in payload)


def test_get_task_returns_task() -> None:
    result = run_cli("get-task", "task-1")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["id"] == "task-1"
    assert isinstance(payload["comments"], list)


def test_add_comment_succeeds() -> None:
    result = run_cli("add-comment", "task-1", "hello")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["comment_id"].startswith("c-")


def test_cli_reads_api_url_from_skill_dotenv() -> None:
    original_dotenv = SKILL_ENV_PATH.read_text(encoding="utf-8") if SKILL_ENV_PATH.exists() else None
    try:
        SKILL_ENV_PATH.write_text(
            f"TASK_API_URL={os.environ['TASK_API_URL']}\n",
            encoding="utf-8",
        )
        env = os.environ.copy()
        env.pop("TASK_API_URL", None)
        result = run_cli("list-tasks", env=env)
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert isinstance(payload, list)
        assert len(payload) >= 1
    finally:
        if original_dotenv is None:
            SKILL_ENV_PATH.unlink(missing_ok=True)
        else:
            SKILL_ENV_PATH.write_text(original_dotenv, encoding="utf-8")


def test_request_json_retries_transient_transport_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"count": 0}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

        def read(self) -> bytes:
            return b'{"ok": true}'

    def fake_urlopen(*args: object, **kwargs: object) -> FakeResponse:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise task_cli.error.URLError(
                ssl.SSLEOFError(
                    8,
                    "[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol",
                )
            )
        return FakeResponse()

    monkeypatch.setattr(task_cli.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(task_cli.time, "sleep", lambda seconds: None)

    args = argparse.Namespace(api_url="https://example.test", token=None)
    payload = task_cli.request_json(args, "GET", "/tasks")

    assert payload == {"ok": True}
    assert attempts["count"] == 3


def test_request_json_does_not_retry_http_429(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    attempts = {"count": 0}

    def fake_urlopen(*args: object, **kwargs: object) -> object:
        attempts["count"] += 1
        raise task_cli.error.HTTPError(
            url="https://example.test/tasks",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=io.BytesIO(b'{"detail": "Rate limit exceeded. Retry the request."}'),
        )

    monkeypatch.setattr(task_cli.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(task_cli.time, "sleep", lambda seconds: None)

    args = argparse.Namespace(api_url="https://example.test", token=None)
    with pytest.raises(SystemExit):
        task_cli.request_json(args, "GET", "/tasks")

    assert attempts["count"] == 1
    assert "HTTP 429" in capsys.readouterr().err


def test_bulk_add_comment_by_status() -> None:
    result = run_cli("bulk-add-comment", "--status", "waiting-for-response", "bulk test comment")
    assert result.returncode == 0, result.stderr
    assert "Found" in result.stdout
    assert "Done." in result.stdout


def test_bulk_add_comment_by_task_ids() -> None:
    result = run_cli("bulk-add-comment", "--task-ids", "task-1", "task-2", "--", "hello from bulk")
    assert result.returncode == 0, result.stderr
    assert "Found 2 task(s)" in result.stdout
    assert "Done." in result.stdout


def test_bulk_add_comment_dry_run() -> None:
    result = run_cli("bulk-add-comment", "--status", "waiting-for-response", "--dry-run", "dry run text")
    assert result.returncode == 0, result.stderr
    assert "Dry-run mode" in result.stdout


def test_bulk_add_comment_missing_args() -> None:
    result = run_cli("bulk-add-comment", "some text")
    assert result.returncode != 0


def test_bulk_add_comment_rate_limit_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: dict[str, int] = {}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

        def read(self) -> bytes:
            return b'{"ok": true, "comment_id": "c-fake"}'

    def fake_urlopen(req: object, *args: object, **kwargs: object) -> object:
        url = getattr(req, "full_url", "")
        if "task-1/comments" in url:
            attempts["task-1"] = attempts.get("task-1", 0) + 1
            if attempts["task-1"] < 3:
                raise task_cli.error.HTTPError(
                    url=url,
                    code=429,
                    msg="Too Many Requests",
                    hdrs=None,
                    fp=io.BytesIO(b'{"detail": "rate limited"}'),
                )
        return FakeResponse()

    monkeypatch.setattr(task_cli.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(task_cli.time, "sleep", lambda s: None)

    args = argparse.Namespace(
        api_url=os.environ.get("TASK_API_URL", "http://127.0.0.1:18080"),
        token=None,
        task_ids=["task-1"],
        status=None,
        dry_run=False,
        text="retry test",
    )
    exit_code = task_cli.handle_bulk_add_comment(args)
    assert exit_code == 0
    assert attempts.get("task-1", 0) == 3
