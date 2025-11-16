# Work Packages: Mission System Architectural Refinement

**Inputs**: Design documents from `/kitty-specs/005-refactor-mission-system/`
**Prerequisites**: plan.md (architectural decisions), spec.md (7 user stories), research.md (Pydantic selection), data-model.md (schema models), quickstart.md (usage guide)

**Tests**: Test-first development for critical validation logic (guards, schema, validators).

**Organization**: 37 fine-grained subtasks rolled into 8 work packages organized by user story priority.

---

## Work Package WP01: Guards Module - Pre-flight Validation (Priority: P1) 🎯 MVP

**Goal**: Extract duplicated worktree location checks to shared `src/specify_cli/guards.py` module, eliminating 60+ lines of duplication across 8 command prompt files.
**Independent Test**: Run `/spec-kitty.plan` from main branch and verify it fails with standardized error from guards module.
**Prompt**: `/tasks/planned/phase-1-foundation/WP01-guards-module-preflight-validation.md`

### Included Subtasks
- [X] T001 Create `src/specify_cli/guards.py` module with docstring and imports
- [X] T002 Define `WorktreeValidationResult` dataclass in guards.py
- [X] T003 [P] Write unit tests in `tests/unit/test_guards.py` (TDD - write first)
- [X] T004 Implement `validate_worktree_location()` function with branch detection
- [X] T005 Implement helpful error formatting in `WorktreeValidationResult.format_error()`
- [X] T006 Add `validate_git_clean()` function for mission switching pre-checks
- [X] T007 Run unit tests and verify 100% coverage for guards module

### Implementation Notes
1. Start with TDD: write test_guards.py first with expected behavior
2. Implement validation logic: check current branch, detect main vs feature, provide worktree suggestions
3. Error messages must be actionable: show exact commands to fix
4. This work package BLOCKS WP05 (command prompt updates) - prioritize completion

### Parallel Opportunities
- T003 (writing tests) can happen in parallel with T001-T002 (module structure)

### Dependencies
- None (foundational work package)

### Risks & Mitigations
- Risk: Breaks existing command execution if validation too strict
- Mitigation: Match existing bash check behavior exactly, extensive testing from both valid and invalid locations

---

## Work Package WP02: Pydantic Mission Schema (Priority: P1) 🎯 MVP

**Goal**: Add Pydantic v2 models to `src/specify_cli/mission.py` for mission.yaml validation, catching typos and structural errors with clear error messages.
**Independent Test**: Create mission.yaml with intentional typo (`validaton:`), verify Pydantic raises clear validation error.
**Prompt**: `/tasks/planned/phase-1-foundation/WP02-pydantic-mission-schema.md`

### Included Subtasks
- [X] T008 Add `pydantic>=2.0` to pyproject.toml or requirements.txt
- [X] T009 Create Pydantic models in mission.py: PhaseConfig, ArtifactsConfig, ValidationConfig
- [X] T010 Create Pydantic models: WorkflowConfig, MCPToolsConfig, CommandConfig, TaskMetadataConfig
- [X] T011 Create root MissionConfig model with all required/optional fields
- [X] T012 [P] Write unit tests in `tests/unit/test_mission_schema.py` covering valid configs
- [X] T013 [P] Write unit tests for invalid configs (typos, missing fields, wrong types)
- [X] T014 Update Mission.__init__ to use Pydantic validation instead of raw YAML
- [X] T015 Add error formatting for ValidationError with helpful messages
- [X] T016 Test with existing software-dev and research mission.yaml files

### Implementation Notes
1. Install Pydantic first
2. Define models incrementally (start with simple PhaseConfig, build up to MissionConfig)
3. Use `extra="forbid"` to catch typos in field names
4. Test extensively with both valid and invalid YAML
5. Maintain backwards compatibility - valid missions should still load

### Parallel Opportunities
- T012 (valid config tests) and T013 (invalid config tests) can be written in parallel
- T009-T011 (model definitions) can be drafted in parallel then integrated

### Dependencies
- None (can start immediately)

