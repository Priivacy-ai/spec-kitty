---
affected_files: []
cycle_number: 1
mission_slug: write-surface-coherence-01KVTVZS
reproduction_command:
reviewed_at: '2026-06-23T21:48:29Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP02
review_artifact_override_at: "2026-06-23T22:05:27Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP02"
review_artifact_override_reason: "Cycle-1 re-review passed (renata). Cycle-0 blocker (TestCoordTopologyPlanningCommitRoundTrip asserting removed planning->coord contract) fixed by 0c0487f92. Re-pin legitimate: bifurcation leg present and non-vacuous (STATUS_STATE stays COORD while SPEC routes PRIMARY). Red-first verified myself: removing SPEC from _PRIMARY_ARTIFACT_KINDS turned both round-trip tests RED; restored -> green. No regression: changed file 7/7, regression suites 49/49, ruff clean. Scope = one test file (133 ins / 47 del). --force/--skip-review-artifact-check for inherited-state guards only."
---

**WP02 Review — CHANGES REQUESTED (1 blocking convergence gap)**

Overall the WP02 implementation is strong and the squad-hardened invariants are
correctly realized. The single blocker is an incomplete write-path convergence:
a contract test for the **removed** planning→coord behavior was missed during the
re-pin sweep. Details below.

---

## VERIFIED — PASS (no action needed)

- **C-001 / G-2 (the squad BLOCKER): PASS.** `status_transition._resolve_write_target`
  threads `kind=STATUS_STATE` and the DoD test
  `test_resolve_write_target_stays_coord_after_required_kind` builds a real coord
  fixture, calls the real `_resolve_write_target`, and asserts
  `resolved == coord.coord_branch and resolved != TARGET_BRANCH` — PASS. The two
  base-ref reads (`tasks.py:359` review-currency, `commands.py:796` lane-base gate)
  both pass `STATUS_STATE` with a "base-ref read under coord topology — coord kind
  preserves G-2" comment. No status caller flipped to primary. **No C-001 regression.**
- **All 7 `resolve_placement_only` sites accounted for.** Sites 2/3/4 threaded here
  (STATUS_STATE, stay coord); sites 5/6/7 (`safe_commit_cmd.py:206`,
  `commands.py:1296`, `mission.py:749` helper) are correctly WP03-owned (T012/T013/T014)
  and left un-threaded for WP03.
- **use_coord single-authority: PASS.** Derived from the kind-aware `placement`
  (`routes_through_coordination(...) and placement.ref != primary_target`). No second
  routing predicate. Red-first PROVEN: reverting the derivation to topology-only makes
  `test_primary_kind_under_coord_topology_does_not_route_to_coord` go RED (materialiser
  called) — verified by revert/restore.
- **Direct-safe_commit writers (T032): PASS.** `tasks.py:2462`/`:3108` resolve via
  `resolve_placement_only(kind=WORK_PACKAGE_TASK/TASKS_INDEX)`; no hardcoded
  `CommitTarget(ref=target_branch)` survives for the planning files. `_skip_target_branch_commit`
  re-documented as a non-routing suppression flag (narrowed per T032, not a parallel router).
- **Kinds correct:** record-analysis → `ANALYSIS_REPORT` (stays coord, C-001);
  acceptance meta → `PRIMARY_METADATA`; `_kind_for_artifact` raises loud KeyError on
  unmapped type (no silent SPEC default). Direct test present + green.
- **Re-pin of `test_protected_primary_spec_commit.py`: legitimate.** The
  `routes_to_coordination` row was correctly FLIPPED to
  `primary_kind_does_not_route_to_coordination`, the coord-forcing stub removed (now uses
  the real kind-aware resolver), and the negative load-bearing proof re-targeted onto the
  COORD path (ANALYSIS_REPORT). This is delete-the-assertion-not-the-test done right.
- ruff clean on owned files; mypy errors on the owned files are all PRE-EXISTING
  `no-any-return`/`misc` outside the diff (confirmed by base-compare) — none on WP02 lines.
