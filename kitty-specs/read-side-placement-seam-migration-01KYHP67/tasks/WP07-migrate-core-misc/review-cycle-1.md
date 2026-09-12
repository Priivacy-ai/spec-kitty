---
affected_files:
- src/specify_cli/acceptance/__init__.py
- src/specify_cli/agent_tasks_ports.py
- src/specify_cli/agent_utils/status.py
- src/specify_cli/cli/commands/agent/mission_record_analysis.py
- src/specify_cli/context/resolver.py
- src/specify_cli/core/stale_detection.py
- src/specify_cli/core/worktree_topology.py
- src/specify_cli/doctrine_synthesizer/apply.py
- src/specify_cli/mission_loader/command.py
- src/specify_cli/missions/plan/plan_interview.py
- src/specify_cli/missions/plan/specify_interview.py
- src/specify_cli/sync/events.py
- src/specify_cli/task_utils/support.py
- src/specify_cli/workspace/context.py
- tests/specify_cli/test_read_seam_migration_core.py
- tests/specify_cli/conftest.py
cycle_number: 1
mission_slug: read-side-placement-seam-migration-01KYHP67
reproduction_command: PWHEADLESS=1 uv run pytest tests/specify_cli/test_read_seam_migration_core.py tests/specify_cli/workspace/ tests/specify_cli/context/ -q
reviewed_at: '2026-07-27T15:40:00Z'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP07
---

**Verdict: APPROVED** — WP07 (core/context/workspace/plan/misc cluster) conforms
to the WP02 classification ledger (`docs/development/read-side-seam-classification.md`
§WP07) site-for-site. Independent reviewer verification against the ledger and by
reverting the source, not the implementer's word.

## Ledger conformance — migrate-fail-loud (all routed through `placement_seam(...).read_dir(kind)`)

Every §WP07 migrate-fail-loud site verified at its ledger kind:

- `acceptance/__init__.py` `_wp_tasks_read_dir` — WORK_PACKAGE_TASK; the
  `is_primary_artifact_kind(WORK_PACKAGE_TASK)` future-repartition invariant is
  preserved verbatim. ✔
- `agent_tasks_ports.py` `RealFsReader` — `planning_read_dir` passthrough
  (caller-supplied `kind`) + `wp_tasks_dir` WORK_PACKAGE_TASK; clean 1:1 swap,
  typed-`Path` local re-pin kept. ✔
- `agent_utils/status.py` `show_kanban_status` — WORK_PACKAGE_TASK. ✔
- `cli/commands/agent/mission_record_analysis.py` — SPEC via
  `_kind_for_artifact("spec")`; matches the ledger (SPEC, not a bespoke mapping).
  Correctly WP07-scoped despite living under WP03's `cli/commands/agent/**` glob
  (ledger cross-glob note honored). ✔
- `context/resolver.py` `resolve_context` — WORK_PACKAGE_TASK (single anchor
  shared with the following meta.json read; both PRIMARY-partition) + LANE_STATE.
  The sibling `resolve_feature_dir_for_mission` HANDLE-canonicalization call is
  correctly left kind-blind (not a ledger bypass primitive). ✔
- `core/stale_detection.py` `_resolve_feature_dir_for_staleness` — WORK_PACKAGE_TASK;
  pre-existing `except Exception: return None` degrade contract preserved. ✔
- `core/worktree_topology.py` `materialize_worktree_topology` — LANE_STATE. ✔
- `doctrine_synthesizer/apply.py` `_feature_dir` — STATUS_STATE, the one genuine
  coord-partition site; fail-loud is correct here (a deleted coord branch MUST
  raise, not silently read primary). ✔
- `mission_loader/command.py` `run_custom_mission` — PRIMARY_METADATA. ✔
- `missions/plan/plan_interview.py` + `specify_interview.py` `_get_mission_id` —
  PRIMARY_METADATA each; `contextlib.suppress(Exception)` contract preserved. ✔
- `sync/events.py` `_resolve_mission_id_for_slug` — PRIMARY_METADATA. ✔
- `task_utils/support.py` `locate_work_package` — WORK_PACKAGE_TASK. ✔
- `workspace/context.py` — all 6 sites: WORK_PACKAGE_TASK ×3 (:481, :679, :730)
  + LANE_STATE ×3 (:770, :811, :877). ✔

