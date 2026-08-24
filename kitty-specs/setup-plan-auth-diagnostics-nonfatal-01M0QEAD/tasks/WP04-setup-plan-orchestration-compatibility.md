---
work_package_id: WP04
title: setup-plan orchestration and compatibility
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-001
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
planning_base_branch: fix/setup-plan-auth-diagnostics-nonfatal
merge_target_branch: fix/setup-plan-auth-diagnostics-nonfatal
branch_strategy: Planning artifacts for this mission were generated on fix/setup-plan-auth-diagnostics-nonfatal. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/setup-plan-auth-diagnostics-nonfatal unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
- T019
phase: Phase 3 - setup-plan integration
history:
- at: '2026-08-24T00:00:00Z'
  actor: system
  action: Rewritten for frozen-local-outcome sequencing and isolated hosted-effects module
- at: '2026-08-23T18:07:49Z'
  actor: system
  action: Prompt replaced with two-lane orchestration and compatibility contract
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- tests/architectural/test_setup_plan_hosted_effect_gate.py
- src/specify_cli/cli/commands/agent/setup_plan_hosted_effects.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/mission_setup_plan.py
- src/specify_cli/cli/commands/agent/setup_plan_hosted_effects.py
- tests/fixtures/setup_plan_pre_mission_replay.py
- tests/runtime/test_setup_plan_sync_evidence.py
- tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py
- tests/specify_cli/cli/commands/agent/test_setup_plan_read_surface.py
- tests/specify_cli/cli/commands/agent/test_issue_3425_setup_plan_legacy_layout_silent_capture.py
- tests/architectural/test_setup_plan_hosted_effect_gate.py
- docs/operations/logged-out-teamspace.md
role: implementer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/3621
- https://github.com/Priivacy-ai/spec-kitty/issues/3127
---

# Work Package Prompt: WP04 – setup-plan orchestration and compatibility

## Do This First: Load Agent Profile

Load `implementer-ivan`, the charter, and all Mission design artifacts. Confirm WP01,
WP02, and WP03 are approved or done. Start with a failing acceptance-test commit that is
red on WP04's dependency-resolved lane base before editing `mission_setup_plan.py`.

## Objectives & Success Criteria

Refactor the real setup-plan entry point into a strictly ordered pipeline. Every eligible
local path produces and freezes the authoritative payload and exit first. Only then may
the command acquire hosted evidence and issue a decision. Hosted diagnostics are
additive. Every physical hosted sink lives in one dedicated executor module and executes
only for the exact canonical allowing decision, while local lifecycle persistence and
other local work remain independent.

Completion requires:

- no auth or structural early exit prevents eligible local verification;
- no hosted assessment runs before the complete local payload and exit are frozen;
- every baseline local outcome retains all primary fields and its exit;
- JSON mode emits one object; human mode has equivalent warning severity;
- real refresh-capable encrypted storage without scope produces no auth warning;
- real unreadable storage produces an auth-assessment-failure diagnostic, not logged out;
- returned and raised structural failures refuse hosted effects and preserve local work;
- local lifecycle JSONL is written while lifecycle fan-out/dossier/queue/upload/
  daemon/dashboard/direct hosted sinks remain zero under refusal;
- an architectural import/name and dominance gate with synthetic mutations prevents
  direct, aliased, containerized, partial, dynamic-import, and reflective bypasses;
- `agent mission create` and setup-plan policy are named consistently in the logged-out
  Teamspace operations document;
- issue #3127 receives a terminal acceptance verdict and remains a release-readiness
  gate when unresolved, not a code or Mission-completion dependency.

## Context & Constraints

Read every artifact in
`kitty-specs/setup-plan-auth-diagnostics-nonfatal-01M0QEAD/`, especially the binding
local outcome matrix and hosted-effect contract. Read accepted auth, transport,
single-authority-gate, and project-sync-store ADRs named by the plan. Treat
`traces/design-decisions.md` as the active supersession index for append-only historical
Decision Moments.

