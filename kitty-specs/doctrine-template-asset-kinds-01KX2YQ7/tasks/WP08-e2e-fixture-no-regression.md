---
work_package_id: WP08
title: E2E fixture + no-regression
dependencies: [WP01, WP02, WP03, WP04, WP05, WP06, WP07]
requirement_refs:
- FR-004
- FR-008
- NFR-001
- NFR-004
tracker_refs: []
planning_base_branch: feat/doctrine-template-asset-kinds-2495
merge_target_branch: feat/doctrine-template-asset-kinds-2495
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-template-asset-kinds-2495. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-template-asset-kinds-2495 unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
phase: Phase 5 - E2E + acceptance
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1975776"
history:
- at: '2026-07-09T10:15:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/doctrine/
create_intent:
- tests/doctrine/test_template_asset_e2e.py
- tests/doctrine/fixtures/org_pack_template_asset/README.md
execution_mode: code_change
model: ''
owned_files:
- tests/doctrine/fixtures/org_pack_template_asset/**
- tests/doctrine/test_template_asset_e2e.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – E2E fixture + no-regression

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` for the frontmatter profile before parsing the rest.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Prove the two kinds work end-to-end on a realistic org-pack and that nothing regressed.

Done when:
- A Regnology-shaped org-pack fixture declares a `template` node + an edge (a styleguide `requires` the template)
  + an `asset` (a real blob + sidecar `*.asset.yaml`); it loads, the merged DRG contains node + edge, and a query
  (incl. `resolve_transitive_refs`) returns them — the asset appears in the `.assets` field (WP07).
- Negative cases fail loud: dup asset id across two packs → `duplicate_asset_id`; dup template URN across
  producers → `duplicate_template_id`; `path: ../..` → `asset_path_escape`; malformed mime → `asset_mime_invalid`.
- The 9 existing kinds load/validate/graph identically; the full doctrine/DRG/charter/pack-validator suites are
  green (incl. the updated lockstep/glob/member-set tests and the new totality guard).

## Context & Constraints

- Plan IC-06. Spec **NFR-001, NFR-004**; scenarios S1–S7; contract **TT-1/TT-2/TT-3, AT-1..AT-8**.
- This WP owns only **new test assets** — do not edit source (all source lands in WP01–WP07). If the e2e reveals
  a source gap, record it as review feedback against the owning WP, don't edit outside your ownership.
- Realistic data: a real template shape (e.g. `meeting-minutes`) + a real asset (e.g. a small png with a correct
  `image/png` manifest), not toy placeholders.
- Depends on **WP01–WP07**.

## Branch Strategy
- **Planning base branch**: feat/doctrine-template-asset-kinds-2495
- **Merge target branch**: feat/doctrine-template-asset-kinds-2495
- **Strategy**: feature-branch (worktree per lane from `lanes.json`)

## Subtasks & Detailed Guidance

### T031 – Positive e2e fixture
- **Steps**: build `tests/doctrine/fixtures/org_pack_template_asset/` — a pack with a `templates/<pack>/` node,
  a `styleguides/<pack>/` that `requires` it, and an `assets/<pack>/` blob + sidecar manifest. Write
  `test_template_asset_e2e.py` asserting: load succeeds; merged DRG has the template node + edge + asset node;
  a transitive query returns them (asset in `.assets`). Include a valid-orphan template (node, no edges).
- **Files**: `tests/doctrine/fixtures/org_pack_template_asset/**`, `tests/doctrine/test_template_asset_e2e.py`.

### T032 – Negative cases (fail-loud)
- **Steps**: add cases for cross-pack/cross-layer dup asset id (`duplicate_asset_id`), dup template URN
  (`duplicate_template_id`), path-escape (`asset_path_escape`), and malformed/mismatched mime
  (`asset_mime_invalid`). Each must raise the distinct structured error.
- **Files**: `tests/doctrine/test_template_asset_e2e.py`, `tests/doctrine/fixtures/org_pack_template_asset/**`.

### T033 – No-regression sweep
- **Steps**: run the full doctrine + DRG + charter + pack-validator suites and assert green; spot-check that a
  representative existing kind (e.g. `directive`) still loads/validates/graphs identically. Record the command +
  result in the handoff note.
- **Files**: `tests/doctrine/test_template_asset_e2e.py` (assertion harness only).

## Test Strategy
`PWHEADLESS=1 pytest tests/doctrine/test_template_asset_e2e.py -q`, then
`PWHEADLESS=1 pytest tests/doctrine tests/charter tests/specify_cli/doctrine -q` for the no-regression gate.
These include CI-only shards — run them locally before handoff (pre-push discipline).

## Risks & Mitigations
- **Asserting from API not behavior**: exercise the real loader/merge/query path, not a mocked shortcut.
- **Cross-ownership edits**: if the e2e surfaces a source bug, file it against the owning WP; do not edit source
  here.

## Review Guidance
- Confirm the fixture is realistic, the positive path proves node+edge+asset+transitive, all four negative errors
  are distinct, and the full-suite sweep is green with the 9 kinds unchanged.

## Activity Log
- 2026-07-09T10:15:17Z – system – Prompt created.
- 2026-07-09T12:12:53Z – claude:sonnet:python-pedro:implementer – shell_pid=1929570 – Assigned agent via action command
- 2026-07-09T12:35:18Z – claude:sonnet:python-pedro:implementer – shell_pid=1929570 – Ready: e2e proof green (9/9 tests) via real load_org_pack -> merge_three_layers(real shipped graph.yaml) -> resolve_transitive_refs; TT-1/AT-1/AT-7 positive path (styleguide--requires-->template--requires-->asset chain + valid orphan template) confirmed; 4 distinct fail-loud negatives confirmed (duplicate_asset_id, duplicate_template_id, asset_path_escape, asset_mime_invalid); directive-kind regression spot-check confirms 9 pre-existing kinds' override tolerance untouched. No-regression sweep: tests/doctrine 2497 passed, tests/charter 1430 passed/1 skipped, tests/specify_cli/doctrine 225 passed, test_no_legacy_terminology 3 passed. ruff+mypy clean on new test file.
- 2026-07-09T12:39:02Z – claude:opus:reviewer-renata:reviewer – shell_pid=1975776 – Started review via action command
