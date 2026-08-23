# Data Model: setup-plan local result and hosted-sync diagnostics

This mission adds no persistent schema. The model consists of immutable, invocation-scoped values composed from existing auth and sync authorities.

## Authentication Classification

Existing authority: `specify_cli.readiness.coordinator.AuthStatus` returned by `probe_auth_status()`.

| Value | Meaning for setup-plan | Diagnostic |
|---|---|---|
| `AUTHENTICATED` | A supported usable local session exists, including a refresh-capable session with an expired access token. | None |
| `LOGGED_OUT_IN_TEAMSPACE` | No usable session exists and a connected Teamspace is known. | `SAAS_SYNC_UNAUTHENTICATED` |
| `NOT_IN_TEAMSPACE` | No usable session exists and no connected Teamspace is known. | `SAAS_SYNC_UNAUTHENTICATED` |
| `UNKNOWN` | The local auth authority could not determine session state. | `SAAS_SYNC_AUTH_UNKNOWN` |
| `DISABLED` | SaaS sync is disabled for this invocation. | None |
| `NOT_CHECKED` | Backward-compatible enum member; not a valid setup-plan hosted-enabled verdict. | Treat defensively as unknown if encountered. |

Validation rules:

- Queue scope must not influence classification.
- No classification performs network I/O.
- An exception while acquiring or evaluating the token manager produces `UNKNOWN`.
- Authenticated means refresh-capable according to `TokenManager.is_authenticated`; access-token freshness alone is not the criterion.

## Hosted Sync Diagnostic

Invocation-scoped value added to the setup-plan output envelope.

| Field | Type | Rules |
|---|---|---|
| `code` | string | Stable enum-like value: `SAAS_SYNC_UNAUTHENTICATED`, `SAAS_SYNC_AUTH_UNKNOWN`, or `SAAS_SYNC_BOUNDARY_UNSAFE`. |
| `message` | string | Human-actionable description; must not claim that local verification failed. |
| `remediation` | array of string | Optional safe next steps; authentication is never performed on the user's behalf. |
| `details` | object | Optional machine-readable evidence. Structural diagnostics contain the existing preflight projection. |

Validation rules:

- At most one auth diagnostic is emitted per invocation.
- Auth and structural diagnostics may coexist because they represent different authorities.
- Warning order is deterministic: auth first, structural second.
- Diagnostics never replace the local result or determine process exit status.

## Structural Boundary Verdict

Existing source: `sync.preflight.PreflightResult`.

Relevant evidence includes the six canonical foreground/daemon mismatches, orphan owner records, unreadable owner records, project-store diagnostics, and active legacy event/body-upload row evidence.

For setup-plan, auth classification is projected separately. Structural safety is derived from the structural fields rather than allowing the preflight's legacy `auth_present` calculation to reintroduce queue/target-derived auth authority. Other sync callers retain their existing contract.

## Hosted Side-Effect Decision

| Field | Type | Derivation |
|---|---|---|
| `allowed` | boolean | True only when SaaS is disabled, or when auth is authenticated and the structural boundary is coherent. |
| `diagnostics` | ordered tuple of Hosted Sync Diagnostic | Derived from auth and structural verdicts. |

`allowed=False` suppresses only hosted enqueue/delivery. It does not suppress local reads, validation, artifact writes, lifecycle JSONL events, documentation wiring, or safe commits.

## Local Verification Outcome

Existing setup-plan payload remains authoritative.

| Field | Meaning |
|---|---|
| `result` | Existing local classification such as `success`, `blocked`, or `error`. |
| `phase_complete` | Existing plan-substantiveness result. |
| `blocked_reason` / `error_code` | Existing local reason when applicable. |
| branch and artifact fields | Existing deterministic mission/branch contract. |
| `warnings` | Additive hosted-sync diagnostics; absent or empty when there are none. |

## State Transitions

```text
START
  -> AUTH_CLASSIFIED
  -> BOUNDARY_CLASSIFIED (after repo root is available)
  -> LOCAL_VERIFICATION_COMPLETE
  -> HOSTED_EFFECT_ALLOWED | HOSTED_EFFECT_REFUSED
  -> RESULT_EMITTED
```

Invariant: `RESULT_EMITTED.exit_status == LOCAL_VERIFICATION_COMPLETE.exit_status` for every auth and boundary state.