WP01 supplies typed session-evaluation evidence. WP02 reads it directly from
`TokenManager` and supplies the no-raise decision. WP03 supplies local-only lifecycle
persistence and explicit fan-out. WP04 adds `setup_plan_hosted_effects.py` as the sole
physical owner of fan-out/dossier sink imports. Consume those APIs; do not recreate their
logic or import their sinks inside `mission_setup_plan.py`.

Do not change `run_preflight`, TokenManager, lifecycle internals, sync-store layout,
hosted-only commands, or add a strict-sync option. Do not catch local workflow failures
merely because assessment failures are nonfatal.

## Branch Strategy

- **Planning base branch**: `fix/setup-plan-auth-diagnostics-nonfatal`
- **Merge target branch**: `fix/setup-plan-auth-diagnostics-nonfatal`
- **Implementation command**: `spec-kitty agent action implement WP04 --agent <name>`
- Run only in the dependency-resolved lane workspace from `lanes.json`.
- Modify only the declared files. `test_setup_plan_read_surface.py` is explicitly owned
  so helper signature or harness changes are reviewable rather than conditional.

## Binding Compatibility Matrix

Before production edits, capture exact current payloads and exits:

| Local condition | Required classification | Exit |
|---|---|---:|
| substantive complete | success, `phase_complete=true` | 0 |
| new pristine scaffold | success, incomplete, `scaffold_only=true` | 0 |
| populated insufficient | blocked with current reason | 0 |
| committed pristine/insufficient | blocked with current reason | 0 |
| non-substantive/uncommitted spec | blocked, `SPEC_NOT_SUBSTANTIVE_OR_UNCOMMITTED` | 0 |
| missing spec | current `SPEC_FILE_MISSING` payload | 1 |
| template configuration error | error, `TEMPLATE_CONFIGURATION_ERROR` | 1 |
| missing template/generic local exception | current error payload | 1 |
| project/context/git resolution | current payload | current exit |

Tests compare the complete baseline payload from the real pre-existing entry point after
removing only the additive `warnings` field. The full applicable readiness cross-product
may add `warnings`; it may not alter any other field or exit.

## Subtasks & Detailed Guidance

### Subtask T013 – Capture baseline and commit rejecting matrix

**Purpose**: Make compatibility objective before rearranging control flow.

1. Inventory every return, emitter, and `typer.Exit` in `setup_plan()` and helpers.
2. Add/extend fixtures for every matrix row in the owned tests.
3. Capture exact `result`, `phase_complete`, `scaffold_only`, `blocked_reason`,
   `error_code`, branch/commit fields, and process exit where present.
4. Cross every matrix row with usable session, logged out, auth-assessment failure,
   boundary unsafe, boundary exception, and route unavailable wherever repository
   context exists.
5. Assert exactly one JSON object.
6. Commit tests red against the old auth/preflight exit-2 behavior before production
   changes.

For pre-root project/context failures, inject fatal boundary and route spies and prove
they are not called; no structural or routing warning may be fabricated. Auth diagnostics
may attach only if already collected without disturbing the existing payload protocol.

### Subtask T014 – Replace early exits with post-outcome evidence collection

**Purpose**: Prevent hosted readiness from controlling local execution.

1. Remove/retire `_enforce_saas_sync_auth_refusal` and
   `_enforce_saas_sync_boundary_preflight` as command-exit guards.
2. Resolve repository/Mission context and complete every eligible local success,
   blocked, or error path before hosted assessment.
3. Materialize one immutable `SetupPlanLocalOutcome` containing the complete primary
   payload and exit before invoking any auth, structural, or route adapter.
4. When SaaS is enabled, obtain WP01's typed session assessment directly through WP02's
   no-raise `TokenManager.session_assessment` adapter. Never call the readiness probe or
   queue scope. Defensively convert unexpected failure to `SAAS_SYNC_AUTH_UNKNOWN`.
5. After the outcome is frozen, invoke WP02's no-raise structural assessment and resolve
   route evidence through `resolve_checkout_sync_routing_readonly(repo_root)`.
6. Treat route as available only for a non-null result with non-empty `project_uuid` and
   `effective_sync_enabled=true`; otherwise add `SAAS_SYNC_ROUTE_UNAVAILABLE`.
