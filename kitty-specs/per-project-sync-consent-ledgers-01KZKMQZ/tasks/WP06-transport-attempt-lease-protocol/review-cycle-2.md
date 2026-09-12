---
affected_files: []
cycle_number: 2
mission_slug: per-project-sync-consent-ledgers-01KZKMQZ
reproduction_command:
reviewed_at: '2026-08-10T17:47:12Z'
reviewer_agent: user
wp_id: WP06
---

# WP06 cycle-2 changes requested

Reviewed authoritative draft PR #3293 product commit `73d61158f` at PR head `9a34bb5ee`, restricted to WP06's five declared files and T026–T030. The cycle-2 remediation closes the five cycle-1 blockers for well-formed inputs, but two acceptance blockers remain.

## 1. Corrupt recovery metadata authorizes an identity-less native query

`plan_delivery_attempt_recovery()` accepts persisted `NATIVE_IDENTITY_QUERY` policy even when `_metadata_from_payload_reference()` yields no original `native_identity`. A standalone production-API corruption probe returned:

```text
corrupt_recovery= query_native_identity native_identity= None may_resend= False
```

This contradicts T027/T030 and Decision 6: a possibly disclosed payload may be queried only with its original native identity. Validate recovery-critical metadata and return `OPERATOR_REVIEW` with `may_resend=False` for missing, malformed, or tuple-inconsistent metadata. Add negative tests for malformed JSON, `{}`, missing identity, corrupt policy, and conflicting identity/authority metadata across recovery states.

## 2. T030 lacks duplicate/refusal proof and the protocol permits contradictory terminal truth for one native identity

The owned suites never exercise `DeliveryOutcome.REFUSED` and contain no duplicate/native-idempotency result path. A direct production-API probe successfully prepared two attempt IDs with the same native identity after terminal refusal and recorded contradictory outcomes:

```text
same_native_identity_terminal_rows=
  [('attempt-1', 'refused', 'refused', 'project_not_admitted'),
   ('attempt-2', 'succeeded', 'delivered', None)]
```

Define and enforce the native-identity idempotency rule so terminal refusal cannot be bypassed with a new attempt ID. Add a refusal test proving original-tuple/category persistence and no retry/promotion, plus a duplicate/native-idempotency test proving one truthful terminal interpretation and original identity across process-death recovery. If remote duplicate is success-equivalent, encode and test that mapping explicitly.

## Evidence and disposition

- Owned suites: 29/29 passed.
- Ruff format/check, strict mypy, workflow validation, `git diff --check`, and declared-file isolation passed.
- Standalone stale-context, cross-project/store-context, corrupted-start-metadata, and invalid-policy probes failed closed; corrupted recovery identity did not.
- Orphan terminalization is private; no raw-UoW public bypass remains.
- Both mission contracts are in scope and require original-identity/truthful recovery.
- Dead code is N/A under the explicit protocol-only staging contract; WP07/WP08 own adapter callers. FR coverage and locked-decision checks fail only for the two blockers above; other anti-pattern checks pass.
- Priivacy-ai/spec-kitty#3309 is open, assigned, and proven pre-WP06 at `14ac8b31`; it is mission-acceptance debt, not a WP06 blocker.
- WP07/WP08 depend on WP06 and must incorporate the next corrected head.
