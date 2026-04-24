"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from app.routers import health, tasks

app = FastAPI(
    title="Task API",
    description=(
        "Central Task API service for the skills-demo-catalog. "
        "Provides task management endpoints used by the task-api-helper skill and task_cli.py."
    ),
    version="1.0.0",
)

app.include_router(health.router)
app.include_router(tasks.router)
