# Contract: CLI Migrate (Windows runtime state migration)

**Spec IDs**: FR-006, FR-007, FR-008, FR-012, FR-013, NFR-003, NFR-004, NFR-005, C-006
**Modules**: `src/specify_cli/cli/commands/migrate_cmd.py`, `src/specify_cli/paths/windows_migrate.py`

## Command surface (unchanged CLI arity)

```
spec-kitty migrate
```

Existing `migrate` subcommand gains a Windows-only auto-run of the state migration on first execution post-upgrade. No new flags required for the happy path. Optional `--debug` writes `migration-log.jsonl`.

## `windows_migrate.migrate_windows_state(dry_run: bool = False) -> list[MigrationOutcome]`

```python
def migrate_windows_state(dry_run: bool = False) -> list[MigrationOutcome]:
    """One-time, idempotent migration of legacy Windows state.

    No-op on non-Windows platforms. Safe under concurrent CLI invocation.
    """
```

## Behavior matrix

| Precondition | Outcome |
|---|---|
| `sys.platform != "win32"` | Returns `[]` immediately. |
| All three legacy roots absent | Returns 3 `MigrationOutcome(status="absent")` records. Idempotent no-op. |
| `~/.spec-kitty` exists, destination empty | `os.replace(legacy, dest)`. Returns `status="moved"`. |
| `~/.spec-kitty` exists, destination non-empty | Renames legacy to `~/.spec-kitty.bak-<ts>`. Returns `status="quarantined"`. |
| `~/.config/spec-kitty` exists, dest (`auth/`) empty | Moves. |
| `~/.config/spec-kitty` exists, dest non-empty | Quarantines to `~/.config/spec-kitty.bak-<ts>`. |
| `~/.kittify` exists | No file move (messaging-only). Returns `status="absent"` (from a state-move perspective). UI layer may still surface a one-line note about stale path references. |
| Lock contention (another CLI already migrating) | Retries for up to 3s, then returns `status="error"` with actionable message and exit code 69 (EX_UNAVAILABLE). |
| `%LOCALAPPDATA%` unresolvable | Returns `status="error"` for all roots; CLI prints actionable guidance; exit code 78 (EX_CONFIG). |
| `dry_run=True` | Computes outcomes without moving anything. Status reflects what *would* happen. |

## Guarantees

- G-01 (idempotency): Invoking twice on the same machine yields only `status="absent"` after the first run, with no filesystem side effects.
- G-02 (no-destroy): No code path deletes either the legacy tree or the destination. Every resolvable outcome is `absent`, `moved`, or `quarantined`.
- G-03 (atomicity on same volume): `os.replace()` is used; interrupts cannot leave half-moved state on single-volume Windows.
- G-04 (cross-volume fallback): When `os.replace` fails with `EXDEV`, the code copies then renames the source to quarantine — never deletes.
- G-05 (contention safety): Two concurrent invocations serialize on `%LOCALAPPDATA%\spec-kitty\.migrate.lock` via `msvcrt.locking`.
- G-06 (quarantine uniqueness): Backup names include an ISO-UTC timestamp; if two migrations collide in a single second, a `_N` suffix is appended.
- G-07 (message actionability): Every non-success outcome produces a CLI message that names the affected path and the next action.

## User-facing output

On `status="moved"` for one or more roots:
```
Migrated Spec Kitty runtime state on Windows.
  Canonical location: C:\Users\alice\AppData\Local\spec-kitty
  Moved: C:\Users\alice\.spec-kitty -> C:\Users\alice\AppData\Local\spec-kitty
```

On `status="quarantined"`:
```
Migrated Spec Kitty runtime state on Windows.
  Canonical location: C:\Users\alice\AppData\Local\spec-kitty
  Destination already contained state; legacy trees preserved as backups:
    C:\Users\alice\.spec-kitty -> C:\Users\alice\.spec-kitty.bak-20260414T103500Z
    C:\Users\alice\.config\spec-kitty -> C:\Users\alice\.config\spec-kitty.bak-20260414T103500Z
  Review the canonical location and delete the backup directories when safe.
```

On `status="error"` for lock contention:
```
Another Spec Kitty CLI instance is migrating runtime state. Please retry in a moment.
```

On `status="error"` for unresolvable `%LOCALAPPDATA%`:
```
Could not resolve %LOCALAPPDATA% on this machine. Spec Kitty needs a writable Windows app-data directory to store runtime state.
Diagnose with: echo %LOCALAPPDATA% (cmd.exe) or $env:LOCALAPPDATA (PowerShell).
```

## Test contract

| Test ID | File | windows_ci? | Asserts |
|---|---|---|---|
| T-MIG-01 | `tests/paths/test_windows_migrate.py::test_absent_noop` | Yes | All legacy absent → all outcomes `absent`; no filesystem writes under `%LOCALAPPDATA%`. |
| T-MIG-02 | `tests/paths/test_windows_migrate.py::test_move_to_empty_destination` | Yes | Legacy tree exists, dest empty → `os.replace` happens; legacy gone, dest populated. |
| T-MIG-03 | `tests/paths/test_windows_migrate.py::test_quarantine_on_conflict` | Yes | Legacy tree + non-empty dest → legacy renamed to `*.bak-<ts>`; dest untouched. |
| T-MIG-04 | `tests/paths/test_windows_migrate.py::test_idempotent_second_run` | Yes | Second invocation yields only `absent` outcomes. |
| T-MIG-05 | `tests/paths/test_windows_migrate.py::test_concurrent_lock_contention` | Yes | Two subprocesses racing → exactly one completes, other returns `status="error"` with the retry message. |
| T-MIG-06 | `tests/paths/test_windows_migrate.py::test_dry_run_no_side_effects` | Yes | `dry_run=True` returns correct outcomes without moving anything. |
| T-MIG-07 | `tests/cli/test_migrate_cmd_messaging.py::test_windows_messaging_uses_real_paths` | Yes | CLI output contains `C:\Users\...\AppData\Local\spec-kitty` and does NOT contain `~/.kittify` or `~/.spec-kitty`. |
