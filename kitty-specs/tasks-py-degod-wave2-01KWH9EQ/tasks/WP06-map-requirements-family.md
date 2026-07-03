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
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "691186"
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
- 2026-07-02T17:01:24Z – claude:fable:python-pedro:implementer – shell_pid=640609 – Assigned agent via action command
- 2026-07-02T18:20:00Z – claude:fable:python-pedro:implementer – T027+T028: VERBATIM relocation of _do_map_requirements + 11 _mr_* + _MapReqState + _default_map_requirements_ports into NEW tasks_map_requirements.py (626 LOC); WP05 seam-bridge idiom applied (49 rewritten call sites, all genuine calls — zero docstring collateral; per-symbol routing decided by a full patch-site census incl. multiline patch strings, which caught the plan_mapping sentinel monkeypatch ×2 (test_tasks_mapping_core.py:307/:341) and the _map_requirements_feature_dir patch ×1 (test_pre30_guard_wiring.py:104) as routed seams). C-001 REFUSE-arm wiring moved untouched: _protected_branch_status_commit_error at its original _mr_resolve_context position, NO _skip_target_branch_commit pre-gate added or removed. map_requirements typer wrapper byte-identical (was already the thin delegate), calls the re-imported _do_map_requirements. tasks.py re-imports the full 14-symbol move-set (explicit as form); plan_mapping kept as explicit as re-export (sentinel seam); SPEC_MD_FILENAME stays tasks.py-owned routed via _tasks.<attr> (WP05 UTC_SECOND_TIMESTAMP_FORMAT precedent); dead imports removed after per-symbol external-reference checks (TRACKER_ONLY_MODE, MappingPlan, MappingRequest, CoverageSummary, CommitTarget, json, kernel._safe_re.re). Byte-freeze suite green after each step (14/14 incl. the 5 family cases). Untrusted-path inventory: NO tasks.py rows remain (the sole family-adjacent row already lives at tasks_move_task.py:204); gate 5/5 green post-move.
- 2026-07-02T18:40:00Z – claude:fable:python-pedro:implementer – T029 (FR-012 re-point, multi-home semantics per tracers/design-decisions.md item 11): pre-re-point the harness hard-failed RED exactly as designed ("floored function '_do_map_requirements' not found in .../tasks.py — the ratchet re-point is broken") — proof the WP05 0-arc/missing-entry guard bites. ENTRY home re-pointed (tasks, "_do_map_requirements") → (tasks_map_requirements, "_do_map_requirements"); the wave-1 pure-core home (tasks_mapping_core, plan_mapping) KEPT; include= derives from the map — new module verified inside the analyze wiring by a real measured %, not a 0-arc hard-fail. Floors byte-identical 65/48/46. Coord harness 16/16 green incl. the refuse-arm case (harness label T005). RED-FIRE EVIDENCE (floor temporarily raised 48.0→90.0, no-cov pass, then restored; harness green after restore):
  ```
  E   AssertionError: from-harness branch coverage dropped below the frozen floor (measured%, floor%): {'map_requirements': (49.1, 90.0)}. A decision branch is now unfrozen — add a driven case before extracting it.
  E   assert not {'map_requirements': (49.1, 90.0)}
  ```
  Honest measured map_requirements 49.1 vs frozen floor 48.0 (matches WP05's post-plumbing-rewrite measurement).
- 2026-07-02T19:00:00Z – claude:fable:python-pedro:implementer – T030: test_tasks_map_requirements_seam.py (29 cases): interception battery (C-001 refuse-arm pin incl. skip_mock.assert_not_called() + protected-gate-not-consulted-when-auto-commit-false, plan_mapping sentinel route, _map_requirements_feature_dir pre30 seam, ProtectionPolicy → commit_artifact policy identity, console/RealRender output legs, _mission_identity_payload, generic exception arm via the routed locate_project_root seam, port-adapter construction via tasks bindings with target_branch threading) + identity battery over the FULL 14-symbol move-set + completeness guard. Seam-checklist WP06 rows committed on primary (8f0a35feb). _CEILING 3046→2524 same-commit (exact achieved size; surface gate 4/4). FINAL EVIDENCE: byte-freeze 14/14 (fixtures untouched); coord harness 16/16; map-req cluster (test_map_requirements* + mapping_core + pre30_wiring + core_backed + coreless + wp03_bypass) 96/96; seam battery 29/29; full surface tests/specify_cli/cli/commands/agent/ + tests/tasks/ + tests/agent/ = 2609 passed with 2 non-WP06 reds, each verified pre-existing at the pre-WP06 lane HEAD in a detached worktree (test_fr011_primary_only_inversion = #2307 pre-existing; sphinx e2e pre-existing). mypy --strict on tasks.py + tasks_map_requirements.py + 3 touched test files together: 0 issues. Diff-scoped ruff: exit 0. Lane commit fd5d99e44.
- 2026-07-02T17:27:58Z – claude:fable:python-pedro:implementer – shell_pid=640609 – WP06 ready: map_requirements family (14 symbols, 626 LOC) relocated VERBATIM to tasks_map_requirements.py with the D1 seam bridge (49 call-site rewrites, census incl. multiline patch strings caught plan_mapping sentinel x2 + _map_requirements_feature_dir x1). C-001 REFUSE arm moved untouched (no skip pre-gate; harness-label-T005 refuse-arm + full coord harness 16/16 green). FR-012 ratchet ENTRY home re-pointed to tasks_map_requirements (plan_mapping core home kept, floors byte-identical 65/48/46); RED fire demonstrated: {'map_requirements': (49.1, 90.0)} with floor raised 48->90 then restored; honest measured 49.1 vs floor 48.0. Byte-freeze 14/14 unmodified fixtures (5 family cases); seam battery 29/29 + checklist rows on primary (8f0a35feb); _CEILING 3046->2524 exact same-commit; parity: map-req cluster 96/96, full surface 2609 passed (2 reds verified pre-existing at pre-WP06 HEAD: #2307 fr011 + sphinx e2e); mypy --strict 0 issues on touched src+tests together; diff-scoped ruff exit 0. Lane commit fd5d99e44.
- 2026-07-02T17:29:32Z – claude:opus:reviewer-renata:reviewer – shell_pid=691186 – Started review via action command
- 2026-07-02T17:43:52Z – user – shell_pid=691186 – Review passed (reviewer-renata): 14/14 map_requirements symbols moved VERBATIM to tasks_map_requirements.py (626 LOC), 3 spot-diffed bodies routing-only (_tasks.<attr> seam-bridge), wrapper byte-identical. C-001 REFUSE arm at original _mr_resolve_context position, NO skip pre-gate; coord harness 16/16 incl. refuse-arm T005; seam battery refuse-arm pin is a real positional pin (skip_mock.assert_not_called + opposite-branch sibling). FR-012 ratchet: entry home re-pointed, plan_mapping core home kept, floors byte-identical 65/48/46, diff-scope respected; RED fire reproduced independently {'map_requirements':(49.1,90.0)} non-vacuous. Byte 14/14, seam 29/29 (identity over full 14-set), surface 4/4, ceiling==LOC==2524; multiline-census seams (plan_mapping setattr, _map_requirements_feature_dir patch) intercept. Deleted imports zero external refs. mypy --strict 0 issues + ruff clean on touched set. Scope clean; the 3 suite reds are non-WP06: #2307 fr011 + sphinx e2e (pre-existing, untouched) + test_empty_queue_exits_0 (flake, passes in isolation, no sync code touched).
