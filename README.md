# Skills Demo Catalog

A **centrally managed** [GitHub Copilot agent skills](https://cli.github.com/manual/gh_skill) catalog that demonstrates the `gh skill publish` workflow for shared, version-controlled AI assistant skills across an organization.

---

## What's in this catalog

| Skill | Description |
|-------|-------------|
| [`release-readiness-check`](./skills/release-readiness-check/SKILL.md) | Structured pre-release review that produces a GO / NO-GO report covering tests, changelog, security, docs, and deployment plan |

---

## Installing a skill

```bash
# Install the release readiness skill into your project
gh skill install tkubica12/skills-demo-catalog release-readiness-check
```

After installation, activate it in GitHub Copilot Chat:

```
@copilot /release-readiness-check
```

---

## Publishing a new catalog release

Skills are versioned and published as GitHub releases. The `gh skill publish` command validates the catalog layout, prompts for a version tag, and creates a release automatically.

### Dry-run validation (no publish)

```bash
# From the repo root
gh skill publish --dry-run
```

### Publish a specific version (non-interactive)

```bash
gh skill publish --tag v1.2.0
```

The command:
1. Discovers all `skills/*/SKILL.md` files.
2. Validates frontmatter (`name`, `description`, `allowed-tools` as a string).
3. Checks that each skill directory name matches the `name` field.
4. Creates a GitHub release tagged `v1.2.0` with auto-generated release notes.

> **Tip:** Use [conventional commits](https://www.conventionalcommits.org/) for PR titles so release notes are meaningful.

---

## Requesting an enhancement

This catalog follows an **issue-driven enhancement flow**:

1. A consuming team opens an issue using the [Skill Enhancement Request](./.github/ISSUE_TEMPLATE/skill-enhancement.yml) template.  
   The issue is automatically labelled `skill-enhancement` + `needs-triage`.

2. Catalog maintainers triage, assign, and implement the change on a feature branch.

3. The PR references the issue (`Closes #<N>`) and is merged into `main`.

4. A new catalog release is published with `gh skill publish --tag vX.Y.Z`.  
   The release notes link directly to the resolved issue(s).

5. The issue is closed and the [`REQUEST-TRACKING.md`](./skills/release-readiness-check/references/REQUEST-TRACKING.md) table is updated.

6. Consuming teams run `gh skill update --all` to get the latest version.

---

## Repository labels

| Label | Purpose |
|-------|---------|
| `skill-enhancement` | New feature or change request for a skill |
| `skill-bug` | Incorrect or misleading skill behaviour |
| `needs-triage` | Awaiting maintainer review |
| `accepted` | Accepted, scheduled for next release |
| `released` | Shipped in a catalog release |

---

## Contributing

1. Fork this repository.
2. Create a branch: `feat/release-readiness-check-add-docker-check`.
3. Edit the relevant `SKILL.md`.
4. Validate locally: `gh skill publish --dry-run`.
5. Open a PR referencing the enhancement issue.
