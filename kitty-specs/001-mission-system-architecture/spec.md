# Feature Specification: Mission System Architecture

**Feature Branch**: `001-mission-system-architecture`
**Created**: 2025-10-29
**Status**: Draft
**Input**: Enable Spec Kitty to support multiple domains (software development, research, writing, SEO audits, etc.) through a modular mission system while maintaining its core workflow excellence.

## User Scenarios & Testing

### User Story 1 - Initialize Project with Mission Selection (Priority: P1)

A user wants to start a new research project using Spec Kitty's structured workflow, but the current system only supports software development. They need to select "Deep Research Kitty" as their mission type during initialization.

**Why this priority**: This is the entry point for all non-software use cases. Without this, users cannot access alternative missions at all. It's the foundation for everything else.

**Independent Test**: Can be fully tested by running `spec-kitty init research-project --mission research` and verifying that research-specific templates, constitution, and workflow are installed instead of software-dev defaults. Delivers immediate value by making research projects possible.

**Acceptance Scenarios**:

1. **Given** a user wants to start a new research project, **When** they run `spec-kitty init my-research --mission research`, **Then** the project is initialized with research-specific templates (research-question.md, methodology.md, etc.) instead of software templates (data-model.md, contracts/, etc.)

2. **Given** a user runs `spec-kitty init` without specifying a mission, **When** the CLI prompts for mission selection, **Then** they see options: "Software Dev Kitty", "Deep Research Kitty", "Writing Kitty", "SEO Audit Kitty" and can choose one

3. **Given** a user initializes a project with `--mission research`, **When** they view `.kittify/active-mission`, **Then** it points to `missions/research/`

4. **Given** a user with an existing software-dev project, **When** they run `spec-kitty mission switch research`, **Then** the system warns about incompatibility and requires confirmation before switching

---

### User Story 2 - Software Dev Mission Extraction (Priority: P1)

As a current Spec Kitty user doing software development, I want the existing functionality to continue working exactly as it does today, even after the mission system is introduced. The software-dev mission should be the default and require zero changes to my workflow.

**Why this priority**: Backwards compatibility is critical. Existing users must not be disrupted. This validates that the mission system architecture doesn't break what already works.

**Independent Test**: Can be tested by initializing a project with `--mission software-dev` (or default) and running through the complete workflow (specify ’ plan ’ tasks ’ implement ’ review ’ accept ’ merge) to verify all existing features work identically. Delivers value by protecting existing user base.

**Acceptance Scenarios**:

1. **Given** an existing Spec Kitty user, **When** they run `spec-kitty init my-app` without specifying a mission, **Then** the software-dev mission is used by default

2. **Given** a software-dev mission is active, **When** the user runs `/spec-kitty.plan`, **Then** they see the familiar Technical Context section (Language/Version, Dependencies, Testing, etc.)

3. **Given** a software-dev project, **When** the user runs `/spec-kitty.tasks`, **Then** work packages reference familiar paths (`src/`, `tests/`, `contracts/`) and phases (research, design, implement, test)

4. **Given** all current templates moved into `missions/software-dev/`, **When** commands execute, **Then** they load templates from the active mission directory transparently

---

### User Story 3 - Research Mission Proof of Concept (Priority: P2)

As a researcher, I want to use Spec Kitty's structured workflow to manage a literature review project, with research-specific templates (research question, methodology, findings) and validation (sources cited, methodology documented) instead of software-specific concepts.

**Why this priority**: Proves the mission system works for a radically different domain. Research has different artifacts, workflow phases, validation rules, and success criteria than software. If this works, other missions become straightforward.

**Independent Test**: Can be tested by initializing with `--mission research`, running through the research workflow (question ’ methodology ’ gather ’ analyze ’ synthesize), and validating research-specific artifacts are created and checked. Delivers value by enabling an entirely new user segment.

**Acceptance Scenarios**:

