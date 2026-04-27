---
work_package_id: WP03
title: FR-001 .python-version + restore strict mypy on mission_step_contracts
dependencies: []
requirement_refs:
- FR-001
- NFR-001
planning_base_branch: release/3.2.0a5-tranche-1
merge_target_branch: release/3.2.0a5-tranche-1
branch_strategy: Planning artifacts for this feature were generated on release/3.2.0a5-tranche-1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into release/3.2.0a5-tranche-1 unless the human explicitly redirects the landing branch.
created_at: '2026-04-27T18:00:45+00:00'
subtasks:
- T010
- T011
- T012
- T013
- T014
agent: "claude:sonnet:implementer-ivan:implementer"
shell_pid: "70758"
history:
- at: '2026-04-27T18:00:45Z'
  actor: claude
  note: WP scaffolded by /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/mission_step_contracts/
execution_mode: code_change
mission_id: 01KQ7YXHA5AMZHJT3HQ8XPTZ6B
mission_slug: release-3-2-0a5-tranche-1-01KQ7YXH
owned_files:
- .python-version
- src/specify_cli/mission_step_contracts/**
- tests/cross_cutting/test_mypy_strict_mission_step_contracts.py
role: implementer
tags:
- type-safety
- python-version
---

# WP03 — FR-001 `.python-version` + restore strict mypy on `mission_step_contracts`

## ⚡ Do This First: Load Agent Profile

Before reading further or making any edits, invoke the `/ad-hoc-profile-load` skill with these arguments:

- **Profile**: `implementer-ivan`
- **Role**: `implementer`

This loads your identity, governance scope, and bug-fixing-checklist tactic. Loosening `.python-version` is a one-byte change but the mypy --strict restoration may surface latent type errors — the bug-fixing tactic guides you through reproduction-first fixes.

## Objective

Two coordinated fixes in one WP:

1. **`.python-version` loosening**: Replace the current hard pin (`3.13`) with `3.11`, matching `pyproject.toml::requires-python = ">=3.11"`. This stops local agents on Python 3.14 (or any other 3.11+ interpreter) from being implicitly blocked by a stricter floor than packaging declares.
2. **Restore `mypy --strict` cleanliness on `src/specify_cli/mission_step_contracts/executor.py`** and add an in-suite assertion so future drift is caught at CI time, not at developer-machine time.

## Context

- Decision Moment `01KQ7ZSQKT9DVH7B4GGXWS8DTW` resolved by user: floor at `3.11`. See [research.md R1](../research.md#r1--python-version-shape-fr-001--805).
- Mission-step contracts live under `src/specify_cli/mission_step_contracts/`; `executor.py` is the central typed surface that mission steps must satisfy.
- `start-here.md` "Verification Targets" already prescribes
  `uv run --extra lint mypy --strict src/specify_cli/mission_step_contracts/executor.py` as the canonical command to run.

## Branch Strategy

- **Planning base branch**: `release/3.2.0a5-tranche-1`
- **Final merge target**: `release/3.2.0a5-tranche-1`
- This WP has no dependencies; its lane is rebased directly onto `release/3.2.0a5-tranche-1`.
- Execution worktrees are allocated per computed lane from `lanes.json` (created by `finalize-tasks`).

## Subtasks

### T010 — Replace `.python-version` contents with `3.11`

**Purpose**: Align `.python-version` with `pyproject.toml::requires-python = ">=3.11"`.

**Files**:
- `.python-version` (one-line file)

**Steps**:

1. Open `.python-version`. It currently contains a single line: `3.13`.
2. Replace with: `3.11`.
3. Ensure no trailing whitespace, exactly one newline at EOF.

**Validation**:
- [ ] `cat .python-version` prints exactly `3.11`.
- [ ] `wc -l .python-version` prints `1`.

**Edge Cases / Risks**:
- Some IDEs auto-write a different format (e.g. `pythoneval pyenv` style). The simple `3.11` content is what `uv` expects.

### T011 — Run `mypy --strict` on `mission_step_contracts/executor.py`; triage any errors

**Purpose**: Restore the type-strictness invariant on the executor.

**Files**:
- Whatever inside `src/specify_cli/mission_step_contracts/` mypy flags (read-mostly; minimal patches expected).

**Steps**:

1. Run `uv run --extra lint mypy --strict src/specify_cli/mission_step_contracts/executor.py`.
2. If exit code is 0, T011 is done — mypy --strict already clean.
3. If errors exist:
   a. Read each error carefully. Most likely categories: `Any` types from third-party imports, missing return-type annotations, missing parameter annotations, untyped `**kwargs`, narrowing failures around `Optional` / `Union`.
   b. Apply the smallest fix per error (`-> None`, explicit type alias, `cast()`, `assert isinstance(...)` narrowing). Do NOT add `# type: ignore` unless you've documented WHY the underlying surface can't be typed (and link to an issue if such ignore is permanent).
   c. After each batch of fixes, re-run mypy and address the next error.
4. Repeat until exit code is 0.

**Validation**:
- [ ] `uv run --extra lint mypy --strict src/specify_cli/mission_step_contracts/executor.py` exits 0.

**Edge Cases / Risks**:
- If mypy fails because of a sibling module imported by `executor.py`, fix only the surface needed to make `executor.py` strict-clean; do NOT recursively strict-up the entire CLI. NFR-001 scope is bounded to the executor module per `start-here.md`.

### T012 — Add `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py`

**Purpose**: Lock the type-strictness invariant inside the pytest suite so a future regression is caught at CI time.

**Files**:
- `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py` (new)

**Steps**:

1. Create the new test file:

   ```python
   from __future__ import annotations

   import subprocess
   import sys
   from pathlib import Path

   import pytest


   REPO_ROOT = Path(__file__).resolve().parents[2]
   TARGET = "src/specify_cli/mission_step_contracts/executor.py"


   @pytest.mark.slow  # mypy invocation is comparatively expensive
   def test_mission_step_contracts_executor_is_mypy_strict_clean() -> None:
       result = subprocess.run(
           [sys.executable, "-m", "mypy", "--strict", TARGET],
           cwd=REPO_ROOT,
           check=False,
           capture_output=True,
           text=True,
       )
       assert result.returncode == 0, (
           "mypy --strict failed on mission_step_contracts/executor.py.\n"
           "stdout:\n"
           + result.stdout
           + "\nstderr:\n"
           + result.stderr
       )
   ```

2. If `tests/cross_cutting/` already uses a different pattern for invoking mypy (check siblings), follow that pattern instead.

**Validation**:
- [ ] `pytest tests/cross_cutting/test_mypy_strict_mission_step_contracts.py -q` exits 0 after T011.
- [ ] Same test FAILS if you temporarily sabotage `executor.py` with a typing error (verify locally).

**Edge Cases / Risks**:
- The test invokes mypy via `sys.executable -m mypy`, which requires the `lint` extra to be installed in the test env. If `tests/cross_cutting/` has a fixture that ensures the extra is available, reuse it. Otherwise document the env requirement at the top of the file.

### T013 — Re-run `tests/cross_cutting/` and `tests/missions/` to confirm no regressions

**Purpose**: Catch any indirect breakage from the python-version change.

**Steps**:

1. Run `PWHEADLESS=1 uv run --extra test python -m pytest tests/cross_cutting/ tests/missions/ -q`.
2. If anything fails, triage. Typical failure modes:
   - Code that uses 3.12+-only syntax (e.g. PEP 695 `type` aliases, `match` improvements). These are bugs against `requires-python = ">=3.11"` and should be fixed in-place to be 3.11-compatible.
   - Tests that hardcode the python-version file content. Update the test fixture, not the version.

**Validation**:
- [ ] Both test directories exit 0.

### T014 — Run `ruff check` on touched surfaces

**Purpose**: No lint regressions.

**Steps**:

1. Run `uv run --extra lint ruff check .python-version pyproject.toml src/specify_cli/mission_step_contracts/`.
2. Fix anything ruff flags. (`ruff check` lints `.python-version` only via the metadata check; the actual lint surface is the Python files inside `mission_step_contracts/`.)

**Validation**:
- [ ] Command exits 0.

## Test Strategy

- T012 is the standing assertion for NFR-001. Once it lands, future regressions in `mission_step_contracts/executor.py` typing fail at pytest time.
- T013 is a safety net to catch python-version-induced fallout in adjacent test surfaces.

## Definition of Done

- [ ] `.python-version` contains exactly `3.11`.
- [ ] `uv run --extra lint mypy --strict src/specify_cli/mission_step_contracts/executor.py` exits 0.
- [ ] `pytest tests/cross_cutting/test_mypy_strict_mission_step_contracts.py -q` exits 0.
- [ ] `pytest tests/cross_cutting/ tests/missions/ -q` exits 0.
- [ ] `ruff check .python-version pyproject.toml src/specify_cli/mission_step_contracts/` exits 0.
- [ ] PR description includes a one-line CHANGELOG entry candidate for **WP02** to consolidate. Suggested: `Loosen \`.python-version\` from a hard \`3.13\` pin to \`3.11\` (the floor declared by \`pyproject.toml\`) and restore \`mypy --strict\` cleanliness on \`mission_step_contracts/executor.py\` (#805).`

## Risks

- **R1**: T011 may surface non-trivial type errors latent in `executor.py`. Budget half the WP time for type-fix iteration. If the errors cascade beyond the executor module, scope-creep — surface the issue and stop at the executor; deeper strict-up is a follow-on tranche.
- **R2**: A test in `tests/cross_cutting/` may hardcode the old `3.13` python-version string. Find with `grep -rn "3.13" tests/cross_cutting/ tests/missions/` and update fixture content (NOT assertion logic).

## Reviewer Guidance

- Verify `.python-version` is exactly two characters of content + newline (`3.11\n`).
- Verify any new `# type: ignore` comments are accompanied by an inline reason and (ideally) an issue link.
- Verify the new pytest test invokes mypy on `mission_step_contracts/executor.py` exactly and asserts on `returncode == 0`.

## Implementation command

```bash
spec-kitty agent action implement WP03 --agent claude
```

## Activity Log

- 2026-04-27T19:47:51Z – claude:sonnet:implementer-ivan:implementer – shell_pid=70758 – Started implementation via action command
