---
work_package_id: WP02
title: 'Merge enforcement: honor retention, couple coord, abort, red-first'
dependencies:
- WP01
requirement_refs:
- C-001
- C-007
- FR-002
- FR-004
- FR-005
- FR-006
- FR-007
- FR-010
- FR-011
- FR-012
- FR-013
- NFR-002
- NFR-003
planning_base_branch: fix/3131-merge-retention
merge_target_branch: fix/3131-merge-retention
branch_strategy: Planning artifacts for this mission were generated on fix/3131-merge-retention. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3131-merge-retention unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
- T011
history:
- at: '2026-08-31T16:30:00Z'
  actor: claude
  action: created
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/merge/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/merge/executor.py
- src/specify_cli/cli/commands/merge.py
- src/specify_cli/orchestrator_api/commands.py
- tests/integration/test_merge_lane_planning_data_loss.py
- tests/merge/test_executor_coverage.py
- tests/merge/test_coordination_flatten_on_branch_delete.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned agent profile via `/ad-hoc-profile-load implementer-ivan` (role: implementer). Then read the mission `plan.md` "Architecture & Approach" and `contracts/retention-resolver-contract.md` — AUTHORITATIVE over this prompt where they conflict. This is destructive git surgery: read `data-model.md` INV-1..INV-4 before changing any cleanup gate.

## Objective

Make `spec-kitty merge` HONOR the resolved retention decision, fail closed, across
the success cleanup AND the abort path — the P1 data-loss fix. **Red-first**: land
the failing regression FIRST (T005), then make it green.

Depends on WP01's `resolve_merge_retention`/`RetentionDecision` (import from
`specify_cli.core.paths`). Merge the WP01 lane in before starting.

## Context — read, do not re-derive

- **`contracts/retention-resolver-contract.md`** → "Consumption contract" + "Anti-vacuity".
- **Scout-verified call sites** (all in `src/specify_cli/merge/executor.py`):
  - `_phase_cleanup_worktrees_and_branches` (~1471): worktree removal under
    `run.remove_worktree` (~1479); lane+mission branch delete under
    `run.delete_branch` (~1516); coord marker-flatten `_flatten_coordination_metadata_after_branch_delete`
    (~1557, currently under `delete_branch`); coord-worktree teardown
    `teardown_coordination_topology` (~1570, currently under `remove_worktree`).
  - `_MergeRunState` fields `delete_branch`/`remove_worktree` (~303-304).
  - `_run_lane_based_merge` (unlocked, ~1764): resolves `primary_meta_dir`
    (~1821) and `identity = resolve_mission_identity(primary_meta_dir)` (~1849).
  - `_run_lane_based_merge_locked` builds `_MergeRunState` (~1721-1739); called
    from the unlocked driver (~1895-1909).
- **CLI**: `src/specify_cli/cli/commands/merge.py` — tri-state flags (~430-431),
  resume fallthrough (~499-501), dispatch (~575-587), abort teardown
  `_teardown_coordination_for_abort` (~251-319).
- **Second entry to audit (C-007)**: `src/specify_cli/orchestrator_api/commands.py` (~569).

## Subtask guidance

### T005 — Red-first regression (COMMIT THIS FIRST, RED on main)
In `tests/integration/test_merge_lane_planning_data_loss.py` add class
`TestRetentionConstraintSurvivesCleanup` with `@pytest.mark.regression` pinned to
#3131. NON-VACUOUS per the contract.
- Build a `coord`-topology mission fixture whose primary `meta.json` sets
  `retain_branches: true` and `retain_worktrees: true`, with a NON-planning lane.
- **AVOID THE VACUOUS-NONE TRAP**: the repro must be RED on current main for the
  RIGHT reason — because the *default* merge deletes despite the meta policy. Do
  NOT pass the tri-state `None` to the pre-change `_run_lane_based_merge` (its
  param is still `bool`, so a falsy `None` would skip cleanup and the test would
  pass for the wrong reason). Instead reproduce the OBSERVED default behavior:
  drive the merge at the layer where the cleanup default lives so that on main it
  resolves to delete/remove. Concretely, invoke the CLI `merge` entry (or
  `_run_real_merge`) WITHOUT specifying the cleanup flags — letting them take
  their default — on the retaining mission. On main the default deletes → the
  assertions below fail (RED). After the fix, the default resolves through
  `resolve_merge_retention` → meta retain → GREEN.
- Assert: the mission branch AND a non-planning lane branch survive
  (`git branch --list`); the lane worktree `.worktrees/<slug>-<mid8>-lane-<id>`
  survives (`Path.exists()`) — explicitly NOT the merge scratch worktree.
