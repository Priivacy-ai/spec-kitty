# Implement-Loop Commit & Move-Task Hardening

**Mission**: `implement-loop-commit-hardening-01KXJ1ZX`
**Type**: software-dev · **Kind**: Task (bundles 2 Bugs + 2 Tasks) · **Milestone**: 3.2.x
**Tracker**: closes [#2647](https://github.com/Priivacy-ai/spec-kitty/issues/2647), [#2648](https://github.com/Priivacy-ai/spec-kitty/issues/2648), [#2649](https://github.com/Priivacy-ai/spec-kitty/issues/2649), [#2650](https://github.com/Priivacy-ai/spec-kitty/issues/2650) — all sub-issues of [#2160](https://github.com/Priivacy-ai/spec-kitty/issues/2160); folds [#2604](https://github.com/Priivacy-ai/spec-kitty/issues/2604) (`_mt_commit_wp_file` complexity, same function as FR-004)

## Purpose

This mission closes the four residual findings from the merged #2533 (partition-aware
implement-claim precondition). Two are reliability bugs in the implement/review loop;
two are maintainability paydowns in the same commit/move-task code. Together they make
the loop reliable **from any working directory** and give the planning-artifact
placement logic a **single, well-tested authority**.

All prior #2160 missions are merged — there is no parallel #2160/#2465 work — so
picking up the #2160 placement-seam slice (#2650) here, with the code context already
loaded, is the efficient path, not a collision risk.

## Domain Language