7. Do not wrap local errors in the hosted assessment exception boundary.
8. Pre-root context/git failures retain their existing payload/exit and do not fabricate
   hosted evidence.
9. Update load-bearing command call-graph comments to match live behavior.

### Subtask T015 – Guard every hosted effect and preserve local intents

**Purpose**: Close the lifecycle bypass and future effect class by construction.

1. Change setup-plan phase emission to WP03's local-only surface and retain returned
   envelopes as inert lifecycle intents.
2. Create `setup_plan_hosted_effects.py` as the sole production module permitted to
   import or name physical setup-plan hosted sinks.
3. Expose one narrow executor that accepts the immutable decision plus inert lifecycle
   and dossier intents. `mission_setup_plan.py` imports only this executor.
4. Validate the exact issued decision identity immediately before any sink is selected
   or called; reject forged, copied, reconstructed, or deserialized equivalents.
5. Revalidate at private sink adapters where selection would otherwise create a bypass.
6. When allowed, invoke explicit lifecycle fan-out and the established dossier seam.
   When refused, invoke neither.
7. Audit the complete transitive setup-plan call graph for offline queue, body upload,
   dossier capture/publication, daemon/dashboard publication, direct SaaS, and
   read-then-act hosted operations.
8. Route every discovered hosted-producing seam through the executor or document with
   proof that it is local-only.
9. Preserve local files, lifecycle JSONL, docs wiring, and safe commits.

An allowed hosted-effect failure must never replace the frozen local result. Preserve
the existing sink's internal reporting and log the executor failure without inventing a
new local exit; transport retry/recovery policy remains outside this Mission.

### Subtask T016 – Build one authoritative outcome reporter

**Purpose**: Ensure diagnostics cannot replace or fragment the local result.

1. Introduce an internal immutable `SetupPlanLocalOutcome` or equivalent value that
   carries primary payload and exit.
2. Centralize hosted assessment, optional execution, JSON serialization, and human
   rendering at one finalization seam that receives an already-frozen local outcome.
3. Attach WP02 diagnostics as `warnings` without mutating primary fields.
4. Thread the same reporting path through complete, scaffold, blocked, committed,
   spec-gate, missing-spec, template, and generic error emitters whenever assessment
   evidence is available.
5. Render diagnostics once and in deterministic order.
6. Preserve existing exit codes; do not normalize blocked outcomes.

Keep the orchestrator under the repository complexity ceiling by extracting only the
deterministic adapter/reporter helpers required by this change.

### Subtask T017 – Add production-chain acceptance

**Purpose**: Make the original issue impossible to fake with Boolean mocks.

1. Use real isolated encrypted/file session storage and real `TokenManager` initialization.
2. Store a session with expired access token and usable refresh token.
3. Provide no queue scope and make every queue-scope reader raise if touched.
4. Invoke the real Typer setup-plan command and assert no auth warning.
5. Add a real corrupted/unreadable storage case and assert exactly
   `SAAS_SYNC_AUTH_UNKNOWN`, zero unauthenticated warnings, and the unchanged local result.
6. Inject an exception from canonical assessment acquisition/evaluation through the real
   command and assert exactly `SAAS_SYNC_AUTH_UNKNOWN`, zero unauthenticated warnings,
   complete baseline payload/exit equality, and zero hosted effects.
7. Inject a raised structural preflight and assert boundary warning, unchanged local
   result, local lifecycle JSONL, and zero hosted sink calls.
8. Under SaaS-disabled mode, make auth, boundary, and route probes fatal if touched and
   assert baseline-identical output/exit, no warnings, and zero hosted effects.
9. Exercise null, denied/missing-identity, and raised canonical route resolution; assert
   `SAAS_SYNC_ROUTE_UNAVAILABLE`, unchanged local output/exit, and zero hosted effects.
10. Include JSON and representative human-output parity.

Never use the real home directory, live SaaS, or a running daemon.

### Subtask T018 – Add structural boundary gate and policy documentation

**Purpose**: Prevent recurrence and close FR-015 concretely.

1. Create `tests/architectural/test_setup_plan_hosted_effect_gate.py`.
2. Define `setup_plan_hosted_effects.py` as the only physical sink boundary and
   `execute_setup_plan_hosted_effects()` as the only orchestrator-facing effect call.
