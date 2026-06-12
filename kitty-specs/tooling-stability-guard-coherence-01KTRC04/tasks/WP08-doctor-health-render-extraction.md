---
work_package_id: WP08
title: doctor.py health-render extraction (pure move)
dependencies: []
requirement_refs:
- FR-006
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-tooling-stability-guard-coherence-01KTRC04
base_commit: add42e46c5442ecd2d1c8c00015fab3fa5c727f1
created_at: '2026-06-10T14:50:29.973850+00:00'
subtasks:
- T031
- T032
- T033
phase: Phase 1 - Independent lanes
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "92560"
history:
- at: '2026-06-10T11:47:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/cli/commands/doctor.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/doctor.py
- src/specify_cli/cli/commands/_profile_health_render.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – doctor.py health-render extraction

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load`; pick the best implementer match if none assigned.

---

## Objectives & Success Criteria
#1623 (DIRECTIVE_013 / adversarial finding I-10): `doctor.py` (3,271 LOC) grew doctrine health-render helpers
during mission 01KT1TV1 that belong beside `_doctrine_health.py`.
- **Pure extraction**: move the self-contained doctrine/profile health-RENDER helpers into a new
  `_profile_health_render.py` beside `_doctrine_health.py`; repoint `doctor.py` imports. **ZERO behavior change.**
- **The full god-module split of doctor.py is explicitly OUT of scope** (FR-006 narrowing) — extract ONLY the
  ticketed render helpers; resist the temptation.
- **Done when:** render output is byte-identical for identical inputs; doctor tests green; `doctor.py` line count reduced by the extracted helpers' size.

## Context & Constraints
- Design (absolute): `kitty-specs/tooling-stability-guard-coherence-01KTRC04/{spec.md (FR-006), plan.md (IC-07), contracts/ (C-DOC-1)}` + ticket #1623 (names the source: profile-diagnostic rendering from mission `org-doctrine-profile-integrity-activation-closure-01KT1TV1`; see its `adversarial-review-debrief.md` I-10 for the helper inventory).
- Identify the helpers by their cohesion with `_doctrine_health.py`'s domain (profile-diagnostic/doctrine health rendering) — typically `_render_*`/`_format_*` functions consumed only by the doctrine-health command paths.

## Branch Strategy
- Planning base / merge target: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance

### T031 — Identify + extract
- Inventory the doctrine/profile health-render helpers in `doctor.py` (use the I-10 debrief as the source list); move them verbatim (no edits beyond import fixes) to `_profile_health_render.py` with `__all__` (C-007).

### T032 — Repoint + identical-output verification
- `doctor.py` imports from the new module. Verify behavior-preservation: capture the rendered doctrine-health output (e.g. `spec-kitty doctor doctrine --json` + the human render on a fixture project) BEFORE and AFTER — byte-identical (or snapshot-test it).

### T033 — Gates
- `pytest` doctor suites green; `ruff`+`mypy` clean on both files; line-count delta reported in the handoff note.

## Definition of Done
- Pure move proven (diff shows relocation + import edits only); identical output; gates green.

## Risks & Mitigations
- *Accidental logic edits* → reviewer diffs the moved bodies against the originals (should be verbatim).
- *Scope creep into the full split* → out of scope; flag any tempting follow-ups in the activity log instead.

## Review Guidance
- Recommended: **reviewer-renata**. Diff-review: moved bodies verbatim; zero behavior change; no scope creep.

## Activity Log
- 2026-06-10T11:47:55Z – system – Prompt created.
- 2026-06-10T15:07:43Z – user – shell_pid=38158 – Pure extraction (#1623/I-10): moved 7 doctrine/profile health-RENDER helpers + _SELECTION_KIND_PLURALS + shared console singleton from doctor.py to new sibling _profile_health_render.py (beside _doctrine_health.py), with __all__. Helpers (verbatim bodies, import fixes only): _render_pack_invalid_profiles, _render_doctrine_pack, _emit_doctrine_human, _emit_doctrine_json, _emit_doctrine_no_packs, _render_org_layer_section, _render_selection_block_lines. doctor.py re-imports all 7 (4 via redundant-alias re-export form) so the test-facing import surface is unchanged. Collectors (_collect_profile_health/_attach_pack_health/_build_pack_entries/_collect_org_layer_data/_collect_doctrine_collisions) + doctrine command STAY in doctor.py (render-only scope; full god-module split OUT of scope per FR-006). Identical-output evidence: spec-kitty doctor doctrine --json AND human render captured before/after = BYTE-IDENTICAL (diff empty). All 7 fn bodies verified verbatim via awk-extract diff. Gates: ruff clean on all 3 files; mypy package-aware clean on new module, doctor.py has ZERO new errors (21 pre-existing on HEAD baseline, identical set, line-shifted only); terminology guard pass. Tests: 409 doctor tests pass (28 in the 3 doctrine suites). One white-box test (test_doctor_doctrine.py:299) updated to patch _profile_health_render.console (canonical owner of the now-moved renderer) — faithful, not behavior change; guard emitted ACTIVE_WP_SCOPE_VIOLATION WARNING (non-blocking) for the test file, justified. LOC delta: doctor.py 3271->3011 (-260); new module 337 LOC. Commit d5d9df851bd9b4bc6221be874d2905229b718bd6.
- 2026-06-10T15:17:08Z – claude:opus:reviewer-renata:reviewer – shell_pid=92560 – Started review via action command
- 2026-06-10T15:25:13Z – user – shell_pid=92560 – Review passed (reviewer-renata): PURE MOVE verified byte-identical. AST-extracted bodies of all 7 render helpers (_render_pack_invalid_profiles, _render_doctrine_pack, _emit_doctrine_human, _emit_doctrine_json, _emit_doctrine_no_packs, _render_org_layer_section, _render_selection_block_lines) + _SELECTION_KIND_PLURALS are IDENTICAL between pre-move doctor.py and new _profile_health_render.py, and all moved out of doctor.py. Console singleton: doctor.py re-imports the single console instance from new module (no reassignment) = one Console. Test-facing import surface preserved via redundant-alias re-exports. Scope: render-only moved; collectors+doctrine command stayed; full split NOT attempted; one test edit repatches console on canonical owner module (faithful adaptation, not behavior change). Gates: ruff clean both files; mypy new module clean, doctor.py 21 errors before AND after (zero new); doctor doctrine suite 19/19, broader doctor+selections-snapshot 170/170. LOC: doctor.py 3271->3011 (-260); new module 337 w/ __all__. NOTE: --force used because an orphaned non-registered worktree (.worktrees/01KTRC04-lane-h on target branch) caused move-task to misresolve the lane worktree and falsely report 'no impl commits'; commit d5d9df851 verifiably exists on registered lane worktree tooling-...-lane-h ahead of target.
