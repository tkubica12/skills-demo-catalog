from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
import zipfile
from collections import Counter
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from copilot import CopilotClient, SubprocessConfig
from copilot.generated.session_events import SessionEventType
from copilot.session import PermissionHandler


BENCHMARK_COMMENT = "Benchmark follow-up - please respond."
BENCHMARK_PROMPT = """
Use the installed task-api-helper skill that is already available in this repository.
Do not edit files, do not create issues, and do not propose improvements.
Your goal is to add this exact comment to every task waiting for response:

"Benchmark follow-up - please respond."

Important constraints:
- use the installed shared skill instead of building a local workaround
- if the API returns a transient rate limit, continue until the workflow succeeds
- stop once every waiting task has the comment
- when you are finished, reply with one short sentence only
""".strip()

SEED_TASKS = [
    {
        "id": "task-1",
        "title": "Waiting on customer confirmation",
        "status": "waiting-for-response",
    },
    {
        "id": "task-2",
        "title": "Pending vendor reply for Q3 renewal",
        "status": "waiting-for-response",
    },
    {
        "id": "task-3",
        "title": "Archive completed onboarding",
        "status": "resolved",
    },
]

SEED_COMMENTS = {
    "task-1": [
        {
            "id": "c-1001",
            "text": "Initial message sent to customer",
            "author": "support-bot",
        }
    ],
    "task-2": [
        {
            "id": "c-1002",
            "text": "Renewal quote sent to vendor",
            "author": "renewal-bot",
        }
    ],
    "task-3": [
        {
            "id": "c-1003",
            "text": "Onboarding completed and archived",
            "author": "ops-bot",
        }
    ],
}

RATE_LIMIT_BUDGET = {
    ("POST", "/tasks/task-1/comments"): 1,
    ("POST", "/tasks/task-2/comments"): 1,
    ("POST", "/tasks/bulk-comment"): 1,
}


@dataclass
class UsageTotals:
    input_tokens: int = 0
    output_tokens: int = 0
    api_duration_ms: int = 0
    llm_calls: int = 0
    premium_requests: int = 0
    tool_counts: Counter[str] = field(default_factory=Counter)


@dataclass
class RunResult:
    name: str
    success: bool
    duration_seconds: float
    updated_count: int
    input_tokens: int
    output_tokens: int
    llm_calls: int
    premium_requests: int
    api_duration_ms: int
    tool_counts: dict[str, int]
    task_api_requests: dict[str, int]
    rate_limit_responses: int
    final_message: str | None = None


class BenchmarkTaskApiServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
    ) -> None:
        super().__init__(server_address, handler_class)
        self.tasks = {task["id"]: dict(task) for task in deepcopy(SEED_TASKS)}
        self.comments = deepcopy(SEED_COMMENTS)
        self.request_counts: Counter[str] = Counter()
        self.rate_limit_budget = Counter(RATE_LIMIT_BUDGET)
        self.rate_limit_responses = 0

    def maybe_rate_limit(self, method: str, path: str) -> bool:
        key = (method, path)
        remaining = self.rate_limit_budget[key]
        if remaining <= 0:
            return False
        self.rate_limit_budget[key] -= 1
        self.rate_limit_responses += 1
        return True

    def comment_occurrences(self, text: str) -> int:
        return sum(
            1
            for comments in self.comments.values()
            for comment in comments
            if comment["text"] == text
        )


