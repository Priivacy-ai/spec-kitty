---
work_package_id: WP01
title: Blocker Verification
dependencies: []
requirement_refs:
- FR-001
- FR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
agent: "claude:sonnet-4-6:implementer:implementer"
shell_pid: "59100"
history:
- date: '2026-05-20'
  event: created
agent_profile: implementer
authoritative_surface: kitty-specs/phase4-canary-gate-01KS1W46/tasks/
execution_mode: planning_artifact
owned_files:
- kitty-specs/phase4-canary-gate-01KS1W46/tasks/WP01-blocker-verification.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load implementer
```

Then read this entire prompt before taking any action.

---

## Objective

Verify that both Phase-4 blocker issues (#1141 and #1182) are **closed** on
`Priivacy-ai/spec-kitty` AND that the fix for #1141 is substantive — a
behavioral change in the `OfflineQueue.queue_event` call chain backed by a
test that fails without the fix and passes with it.

**This is a hard gate.** If either issue is still OPEN, or if the #1141 fix
is diagnostic-only (logging changes with no behavioral code change + no new
failing test), stop here and report. Do not proceed to WP02.

---

## Context

`rc15` landed a diagnostic breadcrumb for #1141 that confirmed `fire_saas_fanout`
saw the correct `in_review → planned` transition at invocation time. The canary
at `artifacts/sync_identity_boundary/rc15-attempt1/run-1.json` still showed
scenario 4 asserting `from='for_review' to='in_review'` — meaning the rollback
event was either not reaching `OfflineQueue.queue_event` or was being silently
overwritten by a prior coalesced event. The issue was re-opened.

`#1182` is new: `sync now` sees durably-queued events as `unknown` errors when
the 5s final-sync flush times out. The fix must change the error-classification
branch, not extend the timeout.

---

## Subtask T001: Query #1141 State

**Purpose**: Confirm the issue is CLOSED on origin before touching anything else.

```bash
unset GITHUB_TOKEN
gh issue view 1141 --repo Priivacy-ai/spec-kitty \
  --json state,closedAt,title,body \
  | python3 -m json.tool
```

**Expected**: `"state": "CLOSED"` with a non-null `closedAt`.

**If OPEN**: Stop immediately. Report:
```
GATE BLOCKED: spec-kitty#1141 is still OPEN.
state: OPEN
Do not proceed to WP02. Wait for the fix-agent track to close this issue.
```

**CLAUDE.md note**: If `gh` returns a scope error, unset `GITHUB_TOKEN` and retry. The keyring token typically has `repo` scope.

---

## Subtask T002: Query #1182 State

**Purpose**: Confirm the second blocker is also CLOSED.

Run concurrently with T001:

```bash
unset GITHUB_TOKEN
gh issue view 1182 --repo Priivacy-ai/spec-kitty \
  --json state,closedAt,title,body \
  | python3 -m json.tool
```

**Expected**: `"state": "CLOSED"` with a non-null `closedAt`.

**If OPEN**: Stop immediately. Report:
```
GATE BLOCKED: spec-kitty#1182 is still OPEN.
state: OPEN
Do not proceed to WP02. Wait for the fix-agent track to close this issue.
```

---

## Subtask T003: Gate Check — Both Must Be CLOSED

**Purpose**: Only continue if both T001 and T002 confirmed CLOSED.

If either is OPEN: halt and present the report format above.
If both are CLOSED: proceed to T004.

---

## Subtask T004: Inspect #1141 Merge Commit Diff

**Purpose**: Confirm the fix changes behavior, not just log output.

First, find the merge commit SHA from the issue or PR:

```bash
unset GITHUB_TOKEN
# Find the closing PR
gh issue view 1141 --repo Priivacy-ai/spec-kitty \
  --json closingPullRequests \
  | python3 -m json.tool

# Get the merge commit SHA from the PR
gh pr view <PR_NUMBER> --repo Priivacy-ai/spec-kitty \
  --json mergeCommit,mergedAt \
  | python3 -m json.tool
```

