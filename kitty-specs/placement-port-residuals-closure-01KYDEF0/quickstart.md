# Quickstart — Placement-Port Residuals Closure

How to drive each red-first repro through its pre-existing entry point, and how
to verify the corpus + gates. Run from the repo root.

## Part C — the six already-red gates (baseline: RED on the merge-base)

```bash
PWHEADLESS=1 python -m pytest -q -p no:cacheprovider \
  "tests/architectural/test_no_write_side_rederivation.py::test_adopted_and_residual_modules_have_no_checkout_derived_commit_target" \
  "tests/architectural/test_guard_capability_call_sites.py::test_protected_flow_capability_call_sites_are_allowlisted" \
  "tests/architectural/test_no_raw_mission_spec_paths.py::test_constant_based_mission_spec_path_construction_stays_in_constructor_files" \
  "tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py::test_app_exposes_exactly_eight_frozen_commands" \
  "tests/cli/commands/test_merge_status_commit.py" \
  "tests/integration/test_merge_lane_planning_data_loss.py::TestPlanningArtifactReachesTarget::test_planning_artifact_only_merge_does_not_require_mission_branch"
```

Expected before the fixes: all red for the reasons in research.md. After: green.

## Part A / B — red-first entry points

| FR | Entry point (pre-existing) | Repro shape |
|----|----------------------------|-------------|
| FR-001 | `cutover_mission(feature_dir, status_feature_dir=…)` | non-PRIMARY `feature_dir` whose resolved PRIMARY home differs → fail closed; verify-passing `status_feature_dir` so the flip is reached |
| FR-002 | `cutover_mission(...)` | PRIMARY `tasks/` with `has_evictable_state()==True` + absent/stale COORD `tasks/` → assert `seeded_count>0` AND events on COORD |
| FR-005 | `DecisionGitLog` emit / `commit_merge_bookkeeping` / status-emit `_resolve_write_target` | mission without `meta.json` → all degrade via the shared helper; `STATUS_STATE`→coord ref |
| FR-006 | `generate_retrospective(...)` / `spec-kitty agent retrospect` | coord mission with deleted `coordination_branch` → returns `[]`, no crash |

## Corpus validation (NFR-002, A1/A3)

```bash
# Exercises _flip_phase + cutover across the whole dogfood corpus
spec-kitty migrate backfill-runtime-state            # or the cutover_repo walk
# Assert: 0 genuinely-legacy missions fail to flip; 0 PRIMARY-runtime evictions
```

## Full gate + quality sweep (NFR-003, NFR-004, SC-007)

```bash
PWHEADLESS=1 python -m pytest tests/architectural/ -q
ruff check .
mypy --strict src/            # per project config
python -m pytest tests/architectural/test_no_legacy_terminology.py -q   # pre-push terminology guard
```
