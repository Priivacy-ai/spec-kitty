---
work_package_id: WP03
title: Nag passthrough test + final verification
dependencies:
- WP02
requirement_refs:
- FR-006
- FR-012
- NFR-001
- NFR-004
- NFR-005
planning_base_branch: kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV
merge_target_branch: kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV
base_commit: df8525a60577bf9686172d5d535e38f34f6b053a
created_at: '2026-05-22T10:44:56.954151+00:00'
subtasks:
- T014
- T015
- T016
- T017
shell_pid: "67861"
history: []
agent_profile: python-pedro
authoritative_surface: tests/readiness/
execution_mode: code_change
owned_files:
- tests/readiness/test_coordinator_nag_passthrough.py
role: implementer
tags: []
agent: "claude:opus:reviewer-renata:reviewer"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

Then return here and read on.

---

## Objective

Lock in the final acceptance gates. Three concrete deliverables:

1. **Nag passthrough behavioral test** (`tests/readiness/test_coordinator_nag_passthrough.py`) — proves the coordinator's wrapping of `_render_nag_if_needed` is byte-for-byte equivalent to the pre-mission inline call (FR-006).
2. **Existing CI-determinism tests pass unchanged** — formal gate for the "preserved nag behavior" contract.
3. **Mypy / coverage / diff-scope verification** — locks NFR-004 (≥ 90% line coverage), NFR-005 (mypy --strict), and AC #9 (diff confined to declared file surfaces).

After this WP: the mission is ready for `/spec-kitty.analyze`, Renata review, and PR open.

---

## Context

Read first:
1. `kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/spec.md` — FR-006, FR-012, AC #5, AC #6, AC #7, AC #9.
2. `tests/cli_gate/test_ci_determinism.py` — the existing CI-determinism tests that MUST continue passing unmodified.
3. `src/specify_cli/cli/helpers.py` `_render_nag_if_needed` — understand the existing behavior the coordinator now wraps (suppression checks, planner call, NagCache write, exception swallowing).
4. WP02's two test files — your fixtures and `_make_ctx` helper carry over (or duplicate them; this is a small mission and copy-paste-for-clarity is acceptable).

---

## Branch Strategy

- **Planning/base branch**: `main`
- **Mission branch**: `kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV`
- **Merge target for the PR**: `main`
- **Worktree for this WP**: `lane-a`.
- **Implement command**: `spec-kitty agent action implement WP03 --agent claude`

---

## Markdown formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``.
Use language identifiers in code blocks: ```` ```python ```` , ```` ```bash ```` .

---

## Subtasks

### Subtask T014 — Write `tests/readiness/test_coordinator_nag_passthrough.py`

**Purpose**: Three cases asserting the coordinator's nag wrapping preserves the existing nag's behavior.

**File**: `tests/readiness/test_coordinator_nag_passthrough.py` (new)

**Content**:

```python
"""Nag passthrough behavioral tests for the readiness coordinator.

Asserts FR-006 (the coordinator wraps _render_nag_if_needed byte-for-byte)
and FR-010 (the coordinator never raises, even when the planner inside the
nag does).

Mission: cli-startup-readiness-coordinator-skeleton-01KS7JRV
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from typing import Any

import pytest
import typer

from specify_cli.readiness import ReadinessResult, evaluate_readiness


def _make_ctx() -> typer.Context:
    app = typer.Typer()

    @app.callback()
    def _root_cb(ctx: typer.Context) -> None:  # pragma: no cover
        pass

    cmd = typer.main.get_command(app)
    ctx = typer.Context(cmd)
    ctx.obj = None
    return ctx


def test_A_nag_renders_on_stderr_under_allow_with_nag(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When compat.plan returns ALLOW_WITH_NAG and conditions permit, the nag
    renders on stderr through the coordinator path."""
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
    monkeypatch.setattr(sys, "argv", ["spec-kitty", "status"])
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(sys.stderr, "isatty", lambda: True)

    expected_nag = "SENTINEL-NAG-LINE: upgrade-to-spec-kitty-cli-99.0.0"

    # Mock the planner used by _render_nag_if_needed.
    from specify_cli.compat import Decision

    class _FakeCLIStatus:
        installed_version = "3.0.0"
        latest_version = "99.0.0"
        latest_source = "test"

    class _FakeResult:
        decision = Decision.ALLOW_WITH_NAG
        rendered_human = expected_nag
        cli_status = _FakeCLIStatus()

    def _fake_plan(inv: Any) -> Any:
        return _FakeResult()

    monkeypatch.setattr("specify_cli.compat.plan", _fake_plan)

    # Avoid touching the real nag cache on disk.
    from specify_cli.compat import NagCache

    class _NoopCache:
        @staticmethod
        def default() -> "_NoopCache":
            return _NoopCache()

        def read(self) -> Any:
            return None

        def write(self, record: Any) -> None:
            return None

    monkeypatch.setattr("specify_cli.compat.NagCache", _NoopCache)

    ctx = _make_ctx()
    result = evaluate_readiness(ctx)

    assert isinstance(result, ReadinessResult)
    captured = capsys.readouterr()
    assert expected_nag in captured.err, (
        f"expected nag on stderr, got stdout={captured.out!r} stderr={captured.err!r}"
    )


def test_B_nag_suppressed_when_json_in_argv(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When --json is in argv, the nag is suppressed even if compat.plan
    would have returned ALLOW_WITH_NAG."""
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("SPEC_KITTY_NO_NAG", raising=False)
    monkeypatch.setattr(sys, "argv", ["spec-kitty", "status", "--json"])
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(sys.stderr, "isatty", lambda: True)

    sentinel = "SENTINEL-NAG-LINE-SHOULD-NOT-APPEAR"

    from specify_cli.compat import Decision

    class _FakeCLIStatus:
        installed_version = "3.0.0"
        latest_version = "99.0.0"
        latest_source = "test"

    class _FakeResult:
        decision = Decision.ALLOW_WITH_NAG
        rendered_human = sentinel
        cli_status = _FakeCLIStatus()

    monkeypatch.setattr("specify_cli.compat.plan", lambda inv: _FakeResult())

    ctx = _make_ctx()
    evaluate_readiness(ctx)

    captured = capsys.readouterr()
    assert sentinel not in captured.out, f"nag leaked to stdout: {captured.out!r}"
    assert sentinel not in captured.err, f"nag leaked to stderr: {captured.err!r}"


def test_C_planner_exception_does_not_propagate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A planner exception inside the wrapped nag is swallowed by
    _render_nag_if_needed's own try/except; the coordinator does not raise."""
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.setattr(sys, "argv", ["spec-kitty", "status"])
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    def _raising_plan(inv: Any) -> Any:
        raise RuntimeError("simulated planner failure")

    monkeypatch.setattr("specify_cli.compat.plan", _raising_plan)

    ctx = _make_ctx()
    # Must not raise.
    result = evaluate_readiness(ctx)
    assert isinstance(result, ReadinessResult)
```

