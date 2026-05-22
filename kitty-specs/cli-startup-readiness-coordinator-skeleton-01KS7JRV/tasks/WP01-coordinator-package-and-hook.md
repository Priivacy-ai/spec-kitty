---
work_package_id: WP01
title: Coordinator package + callback hook
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- NFR-005
planning_base_branch: kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV
merge_target_branch: kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV
base_commit: 0a2039b99964e4109827baa635e397da5c57e39b
created_at: '2026-05-22T10:38:40.128947+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
- T009
- T010
shell_pid: "62483"
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/readiness/
execution_mode: code_change
owned_files:
- src/specify_cli/readiness/__init__.py
- src/specify_cli/readiness/coordinator.py
- src/specify_cli/cli/helpers.py
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

Land the central CLI startup readiness coordinator (the seam referenced by Priivacy-ai/spec-kitty#1093) and wire it into the root CLI callback in a single coherent change. When this WP is done:

- `src/specify_cli/readiness/` exists with `__init__.py` and `coordinator.py`.
- The five public symbols (`AuthStatus`, `OutputPolicy`, `ReadinessResult`, `evaluate_readiness`, `get_readiness`) are importable from `specify_cli.readiness`.
- `evaluate_readiness(ctx)` gates on `is_saas_sync_enabled()` first (FR-003), composes output policy + auth stub + nag passthrough, and stores a typed result on `ctx.obj` (FR-007).
- `get_readiness(ctx)` reads the cached result safely (FR-008); double-invocation returns the cached instance (FR-009).
- The coordinator never raises (FR-010).
- `src/specify_cli/cli/helpers.py` `callback()` calls `evaluate_readiness(ctx)` in place of its previous inline call to `_render_nag_if_needed(ctx)` (FR-002, FR-006).
- `mypy --strict` passes on the new + modified surfaces (NFR-005).

Tests for this WP land in WP02 (suppression matrix + caching) and WP03 (nag passthrough + final verification). This WP delivers production code only.

---

## Context

Read first:
1. `kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/spec.md` — authoritative spec (FR-001 through FR-010, all Constraints).
2. `kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/plan.md` — architecture sections "The seam", "The callback hook", "`ctx.obj` keying", "How `OutputPolicy` is derived".
3. `kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/data-model.md` — public types contract.
4. `kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/contracts/readiness-api.md` — API surface contract.
5. `kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/research.md` — design decisions 1–6.
6. `src/specify_cli/cli/helpers.py` (current state) — understand `_render_nag_if_needed` and `_should_suppress_nag` before touching the callback.
7. `src/specify_cli/saas/rollout.py` — `is_saas_sync_enabled()` truthy-value contract.
8. `src/specify_cli/cli/commands/_auth_recovery.py` — `detect_logged_out_with_connected_teamspace` (imported here as a typed stub seam; not exercised in this mission).

---

## Branch Strategy

- **Planning/base branch**: `main`
- **Mission branch (carries WP commits)**: `kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV`
- **Merge target for the PR**: `main`
- **Worktree for this WP**: `lane-a`, allocated by `finalize-tasks`; consult `lanes.json`.
- **Implement command**: `spec-kitty agent action implement WP01 --agent claude`

---

## Markdown formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``.
Use language identifiers in code blocks: ```` ```python ```` , ```` ```bash ```` .

---

## Subtasks

### Subtask T001 — Create `src/specify_cli/readiness/__init__.py`

**Purpose**: Re-export the public API so consumers import from `specify_cli.readiness` rather than the internal `coordinator` module.

**File**: `src/specify_cli/readiness/__init__.py` (new)

**Content**:

```python
"""Central CLI startup readiness coordinator.

Public surface (consumed by the root CLI callback and by subcommands that
need to read the readiness verdict):

    from specify_cli.readiness import (
        AuthStatus,
        OutputPolicy,
        ReadinessResult,
        evaluate_readiness,
        get_readiness,
    )

See ``kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/contracts/readiness-api.md``
for the stability contract.

Tracking issue: https://github.com/Priivacy-ai/spec-kitty/issues/1093
"""

from __future__ import annotations

from specify_cli.readiness.coordinator import (
    AuthStatus,
    OutputPolicy,
    ReadinessResult,
    evaluate_readiness,
    get_readiness,
)

__all__ = [
    "AuthStatus",
    "OutputPolicy",
    "ReadinessResult",
    "evaluate_readiness",
    "get_readiness",
]
```

**Validation**: `python -c "from specify_cli.readiness import AuthStatus, OutputPolicy, ReadinessResult, evaluate_readiness, get_readiness; print('OK')"` prints `OK` (only after T002+T003 are in place).

---

### Subtask T002 — Create `coordinator.py` types

**Purpose**: Define `OutputPolicy`, `AuthStatus`, `ReadinessResult`, and the `_NOOP_DISABLED` module sentinel. Establish the `_auth_recovery` stub seam.

**File**: `src/specify_cli/readiness/coordinator.py` (new)

**Content**:

```python
"""Central CLI startup readiness coordinator implementation.

See spec: kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/spec.md
See data model: kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/data-model.md
See contracts: kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/contracts/readiness-api.md

The coordinator's first gate is ``is_saas_sync_enabled()``. When hosted mode is
disabled the coordinator returns a no-op result and emits no Teamspace-labeled
output. When hosted mode is enabled the coordinator composes (stubbed in this
mission) feature-gate state, output policy, auth readiness, and upgrade
readiness into a typed ``ReadinessResult`` cached on ``ctx.obj``.

Tracking issue: https://github.com/Priivacy-ai/spec-kitty/issues/1093
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import StrEnum

import typer

# WS2: auth probe wiring — imported as a typed stub seam, not exercised in this mission.
# The next mission (workstream 2, issue #1094) will call this from inside
# ``_evaluate_uncached`` on the enabled path; this import keeps the symbol
# type-checked and grep-able as a hand-off marker.
from specify_cli.cli.commands._auth_recovery import (  # noqa: F401
    detect_logged_out_with_connected_teamspace,
)

_READINESS_CTX_KEY = "readiness"


class OutputPolicy(StrEnum):
    """Three-bucket suppression classification.

    See ``data-model.md`` for the precedence rules.
    """

    INTERACTIVE = "interactive"
    NON_INTERACTIVE = "non_interactive"
    MACHINE_OUTPUT = "machine_output"


class AuthStatus(StrEnum):
    """Coordinator's record of Teamspace-auth state.

    This mission ships only ``NOT_CHECKED`` and ``DISABLED``. WS2 (issue
    #1094) widens this enum with values like ``AUTHENTICATED`` and
    ``LOGGED_OUT_ON_CONNECTED_TEAMSPACE``.
    """

    NOT_CHECKED = "not_checked"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    """Cached readiness verdict for a single CLI invocation.

    Frozen and slotted: subcommands MUST NOT mutate fields. Field additions
    in future missions are allowed; removals require a mission-level
    deprecation per ``contracts/readiness-api.md``.
    """

    enabled: bool
    ran: bool
    output_policy: OutputPolicy
    auth_status: AuthStatus
    nag_invoked: bool


_NOOP_DISABLED: ReadinessResult = ReadinessResult(
    enabled=False,
    ran=False,
    output_policy=OutputPolicy.NON_INTERACTIVE,
    auth_status=AuthStatus.DISABLED,
    nag_invoked=False,
)
```

**Validation**: `mypy --strict src/specify_cli/readiness/coordinator.py` passes.

---

### Subtask T003 — Implement `_derive_output_policy(argv=None) -> OutputPolicy`

**Purpose**: Compute the 3-bucket suppression classification from the same primitive signals `_should_suppress_nag()` consults, exactly once per invocation.

**File**: `src/specify_cli/readiness/coordinator.py` (append)

**Append**:

```python
def _derive_output_policy(argv: list[str] | None = None) -> OutputPolicy:
    """Classify the active suppression conditions into the 3-bucket policy.

    Precedence (highest first):
      MACHINE_OUTPUT — `--json` or `--quiet` in argv.
      NON_INTERACTIVE — `--help`/`-h`/`--version`/`-v` in argv,
                        OR is_ci_env() true,
                        OR stdout is not a TTY.
      INTERACTIVE — otherwise.

    Mirrors the signal set consulted by ``_should_suppress_nag`` but produces a
    three-bucket value instead of a single boolean. The single source of truth
    for nag suppression remains ``_should_suppress_nag`` inside
    ``_render_nag_if_needed``; this function records the bucket for
    downstream consumers (WS2 auth, WS3 upgrade UX).
    """
    if argv is None:
        argv = sys.argv[1:]

    if "--json" in argv or "--quiet" in argv:
        return OutputPolicy.MACHINE_OUTPUT

    help_flags = {"--help", "-h", "--version", "-v"}
    if any(tok in help_flags for tok in argv):
        return OutputPolicy.NON_INTERACTIVE

    # Lazy import: keeps coordinator import-time cheap.
    from specify_cli.compat.planner import is_ci_env  # noqa: PLC0415

    if is_ci_env():
        return OutputPolicy.NON_INTERACTIVE

    try:
        if not sys.stdout.isatty():
            return OutputPolicy.NON_INTERACTIVE
    except Exception:  # noqa: BLE001 — isatty() can raise on exotic stream objects; treat as non-tty.
        return OutputPolicy.NON_INTERACTIVE

    return OutputPolicy.INTERACTIVE
```

---

### Subtask T004 — Implement `_read_cached` and `_write_cached`

**Purpose**: Encapsulate the `ctx.obj` keying contract.

**File**: `src/specify_cli/readiness/coordinator.py` (append)

**Append**:

```python
def _read_cached(ctx: typer.Context) -> ReadinessResult | None:
    """Return the cached readiness result if reachable, else ``None``.

    Never raises. Returns ``None`` (not ``_NOOP_DISABLED``) so callers can
    distinguish "no cache" from "cached no-op".
    """
    obj = ctx.obj
    if not isinstance(obj, dict):
        return None
    cached = obj.get(_READINESS_CTX_KEY)
    if isinstance(cached, ReadinessResult):
        return cached
    return None


def _write_cached(ctx: typer.Context, result: ReadinessResult) -> None:
    """Store ``result`` on ``ctx.obj`` under ``_READINESS_CTX_KEY``.

    If ``ctx.obj`` is ``None``, initialize it to ``{}``. If ``ctx.obj`` is
    already a dict, set the key (other keys like ``compat_plan_result``
    remain untouched). If ``ctx.obj`` is a non-dict, non-None object
    (defensive), skip caching silently — ``get_readiness`` will return
    ``_NOOP_DISABLED`` for that ``ctx``.
    """
    obj = ctx.obj
    if obj is None:
        ctx.obj = {_READINESS_CTX_KEY: result}
        return
    if isinstance(obj, dict):
        obj[_READINESS_CTX_KEY] = result
```

---

### Subtask T005 — Implement `_invoke_nag`

**Purpose**: Wrap `_render_nag_if_needed(ctx)` from inside the coordinator. Lazy import breaks the cycle between `helpers.py` and `coordinator.py`.

**File**: `src/specify_cli/readiness/coordinator.py` (append)

**Append**:

```python
def _invoke_nag(ctx: typer.Context) -> None:
    """Invoke the existing upgrade-nag renderer through the coordinator.

    Lazy import: ``helpers.callback`` imports ``evaluate_readiness`` from
    ``specify_cli.readiness`` at call time. Importing ``_render_nag_if_needed``
    at module scope here would form an import cycle.

    ``_render_nag_if_needed`` already swallows its own exceptions and applies
    its own suppression checks; this wrapper adds no gating of its own.
    Preserves byte-for-byte behavior of the pre-mission inline call from
    ``callback()``.
    """
    from specify_cli.cli.helpers import _render_nag_if_needed  # noqa: PLC0415

    _render_nag_if_needed(ctx)
```

---

### Subtask T006 — Implement `_evaluate_uncached`

**Purpose**: The branching logic.

**File**: `src/specify_cli/readiness/coordinator.py` (append)

**Append**:

```python
def _evaluate_uncached(ctx: typer.Context) -> ReadinessResult:
    """Compute a fresh ``ReadinessResult`` for the current invocation.

    Branches on ``is_saas_sync_enabled()``:

    - **Disabled path**: return a ``ReadinessResult`` with ``enabled=False``
      and ``ran=False``. The legacy upgrade-nag still fires (existing
      behavior is preserved exactly), so ``_invoke_nag`` is called before
      returning.

    - **Enabled path**: derive the output policy, stub ``auth_status`` as
      ``NOT_CHECKED`` (WS2 will wire the real probe here using the import
      already established in this module), invoke the nag, and return a
      ``ReadinessResult`` with ``enabled=True`` and ``ran=True``.

    No network I/O. No SaaS DB / queue / readiness counter mutation.
    """
    from specify_cli.saas.rollout import is_saas_sync_enabled  # noqa: PLC0415

    output_policy = _derive_output_policy()

    if not is_saas_sync_enabled():
        _invoke_nag(ctx)
        return ReadinessResult(
            enabled=False,
            ran=False,
            output_policy=output_policy,
            auth_status=AuthStatus.DISABLED,
            nag_invoked=True,
        )

    # WS2: auth probe wiring — the next mission will call
    # detect_logged_out_with_connected_teamspace() here and translate the
    # result into the appropriate AuthStatus value.
    _invoke_nag(ctx)
    return ReadinessResult(
        enabled=True,
        ran=True,
        output_policy=output_policy,
        auth_status=AuthStatus.NOT_CHECKED,
        nag_invoked=True,
    )
```

---

### Subtask T007 — Implement `evaluate_readiness` (public API)

**Purpose**: Idempotent entry point with cache + exception-swallowing safety net.

**File**: `src/specify_cli/readiness/coordinator.py` (append)

**Append**:

```python
def evaluate_readiness(ctx: typer.Context) -> ReadinessResult:
    """Compute (or return the cached) readiness result for this CLI invocation.

    Idempotent: a second call on the same ``ctx`` returns the cached
    ``ReadinessResult`` without re-running any logic (FR-009).

    Never raises. Internal exceptions are swallowed and the caller receives
    ``_NOOP_DISABLED`` instead (FR-010). The CLI cannot crash because of
    readiness logic.

    Side effects:
      - On the first invocation, stores the result on ``ctx.obj['readiness']``
        when ``ctx.obj`` is ``None`` or a dict.
      - Invokes ``_render_nag_if_needed(ctx)`` exactly once during the first
        invocation under both the disabled and enabled paths.
    """
    cached = _read_cached(ctx)
    if cached is not None:
        return cached

    try:
        result = _evaluate_uncached(ctx)
    except Exception:  # noqa: BLE001 — coordinator must never raise out of the CLI startup path.
        result = _NOOP_DISABLED

    _write_cached(ctx, result)
    return result
```

---

### Subtask T008 — Implement `get_readiness` (public API)

**Purpose**: Read-only accessor for subcommand handlers.

**File**: `src/specify_cli/readiness/coordinator.py` (append)

**Append**:

```python
def get_readiness(ctx: typer.Context) -> ReadinessResult:
    """Return the cached readiness result, or ``_NOOP_DISABLED`` if none cached.

    Never re-runs ``evaluate_readiness``. Never raises. Safe to call from any
    subcommand handler regardless of ``ctx.obj`` state.
    """
    cached = _read_cached(ctx)
    return cached if cached is not None else _NOOP_DISABLED
```

---

### Subtask T009 — Wire the coordinator into the root callback

**Purpose**: Replace the inline `_render_nag_if_needed(ctx)` call in `callback()` with `evaluate_readiness(ctx)`. The coordinator now owns the nag call site (FR-006).

**File**: `src/specify_cli/cli/helpers.py` (modify the `callback` function only)

**Current state** (around line 267–290):

```python
def callback(ctx: typer.Context) -> None:
    """Display the banner when CLI is invoked without a subcommand."""
    if ctx.invoked_subcommand is None and "--help" not in sys.argv and "-h" not in sys.argv:
        show_banner()
        console.print(Align.center("[dim]Run 'spec-kitty --help' for usage information[/dim]"))
        console.print()

    # WP08: render upgrade nag through planner if needed.
    _render_nag_if_needed(ctx)

    # WP09 (FR-007): emit "no upgrade available" notice when warranted.
    # ... unchanged ...
```

**Target state**:

```python
def callback(ctx: typer.Context) -> None:
    """Display the banner when CLI is invoked without a subcommand."""
    if ctx.invoked_subcommand is None and "--help" not in sys.argv and "-h" not in sys.argv:
        show_banner()
        console.print(Align.center("[dim]Run 'spec-kitty --help' for usage information[/dim]"))
        console.print()

    # Teamspace CLI auth/upgrade readiness coordinator (Priivacy-ai/spec-kitty#1093).
    # First-gated on is_saas_sync_enabled(); no-ops when hosted mode is disabled.
    # The coordinator owns the call to _render_nag_if_needed() so downstream
    # missions (WS2 auth, WS3 upgrade UX) can extend behavior through one seam.
    # Lazy import to avoid module-load circularity (readiness/coordinator.py
    # imports _render_nag_if_needed back from this module at call time).
    from specify_cli.readiness import evaluate_readiness  # noqa: PLC0415

    evaluate_readiness(ctx)

    # WP09 (FR-007): emit "no upgrade available" notice when warranted.
    # ... unchanged ...
```

**Diff invariants**:
- Banner block is byte-identical.
- `maybe_emit_no_upgrade_notice` block is byte-identical.
- `_render_nag_if_needed(ctx)` is no longer called directly from `callback()`.
- `_render_nag_if_needed` remains in `helpers.__all__` (C-005).

---

### Subtask T010 — Verification

**Purpose**: Confirm the WP01 acceptance gates before handoff to WP02.

**Steps**:

1. Confirm imports resolve from a clean Python process:
   ```bash
   python -c "from specify_cli.readiness import AuthStatus, OutputPolicy, ReadinessResult, evaluate_readiness, get_readiness; print('OK')"
   ```
   Expected: `OK`.

2. Confirm mypy --strict on both surfaces:
   ```bash
   mypy --strict src/specify_cli/readiness/ src/specify_cli/cli/helpers.py
   ```
   Expected: no errors.

3. Confirm the existing CI-determinism tests still pass (smoke gate; WP03 makes this the formal gate):
   ```bash
   pytest -q tests/cli_gate/test_ci_determinism.py
   ```
   Expected: green.

4. Confirm `_render_nag_if_needed` is no longer called inline from `callback`:
   ```bash
   grep -n "_render_nag_if_needed" src/specify_cli/cli/helpers.py
   ```
   Expected: hits inside the function definition itself and in `__all__`, but no longer inside `callback()`.

5. Confirm `WS2: auth probe wiring` marker is present:
   ```bash
   grep -n "WS2: auth probe wiring" src/specify_cli/readiness/coordinator.py
   ```
   Expected: at least 1 hit.

---

## Definition of Done

- [ ] `src/specify_cli/readiness/__init__.py` and `coordinator.py` exist with the documented public surface and full implementation.
- [ ] `_derive_output_policy`, `_read_cached`, `_write_cached`, `_invoke_nag`, `_evaluate_uncached`, `evaluate_readiness`, `get_readiness` all implemented per the snippets.
- [ ] `callback()` in `helpers.py` calls `evaluate_readiness(ctx)` in place of the inline `_render_nag_if_needed(ctx)` call.
- [ ] `mypy --strict src/specify_cli/readiness/ src/specify_cli/cli/helpers.py` passes.
- [ ] `pytest -q tests/cli_gate/test_ci_determinism.py` passes (smoke).
- [ ] `_render_nag_if_needed` still in `helpers.__all__` (C-005).
- [ ] `WS2: auth probe wiring` marker present in `coordinator.py`.
- [ ] No other files modified.

## Risks

- **R1**: Import cycle between `helpers.py` and `coordinator.py`. **Mitigation**: both directions are lazy — `helpers.callback` lazily imports `evaluate_readiness`; `coordinator._invoke_nag` lazily imports `_render_nag_if_needed`.
- **R2**: Subtle behavior shift in the moved nag call. **Mitigation**: `_invoke_nag` does nothing but call the existing function with the same `ctx`. WP02 and WP03 verify under tests.
- **R3**: `ctx.obj` contention with the existing `compat_plan_result` writer. **Mitigation**: distinct keys; `_write_cached` never replaces a non-dict `ctx.obj`.
- **R4**: `_derive_output_policy` precedence drift (MACHINE_OUTPUT must beat NON_INTERACTIVE). **Mitigation**: WP02 row 4/5 asserts MACHINE_OUTPUT for `--json` / `--quiet` even when other suppression conditions are also active.

## Reviewer Guidance

- Read `data-model.md` first; confirm enum values, field names, and types match exactly.
- Confirm the `callback()` diff in `helpers.py` is minimal — two lines added (the import + the call), a block of explanatory comment, one line removed (the old `_render_nag_if_needed(ctx)` call).
- Confirm both `_auth_recovery` and `_render_nag_if_needed` imports inside `coordinator.py` are lazy (function-scope) or grep-marked (`# WS2: auth probe wiring`); the only module-scope cross-package import is `detect_logged_out_with_connected_teamspace` which is needed for mypy --strict signal.
- Confirm `_invoke_nag` calls `_render_nag_if_needed(ctx)` unconditionally — no pre-gate, no re-suppression check.
- Confirm `_derive_output_policy`'s precedence: MACHINE_OUTPUT > NON_INTERACTIVE > INTERACTIVE.

## Out of Scope

- Writing tests — WP02 (suppression matrix + caching) and WP03 (nag passthrough + final).
- Implementing the auth probe body — WS2 mission (#1094).
- Changing `_render_nag_if_needed` or `_should_suppress_nag` — both stay byte-identical (C-003, C-005).
- Implementing upgrade UX changes — WS3 mission (#1092).

## Activity Log

- 2026-05-22T10:38:41Z – claude:opus:python-pedro:implementer – shell_pid=62483 – Assigned agent via action command
