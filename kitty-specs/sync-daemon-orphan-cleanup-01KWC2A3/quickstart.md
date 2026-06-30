# Quickstart: Safe Sync Daemon Orphan Cleanup

## Operator remediation (the two-command path — SC-005)

You have accumulated old sync daemons (e.g. after several upgrades). Inspect, then clean:

```bash
# 1. See what is running and how it is classified (read-only — never kills)
spec-kitty auth doctor
#   Orphans table shows: PID · PORT · VERSION · CLASS (safe_auto|operator_required) · REASON

# 2. Clean the safe ones. Same-scope stale daemons (the usual upgrade case) are
#    safe_auto and are swept automatically:
spec-kitty auth doctor --reset
#   → swept: N · skipped: M (operator_required) · failed: K

# 3. Only if step 2 reported skipped operator_required daemons that you recognise
#    as yours (e.g. a stale cross-checkout daemon), force them:
spec-kitty auth doctor --reset --force
```

What is **never** touched: third-party listeners on a reserved port, dashboard
daemons (ports `9237–9336`), out-of-range processes, and the currently-active daemon.

JSON for scripts/CI:

```bash
spec-kitty auth doctor --json | jq '.orphans[] | {port, pid, cleanup_class, skip_reason}'
spec-kitty auth doctor --reset --json | jq '.reset_result'   # {swept[], skipped[], failed[]}
```

## What changed (operator-visible)

- `auth doctor` now shows a **cleanup class** and **reason** per daemon, not just a count.
- `auth doctor --reset` reports **exact** swept / skipped / failed entries.
- Startup auto-clean now removes provably-stale **same-scope** daemons (including
  older versions) instead of skipping them — so orphans no longer pile up across upgrades.
- A new sync daemon **self-retires** once it is superseded and idle.

## Developer / test quickstart

The venv is assumed warm. Live-subprocess suite (real loopback ports, real PIDs):

```bash
# Serial — real ports are OS-global and not HOME-isolated:
PWHEADLESS=1 pytest tests/sync/test_daemon_orphan_classification.py -n0 -q
PWHEADLESS=1 pytest tests/sync/test_daemon_cleanup_boundary.py -n0 -q
# Existing harness this builds on:
PWHEADLESS=1 pytest tests/sync/test_orphan_sweep.py -n0 -q
```

Spawn an old-version daemon in a test by spoofing the version env (no packaging needed):

```python
# _get_package_version() reads SPEC_KITTY_CLI_VERSION first (daemon.py:238-250)
env = {**os.environ, "SPEC_KITTY_CLI_VERSION": "3.2.2"}
proc = subprocess.Popen([sys.executable, "-c", spawn_script], env=env, start_new_session=True)
```

Reusable fixtures: `_DaemonHarness`, `_spawn_daemon`, `_find_free_port_in_range`,
`_wait_until_listening` (`tests/sync/test_orphan_sweep.py`); `_build_record`
(`tests/sync/test_daemon_owner_record.py`); `_write_state`
(`tests/sync/test_daemon_self_retirement.py`).

Lint / type gates (must be clean — NFR-005):

```bash
.venv/bin/ruff check src/specify_cli/sync tests/sync
.venv/bin/mypy --strict src/specify_cli/sync
```

## #1071 reconfirmation (FR-012)

The same-`$HOME` singleton scenario from #1071 is reproduced as an automated test in
the live harness; once green, close #1071 referencing that test.
