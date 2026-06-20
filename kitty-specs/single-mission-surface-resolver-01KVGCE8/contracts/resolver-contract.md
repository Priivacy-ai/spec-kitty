# Behavioural Contract: the single mission-surface resolver

No network/API surface — these are the behavioural guarantees of the canonical
resolver, each a testable assertion (the FR-002 equivalence test enforces them across
every entry point).

## C-RES-1 — single authority
Every mission-surface directory read resolves via `resolve_status_surface_with_anchor`
(or a blessed delegator). A `raw-bypass` join (`repo_root/KITTY_SPECS_DIR/<slug>`)
outside that set is a guard failure (FR-004).

## C-RES-2 — equivalence across entry points
For a fixed `(handle, repo_root, topology)`, all of `resolve_mission_read_path`,
`MissionStatus.load`/`_resolve_read_dir`, the `mission_runtime/resolution` boundary, and
the unified `primary_feature_dir_for_mission` return the **same directory** OR raise the
**same typed error**. (FR-002)

## C-RES-3 — topology outcomes
- `no-coord` → primary dir.
- `coord-fresh` → coord dir.
- `coord-empty` → raise `STATUS_READ_PATH_NOT_FOUND` whose message names BOTH recovery
  paths (collapse/flatten OR recreate/populate the coord branch). No silent primary
  fallback. (FR-006)
- `coord-deleted` → `CoordinationBranchDeleted`.

## C-RES-4 — handle disambiguation
A `mid8` handle resolves through the one canonical handle resolver. Ambiguous → raise
`MISSION_AMBIGUOUS_SELECTOR`; NEVER silent first-match `glob`. (FR-008)

## C-RES-5 — typed-error preservation
`STATUS_READ_PATH_NOT_FOUND` / `MISSION_AMBIGUOUS_SELECTOR` survive end-to-end through
`next` / `mission_runtime`; they are NOT flattened to `MISSION_NOT_FOUND`. (FR-005)

## C-RES-6 — single primary primitive
Exactly one `primary_feature_dir_for_mission`, composing `<slug>[-mid8]` via the single
`_compose_mission_dir` grammar. (FR-009)

## Verification
Each contract is covered by the FR-002 differential test and/or a mutation-killing test
(SC-001..SC-006). Deletion of any duplicate resolver is gated on the equivalence test
being green (C-004).
