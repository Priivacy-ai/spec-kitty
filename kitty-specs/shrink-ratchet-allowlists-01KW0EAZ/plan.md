# Implementation Plan: Shrink Architectural Ratchet Allowlists

> **⚠️ Refresh reconciliation (2026-06-29) — READ FIRST:** PR #2159 was refreshed onto current
> `origin/main`, where the **`harden-dead-symbol-gate` mission has since LANDED** and OVERTOOK
> **FR-001** (`category_a` `StagedArtifact`/`promote`), **FR-002** (`category_b` `charter_*_app`), and
> **FR-006** (the `_extract_all_literal` parser fix — it landed on main here). **Delivered scope is now
> FR-003 + FR-004 + an accuracy sync (FR-005).** The adapter deletion orphaned
> `core.version_checker::MismatchType`, which was **DEMOTED out of `version_checker.__all__` — NOT
> grandfathered** (the gate scans only `__all__` names). Final baselines: enforced
> `legacy_contract_allowlist: 151`, `pure_shim_files: 0`, `category_5_wp_in_flight_adapters: 0`;
> informational `category_a_slice_f_deferred: 10`, `category_b_grandfathered_legacy: 264`
> (273 live on main − 9 dead adapter symbols, no +1); `category_4_backcompat_shims: 8` untouched.
>
> **Everything in the body below is the ORIGINAL pre-refresh plan and is OVERTAKEN / historical** —
> retained for traceability only. Any mention of the parser fix, the `write_pipeline.__all__` trim,
> `StagedArtifact`/`charter_*_app` removals, or `category_a → 9` / `category_b → 284`/`276`/`286`
> targets describes the superseded original plan, not the delivered PR. The current, authoritative
> account lives in [spec.md](./spec.md), [data-model.md](./data-model.md), and [research.md](./research.md).


**Branch**: `feat/shrink-ratchet-allowlists` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/shrink-ratchet-allowlists-01KW0EAZ/spec.md`

## Summary

Burn down the evidence-backed stale architectural-ratchet allowlist entries across four categories,
fix the `_extract_all_literal` dead-symbol-gate parser bug, and correct drift in issue #2049. The work
is mechanical test/ledger editing plus three dead-file deletions and one small `__all__` trim — no
runtime behavior change. The non-obvious part is the **FR-001 ↔ FR-006 interaction**: fixing the parser
un-blinds the dead-symbol gate to `write_pipeline.py`, so the slice-F removals must be paired with
trimming `write_pipeline.__all__` to its live-caller symbols (see research.md D-02).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest (architectural + contract gate suites), ruff, mypy — no new runtime deps
**Storage**: N/A
**Testing**: pytest; authoritative gates: `tests/architectural/test_ratchet_baselines.py`, `test_no_dead_modules.py`, `test_no_dead_symbols.py`, `test_compat_shims.py`, and `tests/contract/test_example_round_trip.py`
**Target Platform**: Linux/macOS dev + CI
**Project Type**: single (Python CLI package `specify_cli` + sibling `charter` package)
**Performance Goals**: N/A
**Constraints**: Each `_baselines.yaml` decrement MUST equal the live frozenset/file-list size (C-001) and carry a `# justification:` comment (C-002); deletions + allowlist removals land together (C-003); do NOT touch `category_4` (C-005, owned by #2048/PR #2152)
**Scale/Scope**: ~8 stale entries across 4 categories + 1 parser fix + 3 file deletions + 1 `__all__` trim; ~6–9 files changed

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present. Relevant gates:
- **Burn-down Policy (C-004) / SHRINK ratchet** — this mission *is* the burn-down; fully compliant and advances the policy. ✅
- **`__all__` Declaration Convention (C-007)** — FR-006's `write_pipeline.__all__` trim keeps a non-empty `__all__` (retains `stage_and_validate`); demoting uncalled symbols to internals is the convention's intended burn-down move, not a violation. ✅
- **ATDD-First (C-011)** — the existing architectural/contract suites are the acceptance oracle; the change is validated by the gates going green at the reduced baselines. ✅
- **DIR-003 (tracker assignment)** — assign #2049 to the HiC at implement start (note: prior mission showed `MOES-Media` can't be assigned upstream; best-effort). ✅
- **DIR-001/002 (identifier safety)** — N/A (no slug/identifier normalization touched).
- **Pre-existing Failure Reporting (DIR-004)** — local `python -m ruff` / order-flake failures are env artifacts, not repo failures (see prior mission); do not file spurious issues.