1. **Given** a research mission is active, **When** the user runs `/spec-kitty.specify`, **Then** they define a research question and scope (not user stories and acceptance criteria)

2. **Given** a research mission is active, **When** the user runs `/spec-kitty.plan`, **Then** they see Methodology Context (Research Method, Data Sources, Analysis Tools) instead of Technical Context

3. **Given** a research project with findings in `for_review/`, **When** the user runs `/spec-kitty.review`, **Then** the agent validates sources are cited, methodology is documented, and findings are synthesized (not "tests pass")

4. **Given** a research project ready for acceptance, **When** the user runs `/spec-kitty.accept`, **Then** validation checks for research-specific completeness (all sources documented, methodology clear, no unresolved questions) instead of software checks (git clean, tests pass)

---

### User Story 4 - Mission-Specific MCP Tool Integration (Priority: P3)

As a research mission user, I want the system to automatically make research-relevant MCP tools available (web-search, pdf-reader, citation-manager) and hide software-specific tools (code-search, test-runner), so agents have the right capabilities for the task at hand.

**Why this priority**: Enhances agent effectiveness by providing domain-appropriate tools. Not blocking for initial implementation (agents can still use generic tools), but important for optimized experience.

**Independent Test**: Can be tested by checking agent context files (CLAUDE.md, GEMINI.md, etc.) after mission initialization to verify they reference mission-appropriate MCP tools. Delivers value by making agents more effective in their domain.

**Acceptance Scenarios**:

1. **Given** a research mission is active, **When** agent context is updated, **Then** CLAUDE.md includes instructions to use `web-search`, `pdf-reader`, `citation-manager` MCP tools

2. **Given** a software-dev mission is active, **When** agent context is updated, **Then** CLAUDE.md includes instructions to use `filesystem`, `git`, `code-search`, `test-runner` MCP tools

3. **Given** a mission.yaml specifies required MCP tools, **When** the system starts, **Then** it validates those tools are installed and warns if missing

4. **Given** a user switches missions, **When** agent context is regenerated, **Then** tool recommendations update to match the new mission

---

### User Story 5 - Mission Switching for Existing Projects (Priority: P3)

As a user who started a software project but now wants to use it for documentation writing, I want to switch missions mid-project while being warned about compatibility issues and given guidance on migration.

**Why this priority**: Nice to have but not critical for MVP. Most users will choose the right mission upfront. However, this enables experimentation and flexibility for power users.

**Independent Test**: Can be tested by creating a software-dev project, switching to writing mission, and verifying templates/validation change while the user is warned about artifacts that may not make sense in new context.

**Acceptance Scenarios**:

1. **Given** an existing software-dev project, **When** the user runs `spec-kitty mission switch writing`, **Then** the system shows a warning: "Current project has software-specific artifacts (contracts/, data-model.md). These may not apply to writing mission. Continue?"

2. **Given** the user confirms mission switch, **When** the switch completes, **Then** `.kittify/active-mission` symlink points to new mission and subsequent commands use new templates

3. **Given** a mission switch has occurred, **When** the user runs `/spec-kitty.plan`, **Then** they see the new mission's plan template (not a hybrid or broken state)

4. **Given** a project with mixed artifacts (some software, some writing), **When** validation runs, **Then** it uses the current mission's validation rules and ignores artifacts from the previous mission

---

## Functional Requirements

### FR1: Mission Directory Structure

The system MUST organize missions in a standard directory structure:

```
.kittify/
   core/                           # Generic workflow engine (unchanged)
      scripts/
      validators/
   missions/                       # NEW: Mission definitions
      software-dev/              # Default mission (extracted from current)
         mission.yaml           # Mission metadata and configuration
         templates/
            spec-template.md
            plan-template.md
            tasks-template.md
            task-prompt-template.md
         commands/              # Command-specific prompts
            specify.md
            plan.md
            tasks.md
            implement.md
            review.md
            accept.md
         constitution/
            principles.md
         validators.py          # Optional Python validation hooks
      research/                  # Research mission (proof of concept)
         mission.yaml
         templates/
         commands/
         constitution/
         validators.py
      writing/                   # Future: Writing mission
   active-mission -> missions/software-dev/  # Symlink to current mission
```

