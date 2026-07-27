# Specification: MVP CLI Sync Boundary Completion

**Mission slug**: `mvp-cli-sync-boundary-completion-01KRX11M`
**Mission ID**: `01KRX11MCY70M5NFBBHT4DQHJ2`
**Target branch**: `kitty/pr/mvp-sync-boundary-cli-01KRVCQS` (PR #1107)
**Created**: 2026-05-18

## Purpose

**TLDR**: Finish PR #1107 and gate sync-producing CLI commands on daemon owner coherence so the MVP sync identity boundary is provable end-to-end.

**Context**: PR #1107 already lands row-level legacy-to-scoped queue migration, daemon owner records, `sync status`/`sync doctor` truthfulness, and `setup-plan` refusal when SaaS sync is enabled without auth. However, the PR's own body documents a remaining medium follow-up: the daemon owner coherence check is reachable from `sync status --check` but is *not* wired into per-action preflights for SaaS-producing commands. Until that gap is closed, a split-brain shape (foreground CLI scope diverges from running daemon) can still silently enqueue events or body uploads into a wrong-scope queue. This mission closes that gap and produces verifiable evidence that the foreground CLI, queue DB, body-upload queue, daemon owner, daemon version/source, and SaaS endpoint describe one coherent delivery boundary — the precondition for merging PR #1107 and closing sub-issues #1090, #1088, #1087, and #1089.

## Primary User Scenario

A spec-kitty CLI operator on macOS, Linux, or Windows 10+, with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` exported (`set SPEC_KITTY_ENABLE_SAAS_SYNC=1` on Windows `cmd.exe` / `$env:SPEC_KITTY_ENABLE_SAAS_SYNC=1` in PowerShell), runs a sync-producing command (`spec-kitty agent mission setup-plan …`, `spec-kitty sync now`, or any mission lifecycle command that emits SaaS events / body uploads). The operator's daemon, foreground CLI, and queue DB may have drifted (different version, different source path, different team, different queue DB, or no daemon owner record at all). The operator expects:

- The command refuses loudly, before any SaaS-visible work is enqueued, when the daemon owner record does not match the foreground process.
- The refusal output names the specific mismatched field(s) so the operator can correct the drift.
- When coherence holds, the command proceeds and enqueues only to the scoped queue DB for the authenticated identity.
- `sync status --check` returns non-zero in every detected split-brain shape and prints all of: active queue DB / counts, legacy queue DB / counts, daemon PID/port/version/executable/source/server/team/queue DB, mismatch fields, and orphan owner-record count.
- `setup-plan` with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` refuses loudly when hosted auth is absent, and when auth is present it never silently writes body uploads to the legacy unscoped queue.

## Exception / Edge Path

After authentication, the operator already has unrelated rows in the scoped queue (from a previous session or another mission) AND rows in the legacy unscoped `~/.spec-kitty/queue.db` from before they authenticated. The mission's row-level migration must merge the legacy rows into the scoped DB without requiring the scoped DB to be empty, must cover both `sync_events`-class rows and `body_upload_queue` rows, and must be safe to retry (idempotent — rows already migrated must not duplicate).

## Always-True Rules

- With `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, no sync-producing path may write SaaS-visible work to a wrong-scope queue, a stale legacy queue, or proceed against an orphan/mismatched daemon owner record without an explicit refusal that names the mismatched field(s).
- Daemon owner mismatch detection must be a reusable preflight available to every sync-producing command — not implemented inline per command.
- `sync status --check` is the operator's source of truth for split-brain detection; it must surface every condition that the preflight refuses on.
- Row-level migration handles `body_upload_queue` rows on the same terms as event rows.
- The mission may not force-push, rewrite published history, mutate prod/dev DB rows, or mark stuck events skipped.

## Domain Language

Canonical terms used in this mission (avoid synonyms in code and docs):

| Canonical term | Meaning | Avoid |
|---|---|---|
| **Scoped queue DB** | Queue DB keyed on authenticated identity (team / user / server). | "user queue", "team queue", "auth queue" |
| **Legacy queue DB** | Unscoped `~/.spec-kitty/queue.db` that pre-existed authentication. | "old queue", "global queue", "default queue" |
| **Daemon owner record** | On-disk record written by the daemon describing the daemon's identity (PID, version, executable, source, server, team/user, queue DB). | "daemon manifest", "daemon meta", "pid file" |
| **Orphan owner record** | A daemon owner record whose `pid` is no longer alive. | "stale daemon", "dead daemon" |
| **Boundary coherence** | The state in which foreground CLI, queue DB, daemon owner record, and SaaS endpoint all describe the same identity. | "sync OK", "auth OK" |
| **Preflight gate** | A reusable check that refuses a command before it produces sync-visible work when boundary coherence fails. | "auth check", "doctor", "validator" |
| **Sync-producing command** | Any CLI command that, with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, enqueues events or body uploads or flushes them to SaaS. | "sync command", "online command" |
| **Force-required rollback** | The settled contract from `spec-kitty-events#32`: review-rejection backward lane transitions require `force=True`. | "rewind", "rollback" without qualifier |

## Functional Requirements

| ID | Description | Status | Source |
|---|---|---|---|
| FR-001 | A reusable preflight gate exists in CLI code and refuses a sync-producing command, before any SaaS-visible enqueue or flush occurs, when the daemon owner record does not match the foreground process on any of: package version, executable path, source path, server URL, team/user, or queue DB path. | Ready | start-here.md §Phase 2; PR #1107 known gap |
| FR-002 | The preflight gate is wired into `sync now`, `agent mission setup-plan`, and every other SaaS-producing mission path that enqueues events or body uploads. | Ready | start-here.md §Phase 2 strict acceptance |
| FR-003 | When the preflight gate refuses, its stderr output explicitly names each mismatched field by its canonical name (e.g., `daemon_executable_path`, `daemon_server_url`). | Ready | start-here.md §Phase 2 |
| FR-004 | `sync status --check` exits non-zero when any of the following are true: foreground vs daemon package versions differ; foreground vs daemon executable/source path differ; foreground vs daemon server/auth/team/queue DB differ; active legacy queue contains rows belonging to the current scope; an orphan daemon owner record exists. | Ready | start-here.md §Phase 2 strict acceptance |
| FR-005 | `sync status --check` prints, on every invocation: active queue DB path, active event queue count, active body upload count, legacy queue DB path, legacy event queue count, legacy body upload count, daemon PID/port/version/executable/source/server/team-or-user/queue DB, mismatch field list (possibly empty), and orphan owner-record count. | Ready | start-here.md §Phase 2 strict acceptance |
| FR-006 | Row-level legacy-to-scoped migration succeeds when the scoped DB already contains unrelated rows: rows from the legacy DB are merged into the scoped DB without losing rows, without duplicating already-migrated rows, and without requiring the scoped DB to be empty. | Ready | start-here.md §Phase 2 strict acceptance |
| FR-007 | Row-level migration covers `body_upload_queue` rows in addition to event rows. Body upload rows are never stranded solely because the scoped DB has at least one other row. | Ready | start-here.md §Phase 2 strict acceptance |
| FR-008 | `SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty agent mission setup-plan …` refuses loudly when hosted auth is absent. The refusal exits non-zero and explains that hosted SaaS sync is enabled but no authenticated identity is available. | Ready | start-here.md §Phase 2 strict acceptance |
| FR-009 | `setup-plan` and other SaaS-producing mission paths never write body uploads into the legacy unscoped queue when authenticated. All SaaS-visible writes go to the scoped queue DB for the authenticated identity. | Ready | start-here.md §Phase 2 strict acceptance |
| FR-010 | Sub-issue closure evidence is captured for each of #1090, #1088, #1087, and #1089: a verification command + expected output is recorded in the mission for the operator to use when commenting on each issue at close time. | Ready | start-here.md §Issue closure |

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|---|---|---|---|
| NFR-001 | Test coverage for new and changed CLI sync code (`src/specify_cli/sync/` and `src/specify_cli/cli/commands/sync.py`, `…/doctor.py`, `…/agent/mission.py` preflight wiring) | ≥ 90% line coverage on changed surfaces, measured by pytest-cov | Ready |
| NFR-002 | Type safety of the entire `src/specify_cli/sync/` package | `uv run mypy --strict src/specify_cli/sync/` exits zero with no new errors | Ready |
| NFR-003 | Preflight gate latency on a coherent host | Adds ≤ 100 ms to each sync-producing command in the coherent case (measured locally; no SaaS round-trip in the gate) | Ready |
| NFR-004 | Refusal output must be actionable in one terminal screen | Operator can read the refusal, identify all mismatched fields, and know which side to correct without consulting external docs; refusal ≤ 25 visible lines | Ready |
| NFR-005 | Test suites stay green after this mission | `uv run pytest tests/sync tests/status tests/runtime -q` exits zero; targeted commands listed under Verification in start-here.md exit zero | Ready |

## Constraints

| ID | Description | Status |
|---|---|---|
| C-001 | All work lands on the existing PR branch `kitty/pr/mvp-sync-boundary-cli-01KRVCQS` for PR #1107. No new long-lived branch. No force-push. No history rewrite. | Ready |
| C-002 | Hosted-auth and sync CLI commands must only be exercised under `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. The mission's test/verification commands respect this rule. | Ready |
| C-003 | The mission may not mutate production/dev SaaS database rows manually to make tests pass, and may not mark stuck events skipped. | Ready |
| C-004 | The mission may not reopen the force-required vs force-optional debate. The events contract (`spec-kitty-events#32`) is settled as force-required; the CLI emits forced backward transitions accordingly and refuses to emit unforced ones. | Ready |
| C-005 | The mission may not close planning/tracking issues (#1090, #1088, #1087, #1089) from summaries alone — closure is gated on the verification evidence captured per FR-010. Actual issue closure happens after merge by the operator. | Ready |
| C-006 | The mission may not land PR #1107 blindly if sync-producing commands can still proceed under a daemon/queue/auth split (i.e., FR-001/FR-002 are not the same as "best effort"). | Ready |
| C-007 | The mission must not regress the existing test suites under `tests/sync`, `tests/status`, and `tests/runtime`. | Ready |
| C-008 | All new code paths and tests must work on Linux, macOS, and Windows 10+. Path handling uses `pathlib.Path` (never raw string concatenation with separator assumptions); home-dir isolation in tests redirects `pathlib.Path.home()` (works on Windows `USERPROFILE` and POSIX `HOME`) rather than setting `HOME` alone. | Ready |

## Acceptance Scenarios

### Scenario 1 — Coherent host: sync-producing command proceeds

1. `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is set; operator is authenticated; daemon is running with a matching owner record.
2. Operator runs `spec-kitty sync now`.
3. The preflight gate passes silently; events flush to SaaS.
4. `sync status --check` exits 0 and prints fields with no mismatches and zero orphans.

### Scenario 2 — Stale daemon: sync-producing command refuses before enqueue

1. `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is set; daemon owner record reports version `v3.2.0rc10` but foreground CLI reports `v3.2.0rc11`.
2. Operator runs `spec-kitty sync now` (or `agent mission setup-plan`).
3. The command exits non-zero before any enqueue. Stderr names `daemon_package_version` as the mismatched field and lists current foreground vs daemon values.
4. `sync status --check` exits non-zero and lists the same mismatch.

### Scenario 3 — Legacy queue with non-empty scoped queue: row-level migration

1. Operator has rows in `~/.spec-kitty/queue.db` (legacy, both `sync_events` rows AND `body_upload_queue` rows).
2. Operator authenticates; scoped queue DB already contains rows from another session.
3. Operator triggers the path that constructs the active `OfflineQueue` (or runs `sync now`).
4. After completion, `sync status --check` reports 0 rows in legacy queue for the current scope and reports the merged count in the active scoped queue, covering both row classes.
5. Re-running the migration is a no-op (idempotent — counts unchanged).

### Scenario 4 — Unauthenticated setup-plan with SaaS enabled

1. `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is set; no authenticated identity present.
2. Operator runs `spec-kitty agent mission setup-plan …`.
3. The command exits non-zero before writing any body upload. Stderr explains that SaaS sync is enabled but no authenticated identity is available, and lists the auth command the operator should run.
4. No row is written to the legacy unscoped queue DB; no `WPCreated`-class event is enqueued.

### Scenario 5 — Orphan daemon owner record

1. Daemon owner record exists on disk but its `pid` is no longer alive (or `is_orphan()` returns true).
2. Operator runs `spec-kitty sync now`.
3. The preflight gate refuses. Stderr names `orphan_daemon_record` and points to `doctor orphan-daemons` for cleanup.
4. `sync status --check` exits non-zero and includes an orphan count ≥ 1.
5. After running `doctor orphan-daemons` to clean up, the preflight passes.

## Success Criteria

- SC-001 (coherence proof): On a coherent host, an operator can run `SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty sync status --check` and see a non-zero exit only when at least one of the documented split-brain conditions is present; the output makes the failing condition obvious without consulting external docs.
- SC-002 (refusal proof): On a host with any single documented split-brain condition (daemon version drift, daemon source drift, daemon server drift, daemon team/user drift, daemon queue DB drift, orphan daemon record), no sync-producing command writes SaaS-visible work; the command refuses and names the mismatch.
- SC-003 (migration proof): An operator who queued events and body uploads while unauthenticated, then authenticated against a non-empty scoped queue, never sees stranded legacy rows after one sync cycle.
- SC-004 (setup-plan proof): An operator with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and no auth never produces silent legacy-queue writes from `setup-plan`; the refusal is immediate and explicit.
- SC-005 (regression containment): All listed verification commands (`tests/sync`, `tests/status`, `tests/runtime`, mypy strict on `src/specify_cli/sync/`) pass in CI on the PR branch.
- SC-006 (issue-closure readiness): For each of #1090, #1088, #1087, #1089 the mission produces a specific evidence command and expected output that the operator copies into the close comment.

## Key Entities

- **DaemonOwnerRecord**: On-disk record describing daemon identity (PID, port, version, executable, source, server URL, team/user, queue DB path). Located in `src/specify_cli/sync/owner.py`. Read by the preflight gate and by `sync status --check`.
- **OfflineQueue / scoped queue DB**: Per-identity SQLite queue DB containing `sync_events` rows and `body_upload_queue` rows. Located via `default_queue_db_path()` in `src/specify_cli/sync/queue.py`.
- **Legacy queue DB**: `~/.spec-kitty/queue.db` written before scoped queues existed. Located via `_legacy_queue_db_path()` in `src/specify_cli/sync/queue.py`.
- **Preflight gate**: New reusable helper that composes `check_daemon_owner_match()`, `is_orphan()`, `list_orphan_records()`, and legacy-rows detection (`detect_legacy_rows_for_scope()`). Lives in `src/specify_cli/sync/` and is invoked from `sync now`, `agent mission setup-plan`, and other SaaS-producing command paths.

## Out of Scope

- Phase 1 (events doctrine reconciliation, `spec-kitty-events#32`) — covered by a separate mission in a sibling repo. This mission consumes the settled force-required contract.
- Phase 3 (SaaS state changes) — out of scope unless an events package version bump requires a dependency pin update, which is also out of scope here.
- Phase 4 (deployed-dev e2e canary, `spec-kitty-end-to-end-testing#41`) — covered by a separate mission in a sibling repo. This mission produces the CLI evidence the canary will consume.
- PR #1107 merge / release / promotion — out of scope here; this mission ends when PR #1107 is *ready* to merge by the criteria above, not when it is merged.

## Assumptions

- The host running the mission's verification has `uv` installed, has Python 3.11+, and can install the project's dev dependencies. Supported hosts are Linux, macOS, and Windows 10+ per the project charter.
- The operator running verification commands has hosted SaaS auth available when commands explicitly require auth; unauthenticated scenarios are tested with a fixture or isolated home, not by deauthenticating a real account.
- The PR branch `kitty/pr/mvp-sync-boundary-cli-01KRVCQS` is up to date with its remote and has no uncommitted local changes outside this mission's artifacts.
- `check_daemon_owner_match()` and related helpers in `src/specify_cli/sync/owner.py` already return enough structured information to name the mismatched field(s); if not, an additive change to that API is in scope.
- The settled force-required review-rejection contract from `spec-kitty-events#32` is already reflected in the events package version this CLI consumes; if not, the gap is a Phase 1 bug, not this mission's problem.
- Cross-platform home-directory resolution uses `pathlib.Path.home()` (which honors `HOME` on POSIX and `USERPROFILE` on Windows). Test fixtures isolate state by redirecting `Path.home()` rather than by setting `HOME` alone, so Windows hosts are exercised by the same fixtures.

## Definition of Done

- All FRs are implemented and have at least one passing test, with regression coverage for the documented edge paths.
- All listed verification commands pass locally and in CI on the PR branch.
- `mypy --strict` on `src/specify_cli/sync/` is clean.
- PR #1107's description is updated to remove the "post-merge follow-up" claim for daemon-owner gating (it is now in-MVP and shipped).
- Each of #1090, #1088, #1087, #1089 has an evidence comment drafted and stored in the mission directory, ready for the operator to post at close time.
- No production/dev DB row mutations; no force-pushes; no skipped stuck events.