### Risks & Mitigations
- Risk: Breaking changes to existing custom missions
- Mitigation: Test with both built-in missions, document migration guide for custom missions
- Risk: Pydantic dependency rejected
- Mitigation: Research.md documents dataclasses fallback option

---

## Work Package WP03: Mission CLI Commands (Priority: P2)

**Goal**: Implement `spec-kitty mission` command group with subcommands: list, current, switch, info.
**Independent Test**: Run `spec-kitty mission list` and verify it displays software-dev and research missions.
**Prompt**: `/tasks/planned/phase-2-mission-cli/WP03-mission-cli-commands.md`

### Included Subtasks
- [X] T017 Create `src/specify_cli/cli/commands/mission.py` with Typer app
- [X] T018 Implement `list_cmd()` - display all available missions
- [X] T019 Implement `current_cmd()` - show active mission details
- [X] T020 Implement `info_cmd(mission_name)` - show specific mission info
- [X] T021 Implement `switch_cmd(mission_name)` with validation hooks
- [X] T022 Register mission command group in main CLI entry point
- [X] T023 [P] Write integration tests in `tests/integration/test_mission_cli.py`
- [X] T024 Test all CLI commands with rich output formatting

### Implementation Notes
1. Reuse existing `mission.py` functions (get_active_mission, set_active_mission, list_available_missions)
2. Add new validation logic for switch command (check worktrees, git status)
3. Use Rich console for formatted output
4. Follow existing CLI patterns from init command

### Parallel Opportunities
- T018-T020 (list/current/info commands) can be implemented in parallel
- T023 (integration tests) can be written in parallel with T017-T022

### Dependencies
- Depends on WP02 (Pydantic schema validation)
- Depends on WP01 (guards module for git-clean validation)

### Risks & Mitigations
- Risk: Switch validation too strict or too loose
- Mitigation: Follow spec requirements exactly (block on worktrees, git dirty, missing mission)

---

## Work Package WP04: Research Mission Templates (Priority: P1)

**Goal**: Update research mission templates to be production-ready with complete sections, research-specific prompts, and integrated CSV tracking.
**Independent Test**: Initialize `--mission research` project, run full workflow (specify → accept), verify all templates work without errors.
**Prompt**: `/tasks/planned/phase-3-research-mission/WP04-research-mission-templates.md`

### Included Subtasks
- [X] T025 [P] Update `.kittify/missions/research/templates/spec-template.md` with research question format
- [X] T026 [P] Update `.kittify/missions/research/templates/plan-template.md` with methodology sections
- [X] T027 [P] Update `.kittify/missions/research/templates/tasks-template.md` for research work packages
- [X] T028 [P] Verify evidence-log.csv template has correct columns and examples
- [X] T029 [P] Verify source-register.csv template has correct columns and examples
- [X] T030 Update research mission.yaml with complete validation rules and artifact list

### Implementation Notes
1. Templates must guide researchers clearly (research question, hypothesis, methodology, findings)
2. Remove any software-dev terminology (no "user stories", "TDD", "contracts")
3. Add inline guidance for populating CSV files
4. Ensure consistency across all research templates

### Parallel Opportunities
- All template updates (T025-T029) can proceed in parallel
- Different agents can own different templates

### Dependencies
- None (can start immediately)

### Risks & Mitigations
- Risk: Templates don't match actual research workflows
- Mitigation: Reference academic research methodology standards

---

## Work Package WP05: Research Citation Validators (Priority: P1)

**Goal**: Create citation validation module enforcing bibliography completeness and format quality in research mission.
**Independent Test**: Create evidence-log.csv with valid/invalid citations, run validation, verify clear errors for problems.
**Prompt**: `/tasks/planned/phase-3-research-mission/WP05-research-citation-validators.md`

