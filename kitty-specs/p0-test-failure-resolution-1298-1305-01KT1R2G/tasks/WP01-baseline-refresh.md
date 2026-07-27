---
work_package_id: WP01
title: Baseline Refresh
dependencies: []
requirement_refs:
- FR-001
- FR-002
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: "claude:sonnet-4-6:reviewer:reviewer"
history: []
agent_profile: debugger-debbie
authoritative_surface: docs/
execution_mode: planning_artifact
owned_files:
- docs/p0-baseline-refresh.md
role: investigator
tags: []
shell_pid: "12062"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load debugger-debbie
```

This configures your investigator persona. Proceed only after the profile is loaded.

---

## Objective

Run the full test suite on the current `main` HEAD of the spec-kitty repository, record the results, and determine which of the four P0 issue clusters (#1301, #1303, #1304, #1305) still reproduce on this commit. Produce a `baseline-refresh.md` document that gates all subsequent fix WPs.

This WP has **no code changes**. Its only deliverable is a written baseline document.

---

## Context

In 2026-05, the full test suite showed 217 failures (commit `4edf74472`). These were triaged into clusters and four P0 sub-issues were filed: #1301 (shared-package events drift), #1303 (charter synthesizer non-determinism), #1304 (doctrine/glossary anchor drift), #1305 (`next` exit-code regressions). Subsequent work on other missions may have resolved some of these. This WP establishes the current ground truth.

**Workspace**: `/Users/robert/spec-kitty-dev/spec-kitty-20260601-155758-52cVFZ/spec-kitty`

---

## Subtask T001 — Run Full Test Suite

**Purpose**: Establish the current failure count and commit SHA.

**Steps**:
1. Ensure you are on `main` with a clean working tree:
   ```bash
   git checkout main
   git status
   git log -1 --format="%H %ai %s"
   ```
2. Ensure the venv is warm:
   ```bash
   uv sync --frozen --all-extras
   ```
3. Run the full suite in headless mode:
   ```bash
   PWHEADLESS=1 pytest tests/ -q --tb=no -p no:cacheprovider 2>&1 | tee /tmp/baseline-full.txt
   ```
4. Capture the summary line from the output (the `=== N failed, M passed ... ===` line).

**Validation**:
- [ ] Command completed (even if slow — expect 10-20 min)
- [ ] Summary line captured with exact counts
- [ ] Commit SHA recorded

---

## Subtask T002 — Group Failures Into Clusters

**Purpose**: Identify which test modules are failing and group them by issue cluster.

**Steps**:
1. Extract the FAILED lines:
   ```bash
   grep "^FAILED" /tmp/baseline-full.txt | sort > /tmp/baseline-failed.txt
   cat /tmp/baseline-failed.txt
   ```
2. Map to clusters:
   - `tests/sync/` → #1301 candidate
   - `tests/contract/` → #1301 candidate
   - `tests/next/` → #1305 candidate
   - `tests/doctrine/` → #1304 candidate
   - `tests/charter/synthesizer/` → #1303 candidate
3. Count failures per cluster.
4. Record any failures outside these clusters (out of scope for this mission).

**Validation**:
- [ ] Each failing test mapped to a cluster or marked "out-of-scope"
- [ ] Counts recorded per cluster

---

## Subtask T003 — Confirm Still-Reproduces for Each P0 Cluster

**Purpose**: Run targeted tests for each cluster to get clean failure evidence (with tracebacks) and confirm the issue still exists.

**Steps**:
Run each command in sequence, capturing output:

```bash
# #1301 cluster
pytest tests/sync/ tests/contract/ -q --tb=short -p no:cacheprovider 2>&1 | tee /tmp/cluster-1301.txt

# #1305 cluster
pytest tests/next/ -q --tb=short -p no:cacheprovider 2>&1 | tee /tmp/cluster-1305.txt

# #1304 cluster
pytest tests/doctrine/ -q --tb=short -p no:cacheprovider 2>&1 | tee /tmp/cluster-1304.txt

# #1303 cluster
pytest tests/charter/synthesizer/ -q --tb=short -p no:cacheprovider 2>&1 | tee /tmp/cluster-1303.txt
```

For each cluster:
- If failures present → mark "STILL REPRODUCES" with failure count
- If all pass → mark "STALE (resolved by prior commits)"

**Validation**:
- [ ] All four targeted runs completed
- [ ] Reproduce/stale status recorded for each cluster

---

## Subtask T004 — Write Baseline-Refresh Document

**Purpose**: Produce the gating artifact that downstream WPs depend on.

**Steps**:
Create `docs/p0-baseline-refresh.md` with this structure:

```markdown
# Baseline Refresh — P0 Test Failures

**Date**: <ISO date>
**Commit SHA**: <full SHA from T001>
**Full suite result**: N failed, M passed, K skipped, W xfailed in Xs

## Cluster Status

| Issue | Cluster | Targeted failures | Status |
|-------|---------|-------------------|--------|
| #1301 | tests/sync/ + tests/contract/ | N | STILL REPRODUCES / STALE |
| #1303 | tests/charter/synthesizer/ | N | STILL REPRODUCES / STALE |
| #1304 | tests/doctrine/ | N | STILL REPRODUCES / STALE |
| #1305 | tests/next/ | N | STILL REPRODUCES / STALE |

## Fix Scope

WPs to execute: [list still-reproducing issues]
WPs to skip (stale): [list resolved issues]

## Out-of-Scope Failures

<list any failures outside the four clusters; do NOT fix these in this mission>
```

Commit the document:
```bash
git add docs/p0-baseline-refresh.md
git commit -m "docs: add baseline-refresh for P0 test failure mission"
```

**Validation**:
- [ ] `docs/p0-baseline-refresh.md` written and committed
- [ ] All four clusters have a clear STILL REPRODUCES / STALE status

---

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: Allocated by `lanes.json` when `spec-kitty agent action implement WP01 --agent claude` is invoked. Do not branch manually.

Implementation command:
```bash
spec-kitty agent action implement WP01 --agent claude
```

---

## Definition of Done

- [ ] Full suite run completed on current `main` HEAD
- [ ] Commit SHA recorded in baseline-refresh.md
- [ ] All four P0 clusters have STILL REPRODUCES or STALE status
- [ ] `baseline-refresh.md` committed to the mission branch
- [ ] Out-of-scope failures documented but not fixed

---

## Risks

- **Suite runtime**: ~15 min. If interrupted, the targeted runs in T003 are sufficient for gating; note the full run as incomplete.
- **Stale issues**: If all four clusters are stale, the mission is complete after WP01. Report this and stop.
- **uv sync failures**: If the venv can't be built, report as a blocker; do not proceed to fix WPs.

## Activity Log

- 2026-06-01T16:47:46Z – claude:sonnet-4-6:implementer:implementer – shell_pid=92178 – Started implementation via action command
- 2026-06-01T17:03:11Z – claude:sonnet-4-6:implementer:implementer – shell_pid=92178 – Ready for review (cycle 1/3). Targeted cluster runs complete. Only #1301 still reproduces (1 test). #1303, #1304, #1305 are stale.
- 2026-06-01T17:03:34Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=12062 – Started review via action command
