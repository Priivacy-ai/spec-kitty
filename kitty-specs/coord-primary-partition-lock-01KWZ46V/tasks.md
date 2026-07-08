# Tasks: Coord/Primary Partition Regression Lock

**Mission**: `coord-primary-partition-lock-01KWZ46V` | **Branch**: `design/coord-primary-partition-lock`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

Authoritative write-side placement-routing strangler: complete + lock the existing
placement SSOT by routing every remaining write/read through the one topology-aware seam,
extend the ratchet, harden the identity/topology bugs, and lock with a characterization
test. All source-code changes; this mission dogfoods the coord/primary partition it locks.

## Sequencing overview

```
WP01 (seam foundation)
  ├─► WP02 (create-time root)      ┐
  ├─► WP03 (implement + record)    ├─ routing (parallel)  ─► WP07 (ratchet lock)
  ├─► WP04 (workflow + router)     │                       └─► WP08 (characterization test)*
  └─► WP05 (tasks move-task)       ┘
WP06 (bug/husk hardening)   — parallel, independent
WP09 (docs & roadmap)       — parallel, independent
```
*WP08 is soft-gated on PR #2429 landing (C-007) — sequence it last.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Add `write_target(kind)`/`read_dir(kind)` projections over `resolve_action_context` | WP01 | |
| T002 | Bind routing to `routes_through_coordination(stored_topology)`; assert P-1/T-1 | WP01 | |
| T003 | Seam unit tests across 2×2 topology × 14 kinds | WP01 | |
| T004 | Consolidate 4 `_planning_read_dir` wrappers → one shared helper | WP01 | |
| T005 | Campsite: Sonar cleanups in WP01 owned files | WP01 | [P] |
| T006 | Red-first: reproduce create-time split-brain via `_commit_feature_file` | WP02 | |
| T007 | Route `mission_creation.py:176` to `seam.write_target(SPEC)` | WP02 | |
| T008 | Verify red→green; regression across coord + non-coord | WP02 | |
| T009 | Campsite: Sonar cleanups in `mission_creation.py` | WP02 | [P] |
| T010 | Red-first: implement.py planning commit derives from checkout/None-fallback | WP03 | |
| T011 | Route `implement.py:885` & `:1462` via `seam.write_target(kind)` | WP03 | |
| T012 | D11 fail-closed: replace `_resolve_placement_ref:672`→`:1467` fallback with require-canonical error | WP03 | |
| T013 | Route `mission_record_analysis.py:80` (ANALYSIS_REPORT); remove None→legacy fallback | WP03 | |
| T014 | Tests incl. fail-closed behavior; regression | WP03 | |
| T015 | Campsite: Sonar cleanups in WP03 owned files | WP03 | [P] |
| T016 | Red-first: workflow.py inline coord/target topology branch | WP04 | |
| T017 | Extract one `_resolve_workflow_placement`; route `:487/503/549/1694` | WP04 | |
| T018 | commit_router extractions to stay ≤15 (`_stage_artifacts_in_coord_worktree`, `commit_for_mission` headroom) | WP04 | |
| T019 | Rename stale `_planning_commit_worktree`; keep PRIMARY-guard `raise` | WP04 | |
| T020 | Tests + regression | WP04 | |
| T021 | Campsite: Sonar cleanups in WP04 owned files | WP04 | [P] |
| T022 | Red-first: tasks move-task/mark-status placement derivation | WP05 | |
| T023 | Extract placement helper from `_mt_commit_wp_file:1252` (≤15) before routing | WP05 | |
| T024 | Route move-task/mark-status cluster via `seam.write_target(STATUS_STATE)`; reconcile #2438 | WP05 | |
| T025 | Tests + regression | WP05 | |
| T026 | Campsite: Sonar cleanups in `tasks_move_task.py` | WP05 | [P] |
| T027 | Red-first: #2091 empty-mid8 → malformed branch at composition seam | WP06 | |
| T028 | Add empty-mid8 guard at `CoordinationWorkspace` composition; verify upstream guard | WP06 | |
| T029 | #2250 verify + regression; distinguish never-created/DELETED/UNMATERIALIZED | WP06 | |
| T030 | FR-012 husk guard: enforce stored-topology-not-husk; flatten-transition regression | WP06 | |
| T031 | Close #2091 + #2250 (green regression) | WP06 | |
| T032 | Campsite: Sonar cleanups in WP06 owned files | WP06 | [P] |
| T033 | Extend ratchet scanner with `CommitTarget(ref=<checkout>)` grammar + detection boundary | WP07 | |
| T034 | Set write-side allow-list to floor (seed@347); expand adopted-module set; coord_authority stays 7 (drain→#2453) | WP07 | |
| T035 | Extend shipped #2198 `test_write_surface_placement_guard.py` (do not duplicate) | WP07 | |
| T036 | Full architectural suite green; self-test that a re-introduced bypass goes red | WP07 | |
| T037 | Campsite: Sonar cleanups in WP07 owned files | WP07 | [P] |
| T038 | Golden-path e2e: create→spec→setup-plan→tasks status→decision verify, one authority | WP08 | |
| T039 | Add ≥1 lifecycle mutation through the seam; assert destination by topology | WP08 | |
| T040 | Assert CWD-independence across coord + non-coord | WP08 | |
| T041 | Edge assertions: flatten/deleted/unmaterialized/protected-primary; #2404-lite ACCEPTANCE_MATRIX | WP08 | |
| T042 | Determinism + <30s (NFR-002); gate authoring on #2429 (C-007) | WP08 | |
| T043 | Retire "planning happens in main" (AGENTS.md + CLAUDE.md); state the partition | WP09 | |
| T044 | Rewrite roadmap: whole #1878 write-side strangler → 3.2.x/G2 | WP09 | |
| T045 | Update #1716 issue body (manual gh) to the planning-on-primary decision | WP09 | |
| T046 | Correct inventory prose (2×2 topology, 14 kinds); terminology + docs-freshness guards | WP09 | [P] |

---

## WP01 — Placement seam formalization (foundation)

- **Goal**: Expose the existing `resolve_action_context` root as the single kind-aware placement seam (`write_target(kind)`/`read_dir(kind)`, classified by `MissionArtifactHome`); consolidate the 4 `_planning_read_dir` wrappers into one helper.
- **Priority**: P0 (foundation — everything routes through this). **Dependencies**: none.
- **Independent test**: seam returns partition-correct write/read locations for all 14 kinds across the 2×2 topology grid; the 4 wrappers delegate to one helper with unchanged behavior.
- **Requirements**: FR-001, FR-002, FR-003, FR-005, FR-006, FR-012, C-001, C-002.
- **Prompt**: [tasks/WP01-placement-seam-formalization.md](./tasks/WP01-placement-seam-formalization.md)

- [x] T001 Add `write_target(kind)`/`read_dir(kind)` projections over `resolve_action_context` (WP01)
- [x] T002 Bind routing to `routes_through_coordination(stored_topology)`; assert P-1/T-1 (WP01)
- [x] T003 Seam unit tests across 2×2 topology × 14 kinds (WP01)
- [x] T004 Consolidate 4 `_planning_read_dir` wrappers → one shared helper (WP01)
- [x] T005 Campsite: Sonar cleanups in WP01 owned files (WP01)

## WP02 — Create-time root strangle (unowned bullseye)

- **Goal**: Route `mission_creation.py:176` (`_commit_feature_file`) to `seam.write_target(SPEC)` instead of `CommitTarget(ref=current_branch)` — the create-time split-brain root.
- **Priority**: P0. **Dependencies**: WP01.
- **Independent test**: red-first test proves the split-brain before, passes after; spec commit lands on the partition-correct surface for coord + non-coord.
- **Requirements**: FR-004, C-001, C-006.
- **Prompt**: [tasks/WP02-create-time-root-strangle.md](./tasks/WP02-create-time-root-strangle.md)

- [x] T006 Red-first: reproduce create-time split-brain via `_commit_feature_file` (WP02)
- [x] T007 Route `mission_creation.py:176` to `seam.write_target(SPEC)` (WP02)
- [x] T008 Verify red→green; regression across coord + non-coord (WP02)
- [x] T009 Campsite: Sonar cleanups in `mission_creation.py` (WP02)

## WP03 — implement.py + record_analysis strangle (fail-closed)

- **Goal**: Route `implement.py:885/1462` and `mission_record_analysis.py:80` through the seam; resolve the two D11 forbidden `None→CommitTarget(ref=<checkout>)` fallbacks fail-closed (require-canonical).
- **Priority**: P0 (authoritative, C-005). **Dependencies**: WP01.
- **Independent test**: red-first tests for both sites; fail-closed raises a structured error instead of a silent checkout fallback; ANALYSIS_REPORT commits to the coord surface.
- **Requirements**: FR-004, FR-005, FR-011, C-001, C-005, C-006 (D11).
- **Prompt**: [tasks/WP03-implement-record-analysis-strangle.md](./tasks/WP03-implement-record-analysis-strangle.md)

- [x] T010 Red-first: implement.py planning commit derives from checkout/None-fallback (WP03)
- [x] T011 Route `implement.py:885` & `:1462` via `seam.write_target(kind)` (WP03)
- [x] T012 D11 fail-closed: replace `_resolve_placement_ref:672`→`:1467` fallback with require-canonical error (WP03)
- [x] T013 Route `mission_record_analysis.py:80` (ANALYSIS_REPORT); remove None→legacy fallback (WP03)
- [x] T014 Tests incl. fail-closed behavior; regression (WP03)
- [x] T015 Campsite: Sonar cleanups in WP03 owned files (WP03)

## WP04 — workflow.py + commit_router strangle

- **Goal**: Route `workflow.py:487/503/549/1694` via one `_resolve_workflow_placement` helper; do the commit_router extractions to stay ≤15; rename the stale `_planning_commit_worktree`.
- **Priority**: P0 (authoritative, C-005). **Dependencies**: WP01.
- **Independent test**: red-first for the inline topology branch; workflow/status writes land partition-correct; extracted helpers ≤15 complexity; `_planning_commit_worktree` PRIMARY-guard `raise` preserved.
- **Requirements**: FR-004, FR-005, C-001, C-005, C-006, NFR-004.
- **Prompt**: [tasks/WP04-workflow-commit-router-strangle.md](./tasks/WP04-workflow-commit-router-strangle.md)

- [x] T016 Red-first: workflow.py inline coord/target topology branch (WP04)
- [x] T017 Extract one `_resolve_workflow_placement`; route `:487/503/549/1694` (WP04)
- [x] T018 commit_router extractions to stay ≤15 (WP04)
- [x] T019 Rename stale `_planning_commit_worktree`; keep PRIMARY-guard `raise` (WP04)
- [x] T020 Tests + regression (WP04)
- [x] T021 Campsite: Sonar cleanups in WP04 owned files (WP04)

## WP05 — tasks.py move-task strangle

- **Goal**: Route the tasks move-task/mark-status write cluster via `seam.write_target(STATUS_STATE)`; extract a placement helper from `_mt_commit_wp_file` (≤15) before routing; reconcile with the just-landed #2438 gate.
- **Priority**: P0 (authoritative, C-005). **Dependencies**: WP01.
- **Independent test**: red-first for placement derivation; move-task bookkeeping lands on the coord surface for coord missions; `_mt_commit_wp_file` ≤15; #2438 gate still green.
- **Requirements**: FR-004, FR-005, C-001, C-005, C-006, NFR-004.
- **Prompt**: [tasks/WP05-tasks-move-task-strangle.md](./tasks/WP05-tasks-move-task-strangle.md)

- [x] T022 Red-first: tasks move-task/mark-status placement derivation (WP05)
- [x] T023 Extract placement helper from `_mt_commit_wp_file:1252` (≤15) before routing (WP05)
- [x] T024 Route move-task/mark-status cluster via `seam.write_target(STATUS_STATE)`; reconcile #2438 (WP05)
- [x] T025 Tests + regression (WP05)
- [x] T026 Campsite: Sonar cleanups in `tasks_move_task.py` (WP05)

## WP06 — Identity/topology hardening (#2091, #2250, husk)

- **Goal**: #2091 empty-mid8 composition guard (red-first); #2250 verify+regression; FR-012 husk guard is **already shipped by #2062** → verify + flatten regression only (do not re-implement). Close both issues.
- **Priority**: P1. **Dependencies**: none (parallel).
- **Independent test**: empty-mid8 fails loudly (no exit-128); never-created coord mission does not report `COORDINATION_BRANCH_DELETED`; flatten transition reads primary, not the husk.
- **Requirements**: FR-007, FR-008, FR-012, C-006, NFR-003.
- **Prompt**: [tasks/WP06-identity-topology-hardening.md](./tasks/WP06-identity-topology-hardening.md)

- [x] T027 Red-first: #2091 empty-mid8 → malformed branch at composition seam (WP06)
- [x] T028 Add empty-mid8 guard at `CoordinationWorkspace` composition; verify upstream guard (WP06)
- [x] T029 #2250 verify + regression; distinguish never-created/DELETED/UNMATERIALIZED (WP06)
- [x] T030 FR-012 husk guard: enforce stored-topology-not-husk; flatten-transition regression (WP06)
- [x] T031 Close #2091 + #2250 (green regression) (WP06)
- [x] T032 Campsite: Sonar cleanups in WP06 owned files (WP06)

## WP07 — Ratchet lock

- **Goal**: Extend `test_no_write_side_rederivation.py` with the `CommitTarget(ref=<checkout>)` grammar; set the **write-side** allow-list to floor (seed@347); expand the adopted-module set; extend the shipped #2198 gate. (`coord_authority` read-side drain deferred to #2453.)
- **Priority**: P0 (lock). **Dependencies**: WP02, WP03, WP04, WP05.
- **Independent test**: architectural suite green; a re-introduced `CommitTarget(ref=<checkout>)` bypass makes the ratchet go red; allow-list at floor; baseline shrunk.
- **Requirements**: FR-011, NFR-001, SC-005.
- **Prompt**: [tasks/WP07-ratchet-lock.md](./tasks/WP07-ratchet-lock.md)

- [ ] T033 Extend ratchet scanner with `CommitTarget(ref=<checkout>)` grammar + detection boundary (WP07)
- [ ] T034 Set write-side allow-list to floor (seed@347); expand adopted-module set; coord_authority stays 7 (drain→#2453) (WP07)
- [ ] T035 Extend shipped #2198 `test_write_surface_placement_guard.py` (do not duplicate) (WP07)
- [ ] T036 Full architectural suite green; self-test that a re-introduced bypass goes red (WP07)
- [ ] T037 Campsite: Sonar cleanups in WP07 owned files (WP07)

## WP08 — Characterization test (regression lock)

- **Goal**: End-to-end golden-path + lifecycle mutation + edge states, CWD-independent, across coord and non-coord; #2404-lite ACCEPTANCE_MATRIX assertion. **Soft-gated on PR #2429 (C-007).**
- **Priority**: P0 (lock). **Dependencies**: WP02, WP03, WP04, WP05, WP06 (+ soft #2429).
- **Independent test**: the test passes on 3 consecutive CI runs, < 30 s, identical results from repo root and an unrelated CWD.
- **Requirements**: FR-009, NFR-002, C-007.
- **Prompt**: [tasks/WP08-characterization-test.md](./tasks/WP08-characterization-test.md)

- [ ] T038 Golden-path e2e: create→spec→setup-plan→tasks status→decision verify, one authority (WP08)
- [ ] T039 Add ≥1 lifecycle mutation through the seam; assert destination by topology (WP08)
- [ ] T040 Assert CWD-independence across coord + non-coord (WP08)
- [ ] T041 Edge assertions: flatten/deleted/unmaterialized/protected-primary; #2404-lite ACCEPTANCE_MATRIX (WP08)
- [ ] T042 Determinism + <30s (NFR-002); gate authoring on #2429 (C-007) (WP08)

## WP09 — Docs & roadmap truth-up

- **Goal**: Retire "planning happens in main"; rewrite roadmap (whole #1878 → 3.2.x); update #1716 body; correct inventory prose.
- **Priority**: P1. **Dependencies**: none (parallel).
- **Independent test**: terminology guard + docs-freshness green; no doc states planning→main for coord missions; roadmap shows whole #1878 under 3.2.x.
- **Requirements**: FR-010, SC-004.
- **Prompt**: [tasks/WP09-docs-roadmap-truth-up.md](./tasks/WP09-docs-roadmap-truth-up.md)

- [x] T043 Retire "planning happens in main" (AGENTS.md + CLAUDE.md); state the partition (WP09)
- [x] T044 Rewrite roadmap: whole #1878 write-side strangler → 3.2.x/G2 (WP09)
- [x] T045 Update #1716 issue body (manual gh) to the planning-on-primary decision (WP09)
- [x] T046 Correct inventory prose (2×2 topology, 14 kinds); terminology + docs-freshness guards (WP09)

---

## MVP scope

**WP01 + WP02** is the minimal viable lock: the seam formalized + the unowned create-time
split-brain root routed through it, red-first. Everything else extends coverage (WP03–05),
hardens (WP06), locks (WP07/WP08), and truth-ups (WP09).

## Campsite note (Sonar)

Each WP carries a **campsite list** in its prompt: Sonar issues in the files it owns,
classified SAFE (clean inline) / ADJACENT (clean if low-risk) / OUT (tracked home). Source:
the aggregated Sonar inventory from the recently-merged sonar-debt missions. Per project
policy: complexity ≤15 via extraction, repeated literals→constants, no empty except, real
fixes over suppression.
