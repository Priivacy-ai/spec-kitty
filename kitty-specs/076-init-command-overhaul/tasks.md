# Tasks: Init Command Overhaul (076)

**Feature:** 076-init-command-overhaul  
**Branch:** `main` → merge target: `main`  
**Generated:** 2026-04-08

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|---------|
| T001 | Delete AgentSelectionConfig dataclass + select_implementer + select_reviewer from agent_config.py | WP01 | No | [D] | [D] |
| T002 | Remove `selection: AgentSelectionConfig` field from AgentConfig | WP01 | No | [D] |
| T003 | Remove selection construction from load_agent_config() | WP01 | No | [D] |
| T004 | Remove selection serialization from save_agent_config() | WP01 | No | [D] |
| T005 | Remove AgentSelectionConfig from __all__ | WP01 | No | [D] |
| T006 | Fix load_agent_config() to try 'tools' key first, fallback to 'agents' | WP01 | No | [D] |
| T007 | Update test_agent_config_unit.py — remove preference tests, add tools-key test | WP01 | No | [D] |
| T008 | Remove all 11 CLI flag definitions from init() signature | WP02 | No |
| T009 | Remove _resolve_preferred_agents() helper function | WP02 | No |
| T010 | Remove Stage 3: preferred agent selection block (lines 911–970) | WP02 | No |
| T011 | Remove Stage 4: script type selection (lines 982–992) | WP02 | No |
| T012 | Remove Stage 5 + Stage 9: mission selection and _activate_mission() call | WP02 | No |
| T013 | Remove --ignore-agent-tools block (lines 884–908) | WP02 | No |
| T014 | Remove remote template mode branch (lines 1006–1021, 1144–1163) | WP02 | No |
| T015 | Remove _apply_doctrine_defaults, _run_inline_interview, _run_doctrine_stack_init (defs + call) | WP02 | No |
| T016 | Remove _maybe_generate_structure_templates definition + call | WP02 | No |
| T017 | Remove ensure_dashboard_running call + initial git commit block | WP02 | No |
| T018 | Fix ensure_runtime() error handling; add global skill installation; fix charter dir in _prepare_project_minimal | WP02 | No |
| T019 | Delete github_client.py; clean template/manager.py (get_local_repo_root + script-copy logic) | WP03 | No |
| T020 | Delete test_init_doctrine.py; update test_init_command.py (remove removed-flag tests) | WP03 | [P] |
| T021 | Update test_m_2_0_1_tool_config_key_rename.py fixtures | WP03 | [P] |
| T022 | Write new init integration tests covering the 14-case positive flow | WP03 | No |
| T023 | Run full test suite + mypy --strict on all Lane A touched files | WP03 | No |
| T024 | Create m_3_2_1_strip_selection_config.py skeleton (migration_id, target_version, imports) | WP04 | No | [D] |
| T025 | Implement detect() + apply() with dry_run support | WP04 | No | [D] |
| T026 | Handle both 'agents.selection' and 'tools.selection' key variants | WP04 | No | [D] |
| T027 | Write test_m_3_2_1_strip_selection_config.py with 5 test cases | WP04 | No | [D] |
| T028 | mypy check + verify migration ID unique in registry | WP04 | No | [D] |
| T029 | Create m_3_2_2_safe_globalize_commands.py skeleton (new migration_id, do NOT touch m_3_1_2) | WP05 | No | [D] |
| T030 | Implement detect() — same pattern as m_3_1_2 | WP05 | No | [D] |
| T031 | Implement _global_commands_present() safety helper | WP05 | No | [D] |
| T032 | Implement apply() with all 4 safety invariants per-agent | WP05 | No | [D] |
| T033 | Write test_m_3_2_2_safe_globalize_commands.py with 6 test cases | WP05 | No | [D] |
| T034 | mypy check; verify m_3_1_2_globalize_commands.py is NOT modified (git diff must be clean for that file) | WP05 | No | [D] |
| T035 | Determine ADR sequence number N; create ADR-A (global ~/.kittify/ as machine-level runtime) | WP06 | No | [D] |
| T036 | Create ADR-B (package-bundled templates as sole source) | WP06 | [D] |
| T037 | Create ADR-C (global skill installation with per-project symlinks) | WP06 | [D] |
| T038 | Create ADR-D (charter and doctrine not init-time concerns) | WP06 | [D] |
| T039 | Create ADR-E (shim generation supersedes script-type dispatch) | WP06 | [D] |
| T040 | Create ADR-F (global agent commands supersede per-project copies; safe removal migration) | WP06 | [D] |
| T041 | Create ADR-G (preferred agent roles removed as unused concept) | WP06 | [D] |
| T042 | Update docs/how-to/non-interactive-init.md — remove preference flag examples | WP07 | [P] |
| T043 | Update docs/reference/cli-commands.md — remove 11 removed flags from init table | WP07 | [P] |
| T044 | Update docs/reference/configuration.md — remove selection block and all preference entries | WP07 | [P] |
| T045 | Update docs/how-to/manage-agents.md — remove preference field references | WP07 | [P] |
| T046 | Update docs/2x/model-discipline-routing.md — remove static preference config reference | WP07 | [P] |
| T047 | Verification grep: confirm zero preference references remain in docs/ | WP07 | No |

