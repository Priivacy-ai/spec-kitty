---
work_package_id: WP03
title: 'sync.py: status/check expansion, sync-now wiring, gate delegation'
dependencies:
- WP01
- WP02
requirement_refs:
- FR-002
- FR-004
- FR-005
- NFR-001
- NFR-002
- NFR-004
planning_base_branch: kitty/pr/mvp-sync-boundary-cli-01KRVCQS
merge_target_branch: kitty/pr/mvp-sync-boundary-cli-01KRVCQS
branch_strategy: Planning artifacts for this mission were generated on kitty/pr/mvp-sync-boundary-cli-01KRVCQS. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/pr/mvp-sync-boundary-cli-01KRVCQS unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
- T015
- T016
agent: "codex:gpt-5:reviewer-rita:reviewer"
shell_pid: "94089"
history:
- at: '2026-05-18T08:00:00Z'
  actor: planner
  note: Initial generation
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/sync.py
execution_mode: code_change
mission_id: 01KRX11MCY70M5NFBBHT4DQHJ2
mission_slug: mvp-cli-sync-boundary-completion-01KRX11M
owned_files:
- src/specify_cli/cli/commands/sync.py
- tests/sync/test_sync_status_boundary_check.py
- tests/sync/test_daemon_owner_record.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, run the `ad-hoc-profile-load` skill to adopt the assigned profile (`implementer-ivan`, role: `implementer`). The profile sets the identity, governance scope, and boundaries for the work in this WP.

## Objective

Make `src/specify_cli/cli/commands/sync.py` the canonical surface for daemon-owner coherence: a single shared failure-set builder consumed by both `sync status --check` and the preflight (`run_preflight` from WP01), with full FR-005 field coverage on output, a `--check --json` mode, and an in-line `run_preflight` call gating `sync now` before any enqueue.

Authoritative contracts:
- [`contracts/sync-boundary-preflight.md`](../contracts/sync-boundary-preflight.md)
- [`contracts/sync-status-output.md`](../contracts/sync-status-output.md)

## Context

- This WP owns `sync.py` exclusively, plus the two test files exercising it.
- Touch points enumerated in `plan.md`: `:342` (`_require_daemon_owner_coherence`), `:1196` (`sync now` call site), `:1286` (`_build_boundary_check_failures`), `:1329` (`sync status`), `:1503` (identity boundary section), `:1655` (`--check` coherence gate), `:1764` (`sync doctor`), `:2007` (orphan daemon record section).
- WP01 supplies `run_preflight`, `PreflightResult`, `OwnerMismatch`, `MismatchField`. WP02 supplies the extended `detect_legacy_rows_for_scope` return shape.

## Branch strategy

- Planning/base branch: `kitty/pr/mvp-sync-boundary-cli-01KRVCQS`.
- Final merge target: `kitty/pr/mvp-sync-boundary-cli-01KRVCQS`.
- Execution worktree: allocated per computed lane from `lanes.json`. Depends on WP01; runs in parallel with WP04 (different files).

## Subtasks

### T010 — Refactor `_build_boundary_check_failures` into a reusable single source of truth

**Purpose**: Eliminate drift between `sync status --check` and the preflight by routing both through one builder.

**Steps**:

1. Read the current `_build_boundary_check_failures()` (around `sync.py:1286`).
2. Refactor so it takes a `ForegroundIdentity` (or constructs one if not provided) and returns a structured failure set: list of `OwnerMismatch`, list of orphan records, legacy event/body subtotals.
3. Export it for import by `src/specify_cli/sync/preflight.py` (move to `src/specify_cli/sync/coherence.py` if cyclic-import pressure emerges; otherwise leave in `sync.py` and have the preflight import via a lazy import — preferred to avoid two-file change).
4. `run_preflight` from WP01 now calls `_build_boundary_check_failures(...)` to produce its mismatches and orphan list. `PreflightResult` adds auth-required-and-absent on top.

**Files**:
- `src/specify_cli/cli/commands/sync.py` (edited)

**Validation**:
- No regression in existing tests touching `_build_boundary_check_failures`.

### T011 — Rewrite `_require_daemon_owner_coherence` as a thin wrapper over `run_preflight`

**Purpose**: Existing call sites keep working; the wrapper becomes one line.

**Steps**:

