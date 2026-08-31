# WP02 review feedback — cycle 3

## Blocking residual invariant: the diagnostic envelope remains caller-controlled

The cycle-3 implementation correctly centralizes and closes the `details` schema: arbitrary reason strings fall back to stable classifications, unknown evidence keys and objects are dropped, known primitive structural classifications survive, and there is no fallback `str(value)` conversion.

However, `HostedSyncDiagnostic.to_dict()` still copies five other public constructor fields verbatim before applying the details gate (`src/specify_cli/cli/commands/agent/setup_plan_hosted.py:118-135`):

- `code`
- `severity`
- `hosted_disposition`
- `message`
- every string in `remediation`

`HostedSyncDecision.to_dict()` delegates directly to that serializer (`:141-147`), so it repeats the same exposure. An executable adversarial probe constructed one exported diagnostic with the sentinel `RuntimeError token=envelope-secret ciphertext=/tmp/envelope.session` in all five fields. The complete sentinel survived in both diagnostic and decision JSON mappings. Unknown diagnostic codes are therefore not fail-closed, and raw exception, token, ciphertext, and filesystem material can still leave the public serialization boundary.

This is the precise residual C-007/FR-012 failure. It also fails the final-cycle requirement to defend unknown codes and both `Diagnostic.to_dict()` and `Decision.to_dict()` surfaces. Sanitizing `details` alone is insufficient because the full diagnostic envelope is untrusted public input.

### Minimal complete remediation

Reconstruct the entire serialized diagnostic from one closed code-to-envelope registry at serialization time. For each of the four allowed codes, the registry must own the stable code, `severity=warning`, `hosted_disposition=refused`, canonical message, canonical remediation, and the code-specific details classifier. Caller-supplied envelope strings must never be emitted.

Unknown codes must fail closed without echoing the unknown value. Because the result-envelope contract permits only four codes, choose one deterministic non-echo behavior at the serializer boundary (for example, omit malformed diagnostics from decision serialization while retaining refusal, or prevent invalid construction and add a defensive decision-level filter). Do not invent a fifth wire code without updating the contract.

Add an adversarial regression that places secret sentinels in every envelope field under both a known and unknown code, then asserts neither diagnostic nor decision serialization contains any caller-provided envelope text. Preserve positive assertions that canonical known-code messages and remediation remain present.

## Verified remediation and gates

- `a4580cc3c` is a tests-only adversarial commit; `ef37f342e` follows with production remediation.
- All prior details paths pass: auth/boundary/route reasons, project-store diagnostics, unknown evidence keys, arbitrary objects, direct details, safe allowlisted classifications, and both details serializers.
- No fallback arbitrary-object string conversion remains.
- `decide_hosted_sync()` remains the sole composition authority; the redundant aggregate collector remains removed.
- Exhaustive 18-row auth × boundary × route truth table and deterministic ordering pass.
- Focused suite: 68 passed, 1 skipped.
- Broader auth/readiness/routing suite: 80 passed.
- Ruff and strict mypy: passed.
- Ownership: `a4580cc3c` and `ef37f342e` modify only WP02's two owned files; canonical preflight and WP01 authority remain untouched.
- No queue-scope reader, hosted sink, transport, migration, repair, or second auth authority is imported.

## Downstream coordination

WP04 depends on WP02 and must wait for the closed full-envelope serializer before consuming these public values.
