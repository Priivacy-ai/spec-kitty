# Feature Specification: Mission System Architectural Refinement

**Feature Branch**: `005-refactor-mission-system`
**Created**: 2025-01-16
**Status**: Draft
**Input**: Refactor mission system based on architectural analysis identifying 9 concerns with specific priorities for improvement.

## User Scenarios & Testing

### User Story 1 - Extract Pre-flight Location Checks to Shared Module (Priority: P1)

As a spec-kitty maintainer, I want the "Location Pre-flight Check" logic extracted to a single shared Python module so that changes to worktree validation logic only need to be made in one place instead of updating 4+ command prompt files per mission.

**Why this priority**: This is the highest-impact quick win. The DRY violation creates maintenance burden and risk of inconsistency. Every command (plan, implement, review, merge) duplicates 20+ lines of identical worktree validation logic. This blocks all other work because any changes to location validation would need to propagate through multiple files.

**Independent Test**: Can be fully tested by running `/spec-kitty.plan` from the wrong location (main branch) and verifying it fails with the shared error message. Delivers immediate value by reducing maintenance burden and improving code quality.

**Acceptance Scenarios**:

1. **Given** a developer runs `/spec-kitty.plan` from the main branch, **When** the shared pre-flight check executes, **Then** it fails with clear error message directing them to the worktree
2. **Given** the shared pre-flight module exists in `src/specify_cli/guards.py`, **When** any command imports and calls `validate_worktree_location()`, **Then** it performs the standardized check without duplicated code
3. **Given** command prompt files (plan.md, implement.md, review.md, merge.md), **When** examining their content, **Then** they reference the Python validation instead of including inline bash checks
4. **Given** a need to update location validation logic, **When** the maintainer updates `guards.py`, **Then** all commands automatically inherit the change

---

### User Story 2 - Add Pydantic Schema Validation for mission.yaml (Priority: P1)

As a spec-kitty user creating a custom mission, I want mission.yaml typos and structural errors to be caught with clear error messages when the mission loads, so I don't waste time debugging silent failures from malformed configuration.

**Why this priority**: Current implementation uses `.get()` with empty defaults, causing typos to fail silently. A user could create a mission with `validaton:` (typo) instead of `validation:` and receive no error - the validation checks would simply be ignored. This prevents custom mission adoption.

**Independent Test**: Can be fully tested by creating a mission.yaml with intentional errors (missing required fields, wrong types, typos) and verifying clear error messages are shown. Delivers value by making custom missions viable.

**Acceptance Scenarios**:

1. **Given** a mission.yaml with a typo in `validaton:`, **When** the mission loads, **Then** Pydantic raises a validation error listing the unknown field
2. **Given** a mission.yaml missing required field `name`, **When** the mission loads, **Then** Pydantic raises an error identifying the missing required field
3. **Given** a mission.yaml with `version: 1` (int instead of string), **When** the mission loads, **Then** Pydantic either coerces to "1" or raises a clear type error
4. **Given** a mission.yaml with invalid enum value for domain, **When** the mission loads, **Then** Pydantic lists valid domain options
5. **Given** a valid mission.yaml, **When** the mission loads, **Then** it loads successfully and the Mission object has typed attributes

---

### User Story 3 - Make Research Mission Production-Ready (Priority: P1)

As a researcher using spec-kitty, I want the research mission to have complete, validated templates and bibliography/citation management hooks so I can conduct systematic literature reviews with the same rigor as software development workflows.

**Why this priority**: Research mission currently has cosmetic changes only (renamed labels, unintegrated CSV templates). Making it production-ready validates that the mission system actually enables different domains. This is the core value proposition of missions.

**Independent Test**: Can be fully tested by initializing a project with `--mission research`, running through a complete research workflow (specify → plan → tasks → implement → review → accept → merge), and verifying research-specific artifacts are created and validated. Delivers value by enabling an entirely new user segment.

**Acceptance Scenarios**:

1. **Given** a research mission project, **When** running `/spec-kitty.specify`, **Then** the spec template prompts for research question, methodology, and expected outcomes (not user stories)
2. **Given** a research mission project, **When** running `/spec-kitty.plan`, **Then** the plan template includes sections for methodology, data sources, and analysis approach
3. **Given** a research mission with tasks in `for_review`, **When** running `/spec-kitty.review`, **Then** validation checks that all sources are documented and cited properly
4. **Given** a research project ready for acceptance, **When** running `/spec-kitty.accept`, **Then** validation ensures bibliography is complete, findings are synthesized, and no unresolved research questions remain
5. **Given** research-specific templates (evidence-log.csv, source-register.csv), **When** referenced in command prompts, **Then** agents know to populate and maintain these files during research tasks
6. **Given** a research mission plan.md, **When** examining validation rules in mission.yaml, **Then** it includes `all_sources_documented`, `methodology_clear`, `findings_synthesized` instead of software-dev checks

