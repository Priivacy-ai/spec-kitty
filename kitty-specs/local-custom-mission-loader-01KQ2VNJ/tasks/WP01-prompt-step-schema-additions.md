---
work_package_id: WP01
title: PromptStep Schema Additions
dependencies: []
requirement_refs:
- FR-008
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-local-custom-mission-loader-01KQ2VNJ
base_commit: 13c8c54cee95c5ddbf820fbf3e132657c5155618
created_at: '2026-04-25T18:08:22.777849+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Schema (foundational)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "33338"
history:
- at: '2026-04-25T17:54:43Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/next/_internal_runtime/schema.py
execution_mode: code_change
owned_files:
- src/specify_cli/next/_internal_runtime/schema.py
- tests/next/test_prompt_step_schema_extensions.py
role: implementer
tags: []
---

# Work Package Prompt: WP01 – PromptStep Schema Additions

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the assigned agent profile:

```
/ad-hoc-profile-load implementer-ivan
```

This grounds you in the role, governance scope, and boundaries the orchestrator expects from this WP. Do not skip.

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`
- **Actual execution workspace is resolved later**: `/spec-kitty.implement` selects the lane worktree and records the lane branch in `base_branch`. Trust the printed lane workspace instead of guessing a path or branch.
- **If human instructions contradict these fields**: stop and resolve the intended landing branch before coding.

## Objectives & Success Criteria

Land two new optional fields on `PromptStep` (`agent_profile`, `contract_ref`) so downstream WPs can express custom-mission step bindings. **No behavior change to built-in missions**: their templates do not set either field, so they parse and execute identically.

Success criteria:
1. `PromptStep` accepts both `agent_profile` and `agent-profile` keys at parse time.
2. `PromptStep` accepts `contract_ref`.
3. Defaults are `None`; existing built-in templates parse with no mutation.
4. `mypy --strict` passes on the modified module.
5. New unit tests pass; the `tests/next/` and `tests/specify_cli/next/` suites stay green.

## Context & Constraints

- This WP is the smallest possible foundational change. Resist adding a `kind` discriminator, a `retrospective` flag, or any new validation in this WP — those belong to WP02 / WP04.
- Charter constraint: `mypy --strict` is enforced.
- Pydantic v2 is in use across `_internal_runtime/schema.py`. Follow the same `model_config = ConfigDict(frozen=True, ...)` pattern that `PromptStep` already has.
- See [data-model.md](../data-model.md) §Schema additions for the authoritative field list.
- See [research.md](../research.md) §R-003 for the alias rationale.

## Subtasks & Detailed Guidance

### Subtask T001 — Add `agent_profile` field to `PromptStep`

- **Purpose**: Provide the per-step opt-in field that the composition gate (WP04) reads. YAML authors write either `agent_profile: implementer-ivan` (snake) or `agent-profile: implementer-ivan` (kebab).
- **Steps**:
  1. Open `src/specify_cli/next/_internal_runtime/schema.py`.
  2. Locate the `PromptStep` class (around line 401).
  3. Add the field with an explicit Pydantic alias:
     ```python
     agent_profile: str | None = Field(
         default=None,
         alias="agent-profile",
         description="Profile id used as profile_hint when this step dispatches via composition.",
     )
     ```
  4. Ensure `Field` is imported (it already is for other fields).
- **Files**: `src/specify_cli/next/_internal_runtime/schema.py`.
- **Parallel?**: must precede T003 in same file.
- **Notes**: Empty string and whitespace-only values should be treated the same as `None`. WP02's validator handles that semantics; this WP just stores the raw string.

### Subtask T002 — Add `contract_ref` field to `PromptStep`

- **Purpose**: Optional pointer to a pre-existing `MissionStepContract.id` for advanced authors who want to share a contract across steps or missions.
- **Steps**:
  1. In the same `PromptStep` class, immediately after `agent_profile`, add:
     ```python
     contract_ref: str | None = Field(
         default=None,
         description="Optional ID of an existing MissionStepContract; when set, contract_synthesis skips this step.",
     )
     ```
- **Files**: `src/specify_cli/next/_internal_runtime/schema.py`.
- **Parallel?**: must follow T001.
- **Notes**: No alias needed for `contract_ref` — single canonical spelling.

### Subtask T003 — Configure `populate_by_name=True` on `PromptStep.model_config`

- **Purpose**: Make Pydantic accept either the alias (`agent-profile`) or the field name (`agent_profile`) when validating from a dict / YAML.
- **Steps**:
  1. Locate `PromptStep`'s `model_config = ConfigDict(frozen=True)` line.
  2. Change to `model_config = ConfigDict(frozen=True, populate_by_name=True)`.
- **Files**: `src/specify_cli/next/_internal_runtime/schema.py`.
- **Parallel?**: must follow T001+T002 in same file.
- **Notes**: This setting is local to `PromptStep`. Do NOT change other models' configs.

### Subtask T004 — Unit tests covering both alias spellings + defaults + mypy

- **Purpose**: Prove FR-008 alias requirement and lock the schema as a stable contract.
- **Steps**:
  1. Create `tests/next/test_prompt_step_schema_extensions.py`.
  2. Author tests:
     - `test_default_fields_are_none` — `PromptStep(id="x", title="X")` → `.agent_profile is None and .contract_ref is None`.
     - `test_snake_alias_parses` — `PromptStep.model_validate({"id": "x", "title": "X", "agent_profile": "implementer-ivan"})` → `.agent_profile == "implementer-ivan"`.
     - `test_kebab_alias_parses` — `PromptStep.model_validate({"id": "x", "title": "X", "agent-profile": "implementer-ivan"})` → `.agent_profile == "implementer-ivan"`.
     - `test_contract_ref_parses` — `.contract_ref == "abc"` when set; defaults to `None` otherwise.
     - `test_both_set_round_trip` — both fields set survive `model_dump(by_alias=True)` and a re-validate.
  3. Use `pytest`'s parametrize for the alias cases if it improves clarity.
- **Files**: `tests/next/test_prompt_step_schema_extensions.py` (NEW).
- **Parallel?**: [P] — independent of T001-T003 once the field signatures are agreed.
- **Notes**: Verify `mypy --strict tests/next/test_prompt_step_schema_extensions.py` passes (no `Any` leaks).

## Test Strategy (charter required)

- Add the file above. No other test files touched in this WP.
- Run locally:
  ```bash
  UV_PYTHON=3.13.9 uv run --no-sync pytest tests/next/test_prompt_step_schema_extensions.py tests/next/test_internal_runtime_coverage.py tests/next/test_internal_runtime_parity.py -q
  UV_PYTHON=3.13.9 uv run --no-sync ruff check src/specify_cli/next/_internal_runtime/schema.py tests/next/test_prompt_step_schema_extensions.py
  UV_PYTHON=3.13.9 uv run --no-sync mypy --strict src/specify_cli/next/_internal_runtime/schema.py
  ```
- Before declaring done, also run the existing composition suite to confirm no regression:
  ```bash
  UV_PYTHON=3.13.9 uv run --no-sync pytest tests/specify_cli/next/test_runtime_bridge_composition.py -q
  ```

## Risks & Mitigations

- **Risk**: Forgetting `populate_by_name=True` makes snake-case parsing fail and breaks downstream WPs that use the snake spelling.
  - **Mitigation**: T004's `test_snake_alias_parses` is explicit; if it fails, T003 is incomplete.
- **Risk**: Adding `Field()` triggers a forward-reference issue in `frozen=True` models.
  - **Mitigation**: Other fields in this module already use `Field(...)` without trouble; mirror their style.

## Review Guidance

- Reviewer checks: alias accepts both spellings; defaults are `None`; mypy strict clean; no unrelated diffs in `schema.py`.
- Reviewer confirms `tests/specify_cli/next/test_runtime_bridge_composition.py` still passes (FR-010 regression trap).

## Activity Log

- 2026-04-25T17:54:43Z -- system -- Prompt created.
- 2026-04-25T18:11:28Z – claude – shell_pid=32550 – Schema fields added; all validation green; built-in templates parse unchanged
- 2026-04-25T18:11:57Z – claude:opus:reviewer-renata:reviewer – shell_pid=33338 – Started review via action command
- 2026-04-25T18:14:35Z – claude:opus:reviewer-renata:reviewer – shell_pid=33338 – Review passed: agent_profile (kebab alias) + contract_ref fields added, populate_by_name=True, scope limited to schema.py + new test file, executor.py untouched, all targeted tests pass (123+35), built-in mission templates still parse via parity tests, ruff/mypy issues confirmed pre-existing on baseline.
