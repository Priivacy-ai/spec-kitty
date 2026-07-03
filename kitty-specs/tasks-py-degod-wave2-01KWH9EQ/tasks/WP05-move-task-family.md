---
work_package_id: WP05
title: 'move_task family relocation (+ #2306 fold)'
dependencies:
- WP04
requirement_refs:
- FR-001
- FR-002
- FR-012
tracker_refs: []
planning_base_branch: degod-follow-ups
merge_target_branch: degod-follow-ups
branch_strategy: Planning artifacts for this mission were generated on degod-follow-ups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into degod-follow-ups unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
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
- src/specify_cli/cli/commands/agent/tasks_move_task.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- tests/architectural/untrusted_path_audit/inventory.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – move_task family relocation (+ #2306 fold)

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

Relocate the LARGEST family — `_do_move_task` (tasks.py:2082) + all 23 `_mt_*` glue
helpers + `_MoveTaskState` (:1249) + `_default_move_task_ports` (:1162) — VERBATIM into
NEW `src/specify_cli/cli/commands/agent/tasks_move_task.py`, thin the `move_task`
wrapper, re-point the branch-coverage ratchet (FR-012), and fold #2306 (the
`inventory.md` off-by-one).

This family carries the **C-001 divergence wiring**: `move_task` is the ONLY command
with the `_skip_target_branch_commit` pre-gate (skip-exit-0 on coord+protected). The
coord harness T004 (skip arm + wrong-leg detector) is your tripwire — any T004 delta
means the move broke the divergence: REVERT.

**Shared-surface note**: edits `tasks.py`, the coord-harness ratchet block, and the
gate-file ceiling — sequential shared surfaces of the linear chain.

## Context & Constraints

- `data-model.md` — move-set row + invariants 1 (interception) and 2 (divergence).
- `research.md` D1 (routing idiom), D7 (seam table — this family calls the heaviest
  symbols: `locate_project_root`, `_find_mission_slug`, `_ensure_target_branch_checked_out`,
  `feature_status_lock`, `emit_status_transition_transactional`, …).
- `contracts/parity-contract.md` Layer 3 (ratchet re-point rule — read verbatim).
- WP02's Activity Log — the established seam-bridge pattern; COPY it, don't reinvent.
- #2306: `tests/architectural/test_untrusted_path_containment.py` is RED on the mission
  base — inventory.md records the `_mt_warn_worktree_kitty_specs` sink at
  `cli/commands/agent/tasks.py:1325`; the actual line is `:1326`.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: degod-follow-ups
- **Merge target branch**: degod-follow-ups

## Subtasks & Detailed Guidance

### Subtask T021 – #2306 pre-fix: inventory.md 1325→1326

- **Purpose**: Unblock the RED gate BEFORE moving the code (clean baseline → clean move).
- **Steps**: In `tests/architectural/untrusted_path_audit/inventory.md`, correct the
  `cli/commands/agent/tasks.py:1325` row to the ACTUAL current line of the
  `worktree_kitty / st.mission_slug / "tasks"` sink (re-locate it — earlier WPs shifted
  lines; verify with the gate itself). Run
  `PWHEADLESS=1 pytest tests/architectural/test_untrusted_path_containment.py -q` → must
  go GREEN. Reference #2306 in the commit message.
- **Files**: `tests/architectural/untrusted_path_audit/inventory.md`.

### Subtask T022 – Create `tasks_move_task.py` (full family move-set)

- **Steps**:
  1. Cut VERBATIM: `_do_move_task`, the 23 `_mt_*` helpers (`grep -nE '^def _mt_' tasks.py` for the authoritative list), `_MoveTaskState`, `_default_move_task_ports`.
  2. Apply the WP02 seam-bridge pattern: lazy `_tasks.<attr>` routing for every D7-table symbol the moved code calls (this includes the SHARED helpers — `_tasks._find_mission_slug(...)`, `_tasks._ensure_target_branch_checked_out(...)` — and the adapters — `_tasks._MoveTaskCoordRouter`).
  3. The `_skip_target_branch_commit` pre-gate CALL stays exactly where it is in the moved `_mt_*` flow — verbatim, C-001.
- **Files**: new module (expect ~900–1100 lines), `tasks.py` (deletions).

### Subtask T023 – Thin the `move_task` wrapper; update inventory.md row

- **Steps**:
  1. The `@app.command` `move_task` wrapper (tasks.py:2163 region) becomes a thin delegate: parse typer params → call the relocated `_do_move_task` (imported binding). Keep the exact typer signature (flags, help text — the `--help` byte fixtures pin this).
  2. `tasks.py` bindings: import back every moved symbol tests patch (D7 + `grep -rn "tasks\._mt_\|tasks\._MoveTaskState\|tasks\._default_move_task_ports" tests/`).
  3. Update the inventory.md row AGAIN: the sink now lives at `cli/commands/agent/tasks_move_task.py:<line>` — the gate must stay green.