1. Read `_require_daemon_owner_coherence()` at `sync.py:342`. Note its current exit code (should be 2) and message format.
2. Rewrite the body to:
   - Call `run_preflight(repo_root=..., require_auth=False)` (the wrapper does not need to enforce auth-required; specific callers do via `sync now` and `setup-plan`).
   - If `result.ok` is `False`, call `result.render(console)` and exit `2`.
   - If `result.ok` is `True`, return.
3. Preserve the public signature so any third-party invoker keeps working.

**Files**:
- `src/specify_cli/cli/commands/sync.py` (edited)

**Validation**:
- `tests/sync/test_daemon_owner_record.py` continues to pass.

### T012 — Wire `run_preflight` into `sync now`

**Purpose**: Refuse `sync now` before any enqueue or flush when boundary is incoherent.

**Steps**:

1. Find the call site around `sync.py:1196`. Replace the inline gate with a call to `run_preflight(repo_root=..., require_auth=True)`.
2. If `result.ok` is `False`, call `result.render(console)` and exit `2` *before* any DB write or SaaS flush.
3. If `result.ok` is `True`, continue.

**Files**:
- `src/specify_cli/cli/commands/sync.py` (edited)

**Validation**:
- New test in `test_sync_status_boundary_check.py` (T016) verifies `sync now` refuses on each documented split-brain shape.

### T013 — Extend `sync status` printed fields per contract

**Purpose**: Match `contracts/sync-status-output.md` exactly so operators see every field they need.

**Steps**:

1. Open `sync.py:1329` (`sync status`) and `:1503` (identity boundary section).
2. Extend the printed output to include, in this order:
   - Foreground: package version, executable path, source path, server URL, team/user, queue DB path.
   - Daemon owner record: status (`present` / `absent` / `orphan`), PID, port, package version, executable path, source path, server URL, team/user, queue DB path.
   - Active queue: path, event count, body upload count.
   - Legacy queue: path, event count, body upload count, rows-in-scope.
   - Mismatches count.
   - Orphan records count.
3. When mismatches > 0, append the mismatch detail block.
4. Use Rich panels / tables consistent with the rest of the file.

**Files**:
- `src/specify_cli/cli/commands/sync.py` (edited)

**Validation**:
- Snapshot tests / asserts on field presence in `test_sync_status_boundary_check.py`.

### T014 — Add `--check --json` mode

**Purpose**: Machine-consumable shape for scripting and CI.

**Steps**:

1. Locate the `sync status --check` command around `sync.py:1655`. Add a `--json` flag.
2. When `--json` is set, suppress the human-readable block and emit `PreflightResult.to_dict()` enriched with `exit_code` and the full identity-boundary fields per `contracts/sync-status-output.md`.
3. Exit code mapping unchanged: 0 if all checks pass, 2 otherwise.

**Files**:
- `src/specify_cli/cli/commands/sync.py` (edited)

**Validation**:
- Test asserts `--check --json` output is a single JSON object on stdout with all documented top-level keys.

### T015 — Update orphan-daemon section to share preflight categories

**Purpose**: Eliminate the risk that `sync doctor` and `doctor orphan-daemons` disagree.

**Steps**:

1. Open the orphan-daemon section in `sync doctor` around `sync.py:2007`.
2. Replace ad-hoc orphan-detection logic with a call to `list_orphan_records()` (existing). Render orphans via the same Rich table format used by `PreflightResult.render`.
3. Confirm `doctor orphan-daemons` in `src/specify_cli/cli/commands/doctor.py` also calls `list_orphan_records()`; if it diverges, note it in WP04's documentation step (T018) and leave the cross-file change to WP04 (doctor.py is outside this WP's owned_files).

**Files**:
- `src/specify_cli/cli/commands/sync.py` (edited)

**Validation**:
- `test_daemon_owner_record.py` asserts identical orphan detection from both `sync doctor` and the preflight path.

### T016 — Extend `test_sync_status_boundary_check.py` and `test_daemon_owner_record.py`

**Purpose**: Lock the expanded behavior.

**Steps**:

