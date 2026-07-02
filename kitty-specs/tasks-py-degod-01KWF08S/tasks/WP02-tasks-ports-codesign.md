---
work_package_id: WP02
title: TasksPorts co-design (stratified, two-capability WRITE)
dependencies:
- WP01
requirement_refs:
- C-001
- C-002
- C-005
- FR-003
- FR-009
- FR-010
tracker_refs: []
planning_base_branch: design/degod-tasks-2116
merge_target_branch: design/degod-tasks-2116
branch_strategy: Planning artifacts for this mission were generated on design/degod-tasks-2116. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/degod-tasks-2116 unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
phase: Phase 2 - Port seam
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "2827278"
history:
- at: '2026-07-01T15:16:35Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_ports.py
create_intent:
- src/specify_cli/cli/commands/agent/tasks_ports.py
- tests/specify_cli/cli/commands/agent/test_tasks_ports.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks_ports.py
- tests/specify_cli/cli/commands/agent/test_tasks_ports.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – TasksPorts co-design (stratified, two-capability WRITE)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `randy-reducer`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Define the injected capability boundary — **stratified**, with a **two-capability** coord WRITE port so Wave 2 reuses it — plus the FR-010 dir-equivalence proof that de-risks the read folds.

- 4 Protocols in `tasks_ports.py`: `FsReader` (coord READ); `CoordCommitRouter` with **two methods** `commit_status` + `commit_artifact`; `GitOps`; `Render` (dual-arm). Real + Fake adapters.
- Injection proven at `_do_<cmd>(*, ports=None)`; no `--ports` Typer flag.
- Stratification invariants + the FR-010 per-kind coord-fixture equivalence test are green.

## Context & Constraints

- Read `data-model.md` (§Ports), `contracts/ports-and-cores.md` (§Port protocols), `research.md` (D2, D8, D10).
- **#2072 predecessor has landed** (allowlist composite-keyed) — not blocked.
- **Two-capability WRITE port (research D2, binding — do NOT fuse into one `commit()`):** `commit_status(mission, event, *, capability)` over `emit_status_transition_transactional` (keyed `GuardCapability`; self-atomic via `BookkeepingTransaction`) + `commit_artifact(mission, paths, message, *, kind, policy)` over `commit_for_mission` (keyed `MissionArtifactKind`+policy, event-less). The Wave-2 consumers use disjoint halves (`implement.py`=commit_status only, `acceptance`=commit_artifact only writer, `move_task`=both) — a fused method is re-cut in Wave 2 (the C-006 failure). Atomicity is a property of the transactional emitter, not port packaging.
- **C-001**: `FsReader` (READ) and `CoordCommitRouter` (WRITE) are distinct ports.
- **C-002**: keep `primary_feature_dir_for_mission` + `_canonicalize_primary_read_handle` fold **co-located inside the adapter method** (intra-function gate → splitting turns it RED).
- **C-005**: `*, ports=None` on the extracted orchestrator helper, never the Typer `@app.command`.
- Rename result types off `CommitResult` (collides with `git/commit_helpers.py:424`) → e.g. `CommitStatusResult`/`CommitArtifactResult`.
- This WP creates the port module + the FR-010 proof; it does not thin command bodies.

## Branch Strategy

- **Planning base branch**: `design/degod-tasks-2116`
- **Merge target branch**: `design/degod-tasks-2116`

## Subtasks & Detailed Guidance

### T008 — Define the 4 Protocols
`FsReader` (`planning_read_dir(mission,*,kind)`, `wp_tasks_dir`, `primary_anchor_dir`); `CoordCommitRouter` (`feature_write_dir`, `commit_status(...)`, `commit_artifact(...)`); `GitOps`; `Render` (`human` + `json_envelope`). See `contracts/ports-and-cores.md`.

### T009 — Real adapters
Wrap the canonical seams: `FsReader` → `resolve_planning_read_dir` (+ co-located canonicalizer fold); `CoordCommitRouter.commit_status` → `emit_status_transition_transactional`; `.commit_artifact` → `commit_for_mission`; `GitOps` → porcelain reads; `Render` → rich + `json.dumps`. Rename result types.

### T010 — Fake adapters [P]
Deterministic in-memory Fakes for all 4 (record calls; return seeded values); no real I/O.

