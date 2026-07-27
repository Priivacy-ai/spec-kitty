# Mission Specification: Relocate SaaS-Sync Flag to Core

**Mission**: relocate-saas-sync-flag-to-core-01KWQ3RV
**Mission type**: software-dev
**Closes**: #2252 (follow-up to #2172)
**Status**: Draft (post-spec gate remediated 2026-07-04)

## Summary

The architectural import boundary enforced by #2172 keeps the **CORE** layer
(`core/`, `status/`, `readiness/`, `invocation/`) independent of the
**INTEGRATION** layer (`orchestrator_api/`, `sync/`, `tracker/`, `saas/`,
`saas_client/`). It retains exactly one documented exemption: the CORE module
`readiness/coordinator.py:237` lazily imports `is_saas_sync_enabled` from the
INTEGRATION module `saas/rollout.py` — solely to read a pure on/off SaaS-sync
feature flag (`SPEC_KITTY_ENABLE_SAAS_SYNC`) with no side effects.

This mission relocates that pure flag reader into a CORE module where it belongs,
repoints the sole CORE caller, removes the exemption AND tightens the count-ratchet
so the boundary is enforced with **zero carve-outs permanently**, and records the
resolution in the ADR + the stability contract — with no behavior change and a
single canonical source for the flag. `saas/rollout.py` is **retained as a thin
re-export shim** (delete is foreclosed — see C-002).

## Domain Language

- **CORE set** — `src/specify_cli/{core,status,readiness,invocation}/`, per the boundary guard.
- **INTEGRATION set** — `src/specify_cli/{orchestrator_api,sync,tracker,saas,saas_client}/`.
- **Boundary rule** — CORE MUST NOT import INTEGRATION (the reverse is allowed).
- **The flag reader** — `is_saas_sync_enabled` + `saas_sync_disabled_message` + `SAAS_SYNC_ENV_VAR` (and the private `_TRUTHY_VALUES` / `_DISABLED_MESSAGE`): the pure, side-effect-free reader of `SPEC_KITTY_ENABLE_SAAS_SYNC`, currently the single source of truth in `saas/rollout.py`.
- **Re-export surfaces** — the modules that re-export the flag names and must keep resolving after the move: `saas/rollout.py` (retained shim), `saas/__init__.py`, `sync/feature_flags.py`, `tracker/feature_flags.py`, and the `sync/__init__.py` / `tracker/__init__.py` lazy facades.
- **Canonical authority** — exactly one *definition* of `is_saas_sync_enabled` / `saas_sync_disabled_message`; every re-export surface delegates, never redefines.

## User Scenarios & Testing

### Primary scenario — boundary enforced with zero exemptions, permanently
The architectural CI gate (`test_integration_boundary.py`) scans the CORE-set
trees for any import of an INTEGRATION module. After this mission, the scan finds
**zero** violations with an **empty** `ALLOWLIST`, and the count-ratchet is
**tightened from `<= 1` to `== 0`** so no future exemption can be silently
re-added. A future CORE→INTEGRATION import is rejected outright.

### Behavior-preservation scenario — the flag reads identically
A contributor with `SPEC_KITTY_ENABLE_SAAS_SYNC` set (or unset) runs any command
that gates on hosted SaaS sync. `is_saas_sync_enabled()` returns the identical
result (truthy set `{1, true, yes, on}`, case-insensitive after strip; everything
else False), and `saas_sync_disabled_message()` returns the byte-identical frozen
message. Every consumer — `readiness/coordinator.py`, the re-export surfaces, and
the ~20 downstream importers — behaves exactly as before; only the import path of
the canonical *definition* changed. The retained `saas/rollout.py` shim re-exports
the **same objects** (object identity preserved), so `tests/saas/test_rollout.py`'s
identity assertions pass unchanged.

