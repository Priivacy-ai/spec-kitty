# Tracer — Tooling Friction (M0 mission_type backfill)

Seeded at planning; append friction as encountered; feeds the next mission.

## F1 — Mission spec landed on a since-merged branch
- Spec/meta live on `upstream/main` (via merged `pr/rc3-friction-mission-specs`), not on
  local `main`. Had to cut the working branch off `upstream/main` to materialize spec.md/
  meta.json (local main had only the dossier snapshot under the mission dir).

## F2 — `target_branch` retarget needed
- meta.json `target_branch` pointed at the deleted `pr/rc3-friction-mission-specs`; retargeted
  to `main` at pre-flight.

## F3 — Completeness-baseline mechanics clarified (for tasks phase)
- The kickoff names `_arch_shard_map.py`, `marker_baseline.txt`, `_golden_count_baseline.json`.
  Reality on this branch:
  - `tests/_arch_shard_map.py` governs ONLY the arch pole roots (`tests/architectural`,
    `tests/adversarial`, `tests/architecture`, `tests/lint`). New tests under
    `tests/specify_cli/...` are NOT in scope → no shard-map edit needed.
  - No `marker_baseline.txt` exists (only a stale `.pyc` under `__pycache__`). The live
    marker gate is `tests/architectural/test_marker_job_completeness.py`, which checks marker
    NAMES are routed — satisfied by using already-routed markers. Convention (CLAUDE.md +
    `test_backfill_identity.py:31`): migration unit tests declare
    `pytestmark = [pytest.mark.unit, pytest.mark.fast]`; red-first gate proofs use
    `pytest.mark.regression`.
  - `tests/architectural/_golden_count_baseline.json` caps `len(x)==int` "convert" sites per
    top-level `tests/<dir>`. New tests go in EXISTING dirs → no baseline edit needed; just
    write frozenset/set-equality assertions, avoid bare `len==N` (or use the
    `# golden-count: cardinality-is-contract` escape hatch).
- Net: WP test files declare a routed `pytestmark` + avoid golden-count litter. No baseline
  FILE edits required. Verify the marker-convention gate, not a nonexistent baseline file.

## F4 — target_branch=main trips the protected-branch bookkeeping guard
- Kickoff said set meta target_branch=main (to drop the stale merged `pr/rc3-friction-mission-specs`).
  But `finalize-tasks` bookkeeping (status transitions) refused: "PROTECTED_BRANCH_REFUSED …
  destination ref 'main' … Bookkeeping commits must target the coordination branch."
- single_branch topology has no coordination branch → bookkeeping routes to primary = the working
  branch. Set target_branch to the live working branch `pr/rc3-mission-type-backfill` (the branch
  `spec-kitty merge` will consolidate lanes into; closeout rebases it onto upstream/main + PRs there).
  This is the correct local mechanic and still fixes the stale-reference the kickoff retarget addressed.
