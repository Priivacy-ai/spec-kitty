# Contract — `spec-kitty auth doctor`

> Implements FR-011, FR-012, FR-013, FR-014, FR-015; NFR-006; C-007, C-008.
> Owned by WP06 (`src/specify_cli/cli/commands/_auth_doctor.py` and the
> new `@app.command()` `doctor` in `src/specify_cli/cli/commands/auth.py`).

## CLI surface

```
Usage: spec-kitty auth doctor [OPTIONS]

  Diagnose CLI auth and sync-daemon state. Default invocation is read-only.

Options:
  --json                 Emit findings as a JSON document instead of Rich layout.
  --reset                Sweep orphan sync daemons in the reserved port range.
  --unstick-lock         Force-release the machine-wide refresh lock if
                         its age exceeds the stuck threshold.
  --stuck-threshold S    Age (seconds) above which the refresh lock is
                         considered stuck. Default: 60.
  -h, --help             Show this message and exit.
```

`--reset` and `--unstick-lock` are independent flags; passing both runs
both repairs in that order. There is no `--auto-fix` (C-008).

## Default invocation (no flags) — schema

Sections rendered in order. Each section has a Rich representation and
a JSON representation.

### 1. Identity

Reuses helpers from `_auth_status.py`. Renders the same
`User / User ID / Teams / Auth method` block as `auth status` for
authenticated sessions. For unauthenticated state, prints the existing
"Not authenticated" message and continues to render diagnostic
sections.

### 2. Tokens

| Field | Source | Rendered as |
|---|---|---|
| Access remaining | `session.access_token_expires_at - now()` | `format_duration(s)` (existing helper) |
| Refresh remaining | `session.refresh_token_expires_at - now()` | `format_duration(s)`, or `"server-managed (legacy)"` for `None` |

### 3. Storage

| Field | Source |
|---|---|
| Backend | `format_storage_backend(session.storage_backend)` |
| Persisted-vs-in-memory drift | `session_id` and `refresh_token` of `_storage.read()` compared against `tm.get_current_session()` |

If drift is detected, surface as `info` (not `warn`) — drift is
expected during a refresh transaction, just not after one.

### 4. Refresh Lock

| Field | Source |
|---|---|
| Held? | `read_lock_record(REFRESH_LOCK_PATH) is not None` |
| Holder PID | `record.pid` |
| Acquired at | `record.started_at` |
| Age | `record.age_s` |
| Stuck? | `record.age_s > stuck_threshold` |
| Same host? | `record.host == socket.gethostname()` |

### 5. Daemon

| Field | Source |
|---|---|
| Active? | `get_sync_daemon_status().healthy` (existing function) |
| PID | from state file |
| Port | from state file |
| Package version | from `/api/health` response |
| Protocol version | from `/api/health` response |

### 6. Orphans

A table of any orphan daemons (`enumerate_orphans()`). Empty table if
none.

| Column | Source |
|---|---|
| PID | `OrphanDaemon.pid` |
| Port | `OrphanDaemon.port` |
| Package version | `OrphanDaemon.package_version` |

### 7. Findings & Remediation

Compute the findings list:

| ID | Trigger | Severity | Remediation command |
|---|---|---|---|
| F-001 | No session loaded | `critical` | `spec-kitty auth login` |
| F-002 | Orphans present | `warn` | `spec-kitty auth doctor --reset` |
| F-003 | Refresh lock stuck (`age > stuck_threshold`) | `critical` | `spec-kitty auth doctor --unstick-lock` |
| F-004 | Daemon running but version mismatches package version | `warn` | `spec-kitty sync restart` (existing) |
| F-005 | Daemon expected (rollout enabled) but not running | `info` | next CLI command will start it |
| F-006 | Persisted/in-memory drift after no in-flight refresh | `warn` | `spec-kitty auth doctor` re-run after a CLI command |
| F-007 | Lock holder is on a different host (NFS scenario) | `warn` | manual investigation; not auto-resolvable |

Each finding renders as: `[severity] summary` followed by an indented
`Run: <command>` line. When `findings` is empty, the report ends with
`No problems detected.`

## Exit codes

| Exit | Meaning |
|---|---|
| 0 | Report rendered. No `critical` findings remain after any repairs the user requested. |
| 1 | Report rendered, but at least one `critical` finding remains. (E.g. `auth doctor` was run without `--unstick-lock` while the lock is stuck.) |
| 2 | Internal error (exception during diagnostic gathering). Stack trace printed; report is partial. |

