---
work_package_id: WP03
title: '#2759 seam core: consistency parity into the freshness read-path'
dependencies:
- WP02
requirement_refs:
- FR-001
- FR-002
- FR-003
- NFR-002
tracker_refs:
- '#2759'
planning_base_branch: feat/doctrine-activation-freshness
merge_target_branch: feat/doctrine-activation-freshness
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-activation-freshness. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-activation-freshness unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/charter_runtime/freshness/
create_intent:
- tests/specify_cli/charter_runtime/test_freshness_activation_visibility.py
execution_mode: code_change
owned_files:
- src/specify_cli/charter_runtime/freshness/computer.py
- src/charter/consistency_check.py
- tests/specify_cli/charter_runtime/test_freshness_activation_visibility.py
role: implementer
tags: []
shell_pid: "3408405"
shell_pid_created_at: "1784325092.27"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via `/ad-hoc-profile-load python-pedro` (implementer). Do not act on the persona name alone — load the YAML.

## Objective

**Close the seam (#2759).** `charter activate`/`deactivate` mutate `config.yaml`
(`activated_*`), which is not one of the four files the content-hash covers, so the derived
freshness signal stays "fresh" while references/graph drift. Make config-activation **visible**
by wiring the already-built `run_consistency_check` parity into the freshness **read-path**, so
a config↔references / config↔graph mismatch reports **stale by construction** (fail-closed,
FR-003).

**Q2 = read-path parity (option a).** This is chosen because it is **writer-agnostic**:
`run_consistency_check` reads `config.yaml` directly (`consistency_check.py:_load_raw_activation_lists:~197`),
so it also covers the `merge_defaults` (`pack_manager.py:~747`) writer that bypasses
`commit_plan` and is ADR-slated for `init`. A write-side marker was rejected (blind to that
bypass). **Reuse `run_consistency_check` — do not reimplement a parallel parity check (C-007).**

**Anchor convention**: line numbers are indicative — resolve by symbol name.

## Hard constraints

- **C-001 layer**: the parity read lives in `specify_cli` (which may import `charter`).
  `commit_plan` / `activation_engine.py` is **NOT** edited. You edit `consistency_check.py`
  (charter) only for the campsite pre-extraction (T010) — record that cross-layer edit
  rationale in the WP note (R-06): the extraction de-risks the complexity-12 function you are
  about to make a read-path dependency.
- **NFR-002 preserve (#2732)**: the parity is a SEPARATE signal **composed with**
  content-identity, never a change to the hash. The per-file BOM/CRLF recipe, write-side
  stamps, `built_in_only` normalization, and the **fresh-seed early-exit**
  (`computer.py:~367-408`) all stay intact. An unchanged bundle still hashes identically.
- **Fresh-seed**: a never-synthesized project must still short-circuit to fresh — the parity
  read must NOT force it stale spuriously.
- Depends on **WP02** (references.yaml presence is a precondition for the parity read;
  fail-closed guarantees it).

## Subtasks

### T009 — Red-first (SC-002)
- Add `tests/specify_cli/charter_runtime/test_freshness_activation_visibility.py`. On a fresh
  project whose bundle + DRG are fresh, `charter activate <kind> <id>`, then compute freshness
  via the pre-existing entry point (`_compute_synthesized_drg` / `compute_freshness`).
- Assert the DESIRED behavior: signal is `stale` (config↔derived mismatch). This is RED today
  (currently reports `fresh`).

### T010 — Campsite pre-extraction (before wiring)
- In `consistency_check.py`, pre-extract the sub-checks of `_check_reference_id_parity`
  (complexity 12) into small helpers so that adding a read-path consumer keeps it ≤15.
- In `computer.py`, extract the `built_in_only` branch and the hash-compare tail of
  `_compute_synthesized_drg` (7 returns today) into helpers so the function stays ≤15 / ≤6
  returns AFTER T011 adds the parity read.
- Pure refactor — behavior identical; run the existing suites green before proceeding.

### T011 — Wire parity into the read-path
- In `_compute_synthesized_drg`, after the content-identity comparison (and PRESERVING the
  fresh-seed early-exit), consult `run_consistency_check` (config↔references + config↔graph).
  On a parity mismatch, the synthesized-DRG signal resolves to `stale` with a reason that names
  the config↔derived drift (compose with, do not replace, the existing stale reasons).
- Keep the call writer-agnostic (it reads `config.yaml`); do not gate it on a specific writer.

### T012 — Tests
- SC-002 end-to-end: activate → stale → reconcile (`charter generate` + `synthesize`) → fresh.
- `deactivate` symmetric.
- **Edge: deactivate-to-empty** — deactivating the last artifact of a kind writes explicit `[]`
  (`activation_engine.py:~338` uses `.remove()`); `_has_explicit_activation` treats `[]` as
  non-None (`consistency_check.py:~237-239`) so parity fires. Lock "signal goes stale" — this
  guards against a future refactor to key-deletion silently reopening the hole via the
  `if not _has_explicit_activation: return coherent` early-exit.
- **Edge: cascade** — `charter activate … --cascade` (multi-key flip) reconciles/reports stale
  once, not per-artifact (read-path parity makes it structurally moot; one assertion locks it).
- **Writer-agnostic**: seed activation state via `merge_defaults` (not `commit_plan`) and assert
  the signal is equally visible (guards R-08).
- **NFR-002 preserve**: an unchanged bundle → unchanged `compute_bundle_content_hash`; a
  never-synthesized fresh-seed project stays in its **pass-state** (`built_in_only`, a passing
  short-circuit — assert the pass-state, NOT a literal `"fresh"` string) with no spurious stale.

### T013 — Gate
- `PWHEADLESS=1 uv run pytest tests/specify_cli/charter_runtime/ tests/charter/ -q` green.
- `ruff check` + `uv run mypy --strict` clean on both owned source files; complexity ≤15.
- Confirm `git diff` does NOT touch `activation_engine.py` / `commit_plan` (C-001).

## Branch Strategy

Planning base + merge target: `feat/doctrine-activation-freshness`. Worktree from `lanes.json`.
Depends on WP02.

## Definition of Done

- [ ] Red-first SC-002 test written, green after wiring.
- [ ] `run_consistency_check` reused (not reimplemented) and consulted from the read-path.
- [ ] Writer-agnostic (merge_defaults-seeded activation visible).
- [ ] Fresh-seed early-exit preserved; unchanged-bundle hash unchanged (NFR-002).
- [ ] `_compute_synthesized_drg` ≤15/≤6 returns; `_check_reference_id_parity` ≤15 after extraction.
- [ ] `commit_plan`/`activation_engine.py` untouched (C-001); cross-layer edit rationale recorded.
- [ ] ruff + mypy --strict clean.

## Risks

- **Spurious stale on fresh-seed** (R-01) → preserve the early-exit; explicit test.
- **Regressing #2732** (R-02) → parity is a separate composed signal, not a hash input; NFR-002 test.
- **Cross-layer edit of consistency_check.py** (R-06) → keep it a local refactor in the same WP that consumes it; record rationale.

## Reviewer guidance (reviewer-renata, opus)

Verify: parity is REUSED not reimplemented; the read-path change composes with (does not replace)
content-identity; fresh-seed still short-circuits; merge_defaults-seeded visibility proven;
`commit_plan` untouched; complexity within budget after extraction.

## Activity Log

- 2026-07-17T21:30:29Z – claude:sonnet:python-pedro:implementer – shell_pid=3372692 – Assigned agent via action command
- 2026-07-17T21:51:01Z – claude:sonnet:python-pedro:implementer – shell_pid=3372692 – Parity wired into read-path (reused, writer-agnostic); #2732 preserved; fresh-seed intact; commit_plan untouched; gates green
- 2026-07-17T21:51:34Z – claude:opus:reviewer-renata:reviewer – shell_pid=3408405 – Started review via action command
- 2026-07-17T21:56:06Z – user – shell_pid=3408405 – Review passed (reviewer-renata/opus): #2759 seam wired correctly. C-007 REUSE confirmed — _activation_parity_drift_reason calls charter.consistency_check.run_consistency_check, no parallel parity logic. NFR-002 preserved — parity is a separate signal consulted AFTER content-identity hash; compute_bundle_content_hash untouched (not in diff); unchanged-bundle-hash test pins it. R-01 fresh-seed preserved — built_in_only + missing-graph short-circuit BEFORE parity read; test asserts pass-state membership (built_in_only), not literal 'fresh'. Writer-agnostic proven via merge_defaults test. C-001 satisfied — only the 3 owned files changed; consistency_check.py forward/reverse split is a pure behavior-identical refactor (doctrine_root threaded, order preserved). Complexity <=15 (ruff C901 clean; _compute_synthesized_drg 3 returns). Live wiring confirmed — parity reached via compute_freshness->_compute_synthesized_drg->_synthesized_drg_graph_state; activate flips signal. 22 tests pass, ruff clean, mypy zero new errors (7 pre-existing redundant-cast only). Local _seed_project_graph in test is the correct scoping call (avoids widening shared fixture blast radius; production-shaped data).