### T011 — Bundle + injection proof
`TasksPorts(fs, coord, git, render)` + `default_ports()`; registration-introspection test proving no `--ports` Typer flag + the orchestrator helper accepts an injected bundle (C-005).

### T012 — Stratification invariants
Unit-test: `FsReader is not CoordCommitRouter` (INV-1/C-001); `commit_status`/`commit_artifact` are co-equal methods over disjoint seams; canonicalizer fold intra-adapter (C-002); exactly 4 ports.

### T013 — FR-010 dir-equivalence proof artifact
For each in-scope `MissionArtifactKind` on the WP01 coord fixture, assert `resolve_feature_dir_for_mission == resolve_planning_read_dir(kind=…)` for the pre30 guard. This pins the correct `kind` per site (the in-file exemplars diverge — `add_history` uses `TASKS_INDEX`, finalize/list_dependents' other reads use `WORK_PACKAGE_TASK`) and de-risks WP06/WP08 before any rewire. Deliver here, not at WP06.

## Test Strategy

- `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_ports.py -q` + `ruff` + `mypy` on both new files.

## Risks & Mitigations

- **Program mis-shape**: a fused `commit()` mis-cuts the reference port. Keep two capabilities.
- **C-002 RED**: don't extract the canonicalizer fold across the boundary.
- **FR-010 parity break**: if the equivalence test fails for any in-scope kind, that kind's read is NOT byte-identical — escalate before the rewire.

## Review Guidance

- Confirm two-capability WRITE port, disjoint-seam wrapping, co-located fold, no-`--ports`-flag proof, pure Fakes, and a green per-kind equivalence artifact.

## Activity Log

- 2026-07-01T15:16:35Z – system – Prompt created.
- 2026-07-01T18:46:22Z – claude:opus:randy-reducer:implementer – shell_pid=2723601 – Assigned agent via action command
- 2026-07-01T19:16:26Z – claude:opus:randy-reducer:implementer – shell_pid=2723601 – TasksPorts: 4 ports (2-capability WRITE commit_status/commit_artifact over disjoint seams), Real+Fake adapters, injection proof (no --ports flag, _do(*,ports=None)), stratification invariants, FR-010 per-kind equivalence proven at guard-outcome level; pinned kinds move_task/finalize_tasks/list_dependents=WORK_PACKAGE_TASK. ruff+mypy clean, golden untouched. NOTE: strict blind==kind-aware path-equality is impossible-by-construction for primary kinds (the split-brain); routed-canonicalizer floor tightened 38->39 for the C-002 anchor.
- 2026-07-01T19:17:51Z – claude:opus:reviewer-renata:reviewer – shell_pid=2775358 – Started review via action command
- 2026-07-01T19:26:48Z – user – shell_pid=2775358 – Moved to planned
- 2026-07-01T19:31:08Z – claude:opus:randy-reducer:implementer – shell_pid=2795574 – Started implementation via action command
- 2026-07-01T19:35:52Z – claude:opus:randy-reducer:implementer – shell_pid=2795574 – Cycle 2: corrected move_task FR-010 pin to STATUS_STATE (coord-husk-preserving) + red-first hazard assertion; guard-only sites unchanged. Tests green, ruff+mypy clean.
- 2026-07-01T19:36:42Z – claude:opus:reviewer-renata:reviewer – shell_pid=2807004 – Started review via action command
- 2026-07-01T19:45:24Z – user – shell_pid=2807004 – Moved to planned
- 2026-07-01T19:46:17Z – claude:opus:randy-reducer:implementer – shell_pid=2822068 – Started implementation via action command
- 2026-07-01T19:48:17Z – claude:opus:randy-reducer:implementer – shell_pid=2822068 – Cycle 3: NFR-003 fixed — deleted unused [misc] ignore (strict mypy warn_unused_ignores passes), narrowed [attr-defined] with isinstance(click.Group) assert. mypy strict clean, ruff clean, 19 tests + 42 golden green. FR-010 pin + hazard assertion untouched (approved).
- 2026-07-01T19:48:55Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=2827278 – Started review via action command
- 2026-07-01T19:51:24Z – user – shell_pid=2827278 – Cycle-3 confirm: NFR-003 fixed — 0 suppressions in owned files, strict mypy clean, frozen test intact, 19+42 green. FR-010 substance approved prior cycle.
