# Tasks: Coord/primary partition-authority residuals

**Mission**: `partition-authority-residuals-01M021K9` · **Branch**: `fix/partition-authority-residuals`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

11 work packages from IC-01…IC-09. **C-007**: no WP mixes a Scope-A partition reroute with a Scope-B
fidelity fix. Most WPs touch disjoint files and run in parallel lanes; the only coordination is the
shared merge-preflight e2e (WP01↔WP02) and the shared `emit_inner_state_changed` *dependency*
(WP01↔WP03 — neither edits it). All dependencies are empty unless noted.

**Universal Definition of Done (every WP):**
- Red-first test authored and shown failing before the fix (ATDD). Scope-A WPs carry a **live
  coord-topology e2e** (NFR-001); Scope-B WPs carry a **regression/migration test** (NFR-004).
- A **non-coord control** (SINGLE_BRANCH/LANES) asserts identical behavior where applicable.
- No predicate fork, no new legacy resolver path (C-001); STATUS reads stay COORD (C-002).
- `ruff` + `mypy` clean; complexity ≤15; new branches/helpers have focused tests (Sonar).
- `pytest tests/architectural/test_no_legacy_terminology.py` green if prose/doctrine touched.

---

## Scope A — Partition-authority residuals (#2160)

### WP01 — #2959 merge-deadlock: partition-correct override write + merge escape hatch
**Concern**: IC-01 · **FR**: FR-001, FR-002 · **Priority**: P1 · **Dependencies**: none
- T001 [test] Red coord-e2e: multi-WP coord mission, reject→fix→approve a WP, `merge` — assert it currently deadlocks.
- T002 [impl] In `tasks_materialization.py:78-90` (`_persist_review_artifact_override`), resolve `placement_seam(...).read_dir(STATUS_STATE)` at the caller and pass that dir into `emit_inner_state_changed` (leave the shared function unchanged). Ref pattern: `tasks_dependency_graph.py:120-135`.
- T003 [impl] Add `merge --skip-review-artifact-check` + `--note` to `cli/commands/merge.py:420-446` (parity with `tasks_transition_core.py:414-418`); record the skip as evidence.
- T004 [test] Assert the e2e now merges with override honored; assert the escape-hatch path merges and records evidence.
- T005 [verify] Register the coord worktree in the fixture (so STATUS_STATE resolves to coord, not the canonicalized primary). Non-coord control unchanged.
**Coordination**: shares the merge-preflight e2e with WP02; shares `emit_inner_state_changed` (no edit) with WP03.

### WP02 — #3439 merge gates read real PRIMARY data on coord missions
**Concern**: IC-02 · **FR**: FR-003, FR-004, FR-005 · **Priority**: P1 · **Dependencies**: none
- T001 [test] Red coord-e2e: coord mission with a risk-flagged WP + a real dependency edge — assert the risk gate SKIPs and the dependency graph is empty today.
- T002 [impl] Thread `repo_root`+`mission_slug` into `_evaluate_risk_gate`/`_evaluate_dependency_gate` (`merge_gates.py:86/194/242`); resolve LANE_STATE / WORK_PACKAGE_TASK via the seam per-leg; keep the STATUS_STATE event read on coord (C-002).
- T003 [impl] `workflow.py:202` (`_enforce_bulk_edit_diff_compliance`) resolve `lanes.json` via the seam (no silent `target_branch` fallback).
- T004 [impl] Remove the C-009 deferral note at `tasks_dependency_graph.py:132`.
- T005 [test] Assert the risk gate fires and the dependency gate sees the true graph on coord; non-coord control unchanged.
**Coordination**: same merge-preflight seam as WP01 — one shared coord-merge e2e can assert a fired risk gate AND an honored override.

