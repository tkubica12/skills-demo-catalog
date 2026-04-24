# Task API Helper Improvement Process

The `task-api-helper` skill is centrally maintained so every consumer gets the same command set, documentation, test coverage, and CI performance guardrails. Centralization matters because:

- command consistency reduces prompt drift between teams
- shared tests prevent one-off wrappers from breaking the API contract
- CI benchmarks make performance trade-offs visible before new commands are standardized

## Full lifecycle

1. **Local experiment**  
   A consumer team tries a temporary local proof of concept in the current repository and validates it against the real workflow that exposed the gap.
2. **Benchmark**  
   The team captures before/after evidence from that local trial — timing data when relevant, but also reliability improvements, fewer retries, fewer manual steps, or cleaner behavior.
3. **Issue with template**  
    The team restores the local changes to the published baseline, then opens an issue with `.github/ISSUE_TEMPLATE/task-api-enhancement.yml` and includes the local proof-of-concept evidence.
4. **Advisory triage**  
   A GitHub Agentic Workflow can add an early recommendation comment and an advisory label such as `copilot-recommended`, but this does not replace human maintainer review. In this repo that workflow is backed by gh-aw and needs `COPILOT_GITHUB_TOKEN` configured in Actions.
5. **Triage**  
   Catalog maintainers review the problem statement, the measured pain, the proposed command syntax, and whether the shared API or CLI contract should change.
6. **Copilot or cloud agent implementation**  
   Once accepted, Copilot or the configured cloud agent implements the change in the central catalog.
7. **Pull request**  
   The PR updates `task_cli.py`, `API.md`, `SKILL.md`, tests, and benchmark evidence.
8. **Catalog release**  
   After merge, the catalog is tagged and released.
9. **Consumer update**  
   Consumer repositories update their installed skill version and stop carrying any local fork.

## Downstream consumer rule

The downstream agent should behave like an engineer, not an issue bot:

1. reproduce the pain locally
2. try a disposable local proof of concept
3. verify whether the idea actually helps
4. write down exact findings
5. remove the local changes
6. only then open the upstream issue

An upstream issue without any local validation is lower quality and should be
avoided when the consumer repo can safely test the idea first.

## What "local experiment" means

A valid local experiment must:

1. be disposable and local to the current repo
2. test the proposed behavior end to end
3. capture concrete evidence, not just an opinion
4. record the exact command syntax or retry strategy that was tried
5. record the observed result: faster, fewer failures, less repetition, cleaner UX, etc.
6. restore the local repo so production stays on the published baseline
7. open the enhancement issue with the findings, not with the forked code

For a repetitive multi-step task workflow, the experiment should verify the
proposed behavior against the real endpoint available to the consumer repo and
capture the practical impact in terms that a maintainer can evaluate.

The local experiment is evidence, not an unofficial rollout path.

## Catalog-side benchmark CI workflow

`.github/workflows/ci-benchmark.yml` now has two benchmark layers:

1. **Low-level workflow benchmark**  
   Starts `tests/mock_api_server.py`, runs `pytest tests/benchmark_bulk.py -v --tb=short`, and gives a fast deterministic signal about the raw workflow delta between repeated single-task calls and the simulated bulk endpoint.
2. **Agent benchmark**  
   Runs `benchmarks/agent_benchmark.py`, which compares the installed skill from `main` with the installed skill from the current patch by running the same Copilot task against both in isolated workspaces.

The agent benchmark is the stronger evidence for central skill evolution because
it measures the real agent workflow, not just the HTTP wrapper.

This is catalog-internal validation. Downstream repos are not expected to
contain these exact benchmark files.

## Token measurement note

Token measurement is no longer described as a placeholder mode switch. The
agent benchmark uses GitHub Copilot SDK session events instead:

- `assistant.usage` for input/output token counts and per-call API duration
- `session.shutdown` for total premium requests and total API duration

If the repository does not have `COPILOT_GITHUB_TOKEN` configured for CI, the
agent benchmark is skipped cleanly and the low-level benchmark still runs.
