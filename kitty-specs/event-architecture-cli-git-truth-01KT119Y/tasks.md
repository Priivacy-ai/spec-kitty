# Tasks: Event Architecture — Git Semantic Truth + WebSocket Awareness (CLI)

**Mission**: event-architecture-cli-git-truth-01KT119Y
**Branch**: `main` → merge target: `main`
**Generated**: 2026-06-01

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-----------|----|---------|
| T001 | Create `src/specify_cli/events/__init__.py` new package | WP01 | [P] |
| T002 | Implement `sanitize_event_for_log()` — strip PII fields | WP01 | |
| T003 | Implement session timestamp replacement (absolute → `session_duration_s`) | WP01 | |
| T004 | Unit tests for PII field removal (table-driven, one case per field) | WP01 | [P] |
| T005 | Unit tests for timestamp replacement edge cases | WP01 | [P] |
| T006 | Implement `DecisionGitLog` class — constructor, delegation to inner emitter | WP02 | |
| T007 | `emit_decision_input_requested()` — sanitize + append to `decisions.events.jsonl` | WP02 | |
| T008 | `emit_decision_input_answered()` — sanitize + append + `safe_commit()` trigger | WP02 | |
| T009 | Wire `DecisionGitLog` into `next/runtime_bridge.py` emitter construction | WP02 | |
| T010 | Remove `DecisionInputRequested/Answered` from `OfflineQueue` write path | WP02 | [P] |
| T011 | Tests for `DecisionGitLog` (append, commit trigger, orphaned request, queue exclusion) | WP02 | [P] |
| T012 | Apply `sanitize_event_for_log()` in `status/store.py::append_event()` | WP03 | |
| T013 | Apply sanitizer in `decisions/emit.py` for `DecisionPointOpened/Resolved` writes | WP03 | [P] |
| T014 | Tests confirming zero PII in `status.events.jsonl` and `decisions.events.jsonl` writes | WP03 | [P] |
| T015 | Skip `_pkg_append_event` in `emit_glossary_sense_updated()` | WP04 | |
| T016 | Verify `GlossaryClarificationResolved/Requested` still reach canonical adapter | WP04 | [P] |
| T017 | Confirm seed file update on `GlossaryClarificationResolved` is synchronous | WP04 | [P] |
| T018 | Tests confirming queue exclusion for `GlossarySenseUpdated` | WP04 | [P] |
| T019 | `SyncState` dataclass + `load_sync_state()` / `save_sync_state()` with atomic write | WP05 | |
| T020 | `emit_local_commit()` — build `LocalCommit` frame, send or store in `sync-state.json` | WP05 | |
| T021 | `flush_pending_local_commits()` — on-connect replay in chronological order | WP05 | |
| T022 | `record_local_commit_ack()` — remove acked frame, update `last_saas_confirmed_hash` | WP05 | |
| T023 | Handle amended commit — replace prior pending frame for same `build_id` | WP05 | |
| T024 | Unit tests for all `local_commit.py` behaviors | WP05 | [P] |
| T025 | Hook in `commit_helpers.py::safe_commit()` — call `emit_local_commit()` after kitty-specs/ commits | WP06 | |
| T026 | Add `LocalCommitAck` dispatch branch in `WebSocketClient._listen()` | WP06 | [P] |
| T027 | Add `flush_pending_local_commits()` call in `WebSocketClient.connect()` after snapshot | WP06 | [P] |
| T028 | Integration tests (safe_commit hook, WebSocket ack handler, on-connect flush) | WP06 | [P] |

---

## Work Packages

### WP01 — PII Event Sanitizer

**Priority**: Critical (shared dependency for WP02 and WP03)
**Prompt**: [tasks/WP01-pii-event-sanitizer.md](tasks/WP01-pii-event-sanitizer.md)
**Estimated size**: ~280 lines
**Dependencies**: None
**Lane**: A (first)

**Goal**: Create `src/specify_cli/events/` package with a pure `sanitize_event_for_log()` function that strips PII fields and replaces absolute session timestamps with a relative duration. No integration with existing code in this WP — this is the standalone building block that WP02 and WP03 consume.

