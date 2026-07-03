---
work_package_id: WP08
title: mark_status + finalize families relocation
dependencies:
- WP07
requirement_refs:
- FR-001
tracker_refs: []
planning_base_branch: degod-follow-ups
merge_target_branch: degod-follow-ups
branch_strategy: Planning artifacts for this mission were generated on degod-follow-ups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into degod-follow-ups unless the human explicitly redirects the landing branch.
subtasks:
- T035
- T036
- T037
- T038
phase: Phase 3 - Family relocations
assignee: ''
agent: claude
history:
- at: '2026-07-02T12:53:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- src/specify_cli/cli/commands/agent/tasks_mark_status.py
- src/specify_cli/cli/commands/agent/tasks_finalize.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks_mark_status.py
- src/specify_cli/cli/commands/agent/tasks_finalize.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – mark_status + finalize families relocation

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

Relocate the two remaining families VERBATIM:
- mark_status: `_do_mark_status` (tasks.py:2641 region) + 9 `_ms_*` + `_MarkStatusState`
  (:2325) + `_default_mark_status_ports` (:2393) → NEW `tasks_mark_status.py`.
- finalize_tasks: `_do_finalize_tasks` (:3122 region) + 4 `_ft_*` (`_ft_resolve_context`,
  `_ft_validate`, `_ft_apply_writes`, `_ft_output`) + `_FinalizeState` (:2924) +
  `_default_finalize_ports` (:2953) → NEW `tasks_finalize.py`.

`mark_status` sits on the REFUSE arm of the C-001 divergence (T005 pins it — no pre-gate
additions/removals). After this WP, ALL five families are out of `tasks.py`.

No ratchet entry exists for `mark_status`/`finalize_tasks` (`_BRANCH_COVERAGE_FLOORS`
covers move_task/status/map_requirements only) — verify that claim against the live
ratchet block and record the verification; if it turns out an entry exists, re-point it
(WP05 mechanism).

**Shared-surface note**: edits `tasks.py` and the gate-file ceiling.

## Context & Constraints

- WP05–WP07 Activity Logs — the recipe, thrice proven.
- `research.md` D3: mark_status owns the no-IDs error byte case (:2477 origin — routed
  through Render by WP04); finalize has no direct emission site.
- `contracts/parity-contract.md` Layers 1/3/4; C-001 refuse arm.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: degod-follow-ups
- **Merge target branch**: degod-follow-ups

## Subtasks & Detailed Guidance

### Subtask T035 – Create `tasks_mark_status.py`

- **Steps**: Cut VERBATIM (`grep -nE '^def _ms_|class _MarkStatusState|def _default_mark_status_ports|def _do_mark_status' tasks.py`); seam-bridge routing (D7 symbols incl. `emit_status_transition_transactional` ×13, `feature_status_lock` ×21, `_MarkStatusCoordRouter` via `_tasks.`); no module-level `tasks` import.
- **Files**: new module (~350–450 lines).

### Subtask T036 – Create `tasks_finalize.py`

- **Steps**: Same recipe for the finalize family (the squad-recovered FIFTH family — `grep -nE '^def _ft_|class _FinalizeState|def _default_finalize_ports|def _do_finalize_tasks' tasks.py`).
- **Files**: new module (~250–350 lines).
- **Parallel?**: independent of T035 within the WP.

### Subtask T037 – Thin both wrappers + bindings; T005 green

- **Steps**: Both `@app.command` wrappers → thin delegates (typer signatures frozen); `tasks.py` binds back patched/moved symbols (`grep -rn "tasks\._ms_\|tasks\._ft_\|_MarkStatusState\|_FinalizeState\|_default_mark_status_ports\|_default_finalize_ports" tests/`); coord harness T005 (mark_status refuse-exit-1) green — any delta = revert. Verify-and-record the no-ratchet-entry claim for both commands.

### Subtask T038 – Parity guard + seam checklists + ceiling ratchet

- **Steps**: Full parity guard; targeted surface; `_CEILING` lowered same-commit (this is the big drop — after this WP `tasks.py` should be near its final size); mypy strict src+tests together; ruff; both families' seam checklists ticked.

## Test Strategy

```bash
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py -q  # MANDATORY (mark_status = commit-router)
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ tests/tasks/ -q -p no:cacheprovider
PWHEADLESS=1 pytest tests/architectural/test_tasks_command_surface.py -q
python -m mypy --strict src/specify_cli/cli/commands/agent/tasks.py src/specify_cli/cli/commands/agent/tasks_mark_status.py src/specify_cli/cli/commands/agent/tasks_finalize.py <touched tests>
```

## Risks & Mitigations

- **Refuse-arm drift** (C-001): the coord-harness refuse-arm case (harness label T005) pins it; no pre-gate changes. (Harness labels ≠ this mission's WP01 subtask IDs.)
- **Two families in one WP**: a deliberate, owned bundling — they are the two smallest
  (9+4 glue), finalize has zero emission sites, and the implement loop cannot split a WP
  mid-mission (no theatrical escape hatch). Sequence T035 fully before T036 so each
  family lands as its own reviewable commit within the WP.
- **Transactional emit/lock seams** (`feature_status_lock`, `emit_status_transition_transactional`): heavily patched — binding + routing + is-identity rows in the committed seam-checklist.md.

## Review Guidance

- Verbatim-move diffs; wrappers thin; coord refuse-arm case green; fixtures unmodified.
- The no-ratchet-entry verification recorded (or re-point evidence if it existed).
- Both seam checklists complete.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-02T12:53:55Z – system – Prompt created.
