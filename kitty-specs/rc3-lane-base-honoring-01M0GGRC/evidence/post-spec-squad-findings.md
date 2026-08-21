# POST-SPEC adversarial squad — convergent findings (2026-08-21)

Four profile-loaded, read-only lenses reviewed the finalized spec against current
`upstream/main`: architect-alphonso (seams), debugger-debbie (reachability + live
repro), reviewer-renata (anti-laziness / contract-vs-impl), python-pedro (implementer
feasibility). Findings that survived independent scrutiny (2+ lenses converge unless
noted). Verdicts: architect = load-bearing gap; reviewer = REVISE-BEFORE-PLAN;
pedro = feasible-but-resolve-collisions; debbie = D2 phantom + real sites confirmed.

## F1 — Caller enumeration (C-001) was incomplete [architect, pedro, debbie]
`allocate_lane_worktree` has **two** production callers, not one:
- `src/specify_cli/lanes/implement_support.py:92` (`create_lane_workspace`, the real
  `implement --base` dispatch)
- `src/specify_cli/orchestrator_api/commands.py:903` (`_resolve_start_workspace`)

The smuggled `mission_branch=base` (implement.py:1412) ALSO flows into
`create_lane_workspace`, where it becomes `base_branch`/`base_commit` recorded in WP
frontmatter, `WorkspaceContext`, `LaneWorkspaceResult.mission_branch`, and drives
`_has_commits_beyond_base` reuse detection (implement_support.py:110-174). Dropping the
smuggle without threading `base` here silently reverts coord provenance to
`kitty/mission-<slug>`. → **C-001 must name implement_support.py + orchestrator_api.**

## F2 — Legacy `--base` (#1684) must not break; the seam is topology-blind [reviewer, pedro, architect]
`_resolve_active_lanes_manifest` (implement.py:1391) branches only on `is_planning_lane`
— it is **topology-blind** (no coord-vs-legacy discrimination). The legacy `else`
(worktree_allocator.py:272-276) reads ONLY `mission_branch`, whose sole source is the
smuggle. A global smuggle-removal silently breaks legacy `--base`. → **Resolution: the
allocator (topology-aware via `_read_coordination_branch`) receives an explicit `base`
param and routes it to BOTH the coord fresh-create AND the legacy path. The "272-276
byte-for-byte" aspiration softens to "behavior-preserving": legacy uses
`base if base is not None else mission_branch`.**

## F3 — D2/AC-3(c) "existing coordination_branch needs re-parenting" is a PHANTOM [debbie HIGH, architect MAJOR]
Empirically probed (`d2_probe.py`): there is one coord fresh-create route
(worktree_allocator.py:260); a pre-existing `coordination_branch` merely makes
`_ensure_branch_exists` a no-op — the lane still branches straight from it. M1 re-parents
the **lane**, not the coord branch, so honoring `base` on fresh-create is always possible
and NEVER "requires re-parenting the coordination_branch." Worse: coord always exists by
the 2nd lane, so any guard on "coord exists + base" would fire on FR-001's happy path.
→ **AC-3(c) as written can only pass by mocking. Its real, reachable attachment point is
F4 (dependency lane), not "coord branch exists."**

## F4 — D1 "base alone" collides with downstream merge composition [pedro HIGH×2, architect MAJOR]
Three couplings the light spec missed:
1. **Dependency-tip merge** (`_merge_dependency_lane_tips`, :419-515): a WP with
   `depends_on_lanes` merges `dep_branch`, which descends from coord→U. Parenting on
   `base` alone then merging re-imports coord+U as ancestors → **violates FR-002**.
   FR-002 and NFR-003 collide for dependency lanes.
