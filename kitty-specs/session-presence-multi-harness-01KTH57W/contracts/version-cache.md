# Contract: Version Cache File Format

## Path

`~/.kittify/last-cli-check.json`

(Note: global user-level cache, not per-project. `Path.home() / ".kittify" / "last-cli-check.json"`)

## Schema

```json
{
  "checked_at": "2026-06-07T13:00:00+00:00",
  "latest_version": "3.2.0"
}
```

| Field | Type | Description |
|---|---|---|
| `checked_at` | ISO 8601 UTC datetime string | When the background check last completed successfully |
| `latest_version` | `str` | Latest version string returned by the index query |

## TTL Semantics

- TTL = 3600 seconds (1 hour).
- Cache is **valid** if `now - checked_at < TTL_SECONDS`.
- Cache is **stale** if the file is absent, unreadable, malformed, or `now - checked_at >= TTL_SECONDS`.
- On stale/absent: `check_in_background()` is spawned (fire-and-forget); `get_available_version()` returns the last known `latest_version` or `None` if no cache exists.
- On valid: `check_in_background()` is not spawned; `get_available_version()` returns the cached `latest_version`.

## Write Semantics

- Written atomically (temp file + `os.replace()`) in the same directory as the target.
- Parent directory `~/.kittify/` is created with `mkdir(parents=True, exist_ok=True)` before writing.
- Any write failure is silently swallowed — the cache is best-effort.
