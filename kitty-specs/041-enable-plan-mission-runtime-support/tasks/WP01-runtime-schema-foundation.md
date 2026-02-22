---
work_package_id: WP01
title: Runtime Schema Foundation
lane: "done"
dependencies: []
base_branch: 2.x
base_commit: 7605f1577bdaa18cc2ab61c4f0fd5ba28fc1ae4c
created_at: '2026-02-22T08:12:56.105802+00:00'
subtasks: [T001, T002, T003, T016]
description: Create the runtime schema that enables plan mission discovery in the runtime loop
estimated_duration: 1-2 hours
priority: P0
shell_pid: "92995"
agent: "codex"
reviewed_by: "Robert Douglass"
review_status: "approved"
---

# WP01: Runtime Schema Foundation

**Objective**: Create the runtime schema (mission-runtime.yaml) that enables the runtime bridge to discover and load the plan mission, unblocking the `spec-kitty next` command.

**Context**: The plan mission currently exists for the planning workflow, but lacks a runtime definition. When users try to use `spec-kitty next --feature <plan-feature>`, the runtime bridge fails because it cannot find the plan mission's runtime schema. This work package creates that foundation.

**Key Success Criterion**: After completion, `spec-kitty next --feature <plan-feature> --agent codex --json` must return a non-blocked status (step, decision_required, or terminal) instead of "Mission 'plan' not found".

**Included Files**:
- `src/specify_cli/missions/plan/mission-runtime.yaml` (create)
- `src/specify_cli/missions/plan/command-templates/` (create directory)
- `src/specify_cli/missions/plan/templates/` (create directory)

---

## Subtask Breakdown

### Subtask T001: Study Existing Patterns
**Duration**: 20-30 minutes
**Goal**: Understand the mission runtime schema by examining successful examples.

**Steps**:

1. **Examine software-dev mission runtime**:
   ```bash
   cat src/specify_cli/missions/software-dev/mission-runtime.yaml
   ```
   Capture:
   - mission.key structure
   - steps array format
   - step dependencies
   - runtime configuration (loop_type, step_transition, terminal_step)

2. **Examine research mission runtime** (if exists):
   ```bash
   cat src/specify_cli/missions/research/mission-runtime.yaml
   ```
   Compare with software-dev to understand variations.

3. **Document the schema pattern**:
   - Minimum 4 steps (plan has 4: specify, research, plan, review)
   - Each step has: id, name, description, order, depends_on
   - Runtime config has: loop_type (sequential), step_transition (manual), prompt_template_dir, terminal_step
   - Dependencies form linear chain (no cycles)

4. **Review runtime bridge expectations** (reference from spec):
   - `src/specify_cli/next/runtime_bridge.py` lines 214, 244, 302
   - Runtime expects: mission.key, steps array, terminal_step
   - Resolver expects: prompt_template_dir for finding templates

**Success Criteria**:
- [ ] mission-runtime.yaml structure understood
- [ ] Step schema documented (ids, names, orders, dependencies)
- [ ] Runtime configuration options confirmed
- [ ] Ready to create plan mission schema

---

### Subtask T002: Create mission-runtime.yaml
**Duration**: 30-45 minutes
**Goal**: Create the mission-runtime.yaml file for the plan mission.

**File Path**: `src/specify_cli/missions/plan/mission-runtime.yaml`

**Content Template** (adapt from software-dev/research patterns):

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
      depends_on: []

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
    loop_type: "sequential"
    step_transition: "manual"
    prompt_template_dir: "command-templates"
    terminal_step: "review"
