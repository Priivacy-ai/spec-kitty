---
work_package_id: WP03
title: Port-scan classification + reset reporting
dependencies:
- WP01
requirement_refs:
- C-002
- FR-001
- FR-005
- NFR-001
- NFR-005
tracker_refs: []
planning_base_branch: fix/sync-daemon-orphan-cleanup
merge_target_branch: fix/sync-daemon-orphan-cleanup
branch_strategy: Planning artifacts for this mission were generated on fix/sync-daemon-orphan-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/sync-daemon-orphan-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
phase: Phase 2 - Cleanup authority
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "22145"
history:
- at: '2026-06-30T11:18:31Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/orphan_sweep.py
create_intent:
- tests/sync/test_orphan_sweep_classification.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/sync/orphan_sweep.py
- tests/sync/test_orphan_sweep_classification.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Port-scan classification + reset reporting

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile named in the frontmatter **before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is set, run `spec-kitty agent profile list` and pick the best match for `task_type: implement` on `authoritative_surface: src/specify_cli/sync/orphan_sweep.py`.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks (```python`, ```bash`).

---

## Objective

Upgrade the operator-facing port-scan surface (`sync/orphan_sweep.py`) so it (a) builds a full `DaemonIdentityRecord` per in-range listener via the WP01 classifier, (b) returns a **structured `ResetResult`** (`swept`/`skipped`/`failed` with per-entry detail) instead of bare counts, and (c) gains a **force-aware** sweep that cleans `safe_auto` by default and `operator_required` only when `include_operator_required=True` (D-02). This is the data layer behind `auth doctor [--reset]` (WP05).

## Context & Constraints

Read before editing:
- [contracts/auth-doctor-json.md](../contracts/auth-doctor-json.md) (the `orphans[]` record + `reset_result` shape), [contracts/cleanup-classification.md](../contracts/cleanup-classification.md), [data-model.md](../data-model.md) ResetResult; [spec.md](../spec.md) FR-001, FR-005, NFR-001, C-002, C-004.
- WP01 provides `classify_candidate` and the probe/record types — import and use them.

Current code (`sync/orphan_sweep.py`):
- `enumerate_orphans()` (`:273-330`) — scans `[9400,9450)`, TCP connect-check (50 ms) then `/api/health` probe (500 ms), `_is_spec_kitty_daemon` (protocol+package keys), skips singleton port, resolves PID via `psutil.net_connections`/`lsof`.
- `sweep_orphans`/`_sweep_one` (`:333-380`) — HTTP shutdown → signal escalation via `_sweep_daemon_process`.
- `SweepReport` (`:107-120`): `swept`, `failed`, `duration_s` — **counts only, no skipped, no identity**.
- Range constants imported from `daemon.py` (`DAEMON_PORT_START`, `DAEMON_PORT_MAX_ATTEMPTS`).

**Negative scope**: do NOT edit `daemon.py`/`owner.py`/`classification.py`. The startup reaper is WP02's surface — this WP is the `auth doctor`/`--reset` surface only. Reuse `_sweep_daemon_process` (owner.py) as-is for kills.

## Branch Strategy

- **Strategy**: lane-per-WP (from `lanes.json`)
- **Planning base branch**: `fix/sync-daemon-orphan-cleanup`
- **Merge target branch**: `fix/sync-daemon-orphan-cleanup`

> Depends on WP01. Parallel-safe with WP02 (different file).

## Subtasks & Detailed Guidance

### Subtask T011 – Build a record per in-range listener

- **Purpose**: Replace the thin orphan tuple with a classified identity record.
- **Files**: `src/specify_cli/sync/orphan_sweep.py`.
- **Steps**:
  1. In `enumerate_orphans`, for each listening in-range port: parse the health payload into a `HealthProbe` (set `responded=False` when no/invalid health — wedged), resolve `listener_pid`, read that pid's cmdline (psutil) to derive `singleton_scope_id`/`spawn_shape_ok`/`executable_summary` (reuse the same `owner.py` helpers WP02 uses), then call `classify_candidate`.
  2. Return the list of `DaemonIdentityRecord`s (keep a back-compatible accessor for the existing `orphans` consumers, or update them within this file).
- **Notes**: `is_recorded_singleton` excludes the live daemon. `never_touch`/out-of-range never enter the list.

### Subtask T012 – In-range / family guard before any signal (NFR-001, C-002, C-004)

- **Purpose**: Hard boundary — sync cleanup never leaves `[9400,9450)` and never kills on port-presence alone.
- **Files**: `src/specify_cli/sync/orphan_sweep.py`.
- **Steps**:
  1. Before any `_sweep_daemon_process` call, assert `record.daemon_family == "sync"` and `9400 <= record.port < 9450`; raise/log-and-skip otherwise.
  2. Never sweep a `never_touch` record. Only `safe_auto` (always) and `operator_required` (force) are actionable.
- **Notes**: This guard is the code-level enforcement that WP07's boundary matrix verifies end-to-end.

### Subtask T013 – Structured ResetResult

