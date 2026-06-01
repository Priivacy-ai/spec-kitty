---
work_package_id: WP04
title: Glossary Queue Reduction
dependencies: []
requirement_refs:
- FR-018
- FR-019
- FR-020
- FR-021
- FR-022
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-event-architecture-cli-git-truth-01KT119Y
base_commit: 6a553f0a7841a3e2c17652192160cd11af4bfcfa
created_at: '2026-06-01T08:16:40.086405+00:00'
subtasks:
- T015
- T016
- T017
- T018
agent: "claude:claude-sonnet-4-6:orchestrator:orchestrator"
shell_pid: "67186"
history:
- date: '2026-06-01'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/glossary/
execution_mode: code_change
owned_files:
- src/specify_cli/glossary/events.py
- tests/specify_cli/glossary/test_events_queue.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Drop `GlossarySenseUpdated` from the canonical queue adapter in `glossary/events.py` so that per-extraction noise (hundreds of events per session) is no longer queued for SaaS delivery. `GlossaryClarificationResolved` and `GlossaryClarificationRequested` must continue reaching the queue unchanged. Confirm the seed file update on resolution is already synchronous.

**Implement command**: `spec-kitty agent action implement WP04 --agent claude`

**Dependencies**: None — independent of all other WPs.

---

## Context

**The problem**: Every glossary term extraction emits a `GlossarySenseUpdated` event. A typical session with 100 extraction steps generates hundreds of these. The SaaS has no consumer that needs per-extraction granularity — the seed file already captures current state. The queue is polluted with noise, slowing drain and obscuring the handful of semantically meaningful clarification events.

**The change**: In `emit_glossary_sense_updated()`, skip calling `_pkg_append_event()` (the canonical adapter that enqueues for SaaS delivery). The local `.kittify/events/glossary/<mission_id>.events.jsonl` write is unchanged — local replay must continue to work.

**Key files to read before starting**:
- `src/specify_cli/glossary/events.py` — find `emit_glossary_sense_updated()` (approximately line 984) and `_persist_event()` (approximately line 530)
- `src/specify_cli/glossary/store.py` — confirm seed file update timing

**Spec references**: FR-018, FR-019, FR-020, FR-021, FR-022, NFR-004

---

## Branch Strategy

- Planning base: `main`
- Final merge target: `main`

---

## Subtask Guidance

### T015 — Skip `_pkg_append_event` in `emit_glossary_sense_updated()`

**Purpose**: Prevent `GlossarySenseUpdated` from reaching the SaaS queue while preserving local JSONL persistence.

**Steps**:
1. Read `src/specify_cli/glossary/events.py` and locate `emit_glossary_sense_updated()` (~line 984).
2. In that function, find the `_persist_event()` call (or direct `_pkg_append_event()` call).
3. The `_persist_event()` function has two paths: canonical adapter (`_pkg_append_event`) and local JSONL fallback. We want **local JSONL only** for `GlossarySenseUpdated`.

   **Option A**: If `emit_glossary_sense_updated()` calls `_persist_event()`, replace it with a direct local-JSONL-only call:
   ```python
   # Before:
   _persist_event(event_dict, repo_root, mission_id, canonical_cls=_CanonicGlossarySenseUpdated)

   # After (local-only — GlossarySenseUpdated is not queued for SaaS; see spec-kitty #1549):
   _local_append_event(event_dict, get_event_log_path(repo_root, mission_id))
   ```

   **Option B**: Add a bypass flag to `_persist_event()` — but prefer Option A to avoid changing the shared function signature.

4. Add a comment on the changed line:
   ```python
   # GlossarySenseUpdated is local-only — not queued for SaaS delivery (spec-kitty #1549).
   # The seed file is the authoritative current glossary state.
   ```

**Files**: `src/specify_cli/glossary/events.py` (~3 lines changed)

---

### T016 — Verify `GlossaryClarificationResolved/Requested` still reach canonical adapter

**Purpose**: Confirm the change to T015 did not accidentally suppress the two event types that must stay in the queue.

**Steps**:
1. Read `emit_glossary_clarification_resolved()` and `emit_glossary_clarification_requested()` in `glossary/events.py`.
2. Confirm both still call `_persist_event()` with their canonical class (not the local-only path).
3. No code changes needed unless those functions were accidentally affected. Document the review outcome in a test assertion (T018).