3. Forbid sink imports, dynamic imports, and sink names in every other setup-plan module;
   this structural edge is the primary safety rule, not an endless catalogue of call
   expression shapes.
4. Prove canonical decision validation dominates every physical sink inside the boundary
   and every private adapter that can select one.
5. Add synthetic direct, alias, nested-function, container, `partial`, dynamic import,
   `vars(...).get`, and `operator.getitem` mutations and assert the gate rejects each.
6. Keep any allowlist specific and shrink-only in spirit; document each authorized site.
7. Update `docs/operations/logged-out-teamspace.md` to distinguish local commands from
   hosted-only commands and explicitly name `agent mission create` and `setup-plan`.
8. State logged-out versus auth-assessment-failure remedies without exposing credentials,
   representing assessment failure as an auth state, or instructing automation to log in
   for the user.

### Subtask T019 – Run integrated gates and closeout evidence

Run the commands in `quickstart.md`, including:

```bash
uv run pytest -q \
  tests/auth/test_token_manager.py \
  tests/readiness/test_auth_probe.py \
  tests/status/test_lifecycle_events.py \
  tests/specify_cli/cli/commands/agent/test_setup_plan_hosted.py \
  tests/runtime/test_setup_plan_sync_evidence.py \
  tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py \
  tests/specify_cli/cli/commands/agent/test_setup_plan_read_surface.py \
  tests/specify_cli/cli/commands/agent/test_issue_3425_setup_plan_legacy_layout_silent_capture.py \
  tests/architectural/test_setup_plan_hosted_effect_gate.py

uv run pytest -q tests/sync/test_sync_boundary_preflight.py \
  tests/architectural/test_status_sync_boundary.py \
  tests/architectural/test_dossier_sync_boundary.py
```

Run Ruff and strict mypy for changed source, plus the terminology gate because operator
documentation changed. Record requirement evidence for all FRs. At Mission acceptance,
record issue #3127 as fixed or deferred-with-followup with evidence. If it remains open
P0, report the release gate honestly without blocking this WP or Mission completion.

## Test Strategy

Testing is outside-in and nonfakeable:

- baseline snapshots freeze current local results before refactor;
- pure decision tests live in WP02;
- lifecycle seam tests live in WP03;
- this WP proves the real cross-layer chain and all transitive effects;
- human/JSON parity and exactly-one-document assertions protect protocol behavior;
- module-edge/dominance gate plus hostile synthetic mutations closes future bypasses.

## Risks & Mitigations

- **Multiple JSON documents**: one reporter and parser-level tests.
- **Early local result loses warnings**: explicit spec/missing/template/generic rows.
- **Local failure becomes success**: baseline payload and exit comparisons.
- **Lifecycle queue bypass survives**: local-only API plus effect spies and structural
  module-edge/dominance gate.
- **Preflight exception escapes**: real CLI exception-injection case.
- **Scope drifts into hosted-only commands**: no ownership outside setup-plan surfaces.
- **Documentation promises more than code**: named parity assertion and same-WP docs.

## Review Guidance

Review this as an authority and egress-boundary change:

1. Trace every setup-plan return/raise path.
2. Verify local outcomes and exits against baseline, not prose alone.
3. Confirm no setup-plan module outside `setup_plan_hosted_effects.py` imports or names a
   physical sink, and confirm exact canonical-decision validation dominates all sinks
   inside it.
4. Confirm local lifecycle persistence remains unconditional where eligible.
5. Inspect the real encrypted-storage tests for accidental Boolean mocks.
6. Run the architectural gate's synthetic self-test.
7. Confirm `sync now` and canonical preflight were not weakened.
8. Confirm issue #3127 has a terminal acceptance verdict and blocks release readiness
   only while unresolved.

## Activity Log

- 2026-08-23T18:07:49Z – system – Prompt replaced with the then-current two-lane orchestration contract (historical; superseded below).
- 2026-08-24 – system – Rewritten for local-first sequencing and sole-module hosted-effect ownership.

### Updating Status

Use `spec-kitty agent tasks move-task WP04 --to <status>`.
