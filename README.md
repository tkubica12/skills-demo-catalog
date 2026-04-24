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

```powershell
New-Item -ItemType Directory C:\git\fresh-skill-demo -Force | Out-Null
Set-Location C:\git\fresh-skill-demo
git init
```

### 2. Install the shared skill from the central catalog

```powershell
gh skill install tkubica12/skills-demo-catalog task-api-helper --scope project --agent github-copilot
```

### 3. Create the installed skill `.env`

```powershell
Copy-Item .agents\skills\task-api-helper\.env.example .agents\skills\task-api-helper\.env
@"
TASK_API_URL=https://task-api-demo.politepond-5bd69c31.swedencentral.azurecontainerapps.io
"@ | Set-Content .agents\skills\task-api-helper\.env
Get-Content .agents\skills\task-api-helper\.env
```

### 4. Open Copilot and paste these prompts

Paste them one by one.

#### Prompt 1

```text
Use the installed task-api-helper skill to list tasks with status waiting-for-response and summarize what needs attention.
```

#### Prompt 2

```text
Use the shared task-api-helper skill to fetch details for task-1 and then add this comment: "Following up - please provide an update."
```

#### Prompt 3

```text
Now use the shared task-api-helper skill to add the same comment to every task with status waiting-for-response. Keep the repo clean and do not invent a permanent local workaround unless absolutely necessary.
```

This is the key demo moment: the agent should feel the workflow gap.

#### Prompt 4

```text
Do not build a permanent local fork. Explain what capability is missing in the shared skill and draft an upstream enhancement issue for tkubica12/skills-demo-catalog.
```

#### Prompt 5

```text
Create the GitHub issue in tkubica12/skills-demo-catalog, then tell me the issue number, the proposed command, and why it should live in the central catalog instead of this repo.
```

## Central maintainer steps

Once the issue exists, switch back to this catalog repo.

### 5. Find the new issue

```powershell
gh issue list -R tkubica12/skills-demo-catalog --limit 10
```

### 6. Accept it for central implementation

Replace `<ISSUE_NUMBER>`:

```powershell
gh issue edit <ISSUE_NUMBER> -R tkubica12/skills-demo-catalog --add-label accepted
```

### 7. Watch Copilot get assigned

```powershell
gh run list -R tkubica12/skills-demo-catalog --workflow "Auto-assign to Copilot" --limit 5
gh issue view <ISSUE_NUMBER> -R tkubica12/skills-demo-catalog
```

### 8. Watch the PR appear

```powershell
gh pr list -R tkubica12/skills-demo-catalog --limit 10
```

If you want the audience to drive Copilot further, use:

```text
Implement the accepted enhancement in the central catalog, update the skill docs and tests, and open a PR.
```

## Full-loop variant

If you want to continue past issue + PR:

### 9. Merge the PR

Replace `<PR_NUMBER>`:

```powershell
gh pr merge <PR_NUMBER> -R tkubica12/skills-demo-catalog --merge
```

### 10. Publish the updated skill

Replace `<NEW_TAG>`:

```powershell
gh skill publish --tag <NEW_TAG>
```

### 11. Go back to the fresh repo and update the installed skill

```powershell
Set-Location C:\git\fresh-skill-demo
gh skill install tkubica12/skills-demo-catalog task-api-helper --scope project --agent github-copilot --force --pin <NEW_TAG>
```

### 12. Final prompt in the fresh repo

```text
Use the updated shared task-api-helper skill to perform the same repetitive task again and tell me whether the central release closed the gap.
```

## Minimal talking points

- "This repo is the central source of truth for shared agent capabilities."
- "The consumer repo starts empty and installs the skill with `gh skill`."
- "The gap is discovered downstream, but fixed centrally."
- "The output is not a local hack. The output is a released shared skill."

## Publishing

Validate:

```powershell
gh skill publish --dry-run
```

Publish:

```powershell
gh skill publish --tag vX.Y.Z
```
