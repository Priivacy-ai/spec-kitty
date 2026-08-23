---
work_package_id: WP02
title: setup-plan local and hosted separation
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-012
planning_base_branch: fix/setup-plan-auth-diagnostics-nonfatal
merge_target_branch: fix/setup-plan-auth-diagnostics-nonfatal
branch_strategy: Planning artifacts for this mission were generated on fix/setup-plan-auth-diagnostics-nonfatal. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/setup-plan-auth-diagnostics-nonfatal unless the human explicitly redirects the landing branch.
created_at: '2026-08-23T16:23:38Z'
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
- T011
phase: Phase 2 - Command behavior
history:
- at: '2026-08-23T16:23:38Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission_setup_plan.py
- tests/runtime/test_setup_plan_sync_evidence.py
- tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/3621
---

# Work Package Prompt: WP02 — setup-plan local and hosted separation

## Objective

Change `spec-kitty agent mission setup-plan` from an early fail-closed mixed command into a correctly separated orchestration:

1. collect local authentication and structural sync-boundary evidence;
2. always perform the requested local repository/spec/plan work;
3. treat that local result as authoritative for result classification and exit status;
4. attach hosted readiness problems as stable, ordered warnings;
5. refuse only dossier enqueue/direct hosted delivery when hosted safety is false.

Structural detectors remain unchanged and fail-closed at hosted side-effect seams. Other synchronization commands retain their existing refusal behavior.

## Success Criteria

- Logged out + complete plan produces local success, one `SAAS_SYNC_UNAUTHENTICATED` warning, and exit 0.
- Unknown auth + complete plan produces local success, one `SAAS_SYNC_AUTH_UNKNOWN` warning, and exit 0.
- Authenticated refresh-capable session without queue scope produces no auth warning.
- Incomplete/non-substantive plan preserves its established blocked result and exit behavior under every auth state.
- Any structural boundary failure produces `SAAS_SYNC_BOUNDARY_UNSAFE` with `PreflightResult.to_dict()` evidence.
- Auth and structural warnings can coexist in deterministic auth-then-structural order.
- Structured output remains one valid JSON object.
- Human output labels diagnostics as warnings and still prints the normal local result.
- Unsafe hosted dossier/enqueue/delivery is not attempted.
- Local phase JSONL events, plan scaffold/readiness, documentation wiring, and commit routing remain active.
- SaaS-disabled and coherent-authenticated behavior stays compatible.

## Context

Read before editing:

- `kitty-specs/setup-plan-auth-diagnostics-nonfatal-01M0QEAD/spec.md` — especially all four user stories, FR-001 and FR-004 through FR-012, NFR-001 through NFR-007, and C-003/C-007.
- `kitty-specs/setup-plan-auth-diagnostics-nonfatal-01M0QEAD/plan.md` — control flow and IC-02/IC-03/IC-04.
- `kitty-specs/setup-plan-auth-diagnostics-nonfatal-01M0QEAD/data-model.md` — invocation-scoped values and exit invariant.
- `kitty-specs/setup-plan-auth-diagnostics-nonfatal-01M0QEAD/research.md` — Decisions 2 through 5.
- `kitty-specs/setup-plan-auth-diagnostics-nonfatal-01M0QEAD/contracts/setup-plan-result-envelope.md` — binding machine/human output and side-effect boundary.

Current call order in `mission_setup_plan.setup_plan()`:

```text
_enforce_saas_sync_auth_refusal        # queue scope, exits 2
locate_project_root
_enforce_saas_sync_boundary_preflight  # run_preflight, exits 2
git preflight / mission resolution / spec gate
plan scaffold + local phase events
plan completeness + commit
documentation wiring
_trigger_dossier_sync                  # hosted side-effect seam
_emit_setup_plan_result
```

The two early `typer.Exit(2)` calls are the defect. `_emit_spec_plan_phase_events` is documented in the source audit as local lifecycle JSONL only; do not suppress it. `_trigger_dossier_sync` is the known dossier upload/enqueue seam and must be conditional.

WP01 provides `probe_auth_status()` semantics. Consume its existing `AuthStatus`; do not create a second auth authority or inspect queue scope.

## Branch Strategy

- Planning base: `fix/setup-plan-auth-diagnostics-nonfatal`.
- Final merge target: `fix/setup-plan-auth-diagnostics-nonfatal`.
- This package depends on WP01.
- Run implementation through `spec-kitty agent action implement WP02 --agent <name>` only after the runtime reports WP01 satisfied.
- Spec Kitty allocates the execution worktree from the dependency-resolved lane in `lanes.json`; do not create or select a worktree manually.
- Modify only the files declared in `owned_files`.

## Required Design Shape

Keep the new command-local model small and immutable. A reasonable shape inside `mission_setup_plan.py` is:

