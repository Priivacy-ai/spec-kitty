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
- at: '2026-08-23T18:07:49Z'
  actor: system
  action: Prompt replaced with two-lane orchestration and compatibility contract
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- tests/architectural/test_setup_plan_hosted_effect_gate.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/mission_setup_plan.py
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
WP02, and WP03 are approved or done. Start with a failing acceptance-test commit before
editing `mission_setup_plan.py`.

## Objectives & Success Criteria

Refactor the real setup-plan entry point into a local lane and a hosted-assessment lane
joined by one explicit decision. Local verification produces the authoritative payload
and exit. Hosted diagnostics are additive. Every hosted effect is executed only through
an allowing decision, while local lifecycle persistence and other local work continue.

Completion requires:

- no auth or structural early exit prevents eligible local verification;
- every baseline local outcome retains all primary fields and its exit;
- JSON mode emits one object; human mode has equivalent warning severity;
- real refresh-capable encrypted storage without scope produces no auth warning;
- real unreadable storage produces an auth-assessment-failure diagnostic, not logged out;
- returned and raised structural failures refuse hosted effects and preserve local work;
- local lifecycle JSONL is written while lifecycle fan-out/dossier/queue/upload/
  daemon/dashboard/direct hosted sinks remain zero under refusal;
- an AST architectural gate with synthetic mutation prevents future bypasses;
- `agent mission create` and setup-plan policy are named consistently in the logged-out
  Teamspace operations document;
- issue #3127 remains a visible release gate, not a code dependency.

## Context & Constraints

Read every artifact in
`kitty-specs/setup-plan-auth-diagnostics-nonfatal-01M0QEAD/`, especially the binding
local outcome matrix and hosted-effect contract. Read accepted auth, transport,
single-authority-gate, and project-sync-store ADRs named by the plan.

WP01 supplies typed session assessment. WP02 supplies the no-raise decision. WP03
supplies local-only lifecycle persistence and explicit fan-out. Consume those APIs; do
not recreate their logic inside `mission_setup_plan.py`.

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

Tests compare complete payload subsets or snapshots from the real pre-existing entry
point. Authentication/boundary variants may add `warnings`; they may not alter any
other field or exit.

## Subtasks & Detailed Guidance

### Subtask T013 – Capture baseline and commit rejecting matrix

**Purpose**: Make compatibility objective before rearranging control flow.

1. Inventory every return, emitter, and `typer.Exit` in `setup_plan()` and helpers.
2. Add/extend fixtures for every matrix row in the owned tests.
3. Capture exact `result`, `phase_complete`, `scaffold_only`, `blocked_reason`,
   `error_code`, branch/commit fields, and process exit where present.
4. Cross representative success, blocked, and error rows with logged out,
   auth-assessment failure, boundary unsafe, and boundary exception.
5. Assert exactly one JSON object.
6. Commit tests red against the old auth/preflight exit-2 behavior before production
   changes.

Pre-root project/context failures need no structural warning because no repository root
exists. Auth diagnostics may attach only if already collected without disturbing the
existing payload protocol.

### Subtask T014 – Replace early exits with evidence collection

**Purpose**: Prevent hosted readiness from controlling local execution.

1. Remove/retire `_enforce_saas_sync_auth_refusal` and
   `_enforce_saas_sync_boundary_preflight` as command-exit guards.
2. When SaaS is enabled, obtain WP01's typed session assessment without queue scope.
3. Resolve the repository root using existing local behavior.
4. After root resolution, invoke WP02's no-raise structural assessment and compose one
   `HostedSyncDecision`, including route evidence if the existing hosted path requires
   it.
5. Continue spec gate, plan scaffold/readiness, commit, and documentation wiring.
6. Do not wrap local errors in the hosted assessment exception boundary.
7. Update load-bearing command call-graph comments to match live behavior.

### Subtask T015 – Guard every hosted effect and preserve local intents

**Purpose**: Close the lifecycle bypass and future effect class by construction.

1. Change setup-plan phase emission to WP03's local-only surface and retain returned
   envelopes as lifecycle intents.
