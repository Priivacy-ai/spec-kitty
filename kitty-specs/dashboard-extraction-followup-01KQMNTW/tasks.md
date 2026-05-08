# Tasks — Dashboard Extraction Follow-up Remediations

**Mission**: `dashboard-extraction-followup-01KQMNTW`
**Branch**: `feature/650-dashboard-ui-ux-overhaul`
**Spec / Plan**: [spec.md](./spec.md) · [plan.md](./plan.md)

> **Implementation status**: All FR-001..FR-010 changes already landed at commit `dcbba9439` on `feature/650-dashboard-ui-ux-overhaul`. The work-package decomposition in this document formalizes the post-merge review trail. Each WP's "implementation" subtasks reference the actual diff that closed the finding.

## Subtask Index

| ID   | Description | WP   | Parallel |
|------|-------------|------|----------|
| T001 | Add `_scan_for_callers` helper + `SCAN_ROOTS` tuple covering `src/specify_cli/` and `src/dashboard/` to `tests/sync/test_daemon_intent_gate.py` | WP01 | — | [D] |
| T002 | Add `src/dashboard/services/sync.py` to `ALLOWED_CALL_SITES` with rationale comment | WP01 | — | [D] |
| T003 | Add `test_gate_detects_unauthorized_call_in_dashboard_tree` — synthetic-tree negative-path test for the scan | WP01 | — | [D] |
| T004 | Author `kitty-specs/dashboard-service-extraction-01KQMCA6/scanner-shim-ownership-addendum.md` (purpose, removal trigger, audit trail) | WP02 | [D] |
| T005 | Add `src/specify_cli/scanner.py` shim entry to `architecture/2.x/05_ownership_map.md` Dashboard slice with cross-link to the addendum | WP02 | — | [D] |
| T006 | Mirror entry in `architecture/2.x/05_ownership_manifest.yaml` | WP02 | — | [D] |
| T007 | Cross-link the addendum from `architecture/2.x/adr/2026-05-02-1-dashboard-service-extraction.md` Consequences section | WP02 | — | [D] |
| T008 | Add module-level `parse_kanban_path` helper in `src/dashboard/services/mission_scan.py` | WP03 | — | [D] |
| T009 | Reduce `handle_kanban` to single service call in `src/specify_cli/dashboard/handlers/features.py`; switch to `_send_json` | WP03 | — | [D] |
| T010 | Add `SyncTriggerResult.body()` in `src/dashboard/services/sync.py` (4-branch dispatch) | WP03 | — | [D] |
| T011 | Reduce `handle_sync_trigger` to single service call in `src/specify_cli/dashboard/handlers/api.py`; use `result.body()` | WP03 | — | [D] |
| T012 | Update kanban seam test in `tests/test_dashboard/test_seams.py` to use `_send_json` pattern; add `test_kanban_returns_404_on_short_path` | WP03 | [D] |
| T013 | Add parametrized `test_sync_trigger_dispatches_all_result_branches` and pure-helper class for `parse_kanban_path` + body() variants in `tests/test_dashboard/test_seams.py` | WP03 | [D] |
| T014 | Author `kitty-specs/dashboard-extraction-followup-01KQMNTW/release-checklist.md` with operator/date/commit slots, SC-006 live-verification checklist, and standing release gates | WP04 | [D] |
| T015 | Run `PYENV_VERSION=3.13.12 uv run --no-sync pytest tests/test_dashboard/ tests/architectural/ tests/sync/test_daemon_intent_gate.py -q`; confirm 310 passed | WP04 | — | [D] |

## Dependencies

```
WP01 ──┐
WP02 ──┼──▶ WP04 (final QA + release-checklist)
WP03 ──┘
```

WP01 / WP02 / WP03 are independent of each other (touch different files). WP04 depends on all three: the release-checklist mentions the FR coverage, and the QA run validates that all changes integrate cleanly.

## Work Packages

### WP01 — RISK-1: daemon-gate scan expansion

