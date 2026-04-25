# CLI Interview Decision Moments

**Mission:** `cli-interview-decision-moments-01KPWT8P`
**Mission ID:** `01KPWT8PNY8683QX3WBW6VXYM7`
**Mission type:** `software-dev`
**Target branch:** `main`
**Related issue:** `spec-kitty#757`

## Context

Today `spec-kitty` conducts user-facing interview Q&A in three flows:
- **Charter** — Python-side Q&A loop backed by `.kittify/charter/interview/answers.yaml`.
- **Specify** and **Plan** — LLM-driven: command templates instruct the agent on what to ask; the agent asks in chat and embeds `[NEEDS CLARIFICATION: …]` markers in `spec.md` / `plan.md` for anything deferred.

There is no structured ledger of "moments when the mission owner was asked a material question." The audit trail is prompt transcripts plus `answers.yaml` for charter only. That makes V1 Decision Moments (as frozen by `spec-kitty-events` 4.0.0 — `DecisionPointOpened(interview)`, `DecisionPointResolved(interview)`) a promise with no producer on this repo's side.

This mission builds the CLI-owned Decision Moment API, wires charter/specify/plan to call it at ask time and resolution time, and lands a deterministic local paper trail under each mission directory. Widening to Slack (`#758`) and SaaS sync (`#110`, `#111`) are downstream and out of scope for V1.

## Stakeholders / Actors

- **Mission owner** — human answering interview questions.
- **Charter command** — Python-side interview driver (`spec-kitty charter interview`).
- **Specify / plan commands** — LLM-driven via command templates.
- **Decision Moment CLI** (new) — owns `decision_id` minting, artifact writing, event emission, verify gate.
- **Event log** — existing `kitty-specs/<mission>/status.events.jsonl` gains DecisionPoint event lines.
- **Downstream consumers** (`#758` Widen Mode, `#110` SaaS projection, `#111` Slack orchestration) — read Decision Moments from the paper trail and event log.

## User Scenarios & Testing

### Scenario 1 — Charter interview emits a local Decision Moment per question

1. `spec-kitty charter interview` prompts mission owner with question Q1.
2. Before displaying Q1, charter calls `spec-kitty agent decision open ... --step-id charter.q1 --input-key ...` and receives `decision_id`.
3. On-disk state immediately has `decisions/index.json` updated and `decisions/DM-<decision_id>.md` created, both in state `open`.
4. Owner answers. Charter calls `spec-kitty agent decision resolve <decision_id> --final-answer "..."`.
5. `DecisionPointOpened(interview)` and `DecisionPointResolved(interview, terminal_outcome=resolved)` events are appended to `status.events.jsonl`.
6. `answers.yaml` is updated as before (primary charter state — unchanged behavior).

### Scenario 2 — Specify interview: LLM-driven ask-time emission

1. Template for specify instructs the LLM: "before asking Q<N>, run `spec-kitty agent decision open --mission <slug> --flow specify --slot-key specify.intent-summary.q1 --input-key <k> --question '<q>' --options '<json>'`."
2. LLM runs the command, receives `decision_id`.
3. Artifact + index + `Opened` event are written.
4. LLM asks the question in chat; the user answers.
5. LLM runs `spec-kitty agent decision resolve <decision_id> --final-answer "..."`.
6. `Resolved(interview)` event appended.

### Scenario 3 — Deferred answer with visible sentinel

1. User says "skip this for now" on a specify question.
2. LLM runs `spec-kitty agent decision defer <decision_id> --rationale "owner deferred; revisit in plan"`.
3. `Resolved(interview, terminal_outcome=deferred)` event emitted. Artifact status becomes `deferred`.
4. LLM writes the visible marker into `spec.md`: `[NEEDS CLARIFICATION: …] <!-- decision_id: <decision_id> -->`.
5. Later, `spec-kitty agent decision verify --mission <slug>` succeeds — every deferred decision has a matching inline marker.

