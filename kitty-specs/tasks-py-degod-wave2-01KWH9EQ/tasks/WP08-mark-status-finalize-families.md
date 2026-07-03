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
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "842552"
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
- 2026-07-02T18:21:36Z – claude:fable:python-pedro:implementer – shell_pid=790167 – Assigned agent via action command
- 2026-07-02T18:30:00Z – claude:fable:python-pedro:implementer – T035: VERBATIM relocation of _do_mark_status + 9 _ms_* + _MarkStatusState + _default_mark_status_ports (12 symbols, 424-LOC tasks_mark_status.py); WP05–WP07 seam-bridge idiom applied; per-symbol routing decided by a full patch-site census incl. multiline patch strings and setattr forms (emit_history_added ×10, feature_status_lock D7, locate_project_root incl. the setattr(tasks_mod, ...) site test_mark_status_input_shapes.py:87, get_auto_commit_default, emit_error_logged, console conftest rebinding, ProtectionPolicy, the tasks_shared helpers, port adapters via tasks bindings incl. _MarkStatusCoordRouter). Mechanical verbatim proof: AST per-def diff vs HEAD — all 12 bodies verbatim modulo _tasks routing (zero non-routing deltas). C-001 REFUSE arm moved untouched: _protected_branch_status_commit_error at its original _ms_resolve_context position, NO _skip_target_branch_commit pre-gate added or removed. _resolve_inline_subtasks stays tasks.py-resident (zero external refs; only caller routes via _tasks.<attr> — the WP07 T007-partition precedent). mark_status typer wrapper untouched (already the thin delegate), calls the re-imported _do_mark_status; tasks.py re-imports the full 12-symbol move-set (explicit as form). Byte suite 14/14 + golden contract 27 + coord harness 16/16 (incl. refuse-arm case, harness label T005) green after the move. Lane commit 3dfc45d4d.
- 2026-07-02T18:40:00Z – claude:fable:python-pedro:implementer – T036: VERBATIM relocation of _do_finalize_tasks + 4 _ft_* + _FinalizeState + _default_finalize_ports (7 symbols, 313-LOC tasks_finalize.py — the squad-recovered FIFTH family; ALL five command families now out of tasks.py). Sequenced fully after T035 (own reviewable commit). Census-routed seams: bootstrap_canonical_state ×7 (test_tasks_canonical_cleanup + coreless), resolve_feature_dir_for_mission ×1 (pre30-guard-wiring multiline site), console, emit_error_logged, the tasks_shared helpers; _default_finalize_ports constructs via _tasks bindings incl. the plain RealCoordCommitRouter (research.md/tasks.py census: the WP07-era as-form re-export was retained precisely for ports-construction — routing via _tasks preserves @patch interception; finalize has ZERO emission sites so no byte case is family-owned). tasks_finalize_validation gate names (validate_wp_coverage etc.) imported directly — zero patch sites, canonical home. Mechanical verbatim proof: AST per-def diff vs HEAD~1 — all 7 bodies verbatim modulo _tasks routing. Byte suite green after the move (14/14, fixtures untouched).
- 2026-07-02T18:45:00Z – claude:fable:python-pedro:implementer – T037: wrappers verified already-thin (WP06/WP07 finding confirmed — both @app.command wrappers were byte-identical delegates pre-move; neither touched). tasks.py binds back both full move-sets (explicit as form; 12+7 symbols). Dead imports removed after per-symbol external-reference checks (AST import/attr/patch-string sweep over tests/+src/ incl. multiline strings): BootstrapResult, MissionHandle, TasksPorts, TASKS_MD_FILENAME, dataclass/field, _resolve_checkbox, _resolve_pipe_table, _resolve_wp_id, _resolve_history_wp_id, FrontmatterUpdatePlan + the 5 finalize-only tasks_finalize_validation gate names. Strict-mypy fold (WP05/WP07 precedent): emit_history_added + resolve_feature_dir_for_mission converted to explicit as re-exports (dual direct-use + routed-seam symbols; no-implicit-reexport attr-defined); _normalize_task_id_input kept as as-form (test_mark_status_input_shapes.py imports it from tasks ×7). NO-RATCHET-ENTRY CLAIM VERIFIED against the live multi-home map (test_tasks_cli_contract_coord.py): _BRANCH_COVERAGE_FLOORS = {move_task: 65.0, map_requirements: 48.0, status: 46.0}; _FLOORED_FUNCTION_HOMES carries the same three keys only — neither mark_status nor finalize_tasks has an entry; no re-point performed (the WP05 mechanism was not exercised). Coord harness 16/16 green incl. the mark_status refuse-exit-1 case.
- 2026-07-02T18:55:00Z – claude:fable:python-pedro:implementer – T038: test_tasks_mark_status_seam.py (30 cases) + test_tasks_finalize_seam.py (17 cases): interception batteries (C-001 refuse-arm positional pin incl. skip_mock.assert_not_called() + protected-gate-not-consulted sibling; feature_status_lock lock-span pin; _resolve_inline_subtasks routed-resident pin; emit_history_added WP-grouped payload; RealRender no-IDs json leg (the family byte case); ProtectionPolicy→commit_artifact policy identity + TASKS_INDEX kind; FsReader kind pins (TASKS_INDEX / WORK_PACKAGE_TASK); bootstrap_canonical_state + resolve_feature_dir_for_mission coord-aware STATUS-partition pins; both _ft_output envelope shapes; generic exception arms via the routed locate_project_root seam; both _default_*_ports constructions via tasks bindings) + identity batteries over BOTH full move-sets (12+7) + completeness guards. Seam-checklist WP08 rows (both families) committed on primary. _CEILING 1979→1470 same-commit (exact achieved size; raw post-move 1458 + 12 lines of strict-mypy as-form rationale; surface gate 4/4). FINAL EVIDENCE: parity 14 byte + 27 contract + 16 coord + 4 surface green (fixtures untouched); seam batteries 47/47; full surface tests/specify_cli/cli/commands/agent/ + tests/tasks/ + tests/agent/ = 2685 passed with 2 non-WP08 reds, each verified pre-existing at the pre-WP08 lane HEAD (d09756c8f) in a detached worktree (test_fr011_primary_only_inversion = #2307 pre-existing; sphinx e2e pre-existing). mypy --strict on tasks.py + tasks_mark_status.py + tasks_finalize.py + both seam test files + the surface gate test together: 0 issues. Ruff on the full touched set: exit 0. Lane commits 3dfc45d4d + bc8aa39b8.
- 2026-07-02T18:51:19Z – claude:fable:python-pedro:implementer – shell_pid=790167 – WP08 ready: mark_status family (12 symbols, 424-LOC tasks_mark_status.py) + finalize family (7 symbols, 313-LOC tasks_finalize.py — the FIFTH family; ALL five families now out of tasks.py) relocated VERBATIM with the D1 seam bridge (AST per-def diff proof: zero non-routing deltas). C-001 REFUSE arm untouched (no skip pre-gate; coord harness 16/16 incl. refuse-arm T005). No-ratchet-entry claim VERIFIED against the live map (floors/homes = move_task/map_requirements/status only; no re-point). Seam batteries 30+17 incl. positional refuse-arm pin (skip_mock.assert_not_called); checklist rows on primary. _CEILING 1979->1470 exact same-commit. Parity 14 byte + 27 contract + 16 coord + 4 surface green, fixtures untouched; full surface 2685 passed (2 reds pre-existing at d09756c8f: #2307 fr011 + sphinx e2e, verified in detached worktree). mypy --strict 0 issues on touched src+tests together; ruff exit 0. Lane commits 3dfc45d4d + bc8aa39b8.
- 2026-07-02T18:52:26Z – claude:opus:reviewer-renata:reviewer – shell_pid=842552 – Started review via action command
- 2026-07-02T19:02:26Z – user – shell_pid=842552 – Review passed: mark_status (12 syms) + finalize (7 syms) VERBATIM (full AST body-diff of all 19 = zero non-routing deltas); C-001 refuse arm intact (protected-gate unconditional, no skip pre-gate; coord harness 16/16 + positional skip_mock.assert_not_called pin); zero _ms_/_ft_ defs left in tasks.py — ALL 5 families out. Heavy seams intercept (seam batteries 47/47; pre-existing test_tasks_mark_status.py 14/14 patches feature_status_lock + emit_status_transition_transactional through relocated path). No-ratchet-entry TRUE (floors/homes exactly 3 keys move_task/map_requirements/status; ratchet block untouched). Parity 14 byte+27 contract+16 coord+4 surface green; fixtures untouched. 4 deleted imports zero external refs; dual-use re-exports (emit_history_added, resolve_feature_dir_for_mission) still intercept. Ceiling 1470==actual LOC same commit (1400 cap deferred to WP09). mypy --strict 6-file set 0 issues; ruff clean. 2 reds (#2307 fr011, sphinx) pre-existing + unrelated (0 refs to move-set).
