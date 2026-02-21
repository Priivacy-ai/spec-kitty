# Implementation Plan: Documentation Mission

**Branch**: `012-documentation-mission` | **Date**: 2026-01-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/012-documentation-mission/spec.md`

## Summary

Add a new "documentation" mission type to spec-kitty that helps teams create and maintain high-quality software documentation. The mission integrates Write the Docs best practices, the Divio documentation system's four types (tutorials, how-to guides, reference, explanation), and automated documentation generation for JavaScript/TypeScript (JSDoc), Python (Sphinx), and Rust (rustdoc).

The implementation extends spec-kitty's existing mission architecture by creating a new mission in `src/specify_cli/missions/documentation/` with custom workflow phases, Divio-specific templates, and generator configuration templates. The mission supports iterative execution with gap analysis to identify missing documentation types and outdated content.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase requirement)
**Primary Dependencies**:

- ruamel.yaml (YAML frontmatter parsing)
- typer (CLI framework)
- Rich (console output)
- pathlib (file operations)
- subprocess (invoking JSDoc, Sphinx, rustdoc)

**Storage**: Filesystem only (mission configs in YAML, templates in Markdown, state in JSON)
**Testing**: pytest (existing spec-kitty test framework)
**Target Platform**: macOS, Linux, Windows (CLI tool, cross-platform)
**Project Type**: Single project (Python library + CLI)
**Performance Goals**:

- Mission discovery < 100ms
- Template generation < 2 seconds for 4 Divio types
- Gap analysis < 5 seconds for typical documentation structures

**Constraints**:

- Must not break existing software-dev and research missions
- Must follow existing mission architecture patterns
- Template changes must be version-controlled and testable
- No external API calls (offline-capable)

**Scale/Scope**:

- 1 new mission type (documentation)
- 4 Divio type templates (tutorial, how-to, reference, explanation)
- 3 generator integrations (JSDoc, Sphinx, rustdoc)
- ~8-10 new files in missions directory
- ~15 functional requirements to implement

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: No project constitution file found at `.kittify/memory/constitution.md`

**Gate Evaluation**: N/A - This is spec-kitty itself, which is the tool that creates and enforces constitutions for other projects. No constitution checks required.

**Architectural Principles** (from spec-kitty's existing patterns):

- ✅ **Library-First**: New mission logic implemented as library modules, exposed via CLI
- ✅ **Test-First**: All mission loading, template generation, and validation will have unit tests
- ✅ **CLI Interface**: Mission management via `spec-kitty` CLI commands
- ✅ **Filesystem State**: Mission configs and templates stored in files, no database

## Project Structure

### Documentation (this feature)

```
kitty-specs/012-documentation-mission/
├── spec.md                    # Feature specification
├── plan.md                    # This file (implementation plan)
├── research.md                # Phase 0: Research findings on doc generators
├── data-model.md              # Phase 1: Entity definitions
├── quickstart.md              # Phase 1: Quick reference for contributors
├── checklists/
│   └── requirements.md        # Spec quality checklist (already created)
└── tasks/                     # Phase 2: Work packages (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/specify_cli/
├── missions/
│   ├── software-dev/          # Existing mission
│   │   ├── mission.yaml
│   │   ├── templates/
│   │   └── command-templates/
│   ├── research/              # Existing mission
│   │   ├── mission.yaml
│   │   ├── templates/
│   │   └── command-templates/
│   └── documentation/         # NEW: Documentation mission
│       ├── mission.yaml       # Mission configuration
│       ├── templates/
│       │   ├── spec-template.md
│       │   ├── plan-template.md
│       │   ├── tasks-template.md
│       │   ├── task-prompt-template.md
│       │   └── divio/         # Divio documentation templates
│       │       ├── tutorial-template.md
│       │       ├── howto-template.md
│       │       ├── reference-template.md
│       │       └── explanation-template.md
│       └── command-templates/ # Command instructions
│           ├── specify.md
│           ├── plan.md
│           ├── tasks.md
│           ├── implement.md
│           └── review.md
├── mission.py                 # Core mission loading (no changes needed)
├── cli/
│   └── commands/
│       └── mission.py         # Mission CLI commands (no changes needed)
└── upgrade/
    └── migrations/
        └── m_0_12_0_documentation_mission.py  # NEW: Migration to install docs mission