### Scenario 4 — Canceled decision

1. User says "this question doesn't apply."
2. LLM runs `spec-kitty agent decision cancel <decision_id> --rationale "not applicable"`.
3. `Resolved(interview, terminal_outcome=canceled)` event emitted. Artifact status becomes `canceled`. Does NOT produce a `[NEEDS CLARIFICATION]` marker.

### Scenario 5 — Other / free-text answer

1. Q5 offers options `["session", "oauth2", "oidc", "Other"]`.
2. User types a custom answer.
3. LLM runs `spec-kitty agent decision resolve <decision_id> --final-answer "internal SSO proxy" --other-answer`.
4. Event emitted with `other_answer=true`, `final_answer="internal SSO proxy"`.

### Scenario 6 — Idempotent retry of `decision open`

1. LLM crashes mid-call and retries `decision open` with the same logical key `(mission_id, flow, step_id/slot_key, input_key)`.
2. CLI returns the existing `decision_id` from the first call. No duplicate event. No duplicate artifact.
3. If the prior decision is in a terminal state, CLI returns a structured `already_closed` error.

### Scenario 7 — Verify catches drift

1. A deferred decision has no matching inline marker in `spec.md`.
2. `spec-kitty agent decision verify --mission <slug>` exits non-zero with a structured error listing the offending decision_id and the missing marker location.

### Scenario 8 — Local-first: SaaS absent

