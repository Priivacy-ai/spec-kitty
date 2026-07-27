# Phase 0 Research: Coord/Primary Partition Regression Lock

**Mission**: `coord-primary-partition-lock-01KWZ46V` · branch `design/coord-primary-partition-lock`
**Source**: pre-spec 4-scout investigation + post-spec 3-lens scope-check squad
(architect-alphonso · paula-patterns · planner-priti), 2026-07-07.

This document consolidates the evidence that shaped the spec. Every decision below
is grounded in a code citation, not intent.

## D1 — The placement SSOT already exists; complete + lock it, do not build

- **Decision**: Formalize the placement **seam** as the thin public authority over the
  existing `resolve_action_context` derivation root; do not introduce a new resolver.
- **Rationale**: The kind→partition SSOT (`_PRIMARY_ARTIFACT_KINDS` /
  `_PLACEMENT_ARTIFACT_KINDS` + `artifact_home_for()` / `MissionArtifactHome`,
  `src/mission_runtime/artifacts.py:91,113,175`) and the write projection
  `resolve_placement_only(...) -> CommitTarget` (`resolution.py:1130`) already exist.
  The read side is ~90% routed through `_read_path_resolver.py` /
  `surface_resolver.py`. Building a parallel authority would itself violate C-001 and
  Directive-044 (canonical sources / no shadow paths).
- **Alternatives considered**: (a) net-new placement API — rejected (forks the SSOT);
  (b) leave the leaf resolvers un-unified — rejected (the duplication is the defect).

## D2 — The partition is settled (planning→primary); this mission ratifies it

- **Decision**: Lock the existing kind→partition mapping; do not change any kind's home.
- **Rationale**: PRs #2106/#2113 established planning-on-primary and superseded #1716's
  original "materialize-coord-at-create / planning→coord" premise (merge commits
  `7868982a1`, `d5989cbd3`, `02cb2176c`). Operator confirmed the canonical partition:
  coord = lifecycle (status/notes/trace/issue-matrix/move-task); primary = stable
  planning (spec/plan/WP outlines); no-coordination topology → all primary.
- **Alternatives considered**: re-open the coord-authority model — rejected (settled,
  and reversing it regresses shipped behavior).

## D3 — Topology is a 2×2 grid, routed by a predicate

- **Decision**: Bind all coord-routing to `routes_through_coordination(stored_topology)`
  over `{COORD, LANES_WITH_COORD}`; forbid inline `topology == COORD` /
  `coordination_branch is not None`.
- **Rationale**: `MissionTopology` = `SINGLE_BRANCH | LANES | COORD | LANES_WITH_COORD`
  (`mission_runtime/context.py:64-134`). A binary coord/single_branch view (the spec's
  first draft) silently mis-handles `LANES_WITH_COORD` and `LANES`. `FLATTENED` is a
  provenance flag, not a topology value → read **stored** `meta.json` topology, never
  the on-disk `-coord` husk (guarded by `_husk_is_authoritative_surface`,
  `coordination/surface_resolver.py:504-537`). → FR-003, FR-012, NFR-003.

## D4 — Kind inventory: 14 members, locked as frozensets

- **Decision**: FR-002 locks membership of the two frozensets verbatim rather than a
  prose kind list.
- **Rationale**: `MissionArtifactKind` has 14 members (`artifacts.py:25-50`); the spec's
  first draft named 8 and invented three (`in-flight-note`/`trace`/`move-task`) that are
  not enum members but operations projected onto `STATUS_STATE` / self-bookkeeping.
  `ACCEPTANCE_MATRIX` and `ANALYSIS_REPORT` are coordination-partition kinds that must
  be represented.

## D5 — The unowned highest-leverage target is the create-time write root

- **Decision**: Strangle `core/mission_creation.py:176` (`_commit_feature_file`) first.
- **Rationale**: It commits the spec (a primary/planning artifact) via
  `CommitTarget(ref=current_branch)` — deriving the destination from the current
  checkout. This is the create-time split-brain root, it is owned by no sibling mission,
  and its grammar is **not** caught by the existing ratchet (see D7). Highest leverage,
  lowest coordination cost.

