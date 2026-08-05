---
work_package_id: WP04
title: The REVIEW_CYCLE kind and its plumbing
dependencies:
- WP01
requirement_refs:
- FR-023
- NFR-002
- NFR-003
planning_base_branch: pr/review-verdict-write-integrity-01KZ1CGF
merge_target_branch: pr/review-verdict-write-integrity-01KZ1CGF
branch_strategy: Planning artifacts for this mission were generated on pr/review-verdict-write-integrity-01KZ1CGF. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/review-verdict-write-integrity-01KZ1CGF unless the human explicitly redirects the landing branch.
created_at: '2026-08-03T08:13:56Z'
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
- T018
history:
- at: '2026-08-03T08:13:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: architect-alphonso
authoritative_surface: src/mission_runtime/
create_intent:
- tests/architectural/census/verdict_seam_IC04.yaml
execution_mode: code_change
model: ''
owned_files:
- src/mission_runtime/artifacts.py
- src/mission_runtime/resolution.py
- src/specify_cli/coordination/commit_router.py
- tests/architectural/test_write_surface_placement_guard.py
- tests/architectural/test_merge_reconciliation_class_guard.py
- tests/architectural/census/verdict_seam_IC04.yaml
- tests/coordination/test_analysis_report_rehome.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP04 - The REVIEW_CYCLE kind and its plumbing

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load architect-alphonso
```

## Objective

Give review-cycle artifacts their own `MissionArtifactKind`, per [ADR
2026-08-03-1](../../../docs/adr/3.x/2026-08-03-1-review-cycle-artifacts-are-coord-partition.md)
(Accepted, operator-adjudicated), and make the **write** side actually follow
it. Today review-cycle artifacts (`tasks/<wp>/review-cycle-N.md`) borrow
`MissionArtifactKind.WORK_PACKAGE_TASK` — a PRIMARY-partition kind — purely
because they live under `tasks/`, a *path* coincidence, not a partition
argument. The canonical glossary
([`docs/context/orchestration.md#coord-partition`](../../../docs/context/orchestration.md#coord-partition))
already lists "review cycles" under COORD. The ADR resolves that contradiction
in the glossary's favour: **COORD under coordination topologies, PRIMARY
otherwise** — per-WP lifecycle bookkeeping, not stable planning output.

**This WP's independent test** (tasks.md): a `kind=REVIEW_CYCLE` write under a
coord topology lands on the coord surface and commits there; the same write
under `SINGLE_BRANCH` lands PRIMARY.

**The read seam needs no code change** — verified by probe in the ADR:
`resolve_artifact_surface` already returns PRIMARY for a COORD kind under
`SINGLE_BRANCH`/`LANES`, so the topology rule falls out of set membership
automatically once the kind exists. **The write side is the actual work**, and
a first draft of the ADR that claimed "no new routing machinery is required"
was rejected by a two-lens adversarial check for exactly this reason.

**Four concrete mechanisms are required deliverables, not optional
follow-ups** — a recurring failure mode on this mission is landing the first
few and treating the last one as later cleanup:

1. **T014** — the filename-anchored classifier leg for `review-cycle-*.md`, so
   `_artifact_kind_for_path` can express the new kind at all.
2. **T015** — proof (trace plus test) that the commit router honours the kind
   for review-cycle paths under both coord and coordless topology.
3. **T016** — an explicit ruling on `REVIEW_CYCLE`'s E2/PUBLISHED-phase
   eligibility.
4. **T017** — resolution of the two-sided `tasks/` merge-reconciliation
   hazard this WP itself creates by putting a genuinely both-sides-divergent
   COORD artifact inside a directory (`tasks/`) the merge guard currently
   classifies as non-divergent.

Skipping T014/T015/T016 means every rejection write under coord topology
fails with `no_op_wrong_surface` and the artifact gets unlinked. Skipping
T017 leaves a real clobber path live in the codebase — a target-side review
cycle silently overwritten by `-X theirs` during merge, the #2804 shape — not
merely an untested edge case; it is not a lower-priority cleanup item than
T014-T016 just because it sits later in the subtask list.

**Do not implement the read-side reconciliation, the numbering fix, or the
writer's commit call** — those are WP07/WP08/WP09/WP10's work, downstream of
this one. This WP's job is narrowly: make `REVIEW_CYCLE` exist, classify
correctly, and route correctly through the commit seam. Nothing in this WP
should touch `review/cycle.py`, `review/artifacts.py`, or
`post_merge/review_artifact_consistency.py`.

## Context & Constraints

Read in full before starting:

- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md` — FR-023
  verbatim: "Read **and** write paths resolve through that one kind; a
  caller-supplied directory is not a substitute for either."
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/plan.md` — the
  "Resolved: the COORD/PRIMARY partition — ADR 2026-08-03-1" section in full,
  and IC-06a's split-out risk notes (the two-sided `tasks/` hazard, the
  create-window split).
- [`docs/adr/3.x/2026-08-03-1-review-cycle-artifacts-are-coord-partition.md`](../../../docs/adr/3.x/2026-08-03-1-review-cycle-artifacts-are-coord-partition.md)
  — the full ADR, including "What the first draft got wrong" (read this table;
  it exists specifically to stop this WP from repeating those two mistakes)
  and the measured migration numbers (102 missions carry review cycles, 45
  declare a coordination branch, 0 of those 45 branches still exist).