**Files**: Review only, unless a bug is found.

---

### T017 — Confirm seed file update on `GlossaryClarificationResolved` is synchronous

**Purpose**: FR-021 requires the seed file to be updated immediately after each resolved clarification. Verify this is already the case (research.md Finding 6 says it is).

**Steps**:
1. Read `src/specify_cli/glossary/store.py` and `src/specify_cli/glossary/clarification.py`.
2. Trace the call path from `GlossaryClarificationResolved` emission to the seed file write in `.kittify/glossaries/<scope>.yaml`.
3. Confirm the seed write is synchronous (not deferred, not queued).
4. If the write is already synchronous: no code change needed — add a test assertion (T018) confirming the file is updated before the function returns.
5. If the write is deferred: add a synchronous write call and document the change.

**Files**: Review only (expected outcome: no code change needed).

---

### T018 — Tests confirming queue exclusion for `GlossarySenseUpdated`

**Purpose**: Automated proof that the queue change is correct and regressions are caught.

**Steps**:
1. Create `tests/specify_cli/glossary/test_events_queue.py`.
2. Mock `_pkg_append_event` and call `emit_glossary_sense_updated()` with a sample payload.
3. Assert `_pkg_append_event` was **not** called:
   ```python
   def test_glossary_sense_updated_not_queued(tmp_path):
       with patch("specify_cli.glossary.events._pkg_append_event") as mock_queue:
           emit_glossary_sense_updated(...)
           mock_queue.assert_not_called()
   ```
4. Assert the local JSONL file **was** written (confirm the event appears in the local log).
5. Test `GlossaryClarificationResolved` — assert `_pkg_append_event` **was** called:
   ```python
   def test_glossary_clarification_resolved_still_queued(tmp_path):
       with patch("specify_cli.glossary.events._pkg_append_event") as mock_queue:
           emit_glossary_clarification_resolved(...)
           mock_queue.assert_called_once()
   ```
6. Same assertion for `GlossaryClarificationRequested`.
7. If T017 found the seed file update is synchronous, add:
   ```python
   def test_seed_file_updated_synchronously_on_resolution(tmp_path):
       emit_glossary_clarification_resolved(...)
       seed_file = tmp_path / ".kittify" / "glossaries" / "test-scope.yaml"
       assert seed_file.exists()
       # assert the resolved term appears in the seed file
   ```

**Files**: `tests/specify_cli/glossary/test_events_queue.py` (~90 lines)

---

## Definition of Done

- [ ] `emit_glossary_sense_updated()` no longer calls the canonical queue adapter
- [ ] Local JSONL write in `emit_glossary_sense_updated()` is unchanged
- [ ] `GlossaryClarificationResolved` and `GlossaryClarificationRequested` still queue via canonical adapter
- [ ] Seed file confirmed synchronous on resolution
- [ ] `mypy --strict` passes on all modified files
- [ ] New tests pass; zero `GlossarySenseUpdated` in mock-captured queue calls

## Risks

- `_pkg_append_event` may be `None` when `spec-kitty-events` is not installed (the `EVENTS_AVAILABLE` flag). The existing guard `if EVENTS_AVAILABLE and _pkg_append_event is not None` must remain intact for other event types — only `GlossarySenseUpdated` bypasses it.
- Ensure the local JSONL write does not also go through `_pkg_append_event` — trace the `_local_append_event` call path to confirm it is truly local-only.

## Reviewer Guidance

1. Confirm that `GlossarySenseUpdated` local JSONL write is untouched
2. Confirm `GlossaryClarificationResolved/Requested` still call the canonical adapter
3. Check that the `EVENTS_AVAILABLE` guard structure for other event types is unaffected

## Activity Log

- 2026-06-01T08:16:40Z – claude:claude-sonnet-4-6:orchestrator:orchestrator – shell_pid=38585 – Assigned agent via action command
- 2026-06-01T08:27:04Z – claude:claude-sonnet-4-6:orchestrator:orchestrator – shell_pid=38585 – Implementation complete, cycle 1. Tests pass (9 new tests), lint clean. GlossarySenseUpdated now local-only, clarification events still queued.
- 2026-06-01T08:29:28Z – claude:claude-sonnet-4-6:orchestrator:orchestrator – shell_pid=67186 – Started review via action command
