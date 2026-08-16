---
affected_files: []
cycle_number: 3
mission_slug: per-project-sync-consent-ledgers-01KZKMQZ
reproduction_command:
reviewed_at: '2026-08-10T18:12:25Z'
reviewer_agent: user
wp_id: WP06
---

# WP06 cycle-3 changes requested

Reviewed authoritative draft PR #3293 semantic product commit `0a2f2d534` at submitted head `9216b7362`, restricted to WP06's five declared files and T026–T030. The cycle-3 remediation correctly reserves native identities per project by `(write_kind, native_identity)`, blocks same-attempt mutations before SQLite, preserves cross-project independence, represents a duplicate as terminal idempotent success, and inverts the cycle-2 refused-then-fresh-delivered reproduction. Two product blockers and one runtime-status gate remain.

## 1. Typed malformed recovery metadata still authorizes automatic native recovery

`_metadata_from_payload_reference()` coerces every non-null JSON value with `str(item)`, and `_metadata_required_identity_diagnostic()` then checks only that the resulting strings are non-empty. Direct production-API probes mutated otherwise durable in-flight metadata to JSON arrays/objects and received automatic native-query decisions:

```text
malformed native_identity => query_native_identity '[]'
malformed write_kind => query_native_identity 'operation-key:abc'
malformed payload_reference => query_native_identity 'operation-key:abc'
```

This violates T027/T030 and cycle-2's requirement that malformed recovery metadata fail closed. Parse and validate the persisted metadata schema without coercing arrays, objects, booleans, or numbers into identities. Require scalar strings of the expected shape for recovery-critical fields and return `OPERATOR_REVIEW`, `may_resend=False` for every invalid type. Add parametrized negative tests for non-string native identity, write kind, payload reference, generations, audience, deadline, and policy across prepared/in-flight/unknown states.

## 2. REFUSED does not require a terminal refusal category

`record_delivery_result()` accepts `DeliveryOutcome.REFUSED` while `terminal_refusal_category` remains optional. A direct production-API probe persisted:

```text
refused_without_category => accepted ('refused', None)
```

T030 and the data model require truthful terminal refusal evidence. Enforce a non-empty refusal category for `REFUSED`, reject refusal categories on `DELIVERED`/`DUPLICATE`, and add negative tests for both directions. Retain the passing positive proof that refusal stores the original epoch/target/admission tuple and cannot recover, retry, promote, or reuse its scoped native identity.

## 3. Canonical status validation is not green

`SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty agent status validate --mission per-project-sync-consent-ledgers-01KZKMQZ` reports:

```text
Event 01KZPA9EPJHSXDY418DDBY27R7: for_review->in_progress without review_ref
Event 01KZPCVC02FG2GC0Z2CGZ6Z83T: for_review->in_progress without review_ref
```

Repair this through the supported runtime-owned status-history path; do not rewrite the append-only event log ad hoc. This is bookkeeping/runtime evidence, not a product-source defect, but the requested status gate must pass before the next approval.

## Passing evidence and disposition

- Owned suites: 40/40 passed, including the unchanged real lease, authority, kill-switch, opt-out, deadline, subprocess-death, and five-window/compound recovery proofs.
- Ruff format/check, strict mypy, `git diff --check`, clean worktree, and declared-file isolation passed.
- Same scoped identity with changed payload hash/reference is blocked; same attempt ID with changed write kind/native identity/hash/reference raises `ProjectStoreError` before SQLite; unreadable existing identity metadata blocks fresh attempts.
- The deliberate scope allows the same native identity for different write kinds and across projects; both direct probes passed.
- Duplicate is terminal success and post-terminal result recording is blocked. The refused-then-fresh-delivered cycle-2 reproduction is now blocked.
- Contract round-trip: both mission contracts are in scope. The malformed-metadata and refusal-category findings fail truthful original-identity/result evidence; other WP06 contract checks pass.
- Anti-patterns: dead code N/A under the explicit protocol-only staging contract (WP07/WP08 own adapter callers); synthetic fixtures PASS; silent empty returns PASS; FR coverage FAIL only for the two product blockers; frozen surface PASS; locked decisions FAIL only for those blockers; shared-file ownership PASS; production fragility PASS because the new raises are deliberate fail-closed protocol boundaries.
- Priivacy-ai/spec-kitty#3309 remains open, assigned, and proven pre-WP06 at `14ac8b31`; it is mission-acceptance debt, not a WP06 blocker.
- WP07/WP08 depend on WP06 and must incorporate the next corrected head.