class BenchmarkTaskApiHandler(BaseHTTPRequestHandler):
    server_version = "TaskApiBenchmark/1.0"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    @property
    def benchmark_server(self) -> BenchmarkTaskApiServer:
        return self.server  # type: ignore[return-value]

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length) if length else b"{}"
        return json.loads(payload.decode("utf-8") or "{}")

    def _send_json(
        self,
        status_code: int,
        payload: object,
        headers: dict[str, str] | None = None,
    ) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _record_request(self, path: str) -> None:
        self.benchmark_server.request_counts[path] += 1

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        self._record_request(f"GET {parsed.path}")
        if parsed.path == "/health":
            self._send_json(200, {"status": "ok"})
            return

        if parsed.path == "/tasks":
            query = parse_qs(parsed.query)
            status = query.get("status", [None])[0]
            tasks = list(self.benchmark_server.tasks.values())
            if status is not None:
                tasks = [task for task in tasks if task["status"] == status]
            self._send_json(200, tasks)
            return

        if parsed.path.startswith("/tasks/"):
            task_id = parsed.path.rsplit("/", 1)[-1]
            task = self.benchmark_server.tasks.get(task_id)
            if not task:
                self._send_json(404, {"error": "Task not found"})
                return
            task_payload = dict(task)
            task_payload["comments"] = list(self.benchmark_server.comments.get(task_id, []))
            self._send_json(200, task_payload)
            return

        self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        self._record_request(f"POST {parsed.path}")
        if self.benchmark_server.maybe_rate_limit("POST", parsed.path):
            self._send_json(
                429,
                {"detail": "Rate limit exceeded. Retry the request."},
                headers={"Retry-After": "1"},
            )
            return

        if parsed.path == "/tasks/bulk-comment":
            payload = self._read_json()
            text = str(payload.get("text", "")).strip()
            task_ids = payload.get("task_ids") or [
                task["id"]
                for task in self.benchmark_server.tasks.values()
                if task["status"] == "waiting-for-response"
            ]
            if not text:
                self._send_json(400, {"error": "text is required"})
                return
            updated: list[str] = []
            for task_id in task_ids:
                if task_id not in self.benchmark_server.tasks:
                    continue
                comment_id = f"c-{uuid.uuid4().hex[:8]}"
                self.benchmark_server.comments.setdefault(task_id, []).append(
                    {"id": comment_id, "text": text, "author": "task-cli"}
                )
                updated.append(task_id)
            self._send_json(200, {"ok": True, "updated": updated})
            return

        parts = parsed.path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "tasks" and parts[2] == "comments":
            task_id = parts[1]
            if task_id not in self.benchmark_server.tasks:
                self._send_json(404, {"error": "Task not found"})
                return
            payload = self._read_json()
            text = str(payload.get("text", "")).strip()
            if not text:
                self._send_json(400, {"error": "text is required"})
                return
            comment_id = f"c-{uuid.uuid4().hex[:8]}"
            self.benchmark_server.comments.setdefault(task_id, []).append(
                {"id": comment_id, "text": text, "author": "task-cli"}
            )
            self._send_json(200, {"ok": True, "comment_id": comment_id})
            return

        self._send_json(404, {"error": "Not found"})


