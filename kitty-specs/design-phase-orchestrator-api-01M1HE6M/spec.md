# Mission Specification: Design-Phase Orchestrator-API Verbs

**Mission Branch**: `feat/design-phase-orchestrator-api-3837`
**Created**: 2026-09-02
**Status**: Draft
**Input**: GitHub issue #3837 — "orchestrator-api: design-phase verbs (specify/plan/tasks/analyze + decision resolution) for external hosts"

## Summary

`spec-kitty orchestrator-api` already lets an external host (a CI pipeline, a
custom dashboard, or a native driver such as Kitty Desktop) run the entire
work-package implementation loop — `contract-version`, `list-ready`,
`start-implementation` (with `--policy`), `start-review`, `transition` (with
the `review_result` triple), `merge-mission` — without ever touching the host
CLI. The design phases (`specify`, `plan`, `tasks`/finalize, `analyze`,
decision resolution) have no such surface: they exist only as host-CLI
commands and slash-command templates. `references/host-boundary-rules.md`'s
own Boundary Decision Matrix states the rule an external host is currently
forced to violate: "Agent queries its next step → Host CLI → Agent is inside
the project," and lists a custom dashboard as its own named example of an
orchestrator-api caller. Today, an external host driving design phases has no
compliant path.

This mission adds an orchestrator-api verb set for the design phases,
mirroring the WP-loop verbs' existing discipline (envelope shape, `--policy`
provenance fields, structured error codes, additive-only contract evolution).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - External host drives specify → plan → tasks without shelling the host CLI (Priority: P1)

An external host (e.g. Kitty Desktop) wants to create a new mission, scaffold
its plan, and finalize its work packages entirely through orchestrator-api —
the same way it already drives the WP-implementation loop — instead of
shelling `spec-kitty specify --json` / `spec-kitty plan --json` / `spec-kitty
tasks --json` across the host-CLI boundary that `host-boundary-rules.md`
forbids it from crossing.

**Why this priority**: This is the largest fraction of the ask by verb count
and the direct precedent-following work: `specify`/`plan`/`tasks` on the host
CLI are already thin shims over `agent_feature.create_mission`,
`agent_feature.setup_plan`, and `agent_feature.finalize_tasks`, all three of
which already accept `json_output: bool` and already skip the interactive
interview path when `json_output=True`. Wrapping them is surface work with no
new engine to build.

**Independent Test**: Can be fully tested by calling the new `specify`,
`plan`, and `tasks` orchestrator-api verbs against a scratch project with only
`--policy` and CLI arguments (no interactive TTY), and asserting each returns
a `success: true` envelope whose `data` carries the artifact paths it wrote
(`spec.md`, `plan.md`, finalized `tasks/` manifest) — verified against the
filesystem, not just the envelope.

**Acceptance Scenarios**:

