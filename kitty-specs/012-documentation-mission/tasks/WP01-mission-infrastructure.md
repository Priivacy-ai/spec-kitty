---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
title: "Mission Infrastructure"
phase: "Phase 0 - Foundation"
lane: "doing"
assignee: ""
agent: "__AGENT__"
shell_pid: "10160"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
  - timestamp: "2026-01-12T17:18:56Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Mission Infrastructure

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Create the documentation mission directory structure and mission.yaml configuration file that defines the documentation workflow, artifacts, and validation rules.

**Success Criteria**:
- Mission directory exists at `src/specify_cli/missions/documentation/`
- `mission.yaml` is valid YAML and passes pydantic validation
- Mission loads successfully via `get_mission_by_name("documentation")`
- Mission appears in `list_available_missions()` output
- Mission config defines 6 workflow phases: discover → audit → design → generate → validate → publish
- Required and optional artifacts are specified
- Path conventions, validation checks, and agent context are defined

## Context & Constraints

**Prerequisites**:
- Existing mission system in `src/specify_cli/mission.py`
- Existing missions: software-dev, research (use as reference)
- Mission schema defined in `MissionConfig` pydantic model

**Reference Documents**:
- [plan.md](../plan.md) - Mission configuration design (lines 182-211)
- [data-model.md](../data-model.md) - Mission Configuration entity (lines 26-91)
- [research.md](../research.md) - Mission phase design (lines 575-617)
- Existing mission configs:
  - `src/specify_cli/missions/software-dev/mission.yaml`
  - `src/specify_cli/missions/research/mission.yaml`

**Constraints**:
- Must follow existing mission architecture patterns
- Must not break existing mission loading logic
- Domain must be "other" (documentation is new domain type)
- Version must follow semver: "1.0.0"

## Subtasks & Detailed Guidance

### Subtask T001 – Create Mission Directory Structure

**Purpose**: Establish the directory hierarchy for the documentation mission.

**Steps**:
1. Create `src/specify_cli/missions/documentation/` directory
2. Create subdirectories:
   - `templates/` (for spec, plan, tasks templates)
   - `command-templates/` (for specify, plan, implement, review)
3. Verify directory structure matches existing missions

**Files**:
- `src/specify_cli/missions/documentation/` (new directory)
- `src/specify_cli/missions/documentation/templates/` (new directory)
- `src/specify_cli/missions/documentation/command-templates/` (new directory)

**Parallel?**: No (foundation for remaining subtasks)

**Notes**: This is the foundation. All other work packages depend on this structure existing.

### Subtask T002 – Create mission.yaml Configuration

**Purpose**: Define the documentation mission configuration following the pydantic schema.

**Steps**:
1. Create `src/specify_cli/missions/documentation/mission.yaml`
2. Define basic metadata:
   ```yaml
   name: "Documentation Kitty"
   description: "Create and maintain high-quality software documentation following Write the Docs and Divio principles"
   version: "1.0.0"
   domain: "other"
   ```
3. Define workflow phases (see T003-T007 for full config)
4. Validate YAML syntax: `python -c "import yaml; yaml.safe_load(open('mission.yaml'))"`

**Files**: `src/specify_cli/missions/documentation/mission.yaml` (new file)

**Parallel?**: No (other subtasks extend this file)

**Notes**: Start with basic structure, other subtasks will add sections.

### Subtask T003 – Define Artifacts

**Purpose**: Specify required and optional artifacts for documentation missions.

**Steps**:
1. Add `artifacts:` section to mission.yaml:
   ```yaml
   artifacts:
     required:
       - spec.md
       - plan.md
       - tasks.md
       - gap-analysis.md  # For gap-filling mode only
     optional:
       - divio-templates/
       - generator-configs/
      - audit-report.md
      - research.md
      - data-model.md
      - quickstart.md
      - release.md
   ```

**Files**: `src/specify_cli/missions/documentation/mission.yaml`

**Parallel?**: No (modifies mission.yaml)

