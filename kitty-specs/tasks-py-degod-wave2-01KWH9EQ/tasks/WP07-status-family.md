---
work_package_id: WP07
title: status family relocation
dependencies:
- WP06
requirement_refs:
- FR-001
- FR-012
tracker_refs: []
planning_base_branch: degod-follow-ups
merge_target_branch: degod-follow-ups
branch_strategy: Planning artifacts for this mission were generated on degod-follow-ups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into degod-follow-ups unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
phase: Phase 3 - Family relocations
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "774420"
history:
- at: '2026-07-02T12:53:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- src/specify_cli/cli/commands/agent/tasks_status_cmd.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks_status_cmd.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – status family relocation

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

Relocate the status family — `_do_status` (tasks.py:4431 region) + 14 `_st_*` glue +
`_StatusState` + `_default_status_ports` — VERBATIM into NEW
`src/specify_cli/cli/commands/agent/tasks_status_cmd.py` (named `_cmd` to avoid clashing
with the existing `tasks_status_view.py` pure core); thin the wrapper; re-point the
`status` ratchet entry (FR-012).

By this point WP04 has already deleted `_StatusRender` — `_default_status_ports`
constructs `RealRender(console=console, indent=2)`; it moves as-is. The status byte case
(indent=2) is the acceptance tripwire.

**Shared-surface note**: edits `tasks.py`, the coord-harness ratchet block, and the
gate-file ceiling — sequential shared surfaces.

## Context & Constraints

- WP05/WP06 Activity Logs — the proven family-move recipe; copy it.
- `research.md` D2/D3 (status leg), D7 (seam symbols this family calls — `console` ×5 is
  patched: keep the module `console` binding in `tasks.py` and route via `_tasks.console`
  where the moved code references it).
- The `status` command's `--json` leg emits via `print(ports.render.json_envelope(result))`
  — that call moves verbatim inside `_do_status`.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: degod-follow-ups
- **Merge target branch**: degod-follow-ups

## Subtasks & Detailed Guidance

### Subtask T031 – Create `tasks_status_cmd.py`

- **Steps**: Cut VERBATIM (`grep -nE '^def _st_|class _StatusState|def _default_status_ports|def _do_status' tasks.py`); seam-bridge routing for D7 symbols (`_tasks.console`, `_tasks.locate_project_root`, shared helpers, …); no module-level `tasks` import; module named `tasks_status_cmd.py` (docstring notes the `_view` core distinction).
- **Files**: new module (~450–600 lines), `tasks.py` deletions.

### Subtask T032 – Thin the wrapper + bindings

- **Steps**: `status` `@app.command` wrapper → thin delegate (typer signature frozen by help fixtures); `tasks.py` binds back moved symbols tests touch (`grep -rn "tasks\._st_\|_StatusState\|_default_status_ports" tests/`).

### Subtask T033 – Ratchet re-point: status

- **Steps**: Update the WP05-built `{floored_name: (module, qualname)}` map:
  `"status": (tasks_status_cmd, "_do_status")` — and ADD the new module to the coverage
  session's `include=[...]` set. Floors unchanged; the vacuous-fallback removal (WP05)
  stays: a 0-arc floored function hard-fails. **Acceptance evidence**: a demonstrated
  RED fire of the re-pointed entry (paste failing output, restore) — not a recorded
  percentage.
