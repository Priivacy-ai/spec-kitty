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
   containing the mission slug, mission directory path, `spec.md` path, and
   the four scaffold-state fields `scaffold_only`, `spec_state`,
   `next_action`, `next_step` — matching the ENRICHED shape
   `_create_mission_for_specify_json` produces
   (`src/specify_cli/cli/commands/lifecycle.py:66-92`, itself wrapping
   `_with_specify_scaffold_state`, `lifecycle.py:51-58`), which is the actual
   host-CLI `--json` contract for `specify` — NOT the raw
   `agent_feature.create_mission(..., json_output=True)` payload alone (see
   Clarification 1: `plan`/`tasks` really are unenriched pass-throughs of
   their `agent_feature.*` calls, but `specify` is not). `kitty-specs/<slug>/
   spec.md` exists on disk with the placeholder template content.
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
prompt template (canonical source:
`packs/built-in/missions/mission-steps/software-dev/analyze/prompt.md`; NOT
the project-local `.kittify/overrides/missions/software-dev/
command-templates/analyze.md` copy, which has independently drifted from the
canonical source — see Clarification #2), not a deterministic engine
spec-kitty can run server-side. The host needs (a) a query verb that hands
back the same prerequisite/context data the host CLI's `agent mission
check-prerequisites --json --include-tasks --mission <slug>` surfaces today,
so its own calling agent can perform the analysis, and (b) a record verb that
persists that agent's finished analysis report exactly as `record_analysis`
does today — with a result the host can actually trust, unlike the raw
subprocess exit code.

**Why this priority**: `analyze` is the one part of the ask with no existing
deterministic engine to wrap; getting its scope boundary and its error-
signal contract right is the highest-risk part of this mission and blocks
Kitty Desktop's design-phase pipeline from being end-to-end orchestrator-api-
only.

**Independent Test**: Can be fully tested by calling the new
`check-prerequisites` orchestrator-api verb against a mission mid-tasks-phase
and asserting its envelope carries the same prerequisite/task data as the
host CLI's `agent mission check-prerequisites --json --include-tasks
--mission <slug>`; then calling `record-analysis` with a fabricated analysis report body and
asserting `analysis-report.md` is written with the submitted verdict,
independent of whatever the underlying event-emitting write path's own exit
behaviour does.

**Acceptance Scenarios**:

1. **Given** a mission with a finalized `tasks/` manifest, **When** the host
   calls the `check-prerequisites` orchestrator-api verb with `--mission`,
   **Then** it returns `success: true` with `data` containing the same
   prerequisite and task-listing fields the host CLI's `agent mission
   check-prerequisites --json --include-tasks --mission <slug>` (canonical
   source: `packs/built-in/missions/mission-steps/software-dev/analyze/
   prompt.md`, NOT the drifted `.kittify/overrides/...` project copy — see
   Clarification #2) already returns for that mission — this verb performs
   no analysis reasoning itself, only assembles the context an external
   agent needs to perform it.
2. **Given** the calling agent has produced an analysis report body,
   **When** the host calls the `record-analysis` orchestrator-api verb with
   `--mission`, `--input-file` (or an inline body), `--agent`, and
   `--policy`, **Then** on success the envelope's `success: true` is derived
   from re-reading `kitty-specs/<slug>/analysis-report.md` off disk and
   confirming BOTH (a) its `verdict` field matches what was submitted AND
   (b) its `generated_at` frontmatter timestamp is later than this call's
   own start time (freshness correlation — NFR-004) — NOT from trusting
   whether the underlying `record_analysis` in-process call returned
   normally, raised, or a raised exception was swallowed (see NFR-004 /
   SK-93 below).
3. **Given** the underlying write path raises an exception that is swallowed
   before reaching this verb (the SK-93 pattern: `record_analysis` observed
   exiting 124 under an operator-imposed `bash timeout 300` wrapper — not a
   Python-level exit code — while `analysis-report.md` had, in fact, already
   been written correctly with `verdict: ready`), **When** `record-analysis`
   re-reads the artifact and finds it correctly written with the submitted
   verdict AND a fresh `generated_at`, **Then** the verb reports
   `success: true` — the artifact on disk is the source of truth, not
   whether the underlying call raised, returned, or hung.
4. **Given** the underlying write path fails AND the artifact was NOT
   (re)written for this call (a genuine failure — e.g. one of
   `mission_record_analysis.py`'s early-exit branches at lines 228-292:
   dirty worktree, unresolved placement, empty body — returns/raises before
   `write_analysis_report` is ever reached), **When** `record-analysis`
   re-reads and finds no matching FRESH artifact, **Then** the verb reports
   `success: false` with a structured `error_code` distinguishing "write did
   not happen" from "write happened, signal was noise."
5. **Given** a STALE `analysis-report.md` already exists on disk from a
   PRIOR call, and its `verdict` happens to coincidentally match the CURRENT
   submission's verdict (a real risk, not a contrived one — `ready` and
   `blocked` are the only two live values), but THIS call's underlying write
   genuinely failed before reaching `write_analysis_report` (one of the
   early-exit branches above), **When** `record-analysis` re-reads the
   artifact, **Then** its `generated_at` timestamp predates this call's
   start time, and the verb reports `success: false` — verdict-string
   equality alone is NEVER sufficient evidence of this call's success.
6. **Given** `analysis-report.md` currently holds verdict `blocked` from a
   prior call whose exit signal was ambiguous, **When** `record-analysis` is
   called again with a DIFFERENT verdict `ready`, **Then** the call is
   treated as a fresh, independently-verified write attempt — the re-read
   check compares against `ready` (this call's submission) and this call's
   own start-time freshness bound, not against the stale `blocked` value —
   and reports `success`/`failure` based on whether `ready` actually landed.
7. **Given** `record_analysis`'s dossier-sync trigger
   (`trigger_feature_dossier_sync_if_enabled`, wrapped only in
   `contextlib.suppress(Exception)`, which does not bound a hang) never
   returns within `record-analysis`'s enforced time bound (NFR-004(b)),
   **When** the host calls `record-analysis`, **Then** the call still
   returns (never hangs the orchestrator-api process indefinitely), with
   `success` determined by re-reading the artifact exactly as in Scenarios
   2-3, not by whether the dossier-sync trigger ever completed.

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
   `open-decision` orchestrator-api verb with `--mission`, `--origin
   specify`, the question payload, and `--policy`, **Then** it returns
   `success: true` with `data.decision_id`, and the decision is persisted in
   the mission's decision ledger with `status: open`.
2. **Given** an open decision id, **When** the host calls `resolve-decision`
   with `--mission`, `--decision-id`, an answer payload, and `--policy`,
   **Then** it returns `success: true` with `data.status: resolved`, and the
   ledger entry's status is updated on disk.
3. **Given** an open decision id, **When** the host calls `defer-decision` or
   `cancel-decision`, **Then** the corresponding `defer_decision` /
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
The verb is named **`design-status`** (matching `mission-state`'s existing
noun-phrase query-verb style and mirroring `list-ready`'s naming pattern).

**Why this priority**: Every WP-loop-driving host needs a status view before
it acts; the design pipeline needs the same, and its absence would force a
host to infer phase state indirectly from artifact presence/absence, which is
exactly the kind of undocumented inference `host-boundary-rules.md` warns
against.

**Independent Test**: Can be fully tested by calling the new `design-status`
verb against missions in different design-phase states (fresh, mid-plan,
tasks finalized, analyze pending, open decision blocking) and asserting the
returned `current_phase` / `next_action` / `open_decisions` fields match the
mission's actual on-disk state.

**Acceptance Scenarios**:

1. **Given** a mission with only `spec.md` scaffolded, **When** the host
   calls the `design-status` verb with `--mission`, **Then** it
   returns `success: true` with `data.current_phase: "specify"` (or
   equivalent) and `data.next_action` naming the `plan` verb.
2. **Given** a mission with an open, unresolved decision moment, **When** the
   host calls `design-status`, **Then** `data.open_decisions` lists
   that decision's id and origin flow, and `data.next_action` indicates
   resolution is required before the phase can advance.
3. **Given** a mission whose `tasks/` is finalized and `analysis-report.md`
   does not yet exist, **When** the host calls `design-status`,
   **Then** `data.current_phase` indicates `analyze` is the next actionable
   phase and `data.next_action` names the `check-prerequisites` verb.
4. `design-status` performs no state transition and no event emission —
   calling it repeatedly against an unchanged mission returns byte-identical
   `current_phase`/`next_action` fields, exactly as repeated `list-ready`
   calls do today for WP state.

---

### User Story 5 - External host resolves a `spec-kitty next` control-loop decision (blocking-audit checkpoint or missing required input) at any DAG step (Priority: P1)

An external host is driving a mission through the `spec-kitty next` control
loop (e.g. an implementation or review step, or a design-phase step whose
workflow defines an audit checkpoint) and the loop returns
`kind: "decision_required"` — a blocking audit checkpoint
(`decision_id: "audit:<step_id>"`) or a missing required input
(`decision_id: "input:<key>"`) — for the CURRENT DAG step, at ANY mission
phase, not only charter/specify/plan. It wants to answer that decision and
advance the loop the same way `spec-kitty next --answer <value>
--decision-id <id> --agent <name> --result <success|failed|blocked>` already
does, via orchestrator-api instead of the host CLI.

`answer-decision` is a COMPOSITE verb, matching what the real CLI invocation
above always does in one pass (`--answer` hard-requires `--result`,
`next_cmd.py:_validate_result_and_answer`; the same call then performs, in
order, `next_cmd.py:213-221`, `next_cmd.py:244-246`, `next_cmd.py:248-250`,
`next_cmd.py:251-258`, and — conditionally — `next_cmd.py:263-269`): (1)
`runtime_bridge.answer_decision_via_runtime` persists the answer against the
`decision_id` (auto-resolved or explicit) and returns nothing usable as a
response payload; (2) the equivalent of `_pair_previous_lifecycle_record`
pairs the previous issuance's `started` lifecycle record BEFORE the DAG
advances; (3) `decide_next` (`src/runtime/next/decision.py:413`, delegating
to `runtime_bridge.decide_next_via_runtime`) advances the DAG using
`answer-decision`'s own `--result` and returns the next-step `Decision` —
the same object `_print_decision` renders as the `next --json` envelope;
(4) the equivalent of `_emit_mission_next_invoked` writes a
`MissionNextInvoked` entry into the mission's event log
(`mission-events.jsonl`); and (5), whenever the resulting
`decision.kind == "step"`, the equivalent of `_write_issuance_lifecycle_record`
writes a new issuance `started` lifecycle record. **Per operator ruling
SPEC-FRESH2-001 (see Clarification 7), steps (2), (4), and (5) are REQUIRED,
not optional or deferred** — `answer-decision` reaches them through a shared
seam extracted from `next_cmd.py` (FR-014), the same functions the host
CLI's own `--answer` handling calls, never by inlining or duplicating that
logic into the orchestrator-api layer. `answer-decision` never performs only
step (1); a decision answer with no DAG advance and no event/lifecycle
bookkeeping is not a state the real CLI can produce, so this verb does not
model it either.

**Why this priority**: This is the literal ask of GitHub issue #3837 — "a
decision-resolution verb covering the `DecisionKind` cases
(`runtime/next/decision.py`)" — and, per Clarification 3, a DISTINCT
mechanism from User Story 3's `OriginFlow`-scoped interview decisions.
Without it, an external host hits a `decision_required` envelope from
`spec-kitty next --json` (e.g. at a blocking audit checkpoint mid-DAG) with
no orchestrator-api-compliant way to unblock it, forcing exactly the
host-CLI crossing `host-boundary-rules.md` forbids. Folded into this
mission's scope per the operator's standing instruction and C-004 (no
follow-up issues; phase larger scope inside this one mission).

**Independent Test**: Can be fully tested against a fixture mission whose
workflow defines a blocking `AuditStep` (or a `PromptStep` with
`requires_inputs`), driving it to a `decision_required` state via
`spec-kitty next --json`, then calling the new `answer-decision`
orchestrator-api verb and asserting (a) the run-snapshot's
`pending_decisions` no longer contains the answered `decision_id`; (b) the
returned envelope's `data` carries the persisted-answer confirmation
(`data.answered_decision_id`) AND is byte-identical, field-for-field, to
what `spec-kitty next --answer ... --json` would have returned for the same
call on every `Decision.to_dict()`-derived key (`kind`, `step_id`,
`decision_id`, `prompt_file`, etc. — see Clarification 3, Mechanism B, for
why `answered_decision_id` itself is a self-documenting orchestrator-api
field name rather than the CLI's terser `answered` key, and is additive on
top of that shape, not a substitute for it — and for why `data` carries no
equivalent of the CLI's `answer` key); (c) the mission's event log
(`mission-events.jsonl`) gained the same `MissionNextInvoked`-equivalent
entry that call would have written; and (d) whenever the resulting
decision's `kind == "step"`, an issuance `started` lifecycle record was
written, matching what the same CLI call would have produced — (c) and (d)
reached via the shared seam FR-014 extracts, per operator ruling
SPEC-FRESH2-001 (see Clarification 7) — verified against the run-snapshot
store, the mission event log, and the lifecycle-record store on disk, not
just the envelope.

**Acceptance Scenarios**:

1. **Given** a mission run whose current DAG step is a blocking `AuditStep`
   (`spec-kitty next --json` returns `kind: "decision_required"`,
   `decision_id: "audit:<step_id>"`, `options: ["approve", "reject"]`),
   **When** the host calls the `answer-decision` orchestrator-api verb with
   `--mission`, `--agent`, `--result success`, `--answer approve`, and
   `--policy` (`--decision-id` omitted — exactly one decision is pending,
   auto-resolved exactly as `next_cmd.py:_handle_answer` auto-resolves it
   when `len(pending) == 1`), **Then** it returns `success: true` with
   `data.answered_decision_id` naming the audit decision (`decision_id`
   persisted by step (1), `answer_decision_via_runtime`), the
   run-snapshot's `pending_decisions` no longer contains that id, AND
   (per the composite design above) `data` ALSO carries the full
   `Decision.to_dict()` shape from step (3)'s `decide_next` call for
   whatever follows the resolved audit checkpoint — `answered_decision_id`
   is always a sibling field alongside that shape, never a replacement for
   it (see Acceptance Scenario 3, which exercises the same envelope from
   the `kind`/next-step side).
2. **Given** a mission run with more than one entry in
   `pending_decisions`, **When** the host calls `answer-decision` without
   `--decision-id`, **Then** the verb rejects with a structured
   `error_code` (e.g. `AMBIGUOUS_PENDING_DECISION`) listing the pending ids
   — mirroring `next_cmd.py`'s own "Multiple pending decisions... Use
   --decision-id" rejection — rather than guessing which one to answer.
3. **Given** a `PromptStep` with an unmet `requires_inputs` entry
   (`spec-kitty next --json` returns `kind: "decision_required"`,
   `decision_id: "input:<key>"`), **When** the host calls `answer-decision`
   with `--mission`, `--agent`, `--result success`, `--decision-id
   "input:<key>"`, `--answer <value>`, and `--policy`, **Then** it returns
   `success: true`, and `data` carries the SAME shape `spec-kitty next
   --answer ... --json` returns for the following step — including the
   resulting `kind` (`step`/`decision_required`/`blocked`/`terminal`), so
   the host can chain directly into its next action without a separate
   query call — PLUS the `answered_decision_id` sibling field from
   Acceptance Scenario 1 naming the `input:<key>` decision this call just
   persisted (the two are the same envelope shape viewed from opposite
   angles: AC1 asserts the persisted-answer confirmation, this scenario
   asserts the next-step parity fields; a real response carries both at
   once).
4. **Given** a `--decision-id` that does not match any entry in the current
   run's `pending_decisions` (e.g. already answered, or naming a different
   step), **When** the host calls `answer-decision`, **Then** it rejects
   with a structured `error_code` (e.g. `DECISION_NOT_PENDING`) rather than
   silently no-oping or answering the wrong decision.
5. **Given** no decision is currently pending for the mission run (the DAG
   is at a plain `step`/`blocked`/`terminal` state), **When** the host calls
   `answer-decision`, **Then** it rejects with a structured `error_code`
   (e.g. `NO_PENDING_DECISION`) — never a silent `success: true` no-op.
6. This mechanism is independent of `OriginFlow`/FR-012's scope guard:
   `answer-decision` operates on the run-snapshot's `pending_decisions`
   (Mechanism B, Clarification 3), not the `decisions/index.json` ledger
   (Mechanism A) — a mission whose current phase has no `OriginFlow` member
   (`tasks`, `analyze`) can still have a pending `decision_required` moment
   (e.g. a blocking audit checkpoint on a `tasks`- or `analyze`-phase DAG
   step) and `answer-decision` resolves it normally; FR-012's
   `INVALID_ORIGIN_FLOW` rejection does not apply to this verb.
7. **Given** the same blocking `AuditStep` scenario as Acceptance Scenario 1,
   with a PRIOR issuance's `started` lifecycle record still open (not yet
   paired), **When** the host calls `answer-decision`, **Then**, in addition
   to the run-snapshot and `Decision.to_dict()` parity already asserted in
   Acceptance Scenario 1, all three of the host CLI's own `--answer`
   lifecycle/event-log side effects occur, reached through the shared seam
   extracted from `next_cmd.py` (FR-014, per operator ruling
   SPEC-FRESH2-001 / Clarification 7) — never inlined or reimplemented
   inside the orchestrator-api layer: (a) the prior issuance's `started`
   lifecycle record is paired with a completed/failed record BEFORE the DAG
   advances (equivalent of `_pair_previous_lifecycle_record`); (b) the
   mission's event log (`mission-events.jsonl`) gains a
   `MissionNextInvoked`-equivalent entry for this call; and (c), because the
   resolved audit checkpoint advances the DAG to a `kind == "step"`
   decision, a new `started` issuance lifecycle record is written for that
   step (equivalent of `_write_issuance_lifecycle_record`). A mission driven
   entirely through `answer-decision` calls is therefore indistinguishable,
   in its event log and lifecycle-record history, from the same mission
   driven through `spec-kitty next --answer`.

---

### Edge Cases

- What happens when an external host calls a design-phase verb against a
  mission slug that does not exist? → structured `error_code` (mirroring
  `_resolve_mission_dir_or_fail`'s existing pattern for the WP-loop verbs),
  never a bare traceback or a silent empty-success envelope.
- What happens when `--policy` is omitted on a verb that mutates state
  (`specify`, `plan`, `tasks`, `record-analysis`, `open-decision`,
  `resolve-decision`, `defer-decision`, `cancel-decision`,
  `answer-decision`)? → rejected with `POLICY_METADATA_REQUIRED`, exactly as
  `start-implementation` and `start-review` already reject a missing
  `--policy` today. Read-only verbs (`check-prerequisites`, `design-status`)
  do not require `--policy`, mirroring `list-ready`'s existing no-policy
  contract.
- What happens when `record-analysis` is called twice with the SAME verdict
  (idempotent retry after an SK-93-style false-failure signal)? → the second
  call re-reads the artifact, finds it already correctly written, and returns
  `success: true` without attempting a duplicate write that could corrupt
  state — never a silent double-write and never a hard failure on "nothing
  changed." See NFR-004's freshness requirement: this is distinguished from
  the stale-artifact case below by correlating the re-read against THIS
  call, not merely against the submitted verdict value.
- What happens when `record-analysis` is called with a DIFFERENT verdict
  than what `analysis-report.md` currently holds on disk (e.g. a first call
  intended `blocked`, the exit signal was ambiguous, and the retry submits
  `ready`)? → the call is treated as a fresh, independently-verified write
  attempt — the re-read check compares against the NEW submission, not the
  stale prior value on disk — and reports `success`/`failure` based on
  whether the new value actually landed. It is never treated as a conflict
  against the previously-recorded verdict.
- What happens when `analysis-report.md` already exists on disk from a PRIOR
  call whose verdict happens to coincidentally match the CURRENT submission,
  but the current call's underlying write genuinely failed before reaching
  `write_analysis_report` (e.g. the dirty-worktree preflight, an unresolved
  placement, or an empty-body check short-circuited it)? → `record-analysis`
  reports `success: false`. Comparing the submitted `verdict` string alone
  is NOT sufficient (`ready`/`blocked` are the only two live values, so a
  coincidental match on retry is a real risk, not a contrived one) — see
  NFR-004's freshness/idempotency requirement.
- What happens when the underlying write path `record-analysis` wraps
  (`record_analysis`'s call into `write_analysis_report` followed by
  `trigger_feature_dossier_sync_if_enabled`) HANGS indefinitely rather than
  returning a bad exit code (the majority SK-93 failure shape — see NFR-004
  and Clarification 5)? → `record-analysis`'s invocation of the underlying
  write path is time-bounded at the orchestrator-api layer itself, so the
  call still returns (with `success` determined by re-reading the artifact)
  rather than hanging the orchestrator-api process forever.
- What happens when a mission already mid-flight (e.g. already in `analyze`,
  already has open WPs in the implementation loop) exists at the moment this
  contract surface ships? → nothing about its existing state or transitions
  changes; the new verbs are purely additive callers of the same underlying
  service functions the host CLI already calls for that mission. See NFR-001.
- What happens when `resolve-decision` is called with a `--decision-id` that
  is already `resolved` or `cancelled` (terminal)? → rejected with the same
  structured error the host-CLI `decision_app resolve` subcommand already
  raises for an invalid terminal-state transition, not silently accepted as a
  no-op success. (This is the `OriginFlow`-ledger mechanism, Clarification 3
  Mechanism A — distinct from `answer-decision`'s run-snapshot mechanism,
  Mechanism B, whose own not-pending/ambiguous/no-pending edge cases are
  covered in User Story 5's Acceptance Scenarios 2, 4, and 5.)

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | `specify` orchestrator-api verb | As an external host, I want to scaffold a new mission via orchestrator-api so that I never shell the host CLI to create a mission. | High | Open |
| FR-002 | `plan` orchestrator-api verb | As an external host, I want to scaffold `plan.md` via orchestrator-api so that plan creation stays inside the orchestrator-api contract. | High | Open |
| FR-003 | `tasks` (finalize) orchestrator-api verb | As an external host, I want to finalize a mission's work-package manifest via orchestrator-api so that task finalization stays inside the contract. | High | Open |
| FR-004 | `check-prerequisites` orchestrator-api verb (query) | As an external host, I want the same prerequisite/task context the host CLI's `agent mission check-prerequisites --json --include-tasks` returns, via orchestrator-api, so that my calling agent can perform cross-artifact analysis without a host-CLI call. | High | Open |
| FR-005 | `record-analysis` orchestrator-api verb | As an external host, I want to persist my agent's finished analysis report via orchestrator-api, with a trustworthy success signal, so that I know the report actually landed regardless of the underlying subprocess's exit behavior. | High | Open |
| FR-006 | `open-decision` orchestrator-api verb | As an external host, I want to open a charter/specify/plan decision moment via orchestrator-api so that decision tracking stays inside the contract. | Medium | Open |
| FR-007 | `resolve-decision` orchestrator-api verb | As an external host, I want to resolve an open decision via orchestrator-api so that I can unblock a phase without the host CLI. | Medium | Open |
| FR-008 | `defer-decision` orchestrator-api verb | As an external host, I want to defer a decision via orchestrator-api so that a decision can be revisited later without blocking the current phase. | Medium | Open |
| FR-009 | `cancel-decision` orchestrator-api verb | As an external host, I want to cancel a decision via orchestrator-api so that a no-longer-relevant decision is removed from the active ledger. | Medium | Open |
| FR-010 | `design-status` orchestrator-api verb | As an external host, I want a `list-ready`-equivalent read-only status view of the design pipeline so that I know the current phase, next action, and any blocking open decisions before I act. | High | Open |
| FR-011 | `CONTRACT_VERSION` bump to 1.4.0 | As an external host, I want a versioned contract bump that documents the new verbs so that I can detect capability via `contract-version` the same way I detect existing verbs. | High | Open |
| FR-012 | `OriginFlow`-decision origin-flow scope guard (Mechanism A only — see Clarification 3) | As an external host, I want `open-decision`/`resolve-decision`/`defer-decision`/`cancel-decision` to reject an origin outside `{charter, specify, plan}` so that I never silently misfile a decision under a flow that has no `OriginFlow` member. Does NOT apply to `answer-decision` (FR-013, Mechanism B), which has no `OriginFlow` concept. | Medium | Open |
| FR-013 | `answer-decision` orchestrator-api verb (`DecisionKind.decision_required` resolution, WITH full CLI event/lifecycle-log parity — depends on FR-014) | As an external host, I want to answer a `spec-kitty next` control-loop `decision_required` moment (a blocking audit checkpoint or a missing required input) at ANY DAG step, via orchestrator-api, so that I can unblock the mission run without shelling `spec-kitty next --answer` — and so that the call performs the SAME lifecycle-pairing, mission-event-log, and issuance-lifecycle side effects the real CLI `--answer` invocation performs (per operator ruling SPEC-FRESH2-001 / Clarification 7), not only the two engine calls, reached through the shared seam FR-014 extracts from `next_cmd.py`. | High | Open |
| FR-014 | Extract shared next-invocation lifecycle/event-log seam (prerequisite for FR-013) | As a maintainer, I want the `_pair_previous_lifecycle_record`, `_emit_mission_next_invoked` (mission event-log write), and `_write_issuance_lifecycle_record` side effects currently inlined in `next_cmd.py`'s `--answer` handling extracted into a shared module both the host CLI and orchestrator-api call, so that `answer-decision` (FR-013) can reach them without inlining CLI-layer helpers into the orchestrator-api layer or duplicating logic that would drift from the CLI's own copy. Sequenced BEFORE FR-013 in the plan/tasks phases (C-005). | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Additive-only contract change | The 10 existing `orchestrator_api/commands.py` verbs (`contract-version`, `mission-state`, `list-ready`, `resolve-workspace`, `start-implementation`, `start-review`, `transition`, `append-history`, `accept-mission`, `merge-mission`) and `MIN_PROVIDER_VERSION` ("0.1.0") are unchanged in behavior, request shape, and response shape. A mission already mid-flight in any phase (including one already in `analyze` or with open WPs in the implementation loop) observes zero change to its existing state-transition contract — the new verbs are additive callers of the same underlying service functions the host CLI already calls. | Compatibility | High | Open |
| NFR-002 | No silent success | No new verb may return `success: true` on a 0-count/no-op operation it did not actually perform, write `unknown` in place of a real field value, or swallow an underlying exception into a bare `None`/empty envelope. Every failure path returns a structured `error_code` with a human-readable `error` message, exactly matching the existing `_fail(cmd, error_code, message, ...)` pattern used throughout `commands.py`. | Reliability | High | Open |
| NFR-003 | Pre-existing test baseline | `main` carries ~23 known-red tests already tracked as issue #3284. New test module(s) added under `tests/specify_cli/orchestrator_api/` for this mission's verbs must be green on introduction; #3284's pre-existing reds are not this mission's concern to fix and no new issue is opened for them. | Testability | Medium | Open |
| NFR-004 | Artifact-verified, time-bounded success for event-emitting wraps | `record-analysis` invokes `record_analysis`'s underlying write path **in-process** (every existing orchestrator-api verb does the same — zero non-git subprocess usage in `commands.py` — so there is no subprocess exit code to distrust; a bare in-process call either returns normally or raises). `record-analysis` MUST (a) determine `success` by re-reading the artifact/state the call was supposed to produce (`analysis-report.md`, correlated with THIS call per the freshness requirement below — not merely a `verdict`-string match) rather than trusting whether the underlying call returned normally, raised, or a raised exception was swallowed; and (b) TIME-BOUND its invocation of the underlying write path at the orchestrator-api layer itself (an explicit, enforced timeout around the call, or excluding/short-circuiting `trigger_feature_dossier_sync_if_enabled` from the in-process wrap and calling `write_analysis_report`/`commit_for_mission` directly) so that an unbounded hang in the dossier-sync trigger (wrapped only in `contextlib.suppress(Exception)`, `mission_record_analysis.py:384-388`, which catches a raised exception but does NOT bound a hang) cannot block the orchestrator-api call forever. **Freshness/idempotency**: the re-read MUST correlate the artifact with THIS call specifically — e.g. record a call-start timestamp before invoking the write path and require the re-read `analysis-report.md`'s `generated_at` frontmatter field (`src/specify_cli/analysis_report.py:505-524`) to be later than it, and/or compare a hash of the submitted report body/findings against what was persisted — not merely that the terminal `verdict` string (`ready`/`blocked` are the only two live values) happens to match; a STALE `analysis-report.md` left by a prior call whose verdict coincidentally matches the current submission, while THIS call's write genuinely failed before reaching `write_analysis_report` (there are multiple early-exit failure branches — dirty worktree, unresolved placement, empty body — before the write, `mission_record_analysis.py:228-292`), MUST report `success: false`. This generalizes the SK-93 finding: `record-analysis` was observed exiting 124 (timeout, with a "project sync store is locked" warning — that exit code was an OPERATOR-imposed `bash timeout 300` wrapper around the CLI invocation, not anything the in-process Python call itself produces, per `SPEC-KITTY-LEDGER.md`'s SK-93 entry) after `analysis-report.md` had, in fact, already been written correctly with `verdict: ready`. Exit code/return value is not evidence in either direction on this call chain, and a silent hang is the majority documented SK-93 failure shape (3 of 4 first-hand occurrences), not a clean bad-exit-code return — this NFR is the standing principle any future event-emitting wrap in this mission or later ones must also follow. | Reliability | High | Open |
| NFR-005 | Envelope/policy-provenance parity | Every new mutating verb accepts and validates `--policy` using the existing `parse_and_validate_policy` / `policy_to_dict` path, and every new verb's response uses the existing `make_envelope(command=..., success=..., data=...)` shape, with `validate_outbound_payload` applied to `data` before emission — matching `start-implementation`/`start-review`/`transition` byte-for-byte in structure. | Consistency | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No `spec-kitty-events` / `spec-kitty-tracker` changes | This mission touches neither the `spec-kitty-events` nor `spec-kitty-tracker` external PyPI packages. Both are true external dependencies (declared in `pyproject.toml`, resolved via `uv sync`), not vendored in this repo, and there is no reference to `spec-kitty-events` anywhere in `orchestrator_api/` or `envelope.py` today. Any FR that would require touching either package is out of scope for this spec. | Technical | High | Open |
| C-002 | No server-side analysis reasoning | Spec-kitty MUST NOT gain a verb that performs the `analyze` cross-artifact reasoning itself. `analyze.md` is an LLM prompt template; the reasoning happens client-side in the calling agent, exactly as spec-kitty cannot perform WP implementation itself in `start-implementation`/`start-review`. `check-prerequisites` supplies context only; `record-analysis` persists a finished report only. | Technical | High | Open |
| C-003 | `open`/`resolve`/`defer`/`cancel`-decision scope bounded to `OriginFlow` members (Mechanism A only) | `open-decision`/`resolve-decision`/`defer-decision`/`cancel-decision` (FR-006–FR-009) cover exactly the `OriginFlow` cases that exist today: `charter`, `specify`, `plan`. `tasks` and `analyze` have no `OriginFlow` member and this mission does not add one. This constraint does NOT bound `answer-decision` (FR-013, Mechanism B, Clarification 3) — that verb resolves `DecisionKind.decision_required` run-loop decisions, which are not `OriginFlow`-scoped and can occur at any DAG step in any phase. | Technical | Medium | Open |
| C-004 | Single PR, no follow-up issues | This mission's default PR shape is one PR covering the full scope (specify/plan/tasks verbs, `OriginFlow`-decision verbs, `answer-decision` (FR-013), check-prerequisites/record-analysis verbs, `design-status` verb, contract-version bump, docs) — every part of the issue #3837 ask belongs in this mission's scope, not deferred to a follow-up issue. The PR body must carry `Closes #3837`. | Process | High | Open |
| C-005 | Seam extraction sequencing and behaviour preservation (FR-014 before FR-013) | Per operator ruling SPEC-FRESH2-001 (Clarification 7), FR-014's seam extraction MUST be planned and implemented before FR-013's `answer-decision` verb, which depends on it. The host CLI's existing `next_cmd.py` call sites for `_pair_previous_lifecycle_record`, `_emit_mission_next_invoked`, and `_write_issuance_lifecycle_record` become callers of the extracted seam — a behaviour-preserving refactor with zero change to the host CLI's own observable event-log or lifecycle-record output — covered by a shared regression test that fails if EITHER caller (the host CLI's `next --answer` or orchestrator-api's `answer-decision`) stops writing the mission-event-log entry or the lifecycle records (SC-008). | Process | High | Open |

### Key Entities

- **Design-phase envelope**: the same canonical JSON response envelope (`make_envelope`) already used by the 10 existing orchestrator-api verbs — `command`, `success`, `data`, and on failure `error_code`/`error`. No new envelope shape is introduced; new verbs reuse it.
- **Decision moment (Mechanism A, `OriginFlow`-scoped)**: an entry in a mission's decision ledger (`decisions/index.json`), keyed by `decision_id`, carrying `origin` (one of `OriginFlow.CHARTER`/`SPECIFY`/`PLAN`), `status` (open/resolved/deferred/cancelled), and the question/answer payload — unchanged in shape by this mission, only newly reachable via `open-decision`/`resolve-decision`/`defer-decision`/`cancel-decision`.
- **Run decision (Mechanism B, `DecisionKind.decision_required`)**: an entry in a mission RUN's `pending_decisions` map (a run-snapshot store read via `_internal_runtime.engine._read_snapshot`, distinct from `decisions/index.json`), keyed by `decision_id` in the form `audit:<step_id>` (blocking audit checkpoint) or `input:<key>` (missing required input), carrying `question` and `options`. Not `OriginFlow`-scoped — can occur at any DAG step in any mission phase. Resolved by `answer-decision` (FR-013) the same way `spec-kitty next --answer --result <...>` resolves it today — which is itself a COMPOSITE of two engine calls PLUS three lifecycle/event-log side effects, not the two engine calls alone (per operator ruling SPEC-FRESH2-001; see Clarification 7): (1) `runtime_bridge.answer_decision_via_runtime` persists the answer (returns nothing usable as a response payload); (2) the equivalent of `_pair_previous_lifecycle_record` pairs the previous issuance's `started` lifecycle record BEFORE the DAG advances; (3) `decide_next` (`src/runtime/next/decision.py:413`, delegating to `runtime_bridge.decide_next_via_runtime`) advances the DAG using the verb's own `--result` and returns the next-step `Decision`; (4) the equivalent of `_emit_mission_next_invoked` writes a `MissionNextInvoked` entry into the mission's event log; and (5), whenever the resulting `decision.kind == "step"`, the equivalent of `_write_issuance_lifecycle_record` writes a new issuance `started` lifecycle record. Steps (2), (4), and (5) are reached through a shared seam extracted from `next_cmd.py` (FR-014) that both the host CLI and orchestrator-api call — never inlined or duplicated into the orchestrator-api layer. `answer-decision`'s response `data` is `Decision.to_dict()` from call (3) — carrying `kind`/`step_id`/`decision_id`/`prompt_file`/etc. for whatever comes next — with one additional sibling field, `answered_decision_id`, set to the `decision_id` persisted in call (1) (see User Story 5 AC1/AC3 for the response-shape contract). `data` carries NO equivalent of the CLI's second extra key, `answer` (the submitted answer text, echoed back by `_print_decision`'s `d["answer"] = answer` at `next_cmd.py:915`): that echo is intentionally OMITTED because the host already possesses the value it submitted in its own request — unlike `answered_decision_id`, which can name an auto-resolved `decision_id` the host did not already know when `--decision-id` was omitted (see Clarification 3, Mechanism B).
- **Analysis report artifact**: `kitty-specs/<slug>/analysis-report.md`, written by `record_analysis` today and by `record-analysis` under this mission — the ground truth `record-analysis` must re-read (and correlate with THIS call via `generated_at` freshness — NFR-004) to determine its own success.
- **Design-phase status snapshot**: the read-only aggregate (`current_phase`, `next_action`, `open_decisions`) returned by the new `design-status` verb, reduced from the mission's event log and decision ledger the same way `list-ready` reduces WP state — never persisted, never mutating.

## Clarifications / Decision Records

Persisted verbatim from the pre-spec readiness investigation so a later
reviewer (or `sk-review`) can audit these without re-deriving them:

1. **Surface-only confirmation — with one payload-shape correction.**
   `specify`/`plan`/`tasks` on the host CLI
   (`src/specify_cli/cli/commands/lifecycle.py:129,212,266`) are already thin
   shims delegating to `agent_feature.create_mission`
   (`mission_create.py:631`), `agent_feature.setup_plan`
   (`mission_setup_plan.py:1097`), `agent_feature.finalize_tasks`
   (`mission_finalize.py:3075`) — all three already accept `json_output:
   bool` and skip the interactive interview path when `json_output=True`
   (`lifecycle.py:178-193,238-262`). **Correction:** `plan` and `tasks`
   really are unenriched pass-throughs — `lifecycle.py:219,273` call
   `agent_feature.setup_plan(..., json_output=json_output)` /
   `agent_feature.finalize_tasks(..., json_output=json_output)` directly and
   return their raw JSON payload. `specify` is NOT: when `json_output=True`,
   `lifecycle.py:161-162` routes through `_create_mission_for_specify_json`
   (`lifecycle.py:66-92`), which captures `agent_feature.create_mission`'s
   stdout and re-emits it through `_with_specify_scaffold_state`
   (`lifecycle.py:51-58`) — adding `scaffold_only`, `spec_state`,
   `next_action`, `next_step` before the host CLI's `--json` caller ever
   sees it. FR-001's new `specify` verb targets this ENRICHED shape (calling
   `_create_mission_for_specify_json` or an equivalent enrichment step
   in-process), not the raw `create_mission` payload — matching the real
   host-CLI `--json` contract rather than an internal implementation detail
   one layer beneath it. Decision resolution is the strongest precedent:
   `src/specify_cli/decisions/service.py` exposes `open_decision` (:260),
   `resolve_decision` (:528), `defer_decision` (:575), `cancel_decision`
   (:612) as pure functions, already wrapped 1:1 by
   `src/specify_cli/cli/commands/decision.py`'s `decision_app`. This mission
   is surface work over an existing engine, not new engine work.

2. **`analyze` precedent choice — re-anchored on the canonical source.**
   `analyze` is the one genuine exception — it has no deterministic engine to
   wrap; the cross-artifact reasoning happens client-side in the calling
   agent via a prompt template. **Canonical source correction:** the
   authoritative template is
   `packs/built-in/missions/mission-steps/software-dev/analyze/prompt.md`
   (per AGENTS.md's "Edit SOURCE files, NOT agent copies" rule and
   DIRECTIVE_044), which runs `spec-kitty agent mission check-prerequisites
   --json --include-tasks --mission <mission-slug>` (registered as the
   `agent mission` Typer group, `src/specify_cli/cli/commands/agent/
   __init__.py:23`; confirmed by the command's own docstring examples,
   `mission_check_prerequisites.py:519-521`) — **not** the project-local
   `.kittify/overrides/missions/software-dev/command-templates/analyze.md`
   copy, which has independently drifted from the canonical source
   (`agent mission-run check-prerequisites` — there is no `mission-run`
   command group anywhere in the CLI — plus stale
   `constitution`/`/memory/constitution.md` terminology and stale
   `mission_dir`/field names where the canonical source says `charter`/
   `/charter/charter.md` and `feature_dir`/`target_branch`/`base_branch`).
   This spec cites the canonical source throughout; the `.kittify/overrides`
   drift is a pre-existing defect this investigation surfaced, is out of
   this mission's scope to fix, and is flagged here (rather than silently
   treated as authoritative) so a later reviewer can ledger it separately.
   **Resolution (adopted, FR-004 / FR-005 / C-002): mirror `start-review`'s
   pattern** — a context/query verb (`check-prerequisites`, mirroring
   `agent mission check-prerequisites --json --include-tasks --mission
   <slug>`) plus a record verb (`record-analysis`, wrapping
   `record_analysis`, `src/specify_cli/cli/commands/agent/
   mission_record_analysis.py:228`). A server-side "do the analysis" verb is
   explicitly rejected — spec-kitty cannot perform the reasoning, exactly as
   it cannot perform WP implementation itself in `start-implementation`/
   `start-review`.

