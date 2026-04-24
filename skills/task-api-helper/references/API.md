# Task API Reference

This document describes the baseline Task API contract used by `skills/task-api-helper/scripts/task_cli.py`.

## Base URL configuration

Set the API root in one of two ways:

- environment variable: `TASK_API_BASE_URL`
- command-line override: `python task_cli.py <command> --base-url https://tasks.internal.example.com`

Example:

```bash
export TASK_API_BASE_URL="https://tasks.internal.example.com"
python task_cli.py list-tasks --status open --project PAYMENTS
```

## Authentication

The API accepts a bearer token through the `Authorization` header.

```http
Authorization: Bearer <token>
```

You can supply the token with:

- `TASK_API_TOKEN`
- `--token <token>`

Unauthenticated requests may still work in lower environments if the service is configured for anonymous read access.

## Endpoints

### GET /health

Basic liveness probe.

```bash
curl -s "$TASK_API_BASE_URL/health"
```

Response:

```json
{
  "status": "ok"
}
```

### GET /tasks

Returns tasks visible to the caller.

Query parameters:

- `status`: `open`, `closed`, or `all`
- `project`: project identifier such as `PAYMENTS`
- `format`: optional response shape override; `ids` returns only task IDs

Example request:

```bash
curl -s -H "Authorization: Bearer $TASK_API_TOKEN" \
  "$TASK_API_BASE_URL/tasks?status=open&project=PAYMENTS"
```

Example response:

```json
[
  {
    "id": "task-1",
    "title": "Finalize sprint board",
    "status": "open",
    "project": "PAYMENTS"
  },
  {
    "id": "task-2",
    "title": "Publish release notes",
    "status": "closed",
    "project": "PAYMENTS"
  }
]
```

When `format=ids`:

```json
[
  "task-1",
  "task-2"
]
```

### GET /tasks/{id}

Returns one task and its comment thread.

Example request:

```bash
curl -s -H "Authorization: Bearer $TASK_API_TOKEN" \
  "$TASK_API_BASE_URL/tasks/task-1"
```

Example response:

```json
{
  "id": "task-1",
  "title": "Finalize sprint board",
  "status": "open",
  "project": "PAYMENTS",
  "comments": [
    {
      "id": "c-1001",
      "message": "Board moved to ready-for-review",
      "author": "release-bot"
    }
  ]
}
```

### POST /tasks/{id}/comments

Appends one comment to a task.

Request:

```http
POST /tasks/task-1/comments HTTP/1.1
Content-Type: application/json
Authorization: Bearer <token>

{
  "message": "Sprint closed — see board for details"
}
```

Response:

```json
{
  "ok": true,
  "comment_id": "c-a3c17f40"
}
```

### POST /tasks/bulk-comment

**Planned, not yet implemented in the production baseline.**

The catalog intentionally does not expose a `bulk-add-comment` CLI command until the centralized improvement process is complete. The benchmark harness in `tests/benchmark_bulk.py` uses a simulated mock implementation of this endpoint to estimate the upside before the API is standardized.

Proposed request shape:

```json
{
  "task_ids": ["task-1", "task-2", "task-3"],
  "message": "Sprint closed — see board for details"
}
```

## Error codes

| Status | Meaning | Typical cause |
|--------|---------|---------------|
| `400` | Bad request | Missing query parameter or malformed JSON body |
| `401` | Unauthorized | Missing or invalid bearer token |
| `404` | Not found | Unknown task ID or path |
| `409` | Conflict | Task state prevents the requested write |
| `429` | Too many requests | Client exceeded service rate limits |
| `500` | Internal server error | Unexpected service-side failure |
| `503` | Service unavailable | Dependency outage or maintenance window |
