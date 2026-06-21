---
work_package_id: WP04
title: Coord-empty Option B (loud primary fallback)
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-003
- NFR-001
- NFR-002
- NFR-003
tracker_refs:
- '1716'
- '2040'
planning_base_branch: feat/mission-surface-resolver-safety-net
merge_target_branch: feat/mission-surface-resolver-safety-net
branch_strategy: Planning artifacts for this mission were generated on feat/mission-surface-resolver-safety-net. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-surface-resolver-safety-net unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
- T021
phase: Phase 2 - Coord-empty convergence
agent: claude:opus:python-pedro:implementer
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/surface_resolver.py
create_intent:
- tests/coordination/test_surface_resolver_coord_empty_warning.py
execution_mode: code_change
mission_id: 01KVN754TY9CVJ8G10ERTMPVRH
owned_files:
- src/specify_cli/coordination/surface_resolver.py
- tests/coordination/test_surface_resolver_coord_empty_warning.py
- tests/coordination/test_surface_resolver_collapse.py
- tests/missions/test_surface_resolution_equivalence.py
- tests/unit/status/test_mission_status_aggregate.py
- tests/mission_runtime/test_status_read_path_error_contract.py
role: implementer
tags: []
wp_code: WP04
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This profile governs your implementation style, boundaries, and quality standards for this work package.

---

## 🧹 Campsite-Cleaning Directive (#1970) — ACTIVE

While inside `surface_resolver.py`, remediate adjacent issues in-slice (the docstring already claims "primary
fallback" while the code hard-fails — fix the now-stale prose; dead branches left after the deletion; type/
lint nits) bounded to this mission's goal. No "out of scope" hand-waving in the touched surface.

## Objective

Apply the operator-decided **Option B**: a materialized-but-empty coordination worktree **no longer
hard-fails** — it falls back to the primary checkout and proceeds, emitting a **loud, observable warning** so
an operator or orchestrating agent can intervene. This drains the coord-empty equivalence cells; the
aggregate inherits primary for coord-empty with **no aggregate code change** (alphonso Q1).

ADR `architecture/3.x/adr/2026-06-19-1-coord-empty-surface-fallback.md` is already amended to Option B.

## ⚠️ Squad-corrected scope (read first)

WP04 OWNS the tests its deletion breaks (no "flag, don't reach"). Gate goes **9/4 → 11/2** (the two
coord-empty cells drain). Adopt WP01's `coord_feature_dir`/`probe_coord_state` helpers. The lane mechanism is
cross-lane tip-merge, NOT "one lane" (see Branch Strategy).

## Context (verified)

- Today `_canonicalize_or_enrich_coord_empty` (`surface_resolver.py:554-585`, called at `:637`) raises
  `CoordinationWorktreeEmpty` (`:176-198`, `__all__:57`) for coord-empty; gated by `_is_coord_empty_condition`
  (`:527-551`); the raise site is `:735-743`. **Do NOT touch the `CoordinationBranchDeleted` raise (`:716-724`)**
  — coord-deleted stays hard-fail (#1848), WP05's job.
- The resolver emits **zero logging today** — the loud warning is **net-new infrastructure** (NFR-003).
- The 4 xfail cells: `coord-empty/{bare,slug-mid8}` (drain here) + `coord-deleted/{bare,slug-mid8}` (drain in
  WP05). The two `*/bare` cells **share one constant** `_XFAIL_BARE_AGGREGATE_COORD_AUTHORITY_OUT_OF_SCOPE`
  (`:442`,`:458`) → retire PER-ROW; do NOT delete the shared constant (WP05 deletes it last).
- Research: `research/collapse-boundary-analysis-alphonso.md` (Q1), `research/collapse-reduction-map-randy.md` (R4-A..D).

## Subtasks

### T015 — Coord-empty → primary fallback (stop raising; adopt WP01 helper)
- At `surface_resolver.py:735-743`, **return the primary dir** (`candidate_feature_dir_for_mission(...)`)
  instead of raising. Route the coord-state decision through WP01's `probe_coord_state` (adopt — do not add a
  copy). Preserve UNCHANGED: create→first-write window + no-coord → primary. Do NOT touch coord-deleted.

### T016 — Emit the LOUD warning (net-new, NFR-003) — TIGHTENED
- Emit a warning via the module `logging.Logger` at **exactly `logging.WARNING`** (not debug/print). Single
  named constant; message names the **stale-surface risk** AND **both** recovery commands: flatten (remove
  `coordination_branch`) AND `spec-kitty agent worktree repair --mission <slug>`. Reuse the ADR recovery text
  (build the message once; paula C-warning-dup).

### T017 — Delete the now-dead error + helpers (adopt WP01 helper at :637)
- Delete `CoordinationWorktreeEmpty` (+ `__all__:57`), `_is_coord_empty_condition` (`:527-551`),
  `_canonicalize_or_enrich_coord_empty` (`:554-585`). Replace the `:637` call with a direct
  `candidate_feature_dir_for_mission(repo_root, mission_slug)` (randy R4-C — both helpers have zero external
  referencers, grep-verify). Route the surviving compose sites through WP01's `coord_feature_dir`.