3. **Decision resolution is TWO distinct mechanisms — this spec now covers
   BOTH.** An earlier draft of this Clarification treated `DecisionKind`
   member names as if they were a superset check against `OriginFlow`
   members and concluded the gap was "a scope boundary, not an oversight."
   That was wrong: `DecisionKind` values (`step`/`decision_required`/
   `blocked`/`terminal`/`query`, `src/runtime/next/decision.py:63-67`) are
   envelope *kinds* emitted by the `spec-kitty next` control loop, not
   origin flows, and they are **not** bounded to charter/specify/plan.
   Correcting the record:

   - **Mechanism A — `OriginFlow`-scoped interview decisions** (unchanged
     from the original draft, covered by FR-006–FR-009 / C-003 / FR-012):
     `src/specify_cli/decisions/service.py` exposes `open_decision` (:260),
     `resolve_decision` (:528), `defer_decision` (:575), `cancel_decision`
     (:612), persisting into a mission's `decisions/index.json` ledger,
     keyed by `origin` — one of `OriginFlow.CHARTER`/`SPECIFY`/`PLAN`
     (`src/specify_cli/decisions/models.py:36-41`; no `tasks`/`analyze`
     member). These are widen-enabled *interview questions* raised by the
     `specify`/`plan` command flows. Real, useful, narrow — but not what
     GitHub issue #3837 is asking for by name.
   - **Mechanism B — `DecisionKind.decision_required` run-loop decisions**
     (NEW, added to this spec's scope by FR-013 / User Story 5 below): the
     `spec-kitty next` control loop's DAG-based planner
     (`src/runtime/next/_internal_runtime/planner.py:420-434` — a blocking
     audit checkpoint, `decision_id="audit:<step_id>"` — and `:458-476` — a
     missing required input, `decision_id="input:<key>"`; a third site,
     `:381-399`, re-emits an already-pending decision read off
     `snapshot.pending_decisions` before DAG traversal even runs) emits a
     `kind="decision_required"` `NextDecision` for **any** DAG step, in
     **any** mission phase — not limited to charter/specify/plan. It is
     resolved today only via `spec-kitty next --answer <value> --decision-id
     <id> --agent <name> --result <success|failed|blocked>`
     (`src/specify_cli/cli/commands/next_cmd.py:923-1018`, `_handle_answer`
     — auto-resolves `--decision-id` when exactly one decision is pending by
     reading `_internal_runtime.engine._read_snapshot(run_ref.run_dir)
     .pending_decisions`, then calls `runtime_bridge.answer_decision_via_
     runtime(...)`, `src/runtime/next/runtime_bridge.py:2587-2662`), which
     writes into a **run-snapshot store** — a completely separate
     persistence layer from `decisions/index.json`. **`_handle_answer` is
     only PART of what the real `--answer` invocation does.** `--answer`
     hard-requires `--result` (`_validate_result_and_answer`,
     `next_cmd.py:743-750`), and the SAME CLI call (`next_cmd.py:213-221`
     then `next_cmd.py:248-250`) ALWAYS follows the persisted answer with a
     second, separate call, `decide_next` (`src/runtime/next/decision.py:413`,
     delegating to `runtime_bridge.decide_next_via_runtime`,
     `runtime_bridge.py:2191`), which advances the DAG using `--result` and
     returns the next-step `Decision`. In the SAME pass, the SAME CLI call
     also pairs the previous issuance's lifecycle record BEFORE `decide_next`
     (`_pair_previous_lifecycle_record`, `next_cmd.py:244-246`) and, after
     `decide_next`, writes the mission event log entry
     (`_emit_mission_next_invoked`, `next_cmd.py:251-258`) and, whenever the
     resulting decision's `kind == "step"`, a new issuance `started`
     lifecycle record (`_write_issuance_lifecycle_record`,
     `next_cmd.py:263-269`). `_print_decision`
     (`next_cmd.py:910-919`) then prints `decision.to_dict()` with two extra
     keys, `answered` and `answer`, merged in flatly. **`answer-decision`
     (FR-013) wraps ALL of this** — both engine calls AND the three
     lifecycle/event-log side effects, reached through the shared seam
     FR-014 extracts from `next_cmd.py` (per operator ruling
     SPEC-FRESH2-001; full rationale in Clarification 7) — matching the real
     CLI's always-does-all-of-it behavior (see User Story 5), and returns
     `Decision.to_dict()` from the `decide_next` call with one added field,
     `answered_decision_id` — `answer-decision`'s own self-documenting name
     for the same bookkeeping the CLI's terser `answered` key carries,
     following the existing orchestrator-api convention of curated,
     self-documenting `data` field names rather than a verbatim re-export of
     an internal function's dict (e.g. `start-implementation`/
     `start-review`'s `wp_id`/`from_lane`/`to_lane`,
     `commands.py:1353-1355,1447-1449`). `answer-decision`'s `data` carries
     NO equivalent of the CLI's second extra key, `answer` (the submitted
     answer text) — that echo is intentionally omitted because the host
     already possesses the value it submitted; see the Key Entities "Run
     decision" bullet for the full response-shape contract. The "SAME
     shape" parity User Story 5 AC3 / the Independent Test / SC-007 require
     is scoped to the `Decision.to_dict()`-derived next-step fields (`kind`,
     `step_id`, `decision_id`, `prompt_file`, etc.), which ARE byte-identical
     to what `next --answer --json` emits for those keys — not to the
     bookkeeping key's literal name — and now additionally requires the
     event-log and lifecycle-record parity described above (SC-007(c)).

   GitHub issue #3837 literally asks for "a decision-resolution verb
   covering the `DecisionKind` cases (`runtime/next/decision.py`)" — that is
   Mechanism B, and an earlier draft of this spec shipped only Mechanism A
   while asserting the gap was deliberate. Per the operator's standing
   instruction (deferring scope to a follow-up issue is not available; if
   scope is larger than it looks, phase it inside this one mission — C-004),
   this spec's scope is EXTENDED to cover Mechanism B via the new
   `answer-decision` verb (FR-013, User Story 5). Both mechanisms are real,
   distinct, and now covered: FR-006–FR-009/C-003/FR-012 for Mechanism A,
   FR-013 for Mechanism B. Neither replaces the other.

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

