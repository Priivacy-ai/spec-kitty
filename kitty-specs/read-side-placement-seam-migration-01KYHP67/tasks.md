# Tasks: Read-Side Placement-Seam Migration

**Mission**: `read-side-placement-seam-migration-01KYHP67`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md) · **Data model**: [data-model.md](./data-model.md) · **Contract**: [contracts/read-side-gate.md](./contracts/read-side-gate.md)

8 work packages. **WP02 (classification) gates the migration batches**; **WP08 (gate) lands last**. WP01 (#2921) is independent.

## Dependencies / lanes

- WP01 (#2921) — independent, any lane.
- WP09 (#2966 part-1 `_mission_id` leg) — independent, any lane.
- WP02 (classify) — independent; **blocks WP03–WP07 and WP08**.
- WP03, WP04, WP05, WP06, WP07 (migration batches) — depend WP02; mutually parallel (disjoint owned_files).
- WP08 (gate) — depends WP03–WP07 (seeded-red/last).

## The shared migration procedure (WP03–WP07)

For each file the WP owns, consult the WP02 classification ledger and apply its verdict:
- **migrate-fail-loud** → replace the direct `resolve_planning_read_dir(root,slug,kind=K)` / `candidate_feature_dir_for_mission(root,slug)` call with `placement_seam(root,slug).read_dir(K)` (declare the correct `MissionArtifactKind`; retrospective reads → `resolve_retrospective_home`). Add/extend a behavior-preservation test (healthy case resolves the identical dir; deleted-coord now raises `CoordinationBranchDeleted`).
- **stay-lenient** → leave the call as-is; ensure WP08's allow-list carries a site-descriptor entry with rationale (coordinate via the ledger). Add an NFR-001 leniency test where the file is a diagnostic/audit reader.
- **sanction-infra** → not applicable to these clusters (handled by WP08).
Gates per WP: `ruff`, `mypy` (project-mode), the touched-module tests, and the behavior-preservation/leniency tests. Reuse the seam + `CoordinationBranchDeleted`; do NOT add a second read authority.

## Subtask Index

| ID | Description | WP |
|----|-------------|----|
| T001 | Red-first repro of #2921 through `repair_lane_mismatch` | WP01 |
| T002 | Fix `task_metadata_validation.py:127`/`:178` (`_` 3rd elem + pass `"\n"`) | WP01 |
| T003 | Assert clean single-frontmatter round-trip + `validate_task_metadata==[]` | WP01 |
| T004 | Enumerate all bypass call sites (59 files; per-site symbol + count) | WP02 |
| T005 | Classify each site: migrate-fail-loud / stay-lenient / sanction-infra (+ kind for kind-blind) | WP02 |
| T006 | Write the committed classification ledger | WP02 |
| T007 | Migrate agent-CLI cluster per ledger (incl. workflow.py 17 sites) | WP03 |
| T008 | Behavior-preservation tests for the agent-CLI cluster | WP03 |
| T009 | Migrate CLI-commands cluster per ledger | WP04 |
| T010 | Behavior-preservation tests for the CLI-commands cluster | WP04 |
| T011 | Migrate merge+lanes cluster per ledger | WP05 |
| T012 | Behavior-preservation tests for the merge+lanes cluster | WP05 |
| T013 | Migrate status/coord/review/dashboard/retrospective cluster per ledger (diagnostic-heavy — many stay-lenient) | WP06 |
| T014 | NFR-001 leniency tests (audit paths tolerate deleted/half-materialized coord) | WP06 |
| T015 | Migrate core/context/workspace/plan/misc cluster per ledger | WP07 |
| T016 | Behavior-preservation tests for the core/misc cluster | WP07 |
| T017 | Structural read gate reusing `_placement_whole_tree_scan.scan_scope()` | WP08 |
| T018 | Sanctioned set (infra) + shrink-only content-descriptor allow-list via `_ratchet_keys` | WP08 |
| T019 | Bite test + symmetry meta-test (same scan_scope as write gate) | WP08 |
| T020 | Green the gate with the shrinking allow-list (seeded-red → shrink) | WP08 |
| T021 | Red-first repro of `_mission_id` coord-leg namespacing (#2966 part-1) | WP09 |
| T022 | Route `_mission_id` to the PRIMARY `read_dir` leg | WP09 |
| T023 | Assert seed ULIDs namespace on the mission ULID | WP09 |

## Work Packages

### WP01 — Fix repair_lane_mismatch frontmatter corruption (#2921)
- **Goal**: `repair_lane_mismatch` writes one well-formed frontmatter block, correct lane, clean fence, body not duplicated.
- **Requirements**: FR-007, SC-005. **Deps**: none.
- **Independent test**: repair a lane-mismatched WP file → clean round-trip + `validate_task_metadata==[]`.
- [ ] T001 Red-first repro (WP01)
- [ ] T002 Fix :127/:178 (WP01)
- [ ] T003 Round-trip assertion (WP01)

### WP02 — Classification ledger (IC-01)
- **Goal**: Every one of the 59 bypass files classified (verdict + kind + rationale) — the migration spine.
- **Requirements**: FR-001, SC-001. **Deps**: none. **Blocks**: WP03–WP08.
- **Independent test**: ledger covers 100% of sites; no `unknown` verdict.
- [ ] T004 Enumerate sites (WP02)
- [ ] T005 Classify each (WP02)
- [ ] T006 Write ledger (WP02)

### WP03 — Migrate agent-CLI cluster (IC-03/IC-04)
- **Goal**: Apply the ledger to `cli/commands/agent/**` (incl. the 17-site `workflow.py`).
- **Requirements**: FR-002, NFR-002. **Deps**: WP02.
- [ ] T007 Migrate cluster (WP03)
- [ ] T008 Behavior-preservation tests (WP03)

### WP04 — Migrate CLI-commands cluster (IC-03/IC-04)
- **Goal**: Apply the ledger to `cli/commands/*.py` (non-agent) + `cli/commands/charter/_widen.py`.
- **Requirements**: FR-002, NFR-002. **Deps**: WP02.
- [ ] T009 Migrate cluster (WP04)
- [ ] T010 Behavior-preservation tests (WP04)

### WP05 — Migrate merge+lanes cluster (IC-03/IC-04)
- **Goal**: Apply the ledger to `merge/**` + `lanes/**`.
- **Requirements**: FR-002, NFR-002. **Deps**: WP02.
- [ ] T011 Migrate cluster (WP05)
- [ ] T012 Behavior-preservation tests (WP05)

### WP06 — Migrate diagnostic-heavy cluster + leniency (IC-03/IC-04/IC-05)
- **Goal**: Apply the ledger to `coordination/status_transition.py`, `status/aggregate.py`, `review/cycle.py`, `dashboard/scanner.py`, `retrospective/summary.py`, `retrospective/writer.py`, `dossier/api.py`, `decisions/service.py` — expect many **stay-lenient** (audit paths).
- **Requirements**: FR-002, FR-004, NFR-001, NFR-002. **Deps**: WP02.
- [ ] T013 Migrate/keep-lenient per ledger (WP06)
- [ ] T014 NFR-001 leniency tests (WP06)

### WP07 — Migrate core/context/workspace/plan/misc cluster (IC-03/IC-04)
- **Goal**: Apply the ledger to the remaining consumers (`acceptance/__init__.py`, `agent_tasks_ports.py`, `agent_utils/status.py`, `context/resolver.py`, `core/stale_detection.py`, `core/worktree_topology.py`, `doctrine_synthesizer/apply.py`, `manifest.py`, `mission_loader/command.py`, `missions/plan/plan_interview.py`, `missions/plan/specify_interview.py`, `orchestrator_api/commands.py`, `sync/events.py`, `task_utils/support.py`, `workspace/context.py`, `runtime/next/runtime_bridge_identity.py` [shared-package boundary — confirm route]).
- **Requirements**: FR-002, NFR-002. **Deps**: WP02.
- [ ] T015 Migrate cluster (WP07)
- [ ] T016 Behavior-preservation tests (WP07)

### WP08 — Structural read-side gate + sanctions + allow-list (IC-02/IC-05/IC-06)
- **Goal**: New `tests/architectural/test_no_read_side_bypass.py` mirroring the structural write gate; sanction infra (`_read_path_resolver.py`, `coordination/surface_resolver.py`, `mission_runtime/write_target_degrade.py`); shrink-only content-descriptor allow-list for stay-lenient residuals; bite + symmetry tests.
- **Requirements**: FR-003, FR-005, FR-006, NFR-003, NFR-004, SC-002, SC-003. **Deps**: WP03–WP07 (lands last).
- [ ] T017 Gate reusing scan_scope() (WP08)
- [ ] T018 Sanctioned set + ratchet allow-list (WP08)
- [ ] T019 Bite + symmetry tests (WP08)
- [ ] T020 Green with shrinking allow-list (WP08)

### WP09 — Route _mission_id to the PRIMARY leg (#2966 part-1 remainder)
- **Goal**: `backfill_runtime_state._mission_id` reads `meta.json` from the PRIMARY `read_dir` leg, so seed ULIDs namespace on the mission ULID (not the coord dir name). E already fixed the `_synthesize_claim_anchor` half.
- **Requirements**: FR-008. **Deps**: none.
- **Independent test**: coord-rooted fixture (no meta on COORD leg) → seed ULIDs namespace on the PRIMARY `mission_id`; no orphaned-event warning.
- [ ] T021 Red-first repro (WP09)
- [ ] T022 Route `_mission_id` to read_dir (WP09)
- [ ] T023 Assert ULID namespacing (WP09)