- `src/mission_runtime/artifacts.py` — read the whole file. Key anchors as of
  this writing (confirm line numbers against your checkout, they drift):
  - `class MissionArtifactKind(enum.Enum)` (~line 62) — the enum this WP adds
    a member to.
  - `_PRIMARY_ARTIFACT_KINDS` (~line 136) and `_PLACEMENT_ARTIFACT_KINDS`
    (~line 172) — the two disjoint, exhaustive frozensets partition membership
    is decided by. `is_primary_artifact_kind` / `kind_is_coordination_residue`
    consult these directly; do not add a third set.
  - `_MISSION_FILE_KIND_BY_BASENAME` (~line 195) — the exact-basename
    classifier dict. This is where `review-cycle-<N>.md` **cannot** be
    expressed, because it has no fixed basename.
  - `_COORD_RESIDUE_DIRS` (~line 233) — `{"tasks": WORK_PACKAGE_TASK,
    "checklists": CHECKLIST, "traces": TRACER_FILE}`, the directory-kind
    fallback `_artifact_kind_for_path` (~line 377) uses for anything nested
    more than one level under the mission root: `return
    _COORD_RESIDUE_DIRS.get(mission_rel_parts[0])`. Today every file under
    `tasks/<wp>/` — `review-cycle-1.md` and `baseline-tests.json` alike —
    falls through to this directory-level fallback and classifies as
    `WORK_PACKAGE_TASK`.
- `src/specify_cli/coordination/coherence.py` — read `is_coord_residue_churn`
  (~line 89) in full. This is the **actual** authority `commit_router.py`'s
  `_group_files_by_partition` delegates to for bucketing a file PRIMARY vs
  COORD — it composes `kind_for_mission_file` (→ `_artifact_kind_for_path`)
  with `kind_is_coordination_residue`. **This means the commit-router
  bucketing bug is really an `artifacts.py` classifier gap, not a
  `commit_router.py` logic gap** — the router already buckets correctly by
  whatever kind the classifier returns; it just has nothing correct to
  receive today. Confirm this by tracing the call chain before assuming
  `commit_router.py` needs a structural change; T015 verifies (and, only if
  genuinely needed, extends) that chain.
- `src/specify_cli/coordination/commit_router.py` — read
  `_group_files_by_partition` (~line 405) and its docstring in full,
  including the "buckets are ABSOLUTE, not relative to the caller" framing
  and the coordless-topology collapse optimization (~line 437-460), plus
  `_representative_kind_for_bucket` (~line 380).
