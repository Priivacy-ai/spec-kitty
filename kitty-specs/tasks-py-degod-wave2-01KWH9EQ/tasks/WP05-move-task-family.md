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
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "622868"
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
- 2026-07-02T15:43:57Z – claude:fable:python-pedro:implementer – shell_pid=518107 – Assigned agent via action command
- 2026-07-02T18:35:00Z – claude:fable:python-pedro:implementer – T021 (#2306 fold): inventory.md row re-pinned via the gate's own AST audit — the recorded tasks.py:1325 was one line stale on the mission base (actual 1326, the #2306 off-by-one) and ~594 lines stale on this lane after WP02–WP04; corrected to :732, drift note appended, gate 5/5 GREEN. Commit ca64a3693.
- 2026-07-02T18:55:00Z – claude:fable:python-pedro:implementer – T022+T023: VERBATIM relocation of _do_move_task + 23 _mt_* + _MoveTaskState + _default_move_task_ports into NEW tasks_move_task.py (1054 LOC); WP02 seam-bridge idiom applied (18 bridged functions; 47 rewritten call sites, all genuine calls — zero docstring collateral; per-symbol routing decided by a full patch-site census incl. multiline patch strings, which caught primary_feature_dir_for_mission ×1 and decide_transition monkeypatch ×2 as routed seams). C-001 _skip_target_branch_commit pre-gate call position untouched. move_task typer wrapper byte-identical, delegates to the re-imported _do_move_task. tasks.py re-imports the full 26-symbol move-set (explicit as form); dead imports removed after per-symbol external-reference checks. inventory.md row followed the code (tasks.py:732 → tasks_move_task.py:204; gate green at BOTH steps). T036 coreless non-vacuity control re-pinned to resolve the move_task closure over tasks_move_task.py (stale premise — the tasks.py wrapper's callee is a re-import, invisible to the FunctionDef scanner). _CEILING 3926→3035 same-commit. Parity 27+16+13 green, unmodified fixtures. Commit 439da97ef.
- 2026-07-02T19:25:00Z – claude:fable:python-pedro:implementer – T024 (FR-012 plumbing rewrite): killing the vacuous arm exposed that ALL THREE floors were vacuous (wave-1 thinned every wrapper; the floors were calibrated on the pre-split single bodies — measuring the _do_* orchestrator alone yields ~0 arcs because it is a linear phase-call sequence). Calibration-faithful basis implemented: _FLOORED_FUNCTION_HOMES {floored_name: ((module, qualname), ...)} = ENTRY home + the PURE-CORE home(s) wave-1 extracted from the calibrated body (map_requirements reproduces the calibrated arc universe 106-vs-104); _same_module_closure resolves entry + same-module phase helpers per home; multi-file include= from the map; per-file cov._analyze merged per command; 0-arcs = pytest.fail. Floors/scenarios/assertions untouched. Honest measured (no-cov pass): move_task 75.9, map_requirements 49.1, status 49.3 — real numbers, none 100.0-vacuous. Commit f69b865ca.
- 2026-07-02T19:30:00Z – claude:fable:python-pedro:implementer – T024 RED-FIRE EVIDENCE (floor temporarily raised 65.0→90.0, no-cov pass, then restored; harness green after restore):
  ```
  E   AssertionError: from-harness branch coverage dropped below the frozen floor (measured%, floor%): {'move_task': (75.9, 90.0)}. A decision branch is now unfrozen — add a driven case before extracting it.
  E   assert not {'move_task': (75.9, 90.0)}
  FAILED tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py::test_from_harness_branch_coverage_ratchet
  ```
- 2026-07-02T19:50:00Z – claude:fable:python-pedro:implementer – T025: test_tasks_move_task_seam.py (40 cases): interception battery (sentinel patches on the tasks namespace driven through the relocated bodies — C-001 pre-gate position + auto-commit-gating pin, decide_transition, review gates, done-ancestry, _detect_reviewer_name, primary_feature_dir_for_mission, read_events_transactional, feature_status_lock, ProtectionPolicy, console, _mt_output quartet, port-adapter construction via tasks bindings) + identity battery over the FULL 26-symbol move-set + completeness guard. Seam-checklist WP05 rows committed on primary (2b09fd32b + 68996e9ec). Coord harness T004 skip-arm + wrong-leg detector and T005 refuse-arms PASSED explicitly. Commit 82bb2352d.
- 2026-07-02T20:20:00Z – claude:fable:python-pedro:implementer – T026: strict-mypy fold — 8 D7 seam symbols converted to explicit as re-exports in tasks.py (no-implicit-reexport); typed intermediate for the issue-matrix blocker return; ruff SIM117/C408/B009 sweep on the new tests; AST import-audit caught tests/agent/test_tasks_helpers.py importing _resolve_wp_slug/_issue_matrix_approval_blocker from tasks (re-exports restored). _CEILING final 3046 (exact achieved size; +11 lines of re-export forms/rationale over the post-move 3035). FINAL EVIDENCE: parity 27 contract + 16 coord + 13 byte green (fixtures untouched); seam battery 40/40; coreless 9/9; gates (LOC ceiling, untrusted-path) green; targeted surface tests/specify_cli/cli/commands/agent/ + tests/tasks/ + tests/agent/ = 2626 passed with 3 non-WP05 reds, each verified pre-existing/environmental on the mission base in a detached worktree (test_fr011_primary_only_inversion = #2307 pre-existing; sphinx e2e pre-existing on base; test_sync empty-queue = serial-class flake, passes isolated and with its own file). mypy --strict on tasks.py + tasks_move_task.py + agent_tasks_ports.py + 4 touched test files together: 0 issues. Diff-scoped ruff: exit 0. Commits a8f55465e + 7ac67cac7.
- 2026-07-02T16:46:24Z – claude:fable:python-pedro:implementer – shell_pid=518107 – WP05 complete: move_task family (26 symbols, 1054 LOC) relocated VERBATIM to tasks_move_task.py with the D1 seam bridge; #2306 inventory fold (gate green pre-fix :732 and post-move tasks_move_task.py:204); FR-012 ratchet plumbing rewritten — multi-home map (entry + wave-1 pure cores = calibrated basis), vacuous 100.0 arm KILLED, RED-fire demonstrated: shortfall {'move_task': (75.9, 90.0)} with floor temporarily raised then restored; honest measured move_task 75.9 / map_requirements 49.1 / status 49.3 vs frozen floors 65/48/46. Parity 27+16+13 green unmodified; T004 skip-arm + wrong-leg detector green; seam battery 40/40 + checklist rows on primary; _CEILING 3926->3046 (exact); mypy --strict 0 issues on touched src+tests together; diff-scoped ruff exit 0. Known non-WP05 reds verified pre-existing on base: #2307 fr011, sphinx e2e; sync empty-queue is a serial-class flake (passes isolated).
- 2026-07-02T16:48:00Z – claude:opus:reviewer-renata:reviewer – shell_pid=622868 – Started review via action command
- 2026-07-02T17:00:23Z – user – shell_pid=622868 – Review passed (reviewer-renata). Verbatim family move: 23 _mt_ helpers + _do_move_task + _MoveTaskState + _default_move_task_ports relocated to tasks_move_task.py (0 remain in tasks.py; bodies byte-identical modulo _tasks. seam bridge), 26-symbol re-import block. C-001 _skip_target_branch_commit pre-gate position identical (T004 skip-arm + wrong-leg + T005 refuse-arms green; full coord harness 16/16). #2306 fold: inventory row followed code tasks.py:1325->tasks_move_task.py:204, commit ca64a3693, untrusted-path gate 5/5. FR-012 ratchet: floors byte-identical 65/48/46, diff-scope clean (only floors-map/line-ranges/include-analyze wiring; scenarios+assertion bodies untouched), vacuous else-100 arm KILLED (pytest.fail on 0 arcs). RED-fire reproduced independently (floor->90, measured move_task 75.9, restored). MULTI-HOME DEVIATION judged PRINCIPLED not curve-fit: the contract-literal single-home form FALSE-REDS map_requirements 45.9<48 and status 45.8<46, proving the wave-1 pure cores (decide_transition/build_transition_plan, plan_mapping, build_status_view/build_stale_fallback_results) are calibration-NECESSARY not padding; arc universe reproduces calibration (map_req 106 possible vs 104 calibrated); homes = exactly the public cores each entry delegates to, no cherry-picking. Vacuity claim verified TRUE (old ratchet measured thin typer wrappers -> ~0 arcs -> 100.0). T036 coreless re-pin is stale-premise (assertion byte-identical, input re-pointed to relocated module), coreless 9/9. Seam battery 40/40, contract 27, byte-freeze 14, ceiling 4 (_CEILING 3046 == actual LOC). mypy --strict 0 issues on 6 touched src+tests, ruff clean. Fixtures untouched across all WP05 commits. Scope clean; #2307 untouched.
