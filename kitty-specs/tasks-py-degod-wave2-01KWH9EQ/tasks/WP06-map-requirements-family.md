---
work_package_id: WP06
title: map_requirements family relocation
dependencies:
- WP05
requirement_refs:
- FR-001
- FR-012
tracker_refs: []
planning_base_branch: degod-follow-ups
merge_target_branch: degod-follow-ups
branch_strategy: Planning artifacts for this mission were generated on degod-follow-ups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into degod-follow-ups unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
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
- src/specify_cli/cli/commands/agent/tasks_map_requirements.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks_map_requirements.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – map_requirements family relocation

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

Relocate the map_requirements family — `_do_map_requirements` (tasks.py:3677 region) +
11 `_mr_*` glue + `_MapReqState` + `_default_map_requirements_ports` — VERBATIM into NEW
`src/specify_cli/cli/commands/agent/tasks_map_requirements.py`; thin the wrapper;
re-point the ratchet (FR-012). This command sits on the REFUSE arm of the C-001
divergence (refuse-exit-1 through `_protected_branch_status_commit_error`, NO skip
pre-gate) — coord harness T005 pins it; do not add or remove any pre-gate.

**Shared-surface note**: edits `tasks.py`, the coord-harness ratchet block, and the
gate-file ceiling — sequential shared surfaces.

## Context & Constraints

- WP05's Activity Log — the family-move recipe, now proven twice (WP02 pattern + WP05).
  Copy it exactly.
- `research.md` D3: this family owns 5 of the 13 byte-freeze cases (unknown-WP,
  malformed-ref, unknown-spec-ids, stale-refs error legs + the `--json` success leg) —
  they are your per-step tripwires.
- `contracts/parity-contract.md` Layer 3 (ratchet), Layer 4 (seam).

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: degod-follow-ups
- **Merge target branch**: degod-follow-ups

## Subtasks & Detailed Guidance

### Subtask T027 – Create `tasks_map_requirements.py`

- **Steps**: Cut VERBATIM (`grep -nE '^def _mr_|class _MapReqState|def _default_map_requirements_ports|def _do_map_requirements' tasks.py` for the authoritative set); apply the seam-bridge routing for D7 symbols + shared helpers + `_MapReqCoordRouter` (via `_tasks.`); no module-level `tasks` import.
- **Files**: new module (~400–550 lines), `tasks.py` deletions.

### Subtask T028 – Thin the wrapper + bindings

- **Steps**: `map_requirements` `@app.command` wrapper → thin delegate (typer signature byte-frozen by help fixtures); `tasks.py` imports back every patched/moved symbol (`grep -rn "tasks\._mr_\|_MapReqState\|_default_map_requirements_ports" tests/`).

### Subtask T029 – Ratchet re-point + coord refuse-arm case

- **Steps**: Update the WP05-built `{floored_name: (module, qualname)}` map:
  `"map_requirements": (tasks_map_requirements, "_do_map_requirements")` — and ADD the new
  module to the coverage session's `include=[...]` set (the map feeds it; verify, don't
  assume). Floors unchanged; the vacuous-fallback removal from WP05 stays (a 0-arc
  function hard-fails). **Acceptance evidence**: a demonstrated RED fire of the
  re-pointed entry (locally lower the floor / drop a scenario, paste output, restore) —
  not a recorded percentage. Coord-harness refuse-arm case (harness label T005,
  refuse-exit-1) green — any delta = revert. (Harness labels T004/T005 ≠ this mission's
  WP01 subtask IDs.)
- **Files**: `test_tasks_cli_contract_coord.py` (ratchet block only — WP05's diff-scope rule applies).

### Subtask T030 – Parity guard + seam checklist + ceiling ratchet

- **Steps**: Full parity guard (the 5 family byte cases especially); seam-checklist rows appended to the committed `seam-checklist.md` (WP02's format) with is-identity tests for every moved patched symbol; `_CEILING` lowered same-commit; mypy strict src+tests together; ruff.

## Test Strategy

```bash
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py -q  # MANDATORY
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ tests/tasks/ -q -p no:cacheprovider
PWHEADLESS=1 pytest tests/architectural/test_tasks_command_surface.py -q
python -m mypy --strict src/specify_cli/cli/commands/agent/tasks.py src/specify_cli/cli/commands/agent/tasks_map_requirements.py <touched tests>
```

## Risks & Mitigations

- **Refuse-arm drift** (C-001): T005 pins it; no pre-gate additions.
- **Error-leg byte drift**: the 5 byte cases catch payload/ordering slips instantly — run after each subtask.
- **Ratchet**: re-point only; reuse WP05's mechanism.

## Review Guidance

- Verbatim-move diff; typer signature unchanged; ratchet floors unchanged.
- The 5 map-requirements byte cases + T005 green; fixtures unmodified.
- Seam checklist complete in the Activity Log.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-02T12:53:55Z – system – Prompt created.
