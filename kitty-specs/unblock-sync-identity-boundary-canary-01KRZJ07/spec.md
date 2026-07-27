# Mission Specification: Unblock Sync Identity-Boundary Canary

**Mission ID**: `01KRZJ079AYV48V0Y41EACAC79` (mid8 `01KRZJ07`)
**Mission slug**: `unblock-sync-identity-boundary-canary-01KRZJ07`
**Target branch**: `main`
**Mission type**: software-dev
**Created**: 2026-05-19

## Purpose

### TLDR

Fix three CLI bugs surfaced by the 2026-05-19 rc13 canary so sync identity-boundary scenarios 1, 2, and 4 turn green again.

### Context

The 2026-05-19 deployed-dev canary against `spec-kitty-cli==3.2.0rc13` hit three CLI blockers that prevent the sync identity-boundary canary from turning green: a `FORBIDDEN_KEY` false positive on lifecycle rows, a Rich-Table ellipsis that truncates queue DB paths in `sync status --check`, and a dead `spec-kitty doctor restart-daemon` reference in sync preflight remediation. A fourth blocker, scenario 3, is gated by a stale-field-name issue in the canary harness (`Priivacy-ai/spec-kitty-end-to-end-testing#43`) that lands separately in the sibling repo and is explicitly out of scope here. Unblocking scenarios 1, 2, and 4 restores the canary as a release gate for the sync surface.

### Source issues

- `Priivacy-ai/spec-kitty#1122` — `FORBIDDEN_KEY` false positive on lifecycle rows blocks TeamSpace migration on fresh missions (scenarios 1, 2).
- `Priivacy-ai/spec-kitty#1123` — `sync status --check` Rich ellipsis truncates queue DB paths (scenario 4).
- `Priivacy-ai/spec-kitty#1124` — Dead `doctor restart-daemon` reference in sync preflight remediation (UX).
- `Priivacy-ai/spec-kitty-end-to-end-testing#43` — Canary harness uses stale mismatch field names (scenario 3). **Out of scope for this mission**; tracked separately in the sibling repo.

## User Scenarios

### Primary actor

Operator of a Spec Kitty project (or the canary harness running on their behalf) who creates fresh missions, runs `spec-kitty sync now` / `sync status --check`, and triages boundary mismatches.

### Scenario 1 — Fresh mission does not auto-create TeamSpace blockers

**Given** a freshly-initialised Spec Kitty project,
**when** the operator runs `spec-kitty agent mission create <slug>` and then `spec-kitty doctor mission-state --audit --json`,
**then** the audit reports zero `FORBIDDEN_KEY` findings caused by mission-lifecycle event rows (`MissionCreated`, `SpecifyStarted`, etc.) in `status.events.jsonl`,
**and** `spec-kitty sync now` does not refuse to connect with "TeamSpace mission-state migration is required".

### Scenario 2 — Canonical queue DB path is preserved in text output

**Given** an operator (or machine consumer) runs `spec-kitty sync status --check` in a non-TTY context or narrow terminal,
**when** the canonical queue DB path is longer than the terminal width,
**then** the rendered text preserves the full path verbatim on a single line (no Unicode ellipsis `…`, no mid-path wrap),
**and** the value is identical to the `active_queue.path` field of the `--json` form.

### Scenario 3 — Sync boundary remediation hints point at real commands

**Given** a sync boundary preflight that detects a daemon-vs-foreground mismatch,
**when** the operator reads the rendered remediation hint,
**then** every command mentioned in `_REMEDIATION_HINTS` (including `spec-kitty doctor restart-daemon`) resolves successfully on the installed CLI,
**and** running `spec-kitty doctor restart-daemon` stops the registered daemon and re-spawns it at the foreground executable/source.

### Scenario 4 — Canary scenarios 1, 2, and 4 turn green

**Given** the rc bump that contains these fixes is installed,
**when** the deployed-dev sync identity-boundary canary runs end-to-end,
**then** scenarios 1, 2, and 4 of `Priivacy-ai/spec-kitty-end-to-end-testing#42` pass,
**and** scenario 3 may remain red pending the separate harness fix in `#43` without blocking this mission's acceptance.

### Edge cases

- Audit on an existing mission whose `status.events.jsonl` contains *only* status-transition rows must still flag any future writer that introduces `event_type`/`event_name` into a canonical status-transition row.
- Audit on a mission whose `status.events.jsonl` contains mixed lifecycle and status-transition rows must flag transitions-with-`event_type` while passing lifecycle rows.
- `sync status --check` in a piped (non-TTY) capture must render queue DB paths verbatim on one line; this is the canary's read path.
- `sync status --check` in a wide TTY must remain visually pleasing for human readers (the new rendering must not regress the operator UX).
- `spec-kitty doctor restart-daemon` with no daemon currently registered must exit non-zero with an actionable message, not crash.
- `spec-kitty doctor restart-daemon` invoked while another `sync` process holds the queue must not corrupt the registered owner record.