**Notes**: gap-analysis.md is required for gap-filling iterations but not initial missions.

### Subtask T004 – Define Path Conventions

**Purpose**: Specify default paths for documentation mission workspace.

**Steps**:
1. Add `paths:` section to mission.yaml:
   ```yaml
   paths:
     workspace: "docs/"
     deliverables: "docs/output/"
     documentation: "docs/"
   ```

**Files**: `src/specify_cli/missions/documentation/mission.yaml`

**Parallel?**: No (modifies mission.yaml)

**Notes**: These are suggestions; users can override in their project structure.

### Subtask T005 – Define Validation Checks

**Purpose**: Specify validation checks that run during mission acceptance.

**Steps**:
1. Add `validation:` section to mission.yaml:
   ```yaml
   validation:
     checks:
       - all_divio_types_valid
       - no_conflicting_generators
       - templates_populated
       - gap_analysis_complete  # For gap-filling mode
     custom_validators: false  # No custom validators.py initially
   ```

**Files**: `src/specify_cli/missions/documentation/mission.yaml`

**Parallel?**: No (modifies mission.yaml)

**Notes**: Validation checks are named; implementation can come later in testing WP.

### Subtask T006 – Add Agent Context

**Purpose**: Provide agent instructions for documentation mission behavior.

**Steps**:
1. Add `agent_context:` section to mission.yaml:
   ```yaml
   agent_context: |
     You are a documentation agent following Write the Docs best practices and the Divio documentation system.

     Key Practices:
     - Documentation as code: docs live in version control alongside source
     - Divio 4-type system: tutorial, how-to, reference, explanation (distinct purposes)
     - Accessibility: clear language, proper headings, alt text for images
     - Bias-free language: inclusive examples and terminology
     - Iterative improvement: support gap-filling and feature-specific documentation

     Workflow Phases: discover → audit → design → generate → validate → publish

     Generator Integration:
     - JSDoc for JavaScript/TypeScript API reference
     - Sphinx for Python API reference (autodoc + napoleon)
     - rustdoc for Rust API reference

     Gap Analysis:
     - Audit existing docs to identify missing Divio types
     - Build coverage matrix showing what exists vs what's needed
     - Prioritize gaps by user impact
   ```

**Files**: `src/specify_cli/missions/documentation/mission.yaml`

**Parallel?**: No (modifies mission.yaml)

**Notes**: Agent context appears in command templates, guides AI behavior.

### Subtask T007 – Add Command Customizations

**Purpose**: Define command-specific prompts for documentation mission commands.

**Steps**:
1. Add `commands:` section to mission.yaml:
   ```yaml
   commands:
     specify:
       prompt: "Define documentation needs: iteration mode (initial/gap-filling/feature-specific), Divio types to include, target audience, and documentation goals"
     plan:
       prompt: "Design documentation structure, configure generators (JSDoc/Sphinx/rustdoc), plan gap-filling strategy if iterating"
     tasks:
       prompt: "Break documentation work into packages: template creation, generator setup, content authoring, quality validation"
     implement:
       prompt: "Generate documentation from templates, invoke generators for reference docs, populate templates with project-specific content"
     review:
       prompt: "Validate Divio type adherence, check accessibility guidelines, verify generator output quality, assess completeness"
   ```

**Files**: `src/specify_cli/missions/documentation/mission.yaml`

**Parallel?**: No (modifies mission.yaml)

**Notes**: These prompts appear in command templates to guide users.

## Test Strategy

**Unit Tests** (to be implemented in WP09):
1. Test mission loads successfully:
   ```python
   def test_documentation_mission_loads():
       mission = get_mission_by_name("documentation")
       assert mission.name == "Documentation Kitty"
       assert mission.domain == "other"
       assert mission.version == "1.0.0"
   ```

2. Test workflow phases are correct:
   ```python
   def test_documentation_mission_phases():
       mission = get_mission_by_name("documentation")
       phases = mission.get_workflow_phases()
       assert len(phases) == 6
       assert phases[0]["name"] == "discover"
       assert phases[5]["name"] == "publish"
   ```

