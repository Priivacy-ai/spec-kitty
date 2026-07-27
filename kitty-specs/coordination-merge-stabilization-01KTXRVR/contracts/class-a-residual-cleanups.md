# Contract: Class A Residuals — Residue-Free Finalize, Canonical Read Surfaces, Baseline Coverage (#1814, #1735, #1827)

## A-r1: Finalize leaves no primary residue (#1814 → FR-006)

**Surface**: `_stage_finalize_artifacts_in_coord_worktree` (`cli/commands/agent/mission.py:99-131`).

GIVEN task finalization on a coordination-topology mission
WHEN staging into the coordination worktree completes
THEN `git status --porcelain` on the primary checkout reports no planning-artifact residue (`lanes.json`, `tasks/*`, matrices) created by the stager
AND subsequent `record-analysis` proceeds (no DIRTY_WORKTREE refusal from stager residue)
AND no operator-authored file is deleted (cleanup is scoped to paths the stager itself materialized — research R6).
CONSTRAINT (C-003): `COORD_OWNED_STATUS_FILES` is not widened.

Ratchet: extend `tests/specify_cli/test_wp06_sc2_paused_mission_blockers.py` (AC-A1).

## A-r2: Canonical status-read surface (#1735 → FR-009)

**Surfaces**: `retrospective/gate.py:597`, `cli/commands/agent_retrospect.py:432`.

GIVEN retrospective completion gating under coordination topology
THEN both read sites obtain events via `resolve_status_surface` (never `resolved.feature_dir` + direct file read)
AND the AC10 architectural ratchet (extend `tests/architectural/test_execution_context_parity.py`) forbids `resolved.feature_dir`-anchored `read_events()`/`status.events.jsonl` access outside the surface resolver. Ratchet lands after the two sites are routed.

## A-r3: Baseline-recording regression coverage (#1827 → FR-010)

GIVEN a coordination-topology merge completing
THEN `git show <target>:kitty-specs/<slug>/meta.json` contains `baseline_merge_commit` (real, unmocked `_record_baseline_merge_commit` — unmock helpers at `test_merge_coord_topology_1772.py:224-225` or add a sibling test)
AND the crash-between-record-and-commit re-run edge is documented in the test as a known bounded behavior (fix itself landed in rc42 9c8bff06f).
