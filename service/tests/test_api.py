"""Tests for the Task API FastAPI service."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.state import reset_stores


@pytest.fixture(autouse=True)
def fresh_state(monkeypatch: pytest.MonkeyPatch):
    """Re-seed the in-memory stores before every test."""
    monkeypatch.setenv("TASK_API_RATE_LIMIT_PROBABILITY", "0")
    reset_stores()
    yield


client = TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


# ---------------------------------------------------------------------------
# GET /tasks
# ---------------------------------------------------------------------------

def test_list_tasks_returns_all():
    response = client.get("/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
    assert len(tasks) >= 5


def test_list_tasks_status_filter():
    response = client.get("/tasks", params={"status": "waiting-for-response"})
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) >= 1
    assert all(t["status"] == "waiting-for-response" for t in tasks)


def test_list_tasks_status_filter_resolved():
    response = client.get("/tasks", params={"status": "resolved"})
    assert response.status_code == 200
    tasks = response.json()
    assert all(t["status"] == "resolved" for t in tasks)


def test_list_tasks_unknown_status_returns_empty():
    response = client.get("/tasks", params={"status": "nonexistent"})
    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_can_return_rate_limited(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TASK_API_RATE_LIMIT_PROBABILITY", "1")
    response = client.get("/tasks")
    assert response.status_code == 429
    assert response.json()["detail"] == "Rate limit exceeded. Retry the request."
    assert response.headers["Retry-After"] == "1"


# ---------------------------------------------------------------------------
# GET /tasks/{id}
# ---------------------------------------------------------------------------

def test_get_task_known():
    response = client.get("/tasks/task-1")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "task-1"
    assert isinstance(body["comments"], list)
    assert len(body["comments"]) >= 1


def test_get_task_includes_all_fields():
    response = client.get("/tasks/task-1")
    body = response.json()
    for field in ("id", "title", "status", "priority", "assignee", "comments"):
        assert field in body, f"Missing field: {field}"


def test_get_task_not_found():
    response = client.get("/tasks/does-not-exist")
    assert response.status_code == 404
    assert "detail" in response.json()


# ---------------------------------------------------------------------------
# POST /tasks/{id}/comments
# ---------------------------------------------------------------------------

def test_add_comment_success():
    response = client.post("/tasks/task-1/comments", json={"text": "hello world"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["comment_id"].startswith("c-")


def test_add_comment_persisted():
    client.post("/tasks/task-2/comments", json={"text": "first comment"})
    detail = client.get("/tasks/task-2").json()
    texts = [c["text"] for c in detail["comments"]]
    assert "first comment" in texts


def test_add_comment_empty_text():
    response = client.post("/tasks/task-1/comments", json={"text": "  "})
    assert response.status_code == 422


def test_add_comment_missing_text():
    response = client.post("/tasks/task-1/comments", json={})
    assert response.status_code == 422


def test_add_comment_task_not_found():
    response = client.post("/tasks/no-such-task/comments", json={"text": "hi"})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /tasks/bulk-comment  (demo/benchmark endpoint)
# ---------------------------------------------------------------------------

def test_bulk_comment_success():
    response = client.post(
        "/tasks/bulk-comment",
        json={"task_ids": ["task-1", "task-2", "task-3"], "text": "bulk reminder"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert set(body["updated"]) == {"task-1", "task-2", "task-3"}
    assert len(body["comment_ids"]) == 3


def test_bulk_comment_skips_unknown_tasks():
    response = client.post(
        "/tasks/bulk-comment",
        json={"task_ids": ["task-1", "does-not-exist"], "text": "ping"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "task-1" in body["updated"]
    assert "does-not-exist" not in body["updated"]


def test_bulk_comment_persisted():
    client.post(
        "/tasks/bulk-comment",
        json={"task_ids": ["task-4", "task-5"], "text": "bulk follow-up"},
    )
    for task_id in ("task-4", "task-5"):
        detail = client.get(f"/tasks/{task_id}").json()
        texts = [c["text"] for c in detail["comments"]]
        assert "bulk follow-up" in texts


def test_bulk_comment_empty_text():
    response = client.post(
        "/tasks/bulk-comment",
        json={"task_ids": ["task-1"], "text": ""},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Seed data sanity: multiple waiting-for-response tasks exist
# ---------------------------------------------------------------------------

def test_seed_has_multiple_waiting_tasks():
    response = client.get("/tasks", params={"status": "waiting-for-response"})
    tasks = response.json()
    assert len(tasks) >= 3, "Demo requires at least 3 waiting-for-response tasks"
