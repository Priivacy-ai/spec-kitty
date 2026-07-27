# Contract: `SyncBoundaryPreflight`

**Module**: `src/specify_cli/sync/preflight.py` (NEW)
**Mission**: `mvp-cli-sync-boundary-completion-01KRX11M`

This contract specifies the public API and behavior of the reusable preflight helper that gates SaaS-producing CLI commands.

## Public API

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from rich.console import Console

# Canonical mismatch field names — must match Domain Language in spec.md.
MismatchField = Literal[
    "daemon_package_version",
    "daemon_executable_path",
    "daemon_source_path",
    "daemon_server_url",
    "daemon_team_or_user",
    "daemon_queue_db_path",
]


@dataclass(frozen=True)
class ForegroundIdentity:
    package_version: str
    executable_path: Path
    source_path: Path
    server_url: str | None
    team_or_user: str | None
    queue_db_path: Path
    pid: int


@dataclass(frozen=True)
class OwnerMismatch:
    field: MismatchField
    foreground_value: str
    daemon_value: str
    remediation_hint: str


@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    mismatches: tuple[OwnerMismatch, ...] = ()
    orphan_records: tuple[Any, ...] = ()  # DaemonOwnerRecord; opaque to callers
    legacy_event_rows: int = 0
    legacy_body_upload_rows: int = 0
    auth_present: bool = False
    auth_required: bool = True

    @property
    def legacy_rows_for_scope(self) -> int:
        return self.legacy_event_rows + self.legacy_body_upload_rows

    def render(self, console: Console) -> None: ...
    def to_dict(self) -> dict[str, Any]: ...


def collect_foreground_identity(repo_root: Path) -> ForegroundIdentity: ...


def run_preflight(
    *,
    repo_root: Path,
    foreground: ForegroundIdentity | None = None,
    require_auth: bool = True,
) -> PreflightResult: ...
```

## Behavior

### `collect_foreground_identity(repo_root)`

- Returns a `ForegroundIdentity` populated from process state and hosted-auth config.
- `server_url` and `team_or_user` are `None` iff hosted auth is absent.
- Pure / side-effect-free (reads files, no writes).

### `run_preflight(...)`

Read-only check. Composes the following in order:

1. Resolve `foreground` if not supplied via `collect_foreground_identity(repo_root)`.
2. Read `DaemonOwnerRecord` at `owner_record_path()` if present.
3. If the record exists and is *not* orphaned, build `OwnerMismatch` entries by comparing each canonical field. A field is considered mismatched when the foreground and daemon values differ. Missing values on either side are rendered as `<unset>` and counted as a mismatch only when one side has a concrete value and the other does not.
4. Collect orphan records via `list_orphan_records()` (existing).
5. Count legacy event-class rows and body-upload-class rows for the current scope via the extended `detect_legacy_rows_for_scope()`. The scope is the foreground's `(server_url, team_or_user)` tuple.
6. Determine `auth_present` from `foreground.server_url is not None and foreground.team_or_user is not None`.
7. Compute `ok` per the invariant in `data-model.md`.

The helper does **not** mutate state and does **not** call SaaS endpoints.

### `PreflightResult.render(console)`

Default human-readable output:

```
Sync boundary refused: <N> mismatched field(s); <M> orphan daemon record(s); <K> legacy rows in scope.

Mismatches:
┌──────────────────────────────┬──────────────────────┬──────────────────────┐
│ Field                        │ Foreground           │ Daemon               │
├──────────────────────────────┼──────────────────────┼──────────────────────┤
│ daemon_package_version       │ 3.2.0rc11            │ 3.2.0rc10            │
│ daemon_executable_path       │ /usr/local/bin/uv    │ /Users/.../bin/uv    │
└──────────────────────────────┴──────────────────────┴──────────────────────┘

Remediation:
  • Run `spec-kitty doctor restart-daemon` to restart the daemon at the foreground source.
  • Run `spec-kitty doctor orphan-daemons` to clean up <M> orphan daemon record(s).
  • Run `spec-kitty sync now` to flush <K> legacy rows for the current scope after the boundary is coherent.
```

When `ok` is `True`, `render()` is a no-op.

### `PreflightResult.to_dict()`

Returns a JSON-serializable dictionary with all dataclass fields plus the computed `legacy_rows_for_scope` and `ok` keys. Used by `--json` flag paths in `sync status --check` and the preflight's optional debug surface.

## Caller contract

Every SaaS-producing CLI entry point MUST:

1. Call `run_preflight(repo_root=..., require_auth=True)` *after* its own input validation and hosted-auth presence preflight, and *before* any code path that:
   - writes a row to the scoped queue DB,
   - writes a row to `body_upload_queue`,
   - flushes rows to SaaS, or
   - reads-then-acts on SaaS endpoints in a way that requires identity coherence.

2. If `result.ok` is `False`:
   - call `result.render(console)`,
   - exit with code `2` (matches existing `_require_daemon_owner_coherence` exit code).

3. If `result.ok` is `True`:
   - proceed with the original command logic.

## Test surface

Tests SHALL cover:

- `run_preflight` returns `ok=True` when no owner record exists and the foreground is authenticated and the scoped queue holds the legacy rows.
- `run_preflight` returns `ok=False` with a `daemon_package_version` mismatch when the owner record's version differs from foreground.
- Same for each of the other five canonical field names (`daemon_executable_path`, `daemon_source_path`, `daemon_server_url`, `daemon_team_or_user`, `daemon_queue_db_path`).
- `run_preflight` returns `ok=False` with `orphan_records` non-empty when an orphan owner record exists (using a written-on-disk fixture; not by invoking `os.kill`).
- `run_preflight` returns `ok=False` with `legacy_rows_for_scope > 0` when the legacy queue contains rows for the current scope.
- `legacy_body_upload_rows > 0` triggers refusal independently of `legacy_event_rows`.
- `PreflightResult.render` produces ≤ 25 visible lines for ≤ 6 mismatches and ≤ 3 orphan records (NFR-004).
- `auth_required=True` and `auth_present=False` produces `ok=False` even when no daemon record exists.

## Performance contract

`run_preflight` SHALL complete in ≤ 100 ms on a coherent host (NFR-003). The helper does not perform SaaS round-trips; it reads owner record, queries SQLite counts, and inspects process state.

## Cross-platform contract (C-008)

The helper SHALL behave identically on Linux, macOS, and Windows 10+ per the project charter:

- All file-system paths use `pathlib.Path`; no string-separator assumptions.
- Home-directory lookups go through `pathlib.Path.home()` (resolves `USERPROFILE` on Windows, `HOME` on POSIX) rather than reading `os.environ["HOME"]` directly.
- Tests isolate the operator's home directory by patching `pathlib.Path.home()` so the same fixtures run on all three platforms.

## Backwards-compatibility contract

- The existing `_require_daemon_owner_coherence()` helper (`src/specify_cli/cli/commands/sync.py:342`) is rewritten to delegate to `run_preflight(...)`. Its public signature is preserved.
- The existing `_build_boundary_check_failures()` helper (`src/specify_cli/cli/commands/sync.py:1286`) is rewritten to share its failure-detection logic with `run_preflight` (single source of truth), but its return shape is preserved.
- No on-disk format changes; no SQLite schema changes; no SaaS payload changes.