2. Define a narrow command-local executor that receives the immutable decision and all
   hosted intents.
3. When allowed, invoke explicit lifecycle fan-out and the established dossier seam.
4. When refused, invoke neither.
5. Audit the complete transitive setup-plan call graph for offline queue, body upload,
   dossier capture/publication, daemon/dashboard publication, direct SaaS, and
   read-then-act hosted operations.
6. Route every discovered hosted-producing seam through the executor or document with
   proof that it is local-only.
7. Preserve local files, lifecycle JSONL, docs wiring, and safe commits.

Do not suppress failures after an allowed hosted effect has actually started; this
Mission controls eligibility, not general transport recovery.

### Subtask T016 – Build one authoritative outcome reporter

**Purpose**: Ensure diagnostics cannot replace or fragment the local result.

1. Introduce an internal immutable `SetupPlanLocalOutcome` or equivalent value that
   carries primary payload and exit.
2. Centralize JSON serialization and human rendering at one final reporting seam.
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
6. Inject a raised structural preflight and assert boundary warning, unchanged local
   result, local lifecycle JSONL, and zero hosted sink calls.
7. Include JSON and representative human-output parity.

Never use the real home directory, live SaaS, or a running daemon.

### Subtask T018 – Add architectural gate and policy documentation

**Purpose**: Prevent recurrence and close FR-015 concretely.

1. Create `tests/architectural/test_setup_plan_hosted_effect_gate.py`.
2. Define the sanctioned setup-plan hosted-effects executor/call site as the explicit
   authority.
3. Detect direct setup-plan calls to known lifecycle fan-out, dossier, queue, upload,
   daemon/dashboard, or hosted transport surfaces outside that authority.
4. Add a synthetic temporary source mutation containing a forbidden call and assert the
   scanner fails. A gate without this negative control is unacceptable.
5. Keep any allowlist specific and shrink-only in spirit; document each authorized site.
6. Update `docs/operations/logged-out-teamspace.md` to distinguish local commands from
   hosted-only commands and explicitly name `agent mission create` and `setup-plan`.
7. State logged-out versus auth-assessment-failure remedies without exposing credentials,
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
documentation changed. Record requirement evidence for all FRs. Verify issue #3127's
state at Mission acceptance/release closeout; if it remains open P0, report the release
gate honestly without blocking completion of this code WP.

## Test Strategy

Testing is outside-in and nonfakeable:

- baseline snapshots freeze current local results before refactor;
- pure decision tests live in WP02;
- lifecycle seam tests live in WP03;
- this WP proves the real cross-layer chain and all transitive effects;
- human/JSON parity and exactly-one-document assertions protect protocol behavior;
- AST gate plus synthetic violation closes future bypasses.

## Risks & Mitigations

- **Multiple JSON documents**: one reporter and parser-level tests.
- **Early local result loses warnings**: explicit spec/missing/template/generic rows.
- **Local failure becomes success**: baseline payload and exit comparisons.
- **Lifecycle queue bypass survives**: local-only API plus effect spies and AST gate.
- **Preflight exception escapes**: real CLI exception-injection case.
- **Scope drifts into hosted-only commands**: no ownership outside setup-plan surfaces.
- **Documentation promises more than code**: named parity assertion and same-WP docs.

## Review Guidance

Review this as an authority and egress-boundary change:

1. Trace every setup-plan return/raise path.
2. Verify local outcomes and exits against baseline, not prose alone.
3. Search for every hosted-producing call and confirm executor dominance.
4. Confirm local lifecycle persistence remains unconditional where eligible.
5. Inspect the real encrypted-storage tests for accidental Boolean mocks.
6. Run the architectural gate's synthetic self-test.
7. Confirm `sync now` and canonical preflight were not weakened.
8. Confirm issue #3127 is tracked only as release-closeout evidence.

## Activity Log

- 2026-08-23T18:07:49Z – system – Prompt replaced with two-lane orchestration and compatibility contract.

### Updating Status

Use `spec-kitty agent tasks move-task WP04 --to <status>`.