**Success Criteria**:
- Directory structure exists and is documented
- Missions are self-contained (all templates, commands, validators in one place)
- Adding a new mission requires only creating a new directory, no core code changes

### FR2: Mission Configuration Schema (mission.yaml)

The system MUST define a YAML schema for mission configuration:

```yaml
name: "Software Dev Kitty"
description: "Build high-quality software with structured workflows"
version: "1.0.0"
domain: "software"

# Workflow customization
workflow:
  phases:
    - name: "research"
      description: "Research technologies and best practices"
    - name: "design"
      description: "Define architecture and contracts"
    - name: "implement"
      description: "Write code following TDD"
    - name: "test"
      description: "Validate implementation"
    - name: "review"
      description: "Code review and quality checks"

# Expected artifacts
artifacts:
  required:
    - spec.md
    - plan.md
    - tasks.md
  optional:
    - data-model.md
    - contracts/
    - quickstart.md
    - research.md
    - checklists/

# Path conventions for this mission
paths:
  workspace: "src/"
  tests: "tests/"
  deliverables: "contracts/"
  documentation: "docs/"

# Validation rules
validation:
  checks:
    - git_clean
    - all_tests_pass
    - kanban_complete
    - no_clarification_markers
  custom_validators: true  # Use validators.py

# MCP tools recommended for this mission
mcp_tools:
  required:
    - filesystem
    - git
  recommended:
    - code-search
    - test-runner
    - docker
  optional:
    - github
    - gitlab

# Agent personality/instructions
agent_context: |
  You are a software development agent following TDD practices.
  Your constitution enforces Library-First, CLI Interface, and Test-First principles.
  You work in structured phases: research ’ design ’ implement ’ test ’ review.

  Key practices:
  - Tests before code (non-negotiable)
  - Library-first architecture
  - CLI interfaces for all features
  - Integration tests over mocks

# Task metadata fields
task_metadata:
  required:
    - task_id
    - lane
    - phase
    - agent
  optional:
    - shell_pid
    - assignee
    - estimated_hours

# Command customization
commands:
  specify:
    prompt: "Define user scenarios and acceptance criteria"
  plan:
    prompt: "Design technical architecture and implementation plan"
  tasks:
    prompt: "Break into work packages with TDD workflow"
  implement:
    prompt: "Execute implementation following test-first methodology"
  review:
    prompt: "Perform code review and validate against specification"
  accept:
    prompt: "Validate feature completeness and quality gates"
```

**Success Criteria**:
- Schema is documented and validated
- All missions use consistent YAML structure
- Mission config drives template selection, validation rules, and agent context

### FR3: Mission Loading System

The system MUST load mission configuration at runtime and use it to customize behavior:

**Python changes** (`src/specify_cli/mission.py` - NEW):
```python
from pathlib import Path
from typing import Dict, Any, List
import yaml

class Mission:
    def __init__(self, mission_path: Path):
        self.path = mission_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        config_file = self.path / "mission.yaml"
        if not config_file.exists():
            raise ValueError(f"Mission config not found: {config_file}")
        with open(config_file) as f:
            return yaml.safe_load(f)

    @property
    def name(self) -> str:
        return self.config.get("name", "Unknown Mission")

    @property
    def templates_dir(self) -> Path:
        return self.path / "templates"

    @property
    def commands_dir(self) -> Path:
        return self.path / "commands"

    def get_template(self, template_name: str) -> Path:
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        return template_path

    def get_validation_checks(self) -> List[str]:
        return self.config.get("validation", {}).get("checks", [])

def get_active_mission() -> Mission:
    """Get the currently active mission."""
    kittify_dir = Path.cwd() / ".kittify"
    active_mission_link = kittify_dir / "active-mission"

    if not active_mission_link.exists():
        # Default to software-dev
        active_mission_link = kittify_dir / "missions" / "software-dev"

    return Mission(active_mission_link.resolve())
```

