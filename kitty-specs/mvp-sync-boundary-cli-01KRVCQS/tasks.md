# Tasks: MVP Sync Boundary — CLI

**Mission**: `mvp-sync-boundary-cli-01KRVCQS`
**Planning base**: `main` | **Merge target**: `main`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Data model**: [data-model.md](./data-model.md)

## Overview

Four WPs, one per CLI issue. WP02 depends on no other WP. WP03 depends on WP01 (status uses migration outputs) and WP02 (status surfaces owner record). WP04 depends on WP01 (re-routed body uploads must land in scoped DB which the new migration must keep consistent) and WP02 (setup-plan refuses when SAAS sync requested but unauth — owner-record check is the natural place to inspect daemon coherence too).

| WP | Title | Subtasks | Deps | Owned surface |
|----|-------|----------|------|---------------|
| WP01 | Row-level legacy→scoped queue migration (#1090) | T001–T005 | none | `src/specify_cli/sync/queue.py`, tests |
| WP02 | Daemon owner record + ownership semantics (#1088) | T006–T011 | none | `src/specify_cli/sync/daemon.py`, `src/specify_cli/sync/owner.py`, tests |
| WP03 | Sync status + doctor truthfulness (#1087) | T012–T016 | WP01, WP02 | `src/specify_cli/cli/commands/sync/`, tests |
| WP04 | Setup-plan SaaS-evidence guarantee (#1089) | T017–T020 | WP01, WP02 | `src/specify_cli/cli/commands/agent/` setup-plan code path, tests |

Total subtasks: 20.

## Subtask Index

| ID | Description | WP |
|----|-------------|----|
| T001 | Enumerate live schema of `queue`, `body_upload_queue`, and (if present) body upload failure/history table; document chosen stable keys in code comment | WP01 |
| T002 | Rewrite `_migrate_legacy_queue_to_scope` as row-level merge per data-model.md; remove whole-DB emptiness guard | WP01 |
| T003 | Add structured info-level log per migrated row (table, stable key) | WP01 |
| T004 | Add tests: `tests/sync/test_queue_row_level_migration.py` covering FR-001..FR-004 plus the four scenarios in start-here.md WP1090 prompt (migrate; migrate when destination has unrelated rows; idempotent re-run; detect legacy rows for active scope) | WP01 |
| T005 | Run `uv run pytest tests/sync` + `mypy --strict src/specify_cli/sync/queue.py`; confirm no regressions | WP01 |
| T006 | Create `src/specify_cli/sync/owner.py` with `DaemonOwnerRecord` dataclass + atomic write/read/compare helpers per data-model.md | WP02 |
| T007 | Wire `daemon.py` start path to write the owner record atomically when the daemon binds its port | WP02 |
| T008 | Extend daemon health endpoint to include the owner record (excluding `token`) | WP02 |
| T009 | Add foreground-side helper `check_daemon_owner_match()` returning a tuple `(is_coherent, mismatched_fields)`. Add a thin call-site shim used by any sync action that talks to the daemon | WP02 |
| T010 | Add orphan-detection helper that identifies owner records whose PID is not alive OR whose executable path no longer exists | WP02 |
| T011 | Tests: `tests/sync/test_daemon_owner_record.py` covering FR-005..FR-007, FR-010, C-002 (no real-process kills; use controlled subprocesses or fake metadata) | WP02 |
| T012 | Extend `sync status` to include the FR-008 fields (foreground identity, daemon owner identity, mismatch diagnostics, orphan count, legacy DB row counts) | WP03 |
| T013 | Implement `sync status --check` exit-code logic per FR-009 (a/b/c) | WP03 |
| T014 | Add `doctor` listing of orphan daemons with a retirement command (FR-010) | WP03 |
| T015 | Add FR-013 "setup-plan stranded" tag when status detects setup-plan body uploads in legacy | WP03 |
| T016 | Tests: `tests/sync/test_sync_status_boundary_check.py` covering stale daemon version, legacy body-upload backlog, daemon queue mismatch, healthy state | WP03 |
| T017 | Audit setup-plan code path; confirm every body-upload-emitting and event-emitting call uses `default_queue_db_path()` (no direct legacy path) | WP04 |
| T018 | Add FR-011 refuse-loudly behaviour: with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and unauthenticated foreground, setup-plan exits non-zero with a specific diagnostic and writes nothing | WP04 |
| T019 | Add cross-cutting regression test (`tests/runtime/test_setup_plan_sync_evidence.py`) that authenticates a tmp HOME and asserts setup-plan rows land in scoped DB, NOT legacy. Second test asserts the FR-011 refuse-loudly behaviour | WP04 |
| T020 | Run full `uv run pytest tests/sync tests/status tests/runtime` and `mypy --strict src/specify_cli/sync/ src/specify_cli/cli/commands/sync/ src/specify_cli/cli/commands/agent/`; confirm green | WP04 |

## Requirement coverage

| Req | WPs |
|---|---|
| FR-001..FR-004 | WP01 |
| FR-005..FR-007, FR-010 | WP02 |
| FR-008..FR-009, FR-013 | WP03 |
| FR-011..FR-012 | WP04 |
| NFR-001 | all WPs (test discipline) |
| NFR-002 | WP04 (final gate) |
| NFR-003 | WP04 (final gate) |
| NFR-004 | WP04 (final gate) |
| C-001..C-006 | reviewer checks on all WPs |

## Work Packages

### WP01 — Row-level legacy→scoped queue migration

**Goal**: Replace the whole-DB emptiness guard in `_migrate_legacy_queue_to_scope` with idempotent row-level merge over the three queue tables. Deduplicate by stable key; delete from legacy only after copy.

**Independent test**: `uv run pytest tests/sync/test_queue_row_level_migration.py` passes.

**Owned files**: `src/specify_cli/sync/queue.py`, `tests/sync/test_queue_row_level_migration.py`.

**Authoritative surface**: `src/specify_cli/sync/`.

**Dependencies**: none.

**Risks**: schema drift across SQLite versions; data loss if delete-from-legacy runs before insert-into-scoped commits. Mitigated by: separate INSERT and DELETE transactions, with a row-existence assertion in between.

**Included subtasks**: T001..T005.

### WP02 — Daemon owner record + ownership semantics

**Goal**: Make the sync daemon a machine-global coherent owner. Add a new `src/specify_cli/sync/owner.py` module with `DaemonOwnerRecord` dataclass + atomic I/O; wire `daemon.py` to write the record on start; expose it via the health endpoint; provide foreground helpers for coherence and orphan detection.

**Independent test**: `uv run pytest tests/sync/test_daemon_owner_record.py` passes.

**Owned files**: `src/specify_cli/sync/daemon.py`, `src/specify_cli/sync/owner.py` (NEW), `tests/sync/test_daemon_owner_record.py`.

**Authoritative surface**: `src/specify_cli/sync/`.

**Dependencies**: none.

**Risks**: race between two daemons writing the owner record. Mitigated by atomic `os.replace()` plus the existing `daemon.lock` advisory file lock.

**Included subtasks**: T006..T011.

### WP03 — Sync status + doctor truthfulness

**Goal**: Make `sync status` show the full boundary state (foreground vs daemon identity, legacy/scoped queue row counts, orphan daemon count) and make `sync status --check` return non-zero when ANY boundary field is incoherent.

**Independent test**: `uv run pytest tests/sync/test_sync_status_boundary_check.py` passes.

**Owned files**: `src/specify_cli/cli/commands/sync/status.py` (or equivalent — agent must locate the live command file), `tests/sync/test_sync_status_boundary_check.py`.

**Authoritative surface**: `src/specify_cli/cli/commands/sync/`.

**Dependencies**: WP01 (for legacy row-count helpers), WP02 (for owner-record helpers).

**Risks**: rich output formatting churn; status text is consumed by tests elsewhere. Mitigated by isolating the new fields into an explicit section and only weakening tests that assert against the renamed section.

**Included subtasks**: T012..T016.

### WP04 — Setup-plan SaaS-evidence guarantee

**Goal**: Make `spec-kitty agent mission setup-plan` refuse to run when `SPEC_KITTY_ENABLE_SAAS_SYNC=1` but the foreground is unauthenticated; ensure every body-upload-emitting code path routes through `default_queue_db_path()`. Lock with regression tests.

**Independent test**: `uv run pytest tests/runtime/test_setup_plan_sync_evidence.py` passes.

**Owned files**: the setup-plan code path in `src/specify_cli/cli/commands/agent/` (agent must locate; likely `mission.py`), `tests/runtime/test_setup_plan_sync_evidence.py`.

**Authoritative surface**: `src/specify_cli/cli/commands/agent/`.

**Dependencies**: WP01 (scoped DB writes), WP02 (foreground/daemon coherence check before setup-plan proceeds).

**Risks**: setup-plan body-upload paths may pass through several helpers; missing one would silently strand work in legacy. Mitigated by the AST/grep regression test that asserts no setup-plan code path calls `_legacy_queue_db_path()` directly.

**Included subtasks**: T017..T020.

## Parallelization

WP01 and WP02 can run in parallel. WP03 starts after both. WP04 starts after both (can run alongside WP03 if test isolation permits, but practically sequence WP04 last to avoid status-output churn during the cross-cutting integration test).

## Next command

`/spec-kitty.analyze --mission mvp-sync-boundary-cli-01KRVCQS`