- `src/mission_runtime/resolution.py` — read `_E2_CONSOLIDATED_ELIGIBLE_KINDS`
  (~line 121: `frozenset(_PRIMARY_ARTIFACT_KINDS | {ISSUE_MATRIX, TRACER_FILE,
  ACCEPTANCE_MATRIX})`) and its comment ("`STATUS_STATE` and `DECISION_LOG`
  are DELIBERATELY excluded") — the eligibility set T016 must rule on.
- `tests/architectural/test_write_surface_placement_guard.py` — read
  `PARTITION_RATIONALE` (~line 446), the pinned-exhaustive
  `dict[MissionArtifactKind, tuple[partition, rationale, load_bearing_consumer]]`,
  and `test_partition_rationale_is_exhaustive` (~line 570), which reds the
  moment a new enum member has no matching row — the mechanism that forces
  T013.
- `tests/architectural/test_merge_reconciliation_class_guard.py` — read the
  module docstring, `_NON_DIVERGENT_COORD_RESIDUE_DIRS` (~line 273:
  `frozenset({"tasks", "checklists"})`), and
  `test_both_sides_divergent_canonical_artifacts_carry_merge_driver` (~line
  276) — the "two-sided `tasks/` hazard" T017 must resolve. `tasks` is
  classified **non-divergent** ("authored once and never independently
  edited on the target side"), which the ADR's Consequences section calls
  falsified once `review-cycle-*.md` becomes a genuinely both-sides-divergent
  COORD artifact inside that same directory.

**Constraints (binding)**:
- **Filename-anchored, never directory-anchored.** The classifier leg for
  `review-cycle-*.md` must match on filename pattern, not on "anything under
  `tasks/<wp>/`" — `tasks/<wp>/baseline-tests.json` is deliberately PRIMARY
  (`WORK_PACKAGE_TASK`, per its own comment in `_MISSION_FILE_KIND_BY_BASENAME`)
  and `tasks/WP*.md` must keep classifying as `WORK_PACKAGE_TASK`. A
  directory-anchored rule would silently re-partition both.
- **P-1 preserved**: `REVIEW_CYCLE` joins exactly one of
  `_PRIMARY_ARTIFACT_KINDS` / `_PLACEMENT_ARTIFACT_KINDS`, never both, never
  neither. `WORK_PACKAGE_TASK` itself does not move.
- **No behaviour change to the read seam.** `resolve_artifact_surface` /
  `resolve_placement_only` need no new branching for `REVIEW_CYCLE` — their
  existing topology-driven logic already produces the correct answer once
  `REVIEW_CYCLE` is a member of `_PLACEMENT_ARTIFACT_KINDS`. If you find
  yourself adding an `if kind is MissionArtifactKind.REVIEW_CYCLE:` branch
  inside either resolver function, stop — that is very likely the #2155-class
  regression the existing coordless-topology collapse logic exists to avoid,
  and it means you have misdiagnosed which layer needs the change.
- **This WP does not write the migration/exception-absorption logic.** The
  ADR's "exception absorption, not empty-directory fallback" section (reads
  absorbing `CoordinationBranchDeleted` to PRIMARY, in one owner function) is
  WP07's/WP13's read-side work, not this WP's write-side plumbing.

## Subtask T012 — Introduce `MissionArtifactKind.REVIEW_CYCLE`

- **Purpose**: The enum member every other subtask in this WP depends on.
- **Steps**:
  1. In `src/mission_runtime/artifacts.py`, add `REVIEW_CYCLE =
     "review_cycle"` to `class MissionArtifactKind(enum.Enum)`, following the
     existing style of a short docstring-comment above the member (see
     `DECISION_LOG` and `TRACER_FILE`'s comments for the house pattern: cite
     the mission and WP that added the kind, and the one-line rationale).
  2. Do not add it to `_PRIMARY_ARTIFACT_KINDS` or `_PLACEMENT_ARTIFACT_KINDS`
     in this subtask — T013 does that deliberately as a separate, reviewable
     step, so the "kind exists but is unclassified" state is a clean commit
     boundary if you are landing this WP as a reviewable sequence per C-006.
  3. Run `tests/architectural/test_write_surface_placement_guard.py::
     test_partition_rationale_is_exhaustive` and confirm it now fails, naming
     `REVIEW_CYCLE` as missing — this is expected and is the mechanism T013
     satisfies next, not a regression to route around.
- **Files**: `src/mission_runtime/artifacts.py`
- **Validation checklist**:
  - [ ] `MissionArtifactKind.REVIEW_CYCLE` exists with value `"review_cycle"`.
  - [ ] `test_partition_rationale_is_exhaustive` fails, naming exactly
        `REVIEW_CYCLE` as the missing member (confirms the guard is doing its
        job, and that you have not accidentally also classified it yet).
  - [ ] No other test file changes yet.
- **Edge Cases**: None — this is a pure enum addition with no branching logic.

## Subtask T013 — Add it to `_PLACEMENT_ARTIFACT_KINDS`; add the `PARTITION_RATIONALE` row

- **Purpose**: Classify `REVIEW_CYCLE` as COORD-partition (per the ADR's
  Decision §2), and satisfy the exhaustiveness guard T012 deliberately broke.
- **Steps**:
  1. In `src/mission_runtime/artifacts.py`, add
     `MissionArtifactKind.REVIEW_CYCLE` to the `_PLACEMENT_ARTIFACT_KINDS`
     frozenset (~line 172), alongside `ACCEPTANCE_MATRIX`, `ISSUE_MATRIX`,
     `STATUS_STATE`, `DECISION_LOG`, `TRACER_FILE`. Add a comment citing this
     mission and ADR 2026-08-03-1, matching the style of the `DECISION_LOG` /
     `TRACER_FILE` comments already there.
  2. In `tests/architectural/test_write_surface_placement_guard.py`, add a
     `MissionArtifactKind.REVIEW_CYCLE` row to `PARTITION_RATIONALE` (~line
     446): partition `"COORD"`, a rationale citing the ADR ("per-WP lifecycle
     bookkeeping, written repeatedly during execution — not stable planning
     output; a stale primary copy is coordination residue under coord
     topology"), and a load-bearing consumer (name the actual future
     consumer — `review/cycle.py`'s writer and `post_merge/
     review_artifact_consistency.py`'s gate, even though neither is edited by
     this WP; they are the surfaces that will break if this kind is
     re-homed).
  3. Run `test_partition_rationale_is_exhaustive` and
     `test_partition_rationale_split_matches_live_frozensets` (~line 587) —
     both must pass now.
  4. Run `test_full_partition_resolves_per_membership` (~line 311) and the
     all-kinds anti-mutant parametrizations — these exercise every
     `MissionArtifactKind` including your new one against the real resolver,
     with zero new code in `resolution.py` (per the "read seam needs no
     change" constraint above). If any of these fail, you have found either a
     genuine gap in that claim (rare — flag it, do not silently patch around
     it) or a mistake in this subtask's frozenset edit (far more likely —
     re-check first).
- **Files**: `src/mission_runtime/artifacts.py`,
  `tests/architectural/test_write_surface_placement_guard.py`
- **Validation checklist**:
  - [ ] `REVIEW_CYCLE in _PLACEMENT_ARTIFACT_KINDS` and
        `REVIEW_CYCLE not in _PRIMARY_ARTIFACT_KINDS`.
  - [ ] `PARTITION_RATIONALE[MissionArtifactKind.REVIEW_CYCLE] ==
        ("COORD", <rationale>, <consumer>)`.
  - [ ] The full `test_write_surface_placement_guard.py` suite passes.
  - [ ] `resolve_placement_only(repo_root, mission_slug,
        kind=MissionArtifactKind.REVIEW_CYCLE)` under a coord topology
        resolves to the coordination ref, and under `SINGLE_BRANCH`/`LANES`
        resolves to the primary `target_branch` — prove both directly (a
        small throwaway script or an ad-hoc test run is fine; a permanent
        test for this belongs in T014/T015's own test additions once the
        classifier exists end-to-end).
- **Edge Cases**: None beyond re-confirming P-1 (exactly one membership) holds
  after the edit.

## Subtask T014 — Add the filename-anchored classifier leg for `review-cycle-*.md`

- **Purpose**: Without this, `_artifact_kind_for_path` cannot express
  `REVIEW_CYCLE` at all — every `tasks/<wp>/review-cycle-N.md` path still
  falls through to `_COORD_RESIDUE_DIRS.get("tasks")` →
  `WORK_PACKAGE_TASK`, and the enum member from T012/T013 is dead code for
  every real path.
- **Steps**:
  1. In `src/mission_runtime/artifacts.py`'s `_artifact_kind_for_path`
     (~line 377), the current logic is: single relative part → basename
     lookup (`_MISSION_FILE_KIND_BY_BASENAME` then `_COORD_RESIDUE_DIRS`);
     multiple relative parts → `_COORD_RESIDUE_DIRS.get(mission_rel_parts[0])`
     unconditionally. Add a nested-pattern leg that runs **before** the
     unconditional `_COORD_RESIDUE_DIRS` fallback for the multi-part case:
     when `mission_rel_parts[0] == "tasks"` and the final path component
     matches `review-cycle-*.md` (a glob-shaped check, e.g. via
     `fnmatch.fnmatch(mission_rel_parts[-1], "review-cycle-*.md")` or an
     equivalent regex — match the house style already used for basename
     matching elsewhere in this module), return
     `MissionArtifactKind.REVIEW_CYCLE`. Only when that pattern does not
     match does the function fall through to the existing
     `_COORD_RESIDUE_DIRS.get(mission_rel_parts[0])` behaviour — this is what
     keeps `tasks/<wp>/baseline-tests.json` and any other non-review-cycle
     file under `tasks/` classifying as `WORK_PACKAGE_TASK` exactly as today.
  2. Do **not** key the new leg on directory depth or on the parent directory
     being a WP-shaped name — key it purely on the filename pattern at the
     final path component, so `tasks/WP01/review-cycle-1.md` and any other
     accepted WP-slug/separator shape (recall spec.md US3: `-`, `_`, `.`, or
     no separator) all classify identically regardless of how the WP
     directory segment is spelled.
  3. Add focused unit tests directly against `kind_for_mission_file` /
     `_artifact_kind_for_path` (not only the higher-level guard tests) proving:
     - `kitty-specs/<slug>/tasks/WP01/review-cycle-1.md` → `REVIEW_CYCLE`
     - `kitty-specs/<slug>/tasks/WP01/baseline-tests.json` → `WORK_PACKAGE_TASK`
       (unchanged)
     - `kitty-specs/<slug>/tasks/WP01-foo.md` (a WP task file, single relative
       part) → `WORK_PACKAGE_TASK` (unchanged, exercises the basename-lookup
       branch, not the new nested-pattern leg)
     - A file named `review-cycle-notes.md` (does not match the numeric
       `review-cycle-<N>.md` shape spec.md's other WPs use) — decide and test
       explicitly whether your glob is `review-cycle-*.md` (matches this too)
       or a stricter numeric pattern; the ADR's own text says
       `review-cycle-*.md`, so a permissive glob is correct per the ADR, but
       write the test either way so the boundary is explicit rather than
       accidental.
- **Files**: `src/mission_runtime/artifacts.py`
- **Validation checklist**:
  - [ ] All four cases above are covered by a passing test.
  - [ ] `kind_for_mission_file("kitty-specs/x/tasks/WP01/baseline-tests.json")
        is MissionArtifactKind.WORK_PACKAGE_TASK` still holds — this is the
        regression the filename-anchoring constraint exists to prevent.
  - [ ] `mypy --strict` / `ruff` clean.
- **Edge Cases**: A review-cycle file for a WP whose slug itself contains the
  substring `review-cycle` (contrived, but check) must still classify
  correctly — the match must be anchored on the **final** path component only,
  never on a substring test against the whole path.

## Subtask T015 — Make the commit router honour the kind for review-cycle paths

- **Purpose**: Confirm — and only if a genuine gap is found, extend — that
  `commit_router.py`'s write-side bucketing correctly routes a
  `kind=REVIEW_CYCLE` write to the coord ref under coord topology, now that
  T014 gives the classifier something correct to return.
- **Steps**:
  1. Trace the call chain end-to-end: a caller invokes `commit_for_mission(...,
     kind=MissionArtifactKind.REVIEW_CYCLE, files=(review_cycle_path,))` →
     `_group_files_by_partition(repo_root, files, mission_slug,
     kind=REVIEW_CYCLE)` → for each file, `is_coord_residue_churn(file,
     mission_slug=mission_slug)` → `kind_for_mission_file(file,
     mission_slug=mission_slug)` (now returns `REVIEW_CYCLE` post-T014) →
     `kind_is_coordination_residue(REVIEW_CYCLE, MissionTopology.COORD)` (now
     `True` post-T013, since `REVIEW_CYCLE in _PLACEMENT_ARTIFACT_KINDS`).
     Since the caller's own `kind` is already `REVIEW_CYCLE` (COORD), and the
     file's own residue classification agrees, this should hit the
     `caller_partition_holds_everything` fast path (~line 475-482) and return
     a single group with the caller's kind — no representative-kind
     resolution needed, no split.
  2. Write an integration-shaped test exercising exactly this path through
     `commit_for_mission` (or the lowest public seam that reaches
     `_group_files_by_partition` without reimplementing it) for: (a) a coord
     topology, asserting the file commits to the coordination ref; (b) a
     `SINGLE_BRANCH`/`LANES` topology, asserting it commits to the primary
     `target_branch` (the coordless collapse path, ~line 499-506 — both
     partitions resolve to the same ref, so the historical single-commit fast
     path is used).
  3. **If and only if** tracing in step 1 surfaces a genuine gap — e.g. a
     caller that constructs the review-cycle commit call with `kind=
     WORK_PACKAGE_TASK` instead of the new `REVIEW_CYCLE` (this would be a
     defect in a caller file outside this WP's `owned_files`, most likely
     `review/cycle.py`'s `_commit_review_cycle_artifact`, which belongs to
     WP10/IC-05a) — do not silently fix the caller from within this WP. Record
     the finding precisely (file, line, current `kind` argument) in this WP's
     Activity Log and in `tests/architectural/census/verdict_seam_IC04.yaml` (T018) as an explicit
     dependency WP10 must satisfy, since `_commit_review_cycle_artifact`
     is not in this WP's `owned_files`.
  4. If tracing confirms `_group_files_by_partition` and
     `_representative_kind_for_bucket` already correctly compose with the new
     classifier leg with no code change required — which is the expected
     outcome given `is_coord_residue_churn` is the sole delegated authority —
     say so explicitly in this file's module-level test docstring, so a future
     reader does not assume `commit_router.py` was silently left broken.
- **Files**: `src/specify_cli/coordination/commit_router.py` (test additions;
  production change only if step 3's gap is found and is genuinely inside
  this module — the classifier fix belongs in `artifacts.py`, already done in
  T014)
- **Validation checklist**:
  - [ ] A new test proves a `kind=REVIEW_CYCLE` write lands on the coord ref
        under a coord topology.
  - [ ] A new test proves the same write lands on `target_branch` under
        `SINGLE_BRANCH`/`LANES`.
  - [ ] If no production change was needed in `commit_router.py`, that is
        stated explicitly (with the trace) rather than left implicit.
  - [ ] Any caller-side gap found is recorded as a named dependency for WP10,
        not silently patched here.
- **Edge Cases**: A batch commit mixing a `REVIEW_CYCLE` file with a
  `WORK_PACKAGE_TASK` file (e.g. a WP task-file edit landing in the same
  commit as a new review cycle) under a coord topology must split into two
  commits against two different refs — test this mixed-batch case explicitly,
  since it is the one case `_group_files_by_partition`'s "genuinely mixed AND
  refs diverge" branch (~line 508-512) actually exercises new code paths for.

## Subtask T016 — Rule on E2 eligibility for `REVIEW_CYCLE`

- **Purpose**: `_E2_CONSOLIDATED_ELIGIBLE_KINDS`
  (`src/mission_runtime/resolution.py:121`) is a closed, explicitly-curated
  frozenset — every PRIMARY kind plus exactly `ISSUE_MATRIX`, `TRACER_FILE`,
  `ACCEPTANCE_MATRIX`, with `STATUS_STATE` and `DECISION_LOG` **deliberately**
  excluded per its own comment. `REVIEW_CYCLE` needs an explicit ruling one
  way or the other — leaving it unruled means a PUBLISHED mission's
  review-cycle write falls through to an unconditional coordination probe
  instead of the E2 CONSOLIDATED-surface short-circuit every other COORD kind
  in that set already gets.
- **Steps**:
  1. Read `_resolve_consolidated_e2_target` and the surrounding
     `resolve_placement_only` logic (~line 1443-1460) to understand what
     "E2-eligible" actually buys a kind: a PUBLISHED mission (Target Ref
     deleted) resolves straight to the CONSOLIDATED surface — the squashed
     Primary-Branch content — instead of attempting to reach a coordination
     branch that, per the ADR's own measurement, is **always** deleted for a
     published coord mission (0 of 45 surviving).
  2. Decide: should `REVIEW_CYCLE` join `_E2_CONSOLIDATED_ELIGIBLE_KINDS`
     alongside `ISSUE_MATRIX`/`TRACER_FILE`/`ACCEPTANCE_MATRIX` (same
     bookkeeping-kind shape, same "coordination branch is gone post-merge"
     reality), or should it be excluded like `STATUS_STATE`/`DECISION_LOG`
     (whose comment states their post-consolidation resolution deliberately
     stays unchanged for a stated reason — read that reasoning and check
     whether it applies to `REVIEW_CYCLE` too, or whether it is specific to
     those two kinds' own consumers)? The ADR's own text treats the
     unconditional-probe fallthrough as a defect to avoid ("or a PUBLISHED
     mission's write falls through to an unconditional coordination probe"),
     which weighs toward inclusion — but confirm this against
     `_resolve_consolidated_e2_target`'s actual behavior for a COORD-partition
     kind rather than assuming the ADR's prose is a substitute for reading the
     resolver.
  3. Implement whichever ruling you reach — either add `REVIEW_CYCLE` to
     `_E2_CONSOLIDATED_ELIGIBLE_KINDS` with a comment citing this mission and
     the ADR, or add a comment next to `REVIEW_CYCLE`'s omission explaining
     why it is excluded, matching the existing `STATUS_STATE`/`DECISION_LOG`
     comment's shape.
  4. Add a test exercising a PUBLISHED mission resolving a `REVIEW_CYCLE`
     artifact and asserting it reaches the CONSOLIDATED surface (if included)
     or documenting/asserting the unconditional-probe fallback behavior
     explicitly (if excluded) — either way, the behavior must be proven, not
     left to fall out of whichever branch happens to execute.
- **Files**: `src/mission_runtime/resolution.py`
- **Validation checklist**:
  - [ ] `REVIEW_CYCLE`'s E2 eligibility is explicitly ruled on, with a comment
        stating the rationale — not silently absent from
        `_E2_CONSOLIDATED_ELIGIBLE_KINDS` with no explanation.
  - [ ] A test proves the ruled-on behavior for a PUBLISHED mission.
  - [ ] `STATUS_STATE` and `DECISION_LOG`'s existing exclusion is unaffected.
- **Edge Cases**: A PUBLISHED mission that is also one of the 45
  coordination-branch-deleted missions from the ADR's measurement is the
  concrete case this ruling protects — make sure your test fixture actually
  models a deleted coordination branch, not merely a mission with no coord
  branch declared at all (a different, unrelated case).

## Subtask T017 — Resolve the two-sided `tasks/` reconciliation-class hazard

- **Purpose**: `tests/architectural/test_merge_reconciliation_class_guard.py`'s
  `_NON_DIVERGENT_COORD_RESIDUE_DIRS` (~line 273) classifies `tasks` as
  human-authored/non-divergent — safe for `git merge --squash -X theirs` to
  blindly prefer the mission-side copy, because (per its own comment) "each
  WP's `tasks/WPNN-*.md` / `checklists/*.md` is authored once and never
  independently edited on the target side." Once `review-cycle-*.md` lives
  inside that same `tasks/` directory as a genuinely both-sides-divergent
  COORD artifact (written repeatedly during execution, per-WP, on the
  coordination branch — the exact shape `traces/` already required a merge
  driver for), that justification is false for `tasks/` as a whole, and `-X
  theirs` can silently clobber a target-side review cycle — the #2804 clobber
  shape, inside a directory the guard currently pre-classifies as safe.
- **Steps**:
  1. Read `test_both_sides_divergent_canonical_artifacts_carry_merge_driver`
     (~line 276) in full, including its assertion that `divergent_dirs ==
     {"traces"}` (~line 294) — this line will need to change once `tasks`
     stops being purely non-divergent, and the test's own failure message
     ("a new coordination-residue directory kind appeared in
     `_COORD_RESIDUE_DIRS` that this guard does not yet classify — add it to
     `_NON_DIVERGENT_COORD_RESIDUE_DIRS`... or confirm it registers a union
     merge driver") is telling you exactly what decision this subtask must
     make.
  2. Decide between the two options the ADR names: **(a)** a reconcile driver
     — register a merge driver for `kitty-specs/**/tasks/*.md` scoped
     specifically to `review-cycle-*.md` (not the whole `tasks/*.md` glob,
     which would also catch WP task files that genuinely are non-divergent),
     mirroring the existing `traces` union-merge driver
     (`merge_driver.py::merge_driver_traces`) as the precedent; or **(b)** a
     documented re-justification for why `tasks` can safely stay in
     `_NON_DIVERGENT_COORD_RESIDUE_DIRS` despite review cycles. **Option (b) is
     legal only if you land a test that demonstrates the specific clobber
     scenario cannot occur** — e.g. a test proving WP10's atomicity work or
     WP13's consumer unification structurally prevents a target-side review
     cycle from ever existing independently of the mission-side one before
     this mission fully lands. A re-justification that is prose only, with no
     demonstrating test, is not a valid discharge of this subtask — it is the
     exact escape hatch a prior adversarial pass flagged as unacceptable. If
     you cannot produce such a test, option (a) is required, not preferred.
  3. If you choose (a): register the driver in `.gitattributes`, the in-code
     `_MERGE_DRIVERS` registry (`src/specify_cli/lanes/merge.py`), the `init`
     seed, and the upgrade migration surface — `test_merge_reconciliation_
     class_guard.py`'s own docstring (T013b section, further down in that
     file) names all four surfaces the driver spec must agree across; do not
     register in only one.
  4. Whichever option you choose, update
     `_NON_DIVERGENT_COORD_RESIDUE_DIRS`'s own module comment (~line 253-272)
     to state the `review-cycle-*.md` exception explicitly — the current
     comment's blanket claim about `tasks/` must not survive this WP
     unmodified once it is no longer fully true.
  5. Confirm `test_both_sides_divergent_canonical_artifacts_carry_merge_driver`
     passes with your chosen classification.
- **Files**: `tests/architectural/test_merge_reconciliation_class_guard.py`,
  and — only if option (a) is chosen — `.gitattributes`,
  `src/specify_cli/lanes/merge.py`, the relevant `init` seed and upgrade
  migration files (these are outside this WP's `owned_files`; if genuinely
  required, treat as a flagged cross-WP dependency the same way T015 handles
  its own caller-side finding, and record it in
  `tests/architectural/census/verdict_seam_IC04.yaml` rather than silently
  expanding this WP's file ownership).
- **Validation checklist**:
  - [ ] The chosen option is explicit and does not leave `divergent_dirs ==
        {"traces"}` stale if `tasks` genuinely becomes divergent.
  - [ ] If option (a) is chosen: a driver is registered and all four surfaces
        the guard's own docstring names agree.
  - [ ] If option (b) is chosen: a test demonstrating the specific clobber
        scenario cannot occur is landed and passing — a prose-only
        re-justification with no demonstrating test does not satisfy this
        subtask, regardless of how persuasive the prose is.
  - [ ] `_NON_DIVERGENT_COORD_RESIDUE_DIRS`'s comment accurately describes the
        post-this-WP state of `tasks/`.
- **Edge Cases**: A driver scoped too broadly (`tasks/*.md` rather than
  `tasks/*/review-cycle-*.md` or equivalent) would apply union-merge semantics
  to WP task files too, which are genuinely single-writer and where a union
  merge could produce a nonsensical merged document — scope narrowly.

## Subtask T018 — Document the create-window artifact split

- **Purpose**: The coord worktree materialises lazily at the commit boundary
  (per existing, unrelated design), so a coord mission's *first* review cycle
  is written to PRIMARY (no coord worktree exists yet to write into) and every
  later one to COORD, with `next_cycle_number` counting only whichever single
  surface it globs. This WP does not fix that split — WP09's numbering work
  and WP13's consumer unification do — but per the ADR, this WP must **state**
  the behavior so it is a documented, understood consequence rather than a
  silently-discovered surprise partway through a later WP.
- **Steps**:
  1. Create `tests/architectural/census/verdict_seam_IC04.yaml`
     as this WP's owned fragment of the fragmented verdict-seam-census
     contract (per plan.md's FR-020 fragmentation design — this WP alone owns
     this file; the fold into the shared contract is WP16/IC-12's job).
  2. In it, record:
     - The `REVIEW_CYCLE` kind's final classification (COORD-partition,
       filename-anchored `review-cycle-*.md` classifier, E2 ruling from T016).
     - The create-window split, stated precisely: "a coord-topology mission's
       first review cycle for a given WP lands PRIMARY (the coord worktree has
       not yet materialised); every subsequent cycle for that WP lands COORD.
       `next_cycle_number` as it exists today globs a single directory and
       will therefore miscount across this split until WP09/WP13 land." Do not
       soften this into "may need attention" — state it as a known, present
       behavior downstream WPs must handle.
     - Any caller-side gap found during T015 (a commit call site still
       passing `kind=WORK_PACKAGE_TASK` for a review-cycle write) as an
       explicit dependency WP10 must close, with file/line citation.
     - Any cross-WP file-ownership dependency surfaced during T017 (e.g. a
       merge-driver registration touching files outside this WP's
       `owned_files`), similarly cited.
  3. Cross-reference `tests/architectural/census/verdict_seam_IC01.yaml`
     (WP01's own fragment) by name — do not duplicate its writer/resolver/
     reader enumeration here; this file's scope is the partition/classifier/
     routing decision this WP specifically owns.
- **Files**: `tests/architectural/census/verdict_seam_IC04.yaml`
- **Validation checklist**:
  - [ ] The create-window split is stated as a present fact, not a caveat.
  - [ ] Every cross-WP finding from T015/T017 is recorded with a concrete
        file/line citation, not a vague "downstream WPs should check this."
  - [ ] The file does not write into the shared
        `tests/architectural/verdict_seam_census.yaml` fold target or WP01's
        `tests/architectural/census/verdict_seam_IC01.yaml`.
- **Edge Cases**: None — this is a documentation deliverable, but it is a
  required one (FR-020's "executable, not decorative" contract discipline
  applies to every `IC-NN.md` fragment, not only the folded whole).

## Branch Strategy

Planning artifacts for this mission were generated on
`pr/review-verdict-write-integrity-01KZ1CGF`. This WP depends on WP01 and
branches from WP01's landed base; worktrees are allocated per lane from
`lanes.json` at `spec-kitty implement WP04` time. Completed changes merge back
into `pr/review-verdict-write-integrity-01KZ1CGF` unless the human explicitly
redirects the landing branch.

## Definition of Done

- `MissionArtifactKind.REVIEW_CYCLE` exists, is classified COORD-partition,
  and has a `PARTITION_RATIONALE` row (T012, T013).
- `_artifact_kind_for_path` correctly, filename-anchoredly, classifies
  `tasks/<wp>/review-cycle-*.md` as `REVIEW_CYCLE` while leaving
  `tasks/<wp>/baseline-tests.json` and `tasks/WP*.md` unchanged as
  `WORK_PACKAGE_TASK` (T014).
- The commit-router write path is proven (via test, and via explicit trace
  documentation) to route a `REVIEW_CYCLE` write to the correct ref under both
  coord and coordless topology, with any genuine caller-side gap recorded as a
  cross-WP dependency rather than silently patched (T015).
- `REVIEW_CYCLE`'s E2/PUBLISHED-phase eligibility is explicitly ruled on and
  tested (T016).
- The `tasks/` two-sided reconciliation hazard has an explicit resolution —
  either a reconcile driver, or a re-justification backed by a passing test
  that demonstrates the clobber scenario cannot occur (prose alone is not a
  valid discharge) — and the guard test's own divergent-set assertion
  reflects it (T017).
- `tests/architectural/census/verdict_seam_IC04.yaml` exists and documents the
  create-window split and every cross-WP finding from this WP's own
  investigation (T018).
- `resolve_artifact_surface` / `resolve_placement_only` in
  `src/mission_runtime/resolution.py` carry **no** new `REVIEW_CYCLE`-specific
  branching — only the E2-eligibility set change from T016, if that ruling is
  inclusion.
- `review/cycle.py`, `review/artifacts.py`, `post_merge/
  review_artifact_consistency.py` show zero diff from this WP.
- `mypy --strict` and `ruff` clean on every touched file, zero new
  suppressions.
- [ ] **NFR-002** — every function this WP touches ends at cyclomatic complexity ≤15: `uv run ruff check --select C901 <touched files>` is clean. Extract helpers rather than leaving a function at 16+.

## Risks & Mitigations

- **Directory-anchoring the classifier instead of filename-anchoring it.**
  This is the single most likely mistake — it is the *easy* fix and it is
  wrong, because it silently reclassifies `baseline-tests.json` too. Mitigate
  with T014's explicit four-case test list, run before considering the
  subtask done.
- **Assuming `commit_router.py` needs new branching logic** when
  `is_coord_residue_churn` already delegates cleanly to the classifier.
  Mitigate by tracing the actual call chain (T015 step 1) before writing any
  new production code in that file — the more likely outcome is that
  `artifacts.py`'s classifier fix (T014) is sufficient and `commit_router.py`
  needs only test coverage.
- **Silently patching a caller outside this WP's `owned_files`** (e.g.
  `review/cycle.py`'s commit call site) to make an end-to-end test pass.
  Mitigate by treating any such finding as a documented cross-WP dependency
  (T015 step 3, T018) rather than expanding this WP's scope past its slicing
  boundary — doing so would violate the `validate_no_overlap` ownership gate
  this mission's own tasks.md establishes.
- **Leaving `tasks`'s non-divergent classification stale** after adding a
  genuinely divergent file inside it. Mitigate by treating T017 as mandatory,
  not optional — the guard test's own assertion (`divergent_dirs ==
  {"traces"}`) will not fail on its own if you skip this; it only fails when a
  *new, unclassified* directory-kind residue appears in `_COORD_RESIDUE_DIRS`,
  which T012/T013 do not add (they add an enum member and a file-pattern leg,
  not a new directory-kind residue) — so this specific guard will not catch a
  skipped T017 by itself. Do not rely on CI red to remind you; do it because
  the ADR names it as a required deliverable.

## Reviewer Guidance

- Confirm the classifier fix is filename-anchored by demanding the
  `baseline-tests.json` and `tasks/WP*.md` negative-case tests from T014 —
  their absence is the single highest-value thing to check first.
- Confirm the reviewer independently traces (or asks the implementer to show)
  the `commit_for_mission` → `_group_files_by_partition` →
  `is_coord_residue_churn` → `kind_for_mission_file` chain, rather than
  accepting "I added a branch to commit_router.py" without justification —
  new branching there is a yellow flag given the classifier-delegation design.
- Confirm T017 was actually resolved, not silently skipped — ask specifically
  "what happens to `tasks/`'s non-divergent classification now that
  review-cycle files live there," and expect either a merge-driver diff or a
  re-justification **backed by a passing test that demonstrates the clobber
  scenario cannot occur**. A written re-justification with no demonstrating
  test is not acceptable and must be rejected outright, not treated as a
  softer but valid alternative to the driver.
- Confirm `review/cycle.py`, `review/artifacts.py`, and `post_merge/
  review_artifact_consistency.py` are byte-identical to before this WP.
- Confirm `tests/architectural/census/verdict_seam_IC04.yaml` names every
  cross-WP finding with a concrete citation — a fragment that says
  "downstream WPs should verify
  this" without naming the specific file/line is not sufficient.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-03T08:13:56Z – system – lane=planned – Prompt created.

---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP04 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
