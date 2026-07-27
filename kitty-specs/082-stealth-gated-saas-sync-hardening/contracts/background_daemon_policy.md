# Contract: Background Daemon Policy and Intent Gate

**Modules**:
- `src/specify_cli/sync/config.py` (extended)
- `src/specify_cli/sync/daemon.py` (extended)

**Stability**: Internal CLI surface. The TOML key shape is **operator-visible** and therefore stable.

---

## Configuration

### TOML Key

**File**: `~/.spec-kitty/config.toml`

```toml
[sync]
server_url = "https://spec-kitty-dev.fly.dev"
max_queue_size = 100000
background_daemon = "auto"   # "auto" | "manual"
```

| Key | Type | Default | Required | Description |
|---|---|---|---|---|
| `[sync].background_daemon` | `"auto"` \| `"manual"` | `"auto"` | no | Operator policy for whether commands that legitimately need hosted sync may auto-start the background daemon. |

**Loader behavior** (`src/specify_cli/sync/config.py`):
- Missing key → default `AUTO` (preserves current behavior).
- Empty string → reject with config error during load.
- Unknown value (e.g., `"sometimes"`) → log a one-line warning to stderr, fall back to `AUTO`.
- Case-insensitive parsing (`"AUTO"`, `"Manual"` accepted).

### `BackgroundDaemonPolicy` Enum

```python
class BackgroundDaemonPolicy(str, Enum):
    AUTO   = "auto"
    MANUAL = "manual"
```

---

## Intent Gate

### `DaemonIntent` Enum

```python
class DaemonIntent(str, Enum):
    LOCAL_ONLY      = "local_only"
    REMOTE_REQUIRED = "remote_required"
```

### `ensure_sync_daemon_running` Signature

```python
def ensure_sync_daemon_running(
    *,
    intent: DaemonIntent,
    config: SyncConfig | None = None,
) -> DaemonStartOutcome: ...
```

- `intent` is **mandatory and keyword-only**. There is no default.
- `config` defaults to a freshly loaded `SyncConfig` if not supplied (matches existing pattern).

### Decision Matrix

| `is_saas_sync_enabled()` | `intent` | `policy` | `started` | `skipped_reason` |
|---|---|---|---|---|
| `False` | any | any | `False` | `"rollout_disabled"` |
| `True` | `LOCAL_ONLY` | any | `False` | `"intent_local_only"` |
| `True` | `REMOTE_REQUIRED` | `MANUAL` | `False` | `"policy_manual"` |
| `True` | `REMOTE_REQUIRED` | `AUTO` | `True` (on success) | `None` |
| `True` | `REMOTE_REQUIRED` | `AUTO` | `False` | `"start_failed: <reason>"` |

### `DaemonStartOutcome`

See [data-model.md §8](../data-model.md). Frozen dataclass; consumers MUST treat it as a value.

---

## Caller Audit (R-005)

The following are the **only** call sites permitted to invoke `ensure_sync_daemon_running()` after this mission. Each is updated to pass an explicit `intent`:

| File | Call site purpose | New `intent` |
|---|---|---|
| `src/specify_cli/dashboard/server.py` | Dashboard process startup | `LOCAL_ONLY` |
| `src/specify_cli/dashboard/handlers/api.py` (read endpoints) | Returning local snapshot data | `LOCAL_ONLY` |
| `src/specify_cli/dashboard/handlers/api.py` (explicit "sync now" endpoint) | User-initiated remote sync from dashboard | `REMOTE_REQUIRED` |
| `src/specify_cli/sync/events.py` (event upload path) | Upload pending events to SaaS | `REMOTE_REQUIRED` |
| `src/specify_cli/cli/commands/tracker.py` (`sync pull`, `sync push`, `sync run`, `sync publish`) | Direct user request | `REMOTE_REQUIRED` |

**No other module** may call `ensure_sync_daemon_running()` without being added to this list and the corresponding test in `tests/sync/test_daemon_intent_gate.py`. A grep test in CI prevents drift.

---

## Manual-Mode CLI Behavior

When `policy_manual` blocks an otherwise-`REMOTE_REQUIRED` call from a CLI command:

- The command exits with code `0` (this is not an error — the operator chose this).
- It prints to stdout (stable wording, asserted by tests):

  > Background sync is in manual mode (`[sync].background_daemon = "manual"`).
  > Run `spec-kitty sync run` to perform a one-shot remote sync.

When `policy_manual` blocks a dashboard handler call:
- The handler logs the skip at INFO level with `skipped_reason="policy_manual"`.
- It does NOT crash the request.
- The dashboard UI surfaces "manual mode" in its status panel (best-effort; not gated by this mission).

---

## Test Requirements

`tests/sync/test_config_background_daemon.py`:
- Missing key → `AUTO` default.
- `"auto"` / `"AUTO"` → `AUTO`.
- `"manual"` / `"Manual"` → `MANUAL`.
- `"banana"` → warning + `AUTO`.
- Empty string → config load error.

`tests/sync/test_daemon_intent_gate.py`:
- Every row of the decision matrix above is asserted.
- Mandatory `intent=` keyword: a TypeError is raised if a caller omits it (regression guard).
- Audit guard: a directory grep test asserts no other module calls `ensure_sync_daemon_running()` outside the audit list.
- Both rollout-on and rollout-off modes exercised.

`tests/agent/cli/commands/test_tracker.py` (extended):
- `sync run` with `policy=MANUAL` exits 0 and prints the manual-mode message.
- `sync run` with `policy=AUTO` reaches the existing daemon path.