1. **Given** a project with `.kittify/` initialized and no existing mission
   for the requested slug, **When** the external host calls the `specify`
   orchestrator-api verb with `--mission-type`, `--topology` (optional) and
   `--policy`, **Then** the command returns `success: true` with `data`
   containing the mission slug, mission directory path, and `spec.md` path,
   and `kitty-specs/<slug>/spec.md` exists on disk with the placeholder
   template content (matching what `agent_feature.create_mission(...,
   json_output=True)` already produces for the host CLI's `--json` path).
2. **Given** a mission already scaffolded via `specify`, **When** the host
   calls the `plan` orchestrator-api verb with `--mission` and `--policy`,
   **Then** the command returns `success: true` with `data.plan_path`
   pointing at `kitty-specs/<slug>/plan.md`, and that file exists on disk.
3. **Given** a mission with a completed `tasks/` directory ready for
   finalization, **When** the host calls the `tasks` (finalize) orchestrator-
   api verb with `--mission` and `--policy`, **Then** the command returns
   `success: true` with `data` reflecting the finalized work-package manifest
   (WP count, WP ids), matching `agent_feature.finalize_tasks(...,
   json_output=True)`'s existing JSON shape.
4. **Given** the host calls `specify` for a slug that already has a mission
   directory, **When** the underlying `create_mission` call raises its
   already-established duplicate-mission error, **Then** the orchestrator-api
   verb returns `success: false` with a structured `error_code` (not a bare
   exception, not a 0-exit silent no-op) and the existing mission directory is
   untouched.

---

### User Story 2 - External host queries analyze context and records an analysis verdict without doing the reasoning itself (Priority: P1)

An external host wants to drive the `analyze` design phase the same way it
drives everything else — but `analyze`'s cross-artifact reasoning is an LLM
prompt template (`.kittify/overrides/missions/software-dev/command-templates/
analyze.md`), not a deterministic engine spec-kitty can run server-side. The
host needs (a) a query verb that hands back the same prerequisite/context data
the host CLI's `check-prerequisites --json --include-tasks` surfaces today, so
its own calling agent can perform the analysis, and (b) a record verb that
persists that agent's finished analysis report exactly as `record_analysis`
does today — with a result the host can actually trust, unlike the raw
subprocess exit code.

**Why this priority**: `analyze` is the one part of the ask with no existing
deterministic engine to wrap; getting its scope boundary and its error-
signal contract right is the highest-risk part of this mission and blocks
Kitty Desktop's design-phase pipeline from being end-to-end orchestrator-api-
only.

**Independent Test**: Can be fully tested by calling the `analyze-context`
verb against a mission mid-tasks-phase and asserting its envelope carries the
same prerequisite/task data as `check-prerequisites --json --include-tasks`;
then calling `analyze-record` with a fabricated analysis report body and
asserting `analysis-report.md` is written with the submitted verdict,
independent of whatever the underlying event-emitting write path's own exit
behaviour does.

**Acceptance Scenarios**:

1. **Given** a mission with a finalized `tasks/` manifest, **When** the host
   calls the `analyze-context` orchestrator-api verb with `--mission`,
   **Then** it returns `success: true` with `data` containing the same
   prerequisite and task-listing fields the host CLI's `agent mission-run
   check-prerequisites --json --include-tasks` already returns for that
   mission — this verb performs no analysis reasoning itself, only assembles
   the context an external agent needs to perform it.
2. **Given** the calling agent has produced an analysis report body,
   **When** the host calls the `analyze-record` orchestrator-api verb with
   `--mission`, `--input-file` (or an inline body), `--agent`, and
   `--policy`, **Then** on success the envelope's `success: true` is derived
   from re-reading `kitty-specs/<slug>/analysis-report.md` off disk and
   confirming its `verdict` field matches what was submitted — NOT from
   trusting the underlying `record_analysis` subprocess/call's raw
   return value or exit code (see NFR-004 / SK-93 below).
3. **Given** the underlying write path exits non-zero or times out (the
   SK-93 pattern: `record_analysis` observed exiting 124 while
   `analysis-report.md` had, in fact, already been written correctly with
   `verdict: ready`), **When** `analyze-record` re-reads the artifact and
   finds it correctly written with the submitted verdict, **Then** the verb
   reports `success: true` — the artifact on disk is the source of truth, not
   the subprocess outcome.
4. **Given** the underlying write path exits non-zero AND the artifact was
   NOT written (a genuine failure), **When** `analyze-record` re-reads and
   finds no matching artifact, **Then** the verb reports `success: false`
   with a structured `error_code` distinguishing "write did not happen" from
   "write happened, signal was noise."

---

### User Story 3 - External host resolves a charter/specify/plan decision moment (Priority: P2)

An external host is driving a mission through `specify`/`plan` and hits a
decision moment (e.g. a widen-enabled interview question) that needs
resolving before the phase can proceed. It wants to open, resolve, defer, or
cancel that decision the same way the existing `decision_app` CLI subcommands
already do (`spec-kitty agent decision open|resolve|defer|cancel`), via
orchestrator-api instead of the host CLI.

**Why this priority**: Decision resolution is the strongest existing
precedent in this mission — `src/specify_cli/decisions/service.py` already
exposes `open_decision`, `resolve_decision`, `defer_decision`, and
`cancel_decision` as pure functions, already wrapped 1:1 by
`src/specify_cli/cli/commands/decision.py`. The scope is bounded: `OriginFlow`
(`src/specify_cli/decisions/models.py:36-41`) only has `charter`, `specify`,
and `plan` members — there is no `tasks` or `analyze` decision-moment
concept to cover.

**Independent Test**: Can be fully tested by opening a decision via the new
verb for a `specify`-origin flow, resolving it, and asserting the persisted
decision ledger (`decisions/index.json`) reflects the resolution — matching
what the equivalent `spec-kitty agent decision resolve` host-CLI call would
produce.

**Acceptance Scenarios**:

1. **Given** a mission mid-`specify` phase, **When** the host calls the
   `decision-open` orchestrator-api verb with `--mission`, `--origin
   specify`, the question payload, and `--policy`, **Then** it returns
   `success: true` with `data.decision_id`, and the decision is persisted in
   the mission's decision ledger with `status: open`.
2. **Given** an open decision id, **When** the host calls `decision-resolve`
   with `--mission`, `--decision-id`, an answer payload, and `--policy`,
   **Then** it returns `success: true` with `data.status: resolved`, and the
   ledger entry's status is updated on disk.
3. **Given** an open decision id, **When** the host calls `decision-defer` or
   `decision-cancel`, **Then** the corresponding `defer_decision` /
   `cancel_decision` service function is invoked and the ledger reflects the
   new status, with the same structured-error behavior as the host-CLI
   `decision_app` subcommands for invalid transitions (e.g. resolving an
   already-terminal decision).
4. **Given** a `--mission` whose current phase is `tasks` or `analyze` (no
   `OriginFlow` member exists for either), **When** the host calls any
   decision-resolution verb with an origin outside `{charter, specify,
   plan}`, **Then** the verb rejects with a structured `error_code` (e.g.
   `INVALID_ORIGIN_FLOW`) rather than silently accepting or misfiling the
   decision under an unrelated origin.

---

### User Story 4 - External host queries design-phase status the way it queries WP readiness (Priority: P2)

An external host wants a `list-ready`-equivalent query for the design
pipeline: "what design phase is this mission in, what's the next actionable
step, are there open decisions blocking it" — without triggering any state
transition, mirroring `list-ready`'s read-only, event-log-reduction pattern.

**Why this priority**: Every WP-loop-driving host needs a status view before
it acts; the design pipeline needs the same, and its absence would force a
host to infer phase state indirectly from artifact presence/absence, which is
exactly the kind of undocumented inference `host-boundary-rules.md` warns
against.

**Independent Test**: Can be fully tested by calling the new status/query
verb against missions in different design-phase states (fresh, mid-plan,
tasks finalized, analyze pending, open decision blocking) and asserting the
returned `current_phase` / `next_action` / `open_decisions` fields match the
mission's actual on-disk state.

**Acceptance Scenarios**:

1. **Given** a mission with only `spec.md` scaffolded, **When** the host
   calls the design-phase status/query verb with `--mission`, **Then** it
   returns `success: true` with `data.current_phase: "specify"` (or
   equivalent) and `data.next_action` naming the `plan` verb.
2. **Given** a mission with an open, unresolved decision moment, **When** the
   host calls the status/query verb, **Then** `data.open_decisions` lists
   that decision's id and origin flow, and `data.next_action` indicates
   resolution is required before the phase can advance.
3. **Given** a mission whose `tasks/` is finalized and `analysis-report.md`
   does not yet exist, **When** the host calls the status/query verb,
   **Then** `data.current_phase` indicates `analyze` is the next actionable
   phase and `data.next_action` names the `analyze-context` verb.
4. This verb performs no state transition and no event emission — calling it
   repeatedly against an unchanged mission returns byte-identical
   `current_phase`/`next_action` fields, exactly as repeated `list-ready`
   calls do today for WP state.

---

### Edge Cases

- What happens when an external host calls a design-phase verb against a
  mission slug that does not exist? → structured `error_code` (mirroring
  `_resolve_mission_dir_or_fail`'s existing pattern for the WP-loop verbs),
  never a bare traceback or a silent empty-success envelope.
- What happens when `--policy` is omitted on a verb that mutates state
  (`specify`, `plan`, `tasks`, `analyze-record`, `decision-open`,
  `decision-resolve`, `decision-defer`, `decision-cancel`)? → rejected with
  `POLICY_METADATA_REQUIRED`, exactly as `start-implementation` and
  `start-review` already reject a missing `--policy` today. Read-only verbs
  (`analyze-context`, the status/query verb) do not require `--policy`,
  mirroring `list-ready`'s existing no-policy contract.
- What happens when `analyze-record` is called twice with the same verdict
  (idempotent retry after an SK-93-style false-failure signal)? → the second
  call re-reads the artifact, finds it already correctly written, and returns
  `success: true` without attempting a duplicate write that could corrupt
  state — never a silent double-write and never a hard failure on "nothing
  changed."
- What happens when a mission already mid-flight (e.g. already in `analyze`,
  already has open WPs in the implementation loop) exists at the moment this
  contract surface ships? → nothing about its existing state or transitions
  changes; the new verbs are purely additive callers of the same underlying
  service functions the host CLI already calls for that mission. See NFR-001.
- What happens when `decision-resolve` is called with a `--decision-id` that
  is already `resolved` or `cancelled` (terminal)? → rejected with the same
  structured error the host-CLI `decision_app resolve` subcommand already
  raises for an invalid terminal-state transition, not silently accepted as a
  no-op success.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | `specify` orchestrator-api verb | As an external host, I want to scaffold a new mission via orchestrator-api so that I never shell the host CLI to create a mission. | High | Open |
| FR-002 | `plan` orchestrator-api verb | As an external host, I want to scaffold `plan.md` via orchestrator-api so that plan creation stays inside the orchestrator-api contract. | High | Open |
| FR-003 | `tasks` (finalize) orchestrator-api verb | As an external host, I want to finalize a mission's work-package manifest via orchestrator-api so that task finalization stays inside the contract. | High | Open |
| FR-004 | `analyze-context` orchestrator-api verb (query) | As an external host, I want the same prerequisite/task context `check-prerequisites --json --include-tasks` returns, via orchestrator-api, so that my calling agent can perform cross-artifact analysis without a host-CLI call. | High | Open |
| FR-005 | `analyze-record` orchestrator-api verb | As an external host, I want to persist my agent's finished analysis report via orchestrator-api, with a trustworthy success signal, so that I know the report actually landed regardless of the underlying subprocess's exit behavior. | High | Open |
| FR-006 | `decision-open` orchestrator-api verb | As an external host, I want to open a charter/specify/plan decision moment via orchestrator-api so that decision tracking stays inside the contract. | Medium | Open |
| FR-007 | `decision-resolve` orchestrator-api verb | As an external host, I want to resolve an open decision via orchestrator-api so that I can unblock a phase without the host CLI. | Medium | Open |
| FR-008 | `decision-defer` orchestrator-api verb | As an external host, I want to defer a decision via orchestrator-api so that a decision can be revisited later without blocking the current phase. | Medium | Open |
| FR-009 | `decision-cancel` orchestrator-api verb | As an external host, I want to cancel a decision via orchestrator-api so that a no-longer-relevant decision is removed from the active ledger. | Medium | Open |
| FR-010 | Design-phase status/query verb | As an external host, I want a `list-ready`-equivalent read-only status view of the design pipeline so that I know the current phase, next action, and any blocking open decisions before I act. | High | Open |
| FR-011 | `CONTRACT_VERSION` bump to 1.4.0 | As an external host, I want a versioned contract bump that documents the new verbs so that I can detect capability via `contract-version` the same way I detect existing verbs. | High | Open |
| FR-012 | Decision-resolution origin-flow scope guard | As an external host, I want the decision-resolution verbs to reject an origin outside `{charter, specify, plan}` so that I never silently misfile a decision under a flow that has no `OriginFlow` member. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Additive-only contract change | The 10 existing `orchestrator_api/commands.py` verbs (`contract-version`, `mission-state`, `list-ready`, `resolve-workspace`, `start-implementation`, `start-review`, `transition`, `append-history`, `accept-mission`, `merge-mission`) and `MIN_PROVIDER_VERSION` ("0.1.0") are unchanged in behavior, request shape, and response shape. A mission already mid-flight in any phase (including one already in `analyze` or with open WPs in the implementation loop) observes zero change to its existing state-transition contract — the new verbs are additive callers of the same underlying service functions the host CLI already calls. | Compatibility | High | Open |
| NFR-002 | No silent success | No new verb may return `success: true` on a 0-count/no-op operation it did not actually perform, write `unknown` in place of a real field value, or swallow an underlying exception into a bare `None`/empty envelope. Every failure path returns a structured `error_code` with a human-readable `error` message, exactly matching the existing `_fail(cmd, error_code, message, ...)` pattern used throughout `commands.py`. | Reliability | High | Open |
| NFR-003 | Pre-existing test baseline | `main` carries ~23 known-red tests already tracked as issue #3284. New test module(s) added under `tests/specify_cli/orchestrator_api/` for this mission's verbs must be green on introduction; #3284's pre-existing reds are not this mission's concern to fix and no new issue is opened for them. | Testability | Medium | Open |
| NFR-004 | Artifact-verified success for event-emitting wraps | Any orchestrator-api verb that wraps an event-emitting host-CLI call (in this mission: `analyze-record` wrapping `record_analysis`) MUST determine `success` by re-reading the artifact/state the call was supposed to produce (the `analysis-report.md` file and/or `status.events.jsonl`) rather than trusting the underlying call's raw exit code or return value. This generalizes the SK-93 finding: `record-analysis` was observed exiting 124 (timeout, with a "project sync store is locked" warning) after `analysis-report.md` had, in fact, already been written correctly with `verdict: ready` — exit code is not evidence in either direction on this call chain, and this NFR is the standing principle any future event-emitting wrap in this mission or later ones must also follow. | Reliability | High | Open |
| NFR-005 | Envelope/policy-provenance parity | Every new mutating verb accepts and validates `--policy` using the existing `parse_and_validate_policy` / `policy_to_dict` path, and every new verb's response uses the existing `make_envelope(command=..., success=..., data=...)` shape, with `validate_outbound_payload` applied to `data` before emission — matching `start-implementation`/`start-review`/`transition` byte-for-byte in structure. | Consistency | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No `spec-kitty-events` / `spec-kitty-tracker` changes | This mission touches neither the `spec-kitty-events` nor `spec-kitty-tracker` external PyPI packages. Both are true external dependencies (declared in `pyproject.toml`, resolved via `uv sync`), not vendored in this repo, and there is no reference to `spec-kitty-events` anywhere in `orchestrator_api/` or `envelope.py` today. Any FR that would require touching either package is out of scope for this spec. | Technical | High | Open |
| C-002 | No server-side analysis reasoning | Spec-kitty MUST NOT gain a verb that performs the `analyze` cross-artifact reasoning itself. `analyze.md` is an LLM prompt template; the reasoning happens client-side in the calling agent, exactly as spec-kitty cannot perform WP implementation itself in `start-implementation`/`start-review`. `analyze-context` supplies context only; `analyze-record` persists a finished report only. | Technical | High | Open |
| C-003 | Decision-resolution scope bounded to `OriginFlow` members | The decision-resolution verbs cover exactly the `OriginFlow` cases that exist today: `charter`, `specify`, `plan`. `tasks` and `analyze` have no decision-moment concept in the current `OriginFlow` enum and this mission does not add one. | Technical | Medium | Open |
| C-004 | Single PR, no follow-up issues | This mission's default PR shape is one PR covering the full scope (specify/plan/tasks verbs, decision-resolution verbs, analyze-context/analyze-record verbs, status/query verb, contract-version bump, docs) — every part of the issue #3837 ask belongs in this mission's scope, not deferred to a follow-up issue. The PR body must carry `Closes #3837`. | Process | High | Open |

### Key Entities

- **Design-phase envelope**: the same canonical JSON response envelope (`make_envelope`) already used by the 10 existing orchestrator-api verbs — `command`, `success`, `data`, and on failure `error_code`/`error`. No new envelope shape is introduced; new verbs reuse it.
- **Decision moment**: an entry in a mission's decision ledger (`decisions/index.json`), keyed by `decision_id`, carrying `origin` (one of `OriginFlow.CHARTER`/`SPECIFY`/`PLAN`), `status` (open/resolved/deferred/cancelled), and the question/answer payload — unchanged in shape by this mission, only newly reachable via orchestrator-api.
- **Analysis report artifact**: `kitty-specs/<slug>/analysis-report.md`, written by `record_analysis` today and by `analyze-record` under this mission — the ground truth `analyze-record` must re-read to determine its own success (NFR-004).
- **Design-phase status snapshot**: the read-only aggregate (`current_phase`, `next_action`, `open_decisions`) returned by the new status/query verb, reduced from the mission's event log and decision ledger the same way `list-ready` reduces WP state — never persisted, never mutating.

## Clarifications / Decision Records

Persisted verbatim from the pre-spec readiness investigation so a later
reviewer (or `sk-review`) can audit these without re-deriving them:

1. **Surface-only confirmation.** `specify`/`plan`/`tasks` on the host CLI
   (`src/specify_cli/cli/commands/lifecycle.py:129,212,266`) are already thin
   shims delegating to `agent_feature.create_mission`
   (`mission_create.py:627`), `agent_feature.setup_plan`
   (`mission_setup_plan.py:1097`), `agent_feature.finalize_tasks`
   (`mission_finalize.py:3075`) — all three already accept `json_output:
   bool` and skip the interactive interview path when `json_output=True`
   (`lifecycle.py:178-193,238-262`). Decision resolution is the strongest
   precedent: `src/specify_cli/decisions/service.py` exposes `open_decision`
   (:260), `resolve_decision` (:528), `defer_decision` (:575),
   `cancel_decision` (:612) as pure functions, already wrapped 1:1 by
   `src/specify_cli/cli/commands/decision.py`'s `decision_app`. This mission
   is surface work over an existing engine, not new engine work.

2. **`analyze` precedent choice.** `analyze` is the one genuine exception —
   it has no deterministic engine to wrap; the cross-artifact reasoning
   happens client-side in the calling agent via the
   `.kittify/overrides/missions/software-dev/command-templates/analyze.md`
   prompt template, not inside spec-kitty. **Resolution (adopted, FR-004 /
   FR-005 / C-002): mirror `start-review`'s pattern** — a context/query verb
   (`analyze-context`, mirroring `agent mission-run check-prerequisites
   --json --include-tasks`) plus a record verb (`analyze-record`, wrapping
   `record_analysis`, `src/specify_cli/cli/commands/agent/
   mission_record_analysis.py:228`). A server-side "do the analysis" verb is
   explicitly rejected — spec-kitty cannot perform the reasoning, exactly as
   it cannot perform WP implementation itself in `start-implementation`/
   `start-review`.

3. **Decision-resolution scope boundary.** `DecisionKind`
   (`src/runtime/next/decision.py:64-68`: `step`, `decision_required`,
   `blocked`, `terminal`, `query`) and `OriginFlow`
   (`src/specify_cli/decisions/models.py:36-41`: `charter`, `specify`,
   `plan` only — no `tasks`/`analyze` member) together mean the
   decision-resolution verbs' real scope is charter/specify/plan decision
   moments only (FR-006–FR-009, C-003, FR-012). `tasks` and `analyze` do not
   have decision moments to resolve; this is a scope boundary, not an
   oversight, and is not silently implied to cover broader ground.

4. **Contract-version bump rationale.** `envelope.py`'s inline changelog
   documents 1.2.0 ("added read-only `resolve-workspace`... Purely
   additive") and 1.3.0 (additive field on `transition`) the same way. The
   current `CONTRACT_VERSION = "1.3.0"` (`src/specify_cli/orchestrator_api/
   envelope.py:28`) is proposed to bump to **1.4.0** for this mission,
   additive only, `MIN_PROVIDER_VERSION` untouched (FR-011, NFR-001). There
   is **no reference anywhere in `orchestrator_api/` or `envelope.py` to the
   vendored — actually external, per C-001 — `spec-kitty-events` package**;
   any framing that this mission needs a coordinated `spec-kitty-events`
   release is explicitly rejected and does not apply to this contract
   surface.

5. **Lock-storm inheritance + SK-93 artifact-verification requirement.**
   `SPEC_KITTY_SYNC_MINIMAL_IMPORT=1` lock-storm exposure is real but
   **pre-existing** (ledger SK-65, SK-72, SK-93 in
   `SPEC-KITTY-LEDGER.md`) and already applies to every event-emitting
   orchestrator-api command today (`start-implementation`, `transition`,
   `append-history`, `merge-mission`). The design-phase verbs **inherit**
   this exposure; they do not introduce a new instance of the problem.
   **SK-93 is the concrete AC-shaping fact carried forward**: `record-
   analysis` was observed exiting 124 (timeout) with a "project sync store
   is locked" warning **after the work had actually succeeded** —
   `analysis-report.md` was independently re-read from disk after the
   failing-looking exit and found correctly written with `verdict: ready`.
   Exit code is not evidence in either direction on this call chain.
   Therefore (NFR-004): any orchestrator-api verb wrapping `record_analysis`
   (and, by the same principle, any other event-emitting wrap this mission
   or a later one adds) MUST verify success via the artifact/state it
   actually wrote rather than trusting a bare exit code or subprocess return
   value. This is a concrete, testable acceptance criterion (User Story 2,
   Acceptance Scenarios 2–3; NFR-004), not prose alone.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An external host can complete an entire design-phase pipeline —
  scaffold a mission (`specify`), scaffold its plan (`plan`), finalize its
  work packages (`tasks`), and record a finished analysis (`analyze-context`
  + `analyze-record`) — using only orchestrator-api verbs, with zero shelled
  host-CLI calls, verified by an end-to-end integration test that never
  invokes `spec-kitty specify`/`plan`/`tasks`/`agent mission record-analysis`
  directly.
- **SC-002**: `contract-version` reports `1.4.0` and the response documents
  the newly added verbs, consumable by a host that gates capability
  detection on the reported version, matching the existing 1.2.0/1.3.0
  changelog-comment pattern in `envelope.py`.
- **SC-003**: 100% of the 10 pre-existing orchestrator-api verbs' request and
  response contracts are unchanged — verified by the existing test suite for
  those verbs passing unmodified against the post-mission code.
- **SC-004**: 100% of the new verbs' failure paths return a structured
  `error_code` (never a bare exception, traceback, or empty/`unknown`
  success envelope) — verified by a negative-path test per new verb.
- **SC-005**: `analyze-record`'s success determination is independently
  verified by test to be artifact-derived — a test that simulates a
  non-zero/timeout exit from the underlying `record_analysis` call while the
  artifact was in fact written correctly must still observe `success: true`
  from `analyze-record` (SK-93 regression guard).
- **SC-006**: `docs/api/orchestrator-api.md` documents every new verb with
  the same level of detail (request shape, response shape, error codes) as
  the existing 10 verbs, and `host-boundary-rules.md`'s Boundary Decision
  Matrix is updated with design-phase rows so the doc no longer implies an
  external host must cross into host-CLI territory to drive design phases.

---

## Scope Notes (non-authoritative, informational only)

Expected touch points, per the pre-spec investigation (not exhaustive, not
binding beyond this scope statement — the plan phase details the actual
change set):

- `src/specify_cli/orchestrator_api/commands.py` — new commands
- `src/specify_cli/orchestrator_api/envelope.py` — `CONTRACT_VERSION` bump +
  changelog comment
- `docs/api/orchestrator-api.md` — new verb documentation
- `src/charter/offering/skills/spec-kitty-orchestrator-api-operator/
  references/host-boundary-rules.md` — Boundary Decision Matrix gains
  design-phase rows
- `tests/specify_cli/orchestrator_api/*` — new test module(s)
- `docs/changelog/CHANGELOG.md`

**Sequencing note (informational, not this spec's concern to resolve):** two
open PRs touch adjacent-but-different code in some of the same files — #3826
touches `commands.py`'s merge-mission area and `mission_create.py`; #3836
touches `mission_setup_plan.py`. Worth a plan-phase Risks-section mention;
not a blocker to this spec.

---

*Issue closure linkage: the eventual PR for this mission must carry `Closes
#3837` in its body (single-PR closure per C-004).*
