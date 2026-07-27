# Boundary Decision: Contract-Conformance Overlap (FR-005)

**Mission**: `ci-local-preflight-parity-01KWXWY0` (#2283 Phase 3)
**Status**: Adjudicated
**Owning requirement**: FR-005 / SC-005

## Context

#2283's original premise named three overlapping "did a retired contract break
something" mechanisms: a **dynamic** review-time gate, a **static**
grep-absence sweep, and the pre-existing `stale_assertions` post-merge
analyzer. Three independently-evolved mechanisms catching slices of the same
failure mode is the over-scope trap this mission is explicitly constrained to
avoid (C-002: ship no 4th detector, no new allowlist artifact). This mission
does not build a mechanism — it adjudicates which existing/incoming mechanism
owns which slice, and files the one durable gap underneath all three.

## Decision

### 1. Factor (c-dynamic) — #2438, CONDITIONAL on merge

**#2438** (`feat(review): auto-scoped review-time regression gate at
move-task --to for_review`, M5's `pre_review_gate.py`) discharges factor
(c-dynamic) — "a consuming test now fails" — by re-running the consuming
shards at `for_review` time.

**This is stated conditionally, not as settled fact**: `pre_review_gate.py`
is **NOT yet on the target branch** (`feat/ci-delivery-topology`) — #2438 is
still an open, unmerged PR at the time of this decision. The correct status
is:

> **(c-dynamic) is delivered-pending-#2438-merge, NOT closed.**

This mission does **not** rebuild `pre_review_gate.py`, does not double
-implement its selection logic (C-003), and does not treat #2438's landing as
guaranteed. Whoever verifies #2283's factor (c-dynamic) closeout after this
mission MUST re-check that #2438 has actually merged to upstream before
treating that clause as discharged.

### 2. Factor (c-static / c′) — owned by CT7 (#2077), sharpened payload

Factor (c-static/c′) — "a production caller still references a retired
contract that NO test exercises" — is a genuine residual that a *test run*
structurally cannot catch (a test run proves the presence of a new failure,
never the absence of a retired symbol). It remains **open** and is owned by
**CT7 (#2077)** ("CT7: Test-hygiene directive/styleguide + recurrence
-prevention guard").

The handoff payload is sharpened here, not left as a vague pointer:

> **Mechanise the `test_no_legacy_*` grep-absence family into a
> content-anchored, allowlist-free retired-contract sweep, triggered on
> shared-contract retirement.**

Today that family (`tests/architectural/test_no_legacy_terminology.py`,
`tests/architectural/test_no_legacy_status_emit_callers.py`,
`tests/audit/test_no_legacy_agent_profiles_path.py`,
`tests/audit/test_no_legacy_path_literals.py`) is four independently
hand-written sweeps, one per retirement, with no shared machinery. CT7's job
is to generalize that pattern into one reusable, content-anchored (never
line-pinned), allowlist-free primitive that fires whenever a shared contract
is retired — not to invent a fifth bespoke sweep here (C-002).

### 3. The durable missing boundary — filed and embedded

Underneath both of the above sits the actual durable gap: **a shared contract
and its retirement are not a modeled, owned artifact with a declared consumer
set.** #2438 (dynamic), `stale_assertions` (post-merge AST analysis), and the
`test_no_legacy_*` family (static grep-absence) are three independently
-scoped point solutions that each rediscover this same underlying absence —
none of them is wrong, but none of them is the durable fix either.

A contract-ownership boundary issue has been filed to track this gap as its
own tracked item, parented under #2283 and #2077:

> **Filed issue**: **[#2441 — Contract-ownership boundary: shared contracts +
> their retirement are not a modeled, owned artifact](https://github.com/Priivacy-ai/spec-kitty/issues/2441)**

This mission ships **no (c) mechanism code and no new allowlist artifact**
(C-002) — the mechanisation is CT7's (#2077), and the ownership-model gap is
#2441's.

## Summary table

| Factor | Mechanism | Status | Owner |
| --- | --- | --- | --- |
| (c-dynamic) | #2438 `pre_review_gate.py` | delivered-pending-#2438-merge, NOT closed | M5 / #2438 |
| (c-static / c′) | `test_no_legacy_*` → mechanised sweep | Open | CT7 (#2077) |
| durable boundary | contract ownership + consumer-set model | Filed | [#2441](https://github.com/Priivacy-ai/spec-kitty/issues/2441) |

## Non-goals (C-002)

This decision record does not introduce, and this mission does not ship:

- A new (c) sweep/grep mechanism.
- A new standalone static-analysis allowlist artifact.
- Any change to `pre_review_gate.py` or #2438.
- Any change to the `test_no_legacy_*` family itself — that mechanisation is
  CT7's, tracked at #2077.
