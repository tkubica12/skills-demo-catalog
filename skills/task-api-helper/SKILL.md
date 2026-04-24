---
name: task-api-helper
description: 'Helper skill for teams using the shared Task API REST service and its task_cli.py wrapper. Use when the user needs to interact with project tasks: list tasks, filter them by status, fetch task details, add comments, and work within the current shared Task API workflow. The skill knows the API contract, CLI command set, and the improvement process for proposing upstream enhancements when teams discover repetitive or awkward workflows.'
license: MIT
allowed-tools: Bash,Python
---

# task-api-helper

## Overview

This skill helps you work with the **Task API** — a shared REST service for project task management — and its companion CLI wrapper `task_cli.py`. Use this skill when you need to:

- Query or update project tasks via the REST API
- Run the `task_cli.py` wrapper commands
- Understand the current shared Task API workflow
- Navigate the improvement process to propose a new command upstream

---

## Environment Setup

```bash
# Preferred: configure the installed skill locally
cp .env.example .env

# Then edit .env
TASK_API_URL="https://tasks.internal.example.com"

# Optional: authentication token
TASK_API_TOKEN="<your-token>"
```

The installed skill reads configuration in this order:

1. `--api-url` / `--token`
2. `.env` in the installed skill folder
3. shell environment variables

Using `.env` in the installed skill folder is the preferred demo setup because
the agent may execute in a different shell than the one where environment
variables were exported.

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

---

## Workflow evolution

This skill is intentionally centrally maintained. If you discover that a common
workflow feels repetitive, awkward, or missing a useful higher-level command,
open an enhancement issue in the catalog repository using the **Task API
Enhancement** template. See `references/IMPROVEMENT-PROCESS.md` for the full
flow.

---

## Quick Diagnostics

```bash
# Verify CLI is functional
python task_cli.py --help

# List tasks waiting for a response using the configured .env / --api-url / env var
python task_cli.py list-tasks --status waiting-for-response
```

---

## Improvement Requests

This skill is centrally maintained. To request a new command or API feature, open an issue in this catalog repository using the **Task API Enhancement** template. Reference the issue number in any PR that implements the change. See `references/IMPROVEMENT-PROCESS.md` for the full lifecycle.
