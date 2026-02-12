# Freeze Auth Architecture for 2.x Stabilization Sprint

**Filename:** `2026-02-12-1-freeze-auth-architecture-for-2x-stabilization.md`

**Status:** Accepted

**Date:** 2026-02-12

**Deciders:** Architecture Team, CLI Team, SaaS Team

**Technical Story:** Feature 009 planning and 2.x stabilization scope control.

---

## Context and Problem Statement

The 2.x branch has functional sync/auth infrastructure but known blocking defects in adjacent workflow paths. The immediate goal is to ship a stable 2.x path for:

* offline queueing and replay
* authenticated sync to dev SaaS
* end-to-end spec-plan-implement-review workflow

The risk is scope expansion: introducing an identity-provider migration while core 2.x stabilization defects are still open.

## Decision Drivers

* **P0 defect pressure:** open 2.x workflow blockers must be resolved first.
* **Branch divergence risk:** 2.x is heavily diverged from main; large auth rewrites increase regression risk.
* **Existing capability already present:** SaaS already has allauth + JWT + API-key infrastructure.
* **Time-to-green:** stabilization sprint must optimize for testable closure, not platform re-architecture.

## Considered Options

* **Option 1:** Migrate identity plane now (Auth0) and integration plane now (Nango).
* **Option 2:** Freeze on current auth stack for stabilization; defer platform migration.
* **Option 3:** Build custom OAuth/OIDC + service-account stack in-house during stabilization.

## Decision Outcome

**Chosen option:** **Option 2**.

For this stabilization sprint, SaaS stays on the existing authentication architecture:

* humans: existing Django allauth + SimpleJWT flow
* CI/service auth: existing API-key mechanism with tighter scope semantics

Explicitly out of scope for this sprint:

* Auth0 migration
* Nango rollout
* broad identity/data-model migrations not required for 2.x readiness

### Consequences

#### Positive

* Keeps sprint focused on closing known 2.x defects.
* Reduces migration blast radius during branch-stabilization window.
* Uses already-shipping primitives in `spec-kitty-saas`.

#### Negative

* Defers strategic identity/integration improvements.
* Requires a follow-on migration ADR/plan.

#### Neutral

* Does not prevent adding migration seams now (claims/scope abstraction, reason codes, contract tests).

### Confirmation

This decision is successful when:

1. 2.x stabilization acceptance tests are green for offline + authenticated sync paths.
2. No Auth0/Nango infrastructure changes are merged as part of stabilization scope.
3. A separate post-stabilization migration ADR/roadmap exists (see ADR-3 from this date).

## Pros and Cons of the Options

### Option 1: Migrate to Auth0/Nango now

**Pros:**

* Faster long-term platform direction once complete.
* Earlier consolidation on B2B identity/integration vendors.

**Cons:**

* High implementation surface area during active defect-remediation.
* Increases risk of missing stabilization window.

### Option 2: Freeze auth architecture for stabilization (CHOSEN)

**Pros:**

* Directly aligns with sprint objective: stabilize existing 2.x behavior.
* Minimizes regressions while fixing known defects.

**Cons:**

* Strategic migration remains pending.

### Option 3: Build custom auth stack now

**Pros:**

* Maximum control.

**Cons:**

* Highest delivery risk and slowest path to stabilization.
* Reimplements existing platform capabilities.

## Evidence

### Repository Evidence (Current Stack Exists)

* `spec-kitty-saas/spec_kitty_saas/settings.py` includes allauth, social providers, SimpleJWT, and `rest_framework_api_key`.
* `spec-kitty-saas/spec_kitty_saas/urls.py` exposes `/api/v1/token/`, `/api/v1/token/refresh/`, `/api/v1/ws-token/`, and `/api/v1/events/batch/`.
* `spec-kitty-saas/apps/api/permissions.py` defines `IsAuthenticatedOrHasUserAPIKey`.
* `spec-kitty-saas/apps/api/models.py` has `UserAPIKey(AbstractAPIKey)` for user-associated keys.
* `spec-kitty-saas/apps/users/views.py` exposes API key create/revoke flows.

### Branch/Scope Risk Evidence

Command output captured during planning:

```text
git rev-list --left-right --count main...2.x
308    588

git merge-base main 2.x
033571b9334a4d44e4858abdd9f4fffd6bf5dfa7

git diff --shortstat main..2.x
376 files changed, 65189 insertions(+), 14439 deletions(-)
```

This confirms 2.x is a substantially diverged delivery branch; major auth-plane rewrites during stabilization are high-risk.

### Stabilization Defect Evidence (Still Active)

```text
uv run pytest tests/integration/test_planning_workflow.py::test_setup_plan_in_main -q
FAILED ... {"error": "name 'get_feature_mission_key' is not defined"}
```

An open workflow blocker reinforces the need to avoid non-essential architecture expansion in this sprint.

## More Information

Related:

* ADR-12 (`2026-01-27-12-two-branch-strategy-for-saas-transformation.md`)
* ADR-6 (`2026-02-11-6-pypi-exact-pinning-for-spec-kitty-events.md`)

