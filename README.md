# Skills Demo Catalog — task-api-helper

This repository is a central GitHub Copilot skill catalog for the `task-api-helper` skill. It packages the skill definition, the companion `task_cli.py` wrapper, reference docs, tests, and automation used to evolve the shared Task API experience in a controlled way.

## What is task-api-helper?

`task-api-helper` is the cataloged skill for teams that use the shared **Task API** REST service for project task management. The skill documents:

- the API contract for listing tasks, reading a task, and adding comments
- the supported `task_cli.py` commands that wrap the REST API
- the improvement path for proposing new commands upstream

The important baseline rule is simple: the CLI is centrally versioned and intentionally small. It supports `list-tasks`, `get-task`, and `add-comment` today.

## Installing the skill with `gh skill install`

```bash
gh skill install tkubica12/skills-demo-catalog task-api-helper
```

After installation, invoke it from Copilot Chat in the appropriate client for your workflow.

## CLI commands

The baseline CLI lives at `skills/task-api-helper/scripts/task_cli.py`.

```sh
python skills/task-api-helper/scripts/task_cli.py list-tasks [--status <status>] [--api-url <url>]
python skills/task-api-helper/scripts/task_cli.py get-task TASK_ID [--api-url <url>]
python skills/task-api-helper/scripts/task_cli.py add-comment TASK_ID "Your comment text" [--api-url <url>]
```

Environment variables:

```sh
# Linux / macOS
export TASK_API_URL="https://tasks.internal.example.com"
export TASK_API_TOKEN="<optional-bearer-token>"

# Windows (PowerShell)
$env:TASK_API_URL = "https://tasks.internal.example.com"
$env:TASK_API_TOKEN = "<optional-bearer-token>"
```

## Known limitation — no bulk-add-comment

The baseline CLI does **not** expose `bulk-add-comment`. Teams that need to comment on many tasks currently use a loop such as:

```sh
# Linux / macOS
for id in $(python skills/task-api-helper/scripts/task_cli.py list-tasks --status waiting-for-response | python -c "import sys,json; [print(t['id']) for t in json.load(sys.stdin)]"); do
  python skills/task-api-helper/scripts/task_cli.py add-comment "$id" "Reminder: please respond so we can close this task"
done
```

```powershell
# Windows (PowerShell)
$ids = python skills/task-api-helper/scripts/task_cli.py list-tasks --status waiting-for-response |
       python -c "import sys,json; [print(t['id']) for t in json.load(sys.stdin)]"
foreach ($id in $ids) {
  python skills/task-api-helper/scripts/task_cli.py add-comment $id "Reminder: please respond so we can close this task"
}
```

That workaround is acceptable for small batches but is slow and brittle in CI because it performs one HTTP round-trip per task.

## Project-side local experiment workflow

Consumer teams should prove a proposed improvement locally before asking the central catalog to take it on:

1. Fork `task_cli.py` locally in your project workspace.
2. Implement the missing behavior in that local fork only.
3. Measure the baseline and the experiment, typically with `tests/benchmark_bulk.py`.
4. Capture the exact command syntax you want to standardize.
5. Restore your fork back to the published baseline.
6. Open a repository issue using the **Task API Enhancement** template with the benchmark data attached.

The key rule: local experiments are for evidence gathering, not for silently shipping production drift.

## Issue → Copilot/cloud-agent → PR flow

The repository is scaffolded for an issue-driven enhancement lifecycle:

1. A consumer files `.github/ISSUE_TEMPLATE/task-api-enhancement.yml`.
2. The issue gets `task-api-enhancement` and `needs-triage`.
3. A maintainer reviews and adds `accepted` when approved for implementation.
4. `.github/workflows/copilot-assign.yml` triggers on the `accepted` label and auto-assigns the issue to the Copilot coding agent when a `COPILOT_TOKEN` secret (personal access token with `repo` scope) is configured. Assignment uses the GitHub GraphQL API. Without the secret the step is skipped with a clear log message.
5. The `skill-maintainer` agent follows `.github/agents/skill-maintainer.md`.
6. The implementation updates `task_cli.py`, `API.md`, and `SKILL.md`, adds tests, and runs benchmarks.
7. A PR is opened, benchmark results are included, and the change is reviewed.
8. After merge, the catalog is released and consumers update to the new tag.

## Benchmark story

`tests/benchmark_bulk.py` compares the current single-comment loop with a simulated bulk endpoint so maintainers can quantify the pain before adding a new command. The benchmark output is intended to look like:

```text
Baseline (loop): 1.20s | Simulated bulk: 0.10s | Speedup: 12.00x
```

The GitHub Actions workflow `.github/workflows/ci-benchmark.yml` runs this automatically. Token measurement for Copilot CLI versus SDK usage is configurable with `BENCHMARK_TOKEN_MODE=cli|sdk`; the default is `none`, which honestly skips token counting when CI does not have the necessary credentials.

## Task API service

A real FastAPI backend lives in [`service/`](service/). It provides the same REST contract consumed by `task_cli.py` and is the canonical backing service for the demo scenario.

