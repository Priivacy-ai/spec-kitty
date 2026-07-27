---
work_package_id: WP06
title: Live-subprocess version matrix
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
requirement_refs:
- C-006
- NFR-004
- NFR-005
- NFR-006
tracker_refs: []
planning_base_branch: fix/sync-daemon-orphan-cleanup
merge_target_branch: fix/sync-daemon-orphan-cleanup
branch_strategy: Planning artifacts for this mission were generated on fix/sync-daemon-orphan-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/sync-daemon-orphan-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
- T030
phase: Phase 4 - Regression
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "16552"
history:
- at: '2026-06-30T11:18:31Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/sync/test_daemon_orphan_classification.py
create_intent:
- tests/sync/_daemon_harness.py
- tests/sync/test_daemon_orphan_classification.py
execution_mode: code_change
model: ''
owned_files:
- tests/sync/_daemon_harness.py
- tests/sync/test_daemon_orphan_classification.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Live-subprocess version matrix

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile named in the frontmatter **before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is set, run `spec-kitty agent profile list` and pick the best match for `task_type: implement` on `authoritative_surface: tests/sync/`.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks (```python`, ```bash`).

---

## Objective

Prove the whole behavior with **real loopback listeners and real subprocess PIDs** (NFR-004) — not mocks. Build a small shared harness module and a version matrix across `3.2.2`/`3.2.3`/`3.2.4` that exercises the acceptance scenarios end-to-end through the production surfaces (startup reaper, `auth doctor`, `--reset`).

## Context & Constraints

Read before editing:
- [spec.md](../spec.md) NFR-004, NFR-006, C-006, AS-1..AS-5; [quickstart.md](../quickstart.md) (version-spoof recipe + serial run); [research.md](../research.md) DD-04.
- Reusable patterns (copy/adapt — do NOT edit those files): `_DaemonHarness`, `_spawn_daemon` (real `run_sync_daemon` subprocess, `start_new_session=True`), `_find_free_port_in_range`, `_wait_until_listening`, `_wait_until_port_free` in `tests/sync/test_orphan_sweep.py:35-197`; `_build_record` (`tests/sync/test_daemon_owner_record.py:55-73`); `_write_state` (`tests/sync/test_daemon_self_retirement.py:41-47`); per-worker HOME isolation (`tests/conftest.py:32-268`).
- **Version spoof (DD-04)**: `_get_package_version()` reads `SPEC_KITTY_CLI_VERSION` first (`sync/daemon.py:238-250`); set it on the subprocess env to spawn a daemon reporting an old version.

**Negative scope**: tests only — do NOT edit `src/`. Do NOT edit `tests/sync/test_orphan_sweep.py` (reuse via the new shared module instead of mutating it). Use an **isolated port sub-range** distinct from `test_orphan_sweep.py` (which uses `[9425,9450)`) — e.g. `[9400,9425)` — and run serial.

## Branch Strategy

- **Strategy**: lane-per-WP (from `lanes.json`)
- **Planning base branch**: `fix/sync-daemon-orphan-cleanup`
- **Merge target branch**: `fix/sync-daemon-orphan-cleanup`

> Depends on WP01–WP05 (needs the full behavior). Builds `tests/sync/_daemon_harness.py`, which WP07 and WP08 reuse.

## Subtasks & Detailed Guidance

### Subtask T026 – Shared harness module + version spoof

- **Purpose**: One reusable live-subprocess harness for this and later WPs.
- **Files**: `tests/sync/_daemon_harness.py` (new).
- **Steps**:
  1. Provide a `DaemonHarness` class: `spawn_daemon(port, token, *, version=None, scope_root=None, home=None)` (sets `SPEC_KITTY_CLI_VERSION` and, where needed, `$HOME`/daemon-root env to simulate cross-root), `spawn_plain(port)` (non-SK listener), `write_state_file(...)`, port→PID tracking (handles macOS `net_connections` `AccessDenied`), and `shutdown()` with escalating termination.
  2. Re-expose the port/wait helpers (`find_free_port_in_range`, `wait_until_listening`, `wait_until_port_free`).
- **Notes**: This is a non-test helper module (no `test_` prefix) so pytest does not collect it; WP07/WP08 import it.

### Subtask T027 – Same-scope stale cleanup + no redundant spawn (AS-1, FR-006/007/008)

- **Purpose**: The headline fix.
- **Files**: `tests/sync/test_daemon_orphan_classification.py` (new).
- **Steps**: Spawn 2–3 same-scope daemons reporting `3.2.2`/`3.2.3` on distinct in-range ports; record one as the singleton. Drive the startup reaper path (or `cleanup_orphan_sync_daemons`) and assert the stale ones are reaped (`safe_auto`, FR-008) and **no additional daemon** is created (FR-007). One version-matrix case per `3.2.2`/`3.2.3`/`3.2.4`.
- **Notes**: Assert by port-closed + PID-gone, not just process exit (mirror the existing harness checks).

### Subtask T028 – Ambiguous survives (AS-2, D-01)

