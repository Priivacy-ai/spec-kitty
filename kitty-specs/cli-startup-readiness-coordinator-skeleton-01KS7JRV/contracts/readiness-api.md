# Contract: `specify_cli.readiness` public API surface

Stability tier: **mission-internal seam**. WS2 (auth probe wiring) will widen the API; this mission only commits to:

- Symbol names listed below.
- The `ReadinessResult` field names listed in `data-model.md`.
- The two `AuthStatus` values shipped by this mission (`NOT_CHECKED`, `DISABLED`).

WS2 MAY add `AuthStatus` values without breaking this contract. WS2 MAY add `ReadinessResult` fields with defaults; existing fields MUST NOT be removed or renamed.

---

## Symbols exported from `specify_cli.readiness`

```python
from specify_cli.readiness import (
    AuthStatus,
    OutputPolicy,
    ReadinessResult,
    evaluate_readiness,
    get_readiness,
)
```

### `evaluate_readiness(ctx: typer.Context) -> ReadinessResult`

**Purpose**: Entry point for the root CLI callback. Computes (or returns the cached) readiness result.

**Contract**:
- MUST be safe to call multiple times with the same `ctx`. The second call returns the cached result without re-running any logic.
- MUST NOT raise. Any internal exception is swallowed; the function returns `_NOOP_DISABLED`.
- MUST NOT perform network I/O.
- MUST NOT mutate SaaS DB, queue, or readiness counters.
- MAY mutate `ctx.obj` per the `ctx.obj` Key Contract in `data-model.md`.
- MAY call `_render_nag_if_needed(ctx)` exactly once (under both enabled and disabled paths), preserving its existing behavior.

**Postconditions**:
- Returns a `ReadinessResult`.
- If `ctx.obj` is `None` or a dict, `ctx.obj["readiness"]` is set to the returned result.

### `get_readiness(ctx: typer.Context) -> ReadinessResult`

**Purpose**: Accessor for subcommand handlers.

**Contract**:
- MUST NOT raise.
- MUST NOT re-run `evaluate_readiness`.
- Returns `ctx.obj["readiness"]` if reachable; else returns `_NOOP_DISABLED`.

### `ReadinessResult` (frozen dataclass)

See `data-model.md`. Public fields are `enabled`, `ran`, `output_policy`, `auth_status`, `nag_invoked`.

### `OutputPolicy` (StrEnum)

Values: `INTERACTIVE`, `NON_INTERACTIVE`, `MACHINE_OUTPUT`. See `data-model.md`.

### `AuthStatus` (StrEnum)

Values shipped in this mission: `NOT_CHECKED`, `DISABLED`. See `data-model.md` for reserved future values.

---

## Backward-compatibility commitments

- The five symbols exported by `specify_cli.readiness.__init__` are stable seam names. Renames require a mission-level deprecation.
- The `ReadinessResult` field names are stable. Field additions allowed; removals require a mission-level deprecation.
- The string values of `OutputPolicy` (`"interactive"`, `"non_interactive"`, `"machine_output"`) are stable for any downstream consumer that serializes the enum.
- The string values of `AuthStatus` (`"not_checked"`, `"disabled"`) are stable.

---

## Out-of-contract behavior

The following are explicit non-commitments in this mission:

- `_NOOP_DISABLED` is a module-private sentinel. Subcommands MUST NOT compare results by identity to `_NOOP_DISABLED`; they MUST inspect the fields.
- The order in which `_render_nag_if_needed` and `_evaluate_uncached`'s other internal steps execute is not part of the contract. Tests assert behavior, not order.
- Internal helpers (`_evaluate_uncached`, `_derive_output_policy`, `_invoke_nag`, `_read_cached`, `_write_cached`) are NOT exported.
