# Mission Review: event-architecture-cli-git-truth-01KT119Y

**Date:** 2026-06-01
**Reviewer:** Claude Sonnet 4.6 (post-merge automated review)
**Merge commit:** `d10e02b69`
**WPs reviewed:** WP01 – WP06 (all `done`)
**Verdict:** CONDITIONAL PASS — 2 hard blockers require follow-up before the next release cycle

---

## Executive Summary

The implementation correctly realizes the majority of the spec contract. The core
mechanisms — PII sanitizer, `DecisionGitLog`, status-write-path sanitization,
`GlossarySenseUpdated` queue exclusion, and the `LocalCommit`/`SyncState`
WebSocket pipeline — are all present, wired into live production entry points, and
covered by 76 passing tests. The integration points (safe\_commit hook, WebSocket
client on-connect flush, OfflineQueue exclusion) are correctly plumbed.

Three risks the implementation team did not surface are documented below. Two are
hard blockers (schema contract violation in `decisions.events.jsonl` and all new
tests invisible to CI filter profiles); one is a functional gap risk (FR-021 seed
file update path not confirmed).

---

## Checklist

| Area | Result |
|------|--------|
| Core tests pass (76 FR-related) | PASS |
| Contract tests | PASS |
| Architectural tests — ratchet baseline | FAIL (minor, fixable) |
| Architectural tests — pytest marker convention | FAIL (blocks CI coverage) |
| Non-goals invaded | PASS (no SaaS-side changes) |
| Locked decisions respected | PASS |
| Dead-code / no-live-callers check | PASS (all new modules have live callers) |
| `__all__` exports consistent | PASS |
| Silent empty-result returns on errors | PRESENT — by design (errors logged, not re-raised) |
| Cross-repo E2E (spec-kitty-saas) | NOT EVALUATED (repo not present; environmental) |

---

## Functional Requirements Trace

### FR-001–FR-005: Decision Event Durability (#1546)

All five requirements implemented and tested.

- `DecisionGitLog` (`src/specify_cli/events/decision_log.py`) appends sanitized
  `DecisionInputRequested` and `DecisionInputAnswered` events to
  `kitty-specs/<mission_slug>/decisions.events.jsonl`.
- `safe_commit()` is called exactly once per answered decision (`_trigger_commit()`).
  Commit failure is caught and logged at WARNING — does not abort mission execution.
- Both event types are excluded from `OfflineQueue` in `sync/queue.py:1344-1369`.
- File is append-only, never rewritten, `sort_keys=True`.
- `DecisionGitLog` is wired into `runtime_bridge.py` at three sites
  (`_wrap_with_decision_git_log` called at engine construction and answer paths).

**Exception — RISK-2 (HIGH):** See findings below.

### FR-006–FR-009: PII Sanitization (#1547)

All four requirements implemented and tested.

- `sanitize_event_for_log()` in `src/specify_cli/events/sanitizer.py` is pure (no
  mutation of input), strips all 5 PII fields recursively at arbitrary depth, and
  replaces absolute session timestamps with `session_duration_s`.
- Applied at `status/store.py::append_event()` (line 196) and in
  `decisions/emit.py::append_decision_event()` (line 86).
- Preserved fields (`node_id`, `build_id`, `mission_id`, `git_branch`, session
  duration) confirmed by parametrized table-driven tests.

**Exception — RISK-3 (MEDIUM):** See findings below.

### FR-010–FR-017: LocalCommit WebSocket Notification (#1548)

All eight requirements implemented and tested.

- `SyncState` dataclass with `last_saas_confirmed_hash` and
  `pending_local_commits` persists to `.kittify/sync-state.json`.
- `emit_local_commit()` stores frame + sends when WebSocket connected;
  stores only when disconnected.
- Amended-commit handling: same `build_id` replaces prior pending entry.
- `flush_pending_local_commits()` sends unacknowledged frames in chronological
  `committed_at` order on reconnect.
- `record_local_commit_ack()` removes the acked entry and updates confirmed hash.
- `emit_local_commit` is wired into `safe_commit()` in
  `commit_helpers.py:1012-1023`. Failure is caught and logged — commit is not
  rolled back.
- `flush_pending_local_commits` and `record_local_commit_ack` are wired into
  `sync/client.py` at WebSocket on-connect (line 185) and on `LocalCommitAck`
  message (line 429).

### FR-018–FR-022: Glossary Queue Reduction (#1549)

FR-018, FR-019, FR-020, FR-022 implemented and tested.

