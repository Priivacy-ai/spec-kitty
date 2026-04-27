---
work_package_id: WP08
title: CLI typer callback wired through planner + safe/unsafe matrix tests
dependencies:
- WP06
- WP07
requirement_refs:
- FR-002
- FR-003
- FR-005
- FR-008
- FR-011
- NFR-001
- NFR-003
- NFR-004
- NFR-007
planning_base_branch: main
merge_target_branch: main
branch_strategy: Worktree branch derived from lanes.json by spec-kitty implement; final merge target is main.
subtasks:
- T030
- T031
- T032
- T033
history:
- at: '2026-04-27T08:19:12Z'
  actor: planner
  note: WP authored from /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/helpers.py
execution_mode: code_change
mission_id: 01KQ6YDNMX2X2AN4WH43R5K2ZS
mission_slug: cli-upgrade-nag-lazy-project-migrations-01KQ6YDN
owned_files:
- src/specify_cli/cli/helpers.py
- tests/cli_gate/__init__.py
- tests/cli_gate/test_safe_commands.py
- tests/cli_gate/test_unsafe_commands.py
- tests/cli_gate/test_ci_determinism.py
- tests/cli_gate/conftest.py
priority: P1
tags: []
---

# WP08 — CLI typer callback wired through planner

## Branch Strategy

