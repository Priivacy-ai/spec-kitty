# Tasks: Relocate SaaS-Sync Flag to Core

**Mission**: relocate-saas-sync-flag-to-core-01KWQ3RV
**Branch**: planning/base/merge-target = `feat/relocate-saas-sync-flag-to-core`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

Strictly-linear (WP01 → WP02). WP01 is the code + boundary change (ATDD red-first); WP02 records the resolution in the ADR + stability contract. Charter scoped-testing: each WP runs only its bounding test packages, not the full suite.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | RED commit: empty `ALLOWLIST` + delete positive-control (`:264-272`) while coordinator still imports INTEGRATION | WP01 | |
| T002 | Create `core/saas_sync_config.py` (move the 5 symbols byte-for-byte + `__all__`) | WP01 | |
| T003 | Repoint `readiness/coordinator.py:237` to `core.saas_sync_config` | WP01 | |
| T004 | Rewrite `saas/rollout.py` as a thin re-export shim; verify the re-export surfaces still resolve | WP01 | |
| T005 | Tighten ratchet `<= 1` → `== 0` + sweep all `<= 1` prose in the boundary test | WP01 | |
| T006 | Fix 3 stale docstrings (`sync`/`tracker` feature_flags "canonical home"; `upgrade_ux.py:77` false "shared") | WP01 | [P] |
| T007 | Validate WP01 green (boundary + saas + feature-flag tests; ruff + mypy-strict) | WP01 | |
| T008 | Update the ADR — sweep all stale `<=1`/"single/exactly one" refs + shim-depth note + #2252 | WP02 | |
| T009 | Update the stability contract `saas_rollout.md` (module line, semantics, shims, version bump) | WP02 | [P] |
| T010 | Validate WP02 green (`test_example_round_trip` + `test_no_legacy_terminology`) | WP02 | |

---

## WP01 — Relocate the flag reader + close the boundary (ATDD red-first)

**Goal**: Move the pure `SPEC_KITTY_ENABLE_SAAS_SYNC` reader from INTEGRATION `saas/rollout.py` into CORE `core/saas_sync_config.py`, repoint the sole CORE importer, retain `saas/rollout.py` as a re-export shim, empty the `ALLOWLIST` and tighten the ratchet to `== 0`, remove the stale positive-control, and fix the stale "canonical home" docstrings — so no CORE module imports INTEGRATION and the boundary is exemption-free permanently. No behavior change; single canonical definition.
**Priority**: P1
**Independent test**: `pytest tests/architectural/test_integration_boundary.py` green with empty `ALLOWLIST` (ratchet `== 0`); `tests/saas/` + feature-flag tests pass unchanged; ruff + mypy-strict clean.
**Requirements**: FR-001, FR-002, FR-003, FR-004
**Dependencies**: none

- [x] T001 RED commit: empty `ALLOWLIST` + delete positive-control (`:264-272`) while coordinator still imports INTEGRATION (WP01)
- [x] T002 Create `core/saas_sync_config.py` (move the 5 symbols byte-for-byte + `__all__`) (WP01)
- [x] T003 Repoint `readiness/coordinator.py:237` to `core.saas_sync_config` (WP01)
- [x] T004 Rewrite `saas/rollout.py` as a thin re-export shim; verify the re-export surfaces still resolve (WP01)
- [x] T005 Tighten ratchet `<= 1` → `== 0` + sweep all `<= 1` prose in the boundary test (WP01)
- [x] T006 Fix 3 stale docstrings (`sync`/`tracker` feature_flags; `upgrade_ux.py:77`) (WP01)
- [x] T007 Validate WP01 green (boundary + saas + feature-flag tests; ruff + mypy-strict) (WP01)

Prompt: [tasks/WP01-relocate-flag-and-close-boundary.md](./tasks/WP01-relocate-flag-and-close-boundary.md) (~420 lines)

## WP02 — Record the resolution (ADR + stability contract)

**Goal**: Update the ADR and the stability contract to reflect the resolved exemption + the new canonical home, sweeping every stale "single/one exemption" and `<= 1` reference.
**Priority**: P1
**Independent test**: `pytest tests/contract/test_example_round_trip.py tests/architectural/test_no_legacy_terminology.py` green; no stale `<= 1`/"single remaining" refs remain in the ADR.
**Requirements**: FR-005, FR-006
**Dependencies**: WP01

- [ ] T008 Update the ADR — sweep all stale `<=1`/"single/exactly one" refs + shim-depth note + #2252 (WP02)
- [ ] T009 Update the stability contract `saas_rollout.md` (module line, semantics, shims, version bump) (WP02)
- [ ] T010 Validate WP02 green (`test_example_round_trip` + `test_no_legacy_terminology`) (WP02)

Prompt: [tasks/WP02-record-adr-and-contract.md](./tasks/WP02-record-adr-and-contract.md) (~220 lines)

---

## MVP / sequencing
Both WPs are required for a coherent, green end state (WP01 closes the boundary; WP02 records it). Strictly sequential — no parallel lanes.
