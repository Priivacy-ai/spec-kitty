# Phase 1 Data Model — 082 Stealth-Gated SaaS Sync Hardening

**Date**: 2026-04-11
**Status**: Complete

This document defines the entities, enums, and dataclasses introduced or modified by this mission. All types live in the new `src/specify_cli/saas/` package or the existing `src/specify_cli/sync/config.py`. The model is purely in-memory — there is no new persistence beyond a single new TOML key on the existing `~/.spec-kitty/config.toml`.

---

## 1. `is_saas_sync_enabled` (Function)

**Module**: `src/specify_cli/saas/rollout.py` (new)
**Signature**:
```python
def is_saas_sync_enabled() -> bool: ...
```
**Behavior**:
- Returns `True` iff the environment variable `SPEC_KITTY_ENABLE_SAAS_SYNC` is set to a truthy value (`"1"`, `"true"`, `"yes"`, case-insensitive).
- Returns `False` for all other values, for empty strings, and when the variable is unset.

**Companion**:
```python
def saas_sync_disabled_message() -> str: ...
```
Returns the canonical disabled-mode message ("Hosted SaaS sync is not enabled on this machine. Set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` to opt in.")

**Backwards-compatibility shims** (modified, not new):
- `src/specify_cli/tracker/feature_flags.py` — re-exports `is_saas_sync_enabled` and `saas_sync_disabled_message` from `specify_cli.saas.rollout`.
- `src/specify_cli/sync/feature_flags.py` — same.

**Validation**:
- mypy --strict-clean. No `Any`. No exceptions raised.

---

## 2. `ReadinessState` (Enum)

**Module**: `src/specify_cli/saas/readiness.py` (new)

```python
from enum import Enum

class ReadinessState(str, Enum):
    ROLLOUT_DISABLED        = "rollout_disabled"
    MISSING_AUTH            = "missing_auth"
    MISSING_HOST_CONFIG     = "missing_host_config"
    HOST_UNREACHABLE        = "host_unreachable"
    MISSING_MISSION_BINDING = "missing_mission_binding"
    READY                   = "ready"
```

**Ordering**: The evaluator checks states in declaration order — cheapest and most consequential first. The first failing state short-circuits.

**Stability contract**: Member names and string values are part of the contract surface (logged, asserted in tests). Adding new members is allowed (additive); removing or renaming requires a follow-up mission.

---

## 3. `ReadinessResult` (Dataclass)

**Module**: `src/specify_cli/saas/readiness.py` (new)

```python
from dataclasses import dataclass, field
from typing import Mapping

@dataclass(frozen=True)
class ReadinessResult:
    state: ReadinessState
    message: str
    next_action: str | None
    details: Mapping[str, str] = field(default_factory=dict)

    @property
    def is_ready(self) -> bool:
        return self.state is ReadinessState.READY
```

**Field semantics**:

| Field | Required | Description |
|---|---|---|
| `state` | yes | Discrete enum member (see §2). |
| `message` | yes | Human-readable description of the failing prerequisite. **Must name the prerequisite explicitly** (NFR-002). |
| `next_action` | no | Single concrete next step the user should take (e.g., "Run `spec-kitty auth login`"). `None` only when `state == READY`. |
| `details` | no | Optional bag of structured details (e.g., `{"host": "https://...", "probe_status": "timeout"}`). Used for logs and structured output, never as a substitute for `message`. |

**Validation rules**:
- If `state == READY`, `next_action` MUST be `None` and `message` SHOULD be the empty string.
- If `state != READY`, `next_action` MUST be a non-empty string.
- The dataclass is frozen — results are values, not handles.

---

## 4. `evaluate_readiness` (Function)

**Module**: `src/specify_cli/saas/readiness.py` (new)

```python
def evaluate_readiness(
    *,
    repo_root: Path,
    feature_slug: str | None = None,
    require_mission_binding: bool = False,
    probe_reachability: bool = False,
) -> ReadinessResult: ...
```