---

### User Story 4 - Implement Mission Switching CLI (Priority: P2)

As a spec-kitty user, I want to run `spec-kitty mission switch research` to alternate between research and software-dev missions within a single project, so I can conduct research that informs implementation without managing multiple separate projects.

**Why this priority**: Enables the core use case of alternating between research and development work. Example workflow: research security review → implement fixes → research performance → optimize. This makes missions genuinely useful rather than just a configuration option at init time.

**Independent Test**: Can be tested by initializing a software-dev project, completing and merging a feature, running `spec-kitty mission switch research`, verifying the switch succeeds, creating a research feature, merging it, and switching back. Delivers value by enabling mission alternation.

**Acceptance Scenarios**:

1. **Given** a clean project (no active worktrees), **When** running `spec-kitty mission list`, **Then** it displays all available missions with descriptions
2. **Given** a software-dev project, **When** running `spec-kitty mission current`, **Then** it displays "Software Dev Kitty" and mission details
3. **Given** a clean project on main branch, **When** running `spec-kitty mission switch research`, **Then** it updates `.kittify/active-mission` symlink and confirms the switch
4. **Given** a project with active worktrees, **When** running `spec-kitty mission switch research`, **Then** it fails with error "Cannot switch missions: active features exist. Merge or abandon worktrees first."
5. **Given** a mission name, **When** running `spec-kitty mission info research`, **Then** it displays mission details (domain, workflow phases, required artifacts, validation checks)
6. **Given** a successful mission switch, **When** running subsequent `/spec-kitty.specify`, **Then** it uses the new mission's templates and prompts

---

### User Story 5 - Enforce Mission Path Conventions (Priority: P2)

As a spec-kitty user, I want path convention validation to ensure my project structure matches the active mission's expectations, so I receive clear feedback if required directories are missing or misnamed.

**Why this priority**: Path conventions are currently documentation-only in mission.yaml. Users can define `workspace: "src/"` but nothing enforces that `src/` actually exists. This creates confusion when commands reference paths that don't exist.

**Independent Test**: Can be tested by creating a software-dev project without creating `src/` or `tests/` directories, running validation, and verifying clear error messages. Delivers value by catching structural issues early.

**Acceptance Scenarios**:

1. **Given** a software-dev mission declaring `workspace: "src/"`, **When** running validation and `src/` doesn't exist, **Then** validation warns "Mission expects workspace directory: src/ (not found)"
2. **Given** a research mission declaring `data: "data/"`, **When** running validation and `data/` doesn't exist, **Then** validation warns "Mission expects data directory: data/ (not found)"
3. **Given** a project with all mission-required directories, **When** running validation, **Then** path convention checks pass
4. **Given** path validation errors, **When** displayed to user, **Then** they include suggestions: "Create directory: mkdir src/"
5. **Given** acceptance workflow, **When** running `/spec-kitty.accept`, **Then** path validation is included in the 7-point readiness check

---

### User Story 6 - Clarify Terminology in Documentation (Priority: P3)

As a spec-kitty user, I want clear, consistent terminology throughout documentation distinguishing between Project (codebase), Feature (unit of work), and Mission (domain mode), so I understand how to organize and discuss my work.

**Why this priority**: Terminology confusion creates communication barriers. The analysis revealed confusion around "project" vs "feature" vs "mission". Clear definitions improve onboarding and reduce support burden.

**Independent Test**: Can be tested by reading updated documentation and finding consistent usage of terms. No code changes required. Delivers value through improved clarity.

**Acceptance Scenarios**:

1. **Given** the README.md, **When** searching for term usage, **Then** "Project" consistently means the entire codebase (e.g., "priivacy_rust project")
2. **Given** the documentation, **When** describing units of work, **Then** "Feature" consistently means a single unit of work (e.g., "001-mission-system-architecture")
3. **Given** command documentation, **When** discussing domain modes, **Then** "Mission" consistently means the domain adapter (software-dev, research)
4. **Given** error messages and CLI output, **When** referencing these concepts, **Then** terminology matches documentation
5. **Given** a glossary section in docs, **When** users need definitions, **Then** clear definitions exist with examples

---

