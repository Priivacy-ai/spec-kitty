---
work_package_id: WP05
title: applies_to_languages any/all guard & scope-filtered diagnostic
dependencies: []
requirement_refs:
- FR-012
- FR-013
tracker_refs: []
subtasks:
- T020
- T021
- T022
- T023
phase: Phase 1 - Thread D
assignee: ''
agent: claude
history:
- at: '2026-06-23T09:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/shared/scoping.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/doctrine.py
- src/doctrine/shared/scoping.py
- src/charter/_catalog_miss.py
- tests/doctrine/shared/test_scoping_any_all.py
- tests/doctrine/test_doctrine_validate_lang_guard.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – applies_to_languages any/all guard & scope-filtered diagnostic

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Stop the doctrine catalog from silently dropping artifacts that declare `applies_to_languages: [any]`/`[all]` (#2092). Fail loud at authoring time, and make the catalog-miss diagnostic name a scope-filtered cause.

**Done when:** `spec-kitty doctrine validate` rejects `[any]`/`[all]` with an actionable message (FR-012); the catalog-miss diagnostic distinguishes "present-but-scope-filtered" (FR-013); tests prove both (SC-006).

## Context

- Spec FR-012/013, SC-006, C-006. Research D-3.
- Anchors: `src/doctrine/shared/scoping.py:24` `applies_to_languages_match` (treats `any`/`all` as literal tokens → never overlap a concrete active set → silently filtered). Active-language set: `src/doctrine/service.py:34-39`. Catalog-miss diagnostic: `src/charter/_catalog_miss.py` (`CharterCatalogMissWarning`, "catalog entry not found").
- `doctrine validate` commands live in `src/specify_cli/cli/commands/doctrine.py` (`validate` at :687, `org validate` at :852). Reproduction precedent: tactic `delete-the-assertion-not-the-test` hit this; PR #2089 worked around it by removing the field.
- **Bug-fix discipline**: write the RED test FIRST through a pre-existing entry point (the `doctrine validate` command / `applies_to_languages_match`), prove it red against current code, then fix.

## Subtasks & Detailed Guidance

### T020 — Validate-time guard [P]
- In the `doctrine validate` path (`doctrine.py`), reject any artifact whose `applies_to_languages` contains `any` or `all` (case-insensitive) with an actionable message: *"`any`/`all` are not language tokens — omit `applies_to_languages` to mean always-applicable."* This is the canonical fix (C-006) — fail where the author sees it. Centralize the check so all artifact kinds are covered.

### T021 — `scoping.py` defense-in-depth [P]
- In `applies_to_languages_match`, add a clear, documented handling decision: since the validate guard rejects `any`/`all`, treat any residual `any`/`all` defensively (either normalize to "unscoped/always-load" with a comment, or document why it cannot reach here). Do not silently filter. Keep the function ≤ complexity 15.

### T022 — Scope-filtered diagnostic [P]
- In `_catalog_miss.py`, add a "present-but-scope-filtered" branch: when a referenced artifact exists in the repo but was filtered by the active language scope, the diagnostic must say so (distinct from "missing/malformed"), pointing the operator at the scope cause rather than `doctrine validate` (which passes for scope-filtered files).

### T023 — Tests [P]
- `tests/doctrine/test_doctrine_validate_lang_guard.py`: a fixture artifact with `applies_to_languages: [any]` makes `doctrine validate` fail with the actionable message (RED-first against current code).
- `tests/doctrine/shared/test_scoping_any_all.py`: `applies_to_languages_match` handling of `any`/`all` per the T021 decision.
- A test for the scope-filtered diagnostic branch.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}
- Parallel lane (no dependency). De-risks WP04 (a `[any]`-scoped styleguide would otherwise be dropped).

## Definition of Done

- [ ] `doctrine validate` rejects `[any]`/`[all]` with an actionable message (FR-012), proven RED-first.
- [ ] `applies_to_languages_match` no longer silently drops `any`/`all`; documented decision (T021).
- [ ] Catalog-miss diagnostic names the scope-filtered cause (FR-013).
- [ ] Tests green; `ruff`+`mypy` clean; complexity ≤ 15.

## Risks & Reviewer Guidance

- **Risk**: fixing only query-time wildcarding leaves the silent-at-authoring gap. **Reviewer**: confirm the guard is at validate time (fails loud), the RED test was proven against pre-fix code, and the diagnostic branch is reachable.
