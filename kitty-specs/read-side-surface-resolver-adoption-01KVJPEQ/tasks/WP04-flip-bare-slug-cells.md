---
work_package_id: WP04
title: Flip the bare-slug equivalence cells (by re-derivation)
dependencies:
- WP02
- WP03
requirement_refs:
- FR-003
- FR-005
- FR-008
tracker_refs: []
planning_base_branch: feat/read-side-surface-resolver-adoption
merge_target_branch: feat/read-side-surface-resolver-adoption
branch_strategy: Planning artifacts for this mission were generated on feat/read-side-surface-resolver-adoption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/read-side-surface-resolver-adoption unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2435348"
history:
- at: '2026-06-20T14:30:00Z'
  actor: claude
  note: WP authored from plan IC-03 (FR-003/FR-005/FR-008). Sanctioned cross-edit to 01KVGCE8's matrix.
agent_profile: python-pedro
authoritative_surface: tests/missions/test_surface_resolution_equivalence.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- tests/missions/test_surface_resolution_equivalence.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro`; acknowledge its initialization declaration.

## Objective
Make the bare-slug coord read reach coord **through the seam**, then flip ONLY `coord-fresh/bare` + `coord-behind/bare` from strict-xfail → GREEN. Per the operator's option-(b) decision, the low primitive `resolve_mission_read_path` stays mid8-blind by design — so the matrix's **read_path observation leg must be re-pointed to call the seam** (the mechanism that makes the cells flip; without it the cells are born-unsatisfiable). Narrow the `coord-empty/bare` + `coord-deleted/bare` xfail reasons to the REMAINING aggregate divergence. (IC-03; FR-003, FR-005, FR-008)

## Context (anti-fake-green — squad-mandated; option b)
- `tests/missions/test_surface_resolution_equivalence.py` is 01KVGCE8's matrix; this is a **sanctioned cross-edit** (the gate protocol assigns xfail-removal to the closing mission).
- **The F-4 mechanism (why the cells can flip):** the matrix's `_entry_points` returns a `resolve_mission_read_path` closure (`:304`) that calls the **raw primitive** with `(slug, mid8)`. Under option (b) the primitive is mid8-blind for a bare slug *by design* (that empty-mid8 direct call is the bypass FR-006 guards), so the closure stays RED unless its **observation target is re-pointed to the seam** `resolve_handle_to_read_path(repo_root, slug)`. Re-pointing the closure is legitimate — post-mission the canonical read path IS the seam, so the matrix should observe what a read CLI actually does. This is the ONLY mechanism that flips the cells; do NOT weaken any assertion.
- The four `*/bare` cells carry `_XFAIL_READPATH_MID8_OUT_OF_SCOPE`. `coord-fresh/bare` + `coord-behind/bare` diverge ONLY on read_path mid8-blindness → the re-pointed seam closes them. `coord-empty/bare` + `coord-deleted/bare` carry a SECOND divergence (the WP04-of-01KVGCE8 aggregate `CoordAuthorityUnavailable` seam, OUT OF SCOPE per spec FR-008) → they do NOT go fully green.

## Subtasks
### T014 — Re-point the read_path leg, then flip the two read_path-only cells
- In `_entry_points`, re-point the `resolve_mission_read_path` observation closure (`:304`) to call the seam `resolve_handle_to_read_path(repo_root, slug, require_exists=True)`. **The `require_exists=True` MUST be passed** (the seam forwards it — WP01 T002): it preserves the raise-on-missing observation for the out-of-scope `coord-empty`/`coord-deleted` `*/slug-mid8` aggregate cells, so re-pointing does NOT disturb them. Run the matrix; confirm `coord-fresh/bare` + `coord-behind/bare` now PASS (read_path-via-seam agrees with surface/aggregate). Remove EXACTLY those two `xfail` markers. **The `_assert_equivalent` body, `_observe`, the `Outcome` shape, and the `_MATRIX`/topology builders MUST be UNCHANGED** — the ONLY sanctioned `git diff` to this file is: (i) re-pointing the one `_entry_points` read_path closure, (ii) 2 removed markers, (iii) 2 narrowed reasons (T015). The `*/slug-mid8` aggregate cells MUST stay untouched.
### T015 — Narrow the two aggregate-remaining reasons (FR-008)
- `coord-empty/bare` + `coord-deleted/bare`: change their xfail reason from `_XFAIL_READPATH_MID8_OUT_OF_SCOPE` to a reason naming ONLY the remaining aggregate `CoordAuthorityUnavailable` divergence (proving the read_path leg was fixed without faking the aggregate convergence). They stay strict-xfail.
### T016 — Gates
- `PWHEADLESS=1 python -m pytest tests/missions/test_surface_resolution_equivalence.py -rA` → **0 XPASS, 0 unexpected failures**; the matrix is green-or-documented-xfail. **C-001: after rebase onto landed 01KVGCE8/main, re-verify the four `*/bare` cells + their markers still exist before editing** (they shift if 01KVGCE8 is revised). ruff clean.

## Branch Strategy
Planning/base + merge target: `feat/read-side-surface-resolver-adoption`. Worktree per lane. Depends **WP02 + WP03** (the cells flip only after the read paths adopt the seam).

## Definition of Done
- [ ] The `_entry_points` read_path closure re-pointed to the seam (the F-4 mechanism); `coord-fresh/bare` + `coord-behind/bare` GREEN; their xfail markers removed.
- [ ] `coord-empty/bare` + `coord-deleted/bare` reasons narrowed to the aggregate divergence (still strict-xfail, FR-008).
- [ ] **Assertion logic FROZEN** — diff = only (i) the one `_entry_points` read_path re-point + (ii) marker/reason edits (reviewer greps for any change to `_assert_equivalent`/`_observe`/`Outcome`/`_MATRIX`/topology builders).
- [ ] `*/slug-mid8` aggregate cells untouched (verified by diff).
- [ ] 0 XPASS / 0 unexpected; ruff clean.

## Risks / Reviewer guidance
- **Risk (fake-green)**: weakening `_assert_equivalent`/`_observe` or editing `_MATRIX` to "flip" a cell. The reviewer MUST `git diff` and confirm ONLY the read_path closure re-point + markers/reasons changed.
- **Risk (born-unsatisfiable)**: forgetting the read_path leg re-point → the cells stay RED because the raw primitive is mid8-blind by design (option b). The re-point IS the flip mechanism — confirm it is present.
- **Reviewer**: confirm the two flipped cells genuinely pass (run them); confirm the read_path closure now calls the seam; confirm the two aggregate cells stay xfail with honest narrowed reasons; do NOT let the `*/slug-mid8` aggregate cells be touched.

## Activity Log

- 2026-06-20T17:03:14Z – claude:opus:python-pedro:implementer – shell_pid=2403664 – Assigned agent via action command
- 2026-06-20T17:28:38Z – claude:opus:python-pedro:implementer – shell_pid=2403664 – read_path leg re-pointed to seam; coord-fresh/bare+coord-behind/bare GREEN; 2 reasons narrowed; assertion logic frozen; mini-mutation confirms re-point load-bearing; lane 9b212f138
- 2026-06-20T17:28:42Z – claude:opus:reviewer-renata:reviewer – shell_pid=2435348 – Started review via action command
- 2026-06-20T17:48:38Z – user – shell_pid=2435348 – reviewer-renata APPROVE: diff exactly sanctioned (read_path leg re-point + 2 markers + 2 reasons), assertion logic frozen, re-point mutation-confirmed load-bearing, 9 passed/4 xfailed/0 XPASS
