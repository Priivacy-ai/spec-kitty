# Implementation Plan: Centralize installed CLI runtime + remediation planning

**Branch**: `feat/installed-runtime-domain` | **Date**: 2026-06-26 | **Spec**: `kitty-specs/installed-runtime-domain-01KW0NR6/spec.md`
**Mission ID**: `01KW0NR6E9XCH0QAREQWQ5ZDPB`

## Summary

Introduce a unified `InstalledCliRuntime` domain type that collapses three
independent uv-receipt-parsing helper sets and five independent
remediation-command construction sites into a single canonical detection +
planning pipeline. A dedicated SQLite history store (separate from NagCache)
records every upgrade attempt for idempotency and retry-eligibility queries.
The migration follows a 7-step strangler plan (FR-016 through FR-022); the
`detect_install_method()` shim is preserved through step 6 and retired in
step 7 after all call sites are migrated.

## Technical Context

**Language/Version**: Python 3.11 (frozen dataclasses, `from __future__ import annotations`, tomllib stdlib)
**Primary Dependencies**: stdlib only — `sqlite3`, `tomllib`, `pathlib`, `dataclasses`, `hashlib`; `platformdirs` for cache-dir resolution (already a project dependency via NagCache)
**Storage**: SQLite sibling table — `~/.cache/spec-kitty/upgrade-history.db` (separate file from `upgrade-nag.json`; same platformdirs-resolved cache dir)
**Testing**: pytest; frozen-dataclass construction tests; snapshot parity tests (SC-003); never-raise probe tests (NFR-001); concurrent-write safety tests (NFR-006)
**Target Platform**: Linux + macOS + Windows (PowerShell-safe render branch preserved, C-005)
**Project Type**: Single Python package (`src/specify_cli/compat/`)
**Performance Goals**: History store O(n) scan on last 100 records (SC-004); `detect_runtime()` single receipt read (SC-001)
**Constraints**: No new pip dependencies; frozen dataclasses; CHK028 validation on render; NFR-007 no PII in events/history records; all new code zero ruff/mypy issues

## Charter Check

No `.kittify/charter/charter.md` file is present in this repository. Charter check is skipped; no conflicts to surface.

## Project Structure

### Documentation (this mission)

```
kitty-specs/installed-runtime-domain-01KW0NR6/
├── plan.md           ← this file
├── research.md       ← caller audit, shared-home assessment, design decisions
├── data-model.md     ← InstalledCliRuntime / RemediationCommand / SQLite schema
├── quickstart.md     ← developer quick-start
└── contracts/
    ├── remediation-command-render.md   ← RemediationCommand.render() contract
    └── history-store-query.md          ← UpgradeAttemptStore query contract
```

### Source Code (repository root)

```
src/specify_cli/compat/
├── _detect/
│   ├── install_method.py    (existing — shim `detect_install_method` lives here through step 6)
│   └── runtime.py           (NEW — InstalledCliRuntime, detect_runtime(), shim)
├── _adapters/
│   ├── __init__.py           (pre-staged, empty)
│   └── uv_receipt.py        (NEW — UvReceiptReader)
├── remediation.py            (NEW — RemediationIntent, RemediationCommand, plan_remediation())
├── history.py                (NEW — UpgradeAttemptRecord, UpgradeAttemptStore)
├── install_events.py         (NEW — VerificationConfidence, UvToolInstallationVerified)
├── upgrade_hint.py           (existing — build_upgrade_hint() reimplemented on plan_remediation())
└── __init__.py               (existing — public API surface updated in step 7)

tests/specify_cli/compat/
├── test_runtime.py           (NEW — WP01: types, WP02: detect_runtime())
├── test_uv_receipt_reader.py (NEW — WP02: UvReceiptReader)
├── test_remediation.py       (NEW — WP03: plan_remediation() snapshot parity)
├── test_history_store.py     (NEW — WP02: UpgradeAttemptStore, queries, concurrent-write)
├── test_install_events.py    (NEW — WP01/WP05: UvToolInstallationVerified construction)
└── test_review_migration.py  (NEW — WP04: review command output parity)
```

## Complexity Tracking

No charter violations. Standard compat-layer expansion with direct precedent in OfflineQueue (SQLite) and existing `_detect` + `_adapters` layering.

## Implementation Concern Map

### IC-01 — Domain types + history-store schema gate