**Note**: `evaluate_readiness` does **not** take a `SyncConfig` parameter. The authoritative SaaS host URL is `SPEC_KITTY_SAAS_URL` (decision D-5 in `src/specify_cli/auth/config.py`), obtained via `specify_cli.auth.config.get_saas_base_url()`. `SyncConfig.get_server_url()` exists in the codebase for legacy reasons but is not the source-of-truth for readiness.

**Behavior** (in declaration order, short-circuits on first failure):

1. **`ROLLOUT_DISABLED`** — `is_saas_sync_enabled() == False` → return immediately. No I/O performed.
2. **`MISSING_AUTH`** — call existing auth lookup (currently the implicit one used by `TrackerService`). If no token, return.
3. **`MISSING_HOST_CONFIG`** — call `specify_cli.auth.config.get_saas_base_url()`; if it raises `ConfigurationError` (because `SPEC_KITTY_SAAS_URL` is unset or empty), return. Otherwise capture the returned URL for use in steps 4 and 6.
4. **`HOST_UNREACHABLE`** — only if `probe_reachability=True`. Issue one HTTP `HEAD` against the URL captured in step 3 with a 2-second total budget. On any failure, return.
5. **`MISSING_MISSION_BINDING`** — only if `require_mission_binding=True`. Look up the binding for `feature_slug` (or the active feature in `repo_root`). If absent, return.
6. **`READY`** — return `ReadinessResult(state=READY, message="", next_action=None)`.

**Error handling**: Any unexpected exception inside the evaluator is caught and converted into `ReadinessResult(state=HOST_UNREACHABLE, ...)` with the exception type in `details["error"]` — readiness must never raise to its caller.

---

## 5. `BackgroundDaemonPolicy` (Enum)

**Module**: `src/specify_cli/sync/config.py` (modified)

```python
class BackgroundDaemonPolicy(str, Enum):
    AUTO   = "auto"
    MANUAL = "manual"
```

**Default**: `AUTO`.

**TOML key**: `[sync].background_daemon` in `~/.spec-kitty/config.toml`. Unknown values fall back to `AUTO` and emit a one-time warning to stderr (charter: actionable failures).

---

## 6. `SyncConfig` (Modified Class)

**Module**: `src/specify_cli/sync/config.py:12-70` (modified)

**Important**: `SyncConfig` is a regular Python **class**, not a `@dataclass`. It manages `~/.spec-kitty/config.toml` via on-demand getter/setter method pairs backed by a private `_load()` (reads via `toml.load`, returns `{}` on missing/invalid) and `_save()` (writes via `atomic_write`). Each getter re-reads the file; there is no cached in-memory state.

**Existing methods (unchanged):**
- `get_server_url() -> str` / `set_server_url(url: str) -> None` — `[sync].server_url` (hardcoded legacy default `https://spec-kitty-dev.fly.dev`; this URL is **not** consulted by the readiness evaluator — see §4 note on D-5 and `SPEC_KITTY_SAAS_URL`)
- `get_max_queue_size() -> int` / `set_max_queue_size(size: int) -> None` — `[sync].max_queue_size` (default `100_000`)

**New method pair (this mission):**
```python
def get_background_daemon(self) -> BackgroundDaemonPolicy: ...
def set_background_daemon(self, policy: BackgroundDaemonPolicy) -> None: ...
```

**`get_background_daemon` behavior**:
- Reads `config.get('sync', {}).get('background_daemon')` via `_load()`.
- Missing key → return `BackgroundDaemonPolicy.AUTO`.
- Non-empty string → `.strip().casefold()` → match against `BackgroundDaemonPolicy._value2member_map_` → return the member on success.
- Empty string → raise the module's existing config error type with message naming the key.
- Unknown value (e.g., `"banana"`) → emit one-line warning to stderr and return `BackgroundDaemonPolicy.AUTO`.

**`set_background_daemon` behavior**: mirrors `set_server_url` — load, mutate `config['sync']['background_daemon'] = policy.value`, save.

