# Skills Demo Catalog

Central catalog for GitHub Copilot skills distributed with `gh skill`.

This demo is about **central skill evolution**:

1. start in a fresh consumer repo
2. install a shared skill from this catalog
3. use it against a real API
4. hit a workflow gap
5. push the improvement upstream through issue -> triage -> Copilot PR -> release

The shared skill in this catalog is **`task-api-helper`**.

## What to showcase

Show these points, in this order:

1. the capability lives in the **central catalog**
2. the consumer repo is just a **plain repo**
3. the agent can use the shared skill immediately
4. the agent discovers a missing higher-level workflow
5. the fix belongs in the **catalog**, not in a permanent local fork

## Fastest Azure API setup

Run the demo API in Azure Container Apps:

```sh
az containerapp up \
  --name task-api-demo \
  --resource-group rg-skills-demo-taskapi \
  --location swedencentral \
  --ingress external \
  --target-port 8080 \
  --image ghcr.io/tkubica12/skills-demo-catalog/task-api:main
```

Current live demo URL:

```text
https://task-api-demo.politepond-5bd69c31.swedencentral.azurecontainerapps.io
```

## Showcase script

### 1. Create a plain fresh repo
We will create new folder and initialize repository.

```sh
mkdir fresh-skill-demo
cd fresh-skill-demo
git init
```

### 2. Install the shared skill from the central catalog
GitHub CLI comes with skill subcommand so we can easily download version-controled skilled.

```sh
gh skill install tkubica12/skills-demo-catalog task-api-helper --scope project --agent github-copilot
```

### 3. In the installed skill folder, create `.env`
Once downloaded make sure to configure `.env` with URL to your instance of demo API.

Copy `.agents/skills/task-api-helper/.env.example` to
`.agents/skills/task-api-helper/.env`, then set it to:

```dotenv
TASK_API_URL=https://task-api-demo.politepond-5bd69c31.swedencentral.azurecontainerapps.io
```

### 4. Open Copilot and try following prompts
Open Copilot in our new project, eg. using Visual Studio Code Agents UI a GitHub Copilot CLI, and try following tasks. Copilot should use our skill accordingly and react to whatever issues it is faced with.

```text
List tasks waiting for response and summarize what needs attention.
```

```text
Open task-1 and add this comment: "Following up - please provide an update."
```

```text
Add the same comment to every task waiting for response. 
```

Note we have seen problems - rate limits on our API and need to go call by call with no bulk operation capability. This all does increase token usage and time, lowers reliability.

```text
Based on your experience with this workflow, suggest one improvement that could make it faster or more reliable next time.
```

At this point agent will probably suggest two improvements:

- API is returning 429 (rate limit) sometimes and CLI has no retry so agent has to retry itself (takes time and costs tokens)
- CLI does not implement bulk operation so agent has to do this in multiple turns (again takes time and costs tokens)

Agent should create local PoC to prove this idea and based on that create Issue in central repository with his suggestions and details how to achieve it.


### 5. Central maintainer steps

Once the issue exists, we run GitHub Agentic Workflows to spin up agent to triage this request. Agent will post its recommendation to issue notes and assign label `copilot-recommended` if agent finds this enhancement useful and feasible. Now it waits for human in the loop.

Assign label "accepted" to it. This will start agentic process to implement this (we have workflow that auto-assigns accepted issues to **Copilot** to implement this).

### 6. Review the Copilot pull request

After the `accepted` label is added, GitHub Actions assigns the issue to **Copilot**. Copilot creates a pull request in this central catalog with the proposed skill enhancement.

```sh
gh pr list -R tkubica12/skills-demo-catalog --limit 10
gh pr view <PR_NUMBER> -R tkubica12/skills-demo-catalog --web
```

In this demo, the PR should show the catalog-controlled change, not a local one-off workaround in the consumer repo:

1. new or updated skill command implementation
2. updated skill instructions or references, if needed
3. tests for the changed command behavior
4. a benchmark spec used by CI to describe why this enhancement should help

The important point is that Copilot is not just writing code. It is also contributing the evidence needed to prove that the central skill got better.

### 7. Show the agentic benchmark check

The PR runs the `CI Benchmark` workflow. This workflow starts an agentic test using the **GitHub Copilot SDK**.

```sh
gh pr checks <PR_NUMBER> -R tkubica12/skills-demo-catalog
gh run list -R tkubica12/skills-demo-catalog --workflow "CI Benchmark" --limit 5
```

The benchmark compares two variants:

1. **baseline** - the current skill from `main`
2. **candidate** - the skill from the pull request

For each variant, the workflow spins up the same local demo Task API scenario and asks Copilot to complete the same goal-level task. The benchmark does not hardcode the exact tool calls Copilot must make. Instead, it measures how the agent behaves with the old skill versus the enhanced skill.

The benchmark captures:

1. whether the task succeeded
2. how many tasks were updated
3. wall-clock duration
4. input and output token usage
5. number of LLM calls
6. Task API requests
7. API rate-limit responses

This lets us demonstrate the business value of the skill change: the enhanced central skill should complete the same work with fewer agent turns, fewer tokens, and less time.

### 8. Show the benchmark PR comment

When the benchmark finishes, the workflow posts a sticky comment on the pull request with a summary table.

```sh
gh pr view <PR_NUMBER> -R tkubica12/skills-demo-catalog --comments
```

For this enhancement, the comment should show something like:

| Variant | Success | Updated | Duration (s) | Input tokens | Output tokens | LLM calls | API requests | 429s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | true | 2 | higher | higher | higher | higher | similar | similar |
| candidate | true | 2 | lower | lower | lower | lower | similar | similar |

Use this comment as the proof point: the pull request is not approved only because the code looks reasonable, but because an automated agentic benchmark shows the enhanced skill saves time and tokens on the workflow it was designed to improve.

### 9. Merge and consume the improved central skill

After reviewing the implementation, tests, and benchmark result, merge the PR into the central catalog.

Then return to the consumer repo and update or reinstall the skill:

```sh
gh skill install tkubica12/skills-demo-catalog task-api-helper --scope project --agent github-copilot
```

Now repeat the original bulk-comment prompt:

```text
Add the same comment to every task waiting for response.
```

The agent should now have a better centrally maintained skill available. The local project did not need to keep custom scripts or a forked workaround.

### 10. Demo reset

For a clean repeatable demo, leave the catalog in the pre-enhancement state until you are ready to show the merge moment. Keep the accepted issue and Copilot PR available when demonstrating the governance flow, then merge only when you want to demonstrate central rollout.

---

