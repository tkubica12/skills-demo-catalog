"""Tasks router — list, get, add comment, and demo bulk-comment endpoint."""

from __future__ import annotations

import os
import random
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models import (
    AddCommentRequest,
    AddCommentResponse,
    BulkCommentRequest,
    BulkCommentResponse,
    Task,
    TaskDetail,
)
from app.state import get_comment_store, get_task_store

RATE_LIMIT_PROBABILITY = 0.30


def maybe_rate_limit() -> None:
    """Randomly return 429 to simulate a retry-worthy shared API."""
    probability = float(os.getenv("TASK_API_RATE_LIMIT_PROBABILITY", str(RATE_LIMIT_PROBABILITY)))
    if probability <= 0:
        return
    if random.random() < probability:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Retry the request.",
            headers={"Retry-After": "1"},
        )


router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(maybe_rate_limit)])


@router.get("", response_model=list[Task])
def list_tasks(
    status: Annotated[str | None, Query(description="Filter by task status")] = None,
    tasks: dict = Depends(get_task_store),
) -> list[Task]:
    """Return all tasks, optionally filtered by status."""
    result = list(tasks.values())
    if status is not None:
        result = [t for t in result if t["status"] == status]
    return [Task(**t) for t in result]


@router.get("/{task_id}", response_model=TaskDetail)
def get_task(
    task_id: str,
    tasks: dict = Depends(get_task_store),
    comments: dict = Depends(get_comment_store),
) -> TaskDetail:
    """Return a single task with its comment thread."""
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskDetail(**task, comments=comments.get(task_id, []))


@router.post("/{task_id}/comments", response_model=AddCommentResponse, status_code=200)
def add_comment(
    task_id: str,
    body: AddCommentRequest,
    tasks: dict = Depends(get_task_store),
    comments: dict = Depends(get_comment_store),
) -> AddCommentResponse:
    """Append a comment to a task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="text must not be empty")

    comment_id = f"c-{uuid.uuid4().hex[:8]}"
    comments.setdefault(task_id, []).append(
        {"id": comment_id, "text": text, "author": "task-cli"}
    )
    return AddCommentResponse(ok=True, comment_id=comment_id)


@router.post("/bulk-comment", response_model=BulkCommentResponse, status_code=200)
def bulk_add_comment(
    body: BulkCommentRequest,
    tasks: dict = Depends(get_task_store),
    comments: dict = Depends(get_comment_store),
) -> BulkCommentResponse:
    """Add the same comment to multiple tasks in a single request.

    This endpoint exists for demo/benchmark purposes only.
    The ``bulk-add-comment`` CLI command is NOT yet part of the baseline CLI.
    """
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="text must not be empty")

    updated: list[str] = []
    comment_ids: dict[str, str] = {}
    for task_id in body.task_ids:
        if task_id not in tasks:
            continue
        comment_id = f"c-{uuid.uuid4().hex[:8]}"
        comments.setdefault(task_id, []).append(
            {"id": comment_id, "text": text, "author": "task-cli"}
        )
        updated.append(task_id)
        comment_ids[task_id] = comment_id

    return BulkCommentResponse(ok=True, updated=updated, comment_ids=comment_ids)
