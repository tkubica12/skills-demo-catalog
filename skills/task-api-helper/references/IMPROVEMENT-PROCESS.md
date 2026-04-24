# Task API Helper Improvement Process

The `task-api-helper` skill is centrally maintained so every consumer gets the same command set, documentation, test coverage, and CI performance guardrails. Centralization matters because:

- command consistency reduces prompt drift between teams
- shared tests prevent one-off wrappers from breaking the API contract
- CI benchmarks make performance trade-offs visible before new commands are standardized

## Full lifecycle

1. **Local experiment**  
   A consumer team forks `task_cli.py` locally, adds the missing command in that private working copy, and validates it against their real workflow.
2. **Benchmark**  
   The team captures before/after timing data, usually by comparing the current loop against the experimental command. `tests/benchmark_bulk.py` is the reference benchmark harness.
3. **Issue with template**  
   The team restores the local fork to the published baseline, then opens an issue with `.github/ISSUE_TEMPLATE/task-api-enhancement.yml` and includes the benchmark data.
4. **Triage**  
   Catalog maintainers review the problem statement, the measured pain, the proposed command syntax, and whether the API contract should change.
5. **Copilot or cloud agent implementation**  
   Once accepted, Copilot or the configured cloud agent implements the change in the central catalog.
6. **Pull request**  
   The PR updates `task_cli.py`, `API.md`, `SKILL.md`, tests, and benchmark evidence.
7. **Catalog release**  
   After merge, the catalog is tagged and released.
8. **Consumer update**  
   Consumer repositories update their installed skill version and stop carrying any local fork.

## What "local experiment" means

A valid local experiment must:

1. fork the CLI script only in a local branch or disposable copy
2. implement the proposed command end to end
3. run the benchmark or equivalent timing measurement before and after
4. record the exact command syntax, request shape, and observed speedup
5. restore the local fork so production stays on the published baseline
6. open the enhancement issue with the data, not with the forked code

The local experiment is evidence, not an unofficial rollout path.

## Benchmark CI workflow

`.github/workflows/ci-benchmark.yml` runs the benchmark harness on every push, pull request, and manual dispatch. The workflow:

1. installs Python plus the lightweight test dependencies
2. starts `tests/mock_api_server.py`
3. runs `pytest tests/benchmark_bulk.py -v --tb=short`
4. prints the baseline loop time, simulated bulk time, and computed speedup

This makes it easy to compare a proposed command against the current baseline and reject regressions before release.

## Token measurement note

Token measurement is optional. The benchmark workflow reads `BENCHMARK_TOKEN_MODE`:

- `none` (default): skip token counting entirely
- `cli`: measure using Copilot CLI-style token accounting when available
- `sdk`: measure using SDK-side token accounting when available

If CI does not have the necessary token source, the measurement can be deferred without blocking the performance comparison itself. See `.github/workflows/ci-benchmark.yml` for the active configuration.