2. **Planning-commit merge** (`_merge_recorded_planning_commit`, :297-355): with a
   genuinely **detached** base (issue's own example `op/elu-detached-forward`),
   `git merge` can return "refusing to merge unrelated histories" (no
   `--allow-unrelated-histories`) → `PlanningCommitMergeConflictError` with zero textual
   conflict. The current repro builds B off the same ROOT, so never exercises this.
3. **for_review gate** (`for_review_gate.resolve_lane_base_ref`, :55-88): independently
   resolves the lane base AS the coordination branch for `rev-list <base>..HEAD`. A
   base-alone lane measures against the wrong ref → a lane with zero real implementation
   work can spuriously PASS the gate.

→ **Resolution (keeps M1 minimal, honors D1/D2):**
- Scope FR-001/FR-002 "base alone" guarantee to **no-dependency** lanes (the #3571 case).
- A WP with `depends_on_lanes` + `--base` ⇒ **fail loud (D2)** — re-parenting coord-descended
  dep tips onto base IS the M8 two-route reconciliation. **This is the real, reachable D2
  trigger** (replaces the phantom in F3).
- Planning-commit merge on a base unrelated to the planning commit ⇒ **fail loud** (do NOT
  silently `--allow-unrelated-histories`). [plan-phase decision; recommended default]
- for_review gate base resolution for base-alone lanes ⇒ **documented M8 limitation**
  (the gate's base resolution is part of the two-route reconciliation). [plan-phase decision]

## F5 — Red-first must go through the real seam [debbie MEDIUM-HIGH, reviewer HIGH]
The committed repro AND the existing #1684 test (test_issue_1684_cross_lane_base.py) both
hand-smuggle `mission_branch` and bypass `_resolve_active_lanes_manifest`. C-003 requires
AC-1 red "through the real `implement --base` entry path." An allocator-only green stays
green even if a caller forgets the param. → **Add a CLI/seam-level AC-1 that drives
`implement --base` (or `_resolve_active_lanes_manifest`→allocator) and asserts ancestry;
keep the allocator unit as companion.** API-shape trap: the symptom-faithful red must
drive the seam so one test body is red-before / green-after (a kwarg-shape test errors
with TypeError on main, which is not symptom-red).

## F6 — Anti-laziness hardening on AC-3/AC-4 [reviewer MEDIUM]
- AC-3: build the REAL reuse (allocate, re-allocate with base) and crash-recovery (branch
  exists, dir gone) states; assert the **typed** exception; forbid mocking the allocator.
- AC-4: one assertion set must prove the success line is PRESENT on the honored path AND
  ABSENT on an ignored/error path.

## F7 — Success print relocation + orchestrator except-tuple + default param [pedro, architect]
- The `→ Using explicit base ref` print (implement.py:1411) fires BEFORE allocation.
  Relocate it to AFTER a successful `create_lane_workspace` return (post-1886), in the CLI
  layer (orchestrator runs silent — commands.py:524). Keep it OUT of the lanes core.
- The new typed fail-loud exception must be added to the orchestrator except-tuple
  (commands.py:906-914, currently `LaneNotFoundError, DirtyWorktreeError,
  DependencyLaneMergeConflictError, RuntimeError`) or it escapes the envelope.
- `allocate_lane_worktree`'s new param must be `base: str | None = None` **with a default**
  to keep all ~30 existing call sites and NFR-001 green.

## F8 — D3 reuse hard-error affects sequential same-lane WPs [architect MINOR]
Orchestrators/agents that pass `--base` on every WP invocation will hard-error on WP2+
(reuse path). → Document in Risks: harnesses pass `--base` only on lane creation.

## F9 — FR-008 docstring must reflect the real threaded mechanism [reviewer LOW]
The corrected docstring (worktree_allocator.py:450-453) must accurately describe `base`
arriving via the threaded param on both routes — not merely "no mission_branch smuggling."

## CONFIRMED REAL (not defects — validation)
- Reuse (:191) and crash-recovery (:235) fail-loud sites: REAL, REACHABLE via
  `implement --base`, correctly warrant D3 hard-error [debbie].
- AC-1 `--is-ancestor` method is sound; committed repro genuinely reaches coord
  fresh-create (no pre-existing worktree/branch) — #3571 reproduces, EXIT=0 [debbie].
- AC-4 core is observably testable through the real entry once the print moves [debbie].
- Allocator-internal merges compose on top of any parent; sparse-checkout registration has
  no ancestry check → coherent with base-alone for the no-dependency case [architect].
