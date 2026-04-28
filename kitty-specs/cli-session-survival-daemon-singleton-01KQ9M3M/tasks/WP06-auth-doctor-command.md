---
work_package_id: WP06
title: spec-kitty auth doctor command
dependencies:
- WP01
- WP05
requirement_refs:
- C-008
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
- NFR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
created_at: '2026-04-28T09:17:32+00:00'
subtasks:
- T023
- T024
- T025
- T026
- T027
- T028
history:
- at: '2026-04-28T09:17:32Z'
  actor: claude
  action: created
authoritative_surface: src/specify_cli/cli/commands/_auth_doctor.py
execution_mode: code_change
mission_slug: cli-session-survival-daemon-singleton-01KQ9M3M
owned_files:
- src/specify_cli/cli/commands/_auth_doctor.py
- src/specify_cli/cli/commands/auth.py
- tests/auth/test_auth_doctor_report.py
- tests/auth/test_auth_doctor_repair.py
- tests/auth/test_auth_doctor_offline.py
priority: P1
status: planned
tags: []
---

# WP06 — `spec-kitty auth doctor` command

## ⚡ Do This First: Load Agent Profile

Load the assigned agent profile via `/ad-hoc-profile-load <agent_profile>` before any other tool call.

## Objective

Add the `spec-kitty auth doctor` typer subcommand. Default invocation is read-only and reports 7 sections (Identity, Tokens, Storage, Refresh Lock, Daemon, Orphans, Findings/Remediation). `--reset` calls `sweep_orphans()` from WP05. `--unstick-lock` calls `force_release()` from WP01 only when the lock is older than `--stuck-threshold` (default 60 s). `--json` emits the schema in `data-model.md`. Default invocation MUST NOT mutate state and MUST NOT make outbound network calls (C-007).

## Context

`auth doctor` is the user surface for the entire mission. It's how a mission-running developer with a misbehaving auth state diagnoses what happened and runs the right repair without learning `lsof`, `ps`, or `psutil`. The command is a diagnostic, not a gate — exit 1 means "critical finding present", not "test failure". Two opt-in repair flags resolve the two specific recovery paths (orphan daemons, stuck refresh lock).

**Key spec references**:
- FR-011: list of required diagnostic fields.
- FR-012: actionable remediation block on every problem.
- FR-013: `--reset` sweeps orphans.
- FR-014: `--unstick-lock` drops a stuck refresh lock past an age threshold.
- FR-015: default invocation MUST NOT mutate state.
- NFR-006: ≤ 3 s time-to-actionable.
- C-007: no network calls on default path (only 127.0.0.1 probes allowed).
- C-008: active repairs require explicit flags; no `--auto-fix`.

**Key planning references**:
- `contracts/auth-doctor.md` — the canonical CLI surface.
- `data-model.md` §"DoctorReport" — the JSON schema.
- `research.md` D9 (active-repair shape, decision moment DM-01KQ9M41VJENF0T6H83VRK5DYQ).

## Branch Strategy

