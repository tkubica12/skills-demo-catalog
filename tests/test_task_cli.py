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


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["TASK_API_BASE_URL"] = os.environ["TASK_API_BASE_URL"]
    return subprocess.run(
        [sys.executable, str(CLI_PATH), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_list_tasks_returns_json() -> None:
    result = run_cli("list-tasks")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert len(payload) >= 1


def test_get_task_returns_task() -> None:
    result = run_cli("get-task", "task-1")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["id"] == "task-1"
    assert isinstance(payload["comments"], list)


def test_add_comment_succeeds() -> None:
    result = run_cli("add-comment", "task-1", "--message", "hello")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["comment_id"].startswith("c-")


def test_bulk_add_comment_not_available() -> None:
    result = run_cli("bulk-add-comment")
    assert result.returncode != 0
    assert "invalid choice" in result.stderr