`auth doctor` is a diagnostic, not a gate — exit 1 is informational, not
a CI failure pattern. Scripts that want to fail on critical findings
must check the JSON output.

## `--json` output (machine-readable)

See `data-model.md` §"DoctorReport JSON schema" for the full shape.
The schema is versioned (`schema_version: 1`) so future tranches can
extend it without breaking consumers.

## `--reset` semantics

1. Run the default report once (read-only).
2. If `findings` contains `F-002`: call `sweep_orphans(enumerate_orphans())`.
3. Re-run the report (post-reset) and print the sweep summary
   (`<n> orphans swept, <m> failed`).
4. Exit code based on post-reset state.

`--reset` is a no-op when no orphans are detected.

## `--unstick-lock` semantics

1. Run the default report once (read-only).
2. If `findings` contains `F-003`: call
   `force_release(REFRESH_LOCK_PATH, only_if_age_s=stuck_threshold)`.
3. Re-run the report and print the unstick outcome.
4. Exit code based on post-unstick state.

`--unstick-lock` is a no-op when the lock is not stuck. The
`only_if_age_s` parameter prevents the user from accidentally dropping
a healthy in-flight lock.

## C-007 enforcement (no network calls in default invocation)

`tests/auth/test_auth_doctor_offline.py` patches `httpx.AsyncClient`,
`urllib.request.urlopen`, and `socket.create_connection` with mocks
that fail the test if invoked. The test then runs `auth doctor` with
no flags and asserts no patch was triggered.

The local-only probes that `enumerate_orphans()` performs are
**127.0.0.1** TCP connects, which are explicitly allowed (the contract
calls them "local" and excludes them from C-007's scope; see C-007
text: "MUST NOT require network access").

## NFR-006 enforcement (≤3 s time-to-actionable)

`auth doctor` uses tight per-probe timeouts (`0.5 s` for each daemon
health probe; total worst case 50 × 0.5 s = 25 s with no daemons,
which violates NFR-006). Mitigation: connection-attempt timeout drops
to 50 ms for `connect_ex` before the HTTP probe, so closed ports are
filtered in <1 s total. This brings the typical run to <300 ms and the
maximum to <3 s in adversarial cases (every port answering slowly).

`tests/auth/test_auth_doctor_report.py::test_runs_under_three_seconds`
asserts a 3-second wall-clock ceiling under realistic fixture state.

## Test contract

### `tests/auth/test_auth_doctor_report.py`

| Test | Predicate |
|---|---|
| `test_renders_authenticated_no_findings` | Healthy state ⇒ all sections render; findings empty; exit 0. |
| `test_renders_unauthenticated` | No session ⇒ F-001 critical; report still complete; exit 1. |
| `test_renders_orphan_finding` | One orphan present ⇒ F-002 warn; report completes; exit 0 (warn is not critical). |
| `test_renders_stuck_lock_finding` | Lock record 120 s old ⇒ F-003 critical; exit 1. |
| `test_renders_legacy_session` | `refresh_token_expires_at is None` ⇒ "server-managed (legacy)" string; no extra finding. |
| `test_runs_under_three_seconds` | 50-port scan + healthy state completes in <3 s. |
| `test_json_output_schema` | `--json` output validates against the schema in `data-model.md` §5. |

### `tests/auth/test_auth_doctor_repair.py`

| Test | Predicate |
|---|---|
| `test_reset_sweeps_orphans` | Two daemons, one orphan ⇒ `--reset` invokes `sweep_orphans`; orphan terminated. |
| `test_reset_noop_when_no_orphans` | No orphans ⇒ `--reset` does not call `sweep_orphans`. |
| `test_unstick_drops_old_lock` | Lock 120 s old ⇒ `--unstick-lock` removes lock file. |
| `test_unstick_preserves_fresh_lock` | Lock 5 s old ⇒ `--unstick-lock` is a no-op; lock still held. |
| `test_combined_flags_run_both` | `--reset --unstick-lock` runs both repairs. |

### `tests/auth/test_auth_doctor_offline.py`

| Test | Predicate |
|---|---|
| `test_no_outbound_http` | Default invocation makes zero `httpx`/`urllib` outbound calls (only 127.0.0.1 connects allowed). |
| `test_no_state_mutation_default` | After default invocation: no files removed, no processes terminated, no locks released. |