- **Fixture cost is real** — this file today only drives `_run_lane_based_merge`
  on non-coord planning/single missions with `delete_branch=False`; there is NO
  reusable coord full-merge fixture here. Adapt a coord-topology full-merge fixture
  from `tests/integration/test_mission_close_discard_coord_teardown.py` or
  `tests/integration/test_merge_cluster_coord_read.py` (they build coord missions
  that survive the review-artifact/WP-done/baseline gates). Drive it via the CLI
  `merge`/`_run_real_merge` layer (where the `True` default lives) — NOT
  `_run_lane_based_merge` directly (whose `delete_branch`/`remove_worktree` params
  have no default, so "letting them default" is impossible there).
- Commit this as the FIRST commit of the lane (ATDD C-011). It MUST be RED on the
  mission base before T006-T011. Verify RED via `PYTHONPATH=<worktree>/src` and
  record the observed failure (branches/worktrees deleted) in the WP notes.
- Add a SECOND assertion tier once enforcement lands (after T007): with an
  EXPLICIT `--delete-branch`/`--remove-worktree` override the same mission DOES
  delete (proving the override path stays reachable and the test isn't just
  asserting "merge never deletes").

### T006 — Tri-state flags
Change `--delete-branch/--keep-branch` and `--remove-worktree/--keep-worktree` to
`Optional[bool]` default `None` (typer supports `--x/--no-x` → None when unset).
Thread the RAW tri-state unchanged through `_run_real_merge` → `_run_lane_based_merge`
(do NOT collapse to bool in the CLI). Existing callers passing explicit `True`/`False`
keep their meaning (CLI wins).

### T007 — Resolve once (unlocked), emit warnings
In `_run_lane_based_merge`, right after `identity = resolve_mission_identity(primary_meta_dir)`,
call `resolve_merge_retention(primary_meta_dir, explicit_delete_branch=..., explicit_remove_worktree=...)`.
- Emit `decision.warnings` (retention honored) and `decision.override_notices`
  (explicit delete over policy) to the console — operator-visible (FR-005/FR-006).
- Corrupt meta → `MissionMetaReadError` aborts the merge with a clean error +
  non-zero exit (mirror the target-branch handling in `merge.py:522-535`).
- Pass the RESOLVED `delete_branch`, `remove_worktree`, `teardown_coordination`
  into `_run_lane_based_merge_locked` (both fresh + `--resume` go through here).

### T008 — Couple the coordination teardown (TOPOLOGY-AWARE — read carefully)
Add `_MergeRunState.teardown_coordination: bool = False` **in the DEFAULTED region
of the dataclass** (after the existing required fields, ~line 311), NOT next to the
required `delete_branch`/`remove_worktree` at ~303-304. A default keeps the other
four `_MergeRunState` construction sites compiling (see the audit note below).