- **Purpose**: Exact reporting (FR-005).
- **Files**: `src/specify_cli/sync/orphan_sweep.py`.
- **Steps**:
  1. Introduce a `ResetResult` dataclass with `swept: list[SweptEntry]`, `skipped: list[SkippedEntry]`, `failed: list[FailedEntry]` matching `data-model.md` (swept carries `pid,port,package_version,protocol_version,cleanup_path,reason`; skipped carries `pid,port,cleanup_class,skip_reason`; failed carries `pid,port,failure_reason`).
  2. `cleanup_path` records which step closed the port: `http_shutdown` | `terminate` | `kill` (derive from `_sweep_one`'s escalation).
- **Notes**: Keep `SweepReport` if other callers use it, or migrate them within scope; grep first.

### Subtask T014 – Force-aware sweep (D-02)

- **Purpose**: Default sweeps `safe_auto`; `operator_required` only under force.
- **Files**: `src/specify_cli/sync/orphan_sweep.py`.
- **Steps**:
  1. Add `include_operator_required: bool = False` to the sweep entry point.
  2. Default: sweep `safe_auto`, list `operator_required` in `skipped` (with `cleanup_class`/`skip_reason`). With the flag: also attempt `operator_required`; successes → `swept`, survivors → `failed`.
- **Notes**: `auth doctor --force` (WP05) flips this flag; this WP just provides the capability + return shape.

### Subtask T015 – Tests

- **Purpose**: Cover record build, the in-range guard, ResetResult shape, and force behavior — fast/deterministic where possible.
- **Files**: `tests/sync/test_orphan_sweep_classification.py` (new).
- **Steps**: Prefer fake-health/fake-pid doubles for unit speed; assert: record built with correct `cleanup_class`; out-of-range/never_touch never swept; ResetResult arrays populated with the right per-entry fields and `cleanup_path`; default sweep skips `operator_required`, force sweeps it. Mark `@pytest.mark.unit` (live-port coverage is WP06/WP07).
- **Notes**: Do not bind real ports here — that is the live matrix's job; keep this file mock-light but subprocess-free.

## Test Strategy

- `PWHEADLESS=1 .venv/bin/pytest tests/sync/test_orphan_sweep_classification.py -q`.
- Regression: `PWHEADLESS=1 .venv/bin/pytest tests/sync/test_orphan_sweep.py -n0 -q` (existing live suite — must stay green).
- `.venv/bin/ruff check src/specify_cli/sync/orphan_sweep.py tests/sync/test_orphan_sweep_classification.py` + `.venv/bin/mypy --strict src/specify_cli/sync/orphan_sweep.py` — zero issues.

## Risks & Mitigations

- **Breaking `enumerate_orphans` consumers**: `_auth_doctor.py` (WP05) reads it — keep a stable accessor or coordinate the shape via `contracts/auth-doctor-json.md` (WP05 depends on WP03).
- **Leaving the range**: the T012 guard is mandatory; WP07 will try to break it with dashboard/third-party ports.
- **Wedged listeners**: `responded=False` → `operator_required` (not swept by default) — matches D-01.

## Review Guidance

- Verify the pre-signal in-range + `daemon_family=="sync"` guard exists (NFR-001/C-002) and that `never_touch` is never swept (C-004).
- Verify `ResetResult` carries exact per-entry detail (FR-005) including `cleanup_path`.
- Verify default vs `include_operator_required` behavior (D-02).
- Verify the existing `test_orphan_sweep.py` live suite still passes.

## Activity Log

- 2026-06-30T11:18:31Z – system – Prompt created.
- 2026-06-30T12:08:11Z – claude:sonnet:python-pedro:implementer – shell_pid=13697 – Assigned agent via action command
- 2026-06-30T12:22:13Z – claude:sonnet:python-pedro:implementer – shell_pid=13697 – Classified scan + ResetResult(swept/skipped/failed) + in-range guard + force; mypy+ruff clean on src AND test; existing orphan_sweep suite green
- 2026-06-30T12:23:09Z – claude:opus:reviewer-renata:reviewer – shell_pid=22145 – Started review via action command
- 2026-06-30T12:28:55Z – user – shell_pid=22145 – Review passed: FR-001 classify_candidate invoked in live enumerate_identity_records scan (orphan_sweep.py:548); NFR-001/C-002/C-004 guard _assert_safe_to_sweep fires before every _sweep_one_with_path/_sweep_daemon_process call and cannot be bypassed (operator_required-without-force short-circuits to skipped); FR-005 ResetResult swept/skipped/failed with cleanup_path in {http_shutdown,terminate,kill} proven by tests; D-02 default sweeps safe_auto + lists operator_required in skipped, force attempts it (success->swept, survivor->failed); back-compat enumerate_orphans/sweep_orphans/OrphanDaemon/SweepReport intact for _auth_doctor.py. 36 classification tests + 9 live orphan_sweep tests pass; ruff + mypy --strict clean on both files; scope limited to 2 owned files. NOTE non-blocking: unused '# type: ignore[misc]' at test line 446 silences nothing (mypy --strict gate + CI both clean since they use the flag form on src/ only) — please drop it on next touch.
