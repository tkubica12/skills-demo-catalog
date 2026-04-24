---
name: release-readiness-check
description: 'Perform a structured release readiness review for a software project. Use when the user asks to check release readiness, review a release candidate, run a pre-release checklist, or mentions "/release-check". Evaluates: (1) Test coverage and CI status, (2) Changelog and version bump correctness, (3) Open blocking issues and pull requests, (4) Security and dependency scan results, (5) Documentation completeness, (6) Rollback and deployment plan presence.'
license: MIT
allowed-tools: Bash,GitHubActions
---

# Release Readiness Check

## Overview

Perform a comprehensive pre-release review that gives the team a clear **GO / NO-GO** signal with an itemized findings report. This skill is shared centrally so all teams follow the same release gate standard.

---

## Checklist

Run through these categories in order. For each item, state **PASS**, **WARN**, or **FAIL** and add a brief finding.

### 1. Version & Changelog

```bash
# Confirm version bump exists
git log --oneline -10

# Confirm CHANGELOG or release notes are updated
ls CHANGELOG* RELEASE_NOTES* docs/releases/ 2>/dev/null || echo "No changelog found"

# Show latest changelog entry
head -40 CHANGELOG.md 2>/dev/null || head -40 CHANGELOG.rst 2>/dev/null || echo "No CHANGELOG.md"
```

**Checks:**
- Version has been bumped (patch / minor / major) relative to the previous tag.
- CHANGELOG entry exists for this version with a summary of changes.
- Version string is consistent across `package.json`, `pyproject.toml`, `pom.xml`, `*.csproj`, or equivalent.

---

### 2. CI / Test Status

```bash
# Show recent workflow runs
gh run list --limit 10

# Show last run summary
gh run view $(gh run list --limit 1 --json databaseId -q '.[0].databaseId') 2>/dev/null
```

**Checks:**
- All required CI checks pass on the release branch or tag commit.
- Test coverage is at or above the project threshold (check `.codecov.yml`, `jest.config.*`, `pytest.ini`, etc.).
- No flaky tests were re-run more than once to pass.

---

### 3. Open Blocking Issues & PRs

```bash
# Blocking issues
gh issue list --label "release-blocker" --state open

# Open PRs targeting main/release branch
gh pr list --base main --state open
gh pr list --base release --state open 2>/dev/null || true
```

**Checks:**
- No open issues labelled `release-blocker`.
- No unmerged PRs that are required for this release (confirm with the team).

---

### 4. Security & Dependencies

```bash
# Check for known vulnerabilities (Node)
npm audit --audit-level=high 2>/dev/null || true

# Python
pip-audit 2>/dev/null || safety check 2>/dev/null || true

# GitHub Dependabot alerts
gh api repos/{owner}/{repo}/vulnerability-alerts 2>/dev/null && echo "Vulnerability alerts API accessible" || true
gh api repos/{owner}/{repo}/dependabot/alerts --jq '[.[] | select(.state=="open")] | length' 2>/dev/null || true
```

**Checks:**
- No HIGH or CRITICAL unresolved dependency vulnerabilities.
- Dependabot alerts are either resolved or have an accepted risk note.

---

### 5. Documentation

```bash
# Confirm docs exist
ls docs/ README* *.md 2>/dev/null | head -20

# Look for broken internal links (basic check)
grep -r "\[.*\](.*\.md)" docs/ README.md 2>/dev/null | grep -v "http" | head -20 || true
```

**Checks:**
- README is up-to-date with any new features or changed configuration.
- API reference / architecture docs reflect the release changes.
- Migration guide exists if there are breaking changes.

---

### 6. Rollback & Deployment Plan

```bash
# Check for deployment runbook
ls .github/deployment* docs/runbook* docs/deploy* ops/runbook* 2>/dev/null || echo "No runbook found"

# Check for feature flags or progressive rollout config
ls .featureflags* config/features* 2>/dev/null || true
```

**Checks:**
- A deployment runbook or script exists.
- Rollback steps are documented (previous release tag, database migration reversal, etc.).
- Feature flags are set appropriately for the rollout strategy.

---

## Output Format

After running all checks, produce a structured report:

```
## Release Readiness Report — v<VERSION>

| Category            | Status | Finding                          |
|---------------------|--------|----------------------------------|
| Version & Changelog | ✅ PASS | v1.2.0 bumped, CHANGELOG updated |
| CI / Tests          | ✅ PASS | All 47 checks green              |
| Blocking Issues     | ⚠️ WARN | 1 open PR not yet merged         |
| Security            | ✅ PASS | 0 high/critical vulns            |
| Documentation       | ✅ PASS | README updated                   |
| Deployment Plan     | ❌ FAIL | No rollback runbook found        |

**Overall: NO-GO** — resolve FAIL items before tagging the release.

### Action Items
1. [ ] Merge PR #42 or mark it post-release.
2. [ ] Add rollback steps to `docs/runbook-deploy.md`.
```

Provide specific file paths and commands the team should run to resolve each FAIL or WARN.

---

## Enhancement Requests

This skill is centrally maintained. To request changes, open an issue in the catalog repository using the **Skill Enhancement Request** template. Reference the issue number in any PR that implements the change. Resolved requests are noted in the catalog release notes.