- **Files**: `tasks.py`, `inventory.md`.

### Subtask T024 – Ratchet re-point: move_task (FR-012) — COVERAGE-PLUMBING REWRITE, not a line-range tweak

- **Purpose**: The ratchet is single-file today AND has a vacuous-green trap (post-tasks squad CRITICAL): `_mutating_function_line_ranges()` parses ONLY `tasks_module.__file__`; the coverage session is `include=[tasks.py]`; and `_branch_coverage_by_function` returns **100.0 when `total == 0`** (zero arcs measured). A naive re-point that changes the name mapping but leaves `include=`/`_analyze()` on `tasks.py` measures NOTHING for the relocated `_do_move_task` → 100.0 → floor 65 "passes" vacuously.
- **Steps** (five coupled edits, all inside the ratchet block of `test_tasks_cli_contract_coord.py`):
  1. Re-key the ratchet to a `{floored_name: (module, qualname)}` map — `"move_task": (tasks_move_task, "_do_move_task")`; `status`/`map_requirements` stay mapped to `tasks.py` until WP07/WP06 re-point them.
  2. `_mutating_function_line_ranges()` resolves each function's AST from ITS OWN module file.
  3. The coverage session's `include=[...]` lists EVERY module in the map (multi-file); `cov._analyze()` runs per-file with results merged per function.
  4. **Kill the vacuous fallback**: replace the `... if total else 100.0` arm with a hard failure (`pytest.fail(f"{name}: 0 branch arcs measured — re-point is vacuous")`).
  5. Floor VALUES, scenario drivers, and assertion bodies untouched (diff-scope rule below).
- **Acceptance evidence** (NOT a recorded percentage): a demonstrated **RED fire** of the re-pointed ratchet — temporarily lower the `move_task` floor locally (or drop a scenario), paste the failing output into the Activity Log, restore. A recorded coverage of exactly 100.0 on move_task (which has known decision branches) is a review-reject pending the non-vacuity proof.
- **Files**: `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py` (ratchet block ONLY).

### Subtask T025 – Seam checklist + interception; coord skip-arm case green

- **Steps**: Per WP02's pattern: (a) is-identity binding tests for EVERY moved patched symbol (appended as rows to the committed `kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md` — columns: `symbol | tasks.py binding | routed-via-_tasks? | interception/identity test id | monkeypatch sites swept`); (b) the coord-harness skip-arm case (harness label T004: move_task coord skip-exit-0 + wrong-leg detector) and the full coord harness green. NOTE: harness case labels T004/T005 are the COORD HARNESS's internal names — do not confuse with this mission's WP01 subtasks T004/T005.

### Subtask T026 – Parity guard + targeted surface + ceiling ratchet

- **Steps**: Full parity guard; `tests/tasks/` + `tests/specify_cli/cli/commands/agent/` targeted surface; `_CEILING` lowered same-commit; mypy strict src+tests together (expect the `test_tasks.py` import of `_get_latest_review_cycle_verdict` etc. already handled by WP02 — verify no new attr-defined); ruff.

## Test Strategy

```bash
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py -q  # MANDATORY (commit-router WP)
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ tests/tasks/ -q -p no:cacheprovider
PWHEADLESS=1 pytest tests/architectural/test_untrusted_path_containment.py tests/architectural/test_tasks_command_surface.py -q
python -m mypy --strict src/specify_cli/cli/commands/agent/tasks.py src/specify_cli/cli/commands/agent/tasks_move_task.py <touched tests>
```

## Risks & Mitigations

- **Divergence collapse** (C-001): T004's wrong-leg detector is engineered for exactly this; treat ANY T004 diff as move-breakage, revert.
- **Ratchet false-red** → T024 is the sanctioned response; floor-lowering/deletion is forbidden and will be rejected in review.
- **Interception loss on the heaviest symbols** (66/65/48 patch sites ride this family's call paths) → the WP02 pattern + spot checks.
- **#2031 analyzer noise at merge**: expected (intra-file analyzer vs cross-file move) — cross-check against the seam checklist, don't chase false positives.

## Review Guidance

- Verbatim-move diff; typer signature of `move_task` unchanged (help fixtures prove it).
- Ratchet: floors unchanged, plumbing re-keyed to `{name: (module, qualname)}`, the
  vacuous-100 fallback REMOVED, RED-fire demonstration recorded. **Diff-scope rule**:
  `git diff` on the coord harness may touch ONLY the floors mapping,
  `_mutating_function_line_ranges`, and the coverage-session include/analyze wiring —
  any edit to `_run_all_scenarios`, floor VALUES, or assertion bodies is rejected.
- inventory.md row followed the code (gate green at BOTH steps: pre-fix and post-move).
- Seam checklist rows appended to the committed seam-checklist.md; coord-harness cases
  T004/T005 (harness labels) untouched and green.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-02T12:53:55Z – system – Prompt created.