### WP03 — #2939 move-task leaves a clean tree after a rejected review
**Concern**: IC-03 · **FR**: FR-007 · **Priority**: P2 · **Dependencies**: none
- T001 [test] Red coord-e2e: reject a WP review; assert `move-task` returns with a dirty `status.events.jsonl`/`status.json`.
- T002 [impl] In `tasks_move_task.py:2190-2318`, gather the post-transition `InnerStateChanged` annotation into the same bookkeeping transaction (or a second atomic status commit). Do NOT edit `emit_inner_state_changed` (emit.py:971-1041).
- T003 [test] Assert a clean tree after reject; also cover the non-rejection `→for_review` path when a note/agent annotation rides along.

### WP04 — #2698 review handoff shows real per-WP lane on coord missions
**Concern**: IC-04 · **FR**: FR-006 · **Priority**: P2 · **Dependencies**: none
- T001 [test] Red coord-e2e: multi-WP coord mission with WPs in mixed lanes; generate the handoff — assert every WP renders stale `planned`.
- T002 [impl] In `core/worktree_topology.py:147-149/207`, resolve the per-WP lane via the coord-aware STATUS_STATE surface (`lane_reader.py:51-76`); keep the PRIMARY dir for identity/lanes/tasks. Ref: `tasks_dependency_graph.py:120-135`.
- T003 [test] Assert the handoff renders true lanes; non-coord control unchanged.

### WP05 — #2966 part-2 the 4th safe-commit sibling routes through the shared helper
**Concern**: IC-05 · **FR**: FR-008 · **Priority**: P2 · **Dependencies**: none
- T001 [test] Red unit: assert `_resolve_mission_aware_target` bypasses `resolve_write_target_or_degrade` today; pin the current refusal behavior.
- T002 [impl] Route `safe_commit_cmd.py:278-307` through `resolve_write_target_or_degrade` (+ pre-gate + caught-set), **preserving** `CONSOLIDATED_CONTENT_ABSENT → MissionAwareCommitRefused` and benign `FileNotFoundError`/`ValueError` → `None` degrade.
- T003 [test] Assert helper-parity with the three siblings AND refusal-parity (both the raise and the degrade paths).

### WP06 — #2937 finalize checkpoints wps.yaml (gated on D-001)
**Concern**: IC-06 · **FR**: FR-009 · **Priority**: P3 · **Dependencies**: none · **Blocked-by**: Decision D-001
- T001 [decision] Resolve D-001: is `wps.yaml` versioned (commit it) or an operator-authored non-versioned input (document + skip)? Default lean: version it. Record in the mission decision log.
- T002 [test] Red test: finalize on a mission with `wps.yaml` — assert it is left uncommitted/dirty today.
- T003 [impl] If versioned: add `feature_dir/"wps.yaml"` to `_collect_finalize_artifacts` (`mission_finalize.py:187-216`) + a `wps.yaml → TASKS_INDEX` classifier entry in `mission_runtime/artifacts.py`; tighten `files_committed` to the true set. If non-versioned: document + adjust reporting only.
- T004 [test] Assert a clean tree after finalize (or the documented non-versioned behavior).

---

## Scope B — Mission-state discovery & diagnostic output fidelity (#2720)

### WP07 — #2692 check-prerequisites reports a truthful planning-artifact inventory
**Concern**: IC-07 · **FR**: FR-010 · **Priority**: P2 · **Dependencies**: none
- T001 [test] Red: mission with `research.md`+`data-model.md` present — assert `check-prerequisites --json` omits them and pin the two assertions at `tests/git_ops/test_worktree.py:465,487`.
- T002 [impl] In `core/worktree.py:661-706`, derive `available_docs`/`artifact_files` from the canonical mission `artifacts` metadata (not hardcoded spec/plan/tasks); fix `research_dir` file-vs-dir semantics (`:718-721`).
- T003 [test] Update the two behavior-locking assertions to the truthful inventory; add a `test_mission_check_prerequisites.py` case for the expanded inventory.

