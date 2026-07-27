# P0 Coord-Topology Defects — Root-Cause Research (debugger-debbie)

**Op:** mission-prep-p0 · **Profile:** debugger-debbie · **Date:** 2026-06-12 · **Mode:** read-only pre-mission research (no fixes, no commits)
**Tree under test:** branch `feat/doctrine-glossary-consolidation-01KTNWFC` @ HEAD `82d2524af`, which contains upstream `3f2af08f0` (coordination-merge-stabilization / mission 131) **as an ancestor** (verified `git merge-base --is-ancestor`), plus our own `8544012fa` (01KTPKST + 01KTRC04 tooling-stability / execution-context unification) and `c5a10ce56` (#1772 coord-topology hardening). **This is NOT the reporter's rc37/rc42 tree** — several defects were repaired *after* the report by `8544012fa`/`c5a10ce56`.
**Version note:** reproductions run against the repo `src/` tree via `PYTHONPATH=.../src` (the worktree code = the branch under test). Installed rc43 in site-packages is structurally identical for the surfaces checked. Reporters saw rc37 (#1889), rc42 (#1883/#1884/#1885).

---

## Per-defect summary table

| Defect | Root file:line | Canonical authority that SHOULD rule | Scan cluster | Quick-fix vs seam | Upstream-overlap verdict (tested on THIS tree) |
|--------|----------------|--------------------------------------|--------------|-------------------|-----------------------------------------------|
| **#1883** accept self-defeats on git_dirty | `acceptance/__init__.py:934` (early `git_dirty` snapshot) **before** `:753-754` (`enforce_negative_invariants`+`write_acceptance_matrix`) + `cli/commands/accept.py:365` (`_commit_residual_*` gated on `commit_required`, skipped in `--no-commit`/diagnose) | "a gate must never fail on state the tool wrote in the same workflow" (the #1814 design principle). No single resolver — needs **pre-write snapshot / accept-owned-path exclusion seam**. | none directly (gate-self-write anti-pattern, sibling of Cluster D's "tool fails on own state") | **NEEDS SEAM** (snapshot-vs-write ordering + non-idempotent matrix write + --no-commit no-cleanup are one structural class) | **NOT FIXED.** `3f2af08f0` only *committed mission-131's own acceptance artifacts* (operator workaround); accept code's last functional change is `8544012fa`. Self-defeat persists. |
| **#1884** setup-plan committedness coord-blind | `cli/commands/agent/mission.py:1821` `is_committed(spec_file, repo_root)` → `_substantive.py:214-239` `git -C repo_root cat-file -e HEAD:<rel>` (primary HEAD only) | `mission_runtime.resolve_placement_only` (the SAME write-side authority setup-plan already uses at `mission.py:566/933/…`) → check `git cat-file -e <placement.ref>:<rel>` against the COORDINATION ref | **Cluster B** (read-side mirror; gate reads primary while writer routes to coord — same shape as #1784 catch-22) | **QUICK-TARGETED** (thread `placement.ref` into `is_committed`; the placement resolver already exists in-module) | **NOT FIXED.** `is_committed` unchanged since #898 (`b8111ecc4`); `3f2af08f0` did not touch `_substantive.py`. Reproduced shape on tree. |
| **#1885** next returns unknown stub | `runtime/next/runtime_bridge.py:3068-3087` (`query_current_state`: `ActionContextError`/`not is_dir` → `mission="unknown",mission_state="unknown", reason=None`) | `mission_runtime.resolve_action_context` + `mission_runtime/resolution.py:118 _mid8_from_primary_meta` (mid8-handle canonicalization) | **Cluster B/C** (mid8-handle resolution; legacy-shape blindness) — but the resolver was *fixed* | **QUICK-TARGETED residual** (the unknown-stub `reason=None` should be a structured error, not silent) | **FIXED (the reported symptom).** On THIS tree `resolve_action_context(feature='01KTXR99')` resolves correctly; `query_current_state` returns `mission=software-dev` not `unknown`. mid8 canonicalization landed in `8544012fa`/`resolution.py`. Residual: the silent-stub fallthrough still exists for genuinely-unresolvable handles. |
| **#1889** decision crash StatusReadPathNotFound on flattened mission | (rc37) `missions/_read_path_resolver.py` fail-closed raised whenever `_declares_coordination_branch` regardless of worktree presence | meta.json is authority; declared-but-unmaterialized coord must have defined semantics. `_read_path_resolver._resolve_existing_for_slug` + the `coord_worktree_materialized` guard | **Cluster A** ("is coord?" / declared-coord topology decision) | (already done) | **FIXED.** The `coord_worktree_materialized` guard added in `8544012fa` (and `cf4ad4cca` for #1718) makes the resolver return the **primary** dir when coord declared but worktree absent. Reproduced flattened fixture: **no crash**, returns primary; bare-slug-without-mid8 raises a *structured* `ActionContextError` (not a raw traceback). |

---

## Shared-root analysis — how many distinct roots across the four?

**Two roots, plus one already-closed.**

1. **ROOT-α — "verify against the wrong authority surface" (read/write split-brain).** Covers **#1884** and **#1889** (and is the deep shape behind #1885's reported symptom). A gate/resolver consults the *primary checkout HEAD or path-shape* while the real authority is the *placement/coordination ref or meta.json topology*. This is exactly Cluster A (#1889 — path-shape vs registry/meta) and Cluster B (#1884 — primary-HEAD read vs `resolve_placement_only` coord ref). The fix template is identical: **route the verifier through the same `resolve_*` authority the writer uses.**
   - #1889 is the **already-closed instance** of ROOT-α: `8544012fa` made the read-path resolver honour `coord_worktree_materialized` (meta-declared-but-unmaterialized → defined primary-fallback semantics, no crash).
   - #1885's reported symptom is the **same root, mid8-handle facet**, also closed by `8544012fa`/`resolution.py` (`_mid8_from_primary_meta`). Its *residual* is a different, smaller root (below).
   - #1884 is the **still-open instance** of ROOT-α: `is_committed` reads primary HEAD; the write side already resolves the coord placement. Quick-targeted: thread `resolve_placement_only(...).ref` into the committedness check.

2. **ROOT-β — "a gate fails on state the tool itself wrote in the same workflow" (self-defeating gate).** Unique to **#1883**. Distinct from ROOT-α: the authority surface is correct, but the *temporal ordering* (snapshot `git_dirty` at L934 → then `write_acceptance_matrix` at L754 → non-idempotent re-execution of negative invariants) plus the **`--no-commit`/diagnose path never running `_commit_residual_acceptance_artifacts`** (accept.py:365 gates it on `commit_required`) leaves accept-owned writes dirty for the next run to trip over. Needs the structural seam: snapshot/diff against a pre-write baseline, or exclude accept-owned artifact paths from accept's own `git_dirty` gate, on **all** modes (incl. `--no-commit`/diagnose).

3. **ROOT-γ (minor, residual) — "silent unusable stub instead of a structured error."** The #1885 residual: `query_current_state` returns `mission="unknown", reason=None` rather than raising a named resolution error when a handle is genuinely unresolvable. Low-severity; folds into the "no silent fallback / structured error" discipline (Cluster D family). Quick-targeted.

**Net for the upcoming mission:** only **#1883 (ROOT-β)** and **#1884 (ROOT-α, still-open)** are live P0 work. **#1889 and #1885's reported symptom are already fixed on this branch** by `8544012fa` (verify-don't-trust their report version). #1885 carries a small ROOT-γ residual (structured-error hardening) and #1884 is a clean quick-targeted fix routing the committedness gate through `resolve_placement_only`; #1883 is the only one demanding a real seam.

---

## Detailed evidence per defect

### #1883 — accept self-defeating git_dirty (ROOT-β, NEEDS SEAM, NOT FIXED)
Mechanism on this tree:
- `collect_feature_summary` (`acceptance/__init__.py:880`) snapshots `git_dirty` at **L934** via `_resolve_git_context` (`:503-529`, `git_status_lines(repo_root)`).
- Later in the SAME call, `_check_lane_gates` (invoked L1012) runs `enforce_negative_invariants` + `write_acceptance_matrix` at **L753-754** when `mutate_matrix=True` (the default; `cli/commands/accept.py:284` passes `mutate_matrix=not diagnose`).
- `enforce_negative_invariants` (`matrix/__init__.py:317`, `_check_invariant` re-runs grep/`subprocess`) writes **fresh** `result`/`evidence` into `acceptance-matrix.json` every run → **non-idempotent write**.
- `summary.ok` (`__init__.py:144-156`) requires `not self.git_dirty`.
- `_commit_residual_acceptance_artifacts` (`accept.py:355-365`) folds the residue into a follow-up commit **only when `commit_required`** — i.e. NOT in `--no-commit` (`accept.py:271`) and NOT in `diagnose`. So in `--no-commit` the matrix/status.json writes are left dirty; the operator restores the tree manually → "clean before, dirty-failure between, clean after" across N runs.
- `materialize()` (`status/reducer.py:318-343`) also writes `status.json` during readiness reads — a second accept-owned write source.
- The fix principle the issue cites (#1814: "a gate must never fail on state the tool itself wrote") is correct: snapshot-before-write or exclude accept-owned paths, applied to ALL modes.
- Secondary (frontmatter regression): the report's "WP01 frontmatter reverted to implementer identity" is the lane-materialization-races-event-log claim. Not reproduced in this pass (read-only / time-boxed); event-log-authoritative materialization is the structural cure and belongs in the same seam.
- **Overlap:** `3f2af08f0` added only mission-131's hand-authored `acceptance-matrix.json` + vcs-lock chores (operator workaround), NOT accept code. Accept code's last functional touch is `8544012fa`. **Defect live.**

### #1884 — setup-plan committedness coord-blind (ROOT-α open, QUICK-FIX, NOT FIXED)
- `mission.py:1819-1837`: `spec_is_committed = is_committed(spec_file, repo_root)` with the **primary** `repo_root`; on false → `error_code: SPEC_NOT_SUBSTANTIVE_OR_UNCOMMITTED`, `spec_committed: false`.
- `_substantive.py:214-239`: `git -C repo_root ls-files --error-unmatch` + `git -C repo_root cat-file -e HEAD:<rel>` — primary HEAD only. Unchanged since #898 (`b8111ecc4`).
- Write side is already coord-aware: setup-plan resolves `resolve_placement_only` via `_resolve_planning_placement` (`mission.py:566-579`, used at L933/L1968/L2012/L3391). The gate simply doesn't consult it.
- Canonical authority: `resolve_placement_only(repo_root, slug).ref` (the COORDINATION ref) → `git cat-file -e <ref>:<rel>`. Scan Cluster B fix-template + the explicit "gates must consult the same placement authority as the writers" the issue states.
- Two sibling defects the issue notes (plan auto-commit refused on protected main; lifecycle emission needing `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS=1`) are the same ROOT-α family — a call path inside setup-plan bypassing the placement routing; worth a targeted trace during implementation.
- **Overlap:** `3f2af08f0` did not touch `_substantive.py`. **Defect live.**

### #1885 — next unknown stub (ROOT-α symptom FIXED; ROOT-γ residual)
- The `[QUERY — no result provided, state not advanced]` label itself is **expected** for a bare `next` call without `--result` (`next_cmd.py:113-118` → `_run_query_mode`; `decision.py:65` `query = "query"`). The defect is the `Mission Type: unknown` / `@ unknown`, i.e. resolution failure.
- Source of the unknown stub: `runtime_bridge.py:3068-3087` (`query_current_state`): `resolve_action_context(...)` raises `ActionContextError` OR `not feature_dir.is_dir()` → returns `mission="unknown", mission_state="unknown", reason=None`.
- **Reproduced on this tree** (fully-planned coord-topology fixture, handle `01KTXR99`):
  - `resolve_action_context(feature='01KTXR99')` → resolves `kitty-specs/myplan-01KTXR99` (OK).
  - `query_current_state('orchestrator','01KTXR99',rr)` → `kind=query, mission=software-dev, state=not_started, preview_step=discovery` — **NOT unknown**.
- mid8-handle canonicalization (`mission_runtime/resolution.py:118 _mid8_from_primary_meta`, the F-001 path) landed in `8544012fa`. The reporter's rc42 predates it. **Reported symptom fixed.**
- **Residual (ROOT-γ):** when a handle is genuinely unresolvable, the function still returns a silent `mission="unknown", reason=None` stub instead of a structured/named resolution error — the "never a silent no-op stub" expectation in the issue is only half-met. Quick-targeted hardening: raise `QueryModeValidationError`/structured error with remediation instead of the unknown stub.

### #1889 — decision crash on flattened mission (ROOT-α, FIXED)
- Path: `cli/commands/decision.py cmd_open` → `decisions/service.py:234 open_decision` → `_mission_dir` → `missions/feature_dir_resolver.py:50 resolve_feature_dir_for_mission` → `mission_runtime.resolve_action_context` → `missions/_read_path_resolver.py`.
- rc37 crash root: the fail-closed branch raised `StatusReadPathNotFound` whenever `_declares_coordination_branch(primary)` was true, even with NO coord worktree on disk (the flatten pattern; matches our own `StatusReadPathNotFound` on flattened missions, MEMORY).
- This tree: BOTH the fail-closed sites now require `coord_worktree_materialized` to be true before raising — `_resolve_existing_for_slug:160-167` and the diagnostic path `:303-329`. With coord declared but worktree absent, the resolver returns the **primary** candidate.
- **Reproduced** (`/tmp/repro1889`: meta declares `coordination_branch`, no `.worktrees/...-coord/`):
  - `resolve_mission_read_path(rr,'myfeat','01ABCDEF', require_exists=False|True)` → both return primary dir, **no raise**.
  - `resolve_feature_dir_for_mission(rr,'myfeat-01ABCDEF')` → primary dir, no crash.
  - Bare slug without embedded mid8 → structured `ActionContextError` ("Mission directory not found…"), not a raw traceback — satisfies the issue's "structured, actionable error" expectation.
- Guard landed in `8544012fa` (with #1718 paired-invariant work in `cf4ad4cca`). **Defect fixed on this branch; verify against reporter's rc37, do not re-fix.**