```python
@dataclass(frozen=True, slots=True)
class HostedSyncDiagnostic:
    code: str
    message: str
    remediation: tuple[str, ...] = ()
    details: Mapping[str, object] | None = None

@dataclass(frozen=True, slots=True)
class HostedSyncDecision:
    allowed: bool
    diagnostics: tuple[HostedSyncDiagnostic, ...] = ()
```

Names may vary to fit repository conventions, but preserve these invariants:

- one value is carried through the command;
- warning order is deterministic;
- JSON serialization is centralized;
- human rendering is centralized;
- `allowed` is consulted only at hosted side-effect seams;
- local result emitters receive diagnostics without recomputing auth/preflight.

Avoid creating a new module unless unavoidable: this WP owns only `mission_setup_plan.py`, and the decision is adapter-specific. `readiness.auth` and `sync.preflight` remain the domain authorities.

## Subtasks and Detailed Guidance

### T005 — Write rejecting setup-plan helper contracts

Update `tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py` first.

Replace the old helper expectations:

- `_enforce_saas_sync_auth_refusal` exits when unauthenticated;
- `_enforce_saas_sync_auth_refusal` passes when scope exists;
- `_enforce_saas_sync_boundary_preflight` exits on incoherence.

with tests for the new read-only collectors/composer. Required cases:

1. SaaS disabled returns `allowed=True` and no diagnostics without calling auth or preflight probes.
2. `AUTHENTICATED` plus coherent structural result allows hosted effects and emits no warning.
3. Each conclusive logged-out status emits one `SAAS_SYNC_UNAUTHENTICATED` warning.
4. `UNKNOWN` and defensive `NOT_CHECKED` emit `SAAS_SYNC_AUTH_UNKNOWN`, never unauthenticated.
5. Structurally non-OK preflight emits one `SAAS_SYNC_BOUNDARY_UNSAFE` warning whose details preserve the full `to_dict()` output.
6. Logged-out/unknown plus structural failure yields exactly two warnings in auth-then-structural order.
7. Result-emitter tests prove warnings attach to success, scaffold-only, blocked, and committed result payloads without changing existing fields.
8. Human emitter uses warning severity and does not print `Refusing setup-plan` or an auth `Error`.

Use fakes of `AuthStatus` and `PreflightResult` through public seams. Do not depend on ambient credentials, daemon records, or a real project store in unit tests.

Rejecting-first rule: run the changed helper tests before production edits and record that the old exit helpers cannot satisfy them.

### T006 — Write rejecting CLI acceptance matrix

Update `tests/runtime/test_setup_plan_sync_evidence.py` before production behavior.

The current module documents and asserts old FR-011 exit-2 behavior. Replace that authority with issue #3621's matrix while retaining queue safety evidence.

Required auth/completeness rows:

| Auth | Local plan | Expected local result | Auth diagnostic | Exit |
|---|---|---|---|---|
| authenticated | complete | success/complete | none | 0 |
| authenticated, no scope | complete | success/complete | none | 0 |
| logged out | complete | success/complete | `SAAS_SYNC_UNAUTHENTICATED` | 0 |
| unknown | complete | success/complete | `SAAS_SYNC_AUTH_UNKNOWN` | 0 |
| authenticated | incomplete | established blocked result | none | established local exit/result |
| logged out | incomplete | same blocked result | unauthenticated warning | same local exit/result |
| unknown | incomplete | same blocked result | unknown warning | same local exit/result |

Required structural rows:

- each of the six canonical owner mismatch fields;
- orphan owner record;
- unreadable owner record;
- project-store diagnostic;
- active legacy event/body-upload row evidence if the current detector can produce it.

Use parametrization over structured preflight fixtures where a full filesystem integration per mismatch would duplicate `tests/sync` detector coverage. Keep at least one real orphan/mismatch integration case to prove command wiring. Every row must assert:

- local verification ran and its result was returned;
- `SAAS_SYNC_BOUNDARY_UNSAFE` identifies the structural evidence;
- `_trigger_dossier_sync` or the underlying enqueue spy was not called;
- legacy and scoped queues gained no hosted row from the refused seam.

Add human-output parity for at least logged-out and structural failure. Parse JSON as one object rather than substring matching multiple writes.

### T007 — Add diagnostic and hosted-decision composition

Implement the command-local immutable model and pure projections in `mission_setup_plan.py`.

Auth projection:

- Import `probe_auth_status` and `AuthStatus` lazily to preserve startup/import behavior.
- Invoke it only when `SPEC_KITTY_ENABLE_SAAS_SYNC == "1"`.
- `AUTHENTICATED` adds no diagnostic.
- `LOGGED_OUT_IN_TEAMSPACE` and `NOT_IN_TEAMSPACE` add `SAAS_SYNC_UNAUTHENTICATED`.
- `UNKNOWN` and defensive unexpected/not-checked values add `SAAS_SYNC_AUTH_UNKNOWN`.
- Do not read `read_queue_scope_from_session` or `read_queue_scope_from_credentials`.