**Validation**:
- `pytest -q tests/readiness/test_coordinator_nag_passthrough.py` is green (3 tests).

**Notes**:
- The exact `specify_cli.compat` import surface may differ from the names above (`Decision`, `NagCache`); inspect `src/specify_cli/compat/__init__.py` and adapt the mock targets. The point of the test is to drive the planner result; the names matter only insofar as they match the real `_render_nag_if_needed` consumption sites.

---

### Subtask T015 — Verify existing CI-determinism tests pass unchanged

**Purpose**: Formal gate for AC #5 — the existing tests in `tests/cli_gate/test_ci_determinism.py` MUST pass with no modification on the mission branch. This is the strongest evidence that `_render_nag_if_needed` behavior is preserved byte-for-byte.

**Steps**:

1. Confirm `tests/cli_gate/test_ci_determinism.py` is unmodified relative to `main`:
   ```bash
   git diff main -- tests/cli_gate/test_ci_determinism.py
   ```
   Expected: empty output (no diff).

2. Run the suite:
   ```bash
   pytest -q tests/cli_gate/test_ci_determinism.py
   ```
   Expected: all tests pass.

3. If any test fails, **stop** and triage. The fix is in the production code (most likely `coordinator.py` or `helpers.py`), not in the test file. Do not modify `tests/cli_gate/test_ci_determinism.py`.

**Validation**: zero diff in `tests/cli_gate/test_ci_determinism.py`; full pass.

---

### Subtask T016 — Verify `mypy --strict` on the readiness package + helpers

**Purpose**: Lock NFR-005.

**Steps**:

```bash
mypy --strict src/specify_cli/readiness/ src/specify_cli/cli/helpers.py
```

Expected: no errors.

If errors appear:
- Missing type annotations in the new code → add them.
- `--strict` complaining about an existing line in `helpers.py` that already passed on `main` → narrow the change so it doesn't widen mypy's surface; the WP01 hook is a 2-line addition that should not regress mypy.

**Validation**: `mypy --strict src/specify_cli/readiness/ src/specify_cli/cli/helpers.py` exits 0.

---

### Subtask T017 — Verify coverage + diff scope

**Purpose**: Lock NFR-004 and AC #9.

**Steps**:

1. Coverage on the readiness package:
   ```bash
   pytest -q --cov=src/specify_cli/readiness --cov-report=term tests/readiness/
   ```
   Expected: `src/specify_cli/readiness/__init__.py` and `coordinator.py` together report ≥ 90% line coverage.

   If coverage is < 90%:
   - Inspect the missing lines (`--cov-report=term-missing`).
   - Add a targeted test to `test_coordinator_caching.py` or `test_coordinator_nag_passthrough.py`. Do NOT loosen the coverage threshold.

