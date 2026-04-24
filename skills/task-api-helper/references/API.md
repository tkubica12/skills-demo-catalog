# Task API Reference

This document describes the baseline Task API contract used by `skills/task-api-helper/scripts/task_cli.py`.

## Base URL configuration

Set the API root in one of two ways:

- environment variable: `TASK_API_URL`
- command-line override: `python task_cli.py <command> --api-url https://tasks.internal.example.com`

Example:

```bash
export TASK_API_URL="https://tasks.internal.example.com"
python task_cli.py list-tasks --status waiting-for-response
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
curl -s "$TASK_API_URL/health"
```

Response:

```json
{
  "status": "ok"
}
```

### GET /tasks

Returns tasks visible to the caller. Optionally filter by status.

Query parameters:

- `status`: any status string the API recognizes, for example `waiting-for-response` or `resolved`. Omit to return all tasks.

Example request:

```bash
curl -s -H "Authorization: Bearer $TASK_API_TOKEN" \
  "$TASK_API_URL/tasks?status=waiting-for-response"
```

Example response:

```json
[
  {
    "id": "task-1",
    "title": "Waiting on customer confirmation",
    "status": "waiting-for-response"
  },
  {
    "id": "task-2",
    "title": "Pending vendor reply for Q3 renewal",
    "status": "waiting-for-response"
  }
]
```

### GET /tasks/{id}

Returns one task and its comment thread.

Example request:

```bash
curl -s -H "Authorization: Bearer $TASK_API_TOKEN" \
  "$TASK_API_URL/tasks/task-1"
```

Example response:

```json
{
  "id": "task-1",
  "title": "Waiting on customer confirmation",
  "status": "waiting-for-response",
  "comments": [
    {
      "id": "c-1001",
      "text": "Initial message sent to customer",
      "author": "support-bot"
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
  "text": "Reminder: please respond so we can close this task"
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

Add the same comment to multiple tasks in a single request. The
`bulk-add-comment` CLI command resolves the target task IDs and then calls this
endpoint once.

Request:

```json
{
  "task_ids": ["task-1", "task-2"],
  "text": "Reminder: please respond so we can close this task"
}
```

Response:

```json
{
  "ok": true,
  "updated": ["task-1", "task-2"],
  "comment_ids": {
    "task-1": "c-a3c17f40",
    "task-2": "c-9f0b1d25"
  }
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
