---
work_package_id: WP06
title: move_task thin-orchestrator rewire + read fold
dependencies:
- WP05
requirement_refs:
- C-001
- C-002
- FR-007
- FR-010
- NFR-004
tracker_refs: []
planning_base_branch: design/degod-tasks-2116
merge_target_branch: design/degod-tasks-2116
branch_strategy: Planning artifacts for this mission were generated on design/degod-tasks-2116. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/degod-tasks-2116 unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
phase: Phase 4 - Body thinning
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3243285"
history:
- at: '2026-07-01T15:16:35Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: tests/specify_cli/cli/commands/agent/test_move_task_orchestration.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_move_task_orchestration.py
execution_mode: code_change
owned_files:
- tests/specify_cli/cli/commands/agent/test_move_task_orchestration.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – move_task thin-orchestrator rewire + read fold

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `randy-reducer`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Reduce `move_task` to a **≤150 LOC thin orchestrator** over its core (WP03) + ports (WP02), and fold its kind-blind read onto the kind-aware coord READ authority with the **pinned kind** proven in WP02.

- `move_task` body ≤150 LOC; all fs/git/emit side effects routed through ports (`commit_status` for the event, `commit_artifact` for the coord-vs-primary write).
- `move_task:1138`'s `_mt_feature_dir` **STAYS on `resolve_feature_dir_for_mission` (coord husk)** — it is SHARED with the coord-authority status reads at 1149 (`_read_transactional_wp_lane`, the authoritative event-log lane / STATUS partition) + 1216 (review-artifact-override persist), which MUST read the coord husk. Do NOT wholesale-repoint it to a primary kind (that reintroduces the split-brain FR-010 closes). If the pre30 guard is routed through `FsReader` at all, use `STATUS_STATE` (path-equal to the coord husk, per the WP02 proof) or a **separate guard-only variable**, leaving the status read on the coord husk.
- WP01 golden byte-identical incl. the skip-exit-0 arm; the orchestration test proves executed side-effects match.

## Context & Constraints

