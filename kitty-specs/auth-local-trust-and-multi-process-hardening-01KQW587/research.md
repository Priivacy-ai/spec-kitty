# Research: Auth Local Trust And Multi-Process Hardening

## Decision: Treat #977 As Hermetic Test Isolation First

**Choice**: Fix refresh-lock concurrency tests so their fake refreshed sessions do not trigger real hosted membership rehydrate when `SPEC_KITTY_SAAS_URL` is configured in the developer shell.

**Rationale**: The known diagnosis says `TokenManager.refresh_if_needed()` calls `_apply_post_refresh_membership_hook()` after refresh, and the fake sessions in `tests/auth/concurrency/test_machine_refresh_lock.py` lack a Private Teamspace. That makes the test accidentally call hosted `/api/v1/me` under inherited hosted URL configuration. The same test passes when the hosted URL is unset.

**Alternatives considered**:

- Change production refresh-lock behavior immediately: rejected because the evidence points to test isolation, not lock algorithm failure.
- Mark the test as hosted smoke: rejected because lock behavior should be hermetic default coverage.
- Clear every hosted env var globally for the whole suite: useful as a guard, but too broad as the only fix because the fixture should model the intended test boundary explicitly.

## Decision: Keep Diagnostic Classification CLI-Owned Initially

**Choice**: Implement #829 and #889 in CLI command/sync/tracker-bound surfaces first, using existing categories where available.

**Rationale**: The visible failure is user-facing classification and guidance. Existing CLI modules already emit `spec-kitty auth login`, direct-ingress warnings, and `server_error` categories. There is no current evidence that `spec-kitty-tracker` owns the classification bug.

**Alternatives considered**:

- Create a tracker mission immediately: rejected because `start-here.md` says tracker is context-only unless ownership is proven.
- Add a new universal auth error enum: rejected unless investigation shows current categories cannot express the required cases.

## Decision: Preserve Existing Direct-Ingress Missing-Private-Team Category

**Choice**: Use the existing `direct_ingress_missing_private_team` style category for Private Teamspace ingress rejection and prevent collapse into `server_error`.

**Rationale**: `src/specify_cli/sync/_team.py` already defines `CATEGORY_MISSING_PRIVATE_TEAM = "direct_ingress_missing_private_team"`, and multiple sync tests already assert the direct-ingress warning/category. The requirement is to classify a 403/missing-private-team path consistently.

**Alternatives considered**:

- Introduce a differently named category: rejected because it would create migration risk and weaken existing tests.
- Treat all 403 responses as auth expired: rejected because missing Private Teamspace is an authorization/domain state, not necessarily an expired login.

## Decision: BLE001 Guardrail Extends Existing Review Direction

**Choice**: Reuse or extract the current BLE001 audit pattern from `src/specify_cli/cli/commands/review.py`, scoped to auth/storage paths, and make it directly testable.

**Rationale**: The repository already treats unjustified BLE001 suppressions as review risk. This mission needs a stronger auth/storage guard, not a new lint ecosystem. The acceptance need is actionable output with file and line.

**Alternatives considered**:

- Rely on ruff alone: rejected because the mission allows broad catches only with an inline safety reason.
- Ban all broad catches in auth/storage: rejected because cleanup and diagnostic-translation boundaries can be legitimate when justified.

## Decision: Hot Path Is Derived, Bounded, And Invalidatable

**Choice**: Any cross-process session hot-path cache or handoff must be derived from durable encrypted storage, invalidated when durable state changes, and safely bypassable.

**Rationale**: The current storage model is encrypted file-only and explicitly excludes Keychain/keyring/Secret Service. The performance issue is repeated local-process work, not lack of durable authority. A derived handoff can reduce work without changing trust authority.

**Alternatives considered**:

- Reintroduce OS credential managers: rejected by spec constraints and current packaging tests.
- Store raw token material in a plaintext cache: rejected because it weakens the local trust model and risks user-output leakage.
- Skip hot-path work entirely: rejected because SaaS #77 explicitly calls for CLI-side cross-process cache/handoff design.

## Decision: Hosted Smoke Remains Explicit

**Choice**: Default tests remain hermetic; any hosted auth/tracker/sync smoke uses explicit command lines and, on this computer, `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.

**Rationale**: The local machine rule exists for hosted testing, but it must not make normal test suites depend on `https://spec-kitty-dev.fly.dev`.

**Alternatives considered**:

- Let all tests use the dev deployment opportunistically: rejected because it caused #977 and makes tests flaky.
- Disable hosted URL configuration in all codepaths: rejected because explicit hosted smoke remains valuable.
