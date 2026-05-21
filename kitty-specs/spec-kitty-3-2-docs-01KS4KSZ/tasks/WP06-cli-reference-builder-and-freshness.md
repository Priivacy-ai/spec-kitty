---
work_package_id: WP06
title: CLI reference builder + freshness checker + tests
dependencies:
- WP05
requirement_refs:
- FR-007
- FR-008
- NFR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
agent: "claude:opus-4-7:python-pedro:implementer"
shell_pid: "41943"
history:
- actor: planner
  at: '2026-05-21T06:52:04Z'
  action: wp_authored
  notes: Initial authorship by tasks phase.
agent_profile: python-pedro
authoritative_surface: scripts/docs/
execution_mode: code_change
model: claude-opus-4-7
owned_files:
- scripts/docs/_typer_walker.py
- scripts/docs/build_cli_reference.py
- scripts/docs/check_cli_reference_freshness.py
- tests/docs/test_build_cli_reference.py
- tests/docs/test_check_cli_reference_freshness.py
- tests/docs/fixtures/sample_cli_reference.md
- tests/docs/fixtures/sample_cli_reference_missing.md
- tests/docs/fixtures/sample_cli_reference_extra.md
- tests/docs/fixtures/sample_cli_reference_no_saas.md
- tests/architectural/test_docs_cli_reference_parity.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

## Objective

Implement the shared Typer walker, the CLI reference builder, the freshness checker, pytest coverage, and the architectural parity test that asserts every non-hidden command path appears in `docs/reference/cli-commands.md`.

## Context

- Contracts:
  - [`contracts/build_cli_reference.md`](../contracts/build_cli_reference.md)
  - [`contracts/check_cli_reference_freshness.md`](../contracts/check_cli_reference_freshness.md)
