---
work_package_id: WP07
title: move-task coord-lane staging via authority path (+
dependencies:
- WP01
requirement_refs:
- C-002
- FR-001
- FR-010
- NFR-005
tracker_refs:
- '2555'
- '2580'
- '2160'
planning_base_branch: feat/loop-friction-quickwins-2
merge_target_branch: feat/loop-friction-quickwins-2
branch_strategy: Planning artifacts for this mission were generated on feat/loop-friction-quickwins-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/loop-friction-quickwins-2 unless the human explicitly redirects the landing branch.
created_at: '2026-07-12T19:30:00Z'
subtasks:
- T025
- T026
- T027
- T028
phase: Coord-lane recovery
agent: claude
history:
- at: '2026-07-12T19:30:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-07; narrowed to staging/router per squad — NO commit_guard exemption)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_move_task.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_authority_staging.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_authority_staging.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 — move-task coord-lane staging via authority path (+ #2580)

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objectives & Success Criteria

`move-task` on a coord-topology lane routes planning-artifact staging through the authority path so no
manual `git restore` is ever needed — with **NO** `commit_guard` exemption and STATUS_STATE placement
byte-for-byte unchanged. Also route the #2580 `_mt_persist_wp_file` shell_pid write through the canonical
writer so it stops diverging.

- **SC (FR-010)**: coord-topology `move-task --to for_review` with untracked planning artifacts on primary resolves via the authority path; no manual `git restore` sequence.
- **SC (dual pin)**: STATUS_STATE ref/event byte-identical pre/post AND zero `kitty-specs/` entries committed on the lane branch.

## Context & Constraints — READ CAREFULLY (coordination-aware, C-002)

The coord line this once feared is **already MERGED** into base (partition-lock #168;
`implement-loop-coord-authority-completion` #2194; `coord-authority-trio-degod` #2545). So this is "do NOT
regress the shipped partition-lock #168 invariants", not "sequence with in-flight work".

**Architectural facts (verified by the post-plan squad):**
- WP-file commits ALREADY route to **primary** via `coordination/commit_router.py` (WORK_PACKAGE_TASK never
  routes to coordination; a protected primary is REFUSED with guidance, not committed to the lane). The
  `skip_target_commit` pre-gate (`tasks_move_task.py:~1379-1409`) already skips the lane commit under coord.
- The friction is a MANUAL agent recovery after `commit_guard.block_mission_specs` refuses a lane commit —
  there is no `git restore` in the code; the durable fix is code-side routing.

**KEEP invariants (hard):**
- **K-6**: do NOT add a `commit_guard.block_mission_specs` exemption. WP-file commits already route to
  primary, so no lane `kitty-specs/` commit is needed; an exemption would weaken partition-lock #168's
  close-by-construction guard. (`commit_guard.py` is NOT in this WP's owned_files by design.)
- **K-7 (Directive-044)**: reuse WP01's `resolve_planning_artifact_staging` seam — the "should this
  kitty-specs diff block?" decision lives in ONE place; do not fork a parallel move-task recovery.
- **K-4**: do NOT touch `_mt_resolve_status_placement_ref` / `_collect_status_artifacts` /
  `_primary_bundle_status_artifacts` — changing how status artifacts bundle would perturb STATUS_STATE placement.
- Re-verify line-anchors before editing: the plan's pre-degod `:299`/`:1302-1390` are stale; the true locus
  is the router-routing decision. Read the current code first.

Depends on **WP01** (the canonical runtime-field helper + `resolve_planning_artifact_staging`).
Plan: IC-07. Research: R-10. Contract: C-E1.

## Branch Strategy

- **Planning base branch / Merge target**: feat/loop-friction-quickwins-2

## Subtasks & Detailed Guidance

### Subtask T025 — Route staging through the authority path (complexity-aware locus)

- **Steps**: Ensure move-task's planning-artifact staging resolves through the authority path
  (`commit_router` WORK_PACKAGE_TASK routing + `skip_target_commit` @ `~1379-1408`), reusing WP01's
  `resolve_planning_artifact_staging`, so untracked-on-primary planning artifacts are staged/committed on
  the resolved primary surface and the lane branch is never asked to commit `kitty-specs/`. No guard exemption.
- **COMPLEXITY GUARD (pedro)**: land the staging call in `_mt_write_and_commit_wp_file` (@ `:1350`, cyclomatic
  ~5) or a NEW small helper — **NOT** in `_mt_commit_wp_file` (@ `:1412`, cyclomatic 11; a branch there
  breaches 15). While here (SAFE campsite), fold the 3× duplicated `write_text_within_directory(...)`
  fallback-write (@ `:1389/:1453/:1459`) into one `_write_wp_fallback(...)` helper.
- **Files**: `src/specify_cli/cli/commands/agent/tasks_move_task.py`.

### Subtask T026 — #2580: route `_mt_persist_wp_file` shell_pid via the canonical writer (SSOT)

- **Steps**: `_mt_persist_wp_file` (@ `:1510`) currently does a bare `set_scalar(updated_front, "shell_pid", …)`
  (@ `:1524`) with NO `shell_pid_created_at` baseline — a 4th divergent writer that also breaks the co-write
  invariant. Route it through the ONE canonical writer **`frontmatter.write_shell_pid_claim`** (@
  `frontmatter.py:335`) — the same symbol WP01 designates — so shell_pid + its baseline are co-written. Name
  that exact symbol; do not introduce a parallel write.
- **Files**: `tasks_move_task.py`.

### Subtask T027 — Red-first dual regression (+ #2580 pin)

- **Steps**: New `tests/specify_cli/cli/commands/agent/test_tasks_move_task_authority_staging.py`: a
  coord-topology `move-task --to for_review` with untracked planning artifacts on primary → (a) STATUS_STATE
  ref/event byte-identical pre/post, AND (b) zero `kitty-specs/` entries committed on the lane branch, AND
  (c) no manual `git restore` needed (the move completes in one pass). **Also (d) #2580 pin**: `shell_pid` +
  its `shell_pid_created_at` baseline persist byte-identically through the canonical `write_shell_pid_claim`
  via `_mt_persist_wp_file` (the "no 4th divergent writer" closure).
- **Files**: the new test file.

### Subtask T028 — Arch guard against placement drift

- **Steps**: Add a lightweight guard (unit or arch test) asserting the WP07 diff does not touch
  `_mt_resolve_status_placement_ref` / `_collect_status_artifacts` / `_primary_bundle_status_artifacts`.
- **Files**: the new test file (or an existing arch test if one fits its owned surface).

## Definition of Done

- Staging routed via the authority path (no `commit_guard` edit); #2580 writer canonicalized; dual regression green; arch guard in place.
- `PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/agent/test_tasks_move_task_authority_staging.py -q` green; `ruff` + `mypy` clean.
- Serial daemon/real-port note: if the test drives real status emission, run it `-n0`.

## Risks & Reviewer Guidance

- **Risk (highest)**: any change to status bundling perturbs STATUS_STATE placement (second split-brain) — reviewer verifies T027(a) + T028.
- **Risk**: temptation to punch a `commit_guard` exemption — reviewer REJECTS any `block_mission_specs` change; the routing fix must make it unnecessary.
