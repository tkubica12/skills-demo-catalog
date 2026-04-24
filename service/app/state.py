"""Application state — in-memory task and comment stores.

Data is seeded from seed_data.py at startup and reset on each container restart.
Dependencies are injected via FastAPI's DI system so tests can override them easily.
"""

from __future__ import annotations

from app.seed_data import make_comment_store, make_task_store

# Module-level singletons; populated once at import time.
_task_store: dict[str, dict] = make_task_store()
_comment_store: dict[str, list[dict]] = make_comment_store()


def get_task_store() -> dict[str, dict]:
    return _task_store


def get_comment_store() -> dict[str, list[dict]]:
    return _comment_store


def reset_stores() -> None:
    """Re-seed both stores from scratch (used in tests)."""
    global _task_store, _comment_store
    _task_store = make_task_store()
    _comment_store = make_comment_store()
