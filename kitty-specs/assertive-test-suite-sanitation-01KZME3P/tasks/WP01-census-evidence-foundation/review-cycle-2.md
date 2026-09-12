---
affected_files: []
cycle_number: 2
mission_slug: assertive-test-suite-sanitation-01KZME3P
reproduction_command:
reviewed_at: '2026-08-10T02:52:08Z'
reviewer_agent: reviewer-renata
wp_id: WP01
---

# WP01 review cycle 2 — changes requested

Cycle-1 census, deselection, collection-crash, canonical-count, causal-KEEP, stale-member, unknown-reference, malformed-aggregate, exact-command, and mypy findings are repaired. Canonical checks now pass at 29,766 source units, 37,444 nodes, and 173 groups/365 members. The remaining blockers were found by new typed-schema and frozen-environment probes.

**Issue 1 — typed validation still accepts invalid ledger records and rejects valid empty collections.** `_required()` at `audit.py:581-584` conflates presence with non-emptiness. Consequently an otherwise valid unmarked observation (`markers: []`) and a valid environment allowlist (`env: {}`) are rejected, despite both matching `data-model.md`. Conversely, `validate_disposition()` at `audit.py:858-1005` returned zero errors for `action: ["delete"]`, `base_evidence: "not-an-object"`, a list-valued `survivor`, list/map-valued HiC approval/issue/owner on `TEMPORARY`, and list-valued family-equivalence dimensions. Replace generic emptiness checks with field-specific presence/cardinality rules and validate every declared scalar/list/map type, including action/survivor, each evidence profile, temporary metadata, and equivalence values.

**Issue 2 — family expansion remains vacuous.** At `audit.py:995-1005`, an observationally divergent family passes with either `node_rows: []` or `node_rows: [{}]`. Merely checking that the field is a list of mappings does not prove node expansion. Require a nonempty, fully typed node row for every divergent member; reconcile node-row identities to candidate members/census nodes and verify every equivalence dimension rather than accepting arbitrary values.

**Issue 3 — workload DAG identity and measurement typing are incomplete.** `validate_documents()` accepts duplicate RunEnvironment IDs. `validate_workload()` at `audit.py:688-721` accepts duplicate dependency edges and a measurement whose collection/setup/call/wall/compute/outcome/artifact fields are all nonempty values of the wrong types. Reject duplicate environment IDs and duplicate edges; deeply validate measurement numbers, outcome enum, SHA-256 artifact, and all route/environment references.

**Issue 4 — sibling E2E frozen environment is factually false.** `base-workloads.yaml:48-59` says the sibling workspace is absent and its lock unobserved. It exists at the prepared sibling checkout, with `uv.lock` SHA-256 `20ba811570bf446830dcf474e38f8c0686c786e043252b8ecd5f74fe1d14e8a7`; local OS/CPU and uv Python resolution are observable. The `install_command` field currently contains the test execution command, not installation/setup. T003 requires exact environment inputs, not transparent placeholders. Record the actual sibling lock, runner/Python/install state and true install command, then recompute the environment/artifact hashes.

Checks passed: independent recursive/nested snapshot; inherited markers; parametrized class selection/deselection; strict duplicate membership; zero root/file; planted `pytest_collection` and `pytest_collection_modifyitems` crash fail-closure; selftest; base validate; ruff; mypy strict; base content proof; raw hashes; canonical counts; exact core full-suite command; duplicate route, unknown environment/edge, stale member, causal KEEP, and malformed aggregate rejection.

Anti-pattern checklist: (1) N/A — intentionally mission-local nonproduction module with documented CLI callers; (2) N/A — no permanent FR-tagged tests, runtime selftest invokes implementation; (3) PASS; (4) FAIL — remaining typed-schema/family/DAG cases have no effective assertion; (5) PASS; (6) FAIL — typed data-model, non-vacuous family expansion, and exact frozen-environment decisions are not enforced; (7) PASS; (8) N/A — no production code path added.
