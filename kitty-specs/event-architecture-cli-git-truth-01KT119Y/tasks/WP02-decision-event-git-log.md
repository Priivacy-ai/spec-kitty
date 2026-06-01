---
work_package_id: WP02
title: Decision Event Git Log
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-event-architecture-cli-git-truth-01KT119Y
base_commit: b437dea359ce00f466a0f34aa34945e2208bc872
created_at: '2026-06-01T08:35:33.200680+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
agent: "claude:claude-sonnet-4-6:orchestrator:orchestrator"
shell_pid: "72351"
history:
- date: '2026-06-01'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/events/
execution_mode: code_change
owned_files:
- src/specify_cli/events/decision_log.py
- src/specify_cli/next/runtime_bridge.py
- tests/specify_cli/events/test_decision_log.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Implement `DecisionGitLog` — an emitter that appends sanitized `DecisionInputRequested` and `DecisionInputAnswered` events to `kitty-specs/<mission>/decisions.events.jsonl`, triggers `safe_commit()` on each answered decision, and delegates all other events to an inner emitter. Wire it into the engine via `runtime_bridge.py` and remove `DecisionInputRequested/Answered` from the `OfflineQueue` write path.

**Implement command**: `spec-kitty agent action implement WP02 --agent claude`

**Prerequisite**: WP01 must be merged (provides `sanitize_event_for_log`).

---

## Context

**Decision emit strategy** (from planning research, Decision DM-01KT11K6629V343DBE4NXQEFJ4):
- Append `DecisionInputRequested` to `decisions.events.jsonl` immediately when emitted.
- Append `DecisionInputAnswered` immediately when received.
- Call `safe_commit()` triggered by the answer — captures the request+answer pair in one commit.
- Orphaned request lines (crash before answer) are left; the SaaS handles gracefully.

**Key existing files to read before starting**:
- `src/specify_cli/next/_internal_runtime/events.py` — `RuntimeEventEmitter` protocol + `JsonlEventLog` class
- `src/specify_cli/next/runtime_bridge.py` — where the concrete emitter is constructed
- `src/specify_cli/git/commit_helpers.py:742` — `safe_commit()` signature
- `src/specify_cli/core/paths.py` — for `kitty-specs/` path resolution if needed

**`safe_commit()` constraint**: Refuses to commit to `main` (protected). Decision commits must land on the coordination branch. The coordination branch is `kitty/mission-<slug>`. This must be passed as `destination_ref`. Verify that `runtime_bridge.py` has or can receive the coordination branch at construction time.

**JSONL format**: One JSON object per line, `json.dumps(sort_keys=True, separators=(",", ":"))`. Same as `status.events.jsonl`.

**Spec references**: FR-001, FR-002, FR-003, FR-004, FR-005

---

## Branch Strategy

- Planning base: `main`
- Final merge target: `main`
- Execution worktree resolved by `spec-kitty agent action implement WP02 --agent <name>`.

---

## Subtask Guidance

### T006 — Implement `DecisionGitLog` class — constructor and delegation

**Purpose**: Create the class skeleton that wraps an inner emitter and establishes the `decisions.events.jsonl` write path.

**Steps**:
1. Create `src/specify_cli/events/decision_log.py`.
2. Define `DecisionGitLog` implementing the `RuntimeEventEmitter` protocol:
   ```python
   class DecisionGitLog:
       def __init__(
           self,
           repo_root: Path,
           worktree_root: Path,
           destination_ref: str,
           mission_slug: str,
           *,
           inner: RuntimeEventEmitter,
       ) -> None:
           self._repo_root = repo_root
           self._worktree_root = worktree_root
           self._destination_ref = destination_ref
           self._mission_slug = mission_slug
           self._inner = inner
           self._decisions_file = repo_root / "kitty-specs" / mission_slug / "decisions.events.jsonl"
   ```
3. For all `emit_*` methods NOT related to decisions, delegate to `self._inner` only.
4. Import `RuntimeEventEmitter` from `specify_cli.next._internal_runtime.events`.

**Files**: `src/specify_cli/events/decision_log.py` (~30 lines for skeleton)

---