**Bash changes** (`scripts/bash/common.sh`):
```bash
# Get active mission directory
get_active_mission_dir() {
    local kittify_dir="$(get_repo_root)/.kittify"
    local active_mission="$kittify_dir/active-mission"

    if [[ -L "$active_mission" ]]; then
        readlink "$active_mission"
    else
        echo "$kittify_dir/missions/software-dev"
    fi
}

# Get template from active mission
get_mission_template() {
    local template_name="$1"
    local mission_dir=$(get_active_mission_dir)
    echo "$mission_dir/templates/$template_name"
}
```

**Success Criteria**:
- Core scripts/Python code load templates from active mission
- No hardcoded paths to templates in core code
- Switching missions changes behavior without code changes

### FR4: Mission Selection During Init

The system MUST allow users to select a mission during project initialization:

**CLI changes** (`src/specify_cli/__init__.py`):
```python
@click.option(
    '--mission',
    type=click.Choice(['software-dev', 'research', 'writing', 'seo-audit']),
    default='software-dev',
    help='Mission type for this project'
)
def init(project_name: str, mission: str, ...):
    """Initialize a new Spec Kitty project with selected mission."""
    # Download/copy mission templates
    # Set up active-mission symlink
    # Copy mission-specific constitution
```

**Success Criteria**:
- `spec-kitty init --mission research` creates research project
- Default mission is software-dev (backwards compatible)
- Mission selection is persisted in `.kittify/active-mission`

### FR5: Mission Switching Command

The system MUST provide a command to switch missions for existing projects:

**CLI changes**:
```bash
spec-kitty mission list              # List available missions
spec-kitty mission current           # Show current mission
spec-kitty mission switch <name>     # Switch to different mission
spec-kitty mission info <name>       # Show mission details
```

**Python implementation** (`src/specify_cli/mission_cli.py` - NEW):
```python
@click.group()
def mission():
    """Manage Spec Kitty missions."""
    pass

@mission.command()
def list():
    """List available missions."""
    # Scan .kittify/missions/ directory
    # Display mission names, descriptions, versions

@mission.command()
def current():
    """Show current mission."""
    # Read active-mission symlink
    # Display mission info

@mission.command()
@click.argument('mission_name')
@click.option('--force', is_flag=True, help='Skip compatibility warnings')
def switch(mission_name: str, force: bool):
    """Switch to a different mission."""
    # Validate mission exists
    # Check for compatibility issues
    # Warn about artifacts that may not apply
    # Update active-mission symlink
```

**Success Criteria**:
- Users can list, view, and switch missions via CLI
- Switching missions shows warnings about incompatibility
- Documentation explains when/why to switch missions

### FR6: Research Mission Implementation

The system MUST include a complete "Deep Research Kitty" mission as proof of concept:

**Required files**:
- `missions/research/mission.yaml` - Full configuration
- `missions/research/templates/spec-template.md` - Research question format
- `missions/research/templates/plan-template.md` - Methodology planning
- `missions/research/templates/tasks-template.md` - Research task breakdown
- `missions/research/commands/specify.md` - Research scoping workflow
- `missions/research/commands/plan.md` - Methodology design workflow
- `missions/research/commands/implement.md` - Research execution workflow
- `missions/research/commands/review.md` - Findings review workflow
- `missions/research/commands/accept.md` - Research validation workflow
- `missions/research/constitution/principles.md` - Research best practices
- `missions/research/validators.py` - Custom validation (sources cited, etc.)

**Key differences from software-dev**:
- Phases: question ’ methodology ’ gather ’ analyze ’ synthesize (not research ’ design ’ implement)
- Artifacts: research-question.md, methodology.md, sources/, findings.md (not data-model.md, contracts/)
- Validation: sources cited, methodology documented (not tests pass, git clean)
- Agent context: "You are a research agent" (not "You are a software development agent")