class RunningScenario:
    def __init__(self) -> None:
        self.server = BenchmarkTaskApiServer(("127.0.0.1", 0), BenchmarkTaskApiHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> tuple[BenchmarkTaskApiServer, str]:
        self.thread.start()
        host, port = self.server.server_address
        return self.server, f"http://{host}:{port}"

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def extract_skill_from_git_ref(repo_root: Path, git_ref: str, destination: Path) -> None:
    archive_path = destination.parent / f"{destination.name}.zip"
    subprocess.run(
        [
            "git",
            "archive",
            "--format=zip",
            f"--output={archive_path}",
            git_ref,
            "skills/task-api-helper",
        ],
        cwd=repo_root,
        check=True,
    )
    extract_root = destination.parent / f"{destination.name}-extract"
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(extract_root)
    source_dir = extract_root / "skills" / "task-api-helper"
    shutil.copytree(source_dir, destination, dirs_exist_ok=True)
    shutil.rmtree(extract_root)
    archive_path.unlink(missing_ok=True)


def prepare_workspace(
    repo_root: Path,
    destination_root: Path,
    workspace_name: str,
    task_api_url: str,
    baseline_ref: str | None = None,
) -> Path:
    workspace = destination_root / workspace_name
    skill_path = workspace / ".agents" / "skills" / "task-api-helper"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    if baseline_ref:
        extract_skill_from_git_ref(repo_root, baseline_ref, skill_path)
    else:
        shutil.copytree(
            repo_root / "skills" / "task-api-helper",
            skill_path,
            dirs_exist_ok=True,
        )
    subprocess.run(["git", "init", "--quiet"], cwd=workspace, check=True)
    (workspace / "README.txt").write_text(
        "Benchmark workspace for task-api-helper skill comparisons.\n",
        encoding="utf-8",
    )
    (skill_path / ".env").write_text(f"TASK_API_URL={task_api_url}\n", encoding="utf-8")
    return workspace


async def run_agent_scenario(
    name: str,
    repo_root: Path,
    workspace_root: Path,
    baseline_ref: str | None,
    model: str,
    prompt: str,
    timeout_seconds: int,
    github_token: str | None,
) -> RunResult:
    with RunningScenario() as (server, task_api_url):
        workspace = prepare_workspace(
            repo_root=repo_root,
            destination_root=workspace_root,
            workspace_name=name,
            task_api_url=task_api_url,
            baseline_ref=baseline_ref,
        )

        usage = UsageTotals()
        final_message: str | None = None
        idle = asyncio.Event()
        env = os.environ.copy()
        env["COPILOT_HOME"] = str(workspace / ".copilot-home")
        config = SubprocessConfig(
            cwd=str(workspace),
            env=env,
            github_token=github_token,
        )

        started = time.perf_counter()
        async with CopilotClient(config) as client:
            async with await client.create_session(
                session_id=f"benchmark-{name}",
                model=model,
                streaming=True,
                on_permission_request=PermissionHandler.approve_all,
            ) as session:

                def on_event(event: Any) -> None:
                    nonlocal final_message
                    if event.type == SessionEventType.ASSISTANT_USAGE:
                        usage.llm_calls += 1
                        usage.input_tokens += int(event.data.input_tokens or 0)
                        usage.output_tokens += int(event.data.output_tokens or 0)
                        usage.api_duration_ms += int(event.data.duration or 0)
                    elif event.type == SessionEventType.TOOL_EXECUTION_START:
                        usage.tool_counts[str(event.data.tool_name)] += 1
                    elif event.type == SessionEventType.ASSISTANT_MESSAGE:
                        final_message = str(event.data.content or "").strip()
                    elif event.type == SessionEventType.SESSION_IDLE:
                        idle.set()
                    elif event.type == SessionEventType.SESSION_SHUTDOWN:
                        usage.premium_requests = int(event.data.total_premium_requests or 0)

                session.on(on_event)
                await session.send(prompt)
                await asyncio.wait_for(idle.wait(), timeout=timeout_seconds)

        duration_seconds = time.perf_counter() - started
        updated_count = server.comment_occurrences(BENCHMARK_COMMENT)
        success = updated_count == 2

        return RunResult(
            name=name,
            success=success,
            duration_seconds=duration_seconds,
            updated_count=updated_count,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            llm_calls=usage.llm_calls,
            premium_requests=usage.premium_requests,
            api_duration_ms=usage.api_duration_ms,
            tool_counts=dict(sorted(usage.tool_counts.items())),
            task_api_requests=dict(sorted(server.request_counts.items())),
            rate_limit_responses=server.rate_limit_responses,
            final_message=final_message,
        )


def build_report(baseline: RunResult, candidate: RunResult, model: str) -> dict[str, Any]:
    return {
        "model": model,
        "benchmark_comment": BENCHMARK_COMMENT,
        "baseline": asdict(baseline),
        "candidate": asdict(candidate),
        "comparison": {
            "duration_delta_seconds": round(
                candidate.duration_seconds - baseline.duration_seconds,
                3,
            ),
            "input_token_delta": candidate.input_tokens - baseline.input_tokens,
            "output_token_delta": candidate.output_tokens - baseline.output_tokens,
            "llm_call_delta": candidate.llm_calls - baseline.llm_calls,
            "premium_request_delta": candidate.premium_requests - baseline.premium_requests,
            "request_delta": sum(candidate.task_api_requests.values())
            - sum(baseline.task_api_requests.values()),
        },
    }


def build_markdown_summary(report: dict[str, Any]) -> str:
    baseline = report["baseline"]
    candidate = report["candidate"]
    comparison = report["comparison"]
    rows = [
        "| Variant | Success | Updated | Duration (s) | Input tokens | Output tokens | LLM calls | Premium requests | API duration (ms) | API requests | 429s |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        (
            f"| baseline (`main`) | {baseline['success']} | {baseline['updated_count']} | "
            f"{baseline['duration_seconds']:.3f} | {baseline['input_tokens']} | "
            f"{baseline['output_tokens']} | {baseline['llm_calls']} | {baseline['premium_requests']} | "
            f"{baseline['api_duration_ms']} | {sum(baseline['task_api_requests'].values())} | "
            f"{baseline['rate_limit_responses']} |"
        ),
        (
            f"| candidate (`patch`) | {candidate['success']} | {candidate['updated_count']} | "
            f"{candidate['duration_seconds']:.3f} | {candidate['input_tokens']} | "
            f"{candidate['output_tokens']} | {candidate['llm_calls']} | {candidate['premium_requests']} | "
            f"{candidate['api_duration_ms']} | {sum(candidate['task_api_requests'].values())} | "
            f"{candidate['rate_limit_responses']} |"
        ),
    ]
    bullets = [
        f"- Model: `{report['model']}`",
        f"- Duration delta (candidate - baseline): `{comparison['duration_delta_seconds']}` s",
        f"- Input token delta: `{comparison['input_token_delta']}`",
        f"- Output token delta: `{comparison['output_token_delta']}`",
        f"- LLM call delta: `{comparison['llm_call_delta']}`",
        f"- Premium request delta: `{comparison['premium_request_delta']}`",
        f"- Task API request delta: `{comparison['request_delta']}`",
    ]
    return "\n".join(["## Agent benchmark summary", "", *rows, "", *bullets, ""])


