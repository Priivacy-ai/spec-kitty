# Command Template Schema Contract

**Purpose**: Define the expected structure for mission-scoped command templates in the plan mission

---

## Template File Structure

Each command template MUST follow this structure:

```markdown
---
step_id: "string"           # Must match step ID in mission-runtime.yaml
mission: "plan"             # Mission identifier
title: "string"             # Human-readable title
description: "string"       # Brief description of this step
estimated_duration: "string" # Time estimate (optional)
---

# {Title}

## Context

[Detailed context about what this step accomplishes]

## Deliverables

- [Specific deliverable 1]
- [Specific deliverable 2]
- [Additional deliverables as needed]

## Instructions

[Step-by-step instructions or prompts for the agent]

## Success Criteria

- [Success criterion 1]
- [Success criterion 2]
- [Additional criteria as needed]

## References

[Links to related documentation, templates, or resources (optional)]
```

---

## Field Specifications

### Frontmatter (YAML)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `step_id` | string | YES | Must match a step ID in mission-runtime.yaml (specify, research, plan, or review) |
| `mission` | string | YES | Must be "plan" |
| `title` | string | YES | Title of the step (e.g., "Specify", "Research", "Plan", "Review") |
| `description` | string | YES | Brief description of step purpose |
| `estimated_duration` | string | NO | Approximate time to complete (e.g., "15-30 minutes") |

### Body Sections

| Section | Type | Required | Description |
|---------|------|----------|-------------|
| Context | Markdown | YES | Explains what should be accomplished in this step, why it matters, and what the agent should focus on |
| Deliverables | Markdown list | YES | Specific outputs the agent should produce (use bullet points) |
| Instructions | Markdown | YES | Step-by-step guidance or prompts for the agent |
| Success Criteria | Markdown list | YES | How to validate the step is complete (use bullet points) |
| References | Markdown | NO | Links to related docs, templates, or external resources |

---

## Plan Mission Command Templates

### 1. specify.md

```yaml
---
step_id: "specify"
mission: "plan"
title: "Specify Feature"
description: "Prepare and specify the feature definition"
estimated_duration: "15-20 minutes"
---
```

**Purpose**: Entry point; create feature specification
**Output**: Feature spec document with clear requirements
**Agent Task**: Ask clarifying questions, document user intent, create specification outline

### 2. research.md

```yaml
---
step_id: "research"
mission: "plan"
title: "Research"
description: "Gather research inputs and technical context"
estimated_duration: "20-30 minutes"
---
```

**Purpose**: Investigate technical requirements and design patterns
**Output**: Research document with findings and recommendations
**Agent Task**: Analyze technical aspects, research patterns, identify dependencies

### 3. plan.md

```yaml
---
step_id: "plan"
mission: "plan"
title: "Plan"
description: "Design and create planning artifacts"
estimated_duration: "30-45 minutes"
---
```

**Purpose**: Create technical design artifacts
**Output**: Data model, API contracts, architecture diagram
**Agent Task**: Design system, create contracts, document architecture

### 4. review.md

```yaml
---
step_id: "review"
mission: "plan"
title: "Review"
description: "Review and validate planning artifacts"
estimated_duration: "10-15 minutes"
---
```

**Purpose**: Validate completeness and consistency
**Output**: Validation report, approval status
**Agent Task**: Review all artifacts, check consistency, validate feasibility

---

## Template Content Guidelines

### Context Section

**Purpose**: Set the stage for the agent

**Good practices**:
- Explain what this step accomplishes
- Describe inputs (what was completed in previous step)
- Describe outputs (what should be delivered)
- Call out any dependencies or prerequisites
- Be specific about the feature context

**Example**:
```
## Context

You are now in the Research phase of planning a new software feature.

**Input**: Feature specification from the Specify step (spec.md)

**What you're doing**: Investigating the technical requirements, design patterns,
and dependencies needed to build this feature.

**Output**: A research document with findings and recommendations that will
inform the design phase.

**Focus areas**:
- Technical requirements and constraints
- Existing design patterns that apply
- Third-party dependencies
- Potential risks or challenges
```

### Deliverables Section

**Purpose**: Define concrete outputs

**Good practices**:
- Use bullet points
- Be specific (file names, document sections, etc.)
- Include format (Markdown, JSON, YAML, etc.)
- Estimate scope ("2-3 pages", "5-10 items", etc.)

**Example**:
```
## Deliverables

- research.md (Markdown document)
  - Technical Analysis section (2-3 pages)
  - Design Patterns section (1-2 pages)
  - Dependencies section (0.5-1 page)
  - Risks & Mitigations section (0.5-1 page)
  - Recommendations section (0.5 page)

- Rough architecture sketch (ASCII diagram or description)
```

### Instructions Section

**Purpose**: Guide the agent through the work

