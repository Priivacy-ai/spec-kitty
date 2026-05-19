# Contract: `spec-kitty doctor restart-daemon` + remediation-hint refresh (for #1124)

**Modules**: `src/specify_cli/cli/commands/doctor.py`, `src/specify_cli/sync/preflight.py`
**WP**: WP03

## CLI surface

```
$ spec-kitty doctor restart-daemon [--json]

Stop the registered sync daemon and respawn it at the foreground
executable / source recorded in the daemon owner record.

Exit codes:
  0  Daemon restarted successfully (or no daemon was running and one is now launched matching the foreground).
  1  No registered daemon and no foreground binding available to launch one. Operator must run `spec-kitty sync now`.
  2  Daemon stop succeeded but respawn failed. The system is left in a stopped state; the underlying error is reported.
  3  Daemon stop failed (process unresponsive). The owner record was not consumed. Operator can retry or use `pkill`.
```

`--json` emits a single object with `status`, `previous_pid`, `new_pid`, and `error` fields.

## Behavioral contract

| Precondition | Action | Outcome |
|--------------|--------|---------|
| Registered daemon running, foreground matches owner | Stop existing process via owner pid; relaunch via existing daemon launcher with owner's `executable_path` / `source_path` | Exit 0; new pid recorded in owner record. |
| Registered daemon running, foreground does NOT match owner | Stop existing process; relaunch using **foreground** executable/source (not the stale owner's) | Exit 0; owner record now binds to foreground. |
| Owner record absent | No daemon to stop | Exit 1 with an actionable message: "no registered daemon — run `spec-kitty sync now` to launch one". |
| Owner record present, process already dead | Skip stop; clean up stale lock; relaunch | Exit 0; surface a "stale owner record cleaned" notice. |
| Stop hangs (process unresponsive) | Owner record left intact | Exit 3 with hint to investigate / `pkill -f run_sync_daemon`. |

## Composition contract

`restart-daemon` is implemented as a composition of existing primitives:

```python
def restart_daemon(repo_root: Path, *, foreground: ForegroundIdentity) -> RestartResult:
    owner = read_owner_record(repo_root)
    if owner is None:
        return RestartResult(status="no_owner", exit_code=1, ...)
    stop_result = stop_registered_daemon(owner)  # existing primitive used by `sync stop`
    if not stop_result.ok and stop_result.kind != "already_dead":
        return RestartResult(status="stop_failed", exit_code=3, ...)
    launch_result = launch_daemon_for_foreground(foreground)  # existing primitive used by `sync now`
    if not launch_result.ok:
        return RestartResult(status="respawn_failed", exit_code=2, ...)
    return RestartResult(status="restarted", exit_code=0, previous_pid=..., new_pid=...)
```

The CLI command in `doctor.py` is a thin typer wrapper around `restart_daemon`.

## Remediation hint refresh

`src/specify_cli/sync/preflight.py` currently mentions `spec-kitty doctor restart-daemon` in 4 hint strings + 1 comment:

- line 99 — `_REMEDIATION_HINTS["..."]`
- line 103 — `_REMEDIATION_HINTS["..."]`
- line 107 — `_REMEDIATION_HINTS["..."]`
- line 119 — `_REMEDIATION_HINTS["..."]`
- line 218 — explanatory comment

After WP03 lands, each hint:
1. References `spec-kitty doctor restart-daemon` (which now exists).
2. Optionally appends a secondary remedy hint for the case where the operator wants to verify the restart (`spec-kitty sync status --check` to confirm).
3. Uses uniform wording across the 4 strings so a future grep stays consistent.

## Test surface (WP03)

`tests/specify_cli/cli/commands/test_doctor_restart_daemon.py`:
- **Happy path**: launch a fake daemon (process double), invoke `doctor restart-daemon`, assert exit 0 and new pid != old pid.
- **No owner**: invoke with no owner record on disk, assert exit 1 and the actionable error mentions `spec-kitty sync now`.
- **Stop fails**: simulate a hung daemon, assert exit 3 and owner record left intact.
- **Respawn fails**: simulate launcher failure post-stop, assert exit 2 and no daemon left running.
- **Foreground binding**: simulate mismatched owner; assert new owner record is bound to foreground after restart.

`tests/specify_cli/sync/test_preflight_remediation_hints.py`:
- **Hint coverage**: every `_REMEDIATION_HINTS` entry that mentions a `spec-kitty …` command, parsed and shell-invoked under `--help`, must exit 0 (i.e., the command actually exists on the installed CLI).
- **Wording uniformity**: assert all 4 hint strings reference `doctor restart-daemon` in the same canonical phrase.
