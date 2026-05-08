# Feature Specification: Dashboard Extraction Follow-up Remediations

**Feature Slug**: `dashboard-extraction-followup-01KQMNTW`
**Mission ID**: `01KQMNTWES1V299MVQBCNMKQJZ`
**Mission Type**: software-dev
**Created**: 2026-05-02
**Target Branch**: `feature/650-dashboard-ui-ux-overhaul`

## Overview

The post-merge mission review of `dashboard-service-extraction-01KQMCA6` (full
report at `/tmp/spec-kitty-mission-review-dashboard-service-extraction-01KQMCA6.md`)
issued a `PASS WITH NOTES` verdict and surfaced four non-blocking open items.
This follow-up mission closes all four items so the
`feature/650-dashboard-ui-ux-overhaul` branch can ship clean.

The four items are:

1. **RISK-1** — `tests/sync/test_daemon_intent_gate.py::test_no_unauthorized_daemon_call_sites`
   only scans `src/specify_cli/`, leaving `src/dashboard/` outside the gate.
   `src/dashboard/services/sync.py` already calls into the sync daemon (via DI
   today, which is authorized), but a future direct call would not be caught.
2. **DRIFT-1** — `src/specify_cli/scanner.py` was added during
   `dashboard-service-extraction-01KQMCA6` outside the DIRECTIVE_024 declared
   scope, with no WP claiming `owned_files` for it. The shim is technically
   correct (it bridges FR-010 by giving `src/dashboard/` a non-`specify_cli.dashboard`
   import path) and carries a `removal_release` annotation, but the governance
   record is silent on it.
3. **DRIFT-4** — FR-007 of the original mission required handlers to be thin
   delegation adapters. Two methods retained non-trivial bodies:
   `handle_kanban` parses path segments inline before delegating, and
   `handle_sync_trigger` is a 34-line method holding HTTP execution, error
   recovery, and 4-way result dispatch. Both should reduce to single service
   calls plus token validation.
4. **RISK-2** — Success Criterion SC-006 of the original mission required a
   manual browser smoke-test that was not formally executed before the mission
   merged. The `feature/650-dashboard-ui-ux-overhaul` branch should not ship to
   end users without that verification recorded.

## Domain Language

| Term | Canonical meaning |
|------|-------------------|
| **Daemon-intent gate** | The architectural test `test_no_unauthorized_daemon_call_sites` that AST-scans for direct calls to `ensure_sync_daemon_running` outside an explicit allowlist |
| **Thin adapter** | A handler method that contains only request parsing, authorization, and a single service call — no business logic |
| **Governance record** | The set of artifacts in `kitty-specs/<mission>/` plus the ownership map and ADRs in `architecture/2.x/` that describe what the mission owned and shipped |
| **Live verification** | A manual smoke-test against the running dashboard with a real browser, documented in the release notes |

## User Scenarios & Testing

### User Story 1 — Reviewer auditing the post-merge follow-ups (Priority: P0)

A reviewer reads the post-merge mission review report, finds the four non-blocking
items, opens this follow-up mission, and confirms that each finding maps to a
concrete remediation backed by a code change, governance update, or release
checklist entry. They can verify each remediation independently:

- For RISK-1: read `tests/sync/test_daemon_intent_gate.py` and confirm `src/dashboard/`
  is in the scan scope; run the test and see it pass.
- For DRIFT-1: read the original mission's governance record and confirm an
  addendum documents `src/specify_cli/scanner.py` ownership.
- For DRIFT-4: read `handle_kanban` and `handle_sync_trigger`; confirm each
  reduces to a single service call after token validation.
- For RISK-2: read the release notes / release checklist and confirm SC-006
  has a verification entry.

### User Story 2 — Future contributor wiring up new sync-daemon callers (Priority: P1)

A contributor adds a new direct call to `ensure_sync_daemon_running` somewhere
inside `src/dashboard/`. The daemon-intent gate test fails immediately, naming
the file and the unauthorized call. The contributor either adds the call site
to `ALLOWED_CALL_SITES` (with rationale) or refactors to use the DI seam.

