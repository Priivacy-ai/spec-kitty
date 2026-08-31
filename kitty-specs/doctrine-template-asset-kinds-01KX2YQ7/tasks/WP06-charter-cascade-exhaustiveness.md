---
work_package_id: WP06
title: Charter-cascade exhaustiveness + context.py:500
dependencies: [WP01]
requirement_refs:
- FR-012
tracker_refs: []
planning_base_branch: feat/doctrine-template-asset-kinds-2495
merge_target_branch: feat/doctrine-template-asset-kinds-2495
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-template-asset-kinds-2495. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-template-asset-kinds-2495 unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
- T026
phase: Phase 4 - Exhaustiveness (charter)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1804330"
history:
- at: '2026-07-09T10:15:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- tests/charter/test_kind_cascade_exhaustive.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/synthesizer/project_drg.py
- src/charter/consistency_check.py
- src/charter/_activation_render.py
- src/charter/context.py
- src/charter/pack_manager.py
- src/charter/kind_vocabulary.py
- src/specify_cli/cli/commands/charter/list_cmd.py
- tests/charter/test_drg_filtering.py
- tests/charter/test_kind_cascade_exhaustive.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Charter-cascade exhaustiveness + context.py:500

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` for the frontmatter profile before parsing the rest.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Cover every charter-layer kind-keyed map and filter so both new members are handled — including the **4th
TEMPLATE-exclusion filter** the totality guard cannot see and the four `.get`-defaulted partials.

Done when:
- `context.py:500` (`_render_generic_artifact_include` bare-probe) excludes ASSET **and** TEMPLATE via the
  canonical `_NON_AUGMENTATION_ELIGIBLE_KINDS` (or a shared "not bare-probeable" predicate) — not a private
  `is not TEMPLATE`.
- `pack_manager.py` (`YAML_KEY_MAP` derived from `CHARTER_KIND_TOKENS` auto-excludes the two; the `.get`-partials
  `_PROJECT_KIND_DIRS:132` / `_ID_FIELD_BY_KIND:225` stay None-safe) and `kind_vocabulary.py`
  (`_ID_FIELD_BY_KIND:75` / `_PROJECT_KIND_DIRS:79`) handle both members.
- `project_drg::_KIND_TO_NODE_KIND` uses `.get` (not a raising subscript), and `consistency_check.py`,
  `_activation_render.py`, `list_cmd::_KIND_ORDER`, and `test_drg_filtering.py` cover both members.
- A cascade-exhaustiveness test asserts the charter surfaces don't crash/drop for template/asset.

## Context & Constraints

- Plan IC-02 (context.py:500) + IC-05 (cascade). Research **D-11, D-13**. Spec **FR-012**.
- Ground truth: `charter/context.py:500` (`member is not ArtifactKind.TEMPLATE` comprehension; comment
  `:493-495` — templates are qualified IDs not bare-probeable; ASSET is identically non-bare-probeable);
  `charter/kind_vocabulary.py:75/79`; `charter/pack_manager.py:120` `YAML_KEY_MAP`, `:132`/`:225` partials;
  `charter/synthesizer/project_drg.py:44` `_KIND_TO_NODE_KIND` (raises on unknown → make `.get`);
  `cli/commands/charter/list_cmd.py:34` `_KIND_ORDER = list(CHARTER_KIND_TOKENS)` (auto-excludes once WP01 lands).
- Import `_NON_AUGMENTATION_ELIGIBLE_KINDS` from `artifact_kinds.py` (WP01) — do not redefine.
- Depends on **WP01**.

## Branch Strategy
- **Planning base branch**: feat/doctrine-template-asset-kinds-2495
- **Merge target branch**: feat/doctrine-template-asset-kinds-2495
- **Strategy**: feature-branch (worktree per lane from `lanes.json`)

## Subtasks & Detailed Guidance

### T022 – `context.py:500` bare-probe filter → canonical set
- **Steps**: replace the `member is not ArtifactKind.TEMPLATE` filter with `member not in
  _NON_AUGMENTATION_ELIGIBLE_KINDS` (or a shared predicate). Verify ASSET no longer gets an unqualified
  `asset:<identifier>` probe. This is a comprehension the totality guard won't catch — cover it with a direct test.
- **Files**: `src/charter/context.py`.

### T023 – `pack_manager` + `kind_vocabulary` partials
- **Steps**: confirm `YAML_KEY_MAP` (derived from `CHARTER_KIND_TOKENS`) auto-excludes template/asset; ensure the
  `.get`-partials `_PROJECT_KIND_DIRS`/`_ID_FIELD_BY_KIND` in both `pack_manager.py` and `kind_vocabulary.py`
  remain None-safe for the new members (no raising access, no crash).
- **Files**: `src/charter/pack_manager.py`, `src/charter/kind_vocabulary.py`.

### T024 – Node-kind map + consistency + render
- **Steps**: change `project_drg::_KIND_TO_NODE_KIND` from a raising subscript to `.get` (unknown → skip/None,
  documented); verify `consistency_check.py` and `_activation_render.py` don't crash/drop for template/asset.
- **Files**: `src/charter/synthesizer/project_drg.py`, `src/charter/consistency_check.py`,
  `src/charter/_activation_render.py`.

### T025 – `_KIND_ORDER` + filtering coverage
- **Steps**: confirm `list_cmd::_KIND_ORDER` excludes template/asset (derived from `CHARTER_KIND_TOKENS`); add
  member coverage in `tests/charter/test_drg_filtering.py`.
- **Files**: `src/specify_cli/cli/commands/charter/list_cmd.py`, `tests/charter/test_drg_filtering.py`.

### T026 – Cascade-exhaustiveness test
- **Steps**: new `tests/charter/test_kind_cascade_exhaustive.py` — assert each owned charter surface handles a
  `template` and an `asset` kind without KeyError/crash/drop, and that `context.py:500` excludes ASSET.
- **Files**: `tests/charter/test_kind_cascade_exhaustive.py`.

## Test Strategy
`pytest tests/charter/test_kind_cascade_exhaustive.py tests/charter/test_drg_filtering.py -q`. Add a **direct**
test for the `context.py:500` exclusion (the totality guard cannot see comprehensions).

## Risks & Mitigations
- **Invisible filter**: the `context.py:500` comprehension is exactly what slips past the guard — it is this WP's
  headline; do not leave a private `is not TEMPLATE`.
- **Raising subscript**: `_KIND_TO_NODE_KIND` must become `.get`.

## Review Guidance
- Confirm no private single-member exclusion survives in the charter cascade and the `.get`-partials stay
  None-safe. Confirm the direct context-probe test exists.

## Activity Log
- 2026-07-09T10:15:17Z – system – Prompt created.
- 2026-07-09T11:02:48Z – claude:sonnet:python-pedro:implementer – shell_pid=1684490 – Assigned agent via action command
- 2026-07-09T11:20:54Z – claude:sonnet:python-pedro:implementer – shell_pid=1684490 – Ready: T022 context.py:500 now filters via canonical _NON_AUGMENTATION_ELIGIBLE_KINDS (was private is-not-TEMPLATE); T024 project_drg._KIND_TO_NODE_KIND is .get-based (unsupported kind -> skip node+edges, no crash); T023/T025 verified pack_manager/kind_vocabulary/list_cmd already None-safe/exclude template+asset via CHARTER_KIND_TOKENS; new tests/charter/test_kind_cascade_exhaustive.py + additions to test_drg_filtering.py. pytest tests/charter -q: 1430 passed, 1 skipped. ruff check (4 files): exit 0. mypy --strict (2 src files): exit 0.
- 2026-07-09T11:22:44Z – claude:opus:reviewer-renata:reviewer – shell_pid=1804330 – Started review via action command
- 2026-07-09T11:31:33Z – user – shell_pid=1804330 – Review passed: context.py:500 filters via imported _NON_AUGMENTATION_ELIGIBLE_KINDS (ASSET+TEMPLATE both excluded); no private is-not-TEMPLATE remains; headline direct test mutation-proven test-locked (reverting to is-not-TEMPLATE fails at assert 'asset' not in queried). project_drg._KIND_TO_NODE_KIND .get-based, unknown->skip via documented continue. pack_manager/kind_vocabulary .get-partials None-safe; YAML_KEY_MAP/_KIND_ORDER derive from CHARTER_KIND_TOKENS excluding both. Commit clean of synthesis-manifest.yaml (test-leak restored). ruff+mypy clean; 34 WP tests pass; tests/charter 1430 passed 1 skipped.
