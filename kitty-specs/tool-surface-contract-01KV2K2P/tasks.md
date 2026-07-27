# Tasks: ToolSurfaceContract -- Unified Tool Surface Registry

**Mission**: tool-surface-contract-01KV2K2P
**Branch**: `feat/tool-surface-contract` → merge target `feat/tool-surface-contract`
**Date**: 2026-06-14
**Parent epic**: #1945 | **Glossary PR**: #1935 (prerequisite)

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T001 | Create `src/specify_cli/tool_surface/` package with `__init__.py` | WP01 | |
| T002 | Implement `enums.py` with all surface-contract enumerations | WP01 | [P] |
| T003 | Implement `model.py` with core dataclasses | WP01 | [P] |
| T004 | Implement `registry.py` stub (`ToolSurfaceRegistry`) | WP01 | |
| T005 | Implement `providers/base.py` (`AbstractSurfaceProvider` protocol) | WP01 | [P] |
| T006 | Implement `builtins.py` stub (empty surface definitions for 19 harnesses) | WP01 | [P] |
| T007 | Write unit tests for enums and model | WP01 | [P] |
| T008 | Write `test_migration_compat.py` asserting `doctor skills --json` schema is unchanged | WP02 | |
| T009 | Write `test_agent_config_compat.py` asserting `agent config` interface is unchanged | WP02 | [P] |
| T010 | Add compat fixture helpers and baseline snapshots | WP02 | |
| T011 | Write compatibility contract doc (`contracts/migration-compatibility.md`) | WP02 | [P] |
| T012 | Implement `providers/command_skills.py` wrapping `command_installer` | WP03 | |
| T013 | Implement `plan.py` `SurfacePlanBuilder` for command skills | WP03 | |
| T014 | Implement `status.py` `SurfaceStatusService` for command skills | WP03 | |
| T015 | Implement `findings.py` with stable finding code constants | WP03 | [P] |
| T016 | Implement `repair.py` `SurfaceRepairService` for command skills | WP03 | |
| T017 | Add `doctor tool-surfaces` subcommand to `cli/commands/doctor.py` | WP03 | |
| T018 | Write integration tests for `doctor tool-surfaces --kind command-skill` | WP03 | [P] |
| T019 | Implement `providers/session_presence.py` wrapping `session_presence.writers.registry` | WP04 | |
| T020 | Implement `providers/native_config.py` for hooks and tool-specific glue | WP04 | [P] |
| T021 | Extend `status.py` and `findings.py` for session-presence provider outputs | WP04 | |
| T022 | Extend repair service for session-presence findings | WP04 | |
| T023 | Write tests for session-presence provider | WP04 | [P] |
| T024 | Implement `providers/managed_skills.py` wrapping `skills.registry/installer/verifier` | WP05 | |
| T025 | Extend `status.py` and `findings.py` for doctrine-skill kind | WP05 | |
| T026 | Extend repair service for doctrine-skill findings | WP05 | |
| T027 | Write tests for managed-skill provider | WP05 | [P] |
| T028 | Implement `profiles/projection.py` -- project built-in and overlay profiles | WP06 | |
| T029 | Implement `profiles/renderers.py` -- per-harness render functions | WP06 | |
| T030 | Implement `profiles/manifest.py` -- track projected files with hashes | WP06 | [P] |
| T031 | Implement `providers/agent_profiles.py` wrapping the profile repository | WP06 | |
| T032 | Extend `status.py` and `findings.py` for agent-profile kind (incl. `RESEARCH_GAP`) | WP06 | |
| T033 | Write tests for profile projection and provider | WP06 | [P] |
| T034 | Refactor `cli/commands/agent/config.py` to route through `SurfacePlan` | WP07 | |
| T035 | Remove duplicated recomputation logic from `agent/config.py` | WP07 | |
| T036 | Verify migration compat fixtures still pass after refactor | WP07 | |
| T037 | Write/update tests for refactored `agent config` | WP07 | [P] |
| T038 | Implement `docs.py` `DocsLinter` scanning doc files for generated-path references | WP08 | |
| T039 | Build registry path index for doc reference validation | WP08 | |
| T040 | Add CI/lint integration for docs contract check | WP08 | |
| T041 | Fix existing doc paths that drift from registry | WP08 | [P] |
| T042 | Write tests for docs linter | WP08 | [P] |
| T043 | Implement `bundles/model.py` (`PluginBundle`, `BundleValidationResult`) | WP09 | |
| T044 | Implement `bundles/claude.py` Claude Code plugin bundle projection | WP09 | |
| T045 | Implement `bundles/copilot.py` and `bundles/vscode.py` bundle projections | WP09 | [P] |
| T046 | Implement `providers/plugin_bundle.py` wrapping bundle projections | WP09 | |
| T047 | Extend `status.py` and `findings.py` for plugin-bundle kind | WP09 | |
| T048 | Write tests for plugin bundle validation | WP09 | [P] |
| T049 | Implement `providers/slash_commands.py` wrapping `AGENT_COMMAND_CONFIG`, `runtime.agent_commands`, and `_load_slash_command_state()` | WP03 | [P] |

