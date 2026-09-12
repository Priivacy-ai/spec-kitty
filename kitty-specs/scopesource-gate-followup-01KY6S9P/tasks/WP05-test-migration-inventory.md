---
work_package_id: WP05
title: Test migration + coverage-parity inventory
dependencies:
- WP04
requirement_refs:
- FR-004
- NFR-003
- NFR-004
planning_base_branch: fix/scopesource-gate-followup
merge_target_branch: fix/scopesource-gate-followup
branch_strategy: Planning artifacts for this mission were generated on fix/scopesource-gate-followup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/scopesource-gate-followup unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
- T030
phase: Phase 5 - coverage-parity close-out
history:
- at: '2026-07-23T10:19:53Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/review/
create_intent:
- tests/review/test_gate_coverage_census_topology.py
execution_mode: code_change
model: ''
owned_files:
- tests/review/test_census_parity.py
- tests/review/test_pre_review_gate_engine.py
- tests/review/test_pre_review_gate_integration.py
- tests/architectural/test_pre_review_scope_singlesource.py
- tests/review/test_gate_coverage_census_topology.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '#2873'
---

# Work Package Prompt: WP05 – Test migration + coverage-parity inventory

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile in the frontmatter and behave per its guidance.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: Review Feedback

Check `review_ref` before starting; address all feedback.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in fenced code blocks.

---

## Objectives & Success Criteria

Discharge **FR-004 exhaustively** — the coverage-parity close-out after WP04's signature change turns the
census-oracle and verdict-diff tests red. **No live-path coverage may be lost**, and the mutation-bite
proof (which is NOT a duplicate) must be carried FORWARD, not retired.

Complete when:

- **Census-only tests retired** (FR-004a): `test_census_parity.py` and the 6 `_derive`-based tests in
  `test_pre_review_gate_engine.py` — they exercised only the deleted duplicate.
- **The 8 verdict-diff tests MIGRATED** (FR-004c): `test_pre_review_gate_engine.py:827,843,868,897,918,936,
  961,996` moved from `filter_groups=`/`composite_routing=` to `scope_source=` injection (the
  `_gate_coverage_source` helper at `:293` already exists). They MUST be migrated, not retired — they carry
  the unique NO_COVERAGE-warn / terminal-interruption / sentinel-None-baseline / NEW_FAILURES coverage.
- **The mutation-bite MIGRATED FORWARD** (M-mut): `tests/architectural/test_pre_review_scope_singlesource.py`'s
  live-CI-topology assertions (proving census derivation consults real `.github/workflows`, not
  `_gate_coverage` in isolation) reproduced against `GateCoverageScopeSource`'s private census helpers
  (`_resolve_excluded_catchall_groups`/`_glob_matches_file`/`_default_filter_groups`/
  `_default_composite_routing`) in a new `test_gate_coverage_census_topology.py`.
- **`test_pre_review_gate_integration.py` reconciled** (kept-seam path): it monkeypatches the KEPT seams
  (`_pre_review_gate_filter_groups`/`_pre_review_gate_composite_routing`, `:390-487`) and references
  `derive_test_scope` in its docstring — verify it still exercises the live path via the seams and repoint
  only the docstring / any dropped-param usage; do NOT retire live-path coverage.
- **Committed coverage-parity inventory** (FR-004d): `coverage-parity-inventory.md` maps every retired test
  → a named surviving test id OR an explicit "not carried forward because X" — reviewed at gate.

Requirements covered: **FR-004**; guards **NFR-003, NFR-004**. Carrier for IC-03.

## Context & Constraints

- **Design authorities**: [spec.md FR-004](../spec.md); [data-model.md §6](../data-model.md);
  [plan.md IC-03](../plan.md); [post-plan-squad.md M-inv / M-mut](../reviews/post-plan-squad.md).
- **The mutation-bite is NOT a duplicate** (M-mut): `test_pre_review_scope_singlesource.py` is the ONLY
  proof census derivation consults **live CI topology**; the surviving `scope_source.py` copy has no
  equivalent (`test_scope_source.py` only asserts return-type). Migrating it FORWARD onto
  `GateCoverageScopeSource`'s private census helpers is mandatory — retiring it silently drops the
  live-topology guarantee.
- **`tests/architectural/_gate_coverage.py` is the LIVE census-topology authority** — do NOT edit or
  retire it; the migrated mutation-bite consults it exactly as the original did.