### Included Subtasks
- [X] T031 Create `src/specify_cli/validators/` directory
- [X] T032 Create `src/specify_cli/validators/research.py` module
- [X] T033 Define CitationValidationResult and CitationIssue dataclasses
- [X] T034 [P] Implement BibTeX citation pattern regex
- [X] T035 [P] Implement APA citation pattern regex
- [X] T036 [P] Implement Simple citation pattern regex
- [X] T037 Implement `validate_citations()` function for evidence-log.csv
- [X] T038 Implement `validate_source_register()` for source-register.csv
- [X] T039 [P] Write unit tests in `tests/unit/test_validators.py` with sample citations
- [X] T040 Integrate citation validation into research mission review workflow

### Implementation Notes
1. Progressive validation: errors for completeness, warnings for format
2. Support multiple formats (BibTeX, APA, Simple) - don't enforce single style
3. Use Python stdlib only (csv + re)
4. Clear error messages: line number, field name, specific issue, suggestion

### Parallel Opportunities
- T034-T036 (pattern development) can proceed in parallel
- T037-T038 (validation functions) can be implemented independently

### Dependencies
- None (can start immediately)

### Risks & Mitigations
- Risk: Regex patterns too strict, reject valid citations
- Mitigation: Test with real-world citation examples, make warnings not errors

---

## Work Package WP06: Update Command Prompts (Priority: P1)

**Goal**: Remove duplicated pre-flight checks from 8 command prompt files, replace with Python validation calls.
**Independent Test**: Run commands from wrong location, verify they fail with guards.py error.
**Prompt**: `/tasks/planned/phase-4-integration/WP06-update-command-prompts.md`

### Included Subtasks
- [X] T041 Update `.kittify/missions/software-dev/commands/plan.md` - replace inline checks with Python call
- [X] T042 Update `.kittify/missions/software-dev/commands/implement.md` - replace inline checks
- [X] T043 Update `.kittify/missions/software-dev/commands/review.md` - replace inline checks
- [X] T044 Update `.kittify/missions/software-dev/commands/merge.md` - replace inline checks
- [X] T045 Update `.kittify/missions/research/commands/plan.md` - replace inline checks
- [X] T046 Update `.kittify/missions/research/commands/implement.md` - add citation tracking guidance
- [X] T047 Update `.kittify/missions/research/commands/review.md` - add citation validation calls
- [X] T048 Update `.kittify/missions/research/commands/merge.md` - replace inline checks

### Implementation Notes
1. **CRITICAL**: This work package MUST wait for WP01 (guards.py) to complete
2. Find "Location Pre-flight Check" sections in each command prompt
3. Replace with: "Run pre-flight validation: `python -m specify_cli.guards validate_worktree`"
4. For research commands, add citation tracking guidance in appropriate sections
5. Test each command from correct and incorrect locations

### Parallel Opportunities
- Software-dev commands (T041-T044) and research commands (T045-T048) can be updated in parallel
- Each command can be updated independently

### Dependencies
- **BLOCKS**: Depends on WP01 (guards.py must exist)

### Risks & Mitigations
- Risk: Commands fail if guards.py has bugs
- Mitigation: Extensive testing of guards.py before updating prompts

---

## Work Package WP07: Path Convention Validation (Priority: P2)

**Goal**: Implement path convention validation with progressive enforcement (warnings at switch, errors at acceptance).
**Independent Test**: Create project without `src/` directory, run validation, verify clear warning with suggestion.
**Prompt**: `/tasks/planned/phase-4-integration/WP07-path-convention-validation.md`

### Included Subtasks
- [X] T049 Create `src/specify_cli/validators/paths.py` module
- [X] T050 Define PathValidationResult dataclass
- [X] T051 Implement `validate_mission_paths()` with strict/non-strict modes
- [X] T052 Implement `suggest_directory_creation()` helper function
- [X] T053 [P] Write unit tests in `tests/unit/test_validators.py` for path validation
- [X] T054 Integrate path validation into mission switch command (warnings only)
- [X] T055 Integrate path validation into acceptance workflow (errors block)
- [X] T056 Update acceptance.py to include path validation in 7-point readiness check

### Implementation Notes
1. Read mission.paths from MissionConfig
2. Check each path exists relative to project root
3. strict=False: return warnings, strict=True: raise errors
4. Generate helpful suggestions: "Create directory: mkdir -p src/"