- **Files**: `test_tasks_cli_contract_coord.py` (ratchet block only — WP05's diff-scope rule applies).

### Subtask T034 – Parity guard + ceiling ratchet

- **Steps**: Full parity guard — the indent=2 status byte case is the headline check; targeted surface; `_CEILING` lowered same-commit; mypy strict src+tests together; ruff; seam-checklist rows appended to the committed `seam-checklist.md` with is-identity tests for every moved patched symbol.

## Test Strategy

```bash
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py -q  # ratchet touched
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ tests/tasks/ -q -p no:cacheprovider
PWHEADLESS=1 pytest tests/architectural/test_tasks_command_surface.py -q
python -m mypy --strict src/specify_cli/cli/commands/agent/tasks.py src/specify_cli/cli/commands/agent/tasks_status_cmd.py <touched tests>
```

## Risks & Mitigations

- **Indent-leg byte drift** → the WP01 status byte case; run per subtask.
- **Name confusion with `tasks_status_view.py`** → `_cmd` suffix + docstrings; imports reviewed.
- **`console` patch seam** (×5): binding + `_tasks.console` routing — spot-check one patching test.

## Review Guidance

- Verbatim-move diff; wrapper thin; ratchet floors unchanged, target re-pointed.
- Status byte case green with fixtures unmodified.
- No stray references to the deleted `_StatusRender` reintroduced.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-02T12:53:55Z – system – Prompt created.
- 2026-07-02T17:44:42Z – claude:fable:python-pedro:implementer – shell_pid=729535 – Assigned agent via action command
- 2026-07-02T18:55:00Z – claude:fable:python-pedro:implementer – T031+T032: VERBATIM relocation of _do_status + 14 _st_* + _StatusState + _default_status_ports (17 defs) into NEW tasks_status_cmd.py (670 LOC; `_cmd` suffix — docstring notes the distinction from the tasks_status_view pure core); WP05/WP06 seam-bridge idiom applied (26 rewritten call sites, all genuine calls — zero docstring collateral; per-symbol routing decided by a full patch-site census incl. multiline patch strings, which caught the build_status_view sentinel monkeypatch ×2 (test_tasks_status_view.py:333/:352), the conftest console rebinding (agent/conftest.py:81) and the multiline get_status_read_root patch (test_pre30_guard_wiring.py:74) as routed seams). _default_status_ports moved as-is constructing RealRender(console=_tasks.console, indent=2) — the ONE indent=2 envelope; the status --json print(ports.render.json_envelope(result)) moved verbatim inside _st_emit_json. status typer wrapper untouched (was already the thin delegate), calls the re-imported _do_status. tasks.py re-imports the full 17-symbol move-set (explicit as form); build_status_view kept as explicit as re-export (sentinel seam, the plan_mapping precedent); get_status_read_root kept (D7 ×3); RealCoordCommitRouter converted to explicit as form (ports-construction seam + remaining _default_finalize_ports caller — required by mypy --strict attr-defined); tasks.py-resident helpers (_review_stall_threshold_minutes, _get_hic_marker, _apply_stale_status_fields, _render_stale_status) stay per the T007 partition record, routed via _tasks.<attr>; 10 dead imports removed after per-symbol external-reference checks (Any, StatusEvent, PROGRESS_SEMANTICS, resolve_lane_alias, MissingLanesError, get_normalized_wp, StatusRequest, StatusView, build_stale_fallback_results, StatusSnapshot). Byte-freeze suite green after each step (13/13 incl. status_success_indent2 — the headline indent=2 byte case, fixtures untouched).
- 2026-07-02T19:10:00Z – claude:fable:python-pedro:implementer – T033 (FR-012 re-point, multi-home semantics per tracers/design-decisions.md item 11): pre-re-point the harness hard-failed RED exactly as designed ("status: floored function '_do_status' not found in .../tasks.py — the ratchet re-point is broken") — proof the WP05 missing-entry guard bites. ENTRY home re-pointed (tasks, "_do_status") → (tasks_status_cmd, "_do_status"); the wave-1 pure-core homes (tasks_status_view: build_status_view + build_stale_fallback_results) KEPT; include= derives from the map — new module verified inside the analyze wiring by a real measured %, not a 0-arc hard-fail. Floors byte-identical 65/48/46. Coord harness 16/16 green. tasks_module import removed from the harness (dead after the re-point — its last code use WAS the old entry home). RED-FIRE EVIDENCE (floor temporarily raised 46.0→90.0, no-cov pass, then restored; harness green after restore):
  ```
  E   AssertionError: from-harness branch coverage dropped below the frozen floor (measured%, floor%): {'status': (51.7, 90.0)}. A decision branch is now unfrozen — add a driven case before extracting it.
  E   assert not {'status': (51.7, 90.0)}
  ```
  Honest measured status 51.7 vs frozen floor 46.0 (above WP01's calibrated 49.0 — the entry-plus-closure basis over the relocated module).
- 2026-07-02T19:25:00Z – claude:fable:python-pedro:implementer – T034: test_tasks_status_cmd_seam.py (29 cases): interception battery (resolution-seam cluster through _st_resolve_dirs' error leg incl. get_status_read_root ×3, resolve_workspace_for_wp mocked-env seam, console no-WPs leg, _review_stall_threshold_minutes route, sentinel-view + identity + auto-commit drive of _st_emit_json (json leg) AND _st_render_human (human leg, with _apply_stale_status_fields not-consulted pin), _get_hic_marker board-cell + render-active routes, _render_stale_status label route, generic exception arm via the routed locate_project_root seam, _default_status_ports construction via tasks bindings pinning console=tasks.console + indent=2) + identity battery over the FULL 17-symbol move-set + completeness guard. Seam-checklist WP07 rows committed on primary. _CEILING 2524→1979 same-commit (exact achieved size; surface gate green). FINAL EVIDENCE: byte-freeze 13/13 (fixtures untouched; status_success_indent2 green); golden contract + coord harness (16/16 incl. re-pointed ratchet) green; seam battery 29/29; full surface tests/specify_cli/cli/commands/agent/ + tests/tasks/ + tests/agent/ = 2638 passed with 2 non-WP07 reds, each verified pre-existing at the pre-WP07 lane HEAD (9c79e4919) in a detached worktree (test_fr011_primary_only_inversion = #2307 pre-existing; sphinx e2e pre-existing). mypy --strict on tasks.py + tasks_status_cmd.py + 3 touched test files together: 0 issues. Diff-scoped ruff: exit 0. Lane commit f46538ef6.
- 2026-07-02T18:10:02Z – claude:fable:python-pedro:implementer – shell_pid=729535 – WP07 ready: status family (17 symbols, 670 LOC) relocated VERBATIM to tasks_status_cmd.py with the D1 seam bridge (26 call-site rewrites; census incl. multiline patch strings caught build_status_view sentinel x2 + conftest console rebinding + get_status_read_root pre30 multiline site). Headline indent=2 status byte case (status_success_indent2) green after every subtask, fixtures unmodified. FR-012 ratchet ENTRY home re-pointed to tasks_status_cmd (tasks_status_view core homes kept, floors byte-identical 65/48/46); RED fire demonstrated: {'status': (51.7, 90.0)} with floor raised 46->90 then restored; honest measured 51.7 vs floor 46.0; missing-entry hard-fail witnessed pre-re-point. Byte-freeze 13/13; seam battery 29/29 + checklist rows on primary (96d3fe20b); _CEILING 2524->1979 exact same-commit; parity: full surface 2638 passed (2 reds verified pre-existing at pre-WP07 HEAD 9c79e4919 in a detached worktree: #2307 fr011 + sphinx e2e); mypy --strict 0 issues on touched src+tests together; diff-scoped ruff exit 0. Lane commit f46538ef6.
- 2026-07-02T18:11:07Z – claude:opus:reviewer-renata:reviewer – shell_pid=774420 – Started review via action command
- 2026-07-02T18:20:41Z – user – shell_pid=774420 – Review passed: verbatim status-family move (17 symbols, 670-LOC tasks_status_cmd.py, zero residual defs); 3 bodies byte-identical bar _tasks routing; byte suite 14/14 + byte_contracts.json untouched by WP07 (indent=2 RealRender as-is, _st_emit_json verbatim); ratchet re-pointed to (tasks_status_cmd,_do_status) w/ both view core homes kept, floors 65/48/46 identical, RED fire reproduced {'status':(51.7,90.0)} then restored, tasks_module import removal legitimate (sole code use re-pointed); console seam kept+routed, sentinel/get_status_read_root/conftest seams intercept (seam battery 29/29, status_view 21, pre30 14); 10 dead imports removed no dangling refs; ceiling 1979==LOC, mypy --strict 0 issues, ruff clean; scope = 5 sanctioned files, #2307/sphinx untouched, RealCoordCommitRouter as-form consumed by _default_finalize_ports.
