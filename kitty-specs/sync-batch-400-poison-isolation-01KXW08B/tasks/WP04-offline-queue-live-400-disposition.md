---
work_package_id: WP04
title: Offline-queue LIVE whole-batch-400 disposition fix
dependencies: []
requirement_refs:
- FR-005
- C-001
- C-004
tracker_refs:
- '#2736'
planning_base_branch: fix/2736-batch-400-poisoning-isolation
merge_target_branch: fix/2736-batch-400-poisoning-isolation
branch_strategy: Planning artifacts for this mission were generated on fix/2736-batch-400-poisoning-isolation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/2736-batch-400-poisoning-isolation unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
phase: Phase 1 - live P1 fix (WP01-independent)
assignee: ''
agent: "claude"
shell_pid: "1604460"
shell_pid_created_at: "1784429585.61"
history:
- at: '2026-07-19T02:11:31Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
create_intent:
- tests/sync/test_batch_400_no_details_poison_2736.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/sync/batch.py
- tests/sync/test_batch_400_no_details_poison_2736.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Offline-queue LIVE whole-batch-400 disposition fix

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Fix the **LIVE** whole-batch-400 poison in the offline-queue (legacy) sync path.

**Post-tasks squad correction (paula, verified from source — do not skip this):** the offline-queue poison
was originally scoped at `_record_all_events_failed:475-499`, but that function is **DORMANT** — all seven
live callers pass `transient=True`, so its `rejected` branch never fires. The **live** poison is
`_parse_error_response`'s no-`details` else-branch (`sync/batch.py:967-985`), reached from the live
`batch_sync` 400 handler (`sync/batch.py:1188`) via `sync/background.py:455` and `sync_all_queued_events`.
On a whole-batch 400 with NO per-event `details`, it stamps EVERY event `status="rejected"`, and
`process_batch_results` bumps `retry_count` on every innocent (only `rejected` mutates retry — see the
`failed_results` docstring).

**Done when**: on a whole-batch 400 with no per-event details, innocents are NOT marked `rejected` and their
`retry_count` is NOT bumped (treated as transient); the per-event-`details` path is unchanged and still
rejects the server-adjudicated events. `tests/sync/` green.

## Context & Constraints

- **Plan**: IC-05. **Spec**: FR-005, SC-007.
- **Fix location**: `_parse_error_response`'s **else-branch only** (`sync/batch.py:967-985`) — when there are
  no structured per-event `details`, the server did NOT adjudicate individual events, so a batch-level 400
  must be treated as **transient** (mirror the sibling 403/5xx branch at ~`:1197-1205`, which already passes
  `transient=True` and does not bump retry). **Do NOT touch the per-event `details` path (`:923-966`)** — that
  IS legitimate server-adjudicated per-event rejection.
- Fix within the legacy `dict`/`BatchEventResult` model. Do NOT import the receiver bisect (different bounded
  context — mechanism vs disposition).
- **WP01-independent**: this fix does not consume the partition primitive. No dependency; ships in
  parallel-group 0.
- `ruff`/`mypy` clean, zero new suppressions.

## Branch Strategy

- **Strategy**: per computed lane from `lanes.json`
- **Planning base branch**: `fix/2736-batch-400-poisoning-isolation`
- **Merge target branch**: `fix/2736-batch-400-poisoning-isolation`

## Subtasks & Detailed Guidance

### Subtask T015 [red] – Live 400-no-details poison test

- **Purpose**: Pin the live poison and guard the adjudicated path before fixing.
- **Steps**: New `tests/sync/test_batch_400_no_details_poison_2736.py`. Drive the live `batch_sync` (or
  `_parse_error_response` directly) with a whole-batch 400 whose body has an `error` but NO per-event
  `details`, over a mixed batch. Assert innocents are NOT `status="rejected"` and their `retry_count` is NOT
  bumped by `process_batch_results`. Add a SECOND assertion (regression guard): a 400 WITH per-event
  `details` still rejects exactly the named events (the adjudicated path stays intact). RED until T016.
- **Files**: `tests/sync/test_batch_400_no_details_poison_2736.py`.

### Subtask T016 – Fix the no-`details` else-branch

- **Purpose**: Stop the live whole-batch poisoning.
- **Steps**: In `_parse_error_response`'s else-branch (`sync/batch.py:967-985`), stop stamping every event
  `status="rejected"` on a no-adjudication 400. Treat it as transient — no `rejected`, no `retry_count` bump
  — consistent with the sibling batch-level branches (403/5xx pass `transient=True`). Keep the operator-facing
  error summary. Leave the `details` path (`:923-966`) untouched.
- **Files**: `src/specify_cli/sync/batch.py`.

## Test Strategy

- `PWHEADLESS=1 pytest tests/sync/ -q` green at close. Run T015 RED first (prove it fails without the fix).
- **Pre-review gate DOES cover this WP** — `tests/sync/**` maps to the focused `sync` CI group, so the gate
  runs the changed test (unlike WP05's architectural tests).

## Risks & Mitigations

- **Over-reaching into the adjudicated `details` path** → the T015 second assertion pins it untouched.
- **Mis-identifying the branch** → the poison is the `else` (no `per_event_details`), not the `if`.

## Review Guidance

- Confirm the fix is in the no-`details` else-branch only; the `details` path still rejects named events.
- Confirm no `retry_count` bump on innocents; no receiver-bisect import.

## Activity Log

- 2026-07-19T02:11:31Z – system – Prompt created.
- 2026-07-19T02:53:38Z – claude – shell_pid=1604460 – Assigned agent via action command
- 2026-07-19T03:10:45Z – claude – shell_pid=1604460 – Moved to for_review
- 2026-07-19T03:21:41Z – user – shell_pid=1604460 – Approved: failed_transient traced through process_batch_results (no DELETE, no retry bump — non-poisoning); adjudicated details path byte-unchanged; dormant fn untouched; RED-first isolated to status string; ruff/mypy clean. 6 parallel reds all verified pre-existing (4 real-port flakes + 2 CI-env).