### Edge case — no second authority is introduced
There remains exactly **one** `def is_saas_sync_enabled` and one
`def saas_sync_disabled_message` repo-wide, in the new CORE home. `saas/rollout.py`,
`saas/__init__.py`, and the `sync`/`tracker` `feature_flags` shims **re-export**
(never redefine). (The unrelated truthy parsers in `compat/config.py` and
`readiness/upgrade_ux.py` gate *different* flags and are out of scope.)

### Invariant that must always hold
No CORE-set module imports any INTEGRATION-set module, and the
`SPEC_KITTY_ENABLE_SAAS_SYNC` check has a single canonical *definition*. The
`saas_rollout.md` stability contract (byte-frozen disabled message) is preserved.

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Relocate the pure flag reader — `is_saas_sync_enabled`, `saas_sync_disabled_message`, `SAAS_SYNC_ENV_VAR` (and the private `_TRUTHY_VALUES` / `_DISABLED_MESSAGE`) — from `src/specify_cli/saas/rollout.py` into a CORE-set module (under `core/`, e.g. `core/saas_sync_config.py`), which becomes THE single canonical *definition* of the `SPEC_KITTY_ENABLE_SAAS_SYNC` check. | Proposed |
| FR-002 | Repoint the sole CORE-set importer — `readiness/coordinator.py:237` (`from specify_cli.saas.rollout import is_saas_sync_enabled`) — to the new CORE location, so no CORE-set module imports `specify_cli.saas.rollout` or any other INTEGRATION module. (The CORE-set importer set is exactly `{readiness/coordinator.py}`; the plan re-verifies no other exists.) | Proposed |
| FR-003 | Retain `saas/rollout.py` as a thin re-export shim delegating to the CORE home (C-002), and preserve every re-export surface — `saas/__init__.py`, `sync/feature_flags.py`, `tracker/feature_flags.py`, the `sync/__init__.py` / `tracker/__init__.py` facades — plus the ~20 downstream importers, so every public import name a consumer relies on keeps resolving to the same objects. | Proposed |
| FR-004 | In `tests/architectural/test_integration_boundary.py`: (a) remove the single `ALLOWLIST` entry (→ empty); (b) tighten `test_allowlist_count_ratchet` from `len(ALLOWLIST) <= 1` to `len(ALLOWLIST) == 0` so the exemption set is permanently closed; (c) remove the now-stale positive-control assertion in `test_allowlist_cannot_be_bypassed` (the block at ~`:264-272` that hard-codes the coordinator→`saas.rollout` allowlisted crossing), retaining the negative-control injection proof that keeps the scanner honest. | Proposed |
| FR-005 | Update ADR `docs/adr/3.x/2026-06-26-1-core-integration-boundary.md` (Allowlist Exemptions table ~`:183` + Confirmation item 3 ~`:254`) to record the exemption resolved by this mission. | Proposed |
| FR-006 | Update the stability contract `kitty-specs/082-stealth-gated-saas-sync-hardening/contracts/saas_rollout.md` (the `**Module**:` location line ~`:3`, the "made once in `saas/rollout.py`" semantics ~`:49`, and the Backwards-Compatibility-Shims section) to name the new CORE canonical home + the retained `rollout.py` shim; keep the file parse-valid for the round-trip test `tests/contract/test_example_round_trip.py:140`, and bump the contract version. The plan decides edit-in-place vs. a superseding note given the archived-mission-folder immutability norm. | Proposed |

### Non-Functional Requirements