**Good practices**:
- Use numbered steps
- Be concrete and actionable
- Include specific questions or prompts
- Reference templates or examples if available
- Break down complex tasks into subtasks

**Example**:
```
## Instructions

1. **Analyze the specification** from the previous step
   - What are the core requirements?
   - What constraints exist?
   - Who are the key users?

2. **Research technical patterns**
   - What design patterns apply to this type of feature?
   - Are there existing examples in similar projects?
   - What dependencies or libraries are commonly used?

3. **Identify risks**
   - What could go wrong?
   - What technical challenges exist?
   - Are there security or compliance concerns?

4. **Compile findings**
   - Organize your research into the research.md document
   - Include alternatives considered
   - Make recommendations for the design phase
```

### Success Criteria Section

**Purpose**: Validate completion

**Good practices**:
- Use bullet points
- Be testable/observable
- Include both content and quality checks
- Focus on outcomes, not process

**Example**:
```
## Success Criteria

- [ ] research.md is complete with all required sections
- [ ] Technical analysis addresses all key requirements
- [ ] Design patterns are well-researched and cited
- [ ] Dependencies are clearly listed with version constraints
- [ ] Risks are identified with mitigation strategies
- [ ] Recommendations are specific and actionable
- [ ] Document is well-organized and easy to follow
- [ ] No broken links or missing references
```

---

## Validation Rules

For each command template file:

✅ File exists in `src/specify_cli/missions/plan/command-templates/{step_id}.md`
✅ Frontmatter YAML parses correctly
✅ `step_id` matches a step in mission-runtime.yaml
✅ `mission` == "plan"
✅ `title` is provided and non-empty
✅ Body has all required sections: Context, Deliverables, Instructions, Success Criteria
✅ References section is optional but if present, all links are valid
✅ No broken references to content templates (../templates/...)
✅ No doctrine path references (2.x-safe paths only)
✅ Content is plan mission-specific (not generic)

---

## Path Reference Rules

### Allowed Paths

✅ Relative to command template file:
```markdown
See: ../templates/research-outline.md
Link: ../data-model.md
Reference: ../../spec.md
```

✅ Absolute within project:
```markdown
Source: src/specify_cli/missions/plan/
Docs: docs/plan-mission/
```

### Prohibited Paths

❌ Doctrine paths (2.x compatibility violation):
```markdown
NO: doctrine/prompts/
NO: .doctrine/
NO: .amazonq/prompts/  (agent-specific - use 2.x paths only)
```

❌ External service references:
```markdown
NO: https://external-api.com/template
NO: Database queries
NO: Network calls
```

---

## Content Template Integration

### When to Reference Content Templates

If a command template needs to reuse common content:

```markdown
See also: ../templates/research-outline.md
```

### Creating Content Templates

Only create if explicitly referenced. Example:

**In research.md**:
```markdown
Use this template: ../templates/research-outline.md
```

**Then create**: `src/specify_cli/missions/plan/templates/research-outline.md`

### No Artificial Templates

Do NOT create templates without explicit references.
- Avoid generic helpers ("common-structure.md", "template-template.md")
- Keep templates mission-specific and focused
- Only create when solving a real referencing problem

---

## Examples

### Minimal Valid Template

```markdown
---
step_id: "specify"
mission: "plan"
title: "Specify"
description: "Create feature specification"
---

# Specify

## Context

You are creating the initial feature specification.

## Deliverables

- spec.md with requirements

## Instructions

1. Define feature goals
2. List requirements
3. Document assumptions

## Success Criteria

- spec.md is complete
- All requirements are testable
- Assumptions are documented
```

### Complete Template with References

```markdown
---
step_id: "research"
mission: "plan"
title: "Research"
description: "Research technical aspects"
estimated_duration: "20-30 minutes"
---

# Research

## Context

You are investigating technical requirements and design patterns for this feature.

**Input**: Feature specification from the Specify step
**Output**: research.md with findings and recommendations

## Deliverables

- research.md (Markdown document)
  - Technical Analysis (2-3 sections)
  - Design Patterns (3-5 patterns)
  - Dependencies (5-10 items)
  - Risks & Mitigations (3-5 items)
  - Recommendations (2-3 actionable items)

## Instructions

Use the research outline template below to structure your findings:

See: ../templates/research-outline.md

Then:
1. Analyze technical requirements
2. Research applicable design patterns
3. Identify key dependencies
4. Surface potential risks
5. Compile recommendations

## Success Criteria

- [ ] research.md follows the outline structure
- [ ] All sections are completed
- [ ] Recommendations are specific and actionable
- [ ] No broken links or references

## References

- Specification: ../spec.md
- Data Model: ../data-model.md
```

---

## References

- Feature Spec: [../spec.md](../spec.md)
- Data Model: [../data-model.md](../data-model.md)
- Implementation Plan: [../plan.md](../plan.md)
- Quick Start: [../quickstart.md](../quickstart.md)
