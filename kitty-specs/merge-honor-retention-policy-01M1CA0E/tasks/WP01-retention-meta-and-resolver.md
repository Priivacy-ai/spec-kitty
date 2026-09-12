---
work_package_id: WP01
title: Retention meta field + pure resolver (foundation)
dependencies: []
requirement_refs:
- FR-001
- FR-003
- NFR-001
planning_base_branch: fix/3131-merge-retention
merge_target_branch: fix/3131-merge-retention
branch_strategy: Planning artifacts for this mission were generated on fix/3131-merge-retention. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3131-merge-retention unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-merge-honor-retention-policy-01M1CA0E
base_commit: e1b35bf7a9a36204ea539d634659154da8a034a9
created_at: '2026-08-31T17:12:47.209222+00:00'
subtasks:
- T001
- T002
- T003
- T004
history:
- at: '2026-08-31T16:30:00Z'
  actor: claude
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/
create_intent:
- tests/core/test_retention_resolver.py
execution_mode: code_change
owned_files:
- src/specify_cli/mission_metadata.py
- src/specify_cli/core/paths.py
- tests/core/test_retention_resolver.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned agent profile via `/ad-hoc-profile-load python-pedro` (role: implementer). Then read the mission `plan.md` "Architecture & Approach" section and `contracts/retention-resolver-contract.md` — they are authoritative over this prompt where they conflict.

## Objective

Establish the **single machine-readable retention authority** and the **one pure
resolver** every merge consumer will share. This WP writes no git-mutating code —
it is the contract foundation (spec FR-001, FR-003, NFR-001).

1. Add `retain_branches` / `retain_worktrees` to the meta.json optional schema (T001).
2. Add `read_retention_from_meta` — a RAW (uncoerced) read over the fail-closed reader (T002).
3. Add the pure `resolve_merge_retention` + `RetentionDecision` (T003).
4. Resolver unit tests: all 6 precedence cases + malformed + corrupt (T004).

## Context — read these, do not re-derive

- **`contracts/retention-resolver-contract.md`** — the signature, the C1–C6
  behavioral table, and the consumption/anti-vacuity contract. AUTHORITATIVE.
- **`data-model.md`** — the `RetentionDecision` fields + invariants INV-1..INV-4.
- **Canonical precedent to MIRROR**: `resolve_merge_target_branch` and
  `read_target_branch_from_meta` in `src/specify_cli/core/paths.py` (~lines 697,
  785). Same shape: `(value, source)` provenance, `load_meta_fail_closed` read,
  corrupt → `MissionMetaReadError`.
- **Schema home**: `MissionMetaOptional` TypedDict in
  `src/specify_cli/mission_metadata.py` (~lines 64-88). `validate_meta`
  (~line 483) preserves unknown fields — no strict schema; add two FLAT bool
  fields (NOT a nested block, per spec C-003).

## Subtask guidance

### T001 — Schema fields
Add to `MissionMetaOptional` (keep alphabetical/grouped with peers like
`merged_push: bool`):
```python
retain_branches: bool
retain_worktrees: bool
```
Do NOT change `validate_meta` to require them, and do NOT default-write them
anywhere in this WP (absence = "no stated policy"; SC-004 byte-identical default).

### T002 — Raw meta read
Add `read_retention_from_meta(primary_meta_dir: Path) -> tuple[object | None, object | None]`
in `core/paths.py`, next to `read_target_branch_from_meta`:
- Use `load_meta_fail_closed(primary_meta_dir)`.
- Return `(meta.get("retain_branches"), meta.get("retain_worktrees"))` as RAW
  values (do NOT coerce to bool — the resolver must detect non-boolean values).
- `(None, None)` when meta is absent. Let `MissionMetaReadError` propagate on corrupt.

### T003 — The resolver
Add `RetentionDecision` (frozen dataclass) and `resolve_merge_retention(...)` per
the contract. Precedence per field: `explicit CLI flag (bool) > meta.json > default`.
- `explicit is not None` → use it; `source="cli"`. If it deletes/removes AND meta
  says retain → append an `override_notices` entry.
- `explicit is None`:
  - meta value is `True` (a real JSON bool) → retain; `source="meta"`; append a
    `warnings` entry naming the source.
  - meta value present but NOT a `bool` (`isinstance(v, bool)` is False — note
    `isinstance(True, int)` is True, so check `bool` explicitly) → retain +
    `warnings` (malformed); `source="meta"`. NEVER `bool()`-coerce.
  - meta value `False`/absent → default (delete/remove); `source="default"`.
- `teardown_coordination = delete_branch AND remove_worktree` (coupled coord).
- Keep cyclomatic complexity ≤15 — extract a per-field helper
  `_resolve_one(explicit, raw_retain) -> (effective, source, warning, override)`
  and call it twice (branches, worktrees).

### T004 — Resolver unit tests
`tests/core/test_retention_resolver.py` — table-driven over C1–C6 plus:
- malformed values `""`, `0`, `None`, `"true"`, `"false"` each → retain + warning.
- corrupt meta → `MissionMetaReadError` raised.
- provenance (`branch_source`/`worktree_source`) asserted per case.
- `teardown_coordination` truth table (only True when both delete+remove).
Use a `tmp_path` meta.json fixture; no git needed.

## Branch Strategy
Planning base and final merge target: `fix/3131-merge-retention`. Execution
worktrees are allocated per computed lane from `lanes.json` at implement time.

## Definition of Done
- Two flat bool fields in `MissionMetaOptional`; no strict-validation change.
- `read_retention_from_meta` + `resolve_merge_retention` + `RetentionDecision`
  match `contracts/retention-resolver-contract.md` exactly.
- All resolver unit tests green; `ruff` + `mypy --strict` clean; functions ≤15.
- No git-mutating code in this WP.

## Test surface
`PWHEADLESS=1 pytest tests/core/test_retention_resolver.py -q`

## Reviewer guidance
- Verify malformed values are NOT truthiness-coerced (the data-loss trap).
- Verify the resolver mirrors `resolve_merge_target_branch` (no hand-rolled meta I/O).
- Verify no default-write of the fields (legacy missions stay field-absent).
