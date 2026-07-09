---
work_package_id: WP02
title: Loader universe + lockstep charter mirrors
dependencies: [WP01]
requirement_refs:
- FR-001
- FR-003
- FR-004
- FR-007
- FR-011
tracker_refs: []
planning_base_branch: feat/doctrine-template-asset-kinds-2495
merge_target_branch: feat/doctrine-template-asset-kinds-2495
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-template-asset-kinds-2495. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-template-asset-kinds-2495 unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
phase: Phase 2 - Node-declarable universe
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1769942"
history:
- at: '2026-07-09T10:15:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/org_pack_loader.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/org_pack_loader.py
- src/charter/activations.py
- src/charter/pack_context.py
- tests/doctrine/test_org_pack_augmentation.py
- tests/charter/test_pack_context.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Loader universe + lockstep charter mirrors

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` for the frontmatter profile before parsing the rest.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Make `templates` and `assets` **node-declarable** org-pack DRG kinds, drive the augmentation exclusion off the
canonical set from WP01, and move the two **locked** charter mirrors in lockstep so the drift-guard stays green.

Done when:
- `_ORG_DRG_KIND_ALIASES` / `_ORG_DRG_CANONICAL_KINDS` include `templates` and `assets`.
- `AUGMENTATION_ELIGIBLE_KINDS` / `_AUGMENTATION_GLOBS` are derived via `kind not in
  _NON_AUGMENTATION_ELIGIBLE_KINDS` (imported from `artifact_kinds.py`) — no `is not TEMPLATE`.
- `charter/activations.py::_ALLOWED_KINDS` and `charter/pack_context.py::_BUILTIN_ARTIFACT_KINDS` move in
  lockstep (the drift-guard `test_org_pack_augmentation.py::test_lockstep_drift_guard` passes).
- Templates/assets are node-declarable but NOT augmentation-eligible and NOT charter-activatable.

## Context & Constraints

- Plan IC-01 + IC-02 (consumption). Research **D-03**; spec **FR-001/003/004/007/011**; the lockstep contract in
  `contracts/asset-kind.md`.
- Ground truth: `org_pack_loader.py:86` `_ORG_DRG_KIND_ALIASES`; `:144-151`/`:176-180` augmentation
  comprehensions; `charter/activations.py:139` `_ALLOWED_KINDS`; `charter/pack_context.py:56`
  `_BUILTIN_ARTIFACT_KINDS`; the drift-guard test `tests/doctrine/test_org_pack_augmentation.py:362-384`.
- **Import** `_NON_AUGMENTATION_ELIGIBLE_KINDS` from `artifact_kinds.py` (WP01) — do not redefine it (single
  canonical authority).
- `_OrgDRGNode` stays **unchanged** (identity-only) — asset metadata is sidecar-only (D-08). Do not add `mime`.
- Depends on **WP01**.

## Branch Strategy
- **Planning base branch**: feat/doctrine-template-asset-kinds-2495
- **Merge target branch**: feat/doctrine-template-asset-kinds-2495
- **Strategy**: feature-branch (worktree per lane from `lanes.json`)

## Subtasks & Detailed Guidance

### T006 – Node-declarable universe += templates, assets
- **Steps**: add `templates` and `assets` to `_ORG_DRG_KIND_ALIASES` and `_ORG_DRG_CANONICAL_KINDS`. Confirm the
  singular/plural resolution matches the 9 existing kinds' pattern.
- **Files**: `src/doctrine/drg/org_pack_loader.py`.

### T007 – Augmentation exclusion off the canonical set
- **Steps**: rewrite `AUGMENTATION_ELIGIBLE_KINDS` (`:144-151`) and `_AUGMENTATION_GLOBS` (`:176-180`) to exclude
  via `kind not in _NON_AUGMENTATION_ELIGIBLE_KINDS`. Both templates and assets must be excluded.
- **Files**: `src/doctrine/drg/org_pack_loader.py`.

### T008 – Move the lockstep mirrors
- **Steps**: add `templates` + `assets` to `charter/activations.py::_ALLOWED_KINDS` and
  `charter/pack_context.py::_BUILTIN_ARTIFACT_KINDS` **in the same WP** — the drift-guard asserts
  `_ORG_DRG_CANONICAL_KINDS == _ALLOWED_KINDS (normalised) ∪ {mission_types}`, so a partial move is guaranteed-red.
- **Files**: `src/charter/activations.py`, `src/charter/pack_context.py`.

### T009 – Tests
- **Steps**: update `test_org_pack_augmentation.py` (eligible-set no longer contains templates/assets; the
  lockstep drift-guard passes) and `tests/charter/test_pack_context.py` (defaults include the two new kinds).
  Add an assertion that a `template`/`asset` kind is node-declarable yet excluded from augmentation.
- **Files**: `tests/doctrine/test_org_pack_augmentation.py`, `tests/charter/test_pack_context.py`.

## Test Strategy
`pytest tests/doctrine/test_org_pack_augmentation.py tests/charter/test_pack_context.py -q`. Because the
drift-guard is red until all three mirrors move, land T006+T007+T008 together before running.

## Risks & Mitigations
- **Split-brain**: if augmentation still uses `is not TEMPLATE` anywhere, ASSET leaks in — route everything
  through the imported set.
- **Lockstep red**: expected mid-edit; resolve by completing T008 before test.

## Review Guidance
- Verify all three mirrors moved together and no private single-member exception survives. Confirm `_OrgDRGNode`
  is untouched.

## Activity Log
- 2026-07-09T10:15:17Z – system – Prompt created.
- 2026-07-09T11:02:23Z – claude:sonnet:python-pedro:implementer – shell_pid=1684490 – Assigned agent via action command
- 2026-07-09T11:16:54Z – claude:sonnet:python-pedro:implementer – shell_pid=1684490 – Ready: templates+assets node-declarable in org_pack_loader (_ORG_DRG_KIND_ALIASES/_ORG_DRG_CANONICAL_KINDS); augmentation exclusion now routes through imported _NON_AUGMENTATION_ELIGIBLE_KINDS (no is-not-TEMPLATE); charter.activations._ALLOWED_KINDS + charter.pack_context._BUILTIN_ARTIFACT_KINDS moved in lockstep, drift-guard green. Tests: uv run pytest tests/doctrine/test_org_pack_augmentation.py tests/charter/test_pack_context.py -q -> 55 passed. Lint: uv run ruff check <diff files> -> exit 0. mypy: Success, no issues.
- 2026-07-09T11:18:26Z – claude:opus:reviewer-renata:reviewer – shell_pid=1769942 – Started review via action command
- 2026-07-09T11:22:42Z – user – shell_pid=1769942 – Review passed: templates+assets added to _ORG_DRG_KIND_ALIASES/_ORG_DRG_CANONICAL_KINDS; augmentation exclusion in both AUGMENTATION_ELIGIBLE_KINDS and _AUGMENTATION_GLOBS derives via 'kind not in _NON_AUGMENTATION_ELIGIBLE_KINDS' imported from artifact_kinds (grep-confirmed zero is-not-TEMPLATE remnant; imported set consumed at both comprehensions, not shadowed); _ALLOWED_KINDS + _BUILTIN_ARTIFACT_KINDS moved in lockstep, drift-guard green; _OrgDRGNode UNCHANGED, no mime (D-08); tests cover eligible-set exclusion + node-declarable-yet-augmentation-excluded via real OrgDRGFragment.model_validate. 55 passed; sanity import OK; scope clean (5 owned files only).
