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

```sh
mkdir fresh-skill-demo
cd fresh-skill-demo
git init
```

### 2. Install the shared skill from the central catalog

```sh
gh skill install tkubica12/skills-demo-catalog task-api-helper --scope project --agent github-copilot
```

### 3. In the installed skill folder, create `.env`

Copy `.agents/skills/task-api-helper/.env.example` to
`.agents/skills/task-api-helper/.env`, then set it to:

```dotenv
TASK_API_URL=https://task-api-demo.politepond-5bd69c31.swedencentral.azurecontainerapps.io
```

### 4. Open Copilot and try following prompts

```text
List tasks waiting for response and summarize what needs attention.
```

```text
Open task-1 and add this comment: "Following up - please provide an update."
```

```text
Add the same comment to every task waiting for response. 
```

```text
Based your experience with this skill do you think we might enhanced this skill in some way to make it faster and more reliable next time some agent uses it?
```

This is the key demo moment: the agent should feel the workflow gap.

#### Prompt 4

```text
Do not build a permanent local fork. Draft an upstream enhancement issue for tkubica12/skills-demo-catalog that explains the gap and proposes the right shared command.
```

#### Prompt 5

```text
Create the GitHub issue in tkubica12/skills-demo-catalog, then tell me the issue number, the proposed command, and why this belongs in the central catalog instead of this repo.
```

## Central maintainer steps

Once the issue exists, switch back to this catalog repo.

### 5. Find the new issue

```sh
gh issue list -R tkubica12/skills-demo-catalog --limit 10
```

### 6. Accept it for central implementation

Replace `<ISSUE_NUMBER>`:

```sh
gh issue edit <ISSUE_NUMBER> -R tkubica12/skills-demo-catalog --add-label accepted
```

### 7. Watch Copilot get assigned

```sh
gh run list -R tkubica12/skills-demo-catalog --workflow "Auto-assign to Copilot" --limit 5
gh issue view <ISSUE_NUMBER> -R tkubica12/skills-demo-catalog
```

### 8. Watch the PR appear

```sh
gh pr list -R tkubica12/skills-demo-catalog --limit 10
```

If you want one more Copilot prompt at this point, use:

```text
Implement the accepted enhancement in the central catalog, update the skill docs and tests, and open a PR.
```

## Full-loop variant

If you want to continue past issue + PR:

### 9. Merge the PR

Replace `<PR_NUMBER>`:

```sh
gh pr merge <PR_NUMBER> -R tkubica12/skills-demo-catalog --merge
```

### 10. Publish the updated skill

Replace `<NEW_TAG>`:

```sh
gh skill publish --tag <NEW_TAG>
```

### 11. Go back to the fresh repo and update the installed skill

```sh
cd fresh-skill-demo
gh skill install tkubica12/skills-demo-catalog task-api-helper --scope project --agent github-copilot --force --pin <NEW_TAG>
```

### 12. Final prompt in the fresh repo

```text
Run the same task workflow again and tell me whether the new shared skill release closed the gap.
```

## Minimal talking points

- "This repo is the central source of truth for shared agent capabilities."
- "The consumer repo starts empty and installs the skill with `gh skill`."
- "The gap is discovered downstream, but fixed centrally."
- "The output is not a local hack. The output is a released shared skill."

## Publishing

Validate:

```sh
gh skill publish --dry-run
```

Publish:

```sh
gh skill publish --tag vX.Y.Z
```
