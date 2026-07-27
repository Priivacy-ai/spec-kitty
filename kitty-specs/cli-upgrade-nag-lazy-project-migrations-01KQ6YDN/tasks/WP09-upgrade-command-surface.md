---
work_package_id: WP09
title: spec-kitty upgrade command surface (--cli, --project, --yes, --no-nag, --json)
dependencies:
- WP06
requirement_refs:
- FR-012
- FR-013
- FR-014
- FR-015
- FR-016
- FR-017
- FR-019
- FR-020
- FR-021
- FR-022
- FR-023
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T034
- T035
- T036
- T037
- T038
agent: "claude:opus:python-reviewer:reviewer"
shell_pid: "17610"
history:
- at: '2026-04-27T08:19:12Z'
  actor: planner
  note: WP authored from /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/upgrade.py
execution_mode: code_change
mission_id: 01KQ6YDNMX2X2AN4WH43R5K2ZS
mission_slug: cli-upgrade-nag-lazy-project-migrations-01KQ6YDN
owned_files:
- src/specify_cli/cli/commands/upgrade.py
- tests/specify_cli/cli/commands/test_upgrade_command.py
priority: P1
tags: []
---

# WP09 — `spec-kitty upgrade` command surface

## Branch Strategy

- **Planning base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP09 --agent <name>` after WP06 merges. Can run in parallel with WP08.

## Objective

Extend `cli/commands/upgrade.py` with the new flag set: `--cli`, `--project`, `--yes`, `--no-nag`. Make `--cli` work outside any project (FR-014). Make `--project` restrict behavior to current-project migrations (FR-015). Make `--yes` a backward-compatible alias for `--force` (FR-017, A-006). Implement `--json` and `--dry-run --json` to emit the contract from `contracts/compat-planner.json`.

Preserve all existing flags (`--dry-run`, `--force`, `--target`, `--verbose`, `--no-worktrees`) per C-006.

## Context

- Spec: FR-006, FR-007, FR-012, FR-013, FR-014, FR-015, FR-016, FR-017, FR-022, FR-023.
- Plan: §"Engineering Alignment" Q2-A; §"Implementation phasing" step 3.
- Research: [`research.md`](../research.md) §R-08 (exit codes), §R-09 (JSON stability).
- Contracts: [`contracts/compat-planner.json`](../contracts/compat-planner.json).
- Quickstart: [`quickstart.md`](../quickstart.md) §3-§5, §8.
- Existing: `src/specify_cli/cli/commands/upgrade.py` (look at the current flag set; new flags are additive).

## Subtasks

### T034 — New flags on `cli/commands/upgrade.py`

**Steps**:
1. Add typer options to the `upgrade` command:
   - `--cli` (boolean) — restrict to CLI guidance.
   - `--project` (boolean) — restrict to current-project compat + migrations.
   - `--yes` (boolean) — non-interactive confirmation; aliases `--force`.
   - `--no-nag` (boolean) — suppress nag (already handled by callback, but exposed here for explicit override).
2. **Mutual exclusion**: `--cli` AND `--project` together returns `BLOCK_INCOMPATIBLE_FLAGS` (exit 2) with a clear typer-style usage error.
3. **`--yes` aliasing `--force`**: in the command body, `confirm = yes or force` — both flags trip the same suppression. Don't deprecate `--force`; both work.
4. Update the command's docstring (`help=` text) to document the new flags and reference `docs/how-to/install-and-upgrade.md`.

**Files**: `src/specify_cli/cli/commands/upgrade.py`.

**Validation**: `spec-kitty upgrade --help` shows the new flags; `spec-kitty upgrade --cli --project` errors with exit 2.

### T035 — `--cli` mode

**Steps**:
1. When `--cli` is set:
   - Skip the project-side flow entirely (don't try to detect or open the current project).
   - Build an `Invocation` with `command_path=("upgrade",)`, `raw_args` including `--cli`.
   - Call `compat.plan(invocation)` — the planner returns a `Plan` with CliStatus and InstallMethod populated, ProjectStatus=NO_PROJECT.
   - Print `result.rendered_human` to stdout (this is the CLI guidance use case — stdout is appropriate; quickstart §5 example matches this).
   - Exit 0 (or 5 if CLI itself is too old to run, but that's a self-incompatibility — practically always 0 here).
2. **No "not a Spec Kitty project" error** (FR-014): even outside a project, `--cli` succeeds.

**Files**: `src/specify_cli/cli/commands/upgrade.py` (extend).

**Validation**: `cd /tmp; spec-kitty upgrade --cli` exits 0 with install-method-specific guidance.

### T036 — `--project` mode

**Steps**:
1. When `--project` is set:
   - Run the existing project-upgrade flow (already implemented today via `upgrade.runner.UpgradeRunner` and friends).
   - Skip CLI nag rendering.
   - If invoked outside a project, exit with a clear "no project here" error (this is the inverse of `--cli`).
2. Wire the existing flags (`--dry-run`, `--target`, `--no-worktrees`, `--verbose`) through unchanged.

**Files**: `src/specify_cli/cli/commands/upgrade.py` (extend).

**Validation**: `spec-kitty upgrade --project --dry-run` shows the project plan only; CLI status not printed.

### T037 — `--json` / `--dry-run --json` per contract

**Steps**:
1. When `--json` is set (with or without `--dry-run`):
   - Suppress all human stdout (no banner, no nag).
   - Build the `Plan` via the planner.
   - Print `json.dumps(result.rendered_json, indent=2)` to stdout.
   - Exit code follows research §R-08: `--dry-run --json` always 0; non-dry-run `--json` follows the planner's `exit_code`.
2. **Contract validation**: in tests, validate the emitted JSON against `kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/contracts/compat-planner.json` using stdlib `jsonschema` if available. Hand-check key set otherwise.
3. **Stable schema**: emit `schema_version: 1` always.

**Files**: `src/specify_cli/cli/commands/upgrade.py` (extend).

**Validation**: every example in the contract JSON is reproducible by invoking the right combination of fixture and flags.

### T038 — Integration tests covering all 5 FR-023 cases

**Steps**:
1. `tests/specify_cli/cli/commands/test_upgrade_command.py`:
   - Test matrix:
     - **cli_update_available**: outdated CLI, compatible project; `upgrade --dry-run` shows nag + project plan.
     - **project_migration_needed**: stale project; `upgrade --dry-run` lists pending migrations; `upgrade --yes` applies them.
     - **project_too_new_for_cli**: too-new project; `upgrade --dry-run` shows CLI upgrade hint; `upgrade --yes` is REJECTED (CHK037).
     - **project_not_initialized**: no project; `upgrade --cli` succeeds with hint; `upgrade --project` errors.
     - **install_method_unknown**: install method = unknown; `upgrade --cli` prints manual instructions, NOT a runnable command (CHK031).
   - For each: assert exit code, assert key strings in stdout/stderr, validate JSON output against contract.
   - Use injected `LatestVersionProvider` and fixture projects.
2. Run existing upgrade-related tests (`pytest tests/specify_cli/upgrade/`) to confirm no regression on the existing flow.

**Files**: `tests/specify_cli/cli/commands/test_upgrade_command.py`.

**Validation**: `pytest tests/specify_cli/cli/commands/test_upgrade_command.py -v` green; existing upgrade tests unchanged.

## Definition of Done

- [ ] `--cli`, `--project`, `--yes`, `--no-nag` flags added; `--cli` + `--project` returns exit 2.
- [ ] `--yes` is functionally equivalent to `--force`; both supported.
- [ ] `--cli` works outside any project (FR-014).
- [ ] `--project` restricts to current-project; CLI nag suppressed.
- [ ] `--json` emits a payload matching `contracts/compat-planner.json`.
- [ ] All 5 FR-023 cases reachable via the matrix in test_upgrade_command.py.
- [ ] Existing upgrade tests still pass (NFR-006 / C-006).
- [ ] `mypy --strict` clean.
- [ ] `ruff check` clean.

## Risks

- Existing `upgrade.py` may have entangled logic between CLI status and project status. Refactor incrementally; each new flag adds a branch rather than rewrites.
- `--yes` semantics: confirm `--force` behavior today (it suppresses confirmation prompts). `--yes` is a synonym; both should work; passing both is allowed (no error).
- The JSON contract has `oneOf` between `command` and `note` in `upgrade_hint`. Make sure exactly one is non-None in the actual output.

## Reviewer Guidance

1. **Backward compat**: every existing flag still works (run the existing test suite).
2. **`--cli` outside project**: literally `cd /tmp && spec-kitty upgrade --cli` succeeds, no "not a Spec Kitty project" message.
3. **`--yes` does NOT bypass too-new schema**: `--yes` against a too-new project still exits 5. Verify with a parametrised test.
4. **JSON cleanliness**: `spec-kitty upgrade --json | jq .` produces no errors. No nag prefix on stdout.
5. **Stable token names**: `case` field uses one of the seven enumerated tokens.

## Implementation command

```bash
spec-kitty agent action implement WP09 --agent <name>
```

## Activity Log

- 2026-04-27T10:10:24Z – claude:sonnet:python-implementer:implementer – shell_pid=13127 – Started implementation via action command
- 2026-04-27T10:23:48Z – claude:sonnet:python-implementer:implementer – shell_pid=13127 – Ready: new flags + JSON contract emission + 5 FR-023 case integration matrix
- 2026-04-27T10:24:08Z – claude:opus:python-reviewer:reviewer – shell_pid=17610 – Started review via action command
- 2026-04-27T10:27:28Z – claude:opus:python-reviewer:reviewer – shell_pid=17610 – Review passed: all 36 new + 624 existing gate tests green; mypy --strict and ruff clean; --cli/--project mutex exit 2; --yes/--force do NOT bypass too-new schema (exit 5 holds); --cli works outside project (no 'not a Spec Kitty project'); JSON emits schema_version=1 per compat-planner.json contract; all 5 FR-023 cases covered; existing flags preserved per C-006.
