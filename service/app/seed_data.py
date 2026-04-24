"""Seed data for the Task API demo service.

All data is kept in-memory and resets on restart.
Comments dictionaries are populated at startup from SEED_COMMENTS.
"""

from __future__ import annotations

from copy import deepcopy

SEED_TASKS: list[dict] = [
    {
        "id": "task-1",
        "title": "Waiting on customer confirmation — order #8821",
        "status": "waiting-for-response",
        "priority": "high",
        "assignee": "alice@example.com",
    },
    {
        "id": "task-2",
        "title": "Pending vendor reply for Q3 renewal",
        "status": "waiting-for-response",
        "priority": "medium",
        "assignee": "bob@example.com",
    },
    {
        "id": "task-3",
        "title": "Awaiting legal sign-off on NDA amendment",
        "status": "waiting-for-response",
        "priority": "high",
        "assignee": "carol@example.com",
    },
    {
        "id": "task-4",
        "title": "Customer reported login failure — needs repro steps",
        "status": "waiting-for-response",
        "priority": "low",
        "assignee": "dave@example.com",
    },
    {
        "id": "task-5",
        "title": "Infrastructure cost review — ops team response needed",
        "status": "waiting-for-response",
        "priority": "medium",
        "assignee": "eve@example.com",
    },
    {
        "id": "task-6",
        "title": "Archive completed onboarding flow for Acme Corp",
        "status": "resolved",
        "priority": "low",
        "assignee": "ops-bot@example.com",
    },
    {
        "id": "task-7",
        "title": "Deploy hotfix 2.3.1 to production",
        "status": "in-progress",
        "priority": "high",
        "assignee": "frank@example.com",
    },
    {
        "id": "task-8",
        "title": "Update API documentation for v3 endpoints",
        "status": "open",
        "priority": "medium",
        "assignee": "grace@example.com",
    },
]

SEED_COMMENTS: dict[str, list[dict]] = {
    "task-1": [
        {"id": "c-1001", "text": "Initial message sent to customer.", "author": "support-bot"},
        {"id": "c-1002", "text": "Follow-up sent after 48 hours.", "author": "alice@example.com"},
    ],
    "task-2": [
        {"id": "c-1003", "text": "Renewal quote sent to vendor.", "author": "renewal-bot"},
    ],
    "task-3": [
        {"id": "c-1004", "text": "NDA draft forwarded to legal on 2024-11-01.", "author": "carol@example.com"},
    ],
    "task-4": [
        {"id": "c-1005", "text": "Ticket opened; waiting for repro steps from customer.", "author": "support-bot"},
    ],
    "task-5": [],
    "task-6": [
        {"id": "c-1006", "text": "Onboarding completed and archived.", "author": "ops-bot@example.com"},
    ],
    "task-7": [
        {"id": "c-1007", "text": "Hotfix branch created.", "author": "frank@example.com"},
        {"id": "c-1008", "text": "Staging deploy successful.", "author": "ci-bot"},
    ],
    "task-8": [],
}


def make_task_store() -> dict[str, dict]:
    return {t["id"]: deepcopy(t) for t in SEED_TASKS}


def make_comment_store() -> dict[str, list[dict]]:
    return {k: deepcopy(v) for k, v in SEED_COMMENTS.items()}
