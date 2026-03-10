---
description: "Work package task list for 042-model-selection-per-task"
---

# Work Packages: Model Selection per Task

**Inputs**: Design documents from `/kitty-specs/042-model-selection-per-task/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Organization**: Fine-grained subtasks (`Txxx`) roll up into 3 work packages. WP01 is the core implementation; WP02 is tests; WP03 is docs.

---

## Work Package WP01: Core Implementation (Priority: P0) 🎯 MVP

**Goal**: Implement `global_config.py` (reads `~/.spec-kitty/config.yaml`) and the `m_2_0_4_model_injection.py` migration that injects `model:` frontmatter into agent command files during `spec-kitty upgrade`.
**Independent Test**: Create `~/.spec-kitty/config.yaml` with a model mapping, run `spec-kitty upgrade` in a test project, inspect command files for injected `model:` fields.
**Prompt**: `tasks/WP01-core-implementation.md`
**Estimated size**: ~350 lines

### Included Subtasks
- [x] T001 Create `src/specify_cli/global_config.py` with `load_model_mapping()` and `get_unknown_commands()`
- [x] T002 Create `src/specify_cli/upgrade/migrations/m_2_0_4_model_injection.py` with `detect()`, `can_apply()`, and `apply()`
- [x] T003 Handle edge cases: files without frontmatter, stale `model:` removal when command absent from config
- [x] T004 Verify migration auto-registration and ordering in the registry

### Implementation Notes
- `global_config.py`: read `Path.home() / ".spec-kitty" / "config.yaml"`, return `{}` on missing, raise clear error on malformed YAML
- Migration uses `get_agent_dirs_for_project()` from `agent_utils/directories.py` and `FrontmatterManager` from `frontmatter.py`
- File glob: `spec-kitty.*.md` — extract command name as `stem.split(".", 1)[1]` (e.g., `spec-kitty.specify.md` → `specify`)
- Idempotent: safe to re-run; if model value already matches config, skip write

### Parallel Opportunities
- T001 and T002 can start in parallel (T002 imports T001, but the file can be stubbed first)

### Dependencies
- None (starting package)

### Risks & Mitigations
- `FrontmatterManager` raises `FrontmatterError` on malformed files — migration should catch and warn, not abort entire upgrade
- File without frontmatter: check for `---` at start; if absent, prepend minimal frontmatter block

**Requirements Refs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008

---

## Work Package WP02: Tests (Priority: P1)

**Goal**: Full test coverage for `global_config.py` and the migration — unit tests for config loading, integration tests for frontmatter injection across multiple agents.
**Independent Test**: `pytest tests/specify_cli/test_model_injection_migration.py -v` passes green.
**Prompt**: `tasks/WP02-tests.md`
**Estimated size**: ~320 lines

### Included Subtasks
- [x] T005 [P] Unit tests for `global_config.py`: missing file, valid mapping, partial mapping, malformed YAML, unknown command keys
- [x] T006 [P] Integration tests for migration: no config (no-op), inject model, update stale model, remove model when absent from config, multi-agent, dry-run mode

### Implementation Notes
- Test file: `tests/specify_cli/test_model_injection_migration.py`
- Use `tmp_path` pytest fixture for isolated home dir simulation (`monkeypatch` `Path.home`)
- Parametrize over a subset of agent dirs (at least `.claude/commands`, `.codex/prompts`, `.opencode/command`)
- Verify idempotency: running migration twice produces same result

### Parallel Opportunities
- T005 and T006 can be written in parallel (different test classes)

### Dependencies
- Depends on WP01

### Risks & Mitigations
- Monkeypatching `Path.home()` can be tricky — use `monkeypatch.setattr` on the `global_config` module's `Path` reference

**Requirements Refs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008

---

## Work Package WP03: Documentation (Priority: P2)

**Goal**: Document the global model config for users — where the file lives, the YAML schema, valid command names, and example config snippets.
**Independent Test**: A new user can follow the docs to configure model selection without reading source code.
**Prompt**: `tasks/WP03-documentation.md`
**Estimated size**: ~200 lines

### Included Subtasks
- [x] T007 Add model-selection section to `docs/` (new file or extend existing config docs) with schema, example, and known command names

### Implementation Notes
- Check `docs/` for existing configuration documentation to extend rather than create a new file
- Include: file location, full YAML schema with all 12 known commands, behaviour on missing/partial config, note that model names are not validated

### Dependencies
- Depends on WP01 (need final list of supported command names)

**Requirements Refs**: FR-009

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02 + WP03 (parallel)
- **Parallelization**: WP02 and WP03 can run concurrently after WP01 merges
- **MVP Scope**: WP01 alone delivers the core feature

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create `global_config.py` | WP01 | P0 | Yes (stub first) |
| T002 | Create migration `m_2_0_4_model_injection.py` | WP01 | P0 | Yes (stub first) |
| T003 | Handle edge cases in migration | WP01 | P0 | No |
| T004 | Verify migration auto-registration | WP01 | P0 | No |
| T005 | Unit tests for `global_config.py` | WP02 | P1 | Yes |
| T006 | Integration tests for migration | WP02 | P1 | Yes |
| T007 | User documentation | WP03 | P2 | Yes (after WP01) |
