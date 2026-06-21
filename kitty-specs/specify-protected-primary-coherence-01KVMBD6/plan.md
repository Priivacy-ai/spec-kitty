# Implementation Plan: Specify on Protected Primary + Branch-Protection Config

**Branch**: `fix/specify-protected-primary-coherence` (stacked on `pr-2051`) | **Date**: 2026-06-21 | **Spec**: [spec.md](spec.md)
**Input**: Mission specification from `kitty-specs/specify-protected-primary-coherence-01KVMBD6/spec.md`
**Design basis**: [research/protected-branch-carrier-decision.md](research/protected-branch-carrier-decision.md) · ADR [`2026-06-21-1`](../../architecture/3.x/adr/2026-06-21-1-protected-branch-config-boundary-resolved-value.md)

## Summary

Close the #1619 P0 specify-phase deadlock on a `main`/`master`-named primary, and remove its
underlying brittleness, in three complementary moves:

1. **Deadlock fix (pillar A):** materialize the coordination worktree **on demand at the spec
   commit boundary** (reuse the canonical `CoordinationWorkspace.resolve()` — the same on-demand
   path `_planning_commit_worktree` already uses for plan/tasks) so the protected-primary commit
   lands on the coordination branch; make the refusal error actionable.
2. **Owner-configurable protection (pillar B):** read the protected-branch set from `.kittify`
   config (default `{main, master}` unchanged). An owner who marks the primary unprotected gets
   the documented "commit straight to the target branch" behavior.
