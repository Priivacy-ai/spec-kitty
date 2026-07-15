# Contract — precondition ref resolution + write-side partition

Internal function contracts (no HTTP/network surface). Corrected after the
post-tasks anti-laziness squad (reviewer-renata + python-pedro) proved the
original single-arg signature could not implement per-kind routing.

## `resolve_precondition_ref(repo_rel_path: str, coord_branch_for_filter: str | None) -> str`

New pure helper in `src/specify_cli/cli/commands/implement_cores.py`. Single owner
of the "compare-against-which-ref" decision, resolved **per file path**.

```python
def resolve_precondition_ref(repo_rel_path: str, coord_branch_for_filter: str | None) -> str:
    if coord_branch_for_filter and is_coordination_artifact_residue_path(repo_rel_path):
        return coord_branch_for_filter
    return "HEAD"
```

- **Takes the path** — per-kind routing is impossible without it (BLOCKER 1). On a
  coord mission `coord_branch_for_filter` is a single non-None branch for *every*
  candidate; only the path distinguishes a PRIMARY `spec.md` from a COORD
  `status.events.jsonl`.
- **Uses `is_coordination_artifact_residue_path`** (exported from `mission_runtime`,
  None-safe) — True only for the STATUS/matrix/analysis COORD kinds. Do **NOT** use
  `is_primary_artifact_kind(kind_for_mission_file(path))`: `kind_for_mission_file("…meta.json")`
  returns `None`, so that form (a) is a `mypy --strict` error and (b) misroutes
  `meta.json` to coord — reintroducing the bug (BLOCKER 2).
- **Defaults toward primary** — everything not explicitly coord-residue (PRIMARY
  kinds, `meta.json`→None, unknown paths) resolves to `"HEAD"`. Fail-safe direction:
  a PRIMARY artifact is never compared against the coord branch.
- **Returns `str`** (never `None`) — no new kind→partition mapping literal (NFR-004).
- **Pure**: no filesystem/git side effects; deterministic.

### Where it is called (public signature stays stable)

Resolve **per file, inside** the staging core — NOT by changing
`resolve_planning_artifact_staging`'s public signature (which already has
`coord_branch_for_filter` in scope). Preferred approach (renata option b, minimal
test churn): inside `resolve_planning_artifact_staging`, partition `files` into
PRIMARY (→ `"HEAD"`) and COORD-residue (→ coord branch) groups and call the existing
`_files_changed_vs_ref(repo_root, group, ref)` once per group — keeping
`_files_changed_vs_ref`'s `(repo_root, files, ref)` signature intact so its unit
tests at `test_implement_cores.py:292,297-300` survive. For the single-path helpers
`_committed_meta_mapping:246` and `_drop_runtime_frontmatter_only_wp:350`, resolve
the ref per their own path via `resolve_precondition_ref`.

**Consequence:** the call sites at `implement.py:542` and `tasks_move_task.py:1400`
need **no edit** (public signature unchanged) → no `tasks_move_task.py` source edit
in the whole mission → the PR #2639 rebase gate no longer applies.

## `resolve_planning_artifact_staging(...)` (existing) — behavioral contract

- **Given** a solo PR-bound `coord` mission whose `spec.md`/`plan.md`/`tasks.md`/
  `tasks/WP*.md`/`lanes.json`/`meta.json` are committed on the feature/target branch,
  **then** the returned `files_to_commit` for those PRIMARY artifacts is **empty**
  (including `meta.json` — the BLOCKER 2 case).
- **Given** a `lanes_with_coord` mission with dirty COORD-owned status files, **then**
  those files are still resolved against the coordination ref and staged as before.

## Write-side: `_commit_planning_artifacts_transaction` (implement.py) — partition-aware commit

Today this commits **all** `files_to_commit` through **one** `BookkeepingTransaction`
to **one** `destination_ref`. On a coord mission that ref is the coord branch, so a
genuinely-dirty PRIMARY artifact would be committed onto coord (FR-003 / INV-1
violation).

- **Contract**: split `files_to_commit` into PRIMARY (→ primary/target ref) and
  COORD-residue (→ coord ref) and commit each group to its own ref (two transactions,
  mirroring `commit_router._group_files_by_partition`). Classify with the same
  `is_coordination_artifact_residue_path` predicate — one authority.
- **Given** a coord mission with a genuinely-dirty PRIMARY `spec.md` that must be
  committed, **then** it lands on the primary/target ref, never on the coordination
  branch; a dirty COORD `status.events.jsonl` still lands on the coord ref.
- **Boundary**: additive partition of the existing transaction flow — do not
  restructure unrelated parts of `implement.py` (C-002).

## Re-pinned / new unit assertions (`tests/specify_cli/cli/commands/test_implement_cores.py`)

- **Re-pin ONLY `:287`** (`test_no_ref_returns_all_files`): the `None → return all
  files` short-circuit is removed (callers always pass a concrete ref now); re-pin to
  the new reality (or delete if the input is no longer reachable).
- **Do NOT touch `:290`** (`test_missing_source_file_is_skipped`, ref `"HEAD"`) — it
  is orthogonal to the change and still valid (DIRECTIVE_041: don't rewrite a correct
  test).
- **New invariant tests**: `resolve_precondition_ref("…/meta.json", coord) == "HEAD"`;
  `resolve_precondition_ref("…/spec.md", coord) == "HEAD"`;
  `resolve_precondition_ref("…/status.events.jsonl", coord) == coord`; a genuinely-dirty
  `spec.md` is still staged (INV-5); a dirty `status.events.jsonl` on a coord mission
  still resolves to the coord ref (coord non-regression).

## Guard contracts (must NOT change)

- `_placement_coord_filter(...)` return type stays `str | None`.
- `_resolve_claim_commit_target(...)` continues to target the coord ref for
  status-event commits.
- `mission_runtime/artifacts.py` and `_assemble_artifact_placement_fragment` are not modified.
