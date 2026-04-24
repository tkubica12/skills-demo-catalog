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

```bash
python skills/task-api-helper/scripts/task_cli.py list-tasks [--status open|closed|all] [--project PROJECT_ID]
python skills/task-api-helper/scripts/task_cli.py get-task TASK_ID
python skills/task-api-helper/scripts/task_cli.py add-comment TASK_ID --message "Your comment"
```

Environment variables:

```bash
export TASK_API_BASE_URL="https://tasks.internal.example.com"
export TASK_API_TOKEN="<optional-bearer-token>"
```

## Known limitation — no bulk-add-comment

The baseline CLI does **not** expose `bulk-add-comment`. Teams that need to comment on many tasks currently use a loop such as:

```bash
for id in $(python skills/task-api-helper/scripts/task_cli.py list-tasks --status open --project PROJ --format ids); do
  python skills/task-api-helper/scripts/task_cli.py add-comment "$id" --message "Sprint closed — see board for details"
done
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
3. `.github/workflows/copilot-assign.yml` can auto-assign the issue to the Copilot coding agent when a `COPILOT_TOKEN` secret is configured.
4. The `skill-maintainer` agent follows `.github/agents/skill-maintainer.md`.
5. The implementation updates `task_cli.py`, `API.md`, and `SKILL.md`, adds tests, and runs benchmarks.
6. A PR is opened, benchmark results are included, and the change is reviewed.
7. After merge, the catalog is released and consumers update to the new tag.

## Benchmark story

`tests/benchmark_bulk.py` compares the current single-comment loop with a simulated bulk endpoint so maintainers can quantify the pain before adding a new command. The benchmark output is intended to look like:

```text
Baseline (loop): 1.20s | Simulated bulk: 0.10s | Speedup: 12.00x
```

The GitHub Actions workflow `.github/workflows/ci-benchmark.yml` runs this automatically. Token measurement for Copilot CLI versus SDK usage is configurable with `BENCHMARK_TOKEN_MODE=cli|sdk`; the default is `none`, which honestly skips token counting when CI does not have the necessary credentials.

## Publishing

Validate the catalog structure without publishing:

```bash
gh skill publish --dry-run
```

Publish a release tag:

```bash
gh skill publish --tag vX.Y.Z
```

## What is fully automated today vs scaffolded?

Fully automated today:

- `pytest tests/ -v`
- `.github/workflows/copilot-setup-steps.yml`
- `.github/workflows/ci-benchmark.yml`

Scaffolded but dependent on external setup:

- `.github/workflows/copilot-assign.yml` requires a `COPILOT_TOKEN` secret with `assignees:write`
- Copilot cloud-agent implementation requires an active Copilot coding agent subscription and repository access

## Repository labels

| Label | Purpose |
|-------|---------|
| `task-api-enhancement` | Requested Task API CLI or skill enhancement |
| `needs-triage` | Waiting for maintainer review |
| `accepted` | Approved for implementation |
| `released` | Included in a published catalog tag |
| `skill-bug` | Incorrect behavior or documentation drift |
