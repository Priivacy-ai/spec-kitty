---
work_package_id: WP04
title: map-requirements re-point + record-analysis double-resolution collapse
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-009
tracker_refs:
- '#2107'
- '#2102'
planning_base_branch: feat/gate-read-surface-completion
merge_target_branch: feat/gate-read-surface-completion
branch_strategy: Planning artifacts for this mission were generated on feat/gate-read-surface-completion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/gate-read-surface-completion unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
phase: Phase 1 - Gate-read spine (Lane A)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4093154"
history:
- at: '2026-06-24T08:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/tasks.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_map_requirements_read_surface.py
- tests/specify_cli/cli/commands/agent/test_record_analysis_double_resolution.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks.py
- tests/specify_cli/cli/commands/agent/test_map_requirements_read_surface.py
- tests/specify_cli/cli/commands/agent/test_record_analysis_double_resolution.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – map-requirements re-point + record-analysis double-resolution collapse

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on
`authoritative_surface: src/specify_cli/cli/commands/agent/tasks.py`.

---

## Objective

Two residual planning-read consolidations:
1. **`map-requirements`** reads WP `tasks/*.md` (a PRIMARY kind, `WORK_PACKAGE_TASK`) off
   the topology-routed `feature_dir` (→ coord) — the **squad-found missed site** (debbie,
   Decision 3). Re-point it onto the seam (FR-004).
2. **record-analysis** does a manual **coord-then-primary double-resolution**
   (`mission.py:1951` coord placement_ref + `:1980` primary write anchor). Collapse the
   planning-read leg onto the canonical seam (FR-009).

## Context & Constraints

Ground truth — read before editing:
- [spec.md](../spec.md) FR-004 (map-requirements enumerated), FR-009 (collapse the
  double-resolution).
- [plan.md](../plan.md) IC-04.
- [data-model.md](../data-model.md) site map row 10 (map-requirements `tasks.py:3727`,
  WORK_PACKAGE_TASK, RESIDUAL) + row 11 (record-analysis double-resolution `mission.py:1980`,
  COLLAPSE).
- [research.md](../research.md) Decision 3 (the missed map-requirements site).

Live-verified:
- `map_requirements` at `tasks.py:3608`; `feature_dir = _map_requirements_feature_dir(...)`
  at `:3727` (resolves the tasks/ read surface → coord); the WP-file read loop at
  `:3778-3781` (`for wp_file in tasks_dir.glob("WP*.md")`).
- `record_analysis` at `mission.py:1898`; `placement_ref = _resolve_record_analysis_placement_ref(...)`
  at `:1951` (coord-aware); `write_feature_dir = primary_feature_dir_for_mission(...)` at
  `:1980` (primary). The double-resolution: it resolves coord for placement, then primary
  for write — the planning-read leg should consume the one seam, not a manual second resolve.

**The fix:**
- map-requirements: route the WP `tasks/*.md` read dir through the seam with
  `kind=WORK_PACKAGE_TASK` (→ primary). Keep the spec.md read (already primary) consistent.
- record-analysis: collapse so the planning-read dir comes from the seam (WP01's
  `_planning_read_dir`); preserve the record-analysis **write** target as
  `primary_feature_dir_for_mission` (data-model.md KEEP: record-analysis write is OK on
  primary). Note: the **ANALYSIS_REPORT** kind is COORD-partition — record-analysis is NOT a
  `kind=SPEC` planning read; the collapse targets the **double-resolution of the planning
  read leg**, not the analysis-report placement. The dirty-tree allowlist is WP05's concern.

**Shared-`mission.py` serialization**: WP01 OWNS `mission.py`. This WP's record-analysis
edit is a well-justified out-of-map edit (record-analysis double-resolution collapse onto
WP01's chokepoint), serialized behind WP01 AND WP05 (WP05 also touches record-analysis —
see dependency note). This WP OWNS `tasks.py` + its two test files exclusively.

**Negative scope**: no new resolver (C-001); no migration (C-004); do NOT touch the
record-analysis dirty-tree allowlist (WP05) or the analysis-report write placement.

## Branch Strategy