5. **Lock-storm exposure is real but NOT currently carried by any existing
   orchestrator-api verb — corrected from an earlier blanket claim; SK-93
   artifact-verification requirement.** `SPEC_KITTY_SYNC_MINIMAL_IMPORT=1`
   lock-storm exposure (ledger SK-65, SK-72, SK-93 in
   `SPEC-KITTY-LEDGER.md`) is real, but an earlier draft of this
   Clarification asserted it "already applies to every event-emitting
   orchestrator-api command today" naming `start-implementation`,
   `transition`, `append-history`, `merge-mission` — that claim does not
   hold against the code as it stands. Verified (grep `sync_dossier`/
   `ensure_sync_daemon` call sites in `commands.py` and their downstream
   engines):
   - `start-implementation` (`commands.py:1332-1333`) and `start-review`
     (`commands.py:1426-1427`) and `transition` (`commands.py:1609-1610`) all explicitly
     pass `ensure_sync_daemon=False, sync_dossier=False` to
     `start_implementation_status`/`start_review_status`/
     `emit_status_transition_transactional` — `status/emit.py`'s
     `if sync_dossier and repo_root is not None: fire_dossier_sync(...)`
     gate (the exact SK-93 dossier body-upload path) is skipped entirely.
   - `append-history` calls `emit_inner_state_changed`
     (`status/emit.py:981`), which has NO `sync_dossier` parameter at all
     and never calls `fire_dossier_sync` in its body — there is no
     dossier-sync call path to opt out of.
   - `merge-mission`'s WP-done/approved bookkeeping
     (`merge/done_bookkeeping.py:285,440`) also explicitly passes
     `ensure_sync_daemon=False, sync_dossier=False` to
     `emit_status_transition_transactional`.
   **None of the 10 existing orchestrator-api verbs is demonstrated to carry
   the SK-93 dossier-sync exposure today** — each either opts out via
   `sync_dossier=False` or calls an engine with no dossier-sync path at all.
   The exposure is real but LATENT: it would apply to any future verb (in
   this mission or later) that wraps a call defaulting `sync_dossier=True`
   or omitting an opt-out. That is exactly `record_analysis`
   (`mission_record_analysis.py:384-388`): its dossier-sync trigger
   (`trigger_feature_dossier_sync_if_enabled`) has NO `sync_dossier`-style
   opt-out parameter today, wrapped only in `contextlib.suppress(Exception)`
   — which suppresses a raised exception but does not bound a hang.
   `record-analysis` is therefore the one new verb in this mission that
   genuinely inherits the exposure, not by generic pattern-matching against
   the 10 existing verbs' behavior, but because its underlying function
   lacks the opt-out the other 9 engines already have. A planning-phase
   consideration worth recording: `record_analysis` could gain the same
   `sync_dossier=False`-style opt-out as an alternative or complement to
   NFR-004's artifact-reread + time-bound requirements.
   **SK-93 is the concrete AC-shaping fact carried forward**: `record-
   analysis` was observed exiting 124 under an OPERATOR-imposed `bash
   timeout 300` wrapper around the CLI invocation (not a Python-level exit
   code the in-process call itself produces) with a "project sync store is
   locked" warning **after the work had actually succeeded** —
   `analysis-report.md` was independently re-read from disk after the
   failing-looking exit and found correctly written with `verdict: ready`.
   Exit code is not evidence in either direction on this call chain, and a
   silent hang (not a clean bad-exit-code return) was the majority
   documented SK-93 failure shape. Therefore (NFR-004): `record-analysis`
   MUST verify success via the artifact/state it actually wrote (correlated
   with THIS call via freshness, not a bare `verdict` match) rather than
   trusting whether the underlying call returned, raised, or hung, AND MUST
   time-bound its invocation of the underlying write path so a hang cannot
   block the orchestrator-api process forever — the same principle any
   future event-emitting wrap in this mission or later ones must also
   follow. This is a concrete, testable acceptance criterion (User Story 2,
   Acceptance Scenarios 2–3 and 5–7; NFR-004), not prose alone.

