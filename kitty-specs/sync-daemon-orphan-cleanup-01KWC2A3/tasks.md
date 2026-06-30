# Tasks: Safe Sync Daemon Orphan Cleanup

**Mission**: `sync-daemon-orphan-cleanup-01KWC2A3` · **Source**: issue [#2261](https://github.com/Priivacy-ai/spec-kitty/issues/2261)
**Branch contract**: planning base `fix/sync-daemon-orphan-cleanup` → merge target `fix/sync-daemon-orphan-cleanup` (later PRs to `main`).
**Inputs**: [spec.md](spec.md) · [plan.md](plan.md) · [research.md](research.md) · [data-model.md](data-model.md) · [contracts/](contracts/) · [quickstart.md](quickstart.md)

8 work packages, 39 subtasks. WPs are partitioned by **disjoint file ownership** so they never collide. The pure classifier (WP01) is the foundation that both cleanup surfaces (WP02 reaper, WP03 port-scan) consume; the CLI (WP05), daemon lifecycle (WP04), two live-subprocess test matrices (WP06/WP07), and the ADR/docs/#1071 closeout (WP08) follow.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | DaemonIdentityRecord + CleanupClass/SkipReason/identity_source enums | WP01 | |
| T002 | Pure input adapters (HealthProbe, SingletonRef, cmdline→scope/exec/spawn) | WP01 | |
| T003 | classify_candidate decision rows 1–6 | WP01 | |
| T004 | classify_candidate rows 7–9 (D-01 wedged, pid/port, FR-008 safe_auto) | WP01 | |
| T005 | Unit tests for every decision-table row | WP01 | [P] |
| T006 | Thread classifier into reap_orphan_daemons | WP02 | |
| T007 | Demote executable-identity skip to stale-version evidence (FR-008) | WP02 | |
| T008 | Reap only safe_auto at startup; structured skip_reason in result | WP02 | |
| T009 | Preserve singleton + cross-root safety; owner.json never kill authority | WP02 | |
| T010 | Reaper scope-authority tests | WP02 | [P] |
| T011 | Build DaemonIdentityRecord per in-range listener in enumerate_orphans | WP03 | |
| T012 | In-range/daemon_family guard before any signal; never act on never_touch | WP03 | |
| T013 | Structured ResetResult (swept/skipped/failed) from sweep_orphans | WP03 | |
| T014 | include_operator_required (force) sweep parameter (D-02) | WP03 | |
| T015 | Port-scan classification + ResetResult tests | WP03 | [P] |
| T016 | Add daemon_family to /api/health; surface singleton_scope_id | WP04 | |
| T017 | Confirm reuse-or-spawn avoids redundant spawn after stale cleanup (FR-007) | WP04 | |
| T018 | SYNC_DAEMON_IDLE_RETIREMENT_SECONDS named constant (default 900) | WP04 | |
| T019 | Self-retirement: superseded-prompt + idle-after-constant; never with work (FR-010/011) | WP04 | |
| T020 | Extend self-retirement tests (patched constant) + health daemon_family test | WP04 | [P] |
| T021 | Add --force flag to auth doctor; thread into reset path (D-02) | WP05 | |
| T022 | Render cleanup_class/reason; bump JSON schema_version→2 with full records | WP05 | |
| T023 | Emit reset_result {swept,skipped,failed}; remediation hint (FR-005/009) | WP05 | |
| T024 | Keep read-only without --reset; --force/confirm gate for operator_required | WP05 | |
| T025 | auth doctor classification + reset_result tests | WP05 | [P] |
| T026 | Shared live-subprocess harness module + version spoof (3.2.2/3.2.3/3.2.4) | WP06 | |
| T027 | Assert same-scope stale → safe_auto cleaned; no redundant spawn (AS-1) | WP06 | |
| T028 | Assert pre-marker/cross-$HOME/wedged → operator_required, not killed (AS-2) | WP06 | |
| T029 | Assert auth doctor --json scan + --reset --json swept/skipped/failed (AS-3/4) | WP06 | |
| T030 | Serial/isolated-range + win32 skip + SAAS env note (NFR-006/C-006) | WP06 | |
| T031 | Boundary harness: sync + dashboard + third-party across 4 entrypoints | WP07 | |
| T032 | Dashboard listener survives every sync cleanup path (C-002, NFR-002/003) | WP07 | |
| T033 | Sync listener survives dashboard cleanup; third-party survives both | WP07 | |
| T034 | First/last/just-outside boundary ports for both ranges | WP07 | |
| T035 | spec-kitty dashboard keeps DaemonIntent.LOCAL_ONLY, no forced sync (AS-7) | WP07 | |
| T036 | ADR: daemon identity contract + cleanup classification | WP08 | |
| T037 | Operator remediation runbook (auth doctor → --reset [--force]) | WP08 | [P] |
| T038 | Automated #1071 same-$HOME singleton reconfirmation test (FR-012) | WP08 | |
| T039 | Close/re-scope #1071 referencing the test (DoD note) | WP08 | |

> The `[P]` column marks parallel-safe subtasks; it is not a status column. Per-WP
> progress is tracked by the checkbox rows under each WP heading below.

## Phase 1 — Classification foundation

### WP01 — Sync daemon classification engine
- **Prompt**: [tasks/WP01-classification-engine.md](tasks/WP01-classification-engine.md)
- **Goal**: A pure, unit-tested `classify_candidate()` turning a probed listener into a `DaemonIdentityRecord` + `cleanup_class`, with the daemon-root scope marker as primary kill authority and version/executable mismatch demoted to stale-version evidence (FR-008); a wedged listener is `operator_required` (D-01).
- **Priority**: P1 (foundation). **Dependencies**: none.
- **Independent test**: feed synthetic inputs for all 9 decision rows → expected `cleanup_class`/`skip_reason`, no subprocess.
- **Owns**: `src/specify_cli/sync/classification.py` (new), `tests/sync/test_daemon_classification_unit.py` (new).
- **Subtasks**:
  - [x] T001 DaemonIdentityRecord + CleanupClass/SkipReason/identity_source enums (WP01)
  - [x] T002 Pure input adapters (HealthProbe, SingletonRef, cmdline→scope/exec/spawn) (WP01)
  - [x] T003 classify_candidate decision rows 1–6 (WP01)
  - [x] T004 classify_candidate rows 7–9 (D-01 wedged, pid/port, FR-008 safe_auto) (WP01)
  - [x] T005 Unit tests for every decision-table row (WP01)
- **Requirements**: FR-001, FR-002, FR-003, FR-008, C-004. **Est. prompt**: ~300 lines.

## Phase 2 — Cleanup authority

### WP02 — Reaper scope authority (startup)
- **Prompt**: [tasks/WP02-reaper-scope-authority.md](tasks/WP02-reaper-scope-authority.md)
- **Goal**: The startup reaper `reap_orphan_daemons` classifies candidates and reaps only `safe_auto` — including older same-scope versions (FR-008) — while leaving `operator_required`/`never_touch` untouched. This is the direct fix for the 18-orphan leak.
- **Priority**: P1. **Dependencies**: WP01.
- **Independent test**: stale same-scope (older version) daemon is reaped; cross-root/pre-marker daemon is skipped; recorded singleton preserved.
- **Owns**: `src/specify_cli/sync/owner.py`, `tests/sync/test_daemon_reaper_scope_authority.py` (new).
- **Subtasks**:
  - [x] T006 Thread classifier into reap_orphan_daemons (WP02)
  - [x] T007 Demote executable-identity skip to stale-version evidence (FR-008) (WP02)
  - [x] T008 Reap only safe_auto at startup; structured skip_reason in result (WP02)
  - [x] T009 Preserve singleton + cross-root safety; owner.json never kill authority (WP02)
  - [x] T010 Reaper scope-authority tests (WP02)
- **Requirements**: FR-003, FR-006, FR-007, FR-008. **Est. prompt**: ~320 lines.

### WP03 — Port-scan classification + reset reporting
- **Prompt**: [tasks/WP03-portscan-reset-reporting.md](tasks/WP03-portscan-reset-reporting.md)
- **Goal**: The `auth doctor` port-scan (`orphan_sweep.py`) builds a full identity record per in-range listener, returns a structured `ResetResult` (swept/skipped/failed), and gains a force-aware sweep that defaults to `safe_auto` only.
- **Priority**: P1. **Dependencies**: WP01.
- **Independent test**: scan yields classified records; sweep returns exact swept/skipped/failed; force vs non-force differ on operator_required.
- **Owns**: `src/specify_cli/sync/orphan_sweep.py`, `tests/sync/test_orphan_sweep_classification.py` (new).
- **Subtasks**:
  - [x] T011 Build DaemonIdentityRecord per in-range listener in enumerate_orphans (WP03)
  - [x] T012 In-range/daemon_family guard before any signal; never act on never_touch (WP03)
  - [x] T013 Structured ResetResult (swept/skipped/failed) from sweep_orphans (WP03)
  - [x] T014 include_operator_required (force) sweep parameter (D-02) (WP03)
  - [x] T015 Port-scan classification + ResetResult tests (WP03)
- **Requirements**: FR-001, FR-005, NFR-001, C-002. **Est. prompt**: ~320 lines.

### WP04 — Daemon health identity + self-retirement
- **Prompt**: [tasks/WP04-daemon-identity-self-retirement.md](tasks/WP04-daemon-identity-self-retirement.md)
- **Goal**: `/api/health` advertises `daemon_family`/`singleton_scope_id`; startup reuse avoids redundant spawn (FR-007); a superseded or idle daemon self-retires via a named constant (FR-010/011).
- **Priority**: P1. **Dependencies**: none (daemon-side file; codes against the health-payload contract).
- **Independent test**: with the constant patched low, a superseded/idle daemon exits; a daemon with work in flight does not; `/api/health` includes `daemon_family`.
- **Owns**: `src/specify_cli/sync/daemon.py`, `tests/sync/test_daemon_self_retirement.py`, `tests/sync/test_daemon_health_identity.py` (new).
- **Subtasks**:
  - [x] T016 Add daemon_family to /api/health; surface singleton_scope_id (WP04)
  - [x] T017 Confirm reuse-or-spawn avoids redundant spawn after stale cleanup (FR-007) (WP04)
  - [x] T018 SYNC_DAEMON_IDLE_RETIREMENT_SECONDS named constant (default 900) (WP04)
  - [x] T019 Self-retirement: superseded-prompt + idle-after-constant; never with work (WP04)
  - [x] T020 Extend self-retirement tests (patched constant) + health daemon_family test (WP04)
- **Requirements**: FR-007, FR-010, FR-011, C-001. **Est. prompt**: ~330 lines.

## Phase 3 — Operator surface

### WP05 — `auth doctor` visibility, reset reporting & `--force`
- **Prompt**: [tasks/WP05-auth-doctor-surface.md](tasks/WP05-auth-doctor-surface.md)
- **Goal**: Surface the classification through `auth doctor [--json]` (read-only), report exact `reset_result` from `--reset`, and gate `operator_required` kills behind `--force`/confirmation (D-02).
- **Priority**: P1. **Dependencies**: WP01, WP03.
- **Independent test**: `--json` emits schema_version 2 with full records; `--reset --json` emits swept/skipped/failed; `operator_required` requires `--force`; no mutation without `--reset`.
- **Owns**: `src/specify_cli/cli/commands/auth.py`, `src/specify_cli/cli/commands/_auth_doctor.py`, `tests/auth/test_auth_doctor_classification.py` (new).
- **Subtasks**:
  - [x] T021 Add --force flag to auth doctor; thread into reset path (D-02) (WP05)
  - [x] T022 Render cleanup_class/reason; bump JSON schema_version→2 with full records (WP05)
  - [x] T023 Emit reset_result {swept,skipped,failed}; remediation hint (FR-005/009) (WP05)
  - [x] T024 Keep read-only without --reset; --force/confirm gate for operator_required (WP05)
  - [x] T025 auth doctor classification + reset_result tests (WP05)
- **Requirements**: FR-004, FR-005, FR-009. **Est. prompt**: ~300 lines.

## Phase 4 — Live regression matrices

### WP06 — Live-subprocess version matrix
- **Prompt**: [tasks/WP06-live-version-matrix.md](tasks/WP06-live-version-matrix.md)
- **Goal**: A shared live-subprocess harness + a version matrix (3.2.2/3.2.3/3.2.4) proving same-scope stale cleanup, no redundant spawn, and `operator_required` survival, plus exact `auth doctor`/`--reset` reporting — all with real listeners and real PIDs (NFR-004).
- **Priority**: P1. **Dependencies**: WP01, WP02, WP03, WP04, WP05.
- **Independent test**: the suite is green serially (`-n0`), skipped on win32.
- **Owns**: `tests/sync/_daemon_harness.py` (new, shared), `tests/sync/test_daemon_orphan_classification.py` (new).
- **Subtasks**:
  - [x] T026 Shared live-subprocess harness module + version spoof (3.2.2/3.2.3/3.2.4) (WP06)
  - [x] T027 Assert same-scope stale → safe_auto cleaned; no redundant spawn (AS-1) (WP06)
  - [x] T028 Assert pre-marker/cross-$HOME/wedged → operator_required, not killed (AS-2) (WP06)
  - [x] T029 Assert auth doctor --json scan + --reset --json swept/skipped/failed (AS-3/4) (WP06)
  - [x] T030 Serial/isolated-range + win32 skip + SAAS env note (NFR-006/C-006) (WP06)
- **Requirements**: NFR-004, NFR-006, C-006. **Est. prompt**: ~360 lines.

### WP07 — Dashboard boundary regression matrix
- **Prompt**: [tasks/WP07-dashboard-boundary-matrix.md](tasks/WP07-dashboard-boundary-matrix.md)
- **Goal**: Prove sync cleanup never touches dashboard/third-party listeners and vice-versa across all four entrypoints, including boundary ports, and that dashboard startup keeps `DaemonIntent.LOCAL_ONLY`.
- **Priority**: P1. **Dependencies**: WP01, WP03, WP04, WP06 (shared harness).
- **Independent test**: every cross-family/boundary assertion green serially.
- **Owns**: `tests/sync/test_daemon_cleanup_boundary.py` (new).
- **Subtasks**:
  - [x] T031 Boundary harness: sync + dashboard + third-party across 4 entrypoints (WP07)
  - [x] T032 Dashboard listener survives every sync cleanup path (C-002, NFR-002/003) (WP07)
  - [x] T033 Sync listener survives dashboard cleanup; third-party survives both (WP07)
  - [x] T034 First/last/just-outside boundary ports for both ranges (WP07)
  - [x] T035 spec-kitty dashboard keeps DaemonIntent.LOCAL_ONLY, no forced sync (AS-7) (WP07)
- **Requirements**: NFR-001, NFR-002, NFR-003, C-002, C-003. **Est. prompt**: ~340 lines.

## Phase 5 — Decision record & closeout

### WP08 — ADR, operator docs & #1071 reconfirmation
- **Prompt**: [tasks/WP08-adr-docs-issue-1071.md](tasks/WP08-adr-docs-issue-1071.md)
- **Goal**: Record the daemon identity-contract change (ADR), document the operator remediation path, and reconfirm #1071 with an automated test before closing/re-scoping it.
- **Priority**: P2. **Dependencies**: WP05, WP06, WP07.
- **Independent test**: ADR + runbook render; #1071 reconfirmation test green.
- **Owns**: `docs/adr/3.x/2026-06-30-1-sync-daemon-identity-and-cleanup-classification.md` (new), `docs/development/sync-daemon-orphan-cleanup.md` (new), `tests/sync/test_issue_1071_singleton_reconfirmation.py` (new).
- **Subtasks**:
  - [ ] T036 ADR: daemon identity contract + cleanup classification (WP08)
  - [ ] T037 Operator remediation runbook (auth doctor → --reset [--force]) (WP08)
  - [ ] T038 Automated #1071 same-$HOME singleton reconfirmation test (FR-012) (WP08)
  - [ ] T039 Close/re-scope #1071 referencing the test (DoD note) (WP08)
- **Requirements**: FR-012, C-005. **Est. prompt**: ~260 lines.

## Dependency graph

```
WP01 ─┬─► WP02 ─┐
      ├─► WP03 ─┼─► WP05 ─┐
WP04 ─┘         │         ├─► WP06 ─┬─► WP07 ─► WP08
                └─────────┘         └───────────►
```

- **Roots (parallel)**: WP01, WP04.
- **After WP01**: WP02, WP03 (parallel).
- **After WP03 (+WP01)**: WP05.
- **After all impl (WP01-05)**: WP06 (builds shared harness).
- **After WP06**: WP07 (reuses harness), then WP08 (docs + #1071, after the matrices exist).

## Requirement coverage

Every FR is owned by ≥1 WP: FR-001 (WP01/03) · FR-002 (WP01) · FR-003 (WP01/02) · FR-004 (WP05) · FR-005 (WP03/05) · FR-006 (WP02) · FR-007 (WP02/04) · FR-008 (WP01/02) · FR-009 (WP05) · FR-010 (WP04) · FR-011 (WP04) · FR-012 (WP08). NFR-001..006 and C-001..007 are covered by WP03/WP04/WP06/WP07/WP08 as noted per WP. `ruff` + `mypy --strict` (NFR-005) is a Definition-of-Done gate in every code-change WP.

## MVP scope

**WP01 + WP02 + WP04** delivers the headline outcome: a freshly-started CLI reaps provably-stale same-scope daemons (including older versions) and reuses the healthy singleton instead of spawning another — i.e. the 18-orphan leak stops. WP03+WP05 add operator visibility/remediation; WP06/WP07 lock it with live regression; WP08 records the decision and closes #1071.