### User Story 7 - Display Active Mission in Dashboard (Priority: P3)

As a spec-kitty user viewing the dashboard, I want to see the currently active mission displayed prominently, so I know which domain mode my current work is using without running CLI commands.

**Why this priority**: Visual confirmation of active mission prevents confusion when switching between research and development work. Nice-to-have enhancement that improves user experience without changing core functionality.

**Independent Test**: Can be tested by switching missions and verifying the dashboard updates. Minimal backend changes. Delivers value through improved situational awareness.

**Acceptance Scenarios**:

1. **Given** a software-dev project, **When** viewing the dashboard, **Then** "Current Mission: Software Dev Kitty" is displayed in the header or sidebar
2. **Given** switching to research mission, **When** refreshing the dashboard, **Then** the displayed mission updates to "Current Mission: Deep Research Kitty"
3. **Given** the dashboard mission display, **When** designing the UI, **Then** it's prominent but not obtrusive (doesn't dominate the interface)
4. **Given** dashboard adaptation opportunities, **When** evaluating UI changes by mission, **Then** only clearly beneficial adaptations are implemented (resist complication)

---

### Edge Cases

- What happens when a user tries to switch missions while Git is dirty (uncommitted changes)?
  - Block the switch with error: "Uncommitted changes detected. Commit or stash changes before switching missions."

- What happens when a mission.yaml references a template file that doesn't exist?
  - Pydantic validation can't catch this (file paths). Mission loading should validate template existence and fail fast with helpful error.

- What happens when validation rules in mission.yaml reference non-existent validators?
  - Current behavior: silently ignored. New behavior: warning logged during mission load.

- What happens when a user creates a mission with invalid workflow phase names?
  - Pydantic should validate that phases is a list of dicts with 'name' and 'description' keys.

- What happens when switching missions and new mission requires artifacts the old mission didn't?
  - Show warning listing missing artifacts: "Warning: Research mission requires findings.md (not found). Create before running acceptance."

- What happens if .kittify/active-mission symlink is broken or points to non-existent mission?
  - Fall back to software-dev with warning: "Active mission link broken, defaulting to software-dev."

## Requirements

### Functional Requirements

**Code Quality & DRY:**

- **FR-001**: System MUST extract worktree location validation to `src/specify_cli/guards.py` with function `validate_worktree_location()`
- **FR-002**: Command prompts (plan.md, implement.md, review.md, merge.md) MUST call Python validation instead of duplicating inline bash checks
- **FR-003**: Shared validation module MUST check: current branch is feature branch (not main), worktree path matches expected pattern

**Schema Validation:**

- **FR-004**: System MUST define Pydantic models for mission.yaml structure with all required and optional fields
- **FR-005**: Mission loading MUST validate configuration against Pydantic schema and raise clear errors for violations
- **FR-006**: Pydantic model MUST enforce: name (str, required), domain (str, required), version (str, required), workflow.phases (list, required), artifacts.required (list, required)
- **FR-007**: Pydantic model MUST provide helpful error messages listing valid options for enum fields

**Research Mission:**

- **FR-008**: Research mission templates MUST include research-specific sections: research question, methodology, data sources, findings synthesis
- **FR-009**: Research mission validation rules MUST check: all_sources_documented, methodology_clear, findings_synthesized, no_unresolved_questions
- **FR-010**: Research mission command prompts MUST guide agents to populate evidence-log.csv and source-register.csv
- **FR-011**: Research mission MUST include bibliography/citation management hooks in implement and review workflows
- **FR-012**: Research mission templates MUST be complete and self-consistent (no references to non-existent files)

**Mission Switching:**

- **FR-013**: System MUST provide `spec-kitty mission` command group with subcommands: list, current, switch, info
- **FR-014**: `spec-kitty mission list` MUST display all available missions with name, description, and domain
- **FR-015**: `spec-kitty mission current` MUST show active mission details: name, domain, workflow phases, validation checks
- **FR-016**: `spec-kitty mission switch <name>` MUST update `.kittify/active-mission` symlink to point to new mission
- **FR-017**: Mission switching MUST validate: no active worktrees exist, no uncommitted git changes, target mission exists
- **FR-018**: Mission switching MUST show warning if new mission requires artifacts that don't exist
- **FR-019**: `spec-kitty mission info <name>` MUST display mission configuration details without switching

**Path Convention Enforcement:**