- **Purpose**: Introduce all frozen-dataclass types and produce the history-store blast-radius assessment as a committed design artifact that gates WP02 implementation.
- **Relevant requirements**: FR-001, FR-004, FR-012, FR-013 (schema design only), C-008
- **Affected surfaces**: `compat/_detect/runtime.py` (new), `compat/remediation.py` (new, types only), `compat/history.py` (new, dataclass only), `compat/install_events.py` (new)
- **Sequencing/depends-on**: none
- **Risks**: CHK028 `_COMMAND_RE` must be replicated exactly; `UpgradeAttemptRecord` must carry no PII; `UvRequirement` field set must match uv receipt TOML schema.

### IC-02 — Receipt adapter, detect_runtime(), detect_install_method() shim, history store

- **Purpose**: Introduce `UvReceiptReader` in the pre-staged `compat/_adapters/uv_receipt.py`, `detect_runtime()` in `compat/_detect/runtime.py`, the backward-compatible shim, and the full history store implementation (gated on the blast-radius assessment from IC-01).
- **Relevant requirements**: FR-007, FR-002, FR-003, FR-013, FR-015, NFR-001, NFR-003, NFR-005, NFR-006
- **Affected surfaces**: `compat/_adapters/uv_receipt.py`, `compat/_detect/runtime.py`, `compat/history.py`
- **Sequencing/depends-on**: IC-01 (types + schema design committed before any implementation starts)
- **Risks**: fail-soft (NFR-003) and never-raise (NFR-001) contracts; concurrent-write safety for SQLite (NFR-006); `_has_uv_tool_receipt` in install_method.py must remain intact for backward-compat shim.

### IC-03 — plan_remediation() + build_upgrade_hint() on planner

- **Purpose**: Introduce the `plan_remediation()` pure function in `compat/remediation.py` and reimplement `build_upgrade_hint()` on top of it, preserving all public contracts verbatim.
- **Relevant requirements**: FR-009, FR-011, FR-006, FR-005, C-002, C-005, NFR-004
- **Affected surfaces**: `compat/remediation.py`, `compat/upgrade_hint.py`
- **Sequencing/depends-on**: IC-02 (planner needs `InstalledCliRuntime` fields from `detect_runtime()`)
- **Risks**: Snapshot parity (SC-003) for all install methods × intents × platforms; CHK028 must raise at render time not at construction time; PowerShell branch must survive.

### IC-04 — Migrate review/__init__.py

- **Purpose**: Delete the ~120 LOC of duplicate receipt-parsing helpers in `review/__init__.py` and replace their call sites with `UvReceiptReader` + `plan_remediation()`.
- **Relevant requirements**: FR-019, FR-008 (partial), SC-002
- **Affected surfaces**: `cli/commands/review/__init__.py`
- **Sequencing/depends-on**: IC-03 (needs both the adapter and the planner)
- **Risks**: Byte-for-byte parity of reinstall command output (acceptance scenario 3 of user story 4).

### IC-05 — Migrate upgrade_ux.py + event emission + history records

- **Purpose**: Delete duplicate helpers in `upgrade_ux.py`, update `_default_upgrade_runner` to consume `RemediationCommand.argv` + `.env`, emit `UvToolInstallationVerified` event (uv-tool only), and append `UpgradeAttemptRecord` to history store on completion.
- **Relevant requirements**: FR-020, FR-012, FR-014, FR-008 (final deletion), C-001
- **Affected surfaces**: `readiness/upgrade_ux.py`, `compat/history.py` (append path), `compat/install_events.py` (emit path)
- **Sequencing/depends-on**: IC-04
- **Risks**: `_default_upgrade_runner` side effects must not break when history store is unreachable (best-effort append); `UvToolInstallationVerified` emitted only for `UV_TOOL` installs.

### IC-06 — Fold hardcoded strings (optional, FR-021)

- **Purpose**: Route the two hardcoded `"pipx upgrade spec-kitty-cli"` strings in `version_checker.py` and `schema_version.py` through `plan_remediation()` so no install-method strings are hardcoded outside the planner.
- **Relevant requirements**: FR-021 (Low priority, explicitly optional)
- **Affected surfaces**: `core/version_checker.py`, `migration/schema_version.py`
- **Sequencing/depends-on**: IC-03
- **Risks**: Scope creep — this WP is independently shippable and may be deferred to a follow-up mission.

