---
work_package_id: WP01
title: Canonical seam core (compose/parse/worktree grammar + failover)
dependencies: []
requirement_refs:
- FR-001
- FR-003
- FR-004
- FR-005
- FR-009
- NFR-003
tracker_refs: []
planning_base_branch: mission/mission-identity-seam-and-1908-panel
merge_target_branch: mission/mission-identity-seam-and-1908-panel
branch_strategy: Planning artifacts for this mission were generated on mission/mission-identity-seam-and-1908-panel. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/mission-identity-seam-and-1908-panel unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mission-identity-seam-and-1908-panel-01KV6510
base_commit: c04971966f95e50fb5182ace7f50b99ceb998b03
created_at: '2026-06-15T18:57:24.231621+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Seam foundation
assignee: ''
agent: claude
shell_pid: '1013856'
history:
- at: '2026-06-15T17:53:20Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/lanes/branch_naming.py
create_intent:
- tests/lanes/test_branch_naming_seam.py
execution_mode: code_change
owned_files:
- src/specify_cli/lanes/branch_naming.py
- tests/lanes/test_branch_naming_seam.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Canonical seam core

## ⚡ Do This First: Load Agent Profile
Use the `/ad-hoc-profile-load` skill to load the profile in the frontmatter before parsing the rest of this prompt.
- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## Objectives & Success Criteria
Make `src/specify_cli/lanes/branch_naming.py` the **single canonical authority** for the
`slug↔mid8↔branch/worktree-name` grammar. Everything else in this mission consumes the API you
add/fix here. Read [spec.md](../spec.md) FR-001/003/004/005, [research.md](../research.md)
R1/R3, and [plan.md](../plan.md) IC-01.

**Done when:**
- Compose is **idempotent** and the new resolve/worktree API exists; the round-trip property test
  passes; ruff + mypy clean; no behavior change for existing callers (byte-identical names).

## Context & Constraints
- The seam already exists (compose: `mission_branch_name` L148 / `mission_branch_name_required`
  L208 / `lane_branch_name` L340; parse: `mid8_from_slug` L116 / `parse_*` / `is_*`). This WP fixes
  bugs **inside** it and **adds** the worktree grammar + failover resolver — it does not rewrite it.
- **TDD-first (C-001):** write the failing regression/property tests first, then make them pass.
- **Idempotency-preserving:** the on-disk/branch forms must be byte-identical for existing inputs
  (a slug already embedding its mid8 stays as-is) — downstream WPs route call sites assuming no churn.
- Honor the existing `BranchIdentityUnresolved` fail-closed error; legacy `NNN-` era stays supported.

> **Squad note (verified):** `mission_branch_name` (L165) AND `lane_branch_name` (L379) **already**
> call `_human_slug_for_mid8_branch` — so #1949's double-append is **already fixed** on the
> `mission_id`-present path. T001 is therefore a **regression-LOCK** plus closing the one real residual
> (the `mission_id is None` branches at L167/L382 do NO dedup). Do not write a tautological
> "no-double-append" test and call #1949 done.

## Subtasks
### T001 — Idempotent compose: regression-lock + close the `mission_id=None` residual (#1949)
- **Steps:** (a) Add a **characterization/lock** test asserting both composers stay single-mid8 for an
  embedded slug WITH `mission_id` (expected GREEN already — label it a lock, not a fix). (b) Find the
  genuine residual: the `mission_id is None` branches (L167 `mission_branch_name`, L382
  `lane_branch_name`) skip `_human_slug_for_mid8_branch` and can double/mis-compose for an embedded
  slug passed with no `mission_id`. Make those branches idempotent too (strip-when-embedded), or
  fail-closed if the embedded tail can't be confirmed. The genuinely-RED test is the `mission_id=None`
  embedded-slug case.
- **Files:** `branch_naming.py`.

### T002 — Demote `mid8_from_slug` IN PLACE + add authoritative `resolve_mid8` (#1918, FR-004)
- **Steps:** (a) `mid8_from_slug` MUST NOT assume any trailing 8-Crockford-char segment is a mid8 —
  decline (keep its `str` return, return `""`) on a coincidental tail when there is no `mission_id`
  to confirm against; docstring: heuristic detector, never authoritative on a correctness path.
  (b) Add an **authoritative** `resolve_mid8(mission_slug, *, mission_id: str | None) -> str` that
  derives the mid8 from a declared `mission_id` (primary) and only falls back to the embedded tail
  when it provably matches. (c) **Do not regress the two final-fallback consumers** —
  `resolve_transaction_mid8` (L244) and `coordination.surface_resolver._coord_mid8` use
  `mid8_from_slug` as their tail fallback; T002's regression set MUST prove a genuine embedded-mid8
  slug still resolves through them (callers are routed in WP06/WP10, but WP01 must keep the detector
  honest for both the decline AND the accept case).
- **Files:** `branch_naming.py`.

