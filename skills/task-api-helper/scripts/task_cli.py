#!/usr/bin/env python3
"""Command-line wrapper for the shared Task API REST service."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib import error, parse, request

DEFAULT_TIMEOUT_SECONDS = 30


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

    bulk_parser = subparsers.add_parser(
        "bulk-add-comment",
        parents=[shared],
        help="Append the same comment to multiple tasks in a single session.",
    )
    target_group = bulk_parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        "--ids",
        nargs="+",
        metavar="ID",
        help="One or more task identifiers to comment on.",
    )
    target_group.add_argument(
        "--status",
        help="Comment on all tasks with this status, for example waiting-for-response.",
    )
    bulk_parser.add_argument(
        "--comment",
        required=True,
        help="Comment text to append to every resolved task.",
    )
    bulk_parser.set_defaults(handler=handle_bulk_add_comment)

    return parser


def resolve_base_url(args: argparse.Namespace) -> str:
    base_url = (getattr(args, "api_url", None) or os.getenv("TASK_API_URL", "")).strip()
    if not base_url:
        raise ValueError("TASK_API_URL is not set. Pass --api-url or export TASK_API_URL.")
    return base_url.rstrip("/")


def resolve_token(args: argparse.Namespace) -> str:
    return (getattr(args, "token", None) or os.getenv("TASK_API_TOKEN", "")).strip()


def pretty_print(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def decode_response(response: Any) -> Any:
    body = response.read().decode("utf-8")
    if not body:
        return None
    return json.loads(body)


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
        print(f"Request failed: {exc.reason}", file=sys.stderr)
        raise SystemExit(1) from exc


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


def handle_bulk_add_comment(args: argparse.Namespace) -> int:
    if args.status is not None:
        tasks = request_json(args, "GET", "/tasks", query={"status": args.status})
        task_ids = [t["id"] for t in tasks]
    else:
        task_ids = args.ids
 
    if not task_ids:
        print("No tasks matched the request.", file=sys.stderr)
        return 3

    response = request_json(
        args,
        "POST",
        "/tasks/bulk-comment",
        payload={"task_ids": task_ids, "text": args.comment},
    )
    pretty_print(response)
    return 0


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
