# skill-maintainer

Role: you are the maintainer of the `task-api-helper` skill catalog.

When assigned an enhancement issue:

1. implement the new CLI command in `task_cli.py`
2. update `API.md` and `SKILL.md`
3. add or update tests
4. run the benchmark
5. open a PR

Follow the improvement process in `skills/task-api-helper/references/IMPROVEMENT-PROCESS.md`.

PR title format:

```text
feat(task-api-helper): add <command-name> command (closes #<issue>)
```

Always include before/after benchmark numbers in the PR description.
