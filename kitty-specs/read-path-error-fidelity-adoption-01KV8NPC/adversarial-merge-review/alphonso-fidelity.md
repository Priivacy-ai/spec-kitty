# Adversarial Merge Review — architect-alphonso

**Mission:** `read-path-error-fidelity-adoption-01KV8NPC`
**Branch:** `feat/read-path-error-fidelity` (all 9 WPs merged; base `889332b59`)
**Lens:** spec→code fidelity + cross-WP integration + factory-seam correctness
**Date:** 2026-06-16
**Verdict:** **PASS — releasable.** No BLOCKER, no SHOULD-FIX. 3 NITs (all already
documented in-mission). Factory seam sole-door confirmed; zero residual flatten /
second-authority; no FR drift; cross-WP integration clean.

---

## 1. Factory seam (D-6 / IC-01) — CONFIRMED sole construction door

- **Sole `ExecutionContext(` runtime site:** `src/mission_runtime/resolution.py:118`,
  inside `build_execution_context`. The only other `grep` hits are unrelated
  (`core/context_validation.py:41` StrEnum, `glossary/middleware.py:27` Protocol,
  `runtime_bridge.py:1660` `StepContractExecutionContext` — a different type). ✅
- **`resolve_action_context` delegates:** both exits route through the factory
  (`resolution.py:935` mission-level, `:950` WP-bearing). All `wp_fields`/`base_fields`
  are assembled *before* the single build call — no post-build mutation (the historical
  `:800-808` split-brain is resolved by building once). ✅
- **Package-private:** `build_execution_context` is **NOT** in `mission_runtime.__all__`
  (verified at runtime: `'build_execution_context' in mr.__all__ == False`). `__all__`
  exposes only `resolve_action_context` / `resolve_placement_only` / `CommitTarget` +
  fragment/error types — no mid8/identity-projection door. ✅ (C-001, ADR lean-API honored.)
- **Build-time invariant fires (C-IC01 / FR-009 / D-2):** runtime-verified — building with
  `target_branch != branch_ref.target_branch` raises
  `ActionContextError("CONTEXT_INVARIANT_VIOLATION")`; the composite is frozen
  (`FrozenInstanceError` on field assignment). The invariant is asserted against
  `branch_ref.target_branch`, never `branch_name` (lane branch legitimately differs) — D-2
  supersession correctly implemented. ✅
- **Primitive pattern honored by consumers (D-6 boundary):** IC-02b (`orchestrator_api`),
  IC-03 (`mission.py`), IC-04 (`decision.py`), IC-05 (`workflow.py`) all read the real
  `mission_id` from primary `meta.json` and pass it to `resolve_mid8(slug, mission_id=<real>)`
  (the `decision.py:421` / `context.py:73` shape). No consumer imports a projection callable
  (none exists) and none seeds empty identity to drive the status-read path. ✅

## 2. Cross-WP integration — CLEAN; no residual flatten / second authority

