# Contract — Upgrade Probe and Notifier

**Mission**: `quality-devex-hardening-3-2-01KRJGKH`
**Requirement**: FR-007 (#740)
**Modules**: `src/specify_cli/core/upgrade_probe.py` + `src/specify_cli/core/upgrade_notifier.py` (both new)
**Tactic**: [`secure-design-checklist`](../../../src/doctrine/tactics/shipped/secure-design-checklist.tactic.yaml) — applied to the new external surface (PyPI probe)

## Purpose

Surface "no upgrade available" / "you are on the latest supported version" / "build channel with no upgrade path" information to the user without:

- blocking the CLI on network IO,
- emitting noisy notifications on every command invocation,
- breaking the existing hard CLI/project version-mismatch error path.

## External surface

### PyPI probe endpoint

- **URL**: `https://pypi.org/pypi/spec-kitty-cli/json` (PyPI's standard JSON metadata endpoint).
- **Method**: `GET`.
- **Auth**: none.
- **Timeout**: 2 seconds (hard cap). Any timeout, connection error, or non-2xx response resolves to `UpgradeChannel.UNKNOWN`.
- **User-Agent**: `spec-kitty-cli/<version> (https://github.com/Priivacy-ai/spec-kitty)`.

### Response handling

PyPI's `/pypi/<package>/json` returns:

```json
{
  "info": { "version": "3.1.8", ... },
  "releases": { "0.1.0": [...], ..., "3.1.8": [...] }
}
```

The probe:

1. Reads `info.version` as the latest published release.
2. Reads `releases` as the set of all known releases for inclusion checks.
3. Classifies channel per the table below.

### Channel classification

| Condition | `UpgradeChannel` |
|---|---|
| `installed_version` parses as a PEP 440 version AND equals `info.version` | `ALREADY_CURRENT` |
| `installed_version` parses AND is **greater than** `info.version` per PEP 440 ordering | `AHEAD_OF_PYPI` |
| `installed_version` parses AND is **not present** in `releases` keys | `NO_UPGRADE_PATH` |
| `installed_version` parses AND is present in `releases` keys but older than `info.version` | `UPGRADE_AVAILABLE` |
| Probe failed (timeout / HTTP error / parse error / malformed response) | `UNKNOWN` |

## Cache contract

### Location

- POSIX: `~/.cache/spec-kitty/upgrade-check.json`
- Windows: `%LOCALAPPDATA%\spec-kitty\upgrade-check.json`

### Schema

```json
{
  "installed_version": "3.2.0rc7",
  "latest_pypi_version": "3.2.0rc7",
  "channel": "already_current",
  "probed_at": "2026-05-14T05:50:00+00:00",
  "error": null,
  "ttl_seconds": 86400
}
```

### TTL

- Successful probes (channel ≠ `UNKNOWN`): `ttl_seconds = 86400` (24 h).
- Failed probes (channel = `UNKNOWN`): `ttl_seconds = 3600` (1 h).

### Cache freshness check

A cache entry is **fresh** iff:

```
now - probed_at < ttl_seconds
AND installed_version == get_cli_version()
```

If the installed version changed (e.g. user upgraded between invocations), the cache is treated as stale even within the TTL window.

### Failure modes

- **Cache file missing**: treat as cache miss; probe.
- **Cache file unparseable**: treat as cache miss; probe.
- **Cache write fails (disk full, permission denied)**: log to debug; do not raise. The user gets a notice this invocation but not the next; behavior is not broken.

## Opt-out

Environment variable `SPEC_KITTY_NO_UPGRADE_CHECK=1` disables the probe entirely:

- The probe is not invoked.
- The cache is not read or written.
- No notice is emitted on any channel.
- This is **separate from** the hard CLI/project version mismatch error path (FR-007 AC #5), which remains unconditionally active.

## Notifier contract

```python
def maybe_emit_upgrade_notice(
    cli_version: str,
    *,
    console: Console | None = None,
    now: datetime | None = None,
    cache_path: Path | None = None,
) -> bool:
    """
    Returns True if a notice was emitted; False otherwise.

    Steps:
      1. Check SPEC_KITTY_NO_UPGRADE_CHECK; if set, return False.
      2. Load cache; if fresh, use cached UpgradeProbeResult.
         Otherwise call probe_pypi(cli_version, timeout_s=2.0).
      3. If channel == ALREADY_CURRENT and previous cache entry within TTL
         was also ALREADY_CURRENT, suppress notice (return False).
      4. Render the channel-appropriate notice via the console.
      5. Persist the result to cache (best-effort).
    """
```

### Notice messages

- `ALREADY_CURRENT`: `[dim]spec-kitty-cli {version} — you are on the latest supported version.[/dim]`
- `AHEAD_OF_PYPI`: `[dim]spec-kitty-cli {version} — build is ahead of the latest PyPI release ({latest}). No upgrade required.[/dim]`
- `NO_UPGRADE_PATH`: `[dim]spec-kitty-cli {version} — installed from a non-PyPI build/channel. No PyPI upgrade path is available.[/dim]`
- `UPGRADE_AVAILABLE`: no no-upgrade notice. The existing upgrade nag owns the actionable upgrade prompt.
- `UNKNOWN`: no notice. (The user is not blocked by inability to probe.)

## Performance contract (NFR-004)

- **Cache-warm path**: ≤ 100 ms wall-clock from invocation to return. Measured on the dev machine; recorded in WP evidence.
- **Cold-cache path**: up to 300 ms permitted **once per 24 h** when the cache is missing or stale. Subsequent invocations within the TTL window read from cache and meet the 100 ms budget.
- **Network unavailable**: probe times out at 2 s, falls through to `UNKNOWN`, returns. The 2-second worst case occurs at most once per 1 h cache window.
- **Recommendation**: do not invoke the notifier from the hot startup path; gate it behind `should_check_version()` so non-interactive commands (e.g. CI-only commands) skip it.

## Integration with existing version check

The existing `version_checker.py::should_check_version(command_name)` function returns `True` for user-facing commands and `False` for internal / utility commands. The notifier reuses this gate — it is **not** a parallel decision point.

The notifier is **separate** from `format_version_error()`. The existing hard-mismatch error path is unchanged; the notifier handles only the "no upgrade available" and "already current" cases that the existing path does not address.

## Security considerations (per `secure-design-checklist`)

- **Least Privilege**: probe is a GET to a public endpoint, no auth, no PII.
- **Fail-Safe Defaults**: probe failure resolves to `UNKNOWN`, no notice. Default behavior is "no information emitted" rather than "user blocked".
- **Complete Mediation**: opt-out env var is checked on every invocation; not cached.
- **Economy of Mechanism**: two small contained modules; no new dependencies; no parallel gate to maintain.
- **Open Design**: source-readable; cache path is documented.
- **Separation of Privilege**: the existing hard-mismatch error path is unaffected; the notifier is purely additive.
- **Least Common Mechanism**: cache is per-user, not shared across projects.
- **Psychological Acceptability**: the notice is one dim line; the opt-out env var is documented in `--help` text.
- **Defense in Depth**: timeout + 2 s ceiling + `try/except` swallow at the call site mean a network anomaly cannot escape into the user's CLI invocation.

Data classification: probe sends `User-Agent` (Public) and `installed version` (Public via the same User-Agent). Receives latest version metadata (Public). No PII; no encryption-at-rest needed.

## Testing contract

Per `function-over-form-testing`:

- **Probe tests** use `requests_mock` to stub PyPI responses for each channel; assert on the resulting `UpgradeProbeResult.channel`.
- **Cache tests** use `freezegun` to advance time; assert on cache freshness boundary, TTL behavior, and stale-install invalidation.
- **Notifier tests** use a captured `Console`; assert on the emitted message **substring** (stable text) rather than the full Rich-rendered output.
- **No tests on `requests` itself** — mock at the network boundary.
- **Performance tests** assert wall-clock budget on the cache-warm path via `time.perf_counter`.

## Acceptance mapping

| Spec AC | Coverage in this contract |
|---|---|
| AC #1 — feedback when no upgrade is available | `ALREADY_CURRENT` and `NO_UPGRADE_PATH` notices |
| AC #2 — explains installed version + why no upgrade | Notice message templates carry both |
| AC #3 — distinguishes "already latest" vs "no upgrade path" | Two distinct channels, two distinct messages |
| AC #4 — not noisy; cache / rate-limit / suppress identical | 24 h cache + identical-channel suppression |
| AC #5 — hard CLI/project mismatch path unchanged | Notifier is separate from `format_version_error()` |