3. Test artifacts are defined:
   ```python
   def test_documentation_mission_artifacts():
       mission = get_mission_by_name("documentation")
       required = mission.get_required_artifacts()
       assert "spec.md" in required
       assert "gap-analysis.md" in required
   ```

**Manual Validation**:
1. Load mission in Python REPL:
   ```python
   from specify_cli.mission import get_mission_by_name, list_available_missions

   # Check mission appears in list
   missions = list_available_missions(Path("src/specify_cli/missions").parent)
   assert "documentation" in missions

   # Load mission
   mission = get_mission_by_name("documentation", Path("src/specify_cli/missions").parent)
   print(mission)  # Should show Mission(name='Documentation Kitty', ...)

   # Check phases
   print(mission.get_workflow_phases())
   # Should show 6 phases: discover, audit, design, generate, validate, publish
   ```

2. Validate YAML syntax:
   ```bash
   python -c "import yaml; print(yaml.safe_load(open('src/specify_cli/missions/documentation/mission.yaml')))"
   ```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Invalid YAML syntax | High - mission won't load | Validate with yaml.safe_load before committing |
| Pydantic validation fails | High - breaks mission system | Test against MissionConfig schema |
| Domain enum doesn't support "other" | Medium - need code change | Check mission.py domain Literal, extend if needed |
| Breaking existing missions | High - software-dev/research stop working | Test that existing missions still load after changes |

## Definition of Done Checklist

- [ ] Directory structure created: `src/specify_cli/missions/documentation/` with `templates/` and `command-templates/` subdirectories
- [ ] `mission.yaml` file created with all required sections
- [ ] mission.yaml passes YAML syntax validation
- [ ] Mission loads successfully via `get_mission_by_name("documentation")`
- [ ] Mission appears in `list_available_missions()` output
- [ ] Workflow phases are correctly defined (6 phases)
- [ ] Required artifacts include spec.md, plan.md, tasks.md, gap-analysis.md
- [ ] Optional artifacts include divio-templates/, generator-configs/, audit-report.md, release.md
- [ ] Path conventions defined (workspace, deliverables, documentation)
- [ ] Validation checks defined (4 checks)
- [ ] Agent context includes Write the Docs and Divio principles
- [ ] Command customizations defined for all 5 commands
- [ ] `tasks.md` in feature directory updated with WP01 status

## Review Guidance

**Key Acceptance Checkpoints**:
1. Mission config is valid YAML and passes pydantic validation
2. Mission loads without errors
3. Workflow phases match documentation workflow (not software-dev phases)
4. Artifacts are appropriate for documentation missions
5. Agent context mentions Write the Docs, Divio, and generators
6. Command prompts are documentation-specific (not generic)

**Validation Commands**:
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('src/specify_cli/missions/documentation/mission.yaml'))"

# Test mission loading
python -c "from specify_cli.mission import get_mission_by_name; m = get_mission_by_name('documentation'); print(m)"

# Check mission list
python -c "from specify_cli.mission import list_available_missions; print(list_available_missions())"
```

**Review Focus Areas**:
- Config completeness: All sections present and populated
- Phase correctness: 6 phases specific to documentation workflow
- Artifact appropriateness: Includes gap-analysis.md for iterative work
- Agent context quality: Clear, actionable guidance for documentation missions

## Activity Log

- 2026-01-12T17:18:56Z – system – lane=planned – Prompt created.
- 2026-01-12T17:44:57Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-12T18:22:44Z – unknown – lane=done – Review passed
- 2026-01-14T16:41:42Z – test-agent – shell_pid=70026 – lane=doing – Started implementation via workflow command
- 2026-01-16T13:37:31Z – test-agent – shell_pid=70026 – lane=done – Review passed: mission documentation infrastructure matches requirements
- 2026-01-16T13:51:33Z – __AGENT__ – shell_pid=10160 – lane=doing – Started review via workflow command
