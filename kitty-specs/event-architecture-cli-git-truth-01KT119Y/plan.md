# Implementation Plan: Event Architecture — Git Semantic Truth + WebSocket Awareness (CLI)

**Branch**: `main` | **Date**: 2026-06-01 | **Spec**: [spec.md](spec.md)
**Mission**: event-architecture-cli-git-truth-01KT119Y
**Source issues**: spec-kitty #1546, #1547, #1548, #1549

---

## Summary

Four tightly related CLI changes that together implement the event architecture redesign:

1. **Decision event durability** (#1546): A new `DecisionGitLog` emitter appends `DecisionInputRequested/Answered` to `kitty-specs/<mission>/decisions.events.jsonl` (sanitized, JSONL format matching `status.events.jsonl`) and commits on each answered decision. Decision events are removed from the SQLite queue.

2. **PII sanitization** (#1547): A pure `sanitize_event_for_log()` function strips `machine_name`, `hostname`, `workspace_path`, `developer_name`, `developer_email`, and absolute session timestamps from any event envelope before write to git-tracked files or the queue.

3. **LocalCommit WebSocket notification** (#1548, full scope): After every `safe_commit()` touching `kitty-specs/`, a `LocalCommit` frame is sent over WebSocket or stored in `.kittify/sync-state.json`. On reconnect, pending frames are flushed. A new `LocalCommitAck` handler in `_listen()` acknowledges receipt.

4. **Glossary queue reduction** (#1549): `GlossarySenseUpdated` is dropped from the canonical queue adapter. `GlossaryClarificationResolved/Requested` remain. Seed file update on resolution is confirmed synchronous (no change needed).

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: spec-kitty-events (external PyPI, v4.0.0+ for decision event models), ulid-py, ruamel.yaml, typer, rich, pytest, mypy
**Storage**: Filesystem (JSONL files, YAML seed, JSON state); SQLite `OfflineQueue` (no structural change — only event-type exclusions)
**Testing**: pytest with ≥90% line coverage on all new modules; `mypy --strict` must pass; integration tests for CLI command paths that exercise the new write paths
**Target Platform**: Linux, macOS, Windows 10+ (existing cross-platform requirement)
**Project Type**: Single Python package (`src/specify_cli/`)
**Performance Goals**: LocalCommit notification delivered ≤1s during live session; on-connect replay of ≤50 frames adds ≤200ms
**Constraints**: `safe_commit()` refuses commits to `main`; decision commits must land on the coordination branch. PII-stripping is write-time only — no retroactive rewriting of existing entries. No changes to `OfflineQueue` drain/retry/ack logic.

---

## Charter Check

**Directives active for this mission:**

- **DIRECTIVE_003** (Decision Documentation Requirement): All four changes involve material behavioral shifts in event routing. Each change area documents its rationale and chosen alternative in `research.md`. ✓
- **DIRECTIVE_010** (Specification Fidelity Requirement): Implementation must match FR-001–FR-022 exactly. Any deviation requires explicit documentation and review before acceptance. ✓
- **DIR-005** (Tests for new functionality): ≥90% coverage on new modules. ✓
- **DIR-006** (mypy --strict): All new modules typed. ✓
- **DIR-008** (No security issues): Sanitizer must prevent PII leakage. Verified at write boundary, not just at construction. ✓
- **DIR-010/011** (ASCII-safe identifiers): `mission_slug` and `build_id` used in file paths; both already ASCII-safe via existing sanitizers. ✓

**No charter violations.**

---

## Project Structure

### Documentation (this mission)

```
kitty-specs/event-architecture-cli-git-truth-01KT119Y/
├── spec.md                         # FR-001–FR-022, NFR-001–NFR-005, C-001–C-005
├── plan.md                         # This file
├── research.md                     # Findings 1–8: commit strategy, PII fields, WebSocket API
├── data-model.md                   # decisions.events.jsonl, sync-state.json, state transitions
├── contracts/
│   └── websocket-frames.md         # LocalCommit / LocalCommitAck frame contracts
└── tasks/                          # Created by /spec-kitty.tasks
```

### Source Code (affected areas)

```
src/specify_cli/
├── events/                         # NEW package
│   ├── __init__.py
│   ├── sanitizer.py                # sanitize_event_for_log() — pure PII stripper
│   └── decision_log.py             # DecisionGitLog emitter (writes decisions.events.jsonl + commits)
│
├── sync/
│   └── local_commit.py             # NEW: LocalCommit frame builder, sync-state.json manager
│
├── next/_internal_runtime/
│   └── engine.py                   # MODIFIED: wire DecisionGitLog into emitter construction
│
├── status/
│   └── store.py                    # MODIFIED: apply sanitize_event_for_log() before append_event
│
├── glossary/
│   └── events.py                   # MODIFIED: skip _pkg_append_event for GlossarySenseUpdated
│
└── git/
    └── commit_helpers.py           # MODIFIED: call emit_local_commit() after successful safe_commit on kitty-specs/ paths

tests/
├── specify_cli/
│   ├── events/
│   │   ├── test_sanitizer.py       # PII field removal, timestamp replacement
│   │   └── test_decision_log.py    # Append behavior, commit trigger, orphaned-request handling
│   ├── sync/
│   │   └── test_local_commit.py    # Frame emit, sync-state read/write, flush-on-connect
│   ├── status/
│   │   └── test_store_sanitized.py # Confirm PII absent from status.events.jsonl writes
│   └── glossary/
│       └── test_events_queue.py    # Confirm GlossarySenseUpdated absent from queue
```

---

## Work Package Outline

The four issue areas map naturally to separable work packages. PII sanitization (#1547) is a shared dependency for decision log (#1546) and must land first.

### WP01 — PII Sanitizer (`events/sanitizer.py`)

**Scope:** New pure function `sanitize_event_for_log()`. No integration with existing code yet — this WP delivers the function and its test coverage in isolation.

**Key deliverables:**
- `src/specify_cli/events/__init__.py`
- `src/specify_cli/events/sanitizer.py` with `sanitize_event_for_log()`
- `tests/specify_cli/events/test_sanitizer.py` (100% coverage; table-driven for each PII field + timestamp replacement)

**Dependencies:** None.

---

### WP02 — Decision Event Git Log (`events/decision_log.py` + engine wiring)

**Scope:** `DecisionGitLog` emitter that appends sanitized events to `decisions.events.jsonl` and commits on answer. Engine wiring in `next/_internal_runtime/engine.py` or `next/runtime_bridge.py`. Removal of `DecisionInputRequested/Answered` from the SQLite queue.

**Key deliverables:**
- `src/specify_cli/events/decision_log.py` with `DecisionGitLog`
- Engine wiring: `DecisionGitLog` constructed with `repo_root`, `worktree_root`, `destination_ref` (coordination branch), `mission_slug`
- Queue exclusion: guard in the queue write path that skips these two event types
- `tests/specify_cli/events/test_decision_log.py`

**Dependencies:** WP01 (sanitizer must be available).

**Commit strategy:** Append immediately for both event types; `safe_commit()` triggered by `emit_decision_input_answered()`.

**Satisfies:** FR-001, FR-002, FR-003, FR-004, FR-005

---

### WP03 — PII Sanitization in Status Write Path

**Scope:** Apply `sanitize_event_for_log()` at the `status/store.py::append_event()` boundary. Covers `status.events.jsonl` writes going forward.

**Key deliverables:**
- `src/specify_cli/status/store.py` modified to call sanitizer before each append
- `tests/specify_cli/status/test_store_sanitized.py` confirming zero PII fields post-change

**Dependencies:** WP01.

**Note:** This is a narrow, focused change. Separating it from WP01 keeps the sanitizer testable in isolation before it has consumers.

---

### WP04 — Glossary Queue Reduction (`glossary/events.py`)

**Scope:** Drop `GlossarySenseUpdated` from the canonical queue adapter in `emit_glossary_sense_updated()`. Keep `GlossaryClarificationResolved` and `GlossaryClarificationRequested` in the queue unchanged. Confirm seed file update on resolution is synchronous (FR-021). Local JSONL write is unchanged (FR-022). Seed file update on `GlossaryClarificationResolved` is confirmed already synchronous — no code change needed there.

**Key deliverables:**
- `src/specify_cli/glossary/events.py` modified: skip `_pkg_append_event` for `GlossarySenseUpdated`
- `tests/specify_cli/glossary/test_events_queue.py` confirming queue exclusion and positive-case retention

**Dependencies:** None (independent of WP01–WP03).

**Satisfies:** FR-018, FR-019, FR-020, FR-021, FR-022, NFR-004

---

### WP05 — LocalCommit WebSocket Notification (`sync/local_commit.py` + client wiring)

**Scope:** Full scope — emit frame, `sync-state.json` persistence, flush-on-connect, `LocalCommitAck` handler.

**Key deliverables:**
- `src/specify_cli/sync/local_commit.py` with `emit_local_commit()`, `flush_pending_local_commits()`, `record_local_commit_ack()`, `SyncState` dataclass, `load/save_sync_state()`
- `src/specify_cli/git/commit_helpers.py` modified: after successful `safe_commit()`, if any committed path is under `kitty-specs/`, call `emit_local_commit()`
- `src/specify_cli/sync/client.py` modified: add `LocalCommitAck` dispatch in `_listen()`; add `flush_pending_local_commits()` call after initial snapshot received on connect
- `tests/specify_cli/sync/test_local_commit.py` (emit, queue-when-disconnected, flush-on-connect, ack handling, amended-commit replacement)

**Dependencies:** WP01 (no PII in frame payload — sanitizer available), but `LocalCommit` frame fields are already PII-free by construction so WP05 can proceed in parallel with WP01 in principle; strict dependency is advisory for test isolation.

---

## Execution Lane Recommendation

```
Lane A (sequential):  WP01 → WP02 → WP03
Lane B (independent): WP04
Lane C (independent): WP05
```

WP04 and WP05 have no dependencies on the sanitizer and can run in parallel with Lane A. WP02 and WP03 both depend on WP01 (they consume `sanitize_event_for_log`).

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `safe_commit()` coordination branch required for decisions; engine may not have `destination_ref` at construction time | Medium | High | Verify `runtime_bridge.py` construction path; add `destination_ref` parameter to bridge if absent |
| `_listen()` in WebSocket client has no dispatch table — adding a new handler may require refactoring the loop | Low | Medium | Read `sync/client.py` fully before WP05; if a dispatch refactor is needed, scope it as part of WP05 |
| Orphaned `DecisionInputRequested` lines confuse SaaS parser if reader is strict | Low | Low | Document in contracts/websocket-frames.md that orphaned requests are valid; SaaS team handles in #293 |
| `GlossarySenseUpdated` removal breaks a SaaS consumer we haven't identified | Low | Medium | Search `spec-kitty-saas` for any `GlossarySenseUpdated` consumers before WP04 merge |

---

## Definition of Done

- All FR-001–FR-022 implemented and verified with automated tests.
- `mypy --strict` passes with zero new ignores.
- ≥90% line coverage on all new modules (`events/`, `sync/local_commit.py`).
- `GlossarySenseUpdated` absent from queue after any mission session (automated test).
- Zero PII fields in any `decisions.events.jsonl` or `status.events.jsonl` written after deployment (automated test with known PII-bearing payloads).
- `contracts/websocket-frames.md` reviewed against spec-kitty-saas counterpart issues #292 and #295.