- **Strategy**: `shared-lane` (Lane A; `tasks.py` exclusive + serialized `mission.py` edit)
- **Planning base branch**: `feat/gate-read-surface-completion`
- **Merge target branch**: `feat/gate-read-surface-completion`

> WP04 OWNS `tasks.py`. Its record-analysis `mission.py` edit serializes behind WP01.
> **Coordinate with WP05** (also touches record-analysis in `mission.py`): WP04 owns the
> double-resolution COLLAPSE (read leg), WP05 owns the dirty-tree allowlist — different
> concerns in the same function. Implement WP04's `mission.py` edit, then WP05 layers the
> allowlist; if implemented in parallel, the second to land rebases. See WP05 dependency.

## Subtasks & Detailed Guidance

### Subtask T014 – Red-first map-requirements repro via the entry point

- **Purpose**: Prove map-requirements reads WP tasks/*.md off coord on a coord-topology
  mission (the missed site) before fixing.
- **Files**: new `tests/specify_cli/cli/commands/agent/test_map_requirements_read_surface.py`.
- **Steps (red-first)**:
  1. Build a coord-topology fixture (composed `<slug>-<mid8>` primary dir) with WP `tasks/*.md`
     files on **primary** and an empty/absent `tasks/` on coord.
  2. Drive `map_requirements(...)` (the pre-existing entry point). Assert PRE-FIX it fails to
     find the WP files (reads coord) — the RED. POST-FIX it reads primary and maps requirements.
  3. Prove red against pre-WP04 `tasks.py`. Record evidence. Real ULID/mid8.

### Subtask T015 – Re-point map-requirements WP-tasks read onto the seam

- **Purpose**: FR-004 (the missed site).
- **Files**: `src/specify_cli/cli/commands/agent/tasks.py` (`:3727`, `:3778-3781`).
- **Steps**:
  1. Resolve the tasks/ read dir via the seam with `kind=WORK_PACKAGE_TASK` (→ primary)
     instead of `_map_requirements_feature_dir` (→ coord), for the WP-file glob at `:3778`.
  2. If `_map_requirements_feature_dir` also resolves a STATUS surface for a non-planning
     read, leave that leg; only the WORK_PACKAGE_TASK read moves (C-002).
  3. Use `resolve_planning_read_dir(repo_root, slug, kind=WORK_PACKAGE_TASK)` (tasks.py may
     call the resolver seam directly — canonical, not a parallel resolver).
- **Notes**: Confirm `WORK_PACKAGE_TASK` is PRIMARY-partition (data-model.md says yes).

### Subtask T016 – Collapse record-analysis double-resolution (planning read leg)

- **Purpose**: FR-009 — one seam, no manual coord-then-primary double-resolve.
- **Files**: `src/specify_cli/cli/commands/agent/mission.py` (`record_analysis`, `:1898-1990`;
  out-of-map edit serialized behind WP01).
- **Steps**:
  1. Where record-analysis resolves a PLANNING-artifact read dir via a manual coord-then-
     primary sequence, replace with WP01's `_planning_read_dir(repo_root, slug,
     artifact_type=...)`.
  2. Preserve the record-analysis **write** anchor (`primary_feature_dir_for_mission` at
     `:1980`) — record-analysis writes ANALYSIS_REPORT to primary is a KEEP (data-model.md).
  3. Do NOT touch `_resolve_record_analysis_placement_ref` placement semantics beyond the
     planning-read collapse; the dirty-tree allowlist is WP05.
- **Notes**: Be precise about which leg is the "planning read" vs the "analysis-report
  write/placement". Only the read leg collapses onto the seam.

### Subtask T017 – Record-analysis collapse: AST dedup guard (NOT a red-first behavioral test)

> **Remediation (reviewer-renata post-tasks):** the record-analysis double-resolution
> collapse is **behavior-neutral** — it is a pure dedup with no observable behavior delta,
> so a behavioral red-first test CANNOT go RED on the un-collapsed code. The previously
> prescribed proof — `assert read_dir == resolve_planning_read_dir(...)` or a spy on the
> resolver — is **tautological** (it pins the implementation to itself; green-before-and-
> after). Do NOT claim a behavioral red-first this WP cannot deliver. The honest proof is a
> **structural AST dedup guard** asserting the double-resolution code path is GONE.

- **Purpose**: Prove the manual coord-then-primary double-resolution is eliminated — the
  read leg now flows through the single seam — via a structural (AST) guard, labeled as a
  **dedup guard**, not a behavioral red-first.
- **Files**: new `tests/specify_cli/cli/commands/agent/test_record_analysis_double_resolution.py`.
- **Steps**:
  1. AST-scan the `record_analysis` function body (`mission.py:1898-1990`): assert it no
     longer contains the manual coord-then-primary **double-resolution** code path for the
     planning read — concretely, the planning-read leg does NOT call
     `primary_feature_dir_for_mission` (or a manual coord-resolve-then-primary-resolve
     sequence) for the READ; it calls the single seam (`_planning_read_dir` /
     `resolve_planning_read_dir`) exactly once for that read.
  2. Assert the record-analysis **write** anchor (`primary_feature_dir_for_mission` at
     `:1980`) is **still present** (the write KEEP is preserved — the dedup removes only the
     read-leg duplicate resolution).
  3. **Anti-vacuity:** prove the guard is non-vacuous WITHOUT depending on the production
     mutation — feed the AST scanner a synthetic snippet that DOES contain the manual
     double-resolution and assert it FLAGS; feed the collapsed snippet and assert it PASSES.
     (Mirrors WP06's mandatory synthetic-AST self-test pattern.)
  4. The genuine **behavioral red-first** for WP04 is carried by the map-requirements leg
     (T014) — that is the only observable behavior delta in this WP. Label T017 explicitly
     as a structural dedup guard so a reviewer does not expect a behavioral red-run.
- **Notes**: This cascades into WP10 T031 — record_analysis has no observable PLANNING-read
  behavior delta post-collapse, so WP10 must NOT assert "planning==primary" for
  record_analysis (it would be vacuous); see the WP10 remediation.

## Test Strategy

- `pytest tests/specify_cli/cli/commands/agent/test_map_requirements_read_surface.py tests/specify_cli/cli/commands/agent/test_record_analysis_double_resolution.py -q`.
- Red-first evidence for both.
- `ruff check` + `mypy` on `tasks.py` and the touched `mission.py` region — zero issues,
  no suppressions.

## Definition of Done

- [ ] map-requirements WP `tasks/*.md` read routed through the seam (`kind=WORK_PACKAGE_TASK`,
  → primary); STATUS legs untouched.
- [ ] record-analysis planning-read double-resolution collapsed onto the seam; analysis-report
  WRITE target (`primary_feature_dir_for_mission`) preserved.
- [ ] dirty-tree allowlist + analysis-report placement NOT touched (deferred to WP05).
- [ ] map-requirements: red-first behavioral test via the real entry point; RED pre-fix
  (reads coord); GREEN post-fix (reads primary); composed `<slug>-<mid8>` fixture (NFR-002).
- [ ] record-analysis: **AST dedup guard** (NOT a behavioral red-first) asserting the
  double-resolution code path is gone + the write anchor preserved + a synthetic-AST
  self-test proving non-vacuity. Explicitly labeled a dedup guard.
- [ ] ruff + mypy clean; record-analysis `mission.py` edit recorded as out-of-map rationale;
  WP05 coordination noted.

## Risks & Mitigations

- **WP05 collision in `record_analysis`**: both edit the same function. Mitigation: WP04 =
  read-leg collapse, WP05 = allowlist; serialize (WP04 lands first or rebase). Dependency
  edge keeps WP04 behind WP01; WP05 depends on WP04 (see WP05) to serialize the shared
  function.
- **Conflating the write/placement with the read leg**: Mitigation: T016 step 2/3 isolates
  the read leg only.
- **map-requirements STATUS leg**: Mitigation: only the WORK_PACKAGE_TASK read moves.

## Review Guidance

- Confirm only the WORK_PACKAGE_TASK read in map-requirements moved (STATUS legs intact).
- Confirm record-analysis WRITE target is unchanged (primary) and only the planning READ leg
  collapsed onto the seam.
- Confirm the record-analysis proof is an **AST dedup guard** (double-resolution gone +
  write anchor preserved + synthetic-AST self-test), NOT a tautological
  `read_dir == seam_result` / spy-on-resolver assertion. Reject a behavioral red-first claim
  for the collapse (it is behavior-neutral and cannot deliver one).
- Confirm the dirty-tree allowlist is untouched here (WP05 owns it).
- Confirm the **map-requirements** red-first drove the real CLI entry point with a composed
  `<slug>-<mid8>` fixture and proved RED on pre-fix code.

## Activity Log

- 2026-06-24T08:00:00Z – system – Prompt created.
- 2026-06-24T15:37:29Z – claude:opus:python-pedro:implementer – shell_pid=4038275 – Assigned agent via action command
- 2026-06-24T15:55:36Z – claude:opus:python-pedro:implementer – shell_pid=4038275 – FR-004/#2107: re-pointed map-requirements WP tasks/*.md read onto the kind-aware seam (resolve_planning_read_dir kind=WORK_PACKAGE_TASK -> primary). Behavioral red-first via real map-requirements CLI entry point with composed <slug>-<mid8> fixture: RED on pre-fix (globs empty coord tasks/ -> 'Unknown WP IDs'), GREEN post-fix (reads primary). FR-009/#2102: collapsed record-analysis manual coord-then-primary double-resolution onto the canonical resolve_planning_read_dir seam (kind=_kind_for_artifact('spec')). Behavior-NEUTRAL dedup proven by AST guard (manual primary_feature_dir_for_mission gone + write KEEP preserved + synthetic-AST non-vacuity self-test) -- NOT a tautological behavioral red-first. Rebased onto latest target (lane base WP01 _planning_read_dir helper was lane-local; merged target uses resolve_planning_read_dir directly); seam call/AST-guard re-pointed accordingly, non-vacuity re-proven. ruff clean; mypy 3 pre-existing mission.py no-any-return only (none in edited region). mission.py edit confined to record_analysis (disjoint from WP02 setup_plan); dirty-tree allowlist untouched (WP05).
- 2026-06-24T15:58:34Z – claude:opus:python-pedro:implementer – shell_pid=4038275 – FR-004/#2107 map-requirements re-point onto kind-aware seam (resolve_planning_read_dir kind=WORK_PACKAGE_TASK -> primary); behavioral red-first via real CLI entry point + composed slug-mid8 fixture (RED on empty coord tasks/, GREEN on primary). FR-009/#2102 record-analysis double-resolution collapsed onto resolve_planning_read_dir (kind=_kind_for_artifact('spec')); behavior-neutral dedup proven by AST guard + synthetic non-vacuity self-test (NOT tautological). Rebased onto latest target; ruff clean; mypy 3 pre-existing only; mission.py edit confined to record_analysis; dirty-tree allowlist untouched (WP05).
- 2026-06-24T16:00:34Z – claude:opus:python-pedro:implementer – shell_pid=4038275 – Lane-e code 233437e57; status from main
- 2026-06-24T16:00:35Z – claude:opus:reviewer-renata:reviewer – shell_pid=4093154 – Started review via action command
- 2026-06-24T16:06:43Z – user – shell_pid=4093154 – Review passed: map-requirements behavioral red-first VERIFIED by reviewer (reverted tasks.py edit -> RED 'Unknown WP IDs / No WP files found in tasks/' on composed slug-mid8 fixture, restored -> GREEN). record-analysis AST dedup guard is NON-VACUOUS (reverted mission.py collapse -> production guard FAILS on primary_feature_dir_for_mission, self-tests independent; restored -> green); collapse is behavior-NEUTRAL (SPEC is PRIMARY-partition -> resolve_planning_read_dir == primary_feature_dir_for_mission, byte-identical dir). Seam-consistency OK: no _planning_read_dir chokepoint on merged target; WP04 uses canonical resolve_planning_read_dir with explicit kind= (4th consistent site), not a path reconstruction -> FR-010 ratchet clean. C-002 no over-reach: tasks.py = single tasks_dir line (STATUS/TASKS_INDEX/spec.md anchors untouched); mission.py confined to record_analysis (disjoint from setup_plan). ruff clean; tasks.py mypy clean; mission.py 3 no-any-return verified pre-existing at parent (none in edited region).