2. Diff scope:
   ```bash
   git diff main...HEAD --stat
   ```
   Expected files (per AC #9):
   - `src/specify_cli/readiness/__init__.py`
   - `src/specify_cli/readiness/coordinator.py`
   - `src/specify_cli/cli/helpers.py`
   - `tests/readiness/__init__.py`
   - `tests/readiness/test_coordinator_suppression_matrix.py`
   - `tests/readiness/test_coordinator_caching.py`
   - `tests/readiness/test_coordinator_nag_passthrough.py`
   - Anything under `kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/` (mission artifacts)

   If any file outside this list shows up, **stop** and remove it (it's accidental scope).

3. Confirm `_render_nag_if_needed` is no longer called inline from `callback`:
   ```bash
   grep -n "_render_nag_if_needed" src/specify_cli/cli/helpers.py
   ```
   Expected: matches inside the function definition itself and in `__all__`, but NOT inside `callback()`. The only call site in `callback()` is now `evaluate_readiness(ctx)`.

4. Confirm the WS2 hand-off marker is still present:
   ```bash
   grep -n "WS2: auth probe wiring" src/specify_cli/readiness/coordinator.py
   ```
   Expected: at least 1 hit (on the `_auth_recovery` import line and/or inline at the call-site stub).

**Validation matrix**:
| Check | Expected | Result |
|---|---|---|
| Coverage ≥ 90% | true | |
| Diff scope matches AC #9 | true | |
| No inline `_render_nag_if_needed(ctx)` in `callback` | true | |
| `WS2: auth probe wiring` marker present | true | |

---

## Definition of Done

- [ ] `tests/readiness/test_coordinator_nag_passthrough.py` written; 3 tests pass.
- [ ] `tests/cli_gate/test_ci_determinism.py` is unmodified and still passes.
- [ ] `pytest -q tests/readiness/ tests/cli_gate/test_ci_determinism.py` green.
- [ ] `mypy --strict src/specify_cli/readiness/ src/specify_cli/cli/helpers.py` exits 0.
- [ ] `pytest --cov=src/specify_cli/readiness tests/readiness/` ≥ 90% line coverage.
- [ ] `git diff main...HEAD --stat` matches AC #9 (no files outside the declared surfaces).
- [ ] `_render_nag_if_needed` not called inline from `callback`.
- [ ] `WS2: auth probe wiring` marker still present in `coordinator.py`.

## Risks

- **R1 (P=Med, I=Med)**: Mocking `specify_cli.compat.plan` may not be load-bearing if `_render_nag_if_needed` imports `plan` under a different name. **Mitigation**: read `helpers.py` lines 195–215 first; mock the exact attribute names. Adapt the snippets if the actual surface differs.
- **R2 (P=Low, I=High)**: Coverage gap on a specific defensive branch (e.g. the non-dict `ctx.obj` branch in `_write_cached`). **Mitigation**: WP02 test E already exercises non-dict `ctx.obj`; verify with `--cov-report=term-missing`.
- **R3 (P=Low, I=Med)**: A test in `tests/cli_gate/test_ci_determinism.py` flakes because the nag call site moved by one stack-frame. **Mitigation**: those tests call `_render_nag_if_needed` directly, not through `callback`; they should not see the move. If a failure appears, triage in production code, not in the test.

## Reviewer Guidance

- Confirm `tests/cli_gate/test_ci_determinism.py` is **byte-identical** to `main`. Any change to that file is a fail.
- Confirm coverage report shows ≥ 90% on `src/specify_cli/readiness/`. Read the missing lines if any; either justify them (e.g. unreachable defensive `except`) or add a test.
- Confirm the `git diff main...HEAD --stat` is small and confined to the declared surfaces.
- Confirm the WS2 seam (`# WS2: auth probe wiring`) is still grep-able for the next mission's reviewer.

## Out of Scope

- Implementing the WS2 auth probe — separate mission (#1094).
- Adding upgrade UX prompts — separate mission (#1092).
- Performance benchmarking — NFR-001 thresholds are checked by inspection only in this mission. A formal benchmark is a follow-up if anyone wants to lock the threshold harder.

## Activity Log

- 2026-05-22T10:44:58Z – claude:opus:python-pedro:implementer – shell_pid=66649 – Assigned agent via action command
- 2026-05-22T10:47:23Z – claude:opus:python-pedro:implementer – shell_pid=66649 – WP03 ready: 3/3 nag passthrough tests pass. 36/36 full suite pass. tests/cli_gate/test_ci_determinism.py byte-identical to main. mypy --strict on readiness/ clean. 94% coverage on readiness package (>=90% target). Diff scope confirmed within AC #9 surfaces.
- 2026-05-22T10:47:30Z – claude:opus:reviewer-renata:reviewer – shell_pid=67861 – Started review via action command
- 2026-05-22T10:47:45Z – claude:opus:reviewer-renata:reviewer – shell_pid=67861 – Renata review: APPROVED. All acceptance criteria pass. 36/36 tests green. tests/cli_gate/test_ci_determinism.py byte-identical to main. mypy --strict clean on readiness/. 94% coverage. Diff scope within AC #9. WS2 seam intact.