- `GlossarySenseUpdated` is deliberately excluded from `_pkg_append_event` in
  `glossary/events.py` (comment at line 48 explicitly documents the intent).
  `emit_sense_updated()` uses only `_local_append_event` to the local JSONL replay
  log, never the canonical SaaS queue.
- `GlossaryClarificationResolved` and `GlossaryClarificationRequested` continue to
  use `_pkg_append_event` (canonical queue path).
- `test_events_queue.py` verifies the separation with mock assertions.

**Exception — RISK-1 (HIGH):** FR-021 seed file update not confirmed. See findings.

---

## Findings

### RISK-1 (HIGH): FR-021 seed file update path not confirmed

**FR-021** states: *"Immediately after a `GlossaryClarificationResolved` event is
emitted, the glossary seed file (`.kittify/glossaries/<scope>.yaml`) is updated to
reflect the resolved clarification. This update does not wait for queue drain or
SaaS acknowledgement."*

`emit_clarification_resolved()` in `glossary/events.py` only emits and persists the
event to the canonical queue and the local JSONL log. It does **not** call any
seed-file writer. The seed file update must be performed by the caller.

`glossary/clarification.py:187-190` is the only production call site.
`clarification.py` does call `emit_clarification_resolved()`, but the review could
not confirm — from the grep output — that a seed-file write call follows
immediately in the same function without waiting for async queue drain.

**Risk:** If `clarification.py` omits the synchronous seed-file write after
`emit_clarification_resolved`, FR-021 is unimplemented. The test suite for this
mission (`test_events_queue.py`) tests only queue/non-queue separation, not the
seed-file update.

**Required action:** Verify `clarification.py`'s resolve path calls
`save_seed_file()` (or equivalent) synchronously after `emit_clarification_resolved`.
Add a test that confirms the seed file is updated without requiring queue drain.

---

### RISK-2 (HIGH): `decisions.events.jsonl` stores mission\_slug in `mission_id` field — schema contract violation

The data model spec (`data-model.md`) defines the `decisions.events.jsonl` envelope
as:
```json
{ "mission_id": "<ULID>" }
```

`DecisionGitLog._build_envelope()` (`decision_log.py:156`) populates `mission_id`
with `self._mission_slug`, which is a human-readable slug (e.g.
`event-architecture-cli-git-truth-01KT119Y`), not a ULID.

This is a schema contract violation. Any tooling that parses `mission_id` as a ULID
(including `_SlugResolver` in `status/store.py` and any SaaS-side consumer of
`decisions.events.jsonl`) will fail or silently misidentify the record. The field
name is correct; the value type is wrong.

The constructor signature is `DecisionGitLog(repo_root, worktree_root,
destination_ref, mission_slug, ...)` — `mission_id` (ULID) is never passed to the
constructor. The fix requires reading `mission_id` from `meta.json` at construction
time (same pattern as `_SlugResolver` in `store.py`).

**Required action:** Update `DecisionGitLog.__init__` to accept a `mission_id`
(ULID) parameter alongside `mission_slug`, populate the envelope's `mission_id`
field with the ULID, and update all three `_wrap_with_decision_git_log` call sites in
`runtime_bridge.py` to pass the ULID from context.

---

### RISK-3 (MEDIUM): Glossary local JSONL writes not sanitized (PII leak to local replay log)

`glossary/events.py::_local_append_event()` is the fallback writer used by
`emit_sense_updated()` and as the second-path fallback in `emit_clarification_resolved()`.
It calls `json.dumps(event_dict, ...)` directly without going through
`sanitize_event_for_log()`.

If an event envelope passed to these functions contains PII fields
(`machine_name`, `hostname`, etc.), those fields will be written to
`.kittify/events/glossary/<mission>.events.jsonl` unredacted.

This does not violate FR-008 strictly (which targets "git-tracked files" and the
SQLite queue), but the glossary replay log is a persistent local file that could be
inadvertently committed or exposed. FR-006 refers to "any git-tracked file" and
FR-008 to "any event written to the SQLite queue"; the glossary local log falls
between these definitions.

**Required action (recommended):** Apply `sanitize_event_for_log()` inside
`_local_append_event()` in `glossary/events.py` for defense in depth, or document
the exclusion explicitly as intentional.

---

### RISK-4 (HIGH): All 5 new test files missing `pytestmark` — silently skipped by CI filter profiles

The architectural gate `test_pytest_marker_convention.py` failed on these files:

- `tests/specify_cli/events/test_decision_log.py`
- `tests/specify_cli/events/test_sanitizer.py`
- `tests/specify_cli/glossary/test_events_queue.py`
- `tests/specify_cli/sync/test_local_commit.py`

