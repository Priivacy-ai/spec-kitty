---
affected_files:
  - tests/architectural/test_ci_collection_completeness.py
  - docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP09.yaml
  - docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp09-results.json
cycle_number: 2
mission_slug: assertive-test-suite-sanitation-01KZME3P
reproduction_command: rg -n -i 'cross-job disjointness|orphan-sweep.*parallel pool|no double-run' docs/plans/testing/ci-coverage-union-audit.md kitty-specs/ci-test-topology-performance-01KXBJRT/contracts/guard-contracts.md kitty-specs/ci-test-topology-performance-01KXBJRT/spec.md
reviewed_at: '2026-08-10T19:35:00+02:00'
reviewer_agent: reviewer-renata
wp_id: WP09
---

# WP09 review cycle 2 — changes requested

## Blocker — cross-job disjointness has a current authority and no surviving oracle

The cycle-2 evidence classifies three frozen identities as
`cross-job-no-boundary` and states that no exclusivity authority exists. That
premise is contradicted by repository authorities that remain active and have
no retirement decision:

- `kitty-specs/ci-test-topology-performance-01KXBJRT/contracts/guard-contracts.md`
  defines GC-2 cross-job disjointness: the serial orphan-sweep selection and
  parallel pool selection must have an empty intersection.
- The same mission's `spec.md` requires zero double-run in Scenario 2,
  FR-004, FR-007, NFR-005, C-007, and SC-005.
- `docs/plans/testing/ci-coverage-union-audit.md` names
  `test_orphan_sweep_and_sync_pool_are_disjoint_today` as the live-current
  guard and documents its realistic fault: removing the pool `--ignore`
  makes `test_orphan_sweep.py` run twice.

After this WP, `cross_job_disjoint_selection` has zero callers and the retained
zero-orphan collection oracle cannot detect duplicate execution. Therefore the
live topology member has a distinct current boundary and its deletion violates
FR-003, FR-007, FR-014, NFR-002, and NFR-007.

Restore/rehome only the minimal real-topology disjointness assertion; the pure
helper self-test and report-only generic duplicate check need not return. Give
the survivor a two-sided controlled fault that removes the actual pool ignore
in a disposable workflow copy, proving healthy topology green and duplicate
selection red. Then remap the three frozen identities by outcome/family and
update exact current/delta totals. Preserve all other cycle-2 deletions.

## Evidence independently verified green

- Correct census join: `collection.nodes[*][1] -> collection.tables.paths`.
- Exact sets: 37 owned test paths, 418 unique frozen nodes, 35 unique current
  nodes, 418 unique terminal mappings; current net reduction 383.
- Windows route equivalence is valid: an independent `windows_ci` marker fault
  reached the retained collection assertion and orphaned all 30 current Windows
  nodes.
- Focused cohort: 35 passed in 180.55s; collection: 35 in 43.25s.
- Ruff clean; mypy clean for 11 changed surviving source files; diff clean.
- No production, workflow, shared shard-map, skip, xfail, quarantine, or flaky
  changes.

## WP anti-pattern checklist

1. Dead code: **FAIL** — `cross_job_disjoint_selection` now has zero callers.
2. Synthetic-fixture test: PASS — sampled survivors use live workflow, test,
   git, source, and residue corpora.
3. Silent empty return: N/A — no production path added.
4. FR coverage: **FAIL** — deletion of the distinct cross-job boundary violates
   the cited FR/NFR coverage requirements.
5. Frozen surface: PASS — no workflow, production, or shared-map edit.
6. Locked decision: **FAIL** — the no-authority conclusion contradicts the
   committed GC-2/C-007 zero-double-run contract.
7. Shared-file ownership: PASS — implementation edits remain WP09-owned.
8. Production fragility: N/A — no production `raise` added.
