---
work_package_id: WP01
title: Enum core + canonical exclusion set
dependencies: []
requirement_refs:
- C-001
- FR-005
- FR-011
tracker_refs: []
planning_base_branch: feat/doctrine-template-asset-kinds-2495
merge_target_branch: feat/doctrine-template-asset-kinds-2495
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-template-asset-kinds-2495. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-template-asset-kinds-2495 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Kind core
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1670597"
history:
- at: '2026-07-09T10:15:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/artifact_kinds.py
- src/doctrine/drg/models.py
- tests/doctrine/test_artifact_kinds.py
- tests/doctrine/drg/test_nodekind_artifactkind.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Enum core + canonical exclusion set

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter before parsing the rest of
this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Add both new enum members and the **one** canonical exclusion set that the rest of the mission consumes. This
WP is the root — every other WP depends on it, so it must be small, correct, and self-contained.

Done when:
- `ArtifactKind.ASSET` exists with `glob_pattern == "*.asset.yaml"` (NOT empty-glob).
- `NodeKind.ASSET` exists; the URN-prefix==kind rule accepts `asset:` (and the existing `template:`).
- `_NON_AUGMENTATION_ELIGIBLE_KINDS = frozenset({ArtifactKind.TEMPLATE, ArtifactKind.ASSET})` is defined in
  `artifact_kinds.py` (the single canonical home imported by downstream WPs).
- `CHARTER_KIND_TOKENS` is derived from that set (was `ArtifactKind − {TEMPLATE}`), so `ASSET` is excluded too.
- Member-set + glob tests updated and green.

## Context & Constraints

- Plan IC-02 (canonical set) + IC-03 (enum). Research **D-03** (canonical set), **D-05** (bare `<kind>:<id>`
  URNs — no pack qualifier). Contract AT-6.
- Ground truth (verify before editing): `src/doctrine/artifact_kinds.py:88` `TEMPLATE`; `:168-173`
  `CHARTER_KIND_TOKENS = ArtifactKind − {TEMPLATE} (+ MISSION_TYPE_TOKEN)`; `src/doctrine/drg/models.py:41`
  `NodeKind.TEMPLATE`; `:115-119` URN-prefix==kind rule.
- **Do NOT** touch the augmentation comprehensions in `org_pack_loader.py` — those are WP02's surface (they
  *import* the set you define here). You own only the definition + `CHARTER_KIND_TOKENS`.
- NFR-002: `ruff` + `mypy` zero-new; complexity ≤15; no suppressions.

## Branch Strategy

- **Planning base branch**: feat/doctrine-template-asset-kinds-2495
- **Merge target branch**: feat/doctrine-template-asset-kinds-2495
- **Strategy**: feature-branch (execution worktree allocated per computed lane from `lanes.json`)

## Subtasks & Detailed Guidance