Structural projection:

- Call `run_preflight(repo_root=repo_root, require_auth=False)` or otherwise explicitly exclude its legacy auth bit from structural safety. Auth is already classified by the canonical auth authority.
- Preserve all structural fields/detectors and use `to_dict()` for diagnostic details.
- Do not alter `src/specify_cli/sync/preflight.py` or its behavior for other callers.
- If the preflight returns non-OK because of a legacy `auth_present` coupling despite `require_auth=False`, derive structural coherence from the documented structural evidence rather than reintroducing target/queue-derived auth.

Messages must be accurate: hosted sync was skipped; local verification did not fail. Remediation can suggest a later authorized login or boundary repair but must not perform it.

### T008 — Replace early exits with collection

Refactor `setup_plan()` so neither auth nor structural hosted readiness raises `typer.Exit(2)` before local work.

Required sequencing:

1. Collect the auth component at the current early location so diagnostics are available without needing repository context.
2. Resolve the repository root as today. A genuine project-root error remains a local command error.
3. Collect structural evidence after repository root resolution.
4. Continue git preflight, mission resolution, spec gate, scaffold/readiness, commit, and documentation wiring unchanged.
5. Carry the composed decision rather than recomputing it.

Remove or rename the obsolete `_enforce_*` helpers. Update their load-bearing comments and the long setup-plan call-graph audit so it states the new guarantee: preflight still protects every hosted-producing path, but it no longer refuses local work.

Do not broaden this mission into generic exception recovery. Existing local errors still fail exactly as before.

### T009 — Attach warnings to JSON and human local outcomes

Centralize serialization so `HostedSyncDiagnostic` becomes a plain JSON object with:

- `code`;
- `message`;
- `remediation` as an array when present;
- `details` when present.

Thread diagnostics through `_emit_setup_plan_result` and local gate/error emitters reached after diagnostics are collected. Required behavior:

1. JSON mode emits one document containing the normal result plus `warnings` when non-empty.
2. Warning addition does not mutate `result`, `phase_complete`, `blocked_reason`, `error_code`, commit fields, or branch contract.
3. Human mode renders warning(s) and the existing normal result. Do not return early from `_emit_setup_plan_result` before rendering diagnostics.
4. Auth warnings are emitted at most once.
5. Both auth and structural warnings remain distinct when they coexist.
6. Local completeness/spec problems remain the primary result, not a warning-only success.

The current `_enforce_spec_gate()` can emit and return before the common final emitter. Adjust its interface or provide a shared result-envelope/render helper so warnings are not lost on incomplete/spec-gate outcomes. Keep changes localized and preserve existing tests for missing/invalid metadata and template errors.

### T010 — Isolate hosted side effects while preserving local effects

Use `HostedSyncDecision.allowed` immediately before every setup-plan hosted-producing seam.

Known seam:

- `_trigger_dossier_sync(feature_dir, mission_slug, repo_root)`.

Audit the full setup-plan call graph again for:

- body upload queue writes;
- event queue writes intended for hosted publication;
- direct SaaS calls;
- read-then-act hosted operations.

The existing source audit says `_emit_spec_plan_phase_events` writes local lifecycle JSONL only. Preserve that call regardless of hosted safety. Likewise preserve plan scaffolding, substantiveness checks, documentation wiring, and safe commit routing.

Tests must use spies/counters to prove both halves:

- unsafe verdict: hosted seam count is zero, local seam counts are one;
- safe coherent verdict: hosted seam retains its established invocation;
- SaaS disabled: established local behavior and absence/no-op hosted behavior remain compatible.

Do not catch and silently downgrade failures that occur after an allowed hosted side effect actually starts; this mission controls eligibility, not general sync error handling.

### T011 — Retire obsolete refusal evidence, preserve boundaries, and run gates

Within the two owned test files and source module:

1. Replace old test/module comments that cite fatal FR-011 exit-2 behavior as current authority.
2. Preserve the AST/no-legacy-DB regression and scoped-store safety assertions.
3. Preserve structural detector coverage by continuing to consume `run_preflight`; do not mock away all real integration evidence.
4. Keep unrelated read-surface, metadata, template resolution, documentation wiring, and commit-result tests unchanged except for signature adjustments required to pass diagnostics.
5. Ensure `sync now` and other hosted-sync entry points are untouched.
6. Do not add `--require-sync`, access-token-expiry UX, queue migration, or dependency changes.

Run a grep after the edit for stale setup-plan authority language such as:

