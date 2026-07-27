# Data Model: Plan Mission Runtime Support

**Feature**: 041-enable-plan-mission-runtime-support
**Purpose**: Define runtime schema, command template structure, and test data model for plan mission

---

## Mission Runtime Schema

### mission-runtime.yaml Structure

**File**: `src/specify_cli/missions/plan/mission-runtime.yaml`

**Schema**:
```yaml
mission:
  key: "plan"
  title: "Planning Mission"
  description: "Plan and design software features through structured phases"

  steps:
    - id: "specify"
      name: "Specify"
      description: "Prepare and specify the feature definition"
      order: 1

    - id: "research"
      name: "Research"
      description: "Gather research inputs and technical context"
      order: 2
      depends_on: ["specify"]

    - id: "plan"
      name: "Plan"
      description: "Design and create planning artifacts"
      order: 3
      depends_on: ["research"]

    - id: "review"
      name: "Review"
      description: "Review and validate planning artifacts"
      order: 4
      depends_on: ["plan"]

  runtime:
    loop_type: "sequential"              # Linear step progression
    step_transition: "manual"            # User must call 'next' to advance
    prompt_template_dir: "command-templates"
    terminal_step: "review"              # Final step
```

**Key Semantics**:
- **4 Steps**: specify → research → plan → review (linear progression)
- **Dependencies**: Each step depends on successful completion of previous step
- **No Parallel Steps**: Sequential execution (unlike some mission workflows)
- **Terminal Step**: "review" is the final step
- **Loop Type**: Simple sequential progression

---

## Command Template Structure

### Command Template File Format

**Location**: `src/specify_cli/missions/plan/command-templates/{step_id}.md`

**Files to Create**:
1. `specify.md` - Step 1: Entry point, feature definition preparation
2. `research.md` - Step 2: Research gathering and context assembly
3. `plan.md` - Step 3: Design and planning artifacts creation
4. `review.md` - Step 4: Final review and validation

### Template Structure

Each command template follows this structure:

```markdown
---
step_id: "{step_id}"
mission: "plan"
title: "{Step Title}"
description: "{Step Description}"
estimated_duration: "{duration}"
---

# {Step Title}

## Context

[Context for this step, what should be done]

## Deliverables

- [Deliverable 1]
- [Deliverable 2]

## Instructions

[Step-by-step instructions or prompts for the agent]

## Success Criteria

- [Criteria 1]
- [Criteria 2]

## References

[Links to related documentation if needed]
```

### Specific Template Semantics

**Step 1: specify.md**
- **Purpose**: Entry point; prepare feature definition
- **Input**: Feature specification request from user
- **Output**: Feature spec outline, user scenarios
- **Agent Task**: Create initial specification for the feature
- **Success**: Feature definition document with clear requirements

**Step 2: research.md**
- **Purpose**: Gather research inputs and context
- **Input**: Feature spec from step 1
- **Output**: Research findings, technical analysis, patterns
- **Agent Task**: Investigate technical requirements, design patterns, dependencies
- **Success**: Research document with analysis and recommendations

**Step 3: plan.md**
- **Purpose**: Design and planning artifacts
- **Input**: Research findings from step 2
- **Output**: Architecture design, data model, API contracts
- **Agent Task**: Create technical design artifacts
- **Success**: Complete design documentation ready for implementation

**Step 4: review.md**
- **Purpose**: Review and validate all artifacts
- **Input**: Design artifacts from step 3
- **Output**: Validation report, approved design
- **Agent Task**: Review and validate completeness and consistency
- **Success**: All artifacts validated and approved

---

## Content Template Structure (Conditional)

### Decision Logic

Content templates are created ONLY if referenced by command templates.

**Pattern**: If a command template includes:
```markdown
See: ../templates/research-outline.md
```

Then create: `src/specify_cli/missions/plan/templates/research-outline.md`

**No Artificial Templates**: Do not create content templates without explicit references.

### Potential Content Templates

Based on command template analysis:

**research-outline.md** (if referenced by research.md)
- Template outline for research document structure
- Sections: Background, Technical Analysis, Design Patterns, Dependencies
- Reusable structure for step 2

**design-checklist.md** (if referenced by plan.md)
- Checklist for design validation
- Items: Architecture, Data Model, APIs, Testing, Security
- Used during step 3

**validation-rubric.md** (if referenced by review.md)
- Rubric for artifact validation
- Criteria: Completeness, Consistency, Feasibility
- Used during step 4

---

## Test Data Model

### Integration Test Data

**Feature Creation (Setup)**:
```json
{
  "slug": "test-plan-feature",
  "mission": "plan",
  "description": "Test feature for plan mission runtime verification"
}
```

**Expected Feature State**:
- Feature directory: `kitty-specs/NNN-test-plan-feature/`
- Meta file: Contains `mission: "plan"`
- Spec file: Created and valid

### Command Resolution Test Data

**Resolver Test Cases**:

| Step | Input | Expected Output | Validation |
|------|-------|-----------------|-----------|
| specify | mission="plan", step="specify" | Valid specify.md template | File exists, resolves without errors |
| research | mission="plan", step="research" | Valid research.md template | File exists, resolves without errors |
| plan | mission="plan", step="plan" | Valid plan.md template | File exists, resolves without errors |
| review | mission="plan", step="review" | Valid review.md template | File exists, resolves without errors |

### Regression Test Data

**Existing Mission Verification**:

| Mission | Test Scenario | Expected Result |
|---------|---------------|-----------------|
| software-dev | Resolve software-dev steps (research → design → implement → test → review) | All steps resolve correctly |
| research | Resolve research steps (question → methodology → gather → analyze → synthesize → publish) | All steps resolve correctly |

