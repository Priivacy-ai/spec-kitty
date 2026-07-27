# Data Model — Partition-Aware Implement-Claim Precondition

This is a control-flow correctness fix; there is no persisted schema. The "model"
is the **ref-resolution decision** the precondition applies per artifact kind.

## Entities / Value Objects

### ArtifactKind partition (authority: `mission_runtime/artifacts.py`)

| Partition | Kinds | Lives on |
|-----------|-------|----------|
| PRIMARY | `spec.md`, `plan.md`, `data-model.md`, `research.md`, checklists, `tasks.md`, `tasks/WP*.md`, `lanes.json`, `meta.json`, retrospective | primary/target branch (every topology) |
| COORD | `status.events.jsonl`, `status.json`, `acceptance-matrix`, `issue-matrix`, `analysis-report` | coordination branch (coord / lanes-with-coord) |

Classified by `kind_for_mission_file(path, mission_slug=...)` /
`is_primary_artifact_kind(kind)`. **Consumed read-only** — not redefined here.

### Precondition comparison ref (the decision this mission corrects)

For each candidate file in the working tree, the precondition asks: *"compare its
bytes against which committed ref to decide if it still needs a commit?"* Resolved
**per path** by `resolve_precondition_ref(repo_rel_path, coord_branch_for_filter)`,
which returns the coord branch only for `is_coordination_artifact_residue_path(path)`
and `"HEAD"` for everything else (fail-safe toward primary).

| Candidate path | `coord_branch_for_filter` | Resolved ref |
|----------------|---------------------------|--------------|
| `spec.md` / `plan.md` / `tasks.md` / `lanes.json` (PRIMARY) | any | `"HEAD"` |
| `meta.json` (kind → `None`; **not** a residue path) | any | `"HEAD"` |
| `status.events.jsonl` / `status.json` / matrices / analysis (COORD residue) | coord branch | coord branch |
| any path | `None` (flat/primary) | `"HEAD"` |

**Before (buggy):** all files → single collapsed `coord_branch_for_filter`; PRIMARY
artifacts (and `meta.json`) absent on the coord branch → false "changed".
**After (fixed):** per-path resolution via `resolve_precondition_ref`. The
`meta.json → None` classification (it is in the self-bookkeeping allowlist, not the
kind map) is why the None-safe residue predicate is used instead of
`is_primary_artifact_kind(kind_for_mission_file(path))`, which would misroute it to
coord and trip `mypy --strict`.

## State Transition — the claim precondition

```
claim(WP##)
  └─ _ensure_planning_artifacts_committed_git         (implement.py:494)
        └─ resolve_planning_artifact_staging          (implement_cores.py:454)
              ├─ _files_changed_vs_ref(files, ref)     (:406)   ← ref now per-kind
              ├─ _committed_meta_mapping(ref)          (:249)   ← ref now per-kind
              └─ _drop_runtime_frontmatter_only_wp(ref)(:387)   ← ref now per-kind
        ⇒ staging set EMPTY for already-committed PRIMARY artifacts ⇒ claim PROCEEDS
        (was: non-empty ⇒ "Planning artifacts not committed" printed at implement.py:319,
         then raise typer.Exit(1) at implement.py:342 on the auto_commit=False path)
```

**Write-side (WP02, FR-003):** when `files_to_commit` is non-empty (a genuinely-dirty
PRIMARY artifact), `_commit_planning_artifacts_transaction` (implement.py) partitions
the set by `is_coordination_artifact_residue_path` and commits PRIMARY → primary/target
ref, COORD → coord ref (two transactions), so a PRIMARY artifact never lands on coord.

Boundary guard (unchanged): status-event commit target
(`_resolve_claim_commit_target`) continues to resolve to the coordination ref.

## Invariants

- **INV-1**: PRIMARY planning artifacts are never diffed against, nor committed to,
  the coordination branch. (FR-001, FR-003)
- **INV-2**: COORD-owned status/matrix/analysis files continue to diff against and
  commit to the coordination ref under coord/lanes-with-coord topology. (NFR-002, C-001)
- **INV-3**: Mission topology derivation is invariant across this change. (NFR-001)
- **INV-4**: Exactly one artifact-kind→partition authority exists
  (`mission_runtime/artifacts.py`); no consumer redefines it. (NFR-004)
- **INV-5**: A PRIMARY artifact with genuine uncommitted working-tree changes is
  still detected (the fix corrects the *ref*, it does not skip the check).
