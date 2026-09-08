# Contract: SaaS Rollout Gate

**Version**: 3 (#3980, Team Kitty launch defaults — the default flipped from opt-in to opt-out; version 2 relocated the canonical home from `saas/rollout.py` to `core/saas_sync_config.py` [#2252])
**Module**: `src/specify_cli/core/saas_sync_config.py` (canonical home). `src/specify_cli/tracker/feature_flags.py` re-exports from here (the `saas/rollout.py` and `sync/feature_flags.py` shims died with their packages, issue #5).
**Stability**: Internal CLI surface, but **public to all of `src/specify_cli/`**. Treat as a stable internal contract.

**Provenance**: this is the live, self-contained version-3 contract for mission
`team-kitty-launch-defaults-01M1XJ4Y` (#3980). The version-2 record it supersedes
lives at `kitty-specs/082-stealth-gated-saas-sync-hardening/contracts/saas_rollout.md`
and stays byte-frozen there — `tests/architectural/test_archive_root_byte_identical.py`
(NFR-002) freezes every pre-existing file under `kitty-specs/` at the port base,
so a contract version bump is recorded as a NEW file in this mission's dossier,
never as an edit to the archived original (same pattern as
`kitty-specs/dispatch-dry-run-route-only-01M1HKV2/contracts/cli-dispatch-dry-run-output.md`).

---

## Functions

### `is_saas_sync_enabled() -> bool`

**Inputs**: None (reads process environment).

**Returns**: `True` unless the environment variable `SPEC_KITTY_ENABLE_SAAS_SYNC` explicitly opts out (launch default, #3980: **on**):

- Unset variable → `True`
- Empty / whitespace-only string → `True`
- `"1"`, `"true"`, `"yes"`, `"y"`, `"on"` (case-insensitive) → `True` (redundant confirmation)
- `"0"`, `"false"`, `"no"`, `"off"` → `False` (the opt-out)
- Any other non-empty value (e.g. `"banana"`) → `False`

**Side effects**: None. Pure function (modulo `os.environ` read).

**Performance**: O(1).

### `sync_active() -> bool`

**Returns**: `is_saas_sync_enabled() and not sync_kill_switch_active()` — the
process-wide kill switch is `SPEC_KITTY_SYNC_DISABLE` alone. `SPEC_KITTY_SYNC_MINIMAL_IMPORT`
no longer disarms sync; it is a deprecated alias of the moment-handler import gate
(`core.env.moment_handlers_disabled_reason`).

### `saas_sync_disabled_message() -> str`

**Inputs**: None.

**Returns**: A human-readable, one-line message explaining the rollout is off and how to re-enable it. Stable wording (asserted by tests):

> Hosted SaaS sync is disabled on this machine. Unset `SPEC_KITTY_ENABLE_SAAS_SYNC` (or set it to `1`) to re-enable it.

---

## Related environment names (#3980 launch table)

| Name | Role |
|---|---|
| `SPEC_KITTY_ENABLE_SAAS_SYNC` | opt-out only (`=0`); absent means on |
| `SPEC_KITTY_SAAS_URL` | dev/self-host override of the packaged default (`DEFAULT_HOSTED_SAAS_URL`, `auth/config.py`) |
| `SPEC_KITTY_SAAS_TOKEN`, `SPEC_KITTY_TEAM_SLUG` | service-token and scope overrides |
| `SPEC_KITTY_SYNC_DISABLE` | the single process-wide kill switch (`sync_active()`), nothing else |
| `SPEC_KITTY_SYNC_MINIMAL_IMPORT` | deprecated alias of the moment-handler gate, warns once |
| `SPEC_KITTY_NO_MOMENT_HANDLERS` | the moment-handler import gate (`status/adapters.py`) |
| `SPEC_KITTY_SKIP_PRE_REVIEW_GATE` | the pre-review regression gate's own opt-out (`agent/tasks_move_task.py`) |
| `SPEC_KITTY_SAAS_FANOUT_TIMEOUT` | unchanged, documented |

Post-launch, `SPEC_KITTY_SYNC_MINIMAL_IMPORT` and the deprecated `ENABLE`
spellings are removed from `core/env.py`, `core/secret_redaction.py`, and
`m_3_2_8_provision_kitty_env.py` (#3980 post-launch section).

---

## Backwards Compatibility Shims

The following modules continue to export `is_saas_sync_enabled` and `saas_sync_disabled_message`:

- `src/specify_cli/tracker/feature_flags.py`

All shims re-export the same function objects (identity preserved) and add **no behavior**. Any future change to the env-var contract is made once in `core/saas_sync_config.py`.

---

## Usage Contract for Callers

1. **CLI Typer registration** (`src/specify_cli/cli/commands/__init__.py`):
   - Registration of the tracker group is **unconditional**; the rollout gate
     is enforced at invocation time by `tracker.py`'s callback
     (`tracker_callback` / per-command checks), which print
     `saas_sync_disabled_message()` and exit 1 when the gate is off.

2. **Programmatic callers** (dashboard, sync events, readiness):
   - MUST call `is_saas_sync_enabled()` directly OR rely on `evaluate_readiness()` (which checks rollout first).
   - MUST NOT cache the result across process boundaries — the env var is read each call by design.

3. **Tests**:
   - Use `monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "0")` to simulate the
     disabled state (deleting the variable no longer disables it — the default
     is on) / `monkeypatch.setenv(..., "1")` for the enabled state.
   - The autouse fixture at `tests/conftest.py` sets the gate ON by default; dual-mode tests opt out explicitly.
   - The deterministic CI producer (`.github/workflows/ci.yml`) pins its own
     ambient environment to `SPEC_KITTY_ENABLE_SAAS_SYNC=0` (and no URL) so
     the suite never depends on the default or on runner ambient state.

---

## Test Requirements

- The rollout-gate test file MUST cover at minimum:
  - Unset env var → `True`
  - Empty string → `True`
  - `"1"` / `"true"` / `"TRUE"` / `"yes"` / `"on"` → `True`
  - `"0"` / `"false"` / `"off"` → `False`
  - Garbage values (`"banana"`) → `False`
  - `sync_active()` is `False` when `SPEC_KITTY_SYNC_DISABLE` is truthy, and is
    NOT disarmed by `SPEC_KITTY_SYNC_MINIMAL_IMPORT` alone
  - The disabled message wording is byte-for-byte stable
- mypy --strict clean