**Goal**: Expand `test_no_unauthorized_daemon_call_sites` to cover `src/dashboard/` so future direct calls to `ensure_sync_daemon_running` from the new package are caught by the existing gate.

**Priority**: P0
**Independent test**: `pytest tests/sync/test_daemon_intent_gate.py -q` passes; the negative-path test detects an unauthorized call in a synthetic `src/dashboard/` tree.

**Subtasks**:
- [x] T001 Add `_scan_for_callers` + `SCAN_ROOTS`
- [x] T002 Add `src/dashboard/services/sync.py` to allowlist
- [x] T003 Add negative-path test

**Implementation sketch**: see `tests/sync/test_daemon_intent_gate.py` — change already landed in commit `dcbba9439`.

**Owned files**: `tests/sync/test_daemon_intent_gate.py`.

### WP02 — DRIFT-1: scanner-shim governance addendum

**Goal**: Retroactively document ownership of `src/specify_cli/scanner.py` so the parent mission's governance record is complete.

**Priority**: P0
**Independent test**: a reviewer reading the parent mission's record can find the scanner shim entry from any of (a) ownership map, (b) ADR, (c) mission directory.

**Subtasks**:
- [x] T004 Author addendum
- [x] T005 Add ownership map entry
- [x] T006 Mirror manifest entry
- [x] T007 Cross-link from ADR

**Implementation sketch**: see commit `dcbba9439` for the actual files.

**Owned files**: `kitty-specs/dashboard-service-extraction-01KQMCA6/scanner-shim-ownership-addendum.md`, `architecture/2.x/05_ownership_map.md`, `architecture/2.x/05_ownership_manifest.yaml`, `architecture/2.x/adr/2026-05-02-1-dashboard-service-extraction.md`.

### WP03 — DRIFT-4: thin handlers

**Goal**: Complete FR-007 of the parent mission by reducing `handle_kanban` and `handle_sync_trigger` to single-call adapters.

**Priority**: P1
**Independent test**: every existing seam test in `tests/test_dashboard/test_seams.py` passes; new pure-helper tests pass; `handle_sync_trigger` body is ≤ 15 lines; `handle_kanban` body is ≤ 10 lines.

**Subtasks**:
- [x] T008 `parse_kanban_path` helper
- [x] T009 thin `handle_kanban`
- [x] T010 `SyncTriggerResult.body()`
- [x] T011 thin `handle_sync_trigger`
- [x] T012 update kanban seam test
- [x] T013 add parametrized body() coverage + pure-helper tests

**Implementation sketch**: see commit `dcbba9439` for the actual diff.

**Owned files**: `src/dashboard/services/mission_scan.py`, `src/dashboard/services/sync.py`, `src/specify_cli/dashboard/handlers/features.py`, `src/specify_cli/dashboard/handlers/api.py`, `tests/test_dashboard/test_seams.py`.

### WP04 — RISK-2: release-checklist + final QA

**Goal**: Record SC-006 live-verification slot on the branch, run full test suite, confirm zero regressions.

**Priority**: P1
**Independent test**: `release-checklist.md` exists with all sections; the test suite is green.

**Subtasks**:
- [x] T014 Author `release-checklist.md`
- [x] T015 Run full test suite

**Implementation sketch**: see commit `dcbba9439` for the release-checklist file. Test suite: 310 passed, 1 skipped (the skip is unrelated retrospective-events boundary test).

**Owned files**: `kitty-specs/dashboard-extraction-followup-01KQMNTW/release-checklist.md`.

## Definition of Done

The mission is done when:

- [x] Every WP's subtasks are checked off and committed.
- [x] `pytest tests/test_dashboard/ tests/architectural/ tests/sync/test_daemon_intent_gate.py -q` is green.
- [x] All four findings (RISK-1, DRIFT-1, DRIFT-4, RISK-2) have a corresponding WP that landed and was approved.
- [x] The post-merge review report at `/tmp/spec-kitty-mission-review-dashboard-service-extraction-01KQMCA6.md`'s "Open items (non-blocking)" list is fully addressed.