- **Planning base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP08 --agent <name>` after WP06 and WP07 merge.

## Objective

Wire the typer callback in `cli/helpers.py` to consult `compat.plan(...)` and render the result. The callback is the **single chokepoint** through which every CLI invocation passes — by routing it through the planner, the spec's gate semantics become a single line of code at the command boundary.

Add the integration tests for the safe/unsafe command matrix and CI determinism.

## Context

- Spec: FR-002, FR-003, FR-008, FR-011, NFR-001, NFR-002, NFR-004, SC-005, SC-006.
- Plan: §"Engineering Alignment" §"Implementation phasing" step 3.
- Research: [`research.md`](../research.md) §R-07 (CI predicate), §R-08 (exit codes).
- Data model: [`data-model.md`](../data-model.md) §1.12 (`Invocation`).
- Existing: `src/specify_cli/cli/helpers.py` houses `BannerGroup` and the simple-help renderer. The schema gate currently lives in `migration/gate.py` and is invoked from `cli/helpers.py` (or wherever the typer app is constructed — inspect to confirm).

## Subtasks

### T030 — Update `cli/helpers.py` typer callback

**Steps**:
1. Locate the typer app's pre-dispatch callback (likely a function decorated with `@app.callback()` or invoked via `BannerGroup`). If none exists, add one.
2. Inside the callback:
   - Build an `Invocation` from typer context (`ctx.invoked_subcommand`, `ctx.args` via parent, and `sys.argv`).
   - Call `result = compat.plan(invocation)`.
   - Stash the `result` on `ctx.obj` so subcommands can read it without re-planning.
3. Render handling:
   - If `result.decision == Decision.ALLOW`: return (let typer dispatch).
   - If `result.decision == Decision.ALLOW_WITH_NAG` AND not `invocation.suppresses_nag()` AND nag enabled: print `result.rendered_human` to **stderr** (so it doesn't pollute stdout/JSON consumers); update nag cache (`record.last_shown_at = now`); return.
   - If `result.decision in {BLOCK_PROJECT_MIGRATION, BLOCK_CLI_UPGRADE, BLOCK_PROJECT_CORRUPT, BLOCK_INCOMPATIBLE_FLAGS}`: print `result.rendered_human` to stderr; raise `SystemExit(result.exit_code)`.

**Files**: `src/specify_cli/cli/helpers.py`.

**Validation**: existing CLI commands still run; new behavior triggers in the right cases.

### T031 — Nag rendering + block rendering with exit codes

**Steps**:
1. Use `rich.console.Console(stderr=True)` for both nag and block renders. Style is plain (no ANSI codes that could mangle redirected stderr) — explicitly disable color when `not stderr.isatty()`.
2. Single-line nag: format from `result.rendered_human` directly (planner already produced it). Trim trailing newlines.
3. Block message: ≤4 lines (NFR-007). Already enforced by planner; just print.
4. Exit codes: 4 (project migration), 5 (CLI upgrade), 6 (corrupt metadata), 2 (incompatible flags), 0 otherwise. The planner returns the right code in `result.exit_code`; this WP just uses it.

**Files**: `src/specify_cli/cli/helpers.py` (extend).

**Validation**: stderr captured in tests matches the planner's `rendered_human`; `result.returncode` matches the planner's `exit_code`.

### T032 — Suppress nag under JSON / quiet / no-TTY / CI

**Steps**:
1. The suppression predicate is owned by `Invocation.suppresses_nag()` (defined in WP06's planner). The callback only checks the result.
2. Additionally suppress nag when `--json` or `--quiet` appears in `sys.argv` (these are command-level flags; the predicate may not catch them depending on argv parse). Belt-and-suspenders: check `("--json" in sys.argv) or ("--quiet" in sys.argv)` before printing.
3. Even when nag is suppressed, the `last_shown_at` cache update is **also** suppressed — we don't want a CI run to silently consume a user's throttle window.

**Files**: `src/specify_cli/cli/helpers.py` (extend).

**Validation**: `CI=1 spec-kitty status` produces no nag and the cache is unchanged after the call.

### T033 — Integration tests: safe matrix, unsafe matrix, CI determinism

**Steps**:
1. `tests/cli_gate/conftest.py`:
   - Fixture `fixture_project_compatible(tmp_path)` — creates a `.kittify/metadata.yaml` with `spec_kitty.schema_version: 3`.
   - Fixture `fixture_project_stale(tmp_path)` — creates `.kittify/metadata.yaml` with `spec_kitty.schema_version: 1`.
   - Fixture `fixture_project_too_new(tmp_path)` — creates `.kittify/metadata.yaml` with `spec_kitty.schema_version: 7`. Override `MAX_SUPPORTED_SCHEMA` via monkeypatch to make the test independent of the live constant.
   - Fixture `fixture_project_corrupt(tmp_path)` — writes a 300 KB YAML file (oversized).
   - Fixture `cli_runner` — typer's `CliRunner` configured for the spec-kitty app.
   - Fixture `network_blocker` — patches `httpx.Client.get` to raise `AssertionError("network call!")`. Test asserts call_count == 0 where applicable.
2. `tests/cli_gate/test_safe_commands.py`:
   - Parametrise over the safe-command list (`status`, `dashboard` (read-only mode), `doctor` (diagnostic mode), `--help`, `--version`, `upgrade --dry-run`, `upgrade --cli`, `agent context resolve --json`).
   - For each: invoke against `fixture_project_too_new` (worst-case schema mismatch) and assert exit code 0.
3. `tests/cli_gate/test_unsafe_commands.py`:
   - Parametrise over a representative unsafe-command list (`next`, `implement WP01`, `tasks`, `merge`, `accept`, `review`).
   - Against `fixture_project_stale`: assert exit code 4, message contains "Run: spec-kitty upgrade".
   - Against `fixture_project_too_new`: assert exit code 5, message contains "Upgrade the CLI".
   - Against `fixture_project_corrupt`: assert exit code 6.
4. `tests/cli_gate/test_ci_determinism.py`:
   - `CI=1` env: assert `network_blocker.call_count == 0`, no nag in stderr.
   - No-TTY: same assertions.
   - `--no-nag` flag: same assertions.
   - `SPEC_KITTY_NO_NAG=1`: same assertions.

**Files**: `tests/cli_gate/__init__.py`, `tests/cli_gate/conftest.py`, `tests/cli_gate/test_safe_commands.py`, `tests/cli_gate/test_unsafe_commands.py`, `tests/cli_gate/test_ci_determinism.py`.

**Validation**: `pytest tests/cli_gate/ -v` green.

## Definition of Done

- [ ] Typer callback consults `compat.plan(...)` exactly once per invocation.
- [ ] All safe commands run successfully under `fixture_project_too_new`.
- [ ] All unsafe commands block with correct exit codes against the relevant fixture.
- [ ] Nag suppressed under CI / no-TTY / `--no-nag` / `SPEC_KITTY_NO_NAG=1` / `--json` / `--quiet`.
- [ ] Zero outbound network calls in any CI-mode test.
- [ ] `mypy --strict` clean.
- [ ] `ruff check` clean.
- [ ] No regression in existing CLI tests (run `pytest tests/specify_cli/cli/` and confirm).

## Risks

- The exact location of the typer callback may differ from `cli/helpers.py`; inspect `cli/main.py` and the typer app construction first. Adjust `owned_files` if a different file ends up owning the callback (would require updating `tasks.md` — flag for review).
- `dashboard` / `doctor` mode-aware safety isn't done until WP10. For this WP, treat them as flat-safe (per WP04's seeds). The test file `test_dashboard_modes.py` lives in WP10, not here.
- Performance: NFR-001 (<100 ms when cache fresh). The planner call is in the hot path. Confirm via a quick `time` measurement after wiring.

## Reviewer Guidance

1. **Single chokepoint**: confirm the planner is consulted exactly once per CLI invocation, in the typer callback. No subcommand re-plans.
2. **Stderr discipline**: the nag and block messages go to **stderr**, not stdout. Verify by capturing stdout in `--json` tests and asserting the JSON parses cleanly without any nag prefix.
3. **Cache discipline**: a CI/non-interactive run does NOT update `last_shown_at`. Verify by snapshotting the cache before and after.
4. **Exit codes**: the test for an unsafe command in a stale project asserts `exit_code == 4` (not just "non-zero").
5. **No regressions**: existing CLI integration tests still pass.

## Implementation command

```bash
spec-kitty agent action implement WP08 --agent <name>
```