### Parallel Opportunities
- T049-T052 (implementation) and T053 (tests) can proceed in parallel
- T054-T055 (integration points) can be done independently

### Dependencies
- Depends on WP02 (Pydantic schema for accessing mission.paths)
- Depends on WP03 (mission switch command to integrate warnings)

### Risks & Mitigations
- Risk: False positives (path exists but with different case on case-insensitive filesystem)
- Mitigation: Use Path.resolve() for canonical path comparison

---

## Work Package WP08: Documentation & Terminology (Priority: P3)

**Goal**: Clarify Project/Feature/Mission terminology across all documentation, add glossary, ensure consistent usage.
**Independent Test**: Search README for term usage, verify consistent definitions.
**Prompt**: `/tasks/planned/phase-5-polish/WP08-documentation-terminology.md`

### Included Subtasks
- [X] T057 [P] Add glossary section to README.md with Project/Feature/Mission definitions
- [X] T058 [P] Review and update README.md for consistent terminology
- [X] T059 [P] Update CLI help text for consistent terminology
- [X] T060 [P] Update error messages for consistent terminology
- [X] T061 [P] Update command prompt files for consistent terminology

### Implementation Notes
1. Define clear, concise definitions with examples
2. Search/replace inconsistent usage
3. Terminology:
   - **Project**: Entire codebase (e.g., "spec-kitty project", "priivacy_rust project")
   - **Feature**: Unit of work (e.g., "001-mission-system-architecture feature")
   - **Mission**: Domain adapter (e.g., "software-dev mission", "research mission")

### Parallel Opportunities
- All subtasks can proceed in parallel (different files)
- Multiple agents can own different documentation sections

### Dependencies
- None (can start immediately)

### Risks & Mitigations
- Risk: Inconsistencies slip through
- Mitigation: Automated terminology checking (grep for patterns)

---

## Work Package WP09: Dashboard Mission Display (Priority: P3)

**Goal**: Add active mission display to dashboard header with manual refresh button.
**Independent Test**: View dashboard, verify mission shown, switch missions, refresh, verify update.
**Prompt**: `/tasks/planned/phase-5-polish/WP09-dashboard-mission-display.md`

### Included Subtasks
- [X] T062 Update `src/specify_cli/dashboard/server.py` to include mission in context
- [X] T063 [P] Update dashboard HTML template to display mission name
- [X] T064 [P] Add refresh button to dashboard header (optional enhancement)
- [X] T065 Style mission display to be prominent but not obtrusive
- [X] T066 Test dashboard with software-dev mission
- [X] T067 Switch to research mission, refresh dashboard, verify update

### Implementation Notes
1. Add mission to template context in index route
2. Display format: "Current Mission: Software Dev Kitty" in header
3. Refresh button is optional enhancement (nice-to-have)
4. Avoid mission-specific UI changes (keep dashboard generic)

### Parallel Opportunities
- T063-T064 (frontend changes) can proceed in parallel
- T062 (backend) must complete first

### Dependencies
- Depends on WP03 (mission switch command to test updates)

### Risks & Mitigations
- Risk: Dashboard becomes cluttered
- Mitigation: Minimal, clean design - resist complication per user guidance

---

## Work Package WP10: Integration Testing (Priority: P1)

**Goal**: Create integration tests validating end-to-end mission switching and research workflows.
**Independent Test**: Run integration test suite, verify all scenarios pass.
**Prompt**: `/tasks/planned/phase-6-testing/WP10-integration-testing.md`

### Included Subtasks
- [X] T068 Create `tests/integration/test_mission_switching.py`
- [X] T069 Test: Clean project → mission switch → verify success
- [X] T070 Test: Active worktrees → mission switch → verify blocked
- [X] T071 Test: Dirty git → mission switch → verify blocked
- [X] T072 Test: Switch to research → create feature → verify research templates used
- [X] T073 Create `tests/integration/test_research_workflow.py`
- [X] T074 Test: Full research workflow (init → specify → plan → tasks → implement → review → accept)
- [X] T075 Test: Citation validation in research workflow
- [X] T076 Test: Path validation warnings at switch, errors at acceptance

