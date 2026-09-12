---
work_package_id: WP03
title: Retained Evidence and Identical Adoption
dependencies:
- WP02
requirement_refs:
- C-001
- C-006
- FR-001
- FR-003
- FR-005
- FR-006
- NFR-002
planning_base_branch: mission/durable-concurrent-review-cycle-records
merge_target_branch: mission/durable-concurrent-review-cycle-records
branch_strategy: Planning artifacts for this mission were generated on mission/durable-concurrent-review-cycle-records. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/durable-concurrent-review-cycle-records unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-durable-concurrent-review-cycle-records-01M0QRX7
base_commit: a831487d364078d0a85d3ce3a56633a9ac1336b5
created_at: '2026-08-24T05:14:13.339853+00:00'
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
phase: Phase 2 - Evidence durability
history:
- at: '2026-08-23T18:37:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/artifacts.py
- src/specify_cli/review/cycle.py
- tests/review/test_artifacts_yaml_seam.py
- tests/review/test_cycle.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/3235
---

# Work Package Prompt: WP03 – Retained Evidence and Identical Adoption

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro`; apply its strict typing, pytest, bug-fix, and boundary guidance before reading further.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

## ⚠️ IMPORTANT: Review Feedback

Inspect `review_ref` through `spec-kitty agent tasks status --mission 01M0QRX7`. Address all feedback and append chronological Activity Log evidence.

## Objectives & Success Criteria

Refactor review-cycle evidence persistence so it tells the truth about Git outcomes, retains recoverable artifacts on failure, adopts an identical retry without allocating a duplicate, and verifies the exact evidence at the governed destination ref.

Completion requires:

- no warning-only false success from returned router failures;
- no deletion of a written artifact after automatic persistence failure;
- a typed result that distinguishes durable, busy, persistence failure, and local-only inputs needed by orchestration;
- identical retry matching from existing canonical evidence fields, with no persisted verdict field;
- same path and bytes reused for an identical pending record;
- non-identical submissions never adopting or overwriting pending evidence;
- exact governed-ref read-back before durable classification;
- safe treatment of `committed`, `unchanged`, returned error, wrong-surface no-op, exception, and interruption;
- preservation of unrelated working-tree and index state.

## Context & Constraints

Prerequisite: WP02's queue primitive must be available in the lane base for WP04 orchestration and test fixtures. WP03 does not acquire it: `cycle.py` must expose one non-acquiring persistence operation that WP04 invokes inside its sole queue lease.

Read:

- `plan.md` sections Critical-section and Retained-record adoption.
- `data-model.md` entities and state transitions.
- `contracts/verdict-save-queue.md` automatic outcome and retry tables.
- `research.md` decisions on retention and independent read-back.
- `src/specify_cli/review/cycle.py`, especially allocation/write under `feature_status_lock`, later commit handling, and exception cleanup.
- `src/specify_cli/coordination/commit_router.py` and the safe-commit result model; consume rather than duplicate them.
- the accepted review-cycle placement ADR.

The event log is not owned here. This WP changes evidence persistence only. Do not modify command orchestration, generic router code, status locks, or placement resolution. Never instantiate or reacquire the verdict queue in `cycle.py`; nested acquisition of the same file lock can self-timeout.

## Branch Strategy

- **Planning base**: `mission/durable-concurrent-review-cycle-records`
- **Merge target**: `mission/durable-concurrent-review-cycle-records`
- **Dependency**: WP02.
- **Execution**: `spec-kitty agent action implement WP03 --agent codex --mission 01M0QRX7`; Spec Kitty uses `lanes.json` to select a dependency-correct lane worktree.

## Subtasks & Detailed Guidance

### T011 – Introduce a typed persistence outcome

**Purpose**: Replace Boolean/warning ambiguity with an outcome the command can enforce.

**Steps**:

1. Model the smallest immutable typed result in `cycle.py` or an existing owned type surface.
2. Include classification, durability Boolean, evidence relative path, governed destination ref when known, stable reason, and human diagnostic.
3. Make impossible combinations unrepresentable where practical: durable requires evidence and destination; non-durable requires a reason.
4. Preserve compatibility only where callers genuinely require it; do not silently coerce failure back to `False` if that can be ignored.
5. Separate `local_only` from automatic failure.
6. Keep verdict value out of the evidence result and artifact.

**Validation**: focused construction tests cover every classification and invalid state.

### T012 – Retain evidence on all automatic failures

**Purpose**: Preserve recovery material and operator observability.

**Steps**:

1. Remove cleanup that unlinks a just-written artifact when commit raises.
2. Treat returned `error`, wrong-surface no-op, exception, and timeout as explicit persistence failures.
3. Return the retained path when allocation/write completed.
4. Leave bytes unchanged after failure so retry identity is stable.
5. Do not emit a success-equivalent signal or claim the record is committed.
6. Keep validation/write failures before a complete artifact distinct; do not retain invalid partial files.

**Tests**: invert existing tests that currently expect deletion and add returned-error retention assertions.

### T013 – Adopt an identical pending record

**Purpose**: Let the operator retry without deleting an orphan or creating a misleading next cycle.

**Steps**:

1. In the non-acquiring persistence operation—called by WP04 while its sole verdict-queue lease is already held—take only the short allocation lock and enumerate candidate review-cycle artifacts for the same mission/WP.
2. Parse candidates through the canonical review-cycle parser rather than regexing filenames only.
3. Compare reviewer, canonical rendered body, and canonical affected-file collection.
4. Ignore timestamp and cycle allocation metadata only.
5. Require the candidate to be absent from the governed destination before classifying it pending.
6. Choose deterministically if corruption leaves multiple identical pending candidates; fail explicitly rather than guessing if ambiguity cannot be resolved safely.
7. Reuse the exact path and bytes; do not allocate the next cycle.
8. A different reviewer, body, or affected-file set must not adopt the candidate.
9. Add a boundary test proving this operation never calls the WP02 queue acquisition seam; WP04 owns acquisition and compensation serialization.

**Authority safeguard**: do not persist verdict, approval/rejection state, or an opaque verdict-derived fingerprint in the artifact.

### T014 – Verify the governed destination

**Purpose**: Define committed by reachability at the actual placement-selected ref.

**Steps**:

1. Consume the existing placement/router outcome to identify the destination ref.
2. After a `committed` result, read the exact relative path from that ref.
3. Compare committed bytes/content identity to the selected local artifact.
4. For `unchanged`, accept only an adopted identical record already proven at the destination; ordinary unchanged without proof is failure.
5. Handle a recovery exception carrying a commit SHA conservatively: inspect destination state before deciding, never infer from the exception type alone.
6. Return destination details needed by command output and event reference.

### T015 – Preserve unrelated repository state

**Purpose**: A retry must not damage user staging or unrelated changes.

**Cases**:

- failed artifact is untracked;
- failed artifact is staged;
- failed artifact is partially staged;
- unrelated tracked and untracked files exist;
- safe-commit temporarily manipulates the index;
- adopted path is already committed but response was interrupted.

Assert unrelated index/worktree state is byte-for-byte and status-for-status preserved. Use existing safe-commit isolation rather than adding custom whole-index restore logic.

### T016 – Complete the cycle truth-table and recovery tests

**Purpose**: Make all semantics reviewable without command-level ambiguity.

**Required rows**:

- `committed` plus read-back → durable;
- `committed` but read-back missing/mismatched → failure, retained;
- ordinary `unchanged` → failure;
- adopted already-committed identical record plus read-back → idempotent durable;
- returned error and wrong-surface no-op → failure, retained;
- raised exception → failure, retained;
- interruption after write/before commit → retained and adoptable;
- identical retry → same cycle/path/bytes, no next cycle;
- non-identical retry → no impersonating adoption;
- local-only writer input → explicit local-only, no queue/commit.

## Test Strategy

```bash
uv run python -m pytest tests/review/test_cycle.py -n0 -q --tb=short
uv run ruff check src/specify_cli/review/cycle.py tests/review/test_cycle.py
uv run mypy --strict src/specify_cli/review/cycle.py
```

Generate coverage XML for the owned tests and run the repository-supported `uv run diff-cover <coverage-xml> --compare-branch=origin/main --fail-under=90 --include 'src/specify_cli/review/cycle.py'`; record the exact command, base, report path, percentage, and exit status.

## Risks & Mitigations

- **Duplicate pending artifacts**: deterministic explicit failure beats guessing.
- **Second verdict authority**: match only evidence-content fields; current verdict remains event-sourced.
- **Wrong ref**: query governed placement and read it directly.
- **Index damage**: exercise clean/staged/partial cases and preserve unrelated staging.
- **Compatibility pressure**: update owned tests toward the new typed contract; downstream call-site changes belong to WP04.

## Review Guidance

Reject if any automatic failure deletes evidence, if identical retry allocates a new cycle, if `unchanged` is accepted without destination proof, if a verdict/fingerprint becomes artifact authority, or if unrelated staging changes. Review the full truth table rather than one happy path.

## Definition of Done

- T011–T016 marked done event-sourced.
- All owned tests pass after WP02 dependency is present.
- Retention/adoption semantics match the contract exactly, including proof that `cycle.py` never reacquires the queue.
- Ruff, strict mypy, and changed-line coverage gates pass.
- No out-of-ownership production edit is made without recorded rationale.

## Activity Log

- 2026-08-23T18:37:05Z – system – Prompt created.

Use `spec-kitty agent tasks move-task WP03 --to for_review --mission 01M0QRX7` when ready.
