# Contract: ProfileInvocationExecutor Boundary

**Mission**: `runtime-mission-execution-extraction-01KPDYGW`
**FR**: FR-009
**Status**: Boundary documentation — Phase 4 shipped; this is a call-boundary reference, not a new scaffold.

---

## Status

`ProfileInvocationExecutor` was fully implemented in mission `profile-invocation-runtime-audit-trail-01KPQRX2` (merged 2026-04-21). It lives at:

```
src/specify_cli/invocation/executor.py
```

This mission does NOT move, rewrite, or re-implement the executor. It documents the canonical boundary so `src/runtime/` code can call it correctly.

## Canonical Import Path

```python
# From src/runtime/ code:
from specify_cli.invocation.executor import ProfileInvocationExecutor
```

Or via the seam alias (preferred — documents the boundary):

```python
from runtime.seams.profile_invocation_executor import ProfileInvocationExecutor
```

The seam alias at `src/runtime/seams/profile_invocation_executor.py` is:

```python
from specify_cli.invocation.executor import ProfileInvocationExecutor
__all__ = ["ProfileInvocationExecutor"]
```

## Public Interface (summary — canonical source is `invocation/executor.py`)

```python
class ProfileInvocationExecutor:
    """Single execution primitive for profile-governed invocations."""

    def __init__(
        self,
        repo_root: Path,
        glossary_chokepoint: GlossaryChokepoint | None = None,
    ) -> None: ...

    def invoke(
        self,
        request: str,
        profile_id: str | None = None,
        action: str | None = None,
    ) -> InvocationResult: ...
```

(The full type signatures live in `invocation/executor.py`. Do not duplicate them here — read the source.)

## Dependency Direction

```
src/runtime/  →  specify_cli.invocation.executor  (runtime calls invocation)
```

`specify_cli.invocation` does NOT call back into `src/runtime/`. This is a one-way service boundary.

## Boundary Rule (enforced by WP07)

Runtime may call `invocation.executor`. Runtime must not own or mutate `invocation/`. The pytestarch rule in WP07 asserts that `runtime` does not import from `specify_cli.cli.*` — `specify_cli.invocation.*` is permitted because `invocation/` is not a CLI module.

## Call Sites

During WP01 T001 or WP05 T022, the implementer audits whether any current `runtime_bridge.py` or CLI adapter code bypasses `invocation/` and calls profile-related logic directly. The result of that audit goes into `research.md` as an addendum. If bypass call sites are found, they must route through `ProfileInvocationExecutor.invoke()` before WP05 is marked done.