- **FR-020**: System MUST validate that mission-declared path conventions match actual project structure
- **FR-021**: Path validation MUST check existence of directories specified in mission.yaml `paths` section
- **FR-022**: Path validation warnings MUST include helpful suggestions: "Create directory: mkdir src/"
- **FR-023**: Acceptance workflow (`/spec-kitty.accept`) MUST include path convention validation in readiness checks

**Documentation:**

- **FR-024**: Documentation MUST define: Project = entire codebase, Feature = unit of work, Mission = domain mode
- **FR-025**: Terminology MUST be used consistently across README, command help text, error messages, and dashboard
- **FR-026**: Glossary section MUST be added to documentation with examples of each term

**Dashboard Integration:**

- **FR-027**: Dashboard MUST display currently active mission name prominently (header or sidebar)
- **FR-028**: Dashboard mission display MUST update when mission is switched (may require refresh)
- **FR-029**: Dashboard MUST avoid mission-specific UI complexity unless clearly beneficial

### Key Entities

- **Mission**: Represents a domain adapter bundle (software-dev, research) with templates, validation rules, workflow phases, and path conventions. Attributes: name, domain, version, workflow phases, required artifacts, validation checks.

- **MissionConfig (Pydantic Model)**: Typed representation of mission.yaml structure for validation. Attributes: name (str), domain (enum), version (str), workflow (WorkflowConfig), artifacts (ArtifactsConfig), paths (dict), validation (ValidationConfig).

- **WorktreeLocation**: Represents the validated location for command execution. Attributes: current_branch, is_feature_branch, worktree_path, expected_pattern.

## Success Criteria

### Measurable Outcomes

**Code Quality:**

- **SC-001**: Pre-flight check logic exists in single location (`src/specify_cli/guards.py`) eliminating 60+ lines of duplication across 4 command files per mission
- **SC-002**: Changes to worktree validation require updates to exactly 1 file instead of 8+ files

**Schema Validation:**

- **SC-003**: Mission.yaml typos are caught immediately on mission load with error messages that list the issue and valid options
- **SC-004**: 100% of mission.yaml required fields are validated (name, domain, version, workflow, artifacts)
- **SC-005**: Custom mission creators receive clear feedback within 5 seconds of loading invalid configuration

**Research Mission:**

- **SC-006**: Users can complete full research workflow (specify → plan → tasks → implement → review → accept → merge) without encountering missing templates or broken references
- **SC-007**: Research mission validation actually validates research-specific requirements (sources documented, methodology clear, findings synthesized)
- **SC-008**: Research mission templates guide agents to use evidence-log.csv and source-register.csv appropriately

**Mission Switching:**

- **SC-009**: Users can switch between software-dev and research missions within a single project in under 10 seconds
- **SC-010**: Mission switch prevents errors by blocking when worktrees exist or git is dirty
- **SC-011**: Users receive clear warnings about missing artifacts when switching to mission with different requirements

**Path Enforcement:**

- **SC-012**: Path convention violations are detected and reported with helpful error messages during validation
- **SC-013**: Acceptance workflow includes path validation in the 7-point readiness check

**Documentation:**

- **SC-014**: Terminology (Project/Feature/Mission) is used consistently in 100% of user-facing documentation and error messages
- **SC-015**: New users can find clear definitions of core terms within 1 minute of reading docs

**Dashboard:**

- **SC-016**: Active mission is visible in dashboard without requiring CLI commands or file inspection
- **SC-017**: Mission display updates within 5 seconds of switching missions (with page refresh if needed)

## Assumptions

1. **Pydantic is acceptable dependency**: Assuming Pydantic (already used in Python ecosystem) is acceptable for schema validation. If not, could use jsonschema or dataclasses with manual validation.

2. **Mission switching is infrequent**: Assuming users don't switch missions multiple times per day. If frequent switching is expected, may need caching or performance optimization.

3. **Dashboard refresh acceptable**: Assuming page refresh after mission switch is acceptable UX. If not, would need WebSocket or polling for live updates.

4. **Research mission users exist**: Assuming there's demand for research mission. If not validated through user research, could defer research mission improvements.

5. **Path conventions are standardized**: Assuming missions use standard paths (src/, tests/, data/). If missions need arbitrary path structures, validation becomes more complex.

6. **Breaking changes acceptable for custom missions**: Schema validation may break existing custom missions with malformed YAML. Acceptable since we're fixing silent failures.

7. **Windows symlink fallback works**: Current file-based fallback for Windows (when symlinks unavailable) works correctly. If not, mission switching needs additional testing on Windows.

8. **CLI-first workflow**: Assuming users primarily use CLI commands. If GUI/dashboard is primary interface, may need dashboard-based mission switching.
