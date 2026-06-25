# Tasks: Shrink Architectural Ratchet Allowlists

**Mission**: `shrink-ratchet-allowlists-01KW0EAZ`
**Planning base branch**: `feat/shrink-ratchet-allowlists`
**Final merge target**: `main` (via PR from the feature branch)
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

## Overview

A single atomic work package. Every FR edits `tests/architectural/_baselines.yaml`, and the dead-symbol
work (FR-001/FR-002/FR-006) plus the pure-shim work (FR-004) both edit
`tests/architectural/test_no_dead_symbols.py` — so they cannot be split into independent parallel lanes
(owned_files would overlap) and the gate must be green at the end. The non-obvious piece is the
**FR-001 ↔ FR-006 interaction** (research.md D-02): fixing the parser un-blinds the gate to
`write_pipeline.py`, so the slice-F removals are paired with trimming `write_pipeline.__all__` to its
live-caller symbol. `category_4` is explicitly untouched (C-005, owned by #2048/PR #2152).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | FR-006: fix `_extract_all_literal` early-return + add a focused unit test | WP01 | |
| T002 | FR-006 cascade: trim `write_pipeline.__all__` to live-caller symbols (verify first) | WP01 | |
| T003 | FR-001: remove 2 `category_a_slice_f_deferred` entries; baseline → 9 (+ drift fix) | WP01 | |
| T004 | FR-002: remove 2 `category_b_grandfathered_legacy` entries; baseline → 284 | WP01 | |
| T005 | FR-004: delete 3 `compat/_adapters/*` files + 4 paired allowlists; `pure_shim_files`/`category_5` → 0 | WP01 | |
| T006 | FR-003: remove dangling `legacy_contract_allowlist` entry; baseline → 151 | WP01 | |
| T007 | FR-005: post issue/doc corrections to #2049 + record in mission notes | WP01 | |
| T008 | Verify: full architectural + contract suites + `ruff` + `mypy` green | WP01 | |

## Work Packages

### WP01 — Burn down the stale ratchet allowlists

- **Goal**: Remove ~8 evidence-backed stale allowlist entries across four categories, fix the
  dead-symbol-gate parser bug (un-blinding `write_pipeline.py` and trimming its `__all__`), retire 3 dead
  adapter shim files, and correct the tracking-issue drift — leaving `tests/architectural/` and
  `tests/contract/` green at the reduced baselines, with no runtime behavior change and `category_4` untouched.
- **Priority**: P1 (the whole mission)
- **Dependencies**: none
- **Prompt**: [tasks/WP01-burn-down-ratchet-allowlists.md](./tasks/WP01-burn-down-ratchet-allowlists.md)
- **Estimated prompt size**: ~480 lines (8 subtasks)
- **Independent test**: `PWHEADLESS=1 uv run pytest tests/architectural/ tests/contract/ -q` green; `_baselines.yaml` shows `category_a_slice_f_deferred: 9`, `category_b_grandfathered_legacy: 284`, `legacy_contract_allowlist: 151`, `pure_shim_files: 0`, `category_5_wp_in_flight_adapters: 0`, `category_4_backcompat_shims` unchanged.

**Included subtasks**:

- [ ] T001 FR-006: in `tests/architectural/test_no_dead_symbols.py`, fix `_extract_all_literal` so a non-`__all__` top-level `AnnAssign` `continue`s instead of early-returning `frozenset()`; add a focused unit test for that case (WP01)
- [ ] T002 FR-006 cascade: in `src/charter/synthesizer/write_pipeline.py`, after verifying no star-import and re-grepping `from`-import callers, trim `__all__` to the live-caller set (`["stage_and_validate"]`), demoting `promote`/`compute_written_artifacts`/`StagedArtifact` (WP01)
- [ ] T003 FR-001: remove `write_pipeline::StagedArtifact` and `::promote` from `category_a_slice_f_deferred`; set `_baselines.yaml` `category_a_slice_f_deferred: 9` (confirm live size after edit) (WP01)
- [ ] T004 FR-002: remove `charter.activate::charter_activate_app` and `charter.deactivate::charter_deactivate_app` from `category_b_grandfathered_legacy`; set `_baselines.yaml` `category_b_grandfathered_legacy: 284` (WP01)
- [ ] T005 FR-004: delete `src/specify_cli/compat/_adapters/{version_checker,gate,detector}.py`; remove their entries from `_ADAPTER_FILES` (`test_compat_shims.py`), `category_5` (`test_no_dead_modules.py`), and the adapter dead-symbol allowlist (`test_no_dead_symbols.py`); set `_baselines.yaml` `pure_shim_files: 0` and `category_5_wp_in_flight_adapters: 0` (WP01)
- [ ] T006 FR-003: remove the dangling `kitty-specs/033-github-observability-event-metadata/contracts/event-envelope.md` entry from `legacy_contract_allowlist` in `tests/contract/test_example_round_trip.py`; set `_baselines.yaml` `legacy_contract_allowlist: 151` (WP01)
- [ ] T007 FR-005: post a comment on issue #2049 with the path/count corrections (`legacy_contract_allowlist` is in `tests/contract/`; `category_7`=7, `category_b`=286) and note them in the mission record (WP01)
- [ ] T008 Verify: `PWHEADLESS=1 uv run pytest tests/architectural/ tests/contract/ -q`, `uv run ruff check .` (diff-scoped), `uv run mypy src/charter/synthesizer/write_pipeline.py`; confirm all green and every baseline matches its live size (WP01)

**Implementation sketch**:
1. FR-006 parser fix + unit test (T001), then the `write_pipeline.__all__` trim (T002) — together, so the un-blinded gate sees only live symbols.
2. Remove the `category_a`/`category_b` entries + decrement (T003, T004).
3. Retire the 3 adapter files + their 4 paired allowlists + decrements (T005).
4. Remove the dangling contract entry + decrement (T006).
5. Post the #2049 corrections (T007).
6. Verify the full suites + gates (T008). Every `_baselines.yaml` edit carries a `# justification:` comment.

**Parallel opportunities**: none — single atomic unit (shared `_baselines.yaml` + `test_no_dead_symbols.py`).

**Risks**:
- **FR-006 cascade** (research.md D-02): un-blinding surfaces `compute_written_artifacts` as newly dead; resolved by the `__all__` trim, NOT a new allowlist entry. Verify no `from`-import caller + no star-import before demoting each symbol; if any has a real caller, keep it in `__all__`.
- **C-001 off-by-one**: each baseline must equal its live frozenset/file-list size after the edit (re-count, especially the `category_a` 12-vs-11 drift → target 9).
- **C-003 atomicity**: the 4 pure-shim surfaces (and the file deletions) must all land together or the dead-module/symbol gate flags an un-allowlisted dead module.
- **C-005**: do NOT touch `category_4_backcompat_shims` (owned by #2048/PR #2152).

## Requirement coverage

FR-001 … FR-006 all map to WP01. FR-005 (issue corrections) is a documentation action within the WP.
NFR-001…004 and C-001…005 are verified by T008 and the constraints baked into the WP prompt.
