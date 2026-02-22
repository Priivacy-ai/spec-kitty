---
work_package_id: WP02
title: Command Templates - All Steps
lane: "done"
dependencies: []
base_branch: 041-enable-plan-mission-runtime-support-WP01
base_commit: fd8b09d0a2d065f9ddd08efc49a5bbc21291c599
created_at: '2026-02-22T08:15:40.811638+00:00'
subtasks: [T004, T005, T006, T007, T008, T009]
description: Create mission-scoped command templates for all 4 planning steps
estimated_duration: 2-3 hours
priority: P0
shell_pid: "93261"
agent: "claude"
reviewed_by: "Robert Douglass"
review_status: "approved"
---

# WP02: Command Templates - All Steps

**Objective**: Create 4 mission-scoped command templates that guide AI agents through each step of the plan mission workflow (specify → research → plan → review).

**Context**: The plan mission has 4 sequential steps defined in the runtime schema (WP01). Each step needs a command template that provides context, deliverables, instructions, and success criteria to the agent. These templates are the primary interaction point between the runtime loop and agents.

**Key Success Criterion**: All 4 command templates must be created and validated, with no broken references or missing sections.

**Included Files**:
- `src/specify_cli/missions/plan/command-templates/specify.md` (create)
- `src/specify_cli/missions/plan/command-templates/research.md` (create)
- `src/specify_cli/missions/plan/command-templates/plan.md` (create)
- `src/specify_cli/missions/plan/command-templates/review.md` (create)

---

## Template Structure Reference

All 4 templates follow this structure:

```markdown
---
step_id: "{step_id}"
mission: "plan"
title: "{Step Title}"
description: "{Step Description}"
estimated_duration: "{time estimate}"
---

# {Step Title}

## Context

[Context for the agent - what is being accomplished, inputs, outputs]

## Deliverables

- [Specific deliverable 1]
- [Specific deliverable 2]
- ...

## Instructions

[Step-by-step instructions for the agent]

## Success Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- ...

## References

[Links to related documentation (optional)]
```

---

## Subtask Breakdown

### Subtask T004: Create specify.md (Step 1)
**Duration**: 30-40 minutes
**Goal**: Create the entry point template that initiates feature planning.

**File Path**: `src/specify_cli/missions/plan/command-templates/specify.md`

**Purpose of Step 1 - Specify**:
- Entry point into the plan mission
- Agent creates initial feature specification
- Establishes scope, requirements, user stories
- Output becomes input for step 2 (research)

**Template Content** (example structure - adapt to plan mission context):

```markdown
---
step_id: "specify"
mission: "plan"
title: "Specify"
description: "Create and document the feature specification"
estimated_duration: "15-20 minutes"
---

# Specify Feature

## Context

You are beginning the planning phase for a new software feature. Your role is to create a clear, detailed specification that will guide the research and design phases.

**Input**: Feature description or user request from the specification step

**Output**: A comprehensive specification document (`spec.md`) that will be the foundation for the remaining planning steps

**What You're Doing**: Analyzing the user's feature request, asking clarifying questions (if needed), and documenting:
- Feature goals and objectives
- User scenarios and use cases
- Functional and non-functional requirements
- Acceptance criteria and success metrics
- Constraints and assumptions

## Deliverables

- `spec.md` document with:
  - Executive Summary (1-2 paragraphs)
  - Problem Statement (what problem does this solve?)
  - Functional Requirements (list of requirements)
  - Success Criteria (measurable outcomes)
  - User Scenarios (3-5 key user flows)
  - Assumptions and Constraints
  - Scope boundaries (in/out of scope)

## Instructions

1. **Analyze the feature request**
   - What is the core feature being requested?
   - Who are the users?
   - What problem does it solve?

2. **Define feature goals**
   - List 3-5 primary goals
   - Ensure each goal is measurable

3. **Create user scenarios**
   - Develop 3-5 key user scenarios
   - Include happy path and at least one edge case
   - Each scenario should be testable

4. **Document requirements**
   - Translate goals and scenarios into testable requirements
   - Separate functional (what it does) from non-functional (performance, security, etc.)
   - Make requirements specific and measurable

5. **Define success criteria**
   - What does done look like?
   - How will we validate the feature works?
   - Include both user-facing and technical criteria

6. **Identify constraints and assumptions**
   - What technical limitations exist?
   - What are we assuming about the environment, users, etc.?
   - What's explicitly out of scope?

## Success Criteria

- [ ] spec.md file created with all required sections
- [ ] Feature goals are clear and measurable
- [ ] User scenarios are specific and testable (not generic)
- [ ] Requirements are testable (not vague like "fast" or "easy")
- [ ] Success criteria are technology-agnostic
- [ ] Scope boundaries are clearly stated
- [ ] No [NEEDS CLARIFICATION] markers remain (or justified and documented)
- [ ] Document is well-organized and readable

## References

- See: ../quickstart.md (for example of spec format)
- See: ../spec.md (if you need a reference specification)
```

