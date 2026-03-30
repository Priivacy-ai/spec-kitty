# Work Packages: Hybrid Prompt and Shim Agent Surface

**Inputs**: Design documents from `kitty-specs/058-hybrid-prompt-and-shim-agent-surface/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md

**Tests**: Required — 90%+ coverage on new code, mypy --strict.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`).

---

## Work Package WP01: Restore Canonical Command Templates (Priority: P0)

**Goal**: Create `src/specify_cli/missions/software-dev/command-templates/` with cleaned-up prompts for all 9 prompt-driven commands. Port today's fixes (project root checkout, template paths, ownership, --feature guidance).
**Independent Test**: All 9 files exist, contain 50+ lines each, have zero references to `057-`, no `.kittify/missions/` read instructions, and use "project root checkout" not "planning repository".
**Prompt**: `tasks/WP01-restore-command-templates.md`
**Requirement Refs**: FR-002, C-004

### Included Subtasks
- [ ] T001 Create `src/specify_cli/missions/software-dev/command-templates/` directory
- [ ] T002 Port and clean specify.md — strip 057 slugs, hardcoded paths, dev-repo references
- [ ] T003 Port and clean plan.md
- [ ] T004 Port and clean tasks.md (ensure ownership metadata guidance is present)
- [ ] T005 [P] Port and clean tasks-outline.md and tasks-packages.md
- [ ] T006 [P] Port and clean checklist.md, analyze.md, research.md, constitution.md
- [ ] T007 Verify all 9 prompts: "project root checkout", no `.kittify/missions/` template reads, `--feature` guidance, no 057 slugs, no `/Users/robert/` paths