- Methodology: [`docs/development/3-2-cli-reference-methodology.md`](../../../docs/development/3-2-cli-reference-methodology.md) (WP05).
- Reference walker pattern: `tests/architectural/test_safety_registry_completeness.py` (prefers `group.name`, falls back to `group.typer_instance.info.name`).
- Live CLI evidence: `cli-audit-3-2.md` (192 visible / 5 hidden / 2 deprecated).
- Charter: no new pip deps; mypy `--strict`; ≥ 90% coverage; integration tests for CLI surfaces.
- **CRITICAL**: `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and `SPEC_KITTY_NO_UPGRADE_CHECK=1` MUST be set in `os.environ` at the **top** of each script before any `from specify_cli ...` import. The scripts must enforce this themselves.

## Subtasks

### T016 — Implement `scripts/docs/_typer_walker.py`

- Single function `walk(app) -> list[CommandPathEntry]`.
- Walks both `registered_commands` and `registered_groups` recursively.
- For groups, prefers `group.name`, falls back to `group.typer_instance.info.name`.
- Detects hidden via Typer's `hidden=True`.
- Detects deprecated via help-text prefix `"Deprecated"` and/or Typer's `deprecated=True`.
- Detects `requires_saas_sync` by inspecting whether the `tracker` or `issue-search` subtree is present (depends on env flag at import time).
- Read-only: never assigns to any attribute on the Typer app or its descendants.
- Returns deterministic ordering (depth-first, sorted by path tuple).

### T017 — Implement `scripts/docs/build_cli_reference.py`

Implement per contract. Required behavior:

- Set `os.environ["SPEC_KITTY_ENABLE_SAAS_SYNC"] = "1"` and `os.environ["SPEC_KITTY_NO_UPGRADE_CHECK"] = "1"` at module top before any `from specify_cli...` import.
- Walk via `_typer_walker.walk(app)`.
- For each visible path, subprocess `uv run spec-kitty <path> --help` and capture stdout.
- Normalize Rich output (strip ANSI; collapse blank-line runs; preserve code blocks).
- Group output by top-level command/group; emit a sectioned markdown document.
- Honour `--mode {generated, hybrid, hand}`:
  - `hybrid` (default): write generated content between `<!-- BEGIN GENERATED -->` and `<!-- END GENERATED -->` markers; preserve all prose outside the markers across runs.
  - `generated`: replace entire file; no preserved prose.
  - `hand`: only write the deprecation/internal classification table.
- Refuse to write if the target file has uncommitted changes (unless `--force`).
- Write `docs/reference/cli-commands.md` and `docs/reference/agent-subcommands.md`.
- Optional `--include-hidden` appendix.
- Optional `--dry-run` prints the diff to stdout.
- Exit codes: 0/1/2/3 per contract.

### T018 — Implement `scripts/docs/check_cli_reference_freshness.py`

Implement per contract. Required rules:

- `REF-MISSING`, `REF-EXTRA`, `REF-DEPRECATED-UNCLASSIFIED`, `REF-INTERNAL-LEAK`, `REF-SAAS-SYNC-OFF`, `HELP-DRIFT` (warning unless `--strict-mode`), `REF-HIDDEN-LEAK`.
- Same env-flag enforcement as builder.
- Optional `--report PATH` for JSON output.
- Optional `--ci` for plain-text output.
- Exit codes: 0/1/2/3 per contract.

### T019 — Author tests

- Unit tests for `_typer_walker.walk()` against a synthetic Typer fixture app embedded in `tests/docs/conftest.py`.
- Unit tests for normalization, mode handling, and rule detection.
- Integration smoke test for the **real** `specify_cli.app`:
  - Set env flags before import.
  - Walk via `_typer_walker.walk(app)`.
  - Assert visible count is between 173 and 211 (192 ± 10%, allowing for natural CLI growth/shrinkage).
  - Assert deprecated count ≥ 1 (currently 2 per audit).
- Fixture-driven tests for missing / extra / no-saas cases.
- Coverage ≥ 90% on the new modules.

### T020 — Architectural parity test

Implement `tests/architectural/test_docs_cli_reference_parity.py`:

- Mirrors `tests/architectural/test_safety_registry_completeness.py` in shape.
- Imports `specify_cli.app` with env flags set.
- Walks via `_typer_walker.walk(app)`.
- Loads `docs/reference/cli-commands.md` and `docs/reference/agent-subcommands.md`.
- Asserts the set of non-hidden command paths is exactly the set named in the two reference files (with deprecated/internal paths allowed only when classified).
- Skips if `docs/reference/cli-commands.md` does not yet exist (e.g., on a branch where WP07 hasn't run); record this with `pytest.skip(...)` for an explicit reason.

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Lane: `B`. Reuses the lane-B worktree.

## Test Strategy

- pytest must pass: `pytest tests/docs/test_build_cli_reference.py tests/docs/test_check_cli_reference_freshness.py tests/architectural/test_docs_cli_reference_parity.py -v`.
- Coverage report shows ≥ 90% on `scripts/docs/_typer_walker.py`, `scripts/docs/build_cli_reference.py`, `scripts/docs/check_cli_reference_freshness.py`.
- mypy `--strict` clean on every new file.
- Integration smoke test runs in CI with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.

## Definition of Done

- [ ] Three new scripts under `scripts/docs/` exist and mypy `--strict` clean.
- [ ] Two test files under `tests/docs/` exist and pass.
- [ ] One architectural test under `tests/architectural/` exists and passes (or skips with explicit reason when reference files absent).
- [ ] Coverage ≥ 90% on new modules.
- [ ] No files outside `owned_files` modified.
- [ ] No Typer code touched; reviewer confirms via `git diff --stat`.

## Risks

- **Subprocess `--help` capture variance across platforms** — Mitigation: normalize output deterministically (strip ANSI; canonicalize whitespace); run in CI on Linux to baseline.
- **Typer app surface drift between planning and implement** — Mitigation: ±10% tolerance band on the visible count; explicit log when count drifts.
- **Hidden path asymmetry (`agent profile` hidden, `agent profile list` visible)** — Mitigation: walker records both; reference allows the child to appear under the visible "Profile commands" surface while the parent stays hidden.

## Reviewer Guidance

- Confirm env-flag enforcement at module top of each script.
- Confirm no mutation of any Typer command object.
- Confirm exit-code matrix covered by tests.
- Run the integration smoke test locally to confirm visible count is within tolerance.

## Implement command

```bash
spec-kitty agent action implement WP06 --agent claude
```

## Activity Log

- 2026-05-21T07:45:58Z – claude:opus-4-7:python-pedro:implementer – shell_pid=41943 – Started implementation via action command
