# Tasks: Do Dispatch Open-Op Lifecycle

**Mission**: do-dispatch-open-op-lifecycle-01KTSJ2H
**Input**: spec.md, plan.md, research.md, data-model.md, contracts/
**Branch contract**: planning artifacts on `kitty/mission-do-dispatch-open-op-lifecycle-01KTSJ2H`; completed changes merge into `main`.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Define `OpStartedEvent` model (required dispatch-context fields) | WP01 | |
| T002 | Define `OpCompletedEvent` model (required outcome, `closed_by`) | WP01 | |
| T003 | Update `InvocationWriter` to serialize/validate the v2 events | WP01 | |
| T004 | Update readers (`invocations list`, doctor orphan scan, evidence promotion) for v2 shapes | WP01 | |
| T005 | Unit tests for v2 models, writer, and readers | WP01 | |
| T006 | Remove auto-close from `do`; Op stays open | WP02 | |
| T007 | Wire SaaS propagator into `do`'s executor builder | WP02 | [P] |
| T008 | Replace commit-hint with close-contract block in rich output | WP02 | |
| T009 | Add `status` + `close_contract` object to `do --json` payload | WP02 | |
| T010 | Rewrite `do` CLI integration tests for open-Op behavior | WP02 | |
| T011 | Add `closed_by` to `complete_invocation` executor path | WP03 | |
| T012 | `profile-invocation complete` CLI writes `closed_by="agent"`; idempotent double close preserved | WP03 | |
| T013 | Close-time auto-commit covers all close paths; open Ops never committed | WP03 | |
| T014 | Executor/CLI close-surface tests (outcomes, evidence gate, double close, auto-commit) | WP03 | |
| T015 | Implement `close_stale_ops()` in doctor ops module | WP04 | |
| T016 | Add `--close-stale` / `--threshold` flags to `doctor ops` CLI | WP04 | |
| T017 | Handle sweep race with concurrent manual close (`already_closed`) | WP04 | |
| T018 | Sweep tests incl. threshold edge cases and 10k-file performance guard | WP04 | |
| T019 | Create op-record schema v2 upgrade migration (detect/apply) | WP05 | |
| T020 | Implement legacy→v2 rewrite mapping (incl. null-outcome → abandoned) | WP05 | |
| T021 | Delete unsalvageable files; atomic rewrite; idempotency | WP05 | |
| T022 | Migration tests (rewrite, delete, skip-v2, double-run) | WP05 | |
| T023 | Session-start orientation lists open Ops with close commands | WP06 | |
| T024 | Generalize Claude Code hook registrar; register Stop reminder hook | WP06 | |
| T025 | Update doctrine skill pack + standalone templates to open→work→close contract | WP06 | [P] |
| T026 | CHANGELOG entry for breaking change; run terminology guard | WP06 | [P] |
| T027 | Session-presence and prose tests (orientation content, hook registration) | WP06 | |

## Work Packages

### WP01 — Op Event Schema v2 (foundation)

- **Prompt**: tasks/WP01-op-event-schema-v2.md
- **Goal**: Split `InvocationRecord` into `OpStartedEvent`/`OpCompletedEvent`; completed events require outcome + `closed_by` and carry no blank started-only fields.
- **Priority**: P0 — every other WP builds on these models.
- **Independent test**: Unit suite proves a completed event without outcome is unconstructible and serialized events match `contracts/op-record-events.md`.
- **Subtasks**:
  - [x] T001 Define `OpStartedEvent` model (WP01)
  - [x] T002 Define `OpCompletedEvent` model (WP01)
  - [x] T003 Update `InvocationWriter` for v2 events (WP01)
  - [x] T004 Update readers for v2 shapes (WP01)
  - [x] T005 Unit tests for models/writer/readers (WP01)
- **Dependencies**: none
- **Estimated prompt size**: ~330 lines

### WP02 — `do` Open-Op Dispatch

- **Prompt**: tasks/WP02-do-open-op-dispatch.md
- **Goal**: `do` opens the Op and leaves it open; gains the SaaS propagator; output (rich + JSON) carries the close contract.
- **Priority**: P0 — the headline behavior change.
- **Independent test**: `do --json` yields `status: "open"`, a `close_contract` object, and a JSONL file with exactly one started event.
- **Subtasks**:
  - [x] T006 Remove auto-close from `do` (WP02)
  - [x] T007 Wire SaaS propagator into `do` (WP02)
  - [x] T008 Close-contract block in rich output (WP02)
  - [x] T009 `status` + `close_contract` in JSON payload (WP02)
  - [x] T010 Rewrite `do` integration tests (WP02)