async def main_async(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    workspace_root = Path(args.workspace_root).resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)
    github_token = (
        args.github_token
        or os.getenv("COPILOT_GITHUB_TOKEN")
        or os.getenv("GH_TOKEN")
        or os.getenv("GITHUB_TOKEN")
    )
    baseline = await run_agent_scenario(
        name="baseline",
        repo_root=repo_root,
        workspace_root=workspace_root,
        baseline_ref=args.baseline_ref,
        model=args.model,
        prompt=args.prompt,
        timeout_seconds=args.timeout_seconds,
        github_token=github_token,
    )
    candidate = await run_agent_scenario(
        name="candidate",
        repo_root=repo_root,
        workspace_root=workspace_root,
        baseline_ref=None,
        model=args.model,
        prompt=args.prompt,
        timeout_seconds=args.timeout_seconds,
        github_token=github_token,
    )
    report = build_report(baseline, candidate, args.model)
    markdown = build_markdown_summary(report)
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.output_markdown:
        Path(args.output_markdown).write_text(markdown, encoding="utf-8")
    print(markdown)
    return 0 if baseline.success and candidate.success else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a Copilot SDK skill benchmark.")
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        help="Repository root containing the task-api-helper skill.",
    )
    parser.add_argument(
        "--workspace-root",
        default=Path(tempfile.gettempdir()) / "task-api-skill-benchmark",
        help="Directory used for temporary benchmark workspaces.",
    )
    parser.add_argument(
        "--baseline-ref",
        default="origin/main",
        help="Git ref used for the baseline skill snapshot.",
    )
    parser.add_argument(
        "--model",
        default="gpt-4.1",
        help="Copilot model identifier for both runs.",
    )
    parser.add_argument(
        "--prompt",
        default=BENCHMARK_PROMPT,
        help="Prompt used for the benchmark run.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=300,
        help="Maximum time to wait for each benchmark run.",
    )
    parser.add_argument(
        "--github-token",
        default=None,
        help="Override the Copilot authentication token.",
    )
    parser.add_argument("--output-json", default=None, help="Optional JSON report path.")
    parser.add_argument(
        "--output-markdown",
        default=None,
        help="Optional Markdown summary path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(main_async(parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
