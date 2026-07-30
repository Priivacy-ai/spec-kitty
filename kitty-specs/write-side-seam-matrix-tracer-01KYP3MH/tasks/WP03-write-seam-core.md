---
work_package_id: WP03
title: Write-seam adoption core + generic bypasses
dependencies: []
requirement_refs:
- C-001
- FR-007
- FR-011
- FR-012
planning_base_branch: feat/write-side-seam-matrix-tracer
merge_target_branch: feat/write-side-seam-matrix-tracer
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-seam-matrix-tracer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-seam-matrix-tracer unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-write-side-seam-matrix-tracer-01KYP3MH
base_commit: 2e3d204662976db7f8bf7481b7609600439805eb
created_at: '2026-07-29T10:35:38.854895+00:00'
subtasks:
- T010
- T011
- T012
- T013
history:
- at: '2026-07-29T09:24:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
create_intent:
- src/specify_cli/coordination/write_seam.py
- tests/coordination/test_write_seam_adoption.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/coordination/write_seam.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/status/emit.py
- tests/coordination/test_write_seam_adoption.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '2663'
- '2966'
- '3033'
---

# Work Package Prompt: WP03 – Write-seam adoption core + generic bypasses

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objective

Establish **one** parameterized write-surface helper — resolve via `PlacementSeam.write_target(kind)` and materialize via `commit_for_mission` — with a **zero-write refusal** (FR-011) and **idempotent, structured results** (FR-012). Route the two generic non-domain bypasses onto it: the #2663 implement-claim partition arm and the `status/emit.py` write (#2966 slice). This is the foundation the Lane-C writers (WP04/05/07/08/10) build on. See [contracts/write-seam-adoption.md](../contracts/write-seam-adoption.md).

## Context

- The write seam already exists (`resolution.py:1430` `write_target`; `commit_router.py:127` `commit_for_mission`). ADR `2026-06-24-1` **C-006 forbids a second write resolver** — this WP does not build one; it wraps the existing authority into a reusable helper.
- **Do NOT route the seam's own engine** (`commit_router` ×4, `write_target_degrade`, `status_transition:300` FR-006 mirror, merge infra) — routing is circular.
- **Ledger-M16 recursion guard**: public boundary → seam; internal callers/leaves (`retrospective/writer.py`, the `read_dir(RETROSPECTIVE)` short-circuit) → the leaf directly. A new writer beneath the short-circuit calls the leaf/`write_target`, never `read_dir`.
- **FR-011**: the existing degrade path (`status_transition._resolve_write_target:640` → `get_feature_target_branch`) falls back to *writing* `main` on a deleted `target_branch` — this resurrects a closed defect and forecloses #3033's `CONSOLIDATED` decision. The helper MUST **refuse (zero write)** with a structured recoverable result disclosing **#3033**, never a fallback write, never a consolidation abort (`2026-07-23-2`).

## Subtasks

### T010 — The shared write-seam helper
Create `src/specify_cli/coordination/write_seam.py`: a small helper that takes a `kind` + payload + mission handle, resolves the surface via `write_target(kind)`, materializes via `commit_for_mission`, and returns a **structured result** (row/entry id + destination surface). On an unroutable target (missing coord surface, deleted `target_branch`, unknown target) it returns a **zero-write refusal** disclosing #3033 — it MUST NOT write anywhere. Re-invocation with identical inputs is a **no-op** (FR-012). Keep complexity ≤ 15 (extract helpers).

### T011 — Route #2663 (implement partition arm)
In `cli/commands/implement.py`, route `_partition_files_for_commit`'s verbatim implement-claim arm (which today commits the whole batch to coord instead of partitioning) through the helper so the partition is materialized on the correct surface. This is the write twin FR-007 unifies (stopgap shipped in PR #2662).

### T012 — Route status/emit.py (#2966 slice, route-only)
In `status/emit.py`, route the status write through the helper. **Route-only** — do not re-implement transition logic; the event log stays the sole status authority (C-003).

### T013 — Recursion-guard + refusal tests
Add `tests/coordination/test_write_seam_adoption.py`: (a) a write beneath the `read_dir(RETROSPECTIVE)` short-circuit calls the leaf/`write_target`, never `read_dir` (Ledger-M16); (b) a deleted `target_branch` yields the zero-write refusal disclosing #3033 with **no** file written; (c) idempotent re-run is a no-op.

## Branch Strategy

Both planning and merge target are `feat/write-side-seam-matrix-tracer`. Allocate via `/spec-kitty.implement WP03`.

## Definition of Done (RE-SCOPED 2026-07-29 — operator-approved)
> **T011 (#2663 implement-partition) and T012 (status/emit.py #2966) are DEFERRED → #3071.** WP03 rediscovered red-first that both collide with deliberate pinned prior-mission invariants (the #2160/C-004 verbatim-commit deferral pinned by `test_implement_coord_idempotency.py`; the literal `_commit_target_ref_for` unification pinned by `test_precondition_ref_unification.py`) — and that `status/emit.py` has no git-commit to route (pure path-I/O). Both are the #2160/#2966 clusters C-006 marks out-of-scope. See `contracts/write-seam-adoption.md` "Deferred out of this mission" + spec FR-007.
- **Delivered:** the helper (`coordination/write_seam.py::write_artifact`, T010) lands with the zero-write refusal disclosing #3033 (FR-011) + idempotent structured result (FR-012); recursion-guard + refusal tests (T013).
- `ruff`/`mypy` clean; complexity ≤ 15; the read-side census + coord-authority gate stay green.
- Tests green including the refusal + recursion-guard.

## Risks / Reviewer guidance
- **No fallback write to `main`** anywhere in the refusal path — this is the load-bearing FR-011 guarantee.
- Confirm no second write resolver is introduced (C-006) — the helper only *composes* `write_target`+`commit_for_mission`.
- Confirm the seam's own engine is not routed (circular).
- **Commit each subtask slice** (helper, then #2663, then status/emit.py) so long-running worktree progress is durable.