- **Dependencies**: WP01
- **Estimated prompt size**: ~340 lines

### WP03 — Close Surface and Closing Actor

- **Prompt**: tasks/WP03-close-surface-closing-actor.md
- **Goal**: Closes record who closed (`agent` vs `doctor_sweep`); double close stays idempotent; auto-commit happens at close time only.
- **Priority**: P0.
- **Independent test**: Closing an Op writes `closed_by="agent"` and auto-commits with `op(<profile>): <action> [<id8>]`; second close errors cleanly.
- **Subtasks**:
  - [x] T011 `closed_by` in executor close path (WP03)
  - [x] T012 CLI close writes `closed_by="agent"` (WP03)
  - [x] T013 Close-time auto-commit semantics (WP03)
  - [x] T014 Close-surface tests (WP03)
- **Dependencies**: WP01
- **Estimated prompt size**: ~290 lines

### WP04 — Doctor Stale Sweep

- **Prompt**: tasks/WP04-doctor-stale-sweep.md
- **Goal**: `doctor ops --close-stale [--threshold H]` closes stale orphans as `abandoned`/`doctor_sweep` per `contracts/doctor-ops-close-stale.md`.
- **Priority**: P1 — the safety net that makes open-by-default sustainable.
- **Independent test**: Quickstart step 5 — sweep closes an old open Op, skips a fresh one, reports `already_closed` on race.
- **Subtasks**:
  - [x] T015 `close_stale_ops()` implementation (WP04)
  - [x] T016 CLI flags wiring (WP04)
  - [x] T017 Race handling (WP04)
  - [x] T018 Sweep tests + perf guard (WP04)
- **Dependencies**: WP03
- **Estimated prompt size**: ~300 lines

### WP05 — Legacy Record Migration

- **Prompt**: tasks/WP05-legacy-record-migration.md
- **Goal**: Upgrade migration rewrites legacy `kitty-ops/` records to v2, deletes unsalvageable files, idempotent on re-run.
- **Priority**: P1.
- **Independent test**: Fixture dir with legacy records → one run produces v2 files per the data-model mapping table; second run is a no-op.
- **Subtasks**:
  - [x] T019 Migration scaffold (detect/apply) (WP05)
  - [x] T020 Legacy→v2 rewrite mapping (WP05)
  - [x] T021 Delete + atomic rewrite + idempotency (WP05)
  - [x] T022 Migration tests (WP05)
- **Dependencies**: WP01
- **Estimated prompt size**: ~280 lines

### WP06 — Session Presence and Contract Prose

- **Prompt**: tasks/WP06-session-presence-contract-prose.md
- **Goal**: Claude Code session-start lists open Ops; Stop hook reminds; doctrine/skill/template prose teaches open→work→close; CHANGELOG records the breaking change.
- **Priority**: P1.
- **Independent test**: `spec-kitty session-start` with an open Op present prints id + close command; doctrine text contains no single-shot description of `do`.
- **Subtasks**:
  - [ ] T023 Open-Ops section in session-start orientation (WP06)
  - [ ] T024 Stop hook via generalized registrar (WP06)
  - [ ] T025 Doctrine skill/template prose updates (WP06)
  - [ ] T026 CHANGELOG + terminology guard (WP06)
  - [ ] T027 Presence/prose tests (WP06)
- **Dependencies**: WP02, WP04
- **Estimated prompt size**: ~330 lines

## Dependency Graph

```
WP01 ──► WP02 ──► WP06
  ├────► WP03 ──► WP04 ──► WP06
  └────► WP05
```

Parallel opportunities: after WP01 lands, WP02/WP03/WP05 can run in parallel lanes; WP04 follows WP03; WP06 last (depends on final capsule wording and doctor flags).

## MVP Scope

WP01 + WP02 + WP03 deliver the honest lifecycle end-to-end (open dispatch + real close). WP04–WP06 complete the safety net and teaching surfaces.
