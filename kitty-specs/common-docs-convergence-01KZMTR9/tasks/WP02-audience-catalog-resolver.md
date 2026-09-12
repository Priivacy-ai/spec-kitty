---
work_package_id: WP02
title: Audience catalog kebab-clean + non-vacuous resolver
dependencies: []
requirement_refs:
- FR-001
- FR-003
planning_base_branch: docs/common-docs-cleanup
merge_target_branch: docs/common-docs-cleanup
branch_strategy: Planning artifacts for this mission were generated on docs/common-docs-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/common-docs-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
history:
- at: '2026-08-10T03:30:00Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: scripts/docs/audience_resolver.py
create_intent:
- scripts/docs/audience_resolver.py
- tests/docs/test_audience_resolves.py
execution_mode: code_change
owned_files:
- docs/context/audience/**
- scripts/docs/audience_resolver.py
- tests/docs/test_audience_resolves.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
```
/ad-hoc-profile-load python-pedro
```
Confirm TDD/red-first; run pytest+ruff+mypy before handoff.

## Objective
Make the existing `docs/context/audience/` catalog naming-clean and add a **non-vacuous** resolver + test
for the `audience:` field. Foundation — gates the rewrites. See [contracts/audience-resolution-contract.md](../contracts/audience-resolution-contract.md),
[plan.md](../plan.md) IC-01, [data-model.md](../data-model.md).

## Context
The catalog has 10 personas (internal/external) + README landing pages; some filenames are snake_case.
`assert_examined_floor` exists in `scripts/docs/_guards.py`; `related_validator.py` is the extension
model (but only accepts a list — the resolver must handle scalar-or-list). The 13 free-text `audience:`
values are migrated by the mover WPs, not here.

## Subtasks
- **T005** — Kebab-rename any snake_case persona files under `docs/context/audience/**` to the FINAL
  kebab paths, ensure an `index.md` landing page per level, and confirm the catalog is complete. Record
  these renames as this WP's occurrence-map fragment (movers will migrate `audience:` values directly to
  the final kebab paths, so do this before them). This is a C-003 authority-path area — coordinate with
  WP11 (do not touch charter config here).
- **T006** — Implement `scripts/docs/audience_resolver.py`: walk `docs/**/*.md`, collect `audience:`
  (scalar OR list), assert each resolves to an existing file under `docs/context/audience/`, reuse
  `assert_examined_floor` with `min_files ≥` the count of audience-tagged pages (fail on zero examined),
  emit `checked_count`, support `--strict` (exit 1 on any dangling).
- **T007** — `tests/docs/test_audience_resolves.py`: red-first tests proving the resolver fails on a
  dangling ref and on zero examined, and passes on the current tagged set.

## Branch Strategy
Base/merge: `docs/common-docs-cleanup`. Worktree per `lanes.json` lane.

## Definition of Done
- Catalog is kebab-clean with per-level `index.md`; renames recorded in the fragment.
- `audience_resolver.py --strict docs` passes on the current tree; fails on injected dangling + on zero
  examined. Tests green; ruff/mypy clean.

## Risks
- `docs/context/audience/` is under a charter authority path (`docs/context/`); renames within it are
  safe (the authority path is the directory), but do not move the directory itself.
