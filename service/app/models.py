"""Pydantic models for the Task API service."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Comment(BaseModel):
    id: str
    text: str
    author: str


class Task(BaseModel):
    id: str
    title: str
    status: str
    priority: str
    assignee: str


class TaskDetail(Task):
    comments: list[Comment]


class AddCommentRequest(BaseModel):
    text: str


class AddCommentResponse(BaseModel):
    ok: bool
    comment_id: str


class BulkCommentRequest(BaseModel):
    task_ids: list[str]
    text: str


class BulkCommentResponse(BaseModel):
    ok: bool
    updated: list[str]
    comment_ids: dict[str, str]


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
