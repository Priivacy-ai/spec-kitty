# Mission Specification: Single-Authority Topology Cleanup & Dedup

**Mission ID**: `01KVRJ6PC66DWS32M30YVPAE28` (mid8 `01KVRJ6P`)
**Slug**: `single-authority-topology-cleanup-01KVRJ6P`
**Type**: software-dev
**Branch**: `feat/single-authority-topology-cleanup`
**Status**: Specified
**Driver ticket**: [#2070](https://github.com/Priivacy-ai/spec-kitty/issues/2070)
**Predecessor (landed)**: `single-planning-surface-authority-01KVPR00` — the MissionTopology SSOT seam, PR [#2086](https://github.com/Priivacy-ai/spec-kitty/pull/2086) (merged to `main` 2026-06-22)

---

## Purpose

**TL;DR**: Remove the now-dead type/shim debt and consolidate the duplicated
mission-shape logic that the focused MissionTopology SSOT seam deliberately left
behind, while turning one band-aid removal into a correctness win that extends a
recent data-loss fix to un-migrated missions.

**Context**: PR #2086 (`single-planning-surface-authority`) closed the
coordination/primary planning-surface **death-spiral** structurally — it retired
*both* live `coordination_branch is None ⇒ FLATTENED` derivations
(`resolution.py` and `runtime_bridge.py`), routed all 9 `.kind is COORDINATION`
**decision** reads through the `routes_through_coordination(target)` predicate,
and made the read / surface / status paths read the **stored** `MissionTopology`
from `meta.json`. To stay reviewable, that mission carved its mechanical cleanup
and broader deduplication into this follow-on (constraint C-007 of the seam
mission, tracked as #2070).

This mission performs that cleanup. It is **behavior-neutral** with exactly
**one** intentional correctness *improvement* (FR-004 — topology absorption
extends the #2062 fix to un-backfilled missions). Everything else removes
vestigial constructs or collapses verbatim duplication without changing
observable behavior, verified by the differential-equivalence gate the seam
mission left in place.

---

## Background & Problem Statement

After the seam landed, the following debt is provably vestigial or duplicated.
Each item is grounded in live code and the four-comment research thread on #2070
(handover, alphonso+randy scoping corrections, paula+randy+alphonso dedup
research, and the operator's `topology=None` absorption refinement).

1. **`CommitTargetKind` is a 3-valued type encoding a 2-valued decision.** After
   the seam, `.kind` is read for a routing decision in exactly **one** place
   (`routes_through_coordination`, `context.py:131`); `safe_commit` reads only
   `.ref`. `PRIMARY` and `FLATTENED` are behaviorally identical at the decision
   point. The enum and its ~45 `src/` references (+ ~139 test references) are now
   pure ceremony around a single boolean.

2. **`CommitTargetKind.FLATTENED` is write-only dead.** There are zero
   `is/== FLATTENED` decision reads in `src/`; it is produced at three sites
   (`resolution.py:156`, `runtime_bridge.py:241`, `upgrade.py:214`) and consumed
   by no decision. (The separate `flattened` **provenance meta-flag** in
   `meta.json` survives — and `FLATTENED.value == "flattened"` string-collides
   with it, so deletion must be symbol-verified, not grep-verified.)

3. **The `ensure_topology` persist shim is dead.** Zero `src/` callers remain —
   minting inlines `classify_topology`, and backfill uses
   `backfill_mission_topology`. Its tests must be retargeted onto the live
   `read_topology` + backfill paths.

4. **Scattered `topology is None` legacy husk-arms remain as band-aids.** At
   least ~8 sites (`_read_path_resolver.py:148/361/724/895`, `surface_resolver`,
   `candidate_feature_dir`) still branch on `topology is None` and fall back to
   consulting the coordination-branch *husk* on disk. Their own comments admit
   they are bypassed whenever a stored topology exists. They are the residual of
   the very desync the seam closed — and on an **un-backfilled flattened
   mission** they can still leak onto the buggy stale-coord path (#2062), because
   such a mission reaches the resolver with `topology=None`.

5. **One question is answered by six predicates and four verbatim frozensets
   (cluster C1).** The set `{COORD, LANES_WITH_COORD}` is defined verbatim 4×
   (`resolution.py:138`, `surface_resolver.py:91`, `runtime_bridge.py:78`, inline
   `status_transition.py:590`); six predicates
   (`destination_kind_for_topology`, `_topology_uses_coord_surface`,
   `_topology_routes_through_coord`, `_mission_routes_through_coordination`,
   `_read_contract_routes_through_coordination`, `routes_through_coordination`)
   all answer "does this topology route through coordination?".

6. **`meta.json` reading is spelled ~45 ways with 4 drifting contracts (cluster
   C2).** `load_meta` appears 8 named + ~37 inline times, with four divergent
   missing/malformed behaviors (`None`+raise / raise `TaskCliError` / return `{}`
   / `MissingIdentityError`). This is the operator's "shims-to-shims" intuition
   made concrete.

7. **A near-dead shadow module duplicates 18 helpers (cluster C6).**
   `scripts/tasks/task_helpers.py` (481 LOC, on the dead-module allowlist)
   re-implements (not delegates) 18 identically-named functions from
   `task_utils/support.py`.

8. **Two `accept`-gate bugs strand finished missions (#2084 P0, #2085 P1).**
   `accept`'s dirty-tree check is **topology-blind**: it never consults
   `is_coordination_artifact_residue_path`, so it blocks on spec-kitty's *own*
   coordination-owned residue (`tasks/WP*.md`, `status.events.jsonl`) on the
   primary checkout under coordination topology (#2084). Separately, `accept`
   demands ticked `tasks.md` checkboxes that an orchestrated mission never writes,
   even when every WP is `approved`/`done` (#2085a). Both are materializations of
   the same topology-blindness / redundant-bookkeeping the SSOT now lets us fix.
   The `accept` dirty gate is **not the only** topology-blind residue gate: the
   merge `advance_branch_ref` callers omit the `coord_owned_filenames` allowance
   and the post-merge invariant hardcodes a third verbatim copy of the residue
   set, leaking coordination-worktree paths into the target index (#1887). The
   recognized-residue knowledge is hardcoded in ≥3 independent places — a
   one-question-N-answers duplication of the same contract.

---

## In Scope

- `CommitTargetKind` **type** eradication; collapse `.kind` into a topology→bool
  projection (FR-001).
- Delete `CommitTargetKind.FLATTENED` (FR-002).
- Remove the `ensure_topology` persist shim (FR-003).
- `topology=None` absorption at the read-path boundary + collapse of the ~8
  legacy husk-arms (FR-004) — the one correctness improvement.
- Cluster C1: coord-routing predicate + frozenset consolidation (FR-005).
- Cluster C2: `meta.json` reader unification (FR-006).
- Cluster C6: `task_helpers` shadow-module retirement (FR-007).
- Fold #2084: topology-aware `accept` dirty-gate residue allowance (FR-008).
- Fold #2085a: `accept` unchecked-tasks gate derives completion from WP terminal
  status (FR-009).
- Fold #1887 + sweep the #2084 sibling gates: every working-tree dirty gate that
  can observe coordination residue (the merge `advance_branch_ref` callers, the
  post-merge invariant) consults the single canonical residue authority (FR-012).
- Fold #1891 (conditional): `CommitResult` is JSON-serializable on the
  `agent … --json` surface, riding FR-001's value-object cleanup (FR-013).
- The verification scaffolding that makes the above non-fakeable (FR-010,
  FR-011).

## Out of Scope

- Any change to observable resolution behavior on **backfilled** missions (the
  whole mission is behavior-neutral there; FR-004's improvement applies only to
  the un-backfilled path).
- #2085's **acceptance-matrix** gate — that is genuine verification evidence, not
  redundant bookkeeping, and is not auto-satisfiable (C-010).
- The load-bearing guards enumerated in Constraints C-001..C-007 — these are
  preserved deliberately and must not be "deduplicated away".
- Any new resolver, auditor, or parallel topology path — adoption only (C-009).
- The **write-side** death-spiral twin (`coordination/transaction.py`
  `_is_legacy_mission`, `lanes/worktree_allocator.py` lane-parent selection) that
  re-infers shape from `coordination_branch` absence — the write-path mirror of
  FR-004. Folding write-path correctness into this behavior-neutral read-path
  mission would break neutrality; it is **carved to epic #1716** (C-012).
- Version assignment (C-008).

---

## User Scenarios & Testing

**Primary actor**: a spec-kitty maintainer / contributor agent running the
mission lifecycle and the test/architectural suite.

### Scenario 1 — Behavior-neutral type eradication (FR-001/FR-002)
- **Given** a mission of any topology on any branch,
- **When** a commit is routed (`safe_commit` / `spec_commit` / status emission),
- **Then** the destination ref and routing decision are byte-identical to
  pre-mission behavior, with `.kind` no longer consulted and the
  `CommitTargetKind` enum removed from `src/`.
- **Acceptance**: the differential-equivalence gate
  (`tests/missions/test_surface_resolution_equivalence.py`) is green across every
  `(topology × transient)` cell; an AST/symbol scan proves zero `CommitTargetKind`
  references remain in `src/` and nothing serializes the former `FLATTENED.value`.

### Scenario 2 — Correctness win for an un-backfilled flattened mission (FR-004)
- **Given** a flattened mission whose `meta.json` carries **no** `topology` key
  (legacy / un-migrated) and has a stale coordination husk on disk,
- **When** its planning surface is resolved,
- **Then** the boundary classifies-on-read to `SINGLE_BRANCH`/`LANES` →
  PRIMARY (the #2062 fix), instead of dropping into the legacy husk arm that can
  leak to the stale-coord path.
- **Acceptance**: a live differential test proves *classify-on-read
  (un-backfilled)* ≡ *backfill-then-read (backfilled)* across every
  `(topology × transient)` cell, and the C-006 transient probe
  (`probe_coord_state` EMPTY/DELETED) still handles the create-window (#1718) and
  coord-deleted (#1848) cases unchanged.

### Scenario 3 — A finished coordination-topology mission passes `accept` (FR-008)
- **Given** a completed coordination-topology mission whose primary checkout
  shows only spec-kitty's own coordination residue (`tasks/WP*.md`,
  `status.events.jsonl`),
- **When** the maintainer runs `spec-kitty accept`,
- **Then** the dirty-tree check ignores that recognized coordination residue and
  proceeds, **but still blocks** on author-owned files (e.g. `spec.md`) and on a
  *flat* mission's real primary artifacts.
- **Acceptance**: a test fixture under coordination topology with only residue
  passes the dirty gate; the same residue paths under a flat mission still block.

### Scenario 4 — An orchestrated mission passes the unchecked-tasks gate (FR-009)
- **Given** a mission whose WPs are all `approved`/`done` but whose `tasks.md`
  checkboxes were never ticked (orchestrated flow),
- **When** the maintainer runs `spec-kitty accept`,
- **Then** completion is derived from WP terminal status and the unchecked-tasks
  gate passes (the acceptance-matrix gate is unaffected and still applies).

### Scenario 5 — The dedup is real and bounded (FR-005/FR-006/FR-007)
- **Given** the consolidated predicate/frozenset (C1), polymorphic `load_meta`
  (C2), and re-exported `task_helpers` (C6),
- **When** the full suite runs,
- **Then** behavior is unchanged, net `src/`+`scripts/` LOC drops materially, and
  the load-bearing KEEP set (C-001..C-007) is provably intact.

### Scenario 6 — Merge does not leak coordination residue, residue authority is single (FR-012, #1887)
- **Given** a coordination-topology mission being merged, whose checked-out
  worktree carries coordination status residue,
- **When** `spec-kitty merge` advances the branch ref and runs its post-merge
  invariant,
- **Then** the ff-advance does not raise `RefAdvanceDirtyWorktreeError` over that
  recognized residue, no `.worktrees/`-rooted paths are staged into the target
  index, and every dirty gate (accept, post-merge invariant, ref-advance) draws
  the recognized-residue set from the single `is_coordination_artifact_residue_path`
  / `COORD_OWNED_STATUS_FILES` authority — no gate carries its own literal.
- **Acceptance**: a test proves a post-write ff-advance with coordination residue
  on a checked-out worktree succeeds; a grep/AST check finds no second hardcoded
  residue literal across the three gates.

### Edge cases
- **Unreadable / malformed `meta.json`**: absorption needs readable meta; the
  corrupt-meta case stays a small typed-fallback (C-004) — FR-004 collapses the
  *absent-field* arms, not the unreadable-meta arm.
- **`FLATTENED.value` string-collision** with the surviving `flattened`
  provenance flag — symbol verification, not grep (NFR-003).
- **`runtime_bridge` parallel classifier** — removing `.kind` must preserve its
  `worktree_root` selection (C-011 risk).
- **Dogfooding hazard**: this mission's own coordination topology exercises the
  paths under cleanup; the seam fix should make the loop clean, which is itself a
  live signal.

---

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Eradicate the `CommitTargetKind` **type**: collapse the single routing decision to a pure `topology → routes_through_coordination(topology) → bool` projection, remove the `.kind` attribute from the `CommitTarget` value object (kept as a ref-only carrier per C-007), and delete the enum and its ~45 `src/` references (+ ~139 test references) across the categorized footprint (2 topology-derived, 11 mechanical `kind=PRIMARY` drop-arg, 3 `kind=COORDINATION` needs-care, 2 `runtime_bridge` parallel-classifier preserving `worktree_root`, plus imports/annotations/enum). | Defined |
| FR-002 | Delete `CommitTargetKind.FLATTENED`, having symbol-verified it is write-only dead (zero decision reads in `src/`; producers emit PRIMARY); preserve the separate `flattened` provenance meta-flag and confirm nothing serializes the former enum `.value`. | Defined |
| FR-003 | Remove the dead `ensure_topology` persist shim (zero `src/` callers) and retarget its tests onto the live `read_topology` reader + `backfill_mission_topology` path. | Defined |
| FR-004 | Absorb `topology=None` at the read-path boundary: acquire topology via the absorbing API (`read_topology` / a pure `classify_from_meta(meta, feature_dir)`) and thread a concrete, non-optional `MissionTopology` downstream, making the ~8 scattered `topology is None` husk-arms dead and collapsing them. This extends the #2062 fix to un-backfilled flattened missions and dissolves the backfill-everything migration gate (backfill becomes a perf optimization, not a precondition), while keeping the unreadable-meta typed-fallback (C-004). | Defined |
| FR-005 | Consolidate cluster C1: collapse the six coord-routing predicates and the four verbatim `{COORD, LANES_WITH_COORD}` frozensets — currently spelled under two distinct constant names (`_COORD_ROUTING_TOPOLOGIES`, `_COORD_SURFACE_TOPOLOGIES`) plus an inline literal — to ONE pure `routes_through_coordination(topology)` and ONE shared frozenset constant (a name reconciliation, not a trivial single-rename). | Defined |
| FR-006 | Consolidate cluster C2: collapse the `meta.json`→dict read sites to ONE polymorphic `load_meta(dir, *, allow_missing, on_malformed)` plus 2 genuinely-distinct adapters. **Footprint re-baselined (squad-verified): ≥66 named `load_meta` call sites + ~107 inline `json.loads(meta_path)` reads across ~20 named wrappers, with 4–6 drifting missing/malformed contracts — materially larger than the original ~45 estimate; treat the count as a floor and re-confirm in planning.** | Defined |
| FR-007 | Retire cluster C6: reduce `scripts/tasks/task_helpers.py` to a thin re-export of the canonical `task_utils/support.py` (eliminating the 18 duplicated independent implementations), honoring the `acceptance_support` compat contract. | Defined |
| FR-008 | Make the `accept` dirty-tree gate topology-aware (#2084): gate the dirty check (`acceptance/__init__.py`, `ACCEPT_OWNED_PATHS`) so that under **actual** coordination topology it ignores recognized coordination residue via `is_coordination_artifact_residue_path` (`mission_runtime/artifacts.py`) — converging on the reference-correct pattern already at `agent/mission.py:862` (`_enforce_analysis_report_write_preflight`, which gates on `routes_through_coordination` + the canonical residue predicate) rather than widening the hardcoded frozenset — while still blocking author-owned files and a flat mission's real primary artifacts. | Defined |
| FR-009 | Derive unchecked-tasks completion from WP terminal status (#2085a): when every WP is `approved`/`done`, the `accept` unchecked-tasks gate (`_find_unchecked_tasks`) is satisfied without demanding ticked `tasks.md` checkboxes; the acceptance-matrix gate is unchanged (C-010). | Defined |
| FR-010 | Extend the differential-equivalence gate (`tests/missions/test_surface_resolution_equivalence.py`) with a classify-on-read ≡ backfill-then-read cell across every `(topology × transient)` combination, proving FR-004's absorption is behavior-equivalent on backfilled missions and correctness-improving on un-backfilled ones. The new cell MUST be asserted **green** — not parked behind the existing `_XFAIL_*_OUT_OF_SCOPE` markers (those guard the orthogonal C-005 transient probes). | Defined |
| FR-011 | Provide a non-fakeable AST/symbol architectural guard that fails CI if any `CommitTargetKind` reference (or a serialization of the former `FLATTENED.value`) is reintroduced into `src/`, binding the eradication to a test (canonical-seams #1868), reusing the existing `tests/architectural/` AST infrastructure (`audit.py`, `_ratchet_keys.py`) per C-009. | Defined |
| FR-012 | Generalize the coordination-residue authority across **all** working-tree dirty gates (#1887 + the #2084 siblings), not just `accept`: the three merge `advance_branch_ref(...)` callers (`cli/commands/merge.py:1284`, `lanes/merge.py:458`, `lanes/merge.py:485`) pass `coord_owned_filenames=COORD_OWNED_STATUS_FILES`; the post-merge invariant (`cli/commands/merge.py:~2625`) consults `is_coordination_artifact_residue_path` instead of its own hardcoded `{status.events.jsonl, status.json, meta.json}` literal; and the lane-auto-rebase conflict arm (`lanes/auto_rebase.py:154` `_is_coordination_owned_artifact`, the 4th site surfaced by the post-plan brownfield squad) converges onto the canonical authority instead of its **drifting** subset `{tasks.md, lanes.json, acceptance-matrix.json}` (which omits `plan.md`/`issue-matrix.md`/`analysis-report.md`). The recognized-residue set is expressed ONCE (`is_coordination_artifact_residue_path` / `_COORD_RESIDUE_FILENAMES`) and consumed by accept, the post-merge invariant, ref-advance, and the auto-rebase arm — no gate carries its own residue literal. | Defined |
| FR-013 | (Conditional fold of #1891) Ensure the `CommitResult` value object returned on the `agent … --json` surface (at minimum `agent tasks map-requirements --json`) is JSON-serializable, riding FR-001's `CommitTarget`/`CommitResult` value-object cleanup. **Gated**: in scope only if FR-001's type rework touches `CommitResult` construction; if planning finds `CommitResult` disjoint from the `.kind` removal, this carves to a standalone fix (recorded, not silently dropped). The separate "`--json` flag missing from `agent action implement`" half of #1891 is OUT of scope. | Defined |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | Behavior neutrality on backfilled missions: zero correctness regression. | The full `tests/architectural/` suite and the differential-equivalence gate pass on the merged branch (pre-merge sweep), with 0 new failures attributable to this mission. | Defined |
| NFR-002 | The single correctness improvement (FR-004) is itself proven by a live repro, not static reading. | A live un-backfilled-flattened-mission test demonstrates the resolved surface is PRIMARY (not the stale-coord husk) before and proves it after; the test fails on the pre-FR-004 code. | Defined |
| NFR-003 | Deletion sweeps are symbol/AST-verified, never grep-only. | FR-002/FR-011 use AST or symbol resolution; a planted `FLATTENED.value` string literal does not produce a false "dead" verdict. | Defined |
| NFR-004 | The deduplication produces a material, measurable net reduction. | Net `src/`+`scripts/`+`tests/` LOC delta is a reduction; the original ~750–1,000 LOC band is a **floor** (the C2 `meta.json` footprint re-baselined upward per FR-006, so realized reduction is expected to exceed it); reported in the PR body with the realized per-cluster counts. | Defined |
| NFR-005 | Every consolidation preserves the documented load-bearing KEEP set. | A reviewer can map each KEEP item (C-001..C-007) to an unchanged or test-pinned code site post-mission; none is collapsed. | Defined |

### Constraints

| ID | Constraint | Rationale |
|----|------------|-----------|
| C-001 | KEEP the `surface_resolver` husk short-circuit (`:667-678`, `_husk_is_authoritative_surface`). | Load-bearing #2062 defense for the worktree-feature-dir-passed-in entry (distinct from the candidate gate that defends the bare/mid8-handle entry); the `df79f76f4` data-loss fix lives here. |
| C-002 | KEEP the genuine-fallback relays at `status_transition.py:599`, `surface_resolver.py:562`, `resolution.py:765`. | Each reads stored topology first and relays via `classify_topology` only on the exception arm — the un-backfilled-legacy migration contract; NOT reducible. |
| C-003 | KEEP the 5-hop feature-dir read path (`candidate_feature_dir_for_mission`→…→`resolve_handle_to_read_path`). | Each hop is a distinct ticket-anchored guard (#1718/#1589/#1848/#2062); flattening reverts fixes. |
| C-004 | KEEP the corrupt/unreadable-meta exception arm. | FR-004 absorbs the absent-field `None`-arms, NOT the unreadable-meta fallback (which cannot classify without readable meta). |
| C-005 | KEEP the create-window (#1718) and coord-deleted (#1848) transient probes (`probe_coord_state` EMPTY/DELETED). | Orthogonal to shape — the `topology is None` arm was a shape standin, not a transient one. |
| C-006 | KEEP the `flattened` provenance meta-flag in `meta.json`. | Distinct from the deleted `CommitTargetKind.FLATTENED` enum; provenance is still recorded. |
| C-007 | KEEP `CommitTarget` as a ref-only value object. | Only `.kind` is removed; the ref carrier and its construction sites remain. |
| C-008 | No version prescription. | The PO assigns the patch/minor at release. |
| C-009 | Canonical-sources discipline: adoption only, reuse the existing differential gate and SSOT API. | Do not build a parallel resolver, auditor, or topology path; do not improvise around the SSOT. |
| C-010 | The #2085 acceptance-matrix gate stays in place and is OUT of scope. | It is genuine verification evidence, not redundant bookkeeping — not auto-satisfiable. |
| C-011 | PRESERVE the `runtime_bridge` parallel-classifier `worktree_root` selection while removing `.kind`. | Risk site: the parallel classifier still selects a worktree root that the `.kind` removal must not disturb. |
| C-012 | CARVE the write-side death-spiral twin to epic #1716: `coordination/transaction.py:200/230` (`_is_legacy_mission` re-inferring shape from `coordination_branch` absence) and `lanes/worktree_allocator.py:159` (lane-parent selection by branch presence). | These are the **write-path** mirror of FR-004's read-side absorption. Folding write-path correctness here would break the behavior-neutral contract and is non-trivial-risk; recorded as considered-and-carved (not missed) so #1716 picks it up. |

---

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | `CommitTargetKind` is absent from `src/`; the single coordination-routing decision is answered by one predicate over stored topology, and a CI guard fails on reintroduction. |
| SC-002 | A maintainer can complete a coordination-topology mission and an orchestrated mission through `spec-kitty accept` **and `spec-kitty merge`** without hand-cleaning spec-kitty's own residue or back-filling `tasks.md` checkboxes, and the merge does not leak coordination-worktree residue into the target branch (#1887); the recognized-residue set lives in exactly one place. |
| SC-003 | An un-backfilled flattened mission resolves to its primary planning surface (not a stale coordination husk), with a live test proving the improvement and the migration backfill no longer a precondition for correctness. |
| SC-004 | The duplicated coord-routing predicates/frozensets (C1), `meta.json` readers (C2), and `task_helpers` shadow module (C6) are each reduced to a single authority, with a measurable net LOC reduction reported in the PR body. |
| SC-005 | The full `tests/architectural/` suite and the differential-equivalence gate pass on the merged branch, and every load-bearing KEEP item (C-001..C-007) is demonstrably intact. |

---

## Dependencies & Assumptions

- **Depends on** the landed seam mission (`single-planning-surface-authority-01KVPR00`, PR #2086): the stored `MissionTopology`, `routes_through_coordination`, `read_topology`/`classify_topology`, and the differential-equivalence gate all exist on `main`.
- **Assumes** the seam's behavior-neutrality claim holds (the ~14 external `resolve_placement_only`/`resolve_action_context` callers are already SSOT-fed; the only WP-bearing adoption site is the `resolve_action_context` WP branch at `resolution.py:1164-1194`, per alphonso+randy — a NEEDS-CARE site, not a sweep).
- **Assumes** `is_coordination_artifact_residue_path` (`mission_runtime/artifacts.py`) already encodes the recognized-residue contract that FR-008 wires into the `accept` gate.
- **Risk**: this mission's own coordination topology dogfoods the paths under cleanup; the seam fix should keep the loop clean — friction here is itself a finding.

---

## Tracked Issues (issue-matrix companion)

Driver and folds (see `issue-matrix.md` for per-issue verdicts):
#2070 (driver), #2084 (P0 fold → FR-008), #2085 (P1 fold → FR-009), #1887 (merge-side residue-gate fold → FR-012), #1891 (conditional JSON-serialization fold → FR-013), #2069 (design predecessor — fixed by #2086), and epic facets #1716 / #2007 / #1619; #1868 (canonical seams — the FR-011 guard binds it). The write-side death-spiral twin is carved to #1716 (C-012). Not parented under any meta rollup.
