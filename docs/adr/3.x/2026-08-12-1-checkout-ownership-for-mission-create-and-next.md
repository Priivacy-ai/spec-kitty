---
title: 'ADR: Explicit Checkout Ownership for Mission Create and Next'
description: 'Introduces a fail-closed, Git-topology-validated ownership claim so mission create and next can use an exact linked-checkout root without ambient primary fallback.'
status: Accepted
date: '2026-08-12'
---

## Context and Problem Statement

`spec-kitty agent mission create` historically refuses invocation from a linked
worktree. `spec-kitty next` either refuses paths recognized by its `.worktrees`
guard or collapses a generic linked worktree to the repository-root checkout.
Removing those guards would not make worktree operation safe: ambient project-root
discovery would still let mission content, refs, or runtime state cross into the
repository-root checkout.

This is the narrow mitigation identified by [#3129]: commands need an explicit
write boundary before the broader scoped-shadow-workspace design is attempted.
It also supplies a prerequisite for [#3128]. This decision establishes an owned
checkout before or while mission identity is becoming readable; #3128 remains
responsible for making later mission-mutating commands compare their caller with
the workspace already declared by a mission.

The detailed domain vocabulary and observable CLI contract remain canonical in
the mission's [data model] and [checkout-ownership CLI contract]. This ADR records
why the boundary exists and which authority is allowed to establish it.

## Decision Drivers

- Preserve the fail-closed behavior of every caller that does not opt in.
- Accept only an exact Git checkout root belonging to the expected common
  repository; a checkout subdirectory must never self-certify.
- Keep the owned root explicit through mission-content, runtime-state, ref, and
  commit decisions instead of rediscovering it from CWD.
- Recognize generic linked-worktree paths, not only a `.worktrees/` convention.
- Keep production `allow_worktree_context=True` unavailable as an authorization
  mechanism.
- Prove isolation with an immutable installed CLI artifact, not an editable
  install or a mocked command.

## Decision

### One explicit ownership primitive

Adopt `OwnershipClaim` and `OwnershipValidationResult` in
`specify_cli.core.checkout_ownership` as the single validation authority shared
by `mission create` and `next`.

An opted-in claim contains the exact claimed checkout root, an independently
resolved repository-root checkout, and one structured result: `OWNED`,
`NESTED`, `FOREIGN_OR_MISMATCHED`, or `BROKEN_POINTER`. Omitting the opt-in
produces `UNOWNED_NO_OPT_IN` and retains the existing command behavior.

Validation reuses the fail-closed common-directory comparator used by
`safe_commit`, confirms that the claim is the Git toplevel rather than a
subdirectory, and consults `git worktree list --porcelain` for generic registry
membership and nested-root checks. Git probe failures are refusals; they do not
activate a fallback.

### A narrow CLI affordance

Expose `--owned-checkout PATH` only on:

- `spec-kitty agent mission create`; and
- `spec-kitty next`.

The option names an exact checkout root for that invocation. It is not inferred
from CWD, environment variables, path naming, or the nearest `.kittify`
directory. Structured refusals distinguish nested, foreign/mismatched, broken
pointer, and no-opt-in cases.

An owned `mission create` uses the validated checkout as its content and ref
boundary. During the short interval before mission identity is readable,
`resolve_create_time_write_target(planning_branch)` carries the already-derived
short planning branch into a `CommitTarget`. That pure seam performs no CWD,
environment, topology, mission-directory, or ambient-root discovery. Ordinary
post-identity writes continue through the existing placement authority.

An owned `next` threads the validated effective root through command, decision,
runtime bridge, mission-context resolution, and owned-mutation persistence.
Mission content and per-checkout runtime state resolve from that same root even
when the command is launched from the repository-root checkout. No opted-in
layer may replace it with `get_main_repo_root` or another ambient resolver.

### Isolation and contention boundaries

The owned checkout receives its mission content, per-checkout runtime state,
mission refs, and command-produced commits. The repository-root checkout and
sibling linked worktrees receive none of those writes.

Git's worktree registry remains a shared Git resource. Coordination-worktree
materialization therefore permits a bounded retry only for positive, recognized
registry-contention evidence. Permission failures and unrelated or permanent
errors re-raise unchanged; the retry does not introduce a persistent lock.
The existing shared status lock, which serializes intentionally convergent
planning writes through the common Git directory, is not reclassified as
per-checkout state.

## Consequences

### Positive

- Accidental ambient primary fallback is no longer an authorization path for
  opted-in mission creation or advancement.
- The same structured claim and refusal taxonomy govern both CLI surfaces.
- Generic linked worktrees work without weakening the legacy default guards.
- #3128 can consume a validated ownership fact instead of inventing another Git
  topology comparator.

### Negative and accepted trade-offs

- Explicit-root propagation adds parameters across the `next` decision and
  runtime-bridge layers; this duplication is intentional because rediscovery
  would erase the security boundary.
- Concurrent missions still contend briefly on Git's shared worktree registry.
  The bounded, signature-specific retry treats that Git implementation detail
  without pretending the object store and refs are physically separate.
- This decision does not deliver the scoped-handle/shadow-workspace redesign in
  #3129 and does not complete #3128's caller-versus-declared-workspace guard.

### Verification and CI follow-up

Acceptance for #3328 is the real installed-wheel test
`tests/e2e/test_worktree_owned_root_concurrency.py`: an immutable wheel drives
two actual linked worktrees concurrently and proves distinct mission identity,
content roots, refs, runtime state, lock cleanup, and clean repository-root/A/B
checkouts. The reviewed local 20-iteration run is the authoritative #3328
mission proof until [#3343] lands; it does not claim CI coverage or override the
mainline release gate.

#3343 owns the missing CI selection contract. Its job must positively select
this file, build and run a non-editable immutable wheel, publish source-commit
and wheel-SHA provenance plus JUnit evidence, and make trigger, timeout,
quality-gate dependency, coverage-consumer, and collection-completeness behavior
explicit. Existing broad jobs must not silently exclude the proof or duplicate
unrelated distribution suites.

## Alternatives Considered

### Reuse or loosen `allow_worktree_context`

Rejected. That parameter is a test/programmatic compatibility escape hatch, not
a Git-topology ownership claim. Promoting it to production authorization would
bypass the exact invariant this decision adds.

### Extend the `.worktrees`-literal execution-context guard

Rejected. Directory naming cannot prove common-repository membership, exact
checkout-root identity, or ownership for a generic linked worktree. It also does
not solve the separate pre-identity `mission create` boundary.

### Infer the owned root from ambient project discovery

Rejected. Ambient discovery currently collapses linked worktrees to the
repository-root checkout. Treating that result as authority would preserve the
cross-write defect while making it harder to observe.

### Adopt scoped shadow workspaces now

Deferred to #3129. A capability-scoped handle is the stronger structural end
state, but it is a broader execution-model decision. Explicit validated
ownership is the independently useful, fail-closed prerequisite.

## References

- Core issue: [#3328]
- Caller/workspace mismatch follow-up: [#3128]
- Scoped shadow-workspace design: [#3129]
- Immutable-install and stale-worktree hazard: [#1907]
- CI selection follow-up: [#3343]
- Related decision: [Execution Lanes Own Worktrees and Mission Branches]
- Related decision: [`ExecutionContext` Owner and `CommitTarget` Atomicity]

[data model]: ../../../kitty-specs/worktree-owned-root-3328-01KZRG01/data-model.md
[checkout-ownership CLI contract]: ../../../kitty-specs/worktree-owned-root-3328-01KZRG01/contracts/checkout-ownership-cli-contract.md
[#1907]: https://github.com/Priivacy-ai/spec-kitty/issues/1907
[#3128]: https://github.com/Priivacy-ai/spec-kitty/issues/3128
[#3129]: https://github.com/Priivacy-ai/spec-kitty/issues/3129
[#3328]: https://github.com/Priivacy-ai/spec-kitty/issues/3328
[#3343]: https://github.com/Priivacy-ai/spec-kitty/issues/3343
[Execution Lanes Own Worktrees and Mission Branches]: ./2026-04-03-1-execution-lanes-own-worktrees-and-mission-branches.md
[`ExecutionContext` Owner and `CommitTarget` Atomicity]: ./2026-06-03-2-executioncontext-owner-and-committarget.md
