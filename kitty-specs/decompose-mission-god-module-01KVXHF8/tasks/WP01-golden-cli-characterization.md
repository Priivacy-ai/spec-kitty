---
work_package_id: WP01
title: Golden CLI characterization harness
dependencies: []
requirement_refs:
- FR-001
- C-001
- C-005
tracker_refs: []
planning_base_branch: prog/2056-mission
merge_target_branch: prog/2056-mission
branch_strategy: Planning artifacts for this mission were generated on prog/2056-mission. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2056-mission unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-decompose-mission-god-module-01KVXHF8
base_commit: cc74304cd7f3ac2d26cc05c3904ff69feb19f276
created_at: '2026-06-24T19:52:40.998893+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Safety net
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2999656"
history:
- timestamp: '2026-06-24T19:52:40Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py
execution_mode: code_change
owned_files:
- tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py
tags: []
---

# Work Package Prompt: WP01 – Golden CLI characterization harness

## Do This First

1. Read `kitty-specs/decompose-mission-god-module-01KVXHF8/contracts/cli-surface-contract.md` (the frozen contract).
2. Read research.md §1 (the 8-command × all-flags table) and §5 (golden-test requirement).
3. This WP captures the safety net BEFORE any extraction. No production code changes — test only.

## Objective

Author a `typer.testing.CliRunner`-based golden characterization test that pins the byte-for-byte
`agent mission` CLI surface so every later WP can prove byte-for-byte preservation.

## Why this is first (C-005)

No single test currently pins the full 8-command × all-flags + JSON-envelope contract. Capturing it FIRST
is the load-bearing safety net for the entire decomposition.

## Implementation

### T001 — Assert the command set
Invoke `app` with `--help` via `CliRunner`; assert it lists exactly the 8 commands (`branch-context`,
`create`, `check-prerequisites`, `record-analysis`, `setup-plan`, `accept`, `merge`, `finalize-tasks`).

### T002 — Assert per-command flags
For each subcommand, invoke `<cmd> --help`; assert the exact flag names + defaults from the contract table
(including `create`'s positional `mission_slug` and the hidden `--mission` deprecation, `record-analysis`'s
`--input-file` default `-`, the `--pr-bound/--no-pr-bound` and `--auto-retry/--no-auto-retry` pairs).

### T003 — Assert representative success envelopes
Drive `branch-context --json` and `check-prerequisites --json` against a fixture mission; assert the
success JSON envelope key set (including `cli_version`/`spec_kitty_version` and mission-alias keys).

### T004 — Assert representative error envelope
Drive `setup-plan --json` with no resolvable mission; assert the `PLAN_CONTEXT_UNRESOLVED` envelope keys
(`error_code`, `error`, `spec_kitty_version`, `available_missions`, `remediation`, `example_command`).
Cross-reference `tests/integration/test_json_envelope_strict.py` (extend, do not replace).

## Acceptance

- The golden test is green against the base (`cc74304cd`).
- ruff + mypy clean on the new test file.

## Out-of-map edits

- None.

## Activity Log

- 2026-06-24T20:24:52Z – claude:opus:randy-reducer:implementer – shell_pid=2956192 – Assigned agent via action command
- 2026-06-24T20:32:52Z – claude:opus:randy-reducer:implementer – shell_pid=2956192 – Golden CLI characterization harness; 16 tests green, ruff+mypy clean
- 2026-06-24T20:32:57Z – claude:opus:reviewer-renata:reviewer – shell_pid=2999656 – Started review via action command
- 2026-06-24T20:33:48Z – user – shell_pid=2999656 – Review passed: 16 golden tests green, full agent suite 337 passed, ruff+mypy clean, test-only
