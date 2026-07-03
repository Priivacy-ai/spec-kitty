---
work_package_id: WP03
title: Adapters module (coord routers)
dependencies:
- WP02
requirement_refs:
- FR-004
tracker_refs: []
planning_base_branch: degod-follow-ups
merge_target_branch: degod-follow-ups
branch_strategy: Planning artifacts for this mission were generated on degod-follow-ups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into degod-follow-ups unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
phase: Phase 2 - Foundations
assignee: ''
agent: claude
history:
- at: '2026-07-02T12:53:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- src/specify_cli/cli/commands/agent/tasks_command_adapters.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks_command_adapters.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Adapters module (coord routers)

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

Relocate the three coord-router adapter classes — `_MoveTaskCoordRouter` (tasks.py:1120),
`_MapReqCoordRouter` (:1172), `_MarkStatusCoordRouter` (:2356) — VERBATIM into a NEW
`src/specify_cli/cli/commands/agent/tasks_command_adapters.py` (FR-004), breaking the
ports↔commands cycle risk before the family moves need them. `_StatusRender` is **NOT
moved** — WP04 deletes it (spec `_StatusRender` ordering edge case).

Success: coord harness (16 cases incl. T004/T005) green; parity guard green; no import
cycle; ceiling ratcheted.

**Shared-surface note**: edits `tasks.py` (deletions + bindings) and the gate-file
ceiling — sequential shared surfaces of the linear chain.

## Context & Constraints

- `kitty-specs/tasks-py-degod-wave2-01KWH9EQ/data-model.md` — adapters module row + the
  no-cycle argument: adapters subclass `RealCoordCommitRouter` from
  `specify_cli.agent_tasks_ports` (top-level ports module — imports downward only).
- `contracts/parity-contract.md` Layers 1+4.
- C-004: adapters remain the ONLY implementations of their port capabilities; do not add
  new adapter variants.
- The adapter classes are patched in coord tests — the D7 seam rules apply (bindings in
  `tasks.py`, routing where relocated code constructs them).

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: degod-follow-ups
- **Merge target branch**: degod-follow-ups

## Subtasks & Detailed Guidance

### Subtask T013 – Create `tasks_command_adapters.py`

- **Purpose**: The cycle-breaking home for the coord routers.
- **Steps**:
  1. Cut the three classes VERBATIM into the new module. Module-level imports allowed:
     `specify_cli.agent_tasks_ports` (ports), stdlib, core modules — but NOT `tasks`
     itself; if an adapter method calls a `tasks`-module symbol (check each method body),
     use the lazy `_tasks.<attr>` route (research.md D1).
  2. Module docstring: why this module exists (import-cycle break; FR-004) + one-adapter-per-port note.
  3. No-cycle proof: `python -c "import specify_cli.cli.commands.agent.tasks_command_adapters"` run via pytest collection (worktree venv caveat) + note the import graph in the Activity Log.
- **Files**: new module (~150–200 lines), `tasks.py` (deletions).

### Subtask T014 – `tasks.py` bindings + adapter seam checklist

- **Purpose**: Coord tests patch these names on `tasks` — the binding must be the constructed object.
- **Steps**:
  1. `from .tasks_command_adapters import _MoveTaskCoordRouter, _MapReqCoordRouter, _MarkStatusCoordRouter` in `tasks.py`.
  2. Grep the patch sites: `grep -rn "CoordRouter" tests/ | grep -v "\.py:.*#"` — list each in the Activity Log with how it's preserved (binding vs re-point). The `_default_*_ports` factories (still in `tasks.py` until their family WPs) construct the routers via the module-level names — patches on `tasks.<Router>` therefore keep intercepting construction.
- **Files**: `tasks.py`.

### Subtask T015 – Parity guard + coord harness + ceiling ratchet

- **Steps**: Full parity guard (quickstart.md) with `test_tasks_cli_contract_coord.py` explicitly included (this WP touches commit-routing classes — coord harness MANDATORY per NFR-005); lower `_CEILING` to the new size in the same commit; mypy strict on `tasks.py` + `tasks_command_adapters.py` + any touched test; ruff.

## Test Strategy

```bash
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py \
  tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py \
  tests/specify_cli/cli/commands/agent/test_tasks_json_bytes.py \
  tests/architectural/test_tasks_command_surface.py -q -p no:cacheprovider
python -m mypy --strict src/specify_cli/cli/commands/agent/tasks.py src/specify_cli/cli/commands/agent/tasks_command_adapters.py
```

## Risks & Mitigations

- **Import cycle via a sneaky tasks-symbol reference in an adapter method** → lazy route + the import-in-isolation proof.
- **Coord tests patching router construction lose interception** → T014 checklist; factories still construct via `tasks.<Router>` bindings.
- **T004/T005 divergence pins**: this WP touches the classes those pins exercise — any T004/T005 delta = revert (C-001).

## Review Guidance

- Verbatim-move diff check; `_StatusRender` untouched (WP04's).
- Adapter patch-site checklist complete in the Activity Log.
- Coord harness ran and passed; ceiling lowered same-commit.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-02T12:53:55Z – system – Prompt created.