## Domain Language

| Term | Meaning | Avoid synonyms |
|------|---------|----------------|
| Status-transition row | A row in `status.events.jsonl` whose canonical shape uses `from_lane` / `to_lane` to describe a WP lane transition. | "status event row", "transition event" |
| Mission-lifecycle row | A row in `status.events.jsonl` written by lifecycle emitters (`MissionCreated`, `SpecifyStarted`, etc.) whose canonical discriminator is `event_type`. | "lifecycle event row" |
| Row family | The named category of a row in `status.events.jsonl` (e.g., `handoff_event_row`, mission-lifecycle row), used by `audit/shape_registry.py` to scope detector rules. | "shape", "row kind" |
| Identity boundary | The pairing of foreground process and registered daemon owner record; mismatches surface in `sync status --check` and `sync/preflight.py`. | "sync boundary" |
| Canonical mismatch field | The named field on `ForegroundIdentity` / `DaemonOwnerRecord` (e.g., `package_version`, `queue_db_path`); the stripped display form has the `daemon_` prefix removed. | "mismatch token" |

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The status-events audit (`src/specify_cli/audit/detectors.py`) MUST treat status-transition rows and mission-lifecycle rows as distinct row families and only forbid `event_type` / `event_name` on rows that should be canonical status-transition rows (e.g., rows whose shape would otherwise match `handoff_event_row` in `audit/shape_registry.py`). Mission-lifecycle rows (e.g., `aggregate_type=Mission`) are explicitly allowed to carry `event_type`. | Accepted |
| FR-002 | After `spec-kitty agent mission create`, `spec-kitty doctor mission-state --audit --json` MUST report zero TeamSpace-blocking findings caused by lifecycle rows in `status.events.jsonl`. | Accepted |
| FR-003 | After `spec-kitty agent mission create`, `spec-kitty sync now` MUST NOT refuse to connect on the grounds of `FORBIDDEN_KEY` findings against mission-lifecycle rows. | Accepted |
| FR-004 | `spec-kitty sync status --check` MUST render the full canonical queue DB path verbatim in its text output, on a single line, regardless of terminal width and regardless of whether stdout is a TTY. | Accepted |
| FR-005 | The text rendering of `sync status --check` MUST emit any boundary-row file path (queue DB path, source checkout path, executable path, etc.) outside the width-constrained Rich `Table`, so paths render as plain `Console.print` lines that preserve the string verbatim. | Accepted |
| FR-006 | The textual representation of every boundary field path in `sync status --check` MUST be byte-identical to the corresponding value in the `--json` form. | Accepted |
| FR-007 | `spec-kitty doctor restart-daemon` MUST exist as a subcommand of `spec-kitty doctor` that stops the registered daemon (via the owner record) and re-spawns it at the foreground executable/source. | Accepted |
| FR-008 | All four `_REMEDIATION_HINTS` occurrences in `src/specify_cli/sync/preflight.py` (lines 99, 103, 107, 119 plus the related comment at 218) MUST be updated together so the wording stays consistent and every command mentioned in any hint resolves on the installed CLI. | Accepted |
| FR-009 | Each fix (FR-001/002/003, FR-004/005/006, FR-007/008) MUST ship with at least one targeted automated regression test that fails on `spec-kitty-cli==3.2.0rc13` and passes after the fix. | Accepted |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | The augmented audit detector MUST NOT increase audit wall-clock time meaningfully. | Audit of a mission tree with 100 mission directories completes in ≤ 2× the rc13 baseline measured on the same hardware. | Accepted |
| NFR-002 | The new `doctor restart-daemon` subcommand MUST complete in bounded wall-clock time on the canary harness. | ≤ 10 seconds end-to-end on macOS and Linux dev machines, including daemon stop + respawn + first heartbeat. | Accepted |
| NFR-003 | Canary scenarios 1, 2, and 4 MUST pass on the rc bump that contains these fixes. | 4-run canary against the rc bump shows ≥ 3 of 4 runs passing scenarios 1, 2, 4 with no flakiness attributable to these fix areas. | Accepted |
| NFR-004 | No regression in existing detector, sync preflight, sync status, or doctor command test suites. | All pre-existing tests in `tests/` continue to pass under `pytest`. | Accepted |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | This mission delivers only into `Priivacy-ai/spec-kitty`. `Priivacy-ai/spec-kitty-end-to-end-testing#43` (canary harness rename) is explicitly out of scope and lands separately in the sibling repo. | Accepted |
| C-002 | Mission "done" is defined by canary scenarios 1, 2, and 4 turning green. Scenario 3 remains red until `#43` lands in the sibling repo and does NOT gate this mission's acceptance. | Accepted |
| C-003 | `status.events.jsonl` continues to hold both row families (status-transition + mission-lifecycle). The file is NOT split; lifecycle event writers in `src/specify_cli/status/lifecycle_events.py`, `src/specify_cli/invocation/propagator.py`, `src/specify_cli/dossier/`, `src/specify_cli/next/_internal_runtime/engine.py`, and `src/specify_cli/retrospective/events.py` MUST remain unchanged with respect to file target. | Accepted |
| C-004 | `_failure_lines_from_set` in `src/specify_cli/cli/commands/sync.py` and the canonical names on `ForegroundIdentity` / `DaemonOwnerRecord` MUST NOT be renamed in this mission. The mismatch-field rename is the responsibility of `#43`. | Accepted |
| C-005 | Any new audit-detector behaviour MUST work additively against existing event logs without requiring a one-time migration of historical `status.events.jsonl` files. | Accepted |

