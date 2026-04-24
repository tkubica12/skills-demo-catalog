# Copilot instructions

This repository is a GitHub Copilot skill catalog. The primary skill is `task-api-helper`.

- When implementing a new CLI command, always update `skills/task-api-helper/scripts/task_cli.py`, `skills/task-api-helper/references/API.md`, and `skills/task-api-helper/SKILL.md`.
- Always run `pytest tests/ -v` before opening a PR.
- The benchmark in `tests/benchmark_bulk.py` must pass and must not regress versus the current baseline.
- Do not add `bulk-add-comment` to the baseline CLI without a linked enhancement issue.
- Use conventional commit format: `feat:`, `fix:`, `docs:`, `test:`.
