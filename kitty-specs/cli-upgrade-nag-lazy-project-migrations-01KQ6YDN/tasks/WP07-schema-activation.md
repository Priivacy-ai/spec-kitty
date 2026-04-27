---
work_package_id: WP07
title: Schema range activation (MIN/MAX) + gate delegation
dependencies:
- WP06
requirement_refs:
- FR-008
- FR-018
- NFR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
history:
- at: '2026-04-27T08:19:12Z'
  actor: planner
  note: WP authored from /spec-kitty.tasks
authoritative_surface: src/specify_cli/migration/
execution_mode: code_change
mission_id: 01KQ6YDNMX2X2AN4WH43R5K2ZS
mission_slug: cli-upgrade-nag-lazy-project-migrations-01KQ6YDN
owned_files:
- src/specify_cli/migration/schema_version.py
- src/specify_cli/migration/gate.py
- tests/specify_cli/migration/test_schema_version_range.py
priority: P1
tags: []
---

# WP07 — Schema range activation (MIN/MAX) + gate delegation

## Branch Strategy

- **Planning base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP07 --agent <name>` after WP06 is merged.

## Objective

Activate the schema gate by splitting `REQUIRED_SCHEMA_VERSION` into `MIN_SUPPORTED_SCHEMA` and `MAX_SUPPORTED_SCHEMA`. Convert `migration/gate.py`'s `check_schema_version` into a thin shim that delegates to `compat.planner.plan(...)`. Update existing schema-version tests to reflect the range semantics. Preserve all existing migration tests (NFR-006).

**Critical activation rule (RP-01)**: `MIN_SUPPORTED_SCHEMA` and `MAX_SUPPORTED_SCHEMA` MUST be set so that no project that exists today is suddenly blocked by this release. Choose `MIN = MAX = current_max_schema_in_registry` so the gate is effectively a no-op for current projects. A future release will bump `MIN` after the corresponding migration ships.

## Context

- Spec: FR-008, FR-009, FR-010, FR-018, NFR-006.
- Plan: §"Engineering Alignment" §"Risks" RP-01; §"Implementation phasing" step 4.
- Research: [`research.md`](../research.md) §R-05 (activation strategy).
- Data model: [`data-model.md`](../data-model.md) §6 (Migration of existing call sites).
- Existing: `src/specify_cli/migration/schema_version.py` declares `REQUIRED_SCHEMA_VERSION: int | None = None` and `SCHEMA_CAPABILITIES`. `src/specify_cli/migration/gate.py` is a typer callback already using `_EXEMPT_COMMANDS = {"upgrade", "init"}`.

## Subtasks

### T027 — Add `MIN_SUPPORTED_SCHEMA` / `MAX_SUPPORTED_SCHEMA` (with deprecated alias)

**Steps**:
1. In `src/specify_cli/migration/schema_version.py`:
   - Read the existing `SCHEMA_CAPABILITIES` to determine the **current max** schema version (today: `3`).
   - Add:
     ```python
     # Inclusive range of project schema versions this CLI build supports.
     # Both endpoints set to the same value during the no-op activation phase
     # (no project is currently blocked by the gate). A later release will bump
     # MIN after the migration that retires schemas <MIN ships.
     MIN_SUPPORTED_SCHEMA: int = 3
     MAX_SUPPORTED_SCHEMA: int = 3
     ```
   - Keep `REQUIRED_SCHEMA_VERSION` as a **deprecated alias** for `MIN_SUPPORTED_SCHEMA`:
     ```python
     # DEPRECATED: kept for backward-compatible imports. New code should read
     # MIN_SUPPORTED_SCHEMA / MAX_SUPPORTED_SCHEMA directly.
     REQUIRED_SCHEMA_VERSION: int | None = MIN_SUPPORTED_SCHEMA
     ```
   - Update the `check_compatibility(project_version, cli_version)` function to compare against the range (treat `cli_version` as `MAX_SUPPORTED_SCHEMA` when called from the new path; preserve old single-int signature for backward compat).

**Files**: `src/specify_cli/migration/schema_version.py`.

**Validation**: existing imports of `REQUIRED_SCHEMA_VERSION` continue to resolve to a non-None integer.

### T028 — `migration/gate.py` becomes a thin shim

**Steps**:
1. Update `check_schema_version(repo_root, invoked_subcommand=None)`:
   - Build an `Invocation`:
     ```python
     from specify_cli.compat import Invocation, plan as compat_plan
     inv = Invocation(
         command_path=(invoked_subcommand,) if invoked_subcommand else (),
         raw_args=tuple(sys.argv[1:]),
         is_help=False, is_version=False,
         flag_no_nag="--no-nag" in sys.argv,
         env_ci=bool(os.environ.get("CI")),
         stdout_is_tty=sys.stdout.isatty(),
     )
     ```
   - Call `result = compat_plan(inv)`.
   - If `result.decision in {Decision.BLOCK_PROJECT_MIGRATION, Decision.BLOCK_CLI_UPGRADE, Decision.BLOCK_PROJECT_CORRUPT}`:
     - `typer.echo(result.rendered_human, err=True)`
     - `raise SystemExit(int(result.exit_code))`
   - Else: return normally (the typer callback continues).
2. Keep `_EXEMPT_COMMANDS` definition for backward compatibility but ensure the planner's safety registry already covers these (WP04 seeds `("upgrade",)` and `("init",)` as safe).
3. Behavior is **observably identical** to today for a fresh install (`REQUIRED_SCHEMA_VERSION` was None and gate was a no-op; now `MIN=MAX=3` and gate is a no-op for projects at schema 3).

**Files**: `src/specify_cli/migration/gate.py`.

**Validation**: existing CLI tests that previously passed against the no-op gate must still pass.

### T029 — Schema-version tests updated; existing migration tests preserved

**Steps**:
1. Create `tests/specify_cli/migration/test_schema_version_range.py`:
   - Test that `MIN_SUPPORTED_SCHEMA <= MAX_SUPPORTED_SCHEMA`.
   - Test that `REQUIRED_SCHEMA_VERSION == MIN_SUPPORTED_SCHEMA`.
   - Test `check_compatibility(project_version=3, cli_version=3)` returns `COMPATIBLE`.
   - Test `check_compatibility(project_version=2, cli_version=3)` returns `OUTDATED`.
   - Test `check_compatibility(project_version=4, cli_version=3)` returns `CLI_OUTDATED`.
   - Test `check_compatibility(project_version=None, cli_version=3)` returns `UNMIGRATED`.
2. Run the **existing** test suite (`pytest tests/specify_cli/upgrade/ tests/cross_cutting/versioning/`) and confirm zero regressions. If any existing test asserts `REQUIRED_SCHEMA_VERSION is None`, update it to assert it equals `MIN_SUPPORTED_SCHEMA` instead — but preserve the *intent* of the test.
3. Add a CHANGELOG-style note in the WP review (not in code) describing the activation: "MIN_SUPPORTED_SCHEMA = MAX_SUPPORTED_SCHEMA = 3 — no behavior change for existing projects."

**Files**: `tests/specify_cli/migration/test_schema_version_range.py` (new).

**Validation**: full migration test suite green.

## Definition of Done

- [ ] `MIN_SUPPORTED_SCHEMA` and `MAX_SUPPORTED_SCHEMA` exist and equal the current max schema in `SCHEMA_CAPABILITIES`.
- [ ] `REQUIRED_SCHEMA_VERSION` is now `int` (not `None`), aliased to `MIN_SUPPORTED_SCHEMA`.
- [ ] `check_schema_version` delegates to `compat.plan()`.
- [ ] No existing project is blocked by this release (verified via test against fixture projects with `schema_version=3`).
- [ ] `tests/specify_cli/upgrade/` and `tests/cross_cutting/versioning/` suites still pass.
- [ ] New `test_schema_version_range.py` covers the range semantics.
- [ ] `mypy --strict` clean.
- [ ] `ruff check` clean.

## Risks

- **RP-01**: this is the WP that triggers RP-01 if mishandled. The mitigation is `MIN = MAX = current_max`. Reviewer must verify this number is correct against `SCHEMA_CAPABILITIES`.
- Existing tests may rely on `REQUIRED_SCHEMA_VERSION is None` as a "gate disabled" signal. Convert these to use a planner-level mock or update the assertion to the new range semantics.
- Importing from `specify_cli.compat` inside `migration.gate` may introduce a circular import if `compat` imports anything from `migration`. The `compat._adapters.gate` adapter (WP05) is the safe path; if circulars appear, push the import inside the function (deferred import).

## Reviewer Guidance

1. **No-op verification**: against a fixture project with `spec_kitty.schema_version: 3`, every CLI command runs identically before and after this WP.
2. **Range correctness**: `MIN ≤ MAX`; `REQUIRED_SCHEMA_VERSION` resolves to a non-None int.
3. **Migration test preservation**: NFR-006 holds. The existing test file count is unchanged; failing tests are updates that preserve intent.
4. **Delegation**: `migration/gate.py` is now under 30 lines of substantive code; the heavy lifting is in `compat.planner`.

## Implementation command

```bash
spec-kitty agent action implement WP07 --agent <name>
```