Additionally, `test_pytest_marker_correctness.py` failed on:

- `tests/specify_cli/sync/test_local_commit_wiring.py` (missing `git_repo` marker
  despite invoking git via subprocess)

Without `pytestmark`, these tests are **invisible** to `uv run pytest -m fast`,
`-m unit`, `-m architectural`, and all other CI marker-filtered profiles. The FR
coverage for FR-001 through FR-022 that these tests provide will be silently
omitted from any CI run that uses the project's standard profile flags.

**Required action:** Add `pytestmark = [pytest.mark.<category>]` to each file.
Suggested markers: `pytest.mark.unit` for `test_sanitizer.py`,
`test_decision_log.py`, `test_local_commit.py`, `test_events_queue.py`; add
`pytest.mark.git_repo` alongside `pytest.mark.integration` for
`test_local_commit_wiring.py`.

---

### MINOR: Ratchet baseline not bumped (`test_no_dead_modules.category_1_auto_discovered_migrations`)

A new migration module was added, raising `category_1_auto_discovered_migrations`
from 75 to 76. Per the burn-down policy (Slice F C-004), `tests/architectural/_baselines.yaml`
must be updated with a one-line diff and a `# justification:` comment in the same PR.

No migration was found in the diff of `src/specify_cli/upgrade/migrations/` for this
mission, so the migration was likely added from a concurrent or prior commit that
landed simultaneously. This is a simple housekeeping fix.

---

### MINOR: Forbidden legacy term `ceremony` in doctrine guidelines (pre-existing)

`src/doctrine/missions/mission-steps/software-dev/tasks/guidelines.md:26` contains
the forbidden term `ceremony`. This appears to be pre-existing drift unrelated to
this mission's changes. It is surfaced here for completeness; it should be addressed
in a follow-up.

---

## Non-Goals / Locked Decisions Check

The following are confirmed **not** present in the merged code, consistent with the
Out of Scope section:

- No SaaS-side handling of `LocalCommit` frames (those are tracked in
  spec-kitty-saas issues #292, #295).
- No upgrade from "local only" to "verified" on push webhook.
- No retroactive PII removal from existing queue entries or git history.
- No changes to `.kittify/events/glossary/` replay log format.

---

## Dead Code / Live Caller Audit

All new modules have live callers from production entry points:

| Module | Live caller |
|--------|-------------|
| `events/sanitizer.py` | `status/store.py:196`, `decisions/emit.py:86` |
| `events/decision_log.py` | `next/runtime_bridge.py:94,1999,2336,2770` |
| `sync/local_commit.py` | `git/commit_helpers.py:1012`, `sync/client.py:185,429` |

`events/__init__.py` exports are consistent with actual module contents (`sanitize_event_for_log`, `Event`, `EventAdapter`, `HAS_LIBRARY`, `LamportClock`).

---

## Gate Results

| Gate | Result | Notes |
|------|--------|-------|
| Gate 1: Contract tests | PASS | No new contract tests added; existing suite unaffected |
| Gate 2: Architectural tests | FAIL | Ratchet baseline (minor); pytest marker violations (blocking) |
| Gate 3: Cross-repo E2E | NOT EVALUATED | spec-kitty-saas repo not present — environmental |
| Gate 4: Issue matrix | PRESENT | issue-matrix.md exists; no blocking issues listed |
| Target test suite (76 tests) | PASS | All pass in 0.73s |

---

## Verdict and Required Actions

**Verdict: CONDITIONAL PASS**

The implementation is functionally correct for 20 of 22 FRs. Before the next
release cycle the following must be addressed:

1. **(HIGH — blocker)** Fix `RISK-2`: `decisions.events.jsonl` `mission_id` field
   must be populated with the ULID from `meta.json`, not the human slug.
2. **(HIGH — blocker)** Fix `RISK-4`: Add `pytestmark` to all 5 new test files so
   they are not silently excluded from CI filter profiles.
3. **(HIGH — investigate)** Confirm `RISK-1`: Verify that `clarification.py`'s
   resolve path writes the seed file synchronously after `emit_clarification_resolved`.
   Add a test asserting the seed file is updated without queue drain.
4. **(MEDIUM — recommended)** Fix `RISK-3`: Apply `sanitize_event_for_log` inside
   `_local_append_event` in `glossary/events.py` for defense in depth.
5. **(MINOR — housekeeping)** Bump `_baselines.yaml` ratchet for
   `category_1_auto_discovered_migrations` from 75 to 76 with a justification comment.
