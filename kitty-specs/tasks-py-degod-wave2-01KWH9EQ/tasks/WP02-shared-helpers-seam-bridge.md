---
work_package_id: WP02
title: Shared-helpers module + seam bridge
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
tracker_refs: []
planning_base_branch: degod-follow-ups
merge_target_branch: degod-follow-ups
branch_strategy: Planning artifacts for this mission were generated on degod-follow-ups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into degod-follow-ups unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
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
- src/specify_cli/cli/commands/agent/tasks_shared.py
- tests/specify_cli/cli/commands/agent/test_tasks_shared_seam.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks_shared.py
- tests/specify_cli/cli/commands/agent/test_tasks_shared_seam.py
- tests/specify_cli/cli/commands/agent/test_tasks.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Shared-helpers module + seam bridge

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

Create `src/specify_cli/cli/commands/agent/tasks_shared.py` housing the ~28 cross-family
helpers (FR-003), moved VERBATIM out of `tasks.py`, with the **seam bridge** (FR-002)
proving patch interception survives. This WP establishes the pattern every family move
(WP05–WP08) copies — get it right here, the rest is mechanical.

Success: parity guard green (43 harness + 13 byte-freeze, unmodified); interception
tests prove `@patch("...agent.tasks.<sym>")` still bites; mypy strict clean on changed
src+tests TOGETHER; LOC ceiling ratcheted down; the two campsite mypy folds done.

**Shared-surface note**: this WP also edits `src/specify_cli/cli/commands/agent/tasks.py`
and ratchets `tests/architectural/test_tasks_command_surface.py` — sequential shared
surfaces of the linear chain (see tasks.md); record edits there in the Activity Log.

## Context & Constraints

Read FIRST:
- `kitty-specs/tasks-py-degod-wave2-01KWH9EQ/data-model.md` — the module map, the
  interception invariant, and the D7 seam-inventory table (23 symbols × 367 patch sites;
  your checklist source).
- `kitty-specs/tasks-py-degod-wave2-01KWH9EQ/research.md` D1 (the VERIFIED live idiom:
  lazy `from specify_cli.cli.commands.agent import tasks as _tasks` INSIDE functions,
  then `_tasks.<attr>(...)`; template evidence mission_create.py:76,204,439) and D7
  (routing rule).
- `kitty-specs/tasks-py-degod-wave2-01KWH9EQ/contracts/parity-contract.md` Layer 4.
- Template precedent: `src/specify_cli/cli/commands/agent/mission_finalize.py` (13 live
  `_mission.<attr>` occurrences — read one to internalize the shape).

Constraints: pure verbatim moves (no refactoring, no renames, no signature changes —
NFR-001); C-001: `_skip_target_branch_commit` and `_protected_branch_status_commit_error`
move as-is, their CALLER wiring stays in the family code (do not touch it).

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: degod-follow-ups
- **Merge target branch**: degod-follow-ups

## Subtasks & Detailed Guidance

### Subtask T007 – Enumerate the definitive shared-helper move-set

- **Purpose**: The squad found ~30 cross-family helpers with no named home; pin the exact list before cutting.
- **Steps**:
  1. Census `tasks.py` top-level defs: `grep -nE '^(def|class) ' src/specify_cli/cli/commands/agent/tasks.py`.
  2. Partition: (a) family sets (5 `_do_*` + `_mt_*`/`_mr_*`/`_st_*`/`_ms_*`/`_ft_*` glue + 5 `_*State` + 5 `_default_*_ports`) — NOT this WP; (b) adapter classes — NOT this WP (WP03); (c) `@app.command` bodies + the 4 small bodies — NOT this WP; (d) **everything else = the shared move-set** (expect ~28: `_output_result` (537), `_output_error` (551), `_find_mission_slug` (481), `_ensure_target_branch_checked_out` (446), `_coord_topology_active` (578), `_skip_target_branch_commit` (597), `resolve_primary_branch` (76), `_validate_ready_for_review` (838), `_check_unchecked_subtasks` (733), `_emit_sparse_session_warning` (421), `_wp_branch_merged_into_target` (874), `_protected_branch_status_commit_error` (564), `_mark_status_json_payload` (2292), module constants they depend on, …). **NOT in the move-set (squad claims-check)**: `_get_latest_review_cycle_verdict` and `_self_review_fallback_option_error` are NOT defs in `tasks.py` — Wave 1 already extracted them to `tasks_parsing_validation.py` (:288/:250); `tasks.py` only re-imports them (:148/:150). Leave those imports as-is.
  3. Record the final list as the FIRST rows of a NEW committed artifact `kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md` with fixed columns: `symbol | tasks.py binding (line) | routed-via-_tasks? | interception/identity test id | monkeypatch sites swept`. This file is the mission-wide seam checklist every family WP (WP05–WP08) appends to — one format, committed evidence, not free-form Activity-Log prose.
- **Notes**: A helper used by exactly ONE family belongs to that family (leave for its WP); when in doubt, count call sites (`grep -c "helper_name(" tasks.py`).

### Subtask T008 – Create `tasks_shared.py` with lazy `_tasks.<attr>` routing

