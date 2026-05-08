# Implementation Plan: Dashboard Extraction Follow-up Remediations

**Branch**: `feature/650-dashboard-ui-ux-overhaul` | **Date**: 2026-05-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/dashboard-extraction-followup-01KQMNTW/spec.md`

## Summary

Close the four non-blocking findings from the post-merge review of mission `dashboard-service-extraction-01KQMCA6` (#111). Three of the four are small targeted code or test changes; one is documentation. All four landed on `feature/650-dashboard-ui-ux-overhaul` in commit `dcbba9439` before this plan was written — this mission's role is to formalize the work-package decomposition and review trail so the post-merge audit cycle is complete.

The four items:

- **RISK-1 (FR-001..FR-003)** — expand `tests/sync/test_daemon_intent_gate.py::test_no_unauthorized_daemon_call_sites` to scan `src/dashboard/` in addition to `src/specify_cli/`; add `src/dashboard/services/sync.py` to `ALLOWED_CALL_SITES`; add a negative-path test that proves the scan covers `src/dashboard/`.
- **DRIFT-1 (FR-004..FR-005)** — file a governance addendum for `src/specify_cli/scanner.py` (the shim added during mission #111); cross-link from the ownership map and the dashboard ADR.
- **DRIFT-4 (FR-006..FR-008)** — finish FR-007 of the parent mission by reducing `handle_kanban` and `handle_sync_trigger` to single-call adapters: move `parse_kanban_path` to a module-level helper in `dashboard.services.mission_scan`, add `SyncTriggerResult.body()` so the handler dispatches via one call.
- **RISK-2 (FR-009..FR-010)** — record SC-006 live verification on the branch via a release-checklist artifact.

## Technical Context

**Language/Version**: Python 3.11+ (existing repo requirement; tests pass on 3.13.12).
**Primary Dependencies**: no new external deps — uses existing stdlib (`ast` for the gate scan), Pydantic-free dataclass (`SyncTriggerResult`), pytest fixtures.
**Storage**: filesystem only — `tests/sync/test_daemon_intent_gate.py`, `kitty-specs/dashboard-service-extraction-01KQMCA6/scanner-shim-ownership-addendum.md`, `architecture/2.x/05_ownership_map.md`, `architecture/2.x/05_ownership_manifest.yaml`, `architecture/2.x/adr/2026-05-02-1-dashboard-service-extraction.md`, `kitty-specs/dashboard-extraction-followup-01KQMNTW/release-checklist.md`.
**Testing**: pytest + the new negative-path daemon-gate test + parametrized seam tests for SyncTriggerResult.body().
**Target Platform**: same as parent mission — local dashboard, loopback only.
**Project Type**: single project.
**Performance Goals**: NFR-001 (≤ 100 ms increase on the daemon-gate test); NFR-002 (zero behavioral regressions). Both verified locally.
**Constraints**: no new Python packages (NFR-004); no JSON shape change on `/api/sync/trigger` or `/api/kanban` (NFR-003); all changes on `feature/650-dashboard-ui-ux-overhaul`.
**Scale/Scope**: 4 findings, ~12 files modified or created.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter directive | Conformance |
|-------------------|-------------|
| DIRECTIVE_024 (Locality of Change) | Pass — allowed scope: `tests/sync/`, `src/dashboard/services/`, `src/specify_cli/dashboard/handlers/`, `kitty-specs/dashboard-service-extraction-01KQMCA6/` (governance addendum), `kitty-specs/dashboard-extraction-followup-01KQMNTW/` (this mission), `architecture/2.x/`. Every change in commit `dcbba9439` lands inside that scope. |
| DIRECTIVE_010 (Test Coverage Discipline) | Pass — FR-003 adds a negative-path test; FR-008 ensures all existing seam coverage continues to pass; new seam-level coverage was added for `SyncTriggerResult.body()` and `parse_kanban_path`. |

No charter violations. No `Complexity Tracking` entries needed.

## Implementation status

Code/doc changes for FR-001..FR-010 already landed at commit `dcbba9439` on `feature/650-dashboard-ui-ux-overhaul`:

- `tests/sync/test_daemon_intent_gate.py` — `_scan_for_callers` helper, `SCAN_ROOTS` tuple, negative-path test
- `src/dashboard/services/mission_scan.py` — module-level `parse_kanban_path`
- `src/dashboard/services/sync.py` — `SyncTriggerResult.body()`
- `src/specify_cli/dashboard/handlers/features.py` — thin `handle_kanban` (single service call after path parse)
- `src/specify_cli/dashboard/handlers/api.py` — thin `handle_sync_trigger` (single service call + `_send_json(result.http_status, result.body())`)
- `tests/test_dashboard/test_seams.py` — kanban seam test moved to `_send_json` pattern; new parametrized SyncTriggerResult.body() coverage
- `kitty-specs/dashboard-service-extraction-01KQMCA6/scanner-shim-ownership-addendum.md` — new governance addendum
- `architecture/2.x/05_ownership_map.md` — Dashboard.shims gains scanner.py entry with cross-link
- `architecture/2.x/05_ownership_manifest.yaml` — mirrored
- `architecture/2.x/adr/2026-05-02-1-dashboard-service-extraction.md` — Consequences section names the scanner shim, links to the addendum
- `kitty-specs/dashboard-extraction-followup-01KQMNTW/release-checklist.md` — SC-006 verification slots + standing release gates

All 310 dashboard / architectural / daemon-intent-gate tests pass under `PYENV_VERSION=3.13.12 uv run --no-sync pytest tests/test_dashboard/ tests/architectural/ tests/sync/test_daemon_intent_gate.py -q`.

## Project Structure

### Documentation (this feature)

```
kitty-specs/dashboard-extraction-followup-01KQMNTW/
├── spec.md                  # ✅ committed
├── plan.md                  # 🆕 this file
├── checklists/
│   └── requirements.md      # ✅ committed
├── release-checklist.md     # ✅ committed
└── tasks.md                 # 🆕 phase 2 (created next)
```

### Source code (already in tree at commit dcbba9439)

```
tests/sync/
└── test_daemon_intent_gate.py             # ✏️  expanded scan + negative-path test