| ID | Requirement | Measurable threshold | Status |
|----|-------------|----------------------|--------|
| NFR-001 | No behavior change to the flag semantics; the retained shim preserves object identity. | The existing rollout / feature-flag / consumer tests pass **unchanged** (no assertion edits) — including `tests/saas/test_rollout.py`'s shim-identity assertions (`is` the same object); `saas_sync_disabled_message()` is byte-identical. | Proposed |
| NFR-002 | Single canonical *definition*. | Exactly **one** `def is_saas_sync_enabled` and **one** `def saas_sync_disabled_message` exist repo-wide (grep the `def`s); every re-export surface (`saas/rollout.py`, `saas/__init__.py`, `sync`/`tracker` `feature_flags`) resolves to them without redefining. | Proposed |
| NFR-003 | Quality gates on changed files. | `ruff` clean and `mypy --strict` clean on all changed files; the targeted test surface (Testing note) green with **0** new failures. | Proposed |
| NFR-004 | Boundary enforced at zero exemptions with the scanner still having teeth. | `pytest tests/architectural/test_integration_boundary.py` passes with `len(ALLOWLIST) == 0`; `test_no_core_imports_integration` reports zero violations; the **negative-control** injection proof (a non-allowlisted CORE→INTEGRATION import is still reported) passes, proving the scanner did not go vacuous. | Proposed |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The relocation target MUST be a module the boundary guard classifies as CORE-set (under `core/`, `status/`, `readiness/`, or `invocation/`) — verified against `CORE_PACKAGES` in `test_integration_boundary.py`. The new CORE module must import only stdlib (`os`) so it introduces no dependency cycle. | Active |
| C-002 | **Resolved: `saas/rollout.py` is retained as a thin re-export shim, not deleted.** Deleting it is foreclosed by NFR-001 (`tests/saas/test_rollout.py:16` hard-imports from `specify_cli.saas.rollout` and asserts shim object-identity — deletion would force test edits). Exactly one *definition* exists (single canonical authority); the shim delegates. | Active |
| C-003 | Preserve the `saas_rollout.md` stability contract's byte-frozen disabled-message wording; the contract's module-location reference is updated under FR-006 with a version bump. | Active |
| C-004 | ATDD red-first: removing the `ALLOWLIST` entry is the failing-first pin — with the entry gone but the coordinator still importing INTEGRATION, `test_no_core_imports_integration` is RED (verified); the relocation + repoint turns it GREEN. | Active |
| C-005 | Terminology canon (Mission, not feature); introduce no new legacy terminology. Campsite fix: `readiness/upgrade_ux.py:77`'s docstring "Stable truthy parser shared with `saas.rollout`" is corrected to the new home (domain-matched, in scope). | Active |

## Success Criteria

- **SC-1**: `pytest tests/architectural/test_integration_boundary.py` passes with an empty `ALLOWLIST`; the count-ratchet is tightened to `len(ALLOWLIST) == 0`; no CORE→INTEGRATION import edge remains.
- **SC-2**: The `SPEC_KITTY_ENABLE_SAAS_SYNC` flag behaves identically — all existing rollout / feature-flag / consumer tests (incl. `tests/saas/test_rollout.py` identity assertions) pass unchanged, and the disabled message is byte-identical.
- **SC-3**: Exactly one `def is_saas_sync_enabled` / `def saas_sync_disabled_message` exists repo-wide (in the CORE home); all re-export surfaces delegate.
- **SC-4**: The ADR (FR-005) and the stability contract (FR-006) both record the exemption resolved / the new canonical home.

## Assumptions

- The exact CORE target module name (e.g. `src/specify_cli/core/saas_sync_config.py`) is a plan-phase naming decision honoring C-001.
- The flag reader is genuinely pure (env read only), as the #2172 allowlist rationale asserts — re-verified at implementation.

## Out of Scope

- Any change to the SaaS-sync behavior, the truthy value set, the env var name, or the disabled-message wording.
- Relocating any other `saas/`/`sync/`/`tracker/` logic beyond the pure flag reader; the unrelated truthy parsers in `compat/config.py` and `readiness/upgrade_ux.py` are untouched (beyond the C-005 docstring fix).
- Changes to the boundary guard's scanner logic or the CORE/INTEGRATION set definitions. (The `ALLOWLIST` emptying, the count-ratchet tightening, and the positive-control removal in FR-004 are the only edits to that test file.)
