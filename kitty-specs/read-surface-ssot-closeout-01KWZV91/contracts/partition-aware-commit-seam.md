# Contract — Partition-Aware Commit Seam (`commit_for_mission`)

**Requirement**: FR-007 · **Constraint**: C-006 (close the class at the seam), C-002 (no partition change) · **IC-01**

## Current (defective) behaviour

`commit_for_mission(repo_root, mission_slug, files, *, kind, message, …)` resolves ONE placement for the
whole batch: `resolve_placement_only(repo_root, mission_slug, kind=kind)` (`commit_router.py:152`). Any caller
that passes a mixed-partition batch under a single `kind` misroutes every file to that kind's partition. Known
offenders: `spec_commit_cmd.py` (`kind=SPEC`, PRIMARY) and `mission_finalize.py:1320` (`kind=TASKS_INDEX`,
PRIMARY) — both commit COORD artifacts (`acceptance-matrix.json`, `issue-matrix.md`, `status.*`) to the primary
branch, so `accept` reads a stale coord copy (#2404).

## Contract (post-fix)

`commit_for_mission` MUST resolve placement **per file**, not per batch:

1. For each `file` in `files`, classify: `kind_f = kind_for_mission_file(file, mission_slug=mission_slug)`;
   `surface_f = PRIMARY if is_primary_artifact_kind(kind_f) else PLACEMENT`.
2. Group files by `surface_f`.
3. Commit each group to its own `CommitTarget` (`resolve_placement_only(kind=<representative kind of group>)`),
   using the existing materialize-then-retry path for a PLACEMENT (coord) group.

**Chosen shape (WP pins one, red-first):**
- **(a) Split-and-commit** — the batch is transparently split into per-partition commits. Preferred: fixes
  existing callers by construction with no caller change.
- **(b) Guard-reject** — `commit_for_mission` raises a structured `MixedPartitionBatch` error and each caller
  must submit single-partition batches. Only if (a) proves infeasible for a caller's atomicity needs.

### Invariants
- **INV-C1**: no file is committed to a ref other than its own partition's. (Pinned by a red-first test that
  submits a mixed batch and asserts each file lands on its partition's ref.)
- **C-002**: the `kind → partition` mapping is unchanged; this contract only changes *routing*, not membership.
- **No fast-path regression**: a single-partition batch commits exactly as today (one commit, one ref).

### By-construction consequences (no per-caller patch)
- `spec_commit_cmd.py` (`kind=SPEC`): a spec-only batch still lands PRIMARY; a batch that includes
  `acceptance-matrix.json` now routes that file to COORD.
- `mission_finalize.py:1320` (`kind=TASKS_INDEX`): tasks/WP files land PRIMARY; the batched
  `acceptance-matrix.json`/`issue-matrix.md`/`status.*` route to COORD.

### Out of contract
- `accept.py`'s residual commit is a separate concern (IC-02/FR-008) — it bypasses `commit_for_mission`
  entirely (raw `git commit`) and is routed + surface-reconciled there.
- `mission_record_analysis.py` already commits `analysis-report.md` with the correct `kind=ANALYSIS_REPORT`
  (COORD) — NOT in scope.
