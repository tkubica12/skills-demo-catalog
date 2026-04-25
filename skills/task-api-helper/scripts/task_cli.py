#!/usr/bin/env python3
"""Command-line wrapper for the shared Task API REST service."""

from __future__ import annotations

import argparse
import json
import os
import socket
import ssl
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib import error, parse, request

DEFAULT_TIMEOUT_SECONDS = 30
TRANSIENT_RETRY_DELAYS_SECONDS = (0.25, 0.5, 1.0)
RATE_LIMIT_RETRY_DELAYS_SECONDS = (2, 4, 8, 16, 32)
SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_DOTENV_PATH = SKILL_ROOT / ".env"


def build_parser() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--api-url",
        help="Override TASK_API_URL for this command.",
    )
    shared.add_argument("--token", help="Override TASK_API_TOKEN for this command.")

    parser = argparse.ArgumentParser(
        description="Interact with the shared Task API service."
    )
    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser(
        "list-tasks",
        parents=[shared],
        help="List tasks from the Task API.",
    )
    list_parser.add_argument(
        "--status",
        default=None,
        help="Filter tasks by status, for example waiting-for-response.",
    )
    list_parser.set_defaults(handler=handle_list_tasks)

    get_parser = subparsers.add_parser(
        "get-task",
        parents=[shared],
        help="Fetch a single task and its comment thread.",
    )
    get_parser.add_argument("task_id", help="Task identifier, for example task-123.")
    get_parser.set_defaults(handler=handle_get_task)

    comment_parser = subparsers.add_parser(
        "add-comment",
        parents=[shared],
        help="Append a comment to a task.",
    )
    comment_parser.add_argument("task_id", help="Task identifier to update.")
    comment_parser.add_argument("text", help="Comment text to append to the task.")
    comment_parser.set_defaults(handler=handle_add_comment)

    bulk_comment_parser = subparsers.add_parser(
        "bulk-add-comment",
        parents=[shared],
        help="Append a comment to multiple tasks with automatic 429 retry.",
    )
    bulk_target = bulk_comment_parser.add_mutually_exclusive_group(required=True)
    bulk_target.add_argument(
        "--status",
        default=None,
        help="Fetch all tasks matching this status and comment on each.",
    )
    bulk_target.add_argument(
        "--task-ids",
        nargs="+",
        metavar="TASK_ID",
        default=None,
        help="Explicit list of task IDs to comment on.",
    )
    bulk_comment_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview affected tasks without posting any comments.",
    )
    bulk_comment_parser.add_argument("text", help="Comment text to append to each task.")
    bulk_comment_parser.set_defaults(handler=handle_bulk_add_comment)

    return parser


@lru_cache(maxsize=1)
def load_skill_dotenv() -> dict[str, str]:
    if not SKILL_DOTENV_PATH.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in SKILL_DOTENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def resolve_config_value(cli_value: str | None, env_name: str) -> str:
    if cli_value:
        return cli_value.strip()

    dotenv_value = load_skill_dotenv().get(env_name, "").strip()
    if dotenv_value:
        return dotenv_value

    return os.getenv(env_name, "").strip()


def resolve_base_url(args: argparse.Namespace) -> str:
    base_url = resolve_config_value(getattr(args, "api_url", None), "TASK_API_URL")
    if not base_url:
        raise ValueError(
            "TASK_API_URL is not set. Pass --api-url, configure .env in the installed "
            "skill folder, or export TASK_API_URL."
        )
    return base_url.rstrip("/")


def resolve_token(args: argparse.Namespace) -> str:
    return resolve_config_value(getattr(args, "token", None), "TASK_API_TOKEN")


