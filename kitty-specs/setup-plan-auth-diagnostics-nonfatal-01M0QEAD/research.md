# Phase 0 Research: Nonfatal setup-plan auth diagnostics

## Decision 1: Reuse the canonical local readiness auth authority

**Decision**: Use `specify_cli.readiness.auth.probe_auth_status()` and its existing `AuthStatus` values. `AUTHENTICATED` permits hosted auth-dependent work; `LOGGED_OUT_IN_TEAMSPACE` and `NOT_IN_TEAMSPACE` map to `SAAS_SYNC_UNAUTHENTICATED`; `UNKNOWN` maps to `SAAS_SYNC_AUTH_UNKNOWN`.

**Rationale**: The readiness probe already delegates positive authentication to `TokenManager.is_authenticated`, which recognizes a stored refresh-capable session without depending on queue scope. It is local-only and performs no SaaS request. The existing enum already distinguishes unknown from both logged-out states.

**Required correction**: `probe_auth_status()` currently catches an exception from `TokenManager.is_authenticated`, sets `authenticated=False`, and may later classify the invocation as `NOT_IN_TEAMSPACE`. That exception path must return `UNKNOWN` so indeterminate storage/session evaluation is not mislabeled as logged out.

**Alternatives considered**:

- Keep reading queue scope: rejected because scope is routing metadata, not authentication proof.
- Add a setup-plan-only auth enum/probe: rejected because it would create a competing authority.
- Call SaaS to validate the token: rejected because planning must remain local/offline-capable and the user explicitly selected a local-only classification.

## Decision 2: Separate structural detection from command severity

**Decision**: Continue calling `sync.preflight.run_preflight()` as the structural authority, but in `setup-plan` convert a non-OK result into a hosted-side-effect refusal plus a nonfatal `SAAS_SYNC_BOUNDARY_UNSAFE` diagnostic. Do not weaken or change the detector, and do not change fail-closed behavior of commands whose purpose is hosted synchronization.

**Rationale**: `run_preflight()` is read-only, has a structured `to_dict()` projection, and detects the six canonical owner mismatches, orphan/unreadable ownership, legacy-row evidence where active, and project-store diagnostics. The defect is not its severity for hosted delivery; it is that setup-plan currently exits before performing unrelated local work.

**Alternatives considered**:

- Remove the structural preflight: rejected because it would permit unsafe hosted writes.
- Downgrade all sync commands globally: rejected because the approved scope is setup-plan's mixed local/hosted orchestration.
- Duplicate only selected checks in setup-plan: rejected because it would drift from the structural safety authority.

## Decision 3: Model one authoritative local result plus supplementary warnings

**Decision**: Preserve the existing setup-plan local payload and add a top-level `warnings` array when SaaS sync is enabled and auth or boundary state is non-ready. Each warning has a stable `code`, `message`, `remediation`, and optional `details`. The local result controls exit status.

**Rationale**: This is additive for successful JSON consumers and lets automation act independently on planning readiness and hosted delivery readiness. A structural warning embeds `PreflightResult.to_dict()` so individual failure classes remain machine-readable without proliferating inconsistent result shapes.

**Alternatives considered**:

- Emit a separate JSON object before the result: rejected because multiple JSON documents break the machine-output contract.
- Replace `result` with a compound status: rejected because it would make hosted readiness authoritative again and break established consumers.
- Use the same code for logged out and unknown: rejected by the user's explicit decision that those states may differ.

## Decision 4: Collect diagnostics before local work, enforce them only at hosted seams

**Decision**: Evaluate auth before repository resolution where feasible, evaluate structural preflight after repository resolution, retain the resulting immutable diagnostic/permission snapshot, and continue the full local setup-plan flow. Before `_trigger_dossier_sync` or any other hosted enqueue/delivery, require the snapshot to be safe. Local lifecycle events, plan scaffolding/readiness, documentation wiring, and safe commit continue.

**Rationale**: Early collection retains useful diagnostics and makes it possible to refuse every unsafe hosted seam, while delaying enforcement prevents the diagnostic from masking project-root, spec, plan, or commit outcomes. The current call graph documents `_emit_spec_plan_phase_events` as local JSONL-only, so those events are not suppressed.

**Alternatives considered**:

- Run diagnostics only after local work: rejected because future hosted seams could accidentally occur before the check.
- Skip all downstream activity after an unsafe verdict: rejected because it would suppress local lifecycle and artifact behavior covered by the mission.
- Rely on exceptions around hosted sync: rejected because prevention and explicit diagnostics are safer than attempting an unsafe side effect.

## Decision 5: ATDD matrix and compatibility boundary

**Decision**: Begin with CLI-level rejecting tests, then add focused units. Cover auth classification × complete/incomplete plan, human/JSON output, all structural failure classes, coherent hosted operation, disabled SaaS operation, and explicit absence of hosted side effects.

**Rationale**: The regression is user-observable control flow and exit semantics. CLI-level tests pin that contract; units make the classification and diagnostic projection failures easy to locate.

**Alternatives considered**:

- Unit tests only: rejected because they would not prove exit codes, early-return emitters, or side-effect suppression.
- Broad full-suite tests only: rejected because they would not provide a rejecting executable contract before implementation.
