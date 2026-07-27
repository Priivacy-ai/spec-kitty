---
work_package_id: WP06
title: 'LocalCommit Integration: Commit Hook and WebSocket Wiring'
dependencies:
- WP05
requirement_refs:
- FR-010
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
- FR-016
- FR-017
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
agent: "claude:claude-sonnet-4-6:orchestrator:orchestrator"
shell_pid: "73756"
history:
- date: '2026-06-01'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/git/
execution_mode: code_change
owned_files:
- src/specify_cli/git/commit_helpers.py
- src/specify_cli/sync/client.py
- tests/specify_cli/sync/test_local_commit_wiring.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Wire the `local_commit.py` machinery from WP05 into two integration points:
1. `commit_helpers.py::safe_commit()` — call `emit_local_commit()` after any commit touching `kitty-specs/`.
2. `WebSocketClient._listen()` — dispatch `LocalCommitAck` frames to `record_local_commit_ack()`.
3. `WebSocketClient.connect()` — call `flush_pending_local_commits()` after the initial snapshot is received.

**Implement command**: `spec-kitty agent action implement WP06 --agent claude`

**Prerequisite**: WP05 must be merged (provides `emit_local_commit`, `flush_pending_local_commits`, `record_local_commit_ack`).

---

## Context

**Read these files fully before editing**:
- `src/specify_cli/git/commit_helpers.py` — `safe_commit()` function (line ~742), specifically its return shape (`CommitResult` with `.sha`)
- `src/specify_cli/sync/client.py` — `WebSocketClient` class, find `_listen()` and `connect()` methods

**Integration point 1 — `safe_commit()` hook**:
After `safe_commit()` succeeds, inspect the committed `paths`. If any path has a component named `kitty-specs`, call `emit_local_commit()`. The `CommitResult.sha` is the `git_hash`. `mission_id`, `build_id`, and `changed_files` must be derived from the committed paths and the session context.

**How to get `mission_id` and `build_id`**: These are session-level identifiers. Check how `safe_commit()` is currently called — its callers may already carry mission context. If they don't, the simplest approach is to accept optional `mission_id` and `build_id` kwargs in `safe_commit()` and pass `None` if absent (skip emit when `None`). Alternatively, derive `mission_id` from the path (`kitty-specs/<slug>/` → second component).

**Integration point 2 — `_listen()` dispatch**:
Find the inbound message dispatch loop in `WebSocketClient._listen()`. Add a branch for `msg["type"] == "LocalCommitAck"` that calls `record_local_commit_ack(repo_root, msg["git_hash"])`.

**Integration point 3 — `connect()` flush**:
In `WebSocketClient.connect()`, find where the initial snapshot is processed. After that point, call `flush_pending_local_commits(repo_root, self)`.

**Spec references**: FR-010, FR-011, FR-012, FR-013, FR-014, FR-015, FR-016, FR-017

---

## Branch Strategy

- Planning base: `main`
- Final merge target: `main`

---

## Subtask Guidance

### T025 — Hook in `commit_helpers.py::safe_commit()`

**Purpose**: After every successful `safe_commit()` call with paths under `kitty-specs/`, emit a `LocalCommit` frame.

**Steps**:
1. Read `safe_commit()` from line ~742 to end. Identify the return statement that yields `CommitResult`.
2. Before returning, check if any committed path is under `kitty-specs/`:
   ```python
   kitty_specs_files = [
       str(p.relative_to(worktree_root)) if p.is_absolute() else str(p)
       for p in paths
       if "kitty-specs" in p.parts
   ]
   if kitty_specs_files:
       from specify_cli.sync.local_commit import emit_local_commit
       emit_local_commit(
           repo_root=repo_root,
           git_hash=commit_sha,  # from CommitResult or captured from _run_commit_capture_sha
           mission_id=_derive_mission_id(kitty_specs_files),
           build_id=_get_current_build_id(repo_root),
           changed_files=kitty_specs_files,
           committed_at=datetime.now(UTC).isoformat(),
       )
   ```
3. Implement `_derive_mission_id(paths)` — extract the second component of the first path starting with `kitty-specs/` (e.g., `kitty-specs/my-mission/f.jsonl` → `my-mission`). Return `""` if extraction fails.
4. Implement `_get_current_build_id(repo_root)` — read the current `build_id` from session state. Check if there is already a mechanism for this in the codebase (search for `build_id` in `src/specify_cli/`). If not, generate a new ULID as a fallback: `str(ulid.ULID())`.
5. The `emit_local_commit()` call must be **non-blocking** — if it raises, log at WARNING and swallow. Do not let a notification failure abort a commit.
6. Keep the `safe_commit()` return value (`CommitResult`) unchanged.

**Files**: `src/specify_cli/git/commit_helpers.py` (+30 lines)

---

### T026 — Add `LocalCommitAck` dispatch in `WebSocketClient._listen()`

**Purpose**: Handle inbound `LocalCommitAck` frames and update `sync-state.json`.