**Backwards compatibility**: Existing config files without the new key continue to load identically (missing key → `AUTO` preserves today's "auto-start when called" behavior).

---

## 7. `DaemonIntent` (Enum)

**Module**: `src/specify_cli/sync/daemon.py` (modified)

```python
class DaemonIntent(str, Enum):
    LOCAL_ONLY      = "local_only"
    REMOTE_REQUIRED = "remote_required"
```

**Purpose**: Mandatory keyword-only argument on `ensure_sync_daemon_running()` so every call site declares whether it actually needs hosted sync.

---

## 8. `DaemonStartOutcome` (Dataclass)

**Module**: `src/specify_cli/sync/daemon.py` (modified)

```python
@dataclass(frozen=True)
class DaemonStartOutcome:
    started: bool
    skipped_reason: str | None
    pid: int | None
```

**Possible shapes**:
| `started` | `skipped_reason` | `pid` | Meaning |
|---|---|---|---|
| `True` | `None` | int | Daemon is now running (newly started or already running) |
| `False` | `"intent_local_only"` | `None` | Caller did not request remote behavior; not started |
| `False` | `"policy_manual"` | `None` | `sync.background_daemon=manual` blocks auto-start |
| `False` | `"rollout_disabled"` | `None` | `SPEC_KITTY_ENABLE_SAAS_SYNC` is unset |
| `False` | `"start_failed: <reason>"` | `None` | Genuine startup failure (preserves current diagnostic surface) |

---

## 9. `ensure_sync_daemon_running` (Modified Function)

**Module**: `src/specify_cli/sync/daemon.py:150+` (modified)

**New signature**:
```python
def ensure_sync_daemon_running(
    *,
    intent: DaemonIntent,
    config: SyncConfig | None = None,
) -> DaemonStartOutcome: ...
```

**Decision matrix**:

| `is_saas_sync_enabled()` | `intent` | `policy` | Outcome |
|---|---|---|---|
| `False` | any | any | `DaemonStartOutcome(started=False, skipped_reason="rollout_disabled")` |
| `True` | `LOCAL_ONLY` | any | `DaemonStartOutcome(started=False, skipped_reason="intent_local_only")` |
| `True` | `REMOTE_REQUIRED` | `MANUAL` | `DaemonStartOutcome(started=False, skipped_reason="policy_manual")` |
| `True` | `REMOTE_REQUIRED` | `AUTO` | Existing start logic (`started=True` on success) |

**Caller audit** (R-005): three call sites updated, listed in research.md and enforced by `tests/sync/test_daemon_intent_gate.py`.

---

## 10. Public API of `src/specify_cli/saas/__init__.py`

**As-shipped in this mission (WP01 owns `__init__.py`):**

```python
from specify_cli.saas.rollout import (
    is_saas_sync_enabled,
    saas_sync_disabled_message,
)

__all__ = [
    "is_saas_sync_enabled",
    "saas_sync_disabled_message",
]
```

**Rationale**: WP01 and WP02 cannot share ownership of `__init__.py` under the finalize-tasks owned-files constraint. WP01 creates the package with the rollout-only export surface. WP02 ships `readiness.py` as a module alongside and callers import readiness via the module path:

```python
from specify_cli.saas.readiness import (
    ReadinessState,
    ReadinessResult,
    evaluate_readiness,
)
```

A future non-urgent cleanup mission can extend `__init__.py` to re-export readiness at the package root too — this is a minor ergonomics improvement, not a correctness concern.

`BackgroundDaemonPolicy`, `DaemonIntent`, and `DaemonStartOutcome` remain exported from their existing `sync/` package — they are daemon-side concerns and the `saas/` package does not need to know about them.

---

## State Machine Notes

There is **no persistent state machine**. `ReadinessResult` is computed on-demand and discarded — repeating the call is the canonical refresh. The only persistent state introduced by this mission is the single new `background_daemon` TOML key, which is operator-set, not transitioning.

The daemon itself already has a lifecycle (`DAEMON_STATE_FILE = SPEC_KITTY_DIR / "sync-daemon"`, `DAEMON_LOCK_FILE = SPEC_KITTY_DIR / "sync-daemon.lock"` — see `src/specify_cli/sync/daemon.py:30-32`); this mission does not change that lifecycle, only the conditions under which it is invoked.