| Canonical term | Meaning |
|----------------|---------|
| Mission root | The canonical repository-root checkout that owns a mission's status surface (not a lane worktree) |
| Status surface | The resolved location of `status.json` / `status.events.jsonl` for a mission |
| Planning-artifact commit executor | The code that partitions dirty planning files by PRIMARY/COORD and commits each group to its ref |
| `planning_branch` | The primary/target ref planning artifacts commit to (a mission's `target_branch`) |
| Residue heuristic vs kind classification | `is_coordination_artifact_residue_path` (name-based) vs `kind_for_mission_file`+`resolve_placement_only` (kind-based) — the two partition classifiers to reconcile |

## User Scenarios & Testing

**Primary actor**: an implementing/reviewing agent (or the operator) driving the
implement/review loop, often with the working directory inside a lane worktree.

### Acceptance Scenarios

1. **move-task from a lane worktree (#2647).**
   *Given* a WP `in_progress` with a lane worktree, and the working directory set to
   that worktree, *When* the agent runs `spec-kitty agent tasks move-task WP## --to for_review`,
   *Then* the transition succeeds (it reads the mission's status surface from the
   canonical mission root, not the worktree), matching the result of running it from
   the repo root.

2. **Protected-branch coord divert fails closed, not silently (#2648).**
   *Given* a coordination mission whose own `planning_branch` is protected AND whose
   `placement_ref` resolved to `None` (the narrow `767` triple: `None` + meta `coord_branch`
   truthy + `is_protected(planning_branch)`), *When* an agent claims a WP, *Then* the
   artifact-commit step fails closed with `PlacementResolutionRequired` (the same precondition
   + operator remediation message as the status-commit step, which already fails closed on
   this state), rather than silently diverting PRIMARY artifacts to the coordination branch.
   The `767-789` fallback arm is removed. *And* a legacy/flat mission (`placement_ref is None`
   with no coord branch) and a coord mission with a non-protected `planning_branch` still
   commit successfully — the strangler fallback is preserved (asserted explicitly).

3. **Sonar debt paid, behavior unchanged (#2649).**
   *Given* the decomposed `implement.py` / `tasks_move_task.py` god-functions, *When*
   the existing suites run, *Then* they pass unchanged and each extracted helper has a
   focused test; SonarCloud no longer reports S3776/S107 on the named functions.

4. **Characterization gate before the swap (#2650, FR-006).**
   *Given* the three partition-decision sites and their `kind=None` disagreement set,
   *When* the characterization gate runs before any consolidation, *Then* the intended
   unified placement (`kind=None`→PRIMARY) is pinned in tests, so the swap is made
   against a documented contract, not against two suites that encode opposite directions.

5. **One commit authority (#2650, FR-005).**
   *Given* the consolidated planning-artifact commit path, *When* planning artifacts are
   committed on any topology, *Then* the three sites resolve to one shared callable
   (structural test), read-side and write-side agree on the primary ref by construction,
   `meta.json`/`kind=None` routes PRIMARY, and #2648's fallback regression stays green.

### Edge Cases

- move-task from the repo root continues to work — asserted explicitly, not just implied (FR-001).
- The residue-vs-kind divergence (#2650) is exactly the `kind=None` set (`meta.json` +
  unrecognized paths): the residue authority routes them PRIMARY (#2533-safe), the kind
  authority routes them to the caller partition (can be COORD → #2533 regression). The
  consolidation MUST pick PRIMARY (C-007) and pin it by test.
- A detached-HEAD / off-target-branch claim no longer risks read/write ref disagreement
  (unified ref expression, FR-005).
- The **narrow-triple** claim (`placement_ref is None` + meta `coord_branch` truthy +
  protected `planning_branch`) must fail closed at BOTH the artifact-commit and status-commit
  steps with the same `PlacementResolutionRequired` precondition — no partial commit, no
  silent coord divert (FR-002). The OTHER `placement_ref is None` states (legacy/flat, and
  coord + non-protected `planning_branch`) are legit strangler fallbacks and MUST keep
  committing successfully — do NOT fail-close on bare `None` (would red 3 shipped write-side
  tests + the #2533 regression; #2463 None-overload landmine).

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `agent tasks move-task` MUST succeed when invoked with the working directory inside a lane worktree, resolving the mission status surface from the canonical mission root independent of cwd — matching the repo-root result. The fix MUST NOT regress the repo-root invocation (asserted explicitly, paired with C-002's red-first harness). (#2647) | Planned |
| FR-002 | The silent protected-`planning_branch` fallback (`implement.py:767-789`, introduced by #2533 WP02) that diverts dirty PRIMARY planning artifacts to the coordination branch MUST be **removed and replaced with a loud fail-close**. The fail-close condition is the NARROW arm that fallback occupies — `placement_ref is None` **AND** a meta-derived `coord_branch` is truthy **AND** `is_protected(planning_branch)` — which is EXACTLY the case where the SAME claim's status-commit half already fail-closes (`_resolve_claim_commit_target`, `implement_cores.py:608`, raises on `None`). On that condition the artifact-commit half MUST raise `PlacementResolutionRequired` with the same operator remediation message, so both halves of the claim agree and no partial/silent commit to coord occurs. **CRITICAL — `placement_ref is None` is NOT unconditionally degenerate.** It is the deliberate C-004 strangler signal (`_resolve_placement_ref` returns `None` on `ActionContextError` OR when `artifact_placement is None`, meaning "keep the legacy meta-derived path"). The two legacy/flat arms MUST stay green: `None` + no `coord_branch` (`755` → `planning_branch`, flat/legacy) and `None` + coord mission + non-protected `planning_branch` (`790` → partition-aware split). Three shipped write-side tests (`test_implement_writeside.py:192/231/285`) and the #2533 regression (`test_implement.py:283`, `TestSoloPrBoundCoordMissionClaimPrecondition`) drive `placement_ref=None` expecting SUCCESS — an unconditional `None`→raise would red all of them and break real flat/legacy claims. The `None`-overload has 3 meanings (ActionContextError / no-placement-for-topology / torn-down-coord — the #2463 landmine); WP03's characterization gate pins the real flat/legacy None-at-this-seam behavior so the narrow condition is CONFIRMED, not guessed. Red-first: a narrow-triple claim now fails LOUDLY at the artifact-commit step (matching the status-commit step); the legacy/flat and coord-non-protected `None` claims still succeed. (#2648) | Planned |
| FR-003 | The `implement.py` god-functions (`_json_safe_output` S3776≈33, `_resolve_bookkeeping_transaction_identifiers` S3776≈16, `_run_recover_mode` S3776≈24) MUST be decomposed to reduce **Sonar S3776 cognitive complexity** with focused tests per extracted helper and NO behavior change. NOTE: all three already pass `ruff C901` (cyclomatic 4-10) — the target metric is S3776 (nesting-weighted, NOT measurable by ruff), so the local done-condition is the extraction + per-helper tests + behavior preservation, with S3776 confirmation advisory-post-merge (SC-003). Before extraction, characterization tests MUST pin the implicit invariants: in `_resolve_bookkeeping_transaction_identifiers` the primary-dir-first cascade order, ambiguous-handle RAISE, the `legacy-<slug>` mission-id fallback, and the mid8 precedence chain (meta-mid8 > `resolve_mid8` > `None`); in `_json_safe_output` the `console._file=None` reset, the `console.quiet` save/restore, the dual exception arms (`typer.Exit` re-raised verbatim vs bare `Exception` wrapped in `typer.Exit(1)`), and the exit_code-0 payload suppression + last-20-non-blank summary. (#2649) | Planned |
| FR-004 | The `tasks_move_task.py` hotspots (`_mt_commit_wp_file` S3776≈19, `_do_move_task` **21 parameters** → parameter-object, `_mt_uncheck_rollback_subtasks` S8572) MUST be decomposed with focused tests, NO behavior change, preserving the #2576 `rollback_uncheck_error` dual-handler contract (C-001) and the degrade-never-crash discipline of the placement-ref path. Local hard gate: `_do_move_task` parameter count ≤ 13 (currently 21 — this IS locally measurable and is the concrete acceptance for the param-object); the S3776 reductions are advisory-post-merge. Folds [#2604](https://github.com/Priivacy-ai/spec-kitty/issues/2604) (the `_mt_commit_wp_file` complexity ticket names the same function). (#2649) | Planned |
| FR-005 | The THREE partition-decision sites — `implement.py::_partition_files_for_commit` (write), `coordination/commit_router.py::_group_files_by_partition` (write), and `implement_cores.py::resolve_precondition_ref` (read) — MUST resolve their PRIMARY-vs-COORD partition through ONE shared authority: the **existing** `mission_runtime.is_coordination_artifact_residue_path` predicate (two sites already call it; the consolidation swaps `commit_router:404`'s divergent `kind_for_mission_file(file) or kind` classifier onto it). Scope is **classifier-only** — `commit_router` MUST keep `resolve_placement_only` for its actual COORD ref (`other_ref`); do NOT introduce a new cli-side `partition_of` wrapper (redundant with the mission_runtime predicate, and homing it in `cli/commands` would invert the `cli → coordination` layering — C-008) and do NOT edit `mission_runtime` (read-only). Separately, the read-side (`"HEAD"`) and write-side (`planning_branch`) primary-ref expression MUST be unified so they agree by construction, not by the HEAD==target invariant — a cli-local (Lane A) helper that does NOT touch `commit_router`. The consolidated authority routes `kind=None` / `meta.json` / unrecognized paths → PRIMARY (C-007), keeping the #2533 regression green. A structural test MUST assert the three named sites resolve partition through the one shared predicate (old per-site classifier deleted or forwarding; `commit_router` no longer consults `is_primary_artifact_kind(kind_for_mission_file(...))` for the split), so they cannot silently re-diverge. (#2650) | Planned |
| FR-006 | Before the FR-005 swap, a characterization gate MUST enumerate the three partition-decision sites and pin the concrete disagreement set: **every non-coord-residue path bundled under a coord-kind caller → PRIMARY** (the recognized-coord paths already agree between the residue predicate and the kind classifier; they disagree ONLY on `kind=None` paths — `meta.json`, primary-source paths, unrecognized — when the caller partition is COORD). Pin the intended UNIFIED post-consolidation placement (`kind=None`→PRIMARY) in tests (DM-D document-first). This gate MUST also characterize the `placement_ref is None` seam behavior for a real flat/legacy mission (confirming the FR-002 narrow-triple, not bare `None`, is the fail-close condition — #2463 None-overload). This WP is ordered ahead of the FR-005 consolidation WP. (#2650) | Planned |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | New/changed code meets the repo quality bar. | `ruff` + `mypy --strict` zero new issues; each touched function complexity ≤ 15; new branches covered by focused tests. | Planned |
| NFR-002 | The degod work is behavior-preserving, with a characterization floor. | Full existing `implement` / `move-task` / `coordination` suites pass unchanged; AND where a target function's branch is not already covered, a characterization test pinning current output is authored BEFORE extraction (not merely "suites pass"). | Planned |
| NFR-003 | The consolidation preserves the #2533-safe placement. | Every residue-vs-kind disagreement path (the `kind=None` set) is covered by a test asserting the PRIMARY direction wins (C-007); no silent placement change except the deliberately-chosen unified None-fallback direction, which is explicitly PRIMARY. | Planned |
| NFR-004 | The degod does not widen the public surface. | No net-new public/exported symbol from FR-003/FR-004 extractions; all extracted helpers remain module-private. | Planned |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | `_mt_uncheck_rollback_subtasks` (S8572) records the #2576 `rollback_uncheck_error` contract — the handler MUST NOT be blindly swapped to `logging.exception()`; any change adjudicated against that contract. | Active |
| C-002 | The two bugs (FR-001, FR-002) MUST be reproduced red-first through the pre-existing real entry points (`move-task` from a worktree cwd; the protected-branch write-side path) per DIRECTIVE_041. | Active |
| C-003 | File-linearized lanes (invariant: no file edited by two parallel lanes; each file serialized within one lane). *Shipped topology (superseded the original 2-lane text at /tasks to break a lane cycle):* **three** lanes — Lane A = `implement.py` + `implement_cores.py`; Lane B = `coordination/commit_router.py`; Lane C = `agent/tasks_move_task.py`. `commit_router.py` was split into its own lane because its FR-005 WP must run *after* the cli-side gate/ref-unification WP; the file-disjoint-per-lane invariant is unchanged. See tasks.md / lanes.json for the authoritative lane IDs. | Active |
| C-004 | #2648's fallback regression test and operator warning are enduring pins the FR-005 consolidation MUST keep green. The FR-002 WP is an explicit **dependency** of the FR-005 WP (guard-first ordering — FR-002 lands before FR-005). | Active |
| C-005 | Landing note: the WP touching `tasks_move_task.py`'s `_do_move_task` rebases after draft PR #2639 (which adds a parameter to it). The ≤13 parameter target is measured POST-rebase; prefer a parameter-object/dataclass extraction so #2639's added arg does not breach the ceiling. | Active |
| C-006 | Cross-lane symbol coupling: Lane B imports `_resolve_bookkeeping_transaction_identifiers` (5-tuple return), `_feature_dir_file_paths`, `_planning_artifact_source_dir` from Lane A (`tasks_move_task.py:1382-1384`) and the runtime call at `:1392` already consumes the 5-tuple. This breaks if the FR-003 degod reshapes those symbols **regardless of lane ordering** (the existing call is the consumer). The guard is therefore NOT mere sequencing — it is a **declared hard dependency edge** (the Lane-B degod WP `depends_on` the Lane-A WP that owns `_resolve_bookkeeping_transaction_identifiers`) **plus** a consumer-side import-contract test in that Lane-A WP asserting the 5-tuple + the two signatures from Lane B's perspective. Do NOT escalate to "move to a shared module" (that adds a net-new public surface — C-008). File-linearization does not cover symbol-contract coupling. | Active |
| C-007 | The FR-005 consolidated authority MUST route `kind=None` / `meta.json` / unrecognized paths → **PRIMARY partition** (the residue-predicate direction), where "PRIMARY" is the artifact **partition** resolved to the auto-detected `HEAD` / anchored `target_branch` — **NEVER the primary/default branch (`main`)**. Choosing the kind-classifier's caller-fallback direction would misroute `meta.json` to COORD and reintroduce #2533 — forbidden. The #2533 regression stays green. | Active |
| C-008 | FR-003/FR-004 extractions MUST remain module-private — no net-new public/exported symbol from the degod (Locality-of-Change). | Active |
| C-009 | FR-002/FR-005 MUST preserve the WP00/FR-004 anchored-primary-surface, fail-closed target resolution (`get_feature_target_branch` reads meta from the canonical checkout, raises `MissionMetaReadError` on corrupt meta) and MUST NOT reintroduce a silent fallback to the primary/default branch (`main`). On the **narrow-triple** `placement_ref is None` state (meta `coord_branch` truthy + protected `planning_branch`) the artifact-commit half **fail-closes** (`PlacementResolutionRequired`), matching the status half; it does not silently divert to coord. This does NOT extend to the legacy/flat strangler `None` paths (C-004), which retain their meta-derived commit. Two senses of "primary" must not be conflated: partition `kind=None`→PRIMARY resolves to the auto-detected `HEAD`/anchored `target_branch` (SAFE); target-branch `None`→primary/default branch (`main`) is the REMOVED WP00 default and must not creep back. | Active |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | An agent can run `move-task` end-to-end from a lane-worktree cwd with no repo-root-only workaround. |
| SC-002 | Zero silent PRIMARY-on-coord commits — the `767` fallback is removed; the narrow-triple state (`placement_ref is None` + meta `coord_branch` truthy + protected `planning_branch`) fails closed loudly (`PlacementResolutionRequired`) at the artifact-commit step, matching the status-commit step; and the legacy/flat + coord-non-protected `None` states still commit successfully (the 3 write-side tests + #2533 regression stay green). |
| SC-003 | Local hard gate (verifiable pre-merge): `ruff C901` stays green (already ≤ 15 on the six functions) AND `_do_move_task` parameters ≤ 13 (from 21, via param-object). The S3776 cognitive-complexity reductions are confirmed by SonarCloud post-merge (advisory — S3776 is not locally measurable by ruff). Behavior preservation + per-helper tests are the enforceable local acceptance for the degods. |
| SC-004 | Exactly one partition-aware placement authority for the three named claim/planning-commit sites — a structural test asserts they resolve partition through the one shared `is_coordination_artifact_residue_path` predicate (old per-site classifier deleted or forwarding; `commit_router` no longer consults the kind classifier for the split); read/write primary-ref agreement holds by construction with `kind=None`→PRIMARY. (Other predicate-consumers — `safe_commit_cmd`, `auto_rebase`, `merge/executor` — are out of scope; this SC does not over-claim "all partition decisions".) |
| SC-005 | Existing implement / move-task / coordination suites remain green; the two red-first bug repros are red-before / green-after. |

## Key Entities

- **Status surface resolver** — the seam that must resolve a mission's status
  location from the mission root regardless of cwd (FR-001).
- **The three partition-decision sites** (all consolidated by FR-005; all in Lane A) —
  `implement.py::_partition_files_for_commit` (write), `commit_router::_group_files_by_partition`
  (write), and `implement_cores.py::resolve_precondition_ref` (read). The read site owns
  the `"HEAD"` primary-ref expression; the write sites own `planning_branch`.
- **Partition classifiers (divergent — the crux of FR-005/C-007)** — `is_coordination_artifact_residue_path`
  (residue; `kind=None`→PRIMARY, #2533-safe) vs `kind_for_mission_file` + caller-fallback
  (kind; `kind=None`→caller partition, can be COORD). The consolidation MUST keep the PRIMARY direction.
- **Cross-lane imported symbols** — `_resolve_bookkeeping_transaction_identifiers` (5-tuple),
  `_feature_dir_file_paths`, `_planning_artifact_source_dir`: Lane-A degod targets that
  Lane B imports (C-006).

## Assumptions

- No active #2160/#2465 parallel work exists (operator-confirmed); the placement-seam
  slice (#2650) is safe to implement here.
- Draft PR #2639 may or may not land before this mission; C-005 covers the rebase.
- The #2533 write-side `767` fallback silently diverts PRIMARY artifacts to coord on the
  narrow-triple state; FR-002 DELETES it and fail-closes that specific state (matching the
  status half), while preserving the legacy/flat strangler `None` paths. This is a behavior
  change on the narrow triple only — confirmed dead-by-design for valid missions (debugger
  forensic + the status half already fail-closing on the same state).
- `placement_ref is None` is overloaded (C-004 strangler signal, not "degenerate" alone);
  WP03's characterization gate confirms the real flat/legacy None-at-this-seam behavior
  before FR-002/FR-005 rely on the narrow condition (#2463 None-overload landmine).

## Out of Scope

- Broader #2160 placement-seam work beyond consolidating the two named executors and
  unifying the primary-ref expression (the rest of #2160 remains its own epic).
- Any behavior change to move-task / commit semantics beyond the two named bug fixes
  (the degod and consolidation are behavior-preserving).