- **Do NOT touch** `test_scope_source.py` (WP02 owns it — the predicate-migration + any oracle-repoint in
  that file are WP02's). This WP owns the OTHER affected test files.
- **#2825 baseline-red-gotcha**: `test_no_dead_symbols` / `test_golden_count_ban` are the SAME gate family
  this touches — confirm any red is pre-existing on `eb06ca176` BEFORE attributing it to this diff.
- **Quality bars (NFR-002)**: `ruff` + `mypy --strict` zero issues on new/changed test code; ≥90% coverage
  of any new helper.

## Branch Strategy

- **Strategy**: single mission branch (file-partitioned ownership)
- **Planning base branch**: `fix/scopesource-gate-followup`
- **Merge target branch**: `fix/scopesource-gate-followup`

## Subtasks & Detailed Guidance

### Subtask T026 – Retire census-only tests (FR-004a)

- **Files**: `tests/review/test_census_parity.py` (delete), `tests/review/test_pre_review_gate_engine.py`
  (remove the 6 `_derive`-based tests that exercise only the deleted duplicate).
- **Steps**: delete only tests that assert the DELETED `pre_review_gate.py` census duplicate. Record each
  in the inventory (T030) as "not carried forward because it exercised the deleted duplicate; live
  derivation is proven by `<GateCoverageScopeSource census test>`".

### Subtask T027 – Migrate the 8 verdict-diff tests (FR-004c)

- **File**: `tests/review/test_pre_review_gate_engine.py:827,843,868,897,918,936,961,996`.
- **Steps**: replace `filter_groups=`/`composite_routing=` arguments (dropped by WP04) with `scope_source=`
  injection using the existing `_gate_coverage_source` helper (`:293`). Preserve each assertion's unique
  verdict-diff intent (NO_COVERAGE warn, terminal-interruption, sentinel/None-baseline degradation,
  NEW_FAILURES). Migration-red ≠ regression-red — note in the Activity Log they moved because the signature
  changed, not because behavior did.

### Subtask T028 – Migrate FORWARD the mutation-bite (M-mut)

- **File (create)**: `tests/review/test_gate_coverage_census_topology.py` (owned, `create_intent`).
- **Steps**: reproduce `test_pre_review_scope_singlesource.py`'s mutation-bite assertions — that the census
  derivation consults the REAL `.github/workflows` topology (not `_gate_coverage` in isolation) — against
  `GateCoverageScopeSource`'s private census helpers. Keep the original `tests/architectural/
  test_pre_review_scope_singlesource.py` (owned) as the migration source; either repoint it forward
  in-place or retire it once the new file subsumes it — record the decision in the inventory. `[P]`.

### Subtask T029 – Reconcile `test_pre_review_gate_integration.py`

- **File**: `tests/review/test_pre_review_gate_integration.py`.
- **Steps**: it monkeypatches the KEPT seams (`:390-487`) — verify it still drives the live path and does
  NOT pass the dropped params to `evaluate_pre_review_gate`. Repoint the docstring references to
  `derive_test_scope` (`:7-12`); if any call uses a dropped param, migrate to `scope_source=`. Preserve its
  live-path coverage. `[P]`.

### Subtask T030 – Committed coverage-parity inventory (FR-004d)

- **File (create)**: `kitty-specs/scopesource-gate-followup-01KY6S9P/coverage-parity-inventory.md`
  (mission-dir planning artifact — created by this WP but NOT in `owned_files`, since ownership tracking
  excludes `kitty-specs/` paths).
- **Steps**: a table — every retired/migrated test → a named surviving test id OR an explicit "not carried
  forward because X". Columns: `former test`, `disposition (retired/migrated/migrated-forward)`, `surviving
  id or rationale`. This is the gate-reviewed artifact M-inv requires — prose alone is insufficient.

## Test Strategy

- **Run**:
  ```bash
  PYTHONPATH=$(pwd)/src PWHEADLESS=1 pytest tests/review/test_pre_review_gate_engine.py \
    tests/review/test_pre_review_gate_integration.py tests/review/test_gate_coverage_census_topology.py \
    tests/architectural/test_pre_review_scope_singlesource.py -q
  ```
- **Gate family** (confirm pre-existing reds first, #2825):
  ```bash
  PYTHONPATH=$(pwd)/src pytest tests/architectural/test_no_dead_symbols.py tests/architectural/test_golden_count_ban.py -q
  ```
- **Quality**: `ruff check` + `mypy --strict` on the changed test files.

## Risks & Mitigations

- **Losing verdict-diff coverage**: the 8 tests are MIGRATED, never retired — the inventory proves it.
- **Retiring the mutation-bite**: it is migrated FORWARD; the live-topology guarantee must survive.
- **Misattributing a gate-family red**: confirm pre-existing on `eb06ca176` first (#2825).

## Review Guidance

- The 8 verdict-diff tests are `scope_source=`-injected and green; no unique intent lost.
- The mutation-bite lives on against `GateCoverageScopeSource`'s census helpers; `_gate_coverage.py` intact.
- Integration test still drives the live path via the kept seams.
- Inventory maps EVERY retired test → surviving id or explicit rationale; gate family green (pre-existing
  reds confirmed).

## Activity Log

> **CRITICAL**: chronological order, append at the END.

- 2026-07-23T10:19:53Z – system – Prompt created.

### Updating Status

`spec-kitty agent tasks move-task WP05 --to <status>`.