**Success Criteria**:
- Can complete a full research workflow using research mission
- Templates use research-appropriate language
- Validation checks research-specific completeness
- Agent context guides research behavior

---

## Non-Functional Requirements

### NFR1: Backwards Compatibility

The mission system MUST NOT break existing Spec Kitty projects or workflows.

**Success Criteria**:
- Existing projects continue working without changes
- Software-dev mission behavior is identical to pre-mission system
- Documentation includes migration guide for existing projects
- All existing tests pass with software-dev mission active

### NFR2: Extensibility

The mission system MUST make it easy to add new missions without modifying core code.

**Success Criteria**:
- New mission can be added by creating a directory with required files
- No changes to core scripts/Python code required for new missions
- Mission template/documentation explains how to create custom missions
- Community can contribute missions as separate packages

### NFR3: Performance

Mission loading and switching MUST NOT introduce noticeable performance overhead.

**Success Criteria**:
- Mission config loaded once per command execution
- Template loading adds <50ms to command execution time
- Mission switching completes in <2 seconds
- Large projects (100+ features) not impacted by mission system

### NFR4: Documentation

The mission system MUST be thoroughly documented for users and mission developers.

**Success Criteria**:
- User guide explains mission selection and switching
- Developer guide explains how to create custom missions
- mission.yaml schema is fully documented with examples
- Each mission includes its own README with usage examples

---

## Out of Scope

The following are explicitly OUT OF SCOPE for this initial implementation:

1. **Hybrid missions** - Projects cannot mix multiple missions simultaneously
2. **Mission versioning/upgrades** - No automatic upgrade path when mission definitions change
3. **Mission marketplace** - No discovery/installation of third-party missions
4. **Cross-mission artifact migration** - No tools to convert software-dev artifacts to research format
5. **Writing/SEO missions** - Only software-dev and research missions in initial release
6. **Custom validation DSL** - Validation must be Python code, no declarative validation language
7. **Mission inheritance** - Missions cannot extend/inherit from each other
8. **Per-feature mission selection** - All features in a project use the same mission
9. **Mission-specific dashboard** - Dashboard remains generic, doesn't customize per mission
10. **AI agent training** - No fine-tuning or training on mission-specific behaviors

---

## Technical Constraints

1. **Python 3.11+ required** - For modern type hints and Path operations
2. **YAML 1.2 format** - Mission configs use standard YAML
3. **Symlinks required** - `active-mission` uses symlinks (Windows may need special handling)
4. **Git required** - Mission system assumes Git-based projects
5. **Backwards compatibility** - Must work with existing .kittify/ structure
6. **No database** - Mission metadata stored in filesystem only
7. **Markdown templates** - All templates must be valid Markdown
8. **No network calls** - Mission loading happens offline (missions bundled with CLI)

---

## Success Criteria

This feature is successful when:

1.  A user can run `spec-kitty init research-project --mission research` and get a fully functional research project
2.  All existing software-dev functionality works identically through the mission system
3.  Research mission can complete a full workflow (specify ’ plan ’ tasks ’ implement ’ review ’ accept)
4.  Switching missions updates templates and validation rules correctly
5.  Documentation clearly explains when to use each mission and how to create custom missions
6.  No performance regression for existing users
7.  Community feedback validates the mission system is intuitive and valuable
8.  At least one external contributor creates a custom mission (writing or SEO)

---

## Open Questions

1. **Should missions be versioned independently from Spec Kitty CLI?**
   - Pro: Allows mission evolution without CLI updates
   - Con: Version compatibility matrix becomes complex
   - **Decision needed**: Single version for CLI+missions vs. independent versioning

2. **How should mission-specific validation errors be displayed?**
   - Current: Generic error messages
   - Proposed: Mission-aware error messages with context
   - **Decision needed**: Generic vs. customized error messaging