### T007 — `emit_decision_input_requested()` — sanitize + append

**Purpose**: Append the sanitized `DecisionInputRequested` event to `decisions.events.jsonl` and delegate to the inner emitter.

**Steps**:
1. In `emit_decision_input_requested(payload: DecisionInputRequestedPayload)`:
   - Convert payload to dict: `payload.model_dump()` (Pydantic v2) or `payload.dict()` (v1). Check which is used in the project.
   - Wrap in envelope: `{"event_id": str(ulid.ULID()), "at": datetime.now(UTC).isoformat(), "event_type": DECISION_INPUT_REQUESTED, "mission_id": self._mission_slug, "payload": payload_dict}`.
   - Call `sanitize_event_for_log(envelope)` from `specify_cli.events`.
   - Append the sanitized dict as a JSON line to `self._decisions_file` (create parent dirs if needed).
   - Delegate to `self._inner.emit_decision_input_requested(payload)`.
2. File append pattern:
   ```python
   self._decisions_file.parent.mkdir(parents=True, exist_ok=True)
   line = json.dumps(sanitized, sort_keys=True, separators=(",", ":"))
   with self._decisions_file.open("a", encoding="utf-8") as f:
       f.write(line + "\n")
   ```

**Files**: `src/specify_cli/events/decision_log.py` (+25 lines)

---

### T008 — `emit_decision_input_answered()` — append + `safe_commit()`

**Purpose**: Append the answer event and trigger a git commit capturing the request+answer pair.

**Steps**:
1. In `emit_decision_input_answered(payload: DecisionInputAnsweredPayload)`:
   - Build envelope, sanitize, append to `self._decisions_file` (same as T007 pattern).
   - Call `safe_commit()`:
     ```python
     from specify_cli.git.commit_helpers import safe_commit
     safe_commit(
         repo_root=self._repo_root,
         worktree_root=self._worktree_root,
         destination_ref=self._destination_ref,
         message="chore(decisions): record decision [skip ci]",
         paths=(self._decisions_file,),
     )
     ```
   - If `safe_commit()` raises (e.g., `SafeCommitHeadMismatch`, `ProtectedBranchRefused`), log the error at WARNING level and continue — do NOT re-raise; a failed commit must not abort mission execution.
   - Delegate to `self._inner.emit_decision_input_answered(payload)`.
2. Import guards: `safe_commit` and `CommitResult` are in `specify_cli.git.commit_helpers`.

**Files**: `src/specify_cli/events/decision_log.py` (+30 lines)

---

### T009 — Wire `DecisionGitLog` into `runtime_bridge.py` emitter construction

**Purpose**: Replace or wrap the existing `JsonlEventLog` construction so that the engine receives a `DecisionGitLog` instance.

**Steps**:
1. Read `src/specify_cli/next/runtime_bridge.py` fully before editing.
2. Find where the emitter is constructed (search for `JsonlEventLog(` or `NullEmitter(`).
3. Modify construction to wrap with `DecisionGitLog`:
   ```python
   from specify_cli.events.decision_log import DecisionGitLog

   inner_emitter = JsonlEventLog(path=existing_log_path)
   emitter = DecisionGitLog(
       repo_root=repo_root,
       worktree_root=worktree_root,
       destination_ref=coordination_branch,
       mission_slug=mission_slug,
       inner=inner_emitter,
   )
   ```
4. Verify `repo_root`, `worktree_root`, and `coordination_branch` are available at this construction site. If `coordination_branch` is not currently passed into `runtime_bridge`, add it as a parameter and trace where bridge construction is called from (`engine.py` or `next/command` entrypoints) to thread it through.
5. `worktree_root` defaults to `repo_root` when the main checkout is the working directory (non-lane execution).

**Files**: `src/specify_cli/next/runtime_bridge.py` (modification, +10–20 lines)

---

### T010 — Remove `DecisionInputRequested/Answered` from `OfflineQueue`

**Purpose**: Ensure these two event types no longer go to the SQLite queue (git is now the record).