```bash
rg -n "refuse-loudly|auth refusal|exits? 2|queue scope.*auth" \
  src/specify_cli/cli/commands/agent/mission_setup_plan.py \
  tests/runtime/test_setup_plan_sync_evidence.py \
  tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py
```

Historical references may remain only when clearly labeled superseded and necessary to explain compatibility.

After the evidence cleanup, run the focused and structural regression gates from the WP execution workspace after WP01 is present:

Run from the WP execution workspace after WP01 is present:

```bash
uv run pytest -q \
  tests/readiness/test_auth_probe.py \
  tests/sync/test_credential_scope_signal.py \
  tests/runtime/test_setup_plan_sync_evidence.py \
  tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py \
  tests/specify_cli/cli/commands/agent/test_setup_plan_read_surface.py

uv run pytest -q tests/sync

uv run ruff check \
  src/specify_cli/readiness/auth.py \
  src/specify_cli/cli/commands/agent/mission_setup_plan.py \
  tests/readiness/test_auth_probe.py \
  tests/sync/test_credential_scope_signal.py \
  tests/runtime/test_setup_plan_sync_evidence.py \
  tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py
```

Run the applicable project typing check for the changed source module. If time permits, run the broader agent mission command suite. Report unrelated baseline failures precisely; do not change unowned files to repair them.

## Test Strategy

Testing is mandatory and outside-in:

- Helper units pin deterministic classification/projection/rendering.
- CLI integration pins actual result and exit behavior.
- Structural parametrization covers every supported failure class while existing `tests/sync` pins detector mechanics.
- Queue assertions prove refusal remains fail-closed for hosted writes.
- Spies prove local effects continue.
- Human and JSON modes are both contractual.
- No test may use real auth, a live home directory, the network, or a running daemon.

Use explicit fixtures for complete and incomplete plan states. Compare local result fields across auth/boundary variants rather than merely asserting that a warning string exists.

## Definition of Done

- [ ] T005 and T006 were run and observed rejecting the old behavior before production edits.
- [ ] Queue scope is absent from setup-plan auth classification.
- [ ] Logged-out and unknown use different stable codes.
- [ ] Complete local verification exits 0 under auth and structural warnings.
- [ ] Incomplete/local-error outcomes retain their established classification and exit status.
- [ ] JSON output is one parseable result object with deterministic warnings.
- [ ] Human output presents warnings without refusal/error language for local work.
- [ ] Every structural failure class is represented and remains fail-closed for hosted delivery.
- [ ] `_trigger_dossier_sync` and any discovered hosted seam are skipped when unsafe.
- [ ] Local lifecycle/artifact/documentation/commit seams remain active.
- [ ] Coherent authenticated and SaaS-disabled paths remain compatible.
- [ ] Focused tests, `tests/sync`, Ruff, and applicable typing gates pass.
- [ ] Only `owned_files` were modified.

## Risks and Mitigations

- **Risk: multiple JSON documents.** Mitigation: collect diagnostics as values and serialize only in the normal result emitter.
- **Risk: early local gate loses warnings.** Mitigation: explicitly test spec/non-substantive paths and thread the same diagnostic tuple through them.
- **Risk: preflight auth bit becomes a second authority.** Mitigation: call structural preflight without auth requirement and classify auth only through WP01's probe.
- **Risk: local failure is accidentally converted to success.** Mitigation: compare identical local fixtures across auth states and assert byte-equivalent primary result fields/exit.
- **Risk: hosted write escapes the decision.** Mitigation: call-graph audit plus spies around dossier/queue seams.
- **Risk: local lifecycle gets suppressed with hosted work.** Mitigation: explicit positive local-event assertions under unsafe states.
- **Risk: structural safety weakened globally.** Mitigation: no edits to `sync.preflight` or other sync commands; run all `tests/sync`.
- **Risk: obsolete comments mislead future maintainers.** Mitigation: update the load-bearing audit and tests in the same WP.
- **Risk: scope creep into token expiry or strict mode.** Mitigation: enforce C-001/C-002 during review.

## Reviewer Guidance

Review this WP as a control-flow and side-effect boundary change:

1. Trace every `setup_plan()` return/raise path and verify auth/structural state cannot preempt local verification.
2. Confirm local failures are still failures and only hosted readiness changed severity.
3. Search for queue-scope auth reads; any remaining setup-plan use is blocking.
4. Confirm unknown is never emitted as unauthenticated.
5. Verify `warnings` is part of the single JSON result and does not create protocol noise.
6. Verify every hosted-producing seam is guarded and every local-only seam remains unconditional.
7. Confirm `run_preflight` and other sync commands were not weakened.
8. Run the entire T011 command set and inspect the parametrized structural evidence.
9. Check the diff stays within the three owned files.

## Activity Log

- 2026-08-23T16:23:38Z — system — Prompt created via `/spec-kitty.tasks`.
