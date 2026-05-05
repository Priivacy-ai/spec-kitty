# Contract: Hosted Sync And Tracker Diagnostic Classification

## Scope

Applies to CLI command paths that require hosted sync, tracker, Teamspace, or direct-ingress state.

## Categories

| Condition | Category | User guidance |
|---|---|---|
| No active local auth session and hosted state is required | `unauthenticated` | `Run spec-kitty auth login` |
| Local session exists but hosted access is denied because Private Teamspace is missing | `direct_ingress_missing_private_team` or existing direct-ingress peer | Explain Private Teamspace requirement; do not call it server failure |
| Hosted service rejects access for authorization or permission reason | `unauthorized` | Explain access/permission issue without token details |
| Timeout, connection failure, or temporary transport issue | `retryable_transport` | Retry later or check network |
| True 5xx or unexpected hosted server failure | `server_error` | Retry later or check server status |

## Invariants

- Missing Private Teamspace direct ingress never maps to `server_error`.
- Logged-out Teamspace/tracker-bound commands include `spec-kitty auth login`.
- User-facing output and machine-facing classification agree on the broad category.
- Raw tokens, lookup hashes, peppers, family IDs, and audit metadata are never displayed.

## Regression Fixtures

- Logged-out Teamspace-bound repository.
- Tracker-bound repository with no active auth session.
- Direct-ingress 403/missing Private Teamspace.
- Retryable transport failure.
- True hosted 5xx.

## Non-Goals

- Changing SaaS route contracts.
- Changing tracker package contracts unless investigation proves CLI cannot classify correctly without that package change.
