---
work_package_id: WP02
title: Hosted assessment and decision
dependencies:
- WP01
requirement_refs:
- FR-007
- FR-008
- FR-012
planning_base_branch: fix/setup-plan-auth-diagnostics-nonfatal
merge_target_branch: fix/setup-plan-auth-diagnostics-nonfatal
branch_strategy: Planning artifacts for this mission were generated on fix/setup-plan-auth-diagnostics-nonfatal. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/setup-plan-auth-diagnostics-nonfatal unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
phase: Phase 2 - Hosted decision
history:
- at: '2026-08-24T00:00:00Z'
  actor: system
  action: Rewritten for direct TokenManager evidence and local-first orchestration
- at: '2026-08-23T18:07:49Z'
  actor: system
  action: Prompt created from remediated hosted-decision architecture
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- src/specify_cli/cli/commands/agent/setup_plan_hosted.py
- tests/specify_cli/cli/commands/agent/test_setup_plan_hosted.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/setup_plan_hosted.py
- tests/specify_cli/cli/commands/agent/test_setup_plan_hosted.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/3621
---

# Work Package Prompt: WP02 – Hosted assessment and decision

## Do This First: Load Agent Profile

Load `implementer-ivan`, the project charter, and action-scoped implementation doctrine.
Begin with a failing test commit that is red on WP02's dependency-resolved lane base.
WP01 must be approved or done before this package is claimed.

## Objectives & Success Criteria

Create one setup-plan-specific decision adapter that reads local session-evaluation
evidence directly from `TokenManager`, combines it with canonical structural preflight,
route availability, and the SaaS-enable flag, and issues an immutable
`HostedSyncDecision` only after WP04 has frozen the local outcome.

Completion requires:

- SaaS disabled invokes no auth, boundary, or route probe and yields no diagnostics;
- only completed assessment + usable session + boundary safe + route available allows
  hosted effects;
- logged out, auth-assessment failure, boundary unsafe, boundary exception, and route
  unavailable refuse hosted effects with distinct stable diagnostics;
- diagnostics are deduplicated and ordered auth → boundary → route;
- token-manager/session-evaluation failures become `SAAS_SYNC_AUTH_UNKNOWN` and never
  escape;
- structural adapter never raises to its local command caller;
- no raw exception, credential, session, or token content appears in details.

## Context & Constraints

Read the Mission spec FR-007/FR-008/FR-012, plan component 2 and diagnostic contract,
research decisions 3–4, data model, and result-envelope contract. Read canonical
`src/specify_cli/sync/preflight.py` but do not edit it.

This module is command-adapter logic, not a new global sync or authentication authority.
It may lazily obtain the existing token manager and consume WP01's typed
`session_assessment` surface. It must not route bearer authority through
`readiness.auth.probe_auth_status()`, import queue-scope readers as authentication
evidence, or change hosted-only command behavior.

## Branch Strategy

- **Planning base branch**: `fix/setup-plan-auth-diagnostics-nonfatal`
- **Merge target branch**: `fix/setup-plan-auth-diagnostics-nonfatal`
- **Implementation command**: `spec-kitty agent action implement WP02 --agent <name>`
- Use only the dependency-resolved lane workspace from `lanes.json`.
- Modify/create only the two owned files.

## Required Design Shape

Use small immutable values, conceptually:

```python
class BoundaryState(StrEnum):
    SAFE = "safe"
    UNSAFE = "unsafe"
    UNKNOWN = "unknown"

@dataclass(frozen=True, slots=True)
class HostedSyncDiagnostic:
    code: str
    severity: str
    hosted_disposition: str
    message: str
    details: Mapping[str, object] | None = None

@dataclass(frozen=True, slots=True)
class HostedSyncDecision:
    requested: bool
    allow_effects: bool
    diagnostics: tuple[HostedSyncDiagnostic, ...]
```

Names may adapt to repository conventions, but invariants may not.

## Subtasks & Detailed Guidance

### Subtask T005 – Write and commit rejecting truth-table tests

**Purpose**: Freeze the decision independently of setup-plan orchestration.

Cover:

1. SaaS disabled short-circuits every supplied probe.
2. Completed assessment + usable session + safe boundary + available route allows with
   no warning.
