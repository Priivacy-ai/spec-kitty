# Contract: SaaS Rollout Gate

**Module**: `src/specify_cli/saas/rollout.py`
**Stability**: Internal CLI surface, but **public to all of `src/specify_cli/`**. Treat as a stable internal contract.

---

## Functions

### `is_saas_sync_enabled() -> bool`

**Inputs**: None (reads process environment).

**Returns**: `True` iff the environment variable `SPEC_KITTY_ENABLE_SAAS_SYNC` is set to a truthy value:
- `"1"`
- `"true"` (case-insensitive)
- `"yes"` (case-insensitive)
- `"on"` (case-insensitive)

Returns `False` for:
- Unset variable
- Empty string
- `"0"`, `"false"`, `"no"`, `"off"`
- Any other value

**Side effects**: None. Pure function (modulo `os.environ` read).

**Performance**: O(1).

---

### `saas_sync_disabled_message() -> str`

**Inputs**: None.

**Returns**: A human-readable, one-line message explaining the rollout is off and how to opt in. Stable wording (asserted by tests):

> Hosted SaaS sync is not enabled on this machine. Set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` to opt in.

---

## Backwards Compatibility Shims

The following modules continue to export `is_saas_sync_enabled` and `saas_sync_disabled_message`:

- `src/specify_cli/tracker/feature_flags.py`
- `src/specify_cli/sync/feature_flags.py`

Both shims re-export from `specify_cli.saas.rollout` and add **no behavior**. Any future change to the env-var contract is made once in `saas/rollout.py`.

---

## Usage Contract for Callers

1. **CLI Typer registration** (`src/specify_cli/cli/commands/__init__.py:37-40, 71-72`):
   - MUST call `is_saas_sync_enabled()` at module import time.
   - MUST conditionally import the tracker module and conditionally `app.add_typer(tracker_module.app, name="tracker")`.
   - MUST NOT register the tracker group when the gate is off, even with a runtime guard, so customers' `--help` output never lists it.

2. **Programmatic callers** (daemon, dashboard, sync events):
   - MUST call `is_saas_sync_enabled()` directly OR rely on `evaluate_readiness()` (which checks rollout first).
   - MUST NOT cache the result across process boundaries — the env var is read each call by design.

3. **Tests**:
   - Use `monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")` / `monkeypatch.delenv(...)`.
   - The autouse fixture at `tests/conftest.py:57-60` sets the gate ON by default; dual-mode tests opt out explicitly.

---

## Test Requirements

- `tests/saas/test_rollout.py` MUST cover at minimum:
  - Unset env var → `False`
  - Empty string → `False`
  - `"1"` → `True`
  - `"0"` → `False`
  - `"true"` / `"TRUE"` / `"True"` → `True`
  - `"yes"` / `"on"` → `True`
  - Garbage values (`"banana"`) → `False`
  - The disabled message wording is byte-for-byte stable
- mypy --strict clean
