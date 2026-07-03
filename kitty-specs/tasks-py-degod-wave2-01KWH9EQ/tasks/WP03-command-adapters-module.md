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
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "450764"
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
- 2026-07-02T14:54:34Z – claude:fable:python-pedro:implementer – shell_pid=411259 – Assigned agent via action command
- 2026-07-02T15:20:00Z – claude:fable:python-pedro:implementer – T013: created `tasks_command_adapters.py` (175 lines) with the 3 coord routers moved verbatim from tasks.py (was :589/:641/:1804 at the WP03 base). Only deltas from verbatim: (a) each method body reaches the patched seam symbols via the D1 lazy bridge (`from specify_cli.cli.commands.agent import tasks as _tasks` in-method, then `_tasks.emit_status_transition_transactional` / `_tasks.commit_for_mission`) — previously implicit via tasks-module globals, now literal; (b) docstring first-lines reworded "*this module's*/*this* module" → "the ``tasks`` module" (the old wording would be factually wrong in the new file; re-resolution semantics unchanged). `_StatusRender` untouched (WP04).
- 2026-07-02T15:20:30Z – claude:fable:python-pedro:implementer – T013 no-cycle proof / import graph: tasks_command_adapters module-scope imports = stdlib (collections.abc, pathlib) + mission_runtime + specify_cli.agent_tasks_ports + specify_cli.core.commit_guard + specify_cli.git.protection_policy + specify_cli.status — all downward-only, none import specify_cli.cli.commands.agent.*; the ONLY edge back to tasks is the lazy in-method D1 bridge (never module scope). tasks.py → tasks_command_adapters is therefore a DAG edge. Proven by pytest collection+execution importing tasks (which imports the new module) across the parity guard.
- 2026-07-02T15:21:00Z – claude:fable:python-pedro:implementer – T014: tasks.py re-imports the 3 routers as explicit `as` re-exports (lines 264–268); `emit_status_transition_transactional` (line 47) and `commit_for_mission` (line 86) converted to explicit `as` re-export form (bindings stay live patch seams; no direct call site remains in tasks.py); unused `Sequence`/`CommitStatusResult` imports dropped. Adapter patch-site checklist: `grep -rn "CoordRouter" tests/` → 10 hits, ALL direct imports/constructions (test_move_task_orchestration.py:33/:221, test_tasks_core_backed_orchestration.py:41/:189, test_tasks_coreless_orchestration.py:55/:206 + docstring refs), ZERO patches on the router names; the patched collaborators (`tasks.commit_for_mission` ×~19 sites, `tasks.emit_status_transition_transactional` ×~15 sites) keep intercepting via the `_tasks.` route; `_default_*_ports` factories (still in tasks.py) construct via the `tasks.<Router>` bindings so patches on `tasks.<Router>` would keep intercepting construction. Full rows appended to seam-checklist.md (primary checkout, commit 247d8293d).
- 2026-07-02T15:22:00Z – claude:fable:python-pedro:implementer – T015: parity guard + coord harness (test_tasks_json_bytes + test_tasks_cli_contract + test_tasks_cli_contract_coord + test_tasks_command_surface) = 61 passed, fixtures untouched. Router patch-site files (move_task/core_backed/coreless orchestration, shared_seam, mark_status, canonical_cleanup, atomic_status_commits) = 108 passed. Fuller surface (tests/specify_cli/cli/commands/agent/ + tests/tasks/) = 1102 passed, 2 xfailed, 1 failed = known pre-existing #2307 (test_fr011_primary_only_inversion_resolves_coord_without_rescue — expected red, unrelated). _CEILING ratcheted 4017 → 3927 in the SAME commit (tasks.py wc -l = splitlines = 3927). mypy --strict on tasks.py + tasks_command_adapters.py (+ agent_tasks_ports.py on the command line so the base class resolves under the `specify_cli.*` follow_imports=skip override — matches CI's whole-directory run): Success, 0 issues; new module needs NO transitional-quarantine entry. ruff check on all 3 touched files: All checks passed (exit 0). Lane commit 619ca6503.
- 2026-07-02T15:08:45Z – claude:fable:python-pedro:implementer – shell_pid=411259 – WP03 ready: 3 coord routers relocated verbatim to tasks_command_adapters.py (D1 lazy _tasks bridge for emit_status_transition_transactional/commit_for_mission); tasks.py re-imports as explicit re-exports; no-cycle import graph (ports/stdlib/core only at module scope); parity guard+coord harness 61 passed, router patch-site files 108 passed, fuller surface 1102 passed (only known #2307 red); _CEILING 4017->3927 same commit; mypy --strict clean, ruff clean. Lane commit 619ca6503; seam-checklist rows 247d8293d.
- 2026-07-02T15:10:04Z – claude:opus:reviewer-renata:reviewer – shell_pid=450764 – Started review via action command
- 2026-07-02T15:16:20Z – user – shell_pid=450764 – Review passed: verbatim relocation of 3 coord routers to tasks_command_adapters.py verified. Docstring reword (this module->tasks module) accurate not logic-smuggling; dropped Sequence/CommitStatusResult imports have zero tasks.* refs; router identity preserved via tasks.py re-exports (is-identity True x3); sentinel proof confirms patch('tasks.commit_for_mission') intercepts relocated adapter path AND preserves MapReq/MarkStatus target_branch divergence; standalone adapters import = no cycle (only lazy in-method _tasks bridge). Parity+coord harness 61 passed (incl T004/T005 pins), router patch-site files 85 passed; ceiling 3927==actual LOC; mypy --strict + ruff clean; scope = 3 sanctioned files, no fixture edits, #2307 pre-existing untouched.
