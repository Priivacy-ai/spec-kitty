# Phase 1 Data Model: Windows Compatibility Hardening Pass

**Mission**: `windows-compatibility-hardening-01KP5R6K`
**Date**: 2026-04-14

This mission is a hardening pass, not a greenfield feature, so the "data model" here is primarily path taxonomy, a small number of in-process dataclasses, and a persisted migration record. No database schema.

## Entities

### E-01. `RuntimeRoot`

Single logical abstraction over "where Spec Kitty writes user state on this platform."

| Field | Type | Description |
|---|---|---|
| `platform` | `Literal["win32", "darwin", "linux"]` | Resolved from `sys.platform`. WSL resolves as `"linux"`. |
| `base` | `Path` | On Windows: `%LOCALAPPDATA%\spec-kitty\`. On POSIX: unchanged from current behavior (`~/.spec-kitty/`). |
| `auth_dir` | `Path` | `base / "auth"` |
| `tracker_dir` | `Path` | `base / "tracker"` |
| `sync_dir` | `Path` | `base / "sync"` |
| `daemon_dir` | `Path` | `base / "daemon"` |
| `cache_dir` | `Path` | `base / "cache"` |

**Invariants**:
- `base` exists before first write (created lazily by the resolver).
- On Windows, all child paths share a single drive-letter root with `base` (no `%APPDATA%` mixing).
- `WSL` resolves `platform == "linux"` and uses Linux layout; never touches Windows paths.

**Resolver**: `get_runtime_root() -> RuntimeRoot` in `src/specify_cli/paths/windows_paths.py`. Uses `platformdirs.user_data_dir("spec-kitty", appauthor=False, roaming=False)` on Windows.

### E-02. `LegacyWindowsRoot`

Description of a pre-mission Windows storage location that migration must consider.

| Field | Type | Description |
|---|---|---|
| `id` | `Literal["spec_kitty_home", "kittify_home", "auth_xdg_home"]` | Stable identifier used in logs and migration records. |
| `path` | `Path` | The legacy directory on disk. |
| `dest` | `Path \| None` | The destination under the new `RuntimeRoot`, or `None` if nothing to move (e.g. `kittify_home` is messaging-only). |
| `exists` | `bool` | Computed at migration time. |

**Known instances**:
- `spec_kitty_home`: `Path.home() / ".spec-kitty"` → `RuntimeRoot.base`
- `kittify_home`: `Path.home() / ".kittify"` → `None` (no state to move; only messaging references)
- `auth_xdg_home`: `Path.home() / ".config" / "spec-kitty"` → `RuntimeRoot.auth_dir`

### E-03. `MigrationOutcome`

Structured result of a single legacy-root migration attempt. Logged in CLI output and, if run under `--debug`, written to a JSONL file at `RuntimeRoot.base / "migration-log.jsonl"`.

| Field | Type | Description |
|---|---|---|
| `legacy_id` | `str` | Matches `LegacyWindowsRoot.id`. |
| `status` | `Literal["absent", "moved", "quarantined", "error"]` | Terminal status. |
| `legacy_path` | `str` | Absolute path as string. |
| `dest_path` | `str \| None` | Absolute destination path or `None`. |
| `quarantine_path` | `str \| None` | If `status == "quarantined"`, the `*.bak-<ts>` path. |
| `timestamp_utc` | `str` | ISO-8601 UTC timestamp of the migration attempt. |
| `error` | `str \| None` | Error message if `status == "error"`. |

**State machine**:
```
start ── legacy absent ──> absent (terminal)
start ── legacy present, dest empty ──> moved (terminal)
start ── legacy present, dest non-empty ──> quarantined (terminal)
start ── lock/IO failure ──> error (terminal)
```

**Invariants**:
- Idempotent: second migration run with no legacy present returns `absent` for all three known roots.
- No path is deleted. Quarantine is move-rename only.
- Per-root lock ensures concurrent CLI invocations serialize.

### E-04. `SecureStorageSelection`

Runtime result of `SecureStorage.from_environment()` after the hard split.

| Field | Type | Description |
|---|---|---|
| `backend` | `Literal["windows_file", "keychain", "linux_file"]` | Resolved backend name. |
| `platform` | `Literal["win32", "darwin", "linux"]` | Source platform. |
| `store_path` | `Path \| None` | For file-backed stores, the resolved auth directory. `None` for keychain-backed. |
| `keyring_available` | `bool` | Always `False` on Windows (hard split). True/False on POSIX depending on `keyring` import health. |

**Invariants**:
- `platform == "win32"` → `backend == "windows_file"`, `keyring_available == False`, `store_path == RuntimeRoot.auth_dir`.
- On Windows, the `keychain` module is never imported (enforced by a test that asserts `"specify_cli.auth.secure_storage.keychain" not in sys.modules` after `from_environment()` runs under a simulated `sys.platform = "win32"` fixture).

### E-05. `HookInstallRecord`

Representation of a generated git pre-commit hook. No persistence beyond the file itself; this is the logical shape the installer renders.

| Field | Type | Description |
|---|---|---|
| `hook_path` | `Path` | `<repo>/.git/hooks/pre-commit`. |
| `interpreter` | `Path` | Absolute path captured from `sys.executable` at install time. |
| `module` | `str` | Always `"specify_cli.policy.commit_guard_hook"`. |
| `shebang` | `Literal["#!/bin/sh"]` | Fixed per Q3=A. |
| `msys_translated_interpreter` | `str \| None` | On Windows, the `/c/Users/...` form for MSYS sh.exe if different from `interpreter`. `None` on POSIX. |
| `mode` | `int` | `0o755`. |

**Invariants**:
- `interpreter.is_file()` at install time.
- Hook body contains the interpreter path exactly once, quoted.
- Executable-test harness runs the hook with a dummy commit and asserts exit code + stdout contract.

### E-06. `WindowsCISuite`

Logical selection of tests that must pass on the blocking Windows job.

| Field | Type | Description |
|---|---|---|
| `marker` | `Literal["windows_ci"]` | Fixed marker name. |
| `tests` | `list[TestId]` | Tests carrying the marker (initial set enumerated in `research.md` R-06). |
| `runner` | `Literal["windows-latest"]` | GitHub-hosted runner. |
| `install_method` | `Literal["pipx"]` | Single install topology per R-07. |
| `env` | `dict[str, str]` | At minimum `{"PYTHONUTF8": "1"}`. |
| `max_wall_clock_minutes` | `int` | 15 (NFR-002). |

**Invariants**:
- Every test in the initial set either references a spec FR/NFR/C or a named regression issue (#586, #105, #101, #71).
- Default Linux CI job runs with `-m "not windows_ci"` to avoid mis-routed tests.

## Relationships

- `RuntimeRoot` is the single source of truth for all path lookups. `file_fallback.EncryptedFileStorage` (auth), `tracker.credentials`, `sync.daemon`, and `kernel.paths` consume `get_runtime_root()`.
- `LegacyWindowsRoot` instances map `id → dest` via `RuntimeRoot`.
- `MigrationOutcome` is produced per `LegacyWindowsRoot` per migration invocation.
- `SecureStorageSelection.store_path` (when populated) is `RuntimeRoot.auth_dir` on Windows.
- `HookInstallRecord.interpreter` has no relationship to `RuntimeRoot`; hooks live in the repo's `.git/hooks/`.
- `WindowsCISuite.tests` reference implementation modules that cover all of the above.

## Validation rules (FR-cross-reference)

| Rule | Enforced by | Spec IDs |
|---|---|---|
| Windows never imports `keychain` at runtime | Unit test on `SecureStorageSelection`; `sys.modules` assertion | FR-001, C-001 |
| `keyring` not installed on Windows | CI assertion: `pip list` on `windows-latest` excludes `keyring` | FR-001, C-001 |
| Only one Windows root for state | Unit test on all consumers: `tracker`, `sync`, `daemon`, `auth` resolve under the same `RuntimeRoot.base` | FR-003, FR-004, FR-005, C-002 |
| Migration never deletes | Integration test: legacy dir either gone (moved) or renamed to `*.bak-<ts>` (quarantined) | FR-006, C-006 |
| Migration idempotent | Integration test: second run on clean state is no-op | FR-006 |
| Migration safe under contention | Stress test: two concurrent processes share a lock | FR-007, NFR-004 |
| Actionable errors | Test message assertions for missing `%LOCALAPPDATA%`, quarantine conflicts, hook install failures | FR-008, NFR-005 |
| Hook pins absolute interpreter | Read-back test on generated hook file; executable-run test | FR-009, FR-010, FR-011 |
| No `~/.kittify` / `~/.spec-kitty` in Windows user output | Grep test in CLI output fixtures; `render_runtime_path` unit tests | FR-012, FR-013, SC-002 |
| Every fix has a Windows test | Code review + lane-G matrix | FR-017, C-007 |
| Audit report exists and is reviewable | File presence test + review checklist | FR-018, SC-005 |

## Persistence

Only one new persistent artifact: the optional `migration-log.jsonl` under `RuntimeRoot.base` when the user invokes migration with `--debug`. Everything else is either ephemeral (in-process dataclasses) or existing persisted state simply relocated under the new root.

No schema changes to existing persisted formats (`status.events.jsonl`, tracker DB, etc.).