6. **FR-010 (`design-status`) candidate-authority citation.** Unlike every
   other FR in this mission, an earlier draft of FR-010 cited no underlying
   engine. Two existing engines are candidate reuse targets and were
   evaluated: (a) `src/runtime/next/_internal_runtime/planner.py`'s
   `resolve_next_workflow_action` — a lightweight, side-effect-free
   `(mission_dir, current_action) -> next_action` lookup over the workflow
   action graph (`meta.json::workflow_id`), exercised today via
   `runtime_bridge_engine.resolve_workflow_for_mission`; and (b) the fuller
   DAG-based `decide_next`/`_resolve_next_unified_step` engine (same
   package) that backs `spec-kitty next --json` query mode
   (`runtime_bridge.query_current_state`) and is `decision_required`-aware.
   **Decision (deliberate, not an oversight): `design-status` does NOT
   delegate to either.** Both existing engines return a WP-loop/run-state
   shaped payload (`action`, `wp_id`, `prompt_file`) rather than FR-010's
   four design-phase fields (`current_phase`, `next_action` naming a VERB,
   `open_decisions`); and `decide_next`'s query path materializes/reads a
   runtime run (`get_or_start_run`) as a side effect this mission does not
   want a read-only status verb depending on. `design-status` instead
   defines a narrower, design-phase-only reduction over on-disk artifact
   presence (`spec.md`/`plan.md`/`tasks/` finalization/`analysis-report.md`)
   and the `decisions/index.json` ledger — the same shape of deliberate
   narrowing `list-ready` already applies (reducing WP state without
   invoking the full FSM transition validators). This citation and
   rationale is recorded here so a plan-phase author does not have to
   re-derive it, and so a hand-rolled reduction is a documented choice, not
   an unexamined drift risk (DIRECTIVE_044).

