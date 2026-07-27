---
work_package_id: WP05
title: Coord-deleted convergence + public-contract migration
dependencies:
- WP04
requirement_refs:
- FR-001
- FR-004
- FR-005
- FR-008
- NFR-001
- NFR-002
tracker_refs:
- '1848'
- '2040'
- '2010'
planning_base_branch: feat/mission-surface-resolver-safety-net
merge_target_branch: feat/mission-surface-resolver-safety-net
branch_strategy: Planning artifacts for this mission were generated on feat/mission-surface-resolver-safety-net. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-surface-resolver-safety-net unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
- T026
- T027
- T028
phase: Phase 3 - Coord-deleted convergence (gate 13/0)
agent: claude:opus:python-pedro:implementer
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/aggregate.py
create_intent:
- tests/status/test_aggregate_coord_deleted_contract.py
execution_mode: code_change
mission_id: 01KVN754TY9CVJ8G10ERTMPVRH
owned_files:
- src/specify_cli/status/aggregate.py
- src/specify_cli/cli/commands/agent/status.py
- tests/status/test_aggregate_surface_resolution.py
- tests/specify_cli/missions/test_handle_equivalence_matrix.py
- tests/architectural/test_no_dead_symbols.py
- tests/status/test_aggregate_coord_deleted_contract.py
role: implementer
tags: []
wp_code: WP05
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This profile governs your implementation style, boundaries, and quality standards for this work package.

---

## 🧹 Campsite-Cleaning Directive (#1970) — ACTIVE

While inside `aggregate.py` / `status.py`, remediate adjacent issues in-slice (stale comments about the
`CoordAuthorityUnavailable` re-wrap, dead branches, type/lint nits) bounded to this mission's goal.

## Objective

Converge **coord-deleted** across all three legs onto the **`CoordinationBranchDeleted`** hard-fail
(`COORDINATION_BRANCH_DELETED`) — data loss stays hard-fail (C-001), only the exception *spelling* converges.
This drains the last cells → **gate 13/0**. Ship the `agent status` public-contract migration **in this same
slice** (editing the WP04-frozen contract is in scope by operator decision).

## ⚠️ Squad-corrected scope (read first)

Gate goes **11/2 → 13/0** (the two coord-deleted cells). The **load-bearing trap (renata SHOULD-FIX-1):**
`CoordinationBranchDeleted` SUBCLASSES `StatusReadPathNotFound`, so the aggregate's existing
`except StatusReadPathNotFound` ALREADY catches it — a flag toggle won't work; you must insert a
more-specific `except CoordinationBranchDeleted: raise` BEFORE it (+ import). The new import also flips a
dead-symbol allowlist entry → you MUST remove it or the architectural gate reds (BLOCKER-3).

## Context (verified)

- `CoordinationBranchDeleted` subclasses `StatusReadPathNotFound` (`surface_resolver.py:126`). The aggregate's
  `_resolve_read_dir` catches `except StatusReadPathNotFound` (`aggregate.py:347`) and re-wraps to
  `CoordAuthorityUnavailable` (`:349-354`) — this **already swallows** `CoordinationBranchDeleted`.
- `CoordinationBranchDeleted` is currently **allowlisted** in `_CATEGORY_C_WP_IN_FLIGHT_TOPOLOGY_AUTHORITY`
  (`tests/architectural/test_no_dead_symbols.py:494`) precisely because it has zero by-name importers today.
  Adding `import CoordinationBranchDeleted` to `aggregate.py` gives it a caller → the stale-allowlist check
  reds unless the entry is removed.
- Keep `CoordAuthorityUnavailable` **exported** (C-003) — deletion is a separate API deprecation, OUT.
- Research: `research/collapse-boundary-analysis-alphonso.md` (Q1), `research/collapse-reduction-map-randy.md` (R5-A..C), paula C6/C7/C8.

## Subtasks

### T022 — Fold the deleted-branch discriminator into the read-path leg (OUT-OF-MAP `_read_path_resolver.py`)
- **Out-of-map (WP01-owned, linearized):** under `require_exists=True`, when `coordination_branch` is declared
  but the branch is **deleted**, the read-path leg must **hard-fail `CoordinationBranchDeleted`** — route
  through WP01's `probe_coord_state` (DELETED arm = the existing `_coord_branch_exists`; no 4th copy) instead
  of returning a stale primary dir.
- **C-002 fallback (TIGHTENED):** attempt the fold FIRST. The fallback (leave the read-path coord-deleted cell
  xfail → 12/1) is permitted ONLY with a recorded live repro showing a create-window regression
  (`test_create_first_write_window_resolves_primary` / `test_unmaterialized_coord_create_window_resolves_primary`);
  a bare "risk" assertion is NOT sufficient, and the xfail reason must cite the failing test.

### T023 — Aggregate: propagate `CoordinationBranchDeleted` verbatim (except-ORDERING + import)
- In `status/aggregate.py`: **add `from ...surface_resolver import CoordinationBranchDeleted`** and insert
  `except CoordinationBranchDeleted: raise` **BEFORE** the existing `except StatusReadPathNotFound:` (`:347`)
  re-wrap. Without the more-specific handler ahead, the subclass is still caught + re-wrapped → the gate's
  `type(a) is type(b)` fails. Hard-fail preserved; only the spelling converges. Keep `CoordAuthorityUnavailable`
  exported + still raised for its remaining legitimate cases.