### Implementation Notes
1. Use pytest fixtures for project setup/teardown
2. Create temporary test projects for isolation
3. Test both happy paths and error scenarios
4. Verify error messages are actionable

### Parallel Opportunities
- T068-T072 (switching tests) and T073-T076 (research tests) can be developed in parallel

### Dependencies
- Depends on WP01, WP02, WP03, WP04, WP05, WP06, WP07 (integration tests run after all modules complete)

### Risks & Mitigations
- Risk: Integration tests brittle, break with unrelated changes
- Mitigation: Focus on contract validation, not implementation details

---

## Dependency & Execution Summary

**Critical Path**:
```
WP01 (Guards) → WP06 (Command Prompts) → WP10 (Integration Tests)
  └─ 1 day   →    1 day                →    1 day
```

**Parallel Execution Strategy**:
```
Phase 1 - Foundation (Days 1-2, Sequential):
  WP01: Guards Module [BLOCKS WP06]

Phase 2 - Parallel Streams (Days 2-5, Concurrent):
  Stream A: WP02 (Pydantic Schema) → WP03 (Mission CLI)
  Stream B: WP04 (Research Templates) → WP05 (Citation Validators)
  Stream C: [WAITING for WP01] → WP06 (Command Prompts)
  Stream D: WP08 (Documentation) + WP09 (Dashboard)

Phase 3 - Integration (Days 6-7):
  WP10: Integration Testing [requires all WPs complete]
```

**Parallelization Opportunities**:
- After WP01 completes: WP02, WP04, WP08, WP09 can run in parallel
- WP03, WP05 can start after their dependencies (WP02, WP04) complete
- WP06 waits for WP01 but can overlap with other streams

**MVP Scope** (minimum viable refactoring):
- WP01: Guards Module (eliminates duplication)
- WP02: Pydantic Schema (fixes silent failures)
- WP06: Command Prompts (applies DRY fix)