3. Logged out yields `SAAS_SYNC_UNAUTHENTICATED`.
4. Failed auth assessment yields `SAAS_SYNC_AUTH_UNKNOWN`, never unauthenticated.
5. Raised token-manager construction, property access, or session evaluation yields
   `SAAS_SYNC_AUTH_UNKNOWN`, never escapes, and never becomes unauthenticated.
6. Returned unsafe boundary yields `SAAS_SYNC_BOUNDARY_UNSAFE` and preserves sanitized
   `PreflightResult.to_dict()` evidence.
7. Raised preflight evaluation yields `SAAS_SYNC_BOUNDARY_UNSAFE` with stable
   `boundary_evaluation_failed`, no raw exception text.
8. Usable session/no route yields `SAAS_SYNC_ROUTE_UNAVAILABLE`, not an auth diagnostic.
9. Combined problems remain distinct and deterministically ordered.
10. Every failed or non-affirmative input refuses.

Commit these tests red before adding the production module.

### Subtask T006 – Implement no-raise boundary assessment

**Purpose**: Preserve strict structural safety without preempting local work.

1. Call `run_preflight(repo_root=repo_root, require_auth=False)`.
2. Translate a passing result to safe.
3. Translate non-passing structural evidence to unsafe with sanitized `to_dict()` data.
4. Catch exceptions only at this setup-plan adapter boundary and translate to unknown.
5. Never call a route reader, auth reader, migration, repair, or hosted sink here.
6. Do not alter `run_preflight` or its behavior for `sync now` and other callers.

### Subtask T007 – Implement diagnostic and decision composition

**Purpose**: Create the single permission consumed by WP04.

1. Accept typed session evaluation, boundary evaluation, and canonical route availability
   as separate inputs. Do not accept an unproven default value.
2. Provide a narrow no-raise collector around `TokenManager.session_assessment` directly,
   validate its runtime shape, and convert unexpected construction, property, or
   evaluation failure into assessment-failed evidence.
3. Build stable warning objects with command severity `warning` and hosted disposition
   `refused`.
4. Permit effects only when all required evidence is affirmative.
5. Preserve multiple warnings; deduplicate by code and use deterministic order.
6. Provide plain JSON serialization that returns primitive collections.
7. Keep human message text accurate: hosted sync was skipped/refused, local setup-plan
   did not fail.

Do not execute effects in this module. It decides; WP04 executes.

### Subtask T008 – Verify quality and safety properties

Run:

```bash
uv run pytest -q tests/specify_cli/cli/commands/agent/test_setup_plan_hosted.py \
  tests/sync/test_sync_boundary_preflight.py
uv run ruff check src/specify_cli/cli/commands/agent/setup_plan_hosted.py \
  tests/specify_cli/cli/commands/agent/test_setup_plan_hosted.py
uv run mypy --strict src/specify_cli/cli/commands/agent/setup_plan_hosted.py
```

Add explicit assertions that diagnostic payloads omit exception reprs, tokens, session
objects, and filesystem ciphertext. Confirm the new module has no imports from queue
scope readers or hosted transports.

## Test Strategy

Pure table tests own composition; one adapter test uses a representative real
`PreflightResult`. Structural detector mechanics remain in `tests/sync`. Inject probes
as callables or patch the canonical import seam so disabled-mode and no-raise behavior
are objective. Do not duplicate all filesystem mismatch fixtures here.

## Risks & Mitigations

- **Second auth authority**: consume WP01 session assessment directly; readiness and
  queue routing are explicitly excluded.
- **Global preflight weakening**: no edits outside owned files.
- **Overbroad exception swallowing**: translate only boundary evaluation, never local
  setup-plan errors or started hosted-effect failures.
- **Credential leakage**: stable reasons and sanitized evidence.

## Review Guidance

Reject if a Boolean false is the only auth input, if `require_auth=True` reintroduces a
second auth bit, if assessment failure or unknown safety evidence allows effects, or if
the module invokes any hosted sink.
Check that the raised-preflight test would fail if the try/except were removed.

## Activity Log

- 2026-08-23T18:07:49Z – system – Prompt created from remediated hosted-decision architecture.
- 2026-08-24 – system – Rewritten for direct TokenManager evidence and local-first sequencing.

### Updating Status

Use `spec-kitty agent tasks move-task WP02 --to <status>`.
