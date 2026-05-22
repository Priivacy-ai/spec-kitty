---
work_package_id: WP02
title: Suppression matrix + caching tests
dependencies:
- WP01
requirement_refs:
- FR-009
- FR-011
- FR-012
- NFR-002
- NFR-004
planning_base_branch: kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV
merge_target_branch: kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV
base_commit: ad5935263513fdf2da6b9eff1a62a8d1449aaf90
created_at: '2026-05-22T10:42:28.677085+00:00'
subtasks:
- T011
- T012
- T013
shell_pid: "65358"
history: []
agent_profile: python-pedro
authoritative_surface: tests/readiness/
execution_mode: code_change
owned_files:
- tests/readiness/__init__.py
- tests/readiness/test_coordinator_suppression_matrix.py
- tests/readiness/test_coordinator_caching.py
role: implementer
tags: []
agent: "claude:opus:python-pedro:implementer"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

Then return here and read on.

---

## Objective

Prove the suppression contract (FR-011) and the once-per-invocation caching invariant (FR-009, part of FR-012) under automated test. Write two new test files under `tests/readiness/`:

1. `test_coordinator_suppression_matrix.py` — 7-row parameterized matrix + 1 hosted-mode-enabled row. Asserts `output_policy`, `enabled`, `ran`, and the no-Teamspace-leakage invariant.
2. `test_coordinator_caching.py` — 5 cases (A–E) covering hosted-on cache, hosted-off cache, `get_readiness` identity, fresh-`ctx` default, non-dict `ctx.obj` default.

After this WP: `pytest -q tests/readiness/test_coordinator_suppression_matrix.py tests/readiness/test_coordinator_caching.py` is green.

---

## Context

Read first:
1. `kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/spec.md` — FR-011 / FR-012 / FR-009 / NFR-002.
2. `kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/plan.md` — Test Strategy section.
3. `tests/cli_gate/test_ci_determinism.py` — the precedent for direct-callback / direct-function invocation in tests.
4. `src/specify_cli/readiness/coordinator.py` (post-WP01) — the API you're testing.

Existing test conventions in this repo:
- pytest with `monkeypatch` for env/`sys.argv`/`sys.stdout.isatty` manipulation.
- `capsys` / `capfd` for stdout/stderr capture.
- Direct construction of `typer.Context` via the existing fixture pattern from `tests/cli_gate/test_ci_determinism.py` (look at how that file constructs `ctx`).

---

## Branch Strategy

- **Planning/base branch**: `main`
- **Mission branch**: `kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV`
- **Merge target for the PR**: `main`
- **Worktree for this WP**: `lane-a`.
- **Implement command**: `spec-kitty agent action implement WP02 --agent claude`

---

## Markdown formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``.
Use language identifiers in code blocks: ```` ```python ```` , ```` ```bash ```` .

---

## Subtasks

### Subtask T011 — Create `tests/readiness/__init__.py`

**Purpose**: Establish `tests/readiness/` as a Python test package. Other test directories under `tests/` follow the same convention.

**File**: `tests/readiness/__init__.py` (new)

**Content**:

```python
"""Tests for the central CLI startup readiness coordinator.

Mission: cli-startup-readiness-coordinator-skeleton-01KS7JRV
Issue: https://github.com/Priivacy-ai/spec-kitty/issues/1093
"""
```

**Validation**: `pytest -q --collect-only tests/readiness/` returns without import errors.

---

### Subtask T012 — Write `tests/readiness/test_coordinator_suppression_matrix.py`

**Purpose**: One parameterized test that exercises every row of the suppression matrix and asserts the no-Teamspace-leakage invariant. Plus an additional hosted-mode-enabled row.

**File**: `tests/readiness/test_coordinator_suppression_matrix.py` (new)

**Content**:

```python
"""Suppression matrix tests for the readiness coordinator.

Asserts FR-011 (no Teamspace leakage when hosted mode is disabled, across the
full suppression matrix) and FR-004 (output policy derivation).

Mission: cli-startup-readiness-coordinator-skeleton-01KS7JRV
"""

from __future__ import annotations

import io
import sys
from dataclasses import dataclass
from typing import Any

import pytest
import typer
from click.testing import CliRunner  # noqa: F401 — kept available for follow-up extension

from specify_cli.readiness import (
    AuthStatus,
    OutputPolicy,
    ReadinessResult,
    evaluate_readiness,
)


@dataclass(frozen=True)
class MatrixRow:
    name: str
    argv: list[str]
    ci_env: bool
    isatty: bool
    hosted_enabled: bool
    expected_policy: OutputPolicy
    expected_enabled: bool


# 7-row suppression matrix (hosted mode OFF) + 1 hosted-mode-enabled row.
MATRIX_ROWS: list[MatrixRow] = [
    MatrixRow(
        name="help",
        argv=["--help"],
        ci_env=False,
        isatty=True,
        hosted_enabled=False,
        expected_policy=OutputPolicy.NON_INTERACTIVE,
        expected_enabled=False,
    ),
    MatrixRow(
        name="version",
        argv=["--version"],
        ci_env=False,
        isatty=True,
        hosted_enabled=False,
        expected_policy=OutputPolicy.NON_INTERACTIVE,
        expected_enabled=False,
    ),
    MatrixRow(
        name="plain_invocation",
        argv=[],
        ci_env=False,
        isatty=True,
        hosted_enabled=False,
        expected_policy=OutputPolicy.INTERACTIVE,
        expected_enabled=False,
    ),
    MatrixRow(
        name="json",
        argv=["status", "--json"],
        ci_env=False,
        isatty=True,
        hosted_enabled=False,
        expected_policy=OutputPolicy.MACHINE_OUTPUT,
        expected_enabled=False,
    ),
    MatrixRow(
        name="quiet",
        argv=["status", "--quiet"],
        ci_env=False,
        isatty=True,
        hosted_enabled=False,
        expected_policy=OutputPolicy.MACHINE_OUTPUT,
        expected_enabled=False,
    ),
    MatrixRow(
        name="ci",
        argv=["status"],
        ci_env=True,
        isatty=True,
        hosted_enabled=False,
        expected_policy=OutputPolicy.NON_INTERACTIVE,
        expected_enabled=False,
    ),
    MatrixRow(
        name="non_tty",
        argv=["status"],
        ci_env=False,
        isatty=False,
        hosted_enabled=False,
        expected_policy=OutputPolicy.NON_INTERACTIVE,
        expected_enabled=False,
    ),
    # Hosted-mode-enabled row: still no Teamspace leakage because the auth probe
    # is not exercised in this mission.
    MatrixRow(
        name="hosted_enabled_interactive",
        argv=["status"],
        ci_env=False,
        isatty=True,
        hosted_enabled=True,
        expected_policy=OutputPolicy.INTERACTIVE,
        expected_enabled=True,
    ),
]


def _make_ctx() -> typer.Context:
    """Build a minimal typer.Context with ctx.obj=None for testing."""
    app = typer.Typer()

    @app.callback()
    def _root_cb(ctx: typer.Context) -> None:  # pragma: no cover - test scaffolding
        pass

    cmd = typer.main.get_command(app)
    return typer.Context(cmd)


@pytest.mark.parametrize("row", MATRIX_ROWS, ids=[r.name for r in MATRIX_ROWS])
def test_suppression_matrix_no_teamspace_leakage(
    row: MatrixRow,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange env
    if row.hosted_enabled:
        monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    else:
        monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)

    if row.ci_env:
        monkeypatch.setenv("CI", "1")
    else:
        monkeypatch.delenv("CI", raising=False)

    # Arrange argv
    monkeypatch.setattr(sys, "argv", ["spec-kitty", *row.argv])

    # Arrange isatty by monkeypatching sys.stdout
    class _StdoutLike(io.StringIO):
        def __init__(self, isatty_value: bool) -> None:
            super().__init__()
            self._isatty_value = isatty_value

        def isatty(self) -> bool:
            return self._isatty_value

    # `capsys` already wraps stdout/stderr; we set isatty on the captured stream.
    # If your project's conftest provides a tty-toggle fixture, prefer that.
    monkeypatch.setattr(sys.stdout, "isatty", lambda: row.isatty)

    # Act
    ctx = _make_ctx()
    result = evaluate_readiness(ctx)

    # Assert: result fields
    assert isinstance(result, ReadinessResult), f"got {type(result)!r}"
    assert result.enabled == row.expected_enabled, f"row={row.name}: enabled mismatch"
    assert result.output_policy == row.expected_policy, f"row={row.name}: policy mismatch"
    if row.expected_enabled:
        assert result.auth_status == AuthStatus.NOT_CHECKED, f"row={row.name}: enabled rows expect NOT_CHECKED (WS2 stub)"
        assert result.ran is True
    else:
        assert result.auth_status == AuthStatus.DISABLED, f"row={row.name}: disabled rows expect DISABLED"
        assert result.ran is False

    # Assert: no Teamspace leakage
    captured = capsys.readouterr()
    assert "teamspace" not in captured.out.lower(), (
        f"row={row.name}: Teamspace leaked to stdout: {captured.out!r}"
    )
    assert "teamspace" not in captured.err.lower(), (
        f"row={row.name}: Teamspace leaked to stderr: {captured.err!r}"
    )
```

