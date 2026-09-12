---
work_package_id: WP11
title: docs/context fold + repair dead charter authority paths
dependencies:
- WP03
- WP04
requirement_refs:
- FR-004
- FR-005
- FR-016
- FR-019
planning_base_branch: docs/common-docs-cleanup
merge_target_branch: docs/common-docs-cleanup
branch_strategy: Planning artifacts for this mission were generated on docs/common-docs-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/common-docs-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T042
history:
- at: '2026-08-10T03:30:00Z'
  actor: claude
  event: created
agent_profile: curator-carla
authoritative_surface: docs/context/
create_intent: []
execution_mode: code_change
owned_files:
- docs/context/*.md
- docs/contextive-glossaries.md
- glossary/**
- spec-driven.md
- .kittify/charter/charter.yaml
- .kittify/charter/governance.yaml
- tests/docs/test_current_charter_paths.py
- tests/contract/test_terminology_guards.py
- tests/architectural/test_no_legacy_terminology.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
```
/ad-hoc-profile-load curator-carla
```

## Objective
Fold the root `glossary/` stub + homeless context explanation files into `docs/context/`, and repair the
THREE dead charter authority paths. `docs/context/audience/**` is WP02's — do not touch it here. See
[plan.md](../plan.md) IC-09, [data-model.md](../data-model.md) authority paths, post-plan SSOT #5.

## Subtasks
- **T031** — Fold root `glossary/README.md` into `docs/context/` (its Domain Index already points into
  `docs/context/*`); rehome `docs/contextive-glossaries.md` and root `spec-driven.md` → `docs/context/`.
  Update `tests/docs/test_current_charter_paths.py:16` (asserts `spec-driven.md` at root) and the
  `docs/development/contributing.md:388,663` refs (hand the contributing.md edit to WP10 if it owns that
  file, else record for WP13). Record moves in the fragment.
- **T032** — In `.kittify/charter/charter.yaml` + `.kittify/charter/governance.yaml`, repair all three
  dead authority paths: `glossary/contexts/` (now `docs/context/`), `architecture/3.x/adr/`, and
  `architecture/adrs/` (now `docs/adr/<era>/`). Add/keep a resolution test asserting every declared
  authority path exists on disk (FR-019). Sequence AFTER WP07 architecture collapse + the glossary fold.
- **T033** — context `index.md` completeness; kebab-case; migrate free-text `audience:`. context/ is a
  charter authority path — pages may be reorganized WITHIN it, but the directory itself stays.
- **T042** — Reconcile the stale `plans/notes/` terminology-guard exemption (NFR-004): the exemption
  list in `tests/contract/test_terminology_guards.py` + `tests/architectural/test_no_legacy_terminology.py`
  names `docs/plans/notes/`, which does not exist. Remove/correct it BEFORE WP13's plans link-fix pass,
  and re-run the terminology guard as the check. (These test files are shared — if not in this WP's
  owned surface, hand the edit to WP13 T039; record which.)

## Branch Strategy
Base/merge: `docs/common-docs-cleanup`. Worktree per `lanes.json` lane.

## Definition of Done
- glossary/ folded; contextive-glossaries + spec-driven rehomed with charter-paths test updated; all 3
  dead authority paths repaired + a resolution test proving every authority path resolves; audience
  migrated. Fragment recorded.

## Risks
- `docs/context/orchestration.md`/`execution.md` are pinned by 3 tests + CLAUDE.md — reorganize content
  within context/ but keep these file paths stable unless the same-change test/CLAUDE updates are made
  (hand CLAUDE.md edits to WP13).
- charter authority-path edits are governance — same-change only, with the resolution test.
