---
work_package_id: WP09
title: Resolution-authority census cleanup (shrink-only)
dependencies:
- WP08
requirement_refs:
- FR-011
tracker_refs: []
planning_base_branch: design/degod-tasks-2116
merge_target_branch: design/degod-tasks-2116
branch_strategy: Planning artifacts for this mission were generated on design/degod-tasks-2116. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/degod-tasks-2116 unless the human explicitly redirects the landing branch.
subtasks:
- T037
- T038
- T039
phase: Phase 5 - Closeout
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3757021"
history:
- at: '2026-07-01T15:16:35Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: tests/architectural/resolution_gate_allowlist.yaml
create_intent:
- tests/architectural/resolution_gate_allowlist.yaml
execution_mode: code_change
owned_files:
- tests/architectural/resolution_gate_allowlist.yaml
- tests/architectural/test_resolution_authority_gates.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP09 – Resolution-authority census cleanup (shrink-only)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `randy-reducer`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

**SLIMMED WP (post-8/9 scoping decision):** the Render seam (former FR-008) and the whole-file ≤1400 shim relocation (SC-005) are **deferred to a follow-up mission** (see spec Deferred). This WP does **ONLY** the resolution-authority census cleanup — the debt the WP01–WP08 rewires created, which must land here so the arch gates are green.

- Lower `COORD_AUTHORITY_WRITE_FLOOR` from 12 → the honest re-measured live WRITE census (currently **9**), **shrink-only**.
- Resolve the 5 stale `coord_authority` allowlist entries (no live match after the rewires): `list_dependents:3568`, `list_tasks:2198`, `move_task:1138`, `move_task:1396`, `validate_workflow:2995` — **re-pin** the ones whose site merely moved (line drift), **drain** the ones whose write site was genuinely removed/reclassified (e.g. `list_dependents:3568` — WP08 removed its `resolve_feature_dir_for_mission` call).
- Fix the stale `coord_authority_baseline` scalar to the honest count; add/keep a **margin gate** so a floor set materially below the live count itself fails.
- The 4 currently-red gate tests go **green**: `test_coord_authority_gate_green_against_seeded_allowlist`, `test_every_allowlist_entry_has_live_match`, `test_coord_authority_gate_floor`, `test_allowlist_no_stale_entries`.
- Ship an **enumerated cross-base drain artifact** (each drained/re-pinned entry → the `git log <lane-base>..<mission-base>` hunk that removed/moved its write indicator) for reviewer (not-author) sign-off.

## Context & Constraints

- Read `spec.md` FR-011 + NFR-005 + the Deferred section (what's descoped and why), `research.md` D9/D10, `plan.md` IC-06.
- **This is NOT the shim WP anymore.** Do **not** touch `tasks.py`, do **not** migrate `json.dumps`, do **not** relocate orchestrators, do **not** add a LOC gate. Those are the follow-up mission's. Your only owned files are `tests/architectural/resolution_gate_allowlist.yaml` + `tests/architectural/test_resolution_authority_gates.py`.
- **Shrink-only (NFR-005/DIRECTIVE_043)**: the census may only go DOWN. Never ADD an allowlist entry to make a gate pass. Lower the floor to match the honest live count; re-pin moved entries; drain removed ones.
- **C-002 non-vacuity**: keep the permanent canonicalizer fixtures (bare-modern probe, read_primary_meta seam-internal, by-design coord writes); assert the gate still has teeth after the drain.
- **`post-merge-arch-gate-adjudication`**: verify each drain against the mission-base-vs-lane-base cross-diff (lane base ≠ mission base) — a site is only legitimately drained if the cross-diff shows it genuinely lost its write indicator in this mission.

## Branch Strategy

- **Planning base branch**: `design/degod-tasks-2116`
- **Merge target branch**: `design/degod-tasks-2116`

## Subtasks & Detailed Guidance

### T037 — Census drain + floor-lower + baseline + margin gate
Re-measure the live coord-authority WRITE census (expected 9). For each of the 5 stale entries, inspect the current `tasks.py` (which is the merged WP01–WP08 state): if the qualname still has a write-classified resolve site → **re-pin** to its new `(qualname, line)`; if the site was removed/reclassified → **drain** (remove the entry) with a one-line rationale. Lower `COORD_AUTHORITY_WRITE_FLOOR` 12 → the re-measured count (shrink-only). Fix the stale `coord_authority_baseline` scalar. Add/confirm the margin gate. Produce the enumerated cross-base drain artifact (each entry → its removing/moving hunk).

### T038 — Non-vacuity assertion
Confirm the canonicalizer gate stays non-vacuous (permanent fixtures intact); confirm 0 NEW arch-ratchet entries were introduced anywhere (shrink-only holds).

### T039 — Full arch cross-base sweep
Run `PWHEADLESS=1 pytest tests/architectural/ -q` + the mission-base-vs-lane-base cross-diff. The 4 named gate tests must be GREEN. Note any OTHER pre-existing arch failures (`test_no_tmp_paths_in_tests`, `test_pytest_marker_convention`, `test_status_module_boundary`, `test_untrusted_path_containment`, `test_gate_coverage`) that fail IDENTICALLY on the mission base — these are pre-existing (confirmed in WP08 review), NOT this WP's to fix; report them for a DIR-013 follow-up but do not expand scope.

## Test Strategy

- `PWHEADLESS=1 pytest tests/architectural/test_resolution_authority_gates.py -q` → green (the 4 named tests).
- `PWHEADLESS=1 pytest tests/architectural/ -q` → only the documented pre-existing failures remain (confirm identical on base).
- No `tasks.py` change → the golden `test_tasks_cli_contract.py` (42) is untouched; sanity-run it.

## Risks & Mitigations

- **Over-lowering the floor**: set it to the honest re-measured count (9), not lower. The margin gate + enumerated artifact + reviewer sign-off guard against masking.
- **Re-pin vs drain confusion**: a moved site is re-pinned (stays counted); only a genuinely-removed/reclassified site drains. Verify each against the cross-base diff.
- **Scope creep**: do NOT start the render/shim work — it's the follow-up mission.

## Review Guidance

- Confirm shrink-only (floor lowered to honest count, no entry added), each drain/re-pin justified by the cross-base diff, the 4 gate tests green, the gate stays non-vacuous, and `tasks.py` untouched.

## Activity Log

- 2026-07-01T15:16:35Z – system – Prompt created.
- 2026-07-02 – system – Slimmed to census-only per the 8/9 scoping decision (Render seam + shim relocation → follow-up mission).
- 2026-07-02T05:18:54Z – claude:opus:randy-reducer:implementer – shell_pid=3714542 – Assigned agent via action command
- 2026-07-02T05:42:41Z – claude:opus:randy-reducer:implementer – shell_pid=3714542 – Census cleanup: floor 12→9 (shrink-only, honest live count=9), 3 drained (move_task:1138, move_task:1396, list_dependents:3568) + 2 re-pinned (list_tasks:2198→2746, validate_workflow:2995→3814) with cross-base artifact (WP06 03be8db6e, WP08 2dda443d5), baseline 13→9, margin gate added; 4 gate tests green; non-vacuity held; tasks.py untouched; golden 42 intact. Pre-existing arch failures (test_no_tmp_paths_in_tests, test_pytest_marker_convention, test_status_module_boundary, test_untrusted_path_containment×2, test_gate_coverage×3) confirmed identical with changes stashed — reported for DIR-013 follow-up.
- 2026-07-02T05:43:48Z – claude:opus:reviewer-renata:reviewer – shell_pid=3757021 – Started review via action command
