---
work_package_id: WP01
title: Repair Scope Confirmation and Freeze Coordination
dependencies: []
requirement_refs:
- C-004
- FR-001
planning_base_branch: fix/teamspace-mission-state-closeout-guards
merge_target_branch: fix/teamspace-mission-state-closeout-guards
branch_strategy: Planning artifacts for this mission were generated on fix/teamspace-mission-state-closeout-guards. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/teamspace-mission-state-closeout-guards unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: "claude:sonnet-4-6:operator:reviewer"
shell_pid: "74463"
history:
- at: '2026-05-11T10:18:12Z'
  event: created
agent_profile: operator
authoritative_surface: kitty-specs/teamspace-mission-state-repair-coordination-01KRB8AC/checklists/
execution_mode: planning_artifact
owned_files:
- kitty-specs/teamspace-mission-state-repair-coordination-01KRB8AC/checklists/wp01-gate-check.md
role: Operator / SRE
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load operator
```

This profile configures your behavior for operational runbook execution: careful sequencing, explicit gate-checks before proceeding, and writing evidence files for each step.

---

## Objective

Confirm the exact repair scope (which repos and branches), verify the PR #1017 gate is cleared, document the spec-kitty-runtime inclusion decision, and establish the contributor freeze window. No repair commands run until this WP is complete.

---

## Context

The TeamSpace mission-state repair touches three repos: `spec-kitty`, `spec-kitty-saas`, `spec-kitty-events`. A fourth repo, `spec-kitty-runtime`, is included only if its baseline audit shows `missions_with_teamspace_blockers > 0`. PR #1017 ("Close mission-state migration readiness gaps") must be merged before any `--fix` run, because it tightens the `spec-kitty-events>=5.0.0` dependency and adds dry-run audit blocker behavior. The gate was confirmed merged on 2026-05-11T09:40:29Z but must be re-verified programmatically before proceeding.

Workspace root: `/Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge/`
Repos: `spec-kitty/`, `spec-kitty-saas/`, `spec-kitty-events/`, `spec-kitty-runtime/` (evaluation only)

---

## T001 — Confirm target branches (main) for each repo

**Purpose**: Verify each repo is on `main` at a clean HEAD before any repair commands run.

**Steps**:
```bash
WORKSPACE=/Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge

for REPO in spec-kitty-saas spec-kitty-events spec-kitty-runtime; do
  echo "=== $REPO ==="
  cd $WORKSPACE/$REPO
  git status --short
  git log --oneline -3
  git rev-parse --abbrev-ref HEAD
done
```

Note: `spec-kitty` itself is on `fix/teamspace-mission-state-closeout-guards` (the repair coordination branch). The other three repos should be on `main`.

**Acceptance**: All three repos show clean working trees on `main`. Record the HEAD SHA of each repo.

**Evidence**: Write the SHA table to `wp01-gate-check.md`:
```
| Repo | Branch | HEAD SHA | Clean? |
|------|--------|----------|--------|
| spec-kitty-saas | main | <sha> | yes |
| spec-kitty-events | main | <sha> | yes |
| spec-kitty-runtime | main | <sha> | yes |
```

---

## T002 — Verify PR #1017 is merged (gate check)

**Purpose**: Programmatically confirm PR #1017 is merged. If it is not, the entire repair sequence must halt.

**Steps**:
```bash
gh pr view 1017 --repo Priivacy-ai/spec-kitty --json state,mergedAt,title
```

**Expected output**:
```json
{"mergedAt": "2026-05-11T09:40:29Z", "state": "MERGED", "title": "Close mission-state migration readiness gaps"}
```

**Gate rule**: If `state != "MERGED"`, stop. Do not proceed to WP02 or any repair step. Raise a blocking comment on #979.

**Evidence**: Append to `wp01-gate-check.md`:
```
## PR #1017 Gate
- State: MERGED
- Merged at: 2026-05-11T09:40:29Z
- Gate: CLEARED
```

---

## T003 — Coordinate contributor freeze on kitty-specs/ paths

**Purpose**: Prevent contributors from editing `kitty-specs/` in the repair-target repos during the repair window, which would create dirty-path conflicts with `--fix`.

**Steps**:

1. Post a freeze notice as a comment on issue #979:
```bash
gh issue comment 979 --repo Priivacy-ai/spec-kitty --body "$(cat <<'EOF'
## Repair Freeze Active

