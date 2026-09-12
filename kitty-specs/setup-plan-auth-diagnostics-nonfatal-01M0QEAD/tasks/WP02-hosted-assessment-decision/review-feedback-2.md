# WP02 review feedback — cycle 2

## Blocking finding: credential-safe serialization is not centralized across public seams

The exact cycle-1 `project_store_diagnostic` leak is fixed: canonical boundary evaluation replaces it with `project_store_unavailable`, and `_boundary_diagnostic()` repeats that classification before decision serialization. However, C-007 and FR-012 govern every public evidence/serialization seam, not only that one canonical dictionary key.

The exported API still copies arbitrary strings or mappings into diagnostic details and then serializes them unchanged:

- `decide_hosted_sync(..., route_reason=<raw>)` reaches `_route_diagnostic()` and `HostedSyncDecision.to_dict()` verbatim (`setup_plan_hosted.py:215-216`, `:266-273`).
- `SessionAssessment.reason` and `BoundaryEvaluation.reason` reach auth/boundary diagnostic details verbatim (`:201-204`, `:212-213`, `:230-263`).
- a noncanonical `BoundaryEvaluation.evidence` key survives `_sanitize_preflight_evidence()` because only `unreadable_owner_record.detail` and top-level `project_store_diagnostic` are classified (`:282-290`).
- direct exported `HostedSyncDiagnostic(..., details=...)` values are recursively stringified by `_plain_json_mapping()` / `_plain_json_value()` (`:66-78`, `:277-301`), including exception/session objects whose string form can contain secrets.

Executable probes using `RuntimeError token=secret ciphertext=/tmp/x` confirmed that raw value survives in `HostedSyncDiagnostic.to_dict()` and `HostedSyncDecision.to_dict()` through all of those paths. These are public WP04-facing values and arguments, so callers cannot be assumed trusted.

### Minimal remediation

Establish one centralized classification/sanitization invariant at the diagnostic serialization boundary and route every diagnostic detail through it. Prefer closed stable reason vocabulary plus an allowlist of permitted evidence fields/primitives; unknown keys, arbitrary objects, exception text, and unrecognized reason strings must be dropped or replaced by a stable classification, never converted with `str(value)`. Ensure both `HostedSyncDiagnostic.to_dict()` and `HostedSyncDecision.to_dict()` enforce the same invariant even when callers construct exported values directly.

Add one parameterized regression that injects exception/token/session/ciphertext sentinels through each exported seam above and proves none appears in either diagnostic or decision serialization. Keep canonical preflight unchanged.

## Verified remediation and gates

- Cycle-1 exact project-store regression: fixed at both boundary evidence and decision serialization seams.
- Red/green ordering: `783eea564` adds the failing leakage regression before `e4b96d48d` applies the fix.
- Redundant `assess_hosted_sync()` aggregate: removed. `decide_hosted_sync()` is the sole composition authority; remaining auth/boundary/route collectors are cohesive and match WP04's phased acquisition order.
- Exhaustive 18-row authenticated/logged-out/auth-unknown × safe/unsafe/unknown boundary × route available/unavailable table: passed.
- Missing requested evidence fails closed; SaaS-disabled decision requires no acquired evidence.
- No queue reader, hosted sink, transport, migration, repair, or direct token-manager authority is imported or invoked.
- Focused suite: 45 passed, 1 skipped.
- Broader auth/readiness/routing suite: 80 passed.
- Ruff and strict mypy: passed.
- Ownership: remediation commits `783eea564` and `e4b96d48d` modify only the two WP02-owned files; canonical preflight and WP01 authority remain untouched.

## Downstream coordination

WP04 depends on WP02. It must wait for the centralized serializer invariant and consume the corrected public values after WP02 re-enters review.