### WP08 — #2696 mission doctors: canonical writer schema + per-mission scoping
**Concern**: IC-07 · **FR**: FR-011, FR-012 · **Priority**: P2 · **Dependencies**: none
- T001 [test] Red: meta audit on a coord mission raises false `UNKNOWN_SHAPE` on `coordination_branch`/`topology`/`flattened`/`pr_bound`.
- T002 [impl] Derive `KNOWN_TOP_LEVEL_KEYS_BY_ARTIFACT["meta.json"]` (`audit/shape_registry.py:31-47`) programmatically from `mission_metadata.py:47-87` TypedDicts + coordination keys; regression test asserts every writer key is a known audit key.
- T003 [impl] Add `--mission` to `coordination_health` (`doctor.py:1258`), filtering through the same resolver as `mission-state` (MissionNotFound/AmbiguousHandle parity).
- T004 [test] Assert zero false `UNKNOWN_SHAPE`; assert `doctor coordination --mission <handle>` scopes to one mission.

### WP09 — #2717 diagnostics discover missions under the canonical kitty-specs root
**Concern**: IC-07 · **FR**: FR-013 · **Priority**: P2 · **Dependencies**: none
- T001 [test] Red: mission with a real `retrospective.yaml` under `kitty-specs/*` — assert `retrospect summary` omits it and counts `.kittify` support dirs.
- T002 [impl] Add one canonical `kitty-specs/*` mission-instance iterator (reads `meta.json`, excludes `.kittify`); route BOTH `summary.py:296-303` and `retrospect.py:1003-1005` through it (avoid the two-copy trap).
- T003 [test] Assert the real record is found and support dirs are not counted; test the shared iterator directly.

### WP10 — #2960 status doctor must not report Healthy over blanked runtime slots
**Concern**: IC-08 · **FR**: FR-014 · **Priority**: P2 · **Dependencies**: none
- T001 [test] Red: fold `agent:""` over `agent:"claude"` — assert the value is blanked and `status doctor` reports Healthy.
- T002 [impl] Normalize `""`→`None` at the `WPInnerStateDelta` write boundary (`status/models.py:460+`); treat empty replace-slots as no-op in `reducer.py:262-264/185`.
- T003 [impl] Add a `doctor.py` check for empty-string runtime slots on non-terminal WPs.
- T004 [test] Assert attribution survives and the doctor flags a blanked slot (no false Healthy).

### WP11 — #3066 mission-state repair preserves legacy WPStatusChanged transitions
**Concern**: IC-09 · **FR**: FR-015 · **Priority**: P1 (data-destroying) · **Dependencies**: none
- T001 [test] Red migration test: repair over an event log with a legacy `WPStatusChanged` row (`wp_id`/`from_lane`/`to_lane`) — assert it is quarantined and `status.json` regenerates with zero WPs.
- T002 [impl] Adopt PR #3067's diff (rerolled onto current main): add `_is_legacy_typed_lane_transition(row)` and route it via passthrough at the head of `_rule_reject_non_status_event` (`migration/mission_state.py:1583-1667`), before the quarantine branches.
- T003 [test] Assert the legacy row is preserved and `status.json` retains the WPs; assert TeamSpace envelopes and `DecisionPointOpened` mirrors stay quarantined. Keep #3067's red-first test.

---

## Dependency graph

All WPs are independent (empty `dependencies`) — disjoint file sets enable parallel lanes.
Coordination (not hard dependencies):
- **WP01 ↔ WP02** — shared merge-preflight coord-merge e2e; whichever lands second extends the shared fixture.
- **WP01 ↔ WP03** — both depend on `emit_inner_state_changed` (emit.py:971-1041) but neither edits it.

## Scope / lane separability (C-007)
Scope A = WP01–WP06 · Scope B = WP07–WP11. No lane may mix the two.

## #2720 close-path
Landing WP07–WP11 resolves #2720's in-class children (#2692/#2696/#2717/#2960/#3066); #2704→#1193 and
#2973 (unparented, new-epic recommended) are reparented out; #2754 already closed. Then #2720 closes.