### T003 — Canonical-first / legacy-failover resolve path (FR-004)
- **Steps:** Add (or adapt) the resolve path so it tries the **new style first**
  (`(slug, mission_id)` / `slug+mid8`) and only falls over to legacy (`NNN-`/bare) on a miss,
  emitting a **one-shot deprecation warning** (reuse the project's one-shot warning mechanism, like
  `selector_resolution`'s suppress-env pattern). Legacy is a warned compatibility branch, not a
  co-equal parser — resolution stays deterministic.
- **Files:** `branch_naming.py`.

### T004 — Worktree + coordination grammar primitives (#1899, FR-005, FR-010 target)
- **Steps:** (a) Add `worktree_dir_name(mission_slug, *, mission_id, lane_id)` that reproduces the
  **current on-disk grammar EXACTLY in BOTH modes**: `mission_id=None` ⇒ legacy `{slug}-{lane_id}`
  (no mid8 — matches today's `f"{mission_slug}-{lane_id}"` allocator/lifecycle f-strings), `mission_id`
  present ⇒ `lane_branch_name(...).removeprefix("kitty/mission-")`. Derive from one grammar; prove
  byte-identical for BOTH a legacy `NNN-` slug AND an embedded slug. (b) Add emit-don't-guess
  `worktree_path(repo_root, mission_slug, *, mission_id, lane_id)`. (c) **Add the bare mission-dir
  primitive WP06 needs:** `mission_dir_name(mission_slug, *, mid8)` (bare `<slug>-<mid8>`, NO lane)
  and the coord derivations (`coord_branch_name`, `coord_dir_name` with the `-coord` suffix) so the
  coordination/missions composers have a real non-lane delegation target. All idempotency-preserving.
- **Files:** `branch_naming.py`.

### T005 — Golden-value table + round-trip property test (NFR-003, FR-005) + TDD failing-first
- **Steps:** Create `tests/lanes/test_branch_naming_seam.py`. (a) Write a **shared golden-value table**
  fixture: for canonical inputs — one legacy `NNN-foo` (mission_id=None) AND one embedded
  `foo-01KV6510` (mission_id set) × lane-a — the expected EXACT branch / lane-branch / worktree-dir /
  mission-dir / coord-dir / coord-branch strings. This table is the binding byte-identical oracle that
  WP03/04/05/06 import. (b) FAILING-FIRST regressions: #1949 `mission_id=None` embedded double, #1918
  coincidental tail. (c) Property test keyed on `(slug, mission_id)`: compose is a fixpoint and
  round-trips for embedded==mid8, embedded≠mid8 (fail-closed/decline), coincidental tail (decline),
  legacy `NNN-` (one warning). Assert `worktree_dir_name` matches the golden table for BOTH the
  legacy (no-mid8) and embedded rows.
- **Files:** `tests/lanes/test_branch_naming_seam.py`.

### T006 — Gates
- **Steps:** `ruff check` (incl. `--select C901` complexity) + `mypy` on `branch_naming.py` (zero new
  issues; extract helpers if any function nears 15). Hoist any repeated grammar/warning literal to a
  module constant (Sonar S1192). Run
  `PWHEADLESS=1 pytest tests/lanes/test_branch_naming_seam.py tests/lanes/ -q`.
- **Validation:** [ ] golden table + property test green; [ ] #1949 `mission_id=None` case was RED
  first; [ ] legacy AND embedded worktree-dir both byte-identical; [ ] `resolve_mid8` added;
  [ ] existing branch-naming tests still pass; [ ] ruff/mypy/C901 clean.

## Branch Strategy
- Planning base / merge target: `mission/mission-identity-seam-and-1908-panel`.
- Lane-per-WP from `lanes.json`; worktrees allocated per computed lane.

## Definition of Done
All 6 subtasks complete; idempotent compose (incl. the `mission_id=None` residual) + demoted
`mid8_from_slug` + authoritative `resolve_mid8` + failover + worktree grammar (legacy-faithful both
modes) + bare `mission_dir_name`/coord derivations + the shared golden-value table all landed;
property test green; byte-identical names verified for BOTH legacy and embedded slugs; ruff/mypy/C901
clean. This WP is the API foundation for WP02–WP06 and WP10 — they cannot route without it.

## Reviewer Guidance
Confirm: (1) #1949 lock test + the genuinely-RED `mission_id=None` residual fix (not a tautology);
(2) `mid8_from_slug` declines on coincidental tails BUT a real embedded mid8 still resolves through
`resolve_transaction_mid8`/`_coord_mid8` (no new fail-close); (3) `resolve_mid8` is the authoritative
correctness-path API; (4) `worktree_dir_name(mission_id=None)` == legacy `{slug}-{lane}` (no mid8) and
`worktree_dir_name(mission_id=…)` == embedded form — both proven against the golden table; (5) bare
`mission_dir_name`/coord derivations exist for WP06; (6) failover emits exactly one warning, prefers
canonical; (7) existing tests unaffected.