tests/specify_cli/
└── missions/
    ├── test_documentation_mission.py          # NEW: Mission config tests
    └── test_documentation_templates.py        # NEW: Template validation tests
```

**Structure Decision**: Single project structure maintained. All mission logic lives in `src/specify_cli/missions/documentation/` following the established pattern from software-dev and research missions. Templates are stored alongside mission config for discoverability and maintainability.

## Complexity Tracking

*No constitution violations - this section is not needed.*

## Phase 0: Research

### Objective

Research documentation generator integration patterns, Divio template best practices, and gap analysis algorithms to inform technical design.

### Research Tasks

1. **JSDoc Integration Patterns**
   - How to invoke JSDoc programmatically from Python
   - Configuration file structure and options
   - Output format options (Markdown, HTML)
   - Common issues and error handling

2. **Sphinx Integration Patterns**
   - How to generate initial Sphinx conf.py from Python
   - Autodoc extension configuration
   - Napoleon extension for Google/NumPy docstrings
   - Theme selection and customization
   - Output to Markdown vs HTML

3. **rustdoc Integration Patterns**
   - How to invoke `cargo doc` from Python
   - Output directory structure
   - JSON output format for parsing
   - Integration with non-Cargo build systems

4. **Gap Analysis Algorithms**
   - How to parse existing documentation structures (Sphinx, Docusaurus, Jekyll, MkDocs)
   - Heuristics for classifying docs into Divio types
   - Version mismatch detection between code and docs
   - Coverage metrics calculation

5. **Mission Phase Design**
   - Appropriate workflow phases for documentation missions
   - How research/software-dev phases map to documentation workflow
   - Custom phase names that make sense for documentation context

### Research Output

See [research.md](research.md) for detailed findings, decisions, and rationale.

## Phase 1: Design

### Objective

Define the documentation mission configuration, template structure, and data model for gap analysis and iteration state.

### Data Model

See [data-model.md](data-model.md) for entity definitions including:

- Documentation Mission entity
- Divio Documentation Type entity
- Gap Analysis entity
- Generator Configuration entity
- Iteration Mode entity

### Mission Configuration Design

**mission.yaml structure**:

- name: "Documentation Kitty"
- domain: "other" (documentation is a new domain)
- workflow phases: discover → audit → design → generate → validate → publish
- required artifacts: spec.md, plan.md, tasks.md, gap-analysis.md (if gap-filling mode)
- optional artifacts: divio-templates/, generator-configs/, audit-report.md, release.md
- validation checks: all_divio_types_valid, no_conflicting_generators, templates_populated

**Template hierarchy**:

- Standard templates (spec, plan, tasks) follow software-dev patterns
- New divio/ subdirectory contains 4 Divio type templates
- Each Divio template includes:
  - Frontmatter with type, audience, purpose
  - Section structure per Divio guidelines
  - Placeholder prompts for content
  - Write the Docs best practice reminders

**Generator configuration templates**:

- `sphinx-conf.py.template` - Parametrized Sphinx configuration
- `jsdoc.json.template` - JSDoc configuration
- `rustdoc-config.toml.template` - Cargo.toml snippet for rustdoc

### Contracts

**Mission API** (interfaces for mission system):

- Mission loading: Existing `get_mission_by_name()` works unchanged
- Template access: Use existing `Mission.get_template()` method
- Phase validation: Implement custom validators.py if needed

**Generator Interfaces** (abstraction for doc generators):

```python
class DocGenerator(Protocol):
    def detect(self, project_root: Path) -> bool: ...
    def configure(self, output_dir: Path, options: Dict[str, Any]) -> Path: ...
    def generate(self, source_dir: Path, output_dir: Path) -> GeneratorResult: ...