3. **Boundary-resolved config (pillar C):** a **standalone, frozen value object**
   (`ProtectionPolicy`) with one `resolve(repo_root)` boundary resolver, passed explicitly,
   feeding the **existing** pure `commit_guard.evaluate(ProtectionState)` decision seam. Replace —
   not parallel — the ~8 scattered `protected_branches(repo_root)` reads; guard the single
   authority (FR-010 / #1868).

Plus pillar **D**: align the `software-dev` specify runbook so its instructions match the guard.

**Key de-risking fact:** the boundary-resolved *decision* already exists
(`core/commit_guard.py` `evaluate(target, ProtectionState, capability)` is pure/IO-free); pillar C
is "lift the input to one resolver + route the callsites", not new decision machinery.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing internal seams — `core/commit_guard.evaluate` + `ProtectionState`
(decision), `coordination/workspace.CoordinationWorkspace.resolve` (materializer),
`git/commit_helpers.protected_branches` (input, to be demoted behind the resolver), `ruamel.yaml`
via the `.kittify/config.yaml` reader pattern (`core/agent_config.py`); typer/rich CLI; pytest/mypy/ruff.
**Storage**: `.kittify/config.yaml` (additive protection key); coordination worktrees on disk under `.worktrees/`.
**Testing**: pytest — zero-mock unit tests for the pure `ProtectionPolicy` value + `resolve()`
(tmp_path config fixtures); integration tests on a real git repo with a `main`-named protected
primary for the spec-commit materialization (the kentonium3 repro); an architectural single-resolver
guard test (FR-010); regression tests for default byte-identical behavior (NFR-004) and the #1718
create-window (NFR-001).
**Target Platform**: Linux/macOS developer CLI (`spec-kitty`).
**Project Type**: single (CLI library — `src/specify_cli/` + `src/mission_runtime/`).
**Performance Goals**: on-demand materialization < 2 s warm with 0 network round-trips (NFR-002);
0 filesystem/git reads for the protection set after boundary resolution (NFR-003).
**Constraints**: reuse the canonical materializer — no parallel path (C-001); never weaken the
protected-branch guard (C-002); preserve the #1718 create-window contract (NFR-001); `.kittify`
config additive + backward-compatible (C-004); default `{main, master}` byte-identical (NFR-004);
distinct seam from #2040 (C-005).
**Scale/Scope**: 1 new value object + 1 boundary resolver; ~8 protection callsites re-routed; 1 new
CLI commit-boundary behavior (materialize-then-retry); 1 runbook alignment; 1 architectural guard.
Estimated 5–6 WPs.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

Charter mode: compact (`software-dev-default`, directives DIR-001..DIR-013). Relevant gates and how
this plan satisfies them:

- **Canonical sources / no improvised parallels** — pillar A reuses `CoordinationWorkspace.resolve()`
  and pillar C reuses `commit_guard.evaluate(ProtectionState)`; no new materializer, no new decision
  function (C-001, C-002). ✅
- **Ownership boundaries for mutating flows** — the protection decision becomes a single boundary
  resolver; the guard (FR-010) ratchets it. ✅
- **Identifier-safety / loopback / terminology canon** — the runbook edit (pillar D) and any new
  config keys use canonical "Mission" terminology and must not introduce `feature*` aliases; the
  pre-push terminology guard applies (doctrine prose touched). ✅ (verify at implement)
- **No suppression of lint/type/Sonar gates** — new code passes ruff/mypy clean; complexity ≤ 15. ✅
- No charter violations identified. Complexity Tracking: none required.

## Implementation Stance — campsite-cleaning default (#1970)

This mission **locally adopts** the [#1970](https://github.com/Priivacy-ai/spec-kitty/issues/1970) stance
(DIRECTIVE_025 Boy Scout as the default, not an optional nicety): it extracts from a god-module
(`mission.py`), reroutes ~8 protection callsites across multiple files, and adds tests — so WP agents
**will** touch code that already carries pre-existing lint/type/test breakage.

- **Default = fix it.** When a WP touches an area with a failing test or a lint/type issue, the default is
  to **fix it outright** within the touched scope — not to leave it and litigate "pre-existing vs introduced".
  Proving innocence routinely costs more than the fix.
- **Bounded.** Cleanup applies only to **areas the work touches** (the WP's `owned_files` + the seams it
  edits) — not unbounded scope expansion or gold-plating (DIRECTIVE_024 Locality of Change still holds).
- **`change-apply-smallest-viable-diff` keeps the *intended change* tight** — it is NOT a license to leave
  touched breakage unfixed.
- The god-module surfaces this mission edits are tagged with their decomposition-tracking issues
  (mission.py→#2056, merge.py→#2057, tasks.py→#2058, doctor.py→#2059); do not add new responsibilities there.

## Project Structure

### Documentation (this mission)

```
kitty-specs/specify-protected-primary-coherence-01KVMBD6/
├── plan.md              # This file
├── spec.md              # Mission spec (11 FR / 4 NFR / 6 C)
├── research.md          # Phase 0 — consolidated decisions (this command)
├── data-model.md        # Phase 1 — ProtectionPolicy / ProtectionState / config schema
├── quickstart.md        # Phase 1 — the kentonium3 repro as the validation scenario
├── contracts/           # Phase 1 — .kittify protection-config schema + resolver contract
├── research/
│   └── protected-branch-carrier-decision.md   # squad synthesis (carrier decision)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── git/
│   ├── protection_policy.py        # NEW — ProtectionPolicy value + resolve(repo_root) (IC-01)
│   └── commit_helpers.py           # protected_branches() demoted behind resolver; safe_commit takes policy (IC-01/IC-02)
├── core/
│   └── commit_guard.py             # REUSED unchanged — evaluate(ProtectionState) decision seam
├── coordination/
│   ├── workspace.py                # REUSED — CoordinationWorkspace.resolve() materializer (IC-02)
│   ├── commit_router.py            # NEW — shared coord-commit helper (extracted pipeline) (IC-02)
│   └── policy.py                   # callsite re-routed (IC-03)
├── cli/commands/
│   ├── spec_commit_cmd.py          # NEW mission-aware spec-commit entrypoint (IC-02, the P0 seam)
│   ├── __init__.py                 # register the new command (IC-02)
│   ├── implement.py                # callsite re-routed (IC-03)
│   ├── accept.py                   # materialize-then-retry (IC-04)
│   └── agent/{tasks.py,mission.py} # tasks.py re-routed (IC-03); mission.py extraction + record-analysis (IC-02)
├── acceptance/__init__.py          # materialize-then-retry (IC-04)
src/doctrine/missions/mission-steps/software-dev/specify/prompt.md   # runbook alignment (IC-06)
tests/
├── git/ + unit                     # pure ProtectionPolicy/resolver (IC-01)
├── integration/                    # spec-commit materialization on protected primary (IC-07)
└── architectural/                  # single-resolver guard (IC-05)
```
> **Erratum (post-tasks):** the P0 seam is a **new** mission-aware entrypoint (`spec_commit_cmd.py` +
> `coordination/commit_router.py`), NOT the generic `safe_commit_cmd.py` (which stays mission-blind and
> unchanged) — operator decision; see WP02. The IC-02 prose below predates this and is kept for lineage.

**Structure Decision**: Single-project CLI. The new `ProtectionPolicy` lives in
`src/specify_cli/git/protection_policy.py` (next to its `commit_helpers` collaborators); everything
else is modifications to existing modules + one doctrine prompt.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs. Tidy-First ordering:
> the pure seam (IC-01) is the foundation; the P0 fix (IC-02) is the MVP slice that consumes it.
> **Revised post-squad** (2026-06-21): the deadlock class is closed at **all four** sibling sites
> (operator decision), and the spec-commit fix uses a **new mission-aware entrypoint** (operator
> decision) rather than overloading the mission-blind `safe-commit`. See Post-Planning Brownfield
> Checks for the squad findings that drove this revision.

### IC-01 — ProtectionPolicy value + single boundary resolver (Tidy-First foundation)

- **Purpose**: Introduce the standalone frozen `ProtectionPolicy` (`protected_branches`,
  `operator_hatch_active`, `is_protected(ref)`) and one `resolve(repo_root)` that reads `.kittify`
  config (default `{main, master}`, remote-default augmentation on the default path) — the single
  sanctioned producer. `protected_branches()` is demoted to the resolver's private delegate.
  **Folds #1828**: the hatch-symmetry between `assert_not_protected_branch` and `safe_commit` is
  consolidated into `operator_hatch_active` / `is_protected()` — pin a regression test and close #1828.
- **Relevant requirements**: FR-004, FR-006, FR-007 (core), FR-008; folds #1828.
- **Affected surfaces**: `src/specify_cli/git/protection_policy.py` (new), `git/commit_helpers.py`
  (`protected_branches`/`_DEFAULT_PROTECTED_BRANCHES`/`_operator_protected_branch_hatch_active`/`_remote_default_branch`),
  `.kittify/config.yaml` reader pattern.
- **Sequencing/depends-on**: none (foundation).
- **Risks / required tests**: must subsume the `_remote_default_branch` git read so NFR-003 holds; the
  **4-row resolution matrix must be tested here** (S-3): absent-config+`origin/HEAD=develop` ⇒
  `{main,master,develop}` byte-identical (NFR-004); explicit non-empty list ⇒ that set only (no remote
  union); `[]` + `origin/HEAD=main` ⇒ `frozenset()` (remote default NOT re-added — the owner-opt-out
  trap); malformed ⇒ fail-closed error.

### IC-02 — Mission-aware spec-commit entrypoint with materialize-then-retry (P0 / MVP)

- **Purpose**: Add a **new mission-aware spec-commit entrypoint** (the operator-chosen seam) that:
  derives/accepts `mission_slug`, resolves the COORDINATION placement via
  `mission_runtime.resolve_placement_only`, materializes the coordination worktree via the canonical
  `CoordinationWorkspace.resolve()`, **copies the spec/planning artifacts across**, and commits on the
  coordination branch; unprotected primary → direct commit; refusal errors are actionable. Builds the
  **shared coord-commit helper** that IC-04 reuses. (Renata B-1: the mission-slug derivation + placement
  resolution + artifact copy-across is the real work — not "pass a policy".)
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-005, FR-007 (deadlock site).
- **Affected surfaces** (resolved post-tasks): new `cli/commands/spec_commit_cmd.py` entrypoint +
  `coordination/commit_router.py` (the planning-commit pipeline **extracted** from `mission.py`) +
  `cli/commands/__init__.py` registration. Reuses `resolve_placement_only` /
  `coordination/workspace.CoordinationWorkspace.resolve`. The generic `safe_commit_cmd.py` is unchanged.
- **Sequencing/depends-on**: IC-01. Bidirectionally coupled with IC-06 (runbook drives the entrypoint
  interface — Renata N-1).
- **Risks**: must NOT introduce a parallel materializer (C-001); preserve #1718 (materialize at commit,
  not at read); idempotent reuse of an already-materialized worktree.

### IC-03 — Route the protection DECISION INPUT through the resolver (all ~8 sites)

- **Purpose**: every protection *decision* reads `ProtectionPolicy` (feeding
  `commit_guard.evaluate(ProtectionState)`) instead of a direct `protected_branches(repo_root)` —
  replace, not parallel; `coordination/policy.py` becomes a real chokepoint. The generic `safe_commit`
  resolves via `ProtectionPolicy.resolve(repo_root)` at **its own** boundary (no param threaded through
  its ~31 callers — Renata S-1); the explicit-policy callers (IC-02/IC-04) pass it in.
- **Relevant requirements**: FR-007, FR-009.
- **Affected surfaces**: `git/commit_helpers.py:1018/1019/527`, `coordination/policy.py:214`,
  `cli/commands/implement.py:59`, `cli/commands/agent/tasks.py:882/916`, `cli/commands/agent/mission.py:898`,
  `cli/commands/accept.py:366`, `acceptance/__init__.py:1202`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: keep `safe_commit`'s default behavior for legacy callers (internal resolve = its boundary);
  leave no residual direct read.

### IC-04 — Close the deadlock class at the 3 sibling mission-aware sites (operator: whole-class)

- **Purpose**: `record-analysis` (`mission.py:~898`), `accept` (`accept.py:366`), and
  `acceptance._commit_acceptance_meta` (`acceptance/__init__.py:1202`) currently `assert_not_protected_branch`
  → `raise typer.Exit(1)` **before** any materialization — the same deadlock class (Paula F1;
  `record-analysis` even has the identical "actionable error points at an unmaterialized path" defect).
  Route them through the **shared coord-commit helper** (IC-02) so they materialize-then-retry instead of
  deadlocking.
- **WP fan-out (post-tasks):** `record-analysis` lives in `mission.py`, so per the disjoint-ownership rule
  it is delivered by **WP02** (which owns all `mission.py` edits); **WP04** delivers `accept` +
  `acceptance._commit_acceptance_meta`. (One IC → multiple WPs, as the IC-map note permits.)
- **Relevant requirements**: FR-001, FR-003 (extended to the class), SC-001 (class).
- **Affected surfaces**: `cli/commands/agent/mission.py` (record-analysis preflight ~831/898 — WP02),
  `cli/commands/accept.py:366` + `acceptance/__init__.py:1202-1224` (WP04).
- **Sequencing/depends-on**: IC-02 (shared helper), IC-03.
- **Risks**: accept/acceptance commit-path blast radius; idempotent reuse; preserve each command's
  existing semantics apart from the protected-primary routing.

### IC-05 — Single-resolver architectural guard (FR-010 / #1868)

- **Purpose**: A `tests/architectural/` guard (reuse the `test_guard_capability_call_sites.py` pattern)
  asserting protected-branch **decisions** route only through the resolver allowlist; any new direct
  `protected_branches(repo_root)` / literal `{main, master}` decision fails CI. **Must allowlist /
  scope-exclude the classification sets** `_WELL_KNOWN_INTEGRATION_BRANCHES` (`acceptance/__init__.py:1193`)
  and `common_primary_branches` (`mission.py:598`) — they are integration/primary detection, NOT
  protection (Paula F2), or the guard is over-broad red on day one.
- **Relevant requirements**: FR-010.
- **Affected surfaces**: `tests/architectural/`.
- **Sequencing/depends-on**: IC-03, IC-04 (the collapsed tree).
- **Risks**: precise allowlist (resolver + demoted delegate; classification sets excluded).

### IC-06 — Specify runbook alignment to the new entrypoint (pillar D)

- **Purpose**: Re-point the `software-dev` specify prompt from `spec-kitty safe-commit <feature_dir>/spec.md`
  to the **new mission-aware spec-commit entrypoint** (IC-02), so a reviewer on a protected primary is
  never told to run a refused command (SC-005).
- **Relevant requirements**: FR-011, SC-005.
- **Affected surfaces**: `src/doctrine/missions/mission-steps/software-dev/specify/prompt.md`.
- **Sequencing/depends-on**: IC-02 (entrypoint interface — bidirectional, N-1). Terminology guard applies.
- **Risks**: SOURCE template only (agent copies regenerate via upgrade); canonical "Mission" terminology.

### IC-07 — Acceptance, regression & non-regression coverage (non-fakeable)

- **Purpose**: prove the fix with assertions that **fail if materialization is removed** (Renata B-2):
  (1) the kentonium3 end-to-end repro (SC-001) on a protected-named primary — after the spec commit,
  `spec.md` is on `kitty/mission-<slug>`, the primary tree is clean, `.worktrees/<slug>-<mid8>-coord/`
  was created **by the command**, with **zero** hatch and **zero** manual git; (2) the same for the 3
  sibling sites (IC-04); (3) US2 config-honoring (protected→worktree, unprotected→direct, SC-002);
  (4) NFR-003 **spy instrument** (Renata S-2): `ProtectionPolicy.resolve`'s reads happen once at the
  boundary, **zero** reads inside `is_protected`/`commit_guard.evaluate`; (5) FR-006 hatch regression
  (active ⇒ `is_protected` False end-to-end); (6) #1718 create-window non-regression (NFR-001) by
  **extending** the existing `tests/mission_runtime/test_read_path_create_window_invariant.py`;
  (7) default byte-identical (NFR-004); (8) NFR-002 materialization bound (observed-or-gated).
  Reuse the existing `tests/git/protected_target_fixtures.py::ProtectedTargetRepo` fixture.
- **Relevant requirements**: SC-001..005, NFR-001..004, FR-006.
- **Affected surfaces**: `tests/integration/`, `tests/git/`, `tests/architectural/`, `tests/mission_runtime/`.
- **Sequencing/depends-on**: IC-02, IC-03, IC-04.

## Post-Planning Brownfield Checks

Dispatched anti-laziness / related-issues discovery squad (profile-loaded, opus): **planner-priti**
(tracker), **patterns-paula** (brownfield scope), **reviewer-renata** (anti-laziness). Outcomes folded
into the IC map above; recorded here:

**Scope corrections (drove the IC revision):**
- **Deadlock is broader than `specify`** (Paula F1, Renata B-1): `record-analysis`/`accept`/
  `acceptance._commit_acceptance_meta` hard-fail the same way. **Operator decision: close the whole
  class** → IC-04. **Operator decision: new mission-aware spec-commit entrypoint** (not overloading the
  mission-blind `safe-commit`) → IC-02/IC-06.
- **`safe_commit` has ~31 callers** (Renata S-1; original "~18" corrected post-tasks): the new-entrypoint
  seam avoids threading a param through them; generic `safe_commit` resolves at its own boundary (IC-03).
- **Non-fakeable test requirements** (Renata B-2/S-2/S-3, S-4): negative materialization assertions,
  NFR-003 spy, the 4-row empty-config/remote-default matrix, FR-006 hatch test, NFR-002 bound → IC-07
  + IC-01.

**Foldable / tracker (Priti):**
- **Fold #1828** (hatch-asymmetry; de-facto fixed by PR #1850; lands in IC-01's exact `commit_helpers.py`
  lines) → verify-and-close via IC-01 regression pin. Issue-matrix: `in-mission (verify-and-close)`.
- **Do NOT fold #1829** (competing "delete the guard" decision — superseded by ADR 2026-06-21-1's
  configure-and-route). Reference only.
