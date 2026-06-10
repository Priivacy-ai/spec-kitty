# Mission Specification: Do Dispatch Open-Op Lifecycle

**Mission ID**: 01KTSJ2H8E5YF2EGJYGAE5Z5Q2
**Mission Slug**: do-dispatch-open-op-lifecycle-01KTSJ2H
**Created**: 2026-06-10
**Status**: Draft
**Related issues**: #1810, #1229, #1688, #1781, #701 (the `dispatch` rename in #1810 is explicitly out of scope)

## Purpose

**TLDR**: Make `spec-kitty do` record honest open→work→close Op lifecycles instead of falsely marking work done at dispatch.

Today `spec-kitty do` closes its operation record with outcome "done" the moment it dispatches, before any work happens, so the permanent audit record in `kitty-ops/` can claim success for work that failed or never occurred. This mission makes the record truthful: dispatch opens the record, the working agent closes it with the real outcome and evidence, hooks remind about open records, and doctor sweeps stale ones — so product owners, auditors, and other agents can trust who did what, when, and why.

## User Scenarios & Testing

### Primary Scenario — governed lightweight dispatch

1. An operator in a host agent session (e.g. Claude Code) says "hey spec kitty, fix that bug".
2. The host agent runs `spec-kitty do "fix that bug"`. The command routes the request to an agent profile, loads governance context, writes an **open** Op record, and prints the governance capsule including an explicit instruction to close the record when the work is finished.
3. The host agent performs the work under the loaded governance context.
4. The host agent closes the Op with `spec-kitty profile-invocation complete --invocation-id <id> --outcome done` (optionally with `--evidence`, `--artifact`, `--commit`).
5. The permanent record now shows: who dispatched, what was requested, which profile/governance applied, what the real outcome was, and when it closed.

### Exception Scenario — work fails or is abandoned

- The agent's work fails: the agent closes the Op with `--outcome failed`. The record reflects failure; it is never recorded as done.
- The session crashes or the agent forgets to close: the Op remains open (an orphan). At the next session start (Claude Code), the operator/agent is reminded of open Ops. `spec-kitty doctor ops` reports all orphans, and `doctor ops --close-stale` closes orphans older than the staleness threshold with outcome `abandoned`.

### Acceptance Scenarios

1. **Given** a fresh project, **when** `spec-kitty do "<request>"` runs, **then** the Op record contains a started event and no completed event, and the command output (rich and JSON) includes the invocation id and the close instruction.
2. **Given** an open Op, **when** the agent runs `profile-invocation complete --outcome failed`, **then** the completed event records `outcome: failed` and includes enough identity context to be understood alongside its started event.
3. **Given** an open Op older than the staleness threshold, **when** `doctor ops --close-stale` runs, **then** the Op is closed with outcome `abandoned` and the action is reported; Ops younger than the threshold are reported but not closed.
4. **Given** `doctor ops --close-stale --threshold 0`, **then** all open Ops are closed as `abandoned` regardless of age.
5. **Given** a completed event in the new schema, **when** read in isolation from its JSONL file, **then** it has a required, non-null outcome and no misleading blank-default fields (no `actor: "unknown"`, no empty `action`/`started_at` masquerading as data).
6. **Given** sync is enabled, **when** `do` opens or the agent closes an Op, **then** the corresponding events are propagated to SaaS asynchronously (same behavior `ask`/`advise` already have); when sync is disabled, local records are still written.
7. **Given** a Claude Code session with an open Op, **when** the session starts and when the session stops (research R5 confirmed both hooks are supported by the existing registrar surface), **then** the operator/agent is informed of open Ops and how to close them.
8. **Given** a repository containing pre-mission Op records in the old schema, **when** the migration runs, **then** salvageable records are rewritten to the new schema and unsalvageable records are deleted; readers never crash on a migrated directory.

### Edge Cases

- Double close: closing an already-closed Op must remain an idempotent error (`AlreadyClosedError`), including when `--close-stale` races a manual close.
- `do` invoked but routing fails (ambiguous/no match): no Op record is created (existing behavior preserved); the error output explains recovery.
- An Op opened by `do` and closed by `doctor ops --close-stale` while the agent is still actually working: the agent's later manual close fails with the idempotent error and the operator can see the abandonment in the record. The threshold default exists to make this rare.
- JSON output mode (`--json`) must carry the invocation id and close contract machine-readably for orchestrators.

## Domain Language