1. `test_sync_status_boundary_check.py`:
   - Reuse anchors at `:193` (coherent → exit 0) and `:269` (orphan daemon → exit 2). Extend with:
     - One test per canonical mismatch field independently failing `--check` (parametrize for compactness).
     - `test_check_fails_on_legacy_rows_for_scope` for both event and body-upload subtotals.
     - `test_check_json_mode_emits_documented_shape`: parse JSON and assert every documented top-level key + a non-empty `mismatches` list for a split-brain fixture; empty `mismatches` for the coherent fixture.
     - `test_status_prints_all_fr005_fields`: scan stdout for every label from `contracts/sync-status-output.md`.
2. `test_daemon_owner_record.py`:
   - Add `test_sync_now_refuses_on_daemon_owner_mismatch`: a SaaS-producing path refuses before enqueue.
   - Add `test_sync_doctor_and_doctor_orphan_daemons_agree`: same orphan-record fixture is detected by both code paths.

**Files**:
- `tests/sync/test_sync_status_boundary_check.py` (extended; +~150 lines)
- `tests/sync/test_daemon_owner_record.py` (extended; +~80 lines)

**Validation**:
- `uv run pytest tests/sync/test_sync_status_boundary_check.py tests/sync/test_daemon_owner_record.py -q` exits 0.
- Coverage on the changed regions of `sync.py` ≥ 90 %.

## Definition of Done

- [ ] All seven subtasks complete.
- [ ] `uv run pytest tests/sync/test_sync_status_boundary_check.py tests/sync/test_daemon_owner_record.py -q` exits 0.
- [ ] `uv run mypy --strict src/specify_cli/sync/` exits 0 (note: the strict scope is `src/specify_cli/sync/`; if sync.py imports from `sync/`, type changes must propagate cleanly).
- [ ] Live `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty sync status --check` matches contract on the coherent fixture.
- [ ] No edits outside `src/specify_cli/cli/commands/sync.py`, `tests/sync/test_sync_status_boundary_check.py`, `tests/sync/test_daemon_owner_record.py`.
- [ ] WP01's `PreflightResult` is imported, not re-implemented.

## Risks

- **Drift between gate and status output**: Eliminated by construction once `_build_boundary_check_failures` is the single source. Reviewer MUST verify there is exactly one call path.
- **Subtle order-of-operations bug in `sync now`**: A pre-existing call may already trigger an enqueue before the preflight. The new call MUST come before any DB write or SaaS round-trip; reviewer MUST trace the function from entry to first side-effect.
- **`doctor orphan-daemons` cross-file consistency**: This WP only touches `sync.py`. T015 step 3 hands the cross-file work to WP04 via T018 inventory.

## Reviewer guidance

- Trace `sync now` end-to-end: the only side effects before the preflight call should be argument parsing and `collect_foreground_identity`.
- Trace `--check` exit-code computation: must use the same failure-set builder as `run_preflight`.
- Verify `--check --json` is JSON-only on stdout (no Rich panels leak to stderr/stdout in JSON mode).
- Spot-check Rich rendering by hand once: confirm ≤ 25 visible lines for a 6-mismatch + 3-orphan fixture.

## Implementation command

```bash
spec-kitty agent action implement WP03 --agent <name> --mission mvp-cli-sync-boundary-completion-01KRX11M
```

## Activity Log

- 2026-05-18T09:30:44Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=48024 – Started implementation via action command
- 2026-05-18T10:05:05Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=48024 – sync.py expanded: single-source failure builder, sync-now preflight, full FR-005 fields, --check --json, orphan rendering shared
- 2026-05-18T10:05:48Z – codex:gpt-5:reviewer-rita:reviewer – shell_pid=85709 – Started review via action command
- 2026-05-18T10:11:25Z – codex:gpt-5:reviewer-rita:reviewer – shell_pid=85709 – Moved to planned
- 2026-05-18T10:11:32Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=89686 – Started implementation via action command
- 2026-05-18T10:18:11Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=89686 – Cycle 2: auth-required exit code fixed in --check/--json; render <=25 lines worst case
- 2026-05-18T10:18:46Z – codex:gpt-5:reviewer-rita:reviewer – shell_pid=94089 – Started review via action command
- 2026-05-18T10:24:17Z – codex:gpt-5:reviewer-rita:reviewer – shell_pid=94089 – Cycle 2 review approved (codex verdict): FR-004 fixed in both --check and --check --json (exits 2 with auth_required=true); NFR-004 render worst case 24 lines at 80 cols; 47 focused tests pass.