### User Story 3 — Dashboard developer reading the handler layer (Priority: P1)

A developer opens `handle_kanban` or `handle_sync_trigger` to understand the
request flow. Each method reads as: parse request, validate, delegate to a
service, send response. The business logic — feature-ID resolution, daemon
ensure-running, HTTP POST to the local daemon, result interpretation — lives
in `MissionScanService.get_kanban` and `SyncService.trigger_sync` respectively.

### Edge cases

- **DI default still calls into `specify_cli.sync`**: `SyncService` uses
  `_ensure_running` and `_get_daemon_status` defaults that resolve at construction
  time. The gate must accept `dashboard/services/sync.py` as an authorized
  call site for `ensure_sync_daemon_running`, not flag it.
- **`scanner.py` removal-release annotation**: The shim already names the
  FastAPI migration milestone as the removal release. The governance addendum
  must not contradict that.
- **Release checklist for an internal feature branch**: This branch may not
  have a formal external release. The SC-006 verification entry should
  therefore land on whichever artifact actually gates the branch's promotion
  — either `feature/650-dashboard-ui-ux-overhaul`'s eventual PR description or
  a dedicated release-readiness file in the branch.

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | The daemon-intent gate test scans both `src/specify_cli/` and `src/dashboard/`; the existing assertion fires for any unauthorized direct call to `ensure_sync_daemon_running` in either tree | Approved |
| FR-002 | `ALLOWED_CALL_SITES` includes `src/dashboard/services/sync.py` with the function name and a one-line rationale; the existing entries are preserved | Approved |
| FR-003 | A test demonstrates the gate's negative path for `src/dashboard/`: a synthetic unauthorized call inside `src/dashboard/` (in a fixture or temp file) is detected by the same assertion | Approved |
| FR-004 | A governance addendum documents `src/specify_cli/scanner.py` as a shim owned by the dashboard service extraction mission, naming its purpose (FR-010 bridge for `dashboard.*`) and its removal trigger (FastAPI transport migration) | Approved |
| FR-005 | The addendum is filed inside `kitty-specs/dashboard-service-extraction-01KQMCA6/` and cross-linked from `architecture/2.x/05_ownership_map.md` and the dashboard ADR so future readers find it from any of the three entry points | Approved |
| FR-006 | `handle_kanban` is reduced to a thin adapter: feature-ID extraction from the request path moves into `MissionScanService` (or a small request-parse helper colocated with the service); the handler method calls one service method, then sends the response | Approved |
| FR-007 | `handle_sync_trigger` is reduced to a thin adapter: token validation stays in the handler; HTTP execution and 4-way result dispatch move into `SyncService.trigger_sync`, which returns a `SyncTriggerResult` already populated with the final HTTP status code and body | Approved |
| FR-008 | All seam tests in `tests/test_dashboard/test_seams.py` continue to pass, demonstrating that adapter delegation is unchanged from the operator's perspective; new seam-level coverage is added for the moved logic | Approved |
| FR-009 | A release-readiness document for `feature/650-dashboard-ui-ux-overhaul` records SC-006 live verification: who performed it, on what date, against which commit, and the observed dashboard behavior | Approved |
| FR-010 | The release-readiness document is committed to the branch alongside the code remediations so the verification artifact ships with the branch | Approved |

## Non-Functional Requirements

| ID | Attribute | Threshold | Status |
|----|-----------|-----------|--------|
| NFR-001 | Test suite execution time | The expanded daemon-intent gate scan does not increase the test's individual wall-clock duration by more than 100 ms (relative to its current measured baseline) | Approved |
| NFR-002 | Behavioral parity | Zero regressions in `tests/test_dashboard/`, `tests/architectural/`, and `tests/sync/` after the FR-006/FR-007 refactor | Approved |
| NFR-003 | Public API surface | No change to the JSON shape of `/api/sync/trigger` or `/api/kanban/<id>` responses; verified by existing seam and integration tests | Approved |
| NFR-004 | New dependencies | Zero new Python packages added to `pyproject.toml` | Approved |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | All changes land on `feature/650-dashboard-ui-ux-overhaul`; no new feature branches or PRs to other branches are created | Confirmed |
| C-002 | The daemon-intent gate's authorization model (explicit allowlist plus DI seams) is preserved; this mission expands scope, not policy | Confirmed |
| C-003 | The original mission's `removal_release` annotation on `src/specify_cli/scanner.py` is the canonical removal trigger; the governance addendum cites it rather than redefining it | Confirmed |
| C-004 | Refactors stay inside `src/dashboard/services/` and `src/specify_cli/dashboard/handlers/`; no other code areas are touched by FR-006 / FR-007 | Confirmed |
| C-005 | Token validation for `handle_sync_trigger` remains in the adapter; never moves into `SyncService` | Confirmed |