- **Op (operation record)**: the Tier 1 permanent record of a standalone invocation, stored as one append-only JSONL file in `kitty-ops/`. Canonical term: **Op**. Avoid "invocation record" in new user-facing prose except where the CLI surface already uses `profile-invocation`. Until the deferred `dispatch` rename mission (#1810) unifies the CLI surface, `profile-invocation` remains the close-command term; all other new prose says "Op".
- **Open Op / orphan**: an Op with a started event and no completed event. "Orphan" is reserved for open Ops that are *unexpectedly* open (crashed/forgotten); the doctor surface uses this term.
- **Dispatch**: the act of routing + governance loading + opening the Op. Dispatch does **not** imply completion. (The command rename to `dispatch` is deferred.)
- **Close**: appending the completed event with a real outcome (`done` | `failed` | `abandoned`).

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `spec-kitty do` MUST NOT auto-close the Op it opens. After a successful `do`, the Op record contains a started event and no completed event. | Proposed |
| FR-002 | `do` output (rich and `--json`) MUST include the invocation id and an explicit instruction/contract for closing the Op with a real outcome, replacing the current "record written, commit it" single-shot message. | Proposed |
| FR-003 | The agent-facing close surface (`profile-invocation complete`) MUST accept outcome `done`, `failed`, or `abandoned`, with optional evidence, artifact links, and commit link, and MUST remain idempotent on double close. | Proposed |
| FR-004 | The completed event schema MUST require a non-null outcome and MUST NOT serialize misleading blank-default fields. Started and completed events MUST be modeled as distinct schemas (or equivalent) such that a completed event cannot validly carry started-only fields defaulted to empty values. | Proposed |
| FR-005 | An Op's JSONL file, read alone, MUST tell a complete story: requester/actor, request text, profile, action, governance context reference, timestamps, and final outcome (once closed). | Proposed |
| FR-006 | `spec-kitty doctor ops` MUST continue to report all open Ops, and MUST gain `--close-stale` which closes open Ops older than a staleness threshold with outcome `abandoned`, recording that the closure was performed by the doctor sweep (not by the working agent). | Proposed |
| FR-007 | `--close-stale` MUST accept a configurable threshold (default 24 hours); `--threshold 0` closes all open Ops. Ops younger than the threshold are reported but never auto-closed. | Proposed |
| FR-008 | `do` MUST propagate Op events to SaaS via the same asynchronous, best-effort propagator already used by `ask` and `advise`, gated by the existing sync routing (local-first; no propagation when sync is disabled). | Proposed |
| FR-009 | Claude Code session presence MUST surface open Ops: the session-start surface lists open Ops with their ids and the close command, and a stop-time reminder hook is registered alongside it (research R5 confirmed the existing registrar surface supports both without new harness work). Other harnesses rely on the capsule text and skill pack for this mission. | Proposed |
| FR-010 | The host wrapper / skill pack / session-presence orientation text MUST state the open→work→close contract explicitly: `do` opens, the agent works under the loaded governance, the agent closes with the real outcome and evidence. All canonical source templates that currently describe `do` as single-shot MUST be updated. | Proposed |
| FR-011 | A migration MUST upgrade existing `kitty-ops/` records to the new schema: salvageable records are rewritten; unsalvageable records (e.g. blank-field completed events with no recoverable identity) are deleted. Readers (`invocations list`, doctor, lifecycle tooling) MUST operate without error on a migrated directory. | Proposed |
| FR-012 | Auto-commit of the Op record MUST occur at close time (as today for completed Ops), including closes performed by `doctor ops --close-stale`. Open Ops remain uncommitted working-tree files so orphan state stays visible. | Proposed |

## Non-Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-001 | `do` dispatch latency must not regress by more than 10% versus the current implementation (SaaS propagation must remain asynchronous and non-blocking, matching existing `ask`/`advise` behavior). | Proposed |
| NFR-002 | `doctor ops --close-stale` must complete in under 5 seconds on a repository with 10,000 Op files (consistent with the existing NFR-008 listing budget). | Proposed |
| NFR-003 | New code must ship with ≥90% test coverage, pass `mypy --strict` and `ruff` with zero suppressions, and include integration tests for the changed CLI commands (charter policy). | Proposed |
| NFR-004 | The migration must be idempotent: running it twice on the same directory produces no further changes and no errors. | Proposed |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Breaking changes are acceptable: no `--single-shot` compatibility flag, no transitional behavior. This is pre-release software; a CHANGELOG entry documents the behavior change. | Accepted |
| C-002 | The `do`→`dispatch` rename (#1810) is out of scope for this mission. | Accepted |
| C-003 | Hook/reminder work is limited to Claude Code in this mission; other harnesses are covered by capsule output and skill-pack text, with broader harness rollout deferred to a later mission. | Accepted |
| C-004 | The append-only JSONL contract for `kitty-ops/` files is preserved: started events are write-once, completed events are appended, no in-place mutation of live records (migration of legacy records is the sole exception). | Accepted |
| C-005 | Edit canonical source templates under `src/doctrine/` (and session-presence content sources), never generated agent copies. | Accepted |

## Success Criteria

1. After this mission, zero Op records exist where the recorded outcome precedes the work: a `do` followed by no agent action yields an open Op, never a `done` record.
2. A product owner or auditor reading any single closed Op JSONL file can answer who did what, when, and why, and whether it succeeded, without consulting any other file.
3. An agent following only the printed capsule (no skill pack, no hooks) has enough instruction to close the Op correctly with a real outcome.
4. Open Ops cannot accumulate silently: every orphan is surfaced at Claude Code session start and is sweepable to `abandoned` via one doctor command.
5. With sync enabled, `do` Ops appear in the SaaS event stream with the same fidelity as `ask`/`advise` Ops.

## Key Entities

- **Op record** (`kitty-ops/<ulid>.jsonl`): append-only event file — started event, optional glossary/artifact/commit link events, completed event.
- **Started event**: identity + dispatch context (profile, action, request, actor, governance hash, mode, timestamps).
- **Completed event**: closure context (required outcome, completed_at, evidence ref, closing actor — agent vs doctor sweep).
- **Ops index** (`kitty-ops/ops-index.jsonl`): performance listing aid; unchanged semantics.
- **Doctor ops surface**: orphan reporting + stale sweep.
- **Session presence orientation**: Claude Code surface that teaches the dispatch contract and surfaces open Ops.

## Assumptions

- The existing `profile-invocation complete` command is the canonical close surface; no new close command is introduced.
- The staleness default of 24 hours is a reasonable balance between not closing in-flight work and not letting orphans linger; it is configurable per invocation and can be revisited.
- "Unsalvageable" legacy records are those lacking a recoverable started event identity; very few exist in the wild and none are precious (user-confirmed), so deletion is acceptable.
- The closing actor distinction (agent close vs doctor sweep) is representable within the completed event without a new event type.
