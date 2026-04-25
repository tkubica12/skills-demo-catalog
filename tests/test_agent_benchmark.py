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

RunResult = agent_benchmark.RunResult
RunningScenario = agent_benchmark.RunningScenario
build_markdown_summary = agent_benchmark.build_markdown_summary
build_report = agent_benchmark.build_report
evaluate_required_comments = agent_benchmark.evaluate_required_comments
load_spec = agent_benchmark.load_spec
prepare_workspace = agent_benchmark.prepare_workspace


def _write_spec(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "id": "bulk-add-comment-retry",
                "title": "Bulk add comment with retry",
                "hypothesis": "A central bulk comment command should reduce repeated calls.",
                "prompt": (
                    "Use the installed task-api-helper skill. Add the exact comment "
                    '"Benchmark follow-up - please respond." to every task waiting for response. '
                    "Do not edit files and keep going through transient rate limits."
                ),
                "scenario": {
                    "tasks": [
                        {
                            "id": "task-1",
                            "title": "Waiting on customer confirmation",
                            "status": "waiting-for-response",
                        },
                        {
                            "id": "task-2",
                            "title": "Pending vendor reply",
                            "status": "waiting-for-response",
                        },
                        {
                            "id": "task-3",
                            "title": "Archive completed onboarding",
                            "status": "resolved",
                        },
                    ],
                    "comments": {
                        "task-1": [
                            {
                                "id": "c-1001",
                                "text": "Initial message sent to customer",
                                "author": "support-bot",
                            }
                        ]
                    },
                    "rate_limit_budget": {
                        "POST /tasks/task-1/comments": 1,
                        "POST /tasks/bulk-comment": 1,
                    },
                },
                "assertions": {
                    "required_comments": [
                        {
                            "text": "Benchmark follow-up - please respond.",
                            "task_status": "waiting-for-response",
                            "min_count": 2,
                        }
                    ]
                },
                "comparison_focus": ["duration_seconds", "input_tokens", "llm_calls"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def test_load_spec_reads_scenario_definition(tmp_path: Path) -> None:
    spec = load_spec(_write_spec(tmp_path / "benchmark-spec.json"))
    assert spec.id == "bulk-add-comment-retry"
    assert spec.title == "Bulk add comment with retry"
    assert spec.rate_limit_budget[("POST", "/tasks/task-1/comments")] == 1
    assert spec.required_comments[0].task_status == "waiting-for-response"
    assert spec.comparison_focus == ("duration_seconds", "input_tokens", "llm_calls")


def test_running_scenario_applies_spec_rate_limits(tmp_path: Path) -> None:
    spec = load_spec(_write_spec(tmp_path / "benchmark-spec.json"))
    with RunningScenario(spec) as (server, base_url):
        assert base_url.startswith("http://127.0.0.1:")
        assert server.maybe_rate_limit("POST", "/tasks/task-1/comments") is True
        assert server.maybe_rate_limit("POST", "/tasks/task-1/comments") is False
        assert server.rate_limit_budget[("POST", "/tasks/task-1/comments")] == 0
        assert server.matching_task_ids(task_status="waiting-for-response") == [
            "task-1",
            "task-2",
        ]


def test_evaluate_required_comments_uses_spec_assertions(tmp_path: Path) -> None:
    spec = load_spec(_write_spec(tmp_path / "benchmark-spec.json"))
    with RunningScenario(spec) as (server, _):
        success, updated_count, results = evaluate_required_comments(spec, server)
        assert success is False
        assert updated_count == 0
        server.comments.setdefault("task-1", []).append(
            {"id": "c-2001", "text": "Benchmark follow-up - please respond.", "author": "task-cli"}
        )
        server.comments.setdefault("task-2", []).append(
            {"id": "c-2002", "text": "Benchmark follow-up - please respond.", "author": "task-cli"}
        )
        success, updated_count, results = evaluate_required_comments(spec, server)
        assert success is True
        assert updated_count == 2
        assert results[0]["required_count"] == 2


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


def test_build_report_and_markdown_summary(tmp_path: Path) -> None:
    spec = load_spec(_write_spec(tmp_path / "benchmark-spec.json"))
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
        assertion_results=[{"success": True}],
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
        assertion_results=[{"success": True}],
        final_message="done",
    )
    report = build_report(baseline, candidate, "gpt-4.1", spec)
    markdown = build_markdown_summary(report)

    assert report["comparison"]["input_token_delta"] == -400
    assert report["comparison"]["llm_call_delta"] == -3
    assert report["comparison"]["premium_request_delta"] == -2
    assert report["spec"]["id"] == "bulk-add-comment-retry"
    assert "baseline (`main`)" in markdown
    assert "candidate (`patch`)" in markdown
    assert "Comparison focus" in markdown
    assert "Bulk add comment with retry" in markdown