---

## Work Packages

### WP01 -- Registry Skeleton and Glossary-Compliant Naming

**Goal**: Introduce `src/specify_cli/tool_surface/` with enums, dataclasses, registry stub, provider protocol, and 19-harness builtins stub. No runtime behavior changes.
**Priority**: Critical -- all subsequent WPs depend on this
**Independent test**: `pytest tests/specify_cli/tool_surface/test_enums.py tests/specify_cli/tool_surface/test_model.py tests/specify_cli/tool_surface/test_registry.py` passes
**Estimated prompt size**: ~320 lines
**Depends on**: none
**Child issue**: #1936

- [ ] T001 Create `src/specify_cli/tool_surface/` package with `__init__.py` (WP01)
- [ ] T002 Implement `enums.py` with all surface-contract enumerations (WP01)
- [ ] T003 Implement `model.py` with core dataclasses (WP01)
- [ ] T004 Implement `registry.py` stub (`ToolSurfaceRegistry`) (WP01)
- [ ] T005 Implement `providers/base.py` (`AbstractSurfaceProvider` protocol) (WP01)
- [ ] T006 Implement `builtins.py` stub (WP01)
- [ ] T007 Write unit tests for enums and model (WP01)

**Prompt**: [WP01-registry-skeleton.md](tasks/WP01-registry-skeleton.md)

---

### WP02 -- Migration and Compatibility Gate

**Goal**: Establish integration test fixtures that assert `doctor skills --json` schema and `agent config` interface are unchanged. These fixtures gate all subsequent WPs.
**Priority**: Critical -- must merge before WP03-WP09; acts as regression guard
**Independent test**: `pytest tests/specify_cli/tool_surface/integration/test_migration_compat.py tests/specify_cli/tool_surface/integration/test_agent_config_compat.py` passes
**Estimated prompt size**: ~280 lines
**Depends on**: WP01
**Child issue**: #1944

- [ ] T008 Write `test_migration_compat.py` asserting `doctor skills --json` schema unchanged (WP02)
- [ ] T009 Write `test_agent_config_compat.py` asserting `agent config` interface unchanged (WP02)
- [ ] T010 Add compat fixture helpers and baseline snapshots (WP02)
- [ ] T011 Write compatibility contract doc (WP02)

**Prompt**: [WP02-migration-compat-gate.md](tasks/WP02-migration-compat-gate.md)

---

### WP03 -- Command-Skill Provider and `doctor tool-surfaces`

**Goal**: Route command-skill status through the provider model; add `spec-kitty doctor tool-surfaces --json/--fix` with stable finding codes.
**Priority**: High -- first user-visible output; establishes finding code contract
**Independent test**: `pytest tests/specify_cli/tool_surface/integration/test_doctor_tool_surfaces_cli.py -k command_skill` passes; `doctor skills --json` schema regression test (WP02) still passes
**Estimated prompt size**: ~420 lines
**Depends on**: WP01, WP02
**Child issue**: #1937

- [ ] T012 Implement `providers/command_skills.py` (WP03)
- [ ] T013 Implement `plan.py` `SurfacePlanBuilder` for command skills (WP03)
- [ ] T014 Implement `status.py` `SurfaceStatusService` for command skills (WP03)
- [ ] T015 Implement `findings.py` with stable finding code constants (WP03)
- [ ] T016 Implement `repair.py` `SurfaceRepairService` for command skills (WP03)
- [ ] T017 Add `doctor tool-surfaces` subcommand to `cli/commands/doctor.py` (WP03)
- [ ] T018 Write integration tests for `doctor tool-surfaces --kind command-skill` (WP03)
- [ ] T049 Implement `providers/slash_commands.py` wrapping AGENT_COMMAND_CONFIG and runtime.agent_commands (WP03)

**Prompt**: [WP03-command-skill-provider.md](tasks/WP03-command-skill-provider.md)

---

### WP04 -- Session-Presence Provider

**Goal**: Add a `SurfaceProvider` for session presence surfaces, expanding them into distinct `context_file`, `hook`, and `rule` SurfaceKind instances in doctor output. (`session_presence` is a provider name, not a SurfaceKind.)
**Priority**: High
**Independent test**: `pytest tests/specify_cli/tool_surface/providers/test_session_presence.py` passes; migration compat tests still pass
**Estimated prompt size**: ~300 lines
**Depends on**: WP01, WP02, WP03
**Child issue**: #1938

- [ ] T019 Implement `providers/session_presence.py` (WP04)
- [ ] T020 Implement `providers/native_config.py` (WP04)
- [ ] T021 Extend `status.py` and `findings.py` for session-presence provider outputs (WP04)
- [ ] T022 Extend repair service for session-presence findings (WP04)
- [ ] T023 Write tests for session-presence provider (WP04)

