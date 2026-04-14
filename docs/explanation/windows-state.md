# Where Spec Kitty Stores State on Windows

Spec Kitty stores all per-user runtime state on Windows under a single root directory:

```
%LOCALAPPDATA%\spec-kitty\
├── auth\         # encrypted credentials (file-backed, no OS secret store)
├── tracker\      # tracker SQLite DB and related state
├── sync\         # sync queue (SQLite), clock, active queue scope
├── daemon\       # daemon PID files and lock files
└── cache\        # version lock, update lock, ephemeral runtime cache
```

In practice `%LOCALAPPDATA%` expands to something like
`C:\Users\<your-name>\AppData\Local\spec-kitty\`.

## Why a Single Root?

Before version 0.12.0, different spec-kitty subsystems stored state in different directories:
`~/.spec-kitty/`, `~/.kittify/`, `~/.config/spec-kitty/`, and sometimes
`%LOCALAPPDATA%\kittify\`. This created a confusing support story: which directory do you
check when something goes wrong? Which directory do you back up?

Starting with 0.12.0, all Windows runtime state lives under one root. The root is resolved via:

```python
platformdirs.user_data_dir("spec-kitty", appauthor=False, roaming=False)
```

which returns the `Local` (non-roaming) AppData directory. This matches Windows conventions for
CLI application data that should not sync across devices.

## Why Not Windows Credential Manager?

Spec Kitty does not use Windows Credential Manager (or macOS Keychain, or Linux Secret Service)
for auth session storage. The reasons:

- CLI tools run in terminal, CI pipelines, and headless automation where Credential Manager
  prompts are unexpected or blocked.
- The `keyring` library (which provides Credential Manager access) is not installed on Windows.
  The `pyproject.toml` dependency has a `sys_platform != "win32"` marker. A new Windows install
  has zero OS-secret-store dependencies.
- The encrypted file-backed store at `%LOCALAPPDATA%\spec-kitty\auth\` provides equivalent
  security for CLI auth tokens: the session file is AES-256 encrypted at rest with a
  machine-derived key.

See [ADR `architecture/adrs/2026-04-14-1-windows-auth-platform-split.md`](../architecture/adrs/2026-04-14-1-windows-auth-platform-split.md)
for the full decision record.

## First-Run Migration

If you upgrade from a version older than 0.12.0, spec-kitty will migrate your existing state
on the first Windows run.

The migration is automatic and produces a summary message like:

```
[spec-kitty] Windows state migration complete.
  Moved: C:\Users\you\.spec-kitty → %LOCALAPPDATA%\spec-kitty
  Moved: C:\Users\you\.kittify    → %LOCALAPPDATA%\spec-kitty (runtime root)
  Note:  C:\Users\you\.config\spec-kitty\auth — destination already had data;
         quarantined as .spec-kitty.bak-20260414T103000Z
```

### How migration works

For each legacy location:

1. If the legacy location does not exist, skip it.
2. If the destination is empty, move the legacy location there atomically.
3. If the destination already has data, rename the legacy location to
   `<name>.bak-<ISO-UTC-timestamp>` (quarantine). Your existing data is preserved;
   the destination data takes precedence.
4. The migration acquires a lock before any move to prevent two concurrent CLI invocations
   from racing into a partial state.

Migration is **idempotent**: running it twice produces the same result as running it once.

### What if migration fails?

The migration fails loudly with an actionable error message. It does not silently continue
with partially-migrated state. If you see a migration error:

1. Close any other spec-kitty processes (they may be holding the migration lock).
2. Run `spec-kitty migrate --force` to retry.
3. If problems persist, check `%LOCALAPPDATA%\spec-kitty\.migrate.lock` exists and delete it
   manually if you are certain no other spec-kitty process is running.

## WSL

WSL (Windows Subsystem for Linux) installs of spec-kitty use the **Linux** storage layout, not
the Windows layout. WSL reports `uname -s` as `Linux`; `sys.platform` is `linux`, not `win32`.
The Windows-specific storage paths are never activated.

If you run spec-kitty in both native Windows and WSL, they use completely separate state
directories. Credentials, tracker databases, and sync queues are not shared between the two
environments.

## Encoding

Spec Kitty enforces UTF-8 on Windows stdout/stderr at startup (via
`sys.stdout.reconfigure(encoding="utf-8")`) to handle Unicode characters in repository paths,
branch names, and commit messages. The CI environment also sets `PYTHONUTF8=1`.

If you see garbled output for non-ASCII characters, set `PYTHONUTF8=1` in your shell environment
as an extra safety measure:

```powershell
$env:PYTHONUTF8 = "1"
spec-kitty status
```

Or add it to your PowerShell profile:

```powershell
[System.Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")
```

## Troubleshooting

### "Credentials not found" after upgrade

Your credentials were stored in a legacy location. Run:

```powershell
spec-kitty auth login
```

to establish a fresh file-backed session under `%LOCALAPPDATA%\spec-kitty\auth\`.

### "Migration lock timeout"

Another spec-kitty process is running (or crashed holding the lock). Ensure all spec-kitty
processes are stopped, then delete the lock file:

```powershell
Remove-Item "$env:LOCALAPPDATA\spec-kitty\.migrate.lock" -Force
```

### Finding your state root

```powershell
spec-kitty doctor state-roots
```

This prints the canonical Windows root and reports the status of each subdirectory.

### Checking if keyring is installed (should not be)

```powershell
pipx runpip spec-kitty-cli show keyring
```

If this returns anything other than an error, keyring has been installed unexpectedly. File an
issue at [Priivacy-ai/spec-kitty](https://github.com/Priivacy-ai/spec-kitty/issues).

---

## Related Reading

- [ADR: Windows Auth Platform Split](../architecture/adrs/2026-04-14-1-windows-auth-platform-split.md)
- [ADR: Windows Runtime State Unification](../architecture/adrs/2026-04-14-2-windows-runtime-state-unification.md)
- [Audit Report: Windows Compatibility Hardening](../architecture/2026-04-14-windows-compatibility-hardening.md)