## Key Entities

- **`ALLOWED_CALL_SITES`** — module-level dict (or set) in `tests/sync/test_daemon_intent_gate.py` mapping authorized files to the daemon functions they may call directly. Mutated by FR-002.
- **`SyncTriggerResult`** — dataclass in `src/dashboard/services/sync.py` returning `status`, `http_status`, `manual_mode`, `reason`, `error`. Extended (or its consumer simplified) so the handler does not need to reinterpret it.
- **`MissionScanService.get_kanban`** — service method in `src/dashboard/services/mission_scan.py`. Either accepts a richer input parameter (request path, decomposed) or a small helper takes over feature-ID extraction so the handler sends one call.
- **Release-readiness document** — new artifact (path TBD; candidates include `kitty-specs/dashboard-extraction-followup-01KQMNTW/release-checklist.md` or a top-level branch checklist) recording SC-006 verification.

## Success Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| SC-001 | The daemon-intent gate detects an unauthorized direct call regardless of whether it lives in `src/specify_cli/` or `src/dashboard/` | The gate test passes today; the negative-path test (FR-003) demonstrates detection in `src/dashboard/` |
| SC-002 | A reviewer reading the original mission's governance record can find an entry explaining `src/specify_cli/scanner.py`'s purpose and removal trigger from any of: ownership map, ADR, mission directory | All three entry points reference the addendum |
| SC-003 | `handle_kanban` and `handle_sync_trigger` each contain exactly one service call (after request parsing and token validation), with no inline HTTP, no inline path arithmetic, no inline result interpretation | Code review against the post-refactor diff; line counts ≤ 15 per method |
| SC-004 | The full test suite (`tests/test_dashboard/`, `tests/architectural/`, `tests/sync/`) passes locally after the refactor | Local run; CI run on the branch |
| SC-005 | SC-006 of the original mission has a recorded verification on the branch before any release tag derived from it | Release-readiness document exists, named operator, recorded date, commit reference |

## Assumptions

- The original mission's `SyncTriggerResult` dataclass already carries enough fields to encode every dispatch outcome the handler currently translates inline; if not, the dataclass may be extended (additive only) without breaking consumers.
- The negative-path daemon-intent test (FR-003) can use a fixture file or `tmp_path` rather than introducing a permanent unauthorized call site in production code.
- The `feature/650-dashboard-ui-ux-overhaul` branch will eventually merge somewhere downstream (likely `main`); the release-readiness document is the artifact that future merge will reference. The exact downstream merge target is not in scope for this mission.

## Governance

### Active Directives

- **DIRECTIVE_024** (Locality of Change) — applied to all four findings; this mission's allowed scope is `tests/sync/`, `src/dashboard/services/`, `src/specify_cli/dashboard/handlers/`, `kitty-specs/dashboard-service-extraction-01KQMCA6/` (governance addendum), `kitty-specs/dashboard-extraction-followup-01KQMNTW/` (this mission's artifacts), and `architecture/2.x/` (cross-link updates).
- **DIRECTIVE_010** (Test Coverage Discipline) — FR-008 ensures pre-existing seam coverage continues to pass; FR-003 adds new negative-path coverage.

### Applied Tactics

- `architectural-test-discipline` — for the daemon-intent gate expansion (FR-001, FR-002, FR-003).
- `governance-record-completeness` — for the scanner-shim addendum (FR-004, FR-005).
- `thin-adapter-pattern` — for the handler refactor (FR-006, FR-007).
