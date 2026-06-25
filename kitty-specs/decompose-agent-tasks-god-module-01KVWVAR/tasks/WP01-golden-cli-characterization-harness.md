---
work_package_id: WP01
title: Golden CLI characterization harness
dependencies: []
requirement_refs:
- FR-001
tracker_refs: []
planning_base_branch: kitty/mission-decompose-agent-tasks-god-module-01KVWVAR
merge_target_branch: kitty/mission-decompose-agent-tasks-god-module-01KVWVAR
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-decompose-agent-tasks-god-module-01KVWVAR. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-decompose-agent-tasks-god-module-01KVWVAR unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Safety net
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2230095"
history:
- at: '2026-06-24T13:22:13Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/cli/commands/agent/
create_intent:
- tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py
- tests/specify_cli/cli/commands/agent/fixtures/tasks_cli/**
execution_mode: code_change
model: ''
owned_files:
- tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py
- tests/specify_cli/cli/commands/agent/fixtures/tasks_cli/**
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Golden CLI characterization harness

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: tests/specify_cli/cli/commands/agent/`.

---

## Objective

Capture the **current** behavior of the `agent tasks` CLI as golden characterization tests, **before
any refactoring happens**, so the decomposition (WP02–07) can be proven byte-identical. This is the
safety net the entire mission rests on (FR-001, C-005, SC-006).

Read `kitty-specs/decompose-agent-tasks-god-module-01KVWVAR/contracts/cli-surface-contract.md` — it
enumerates the 9 commands, their flags, and the invariants (CONTRACT-1…5) you must pin.

## Context

- The target module is `src/specify_cli/cli/commands/agent/tasks.py` (typer `app`, `name="tasks"`).
- The 9 commands: `move-task`, `mark-status`, `list-tasks`, `add-history`, `finalize-tasks`,
  `map-requirements`, `validate-workflow`, `status`, `list-dependents`.
- Existing tests are import-based (they call helper functions directly), so they will NOT catch a
  contract regression when functions move to seams. That is exactly the gap this WP fills.
- Use `typer.testing.CliRunner` against the `app` object — do **not** shell out to the installed CLI.
- **No new dependency**: do not add `pytest-snapshot` or similar. Use plain committed fixture files
  compared in-test.

## Subtasks

### T001 — Build the capture harness
Create `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py`. Add a small helper that
invokes a command via `CliRunner().invoke(app, [...])` and returns `(exit_code, normalized_stdout)`.
Import `app` from `specify_cli.cli.commands.agent.tasks`. Parametrize over the 9 command names.

### T002 [P] — Golden `--help` fixtures for all 9 commands
For each command, capture `<command> --help` output into a committed fixture under
`tests/specify_cli/cli/commands/agent/fixtures/tasks_cli/help/<command>.txt`. Add a test asserting
the live `--help` equals the fixture. Also assert the **top-level** `agent tasks --help` lists
exactly the 9 commands (CONTRACT-1) and that each command's `--help` contains its expected flags
(CONTRACT-2) — see the contract doc for the flag list.

### T003 [P] — Exit-code + `--json` envelope fixtures
Capture representative `--json` outputs and exit codes for the read-only / easily-staged paths
(e.g. `list-tasks --json`, `status --json`, `finalize-tasks --validate-only --json`, an invalid-input
error path returning exit 1, a usage error returning exit 2). Store JSON-shape fixtures (top-level
keys) under `fixtures/tasks_cli/json/`. Assert the live envelope keys match (CONTRACT-3, CONTRACT-4).
You do **not** need full end-to-end mission setup for every command — pin the envelope **shape**
(keys + types), normalizing values.

### T004 — Normalize volatile substrings
Before comparing, normalize absolute paths (→ `<PATH>`), ISO timestamps (→ `<TS>`), ULIDs (→ `<ULID>`),
and the repo root, so fixtures are deterministic across machines and under per-worker HOME isolation
(WP04 parallel-test isolation). Put the normalizer in the test module; document each substitution.

### T005 — Prove green on current code; wire into suite
Run `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py -q` and
confirm all assertions pass against the **current** `tasks.py`. Commit the fixtures. This frozen
baseline is what WP02–07 must keep green.

## Branch Strategy

- Base/merge branch: the mission branch **kitty/mission-decompose-agent-tasks-god-module-01KVWVAR** — lanes merge here; the mission branch PRs to `main` at mission end (`main` is protected).
- Execution worktrees are allocated per computed lane from `lanes.json` during `/spec-kitty.implement`.
- This WP has no dependencies — it runs first.

## Definition of Done

- [ ] `test_tasks_cli_contract.py` exists and passes on current `main`.
- [ ] Golden fixtures committed for all 9 commands' `--help` (CONTRACT-1, CONTRACT-2).
- [ ] Exit-code + `--json` envelope assertions cover the staged paths (CONTRACT-3, CONTRACT-4).
- [ ] Volatile-substring normalizer in place and documented.
- [ ] `ruff` + `mypy --strict` clean on the new test file; no new dependencies added.

## Risks

- **Volatile output** (paths/timestamps/ULIDs) → flaky fixtures. Mitigate with the T004 normalizer.
- **Over-scoping**: don't try to fully exercise every command end-to-end; pin the *contract shape*.
  Deep behavior is already covered by the existing 72-test suite.
- **HOME isolation**: ensure fixtures don't bake in a real `~/.spec-kitty` path.

## Reviewer guidance

Confirm the fixtures genuinely reflect current behavior (not aspirational), the normalizer can't mask
a real contract change (e.g. a renamed flag), and the test fails loudly if a command/flag is
added/removed/renamed. This is the net every later WP relies on — be strict.

## Activity Log

- 2026-06-24T13:39:16Z – claude:opus:python-pedro:implementer – shell_pid=2197563 – Assigned agent via action command
- 2026-06-24T14:00:16Z – claude:opus:python-pedro:implementer – shell_pid=2197563 – Golden CLI characterization harness: all 9 commands pinned (help/flags/exit-codes/json envelope), normalizer in place, suite green
- 2026-06-24T14:01:00Z – claude:opus:reviewer-renata:reviewer – shell_pid=2230095 – Started review via action command
- 2026-06-24T14:05:15Z – user – shell_pid=2230095 – Review passed: 27 tests green; CONTRACT-1/2/3/4 all genuinely assert against live tasks.py (9 cmds set==, byte-frozen help + Click flag subset, exit 0/1/2 pinned, JSON envelope keys+types via _shape); fixtures match live introspection; ruff+mypy --strict clean; scope test-only. NOTE: invoke()/normalize() are dead helpers — net relies on byte-exact help + shape reduction (stronger; normalizer cannot mask a contract change). Recommend removing dead helpers in follow-up, not wiring them in (path regex over-matches lane fragments). issue-matrix rows set in-mission (decomposition WP02-07 own tasks.py).
- 2026-06-24T17:14:27Z – user – shell_pid=2230095 – Moved to done