**Steps**:

1. **Create the file**:
   ```bash
   touch src/specify_cli/missions/plan/command-templates/specify.md
   ```

2. **Write the template** using the structure above, customized for the plan mission's specify step

3. **Validate**:
   - YAML frontmatter parses
   - All required sections present
   - No broken references
   - Content is clear and actionable

**Success Criteria**:
- [ ] specify.md created at correct path
- [ ] Frontmatter YAML valid
- [ ] All required sections: Context, Deliverables, Instructions, Success Criteria
- [ ] Clear guidance on what agent should do
- [ ] Ready for agent to use

---

### Subtask T005: Create research.md (Step 2)
**Duration**: 30-40 minutes
**Goal**: Create the research phase template.

**File Path**: `src/specify_cli/missions/plan/command-templates/research.md`

**Purpose of Step 2 - Research**:
- Takes the specification from step 1
- Investigates technical requirements, patterns, dependencies
- Identifies risks and alternative approaches
- Output feeds into step 3 (plan/design)

**Template Guidance**:
- Input: spec.md from step 1
- Output: research.md with technical analysis
- Focus: Technical feasibility, patterns, dependencies, risks
- Key sections: Technical Analysis, Design Patterns, Dependencies, Risks & Mitigations, Recommendations

**Steps**:

1. Create research.md following the template structure

2. Key sections to include:
   - Technical Analysis: What are the technical requirements?
   - Design Patterns: What existing patterns apply?
   - Dependencies: What libraries, services, or systems are needed?
   - Risks: What could go wrong?
   - Recommendations: What approach is recommended?

3. Validate and ensure quality

**Success Criteria**:
- [ ] research.md created at correct path
- [ ] Frontmatter YAML valid
- [ ] Clear guidance on technical investigation
- [ ] Deliverables are specific (what research artifacts should be created?)

---

### Subtask T006: Create plan.md (Step 3)
**Duration**: 30-40 minutes
**Goal**: Create the design/planning phase template.

**File Path**: `src/specify_cli/missions/plan/command-templates/plan.md`

**Purpose of Step 3 - Plan**:
- Takes research findings from step 2
- Creates technical design artifacts
- Defines data models, API contracts, architecture
- Output is ready for implementation phase

**Template Guidance**:
- Input: research.md from step 2
- Output: design artifacts (data-model.md, contracts/, etc.)
- Focus: Architecture, data model, API design, implementation approach
- Key sections: Architecture Design, Data Model, API Contracts, Implementation Sketch, Assumptions

**Steps**:

1. Create plan.md following the template structure

2. Key sections to include:
   - Architecture Design: System design, component interactions
   - Data Model: Entities, relationships, schemas
   - API Contracts: REST/GraphQL endpoints, request/response shapes
   - Implementation Sketch: High-level implementation steps
   - Assumptions: Design assumptions documented

