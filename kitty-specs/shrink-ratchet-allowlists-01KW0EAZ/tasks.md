# Tasks: Shrink Architectural Ratchet Allowlists

**Mission**: `shrink-ratchet-allowlists-01KW0EAZ`
**Planning base branch**: `feat/shrink-ratchet-allowlists`
**Final merge target**: `main` (via PR from the feature branch)
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

## Overview

A single atomic work package: the clean allowlist burn-down. Every FR edits
`tests/architectural/_baselines.yaml`, and FR-001/FR-002/FR-004 all edit
`tests/architectural/test_no_dead_symbols.py` — so they cannot split into independent parallel lanes
(owned_files would overlap) and the gate must be green at the end.

**FR-006 (the `_extract_all_literal` parser fix) is DEFERRED to #2158** — un-blinding it surfaces ~117
pre-existing dead symbols across ~57 modules, which would *grow* the ratchet. This mission does **not**
touch the parser or `src/charter/synthesizer/write_pipeline.py`. `category_4` is also untouched (C-005,
owned by #2048/PR #2152).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | FR-001: remove 2 `category_a_slice_f_deferred` entries; baseline → 9 (+ drift fix) | WP01 | |
| T002 | FR-002: remove 2 `category_b_grandfathered_legacy` entries; baseline → 284 | WP01 | |
| T003 | FR-004: delete 3 `compat/_adapters/*` files + 4 paired allowlists; `pure_shim_files`/`category_5` → 0 | WP01 | |
| T004 | FR-003: remove dangling `legacy_contract_allowlist` entry; baseline → 151 | WP01 | |
| T005 | FR-005: post issue/doc corrections to #2049 (note parser fix → #2158) | WP01 | |
| T006 | Verify: full architectural + contract suites + `ruff` + `mypy` green; net allowlist SHRINK | WP01 | |

## Work Packages

### WP01 — Burn down the stale ratchet allowlists (clean shrink)

- **Goal**: Remove ~7 evidence-backed stale allowlist entries across four categories and retire 3 dead
  adapter shim files, leaving `tests/architectural/` and `tests/contract/` green at the reduced baselines
  with **no runtime behavior change**, **no net allowlist growth**, and the parser / `write_pipeline.py` /
  `category_4` untouched.
- **Priority**: P1 (the whole mission)
- **Dependencies**: none
- **Prompt**: [tasks/WP01-burn-down-ratchet-allowlists.md](./tasks/WP01-burn-down-ratchet-allowlists.md)
- **Estimated prompt size**: ~360 lines (6 subtasks)
- **Independent test**: `PWHEADLESS=1 uv run pytest tests/architectural/ tests/contract/ -q` green; `_baselines.yaml` shows `category_a_slice_f_deferred: 9`, `category_b_grandfathered_legacy: 284`, `legacy_contract_allowlist: 151`, `pure_shim_files: 0`, `category_5_wp_in_flight_adapters: 0`, `category_4_backcompat_shims` unchanged; `test_no_dead_symbols.py` net change is small (entries removed, not added).

**Included subtasks**:

- [ ] T001 FR-001: remove `write_pipeline::StagedArtifact` and `::promote` from `category_a_slice_f_deferred` (`test_no_dead_symbols.py`); set `_baselines.yaml` `category_a_slice_f_deferred: 9` (live was 11 → −2 = 9; confirm) (WP01)
- [ ] T002 FR-002: remove `charter.activate::charter_activate_app` and `charter.deactivate::charter_deactivate_app` from `category_b_grandfathered_legacy`; set `_baselines.yaml` `category_b_grandfathered_legacy: 284` (confirm live == 284; do NOT add any other entries) (WP01)
- [ ] T003 FR-004: delete `src/specify_cli/compat/_adapters/{version_checker,gate,detector}.py`; remove their entries from `_ADAPTER_FILES` (`test_compat_shims.py`), `category_5` (`test_no_dead_modules.py`), and the adapter dead-symbol entries (`test_no_dead_symbols.py`); set `_baselines.yaml` `pure_shim_files: 0` and `category_5_wp_in_flight_adapters: 0` (WP01)
- [ ] T004 FR-003: remove the dangling `kitty-specs/033-github-observability-event-metadata/contracts/event-envelope.md` entry from `legacy_contract_allowlist` in `tests/contract/test_example_round_trip.py`; set `_baselines.yaml` `legacy_contract_allowlist: 151` (WP01)
- [ ] T005 FR-005: post (or confirm already-posted) a comment on #2049 with the path/count corrections and note the parser fix moved to #2158 (WP01)
- [ ] T006 Verify: `PWHEADLESS=1 uv run pytest tests/architectural/ tests/contract/ -q`, `uv run ruff check` (diff-scoped), `uv run mypy`; confirm every baseline matches its live size, `category_4` untouched, and `test_no_dead_symbols.py` shows a net SHRINK (WP01)

**Implementation sketch**:
1. Reset the lane to base (discard the prior parser-fix attempt).
2. Remove the `category_a`/`category_b` entries + decrements (T001, T002).
3. Retire the 3 adapter files + their 4 paired allowlists + decrements (T003).
4. Remove the dangling contract entry + decrement (T004).
5. Confirm/post the #2049 corrections (T005).
6. Verify the full suites + gates and that the net change is a SHRINK (T006). Every `_baselines.yaml` edit carries a `# justification:` comment.

**Parallel opportunities**: none — single atomic unit.

**Risks**:
- **Do NOT touch the parser or `write_pipeline.py`** (FR-006 deferred to #2158). If the gate flags newly-visible dead symbols, STOP — that means the parser was inadvertently changed.
- **C-001 off-by-one**: each baseline must equal its live frozenset/file-list size after the edit.
- **C-003 atomicity**: the 4 pure-shim surfaces + file deletions land together.
- **C-005**: do NOT touch `category_4_backcompat_shims`.

## Requirement coverage

FR-001 … FR-005 all map to WP01. NFR-001…004 and C-001…005 are verified by T006 and the WP constraints.
