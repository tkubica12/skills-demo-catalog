from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "benchmarks" / "agent_benchmark.py"
MODULE_SPEC = importlib.util.spec_from_file_location("agent_benchmark_module", MODULE_PATH)
assert MODULE_SPEC is not None and MODULE_SPEC.loader is not None
agent_benchmark = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = agent_benchmark
MODULE_SPEC.loader.exec_module(agent_benchmark)

BENCHMARK_COMMENT = agent_benchmark.BENCHMARK_COMMENT
RATE_LIMIT_BUDGET = agent_benchmark.RATE_LIMIT_BUDGET
RunResult = agent_benchmark.RunResult
RunningScenario = agent_benchmark.RunningScenario
build_markdown_summary = agent_benchmark.build_markdown_summary
build_report = agent_benchmark.build_report
prepare_workspace = agent_benchmark.prepare_workspace


def test_running_scenario_applies_deterministic_rate_limits() -> None:
    with RunningScenario() as (server, base_url):
        assert base_url.startswith("http://127.0.0.1:")
        assert server.maybe_rate_limit("POST", "/tasks/task-1/comments") is True
        assert server.maybe_rate_limit("POST", "/tasks/task-1/comments") is False
        assert server.rate_limit_budget[("POST", "/tasks/task-1/comments")] == 0
        assert server.rate_limit_budget[("POST", "/tasks/bulk-comment")] == RATE_LIMIT_BUDGET[
            ("POST", "/tasks/bulk-comment")
        ]


def test_prepare_workspace_installs_skill_and_env(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workspace = prepare_workspace(
        repo_root=repo_root,
        destination_root=tmp_path,
        workspace_name="candidate",
        task_api_url="http://127.0.0.1:18080",
        baseline_ref=None,
    )
    skill_root = workspace / ".agents" / "skills" / "task-api-helper"
    assert (workspace / ".git").exists()
    assert (skill_root / "scripts" / "task_cli.py").exists()
    assert (skill_root / ".env").read_text(encoding="utf-8") == "TASK_API_URL=http://127.0.0.1:18080\n"


def test_build_report_and_markdown_summary() -> None:
    baseline = RunResult(
        name="baseline",
        success=True,
        duration_seconds=9.5,
        updated_count=2,
        input_tokens=1200,
        output_tokens=220,
        llm_calls=5,
        premium_requests=4,
        api_duration_ms=8000,
        tool_counts={"shell": 4},
        task_api_requests={"GET /tasks": 1, "POST /tasks/task-1/comments": 2},
        rate_limit_responses=2,
        final_message="done",
    )
    candidate = RunResult(
        name="candidate",
        success=True,
        duration_seconds=4.0,
        updated_count=2,
        input_tokens=800,
        output_tokens=120,
        llm_calls=2,
        premium_requests=2,
        api_duration_ms=3500,
        tool_counts={"shell": 2},
        task_api_requests={"GET /tasks": 1, "POST /tasks/bulk-comment": 2},
        rate_limit_responses=1,
        final_message="done",
    )
    report = build_report(baseline, candidate, "gpt-4.1")
    markdown = build_markdown_summary(report)

    assert report["comparison"]["input_token_delta"] == -400
    assert report["comparison"]["llm_call_delta"] == -3
    assert report["comparison"]["premium_request_delta"] == -2
    assert "baseline (`main`)" in markdown
    assert "candidate (`patch`)" in markdown
    assert "LLM call delta" in markdown
    assert "Task API request delta" in markdown
    assert BENCHMARK_COMMENT in json.dumps(report)