- Added references: **#1878** (placement strangler umbrella — discharges its specify-phase evidence),
  **#1829** (divergent decision), **#2040** (out-of-scope boundary marker, C-005).

**Deferred-with-note (safe as scoped):**
- Classification sets `_WELL_KNOWN_INTEGRATION_BRANCHES` / `common_primary_branches` inspected — NOT
  protection decisions; IC-05 guard must scope-exclude them (Paula F2).
- `.kittify` config-loader consolidation deferred (Paula F4): adding `protection:` introduces no
  split-brain (new key, no competing reader); follow-on strangler should note **N≥6** existing readers,
  not "four".
- `--to-branch` v3.3 deprecation (Paula F3): **defer to a release-gated change** (no version
  prescription); do not silently drop the warning when touching the surface.

### Test Impact & CI (sweep squad — renata + paula)

**Existing-test landmines (must be edited in the SAME WP that changes the behavior — never ship a
refusal→materialize flip while a test still asserts the old refusal):**
- **L1** `tests/specify_cli/cli/commands/agent/test_record_analysis_coord_worktree.py:225` — asserts
  `PROTECTED_BRANCH_REFUSED`; **REWRITE** for IC-04 (materialize-then-retry, report lands on coord branch).
- **L2** `tests/cross_cutting/misc/test_acceptance_support.py:519` `test_accept_protected_branch_no_mutation`
  — asserts refusal + no mutation; **REWRITE** for IC-04.

