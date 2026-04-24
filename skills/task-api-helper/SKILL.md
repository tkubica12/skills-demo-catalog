---
name: task-api-helper
description: 'Helper skill for teams using the shared Task API REST service and its task_cli.py wrapper. Use when the user needs to interact with project tasks: list tasks (optionally filtering by status such as waiting-for-response), get a task, add comments to one or many tasks. The skill knows the API contract and full CLI command set. Supports: list-tasks, get-task, add-comment, bulk-add-comment.'
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
export TASK_API_URL="https://tasks.internal.example.com"

# Optional: authentication token
export TASK_API_TOKEN="<your-token>"
```

---

## Supported CLI Commands

### list-tasks

```bash
python task_cli.py list-tasks [--status <status>] [--api-url <url>]
```

Lists all tasks. Use `--status` to filter by any status value the API supports, for example `waiting-for-response` or `resolved`. Omit `--status` to return all tasks.

### get-task

```bash
python task_cli.py get-task TASK_ID [--api-url <url>]
```

Fetches a single task by ID including its comment thread.

### add-comment

```bash
python task_cli.py add-comment TASK_ID "Your comment text" [--api-url <url>]
```

Appends a comment to a single task. The comment text is a positional argument.

### bulk-add-comment

```bash
python task_cli.py bulk-add-comment (--ids <id>... | --status <status>) --comment <text> [--api-url <url>]
```

Appends the same comment to multiple tasks in a single session. Provide either `--ids` with one or more task identifiers, or `--status` to target all tasks with that status. Returns a JSON summary with the number of tasks updated and each individual comment result.

---

## Known Limitation: No bulk-add-comment

~~The baseline CLI does **not** support `bulk-add-comment`.~~

`bulk-add-comment` is now available. See the **Supported CLI Commands** section above.

---

## Quick Diagnostics

```bash
# Confirm the API is reachable
curl -s "$TASK_API_URL/health"

# List tasks waiting for a response
python task_cli.py list-tasks --status waiting-for-response

# Verify CLI is functional
python task_cli.py --help
```

---

## Improvement Requests

This skill is centrally maintained. To request a new command or API feature, open an issue in this catalog repository using the **Task API Enhancement** template. Reference the issue number in any PR that implements the change. See `references/IMPROVEMENT-PROCESS.md` for the full lifecycle.