```

Concrete implementations: `JSDocGenerator`, `SphinxGenerator`, `RustdocGenerator`

### Work Breakdown

Will be detailed in Phase 2 (tasks.md). High-level work packages:

1. **WP01: Mission Infrastructure** - Create mission.yaml and directory structure
2. **WP02: Core Templates** - Create spec/plan/tasks templates for documentation mission
3. **WP03: Divio Templates** - Create 4 Divio type templates with guidance
4. **WP04: Generator Abstraction** - Implement DocGenerator protocol and concrete generators
5. **WP05: Gap Analysis** - Implement documentation auditing and gap detection
6. **WP06: State Management** - Implement iteration state persistence in meta.json
7. **WP07: Command Templates** - Create specify/plan/implement/review command instructions
8. **WP08: Migration** - Write migration to install documentation mission
9. **WP09: Testing** - Unit tests for mission loading, templates, generators
10. **WP10: Documentation** - Update spec-kitty docs to explain documentation missions

### Integration Points

- **Mission loading**: Uses existing `Mission` class, no changes needed
- **Template system**: Uses existing `Mission.get_template()`, extends with divio/ subdirectory
- **CLI commands**: Existing `/spec-kitty.*` commands work unchanged, mission determines behavior
- **Upgrade system**: New migration installs documentation mission to `.kittify/missions/documentation/`

### Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Generator subprocess failures | High - blocks reference doc generation | Graceful degradation: generate manual templates if generator fails, log errors clearly |
| Gap analysis false positives | Medium - confuses users about missing docs | Conservative heuristics: only flag obvious gaps, allow user override |
| Mission config breaking changes | High - breaks existing missions | Strict validation tests, migration tests verify software-dev/research unchanged |
| Template content quality | Medium - users get poor guidance | Extensive Write the Docs research, user testing with spec-kitty's own docs |
| Multi-language complexity | Medium - polyglot projects edge cases | Start with single-language, test multi-language as P3 user story |

### Non-Functional Requirements

- **Performance**: Mission discovery < 100ms (already met by existing system)
- **Reliability**: Template generation must be deterministic and repeatable
- **Testability**: All templates must have validation tests (schema, required sections)
- **Maintainability**: Mission config follows existing patterns, easy for contributors to extend
- **Portability**: Cross-platform (macOS, Linux, Windows), no OS-specific dependencies

## Phase 2: Implementation

**Note**: Phase 2 (work package generation) is handled by the `/spec-kitty.tasks` command, which must be run explicitly after this planning phase completes.

The tasks command will:

1. Read this plan and the specification
2. Break the work breakdown above into detailed work packages
3. Generate individual WP prompt files in `tasks/WP*.md`
4. Create `tasks.md` with the full work package list
5. Populate dependency relationships between work packages

**Agent reminder**: DO NOT create tasks.md or WP files in this planning phase. Stop after Phase 1 design and report completion.

## Agent Context Updates

After Phase 1 design completes, the following agent context files will be updated:

**Files to update**:

- `.claude/` - Add documentation mission to known missions
- `.github/prompts/` - Add documentation mission patterns
- `.gemini/` - Add documentation mission context
- `.cursor/` - Add documentation mission examples
- And 8 other agent directories (12 total agents)

**Content to add**: "Documentation mission available for creating/maintaining project docs following Divio system (tutorial, how-to, reference, explanation)"

## Success Criteria Validation

Validating against spec.md success criteria:

- **SC-001** (30 min setup): Design enables this via templates and generator configs
- **SC-002** (100% gap detection): Gap analysis algorithm design addresses this
- **SC-003** (10% manual correction): Generator integration design minimizes post-processing
- **SC-004** (60% time reduction): Divio templates with guidance and placeholders enable this
- **SC-005** (multi-language): Generator abstraction supports multiple languages
- **SC-006** (90% accessibility): Templates include accessibility prompts per Write the Docs
- **SC-007** (iteration detection): State management in meta.json enables this
- **SC-008** (hosting integration): Templates generate standard formats (Markdown, HTML)

All success criteria are addressable by the planned design.

## Next Steps

1. **Complete Phase 0 Research** → Generate research.md with generator integration findings
2. **Complete Phase 1 Design** → Generate data-model.md with entity definitions
3. **Generate quickstart** → Create quickstart.md for contributors
4. **Prepare release guidance (optional)** → Create release.md when publish is in scope
4. **Update agent context** → Add documentation mission to all 12 agent directories
5. **Report completion** → User runs `/spec-kitty.tasks` to generate work packages

---

**Planning Status**: Phase 0 and Phase 1 in progress. Agent will generate research.md, data-model.md, and quickstart.md next.