**Success test**: `pytest tests/specify_cli/events/test_sanitizer.py` passes; `mypy --strict src/specify_cli/events/` passes; none of the PII fields appear in any output dict; function is pure (does not mutate input).

**Included subtasks:**
- [x] T001 Create `src/specify_cli/events/__init__.py` new package (WP01)
- [x] T002 Implement `sanitize_event_for_log()` — strip PII fields (WP01)
- [x] T003 Implement session timestamp replacement (absolute → `session_duration_s`) (WP01)
- [x] T004 Unit tests for PII field removal (table-driven, one case per field) (WP01)
- [x] T005 Unit tests for timestamp replacement edge cases (WP01)

---

### WP02 — Decision Event Git Log

**Priority**: High
**Prompt**: [tasks/WP02-decision-event-git-log.md](tasks/WP02-decision-event-git-log.md)
**Estimated size**: ~380 lines
**Dependencies**: WP01
**Lane**: A (after WP01; parallel with WP03)

**Goal**: Implement `DecisionGitLog` — an emitter that appends sanitized `DecisionInputRequested/Answered` events to `kitty-specs/<mission>/decisions.events.jsonl`, triggers `safe_commit()` on each answered decision, and removes those two event types from the `OfflineQueue`. Wire it into the engine emitter construction via `runtime_bridge.py`.

**Success test**: After a mission session with at least one decision, `kitty-specs/<mission>/decisions.events.jsonl` exists in git; no `DecisionInputRequested` or `DecisionInputAnswered` entries in the queue.

**Included subtasks:**
- [ ] T006 Implement `DecisionGitLog` class — constructor, delegation to inner emitter (WP02)
- [ ] T007 `emit_decision_input_requested()` — sanitize + append to `decisions.events.jsonl` (WP02)
- [ ] T008 `emit_decision_input_answered()` — sanitize + append + `safe_commit()` trigger (WP02)
- [ ] T009 Wire `DecisionGitLog` into `next/runtime_bridge.py` emitter construction (WP02)
- [ ] T010 Remove `DecisionInputRequested/Answered` from `OfflineQueue` write path (WP02)
- [ ] T011 Tests for `DecisionGitLog` (append, commit trigger, orphaned request, queue exclusion) (WP02)

---

### WP03 — Status Write Path Sanitization

**Priority**: High
**Prompt**: [tasks/WP03-status-write-sanitization.md](tasks/WP03-status-write-sanitization.md)
**Estimated size**: ~200 lines
**Dependencies**: WP01
**Lane**: A (after WP01; parallel with WP02)

**Goal**: Apply `sanitize_event_for_log()` at the two existing write-to-git boundaries: `status/store.py::append_event()` (for `status.events.jsonl`) and `decisions/emit.py` (for `DecisionPointOpened/Resolved` events that currently write to `status.events.jsonl`). Confirm zero PII fields in all written output.

**Success test**: Table-driven test confirms none of the six PII field names appear in any line written to `status.events.jsonl` when a pre-PII-era envelope is passed through the write path.

**Included subtasks:**
- [ ] T012 Apply `sanitize_event_for_log()` in `status/store.py::append_event()` (WP03)
- [ ] T013 Apply sanitizer in `decisions/emit.py` for `DecisionPointOpened/Resolved` writes (WP03)
- [ ] T014 Tests confirming zero PII in `status.events.jsonl` and `decisions.events.jsonl` writes (WP03)

---

### WP04 — Glossary Queue Reduction

**Priority**: Medium
**Prompt**: [tasks/WP04-glossary-queue-reduction.md](tasks/WP04-glossary-queue-reduction.md)
**Estimated size**: ~250 lines
**Dependencies**: None
**Lane**: B (independent; can run in parallel with Lane A and C)

**Goal**: Drop `GlossarySenseUpdated` from the canonical queue adapter in `glossary/events.py`. Keep `GlossaryClarificationResolved` and `GlossaryClarificationRequested` in the queue unchanged. Confirm seed file update on resolution is already synchronous (no code change required there, just test coverage).

**Success test**: After a mission session with ≥10 glossary extraction steps, queue contains zero `GlossarySenseUpdated` entries. `GlossaryClarificationResolved` still present in queue.

