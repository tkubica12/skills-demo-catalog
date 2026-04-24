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

For demo purposes, requests under `/tasks` have a 30% chance of returning
`429 Too Many Requests` with `Retry-After: 1`. This is intentional so agents can
discover that retry handling is a useful next enhancement for the shared skill.

## Local development

Requires [uv](https://docs.astral.sh/uv/). Install it once with:

```sh
# Linux / macOS / WSL
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then from the `service/` directory:

```sh
uv sync                                              # install all deps into .venv
uv run uvicorn app.main:app --reload --port 8080    # start dev server with auto-reload
```

Then point the CLI at it:

```sh
# Linux / macOS
export TASK_API_URL=http://localhost:8080
python ../skills/task-api-helper/scripts/task_cli.py list-tasks
python ../skills/task-api-helper/scripts/task_cli.py list-tasks --status waiting-for-response
python ../skills/task-api-helper/scripts/task_cli.py get-task task-1
python ../skills/task-api-helper/scripts/task_cli.py add-comment task-1 "Following up"

# Windows (PowerShell)
$env:TASK_API_URL = "http://localhost:8080"
python ..\skills\task-api-helper\scripts\task_cli.py list-tasks
```

## Run tests

```sh
cd service/
uv run pytest tests/ -v
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

## Published image

```
ghcr.io/tkubica12/skills-demo-catalog/task-api:<tag>
```

The CI/CD pipeline in `.github/workflows/service-publish.yml` builds and pushes this image automatically on every push to `main` and on `v*.*.*` tags.
Azure Container Apps deployment is handled by `.github/workflows/service-deploy.yml`.
See the top-level [README](../README.md) for required secrets, variables, and the public endpoint format.
