# Mission E (#3008/#3147) — pre-spec corpus research (captured 2026-08-10, E paused)

## #3008 — TWO gates hide corpus regressions:
- **Gate 0 (DECISIVE):** ci-quality.yml `pull_request.paths` (:14-30) AND `push.paths` (:44-66)
  allowlists OMIT `packs/**`, `kitty-specs/**`, most `.kittify/**`. A data-only PR NEVER TRIGGERS
  the workflow — pre- AND post-merge (push hole). Must fix triggers FIRST.
- **Gate 1:** no dorny group (:200-476) for packs/kitty-specs; `unmatched` catch-all is src-only (:475-535).
- Covered already: `docs/**`→fast-tests-docs; `src/doctrine/**`→doctrine/core_misc/missions (both in allowlist).
- Highest-risk bucket: `packs/built-in/**` (SHIPPED wheel data, pyproject :179-186) — ~60 tests read it
  (tests/doctrine/** via load_built_in_graph + conftest fixtures; architectural; missions; charter; contract/glossary), NONE run on packs-only PR.
- kitty-specs readers (narrow!): test_wp_owned_files_no_kitty_specs, test_no_tracked_test_feature_missions,
  test_events_tracker_public_imports, test_verdict_seam_census, contract/test_example_round_trip,
  charter/synthesizer/test_manifest, integration/test_mission_review_contract_gate.

### Recommended fix (2 edits):
1. Add to BOTH pull_request.paths + push.paths: `packs/**`, `kitty-specs/**/{spec.md,plan.md,tasks/**,contracts/**,acceptance-matrix.json}`
   (NARROW — exclude status.events.jsonl churn!), `.kittify/{charter,glossaries,doctrine,skills}/**`, `.kittify/release/downstream-verified.json`.
2. **Cheaper (recommended):** ONE `corpus-tests` job modeled on fast-tests-docs (:1808-1833), gated `corpus || push`,
   running `tests/doctrine tests/missions tests/specify_cli/missions tests/charter tests/architectural tests/contract tests/glossary tests/docs -m "not windows_ci"`. Avoids fanning ~9 heavy jobs.
   Add `corpus` group to changes.outputs (:162-191). arch-adversarial needs no edit (always() once triggered).
- False-trigger risk: whole kitty-specs/** fires on nearly every PR (status churn) → MUST narrow globs.
- Governing arch invariants that must co-evolve: tests/architectural/test_ci_quality_path_filters.py,
  test_ci_collection_completeness.py, ci_topology_census.json. Prior art: doctrine-charter-tests.yml (WP07 path-filtered).

## #3147 — docs dead-link gate over-fires whole-tree; scope BLOCKING check to PR diff, whole-tree → nightly/full-run boolean.
  (docs-freshness.yml PR paths :34-45; whole-tree link scan currently only via push:main backstop :46-47.)

## Operator decisions (E): corpus gate BLOCKING; whole-tree #3147 nightly/full-run via CI boolean; corpus scope = squad-enumerated (this).