## D6 — The remaining write bypasses are sibling-owned; this mission is authoritative

- **Decision** (operator): Strangle the sibling-owned sites too — `implement.py:885/1462`,
  `workflow.py:487/503/549/1694`, and the `tasks.py` move-task/mark-status cluster.
  Where `coord-authority-gate-hardening-01KW4T2F` / `implement-loop-coord-authority-01KW2E7A`
  collide on the shared seam or ratchet substrate, **this mission's routing wins and they
  rebase onto it** (operator sequences merges). → C-005.
- **Rationale**: SC-001 ("0 bypassing sites") is unachievable if these are fenced off;
  the operator chose authority over deferral. Note: **PR #2438 (review-regression-gate)
  just landed on `tasks.py`/`tasks_move_task.py`** (rebased in) — the strangle must
  account for the new move-task gate code on that surface.
- **Alternatives considered**: descope to non-sibling surfaces + hand-off (rejected by
  operator); hard-sequence after siblings (rejected — this mission is the authority).

## D7 — Extend the existing ratchet; it has a blind spot

- **Decision**: Extend `tests/architectural/test_no_write_side_rederivation.py` with a
  `CommitTarget(ref=<checkout>)` grammar (FR-011); pin the write-side line allow-list
  baseline (seed = 1: `coordination/status_transition.py:343`) and shrink it; expand the
  adopted-module set as each surface is strangled; shrink `coord_authority_baseline` in
  `resolution_gate_allowlist.yaml` from 7 toward its permanent floor.
- **Rationale**: The scanner today matches three grammars (`parent.parent` root-walks,
  `mission_id[:8]` recompute, `coord_branch or _current_branch`) but **not**
  `CommitTarget(ref=<checkout>)` — exactly where D5/D6 bypasses live. Without the grammar
  the strangle is unverifiable. Building a second ratchet would be a shadow gate.

## D8 — Bugs #2091/#2250 are mostly shipped; one real residual remains

- **Decision**: #2091 → add the missing empty-`mid8` guard at the **composition seam**
  `CoordinationWorkspace` (`coordination/workspace.py:161-226`) red-first; verify the
  upstream `runtime_bridge.py:223-235` guard remains. #2250 → verify + regression-lock
  the shipped fix (`_read_path_resolver.py:697-706`, test `test_coord_never_created.py`);
  distinguish `never-created` / `DELETED` / `UNMATERIALIZED`. Close both issues.
- **Rationale**: Priti found both fixed on main (`48341cab5`, `f57c6e616`); Paula found
  the composition seam itself still lacks the guard (upstream is belt-and-suspenders).
  So #2091 has a genuine defense-in-depth residual; #2250 is verify-only (not red-first).

## D9 — Characterization test scope

- **Decision**: FR-009 walks `create → commit spec → setup-plan → tasks status →
  decision verify`, includes ≥1 lifecycle **mutation** through the seam, and asserts
  CWD-independent, partition-correct resolution across coord and non-coord topologies;
  authored **after** PR #2429 lands (C-007, it extends `resolve_planning_read_dir`).
- **Rationale**: The read-only golden path misses write/mutation fidelity — the exact
  place split-brain reappears. #2429 is a soft pre-req (timing only); it has not landed
  as of this rebase.

## D10 — Roadmap correction (operator decision)

- **Decision**: FR-010 rewrites `docs/release-goals/3.2.x.md` to move the **entire**
  #1878 write-side strangler (placement-routing **and** commit/protected-branch
  durability) into 3.2.x/G2.
- **Rationale**: Operator directive supersedes the roadmap's current 3.3.x placement of
  the durability slice. This mission delivers the placement-routing slice; the
  commit-durability slice becomes a 3.2.x fast-follow mission (Out of Scope here).

