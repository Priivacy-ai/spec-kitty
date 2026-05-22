# Data Model: CLI Startup Readiness Coordinator Skeleton

This document defines the public data types introduced by `src/specify_cli/readiness/`.

---

## `OutputPolicy` (StrEnum)

Three-bucket suppression classification.

| Value | Semantics | Use cases |
|---|---|---|
| `INTERACTIVE` | TTY, no suppression conditions active. Prompts and rich rendering are permitted. | Default human use from a terminal. |
| `NON_INTERACTIVE` | Non-TTY OR `CI=1` OR `--help` / `-h` / `--version` / `-v`. No prompts; stable single-line stderr is permitted. | Scripted use, CI logs, help/version commands. |
| `MACHINE_OUTPUT` | `--json` OR `--quiet`. No prompts; stdout must remain parseable; stderr noise minimized. | JSON pipes, `--quiet` automation. |

**Precedence**: `MACHINE_OUTPUT` > `NON_INTERACTIVE` > `INTERACTIVE`. If `--json` and `--help` are both in argv, the policy is `MACHINE_OUTPUT`.

**Invariant**: The policy is computed exactly once per `evaluate_readiness` call from the same primitive signals `_should_suppress_nag` consults, and cached on `ReadinessResult.output_policy`.

---

## `AuthStatus` (StrEnum)

Coordinator's record of the user's Teamspace-auth state. This mission ships two values; WS2 will add more.

| Value | This-mission semantics | Future (WS2) semantics |
|---|---|---|
| `NOT_CHECKED` | Hosted mode enabled but the auth probe is not exercised yet. Marker for the WS2 seam. | (still valid — used when the probe is intentionally skipped) |
| `DISABLED` | Hosted mode is off (`is_saas_sync_enabled() == False`). The probe was not attempted. | (unchanged) |

**Reserved future values (DO NOT ship in this mission)**: `AUTHENTICATED`, `LOGGED_OUT_ON_CONNECTED_TEAMSPACE`, `LOGGED_OUT_LOCAL_ONLY`, `PROBE_ERROR`.

**Invariant**: When `ReadinessResult.enabled == False`, `auth_status == DISABLED`. When `enabled == True`, `auth_status == NOT_CHECKED` (this mission); WS2 will widen.

---

## `ReadinessResult` (frozen dataclass)

The cached result returned by `evaluate_readiness` and read by `get_readiness`.

```python
@dataclass(frozen=True, slots=True)
class ReadinessResult:
    enabled: bool
    ran: bool
    output_policy: OutputPolicy
    auth_status: AuthStatus
    nag_invoked: bool
```

| Field | Type | Semantics |
|---|---|---|
| `enabled` | `bool` | `is_saas_sync_enabled()` at evaluation time. |
| `ran` | `bool` | `True` iff the coordinator's enabled-path logic ran. Equivalent to `enabled and not internal_exception`. |
| `output_policy` | `OutputPolicy` | The 3-bucket suppression classification at evaluation time. |
| `auth_status` | `AuthStatus` | The (stubbed this mission) auth state. |
| `nag_invoked` | `bool` | `True` iff `_render_nag_if_needed(ctx)` was called during this evaluation. The flag does NOT track whether the nag actually rendered output — that's an internal detail of `_render_nag_if_needed`. |

**Invariants**:
- Frozen. Subcommands MUST NOT attempt to mutate fields; doing so raises `FrozenInstanceError`.
- Slots. No `__dict__`; adding fields requires editing the dataclass.
- `nag_invoked == True` whenever the coordinator reached the nag-invocation step (both enabled and disabled paths). `nag_invoked == False` iff the coordinator returned the `_NOOP_DISABLED` sentinel from the exception path.

---

## `_NOOP_DISABLED` (module-level sentinel)

Module-level constant returned from:
- The exception-swallowing path inside `evaluate_readiness`.
- `get_readiness(ctx)` when no cached result is reachable (`ctx.obj` is `None`, not a dict, or missing the `"readiness"` key).

```python
_NOOP_DISABLED: ReadinessResult = ReadinessResult(
    enabled=False,
    ran=False,
    output_policy=OutputPolicy.NON_INTERACTIVE,
    auth_status=AuthStatus.DISABLED,
    nag_invoked=False,
)
```

**Rationale**: `_NOOP_DISABLED` represents "no readiness work was done and no output policy could be derived safely". Subcommands should treat it as "fall back to pre-readiness behavior". Choosing `output_policy = NON_INTERACTIVE` as the default biases toward suppression (no prompts) — the safest posture when the coordinator couldn't decide.

---

## `ctx.obj` Key Contract

| Key | Writer | Reader | Type |
|---|---|---|---|
| `"readiness"` | `evaluate_readiness` | `get_readiness` (and any subcommand consuming readiness state) | `ReadinessResult` |
| `"compat_plan_result"` | `_render_nag_if_needed` (existing, unchanged) | existing subcommands that consult the planner result | `CompatPlanResult` |

The coordinator MUST coexist with the existing `"compat_plan_result"` writer; both keys live side by side in `ctx.obj` as a dict.

**Invariants**:
- If `ctx.obj is None`, the coordinator sets `ctx.obj = {}` before writing.
- If `ctx.obj` is a dict, the coordinator writes the key and leaves other keys untouched.
- If `ctx.obj` is a non-dict, non-None object (defensive), the coordinator does NOT replace it. The result is computed but not cached; `get_readiness` then returns `_NOOP_DISABLED`.

---

## Public API Module Layout

```python
# src/specify_cli/readiness/__init__.py
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

---

## State Transitions

There is no persistent state in this data model. `ReadinessResult` is immutable; the only "transition" is `None → ReadinessResult` when `evaluate_readiness` writes its cache. Subsequent calls return the cached instance unchanged.

---

## Validation Rules

- `evaluate_readiness(ctx)` always returns a `ReadinessResult`. Never `None`, never raises.
- `get_readiness(ctx)` always returns a `ReadinessResult`. Never `None`, never raises, never re-runs the coordinator.
- `evaluate_readiness` invoked twice with the same `ctx` (when `ctx.obj` is dict-storable) returns the same `ReadinessResult` instance (object identity).
