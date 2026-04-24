# Copilot instructions

This repository is a GitHub Copilot skill catalog. The primary skill is `task-api-helper`.

- When implementing a new CLI command, always update `skills/task-api-helper/scripts/task_cli.py`, `skills/task-api-helper/references/API.md`, and `skills/task-api-helper/SKILL.md`.
- Always run `pytest tests/ -v` before opening a PR.
- Keep the benchmark story honest: `tests/benchmark_bulk.py` is the fast low-level harness, while `benchmarks/agent_benchmark.py` is the real agent comparison harness for central skill changes.
- Do not add `bulk-add-comment` to the baseline CLI without a linked enhancement issue.
- Use conventional commit format: `feat:`, `fix:`, `docs:`, `test:`.
