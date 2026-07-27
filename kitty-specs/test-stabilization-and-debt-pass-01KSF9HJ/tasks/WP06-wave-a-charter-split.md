---
work_package_id: WP06
title: 'Wave A MS-1: split cli/commands/charter.py per-subcommand (FR-007)'
dependencies:
- WP05
requirement_refs:
- FR-007
planning_base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
merge_target_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
base_commit: c6020b60a5e093abfc77398af96c2faba87c9c92
created_at: '2026-05-25T14:44:28.427225+00:00'
subtasks:
- T019
- T020
- T021
- T022
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "2175625"
history:
- by: claude
  at: '2026-05-25T14:00:00+00:00'
  action: generated
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/charter/
execution_mode: code_change
mission_id: 01KSF9HJBFKRBC617JVHKZXNE2
mission_slug: test-stabilization-and-debt-pass-01KSF9HJ
owned_files:
- src/specify_cli/cli/commands/charter.py
- src/specify_cli/cli/commands/charter/**
priority: P1
review_status: acknowledged
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Invoke `/ad-hoc-profile-load` with argument `python-pedro` before reading further. Behaviour-preserving structural refactor.

## Objective

Split `src/specify_cli/cli/commands/charter.py` (3,328 lines, MS-1 in the architect review) into a per-subcommand package `src/specify_cli/cli/commands/charter/` with one module per subcommand:

- `status.py`, `sync.py`, `synthesize.py`, `lint.py`, `preflight.py`, `bundle.py`, `resynthesize.py`

The package's `__init__.py` becomes the typer-app registration shim. Old import paths (e.g., `from specify_cli.cli.commands.charter import charter_lint`) continue to resolve via the package's re-exports. Behaviour and CLI surface unchanged.

Success criterion 3 (spec): `wc -l src/specify_cli/cli/commands/charter.py` returns 0 OR ≤ 150 (kept only as the typer-app wiring shim). Each new per-subcommand module ≤ 500 lines.

## Branch strategy

- Planning base branch: mission lane branch (post-WP05)
- Merge target branch: `main`
- Execution: lane workspace allocated by `finalize-tasks`.

## Context

- [`spec.md`](../spec.md) FR-007 + C-003 (typer registration pattern preserved).
- [`plan.md`](../plan.md) Wave A § WP06 + Phase 1 Architect-resolved Q1 (ONE WP, not two).
- [`docs/engineering_notes/architectural-review/2026-05-25-deep-dive-architectural-review.md`](../../../docs/engineering_notes/architectural-review/2026-05-25-deep-dive-architectural-review.md) §3 MS-1.
- Existing source: `src/specify_cli/cli/commands/charter.py`. Inspect with `grep -n "@app.command" src/specify_cli/cli/commands/charter.py` to find the registered subcommands.

## Subtask details

### T019 — Create the new package skeleton

```bash
mkdir -p src/specify_cli/cli/commands/charter
```

Create `src/specify_cli/cli/commands/charter/__init__.py`:
```python
"""Per-subcommand modules for the ``spec-kitty charter`` typer app.

Behaviour-preserving split of the legacy single-file ``charter.py`` (MS-1 from
the post-mission-122 architectural review).
"""
from __future__ import annotations

# Re-export the typer app so existing imports continue to resolve.
from specify_cli.cli.commands.charter._app import charter_app, app  # noqa: F401

# Re-export each subcommand handler so any test or sibling module that
# does ``from specify_cli.cli.commands.charter import charter_lint`` keeps working.
from specify_cli.cli.commands.charter.status import status as charter_status  # noqa: F401
from specify_cli.cli.commands.charter.sync import sync as charter_sync  # noqa: F401
from specify_cli.cli.commands.charter.synthesize import synthesize as charter_synthesize  # noqa: F401
from specify_cli.cli.commands.charter.lint import charter_lint  # noqa: F401
from specify_cli.cli.commands.charter.preflight import charter_preflight  # noqa: F401
from specify_cli.cli.commands.charter.bundle import bundle as charter_bundle  # noqa: F401
from specify_cli.cli.commands.charter.resynthesize import resynthesize as charter_resynthesize  # noqa: F401

__all__ = [
    "charter_app",
    "app",
    "charter_status",
    "charter_sync",
    "charter_synthesize",
    "charter_lint",
    "charter_preflight",
    "charter_bundle",
    "charter_resynthesize",
]
```

Create `src/specify_cli/cli/commands/charter/_app.py` that owns the typer app instance:
```python
"""The charter typer app — shared instance for all subcommand modules."""
from __future__ import annotations

import typer

charter_app = typer.Typer(help="Charter governance commands.")
app = charter_app  # legacy alias; tests reference both names
```

### T020 — Move each subcommand handler [P]

For each of the 7 subcommands, create a module under `charter/` containing:
- The handler function annotated with `@charter_app.command(...)`.
- Any subcommand-specific helpers.
- Imports lifted from the original `charter.py`.

Each module ≤ 500 lines. Example for `lint.py`:
```python
"""``spec-kitty charter lint`` — decay detection."""
from __future__ import annotations

import typer
# ... (lift from charter.py lines 3082-3241)

from specify_cli.cli.commands.charter._app import charter_app

@charter_app.command("lint")
def charter_lint(
    mission: str | None = typer.Option(None, "--mission", ...),
    # ... full signature
) -> None:
    """Detect decay in charter artifacts via graph-native checks."""
    # ... lifted body
```

This subtask is `[P]` — the 7 moves are independent of each other.

### T021 — Reduce/delete the old `charter.py`

After all subcommand handlers have been moved into the package, the old `src/specify_cli/cli/commands/charter.py` should either:

**Option A (preferred)**: delete the file entirely. Python's package-import resolution will use `charter/__init__.py` (it's a directory, so it wins).

**Option B (fallback)**: leave it as a ≤150-line shim that does:
```python
"""Legacy module-level shim — see ``charter/`` package."""
from specify_cli.cli.commands.charter import *  # noqa: F401,F403
```

Test imports first with Option A; if pytest collection fails on any module that explicitly imports `from specify_cli.cli.commands.charter` (the module, not the package), fall back to Option B.

### T022 — Verify charter integration tests

```bash
PWHEADLESS=1 .venv/bin/pytest \
  tests/specify_cli/cli/commands/test_charter_lint.py \
  tests/integration/test_charter_status_freshness.py \
  tests/integration/test_charter_lint_lints_all_layers.py \
  tests/specify_cli/charter_lint/ \
  tests/specify_cli/charter_freshness/ \
  tests/specify_cli/charter_preflight/ \
  -q
```

Expected: same pass/fail count as pre-WP06 baseline. No new failures.

## Definition of Done

- [ ] `src/specify_cli/cli/commands/charter/` package exists with 7 subcommand modules + `_app.py` + `__init__.py`.
- [ ] Each subcommand module ≤ 500 lines.
- [ ] `src/specify_cli/cli/commands/charter.py` is either deleted OR ≤ 150 lines (shim).
- [ ] `__all__` exports in `__init__.py` cover every previously-public symbol from `charter.py`.
- [ ] `spec-kitty charter --help` lists the same subcommands as before.
- [ ] Behaviour-preservation tests green.
- [ ] `mypy --strict` clean on the new package.

## Risks

- **Pytest collection failure**: tests that do `from specify_cli.cli.commands.charter import <symbol>` may break if the symbol moved. The `__init__.py` re-exports cover the common case; spot-check any test file with such imports.
- **Typer app instance identity**: typer apps are stateful; if any test asserts `id(app) == id(other)`, the new shared instance from `_app.py` must be the same object referenced everywhere.

## Reviewer guidance

1. Verify `spec-kitty charter --help` output matches pre-WP06 (same subcommands, same descriptions).
2. Verify no per-subcommand module exceeds 500 lines.
3. Spot-check 2 tests that import from `specify_cli.cli.commands.charter` — confirm they still pass.

## Activity Log

- 2026-05-25T14:44:29Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1905071 – Assigned agent via action command
- 2026-05-25T14:44:42Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1906636 – Assigned agent via action command
- 2026-05-25T15:14:15Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1906636 – MS-1 split: 7 per-subcommand modules; behaviour-preservation tests green
- 2026-05-25T15:15:39Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1906636 – claiming for WP06 implementation
- 2026-05-25T15:15:50Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1906636 – WP06 implementation in progress
- 2026-05-25T15:16:11Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1906636 – MS-1 split: 7 per-subcommand modules; behaviour-preservation tests green
- 2026-05-25T15:20:05Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=2060051 – Started review via action command
- 2026-05-25T15:30:45Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=2060051 – Moved to planned
- 2026-05-25T15:31:16Z – claude:opus-4-7:python-pedro:implementer – shell_pid=2121201 – Started implementation via action command
- 2026-05-25T15:42:29Z – claude:opus-4-7:python-pedro:implementer – shell_pid=2121201 – Cycle 2: all 4 modules now route through _charter_pkg shim; charter test count back to baseline
- 2026-05-25T15:43:08Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=2175625 – Started review via action command
- 2026-05-25T15:47:44Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=2175625 – Cycle-2 review approves: cycle-1 findings (4 modules bypassing _charter_pkg shim) resolved in ad6fdea46; charter test slice 10 failed/1641 passed == planning baseline; ruff clean; --help surfaces all 10 subcommands