- **`next` family (#15/#14/#12, FR-001/002, WP02):** the `MISSION_NOT_FOUND` collapse is
  now *gated* by `_is_read_path_error` against `_READ_PATH_ERROR_CODES`
  (`runtime_bridge.py:245-256`). Read-path topology codes re-raise verbatim
  (`:3159-3160`); only a genuinely-missing mission (`FEATURE_CONTEXT_UNRESOLVED`) collapses
  (`:3163`). The decision-answer path (`:3303-3318`) re-raises **all** `ActionContextError`
  verbatim. The `next_cmd` emitter (`_emit_read_path_error`) surfaces `error_code`,
  `checked_paths`, and a read-path `next_step`/`remediation` (the #1911 restoration) in
  both JSON and console. ✅
- **M1 (`context/resolver.py:164`, WP02):** the flatten-to-"check the slug" is replaced by
  a typed pass-through carrying `[exc.code]` + the resolver message into `FeatureNotFoundError`. ✅
- **M2/M3 (`orchestrator_api/commands.py`, WP09):** a *single* shared seam
  `_resolve_mission_dir_or_fail` (`:334`) serves all 8 read endpoints — no 8 divergent
  patches. M2: `StatusReadPathNotFound` propagates with `error_code` + `coord_candidate` /
  `primary_candidate` (envelope shape preserved). M3: the empty-`mid8` seed that suppressed
  the coord-aware fail-closed guard is gone; identity is read from declared meta
  (`_read_primary_meta`), and a coord-declaring topology with unprovable identity **fails
  closed** (`:320-328`, the M5 caveat) rather than reading stale primary. ✅
- **No second authority anywhere:** the `decision` escape-walk-to-`kitty-specs/` is deleted
  (`_resolve_repo_root_and_slug` now validates only the *raw* token via `_SAFE_SLUG_RE` and
  trusts the single canonical resolver — `decision.py:60-118`); all 5 decision catch-sites
  route to `_handle_action_context_error` (structured, no flatten). The implement re-resolutions
  that could independently report "no workspace could be resolved" are eliminated
  (`workflow.py` `_ensure_workspace_materialized` re-stats the single resolved context). ✅
- **Two root authorities agree (FR-007, WP06):** `resolve_canonical_root` (`core/paths.py:287-299`)
  now distinguishes a worktree pointer (follow to main) from a submodule/separate-git-dir
  pointer (stop at the `.kittify` marker), mirroring `locate_project_root`. ✅

## 3. NFR-001 behavioral equivalence — no remaining input-class asymmetry

- The single factory + invariant + frozen composite make the resolver emit the same typed
  outcome regardless of input class. `is_committed` now ORs three legs (coord-ref, HEAD,
  primary-target-branch) with a diagnostics sink listing every surface checked
  (`_substantive.py`), closing the coord-only surface-blindness (#7). The submodule leg is
  unified at the root resolver. Behavioral tests over the three topologies are green
  (`test_resolve_canonical_root_submodule.py`, `test_decision_single_authority.py`,
  factory-invariant + read-path-error-contract suites — 28 tests pass in this review).
  No residual asymmetry found. ✅

## 4. Spec fidelity — FR-001..FR-012 all delivered as specified; no drift

| FR | Status | Evidence |
|----|--------|----------|
| FR-001 | ✅ | Gated collapse + M1/M2 typed pass-through; `_READ_PATH_ERROR_CODES` set |
| FR-002 | ✅ | `_emit_read_path_error` surfaces code + checked_paths + read-path remediation (#1911) |
| FR-003 | ✅ | Escape-walk deleted; single canonical resolver; `_SAFE_SLUG_RE` on raw token only |
| FR-004 | ✅ | `_sole_mission_slug_or_none` (returns None for 0 or >1 → structured error, no silent fallback); placed in `setup_plan`, not the shared helper |
| FR-005 | ✅ | Primary-target-branch leg added (3-leg OR) + diagnostics sink |
| FR-006 | ✅ (D-5 narrow) | Typed `CommitToBranchResult` (committed/unchanged/no_op_wrong_surface) + real hash |
| FR-007 | ✅ | `resolve_canonical_root` stops at submodule `.kittify` boundary; agrees with `locate_project_root` |
| FR-008 | ✅ | Single `resolve_workspace_for_wp` call; `_ensure_workspace_materialized` consumes it |
| FR-009 | ✅ | Single factory + build-invariant (reject-on-mismatch) + frozen (D-2 rule) |
| FR-010 | ✅ | Side-effecting `ensure_charter_bundle_fresh`/`generate_all` removed from read-only collector; old `# noqa: BLE001` handler removed |
| FR-011 | ✅ | Verification-by-deletion across IC-02/03/04/05 + orchestrator; single-authority |
| FR-012 | ✅ (D-3) | #1827 test-only regression + falsification guard; verified-already-fixed |

- **D-1 (#1716 deferred) honored:** no write-side topology pulled in; only the #1993
  `resolve_lanes_dir` minimal seam landed (`lanes/persistence.py:23`). ✅
- **Deferred items as documented:** M4 (`_find_first_for_review_wp` re-deriver) = conscious
  deferral, recorded in tasks.md T044 + in-code at `workflow.py`. Fragment retirement limited
  to `prompt_source` + dead `StatusSurfaceFragment surface=` per D-6. ✅
- **No new suppressions:** the full mission diff adds **zero** `# noqa` / `# type: ignore` /
  `# nosec` (grep over the `+` diff lines). `ruff` clean on all 12 touched files. (NFR-004.) ✅

## 5. Missed residual — none unaccounted-for

- **4th lanes-dir derivation (`context/resolver.py:207`, `require_lanes_json(feature_dir)`):**
  consciously left (not IC-05-owned). It already routes through the canonical
  `resolve_lanes_dir` *internally* (via `require_lanes_json` → `read_lanes_json` →
  `resolve_lanes_dir`), so it is **not** an ad-hoc join — only a display f-string at `:210`
  spells `feature_dir / 'lanes.json'`. Tracked in the WP05 review note ("resolver.py:203 not
  owned; untouched"). Correct call. ✅
- The remaining `feature_dir / lanes.json` literals (`mission.py` error strings,
  `resolver.py:210`) are operator-facing message text, not derivation paths. ✅

---

## NITs (all already documented in-mission — informational, no action required for release)

- **NIT-1 (latent 4th empty-mid8 seed — `agent/tasks.py:4047`).** `resolve_mid8(mission_slug,
  mission_id=None)` is the same empty-identity *shape* as the M3 defect, in a tasks-finalize
  read-path bootstrap. Plan §179-182 + `tasks-review/paula-coverage.md` NIT-3 flagged it as
  "verify-or-document". It now carries an in-code rationale (`tasks.py:4042-4046`: "no declared
  mission_id at this bootstrap, so the seam DECLINES a coincidental tail rather than
  mis-routing"), so the D-6 "MUST-NOT seed empty" contract is enforced-by-documentation here.
  Benign in context; no coord-guard suppression because no coord topology is asserted at this
  bootstrap. Recommend an explicit follow-up tracker so it is not re-flagged by a future sweep.

- **NIT-2 (dict `# type: ignore[type-arg]` at `decision.py:129/153`).** Pre-existing (not added
  by this mission — confirmed: zero new suppressions in the diff). Out of scope; note only.

- **NIT-3 (M1 naming vs. spec/plan).** Plan D-7 calls the M1 surface "context mission-resolve"
  but the fix lives in `context/resolver.py` (routing through `resolve_feature_dir_for_mission`),
  with the cite-correction recorded in-plan. Cosmetic — the code is correct and the plan already
  carries the corrected cite. No action.

---

## Tests run in this review

- `tests/mission_runtime/test_context_factory_invariant.py` + `test_status_read_path_error_contract.py` — 10 passed
- `tests/specify_cli/cli/commands/test_decision_single_authority.py` + `core/test_resolve_canonical_root_submodule.py` + `cli/commands/charter/test_status_no_op.py` — 18 passed
- Runtime-verified: factory privacy, invariant fires, composite frozen
- `ruff check` on all 12 touched source files — All checks passed