No violations. No Complexity Tracking entries required.

## Project Structure

### Documentation (this mission)
```
kitty-specs/shrink-ratchet-allowlists-01KW0EAZ/
├── plan.md · research.md · data-model.md · quickstart.md · spec.md
```

### Source Code (repository root)
```
src/
├── charter/synthesizer/write_pipeline.py        # FR-006: trim __all__ to live-caller symbols
└── specify_cli/compat/_adapters/
    ├── version_checker.py                        # FR-004: DELETE
    ├── gate.py                                   # FR-004: DELETE
    └── detector.py                               # FR-004: DELETE

tests/
├── architectural/
│   ├── _baselines.yaml                           # decrement category_a→9, category_b→284, pure_shim→0, category_5→0 (+justifications)
│   ├── test_no_dead_symbols.py                   # FR-001/002 entry removals; FR-006 parser fix; FR-004 adapter symbol entries
│   ├── test_no_dead_modules.py                   # FR-004 category_5 adapter module entries
│   └── test_compat_shims.py                      # FR-004 _ADAPTER_FILES entries
└── contract/
    └── test_example_round_trip.py                # FR-003 legacy_contract_allowlist dangling entry
```

**Structure Decision**: Single repo. Edits cluster on `test_no_dead_symbols.py` + `_baselines.yaml`
(shared by the dead-symbol and pure-shim work → must share a lane, D-03), plus the contract test and the
three deleted adapter files. `category_4` is explicitly untouched.

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs. IC-01 and IC-02 share
> `test_no_dead_symbols.py` + `_baselines.yaml`, so they cannot be independent parallel lanes (D-03).

### IC-01 — Dead-symbol burn-down + parser fix
- **Purpose**: Reduce the dead-symbol categories and un-blind the gate, coherently.
- **Relevant requirements**: FR-001, FR-002, FR-006, NFR-004, C-001, C-002
- **Affected surfaces**: `tests/architectural/test_no_dead_symbols.py` (remove `category_a` StagedArtifact/promote + `category_b` charter_*_app entries; fix `_extract_all_literal` ~line 938), `src/charter/synthesizer/write_pipeline.py` (trim `__all__` → `["stage_and_validate"]` after verifying callers, D-02), `tests/architectural/_baselines.yaml` (`category_a_slice_f_deferred: 9`, `category_b_grandfathered_legacy: 284`).
- **Sequencing/depends-on**: Apply the parser fix + `__all__` trim together with the `category_a` removal so the gate is green at the commit; re-confirm the latent 12-vs-11 `category_a` drift (target 9).
- **Risks**: FR-006 cascade — un-blinding surfaces `compute_written_artifacts` as newly dead; resolved by the `__all__` trim, not a new allowlist entry. Verify no star-import / no `from`-import caller before demoting (D-02).

### IC-02 — Pure-shim adapter retirement
- **Purpose**: Delete 3 dead adapter shims and drop their (paired) allowlists to 0.
- **Relevant requirements**: FR-004, NFR-002, NFR-004, C-001, C-002, C-003
- **Affected surfaces**: delete `src/specify_cli/compat/_adapters/{version_checker,gate,detector}.py`; remove entries from `test_compat_shims.py` (`_ADAPTER_FILES`), `test_no_dead_modules.py` (`category_5`), `test_no_dead_symbols.py` (adapter symbols); `_baselines.yaml` `pure_shim_files: 0` + `category_5_wp_in_flight_adapters: 0`.
- **Sequencing/depends-on**: All four surfaces land together (C-003). Re-confirm zero `from ... import specify_cli.compat._adapters.*` in `src/` first.
- **Risks**: Missing one of the four paired surfaces → red gate. `category_5` and `pure_shim_files` both pin the same files.

### IC-03 — Legacy-contract + issue corrections
- **Purpose**: Drop the dangling contract entry and record the FR-005 doc corrections.
- **Relevant requirements**: FR-003, FR-005, NFR-001, C-001, C-002
- **Affected surfaces**: `tests/contract/test_example_round_trip.py` (`legacy_contract_allowlist`), `_baselines.yaml` (`legacy_contract_allowlist: 151`), a comment on issue #2049 (FR-005 corrections).
- **Sequencing/depends-on**: Independent of IC-01/IC-02 except for the shared `_baselines.yaml` (resolve as ordered edits in one lane).
- **Risks**: Low — verify the `033-…/event-envelope.md` path is genuinely absent before removing.