**Validation**:
- `pytest -q tests/readiness/test_coordinator_suppression_matrix.py` is green (8 parameterized rows).

**Notes**:
- If your project's existing test conventions differ on how to construct a `typer.Context`, prefer the existing pattern from `tests/cli_gate/test_ci_determinism.py`. Adapt `_make_ctx()` to match.
- The `CliRunner` import is kept for follow-up missions that may want full-CLI invocation; this WP uses direct `evaluate_readiness(ctx)` calls.

---

### Subtask T013 — Write `tests/readiness/test_coordinator_caching.py`

**Purpose**: Lock in the once-per-invocation caching invariant (FR-009) and the safe-defaults of `get_readiness` (FR-008).

**File**: `tests/readiness/test_coordinator_caching.py` (new)

**Content**:

```python
"""Caching invariants for the readiness coordinator.

Asserts FR-008 (get_readiness never raises, returns no-op default when no cache),
FR-009 (double-invocation returns cached result), and FR-007 (ctx.obj keying).

Mission: cli-startup-readiness-coordinator-skeleton-01KS7JRV
"""

from __future__ import annotations

import sys
from typing import Any

import pytest
import typer

from specify_cli.readiness import (
    AuthStatus,
    OutputPolicy,
    ReadinessResult,
    evaluate_readiness,
    get_readiness,
)
from specify_cli.readiness import coordinator as coord_module


def _make_ctx(obj: Any = None) -> typer.Context:
    """Build a minimal typer.Context with a settable ctx.obj."""
    app = typer.Typer()

    @app.callback()
    def _root_cb(ctx: typer.Context) -> None:  # pragma: no cover
        pass

    cmd = typer.main.get_command(app)
    ctx = typer.Context(cmd)
    ctx.obj = obj
    return ctx


def test_A_hosted_enabled_cached_after_first_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With SAAS sync enabled, calling evaluate_readiness twice invokes the nag once."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setattr(sys, "argv", ["spec-kitty", "status"])

    call_count = {"n": 0}

    def _spy_invoke_nag(ctx: typer.Context) -> None:
        call_count["n"] += 1

    monkeypatch.setattr(coord_module, "_invoke_nag", _spy_invoke_nag)

    ctx = _make_ctx()
    first = evaluate_readiness(ctx)
    second = evaluate_readiness(ctx)

    assert call_count["n"] == 1, f"expected 1 nag call, got {call_count['n']}"
    assert first is second, "second call should return cached result instance"
    assert first.enabled is True


def test_B_hosted_disabled_cached_after_first_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without SAAS sync, the disabled path still caches and still invokes the nag exactly once."""
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.setattr(sys, "argv", ["spec-kitty", "status"])

    call_count = {"n": 0}

    def _spy_invoke_nag(ctx: typer.Context) -> None:
        call_count["n"] += 1

    monkeypatch.setattr(coord_module, "_invoke_nag", _spy_invoke_nag)

    ctx = _make_ctx()
    first = evaluate_readiness(ctx)
    second = evaluate_readiness(ctx)

    assert call_count["n"] == 1, f"expected 1 nag call, got {call_count['n']}"
    assert first is second
    assert first.enabled is False


def test_C_get_readiness_returns_same_instance_after_evaluate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_readiness returns the cached ReadinessResult by identity."""
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.setattr(sys, "argv", ["spec-kitty"])
    monkeypatch.setattr(coord_module, "_invoke_nag", lambda ctx: None)

    ctx = _make_ctx()
    evaluated = evaluate_readiness(ctx)
    retrieved = get_readiness(ctx)

    assert retrieved is evaluated


def test_D_get_readiness_fresh_ctx_returns_noop_default() -> None:
    """get_readiness on a fresh ctx with no cache returns the no-op default, does not raise."""
    ctx = _make_ctx(obj=None)
    result = get_readiness(ctx)
    assert isinstance(result, ReadinessResult)
    assert result.enabled is False
    assert result.ran is False
    assert result.auth_status == AuthStatus.DISABLED
    assert result.nag_invoked is False


def test_E_get_readiness_non_dict_ctx_obj_returns_noop_default() -> None:
    """get_readiness with a non-dict, non-None ctx.obj returns the no-op default, does not raise."""

    class _Opaque:
        pass

    ctx = _make_ctx(obj=_Opaque())
    result = get_readiness(ctx)
    assert isinstance(result, ReadinessResult)
    assert result.enabled is False
    assert result.ran is False
    assert result.auth_status == AuthStatus.DISABLED
```