**Steps**:
1. Read `src/specify_cli/sync/client.py` fully. Find `_listen()`.
2. Locate the inbound message dispatch — it likely has a chain of `if msg["type"] == "..."` or a dispatch dict.
3. Add a handler for `"LocalCommitAck"`:
   ```python
   elif msg.get("type") == "LocalCommitAck":
       git_hash = msg.get("git_hash", "")
       if git_hash:
           from specify_cli.sync.local_commit import record_local_commit_ack
           record_local_commit_ack(self._repo_root, git_hash)
   ```
4. If `_listen()` does not currently have access to `repo_root`, check the constructor — it likely does. If not, thread it through.
5. The handler must never raise — wrap in `try/except` if the dispatch loop is not already protected.

**Files**: `src/specify_cli/sync/client.py` (+10 lines)

---

### T027 — Add `flush_pending_local_commits()` in `WebSocketClient.connect()`

**Purpose**: On WebSocket connect, replay any `LocalCommit` frames that were sent while offline.

**Steps**:
1. In `WebSocketClient.connect()`, find the point after the initial snapshot is received and processed.
2. Add the flush call immediately after:
   ```python
   from specify_cli.sync.local_commit import flush_pending_local_commits
   flush_pending_local_commits(self._repo_root, self)
   ```
3. The flush is fire-and-forget from the connect sequence's perspective — if `flush_pending_local_commits` raises, log and continue. Connection success must not be gated on flush success.
4. Confirm `self._repo_root` is available in `connect()` (or accessible via `self`).

**Files**: `src/specify_cli/sync/client.py` (+8 lines)

---

### T028 — Integration tests (safe_commit hook, WebSocket ack handler, on-connect flush)

**Purpose**: End-to-end verification of the three wiring points.

**Steps**:
1. Create `tests/specify_cli/sync/test_local_commit_wiring.py`.
2. **Test: `safe_commit()` hook emits when path is under `kitty-specs/`**:
   ```python
   def test_safe_commit_emits_local_commit_for_kitty_specs_path(tmp_path, fake_git_repo):
       with patch("specify_cli.git.commit_helpers.emit_local_commit") as mock_emit:
           safe_commit(
               repo_root=tmp_path,
               worktree_root=tmp_path,
               destination_ref="kitty/branch",
               message="test",
               paths=(tmp_path / "kitty-specs" / "my-mission" / "file.jsonl",),
           )
           mock_emit.assert_called_once()
           args = mock_emit.call_args
           assert "my-mission" in args.kwargs.get("mission_id", "")
           assert "kitty-specs/my-mission/file.jsonl" in args.kwargs.get("changed_files", [])
   ```
3. **Test: `safe_commit()` does NOT emit for non-`kitty-specs/` paths**:
   - Call `safe_commit()` with a path outside `kitty-specs/`.
   - Assert `emit_local_commit` not called.
4. **Test: `LocalCommitAck` handler calls `record_local_commit_ack()`**:
   - Construct a `WebSocketClient` instance (or mock the relevant parts).
   - Simulate receiving `{"type": "LocalCommitAck", "git_hash": "abc123..."}`.
   - Assert `record_local_commit_ack` called with the correct hash.
5. **Test: `connect()` calls `flush_pending_local_commits()`**:
   - Mock `flush_pending_local_commits`.
   - Trigger `connect()` (or the post-snapshot step).
   - Assert flush was called.
6. **Test: `safe_commit()` failure in emit does not abort the commit** — if `emit_local_commit` raises, `safe_commit()` still returns `CommitResult` successfully.

**Files**: `tests/specify_cli/sync/test_local_commit_wiring.py` (~120 lines)

---

## Definition of Done

- [ ] `safe_commit()` calls `emit_local_commit()` after success when any path is under `kitty-specs/`
- [ ] `safe_commit()` does NOT call `emit_local_commit()` for non-`kitty-specs/` commits
- [ ] `emit_local_commit()` failure in commit hook is swallowed (log + continue)
- [ ] `WebSocketClient._listen()` dispatches `LocalCommitAck` to `record_local_commit_ack()`
- [ ] `WebSocketClient.connect()` calls `flush_pending_local_commits()` after snapshot
- [ ] Flush failure does not prevent successful connect
- [ ] `mypy --strict` passes on all modified files
- [ ] All integration tests pass; ≥90% coverage on new test file

## Risks

- `safe_commit()` is a ~225-line function with multiple early-return paths — insert the emit hook only once, after the successful commit, not inside any validation branch.
- `WebSocketClient` may use asyncio patterns that make synchronous testing difficult. Use `AsyncMock` and `asyncio.run()` in tests if needed.
- `build_id` derivation — if there is no session-level `build_id` available in `safe_commit()`'s scope, a ULID fallback per-commit is acceptable but means each commit gets a different `build_id`. The SaaS uses `build_id` to group commits from the same session. Investigate the session context before falling back to a per-call ULID.

## Reviewer Guidance

1. Confirm the emit hook is after the commit succeeds, not before
2. Confirm non-`kitty-specs/` paths do not trigger an emit
3. Confirm neither the ack handler nor the flush call can propagate an exception that kills the WebSocket session
4. Verify `mission_id` derivation from path is correct for all slug formats (including slugs with hyphens and version suffixes like `01KT119Y`)

## Activity Log

- 2026-06-01T08:39:36Z – claude:claude-sonnet-4-6:orchestrator:orchestrator – shell_pid=73756 – Started implementation via action command
