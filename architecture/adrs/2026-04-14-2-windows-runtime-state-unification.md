# ADR 2 (2026-04-14): Windows Runtime State Unification

**Date:** 2026-04-14
**Status:** Accepted
**Deciders:** spec-kitty core team
**Technical Story:** [Priivacy-ai/spec-kitty#105](https://github.com/Priivacy-ai/spec-kitty/issues/105) (hard-coded `~/.spec-kitty` paths), [Priivacy-ai/spec-kitty#603](https://github.com/Priivacy-ai/spec-kitty/issues/603) (Windows storage unification)
**Tags:** windows, state, paths, migration, runtime, platformdirs, unification

---

## Context and Problem Statement

Before this mission, spec-kitty's Windows state was incoherent: different subsystems each chose
their own root based on POSIX conventions that do not apply to Windows:

| Subsystem | Pre-mission Windows root |
|-----------|--------------------------|
| Global runtime (templates, agent commands) | `~/.kittify/` (POSIX home) |
| Sync config, credentials, queue | `~/.spec-kitty/` (POSIX home) |
| Auth (mission 080 fallback) | `~/.config/spec-kitty/auth/` |
| Tracker DB, credentials | `~/.spec-kitty/` (POSIX home) |
| Daemon PID / lock files | `~/.spec-kitty/` (POSIX home) |
| kernel/paths `get_kittify_home()` | `%LOCALAPPDATA%\kittify\` |

This produced multiple problems:

- **Support confusion**: users saw three different path prefixes in error messages; it was
  unclear which directory to check or delete.
- **AppData vs home**: `%USERPROFILE%` / `~` on Windows is the user's profile root, not an
  appropriate location for application data. Windows convention (and Windows Store policy) is
  `%LOCALAPPDATA%` (non-roaming) or `%APPDATA%` (roaming). CLI state is non-roaming.
- **Split roots**: `kernel/paths` resolved to `%LOCALAPPDATA%\kittify\` while every other
  subsystem resolved to `%USERPROFILE%\.spec-kitty\` or `%USERPROFILE%\.kittify\`, making the
  "unified" root claim false.
- **Migration debt**: each release that fixed one subsystem potentially created a new split for
  another.

The spec (FR-003..FR-008) requires a single canonical root on Windows under `%LOCALAPPDATA%`
and a one-time, destination-wins migration that moves legacy state.

---

## Decision Drivers

- Single canonical root on Windows: `%LOCALAPPDATA%\spec-kitty\` (FR-005, C-002).
- All subsystems (auth, tracker, sync, daemon, runtime cache) must resolve under this root.
- `platformdirs.user_data_dir("spec-kitty", appauthor=False, roaming=False)` is the canonical
  resolution function (research R-01).
- One-time migration: destination-wins; quarantine-on-conflict (Q2=A, research R-03).
- POSIX layout (`~/.kittify/`, `~/.spec-kitty/`) is unchanged on macOS/Linux.
- WSL is treated as Linux (research R-02); Windows-specific paths are never activated.
- No long-term dual-root steady state (C-005).

---

## Considered Options

- **Option A: Keep split roots, add aliases.** Add environment variables or a config file to
  let users specify each root. Rejected: increases configuration surface; does not eliminate
  the support confusion; `%LOCALAPPDATA%` is the correct Windows answer and there is no reason
  to offer an alternative.

- **Option B: Single root, migration optional.** Implement the unified root but leave migration
  as an operator task. Rejected: legacy directories would persist indefinitely; runtime would
  silently ignore them, causing data-not-found errors on first Windows run after upgrade.

- **Option C (chosen): Single root + one-time destination-wins migration.**
  `%LOCALAPPDATA%\spec-kitty\` is the canonical root. First Windows run executes a migration
  that moves each legacy root (if present) to the canonical destination. If the destination
  already has data, the legacy root is renamed to `<name>.bak-<ISO-UTC-timestamp>` (quarantine).

- **Option D: Per-subsystem migration decisions.** Each subsystem migrates independently at its
  first access point. Rejected: would produce partial migration states that are hard to diagnose;
  a single migration pass is cleaner and produces a single audit event.

---

## Decision

Adopt **Option C**: single root `%LOCALAPPDATA%\spec-kitty\` + one-time destination-wins migration.

### Root layout

```
%LOCALAPPDATA%\spec-kitty\
├── auth\         # encrypted credentials (file-backed, no OS secret store)
├── tracker\      # tracker SQLite DB and related state
├── sync\         # sync queue (SQLite), clock.json, active_queue_scope
├── daemon\       # daemon PID files, lock files
└── cache\        # version.lock, .update.lock, ephemeral runtime cache
```

### Resolution function

`platformdirs.user_data_dir("spec-kitty", appauthor=False, roaming=False)` returns:
- Windows: `C:\Users\<user>\AppData\Local\spec-kitty`
- macOS/Linux: unchanged (returns `~/.local/share/spec-kitty` but POSIX subsystems
  continue to use `~/.spec-kitty` and `~/.kittify` via their existing resolvers)

The `RuntimeRoot` dataclass (`src/specify_cli/paths/windows_paths.py`) wraps the resolution and
provides typed sub-root accessors (`RuntimeRoot.auth`, `.tracker`, `.sync`, `.daemon`, `.cache`).

### Migration algorithm (research R-03)

For each legacy root (`~/.spec-kitty`, `~/.kittify`, `~/.config/spec-kitty`):

1. Resolve `legacy_root`. If absent → skip (`status: absent`).
2. Resolve `dest_root` under `%LOCALAPPDATA%\spec-kitty\...`.
3. Acquire `%LOCALAPPDATA%\spec-kitty\.migrate.lock` via `msvcrt.locking()` (timeout → actionable error).
4. If `dest_root` absent or empty → `os.replace(legacy_root, dest_root)` (atomic on same volume; copy-and-remove fallback across volumes).
5. If `dest_root` non-empty → rename `legacy_root` to `<name>.bak-<YYYYMMDDTHHMMSSz>` (`status: quarantined`).
6. Release lock; emit one summary message.

Migration is idempotent: step 1 makes repeat invocations no-ops.

### WSL policy

WSL installs `uname -s` → `Linux`. The `sys.platform` guard in `windows_paths.py` is
`== "win32"`. WSL returns `linux` → POSIX layout applies. No Windows paths are activated.

---

## Consequences

### Positive

- One directory to check, one directory to back up, one directory to clean.
- Matches Windows conventions for non-roaming application data.
- Closes #105 (hard-coded `~/.spec-kitty`), contributes to closing #603.
- Migration complexity is incurred once at upgrade time; no steady-state overhead.
- `RuntimeRoot` provides a typed, testable abstraction that is easy to mock in tests.

### Negative

- One-time migration means there is a window (first run after upgrade) where state appears
  missing if the migration fails. The migration is designed to be atomic and to fail loudly
  (the lock-acquisition timeout produces an actionable error message), but a failed migration
  leaves state in the legacy root.
- Quarantine creates backup directories that users may not know to clean up. The migration
  summary message names the quarantine paths explicitly.

### Neutral

- POSIX layout is unaffected. The change is Windows-only.
- WSL users are unaffected (treated as Linux).
- The `SPEC_KITTY_HOME` environment variable still overrides the Windows root for CI / testing.

---

## References

- Spec: FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, C-002, C-005, C-006
- Research: R-01 (platformdirs), R-02 (WSL detection), R-03 (migration algorithm)
- WP01 commit: `b4352ae1` — `feat(WP01): add Windows paths subpackage + render helper`
- WP02 commit: `b7695489` — `feat(WP02): implement Windows runtime state migration module`
- WP04 commit: `f667c4f1`, `c06fa025` — `feat(WP04): replace legacy path literals + wire Windows state migration`
- WP05 commit: `d4eae48c` — `feat(WP05): re-root tracker / sync / daemon / kernel.paths to unified Windows root`
- Audit report: `architecture/2026-04-14-windows-compatibility-hardening.md`
- User-facing explainer: `docs/explanation/windows-state.md`
- Issue: [#105](https://github.com/Priivacy-ai/spec-kitty/issues/105)
- Issue: [#603](https://github.com/Priivacy-ai/spec-kitty/issues/603)