### Implementation Notes
- Source: `.claude/commands/spec-kitty.*.md` files in this dev repo (with today's fixes applied)
- Strip frontmatter `---` blocks if present (the asset generator adds its own)
- The filename convention is `specify.md` not `spec-kitty.specify.md` (the prefix is added during rendering)

### Dependencies
- None (starting package).

---

## Work Package WP02: Update Registry and Generator (Priority: P0)

**Goal**: Add PROMPT_DRIVEN / CLI_DRIVEN classification to the shim registry. Update generator to only produce shims for CLI-driven commands. Update shim entrypoint dispatch.
**Independent Test**: `generate_all_shims()` produces exactly 7 shim files (not 16). `shim_dispatch()` returns None for prompt-driven commands.
**Prompt**: `tasks/WP02-registry-and-generator.md`
**Requirement Refs**: FR-001, FR-004, FR-007

### Included Subtasks
- [ ] T008 Add `PROMPT_DRIVEN_COMMANDS` and `CLI_DRIVEN_COMMANDS` frozensets to `src/specify_cli/shims/registry.py`
- [ ] T009 Update `generate_all_shims()` in `src/specify_cli/shims/generator.py` to skip prompt-driven commands
- [ ] T010 Update `shim_dispatch()` in `src/specify_cli/shims/entrypoints.py` — return None for prompt-driven, delegate CLI-driven to existing handlers
- [ ] T011 [P] Tests for registry classification and generator output count

### Implementation Notes
- `PROMPT_DRIVEN_COMMANDS`: specify, plan, tasks, tasks-outline, tasks-packages, checklist, analyze, research, constitution
- `CLI_DRIVEN_COMMANDS`: implement, review, accept, merge, status, dashboard, tasks-finalize
- Verify `PROMPT_DRIVEN_COMMANDS | CLI_DRIVEN_COMMANDS == CONSUMER_SKILLS`

### Dependencies
- None (independent of WP01).

---

## Work Package WP03: Update Init for Hybrid Install (Priority: P0)

**Goal**: Update `spec-kitty init` to install full prompts for prompt-driven commands (via `generate_agent_assets()`) and thin shims for CLI-driven commands (via `generate_all_shims()`).
**Independent Test**: After `spec-kitty init` in a temp dir, `spec-kitty.specify.md` has 100+ lines (full prompt) and `spec-kitty.implement.md` has <5 lines (thin shim).
**Prompt**: `tasks/WP03-init-hybrid-install.md`
**Requirement Refs**: FR-003, FR-004, FR-005

### Included Subtasks
- [ ] T012 Update `init.py` to call `generate_agent_assets()` for prompt-driven commands using the restored command-templates directory
- [ ] T013 Verify the 4-tier resolution chain (`overrides → legacy → global runtime → package`) resolves correctly for the restored templates
- [ ] T014 Ensure `ensure_runtime()` deploys the new command-templates to `~/.kittify/missions/software-dev/command-templates/`
- [ ] T015 [P] Integration test: `spec-kitty init` in temp dir produces hybrid output

### Implementation Notes
- `generate_agent_assets()` in `src/specify_cli/template/asset_generator.py` expects a `command_templates_dir` parameter
- The 4-tier resolver is `_resolve_mission_command_templates_dir()` — verify it finds the new files
- `generate_all_shims()` call stays but now only produces 7 files (after WP02)
- `ensure_runtime()` in `runtime/bootstrap.py` copies from package `missions/` to `~/.kittify/missions/` — no changes needed, just verify

### Dependencies
- Depends on WP01 (templates must exist) and WP02 (generator must only produce CLI shims).

---

## Work Package WP04: Migration for Consumer Projects (Priority: P1)

**Goal**: Write a migration that replaces thin shims with full prompts for prompt-driven commands in existing consumer projects.
**Independent Test**: Set up a project with 16 thin shims, run upgrade, verify 9 are replaced with full prompts and 7 remain as shims.
**Prompt**: `tasks/WP04-consumer-migration.md`
**Requirement Refs**: FR-008, FR-009

### Included Subtasks
- [ ] T016 Write `m_2_1_3_restore_prompt_commands.py` — detect thin shims for prompt-driven commands, replace with full prompts from global runtime
- [ ] T017 Ensure migration is idempotent (running twice produces same result)
- [ ] T018 [P] Test migration with mock consumer project

### Implementation Notes
- Detection: if file is <10 lines and contains "spec-kitty agent shim", it's a thin shim to replace
- Source: read full prompt from `~/.kittify/missions/software-dev/command-templates/` (deployed by ensure_runtime)
- Render through `generate_agent_assets()` for proper agent-specific formatting
- Register in migration registry with `target_version = "2.1.3"`

### Dependencies
- Depends on WP03 (init must work so the runtime has templates deployed).

---

## Work Package WP05: Deploy to Consumer Projects (Priority: P1)

**Goal**: Run `spec-kitty upgrade` on spec-kitty-tracker, spec-kitty-saas, and spec-kitty-planning to restore working slash commands.
**Independent Test**: Agent in each project can invoke `/spec-kitty.specify` and see the full discovery workflow prompt.
**Prompt**: `tasks/WP05-deploy-to-consumers.md`
**Requirement Refs**: FR-008

### Included Subtasks
- [ ] T019 Delete `~/.kittify/cache/version.lock` to force runtime refresh with new templates
- [ ] T020 Run `spec-kitty upgrade` in spec-kitty-tracker
- [ ] T021 Run `spec-kitty upgrade` in spec-kitty-saas
- [ ] T022 Run `spec-kitty upgrade` in spec-kitty-planning
- [ ] T023 Verify each project: `spec-kitty.specify.md` is full prompt, `spec-kitty.implement.md` is thin shim

### Implementation Notes
- This is operational, not code
- May need to handle the existing `m_2_1_3_fix_planning_repository_terminology` migration that already ran
- The new migration should be named differently or check if prompts are already full

### Dependencies
- Depends on WP04 (migration must exist).

---

## Work Package WP06: Tests and Final Validation (Priority: P1)

**Goal**: Full test suite passes. All new code has 90%+ coverage. mypy --strict on new/modified modules.
**Independent Test**: `python -m pytest tests/` passes. No regressions from 057 test stabilization.
**Prompt**: `tasks/WP06-tests-and-validation.md`
**Requirement Refs**: NFR-003, NFR-004

### Included Subtasks
- [ ] T024 Update existing shim tests to expect 7 files not 16
- [ ] T025 Update init tests to verify hybrid output
- [ ] T026 Test prompt content: all 9 files have no 057 slugs, no `.kittify/missions/` reads, use "project root checkout"
- [ ] T027 Run full test suite, fix any regressions
- [ ] T028 mypy --strict on modified modules

### Dependencies
- Depends on WP03 (init must work before testing).

---

## Dependency & Execution Summary

```
Wave 1: WP01 ──────── WP02
        (Templates)   (Registry)
              \        /
Wave 2:       WP03
              (Init)
                │
Wave 3: WP04 ──────── WP06
        (Migration)   (Tests)
                │
Wave 4:       WP05
              (Deploy)
```

- **Parallelization**: WP01 and WP02 can run in parallel (Wave 1)
- **MVP**: WP01-WP03 deliver the core fix (init works for new projects)
- **Critical path**: WP01 → WP03 → WP04 → WP05

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP02 |
| FR-002 | WP01 |
| FR-003 | WP03 |
| FR-004 | WP02, WP03 |
| FR-005 | WP03 |
| FR-006 | WP02 |
| FR-007 | WP02 |
| FR-008 | WP04, WP05 |
| FR-009 | WP04 |
| FR-010 | Deferred (Low priority) |
| NFR-003 | WP06 |
| NFR-004 | WP06 |
| C-004 | WP01 |

---

## Subtask Index

| ID | Summary | WP | Parallel? |
|----|---------|-----|-----------|
| T001 | Create command-templates directory | WP01 | No |
| T002 | Port specify.md | WP01 | No |
| T003 | Port plan.md | WP01 | No |
| T004 | Port tasks.md | WP01 | No |
| T005 | Port tasks-outline.md, tasks-packages.md | WP01 | Yes |
| T006 | Port checklist, analyze, research, constitution | WP01 | Yes |
| T007 | Verify all 9 prompts clean | WP01 | No |
| T008 | Add PROMPT_DRIVEN / CLI_DRIVEN to registry | WP02 | No |
| T009 | Update generate_all_shims() | WP02 | No |
| T010 | Update shim_dispatch() | WP02 | No |
| T011 | Tests for registry/generator | WP02 | Yes |
| T012 | Update init.py for hybrid install | WP03 | No |
| T013 | Verify 4-tier resolution | WP03 | No |
| T014 | Verify ensure_runtime deploys templates | WP03 | No |
| T015 | Integration test: init hybrid output | WP03 | Yes |
| T016 | Write migration | WP04 | No |
| T017 | Test migration idempotency | WP04 | No |
| T018 | Test migration with mock project | WP04 | Yes |
| T019 | Delete version.lock for refresh | WP05 | No |
| T020 | Upgrade spec-kitty-tracker | WP05 | Yes |
| T021 | Upgrade spec-kitty-saas | WP05 | Yes |
| T022 | Upgrade spec-kitty-planning | WP05 | Yes |
| T023 | Verify hybrid output in all 3 projects | WP05 | No |
| T024 | Update shim tests | WP06 | No |
| T025 | Update init tests | WP06 | No |
| T026 | Test prompt content cleanliness | WP06 | Yes |
| T027 | Full test suite | WP06 | No |
| T028 | mypy --strict | WP06 | No |