### T018 — Warning-fires test (load-bearing, NON-FAKEABLE)
- `tests/coordination/test_surface_resolver_coord_empty_warning.py` (new): on a coord-empty `tmp_path`
  mission, assert **(a)** `caplog.records` has a record at **exactly `logging.WARNING`** from the named module
  logger, **(b)** the message contains BOTH recovery tokens (`flatten`/`coordination_branch` AND
  `worktree repair`), **(c)** the resolver returns the **primary dir**. All three are conjunctive (a print or
  debug line must NOT pass). State the constant + logger name so the reviewer can grep.

### T019 — OWN + invert the stranded coord-empty tests (BLOCKER fixes B1/B2/B3/S3)
- `tests/coordination/test_surface_resolver_collapse.py` (`:31` imports `CoordinationWorktreeEmpty`; `:91`,
  `:137` assert the old raise) → **rewrite to assert the Option-B primary+warning contract** (fold/keep
  alongside the new warning test; do not leave a parallel duplicate).
- `tests/unit/status/test_mission_status_aggregate.py::test_fails_closed_when_coord_worktree_materialized_but_missing_mission_dir`
  (builds coord-empty, asserts `CoordAuthorityUnavailable`) → **invert to "resolves primary + warning"**
  (coord-empty breaks at THIS boundary, not WP05's).
- `tests/mission_runtime/test_status_read_path_error_contract.py:90/98` (the "materialized but empty"
  assertion via `mission_runtime`) → **verify-first** then invert/adjust to the new primary-resolve path.
- **OUT-OF-MAP (WP05-owned, but break at THIS coord-empty boundary — invert here, linearized):**
  `tests/status/test_aggregate_surface_resolution.py::test_coord_empty_is_a_separate_hard_fail_cell` (`:216`)
  and `tests/specify_cli/missions/test_handle_equivalence_matrix.py::test_fail_closed_window_yields_coord_authority_unavailable_for_all_handles`
  (`:588`) both build the coord-empty shape and assert `CoordAuthorityUnavailable` → invert the **coord-empty
  parts** to primary+warning (leave their coord-deleted parts for WP05). Record these as out-of-map edits.
- Campsite: remove the now-dangling `CoordinationWorktreeEmpty` allowlist entry +
  rationale in `tests/architectural/test_no_dead_symbols.py:484-489,495` — **out-of-map note for WP05** (it
  owns that file); if you cannot edit it here, list it explicitly in your handoff so WP05 removes it.

### T020 — Retire the coord-empty xfail cells PER-ROW (gate 9/4 → 11/2)
- In `tests/missions/test_surface_resolution_equivalence.py` (now WP04-owned), retire the xfail marker on the
  `coord-empty/bare` AND `coord-empty/slug-mid8` rows ONLY (per-row — the `*/bare` cells share a constant with
  coord-deleted; **do NOT delete the shared constant** `_XFAIL_BARE_AGGREGATE_COORD_AUTHORITY_OUT_OF_SCOPE`,
  WP05 deletes it last). Also delete the dead `_XFAIL_READPATH_MID8_OUT_OF_SCOPE` constant if unreferenced by
  `_MATRIX` (WP01 flagged it). **Do NOT weaken** the `type(a) is type(b)` + `error_code` assertion. Run the
  gate; confirm **11 passed / 2 xfailed**, no unexpected XPASS, create-window + no-coord still green.

### T021 — Campsite
- Fix the stale "primary fallback" docstring/header in `surface_resolver.py` (it already claims fallback while
  the code hard-failed) + any dead branch left by the deletion.

## Branch Strategy
Planning base / merge target: `feat/mission-surface-resolver-safety-net`. **WP04 is its own lane (lane-d),
`depends_on: lane-a` (WP01).** It is NOT one lane with WP01 — the allocator merges WP01's **committed,
approved** lane tip into this worktree **at allocation time**. So: allocate WP04 only **after WP01 is
committed + approved**; if you resume a stale WP04 worktree, `git merge` the WP01 lane branch first (the tip
is not re-merged idempotently for new WP01 commits). WP01's `coord_feature_dir`/`probe_coord_state` must be
present in your worktree before you adopt them.

## Definition of Done
- Coord-empty resolves primary on all three legs + loud warning (3-part non-fakeable test); the error + 2
  helpers deleted; the `:637` call routed to `candidate_feature_dir_for_mission`; WP01 helpers adopted.
- All 4 stranded tests (collapse, aggregate, mission_runtime contract, + the dangling allowlist) owned and
  inverted/handed-off; create-window + no-coord preserved (#1718).
- Equivalence gate **11 passed / 2 xfailed**, per-row retirement, shared constant NOT deleted, assertion un-weakened.
- `ruff` + `mypy` clean. Campsite (stale docstring) fixed. Handoff names the warning constant + the WP05 allowlist note.

## Risks & Reviewer Guidance
- Reviewer: the warning test must be the 3-part conjunction (WARNING level + both tokens + primary dir) — a
  debug/print line must fail it. Confirm create→first-write window did NOT regress to hard-fail (#1718).
  Confirm coord-deleted (`CoordinationBranchDeleted:716-724`) untouched. Confirm per-row xfail retirement (the
  shared bare constant survives for WP05). Confirm the inverted stranded tests assert primary+warning, not the
  old raise.

## Activity Log
- 2026-06-21T14:42:27Z – system – WP04 prompt generated via /spec-kitty.tasks