**Prompt**: [WP04-session-presence-provider.md](tasks/WP04-session-presence-provider.md)

---

### WP05 -- Managed Doctrine Skill Provider

**Goal**: Add a `SurfaceProvider` for managed doctrine skills, explicitly separating them from command skills in doctor output.
**Priority**: High
**Independent test**: `pytest tests/specify_cli/tool_surface/providers/test_managed_skills.py` passes; migration compat tests still pass
**Estimated prompt size**: ~280 lines
**Depends on**: WP01, WP02, WP03
**Child issue**: #1939

- [ ] T024 Implement `providers/managed_skills.py` (WP05)
- [ ] T025 Extend `status.py` and `findings.py` for doctrine-skill kind (WP05)
- [ ] T026 Extend repair service for doctrine-skill findings (WP05)
- [ ] T027 Write tests for managed-skill provider (WP05)

**Prompt**: [WP05-managed-doctrine-skill-provider.md](tasks/WP05-managed-doctrine-skill-provider.md)

---

### WP06 -- Native Agent Profile Projection

**Goal**: Project built-in and org/project overlay profiles into host-native agent/subagent formats; track in manifest; add to `doctor tool-surfaces` output.
**Priority**: Medium
**Independent test**: `pytest tests/specify_cli/tool_surface/profiles/` passes; tools without native agent support report `RESEARCH_GAP`
**Estimated prompt size**: ~380 lines
**Depends on**: WP01, WP02, WP03
**Child issue**: #1940

- [ ] T028 Implement `profiles/projection.py` (WP06)
- [ ] T029 Implement `profiles/renderers.py` (WP06)
- [ ] T030 Implement `profiles/manifest.py` (WP06)
- [ ] T031 Implement `providers/agent_profiles.py` (WP06)
- [ ] T032 Extend `status.py` and `findings.py` for agent-profile kind (WP06)
- [ ] T033 Write tests for profile projection and provider (WP06)

**Prompt**: [WP06-native-agent-profile-projection.md](tasks/WP06-native-agent-profile-projection.md)

---

### WP07 -- Legacy Agent Config Refactor

**Goal**: Refactor `spec-kitty agent config list/status/sync` to consume `SurfacePlan` internally while preserving its external interface unchanged.
**Priority**: Medium
**Independent test**: `pytest tests/specify_cli/cli/commands/test_agent_config.py` passes; WP02 compat fixtures pass
**Estimated prompt size**: ~260 lines
**Depends on**: WP01, WP02, WP03
**Child issue**: #1941

- [ ] T034 Refactor `cli/commands/agent/config.py` to route through `SurfacePlan` (WP07)
- [ ] T035 Remove duplicated recomputation logic from `agent/config.py` (WP07)
- [ ] T036 Verify migration compat fixtures still pass (WP07)
- [ ] T037 Write/update tests for refactored `agent config` (WP07)

**Prompt**: [WP07-legacy-agent-config-refactor.md](tasks/WP07-legacy-agent-config-refactor.md)

---

### WP08 -- Docs Contract Lint

**Goal**: Add `DocsLinter` that validates generated/native path references in docs against the registry; integrate into CI/lint.
**Priority**: Medium
**Independent test**: `pytest tests/specify_cli/tool_surface/test_docs.py` passes; lint step fails on a doc file with a drift path
**Estimated prompt size**: ~300 lines
**Depends on**: WP01 through WP06
**Child issue**: #1942

- [x] T038 Implement `docs.py` `DocsLinter` (WP08)
- [x] T039 Build registry path index for doc reference validation (WP08)
- [x] T040 Add CI/lint integration for docs contract check (WP08)
- [x] T041 Fix existing doc paths that drift from registry (WP08)
- [x] T042 Write tests for docs linter (WP08)

**Prompt**: [WP08-docs-contract-lint.md](tasks/WP08-docs-contract-lint.md)

---

### WP09 -- Plugin Bundle Projection and Validation

**Goal**: Implement plugin bundle projection and pre-publish validation for Claude Code, Copilot, and VS Code targets. No auto-install. No marketplace push.
**Priority**: Low (release/staging capability)
**Independent test**: `pytest tests/specify_cli/tool_surface/providers/test_plugin_bundle.py` passes; validation correctly reports incomplete bundles
**Estimated prompt size**: ~360 lines
**Depends on**: WP01 through WP06
**Child issue**: #1943

- [x] T043 Implement `bundles/model.py` (WP09)
- [x] T044 Implement `bundles/claude.py` (WP09)
- [x] T045 Implement `bundles/copilot.py` and `bundles/vscode.py` (WP09)
- [x] T046 Implement `providers/plugin_bundle.py` (WP09)
- [x] T047 Extend `status.py` and `findings.py` for plugin-bundle kind (WP09)
- [x] T048 Write tests for plugin bundle validation (WP09)

**Prompt**: [WP09-plugin-bundle-validation.md](tasks/WP09-plugin-bundle-validation.md)