def pretty_print(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def decode_response(response: Any) -> Any:
    body = response.read().decode("utf-8")
    if not body:
        return None
    return json.loads(body)


def is_transient_transport_error(exc: error.URLError) -> bool:
    reason = exc.reason
    if isinstance(
        reason,
        (
            ssl.SSLError,
            socket.timeout,
            TimeoutError,
            ConnectionResetError,
            ConnectionAbortedError,
        ),
    ):
        return True

    message = str(reason).lower()
    return any(
        fragment in message
        for fragment in (
            "unexpected eof while reading",
            "eof occurred in violation of protocol",
            "connection reset",
            "timed out",
        )
    )


def request_json(
    args: argparse.Namespace,
    method: str,
    path: str,
    query: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> Any:
    base_url = resolve_base_url(args)
    cleaned_query = {
        key: value
        for key, value in (query or {}).items()
        if value is not None and value != ""
    }
    url = f"{base_url}{path}"
    if cleaned_query:
        url = f"{url}?{parse.urlencode(cleaned_query)}"

    headers = {"Accept": "application/json"}
    token = resolve_token(args)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    http_request = request.Request(url, data=data, headers=headers, method=method)
    last_url_error: error.URLError | None = None
    for attempt_index in range(len(TRANSIENT_RETRY_DELAYS_SECONDS) + 1):
        try:
            with request.urlopen(http_request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
                return decode_response(response)
        except error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            try:
                parsed_body = json.loads(message) if message else {"error": exc.reason}
                formatted_body = json.dumps(parsed_body, indent=2, sort_keys=True)
            except json.JSONDecodeError:
                formatted_body = message or str(exc.reason)
            print(f"HTTP {exc.code}: {formatted_body}", file=sys.stderr)
            raise SystemExit(1) from exc
        except error.URLError as exc:
            last_url_error = exc
            if (
                attempt_index < len(TRANSIENT_RETRY_DELAYS_SECONDS)
                and is_transient_transport_error(exc)
            ):
                time.sleep(TRANSIENT_RETRY_DELAYS_SECONDS[attempt_index])
                continue
            break

    message = f"Request failed: {last_url_error.reason}" if last_url_error else "Request failed."
    if last_url_error and is_transient_transport_error(last_url_error):
        attempts = len(TRANSIENT_RETRY_DELAYS_SECONDS) + 1
        message = f"Request failed after {attempts} attempts: {last_url_error.reason}"
    print(message, file=sys.stderr)
    raise SystemExit(1) from last_url_error


def handle_list_tasks(args: argparse.Namespace) -> int:
    query: dict[str, Any] = {}
    if args.status is not None:
        query["status"] = args.status
    response = request_json(args, "GET", "/tasks", query=query or None)
    pretty_print(response)
    return 0


def handle_get_task(args: argparse.Namespace) -> int:
    response = request_json(args, "GET", f"/tasks/{parse.quote(args.task_id)}")
    pretty_print(response)
    return 0


def handle_add_comment(args: argparse.Namespace) -> int:
    response = request_json(
        args,
        "POST",
        f"/tasks/{parse.quote(args.task_id)}/comments",
        payload={"text": args.text},
    )
    pretty_print(response)
    return 0


def _post_comment_with_rate_limit_retry(
    args: argparse.Namespace,
    task_id: str,
    text: str,
) -> dict[str, Any] | None:
    """POST a comment to one task, retrying up to 5 times on HTTP 429.

    Returns the decoded response dict on success, or None on failure (after
    logging the error to stderr).
    """
    base_url = resolve_base_url(args)
    url = f"{base_url}/tasks/{parse.quote(task_id)}/comments"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    token = resolve_token(args)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps({"text": text}).encode("utf-8")

    max_retries = len(RATE_LIMIT_RETRY_DELAYS_SECONDS)
    for attempt in range(max_retries + 1):
        http_request = request.Request(url, data=data, headers=headers, method="POST")
        try:
            with request.urlopen(http_request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
                return decode_response(response)
        except error.HTTPError as exc:
            if exc.code == 429 and attempt < max_retries:
                delay = RATE_LIMIT_RETRY_DELAYS_SECONDS[attempt]
                print(
                    f"  [rate limited] retrying {task_id} in {delay}s"
                    f" (attempt {attempt + 1}/{max_retries})...",
                    flush=True,
                )
                time.sleep(delay)
                continue
            message = exc.read().decode("utf-8", errors="replace")
            try:
                parsed_body = json.loads(message) if message else {"error": exc.reason}
                formatted_body = json.dumps(parsed_body, indent=2, sort_keys=True)
            except json.JSONDecodeError:
                formatted_body = message or str(exc.reason)
            print(f"HTTP {exc.code}: {formatted_body}", file=sys.stderr)
            return None

    return None


def handle_bulk_add_comment(args: argparse.Namespace) -> int:
    if args.status is not None:
        print(f"Fetching tasks with status '{args.status}'...", flush=True)
        tasks = request_json(args, "GET", "/tasks", query={"status": args.status})
        task_ids = [t["id"] for t in tasks]
    else:
        task_ids = list(args.task_ids)

    if not task_ids:
        print("No tasks found.", flush=True)
        return 0

    id_list = ", ".join(task_ids)
    print(f"Found {len(task_ids)} task(s): {id_list}", flush=True)

    if args.dry_run:
        print("Dry-run mode: no comments posted.", flush=True)
        return 0

    failures = 0
    for task_id in task_ids:
        print(f"Commenting on {task_id}...", flush=True)
        result = _post_comment_with_rate_limit_retry(args, task_id, args.text)
        if result is None:
            failures += 1
        else:
            comment_id = result.get("comment_id", "?")
            print(f"  \u2713 {task_id} \u2192 comment {comment_id}", flush=True)

    total = len(task_ids)
    succeeded = total - failures
    print(f"\nDone. {succeeded}/{total} task(s) updated.", flush=True)
    return 0 if failures == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 1
    try:
        return int(args.handler(args))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