3. **Should missions be able to add new slash commands?**
   - Example: Research mission adds `/spec-kitty.literature-review`
   - Pro: Allows domain-specific workflows
   - Con: Increases complexity, may confuse users switching missions
   - **Decision needed**: Fixed command set vs. extensible commands

4. **How to handle mission compatibility when switching?**
   - Strict: Block switch if artifacts are incompatible
   - Permissive: Allow switch with warnings
   - Assisted: Offer migration tools
   - **Decision needed**: Compatibility enforcement level

5. **Should agent context files be per-mission or universal?**
   - Per-mission: `missions/research/CLAUDE.md` (mission-specific guidance)
   - Universal: `.claude/CLAUDE.md` (mission-agnostic, dynamic)
   - **Decision needed**: Where agent context lives

6. **How to distribute custom missions?**
   - Git repos: Users clone mission repos into `.kittify/missions/`
   - PyPI packages: Missions distributed as Python packages
   - Bundled: All missions ship with CLI
   - **Decision needed**: Mission distribution strategy

---

## Dependencies

- **Python packages**: PyYAML (for mission config parsing)
- **Git**: Required for worktree management
- **CLI framework**: Click (already used)
- **Existing Spec Kitty infrastructure**: Templates, scripts, dashboard

---

## Migration Path

For existing Spec Kitty users:

1. **Phase 1: Transparent migration** (CLI update)
   - User updates `spec-kitty` CLI
   - On first run, system detects old structure
   - Auto-migrates by setting `active-mission -> missions/software-dev/`
   - No user action required, everything continues working

2. **Phase 2: Mission awareness** (Optional)
   - User runs `spec-kitty mission current` to see they're using software-dev
   - User reads about new mission system in CHANGELOG
   - No action required, but can explore other missions

3. **Phase 3: Experimentation** (Optional)
   - User tries `spec-kitty init test-research --mission research` in a separate project
   - Explores research mission capabilities
   - Decides whether to use for future projects

4. **Phase 4: Adoption** (Optional)
   - User starts new projects with appropriate missions
   - Shares custom missions with community
   - Provides feedback for mission improvements

---

## Timeline Estimate

- **Phase 1**: Extract software-dev into missions/ (2-3 days)
  - Move templates, commands, constitution
  - Update core scripts to load from active-mission
  - Validate backwards compatibility

- **Phase 2**: Implement mission loading system (2-3 days)
  - Create mission.yaml schema
  - Implement Python Mission class
  - Add bash helper functions
  - Test mission loading

- **Phase 3**: Create research mission (3-4 days)
  - Design research workflows
  - Write research templates
  - Create research validators
  - Test full research workflow

- **Phase 4**: Add mission CLI commands (1-2 days)
  - Implement mission list/current/switch/info
  - Add mission selection to init
  - Test mission switching

- **Phase 5**: Documentation and testing (2-3 days)
  - Write user guide
  - Write mission developer guide
  - Create example custom mission
  - Integration testing

**Total estimate**: 10-15 days for complete implementation

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking existing workflows | High | Medium | Extensive backwards compatibility testing, feature flags |
| Mission system too complex | Medium | Medium | Start simple, validate with users, iterate |
| Research mission not useful | Medium | Low | User research before implementation, prototype validation |
| Performance degradation | Medium | Low | Performance benchmarking, lazy loading |
| Community doesn't adopt | Low | Medium | Clear documentation, example missions, marketing |
| Mission proliferation (too many missions) | Low | Low | Quality guidelines, curation, featured missions list |

---

## Notes

- This specification follows Spec Kitty's own methodology (eating our own dog food)
- The mission system must feel natural and not add cognitive overhead
- Success depends on research mission being genuinely useful, not just a tech demo
- Community contributions are essential for long-term success
- Branding: Use "Kitty" suffix for all missions (e.g., "Deep Research Kitty", "Writing Kitty")
