---
work_package_id: WP01
title: Burn down the stale ratchet allowlists
dependencies: []
requirement_refs:
- FR-003
- FR-004
- FR-005
tracker_refs:
- '2049'
planning_base_branch: feat/shrink-ratchet-allowlists
merge_target_branch: feat/shrink-ratchet-allowlists
branch_strategy: Planning artifacts for this mission were generated on feat/shrink-ratchet-allowlists. The PR (#2159) was refreshed by recreating it on current origin/main; completed changes merge back into feat/shrink-ratchet-allowlists unless the human explicitly redirects the landing branch.
created_at: '2026-06-26T00:00:00+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
agent: claude
shell_pid: "452836"
history:
- date: '2026-06-26'
  action: created
  actor: claude
- date: '2026-06-29'
  action: refreshed onto current origin/main; FR-001/FR-002/FR-006 overtaken by harden-dead-symbol-gate
  actor: claude
agent_profile: randy-reducer
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/compat/_adapters/version_checker.py
- src/specify_cli/compat/_adapters/gate.py
- src/specify_cli/compat/_adapters/detector.py
- src/specify_cli/compat/_adapters/__init__.py
- src/specify_cli/core/version_checker.py
- tests/architectural/_baselines.yaml
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/test_no_dead_modules.py
- tests/architectural/test_compat_shims.py
- tests/contract/test_example_round_trip.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via the `/ad-hoc-profile-load` skill (profile: **randy-reducer**, role: implementer). Adopt its boundaries, governance scope, and initialization declaration for this work package. Then return here. This is a behavior-preserving *burn-down* — remove the stale allowlist surface, keep behavior identical, prove it with the gates.

## ⚠️ Refresh reconciliation (2026-06-29) — what main already overtook

This PR (#2159) was 97 commits behind `main` and was refreshed by recreating it on current `origin/main`.
Main's **`harden-dead-symbol-gate` mission has since LANDED** and OVERTOOK roughly half of the original
plan:

- **FR-001 OVERTAKEN** — main's new caller-detectors rescued `write_pipeline::promote`; `StagedArtifact`
  remains legitimately allowlisted on main. Do **NOT** touch `category_a` entries.
- **FR-002 OVERTAKEN** — `charter.activate::charter_activate_app` / `…deactivate::charter_deactivate_app`
  no longer exist in `src/` on main. Nothing to remove.
- **FR-006 LANDED on main** — the `_extract_all_literal` parser fix is present on main. Do **NOT** touch
  the parser or `src/charter/synthesizer/write_pipeline.py`.

**Delivered scope = FR-003 + FR-004 + the FR-005 accuracy sync.** If the dead-symbol gate suddenly flags
many new dead symbols, STOP — you've touched the parser or `write_pipeline.py`; revert that.

## ⚠️ Before you start

1. **Confirm you are on the refreshed PR branch** (recreated on current `origin/main`). Re-read the live
   `_baselines.yaml` values before editing (they drift): `legacy_contract_allowlist` 152, `pure_shim_files`
   3, `category_5_wp_in_flight_adapters` 3, `category_a_slice_f_deferred` live 10 (recorded stale 12),
   `category_b_grandfathered_legacy` live 273 (recorded stale 286), `category_4_backcompat_shims` 8.
2. **DIR-003**: best-effort `unset GITHUB_TOKEN && gh issue edit 2049 --repo Priivacy-ai/spec-kitty --add-assignee MOES-Media` (known to fail upstream — note + continue).
3. **Run all `spec-kitty`/`pytest`/`ruff`/`mypy` via `uv run …`** (installed `spec-kitty` lags local `main`).

## Objective

Remove the still-stale allowlist surfaces that main's `harden-dead-symbol-gate` did not already clear —
retire the dead `compat/_adapters/` package and the dangling contract entry, demote the orphaned
`MismatchType`, and sync the two unenforced informational baselines to their true live size. Leave
`tests/architectural/` and `tests/contract/` green at the reduced baselines, with **no runtime behavior
change**, **no net allowlist growth**, and the parser / `write_pipeline.py` / `category_a` entries /
`category_4` untouched.

Requirements basis: `docs/engineering_notes/2049-ratchet-burndown-audit.md` (squad-verified) + this
mission's `research.md`, re-reconciled against current `origin/main` (line numbers drift — locate by
symbol name).

## Constraints

- **C-001**: every **enforced** `_baselines.yaml` decrement MUST equal the live frozenset/file-list size after the edit. Re-count. (`legacy_contract_allowlist`, `pure_shim_files`, `category_5_wp_in_flight_adapters`.)
- **C-002**: every `_baselines.yaml` edit MUST carry a `# justification:` comment naming #2049.
- **C-003**: the `compat/_adapters/` package deletion + its allowlist removals land together (gate green at each commit).
- **C-005**: do NOT touch `category_4_backcompat_shims` (reads `8`; leave it).

## Subtasks

### T001 — FR-003: shrink `legacy_contract_allowlist` to 151

**Steps**:
1. Confirm absent: `test ! -d kitty-specs/033-github-observability-event-metadata`.
2. In `tests/contract/test_example_round_trip.py`, remove the entry
   `kitty-specs/033-github-observability-event-metadata/contracts/event-envelope.md` from
   `_LEGACY_CONTRACT_ALLOWLIST` (note: this allowlist is in `tests/contract/`, NOT architectural).
3. Set `_baselines.yaml` `legacy_contract_allowlist: 151` with a `# justification:` comment. Confirm live == 151 (enforced).

**Validation**: dangling entry gone; live == 151.

### T002 — FR-004: retire the `compat/_adapters/` package

**Steps**:
1. **Verify**: `grep -rn "compat._adapters" src/ | grep import` — confirm no functional `from specify_cli.compat._adapters.* import` in `src/`.
2. `git rm src/specify_cli/compat/_adapters/{version_checker,gate,detector}.py` AND the now-empty package `git rm src/specify_cli/compat/_adapters/__init__.py` (the whole package is removed — an abandoned WP05/WP07 migration seam; the real cutover landed via `migration.gate` delegating directly to `compat.planner`).
3. Remove their entries from **all three** test surfaces (C-003): empty `_CATEGORY_5_WP_IN_FLIGHT_ADAPTERS` (`test_no_dead_modules.py`); `_ADAPTER_FILES` (`test_compat_shims.py`) is glob-discovered so self-empties on the deletion; remove the 9 `specify_cli.compat._adapters.*::*` symbol entries from `_CATEGORY_B_GRANDFATHERED_LEGACY` (`test_no_dead_symbols.py`).
4. Set `_baselines.yaml` `pure_shim_files: 0` AND `category_5_wp_in_flight_adapters: 0` (both pin the same package), each with a `# justification:` comment.

**Validation**: package deleted; `grep -rn "compat._adapters" src/` empty; both enforced baselines 0; live sizes match.

### T003 — FR-004 (orphan): demote `MismatchType` — NOT grandfather

**Steps**:
1. The adapter deletion orphans `specify_cli.core.version_checker::MismatchType` (a `Literal` type alias whose only cross-file importer was the deleted `compat/_adapters/version_checker.py` shim).
2. **Demote** it: remove `MismatchType` from `src/specify_cli/core/version_checker.py`'s `__all__`. Leave the alias defined (it stays as an internal annotation on `compare_versions` / `format_version_error`). Add a comment explaining the demotion.
3. Do **NOT** grandfather `MismatchType` into any allowlist. The dead-symbol gate scans only `__all__` names, so demotion closes the orphan at the root with zero new allowlist debt and no follow-up ticket owed.

**Validation**: `MismatchType` defined but absent from `__all__`; no new dead-symbol allowlist entry; gate green. This is why `category_b` lands at 264 (273 − 9), not 265.

### T004 — FR-005: accuracy-sync the two UNENFORCED informational baselines

**Steps**:
1. The `test_no_dead_symbols:` section of `_baselines.yaml` (`category_a_*`, `category_b_*`) is **not** cross-checked by `test_ratchet_baselines.py` (it enforces only `test_no_dead_modules` / `test_compat_shims` / `test_example_round_trip` and 3 others). Its values went stale because `harden-dead-symbol-gate` landed without re-recording them.
2. Set `category_a_slice_f_deferred: 10` (the true live frozenset size; main rescued `write_pipeline::promote` and one more — this PR removes no `category_a` entry) with a `# justification:` comment.
3. Set `category_b_grandfathered_legacy: 264` (273 live on main − the 9 dead adapter symbols removed in T002; **no +1** because `MismatchType` was demoted, not added) with a `# justification:` comment. Confirm live == 264.

**Validation**: informational baselines record the true live size (10 and 264).

### T005 — FR-005: record the corrections

**Steps**:
1. Record (in the artifacts / PR body / a comment on #2049) that `legacy_contract_allowlist` lives in `tests/contract/` (not `tests/architectural/`) and that the `_extract_all_literal` parser fix (FR-006) landed on main via `harden-dead-symbol-gate` (originally split to #2158).

**Validation**: the corrections are captured in the artifacts or PR body.

### T006 — Verify everything green + net SHRINK

**Steps**:
1. `PWHEADLESS=1 uv run pytest tests/architectural/test_ratchet_baselines.py tests/architectural/test_no_dead_modules.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_compat_shims.py tests/contract/test_example_round_trip.py -q`
2. `PWHEADLESS=1 uv run pytest tests/architectural/ tests/contract/ -q`
3. Diff-scoped lint: `git diff --name-only --diff-filter=AMR HEAD | rg '\.py$'` then `uv run ruff check <those files>` (exit 0).
4. `uv run mypy` on any changed `.py` (best-effort; ignore pre-existing errors unchanged by the diff).
5. Confirm the enforced baselines (`legacy_contract_allowlist: 151`, `pure_shim_files: 0`, `category_5_wp_in_flight_adapters: 0`) match their live size; the informational baselines record the true live size (`category_a_slice_f_deferred: 10`, `category_b_grandfathered_legacy: 264`); `category_4` unchanged at 8; **`git diff` of `test_no_dead_symbols.py` is a NET REMOVAL** (the 9 adapter symbols deleted, nothing mass-added — if it grew, the parser was touched: revert).

**Validation**:
- [ ] Gates pass; every enforced baseline == its live size; informational baselines record the live size; `category_4` untouched at 8.
- [ ] `test_no_dead_symbols.py` diff is a net shrink (no mass additions).
- [ ] `ruff`/`mypy` clean on the diff. (Ignore local-env `python -m ruff` tid251 failures + the order-flaky `test_pytest_marker_convention` — env artifacts, verify on CI; any pre-existing `test_example_round_trip MISSING_FRONTMATTER` failures for OTHER missions' contracts are unrelated.)

## Branch Strategy

- **Planning base branch**: `feat/shrink-ratchet-allowlists`.
- **Final merge target**: `feat/shrink-ratchet-allowlists`, which merges to `main` via a cross-fork PR (#2159; push to `fork`, `gh pr create --repo Priivacy-ai/spec-kitty --head MOES-Media:feat/shrink-ratchet-allowlists`). Do not push to `origin/main`.
- Execution worktrees are allocated per computed lane from `lanes.json`.

## Definition of Done

- `_baselines.yaml`: enforced — `legacy_contract_allowlist: 151`, `pure_shim_files: 0`, `category_5_wp_in_flight_adapters: 0`; informational — `category_a_slice_f_deferred: 10`, `category_b_grandfathered_legacy: 264`; `category_4_backcompat_shims` unchanged at 8; each edit has a `# justification:` and (for the enforced keys) matches its live size.
- `compat/_adapters/` package deleted (3 shims + empty `__init__.py`); no functional importers remain; `MismatchType` demoted out of `core/version_checker.__all__` (NOT grandfathered).
- Dangling `legacy_contract` entry removed; #2049 / PR body records the corrections + that the parser fix landed on main.
- `pytest tests/architectural/ tests/contract/`, `ruff`, `mypy` all green; `test_no_dead_symbols.py` diff is a net shrink.
- Parser / `write_pipeline.py` / `category_a` entries / `category_4` NOT touched.

## Risks & Reviewer Guidance

- **Scope guardrail (the key check)**: Reviewer — confirm `_extract_all_literal`, `src/charter/synthesizer/write_pipeline.py`, and the `category_a`/`category_b` `charter_*_app` entries are NOT in the diff (FR-001/FR-002/FR-006 are OVERTAKEN by main), and that `test_no_dead_symbols.py` shows a NET REMOVAL.
- **MismatchType**: Reviewer — confirm it is **demoted** out of `version_checker.__all__`, NOT grandfathered into an allowlist (grandfathering would land `category_b` at 265, not 264, and owe a follow-up ticket).
- **C-001 off-by-one**: Reviewer — for each of the 3 enforced baselines, confirm declared == live size (`test_ratchet_baselines.py` is the oracle).
- **C-003 atomicity**: all 3 pure-shim surfaces moved together with the package deletion; no dead-module gate flags an un-allowlisted file.
- **C-005**: `category_4_backcompat_shims` NOT in the diff (stays at 8).
- **NFR-002**: the only `src/` edits are the `compat/_adapters/` package deletion and the `MismatchType` `__all__` demotion.
