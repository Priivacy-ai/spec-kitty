# Contracts — Mission-Lifecycle Tooling Friction

This mission hardens the spec-kitty mission-lifecycle tooling surfaces
(authoring contract, claim guard, create-time topology, retrospect ingest,
issue-matrix lint, backfill scope). It introduces **no new external/API
contract** — the deliverables are behavioral changes to existing CLI,
doctrine, validator, and migration surfaces.

The binding contracts for this mission are therefore the **executable
acceptance tests** enumerated in `../acceptance-matrix.json`, one per FR:

| FR | Contract (behavioral) | Test |
|----|-----------------------|------|
| FR-001/002/003 | WP-authoring frontmatter contract (repo-relative owned_files; complete template) | `tests/doctrine/test_wp_authoring_contract_roundtrip.py` |
| FR-004/005 | `specify --topology` canonical enum + conditional coord mint + single_branch e2e | `tests/specify_cli/test_specify_topology_flag.py`, `tests/core/test_mission_creation_topology.py` |
| FR-006 | vcs-lock-only claim-guard exclusion (lock-field-only) | `tests/specify_cli/cli/commands/test_implement_vcs_lock_claim.py` |
| FR-007/008 | retrospect traces/*.md ingest + entity-gated data-model gap | `tests/specify_cli/retrospective/test_generator_traces_ingest.py` |
| FR-009 | finalize-tasks advisory issue-matrix lint (one engine, two callers) | `tests/specify_cli/cli/commands/review/test_issue_matrix_finalize_lint.py` |
| FR-010 | `backfill-topology --mission` scope (only target mutated) | `tests/specify_cli/migration/test_backfill_topology_mission_scope.py` |

Negative invariants (`acceptance-matrix.json` → `negative_invariants`) pin the
must-not-happen properties: no `coordination_branch` for single_branch; the
lock exclusion is not a blanket `meta.json` bypass; the issue-matrix lint never
blocks finalize.