Then inspect the diff for the key files:

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty
git fetch origin main
git show <MERGE_SHA> -- \
  src/specify_cli/sync/queue.py \
  src/specify_cli/status/adapters.py \
  src/specify_cli/sync/
```

**What you are looking for**:
- Changes to `queue_event` method logic (not just `logger.*` lines)
- Changes to the `WPStatusChanged` handling path in `emit_wp_status_changed` or `fire_saas_fanout`
- Any change that prevents silent coalescing or overwrite of `WPStatusChanged` rows

**Red flag — reject as diagnostic-only if**:
- The only changed lines are `logger.debug(...)`, `logger.info(...)`, `logger.warning(...)` calls
- No change to control flow, conditional logic, or database writes
- No change to how `WPStatusChanged` events are stored or ordered in the queue

**Accept if**:
- `queue_event` or its callers have a behavioral code change (new conditional, changed INSERT logic, coalescing exclusion for `WPStatusChanged`, ordering fix, etc.)

---

## Subtask T005: Verify #1141 Test Coverage

**Purpose**: The fix must be backed by a test that fails without it.

From the same merge commit diff:

```bash
git show <MERGE_SHA> -- tests/sync/ tests/specify_cli/sync/
```

**What you are looking for**:
- A test that sets up the scenario 4 failure: `move-task --to planned` (review rejection rollback)
- The test must assert that the LAST queued `WPStatusChanged` event has `from='in_review' to='planned'` (not `from='for_review' to='in_review'`)
- The test comment or commit message should indicate it was added for this fix

**If no such test exists**:
```
GATE BLOCKED: spec-kitty#1141 fix appears to be diagnostic-only.
The merge commit diff shows only logging changes (or no test covers the
in_review → planned rollback assertion).
Push back: a substantive fix requires a test that fails on pre-fix code.
Do not proceed to WP02.
```

---

## Subtask T006: Inspect #1182 Merge Commit Diff

**Purpose**: Confirm `sync now` no longer misclassifies queued-pending events as `unknown` errors.

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty
git show <MERGE_SHA_FOR_1182> -- \
  src/specify_cli/cli/commands/sync.py \
  src/specify_cli/sync/
```

**What you are looking for**:
- The error-classification branch that produces `"unknown"` errors for events that are durably queued but unflushed within the 5s window
- The fix should reclassify those events as `queued_pending` (or similar non-error status) rather than treating the 5s timeout expiry as a failure

**Accept if**:
- The classification logic for `event_loop_unavailable`-triggered results is changed from error to queued/pending
- A test verifies the reclassification

**If only timeout extension**: flag it — extending the timeout is option B, which was rejected in the research.

---

## Definition of Done

- [ ] T001: `#1141` confirmed CLOSED with `closedAt` non-null
- [ ] T002: `#1182` confirmed CLOSED with `closedAt` non-null
- [ ] T003: Both issues CLOSED; gate passed
- [ ] T004: #1141 merge diff shows behavioral change (not logging-only)
- [ ] T005: Test added that covers `in_review → planned` rollback assertion
- [ ] T006: #1182 merge diff shows error-classification change for queued-pending events

---

## Risks

| Risk | Mitigation |
|------|-----------|
| #1141 fix is another diagnostic landing | Reject in T005; do not proceed |
| GitHub token scope errors | `unset GITHUB_TOKEN` per CLAUDE.md |
| Merge commit not findable via gh | Check `git log --oneline -20 origin/main` for the fix commit |

---

## Reviewer Guidance

- Verify the gate checks ran in the order T001/T002 → T003 → T004/T005/T006
- Confirm the agent did NOT proceed to WP02 if any gate check failed
- The diff inspection must be substantive — "looks like a real fix" is not sufficient; demand the test evidence

---

## Branch Strategy

Planning branch: `main`. Merge target: `main`.
This WP runs in the root repo checkout. No worktree needed.
Run `spec-kitty agent action implement WP01 --agent claude` to start this WP.

## Activity Log

- 2026-05-20T05:19:00Z – claude:sonnet-4-6:implementer:implementer – shell_pid=59100 – Started implementation via action command