src/dashboard/services/
├── mission_scan.py                        # ✏️  parse_kanban_path module-level helper
└── sync.py                                # ✏️  SyncTriggerResult.body()

src/specify_cli/dashboard/handlers/
├── features.py                            # ✏️  thin handle_kanban
└── api.py                                 # ✏️  thin handle_sync_trigger

tests/test_dashboard/
└── test_seams.py                          # ✏️  parametrized body() coverage + pure-helper tests

kitty-specs/dashboard-service-extraction-01KQMCA6/
└── scanner-shim-ownership-addendum.md     # 🆕 governance addendum

architecture/2.x/
├── 05_ownership_map.md                    # ✏️  Dashboard.shims entry
├── 05_ownership_manifest.yaml             # ✏️  mirrored
└── adr/2026-05-02-1-dashboard-service-extraction.md  # ✏️  Consequences cross-link
```

**Structure Decision**: tightly scoped follow-up mission. No new top-level packages. All edits inside DIRECTIVE_024 allowed scope.

## Phase 0 — Research

Not applicable for this mission. The four findings are mechanically defined by the post-merge review report at `/tmp/spec-kitty-mission-review-dashboard-service-extraction-01KQMCA6.md`. No design alternatives to research.

## Phase 1 — Design & Contracts

The relevant contracts are inherited from the parent mission. This mission's "design" output is the spec itself plus the governance addendum (`scanner-shim-ownership-addendum.md`), which serves as the contract for shim ownership. No new `data-model.md`, `contracts/`, or `quickstart.md` are required — the spec's FR table and the release-checklist already capture everything a reviewer needs.

## Phase 2 — Tasks

Phase 2 produces `tasks.md` with one work package per finding plus a small final QA WP. Anticipated decomposition:

- **WP01 — RISK-1: daemon-gate scan expansion** (3 subtasks)
- **WP02 — DRIFT-1: scanner-shim governance addendum** (3 subtasks, parallelizable with WP01)
- **WP03 — DRIFT-4: thin handlers** (4 subtasks)
- **WP04 — RISK-2: release-checklist record** (2 subtasks, parallelizable with the others)

## Phase 3 — Implementation

Already complete at commit `dcbba9439`. The implement-review cycle in this mission is a bookkeeping pass: each WP claims and approves the work that already landed.

## Phase 4 — Review & Merge

Per-WP review confirms the actual diff matches the WP's owned files and FRs. After all WPs are `done`, `spec-kitty merge --mission dashboard-extraction-followup-01KQMNTW` runs the standard merge pipeline. Post-merge `/spec-kitty.mission-review` (optional) audits this remediation mission for its own drift.

## Complexity Tracking

*No charter violations identified. Section intentionally empty.*
