---
name: task-api-helper
description: 'Helper skill for teams using the shared Task API REST service and its task_cli.py wrapper. Use when the user needs to interact with project tasks: list tasks, get a task, add comments, or investigate missing bulk operations. The skill knows the API contract, CLI command set, and the improvement process for proposing new CLI commands upstream. Supports: list-tasks, get-task, add-comment. Does NOT support bulk-add-comment in the baseline — consumers who need that capability should follow the improvement process.'
license: MIT
allowed-tools: Bash,Python
---

# task-api-helper

## Overview

This skill helps you work with the **Task API** — a shared REST service for project task management — and its companion CLI wrapper `task_cli.py`. Use this skill when you need to:

- Query or update project tasks via the REST API
- Run the `task_cli.py` wrapper commands
- Understand what the CLI can and cannot do today
- Navigate the improvement process to propose a new command upstream

---

## Environment Setup

```bash
# Set the API base URL (required)
export TASK_API_BASE_URL="https://tasks.internal.example.com"

# Optional: authentication token
export TASK_API_TOKEN="<your-token>"
```

---

## Supported CLI Commands

### list-tasks

```bash
python task_cli.py list-tasks [--status open|closed|all] [--project PROJECT_ID]
```

Lists tasks. Defaults to `status=open`.

### get-task

```bash
python task_cli.py get-task TASK_ID
```

Fetches a single task by ID including its comment thread.

### add-comment

```bash
python task_cli.py add-comment TASK_ID --message "Your comment"
```

Appends a comment to a single task.

---

## Known Limitation: No bulk-add-comment

The baseline CLI does **not** support `bulk-add-comment`. Teams that need to annotate many tasks at once currently work around this with a shell loop:

```bash
for id in $(python task_cli.py list-tasks --status open --project PROJ --format ids); do
  python task_cli.py add-comment "$id" --message "Sprint closed — see board for details"
done
```

This is slow (one HTTP round-trip per task) and brittle in CI. If your team has measured this pain, open an enhancement issue in the catalog repository using the **Task API Enhancement** template. See `references/IMPROVEMENT-PROCESS.md` for the full flow.

---

## Quick Diagnostics

```bash
# Confirm the API is reachable
curl -s "$TASK_API_BASE_URL/health"

# List open tasks for a project
python task_cli.py list-tasks --project MY_PROJECT

# Verify CLI is functional (uses mock server if TASK_API_BASE_URL not set)
python task_cli.py --help
```

---

## Improvement Requests

This skill is centrally maintained. To request a new command or API feature, open an issue in this catalog repository using the **Task API Enhancement** template. Reference the issue number in any PR that implements the change. See `references/IMPROVEMENT-PROCESS.md` for the full lifecycle.
