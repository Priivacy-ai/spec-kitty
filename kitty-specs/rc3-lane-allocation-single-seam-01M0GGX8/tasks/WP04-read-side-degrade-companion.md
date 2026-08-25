---
work_package_id: WP04
title: Read-side degrade companion resolve_read_dir_or_degrade
dependencies: []
requirement_refs:
- FR-006
planning_base_branch: rc3-lane-allocation-single-seam-01M0GGX8
merge_target_branch: rc3-lane-allocation-single-seam-01M0GGX8
branch_strategy: Planning artifacts for this mission were generated on rc3-lane-allocation-single-seam-01M0GGX8. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rc3-lane-allocation-single-seam-01M0GGX8 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rc3-lane-allocation-single-seam-01M0GGX8
base_commit: 2520e7ad4243857b18f3b6c26eb9e14df33b855a
created_at: '2026-08-22T06:34:00.443970+00:00'
subtasks:
- T009
- T010
- T011
- T012
- T013
history: []
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/
create_intent:
- src/mission_runtime/read_dir_degrade.py
- tests/mission_runtime/test_read_dir_degrade.py
execution_mode: code_change
owned_files:
- src/mission_runtime/read_dir_degrade.py
- src/specify_cli/retrospective/generator.py
- src/specify_cli/core/worktree_topology.py
- tests/mission_runtime/test_read_dir_degrade.py
- tests/architectural/test_layer_rules.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objective

Ship `resolve_read_dir_or_degrade` as the read-side companion to the write-side
`resolve_write_target_or_degrade`, and migrate the **two genuine resolve-then-degrade** consumers onto it
(#3462, FR-006). Preserve the #1848 data-loss re-raise; do NOT force-migrate the FAIL_CLOSED pass-through
or bespoke sites — park them on the WP3 allowlist.

## Context

- Right-sizing (post-plan squad, rule-of-three): only **two** genuine degrade consumers —
  `retrospective/generator.py:264` (ZERO_EVIDENCE) and `core/worktree_topology.py:173`
  (DEGRADE_TO_FEATURE_DIR). The `agent/status.py:154/:195` FAIL_CLOSED sites re-raise then `typer.Exit`
  (no `try/except` removed) and `status/aggregate.py:351` + `_review_cycle_reconcile_doctor.py` are
  bespoke → **allowlist**, not migrate.
- **#1848 (do NOT collapse):** `status/aggregate.py:351` re-raises `CoordinationBranchDeleted` verbatim
  ahead of the `StatusReadPathNotFound → CoordAuthorityUnavailable` re-wrap. Leave that site untouched.
- **Layering (CRITICAL):** `mission_runtime` may not import `specify_cli.*` at module scope. Mirror
  `write_target_degrade.py` — keep the typed-error/resolver imports **function-scoped**, and add the new
  module to `tests/architectural/test_layer_rules.py` (`_MISSION_RUNTIME_ALLOWED_SPECIFY_CLI`) in THIS WP.
- **M5 co-edit:** `retrospective/generator.py` is also edited by mission M5 on `generate_retrospective`
  (~:1319). You own only `_load_traces` (~:224-299, the degrade `try/except` ~:264). Keep the new import
  **function-local** so the top-of-file import region (`~:20-33`) stays untouched.
- Contracts: `contracts/read-dir-degrade.md` (signature, migration map, allowlist criterion, INV-R1..3).
  Data model: `data-model.md` (`ReadDegradeStrategy`, `ReadDirDecision`).

## Subtasks

### T009 — the companion module
Create `src/mission_runtime/read_dir_degrade.py`:
- `ReadDegradeStrategy` enum: `DEGRADE_TO_FEATURE_DIR`, `DEGRADE_TO_PRIMARY_FEATURE_DIR`, `ZERO_EVIDENCE`,
  `FAIL_CLOSED`.
- `ReadDirDecision` frozen dataclass: `read_dir: Path`, `degraded: bool`, `strategy: ReadDegradeStrategy`.
- `resolve_read_dir_or_degrade(repo_root, mission_slug, kind, *, strategy, caught, degrade_target=None)`:
  resolve first; on `e in caught` apply strategy (degrade returns `degrade_target` + WARNING log;
  `FAIL_CLOSED` re-raises); `e not in caught` propagates verbatim. All `specify_cli.*` imports FUNCTION-SCOPED.

### T010 — layer-rules ledger
Add `read_dir_degrade` to the `mission_runtime` allowlist in
`tests/architectural/test_layer_rules.py` (`_MISSION_RUNTIME_ALLOWED_SPECIFY_CLI["missions"]` or the
equivalent key the sibling `write_target_degrade` uses). Run `test_layer_rules.py` and confirm green.

### T011 — migrate `retrospective/generator.py:264` (ZERO_EVIDENCE)
Replace the hand-rolled `try/except CoordinationBranchDeleted` in `_load_traces` with a
`resolve_read_dir_or_degrade(..., strategy=ZERO_EVIDENCE, caught=(CoordinationBranchDeleted,),
degrade_target=<empty-trace dir>)` call (function-local import). Behavior byte-identical, WARNING preserved.

### T012 — migrate `core/worktree_topology.py:173` (DEGRADE_TO_FEATURE_DIR)
Replace the `try/except CoordinationBranchDeleted` degrading `status_feature_dir` to `feature_dir` with a
`resolve_read_dir_or_degrade(..., strategy=DEGRADE_TO_FEATURE_DIR, caught=(CoordinationBranchDeleted,),
degrade_target=feature_dir)` call. Behavior byte-identical.

### T013 — red-first tests (`tests/mission_runtime/test_read_dir_degrade.py`)
- INV-R1: per-migrated-site before/after parity (generator ZERO_EVIDENCE, topology DEGRADE_TO_FEATURE_DIR).
- INV-R2 (#1848): a `CoordinationBranchDeleted` at a site whose `caught` excludes it propagates verbatim
  (helper never swallows an excluded exception). Pin that `aggregate.py` still surfaces
  `COORDINATION_BRANCH_DELETED` (do not migrate it).
- INV-R3: `ZERO_EVIDENCE`/degrade path logs at WARNING.

## Definition of Done
- `read_dir_degrade.py` exists with function-scoped imports; `test_layer_rules.py` green (module ledgered).
- The two consumers migrated, behavior byte-identical; aggregate #1848 untouched and green.
- `.venv/bin/ruff check .` + `.venv/bin/mypy src/` clean; `.venv/bin/python -m pytest tests/mission_runtime/ -q`
  and `.venv/bin/python -m pytest tests -k "coordination_branch_deleted" -q` green.

## Risks
- Module-level `specify_cli` import → breaks `test_layer_rules.py` (mitigated: function-scoped + ledger).
- Collapsing #1848 (mitigated: aggregate not migrated). M5 co-edit (mitigated: function-local import).

## Reviewer Guidance
Confirm only the two genuine degrade sites migrated; imports are function-scoped; the ledger entry landed
in the same WP; #1848 aggregate site is untouched and still surfaces the distinct error; parity tests are
per-site.