- **Purpose**: Never silently kill ambiguous daemons.
- **Files**: `tests/sync/test_daemon_orphan_classification.py`.
- **Steps**: Stand up (a) a **pre-marker** daemon (spawn without the daemon-root scope marker), (b) a **cross-`$HOME`** daemon (different `$HOME`/daemon-root env), and (c) a **wedged** listener (real socket that never answers `/api/health`). Assert each classifies `operator_required` and is **not** killed by startup auto-clean.
- **Notes**: The wedged case can be a `spawn_plain` socket that accepts but never responds → `unresponsive` (D-01).

### Subtask T029 – `auth doctor` scan + `--reset` reporting (AS-3/AS-4, FR-004/005)

- **Purpose**: End-to-end CLI proof.
- **Files**: `tests/sync/test_daemon_orphan_classification.py`.
- **Steps**: With a mix of `safe_auto` + `operator_required` + a third-party listener live, invoke `auth doctor --json` and assert every candidate's `cleanup_class` is present; invoke `auth doctor --reset --json` and assert `reset_result.swept/skipped/failed` match the real outcomes; invoke `--reset --force` and assert `operator_required` (same-machine, but ambiguous) are then attempted.
- **Notes**: Drive the CLI via its callable entry (e.g. `doctor_impl`) or a `subprocess` invocation — prefer the in-process callable for speed where it still exercises real listeners.

### Subtask T030 – Isolation + skips + SAAS env

- **Purpose**: Deterministic, CI-safe.
- **Files**: `tests/sync/test_daemon_orphan_classification.py`.
- **Steps**: `@pytest.mark.integration`; `skipif(sys.platform == "win32")` for socket-bound cases; use the isolated `[9400,9425)` sub-range; document the serial `-n0` requirement at the top of the file. Where hosted auth/sync is touched, gate with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` (C-006).
- **Notes**: Add a module docstring noting "real-port serial suite — run with `-n0`".

## Test Strategy

- `PWHEADLESS=1 .venv/bin/pytest tests/sync/test_daemon_orphan_classification.py -n0 -q` (serial, real ports).
- `.venv/bin/ruff check tests/sync/_daemon_harness.py tests/sync/test_daemon_orphan_classification.py` — zero issues. (`mypy --strict` on test helpers where the repo applies it.)

## Risks & Mitigations

- **Port collisions / flakiness (NFR-006)**: isolated sub-range + `-n0` + the harness port→PID map + `wait_until_*` polling (no fixed sleeps).
- **Leaked subprocesses**: `shutdown()` in fixture teardown must escalate terminate→kill for every spawned proc.
- **macOS `net_connections` AccessDenied**: rely on the harness's recorded port→PID map, not live enumeration.

## Review Guidance

- Verify the suite uses **real** subprocesses + real ports (no HTTP/socket mocks) for the daemon layer (NFR-004).
- Verify the version matrix covers `3.2.2`/`3.2.3`/`3.2.4` via `SPEC_KITTY_CLI_VERSION`.
- Verify AS-1 (no redundant spawn) and AS-2 (ambiguous survives) both proven.
- Verify the file is serial-safe (`-n0`) and win32-skipped.

## Activity Log

- 2026-06-30T11:18:31Z – system – Prompt created.
- 2026-06-30T13:13:38Z – claude:sonnet:python-pedro:implementer – shell_pid=7594 – Assigned agent via action command
- 2026-06-30T13:34:31Z – claude:sonnet:python-pedro:implementer – shell_pid=7594 – Live version matrix: same-scope stale reaped (3.2.2/3.2.3/3.2.4, no redundant spawn), pre-marker/cross-HOME/wedged survive, auth doctor json+reset verified; real subprocesses, serial -n0, isolated [9400,9425); shared _daemon_harness.py; mypy+ruff clean
- 2026-06-30T13:35:19Z – claude:opus:reviewer-renata:reviewer – shell_pid=16552 – Started review via action command
- 2026-06-30T13:40:33Z – user – shell_pid=16552 – Review passed: real-subprocess version matrix (3.2.2/3.2.3/3.2.4 via SPEC_KITTY_CLI_VERSION on a real run_sync_daemon Popen, start_new_session=True). AS-1 same-scope stale reaped (port-closed+PID-gone) + singleton survives + no redundant spawn; AS-2 pre-marker/cross-HOME/wedged classify operator_required and survive auto-clean; AS-3/4 auth doctor --json cleanup_class + --reset swept/skipped/failed + --force operator_required attempted via real doctor_impl. No daemon leak (pgrep clean post-run). Serial -n0, isolated [9400,9425), win32-skipped. The 1 skip is the C-006 SAAS env gate (SPEC_KITTY_ENABLE_SAAS_SYNC). mypy --strict + ruff clean. Minor non-blocking nit: dead module constants _SCOPE_ARG_PREFIX/_EXEC_ARG_PREFIX duplicate production DAEMON_*_ARG_PREFIX (harness uses the imported production ones); safe to drop.
