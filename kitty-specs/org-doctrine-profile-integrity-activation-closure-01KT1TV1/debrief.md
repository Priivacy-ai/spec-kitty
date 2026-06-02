# Debrief: Source Issues and Mainline Context

This pre-implementation debrief records why this mission slice exists and how it relates to recent mainline work.

---

## Branch Contract

- Current branch at mission creation: `mission/org-doctrine-profile-integrity-activation-closure`
- Planning/base branch: `mission/org-doctrine-profile-integrity-activation-closure`
- Final merge target for this mission: `mission/org-doctrine-profile-integrity-activation-closure`
- Branch matches target: true
- Mission created from upstream `main` after PR #1576 was fetched.

---

## Included Issues

### #1583 - Missing DRG edge relation: `specializes_from` for agent profile inheritance

The compiled DRG relation vocabulary lacks a relation for profile lineage. Org packs need to express that a domain-specific agent profile inherits from a built-in profile. The issue rejects using `delegates_to` because that relation means runtime handoff, not structural inheritance. The mission includes this because activation cascade and diagnostics need accurate graph semantics before relying on org-pack profile relationships.

### #1584 - `AgentProfileRepository.list_all()` silently drops profiles that fail schema validation

An rc30 to rc32 upgrade exposed org-pack profiles that fail the newer schema. The loaded profile list becomes shorter, but callers cannot tell what was skipped after construction. `doctor doctrine` can therefore look healthy while profile files are missing from the resolved catalog. The mission includes this as a prerequisite to trustworthy activation validation.

### #1557 - Charter activation follow-on

PR #1535 shipped the activation layer but explicitly deferred cascade execution, cascade deactivation, artifact ID validation, OperationalContext production wiring, and cleanup findings from adversarial review. This mission includes those items after #1583 and #1584 because activation correctness depends on valid graph relations and visible profile catalog failures.

### #1111 - Parent release epic

The parent epic started as a broader 3.2.0 charter/doctrine launch umbrella. The closed work now establishes lifecycle freshness, shipped DRG freshness, dashboard resilience, org-layer DRG, monorepo visibility, composable workflows, and governance references. This mission is the next closure slice, not a reopening of the whole epic.

---

## Recent Mainline Context

The mission branch starts after these relevant mainline merges:

- #1535 delivered the charter activation layer and documented deferred follow-up scope.
- #1568 improved lane state sync for implement/review orchestration.
- #1570 hardened doctrine trust boundaries, including org doctrine fetch and scope failure behavior.
- #1576 migrated status emits through bookkeeping transactions.

These merges reduce orchestration and doctrine trust-boundary risk, making it reasonable for this mission to focus narrowly on profile integrity and activation correctness.

---

## Explicit Ordering Rationale

The mission order is:

1. Fix graph semantics (#1583).
2. Make profile load failures durable and visible (#1584).
3. Surface profile health through doctor.
4. Finish activation correctness (#1557).

This avoids a flawed dependency chain where activation validation and cascade behavior rely on a catalog that can silently lose profiles or on graph edges that encode inheritance as delegation.

---

## Deferred Items

- #1333 - doctrine template listing and charter-based template resolution. Valuable, but it introduces a new artifact surface and should follow after activation correctness.
- #1040 - ADRs as a first-class primitive. Out of scope except for preserving future compatibility with mission-local decision records.
- #1571 through #1575 - merge/orchestration reliability bugs from the event architecture mission. Relevant to process reliability, but not part of this charter/doctrine profile slice.

---

## Review Notes for Planning

- Treat #1583 and #1584 as acceptance-critical, not opportunistic fixes.
- Add ATDD-style failing tests before implementation WPs for profile lineage validation, retained load diagnostics, doctor JSON diagnostics, unknown activation IDs, cascade activation, cascade deactivation, and OperationalContext guard behavior.
- Keep invalid profiles out of runtime assignment until a future mission defines degraded profile semantics.
- Verify `doctor doctrine` stays a diagnostic command unless a separate product decision changes its exit-code contract.