3. Validate and ensure quality

**Success Criteria**:
- [ ] plan.md created at correct path
- [ ] Frontmatter YAML valid
- [ ] Clear guidance on design artifact creation
- [ ] Deliverables are specific and implementable

---

### Subtask T007: Create review.md (Step 4)
**Duration**: 30-40 minutes
**Goal**: Create the final review phase template.

**File Path**: `src/specify_cli/missions/plan/command-templates/review.md`

**Purpose of Step 4 - Review** (Terminal Step):
- Takes design artifacts from step 3
- Reviews completeness and consistency
- Validates feasibility and alignment with spec
- Output signals planning is complete, ready for task generation

**Template Guidance**:
- Input: All planning artifacts (spec, research, design)
- Output: Validation report, approved design
- Focus: Completeness, consistency, feasibility, alignment
- Key sections: Validation Checklist, Issues Found, Recommendations, Approval Status

**Steps**:

1. Create review.md following the template structure

2. Key sections to include:
   - Validation Checklist: Is the design complete?
   - Issues Found: Any inconsistencies or missing pieces?
   - Recommendations: Changes needed?
   - Approval Status: Is the design approved?

3. Validate and ensure quality

**Success Criteria**:
- [ ] review.md created at correct path
- [ ] Frontmatter YAML valid
- [ ] Clear validation criteria documented
- [ ] Deliverables are specific (validation report format)

---

### Subtask T008: Validate All Templates
**Duration**: 30-40 minutes
**Goal**: Ensure all 4 templates are complete, consistent, and ready for use.

**Validation Checklist**:

For each template file (specify.md, research.md, plan.md, review.md):

1. **File existence**:
   - [ ] File exists at correct path
   - [ ] File is readable

2. **YAML frontmatter**:
   - [ ] Parses without errors: `python -c "import yaml; yaml.safe_load(open('file'))"`
   - [ ] step_id matches filename (specify.md has step_id: "specify", etc.)
   - [ ] mission == "plan"
   - [ ] title is non-empty
   - [ ] description is non-empty

3. **Body sections**:
   - [ ] Context section present and filled
   - [ ] Deliverables section present with bullet points
   - [ ] Instructions section present with numbered steps
   - [ ] Success Criteria section present with checkboxes
   - [ ] References section (optional, but if present check links are valid)

4. **Content quality**:
   - [ ] Context explains what's being accomplished
   - [ ] Deliverables are specific (not generic)
   - [ ] Instructions are actionable (not vague)
   - [ ] Success criteria are testable (not subjective)
   - [ ] No external service dependencies mentioned
   - [ ] No broken links or references

5. **Consistency**:
   - [ ] All 4 templates follow the same structure
   - [ ] Tone and style are consistent
   - [ ] Similar topics use similar language

**Validation Script** (run to check):

```bash
for file in specify research plan review; do
  echo "Validating $file.md..."
  python -c "
import yaml
from pathlib import Path

f = Path('src/specify_cli/missions/plan/command-templates/$file.md')
content = f.read_text()

# Extract frontmatter
parts = content.split('---')
frontmatter = yaml.safe_load(parts[1])

# Validate
assert frontmatter['step_id'] == '$file', f\"step_id mismatch: {frontmatter['step_id']}\"
assert frontmatter['mission'] == 'plan', f\"mission should be plan\"
assert '## Context' in content, 'Missing Context section'
assert '## Deliverables' in content, 'Missing Deliverables section'
assert '## Instructions' in content, 'Missing Instructions section'
assert '## Success Criteria' in content, 'Missing Success Criteria section'

print(f'✓ $file.md validates')
  " || exit 1
done

echo "✓ All templates valid"
```

**Success Criteria**:
- [ ] All 4 templates validated using script above
- [ ] No syntax or structure errors
- [ ] All required sections present in all templates
- [ ] Frontmatter parses for all templates
- [ ] Ready for WP03 (analysis for content template references)