**Silently-vacuous patch targets (mocks survive as importable names but leave the decision path — add the
NFR-003 resolver spy so a moved decision can't hide green):**
- **P1** `tests/agent/test_implement_command.py:428` (patches `implement.protected_branches`) — re-point to resolver.
- **P2** `tests/specify_cli/cli/commands/agent/test_move_task_guard.py:163/210/222` (patches `tasks.protected_branches`).
- **P3** `tests/git/protected_target_fixtures.py:79-81` `ProtectedTargetRepo.assert_target_is_protected` calls
  `protected_branches()` directly and backs 5+ suites — route through `ProtectionPolicy` OR keep
  `protected_branches` a public delegate (decide in IC-01).

**Architectural ratchet (decide import topology in IC-01 BEFORE writing IC-03 callsites):**
- **A1** `tests/architectural/test_safe_commit_import_boundary.py:146` — `_BLESSED_EVALUATE_IMPORTERS` is
  locked to `commit_helpers` + `coordination/policy`. Route the new resolver/callsites' `commit_guard.evaluate`
  use through the `commit_helpers` facade, OR add `git/protection_policy.py` to the allowlist with rationale.

**KEEP (preserved by C-002 / reuse):** the generic `safe_commit()` refusal tests, `test_commit_guard.py`
(reused decision seam), all `CoordinationWorkspace.resolve`/`resolve_placement_only`/`_planning_commit_worktree`
suites (IC-02 reuses, adds a caller — no path change), `test_read_path_create_window_invariant.py` (extended by IC-07).

**CI / test architecture (paula) — NO new test block, NO new CI job, NO new marker:**
- IC-07 e2e → `tests/integration/` (precedent `test_sc6_planning_placement_e2e.py`); config-honoring +
  pure resolver → `tests/git/`; #1718 → **extend** the existing invariant test; IC-05 guard →
  `tests/architectural/` (clone `test_guard_capability_call_sites.py`). Markers reused
  (`architectural`/`integration`/`git_repo`/`regression`/`unit`/`timing`).
- IC-07 integration is **parallel-safe** (hermetic `tmp_path` `ProtectedTargetRepo`) — **no `-n0` lane**.
- IC-05 guard auto-collected via `pytestmark = pytest.mark.architectural`; rides `integration-tests-core-misc`
  → `quality-gate`. No aggregation edit.
- **Gate-safety (the standing CI-only-gate trap):** the `architectural` shard runs ONLY in
  `integration-tests-core-misc` (heavy lane, skipped on draft PRs without `ci:full`) — NOT in fast-tests.
  The IC-05 guard MUST be a **repo-wide `src/` scan** (never mission-diff-scoped) and ship its F2
  classification-set exclusions in the **same commit**. Pre-push runbook (add to the IC-05/IC-07 WP):
  `PWHEADLESS=1 pytest tests/architectural/ -m architectural -q` + the new integration/create-window tests
  + `pytest tests/architectural/test_no_legacy_terminology.py -q` (IC-06 doctrine prose).

## Complexity Tracking

No Charter Check violations — section intentionally empty.