### IC-07 — Retire detect_install_method() shim

- **Purpose**: Remove `detect_install_method()` from all 7 call sites, update `compat/__init__.py` public API, and delete the shim.
- **Relevant requirements**: FR-022
- **Affected surfaces**: All 7 call sites (see research.md §Caller Audit FR-022); `compat/_detect/runtime.py` (shim deleted); `compat/__init__.py` (re-export updated)
- **Sequencing/depends-on**: IC-04, IC-05 (all migration steps complete before shim can be removed)
- **Risks**: Any remaining test or caller using the shim becomes a compilation error; verify with `grep -rn detect_install_method` before merge.

---

## Strangler Step → WP Mapping

| WP | FR Step | IC | Key Deliverables | Independently Shippable Gate |
|----|---------|-----|-----------------|------------------------------|
| WP01 | FR-016 + C-008 | IC-01 | `InstalledCliRuntime`, `RemediationCommand`, `UvToolInstallationVerified`, `UpgradeAttemptRecord` types; history-store schema design + blast-radius assessment committed | Full test suite green; types only, zero behavior change |
| WP02 | FR-017 + FR-013 + FR-015 | IC-02 | `UvReceiptReader`, `detect_runtime()`, `detect_install_method()` shim, `UpgradeAttemptStore` with full query interface | All 7 shim call sites still green; detect_runtime() never-raise coverage ≥95% |
| WP03 | FR-018 | IC-03 | `plan_remediation()`, `build_upgrade_hint()` on planner, snapshot tests | SC-003 snapshot parity for all install methods; CHK028 regression tests pass |
| WP04 | FR-019 | IC-04 | `review/__init__.py` duplicate helpers deleted, call sites migrated | Existing review tests pass; new parity snapshot tests committed |
| WP05 | FR-020 + FR-012 + FR-014 | IC-05 | `upgrade_ux.py` helpers deleted, event emission + history append in `_default_upgrade_runner` | `UvToolInstallationVerified` event unit tests pass; history store append tests pass |
| WP06 | FR-021 | IC-06 | Hardcoded pipx strings routed through `plan_remediation()` (optional) | version_checker + schema_version tests pass; no snapshot regressions |
| WP07 | FR-022 | IC-07 | `detect_install_method()` shim retired, all 7 call sites updated | grep for `detect_install_method` returns zero production hits; full suite green |

Each WP must pass the full test suite (including `tests/architectural/test_no_legacy_terminology.py`) before the next WP begins (NFR-008).

---

## Key Design Decisions

### D-01: History store file location
- **Chosen**: `~/.cache/spec-kitty/upgrade-history.db` via `platformdirs.user_cache_dir("spec-kitty")` — same cache-dir as NagCache, different file.
- **Rationale**: Consistent with NagCache pattern; no new directory introduced; `platformdirs` already a dependency.
- **Rejected**: `~/.spec-kitty/upgrade-history.db` — would co-locate with OfflineQueue's `~/.spec-kitty/` dir, mixing two different domains.

### D-02: Home-dir isolation for shared-home scenarios
- **Chosen**: OS-user-level isolation (same blast radius as NagCache). No additional scoping key in the history store. See research.md §Shared-Home Blast Radius Assessment.
- **Rationale**: Docker/SaaS tenants that share the same OS user also share NagCache and OfflineQueue legacy path; the history store does not make this worse. Proper Docker isolation uses separate OS users.
- **Rejected**: Per-executable hash scoping — would derive from `sys.executable` path (PII per NFR-007).

### D-03: Module placement for UvReceiptReader
- **Chosen**: `compat/_adapters/uv_receipt.py` (pre-staged directory per C-007).
- **Rationale**: Pre-staged empty `_adapters/__init__.py` already committed; consistent with the `_detect` sub-package convention.

### D-04: plan_remediation() module
- **Chosen**: `compat/remediation.py` — new top-level module under `compat/`.
- **Rationale**: Peer to `compat/upgrade_hint.py`; visible at the same import depth; no circular imports since it depends only on `_detect/runtime.py` types.

### D-05: No Protocol types introduced
- **Chosen**: Concrete implementations only, per C-003.
- **Rationale**: `UvReceiptReader` has one concrete implementation (no second impl exists at time of introduction); `UpgradeAttemptStore` has one implementation.