---

### Subtask T009: Analyze for Content Template References
**Duration**: 15-20 minutes
**Goal**: Identify any references to content templates in the command templates.

**Background**: Content templates are optional templates that command templates might reference (e.g., "Use this template: ../templates/research-outline.md"). We only create content templates if explicitly referenced.

**Steps**:

1. **Search for content template references**:
   ```bash
   grep -r "\.\./templates/" src/specify_cli/missions/plan/command-templates/
   ```

2. **For each reference found**, document:
   - Which template file references it
   - What the reference is
   - Why it's needed

3. **Example patterns** (if found):
   - `See: ../templates/research-outline.md`
   - `Use: ../templates/design-checklist.md`
   - `Reference: ../templates/validation-rubric.md`

4. **Create analysis document** (capture in subtask notes or comments):
   - List any content templates that need to be created
   - Estimated number: 0-3 templates
   - These will be created in WP03 (T010)

5. **If no references found**:
   - Document: "No content template references found in command templates"
   - templates/ directory will remain empty (per spec guidelines)

**Success Criteria**:
- [ ] All command templates scanned for content references
- [ ] References documented and captured
- [ ] List of content templates to create (if any) prepared for WP03
- [ ] Clear understanding of what WP03 T010 needs to create

---

## Test Strategy

**No automated tests for this WP** - Templates are configuration files. Functional testing happens in WP04.

**Manual validation**:
- [ ] All 4 templates created at correct paths
- [ ] All YAML frontmatter parses
- [ ] All required sections present
- [ ] No broken references
- [ ] Content is clear and actionable

**Functional validation** (WP04):
- Runtime resolver can load each template
- Templates are executable (agents can follow them)
- Agent output matches expected format

---

## Definition of Done

- [x] specify.md created with entry point guidance
- [x] research.md created with research phase guidance
- [x] plan.md created with design phase guidance
- [x] review.md created with review phase guidance
- [x] All 4 templates follow consistent structure
- [x] All frontmatter YAML parses correctly
- [x] All required sections present (Context, Deliverables, Instructions, Success Criteria)
- [x] Validation script passes for all templates
- [x] Content template references identified and documented
- [x] Templates are 2.x-compatible (no doctrine paths, no mainline references)

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Inconsistent template structure | MEDIUM | Use template structure exactly; validate all 4 files |
| Missing content template references | MEDIUM | Scan all templates for references; document findings |
| Unclear instructions for agents | HIGH | Review instructions for clarity and specificity |
| Broken references to other files | LOW | Validation script checks for broken links |

---

## Reviewer Guidance

**What to Check**:
1. Do all 4 templates have consistent structure?
2. Are all required sections present in each template?
3. Is the guidance clear and actionable for an AI agent?
4. Are deliverables specific (not vague)?
5. Are success criteria testable (not subjective)?
6. Have content template references been identified?

**Green Light**: All templates created, validated, consistent, and ready for resolver testing in WP04.

**Red Light**: Missing sections, inconsistent structure, unclear guidance, or broken references.

---

## Next Work Package

WP03 will analyze content template references and create any needed supporting templates, then set up the test framework.

Implementation command after WP01 completes:
```bash
spec-kitty implement WP02 --base WP01
```

After completion:
```bash
spec-kitty implement WP03 --base WP02
```

## Activity Log

- 2026-02-22T08:15:41Z – claude – shell_pid=93261 – lane=doing – Assigned agent via workflow command
- 2026-02-22T08:18:16Z – claude – shell_pid=93261 – lane=for_review – Ready for review: All 4 command templates created and validated
- 2026-02-22T08:21:30Z – claude – shell_pid=93261 – lane=done – All 4 command templates created and validated. Frontmatter valid, all required sections present, step progression clear, no broken references. Ready for WP04 integration testing.
