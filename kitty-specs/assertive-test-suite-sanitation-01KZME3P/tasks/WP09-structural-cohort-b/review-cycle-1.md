---
affected_files: []
cycle_number: 1
mission_slug: assertive-test-suite-sanitation-01KZME3P
reproduction_command:
reviewed_at: '2026-08-10T16:44:28Z'
reviewer_agent: reviewer-renata
wp_id: WP09
---

# WP09 review cycle 1 — changes requested

## Blocker 1 — baseline node accounting joins the wrong census table

`wp09-results.json.node_accounting.base_nodeids_ref` and `WP09.yaml.base_census.exact_nodeids` say `collection.nodes[].path_ref` maps through top-level `test_files`. In the frozen `test-sanitation/v1` census, `path_ref` indexes `collection.tables.paths`; top-level `test_files` is a different source-file inventory. Reproducing WP09 ownership with the authoritative table yields **418** baseline nodes, not 504. With the independently collected 35 survivors, the net reduction is **383**, not 469.

This is not a cosmetic total. Per-file counts and the rule-derived deleted identities are cross-file data. Examples: `test_arch_pole_deserialized.py` claims 39 but has 2 frozen-base nodes; `test_ci_collection_completeness.py` claims 7 but has 46; `test_gate_coverage.py` claims 7 but has 37; `test_push_preflight.py` claims 21 but has 20.

Regenerate both evidence artifacts from `collection.tables.paths`, correct every baseline/current/delta summary, and make the exact removed-node derivation schema-correct. Add or run a fail-closed reconciliation that proves the 37 owned paths, their frozen-base node sets, the 35 current nodes, and the arithmetic.

## Blocker 2 — wrong join masks required node-level deletion adjudication

FR-003/FR-014/NFR-002/NFR-007 require materially divergent members to expand to exact node-level or valid same-path/same-authority/same-corpus/same-oracle/same-fault families. Current file-level rows cannot establish that because their base membership is wrong. For example, `test_gate_coverage.py` is classified wholesale as seven “scanner implementation tests,” while its actual 37-node frozen-base set includes live workflow guards such as the Windows route model and cross-job selection checks.

Reconcile the actual nodeids and explicitly map each deleted live guard either to a current authority-violating equivalent survivor/fault proof or to a deletion rationale showing no current authority/unique boundary. Preserve the deletion patch unless this corrected audit proves a unique guard. Reviewer sampling confirmed the retained collection oracle does catch a realistic Windows-marker route fault (23 Windows nodes orphaned), so that specific guard can be documented as equivalent rather than restored.

## Evidence already green

- 26 files deleted; no production, workflow, or shared shard-map edits.
- Current retained cohort: 35 passed.
- Ruff: clean. Focused mypy: clean.
- Workflow, collection, shard, resolver, push-safety, and residue fault families visibly reach intended assertions; the correction requested above is evidence identity/classification, not a request to expand the suite.

## WP anti-pattern checklist

1. Dead code: N/A — no production API/module added.
2. Synthetic-fixture test: PASS — sampled survivors exercise live workflow, collection, git, and artifact-partition paths.
3. Silent empty return: N/A — no production path added.
4. FR coverage: **FAIL** — exact FR-003/FR-014/NFR-002/NFR-007 membership evidence is invalid due to the wrong path table.
5. Frozen surface: PASS.
6. Locked decision: PASS.
7. Shared-file ownership: PASS — implementation edits stay within WP09-owned files/evidence.
8. Production fragility: N/A — no production `raise` added.