**Included subtasks:**
- [x] T015 Skip `_pkg_append_event` in `emit_glossary_sense_updated()` (WP04)
- [x] T016 Verify `GlossaryClarificationResolved/Requested` still reach canonical adapter (WP04)
- [x] T017 Confirm seed file update on `GlossaryClarificationResolved` is synchronous (WP04)
- [x] T018 Tests confirming queue exclusion for `GlossarySenseUpdated` (WP04)

---

### WP05 — LocalCommit Core: SyncState and Frame Logic

**Priority**: High
**Prompt**: [tasks/WP05-localcommit-core.md](tasks/WP05-localcommit-core.md)
**Estimated size**: ~360 lines
**Dependencies**: None
**Lane**: C (independent; WP06 depends on this)

**Goal**: Implement `src/specify_cli/sync/local_commit.py` — the full data layer and business logic for `LocalCommit` frame emission. Includes `SyncState` dataclass, atomic `sync-state.json` read/write, `emit_local_commit()`, `flush_pending_local_commits()`, `record_local_commit_ack()`, and amended-commit replacement. No integration with `commit_helpers.py` or the WebSocket client yet — that is WP06.

**Success test**: Unit tests covering: emit when connected (frame sent), emit when disconnected (stored), flush order (chronological), ack removes entry, amended commit replaces prior pending frame.

**Included subtasks:**
- [x] T019 `SyncState` dataclass + `load_sync_state()` / `save_sync_state()` with atomic write (WP05)
- [x] T020 `emit_local_commit()` — build `LocalCommit` frame, send or store in `sync-state.json` (WP05)
- [x] T021 `flush_pending_local_commits()` — on-connect replay in chronological order (WP05)
- [x] T022 `record_local_commit_ack()` — remove acked frame, update `last_saas_confirmed_hash` (WP05)
- [x] T023 Handle amended commit — replace prior pending frame for same `build_id` (WP05)
- [x] T024 Unit tests for all `local_commit.py` behaviors (WP05)

---

### WP06 — LocalCommit Integration: Commit Hook and WebSocket Wiring

**Priority**: High
**Prompt**: [tasks/WP06-localcommit-wiring.md](tasks/WP06-localcommit-wiring.md)
**Estimated size**: ~260 lines
**Dependencies**: WP05
**Lane**: C (after WP05)

**Goal**: Wire `local_commit.py` into the two integration points: (1) `commit_helpers.py::safe_commit()` calls `emit_local_commit()` after any commit touching `kitty-specs/`; (2) `WebSocketClient._listen()` dispatches `LocalCommitAck` frames to `record_local_commit_ack()`; (3) `WebSocketClient.connect()` calls `flush_pending_local_commits()` after the initial snapshot.

**Success test**: Integration test confirms that after `safe_commit()` on a `kitty-specs/` file, (a) a `LocalCommit` frame is sent when connected and (b) stored in `sync-state.json` when disconnected; that a `LocalCommitAck` clears the pending entry.

**Included subtasks:**
- [ ] T025 Hook in `commit_helpers.py::safe_commit()` — call `emit_local_commit()` after kitty-specs/ commits (WP06)
- [ ] T026 Add `LocalCommitAck` dispatch branch in `WebSocketClient._listen()` (WP06)
- [ ] T027 Add `flush_pending_local_commits()` call in `WebSocketClient.connect()` after snapshot (WP06)
- [ ] T028 Integration tests (safe_commit hook, WebSocket ack handler, on-connect flush) (WP06)

---

## Execution Lanes

```
Lane A:  WP01 ──► WP02 ──► (WP03 can run in parallel with WP02 after WP01)
                   ├──► WP02
                   └──► WP03

Lane B:  WP04  (independent, no deps)

Lane C:  WP05 ──► WP06
```

**Parallelization opportunities:**
- WP02 and WP03 can run concurrently (both depend on WP01, not on each other)
- Lane B (WP04) can run in parallel with all of Lane A and Lane C
- Lane C (WP05) can start concurrently with Lane A

**MVP recommendation**: WP01 (sanitizer) is the natural starting point — it unblocks WP02 and WP03. WP04 is the most self-contained quick win. WP05 + WP06 together deliver the new user-visible behavior (SaaS build surface awareness).