## Stay-lenient preserved (critical)

- `manifest.py` `candidate_feature_dir_for_mission(worktree_path, feature)` — UNTOUCHED
  (feat commit `4b3c77b68` does not modify manifest.py). The worktree-vs-primary drift
  probe stays kind-blind, as the ledger prescribes. A dedicated AST-based test
  (`test_manifest_stay_lenient_site_is_unchanged`) pins that it stays on the blind
  primitive. ✔

## No-op sites confirmed untouched

- `orchestrator_api/commands.py` and `runtime/next/runtime_bridge_identity.py` —
  comment/docstring mentions only, zero real call sites; both untouched by the feat
  commit. `src/runtime/` was not modified, so the shared-package-boundary gate is N/A. ✔

## ATDD judgment (red-first + discriminating negative)

- **Red-first genuine**: reverting only `doctrine_synthesizer/apply.py` to its base
  form (`4b3c77b68~1`) makes exactly 1 of 12 tests fail —
  `test_doctrine_synthesizer_feature_dir_raises_on_deleted_coord` ("DID NOT RAISE
  CoordinationBranchDeleted"); the other 11 pass. Matches the implementer's claim. ✔
- **Discriminating negative genuine**: `test_lane_state_reads_unaffected_by_deleted_coord`
  drives the SAME `_build_deleted_coord_mission` fixture through
  `materialize_worktree_topology` (LANE_STATE) and asserts it does NOT raise and
  returns primary-anchored topology (`target_branch == "main"`, WP01 present). It
  asserts concrete resolved values, not a smoke pass — it genuinely pins that fail-loud
  is scoped to coord-partition kinds only. ✔

## Gates (in-lane, strict exit codes)

- `PWHEADLESS=1 uv run pytest tests/specify_cli/test_read_seam_migration_core.py
  tests/specify_cli/workspace/ tests/specify_cli/context/ -q` → **exit 0, 149 passed**.
- `uv run ruff check .` → **exit 0, All checks passed**.
- `uv run mypy src` (project-mode) → **exit 0, Success, 0 errors in 1155 files**.
  ZERO new mypy errors introduced by WP07; no WP07-touched file appears in any mypy
  diagnostic.

## Baseline reds (not green-washed)

- `tests/specify_cli/agent_utils/test_status.py` → 7 failures
  (`test_show_kanban_status_*`, `test_stall_*`, `test_stale_verdict_*`), all a
  pre-existing `/tmp/kitty-specs/...` "Feature directory not found" test-environment
  isolation issue. Confirmed identical (7 failed / 22 passed, same test names) after
  reverting `agent_utils/status.py` to base — NOT a WP07 regression.

## Stray-artifact reconciliation (both surfaces)

- Primary checkout: the stray handover-recovery `WP07.../review-cycle-1.md`
  (verdict rejected, "no implementation agent was dispatched", added by
  `f9c1db15e`) was removed by `491acce4e`; the WP07 tasks dir now holds only
  `baseline-tests.json`. ✔
- Coord surface (`kitty/mission-read-side-placement-seam-migration-01KYHP67`): no
  review-cycle artifact anywhere in the mission tree. ✔
- No stale `rejected` copy lingers where the review/merge gate reads. This
  reviewer-authored `approved` artifact is now the authoritative WP07 verdict.

## Anti-pattern checklist

1. Dead code — N/A (WP07 swaps call sites; introduces no new production symbol).
2. Synthetic-fixture test — PASS (tests invoke real production paths; red-first proven).
3. Silent empty return — PASS (only pre-existing documented `stale_detection` degrade).
4. FR coverage — PASS (FR-002 route-through-seam + NFR-002 fail-loud both asserted).
5. Frozen surface — PASS (manifest.py + no-op sites untouched).
6. Locked decision — PASS (C-001: routes through the single authority; no new resolver).
7. Shared-file ownership — PASS (all in owned_files; cross-glob note honored for
   mission_record_analysis.py).
8. Production fragility — PASS (the STATUS_STATE fail-loud raise is a functional read
   with documented NFR-002 rationale).
