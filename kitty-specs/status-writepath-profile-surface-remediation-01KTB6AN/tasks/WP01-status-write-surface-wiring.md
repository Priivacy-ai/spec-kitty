---
work_package_id: WP01
title: Status write-surface wiring + slug guard
dependencies: []
requirement_refs:
- FR-004
- FR-007
tracker_refs:
- '1667'
planning_base_branch: feature/status-writepath-profile-surface-remediation
merge_target_branch: feature/status-writepath-profile-surface-remediation
branch_strategy: Planning artifacts for this mission were generated on feature/status-writepath-profile-surface-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/status-writepath-profile-surface-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: 'Lane A — #1667 ownership'
agent: "claude"
assignee: "claude"
history:
- at: '2026-06-05T08:32:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/status.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/status.py
- src/specify_cli/status/aggregate.py
- tests/unit/status/test_mission_status_aggregate.py
- tests/status/test_agent_status_emit_aggregate_wiring.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Status write-surface wiring + slug guard

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Realize #1667's single-domain status-write ownership (FR-004) and add an identifier-safety guard (FR-007).

- **FR-004**: `spec-kitty agent status emit` routes its write through `MissionStatus.transition()` (+ `MissionStatus.save()` where the command relies on the transactional commit) instead of calling `emit_status_transition_transactional(...)` directly. The aggregate becomes the **sole** entry point for status writes. **Behavior-preserving** — same emitted event, same CLI output, same exit codes.
- **FR-007**: `MissionStatus.load()` validates `mission_slug` against `^[A-Za-z0-9_-]+$` (`.isascii()` must be true) at entry and raises a typed error on mismatch.

**Done when**: `agent status emit` no longer calls `emit_status_transition_transactional` directly; a malformed slug is rejected at `load()`; all new + existing status tests pass; **no change to `coordination/transaction.py`**.

## Context & Constraints

- **Why**: the dialectic review confirmed the aggregate write methods are tested (#1682) but **unwired** — `agent status emit` bypasses them (`cli/commands/agent/status.py:275`), so the domain-ownership invariant is unmet. See [spec.md](../spec.md) FR-004, [plan.md](../plan.md) D-1, [dialectic-review.md](../dialectic-review.md).
- **Key fact**: `MissionStatus.transition()` already delegates to `emit_status_transition_transactional`, so routing through it is behavior-preserving by construction.
- **Constraints**: C-001 (no change to `coordination/transaction.py`), C-004 (ULID/slug identity only), DIRECTIVE_010/011 (ASCII allowlist + regression coverage).

## Branch Strategy

- **Strategy**: see frontmatter `branch_strategy`
- **Planning base branch**: `feature/status-writepath-profile-surface-remediation`
- **Merge target branch**: `feature/status-writepath-profile-surface-remediation`

## Subtasks & Detailed Guidance

### Subtask T001 – Route `agent status emit` through `ms.transition()`

- **Purpose**: make the aggregate the sole write entry point (FR-004).
- **Steps**:
  1. In `cli/commands/agent/status.py` `emit(...)` (around the current direct call at line ~275), keep the `MissionStatus` instance currently resolved via `_resolve_feature_dir_for_repo` (which calls `MissionStatus.load()` and **discards** the instance). Refactor so the resolved `MissionStatus` object is retained.
  2. Replace `event = emit_status_transition_transactional(TransitionRequest(...))` with `event = ms.transition(TransitionRequest(...))` using the same request fields.
  3. Leave the `TransitionRequest` construction unchanged.
- **Files**: `src/specify_cli/cli/commands/agent/status.py`
- **Notes**: if `_resolve_feature_dir_for_repo` only returns `read_dir`, extend it (or add a sibling helper) to also return the `MissionStatus` instance so the command does not `load()` twice.

### Subtask T002 – Preserve commit semantics via `ms.save()`

- **Purpose**: ensure the transactional commit + receipt behavior is identical.
- **Steps**:
  1. Confirm whether the prior direct path committed inside `emit_status_transition_transactional` or required a follow-up commit. Mirror that: if a commit step is needed, call `ms.save(operation="status-emit")` and surface the `CommitReceipt` exactly as before.
  2. Preserve any JSON output fields (event id, commit hash) the command currently emits.
- **Files**: `src/specify_cli/cli/commands/agent/status.py`

### Subtask T003 – Slug allowlist guard at `MissionStatus.load()`

- **Purpose**: identifier safety (FR-007, DIRECTIVE_010/011).
- **Steps**:
  1. At the top of `MissionStatus.load()` (`status/aggregate.py`), validate `mission_slug` against `re.compile(r"^[A-Za-z0-9_-]+$")` (compile with `re.ASCII` or assert `mission_slug.isascii()`).
  2. On mismatch raise a typed error (reuse `MissionMetadataUnavailable` or add a dedicated `InvalidMissionSlug` if clearer) with a message naming the offending slug.
- **Files**: `src/specify_cli/status/aggregate.py`

### Subtask T004 – Unit test: slug guard

- **Steps**: in `tests/unit/status/test_mission_status_aggregate.py`, add tests: (a) a normal slug passes; (b) an accented-Latin slug (e.g. `"café-mission"`) is rejected; (c) assert the produced/validated identifier is `.isascii()`.
- **Files**: `tests/unit/status/test_mission_status_aggregate.py`

### Subtask T005 – Integration test: emit routes through aggregate

- **Steps**: in a new `tests/status/test_agent_status_emit_aggregate_wiring.py`, drive `agent status emit` end-to-end (reuse the worktree/coord fixture pattern from `tests/architectural/test_execution_context_parity.py`) and assert the lane transition lands. Assert (via patching/spy) that `MissionStatus.transition` is invoked and `emit_status_transition_transactional` is **not** called directly from the command.
- **Files**: `tests/status/test_agent_status_emit_aggregate_wiring.py`

### Subtask T006 – Behavior-parity verification

- **Steps**: assert the emitted `StatusEvent` fields and the command's JSON output are identical to a captured baseline of the prior direct path (snapshot compare).
- **Files**: `tests/status/test_agent_status_emit_aggregate_wiring.py`

## Test Strategy

- `pytest tests/unit/status/test_mission_status_aggregate.py tests/status/test_agent_status_emit_aggregate_wiring.py`
- `mypy --strict` on touched modules; `ruff check`.

## Risks & Mitigations

- **Touching the live write path** → keep strictly behavior-preserving; rely on the existing `transition()`→`emit_status_transition_transactional` delegation; snapshot-compare outputs (T006).
- **Double `load()`** → retain the instance from the first resolution (T001 note).

## Review Guidance

- Verify zero direct `emit_status_transition_transactional` calls remain in `agent/status.py`.
- Verify `coordination/transaction.py` is untouched.
- Verify slug-guard regression includes an accented case and an `.isascii()` assertion.

## Activity Log

- 2026-06-05T08:32:05Z – system – Prompt created.
- 2026-06-05T12:53:54Z – claude – Moved to in_progress
- 2026-06-05T12:54:28Z – claude – Implemented via bypass; tests green