### T001 – `ArtifactKind.ASSET` member + glob
- **Steps**: add `ASSET = "asset"` to `ArtifactKind`; ensure its `glob_pattern` resolves to `*.asset.yaml`
  (mirror how the 9 schema'd kinds derive their glob). TEMPLATE stays the sole empty-glob member.
- **Files**: `src/doctrine/artifact_kinds.py`.

### T002 – `NodeKind.ASSET` + URN-prefix rule `[P]`
- **Steps**: add `ASSET = "asset"` to `NodeKind` (`drg/models.py`); confirm the URN-prefix==kind validation
  (`:115-119`) accepts `asset:<id>` and `template:<id>` (both bare — no `<pack>/`). No new relation rules.
- **Files**: `src/doctrine/drg/models.py`.

### T003 – Canonical exclusion set
- **Steps**: define `_NON_AUGMENTATION_ELIGIBLE_KINDS: frozenset[ArtifactKind] = frozenset({ArtifactKind.TEMPLATE, ArtifactKind.ASSET})`
  in `artifact_kinds.py`. Export it (module-level, importable by `org_pack_loader.py` and the charter cascade).
- **Files**: `src/doctrine/artifact_kinds.py`.

### T004 – Drive `CHARTER_KIND_TOKENS` off the set
- **Steps**: rewrite `CHARTER_KIND_TOKENS` (`:168-173`) so its exclusion is `kind not in
  _NON_AUGMENTATION_ELIGIBLE_KINDS` instead of the single-member `is not TEMPLATE`. Preserve the existing
  `MISSION_TYPE_TOKEN` handling exactly. Net effect: TEMPLATE **and** ASSET are excluded from charter tokens.
- **Files**: `src/doctrine/artifact_kinds.py`.

### T005 – Update member-set + glob tests
- **Steps**: update `tests/doctrine/test_artifact_kinds.py` (member set + the glob pin: the empty-glob set
  must now be exactly `{TEMPLATE}`) and `tests/doctrine/drg/test_nodekind_artifactkind.py` (add ASSET). Add a
  focused assertion that `ASSET not in CHARTER_KIND_TOKENS` and `TEMPLATE not in CHARTER_KIND_TOKENS`.
- **Files**: `tests/doctrine/test_artifact_kinds.py`, `tests/doctrine/drg/test_nodekind_artifactkind.py`.

## Test Strategy

`pytest tests/doctrine/test_artifact_kinds.py tests/doctrine/drg/test_nodekind_artifactkind.py -q`. Add the
`CHARTER_KIND_TOKENS` exclusion assertions in the same PR as the code (Sonar new-code coverage). Run the
diff-scoped `ruff` sweep before handoff.

## Risks & Mitigations
- **Glob pin regression**: the `[k for k if not k.glob_pattern] == [TEMPLATE]` pin breaks if ASSET is
  empty-glob → give ASSET the real `*.asset.yaml` glob (D-02/D-05).
- **Leaking ASSET into charter tokens**: the whole point of T004 — verify with the added assertion.

## Review Guidance
- Confirm `_NON_AUGMENTATION_ELIGIBLE_KINDS` is the **only** new exclusion source and that `CHARTER_KIND_TOKENS`
  consumes it (no lingering `is not TEMPLATE`). Confirm URNs are bare (no `<pack>/`).

## Activity Log
- 2026-07-09T10:15:17Z – system – Prompt created.
- 2026-07-09T10:42:56Z – claude:sonnet:python-pedro:implementer – shell_pid=1654283 – Assigned agent via action command
- 2026-07-09T10:52:22Z – claude:sonnet:python-pedro:implementer – shell_pid=1654283 – Ready for review: added ArtifactKind.ASSET (*.asset.yaml glob) + NodeKind.ASSET, defined canonical _NON_AUGMENTATION_ELIGIBLE_KINDS={TEMPLATE,ASSET} and rederived CHARTER_KIND_TOKENS off it; ruff check on 4 changed files exit 0, mypy clean, 41/41 target tests pass.
- 2026-07-09T10:52:58Z – claude:opus:reviewer-renata:reviewer – shell_pid=1670597 – Started review via action command
- 2026-07-09T10:59:45Z – user – shell_pid=1670597 – Review passed (reviewer-renata): ArtifactKind.ASSET+NodeKind.ASSET added; ASSET glob=*.asset.yaml (TEMPLATE remains sole empty-glob); bare asset:/template: URNs accepted (D-05, no pack qualifier); _NON_AUGMENTATION_ELIGIBLE_KINDS={TEMPLATE,ASSET} single canonical set and CHARTER_KIND_TOKENS derives from 'not in' it (both excluded, mission-type preserved, no lingering is-not-TEMPLATE). Tests 41/41 green, ruff+mypy clean, only 4 owned files changed, downstream import smoke OK. Anti-pattern checklist all PASS/N-A. Filled mission issue-matrix (in-mission #2495/#2469; deferred-with-followup #2467/#2466/#2216) to satisfy approve gate.