---

## Runtime Bridge Integration Points

### Discovery (runtime_bridge.py, line 214)

**Trigger**: Feature has `mission="plan"`

**Process**:
1. Runtime bridge calls: `discover_mission("plan")`
2. Bridge looks for: `src/specify_cli/missions/plan/mission-runtime.yaml`
3. Expected: YAML loads successfully with proper schema

**Data**:
- Input: Feature slug
- Output: Mission definition (steps, prompt_template_dir)
- Error Handling: "Mission 'plan' not found" if YAML missing

### Template Resolution (runtime_bridge.py, line 244)

**Trigger**: Step progression (step 1 → step 2 → step 3 → step 4)

**Process**:
1. Runtime bridge calls: `resolve_command(mission="plan", step=current_step)`
2. Bridge looks for: `src/specify_cli/missions/plan/command-templates/{step_id}.md`
3. Expected: Template loads and resolves fully

**Data**:
- Input: mission key, step id
- Output: Resolved command template (context + prompt)
- Error Handling: Missing file errors if template not found

### Execution (runtime_bridge.py, line 302)

**Trigger**: Agent executes command for current step

**Process**:
1. Runtime passes resolved template to agent
2. Agent executes and produces output
3. Runtime transitions to next step (or terminal if final step)

**Data**:
- Input: Resolved template
- Output: Agent response (artifact created)
- State: Feature progresses through lane transitions

---

## Key Entities & Relationships

### Feature Entity

```
Feature (existing, extended with mission field)
├── slug: "041-..."
├── mission: "plan"  ← NEW: now plan-compatible
├── meta.json
│   └── mission: "plan"
└── artifacts/
    ├── spec.md
    ├── research.md (generated during step 2)
    ├── data-model.md (generated during step 3)
    └── contracts/ (generated during step 3)
```

### Step Entity

```
Step (runtime concept)
├── id: "specify" | "research" | "plan" | "review"
├── order: 1-4
├── depends_on: [previous_step_id] (or [])
└── template: command-templates/{step_id}.md
```

### Template Entity

```
Template (Markdown file)
├── Frontmatter (YAML):
│   ├── step_id
│   ├── mission
│   ├── title
│   └── description
└── Body (Markdown):
    ├── Context
    ├── Deliverables
    ├── Instructions
    ├── Success Criteria
    └── References
```

---

## Validation Rules

### mission-runtime.yaml Validation

- [ ] `mission.key` = "plan"
- [ ] `steps` array has exactly 4 items
- [ ] Steps are ordered: specify (1), research (2), plan (3), review (4)
- [ ] Each step has `id`, `name`, `order`
- [ ] Dependencies form a linear chain (no cycles, no gaps)
- [ ] `runtime.terminal_step` = "review"

### Command Template Validation

- [ ] File exists: `command-templates/{step_id}.md`
- [ ] YAML frontmatter parses correctly
- [ ] Required fields: `step_id`, `mission`, `title`
- [ ] Body sections present: Context, Deliverables, Instructions, Success Criteria
- [ ] No broken references to content templates
- [ ] No doctrine path references (2.x-safe paths only)

### Content Template Validation

- [ ] File exists if referenced by command templates
- [ ] Content is plan-specific (no generic helpers)
- [ ] No external service dependencies
- [ ] 2.x-compatible paths only

---

## State Transitions

### Feature Progression Through Plan Mission

```
Feature Created (mission=plan)
    ↓
Step 1: specify
    └─ Output: spec.md or similar
    ↓
Step 2: research
    └─ Output: research.md or similar
    ↓
Step 3: plan
    └─ Output: data-model.md, contracts/, etc.
    ↓
Step 4: review
    └─ Output: validation report
    ↓
Feature Planning Complete
```

### Runtime Loop State Machine

```
IDLE
  ↓ (feature created with mission=plan)
STEP_1_SPECIFY
  ↓ (agent completes spec, user calls next)
STEP_2_RESEARCH
  ↓ (agent completes research, user calls next)
STEP_3_PLAN
  ↓ (agent completes design, user calls next)
STEP_4_REVIEW
  ↓ (agent completes review, user calls next)
TERMINAL (Planning complete, ready for tasks.md)
```

---

## File Inventory

| File | Purpose | Status |
|------|---------|--------|
| `mission-runtime.yaml` | Runtime schema for plan mission | TO CREATE |
| `command-templates/specify.md` | Specify step template | TO CREATE |
| `command-templates/research.md` | Research step template | TO CREATE |
| `command-templates/plan.md` | Plan step template | TO CREATE |
| `command-templates/review.md` | Review step template | TO CREATE |
| `templates/research-outline.md` | Research outline template (if referenced) | CONDITIONAL |
| `templates/design-checklist.md` | Design checklist (if referenced) | CONDITIONAL |
| `templates/validation-rubric.md` | Validation rubric (if referenced) | CONDITIONAL |
| `test_plan_mission_runtime.py` | Tests for plan mission | TO CREATE |

---

## Summary

The plan mission runtime support requires:

1. **Schema Definition** (mission-runtime.yaml): 4-step linear workflow (specify → research → plan → review)
2. **Command Templates**: 4 Markdown files with context and prompts for each step
3. **Content Templates**: Created only if referenced by command templates
4. **Test Coverage**: Integration (feature creation + next progression) + resolver tests (4 step resolutions) + regression tests (other missions)

All artifacts maintain 2.x compatibility with no doctrine path migrations.