**Validation**:
- `pytest -q tests/readiness/test_coordinator_caching.py` is green (5 tests).

---

## Definition of Done

- [ ] `tests/readiness/__init__.py` exists.
- [ ] `tests/readiness/test_coordinator_suppression_matrix.py` exercises the 8 rows (7 disabled + 1 enabled) and asserts the no-Teamspace-leakage invariant on every row.
- [ ] `tests/readiness/test_coordinator_caching.py` covers all 5 cases A–E.
- [ ] `pytest -q tests/readiness/test_coordinator_suppression_matrix.py tests/readiness/test_coordinator_caching.py` is green.
- [ ] No production code modified in this WP (tests only).

## Risks

- **R1 (P=Med, I=Low)**: `_make_ctx` may not exactly match the project's existing convention for building typer.Context in tests. **Mitigation**: copy or adapt the pattern from `tests/cli_gate/test_ci_determinism.py`.
- **R2 (P=Low, I=Low)**: Monkeypatching `sys.stdout.isatty` may interact with `capsys`. **Mitigation**: if interference appears, switch to setting `isatty` on the captured stream directly or using a custom stdout replacement.
- **R3 (P=Low, I=Med)**: The spy for `_invoke_nag` patches a module attribute that's referenced by name from inside `_evaluate_uncached`. **Mitigation**: patch on the `coordinator` module attribute (already done in the snippets — `monkeypatch.setattr(coord_module, "_invoke_nag", ...)`).

## Reviewer Guidance

- Confirm the 7-row matrix matches the rows in `spec.md` and `plan.md` exactly: help, version, plain, --json, --quiet, CI=1, non-TTY.
- Confirm the 8th row (hosted-mode-enabled) asserts `enabled=True`, `auth_status=NOT_CHECKED`, and that **no** Teamspace string leaked (because the auth probe is not exercised this mission).
- Confirm the caching tests do NOT rely on internal helpers; they go through the public `evaluate_readiness` + `get_readiness` API.
- Confirm `_invoke_nag` is patched on `coord_module` (the import target), not on the helpers module.

## Out of Scope

- Nag passthrough behavioral tests — WP03.
- Verifying the existing `tests/cli_gate/test_ci_determinism.py` still passes — WP03 (formal gate).
- Coverage report — WP03.

## Activity Log

- 2026-05-22T10:42:30Z – claude:opus:python-pedro:implementer – shell_pid=65358 – Assigned agent via action command