---

## Work Packages

---

### WP01 — Agent Config Data Model Cleanup

**Lane:** A · **Priority:** Critical · **Est. prompt:** ~320 lines  
**Depends on:** nothing  
**Owned files:** `src/specify_cli/core/agent_config.py`, `tests/agent/test_agent_config_unit.py`

**Goal:** Remove the entirely unused `preferred_implementer`/`preferred_reviewer` preference system from the data model and fix the pre-existing `agents→tools` key mismatch in `load_agent_config()`.

- [ ] T001 Delete AgentSelectionConfig dataclass + select_implementer + select_reviewer from agent_config.py (WP01)
- [ ] T002 Remove `selection: AgentSelectionConfig` field from AgentConfig (WP01)
- [ ] T003 Remove selection construction from load_agent_config() (WP01)
- [ ] T004 Remove selection serialization from save_agent_config() (WP01)
- [ ] T005 Remove AgentSelectionConfig from __all__ (WP01)
- [ ] T006 Fix load_agent_config() to try 'tools' key first, fallback to 'agents' (WP01)
- [ ] T007 Update test_agent_config_unit.py — remove preference tests, add tools-key test (WP01)

**Definition of done:** `grep -r "AgentSelectionConfig\|select_implementer\|select_reviewer\|preferred_implementer\|preferred_reviewer" src/specify_cli/core/` → 0 results; `mypy --strict` clean; tests green.

---

### WP02 — init.py Surgery: Remove All Flags and Stages

**Lane:** A · **Priority:** Critical · **Est. prompt:** ~620 lines  
**Depends on:** WP01  
**Owned files:** `src/specify_cli/cli/commands/init.py`

**Goal:** Remove all 11 CLI flags and their associated processing stages from init.py. Fix the ensure_runtime() error handling and add global skill installation. Result is a coherent, lean init command following the positive flow defined in plan.md.

- [ ] T008 Remove all 11 CLI flag definitions from init() signature (WP02)
- [ ] T009 Remove _resolve_preferred_agents() helper function (WP02)
- [ ] T010 Remove Stage 3: preferred agent selection block (lines 911–970) (WP02)
- [ ] T011 Remove Stage 4: script type selection (lines 982–992) (WP02)
- [ ] T012 Remove Stage 5 + Stage 9: mission selection and _activate_mission() call (WP02)
- [ ] T013 Remove --ignore-agent-tools block (lines 884–908) (WP02)
- [ ] T014 Remove remote template mode branch (lines 1006–1021, 1144–1163) (WP02)
- [ ] T015 Remove _apply_doctrine_defaults, _run_inline_interview, _run_doctrine_stack_init (defs + call) (WP02)
- [ ] T016 Remove _maybe_generate_structure_templates definition + call (WP02)
- [ ] T017 Remove ensure_dashboard_running call + initial git commit block (WP02)
- [ ] T018 Fix ensure_runtime() error handling; add global skill installation; fix charter dir in _prepare_project_minimal (WP02)

