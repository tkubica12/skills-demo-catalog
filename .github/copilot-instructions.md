# Copilot instructions

This repository is a GitHub Copilot skill catalog. The primary skill is `task-api-helper`.

- When implementing a new CLI command, always update `skills/task-api-helper/scripts/task_cli.py`, `skills/task-api-helper/references/API.md`, and `skills/task-api-helper/SKILL.md`.
- Always run `pytest tests/ -v` before opening a PR.
- For accepted enhancement issues, add a benchmark spec file under `benchmarks/specs/task-api-helper/` that explains the workflow benefit to benchmark.
- Keep the benchmark story honest: `benchmarks/agent_benchmark.py` is a generic runner, while the actual benchmark scenario and prompt are authored in the benchmark spec file.
- Keep the benchmark prompt goal-level so the agent discovers whether the enhancement helps; do not hardcode the new CLI syntax into the benchmark prompt.
- Do not add `bulk-add-comment` to the baseline CLI without a linked enhancement issue.
- Use conventional commit format: `feat:`, `fix:`, `docs:`, `test:`.
