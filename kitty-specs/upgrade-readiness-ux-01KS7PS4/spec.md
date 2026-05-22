# Spec: Upgrade Readiness UX (WS3, issue #1092)

## Purpose

Convert the current print-and-move-on upgrade nag into a real UX:

1. Interactive prompt with four choices: **Upgrade now**, **Always keep me up to date**, **Not now**, **Never ask again**.
2. Snooze cadence per remote version: 24h → 48h → 7d. A new remote version resets the cadence.
3. Safe auto-upgrade gated on installer detection (pipx, brew, pip-user / pip-system, source). Unknown installer → guidance only, no mutation.
4. Hard guarantee: no prompt and no upgrade attempt in machine-output contexts (`--json`, `--quiet`, `--help`, `--version`, CI, non-TTY).
5. Hidden behind `is_saas_sync_enabled()` UNLESS the existing non-Teamspace upgrade nag already applies — preserve that legacy behavior byte-for-byte.

## In scope

- `src/specify_cli/readiness/coordinator.py` — extend the upgrade-nag invocation seam.
- `src/specify_cli/compat/cache.py` — extend `NagCacheRecord` with snooze + preference fields (backward read-compat with legacy entries).
- `src/specify_cli/compat/_detect/install_method.py` — already exists; reuse via a new `is_safe_for_auto_upgrade()` helper colocated.
- New helper module `src/specify_cli/readiness/upgrade_ux.py`: cadence math, prompt state machine, preference resolution.
- Tests under `tests/readiness/` and `tests/specify_cli/compat/`.

## Out of scope

- Auth readiness (Mission C, issue #1094).
- Tracker alignment (Mission E).
- Docs (Mission F).
- SaaS-side changes.
- Implementing a new package manager.
- Changing the `spec-kitty upgrade` command's CLI contract.

## Acceptance criteria

1. `NagCacheRecord` extends to carry: `remote_version_seen` (anchors cadence), `snooze_step` (`"24h" | "48h" | "7d"` or `None`), `snoozed_until` (datetime or None), `always_upgrade` (bool), `never_ask` (bool). Old cache files load without crash; missing keys default to safe values.
2. Snooze cadence per remote version: first "Not now" → 24h, second → 48h, subsequent → 7d. A new `remote_version_seen` resets `snooze_step` to None and clears `snoozed_until`.
3. Four prompt choices map to NagCache mutations:
   - **Upgrade now** → invoke `spec-kitty upgrade --yes` via subprocess if installer is safe; otherwise print guidance.
   - **Always keep me up to date** → set `always_upgrade=True`. Subsequent invocations auto-upgrade if safe; otherwise nag with guidance.
   - **Not now** → advance snooze step.
   - **Never ask again** → set `never_ask=True`; suppress the prompt indefinitely until a new remote version is seen.
4. New env keys (no new pip deps):
   - `SPEC_KITTY_UPGRADE_AUTO=1` — alias for "always keep me up to date" (config-by-env escape hatch).
   - `SPEC_KITTY_UPGRADE_NEVER_ASK=1` — alias for "never ask again".
   - `SPEC_KITTY_UPGRADE_DISABLED=1` — fully suppress the upgrade nag and prompt (internal/CI escape hatch).
5. Installer-safety helper `is_safe_for_auto_upgrade(method: InstallMethod) -> bool` returns `True` for `PIPX`, `BREW`, `PIP_USER`, `PIP_SYSTEM`. Returns `False` for `SOURCE`, `SYSTEM_PACKAGE`, `UNKNOWN`.
6. Prompt and auto-upgrade MUST NOT run when `_should_suppress_nag()` would suppress (this is the canonical gate; do not duplicate logic).
7. `evaluate_readiness()` invokes the new UX path only when (a) `is_saas_sync_enabled()` is true OR (b) the existing legacy nag would have fired (i.e. `compat_plan(...).decision == ALLOW_WITH_NAG`).
8. Existing `spec-kitty upgrade` CLI contract is unchanged.

## Test matrix

- Four-choice unit tests (one per choice → expected NagCache mutation).
- Cadence per remote version: 24h → 48h → 7d → new version resets to None.
- Suppression matrix: `--json`, `--quiet`, `--help`, `--version`, `CI=1`, non-TTY each separately suppress prompt and auto-upgrade.
- Unknown installer + "Upgrade now" → emit guidance, no subprocess call, no mutation.
- Hosted-off + no legacy nag → no prompt path executes.
- Hosted-off + legacy nag triggers → existing render path preserved byte-for-byte.
- "Never ask again" persists across invocations.
- Backward read-compat: legacy `NagCacheRecord` JSON (only the original five fields) loads cleanly with defaults.

## Non-functional

- No new pip deps.
- No SaaS DB / queue / readiness mutation.
- Auto-upgrade subprocess uses the already-installed `spec-kitty upgrade --yes`; never installs new tooling.
- Pure functions where possible; injectable clock + injectable installer detector for testability.