- **Planning/base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP06`. Depends on WP01 + WP05; the resolver may rebase across both lanes before opening the worktree.

To start work:
```bash
spec-kitty implement WP06
```

## Subtasks

### T023 — `_auth_doctor.py` skeleton + `assemble_report()` (read-only)

**Purpose**: Build the data layer. Pure functions reading session, lock, daemon, and orphan state into a `DoctorReport` dataclass. No I/O side effects, no network, no Rich rendering yet.

**Files to create**: `src/specify_cli/cli/commands/_auth_doctor.py`.

**Steps**:
1. Module docstring stating purpose, the read-only-by-default contract, and C-007 compliance.
2. Define `@dataclass(frozen=True) class Finding`:
   ```python
   id: str
   severity: Literal["info", "warn", "critical"]
   summary: str
   remediation_command: str | None
   remediation_description: str | None
   ```
3. Define `@dataclass(frozen=True) class DoctorReport` per `data-model.md` §"DoctorReport":
   - `schema_version: int` (always `1`)
   - `generated_at: datetime` (UTC)
   - `auth_root: Path`
   - `session: SessionSummary | None`
   - `refresh_lock: LockSummary`
   - `daemon: DaemonSummary | None`
   - `orphans: list[OrphanDaemon]`
   - `findings: list[Finding]`
4. Define helper subtypes (`SessionSummary`, `LockSummary`, `DaemonSummary`) as frozen dataclasses with the fields from `data-model.md` §5.
5. Define `def assemble_report(*, stuck_threshold_s: float = 60.0) -> DoctorReport`:
   - Call `get_token_manager().get_current_session()` to read session state.
   - Call `read_lock_record(REFRESH_LOCK_PATH)` from WP01 to read the refresh lock.
   - Call `get_sync_daemon_status()` (existing helper in `sync/daemon.py`) to read daemon health.
   - Call `enumerate_orphans()` from WP05 for orphans.
   - Compute findings (T025).
   - Return `DoctorReport(...)`.

**Validation**: `python -c "from specify_cli.cli.commands._auth_doctor import assemble_report, DoctorReport"` succeeds; calling `assemble_report()` against a clean fixture state produces a `DoctorReport` with empty `findings` and the correct nested shapes.

### T024 — Rich rendering of 7 sections

**Purpose**: Build the human-facing layout. Reuse formatters from `_auth_status.py` (`format_duration`, `format_storage_backend`, `format_auth_method`).

**Steps**:
1. Define `def render_report(report: DoctorReport, console: Console) -> None`.
2. Section 1 — Identity: if `report.session` is `None`, print `[red]X Not authenticated[/red]` plus the "run spec-kitty auth login" hint. Else delegate to a small reused block adapted from `_auth_status._print_identity`.
3. Section 2 — Tokens: print access remaining and refresh remaining via `format_duration`. Handle `refresh_token_expires_at is None` (legacy) per `_auth_status` precedent.
4. Section 3 — Storage: print `format_storage_backend(session.storage_backend)`. If `report.session.in_memory_drift` is `True`, surface as `[dim]Note: persisted differs from in-memory (typical during in-flight refresh)[/dim]`.
5. Section 4 — Refresh Lock: if `LockSummary.held`, print holder PID, started_at (ISO), age_s, host. If `is_stuck`, render in red. Else "unheld".
6. Section 5 — Daemon: if active, print PID/port/package_version/protocol_version; else "not running".
7. Section 6 — Orphans: print a `rich.table.Table` with columns PID, Port, Package version. Empty rendering when none.
8. Section 7 — Findings & Remediation: for each finding, print `[severity] summary` + indented `Run: <command> — <description>`.

**Files**: `src/specify_cli/cli/commands/_auth_doctor.py`.

**Validation**: T028 captures rendered output and asserts each section header appears.

### T025 — Findings + remediation logic + exit-code policy

**Purpose**: Compute the `findings` list per `contracts/auth-doctor.md` §"Findings & Remediation".

**Steps**:
1. Inside `assemble_report` (or a `_compute_findings(report_inputs)` helper), build `findings` per the table:
   - F-001 (critical): `report.session is None` → "No active session"; remediation `spec-kitty auth login`.
   - F-002 (warn): `len(report.orphans) > 0` → "%d orphan daemon(s) detected" + ports list; remediation `spec-kitty auth doctor --reset`.
   - F-003 (critical): `report.refresh_lock.is_stuck` → "Refresh lock stuck (age %.1fs > threshold %.1fs)"; remediation `spec-kitty auth doctor --unstick-lock`.
   - F-004 (warn): daemon active but `package_version != installed_version` → "Daemon version mismatch"; remediation `spec-kitty sync restart`.
   - F-005 (info): rollout enabled but daemon not running → "Daemon not running; next CLI command will start it"; no remediation.
   - F-006 (warn): persisted/in-memory drift after no in-flight refresh → "Storage drift"; remediation `spec-kitty auth doctor` re-run.
   - F-007 (warn): `lock.host != socket.gethostname()` → "Lock holder on different host (NFS scenario)"; remediation `manual investigation`.
2. Define `compute_exit_code(findings) -> int`: return 1 if any `severity == "critical"` and the corresponding repair was not requested via flags; 0 otherwise. (Internal exception → 2 — handled in T027.)

**Files**: `src/specify_cli/cli/commands/_auth_doctor.py`.

**Validation**: T028 covers each finding's trigger condition and the exit-code policy.

### T026 — `--json` mode + offline assertion

**Purpose**: Machine-readable output for ops scripts. The schema is versioned (`schema_version: 1`) so future tranches can extend it without breaking consumers. Default invocation must not make outbound network calls (C-007).

**Steps**:
1. Define `def render_report_json(report: DoctorReport) -> str`: serialize via `dataclasses.asdict` + `json.dumps`. Convert `datetime` to ISO-8601 strings; convert `Path` to `str`.
2. Confirm assemble_report has zero outbound calls. Audit:
   - `get_current_session()` reads local state — OK.
   - `read_lock_record()` reads local file — OK.
   - `get_sync_daemon_status(timeout=0.5)` makes a 127.0.0.1 HTTP call — this is local, allowed by C-007.
   - `enumerate_orphans()` makes 127.0.0.1 HTTP calls — local, allowed.
   - No call to `httpx.AsyncClient`, `urllib.request.urlopen` against a non-127.0.0.1 host.
3. Add an `assert_no_remote_io` decorator-style helper (or a fixture-only assertion) that's used by the offline test in T028 to guarantee `httpx`/`urllib` are not called against non-local hosts during default invocation.

**Files**: `src/specify_cli/cli/commands/_auth_doctor.py`.

**Validation**: T028's `test_no_outbound_http` test patches `httpx.AsyncClient` and `urllib.request.urlopen` to fail; default invocation passes.

### T027 — Wire `doctor` typer subcommand

**Purpose**: Add the user-facing CLI entry point in `cli/commands/auth.py`. Lazy-import `_auth_doctor` per the existing pattern.

**Steps**:
1. In `src/specify_cli/cli/commands/auth.py`, add:
   ```python
   @app.command()
   def doctor(
       json_output: bool = typer.Option(False, "--json", help="Emit findings as JSON."),
       reset: bool = typer.Option(False, "--reset", help="Sweep orphan sync daemons."),
       unstick_lock: bool = typer.Option(False, "--unstick-lock", help="Force-release a stuck refresh lock."),
       stuck_threshold: float = typer.Option(60.0, "--stuck-threshold", help="Age (seconds) above which the refresh lock is considered stuck."),
   ) -> None:
       """Diagnose CLI auth and sync-daemon state. Default invocation is read-only."""
       from specify_cli.cli.commands._auth_doctor import doctor_impl
       try:
           exit_code = doctor_impl(
               json_output=json_output,
               reset=reset,
               unstick_lock=unstick_lock,
               stuck_threshold=stuck_threshold,
           )
       except Exception as exc:
           console.print(f"[red]Internal error during doctor: {exc}[/red]")
           raise typer.Exit(2) from exc
       raise typer.Exit(exit_code)
   ```
2. In `_auth_doctor.py`, define `doctor_impl(*, json_output, reset, unstick_lock, stuck_threshold) -> int`:
   - Call `report = assemble_report(stuck_threshold_s=stuck_threshold)`.
   - If `reset`: invoke `sweep_orphans(report.orphans)`; `report = assemble_report(...)` re-runs.
   - If `unstick_lock`: invoke `force_release(REFRESH_LOCK_PATH, only_if_age_s=stuck_threshold)`; re-run `report`.
   - If `json_output`: print `render_report_json(report)`; return `compute_exit_code(report.findings)`.
   - Else: call `render_report(report, console)`; return `compute_exit_code(report.findings)`.

**Files**: `src/specify_cli/cli/commands/auth.py`, `src/specify_cli/cli/commands/_auth_doctor.py`.

**Validation**: `spec-kitty auth doctor --help` shows the four flags with descriptions; running it on the maintainer's machine renders all 7 sections.

### T028 — Test trio: report + repair + offline

**Purpose**: Cover every section, every finding, every flag combination, and the C-007 offline guarantee.

**Files to create**: `tests/auth/test_auth_doctor_report.py`, `tests/auth/test_auth_doctor_repair.py`, `tests/auth/test_auth_doctor_offline.py`.

**Steps**:

**`test_auth_doctor_report.py`** (per contract):
- `test_renders_authenticated_no_findings` — healthy state ⇒ all 7 sections render; `findings == []`; exit 0.
- `test_renders_unauthenticated` — no session ⇒ F-001 critical; exit 1.
- `test_renders_orphan_finding` — orphan present ⇒ F-002 warn; exit 0 (warn is not critical).
- `test_renders_stuck_lock_finding` — lock record 120 s old ⇒ F-003 critical; exit 1.
- `test_renders_legacy_session` — `refresh_token_expires_at is None` ⇒ "server-managed (legacy)" line; no extra finding.
- `test_runs_under_three_seconds` — 50-port scan + healthy state ⇒ wall-clock < 3 s.
- `test_json_output_schema` — `--json` payload validates against `data-model.md` §5 schema.

**`test_auth_doctor_repair.py`**:
- `test_reset_sweeps_orphans` — orphan present; `--reset` invokes `sweep_orphans`; orphan terminates.
- `test_reset_noop_when_no_orphans` — no orphans; `--reset` does not call `sweep_orphans`.
- `test_unstick_drops_old_lock` — 120-s-old lock; `--unstick-lock` removes it.
- `test_unstick_preserves_fresh_lock` — 5-s-old lock; `--unstick-lock` is a no-op.
- `test_combined_flags_run_both` — `--reset --unstick-lock` runs both.

**`test_auth_doctor_offline.py`**:
- `test_no_outbound_http` — patch `httpx.AsyncClient` and `urllib.request.urlopen` with mocks that fail the test if invoked against any non-127.0.0.1 host; default `auth doctor` passes.
- `test_no_state_mutation_default` — capture file-system state before and after default invocation; assert no files removed, no new files except possibly the auth-store dir creation.

**Validation**: `pytest tests/auth/test_auth_doctor_*.py -v` passes.

## Definition of Done

- All 6 subtasks complete.
- `mypy --strict` zero errors on `_auth_doctor.py` and `auth.py`.
- `ruff check` clean.
- Coverage ≥ 90 % on `_auth_doctor.py`.
- All three test files pass.
- `spec-kitty auth doctor --help` renders the four flags clearly.
- C-007 offline assertion passes (`test_no_outbound_http`).
- NFR-006 wall-clock assertion passes (`test_runs_under_three_seconds`).
- `auth doctor` (no flags) does not mutate any state — verified by `test_no_state_mutation_default`.

## Risks

- **R3** — `auth doctor` itself depends on the broken refresh path. Counter: assemble_report calls only local-state readers + 127.0.0.1 probes; never invokes `TokenManager.refresh_if_needed`.
- **NFR-006** (3 s ceiling) — naive port scan with full HTTP handshake could approach 25 s worst case. Counter: 50 ms `connect_ex` pre-filter cuts the worst case to < 3 s.

## Reviewer Guidance

Verify:
1. Default invocation (no flags) makes ZERO mutations: no `Path.unlink`, no `psutil.terminate`, no `psutil.kill`, no `force_release`, no `storage.delete`.
2. Default invocation makes ZERO non-local network calls (only 127.0.0.1 probes for daemon/orphan health).
3. `--reset` and `--unstick-lock` are independent flags — no `--auto-fix` exists (C-008).
4. Exit codes: 0 (clean or non-critical), 1 (critical findings remain), 2 (internal exception).
5. The schema_version field is present in JSON output as `1`.
6. Reused formatters from `_auth_status.py` are not copy-pasted — they're imported.