## Success Criteria

1. A fresh `spec-kitty agent mission create` on the fixed CLI produces zero TeamSpace blocker findings; `spec-kitty sync now` connects on the first try.
2. `spec-kitty sync status --check` in a piped (non-TTY) capture of any width preserves the canonical queue DB path verbatim, byte-identical to the `--json` form.
3. Every command mentioned in any sync preflight remediation hint resolves successfully on the installed CLI; `spec-kitty doctor restart-daemon` actually restarts the registered daemon.
4. The 2026-05-19 deployed-dev sync identity-boundary canary turns scenarios 1, 2, and 4 green on the rc bump that bundles these fixes.
5. No existing detector, sync, or doctor test fails on the rc bump that bundles these fixes.

## Assumptions

- The existing `audit/shape_registry.py` is the right place to encode the row-family boundary for the FORBIDDEN_KEY rule; no new module is required.
- The Rich `Table` is the only width-constrained surface in `sync status --check` that currently truncates paths; refactoring to plain `Console.print` for path rows is sufficient.
- The registered daemon owner record exposes enough state for `doctor restart-daemon` to stop and respawn the daemon without re-deriving environment from scratch.
- The canary harness re-run will happen against an rc bump (`3.2.0rc14` or later) that includes all three fixes simultaneously; the canary is not asked to mix-and-match.
- Scenario 3 remains red until sibling-repo `#43` lands; this is acceptable and documented in C-002.

## Out of Scope

- Splitting `status.events.jsonl` into separate files per row family.
- Renaming `_failure_lines_from_set` mismatch tokens or any `ForegroundIdentity` / `DaemonOwnerRecord` field.
- Any change to the canary harness (`spec-kitty-end-to-end-testing`), including the stale field-name fix and the secondary `_default_baseline` symptom called out in `#43`.
- Broader refactors of `sync.py`, `preflight.py`, or `audit/` beyond what these three bugs require.
- Adding new audit detectors unrelated to the `FORBIDDEN_KEY` row-family scoping.

## Key Entities

- **`status.events.jsonl`** — Per-mission append-only event log. Two row families coexist: canonical status-transition rows (`from_lane` / `to_lane`) and mission-lifecycle rows (`event_type` discriminator).
- **`audit/shape_registry.py`** — Registry of named row shapes used by detectors; the boundary contract for the row-family-scoped FORBIDDEN_KEY rule.
- **Sync boundary table** — Rich-Table surface in `src/specify_cli/cli/commands/sync.py` (≈line 1856) rendering identity-boundary state; path fields will move out of the table.
- **`_REMEDIATION_HINTS`** — Dictionary in `src/specify_cli/sync/preflight.py` mapping boundary-mismatch kinds to operator-facing remediation copy.
- **Daemon owner record** — Persistent record of the registered sync daemon (executable path, source path, package version, server, queue DB). Read by the new `doctor restart-daemon` subcommand to identify and respawn the daemon.

## Dependencies and References

- Audit pipeline: `src/specify_cli/audit/detectors.py`, `src/specify_cli/audit/shape_registry.py`, `src/specify_cli/audit/models.py`.
- TeamSpace gate: `src/specify_cli/cli/commands/_teamspace_mission_state_gate.py`.
- Lifecycle event writers (unchanged in scope): `src/specify_cli/status/lifecycle_events.py`, `src/specify_cli/invocation/propagator.py`, `src/specify_cli/dossier/`, `src/specify_cli/next/_internal_runtime/engine.py`, `src/specify_cli/retrospective/events.py`.
- Sync surface: `src/specify_cli/cli/commands/sync.py`, `src/specify_cli/sync/preflight.py`.
- Doctor surface: `src/specify_cli/cli/commands/doctor.py` (and friends).
- Canary repo (read-only here): `Priivacy-ai/spec-kitty-end-to-end-testing`, scenarios 1–4 of `#42`.
- Decisions: `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/decisions/` (5 resolved decisions covering scope, fix selections, and done criterion).
