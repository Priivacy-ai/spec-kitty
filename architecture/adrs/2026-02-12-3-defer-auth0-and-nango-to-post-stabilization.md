# Defer Auth0 and Nango to Post-Stabilization Migration

**Filename:** `2026-02-12-3-defer-auth0-and-nango-to-post-stabilization.md`

**Status:** Accepted

**Date:** 2026-02-12

**Deciders:** Architecture Team, SaaS Team, Product

**Technical Story:** Strategic platform direction for identity plane and connector integration plane.

---

## Context and Problem Statement

Strategically, the team wants:

* identity plane: externalized, enterprise-ready auth
* integration plane: broad connector network (Jira, Slack, GitHub, and more)

The immediate stabilization sprint, however, is focused on fixing 2.x runtime/auth/sync defects. The question is sequencing, not end-state direction.

## Decision Drivers

* **Strategic fit:** Auth0 + Nango strongly aligns with long-term B2B identity + connector breadth.
* **Sequencing discipline:** stabilization sprint should not absorb platform migration risk.
* **Migration safety:** staged rollout requires compatibility seams and contract tests first.
* **Delivery certainty:** close current readiness gaps before infra replacement.

## Considered Options

* **Option 1:** Execute Auth0 + Nango migration now, inside stabilization sprint.
* **Option 2:** Formally defer Auth0 + Nango to a dedicated migration phase (chosen).
* **Option 3:** Permanently reject external vendors and build/operate all identity+connector layers in-house.

## Decision Outcome

**Chosen option:** **Option 2**.

Post-stabilization target architecture is recorded as:

* **Identity plane target:** Auth0
* **Integration plane target:** Nango

But this is explicitly **deferred** out of stabilization scope. Current sprint only prepares seams:

* reason-coded authz/authn responses
* scope/claim abstraction points
* contract-conformance tests across CLI/SaaS/events

### Consequences

#### Positive

* Preserves long-term direction without destabilizing near-term sprint.
* Reduces chance of mixed partial migrations.
* Enables better migration design after core sync path is stable.

#### Negative

* Strategic benefits of Auth0/Nango are delayed.
* Requires follow-up migration planning and staffing.

#### Neutral

* Existing allauth/simplejwt/API-key stack remains authoritative until migration ADR is accepted and executed.

### Confirmation

This decision is successful when:

1. Stabilization sprint closes without Auth0/Nango runtime dependencies.
2. A follow-on migration feature/ADR defines phased rollout and cutover.
3. Migration starts only after stabilization acceptance criteria are met.

## Pros and Cons of the Options

### Option 1: Migrate now

**Pros:**

* Earliest possible strategic alignment.

**Cons:**

* High scope expansion risk during critical stabilization window.
* Hard to isolate regressions (stabilization vs migration effects).

### Option 2: Defer to dedicated phase (CHOSEN)

**Pros:**

* Maintains stabilization focus.
* Still records clear strategic direction.
* Enables cleaner migration test gates later.

**Cons:**

* Delayed realization of platform benefits.

### Option 3: Build everything in-house

**Pros:**

* Full customization/control.

**Cons:**

* Slowest path; highest operational burden and maintenance cost.
* Distracts from product delivery.

## Evidence

### External Product/Platform Evidence (reviewed 2026-02-12)

* Auth0 documents OAuth2 Client Credentials for machine-to-machine access:
  * https://dev.auth0.com/docs/get-started/authentication-and-authorization-flow/client-credentials-flow
* Auth0 Organizations documents org-scoped login patterns for B2B:
  * https://dev.auth0.com/docs/manage-users/organizations/login-flows-for-organizations
* Nango provides prebuilt API integration catalog and auth/token lifecycle tooling:
  * https://nango.dev/api-integrations
  * https://nango.dev/docs/guides/use-cases/api-auth
* Clerk machine-auth docs (at review time) indicate OAuth2 `client_credentials` for OAuth access tokens is not yet supported:
  * https://clerk.com/docs/guides/development/machine-auth/overview

### Local Repository Evidence (Current State)

* Current SaaS auth stack is allauth + SimpleJWT + API keys:
  * `spec-kitty-saas/spec_kitty_saas/settings.py`
* Sync endpoints and JWT issuance already exist:
  * `spec-kitty-saas/spec_kitty_saas/urls.py`
* API-key permission path is already integrated:
  * `spec-kitty-saas/apps/api/permissions.py`
  * `spec-kitty-saas/apps/api/models.py`

### Stabilization Pressure Evidence

* 2.x remains materially diverged from main:
  * `main...2.x` count: `308` (main side) / `588` (2.x side)
  * shortstat: `376 files changed, 65189 insertions(+), 14439 deletions(-)`
* Active P0 workflow failure remains in 2.x:
  * `test_setup_plan_in_main` fails with `name 'get_feature_mission_key' is not defined`

These signals support sequencing migration after stabilization, not during it.

## More Information

This ADR is a sequencing decision. It does not supersede the strategic recommendation to adopt Auth0 and Nango; it defers execution until after stabilization completion.

