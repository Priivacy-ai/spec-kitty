---
work_package_id: WP01
title: Golden CLI-characterization harness
dependencies: []
requirement_refs:
- C-004
- FR-001
- NFR-001
tracker_refs: []
planning_base_branch: design/degod-tasks-2116
merge_target_branch: design/degod-tasks-2116
branch_strategy: Planning artifacts for this mission were generated on design/degod-tasks-2116. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/degod-tasks-2116 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Safety net
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2701877"
history:
- at: '2026-07-01T15:16:35Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py
execution_mode: code_change
owned_files:
- tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Golden CLI-characterization harness

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `randy-reducer`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Freeze the **full observable `agent tasks` contract** BEFORE any body extraction (the load-bearing safety net — C-004). Post-squad hardening: the freeze must cover **every** `move_task` decision branch, not just skip/refuse, gated by a from-harness branch-coverage measurement.

- All 9 subcommands' flag/option surface, exit codes {0,1,2}, `--json` top-level keys pinned.
- The coord skip-exit-0 arm, the refuse-exit-1 arms, **and every other named `move_task` guard branch** are frozen via a new coord-topology + protected-branch fixture.
- A from-harness branch-coverage gate on the mutating commands is green; harness is test-only, green on base.

## Context & Constraints

- Read `research.md` (D1, D10), `data-model.md` (§Characterization contract), `contracts/ports-and-cores.md`, `quickstart.md` (Scenario 1).
- **FIRST** (C-004). **Pure parity** (NFR-001): identical before/after every later WP; the skip-vs-refuse inconsistency is preserved (deferred #2300).
- Extend the existing `test_tasks_cli_contract.py` — its docstring punts the coord skip arm + covers no mutating command; this WP closes that.
- Anchors are indicative (re-census at start): skip arm `skip_target_branch_commit` fall-through 1083→1648/1783 (no `typer.Exit(0)`); refuse raises `mark_status:1952`, `map_requirements:2629`.

## Branch Strategy

- **Planning base branch**: `design/degod-tasks-2116`
- **Merge target branch**: `design/degod-tasks-2116`

## Subtasks & Detailed Guidance

### T001 — Command set + flag surface
`CliRunner` `--help` introspection: exact 9-command set + each subcommand's flag names/defaults.

### T002 — Exit codes + `--json` key sets
For each of the 9 subcommands (human + `--json`): exit codes {0,1,2} + `--json` top-level key set. Normalize ULIDs/timestamps/paths — but not so widely that the skip-arm's extra keys are masked.

### T003 — Coord-topology + protected-branch fixture
Fixture class constructing **real on-disk coord-worktree state** (coordination branch + protected primary). Vehicle for T004–T007. Do not stub the topology.

### T004 — Skip-exit-0 arm (DISTINGUISHING evidence)
Drive `move_task` on the coord + protected tree; assert **primary-branch HEAD unchanged** AND the coord event emitted AND conditional `--json` keys (`wp_file_update`/`status_events_path`). Do NOT rely on exit-0 + key-presence alone (a non-skip success also exits 0).

### T005 — Refuse-exit-1 arms
Drive `mark_status` and `map_requirements` on the same tree; assert **exit 1** refuse (current behavior). Comment that the divergence from move_task is deliberately preserved (#2300).

### T006 — Every other move_task decision branch
Freeze, as explicit cases, the branches WP03 will extract: arbiter-override, rejected-verdict, the FR-008a planning-artifact-WP arm, review-currency, and for_review→in_progress force paths. Each must be a driven, asserted case.

### T007 — Side-effects + branch-coverage gate
Freeze the no-stdout side-effect set (coord-vs-primary emission, WP-file writes, tracker-ref frontmatter, review-artifact override to both dirs). Add a **from-harness branch-coverage measurement** of `move_task`/`status`/`map_requirements` (`pytest --cov` on those functions ≥ a stated threshold) so no decision branch is left unfrozen before WP03.

## Test Strategy

- `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py -q` + `--cov` on the three mutating commands. Green on base; ruff+mypy clean.

## Risks & Mitigations

- If T003/T004 stub the topology, or T006 omits a branch, WP03 extracts unguarded logic — the exact failure this WP exists to prevent.

## Review Guidance

- Confirm the fixture is real coord state; T004 asserts primary HEAD unchanged (not exit-0); T006 covers all named branches; the branch-cov gate is present and meets threshold.

## Activity Log

- 2026-07-01T15:16:35Z – system – Prompt created.
- 2026-07-01T17:54:02Z – claude:opus:randy-reducer:implementer – shell_pid=2640389 – Assigned agent via action command
- 2026-07-01T18:33:00Z – claude:opus:randy-reducer:implementer – shell_pid=2640389 – Golden harness: 42 cases green on base, coord skip/refuse/all-branches frozen, from-harness branch-cov ratchet (move_task>=65/map_req>=48/status>=46), ruff+mypy clean, test-only
- 2026-07-01T18:34:07Z – claude:opus:reviewer-renata:reviewer – shell_pid=2701877 – Started review via action command
- 2026-07-01T18:43:11Z – user – shell_pid=2701877 – APPROVED. Golden CLI-characterization harness verified against code (not handoff). Test-only diff (1 file); 42 passed/0 skipped on base (branch-cov ratchet RAN); ruff+mypy clean. T003 coord fixture REAL (git init + real commit + CoordinationWorkspace.resolve worktree); smoke test asserts worktree/.git/coord-branch exist, _coord_topology_active True, _skip_target_branch_commit True(main)/False(non-protected). T004 skip-arm DISTINGUISHING: primary HEAD before==after AND coord_events+1 AND wp_file_update=='skipped' + status_events_path under .worktrees. T005 refuse exit1 same tree, #2300 preserved. All FIVE named move_task decision branches driven+asserted: arbiter-override, rejected-verdict(+override), FR-008a planning-artifact done WITH code_change ancestry CONTRAST, review-currency 'stale', for_review->in_progress force. Uncovered arcs are defensive/IO + real-git commit success path + validation guards in already-seam'd helpers; no named decision arm uncovered. NOTE non-blocking: installed typer 0.25.1 != uv.lock 0.24.2, help fixtures typer-coupled — reconcile before merge.