```

**Steps**:

1. **Create the file**:
   ```bash
   touch src/specify_cli/missions/plan/mission-runtime.yaml
   ```

2. **Write the schema**:
   - Use the template above as starting point
   - Ensure 4 steps: specify → research → plan → review
   - Each step has order 1-4
   - Dependencies form linear chain (specify has no deps, each subsequent depends on previous)
   - Runtime config: sequential loop, manual transitions, templates in "command-templates" dir

3. **Validate YAML syntax**:
   ```bash
   python -c "import yaml; yaml.safe_load(open('src/specify_cli/missions/plan/mission-runtime.yaml'))"
   ```
   Should produce no errors.

4. **Verify completeness**:
   - [ ] mission.key == "plan"
   - [ ] 4 steps present
   - [ ] Each step has id, name, description, order
   - [ ] Step orders are 1, 2, 3, 4
   - [ ] Step IDs match: specify, research, plan, review
   - [ ] Dependencies form chain: [] → [specify] → [research] → [plan]
   - [ ] runtime.terminal_step == "review"

**Success Criteria**:
- [ ] File created at correct path
- [ ] YAML parses without errors
- [ ] Schema matches software-dev pattern
- [ ] All 4 steps defined with correct sequence
- [ ] Dependencies form linear chain with no cycles

---

### Subtask T003: Validate Against Runtime Bridge
**Duration**: 15-20 minutes
**Goal**: Ensure the schema will work with the existing runtime bridge.

**Validation Checklist**:

1. **Check mission discovery** (runtime_bridge.py line 214):
   - Will the bridge find and load `mission-runtime.yaml`?
   - Verify: mission.key exists and equals "plan"
   - Verify: mission object has "steps" key (array)
   - Verify: mission object has "runtime" key (object)

2. **Check step sequence** (runtime_bridge.py line 244):
   - Will the bridge correctly sequence the 4 steps?
   - Verify: steps array has exactly 4 items
   - Verify: each step has "id" and "order" fields
   - Verify: orders are sequential (1, 2, 3, 4)
   - Verify: terminal_step field points to last step ("review")

3. **Check template resolution** (runtime_bridge.py line 302):
   - Will the bridge correctly resolve templates?
   - Verify: runtime.prompt_template_dir == "command-templates"
   - Verify: this directory will be created in T016
   - Expected resolver path: `src/specify_cli/missions/plan/command-templates/{step_id}.md`

4. **Dry-run validation** (if possible):
   ```bash
   python -c "
   import yaml
   from pathlib import Path

   schema = yaml.safe_load(Path('src/specify_cli/missions/plan/mission-runtime.yaml').read_text())

   # Check mission structure
   assert schema['mission']['key'] == 'plan'
   assert len(schema['mission']['steps']) == 4
   assert schema['mission']['runtime']['terminal_step'] == 'review'

   # Check steps
   steps = {s['id']: s for s in schema['mission']['steps']}
   assert set(steps.keys()) == {'specify', 'research', 'plan', 'review'}
   for order, step_id in enumerate(['specify', 'research', 'plan', 'review'], 1):
       assert steps[step_id]['order'] == order

   print('✓ Schema validates successfully')
   "
   ```

**Success Criteria**:
- [ ] Schema loads without errors
- [ ] mission.key == "plan"
- [ ] 4 steps present with correct order
- [ ] Dependencies form linear chain
- [ ] terminal_step == "review"
- [ ] prompt_template_dir is "command-templates"
- [ ] Ready for runtime bridge consumption

---

### Subtask T016: Create Directory Structure
**Duration**: 5-10 minutes
**Goal**: Create the directories needed for command templates and content templates.

**Directories to Create**:
1. `src/specify_cli/missions/plan/command-templates/` - For the 4 step command templates
2. `src/specify_cli/missions/plan/templates/` - For any referenced content templates

**Steps**:

1. **Create command-templates directory**:
   ```bash
   mkdir -p src/specify_cli/missions/plan/command-templates
   ```

2. **Create templates directory**:
   ```bash
   mkdir -p src/specify_cli/missions/plan/templates
   ```

3. **Create placeholder files** (to ensure directories are tracked by git):
   ```bash
   touch src/specify_cli/missions/plan/command-templates/.gitkeep
   touch src/specify_cli/missions/plan/templates/.gitkeep
   ```

4. **Verify structure**:
   ```bash
   tree src/specify_cli/missions/plan/
   # Expected:
   # src/specify_cli/missions/plan/
   # ├── mission.yaml
   # ├── mission-runtime.yaml (NEW)
   # ├── command-templates (NEW)
   # │   └── .gitkeep
   # └── templates (NEW)
   #     └── .gitkeep
   ```

**Success Criteria**:
- [ ] Both directories created
- [ ] Directories are empty (except for .gitkeep)
- [ ] Ready for WP02 (templates) and WP03 (content)

---

## Test Strategy

**No unit tests required for this WP** - Runtime schema validation is simple YAML parsing. Functional validation happens in WP04.

**Manual validation checks**:
- [ ] YAML parses successfully
- [ ] Schema matches reference missions (software-dev, research)
- [ ] All required fields present
- [ ] Step sequence is correct
- [ ] Directories exist and are empty

**Integration validation** (WP04):
- Runtime bridge can discover plan mission
- All 4 steps are accessible via resolver
- No "Mission 'plan' not found" error

---

## Definition of Done

- [x] mission-runtime.yaml created at `src/specify_cli/missions/plan/mission-runtime.yaml`
- [x] Schema contains 4-step linear sequence (specify → research → plan → review)
- [x] Each step has correct order (1-4) and dependencies
- [x] terminal_step == "review"
- [x] prompt_template_dir == "command-templates"
- [x] YAML syntax validates (no parse errors)
- [x] `command-templates/` directory created and empty
- [x] `templates/` directory created and empty
- [x] .gitkeep files added to both directories
- [x] All files tracked by git

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Schema incompatible with runtime bridge | HIGH | Follow software-dev pattern exactly; test parsing |
| Circular dependencies in steps | HIGH | Validate chain: [] → [specify] → [research] → [plan] |
| Missing required fields | MEDIUM | Checklist in T002 and T003 validation |
| Directory creation permissions | LOW | Use standard mkdir with -p flag |

---

## Reviewer Guidance

**What to Check**:
1. Does mission-runtime.yaml match the software-dev/research pattern?
2. Are all 4 steps present with correct sequence?
3. Do step dependencies form a linear chain (no cycles)?
4. Is terminal_step set to "review"?
5. Do directories exist and will WP02 be able to create templates there?

**Green Light**: Schema is valid YAML, follows established patterns, and will support the next work package (command templates).

**Red Light**: Schema doesn't match reference missions, has invalid step order, has circular dependencies, or missing key fields.

---

## Next Work Package

WP02 will create the 4 command templates (specify.md, research.md, plan.md, review.md) in the `command-templates/` directory created by this WP.

Implementation command after setup:
```bash
spec-kitty implement WP01
```

After completion:
```bash
spec-kitty implement WP02 --base WP01
```

## Activity Log

- 2026-02-22T08:12:56Z – claude – shell_pid=90107 – lane=doing – Assigned agent via workflow command
- 2026-02-22T08:15:16Z – claude – shell_pid=90107 – lane=for_review – WP01 implementation complete: Runtime schema foundation with mission-runtime.yaml and directory structure ready for command template creation
- 2026-02-22T08:15:24Z – codex – shell_pid=92995 – lane=doing – Started review via workflow command
- 2026-02-22T08:17:37Z – codex – shell_pid=92995 – lane=for_review – Runtime schema foundation complete: mission-runtime.yaml created with 4-step schema
- 2026-02-22T08:20:53Z – codex – shell_pid=92995 – lane=done – All acceptance criteria verified: mission-runtime.yaml schema complete with 4-step linear workflow, correct dependencies, runtime configuration, and directory structure ready for WP02