- The 4 `test_sc6_planning_placement_e2e.py` failures are the FR-008/WP03
  protected-primary deadlock class (finalize-tasks now routes TASKS_INDEX to primary →
  protected-fixture refuses until WP03 makes it deadlock-free). NOT a WP02 defect.

---

## BLOCKER — Incomplete write-path convergence (FR-003 / C-005)

**Issue:** `tests/specify_cli/cli/commands/test_wp05_write_surface_authority.py::TestCoordTopologyPlanningCommitRoundTrip`
(two tests) asserts the **exact contract WP02 removes** and was missed in the re-pin sweep:

1. `test_spec_commit_lands_and_reads_back_from_coordination_surface` — calls
   `commit_for_mission(...)` for a `spec.md` and asserts
   `result.placement_ref == _COORD_BRANCH` and reads the spec back from the **coordination
   worktree** (`assert ".worktrees" in str(read_surface)`).
2. `test_negative_primary_read_does_not_see_the_coord_commit` — asserts the spec commit
   does NOT land on primary HEAD.

Both directly contradict the mission's own spec:
- **FR-002**: "The coordination worktree is never the authoring/read surface for planning artifacts."
- **FR-003** (WP02's requirement): "the 'commit planning artifacts to the coordination branch' path is removed."
- **C-005**: "remove the planning-artifact-on-coordination write path; do not preserve it as a compatibility fallback."

Current state under WP02: these two tests **TypeError** (`commit_for_mission() missing
required keyword-only argument 'kind'`) because they were not threaded, AND even if
threaded with `SPEC` their `placement_ref == _COORD_BRANCH` assertion would be WRONG under
the new contract (SPEC is now primary).

**Note on "0 introduced":** Strictly these were already red on the WP01 base (same
TypeError root cause from WP01's required `kind`), so they are not *newly introduced* by
WP02. But WP02 owns FR-003 and the `commit_for_mission` write-path convergence, and the
implementer correctly re-pinned the *sibling* round-trip test
(`test_protected_primary_spec_commit.py`) — this round-trip test is the same class and was
simply missed. WP05 does NOT own it (WP05 = "coord-worktree helper governance", ff-advance
only; its task file does not reference this test). WP03's only reference is a passing
comment, not an ownership claim. It belongs to the WP02 convergence.

**How to fix (delete-the-assertion-not-the-test):** Re-pin
`TestCoordTopologyPlanningCommitRoundTrip` to the NEW contract, preserving the
anti-fakeable round-trip structure:
- Thread `kind=MissionArtifactKind.SPEC` into both `commit_for_mission` calls.
- Flip the WRITE-leg assertion: a SPEC planning commit lands on the **primary**
  `target_branch` (NOT `_COORD_BRANCH`); the read-back surface is the **primary** feature
  dir (NOT `.worktrees`).
- Flip the negative test accordingly: the committed content IS on the primary surface;
  assert it is NOT carried onto a coord worktree (the inverse anti-fakeable proof).
- Keep the #2063 round-trip intent — it is "preserved and corrected" to planning-on-primary
  (per WP03 T012's own note), so the round-trip should now prove write↔read coherence on
  the **primary** seam, not delete the coverage.

Alternatively, if the project decides this specific test is WP07's behavioral-verification
responsibility, that must be made explicit (add it to a WP's scope) rather than left as a
stale-intent test asserting a removed contract on a broken signature. As-is it is an
un-owned convergence gap in WP02's own FR.

---

## Tests run by reviewer
- `test_commit_router.py`, `test_kind_for_artifact.py`, `test_status_transition_adoption.py` — 25 passed
- `test_protected_primary_spec_commit.py`, `test_artifact_partition.py`, `test_resolve_placement_only.py` — 24 passed
- C-001 DoD test isolated — passed; red-first use_coord revert — RED as expected (restored)
- 141 passed across the remaining touched-file tests
- `test_sc6_planning_placement_e2e.py` — 4 failed (FR-008/WP03 class; not a WP02 defect)
- `test_wp05_write_surface_authority.py::TestCoordTopologyPlanningCommitRoundTrip` — **2 failed (the blocker above)**
