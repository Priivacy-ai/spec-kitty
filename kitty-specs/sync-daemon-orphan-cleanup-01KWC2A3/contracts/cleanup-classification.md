# Contract: Cleanup Classification Engine

**Module (new)**: `src/specify_cli/sync/classification.py`
**Requirements**: FR-001, FR-002, FR-003, FR-008

## Function

```python
def classify_candidate(
    *,
    port: int,
    listener_pid: int | None,
    health: HealthProbe | None,       # parsed /api/health, or None if unresponsive
    cmdline: Sequence[str] | None,    # process argv via psutil, or None
    foreground_scope: str,            # _daemon_scope_root() of this runtime
    foreground_exec_scope: str,       # canonical_executable_scope() of this runtime
    recorded_singleton: SingletonRef | None,  # state-file (pid, port)
) -> DaemonIdentityRecord:
    ...
```

- **Pure / deterministic**: no process signals, no filesystem writes, no network. All probing happens in the caller; the classifier only decides. This makes it unit-testable in isolation (Sonar-friendly extraction).
- Returns a fully-populated `DaemonIdentityRecord` (fields in `../data-model.md`) including `daemon_family="sync"`, `cleanup_class`, and `skip_reason`.

## Classification rules (normative)

The engine implements the decision table in `../data-model.md` (rows 1–9). Key guarantees:

1. **Primary kill authority is the daemon-root scope marker** (`singleton_scope_id`), not `owner.json` (FR-003). `owner_present` is recorded for reporting but never affects `cleanup_class`.
2. **`safe_auto` requires a live self-report** whose `pid`/`port` match the listener (D-01). Unresponsive ⇒ `operator_required` (`skip_reason=unresponsive`).
3. **Version/executable mismatch is evidence, not a gate** (FR-008): once scope + responsiveness + spawn-shape + not-singleton hold, a differing `package_version`/`executable_summary` yields `safe_auto`, not a skip.
4. **`port` is always in `[9400,9450)`** for any record emitted (NFR-001); the caller never hands the sync engine an out-of-range or dashboard port.

## Caller obligations (boundary — C-002, NFR-001)

- The sync scan enumerates only `range(DAEMON_PORT_START, DAEMON_PORT_START + DAEMON_PORT_MAX_ATTEMPTS)` = `[9400,9450)`.
- Any signal/kill derived from a record MUST assert `record.port` is in range and `record.daemon_family == "sync"` before calling `_sweep_daemon_process`.
- The classifier MUST NOT be invoked with dashboard-range ports; cross-family inputs are a caller bug, caught by the boundary regression matrix (IC-05).

## Test surface

- Unit: feed synthetic inputs covering every decision-table row (no subprocess).
- Integration: drive via the live `_DaemonHarness` (IC-04) with real listeners and real PIDs.