1. `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is NOT set.
2. All decision operations complete locally: paper trail, events, verify.
3. No hosted auth or network calls.

### Edge cases

- `decision open` without `--step-id` or `--slot-key` → reject with structured error.
- `decision resolve` called twice with identical payload → idempotent no-op.
- `decision resolve` called twice with different `final_answer` → reject with structured `conflict` error.
- `decision resolve` after `decision defer` → reject with `already_closed`.
- Re-asking a previously closed question → NOT auto-revived. A new Decision Moment must be minted explicitly via `decision open` with a different `slot_key` (e.g., `.retry-1`).
- Event log corruption or write failure mid-operation → operation is atomic at the event-write boundary; partial artifact writes are cleaned up or detected by verify.
- Charter `answers.yaml` is unchanged when a decision is deferred or canceled — only `resolve` writes into `answers.yaml` (same as 3.x "only real answers are recorded").

## Functional Requirements

| ID     | Requirement                                                                                                                                                                                                                                                                                 | Status   |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| FR-001 | Introduce a new CLI subgroup `spec-kitty agent decision` with subcommands `open`, `resolve`, `defer`, `cancel`, `verify`. Each returns JSON on `--json` (default) and structured errors with stable error codes.                                                                               | Approved |
| FR-002 | `decision open` SHALL require `--mission <handle>`, `--flow {charter\|specify\|plan}`, `--input-key <str>`, `--question <str>`, and EITHER `--step-id <str>` OR `--slot-key <str>`. It SHALL reject calls missing both step_id and slot_key with a structured error.                            | Approved |
| FR-003 | `decision open` SHALL mint a ULID `decision_id` at invocation time and return it on stdout/JSON before any artifact write or event emission.                                                                                                                                                 | Approved |
| FR-004 | `decision open` SHALL be idempotent on the logical key `(mission_id, origin_flow, step_id\|slot_key, input_key)`: if an existing Decision Moment in a non-terminal state matches, return the existing `decision_id` with no new event and no new artifact.                                   | Approved |
| FR-005 | If the matching Decision Moment is in a terminal state, `decision open` SHALL return a structured `already_closed` error (code `DECISION_ALREADY_CLOSED`) including the existing `decision_id` and its terminal outcome.                                                                      | Approved |
| FR-006 | `decision open` SHALL persist (atomically) a new entry in `kitty-specs/<mission>/decisions/index.json` and a new per-decision artifact at `kitty-specs/<mission>/decisions/DM-<decision_id>.md`, both in state `open`, BEFORE appending the `DecisionPointOpened(interview)` event.             | Approved |
| FR-007 | `decision open` SHALL append a `DecisionPointOpened` event (interview variant per `spec-kitty-events` 4.0.0) to `kitty-specs/<mission>/status.events.jsonl` with origin_surface=planning_interview, origin_flow, question, options, input_key, step_id (or slot_key), actor metadata.          | Approved |
| FR-008 | `decision resolve <decision_id>` SHALL require `--final-answer <str>` (non-empty) and OPTIONAL `--other-answer`, `--rationale`, `--resolved-by`. Emits `DecisionPointResolved(interview, terminal_outcome=resolved)`. Artifact status becomes `resolved`. Index entry updates.                  | Approved |
| FR-009 | `decision defer <decision_id>` SHALL require `--rationale <str>` (non-empty) and OPTIONAL `--resolved-by`. Emits `DecisionPointResolved(interview, terminal_outcome=deferred)`. Artifact status becomes `deferred`. Does NOT emit `DecisionInputAnswered`.                                     | Approved |
| FR-010 | `decision cancel <decision_id>` SHALL require `--rationale <str>` (non-empty) and OPTIONAL `--resolved-by`. Emits `DecisionPointResolved(interview, terminal_outcome=canceled)`. Artifact status becomes `canceled`. Does NOT emit `DecisionInputAnswered`.                                    | Approved |
| FR-011 | Terminal commands (`resolve`/`defer`/`cancel`) SHALL be idempotent on exact re-call: identical payload returns success no-op. Contradictory re-call (different final_answer, or different terminal outcome) SHALL be rejected with code `DECISION_TERMINAL_CONFLICT`.                         | Approved |
| FR-012 | `spec-kitty charter interview` SHALL call `decision open` before presenting each question and `decision resolve`/`defer`/`cancel` after each answer. Existing `answers.yaml` behavior SHALL be preserved: only resolved-with-answer decisions write to `answers.yaml`.                         | Approved |
| FR-013 | The `specify` and `plan` command templates under `src/specify_cli/missions/*/command-templates/` SHALL instruct the LLM to call `decision open` before asking each interview question and the appropriate terminal command after each answer. Templates SHALL be updated in this mission.      | Approved |
| FR-014 | The LLM SHALL place visible `[NEEDS CLARIFICATION: <text>] <!-- decision_id: <decision_id> -->` markers in `spec.md` / `plan.md` for every deferred Decision Moment. Templates SHALL instruct the LLM to do so and to include the hidden anchor comment.                                       | Approved |
| FR-015 | `spec-kitty agent decision verify --mission <slug>` SHALL check: (a) every deferred decision has a matching inline marker with matching `decision_id` anchor in the appropriate target doc, (b) every marker has a backing deferred decision, (c) no stale markers linger after a decision moves out of deferred state. Exits 0 on clean, non-zero with structured JSON findings otherwise. | Approved |
| FR-016 | The CLI SHALL bump `spec-kitty-events` dependency to `==4.0.0` and refresh the vendored copy at `src/specify_cli/spec_kitty_events/`. Any existing ADR-style DecisionPoint payload producer in the CLI SHALL add `origin_surface="adr"`.                                                       | Approved |
| FR-017 | All decision operations SHALL work with `SPEC_KITTY_ENABLE_SAAS_SYNC` unset. No network calls, no hosted-auth access in local-only mode.                                                                                                                                                      | Approved |
| FR-018 | The per-decision artifact `DM-<decision_id>.md` SHALL be human-readable markdown including: decision_id, origin_flow, step_id/slot_key, input_key, question, options, status, final_answer (if resolved), rationale (if deferred/canceled), other_answer flag, created_at, resolved_at, resolved_by. Updated on every state transition. | Approved |
| FR-019 | `decisions/index.json` SHALL be a deterministic JSON document (sorted keys, stable ordering) listing every decision_id with its state and metadata. Updated on every state transition.                                                                                                        | Approved |
| FR-020 | The CLI SHALL support `--dry-run` on `decision open`/`resolve`/`defer`/`cancel` that validates inputs and reports what would happen without side effects.                                                                                                                                    | Approved |

## Non-Functional Requirements

| ID      | Requirement                                                                                                                                                                                                                                                | Status   |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| NFR-001 | All decision operations SHALL complete in under 200 ms p95 on a warm filesystem with an index of up to 1000 existing decisions in the mission.                                                                                                              | Approved |
| NFR-002 | Writes SHALL be atomic at the file level: partial index/artifact writes SHALL NOT leave the mission in a half-updated state. Use write-to-tmp-then-rename pattern or equivalent.                                                                            | Approved |
| NFR-003 | `ruff check .` and `ruff format --check .` SHALL pass on all new/changed code. `mypy` SHALL pass on changed modules (the repo's existing type-checking scope).                                                                                               | Approved |
| NFR-004 | Unit and integration tests SHALL cover at least 90% of new code in `src/specify_cli/` (charter/specify CLI extensions + decision module).                                                                                                                    | Approved |
| NFR-005 | `pytest tests/` SHALL remain green on the full suite after changes. Full-suite wall time SHALL NOT regress more than 10% vs. baseline.                                                                                                                      | Approved |
| NFR-006 | All events emitted SHALL validate against the committed `spec-kitty-events` 4.0.0 JSON schemas. Schema-drift check (if present in this repo) SHALL pass.                                                                                                     | Approved |

## Constraints

| ID    | Constraint                                                                                                                                                                                                                                                    | Status   |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| C-001 | V1 scope: charter + specify + plan only. `tasks` is out of scope for this mission. Any tasks-side interview must reuse the same API in a future mission.                                                                                                        | Approved |
| C-002 | Widen Mode (widening a Decision Moment to Slack) is out of scope for this mission (`#758`). The `Widened` event is NOT emitted by this mission's code.                                                                                                          | Approved |
| C-003 | SaaS sync is out of scope. No SaaS-specific code, tests, or fixtures. Decisions work when `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is not set.                                                                                                                           | Approved |
| C-004 | `decision_id` is a plain ULID. No `DM-` prefix on the wire. The `DM-` prefix lives only in artifact filenames: `DM-<decision_id>.md`.                                                                                                                         | Approved |
| C-005 | Charter's `answers.yaml` remains primary charter state in V1. Decision Moments are additive. Do NOT remove or refactor answers.yaml consumers in this mission.                                                                                                  | Approved |
| C-006 | `[NEEDS CLARIFICATION]` markers remain LLM-authored. CLI does NOT patch `spec.md` / `plan.md` body text in V1.                                                                                                                                                   | Approved |
| C-007 | Dependency upgrade: `spec-kitty-events` MUST move to `==4.0.0`. The vendored copy at `src/specify_cli/spec_kitty_events/` MUST match 4.0.0 exactly.                                                                                                             | Approved |
| C-008 | All new code lives under `src/specify_cli/`. No new top-level packages.                                                                                                                                                                                         | Approved |
| C-009 | Events appended to `status.events.jsonl` MUST preserve the existing event envelope shape used by the status-model pipeline.                                                                                                                                     | Approved |
| C-010 | `decision verify` is check-only in V1. No auto-fix, no doc body mutation.                                                                                                                                                                                       | Approved |

## Success Criteria

- **SC-1 — Ask-time paper trail complete.** Every interview question asked by charter/specify/plan has a corresponding Decision Moment artifact on disk BEFORE the user sees the question.
- **SC-2 — Terminal parity.** Every user answer produces exactly one of: resolved event + DecisionInputAnswered, deferred event (no DecisionInputAnswered), canceled event (no DecisionInputAnswered). No silent drops.
- **SC-3 — Verify catches drift.** `decision verify` rejects any spec/plan doc where a deferred DM lacks a matching inline sentinel or a sentinel lacks a backing DM.
- **SC-4 — Local-first baseline.** All 8 user scenarios work end-to-end with SaaS absent.
- **SC-5 — Idempotency.** Retried `decision open` never produces duplicate events or artifacts on the happy path; retried terminal commands never produce duplicates on exact re-call.
- **SC-6 — Upstream contract conformance.** 100% of emitted events validate against `spec-kitty-events 4.0.0` schemas.
- **SC-7 — Full-suite green.** All pre-existing spec-kitty tests continue to pass; new tests cover ≥90% of new code.

## Key Entities

- **DecisionMoment (on-disk)** — artifact at `decisions/DM-<decision_id>.md` + index row at `decisions/index.json`.
- **decision_id** — ULID, plain (no prefix on the wire).
- **Logical key** — `(mission_id, origin_flow, step_id|slot_key, input_key)` tuple used for idempotency.
- **Index entry** — `{decision_id, origin_flow, step_id, slot_key, input_key, question, options, status, final_answer?, rationale?, other_answer, created_at, resolved_at?, resolved_by?}`.
- **Artifact** — Markdown rendering of the index entry with full question/options context + change log.
- **DecisionPoint events** — wire-level events emitted to `status.events.jsonl`: `DecisionPointOpened(interview)`, `DecisionPointResolved(interview)`. `DecisionPointWidened` and `DecisionPointDiscussing` are OUT OF SCOPE for this mission.
- **Sentinel marker** — `[NEEDS CLARIFICATION: <text>] <!-- decision_id: <decision_id> -->` in `spec.md` / `plan.md`.

## Assumptions

1. `spec-kitty-events 4.0.0` is shipped and importable (repo 1 of this program just merged it).
2. The existing `status.events.jsonl` event envelope accepts new event types without schema changes to the envelope itself — only the payload shape is DecisionPoint-specific.
3. Charter's `answers.yaml` schema is unchanged; `decision resolve` writes to it via the existing charter persistence path.
4. Command templates under `src/specify_cli/missions/*/command-templates/` are the source of truth for LLM instructions (per CLAUDE.md). Agent copies (`.claude/commands/*`, `.agents/skills/*`, etc.) regenerate via the existing migration/publish path.
5. The Python CLI uses `typer`, `rich`, `ruamel.yaml`, `pytest`. This mission stays within that stack.
6. The vendored `src/specify_cli/spec_kitty_events/` is updated by copying the 4.0.0 source tree from `../spec-kitty-events/src/spec_kitty_events/`.

## Out of Scope

- Widen Mode (`spec-kitty#758`) — `DecisionPointWidened` event emission, Slack orchestration, SaaS audience lookup.
- SaaS sync projections (`spec-kitty-saas#110`, `#111`).
- Tasks-phase interview support.
- Auto-fix in `decision verify`.
- CLI doc-patching of `spec.md` / `plan.md` body text.
- Migrating charter to DecisionMoment-primary (answers.yaml derived); stays as `answers.yaml` primary in V1.
- Any changes to the existing Discussing/Overridden event code paths.

## Dependencies

- **Upstream (blockers):** `spec-kitty-events 4.0.0` (completed; merged on main of that repo).
- **Downstream (unblocks):** `spec-kitty#758` (Widen Mode + write-back), `spec-kitty-saas#110` (Teamspace projection), `spec-kitty-saas#111` (Slack orchestration), `spec-kitty-end-to-end-testing#25` (E2E acceptance), `spec-kitty-plain-english-tests#1` (regression coverage).

## Open Questions

None. All clarifications resolved during discovery (vocabulary, idempotency, paper trail layout, step_id fallback, decision_id format, dependency bump, answers.yaml migration posture, sentinel rendering).
