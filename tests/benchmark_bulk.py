from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


CLI_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "task-api-helper"
    / "scripts"
    / "task_cli.py"
)
BASELINE_DURATION: float | None = None


def _base_url() -> str:
    return os.environ.get("TASK_API_BASE_URL", "http://127.0.0.1:18080")


def _run_add_comment(task_id: str, message: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["TASK_API_BASE_URL"] = _base_url()
    return subprocess.run(
        [sys.executable, str(CLI_PATH), "add-comment", task_id, "--message", message],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _measure_baseline() -> float:
    start = time.perf_counter()
    for index, task_id in enumerate(["task-1", "task-2", "task-3"], start=1):
        result = _run_add_comment(task_id, f"benchmark-{index}")
        assert result.returncode == 0, result.stderr
    return time.perf_counter() - start


def _measure_simulated_bulk() -> float:
    payload = json.dumps(
        {
            "task_ids": ["task-1", "task-2", "task-3"],
            "message": "benchmark-bulk",
        }
    ).encode("utf-8")
    request_obj = urllib.request.Request(
        f"{_base_url()}/tasks/bulk-comment",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    start = time.perf_counter()
    with urllib.request.urlopen(request_obj, timeout=10) as response:
        body = json.loads(response.read().decode("utf-8"))
    duration = time.perf_counter() - start
    assert body["ok"] is True
    return duration


def test_single_add_comment_baseline() -> None:
    global BASELINE_DURATION
    BASELINE_DURATION = _measure_baseline()
    assert BASELINE_DURATION >= 0


def test_bulk_add_comment_simulated(capsys) -> None:
    baseline = BASELINE_DURATION if BASELINE_DURATION is not None else _measure_baseline()
    bulk_duration = _measure_simulated_bulk()
    speedup = baseline / bulk_duration if bulk_duration > 0 else float("inf")
    token_mode = os.environ.get("BENCHMARK_TOKEN_MODE", "none")

    with capsys.disabled():
        print(
            f"Baseline (loop): {baseline:.4f}s | "
            f"Simulated bulk: {bulk_duration:.4f}s | "
            f"Speedup: {speedup:.2f}x | "
            f"Token mode: {token_mode}"
        )

    assert bulk_duration >= 0