7. **Operator ruling — `answer-decision` requires event/lifecycle-log
   parity, reached via an extracted shared seam (SPEC-FRESH2-001).** A
   fresh-sweep review round found that FR-013's two-engine-call composite
   design (User Story 5, Clarification 3 Mechanism B) omitted three side
   effects the real `spec-kitty next --answer ...` invocation always
   performs in the same pass: `_pair_previous_lifecycle_record` (before
   `decide_next`), and, after `decide_next`, `_emit_mission_next_invoked`
   (writes a `MissionNextInvoked` entry into the mission's event log) and
   `_write_issuance_lifecycle_record` (writes a `started` lifecycle record
   whenever the resulting decision is `kind == "step"`). None of the three
   live inside the engine layer (`runtime_bridge.py`, `decision.py`) the
   original design wrapped — they are CLI-command-layer orchestration in
   `next_cmd.py`. A WP built strictly from the original FR/Scope-Notes
   surface would have produced an `answer-decision` verb whose JSON
   response looked byte-identical to the CLI's while silently failing to
   advance the mission's event log or lifecycle store — an observable
   divergence between a mission driven via the host CLI and one driven via
   orchestrator-api.

   **The operator ruled: require the three side effects, reached through a
   seam extracted from `next_cmd.py` that BOTH the host CLI and
   orchestrator-api call — not by inlining or duplicating the calls into
   the orchestrator-api layer** (FR-014). Rationale, recorded here so a
   plan-phase author does not have to re-derive it:

   - *The issue's own premise.* #3837 exists because external hosts driving
     design phases today must shell the host CLI, which the boundary rules
     forbid. A verb that returns the right-looking JSON while failing to
     advance the event and lifecycle logs does not remove that need — it
     replaces a documented boundary violation with a silent behavioural
     divergence, which is worse because nothing surfaces it.
   - *Self-consistency within this mission.* This mission also specifies a
     `design-status` query verb (FR-010) that READS the mission event log.
     An `answer-decision` that does not write to that log makes the mission
     internally incoherent: its own status verb would under-report progress
     driven through its own answer verb.
   - *Silent success is this repository's named dominant failure mode*
     (charter; spec-kitty overlay §1a; issues #3133, #3212, #3282, #3336).
     A code path that reports success while omitting part of its work is
     that class exactly.
   - *Why extract rather than inline.* Inlining would put orchestrator-api
     code in reach of CLI-layer helpers — an architecture violation caught
     at implementation time — and would duplicate logic that then drifts
     from the CLI's own copy. Extraction costs a refactor work package
     (FR-014); the operator accepted that cost explicitly.

   **Scope consequence:** this enlarges the mission. FR-014 (seam
   extraction) is a new functional requirement, sequenced BEFORE FR-013 in
   the plan and tasks phases (C-005) — the plan/tasks phases must carry a
   dedicated work package for it. The host CLI's own `next_cmd.py` call
   sites become callers of the extracted seam: a behaviour-preserving
   refactor (C-005), covered by a shared test that fails if either caller
   (the host CLI or orchestrator-api) stops writing the event-log entry or
   the lifecycle records (SC-008). See User Story 5's updated
   composite-design description, the Key Entities "Run decision" bullet,
   Acceptance Scenario 7, and SC-007(c)/SC-008 for where this requirement
   is pinned down as testable acceptance coverage.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An external host can complete an entire design-phase pipeline —
  scaffold a mission (`specify`), scaffold its plan (`plan`), finalize its
  work packages (`tasks`), and record a finished analysis (`check-prerequisites`
  + `record-analysis`) — using only orchestrator-api verbs, with zero shelled
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
- **SC-005**: `record-analysis`'s success determination is independently
  verified by test to be artifact-derived and time-bounded — (a) a test that
  simulates a swallowed/raised exception from the underlying write path
  while the artifact was in fact written correctly (with a fresh
  `generated_at`) must still observe `success: true` from `record-analysis`
  (SK-93 regression guard); (b) a test that simulates the underlying write
  path HANGING (never returning) must observe `record-analysis` still
  returning within its enforced time bound, rather than hanging the caller
  indefinitely — the majority documented SK-93 failure shape, not only the
  bad-exit-code shape; and (c) a test with a STALE `analysis-report.md` on
  disk whose verdict coincidentally matches the new submission but whose
  `generated_at` predates this call must observe `success: false`
  (SPEC-VERIFY-001 regression guard).
- **SC-006**: `docs/api/orchestrator-api.md` documents every new verb —
  `specify`, `plan`, `tasks`, `check-prerequisites`, `record-analysis`,
  `open-decision`, `resolve-decision`, `defer-decision`, `cancel-decision`,
  `design-status`, and `answer-decision` (FR-013) — by that literal name,
  with the same level of detail (request shape, response shape, error codes)
  as the existing 10 verbs, and `host-boundary-rules.md`'s Boundary Decision
  Matrix is updated with design-phase rows so the doc no longer implies an
  external host must cross into host-CLI territory to drive design phases.
- **SC-007**: An external host can resolve a `spec-kitty next` control-loop
  `decision_required` moment — a blocking-audit checkpoint OR a missing
  required input — for a DAG step in ANY mission phase via `answer-decision`,
  verified by an integration test that drives a fixture mission run to a
  `decision_required` state, calls `answer-decision`, and confirms (a) the
  run-snapshot's `pending_decisions` no longer contains the answered
  `decision_id`; (b) the resulting envelope carries both the
  persisted-answer confirmation (`data.answered_decision_id`) and, on every
  `Decision.to_dict()`-derived key (`kind`, `step_id`, `decision_id`,
  `prompt_file`, etc.), matches what `spec-kitty next --answer ... --json`
  returns for the identical call; and (c) the mission's event log and
  lifecycle-record store show the SAME `MissionNextInvoked`-equivalent
  entry and issuance/pairing lifecycle records that call would have
  produced (per operator ruling SPEC-FRESH2-001 / Clarification 7 / FR-014)
  — proving `answer-decision` performed BOTH engine calls the real CLI
  performs (`answer_decision_via_runtime` then
  `decide_next`/`decide_next_via_runtime`) AND the three lifecycle/event-log
  side effects (`_pair_previous_lifecycle_record`,
  `_emit_mission_next_invoked`, `_write_issuance_lifecycle_record`
  equivalents), not only the persist-and-advance steps — never invoking
  `spec-kitty next` directly.
- **SC-008**: A shared regression test (per FR-014 / C-005) fails if EITHER
  caller of the extracted lifecycle/event-log seam — the host CLI's
  `spec-kitty next --answer ...` or orchestrator-api's `answer-decision` —
  stops writing the mission's `MissionNextInvoked` event-log entry, the
  paired-previous-issuance lifecycle record, or the new issuance `started`
  lifecycle record; proving the seam extraction (FR-014) is
  behaviour-preserving for the host CLI and load-bearing, not incidental,
  for `answer-decision` (FR-013).

---

## Scope Notes (non-authoritative, informational only)

Expected touch points, per the pre-spec investigation (not exhaustive, not
binding beyond this scope statement — the plan phase details the actual
change set):

- `src/specify_cli/orchestrator_api/commands.py` — new commands
- `src/specify_cli/orchestrator_api/envelope.py` — `CONTRACT_VERSION` bump +
  changelog comment
- `src/runtime/next/runtime_bridge.py` (`answer_decision_via_runtime`,
  `decide_next_via_runtime`, `get_or_start_run`, `_read_snapshot`) and
  `src/runtime/next/decision.py` (`decide_next`) — the two ENGINE calls
  `answer-decision` (FR-013) wraps: `answer_decision_via_runtime` persists
  the answer, then `decide_next`/`decide_next_via_runtime` (passing the
  verb's own `--result`) advances the DAG and produces the next-step
  `Decision` that becomes `data`; likely read/advance reuse, no engine
  changes expected, but the plan phase should confirm no new public surface
  is needed there
- `src/specify_cli/cli/commands/next_cmd.py` (`_pair_previous_lifecycle_record`
  at `next_cmd.py:333`, `_emit_mission_next_invoked` at `next_cmd.py:863`,
  `_write_issuance_lifecycle_record` at `next_cmd.py:430`) — the THREE
  lifecycle/event-log side effects FR-014 extracts into a shared seam so
  `answer-decision` (FR-013) can call them too, per operator ruling
  SPEC-FRESH2-001 (Clarification 7); the plan phase determines the exact
  target module for the extracted seam — a location both `next_cmd.py` and
  `src/specify_cli/orchestrator_api/commands.py` can import without
  orchestrator-api reaching into CLI-command-layer code (this repo's
  `CLAUDE.md` already treats `src/runtime/next/` as the canonical runtime
  home under the Shared Package Boundary) — and updates `next_cmd.py`'s own
  call sites to call through it (behaviour-preserving, C-005)
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
