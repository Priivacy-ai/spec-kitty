---
work_package_id: WP05
title: charter context --include activation gate
dependencies: []
requirement_refs:
- FR-016
tracker_refs:
- '1636'
planning_base_branch: feature/status-writepath-profile-surface-remediation
merge_target_branch: feature/status-writepath-profile-surface-remediation
branch_strategy: Planning artifacts for this mission were generated on feature/status-writepath-profile-surface-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/status-writepath-profile-surface-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
phase: 'Lane B-charter — #1636'
agent: "claude"
assignee: "claude"
history:
- at: '2026-06-05T08:32:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/context.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/context.py
- tests/charter/test_context_include_activation.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – charter context --include activation gate

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (role `implementer`) before proceeding.

---

## Objectives & Success Criteria

- **FR-016**: `charter context --include agent-profile:<id>` resolves through an activation-aware service so the fetch path inherits the activation gate — **without** changing the other 5 call sites of `_build_doctrine_service`.

**Done when**: the `agent-profile:<id>` include branch is gated; the other include kinds and call sites behave exactly as before.

## Context & Constraints

- **Corrected scope (dialectic review)**: `_build_doctrine_service` is at `src/charter/context.py:1235`, returns a plain `DoctrineService(**kwargs)` with **no** `PackContext`, and has **6 callers** (lines 333/352/863/1373/2620 + `_maybe_build_doctrine_service@2887`). **Do not blanket-wrap it.**
- Add a **scoped** helper and route only the agent-profile include branch through it. The module already imports `PackContext` and constructs one in a different function near line 244 — construct a fresh `PackContext.from_config(repo_root)` locally in the new helper.
- This change lives entirely in `charter.*` (it cannot import `specify_cli`), so it builds its own wrapped service via `charter.resolver.DoctrineService` directly (not the WP03 factory).

## Branch Strategy

- **Planning base / merge target**: `feature/status-writepath-profile-surface-remediation` · **Depends on**: none (independent lane).

## Subtasks & Detailed Guidance

### Subtask T023 – Scoped wrapped helper

- **Steps**: add `_build_activation_aware_doctrine_service(repo_root, *, org_roots=None)` in `charter/context.py` that builds the inner service (same kwargs as `_build_doctrine_service`) and wraps it with `charter.resolver.DoctrineService(inner, pack_context=PackContext.from_config(repo_root))`.
- **Files**: `src/charter/context.py`

### Subtask T024 – Route the agent-profile include branch

- **Steps**: in `build_charter_context_include` (around the `agent_profile` render branch, ~`context.py:352-358`), use the new scoped helper instead of `_build_doctrine_service`. Leave all other kinds and call sites on the original helper.

### Subtask T025 – Test: include inherits the gate [P]

- **Steps**: in `tests/charter/test_context_include_activation.py`, assert `--include agent-profile:<non-activated>` is gated (not rendered / structured miss), while an activated profile renders. Mirror existing `test_context_include.py` fixtures.
- **Files**: `tests/charter/test_context_include_activation.py`

### Subtask T026 – Regression: other call sites unchanged

- **Steps**: assert the other include kinds (directive/template/section) and the 5 non-profile `_build_doctrine_service` callers still return the unwrapped service (no behavior change). A focused test or explicit assertion suffices.

## Test Strategy

- `pytest tests/charter/test_context_include_activation.py`; `mypy --strict`; `ruff check`.

## Risks & Mitigations

- **Accidental blanket wrap** → only the agent-profile branch uses the new helper; grep the 6 call sites to confirm.

## Review Guidance

- Confirm exactly one call site changed; the other five are byte-identical.

## Activity Log

- 2026-06-05T08:32:05Z – system – Prompt created.
- 2026-06-05T12:58:35Z – claude – Moved to in_progress
- 2026-06-05T12:58:36Z – claude – Implemented via bypass; tests green