Quick start (requires [uv](https://docs.astral.sh/uv/)):

```sh
# Run locally
cd service/
uv sync
uv run uvicorn app.main:app --reload --port 8080

# Set the API URL (Linux/macOS)
export TASK_API_URL=http://localhost:8080
# Set the API URL (Windows PowerShell)
$env:TASK_API_URL = "http://localhost:8080"

# Or via Docker (no local Python needed)
docker build -t task-api-service:latest service/
docker run --rm -p 8080:8080 task-api-service:latest
```

See [`service/README.md`](service/README.md) for full endpoint reference and Docker details.

## Container packaging, CI/CD & deployment

### Workflows

| Workflow file | Trigger | Purpose |
|---|---|---|
| `.github/workflows/service-ci.yml` | Push/PR touching `service/**` | Run pytest + Dockerfile lint |
| `.github/workflows/service-publish.yml` | Push to `main` or `v*.*.*` tag | Build & push image to GHCR |
| `.github/workflows/service-deploy.yml` | After publish succeeds on `main` or manual dispatch | Deploy/update Azure Container Apps |

### GHCR image

```
ghcr.io/tkubica12/skills-demo-catalog/task-api:<tag>
```

Tags produced on every push to `main`:
- `main` — latest from the default branch
- `sha-<short>` — immutable pin to the exact commit

Tags produced on a `v*.*.*` git tag:
- `vX.Y.Z` — explicit version
- `X.Y` — minor floating tag
- `latest` — latest stable release

### Required GitHub secrets

Set these under **Settings → Secrets and variables → Actions → Secrets**:

| Secret | Description |
|---|---|
| `AZURE_CREDENTIALS` | Service-principal JSON from `az ad sp create-for-rbac --sdk-auth` with `contributor` role on the resource group |

Generate the secret:

```bash
az ad sp create-for-rbac \
  --name "skills-demo-deploy" \
  --role contributor \
  --scopes /subscriptions/<subscription-id>/resourceGroups/<resource-group> \
  --sdk-auth
```

Copy the entire JSON output as the `AZURE_CREDENTIALS` secret value.

### Required GitHub repository variables

Set these under **Settings → Secrets and variables → Actions → Variables**:

| Variable | Example value | Description |
|---|---|---|
| `AZURE_RESOURCE_GROUP` | `rg-skills-demo` | Resource group containing the Container App |
| `AZURE_CONTAINER_APP_NAME` | `task-api` | Name of the Azure Container App resource |
| `AZURE_CONTAINER_APP_ENV` | `cae-skills-demo` | ACA managed environment (only needed for first-time creation) |
| `AZURE_LOCATION` | `eastus` | Azure region (only needed for first-time creation) |

### Public endpoint

After a successful deploy the workflow prints the public FQDN. The format is:

```
https://<app-name>.<unique-id>.<region>.azurecontainerapps.io
```

Point the CLI and skill at it:

```sh
# Linux / macOS
export TASK_API_URL=https://<your-fqdn>
python skills/task-api-helper/scripts/task_cli.py list-tasks

# Windows (PowerShell)
$env:TASK_API_URL = "https://<your-fqdn>"
python skills/task-api-helper/scripts/task_cli.py list-tasks
```

If the consuming project repo uses a repository variable or `.env` file to hold `TASK_API_URL`, set it to the ACA FQDN after the first successful deploy.

### Private GHCR images

Packages in a public repository are publicly readable by default — no pull secret is needed for ACA to pull the image.  If the repository is private, create a GitHub PAT with `read:packages` scope, store it as a secret named `GHCR_TOKEN`, and pass it via `az containerapp registry set` or the `--registry-*` flags on `az containerapp create/update`.

## Publishing

Validate the catalog structure without publishing:

```sh
gh skill publish --dry-run
```

Publish a release tag:

```sh
gh skill publish --tag vX.Y.Z
```

## Developer setup

This repo uses [uv](https://docs.astral.sh/uv/) for Python tooling. Install uv once:

```sh
# Linux / macOS / WSL
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then bootstrap both projects:

```sh
# Root (CLI tests + benchmark)
uv sync
uv run pytest tests/ -v

# Service
cd service
uv sync
uv run pytest tests/ -v
uv run uvicorn app.main:app --reload --port 8080
```

## What is fully automated today vs scaffolded?

Fully automated today:

- `pytest tests/ -v`
- `.github/workflows/copilot-setup-steps.yml`
- `.github/workflows/ci-benchmark.yml`

Scaffolded but dependent on external setup:

- `.github/workflows/copilot-assign.yml` requires a `COPILOT_TOKEN` secret (personal access token with `repo` scope); triggers on the `accepted` label after triage, not on every filed issue. **Limitation:** Copilot coding agent assignment via GraphQL requires the organization to have the Copilot coding agent feature enabled and the repository to be in scope.
- Copilot cloud-agent implementation requires an active Copilot coding agent subscription and repository access

## Repository labels

| Label | Purpose |
|-------|---------|
| `task-api-enhancement` | Requested Task API CLI or skill enhancement |
| `needs-triage` | Waiting for maintainer review |
| `accepted` | Approved for implementation |
| `released` | Included in a published catalog tag |
| `skill-bug` | Incorrect behavior or documentation drift |
