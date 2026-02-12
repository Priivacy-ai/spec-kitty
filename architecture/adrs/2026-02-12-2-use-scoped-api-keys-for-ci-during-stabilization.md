# Use Scoped API Keys for CI During Stabilization

**Filename:** `2026-02-12-2-use-scoped-api-keys-for-ci-during-stabilization.md`

**Status:** Accepted

**Date:** 2026-02-12

**Deciders:** Architecture Team, SaaS Team

**Technical Story:** Feature 009 service authentication choice for stabilization sprint.

---

## Context and Problem Statement

The sprint requires service/automation authentication for CLI sync and CI jobs, but full OAuth client-credentials service accounts are not needed to close current P0 stabilization gaps.

We already have an operational API-key path in SaaS, including model, permission integration, and UI lifecycle operations. The decision is whether to use that path now or introduce OAuth M2M service-account flows in this sprint.

## Decision Drivers

* **Reuse existing capabilities:** avoid introducing a second auth stack mid-sprint.
* **Low migration cost:** API-key path already integrated with DRF permissions.
* **Operational simplicity:** immediate compatibility with CI secret storage.
* **Incremental hardening:** add scope and team constraints without auth-plane migration.

## Considered Options

* **Option 1:** OAuth2 Client Credentials service accounts now.
* **Option 2:** Scoped API keys now; defer OAuth M2M service accounts.
* **Option 3:** No machine auth in sprint (humans only).

## Decision Outcome

**Chosen option:** **Option 2**.

For stabilization:

* CI/service auth uses API keys.
* API keys must be constrained by:
  * team/org membership checks
  * explicit scopes (minimum required for sync endpoints)
  * reason-coded 401/403 responses

Deferred:

* OAuth2 client-credentials service-account rollout
* external IdP-backed machine identities

### Consequences

#### Positive

* Immediate implementation path using existing models and permission classes.
* Low-risk for stabilization schedule.
* Clear bridge to later service-account migration.

#### Negative

* API keys are an interim machine-auth mechanism, not final identity-plane architecture.
* Requires careful scope/revocation discipline.

#### Neutral

* Token format remains bearer-based; downstream CLI behavior unchanged.

### Confirmation

This decision is validated when:

1. CI can authenticate sync endpoints via API keys.
2. Unauthorized/mis-scoped keys return deterministic reason-coded 401/403 responses.
3. Human JWT flows continue to function unchanged.

## Pros and Cons of the Options

### Option 1: OAuth2 client credentials now

**Pros:**

* Standards-aligned machine identity model.
* Better long-term parity with external IdPs.

**Cons:**

* Non-trivial implementation and migration during stabilization.
* Expands test matrix and rollout risk.

### Option 2: Scoped API keys now (CHOSEN)

**Pros:**

* Already implemented in core SaaS auth path.
* Fastest path to secure machine auth for current sprint.
* Minimal refactor surface.

**Cons:**

* Interim architecture; full service-account model deferred.

### Option 3: Human-only auth

**Pros:**

* Simplest implementation.

**Cons:**

* Blocks CI/service use cases explicitly required by feature scope.

## Evidence

### Existing API-Key Infrastructure

* `spec-kitty-saas/spec_kitty_saas/settings.py` includes `rest_framework_api_key` and sets DRF default permission to `apps.api.permissions.IsAuthenticatedOrHasUserAPIKey`.
* `spec-kitty-saas/apps/api/models.py`:
  * `UserAPIKey(AbstractAPIKey)` exists today.
* `spec-kitty-saas/apps/api/permissions.py`:
  * `HasUserAPIKey` and hybrid `IsAuthenticatedOrHasUserAPIKey` are implemented.
* `spec-kitty-saas/apps/users/views.py`:
  * `create_api_key` and `revoke_api_key` endpoints exist.
* `spec-kitty-saas/templates/account/components/api_keys.html`:
  * user-facing key management UI exists.

### Existing JWT/Human Path (Unaffected)

* `spec-kitty-saas/spec_kitty_saas/urls.py` exposes `/api/v1/token/` and `/api/v1/token/refresh/`.
* `spec-kitty-saas/spec_kitty_saas/settings.py` configures `rest_framework_simplejwt.authentication.JWTAuthentication`.

## More Information

This ADR intentionally optimizes stabilization delivery. It does not reject OAuth2 service accounts; it sequences them after stabilization (see ADR-3 from 2026-02-12).