Repair sequence started at 2026-05-11T10:18:12Z.

**Please do not push commits to `kitty-specs/` paths in `spec-kitty`, `spec-kitty-saas`, or `spec-kitty-events`** until the repair PRs are raised and reviewed.

Repair scope: spec-kitty, spec-kitty-saas, spec-kitty-events
Estimated duration: ~2 hours
Operator: Claude Code (automated repair)
Tracking: spec-kitty#979, spec-kitty#920
EOF
)"
```

2. Verify each target repo has a clean `kitty-specs/` tree:
```bash
for REPO in spec-kitty-saas spec-kitty-events; do
  echo "=== $REPO ==="
  cd /Users/robert/spec-kitty-dev/spec-kitty-20260511-103721-tglUge/$REPO
  git diff --name-only HEAD | grep "kitty-specs/" || echo "clean"
done
```

**Acceptance**: Freeze comment posted, all repos clean in `kitty-specs/`.

---

## T004 — Document spec-kitty-runtime inclusion decision

**Purpose**: Record the inclusion criterion for spec-kitty-runtime before the baseline audit phase begins, so there is no ambiguity later.

**Decision**: Include spec-kitty-runtime in WP02 audit only. Include it in WP03 repair only if `missions_with_teamspace_blockers > 0` in its baseline audit.

**Rationale**: Runtime's status history is primarily side logs (`run.events.jsonl`), classified as `local_only_side_log` by PR #19. PR #19 is already merged on main. Runtime is unlikely to have TeamSpace blockers.

**Steps**: Append to `wp01-gate-check.md`:
```
## spec-kitty-runtime Inclusion Decision
- Criterion: include in WP03 repair ONLY if missions_with_teamspace_blockers > 0 in WP02 baseline audit
- Rationale: PR #19 already classified side logs as local_only_side_log; no blockers expected
- Status: decision documented; runtime will be audited in WP02 but repair will only run if criterion is met
```

---

## Branch Strategy

This WP produces only planning artifacts (the `wp01-gate-check.md` evidence file) committed to `fix/teamspace-mission-state-closeout-guards` in the spec-kitty repo. No execution worktree is created. All shell commands run in-place in the relevant repo directories.

- Planning/base branch: `fix/teamspace-mission-state-closeout-guards`
- Merge target: `fix/teamspace-mission-state-closeout-guards`

---

## Definition of Done

- [ ] T001: Branch/HEAD table written for all three repos; all show clean main
- [ ] T002: PR #1017 confirmed MERGED; gate cleared in evidence file
- [ ] T003: Freeze comment posted on #979; repos clean in kitty-specs/
- [ ] T004: Runtime inclusion criterion documented in evidence file
- [ ] `wp01-gate-check.md` written to `checklists/` and committed

---

## Risks

- **PR #1017 not merged**: If gate check fails, halt immediately. Do not proceed to WP02. Post a blocking comment on #979.
- **Dirty working tree**: If any repo has uncommitted changes in `kitty-specs/`, pause and investigate before running audit commands.
- **Freeze not respected**: If a contributor pushes to `kitty-specs/` during the repair window, re-audit from a fresh pull before proceeding to WP03.

---

## Reviewer Guidance

Verify `wp01-gate-check.md` contains:
1. SHA table for all three repos (all on main, clean)
2. PR #1017 gate section with `state: MERGED` and a real `mergedAt` timestamp
3. Freeze comment URL or confirmation
4. Runtime inclusion decision with criterion

## Activity Log

- 2026-05-11T10:25:01Z – claude:sonnet-4-6:operator:implementer – shell_pid=74309 – Started implementation via action command
- 2026-05-11T10:25:54Z – claude:sonnet-4-6:operator:implementer – shell_pid=74309 – Gate checks complete: PR #1017 MERGED, all repos on clean main, freeze comment posted on #979, runtime inclusion criterion documented
- 2026-05-11T10:26:04Z – claude:sonnet-4-6:operator:reviewer – shell_pid=74463 – Started review via action command
- 2026-05-11T10:26:25Z – claude:sonnet-4-6:operator:reviewer – shell_pid=74463 – Review passed: PR #1017 confirmed MERGED, all repos on clean main, freeze posted, runtime criterion documented