**The trap to avoid (reintroduces #3086 / violates INV-2):** today the coord
marker-flatten (`_flatten_coordination_metadata_after_branch_delete`, ~1557) is
deliberately ATOMIC with the coordination-branch deletion — both inside the
`delete_branch` block — so the branch is never deleted while its `coordination_branch`
marker is stranded (the #3086 crash). For a `coord` mission,
`lanes_manifest.mission_branch` IS the coordination branch. Naively moving only the
flatten (or only the worktree teardown) under a new gate while leaving the coord
branch deletion on `delete_branch` would, for the reachable case
`delete_branch=True, remove_worktree=False`, delete the coord branch but skip the
flatten → stranded marker → #3086.

**Correct design (topology-aware):** the coordination branch + its marker + its
worktree are ONE unit gated by `teardown_coordination` (= `delete_branch AND
remove_worktree`); lane resources stay per-flag:
- lane worktree removal → `if run.remove_worktree` (unchanged)
- **lane** branch deletion → `if run.delete_branch` (unchanged) — lane branches only.
- For a **coord-topology** mission: the coord/mission branch deletion, the
  marker-flatten (~1557), AND the coord-worktree teardown (~1570) all move under
  `if run.teardown_coordination:` — kept atomic. Use the existing coord signal
  (the flatten helper already early-returns when `coordination_branch` is absent)
  to stay topology-aware.
- For a **non-coord** mission (`single_branch`/`lanes`): the mission-branch
  deletion stays under `if run.delete_branch` exactly as today (no coord marker,
  no coord worktree) — no behavior change. Do NOT move non-coord mission-branch
  deletion under `teardown_coordination`.
- `cleanup_merge_workspace` (~1598) stays UNGATED (FR-013 / C-006) — do not touch it.

Result: a coord retaining mission (either field set) keeps its whole coord triple
consistent (INV-2); a fully-cleaned coord mission (both delete+remove) tears the
triple down atomically (#3086 preserved). This also fixes the pre-existing
`--keep-worktree`-on-coord husk (branch+marker gone, worktree kept).

**Audit all 5 `_MergeRunState` construction sites** for the new field (default
keeps them valid): `executor.py:~1721`; `tests/merge/test_executor_phase_boundary.py:~42`;
`tests/merge/test_executor_coord_reconcile.py:~192`;
`tests/merge/test_coordination_flatten_on_branch_delete.py:~125,~230`;
`tests/specify_cli/test_workspace_context_tombstone.py:~253`. Only
`test_coordination_flatten_on_branch_delete.py` needs a BEHAVIORAL update (see T011).

### T009 — Abort honors retention
In `_teardown_coordination_for_abort` (`merge.py`), resolve the coord-retention
decision (reuse `resolve_merge_retention` against the primary meta) and skip the
coord-worktree destroy + warn when the mission requests worktree retention (FR-012).

### T010 — Route the second merge entry through the resolver (C-007)
`orchestrator_api/commands.py` `_execute_lane_merge` is a GENUINE second deletion
implementation, not a passthrough: it is called with hardcoded
`delete_branch=True, remove_worktree=True` (~`commands.py:1826-1827`) and deletes
worktrees/branches with its own inline code (`if remove_worktree:` ~659,
`if delete_branch:` ~675). This is a live silent-deletion bypass reaching
lane/coord deletion, so NFR-003 ("all cleanup paths") REQUIRES routing it through
`resolve_merge_retention` (read the mission's primary meta; honor retention +
coupled coord there too). "Document as out-of-scope" is acceptable ONLY if you can
prove this path never runs for a retaining coord mission — prefer routing. Whichever
you choose, add the asserting test in T011.

### T011 — Executor + abort unit tests
Home for ALL new unit assertions: `tests/merge/test_executor_coverage.py` (owned).
The `merge --abort` assertion calls `merge._teardown_coordination_for_abort`
directly (imported from `cli.commands.merge`, owned) — do NOT edit the unowned
`tests/specify_cli/cli/commands/test_merge.py`. Cover:
- coupled coord gate: partial retention does NOT half-tear coord (both cases:
  `delete_branch=True,remove_worktree=False` and the reverse) — assert marker,
  coord branch, and coord worktree end mutually consistent.
- malformed meta value → retained.
- override notice emitted when explicit delete over a retaining policy.
- **FR-007 resume**: a `--resume`d merge of a retaining coord mission preserves
  the resolved retention (branches/worktrees survive) — the resume path falls
  through `merge.py:499-501` into the same resolver, so assert it is honored, not
  just assumed.
- **C-007 orchestrator entry**: `orchestrator_api._execute_lane_merge` honors
  retention for a retaining coord mission (paired with T010's routing) — a
  retaining mission driven through that entry does NOT delete.
- `merge --abort` on `retain_worktrees: true` → coord worktree survives (FR-012).
- scratch worktree STILL removed under `retain_worktrees: true` (FR-013).
- non-retaining mission: byte-identical cleanup (FR-010) — existing tests stay green.

**Behavioral update to the existing coord flatten test (required by T008):**
`tests/merge/test_coordination_flatten_on_branch_delete.py::test_issue_3086_merge_delete_branch_flattens_coordination_metadata`
currently uses `delete_branch=True, remove_worktree=False` and asserts the marker
IS flattened. Under the corrected coupling that case now RETAINS the coord triple
(teardown_coordination=False). Update the test to `remove_worktree=True` (so
`teardown_coordination=True`) to keep exercising the #3086 flatten-atomicity, and
add a new case asserting `delete_branch=True, remove_worktree=False` on a coord
mission RETAINS branch+marker+worktree together (the corrected INV-2 behavior).

## Branch Strategy
Planning base and final merge target: `fix/3131-merge-retention`. This WP depends
on WP01 — merge that lane in first. Execution worktrees are per computed lane from `lanes.json`.

## Definition of Done
- T005 regression RED on the mission base, GREEN at this WP's final commit.
- Coordination teardown coupled; abort honors retention; scratch worktree ungated.
- Operator-visible warning + recorded override notice; corrupt meta aborts.
- `orchestrator_api` entry resolved or documented.
- `ruff` + `mypy --strict` clean; functions ≤15 (extract helpers as needed).

## Test surface
`pip install -e . && PWHEADLESS=1 pytest tests/integration/test_merge_lane_planning_data_loss.py tests/merge/test_executor_coverage.py -q`
(reinstall editable — merge tests shell out to `spec-kitty`; stale install = false reds).

## Reviewer guidance
- Confirm the resolver is read from `primary_meta_dir`, NOT the locked driver's
  coord STATUS husk (the partition trap).
- Confirm the red-first test is non-vacuous (coord topology, non-planning lane,
  `.worktrees/` path, no explicit flags) and was RED on base.
- Confirm no silent-deletion path remains across success + abort (NFR-003).