- **Purpose**: The move + the interception-preserving mechanism.
- **Steps**:
  1. Cut each move-set def VERBATIM into `tasks_shared.py` (module docstring: purpose + the seam-bridge explanation + pointer to this mission).
  2. Inside each moved function, for every call to a symbol in the D7 seam table (e.g. `locate_project_root`, `commit_for_mission`, `get_mission_type`, and moved siblings like `_find_mission_slug`): add the lazy import `from specify_cli.cli.commands.agent import tasks as _tasks` at the top of the FUNCTION body and call via `_tasks.<attr>(...)`. Calls to non-patched, non-tasks symbols keep direct imports at module level.
  3. NO module-level import of `tasks` in `tasks_shared.py` (cycle rule; research D1).
  4. No `__all__` (template precedent, spec FR-008 note).
- **Files**: `src/specify_cli/cli/commands/agent/tasks_shared.py` (new, expect ~700–900 lines), `tasks.py` (deletions).

### Subtask T009 – `tasks.py` module bindings for every moved symbol

- **Purpose**: The interception invariant — `tasks.<symbol>` must remain a module attribute that IS the called object.
- **Steps**: In `tasks.py`, import every moved symbol back: `from .tasks_shared import _output_result, _output_error, _find_mission_slug, …` (grouped, commented as the seam surface). Remaining `tasks.py` code calls them exactly as before (bare names now bound to the shared defs). Verify no name vanished: `python -c "from specify_cli.cli.commands.agent import tasks; [getattr(tasks, n) for n in [<move-set names>]]"` via pytest (worktree venv caveat — verify through pytest, not bare imports).

### Subtask T010 – Seam interception tests

- **Purpose**: Layer-4 proof that patches INTERCEPT, not merely resolve (the squad's CRITICAL finding).
- **Steps**: New `tests/specify_cli/cli/commands/agent/test_tasks_shared_seam.py`:
  1. For the top defensively-patched symbols (`_find_mission_slug` ×65, `_ensure_target_branch_checked_out` ×48, `locate_project_root` ×66): a test that patches `...agent.tasks.<sym>` with a sentinel and invokes a **relocated shared helper** that calls it, asserting the sentinel was hit (interception through the `_tasks.<attr>` route).
  2. An identity test: `tasks.<sym> is tasks_shared.<sym>` for **EVERY** moved def (binding present and same object) — parametrize over the full move-set list; this is cheap and non-fakeable, so no spot-checking.
  3. Markers matching the sibling contract tests (gate-visible).
- **Files**: new test file (~100–150 lines).

### Subtask T011 – mypy strict campsite folds in `test_tasks.py`

- **Purpose**: Domain-matched folds recorded in the spec (Campsite Folds section).
- **Steps**: Run `python -m mypy --strict src/specify_cli/cli/commands/agent/tasks.py src/specify_cli/cli/commands/agent/tasks_shared.py tests/specify_cli/cli/commands/agent/test_tasks.py`. Fix: (a) the `attr-defined` on `_get_latest_review_cycle_verdict` — the symbol is defined in `tasks_parsing_validation.py` and re-imported by `tasks.py`; either re-point the `test_tasks.py:26–28` import to the defining module or make the `tasks.py` re-export explicit — pick whichever keeps the patch seams intact; (b) the redundant cast at `test_tasks.py:1028` (delete the cast). Expect a 2–3 step narrowing cascade (tracer warning) — fix each, never suppress.

### Subtask T012 – Parity guard + LOC ceiling ratchet

- **Steps**: Run the full parity guard (quickstart.md); lower `_CEILING` in `tests/architectural/test_tasks_command_surface.py` to the new `tasks.py` LOC in the SAME commit as the move; run the WP's targeted surface; `ruff check` on all touched files.

## Test Strategy

```bash
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py -q  # MANDATORY: this WP moves the C-001 divergence helpers
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ tests/tasks/ -q -p no:cacheprovider
PWHEADLESS=1 pytest tests/architectural/test_tasks_command_surface.py -q
python -m mypy --strict src/specify_cli/cli/commands/agent/tasks.py src/specify_cli/cli/commands/agent/tasks_shared.py tests/specify_cli/cli/commands/agent/test_tasks.py tests/specify_cli/cli/commands/agent/test_tasks_shared_seam.py
```

## Risks & Mitigations

- **Interception loss** (patch resolves but doesn't bite): the T010 tests are the guard; every moved D7 symbol's callers routed via `_tasks.<attr>` — checklist ticked per symbol in the Activity Log.
- **Hidden single-family helper misclassified as shared**: call-site count evidence in T007.
- **monkeypatch.setattr sites** (~37) target the same symbols — the binding+routing preserves them identically; spot-check two.
- **Golden delta** → revert the move (never adjust fixtures).

## Review Guidance

- Diff review: every moved def byte-identical (whitespace-only context changes aside); no logic edits smuggled in.
- The committed `seam-checklist.md` covers every D7 symbol the move-set defines or calls, with (a) binding proven by the parametrized is-identity test, (b) routing, (c) interception evidence, (d) monkeypatch sites swept — per row.
- `_CEILING` lowered in the same commit; parity suites unmodified.
- mypy strict run covered src+tests TOGETHER (ask for the command line used).

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-02T12:53:55Z – system – Prompt created.