**Definition of done:** `spec-kitty init --help` shows ≤4 option flags; `spec-kitty init --non-interactive --ai claude` exits 0; mypy clean.

---

### WP03 — Template Module Cleanup + Test Suite Overhaul

**Lane:** A · **Priority:** High · **Est. prompt:** ~380 lines  
**Depends on:** WP02  
**Owned files:** `src/specify_cli/template/github_client.py`, `src/specify_cli/template/manager.py`, `tests/specify_cli/cli/commands/test_init_doctrine.py`, `tests/agent/test_init_command.py`, `tests/upgrade/migrations/test_m_2_0_1_tool_config_key_rename.py`, `tests/specify_cli/cli/commands/test_init_integration.py`

**Goal:** Delete github_client.py, clean template/manager.py, delete the doctrine test file, update affected test files, and write the new positive-flow integration tests for the redesigned init.

- [ ] T019 Delete github_client.py; clean template/manager.py (get_local_repo_root + script-copy logic) (WP03)
- [ ] T020 Delete test_init_doctrine.py; update test_init_command.py (remove removed-flag tests) (WP03)
- [ ] T021 Update test_m_2_0_1_tool_config_key_rename.py fixtures (WP03)
- [ ] T022 Write new init integration tests covering the 14-case positive flow (WP03)
- [ ] T023 Run full test suite + mypy --strict on all Lane A touched files (WP03)

**Definition of done:** `src/specify_cli/template/github_client.py` does not exist; `tests/specify_cli/cli/commands/test_init_doctrine.py` does not exist; `pytest` full suite green; mypy clean.

---

### WP04 — Migration A: Strip Selection Keys from config.yaml

**Lane:** B · **Priority:** High · **Est. prompt:** ~260 lines  
**Depends on:** nothing  
**Owned files:** `src/specify_cli/upgrade/migrations/m_3_2_1_strip_selection_config.py`, `tests/upgrade/migrations/test_m_3_2_1_strip_selection_config.py`

**Goal:** New upgrade migration that strips `agents.selection.preferred_implementer` and `agents.selection.preferred_reviewer` from existing `.kittify/config.yaml` files on `spec-kitty upgrade`.

- [ ] T024 Create m_3_2_1_strip_selection_config.py skeleton (WP04)
- [ ] T025 Implement detect() + apply() with dry_run support (WP04)
- [ ] T026 Handle both 'agents.selection' and 'tools.selection' key variants (WP04)
- [ ] T027 Write test_m_3_2_1_strip_selection_config.py with 5 test cases (WP04)
- [ ] T028 mypy check + verify migration ID unique in registry (WP04)

**Definition of done:** Migration strips selection keys from both `agents` and `tools` root key layouts; 5 tests green; mypy clean.

---

### WP05 — Migration B: Safe Local Command Removal (m_3_2_2)

**Lane:** B · **Priority:** High · **Est. prompt:** ~380 lines  
**Depends on:** WP04  
**Owned files:** `src/specify_cli/upgrade/migrations/m_3_2_2_safe_globalize_commands.py`, `tests/upgrade/migrations/test_m_3_2_2_safe_globalize_commands.py`

**Goal:** New upgrade migration that safely removes per-project spec-kitty command files when and only when global equivalents are confirmed present — eliminating duplicate slash commands in AI tools. **Must NOT modify `m_3_1_2_globalize_commands.py`.**

