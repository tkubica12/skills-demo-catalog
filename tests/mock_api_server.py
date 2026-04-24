#!/usr/bin/env python3
"""Minimal mock Task API server for local tests and CI."""

from __future__ import annotations

import argparse
import json
import uuid
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

TASKS = [
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

COMMENTS = {
    "task-1": [
        {"id": "c-1001", "text": "Initial message sent to customer", "author": "support-bot"}
    ],
    "task-2": [
        {"id": "c-1002", "text": "Renewal quote sent to vendor", "author": "renewal-bot"}
    ],
    "task-3": [
        {"id": "c-1003", "text": "Onboarding completed and archived", "author": "ops-bot"}
    ],
}


class TaskApiHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_class: type[BaseHTTPRequestHandler]):
        super().__init__(server_address, handler_class)
        self.tasks = {task["id"]: dict(task) for task in deepcopy(TASKS)}
        self.comments = deepcopy(COMMENTS)


class TaskApiHandler(BaseHTTPRequestHandler):
    server_version = "TaskApiMock/1.0"

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length) if length else b"{}"
        return json.loads(payload.decode("utf-8") or "{}")

    def _send_json(self, status_code: int, payload: object) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"status": "ok"})
            return

        if parsed.path == "/tasks":
            query = parse_qs(parsed.query)
            status = query.get("status", [None])[0]

            tasks = list(self.server.tasks.values())
            if status is not None:
                tasks = [task for task in tasks if task["status"] == status]

            self._send_json(200, tasks)
            return

        if parsed.path.startswith("/tasks/"):
            task_id = parsed.path.rsplit("/", 1)[-1]
            task = self.server.tasks.get(task_id)
            if not task:
                self._send_json(404, {"error": "Task not found"})
                return

            task_payload = dict(task)
            task_payload["comments"] = list(self.server.comments.get(task_id, []))
            self._send_json(200, task_payload)
            return

        self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/tasks/bulk-comment":
            payload = self._read_json()
            task_ids = payload.get("task_ids") or list(self.server.tasks.keys())
            self._send_json(
                200,
                {
                    "ok": True,
                    "updated": task_ids,
                    "simulated": True,
                },
            )
            return

        parts = parsed.path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "tasks" and parts[2] == "comments":
            task_id = parts[1]
            if task_id not in self.server.tasks:
                self._send_json(404, {"error": "Task not found"})
                return

            payload = self._read_json()
            text = str(payload.get("text", "")).strip()
            if not text:
                self._send_json(400, {"error": "text is required"})
                return

            comment_id = f"c-{uuid.uuid4().hex[:8]}"
            self.server.comments.setdefault(task_id, []).append(
                {"id": comment_id, "text": text, "author": "task-cli"}
            )
            self._send_json(200, {"ok": True, "comment_id": comment_id})
            return

        self._send_json(404, {"error": "Not found"})


def create_server(port: int = 18080) -> TaskApiHTTPServer:
    return TaskApiHTTPServer(("127.0.0.1", port), TaskApiHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the mock Task API server.")
    parser.add_argument("--port", type=int, default=18080, help="Port to listen on.")
    args = parser.parse_args()

    server = create_server(args.port)
    print(f"Mock Task API server listening on http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
