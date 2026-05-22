# Plan: Upgrade Readiness UX

## Architecture

### Module layout

```
src/specify_cli/
  readiness/
    coordinator.py       (extend: route upgrade UX through _invoke_nag())
    upgrade_ux.py        (new: cadence math, preference resolution, prompt state machine)
  compat/
    cache.py             (extend: NagCacheRecord schema; backward read-compat)
    _detect/
      install_method.py  (extend: is_safe_for_auto_upgrade() helper)
```

### Data flow

```
callback() → evaluate_readiness(ctx)
    └─→ _evaluate_uncached(ctx)
        ├─ if is_saas_sync_enabled():
        │   └─ _invoke_upgrade_ux(ctx)
        │       └─ run_upgrade_ux(ctx, suppressed=_should_suppress_nag())
        │           ├─ if suppressed: return (machine-output safe)
        │           ├─ read NagCacheRecord
        │           ├─ resolve env preferences → effective preference
        │           ├─ if never_ask & remote unchanged: return
        │           ├─ if snoozed_until > now: return
        │           ├─ compat_plan(invocation) → if not ALLOW_WITH_NAG: return
        │           ├─ if always_upgrade & is_safe_for_auto_upgrade(): try auto-upgrade
        │           └─ else: prompt 4-choice → mutate cache + maybe upgrade
        └─ else:
            └─ _invoke_nag(ctx)  ← existing legacy path preserved byte-for-byte
```

### Schema extension (NagCacheRecord)

Add five optional fields (all default to None / False at read-time when absent in the JSON, so old files load cleanly):

| Field | Type | Default | Meaning |
|---|---|---|---|
| `remote_version_seen` | `str \| None` | None | Anchors cadence; mismatch resets snooze_step + snoozed_until |
| `snooze_step` | `Literal["24h","48h","7d"] \| None` | None | Current cadence position |
| `snoozed_until` | `datetime \| None` | None | UTC; while now < snoozed_until, suppress prompt |
| `always_upgrade` | `bool` | False | Auto-upgrade on every invocation when installer is safe |
| `never_ask` | `bool` | False | Suppress the prompt until a new remote version is seen |

`NagCacheRecord.from_dict()` MUST accept legacy JSON missing all five new fields and assign defaults (do NOT raise). This is the backward-compat guarantee.

### Cadence state machine

```
[None] --not-now--> 24h (snoozed_until = now + 24h)
[24h]  --not-now--> 48h (snoozed_until = now + 48h)
[48h]  --not-now--> 7d  (snoozed_until = now + 7d)
[7d]   --not-now--> 7d  (snoozed_until = now + 7d)  -- ceiling

[any]  --new remote version--> None (cleared)
```

### Installer-safety whitelist

```python
_SAFE_AUTO_UPGRADE_METHODS = frozenset({
    InstallMethod.PIPX,
    InstallMethod.BREW,
    InstallMethod.PIP_USER,
    InstallMethod.PIP_SYSTEM,
})
```

`SOURCE`, `SYSTEM_PACKAGE`, `UNKNOWN` → guidance only.

### Auto-upgrade execution

When the user picks "Upgrade now" or has `always_upgrade=True` AND installer is safe:

- `subprocess.run(["spec-kitty", "upgrade", "--yes"], check=False, timeout=300)`.
- On non-zero exit: print failure guidance, leave cache state alone.
- On success: clear `snoozed_until` and `snooze_step`.

### Env-driven preferences

Resolved at `run_upgrade_ux()` entry:

- `SPEC_KITTY_UPGRADE_DISABLED=1` → return immediately.
- `SPEC_KITTY_UPGRADE_AUTO=1` → treat as always_upgrade=True for this invocation.
- `SPEC_KITTY_UPGRADE_NEVER_ASK=1` → treat as never_ask=True for this invocation.

Truthy parsing matches `SPEC_KITTY_ENABLE_SAAS_SYNC`.

### Dependencies

No new pip deps. Reuses `compat.cache`, `compat.planner`, `compat._detect.install_method`, `cli.helpers._should_suppress_nag`, stdlib.

### Test strategy

- Unit tests for `upgrade_ux` module (cadence, preference resolution, installer-safety).
- Schema tests for `NagCacheRecord` (round-trip + legacy backward compat).
- Coordinator integration tests in `tests/readiness/` covering:
  - Hosted-off + no legacy nag → silent.
  - Hosted-off + legacy nag → existing path preserved.
  - Hosted-on suppression matrix (--json/--quiet/--help/--version/CI/non-TTY).
  - Hosted-on always_upgrade safe installer → subprocess fires.
  - Hosted-on always_upgrade UNKNOWN installer → guidance only.
  - never_ask persists.
  - Four-choice prompt mutations.
