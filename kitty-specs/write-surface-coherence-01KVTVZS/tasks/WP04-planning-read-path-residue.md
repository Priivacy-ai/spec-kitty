---
work_package_id: WP04
title: Planning read-path residue
dependencies:
- WP01
requirement_refs:
- FR-006
tracker_refs: []
planning_base_branch: feat/write-surface-coherence
merge_target_branch: feat/write-surface-coherence
branch_strategy: Planning artifacts for this mission were generated on feat/write-surface-coherence. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-surface-coherence unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
phase: Phase 3 - Read-path symmetry
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2609466"
history:
- at: '2026-06-23T19:28:09Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/missions/_read_path_resolver.py
- src/specify_cli/coordination/surface_resolver.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Planning read-path residue

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: src/specify_cli/missions/`.

---

## Objective

Once planning **writes** are primary-always (WP01–WP03), the planning **read** path must
resolve the **PRIMARY** feature dir for primary-partition kinds — a stale pre-mission
coord husk copy must not shadow primary truth (the **#2062** stale-coord class,
INV-4 / FR-006). **Preserve** the C-005 KEEP transients (#1718 create-window, #1848
coord-deleted) — only primary-partition planning-artifact reads route to primary;
status reads keep the topology-aware seam and its transients.

**This WP runs in PARALLEL with WP02/WP03** — it depends only on WP01 (the partition).

## The real mechanism (DECISION 4 — NOT a no-op)

`resolve_handle_to_read_path` (`_read_path_resolver.py:843`) returns **ONE** mission dir
chosen by topology. After WP01–WP03 move planning writes to primary, a **coord-topology**
mission's planning artifacts physically live on the **primary** feature dir — but
`resolve_handle_to_read_path` under coord topology can still resolve the **coord** dir
for those reads. Result: FR-006 / #2062 stays OPEN — a stale coord husk shadows the real
primary planning artifacts.

**The fix is a real per-kind read split, not an investigation**: planning-artifact reads
must resolve the **PRIMARY** feature dir (`primary_feature_dir_for_mission` — already the
sanctioned pattern at `mission.py:830`, `:1226`, `:1273`, `:1903`), while **status**
reads keep the topology-aware seam (`resolve_handle_to_read_path` / `resolve_status_surface`).
This WP must:
- (a) identify the **planning-read** callers that currently go through the topology seam
  for a primary-partition artifact and route them to the primary feature dir, and
- (b) clean up the husk residue (`_coord_mid8` at `surface_resolver.py:473`, the
  `consults_coord_husk` arms at `_read_path_resolver.py:961-963`, the `topology is None`
  husk-consulting arms) for the planning-read case — **PRESERVING** the C-005 KEEP
  transients (#1718 create-window, #1848 coord-deleted).

## Context & Constraints

Ground truth: [spec.md](../spec.md) FR-006, C-006; [plan.md](../plan.md) IC-04;
[research.md](../research.md) D-5; [data-model.md](../data-model.md) INV-4.

The read side converged in mission 01KVRJ6P and is **topology-gated** — study these gates
before changing anything:
- `_read_path_resolver.py:336-415` `_resolve_existing_for_slug`: a stored coord-less
  topology (`SINGLE_BRANCH`/`LANES`) resolves PRIMARY before any husk probe (`:380-381`,
  the structural #2062 read-leg close). **Note #2062-residual** (memory): the coord-arm
  probes coord by disk-existence WITHOUT a `coordination_branch` for a flattened mission —
  watch that this WP does not re-introduce a coord-shadow for a primary-partition read.
- `_read_path_resolver.py:645-791` `_resolve_not_found`: same stored-topology gate
  (`:698-707`); DELETED/EMPTY transients at `:732-787` (C-005 KEEP — do NOT weaken).
- `_read_path_resolver.py:843` `resolve_handle_to_read_path`: the single read seam;
  `consults_coord_husk` derived from the stored topology (`:961-963`).
- `_read_path_resolver.py:1212` `primary_feature_dir_for_mission`: the primary-dir
  primitive to route planning reads through.
- `surface_resolver.py:503-528` `_husk_is_authoritative_surface`: gates the `.worktrees`
  short-circuit against the stored topology; `_coord_mid8` at `:473`.

## Branch Strategy

- **Strategy**: `shared-lane`
- **Planning base branch**: `feat/write-surface-coherence`
- **Merge target branch**: `feat/write-surface-coherence`

> No surface overlap with WP02/WP03 (different modules) — genuinely parallel.

## Subtasks & Detailed Guidance

### Subtask T017 – Route primary-partition planning reads to the PRIMARY feature dir

- **Files**: `_read_path_resolver.py`, `surface_resolver.py`.
- **Steps**:
  1. Trace the planning-artifact read path: how `spec.md`/`tasks.md`/`tasks/WP*.md` are
     located for a **coord-topology** mission post-WP01. Identify each caller that resolves
     a planning artifact via `resolve_handle_to_read_path` / the topology seam (rather than
     directly via `primary_feature_dir_for_mission`).
  2. **Route primary-partition reads to PRIMARY**: a primary-partition artifact
     (`_PRIMARY_ARTIFACT_KINDS`, imported from `mission_runtime` — do NOT add a parallel
     classification, C-006 / NFR-004) resolves from `primary_feature_dir_for_mission`
     regardless of topology, mirroring the write-side INV-5 symmetry. The status read
     surface keeps the topology-aware seam.
  3. **Clean the husk residue** for the planning-read case: the `consults_coord_husk`
     arms (`_read_path_resolver.py:961-963`), the `topology is None` (corrupt-meta)
     husk-consulting arms, and the `surface_resolver` `.worktrees` short-circuit
     (`_husk_is_authoritative_surface:503-528`, `_coord_mid8:473`) must not return a coord
     husk dir for a primary-partition read. Narrow them to STATUS reads.
- **DoD (DECISION 4 — line-cited, NO green-pin escape)**: the WP MUST produce a
  line-cited deliverable naming the **exact resolver line(s) changed** to route a
  primary-partition planning read to primary (e.g. "`_read_path_resolver.py:NNN`: gated
  the husk arm behind `kind not in _PRIMARY_ARTIFACT_KINDS`" or "routed planning reads at
  caller `<file>:NNN` through `primary_feature_dir_for_mission`"). If — for a SPECIFIC
  caller — the read is genuinely already primary, the DoD must **cite the exact line that
  proves it** (e.g. "`mission.py:830` already calls `primary_feature_dir_for_mission`")
  AND state which caller(s) needed the new gate. A bare "investigated; no change needed"
  / "green-before-and-after pin" for the WHOLE WP is **rejected** (DIRECTIVE_034): the
  coord-topology planning-read residue is real (the write-side moved), so at least one
  line-cited routing change is expected; a no-op claim requires a per-caller line-cited
  justification proving every planning read already resolves primary.
- **Notes**: The likely real residue is the coord-topology branch of the read seam and the
  `.worktrees` husk short-circuit. Verify BOTH a flattened-with-stale-husk mission AND a
  coord-topology-with-stale-husk mission read the PRIMARY planning artifacts.

### Subtask T018 – Preserve the C-005 KEEP transients

- **Files**: `_read_path_resolver.py`, `surface_resolver.py`.
- **Steps**:
  1. The #1718 create-window (`UNMATERIALIZED` → primary) and #1848 coord-deleted
     (`DELETED` → loud `CoordinationBranchDeleted` hard-fail) status transients MUST be
     untouched. Confirm `probe_coord_state` (`_read_path_resolver.py:282-320`) and the
     `_resolve_not_found` DELETED/EMPTY arms (`:732-787`) still behave for STATUS reads.
  2. Add NOTHING that weakens the fail-closed `DELETED` hard-fail (data-loss guard).
- **Notes**: The distinction is artifact-class: PLANNING reads stop consulting the husk;
  STATUS reads keep the create-window / coord-deleted transients (C-005 from 01KVRJ6P).

### Subtask T019 – Red-first stale-coord-shadow test (#2062 class, DIRECTIVE_034)

- **Files**: `tests/missions/` or `tests/specify_cli/` (locate the existing
  `_read_path_resolver` / surface-resolver test module).
- **Steps (red-first)**:
  1. Write the failing test FIRST through the pre-existing read entry point
     (`resolve_handle_to_read_path` / the planning-artifact read used by finalize-tasks):
     seed a mission whose PRIMARY `spec.md` carries the truth and a STALE `-coord` husk
     copy carries different content; assert the read resolves the PRIMARY content for the
     planning artifact.
  2. The headline variant is the **coord-topology** case (coord mission, primary planning
     truth, stale husk) — that is the variant this mission's write-side change makes
     correct and the one that proves the T017 routing change. Also add the
     flattened-with-stale-husk variant.
  3. Prove **red** on the pre-fix read path: the coord-topology planning read resolves the
     stale husk content pre-fix (RED), the primary content post-fix (GREEN). This is a
     genuine behavior change, not a green-pin — drive red by running against the unfixed
     resolver (revert + restore). A green-before-and-after pin is acceptable ONLY for a
     specific caller the T017 line-cited deliverable proves is already-primary; the
     coord-topology variant MUST be red-first.
  4. Realistic fixtures: real ULID/mid8, real `<slug>-<mid8>` dir, real `.worktrees/<slug>-<mid8>-coord/...` husk path.

## Test Strategy

- `pytest tests/ -k "read_path or surface_resolver or stale_coord or 2062" -q`.
- `ruff check` + `mypy` on owned files — zero issues, no suppressions.

## Risks & Mitigations

- **Over-reach**: weakening a status transient to "fix" a planning read re-opens #1718/
  #1848. Mitigation: T018 pins the transients; only PLANNING-kind reads change.
- **False no-op (DECISION 4)**: claiming "read path already correct" without a per-caller
  line-cited proof masks the real coord-topology residue. Mitigation: T017 DoD requires a
  line-cited deliverable (the changed resolver line, OR a per-caller already-primary
  citation); the coord-topology T019 variant must be red-first.
- **Parallel-WP merge**: WP04 lands alongside WP02/WP03; no shared files, so merge is
  clean — but rebase on WP01 first.

## Review Guidance

- Verify primary-partition reads resolve PRIMARY under coord topology with a stale husk.
- Verify the **line-cited deliverable** (DECISION 4): the exact resolver line(s) changed,
  or a per-caller citation proving already-primary. Reject a whole-WP "no change needed"
  claim without per-caller line citations.
- Verify the coord-topology T019 variant is genuinely red-first (request red-run evidence).
- Verify #1718 create-window and #1848 coord-deleted transients are intact.

## Activity Log

- 2026-06-23T19:28:09Z – system – Prompt created.
- 2026-06-23T20:35:04Z – claude:opus:python-pedro:implementer – shell_pid=2561871 – Assigned agent via action command
- 2026-06-23T20:55:56Z – claude:opus:python-pedro:implementer – shell_pid=2561871 – Per-kind planning READ split (FR-006/INV-4/INV-5). resolve_planning_read_dir in _read_path_resolver.py: _PRIMARY_ARTIFACT_KINDS read -> primary_feature_dir_for_mission (topology-blind); STATUS kinds -> candidate_feature_dir_for_mission (topology seam, C-005 transients intact); classification imports _PRIMARY_ARTIFACT_KINDS from mission_runtime.artifacts (no parallel classification, C-006). Routed 2 planning-read callers in agent/tasks.py: _resolve_wp_slug (tasks/ -> WORK_PACKAGE_TASK), _check_unchecked_subtasks (tasks.md -> TASKS_INDEX). Left workflow.py:2103/2109 (worktree-anchored D-1) + review/cycle.py (review-cycle, not primary-partition) untouched per DIRECTIVE_024. Red-first: tests/missions/test_wp04_planning_read_split.py - no-op'd the split on pre-fix code, 6 planning tests RED (resolved .worktrees/-coord husk -> STALE_HUSK), 3 status/transient GREEN; restored -> 9 GREEN. KEEP transients byte-unchanged (probe_coord_state EMPTY/DELETED + DELETED hard-fail, #1718/#1848). Diff-scoped ruff exit 0; mypy clean. --force used ONLY for the inherited-lane-kitty-specs guard (mission spec verified present on feat/write-surface-coherence); zero kitty-specs in the WP04 diff. Pre-existing lane-base failures (WP01 resolve_placement_only kind break fixed by WP02/WP03; unrelated task_helpers dead-symbol gate) identical pre/post - zero new failures from this diff.
- 2026-06-23T20:56:28Z – claude:opus:python-pedro:implementer – shell_pid=2561871 – WP04 per-kind planning read split ready for review (full deliverable in commit c87b0ba6d).
- 2026-06-23T20:57:17Z – claude:opus:python-pedro:implementer – shell_pid=2561871 – WP04 per-kind planning read split ready for review (commit c87b0ba6d on lane-c). Surfacing for_review on the primary/coord status board (dual-surface divergence is the mission target itself).
- 2026-06-23T20:58:27Z – claude:opus:reviewer-renata:reviewer – shell_pid=2609466 – Started review via action command
- 2026-06-23T21:06:12Z – user – shell_pid=2609466 – Review PASSED (reviewer-renata; DIR-001/024/030/032/041 applied). Reviewer re-ran tests: WP04 test_wp04_planning_read_split.py 9/9 GREEN + KEEP-transient test_wp17_husk_arm_collapse.py GREEN (26 passed). Cross-lane judgment: ALL 32 broad failures share root cause 'resolve_placement_only() missing kind' = WP01 break threaded by WP02/WP03 (resolved at merge); PROVED base by reverting WP04 source to WP01 base (d30927194) -> same representative failures persist identically; zero failures attributable to WP04 diff. Red-first VERIFIED by reviewer: no-op'd the split -> exactly 6 planning-read tests RED (resolve STALE_HUSK), 3 status/transient GREEN = behavioral not green-pin. C-006: imports single _PRIMARY_ARTIFACT_KINDS (5 planning kinds in, STATUS_STATE out), no parallel classification. C-005 KEEP transients #1718/#1848 byte-unchanged. Citations spot-checked: workflow.py:2102-2109 + review/cycle.py:266 correctly untouched; both changed callers were real kind-blind planning-read residue. ruff+mypy clean; zero kitty-specs in WP04 diff. --force: inherited-lane-kitty-specs guard only (spec.md verified present on feat/write-surface-coherence; not part of WP04 diff).