**Full Scope** (all improvements):
- MVP + WP03 (Mission CLI) + WP04 (Research Templates) + WP05 (Citation Validators) + WP07 (Path Validation) + WP08 (Docs) + WP09 (Dashboard) + WP10 (Integration Tests)

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| **Foundation** |
| T001 | Create guards.py module structure | WP01 | P1 | No |
| T002 | Define WorktreeValidationResult dataclass | WP01 | P1 | No |
| T003 | Write unit tests for guards | WP01 | P1 | Yes |
| T004 | Implement validate_worktree_location() | WP01 | P1 | No |
| T005 | Implement error formatting | WP01 | P1 | No |
| T006 | Implement validate_git_clean() | WP01 | P1 | No |
| T007 | Run unit tests, verify coverage | WP01 | P1 | No |
| **Schema Validation** |
| T008 | Add pydantic dependency | WP02 | P1 | No |
| T009 | Create Phase/Artifacts/Validation models | WP02 | P1 | Yes |
| T010 | Create Workflow/MCP/Command models | WP02 | P1 | Yes |
| T011 | Create root MissionConfig model | WP02 | P1 | No |
| T012 | Write tests for valid configs | WP02 | P1 | Yes |
| T013 | Write tests for invalid configs | WP02 | P1 | Yes |
| T014 | Update Mission.__init__ with validation | WP02 | P1 | No |
| T015 | Add error formatting | WP02 | P1 | No |
| T016 | Test with existing missions | WP02 | P1 | No |
| **Mission CLI** |
| T017 | Create mission.py CLI module | WP03 | P2 | No |
| T018 | Implement list_cmd | WP03 | P2 | Yes |
| T019 | Implement current_cmd | WP03 | P2 | Yes |
| T020 | Implement info_cmd | WP03 | P2 | Yes |
| T021 | Implement switch_cmd with validation | WP03 | P2 | No |
| T022 | Register command group | WP03 | P2 | No |
| T023 | Write integration tests | WP03 | P2 | Yes |
| T024 | Test CLI output formatting | WP03 | P2 | No |
| **Research Templates** |
| T025 | Update spec-template.md | WP04 | P1 | Yes |
| T026 | Update plan-template.md | WP04 | P1 | Yes |
| T027 | Update tasks-template.md | WP04 | P1 | Yes |
| T028 | Verify evidence-log.csv template | WP04 | P1 | Yes |
| T029 | Verify source-register.csv template | WP04 | P1 | Yes |
| T030 | Update research mission.yaml | WP04 | P1 | No |
| **Citation Validators** |
| T031 | Create validators directory | WP05 | P1 | No |
| T032 | Create research.py module | WP05 | P1 | No |
| T033 | Define validation result models | WP05 | P1 | No |
| T034 | Implement BibTeX pattern | WP05 | P1 | Yes |
| T035 | Implement APA pattern | WP05 | P1 | Yes |
| T036 | Implement Simple pattern | WP05 | P1 | Yes |
| T037 | Implement validate_citations() | WP05 | P1 | No |
| T038 | Implement validate_source_register() | WP05 | P1 | No |
| T039 | Write validator unit tests | WP05 | P1 | Yes |
| T040 | Integrate into review workflow | WP05 | P1 | No |
| **Command Prompts** |
| T041 | Update software-dev plan.md | WP06 | P1 | Yes |
| T042 | Update software-dev implement.md | WP06 | P1 | Yes |
| T043 | Update software-dev review.md | WP06 | P1 | Yes |
| T044 | Update software-dev merge.md | WP06 | P1 | Yes |
| T045 | Update research plan.md | WP06 | P1 | Yes |
| T046 | Update research implement.md | WP06 | P1 | Yes |
| T047 | Update research review.md | WP06 | P1 | Yes |
| T048 | Update research merge.md | WP06 | P1 | Yes |
| **Path Validation** |
| T049 | Create paths.py module | WP07 | P2 | No |
| T050 | Define PathValidationResult | WP07 | P2 | No |
| T051 | Implement validate_mission_paths() | WP07 | P2 | No |
| T052 | Implement suggest_directory_creation() | WP07 | P2 | No |
| T053 | Write unit tests | WP07 | P2 | Yes |
| T054 | Integrate into mission switch (warnings) | WP07 | P2 | No |
| T055 | Integrate into acceptance (errors) | WP07 | P2 | No |
| T056 | Update acceptance.py readiness check | WP07 | P2 | No |
| **Documentation** |
| T057 | Add glossary to README.md | WP08 | P3 | Yes |
| T058 | Update README terminology | WP08 | P3 | Yes |
| T059 | Update CLI help text | WP08 | P3 | Yes |
| T060 | Update error messages | WP08 | P3 | Yes |
| T061 | Update command prompts terminology | WP08 | P3 | Yes |
| **Dashboard** |
| T062 | Update server.py with mission context | WP09 | P3 | No |
| T063 | Update dashboard template | WP09 | P3 | Yes |
| T064 | Add refresh button | WP09 | P3 | Yes |
| T065 | Style mission display | WP09 | P3 | No |
| T066 | Test with software-dev | WP09 | P3 | No |
| T067 | Test with research mission | WP09 | P3 | No |
| **Integration Tests** |
| T068 | Create test_mission_switching.py | WP10 | P1 | No |
| T069 | Test clean switch happy path | WP10 | P1 | Yes |
| T070 | Test worktrees block switch | WP10 | P1 | Yes |
| T071 | Test dirty git blocks switch | WP10 | P1 | Yes |
| T072 | Test research template usage | WP10 | P1 | Yes |
| T073 | Create test_research_workflow.py | WP10 | P1 | No |
| T074 | Test full research workflow | WP10 | P1 | No |
| T075 | Test citation validation | WP10 | P1 | Yes |
| T076 | Test path validation | WP10 | P1 | Yes |

---

**Total**: 76 subtasks across 10 work packages
**Parallel-Safe**: 45 subtasks marked [P] (59%)
**Critical Path**: WP01 → WP06 → WP10 (3-4 days)
**With Parallelization**: 6-8 days total
