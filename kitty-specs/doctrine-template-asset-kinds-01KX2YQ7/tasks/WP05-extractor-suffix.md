---
work_package_id: WP05
title: Extractor + doctrine-CLI suffix
dependencies: [WP01]
requirement_refs:
- FR-007
- FR-012
tracker_refs: []
planning_base_branch: feat/doctrine-template-asset-kinds-2495
merge_target_branch: feat/doctrine-template-asset-kinds-2495
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-template-asset-kinds-2495. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-template-asset-kinds-2495 unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
phase: Phase 3 - Registration
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1769942"
history:
- at: '2026-07-09T10:15:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/migration/extractor.py
create_intent:
- tests/doctrine/drg/test_extractor_asset.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/migration/extractor.py
- src/specify_cli/cli/commands/doctrine.py
- tests/doctrine/drg/test_extractor_asset.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Extractor + doctrine-CLI suffix

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` for the frontmatter profile before parsing the rest.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Register ASSET in the migration extractor and the CLI suffix→kind map, using `.get` (never a raising subscript)
so a future kind cannot crash these sites.

Done when:
- `extractor.scan_dirs` includes `assets`; `_KIND_MAP` resolves the asset type via `.get` (None-safe — the
  built-in migration extractor keeps skipping non-DRG types cleanly).
- `doctrine.py::_SUFFIX_TO_KIND` maps `*.asset.yaml` → ASSET.
- Focused tests cover both registrations.

## Context & Constraints

- Plan IC-03 + IC-05. Spec **FR-007 (extractor), FR-012**. Research **D-05**, **D-13** (`.get`, not raise).
- Ground truth: `drg/migration/extractor.py:122` `_KIND_MAP`, `:743` `scan_dirs`, `:349`
  `continue  # skip non-DRG types (e.g. template)` (driven by `_kind_for_type` → None; keep it None-safe);
  `cli/commands/doctrine.py::_SUFFIX_TO_KIND`.
- Depends on **WP01** (ASSET kind).

## Branch Strategy
- **Planning base branch**: feat/doctrine-template-asset-kinds-2495
- **Merge target branch**: feat/doctrine-template-asset-kinds-2495
- **Strategy**: feature-branch (worktree per lane from `lanes.json`)

## Subtasks & Detailed Guidance

### T019 – Extractor registration
- **Steps**: add `assets` to `scan_dirs` (`:743`); ensure `_KIND_MAP` (`:122`) is read via `.get` so unknown/new
  types return None and are skipped, not raised. Confirm the `:349` skip stays correct for template/asset in the
  built-in extractor (org packs declare assets via `org_pack_loader`, not this path).
- **Files**: `src/doctrine/drg/migration/extractor.py`.

### T020 – `_SUFFIX_TO_KIND` += `*.asset.yaml` `[P]`
- **Steps**: map the `.asset.yaml` suffix to `ArtifactKind.ASSET` in `doctrine.py::_SUFFIX_TO_KIND`.
- **Files**: `src/specify_cli/cli/commands/doctrine.py`.

### T021 – Tests
- **Steps**: new `tests/doctrine/drg/test_extractor_asset.py` — assert `scan_dirs` includes `assets`, `_KIND_MAP`
  `.get` is None-safe for an unknown type, and `_SUFFIX_TO_KIND` resolves `*.asset.yaml`.
- **Files**: `tests/doctrine/drg/test_extractor_asset.py`.

## Test Strategy
`pytest tests/doctrine/drg/test_extractor_asset.py -q`. Assert the `.get`-None-safety explicitly (a raising
subscript is the regression this guards).

## Risks & Mitigations
- **Raising subscript**: never `_KIND_MAP[type]` — always `.get`.

## Review Guidance
- Confirm both maps use `.get` and the new test executes the None-safe branch directly.

## Activity Log
- 2026-07-09T10:15:17Z – system – Prompt created.
- 2026-07-09T11:02:39Z – claude:sonnet:python-pedro:implementer – shell_pid=1684490 – Assigned agent via action command
- 2026-07-09T11:15:51Z – claude:sonnet:python-pedro:implementer – shell_pid=1684490 – Ready: scan_dirs+assets/built-in discovery, _KIND_MAP stays .get-based/asset-free (deliberate, org_pack_loader owns asset refs), _SUFFIX_TO_KIND += .asset.yaml. 4 new tests green; ruff exit 0; mypy clean.
- 2026-07-09T11:18:37Z – claude:opus:reviewer-renata:reviewer – shell_pid=1769942 – Started review via action command
- 2026-07-09T11:22:47Z – user – shell_pid=1769942 – Review passed: scan_dirs gains assets/built-in carrying NodeKind.ASSET directly (discovery independent of _KIND_MAP, validated); _KIND_MAP reads via _kind_for_type/.get None-safe, asset deliberately absent as unknown-type probe (sound — the only subscripts at 653-654 are over hardcoded _CURATED_ARTIFACT_EDGES with known types, no asset); _SUFFIX_TO_KIND maps *.asset.yaml. 4 new tests execute real prod paths (green); pre-existing test_extractor.py green (44 passed total); ruff+mypy clean on changed sources; scope limited to 3 owned files.