## D11 — Forbidden-fallback resolution (post-plan brownfield finding)

- **Decision**: The two live `if …is None: CommitTarget(ref=<checkout>)` legacy fallbacks
  (`implement.py:672 → :1467` `_resolve_placement_ref`; `mission_record_analysis.py:80`
  `_resolve_record_analysis_placement_ref`) are resolved **fail-closed / require-canonical**:
  replace the None→legacy-checkout fallback with a structured error; support genuinely-legacy
  missions via migration/backfill, not a silent runtime fallback.
- **Rationale**: These violate the no-legacy-resolver-paths standing order (forbidden
  `if id is None: <fallback>`). The inline "C-004 never break the lifecycle" justification does
  not license a silent shadow path — it is exactly the `CommitTarget(ref=<checkout>)` grammar the
  IC-04 ratchet (D7) must catch. `mission_record_analysis.py:80` is also the **second CommitTarget
  producer** the squad missed; SC-001 ("0 bypassing sites") is unmet if it is fenced off.
- **Alternatives considered**: keep the fallback with a documented ratchet exemption — rejected
  (perpetuates the anti-pattern the mission exists to kill).

## D12 — Additional census corrections (post-plan brownfield finding)

- The 4 `_planning_read_dir` copies already delegate to the seam → IC-01 consolidation is DRY-only.
- IC-04 EXTENDS the shipped `test_write_surface_placement_guard.py` (#2198 CLOSED), not a new gate.
- Campsite: `_planning_commit_worktree` (`commit_router.py:475`) name is stale post-D2; rename,
  keep its PRIMARY-guard `raise`. #2404 (accept reads acceptance-matrix from stale coord) folds
  lite into the IC-06 char test as an ACCEPTANCE_MATRIX read-partition assertion.

## D13 — Post-tasks squad + post-rebase drift remediations (2026-07-07)

A 3-lens post-tasks squad (planner-priti, python-pedro, architect-alphonso), run after rebasing
onto upstream/main (8 commits: #2032 session-reaper, #2283 CI-parity), reshaped the tasks:

- **FR-005 scoped down (Priti H1 / Alphonso H-2):** this mission routes the ~5 *named checkout-derived
  write* bypasses; the broad kind-blind `resolve_feature_dir_for_mission` read-site sweep (~71 sites /
  18 write) + the `coord_authority_baseline` 7→2 drain are a separate strangle → **#2453**. SC-001/SC-005
  reworded; WP07 keeps `coord_authority` at 7.
- **More checkout-derived fallbacks than D11 named:** a third (`orchestrator_api/commands.py:1451`) and the
  BookkeepingTransaction legacy HEAD override (`transaction.py:751-771`) — both **#2453**, flagged VISIBLE
  by WP07's grammar (allow-listed with a `tracked` rationale), not silent.
- **RETROSPECTIVE parallel authority (Alphonso H-1):** WP01's seam delegates its RETROSPECTIVE leg to the
  existing `resolve_retrospective_home` (#2119) — no second authority; WP07 allow-lists it.
- **FR-012 husk guard subsumed (all lenses):** `_husk_is_authoritative_surface` shipped by #2062 (pre-merge-base);
  WP06 T030 → verify + flatten-regression only (re-implementing = C-001 fork).
- **WP08 #2429 gate likely moot (Priti M2):** `resolve_planning_read_dir` already kind-aware; verify, don't hold.
- **Ratchet seed re-anchored 343→347** (#1842 tombstone hook); `test_wp05_write_target_drain.py` added to WP07 owned_files.
- **Line drift** corrected to symbol-anchored (implement.py:886, workflow ~502/552/1699, empty-except ~1608).

## Open coordination note

The shared ratchet substrate (`resolution_gate_allowlist.yaml`, the floor scalars in
`test_resolution_authority_gates.py`) is edited by the active sibling
`coord-authority-gate-hardening-01KW4T2F`. Per C-005 this mission is authoritative;
the operator sequences the merges so siblings rebase onto our baseline changes.