- Read `plan.md` (IC-04, IC-05), `research.md` (D8, D10), `contracts/ports-and-cores.md`.
- **Skip-exit-0 arm**: driven by `skip_target_branch_commit` (fall-through, NOT `typer.Exit(0)`). Preserve that control shape — the WP03 outcome carries `skip_primary`, and `commit_status` returns `.skipped`.
- **C-001**: reads via `FsReader`, writes via `CoordCommitRouter` (`commit_status`/`commit_artifact`) — never conflate.
- **C-002**: the read fold routes through `resolve_planning_read_dir`; keep the canonicalizer fold in the adapter (don't re-implement in `move_task`).
- **FR-010 (move_task is the SHARED-VAR site — reviewer-caught)**: the WP02 pin table marks `move_task:1138` as **coord-husk-preserving** (`STATUS_STATE` / separate guard var), NOT `WORK_PACKAGE_TASK`→primary. The `WORK_PACKAGE_TASK`→primary migrations are the guard-only sites `finalize_tasks:2373` / `list_dependents:3568`, which belong to **WP08**, not this WP. If any golden case OR the coord status read shifts, stop.
- **NFR-004**: extracted glue helper ≤150 LOC / CC≤15 (glue must not absorb un-tested decision logic — decisions live in the WP03 core); enforced by the WP09 LOC gate.
- **Ownership/leeway**: own `test_move_task_orchestration.py`; the `move_task` body edits are documented **leeway edits** to `tasks.py` (owned by WP09). Record in "Out-of-map edits".

## Branch Strategy

- **Planning base branch**: `design/degod-tasks-2116`
- **Merge target branch**: `design/degod-tasks-2116`

## Subtasks & Detailed Guidance

### T026 — Route execution through ports
Replace inline event emission / coord-vs-primary write / WP-file writes with `commit_status`/`commit_artifact`/`FsReader` calls executing the WP03 `TransitionOutcome`. Body ≤150 LOC.

### T027 — FR-010 move_task:1138 (coord-husk-preserving, per WP02 pin)
The shared `_mt_feature_dir` **stays on `resolve_feature_dir_for_mission` (coord husk)** — it feeds the real coord status reads at 1149/1216. Do NOT repoint it to a primary kind. If you route the pre30 guard through `FsReader`, use `STATUS_STATE` (path-equal to the coord husk per the WP02 proof) or a **separate guard-only variable**, leaving the status read on the coord husk. Add an assertion that the coord status read still resolves the coord husk (guards against a future wholesale-repoint). Golden + coord status read byte-identical.

### T028 — Glue extraction + clean
Extract remaining glue into helpers ≤150 LOC / CC≤15. ruff+mypy clean, 0 new suppressions.

### T029 — Prove parity
WP01 golden byte-identical (incl. skip-exit-0). `test_move_task_orchestration.py` asserts executed side-effects (coord-vs-primary emission, WP-file writes) via Fake ports match pre-rewire. Both green.

## Test Strategy

- `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_move_task_orchestration.py tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py -q`

## Risks & Mitigations

- **Skip-arm regression**: routing through `commit_status` can turn the fall-through into an early exit — assert the skip arm explicitly (golden T004 + orchestration test).
- **FR-010 dir shift**: if the reclassified read resolves a different dir for any case, revert and escalate.

## Out-of-map edits

- `src/specify_cli/cli/commands/agent/tasks.py` (`move_task` body only) — documented leeway; `tasks.py` owned by WP09. Strictly-linear chain → no parallel collision.

## Review Guidance

- Confirm `move_task` ≤150 LOC, reads via `FsReader` / writes via the two WRITE capabilities, skip-exit-0 preserved, golden byte-identical.

## Activity Log

- 2026-07-01T15:16:35Z – system – Prompt created.
- 2026-07-01T22:56:52Z – claude:opus:randy-reducer:implementer – shell_pid=3161128 – Assigned agent via action command
- 2026-07-01T23:37:31Z – claude:opus:randy-reducer:implementer – shell_pid=3161128 – move_task 88 LOC over WP03 core + WP02 ports; commit_status/commit_artifact routing; FR-010 :1138 coord-husk (feature_write_dir=resolve_feature_dir_for_mission); WP03 partial-write timing + WP02 hazard + skip-arm + golden 42 all green; 903 agent-dir tests pass; strict mypy (src+test together) + ruff clean; 2 pre-existing protected-branch failures out of scope (fail identically on base)
- 2026-07-01T23:38:51Z – claude:opus:reviewer-renata:reviewer – shell_pid=3243285 – Started review via action command
- 2026-07-01T23:50:07Z – user – shell_pid=3243285 – APPROVED. Pre-existing failures cross-base verified: both test_issue_1386::...refuses_protected_branch_before_mutation ('finalize-tasks...bootstrap the event log' error) and test_wp03_bypass_writers_fr008::...protected_primary_message_byte_identical ('Mission directory not found: write-surface-coherence-01KVTVZS') fail IDENTICALLY at the WP06 base (parent 2cccb69c9, deps present/WP06 absent) — same assertion line, same error text. Genuinely pre-existing (finalize/bootstrap env), NOT a WP06 regression; protected-branch refusal timing unchanged. DIR-013 already reported in activity log; suggest follow-up issue. Port-seam SOUND: _MoveTaskCoordRouter subclasses RealCoordCommitRouter, methods structurally identical, only re-resolves canonical emit_status_transition_transactional/commit_for_mission through tasks.py namespace to preserve ~900 @patch seams; feature_write_dir inherited -> coord husk (no divergence). 4 guards GREEN (override_persist_survives_later_guard_refusal, fr010 husk pin x2, golden T004 skip-arm + all help goldens); skip-suppression test non-tautological (forces skip_primary via real core, asserts artifact_calls==[] + WP file unchanged). FR-010: mt_feature_dir=feature_write_dir=resolve_feature_dir_for_mission, never repointed to primary. LOC: _do_move_task body thin, all _mt_* helpers <=85 LOC, ruff C901 clean; _mt_run_decision delegates to WP03 decide_transition (glue only). mypy --strict --no-incremental (tasks.py + test together) Success; ruff clean; 0 new type:ignore/noqa. Boy-scout tracking_emit(**kwargs) correct: capability default IS GuardCapability.STANDARD. 903 agent-dir tests pass.