**Steps**:
1. Search for where `DecisionInputRequested` and `DecisionInputAnswered` are enqueued. Likely in a propagator or fan-out function — check `src/specify_cli/invocation/propagator.py` and `src/specify_cli/sync/emitter.py`.
2. Add a guard that short-circuits queuing for these event types:
   ```python
   _QUEUE_EXCLUDED_EVENT_TYPES = frozenset({
       "DecisionInputRequested",
       "DecisionInputAnswered",
   })

   if event_dict.get("event_type") in _QUEUE_EXCLUDED_EVENT_TYPES:
       return  # Written to git by DecisionGitLog instead
   ```
3. Place the guard as early as possible in the queue write path (before the SQLite insert).
4. Add a comment referencing spec-kitty issue #1546 as the reason.

**Files**: `src/specify_cli/invocation/propagator.py` or `src/specify_cli/sync/emitter.py` (modification, +8 lines)

---

### T011 — Tests for `DecisionGitLog`

**Purpose**: Automated verification of append behavior, commit trigger, orphaned-request handling, and queue exclusion.

**Steps**:
1. Create `tests/specify_cli/events/test_decision_log.py`.
2. Use `tmp_path` fixture for all file operations.
3. Mock `safe_commit` to verify it is called on answer but not on request:
   ```python
   from unittest.mock import MagicMock, patch

   def test_commit_triggered_on_answer(tmp_path):
       with patch("specify_cli.events.decision_log.safe_commit") as mock_commit:
           log = DecisionGitLog(tmp_path, tmp_path, "kitty/branch", "my-mission", inner=NullEmitter())
           log.emit_decision_input_requested(mock_requested_payload())
           mock_commit.assert_not_called()
           log.emit_decision_input_answered(mock_answered_payload())
           mock_commit.assert_called_once()
   ```
4. Test append behavior: after request + answer, `decisions.events.jsonl` has exactly two lines, both valid JSON, no PII fields.
5. Test orphaned request: after request only (no answer), file has one line; no commit triggered.
6. Test queue exclusion: mock the propagator/emitter and confirm `DecisionInputRequested` and `DecisionInputAnswered` do not reach the queue write path.
7. Test `safe_commit` failure is swallowed: if `safe_commit` raises `ProtectedBranchRefused`, the emit method does not re-raise.

**Files**: `tests/specify_cli/events/test_decision_log.py` (~120 lines)

---

## Definition of Done

- [ ] `DecisionGitLog` fully implements the `RuntimeEventEmitter` protocol
- [ ] `decisions.events.jsonl` created and appended on request and answer events
- [ ] `safe_commit()` called exactly once per answered decision
- [ ] `safe_commit()` failure does not abort mission execution (logged, not re-raised)
- [ ] `DecisionInputRequested` and `DecisionInputAnswered` absent from `OfflineQueue` after a session
- [ ] `mypy --strict` passes on all modified and new files
- [ ] All tests pass; ≥90% coverage on `decision_log.py`

## Risks

- `runtime_bridge.py` may not currently receive the coordination branch — trace callers before editing to understand the full parameter chain. If this requires a larger refactor, flag it in the PR description.
- `payload.model_dump()` vs `payload.dict()` — check the Pydantic version used in the project. Using the wrong method silently produces empty dicts in some versions.
- `safe_commit()` requires `worktree_root` to match the current HEAD branch. In non-lane execution (main checkout), `worktree_root == repo_root` and HEAD is `main` (protected). Ensure the coordination branch is passed as `destination_ref` and that the checkout at `worktree_root` is actually on that branch when `DecisionGitLog` is used inside a lane worktree.

## Reviewer Guidance

Confirm:
1. Commit message includes `[skip ci]` to avoid triggering CI on every decision commit
2. `safe_commit()` errors are caught and logged, never re-raised
3. The queue exclusion guard uses the exact string constants (`DECISION_INPUT_REQUESTED`, `DECISION_INPUT_ANSWERED`) not magic strings
4. No PII fields in any line of `decisions.events.jsonl` (run test with a payload containing all PII fields)

## Activity Log

- 2026-06-01T08:35:51Z – claude:claude-sonnet-4-6:orchestrator:orchestrator – shell_pid=72351 – Assigned agent via action command