### T024 — Remove the now-live dead-symbol allowlist entry (BLOCKER-3) + the dangling WP04 one
- Remove `CoordinationBranchDeleted` from `_CATEGORY_C_WP_IN_FLIGHT_TOPOLOGY_AUTHORITY`
  (`test_no_dead_symbols.py:494`) — it now has a by-name caller (T020). Also remove the now-dangling
  `CoordinationWorktreeEmpty` entry + rationale (`:484-489,495`, WP04 deleted the class). Run
  `test_no_public_symbol_in_all_is_unimported` to confirm green.

### T025 — Migrate the `agent status` public contract (in-slice; status.py:165/:200)
- Add `CoordinationBranchDeleted` to the **two `except` tuples** (`cli/commands/agent/status.py:165`, `:200`)
  so the CLI surfaces the converged hard-fail identically. MUST land in THIS WP or CI reds.

### T026 — Migrate the coord-deleted contract tests
- `tests/status/test_aggregate_surface_resolution.py` + `tests/specify_cli/missions/test_handle_equivalence_matrix.py`
  (WP05-owned): update their **coord-deleted** assertions to the converged `CoordinationBranchDeleted` shape
  (their coord-empty parts were inverted by WP04). Add `tests/status/test_aggregate_coord_deleted_contract.py`
  asserting all three legs → `CoordinationBranchDeleted` / `COORDINATION_BRANCH_DELETED`.

### T027 — Campsite C6 (split-brain) + C8 (literal) — the flagged dedup wins
- **C6 (split-brain delete):** `agent/status.py:39-55 _resolve_bare_modern_mission_slug` is a byte-for-byte
  clone of `_read_path_resolver.py:645-690 resolve_bare_modern_mission_dir_name` (whose docstring `:665`
  already CLAIMS the CLI consumes it). Delete the clone; call
  `resolve_bare_modern_mission_dir_name(get_main_repo_root(repo_root), raw_handle)` at `status.py:97`; add a
  focused test that the CLI resolves a bare modern slug through the shared seam.
- **C8 (literal hoist):** once C6 removes the CLI glob clone, hoist the repeated `"meta.json"` literal in
  `aggregate._find_meta_path` (`:493/:513/:524/:534`, ≥3) to a module constant.
- Reword the now-stale `_find_meta_path:519-523` comment ("surfaces the established CoordAuthorityUnavailable
  shape") to match the converged type (randy R5-C — comment fidelity, do not delete the branch).

### T028 — Retire the coord-deleted xfail cells + delete the shared constant LAST (OUT-OF-MAP) → 13/0
- **Out-of-map (WP04-owned equivalence test, linearized):** retire the xfail on the `coord-deleted/bare` and
  `coord-deleted/slug-mid8` rows, then **delete the now-fully-unused shared constant**
  `_XFAIL_BARE_AGGREGATE_COORD_AUTHORITY_OUT_OF_SCOPE` + `_XFAIL_COORD_DELETED_SEAM_OUT_OF_SCOPE`. **Do NOT
  weaken** the `type(a) is type(b)` + `error_code` assertion. Run the gate; confirm **13 passed / 0 xfailed**
  (or 12/1 with a recorded C-002 fallback), no unexpected XPASS.

## Branch Strategy
Planning base / merge target: `feat/mission-surface-resolver-safety-net`. **WP05 is its own lane (lane-e),
`depends_on: lane-d` (WP04) → transitively lane-a (WP01).** Allocate WP05 only **after WP04 is committed +
approved** (the allocator merges WP04's approved tip in at allocation; if resuming a stale worktree, `git
merge` the WP04 lane branch first). WP01's helpers + WP04's Option B must be present before you start.

## Definition of Done
- All three legs hard-fail coord-deleted with identical `CoordinationBranchDeleted` / `COORDINATION_BRANCH_DELETED`
  (achieved via the more-specific `except … : raise` ahead of `StatusReadPathNotFound` + the read-path fold).
- `CoordAuthorityUnavailable` remains exported; both `agent status` `except` tuples migrated; the two dead-symbol
  allowlist entries removed (`test_no_public_symbol_in_all_is_unimported` green).
- C6 clone deleted (CLI calls the shared seam); C8 literal hoisted.
- Equivalence gate **13/0** (or 12/1 with recorded C-002 fallback), assertion un-weakened, shared constant deleted last.
- `ruff` + `mypy` clean. Campsite noted.

## Risks & Reviewer Guidance
- **HIGHEST blast radius.** Confirm the `except CoordinationBranchDeleted: raise` sits BEFORE
  `except StatusReadPathNotFound` (else the subclass is still swallowed — the convergence silently fails the
  gate). Confirm BOTH dead-symbol allowlist entries removed (the `CoordinationBranchDeleted` one is a CI red,
  the `CoordinationWorktreeEmpty` one is dangling). Confirm `CoordAuthorityUnavailable` still imports. Confirm
  the read-path fold did NOT regress #1718 (or the C-002 fallback cites a real failing test). Confirm the gate
  is 13/0 with the assertion intact and the shared constant deleted only here (last).

## Activity Log
- 2026-06-21T14:42:27Z – system – WP05 prompt generated via /spec-kitty.tasks
