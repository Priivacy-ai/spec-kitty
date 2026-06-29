# Tasks: Shrink Architectural Ratchet Allowlists

**Mission**: `shrink-ratchet-allowlists-01KW0EAZ`
**Planning base branch**: `feat/shrink-ratchet-allowlists`
**Final merge target**: `main` (via PR #2159 from the refreshed feature branch)
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

## Overview

A single atomic work package: the clean allowlist burn-down, refreshed onto current `origin/main`.

> **Refresh reconciliation (2026-06-29):** PR #2159 was refreshed onto current `origin/main`, where
> `harden-dead-symbol-gate` had landed and OVERTOOK **FR-001** (`category_a` `StagedArtifact`/`promote`),
> **FR-002** (`category_b` `charter_*_app`), and **FR-006** (the `_extract_all_literal` parser fix —
> landed on main). This WP does **not** touch the parser, `write_pipeline.py`, or those `category_a`/
> `category_b` entries. **Delivered scope: FR-003 + FR-004 + an accuracy sync (FR-005).** `category_4`
> is untouched (C-005, owned by #2048/PR #2152) and stays at main's value **8**.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | FR-003: remove dangling `legacy_contract_allowlist` entry; enforced baseline 152→151 | WP01 | |
| T002 | FR-004: delete `compat/_adapters/` package + 3 paired allowlist surfaces; `pure_shim_files`/`category_5` 3→0; remove 9 dead adapter symbols from `category_b` | WP01 | |
| T003 | FR-004 (orphan): demote `MismatchType` out of `core/version_checker.__all__` — NOT grandfathered | WP01 | |
| T004 | FR-005: accuracy-sync the two UNENFORCED informational baselines — `category_a` 12→10, `category_b` 286→264 | WP01 | |
| T005 | FR-005: record corrections (legacy_contract lives in `tests/contract/`; parser fix landed on main via harden-dead-symbol-gate) | WP01 | |
| T006 | Verify: full architectural + contract suites + `ruff` + `mypy` green; net allowlist SHRINK | WP01 | |

## Work Packages

### WP01 — Burn down the stale ratchet allowlists (clean shrink, refreshed)

- **Goal**: Remove the still-stale allowlist surfaces that main's `harden-dead-symbol-gate` did not
  already clear — retire the dead `compat/_adapters/` package and the dangling contract entry — and
  sync the two unenforced informational baselines to their true live size, leaving `tests/architectural/`
  and `tests/contract/` green with **no runtime behavior change**, **no net allowlist growth**, and the
  parser / `write_pipeline.py` / `category_a` entries / `category_4` untouched.
- **Priority**: P1 (the whole mission)
- **Dependencies**: none
- **Prompt**: [tasks/WP01-burn-down-ratchet-allowlists.md](./tasks/WP01-burn-down-ratchet-allowlists.md)
- **Estimated prompt size**: ~360 lines (6 subtasks)
- **Independent test**: `PWHEADLESS=1 uv run pytest tests/architectural/ tests/contract/ -q` green; `_baselines.yaml` shows enforced `legacy_contract_allowlist: 151`, `pure_shim_files: 0`, `category_5_wp_in_flight_adapters: 0`, and informational `category_a_slice_f_deferred: 10`, `category_b_grandfathered_legacy: 264`, with `category_4_backcompat_shims` unchanged at 8.

**Included subtasks**:

- [x] T001 FR-003: remove the dangling `kitty-specs/033-github-observability-event-metadata/contracts/event-envelope.md` entry from `_LEGACY_CONTRACT_ALLOWLIST` in `tests/contract/test_example_round_trip.py`; set `_baselines.yaml` `legacy_contract_allowlist: 151` (WP01)
- [x] T002 FR-004: delete the whole `src/specify_cli/compat/_adapters/` package (`detector.py`, `gate.py`, `version_checker.py`, empty `__init__.py`); empty `_CATEGORY_5_WP_IN_FLIGHT_ADAPTERS` (`test_no_dead_modules.py`); `_ADAPTER_FILES` (`test_compat_shims.py`) self-empties via glob; remove the 9 `specify_cli.compat._adapters.*::*` symbols from `_CATEGORY_B_GRANDFATHERED_LEGACY` (`test_no_dead_symbols.py`); set `_baselines.yaml` `pure_shim_files: 0` and `category_5_wp_in_flight_adapters: 0` (WP01)
- [x] T003 FR-004 (orphan): demote `MismatchType` out of `src/specify_cli/core/version_checker.py`'s `__all__` — NOT grandfathered (the gate scans only `__all__` names, so demotion closes the orphan with zero new allowlist debt) (WP01)
- [x] T004 FR-005: accuracy-sync the two UNENFORCED informational baselines — set `_baselines.yaml` `category_a_slice_f_deferred: 10` (live size; PR removes no category_a entry) and `category_b_grandfathered_legacy: 264` (273 live on main − 9 dead adapter symbols; no +1) (WP01)
- [x] T005 FR-005: record the corrections — `legacy_contract_allowlist` lives in `tests/contract/`; the parser fix (FR-006) landed on main via harden-dead-symbol-gate (WP01)
- [x] T006 Verify: `PWHEADLESS=1 uv run pytest tests/architectural/ tests/contract/ -q`, `uv run ruff check` (diff-scoped), `uv run mypy`; confirm enforced baselines match their live size, informational baselines record the true live size, `category_4` untouched, and `test_no_dead_symbols.py` shows a net SHRINK (WP01)

**Implementation sketch**:
1. Remove the dangling contract entry + enforced decrement (T001).
2. Delete the `compat/_adapters/` package + its 3 paired allowlist surfaces + enforced decrements (T002).
3. Demote `MismatchType` out of `version_checker.__all__` to close the orphan at the root (T003).
4. Sync the two unenforced informational baselines to their live size (T004).
5. Record the FR-005 corrections (T005).
6. Verify the full suites + gates and that the net change is a SHRINK (T006). Every `_baselines.yaml` edit carries a `# justification:` comment.

**Parallel opportunities**: none — single atomic unit.

**Risks**:
- **Do NOT touch the parser, `write_pipeline.py`, or the `category_a`/`category_b` `charter_*_app` entries** (FR-001/FR-002/FR-006 OVERTAKEN by main). If the gate flags newly-visible dead symbols, STOP.
- **MismatchType**: demote out of `__all__`, do NOT grandfather (that would leave a `+1` to burn down later and land `category_b` at 265 instead of 264).
- **C-001 off-by-one**: each enforced baseline must equal its live frozenset/file-list size after the edit.
- **C-003 atomicity**: the 3 pure-shim surfaces + package deletion land together.
- **C-005**: do NOT touch `category_4_backcompat_shims` (stays at 8).

## Requirement coverage

FR-003, FR-004, FR-005 map to WP01 (delivered). FR-001/FR-002/FR-006 are OVERTAKEN by main and require no
action. NFR-001…004 and C-001…005 are verified by T006 and the WP constraints.
