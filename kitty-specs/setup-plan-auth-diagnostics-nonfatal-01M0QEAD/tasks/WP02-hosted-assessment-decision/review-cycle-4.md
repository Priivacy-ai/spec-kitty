---
affected_files: []
cycle_number: 4
mission_slug: setup-plan-auth-diagnostics-nonfatal-01M0QEAD
reproduction_command:
reviewed_at: '2026-08-23T20:30:00Z'
reviewer_agent: user
wp_id: WP02
---

# WP02 post-arbiter review feedback

## Blocking proof gap: the exact four-entry runtime registry is not asserted

Runtime behavior satisfies the arbiter's security and decision invariants, and manual inspection confirms `_DIAGNOSTIC_REGISTRY` currently has exactly the four contract codes. However, `test_wire_registry_contains_exactly_four_codes()` is self-referential: it constructs diagnostics only from `_WIRE_REGISTRY_EXPECTATIONS` and then compares the serialized subset back to that same test-side mapping. It never reads or compares the runtime registry.

Adding a fifth entry to `_DIAGNOSTIC_REGISTRY` would therefore leave the test green. This does not prove the arbiter's binding “exactly four registry entries” acceptance check or the result-envelope contract's closed allowed-code set.

### Minimal remediation

Add one direct equality assertion between the runtime registry key set and the test-side expected four-code set, for example conceptually:

```python
assert set(setup_plan_hosted._DIAGNOSTIC_REGISTRY) == set(_WIRE_REGISTRY_EXPECTATIONS)
```

Use the repository's preferred narrowly justified private-access approach, or expose an immutable canonical code-set view if that is the established convention. The essential requirement is equality against the runtime source of truth, not reconstruction from the test-side set.

## All other arbiter checks passed

- Runtime registry currently contains exactly four immutable entries.
- Complete envelope fields are reconstructed from the registry; caller sentinels in code, severity, disposition, message, remediation, details, unknown keys, and arbitrary objects do not survive diagnostic or decision serialization.
- Unknown diagnostic code construction raises a fixed non-echoing error.
- `allow_effects=True` plus diagnostics is rejected without echoing input.
- No fifth code or malformed diagnostic can be silently omitted into an allowing decision at runtime.
- Canonical messages and remedies are retained for all four codes.
- SaaS-disabled decisions and sole `decide_hosted_sync()` authority remain unchanged.
- ATDD ordering: `fe432e1b3` is tests-only; `a7a9525c2` provides the implementation.
- Focused suite: 51 passed.
- Expanded preflight bundle: 82 passed, 1 skipped.
- Broader auth/readiness/routing suite: 80 passed.
- Ruff and strict mypy: passed.
- Ownership/frozen surfaces/forbidden imports: passed; only the two WP02-owned files changed.

WP04 depends on WP02 and must wait for this final non-vacuous registry-cardinality guard.