- [ ] T029 Create m_3_2_2_safe_globalize_commands.py skeleton (new migration_id, do NOT touch m_3_1_2) (WP05)
- [ ] T030 Implement detect() — same pattern as m_3_1_2 (WP05)
- [ ] T031 Implement _global_commands_present() safety helper (WP05)
- [ ] T032 Implement apply() with all 4 safety invariants per-agent (WP05)
- [ ] T033 Write test_m_3_2_2_safe_globalize_commands.py with 6 test cases (WP05)
- [ ] T034 mypy check; verify m_3_1_2_globalize_commands.py is NOT modified (WP05)

**Definition of done:** 6 safety-invariant tests green; no project-local files deleted when global is absent; mypy clean; `git diff src/specify_cli/upgrade/migrations/m_3_1_2_globalize_commands.py` empty.

---

### WP06 — Author 7 Architecture Decision Records

**Lane:** C · **Priority:** High · **Est. prompt:** ~420 lines  
**Depends on:** nothing  
**Owned files:** `architecture/adrs/2026-04-08-*`

**Goal:** Author all 7 ADRs documenting the architectural decisions made during this overhaul. These are required deliverables per DIRECTIVE_003.

- [ ] T035 Determine ADR sequence number N; create ADR-A (global ~/.kittify/ as machine-level runtime) (WP06)
- [ ] T036 Create ADR-B (package-bundled templates as sole source) (WP06)
- [ ] T037 Create ADR-C (global skill installation with per-project symlinks) (WP06)
- [ ] T038 Create ADR-D (charter and doctrine not init-time concerns) (WP06)
- [ ] T039 Create ADR-E (shim generation supersedes script-type dispatch) (WP06)
- [ ] T040 Create ADR-F (global agent commands supersede per-project copies; safe removal migration) (WP06)
- [ ] T041 Create ADR-G (preferred agent roles removed as unused concept) (WP06)

**Definition of done:** 7 new ADR files in `architecture/adrs/`; all follow the template structure from `architecture/adr-template.md`; no placeholder text remains.

---

### WP07 — Documentation Updates

**Lane:** C · **Priority:** Medium · **Est. prompt:** ~280 lines  
**Depends on:** WP06  
**Owned files:** `docs/how-to/non-interactive-init.md`, `docs/reference/cli-commands.md`, `docs/reference/configuration.md`, `docs/how-to/manage-agents.md`, `docs/2x/model-discipline-routing.md`

**Goal:** Remove all references to removed flags and the deleted preference system from user-facing documentation.

- [ ] T042 Update docs/how-to/non-interactive-init.md — remove preference flag examples (WP07)
- [ ] T043 Update docs/reference/cli-commands.md — remove 11 removed flags from init table (WP07)
- [ ] T044 Update docs/reference/configuration.md — remove selection block and all preference entries (WP07)
- [ ] T045 Update docs/how-to/manage-agents.md — remove preference field references (WP07)
- [ ] T046 Update docs/2x/model-discipline-routing.md — remove static preference config reference (WP07)
- [ ] T047 Verification grep: confirm zero preference references remain in docs/ (WP07)

**Definition of done:** `grep -r "preferred_implementer\|preferred_reviewer\|--preferred\|--script " docs/` → 0 results; all 5 files render valid markdown.

---

## Dependency Graph

```
WP01 ──► WP02 ──► WP03     (Lane A — sequential)
WP04 ──► WP05              (Lane B — sequential)
WP06 ──► WP07              (Lane C — sequential)
```

All three lanes run in parallel. Merge order: Lane C → Lane B → Lane A.

## WP Prompt Files

| WP | File | Subtasks | Est. Lines |
|----|------|----------|-----------|
| WP01 | tasks/WP01-agent-config-cleanup.md | 7 | ~320 |
| WP02 | tasks/WP02-init-surgery.md | 10 | ~620 |
| WP03 | tasks/WP03-template-and-tests.md | 5 | ~380 |
| WP04 | tasks/WP04-migration-strip-selection.md | 5 | ~260 |
| WP05 | tasks/WP05-migration-safe-globalize.md | 6 | ~380 |
| WP06 | tasks/WP06-author-adrs.md | 7 | ~420 |
| WP07 | tasks/WP07-doc-updates.md | 6 | ~280 |
