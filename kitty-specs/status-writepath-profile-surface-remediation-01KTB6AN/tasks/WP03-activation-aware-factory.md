---
work_package_id: WP03
title: Activation-aware doctrine service factory + glossary terms
dependencies: []
requirement_refs:
- FR-010
- FR-019
tracker_refs:
- '1636'
planning_base_branch: feature/status-writepath-profile-surface-remediation
merge_target_branch: feature/status-writepath-profile-surface-remediation
branch_strategy: Planning artifacts for this mission were generated on feature/status-writepath-profile-surface-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/status-writepath-profile-surface-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T029
phase: 'Lane B-core — #1636'
agent: "claude"
history:
- at: '2026-06-05T08:32:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/doctrine_service_factory.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/doctrine_service_factory.py
- tests/specify_cli/test_doctrine_service_factory.py
- glossary/contexts/governance.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Activation-aware doctrine service factory

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (role `implementer`) before proceeding.

---

## Objectives & Success Criteria

Provide a single construction seam so profile surfaces resolve through the existing charter activation chokepoint.

- **FR-010**: `build_activation_aware_doctrine_service(repo_root) -> charter.resolver.DoctrineService` constructs the inner `doctrine.service.DoctrineService` and wraps it in `charter.resolver.DoctrineService(inner, pack_context=PackContext.from_config(repo_root))`.
- **FR-019** (DIR-032, vocabulary-before-code): add the glossary terms *abstract base profile*, *activation chokepoint*, *activated vs available profile* **here in WP03** — the dependency-free, earliest profile-surface WP — so the vocabulary is ratified **before** WP04 ships the `profile show` warning string that uses "abstract base profile". (Moved from WP06 per the `/spec-kitty.analyze` I1 finding.)

**Done when**: the factory exists, is typed, and its `.agent_profiles` honors the three-state `activated_agent_profiles` contract; import is layer-safe; the three glossary terms are defined.

## Context & Constraints

- The activation-aware wrapper already exists at `src/charter/resolver.py:56-129` (do **not** duplicate it — C-003). The factory generalises the construction pattern at `charter/generate.py:46-74`.
- **Layer rule (C-005)**: the factory lives in `specify_cli.*` and imports `charter.*` + `doctrine.service` (the allowed direction). It must not be placed inside `charter.*` or `doctrine.*`.
- See [data-model.md](../data-model.md) for the signature and placement decision.

## Branch Strategy

- **Planning base / merge target**: `feature/status-writepath-profile-surface-remediation` · **Depends on**: none (foundation for WP04).

## Subtasks & Detailed Guidance

### Subtask T011 – Implement the factory

- **Steps**: create `src/specify_cli/doctrine_service_factory.py` with `build_activation_aware_doctrine_service(repo_root: Path) -> "charter.resolver.DoctrineService"`. Fully type-annotated, with a docstring stating it is the single seam for activation-aware profile resolution.
- **Files**: `src/specify_cli/doctrine_service_factory.py`

### Subtask T012 – Construct + wrap

- **Steps**: build the inner `doctrine.service.DoctrineService(built_in_root=..., project_root=..., org_roots=...)` using the same root-resolution the existing CLI surfaces use (mirror `charter/generate.py`), then wrap with `charter.resolver.DoctrineService(inner, pack_context=PackContext.from_config(repo_root))`.
- **Notes**: reuse existing root resolvers; do not reinvent path discovery.

### Subtask T013 – Unit test: three-state filtering

- **Steps**: in `tests/specify_cli/test_doctrine_service_factory.py`, assert: absent `activated_agent_profiles` → all built-ins; empty set → `{}`; explicit set → only those ids. Use a temp project with a `.kittify/config.yaml`.
- **Parallel?**: [P] with T014.

### Subtask T014 – Layer-safety test

- **Steps**: assert importing the factory module does not import `specify_cli` from within `charter`/`doctrine` (guard the dependency direction). A lightweight import-order/`importlib` assertion is sufficient.
- **Parallel?**: [P] with T013.

### Subtask T029 – Glossary terms (FR-019)

- **Purpose**: ratify vocabulary before the warning string ships (DIR-032).
- **Steps**: add to `glossary/contexts/governance.md`, following the existing entry format: *abstract base profile* (a profile referenced via `specializes_from` that is not itself activated — a shared-element store, not directly selectable), *activation chokepoint* (the `charter.resolver.DoctrineService` activation filter), *activated vs available profile*.
- **Files**: `glossary/contexts/governance.md`
- **Parallel?**: [P] — independent of the factory code.

## Test Strategy

- `pytest tests/specify_cli/test_doctrine_service_factory.py`; `mypy --strict`; `ruff check`.

## Risks & Mitigations

- **Duplicating the wrapper** → import and reuse `charter.resolver.DoctrineService`; do not reimplement filtering.
- **Wrong root resolution** → copy the proven pattern from `charter/generate.py`.

## Review Guidance

- Confirm the wrapper is reused, not duplicated.
- Confirm the factory is in `specify_cli.*` and the layer direction holds.
- **NFR-003**: confirm `runtime/next` profile-resolution behavior is unchanged (it already uses the wrapper; the new factory must not alter it).

## Activity Log

- 2026-06-05T08:32:05Z – system – Prompt created.
- 2026-06-05T12:58:30Z – claude – Implemented via bypass; tests green
