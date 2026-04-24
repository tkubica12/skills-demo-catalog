# Task API Service

A real FastAPI backend for the `task-api-helper` skill demo. It serves in-memory, seed-seeded task data and exposes the same contract used by `task_cli.py`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health check |
| `GET` | `/tasks` | List tasks; optional `?status=` filter |
| `GET` | `/tasks/{id}` | Get a single task with comments |
| `POST` | `/tasks/{id}/comments` | Add a comment `{"text": "..."}` |
| `POST` | `/tasks/bulk-comment` | Add one comment to many tasks (demo/benchmark only) |

Interactive docs are available at `/docs` (Swagger UI) and `/redoc`.

## Local development

```bash
# From the service/ directory
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8080
```

Then point the CLI at it:

```bash
export TASK_API_URL=http://localhost:8080
python ../skills/task-api-helper/scripts/task_cli.py list-tasks
python ../skills/task-api-helper/scripts/task_cli.py list-tasks --status waiting-for-response
python ../skills/task-api-helper/scripts/task_cli.py get-task task-1
python ../skills/task-api-helper/scripts/task_cli.py add-comment task-1 "Following up"
```

## Run tests

```bash
cd service/
pytest tests/ -v
```

## Docker

**Build:**

```bash
docker build -t task-api-service:latest .
```

**Run:**

```bash
docker run --rm -p 8080:8080 task-api-service:latest
```

**Test the running container:**

```bash
curl http://localhost:8080/health
curl "http://localhost:8080/tasks?status=waiting-for-response"
curl http://localhost:8080/tasks/task-1
curl -X POST http://localhost:8080/tasks/task-1/comments \
     -H "Content-Type: application/json" \
     -d '{"text": "Following up"}'
```

## Seed data

Eight tasks are seeded on startup (five `waiting-for-response`, one `resolved`, one `in-progress`, one `open`). State is in-memory and resets on each container restart — no database required for the demo.

## Planned next steps

- Publish image to GHCR (`ghcr.io/tkubica12/skills-demo-catalog/task-api:latest`)
- Deploy to Azure Container Apps
