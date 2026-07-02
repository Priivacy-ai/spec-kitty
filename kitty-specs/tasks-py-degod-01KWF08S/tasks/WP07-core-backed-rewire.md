---
work_package_id: WP07
title: Core-backed rewire — map_requirements + status
dependencies:
- WP06
requirement_refs:
- FR-007
- NFR-004
tracker_refs: []
planning_base_branch: design/degod-tasks-2116
merge_target_branch: design/degod-tasks-2116
branch_strategy: Planning artifacts for this mission were generated on design/degod-tasks-2116. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/degod-tasks-2116 unless the human explicitly redirects the landing branch.
subtasks:
- T030
- T031
- T032
phase: Phase 4 - Body thinning
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3338460"
history:
- at: '2026-07-01T15:16:35Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: tests/specify_cli/cli/commands/agent/test_tasks_core_backed_orchestration.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_tasks_core_backed_orchestration.py
execution_mode: code_change
owned_files:
- tests/specify_cli/cli/commands/agent/test_tasks_core_backed_orchestration.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – Core-backed rewire (map_requirements + status)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `randy-reducer`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Thin the two **core-backed** bodies to **≤150 LOC** orchestrators over the WP04/WP05 cores + ports. (Split from the old single 4-body WP per the post-tasks squad — this slice is the core-backed half; WP08 is the coreless half.)

- `map_requirements` → orchestrator over the WP04 `plan_mapping` core + ports (write via port); ≤150 LOC.
- `status` → orchestrator over the WP05 `build_status_view` core + the `Render` port; ≤150 LOC.
- WP01 golden byte-identical for both; ruff + mypy clean.

## Context & Constraints

- Read `plan.md` (IC-04), `spec.md` (FR-007, NFR-004).
- Both bodies already route through their cores (WP04/WP05 wiring); this WP completes the port-based thinning.
- **NFR-004**: each body ≤150 LOC; extracted glue helpers ≤150 LOC / CC≤15 (enforced by the WP09 LOC gate).
- `status`'s Render migration here must be **scoped** so WP09's render-seam sweep does not re-touch/re-conflict it (coordinate the boundary — migrate `status`'s own render calls, leave the rest to WP09).
- **Ownership/leeway**: own `test_tasks_core_backed_orchestration.py`; the two body edits are documented **leeway edits** to `tasks.py` (owned by WP09).

## Branch Strategy

- **Planning base branch**: `design/degod-tasks-2116`
- **Merge target branch**: `design/degod-tasks-2116`

## Subtasks & Detailed Guidance

### T030 — Thin `map_requirements`
Reduce to a thin orchestrator over the WP04 `plan_mapping` core + ports (frontmatter write via port). ≤150 LOC. **Route the co-located canonicalizer fold at `tasks.py:2647-2648` (`primary_feature_dir_for_mission(_canonicalize_primary_read_handle(...))`) through `FsReader.primary_anchor_dir`** (the WP02 port method built for exactly this fold — this is its named consumer, per the WP02 review Note A; keeps it from being dead infrastructure).

### T031 — Thin `status`
Reduce to a thin orchestrator over the WP05 `build_status_view` core + the `Render` port. ≤150 LOC. Scope the Render migration to `status`'s own sites.

### T032 — Prove parity
WP01 golden byte-identical for both commands. `test_tasks_core_backed_orchestration.py` asserts executed side-effects via Fake ports. ruff + mypy clean.

## Test Strategy

- `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_core_backed_orchestration.py tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py -q`

## Risks & Mitigations

- **Render double-migration**: coordinate the `status` Render boundary with WP09 to avoid re-conflict.

## Out-of-map edits

- `src/specify_cli/cli/commands/agent/tasks.py` (`map_requirements`, `status` bodies) — documented leeway; `tasks.py` owned by WP09. Strictly-linear chain → no parallel collision.

## Review Guidance

- Confirm both bodies ≤150 LOC over their cores, `status` Render scoped, golden byte-identical.

## Activity Log

- 2026-07-01T15:16:35Z – system – Prompt created.
- 2026-07-01T23:50:56Z – claude:opus:randy-reducer:implementer – shell_pid=3268686 – Assigned agent via action command
- 2026-07-02T00:24:27Z – claude:opus:randy-reducer:implementer – shell_pid=3268686 – map_requirements 56 LOC (Typer) / _do_map_requirements 47 LOC + status 24 LOC (Typer) / _do_status 30 LOC over WP04/WP05 cores; primary_anchor_dir wired as fold consumer; commit_artifact threads target_branch; Render port scoped to status sites (indent=2 envelope); write-timing + aggregation byte-identical; golden 42 + WP04/WP05 tests green; strict mypy (src+test together) clean.
- 2026-07-02T00:25:28Z – claude:opus:reviewer-renata:reviewer – shell_pid=3338460 – Started review via action command
- 2026-07-02T00:32:41Z – user – shell_pid=3338460 – APPROVE. Status --json byte-identical: original print(json.dumps(result,indent=2)) reproduced by _StatusRender.json_envelope (indent=2, default seps, no sort_keys) over identical result-dict keys/order from build_status_view; golden test_tasks_cli_contract status --json green. 'Indent divergence' = generic WP02 RealRender.json_envelope uses compact json.dumps (matches the many compact inline sites); status is the one indent=2 site so WP07 made a status-scoped override — status output correct/byte-identical NOW, WP09 reconciles the generic seam (acceptable, not deferred). map_req write-timing: _mr_write_frontmatter runs BEFORE _mr_stale_gate (partial-write-on-refusal preserved). primary_anchor_dir: fold routed via ports.fs.primary_anchor_dir; C-002 canonicalizer+primary_feature_dir_for_mission co-located inside RealFsReader adapter; _MapReqCoordRouter threads target_branch (test asserts) + re-resolves commit_for_mission for @patch seam; _StatusRender binds module console. LOC: map_requirements 56 / _do 47, status 24 / _do 30, all _mr_/_st_ helpers <=150 (max 61). ruff C901 + full clean; mypy --strict --no-incremental both files Success; zero # noqa/# type:ignore. agent/ suite 908 passed 2 xfailed 0 failed (xfails pre-existing SC6 flattened gaps); WP07 orchestration test 5 passed. Anti-patterns 1-8 PASS (tests drive _do_* production paths, not synthetic; tasks.py leeway documented, linear chain WP07->WP09).
