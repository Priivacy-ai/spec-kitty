---
affected_files: []
cycle_number: 3
mission_slug: assertive-test-suite-sanitation-01KZME3P
reproduction_command:
reviewed_at: '2026-08-10T03:21:56Z'
reviewer_agent: reviewer-renata
wp_id: WP01
---

# WP01 review cycle 3 — changes requested

Cycles 1–2 are substantially repaired. All 62 selftests pass, as do canonical 29,766/37,444/173/365 counts, recursive/deselection/crash probes, valid empty marker/environment records, typed scalar/container checks, non-vacuous family rows, duplicate IDs/edges, finite-number boundaries, malformed aggregation, exact core/sibling workload identities, base validation, hashes, ruff, and mypy strict. One relational evidence hole still permits a fabricated deletion ledger to validate successfully.

**Issue 1 — evidence rows are type-correct containers but can be wholly vacuous.** `_validate_evidence()` at `audit.py:914-948` accepts required `authority_evidence: [{}]` and `routing_evidence: [{}]`; it also accepts malformed nested values such as `routing_evidence: [{route_id: 123}]`. The data model declares command/result, reference/result, RouteMembership/result, and comparison element types, not arbitrary mappings. Validate each evidence-row schema and require meaningful nonempty identity/result fields so `[{}]` cannot satisfy a deletion profile.

**Issue 2 — observations are not reconciled to the census candidate.** `validate_disposition()` at `audit.py:1105-1139` checks that `nodeid` is a string but never checks that it exists in the global census or belongs to the candidate/family. A candidate with a real census member and `nodeid: tests/not-in-census.py::test_fabricated` passes. Reconcile every non-null observation nodeid to a census node and to the candidate's source/family identity; enforce the complementary null/state rules.

**Issue 3 — owner routes are not reconciled to the frozen workload DAG.** `validate_route()` at `audit.py:643-651` validates only shape. `validate_documents()` builds environment and census identity sets but never builds/passes frozen route IDs, so `route_id: does-not-exist` is accepted as the candidate's sole owner route. Build the route authority from the frozen workload and reject unknown candidate/evidence route references.

Combined reproduction: validating the committed base census + committed workload + an inert DELETE shard with a real candidate member, fabricated observation nodeid, nonexistent owner route, and `[{}]` evidence returned `valid: true`, zero errors. This is merge-blocking because it lets later sanitation WPs manufacture proof while satisfying the nominal closure gate.

Anti-pattern checklist: (1) N/A — intentionally mission-local nonproduction module with documented CLI callers; (2) N/A — no permanent FR-tagged tests and runtime selftests call implementation; (3) PASS; (4) FAIL — relational census/route/evidence-row behaviors lack assertions; (5) PASS; (6) FAIL — the disposition-ledger fail-closed and class-specific evidence decisions remain bypassable; (7) PASS; (8) N/A — no production code path added.
