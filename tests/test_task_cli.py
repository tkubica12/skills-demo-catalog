from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


CLI_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "task-api-helper"
    / "scripts"
    / "task_cli.py"
)
SKILL_ENV_PATH = CLI_PATH.parent.parent / ".env"


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


def test_bulk_add_comment_not_available() -> None:
    result = run_cli("bulk-add-comment")
    assert result.returncode != 0
    assert "invalid choice" in result.stderr
