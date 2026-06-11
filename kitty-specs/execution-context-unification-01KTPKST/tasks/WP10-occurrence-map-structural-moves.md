---
work_package_id: WP10
title: Occurrence-map structural-move extension (#1815)
dependencies: []
requirement_refs:
- FR-010
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
phase: Phase 0 - Adjacent
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3763005"
history:
- at: '2026-06-09T17:17:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/bulk_edit/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/bulk_edit/**
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP10 – Occurrence-map structural-move extension

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load`; if none set, pick an implementer profile for `code_change` on `src/specify_cli/bulk_edit/`.

---

## Objectives & Success Criteria
- Per operator decision, **extend** the occurrence-map schema + the `spec-kitty-bulk-edit-classification` skill/doctrine to model **multi-path structural moves** (`moves: [{from: [...], to: ...}]`) in addition to the 8 single-term-rename categories — one artifact, broader schema (FR-010, #1815).
- **Backward-compatible (C-OMAP-1):** an existing single-term map (8 categories, no `moves:`) validates and gates exactly as before.
- **Done when:** schema + gate + classification skill handle `moves:`; legacy maps unchanged; tests cover both shapes.

## Context & Constraints
- Design: `spec.md` FR-010; `plan.md` IC-10; `contracts/...` C-OMAP-1; `data-model.md` occurrence-map schema extension.
- This is the mechanism gap that #1815 filed when the paused mission 01KTNWFC's structural restructure could not be expressed as single-term renames.
- This mission itself is NOT `change_mode: bulk_edit` — WP10 improves the *mechanism* for future missions.
- Edit SOURCE doctrine (CLAUDE.md): the bulk-edit-classification skill source lives under `src/doctrine/` (or the skill source tree) — locate it; editing it is an expected out-of-map edit (record a one-line rationale).

## Branch Strategy
- **Planning base / merge target**: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance
### T031 — Extend schema with `moves:`
- Add an optional `moves:` block to `bulk_edit/occurrence_map.py`; keep the 8 categories optional/unchanged.
### T032 — Update gate/inference/diff_check
- `bulk_edit/gate.py` + `inference.py` + `diff_check.py` validate/handle `moves:` (multi-path from→to), including the implement-gate path-heuristic for `do_not_change` blocks.
### T033 — Update classification skill/doctrine
- Teach the `spec-kitty-bulk-edit-classification` skill the moves model (out-of-map doctrine edit + rationale).
### T034 — Backward-compat test
- Prove a legacy single-term map validates unchanged (C-OMAP-1); add a `moves:` map test.

## Test Strategy
- Backward-compat + `moves:` tests; `ruff`+`mypy` zero issues; terminology guard (`tests/architectural/test_no_legacy_terminology.py`) green for any doctrine prose touched.

## Risks & Mitigations
- *Schema regression* → keep `moves:` optional; never reject legacy maps; version the schema if needed.

## Review Guidance
- Recommended: **architect-alphonso** + **doctrine/charter** sign-off (schema + doctrine), **reviewer-renata** standard.

## Activity Log
- 2026-06-09T17:17:15Z – system – Prompt created.
- 2026-06-09T20:26:03Z – claude:opus:python-pedro:implementer – shell_pid=3730248 – Assigned agent via action command
- 2026-06-09T20:32:58Z – claude:opus:python-pedro:implementer – shell_pid=3730248 – Occurrence-map moves: schema (optional moves: block in occurrence-map.schema.yaml + MoveEntry/parse/validate in occurrence_map.py) + gate (diff_check exempts declared move source/destination paths from do_not_change heuristic) + skill (spec-kitty-bulk-edit-classification SKILL.md + template document moves) + backward-compat (legacy 8-category maps validate/gate exactly as before, C-OMAP-1). 107 bulk_edit tests + 17 new move tests green; ruff/mypy clean; terminology guard green.
- 2026-06-09T20:46:01Z – claude:opus:reviewer-renata:reviewer – shell_pid=3763005 – Started review via action command
- 2026-06-09T20:50:03Z – user – shell_pid=3763005 – Review passed: WP10 occurrence-map structural-moves (#1815). C-OMAP-1 backward-compat verified independently (hand-built legacy 8-cat map + null-moves: empty moves, validates/admits/schema all green, do_not_change still blocks). moves: schema (T031) optional, additionalProperties:false, MoveEntry VO sane. Gate (T032): precedence exceptions->moves->category correct; path matching exact/glob(**)/dir-prefix with proper / boundary (src/auth NOT matching src/authentication); non-declared do_not_change still blocks. Doctrine (T033) edits are SOURCE (src/doctrine/ schema+SKILL.md+template), template moves block commented-out=backward-safe. Gates: 107 bulk_edit tests pass, ruff clean, mypy clean on 3 changed files, terminology guard 2/2 pass. Scope clean. No dead code (MoveEntry/.moves live in assess_file gate). No synthetic fixtures. Note: from:[**] move exempts all paths but map is reviewer-authored artifact; acceptable by-design, not a gate-bypass.
