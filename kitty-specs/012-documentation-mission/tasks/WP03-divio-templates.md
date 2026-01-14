---
work_package_id: "WP03"
subtasks:
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
title: "Divio Documentation Templates"
phase: "Phase 0 - Foundation"
lane: "doing"
assignee: ""
agent: "test"
shell_pid: "71983"
review_status: ""
reviewed_by: ""
dependencies:
  - "WP01"
history:
  - timestamp: "2026-01-12T17:18:56Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Divio Documentation Templates

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

## ⚠️ Dependency Rebase Guidance

**This WP depends on**: WP01 (Mission Infrastructure)

**Before starting work**:
1. Ensure WP01 is complete
2. Mission directory exists: `src/specify_cli/missions/documentation/`
3. Templates directory exists: `src/specify_cli/missions/documentation/templates/`

---

## Objectives & Success Criteria

**Goal**: Create the four Divio documentation type templates (tutorial, how-to, reference, explanation) with comprehensive guidance following Write the Docs best practices and Divio principles.

**Success Criteria**:
- Four template files created in `templates/divio/` subdirectory
- Each template has YAML frontmatter with `type` field
- Each template has section structure appropriate to its Divio type
- Templates include Write the Docs guidance (accessibility, bias-free language, clear structure)
- Templates have placeholders for project-specific content
- Each template clearly explains its purpose and when to use it
- Templates load successfully via `Mission.get_template()`
- Templates enable users to create high-quality documentation without prior Divio knowledge

## Context & Constraints

**Prerequisites**:
- WP01 complete: Mission directory structure exists
- Understanding of Divio documentation system from research

**Reference Documents**:
- [research.md](../research.md) - Divio documentation types (lines 87-210)
  - Tutorial research (lines 87-105)
  - How-to research (lines 107-125)
  - Reference research (lines 127-145)
  - Explanation research (lines 147-165)
- [data-model.md](../data-model.md) - Divio Documentation Type entity (lines 93-157)
- [spec.md](../spec.md) - Divio requirements (FR-010 to FR-017, lines 114-122)
- External references:
  - [Divio Tutorial Guide](https://docs.divio.com/documentation-system/tutorials/)
  - [Divio How-To Guide](https://docs.divio.com/documentation-system/how-to-guides/)
  - [Divio Reference Guide](https://docs.divio.com/documentation-system/reference/)
  - [Divio Explanation Guide](https://docs.divio.com/documentation-system/explanation/)
  - [Write the Docs Style Guide](https://www.writethedocs.org/guide/writing/style-guides/)

**Constraints**:
- Must follow Divio principles exactly (don't mix types)
- Must include accessibility guidance
- Must encourage bias-free language
- Templates should be usable without reading external Divio docs

**Divio Type Characteristics** (from research):

| Type | Orientation | Audience | Approach | Outcome |
|------|-------------|----------|----------|---------|
| Tutorial | Learning | Beginners | Step-by-step | Can do something |
| How-To | Goal | Experienced | Problem-solving | Solve specific problem |
| Reference | Information | All | Technical description | Know what exists |
| Explanation | Understanding | Curious | Conceptual discussion | Understand why/how |

## Subtasks & Detailed Guidance

### Subtask T012 – Create divio/ Subdirectory

**Purpose**: Create the subdirectory to organize Divio type templates separately from core mission templates.

**Steps**:
1. Create `src/specify_cli/missions/documentation/templates/divio/` directory
2. Add `.gitkeep` if needed (though templates will be added immediately)
3. Verify directory structure:
   ```
   src/specify_cli/missions/documentation/
   └── templates/
       ├── spec-template.md
       ├── plan-template.md
       ├── tasks-template.md
       ├── task-prompt-template.md
       └── divio/               # NEW
           ├── tutorial-template.md
           ├── howto-template.md
           ├── reference-template.md
           └── explanation-template.md
   ```

**Files**: `src/specify_cli/missions/documentation/templates/divio/` (new directory)

**Parallel?**: Yes (can proceed immediately alongside template creation)

**Notes**: Simple directory creation; other subtasks create files in this directory.

### Subtask T013 – Create tutorial-template.md

**Purpose**: Create template for learning-oriented tutorial documentation following Divio tutorial principles.

**Divio Tutorial Principles** (from research):
- **Learning-oriented**: Focused on enabling the learner to do something
- **Step-by-step**: Sequential actions leading to concrete accomplishment
- **For beginners**: Assume minimal prior knowledge
- **Immediately rewarding**: Each step shows visible result
- **Minimize explanations**: Do over learn, teach actions not concepts
- **Reliable**: Must work for all users following instructions

**Steps**:
1. Create `src/specify_cli/missions/documentation/templates/divio/tutorial-template.md`
2. Add YAML frontmatter:
   ```yaml
   ---
   type: tutorial
   audience: "{target_audience}"
   purpose: "Learn how to {goal}"
   created: "{date}"
   estimated_time: "{duration}"
   prerequisites: "{required_knowledge}"
   ---
   ```
3. Add template structure:
   ```markdown
   # Tutorial: {Title}

   > **What you'll build**: [Describe the concrete outcome - what learners will have accomplished by the end]
   >
   > **Estimated time**: {duration} minutes
   >
   > **Prerequisites**: [Minimal requirements - software installed, basic knowledge]

   ## What You'll Learn

   By the end of this tutorial, you will:
   - [Specific skill or capability 1]
   - [Specific skill or capability 2]
   - [Specific skill or capability 3]

   ## Before You Begin

   Make sure you have:
   - [ ] [Required tool/software installed]
   - [ ] [Basic knowledge/skill]
   - [ ] [Required access/permissions]

   ## Step 1: {First Action}

   > **Goal**: [What learner accomplishes in this step]

   [Clear, explicit instructions]

   ```bash
   # Exact command to run
   command --with-flags argument
   ```

   **You should see**:
   ```
   [Expected output]
   ```

   ✓ **Checkpoint**: You now have [concrete accomplishment].

   ## Step 2: {Next Action}

   > **Goal**: [What learner accomplishes in this step]

   [Continue with same structure...]

   ## Step 3: {Another Action}

   [Repeat...]

   ## What You've Accomplished

   Congratulations! You've now:
   - ✓ [Specific achievement 1]
   - ✓ [Specific achievement 2]
   - ✓ [Specific achievement 3]

   ## Next Steps

   Now that you can {capability}, you might want to:
   - [Link to related tutorial]
   - [Link to how-to guide for specific problem]
   - [Link to reference for details]
   - [Link to explanation for understanding why]

   ## Troubleshooting

   ### Problem: {Common issue}

   **Symptoms**: [What user sees]
   **Solution**: [How to fix it]

   ### Problem: {Another common issue}

   **Symptoms**: [What user sees]
   **Solution**: [How to fix it]

   ---

   ## Writing Guide for Tutorial Authors

   **✓ DO**:
   - Focus on enabling doing, not explaining concepts
   - Provide exact commands and expected outputs
   - Show immediate results after each step
   - Use encouraging language ("Great!", "Well done!")
   - Test tutorial with someone unfamiliar with the topic
   - Keep explanations minimal (link to explanation docs instead)

   **✗ DON'T**:
   - Explain how things work (save for explanation docs)
   - Assume prior knowledge beyond prerequisites
   - Skip steps or say "obviously" or "simply"
   - Give options or alternatives (one path only)
   - Include tangential information or advanced features

   **Accessibility Checklist**:
   - [ ] Proper heading hierarchy (one H1, H2 for steps)
   - [ ] Code blocks have language tags
   - [ ] Screenshots have alt text describing what they show
   - [ ] Clear, plain language (avoid jargon or define it)

   **Inclusivity Checklist**:
   - [ ] Examples use diverse names
   - [ ] Gender-neutral language
   - [ ] No cultural assumptions
   - [ ] Welcoming tone for newcomers
   ```

**Files**: `src/specify_cli/missions/documentation/templates/divio/tutorial-template.md` (new file)

**Parallel?**: Yes (can be created alongside other Divio templates)

**Notes**:
- Tutorial is about "doing to learn", not "learning about"
- Each step must show immediate, visible result
- Keep it simple - one path through, no branches
- Test with actual beginners before finalizing

**Quality Validation**:
- Have a beginner follow the tutorial - can they complete it?
- Does every step show a result?
- Are explanations minimal?
- Is the outcome concrete and valuable?

### Subtask T014 – Create howto-template.md

**Purpose**: Create template for goal-oriented how-to guide documentation following Divio how-to principles.

**Divio How-To Principles** (from research):
- **Goal-oriented**: Solve a specific, practical problem
- **For experienced users**: Assume basic familiarity with the system
- **Problem-solving format**: Recipe for achieving an outcome
- **Flexible**: Readers adapt to their specific situation
- **Minimal explanation**: Steps not why (link to explanations)
- **Action-focused**: Sequence of operations leading to result

**Steps**:
1. Create `src/specify_cli/missions/documentation/templates/divio/howto-template.md`
2. Add YAML frontmatter:
   ```yaml
   ---
   type: how-to
   audience: "{target_audience}"
   purpose: "How to {solve_problem}"
   created: "{date}"
   problem: "{problem_description}"
   solution_summary: "{quick_summary}"
   ---
   ```
3. Add template structure:
   ```markdown
   # How to {Accomplish Goal}

   > **Problem**: [What specific problem does this solve?]
   >
   > **Solution**: [One-sentence summary of the approach]
   >
   > **When to use this**: [Scenarios where this guide applies]

   ## Prerequisites

   Before following this guide, you should:
   - [ ] [Required knowledge or experience]
   - [ ] [Required access or permissions]
   - [ ] [Required tools or setup]

   ## Overview

   To {accomplish goal}, you will:
   1. [High-level step 1]
   2. [High-level step 2]
   3. [High-level step 3]

   ## Steps

   ### 1. {First Action}

   [Actionable instructions]

   ```bash
   # Command or code example
   command --option value
   ```

   **Result**: [What you achieve with this step]

   ### 2. {Next Action}

   [Continue with actionable instructions...]

   ### 3. {Another Action}

   [Additional steps as needed...]

   ## Verification

   To confirm it worked:
   1. [Check or test to perform]
   2. [Expected outcome]

   ## Common Variations

   ### Variation: {Different Scenario}

   If you need to {alternative goal}:
   - [Modified approach]
   - [Different command/configuration]

   ### Variation: {Another Scenario}

   [Another common variation...]

   ## Troubleshooting

   ### Issue: {Common problem}

   **Symptoms**: [What you see]
   **Cause**: [Why it happens]
   **Solution**: [How to fix]

   ## Related

   - **Tutorial**: [Link to getting-started tutorial if user is new]
   - **Reference**: [Link to relevant API/config reference]
   - **Explanation**: [Link to explanation of why this approach works]
   - **Other How-Tos**: [Related problem-solving guides]

   ---

   ## Writing Guide for How-To Authors

   **✓ DO**:
   - Focus on solving a specific problem
   - Assume reader knows the basics
   - Provide clear, numbered steps
   - Allow for flexibility and adaptation
   - Include common variations
   - Link to reference for technical details
   - Link to explanation for "why"

   **✗ DON'T**:
   - Teach basics (that's for tutorials)
   - Explain concepts in depth (that's for explanations)
   - List every possible option (that's for reference)
   - Make it too rigid (readers need to adapt)

   **Structure Check**:
   - [ ] Title starts with "How to..."
   - [ ] Problem statement is clear
   - [ ] Prerequisites are realistic (not everything)
   - [ ] Steps are actionable and concise
   - [ ] Common variations are included
   - [ ] Links to related docs (tutorial, reference, explanation)

   **Accessibility Checklist**:
   - [ ] Proper heading hierarchy
   - [ ] Code blocks have language tags
   - [ ] Screenshots have alt text
   - [ ] Clear, professional language

   **Inclusivity Checklist**:
   - [ ] Examples use diverse names
   - [ ] Gender-neutral language
   - [ ] No assumptions about reader's context
   ```

**Files**: `src/specify_cli/missions/documentation/templates/divio/howto-template.md` (new file)

**Parallel?**: Yes (can be created alongside other Divio templates)

**Notes**:
- How-to is NOT a tutorial (not for beginners)
- Reader is solving a specific problem, not learning
- Allow flexibility - readers adapt to their situation
- Link to reference for details, explanation for understanding

**Quality Validation**:
- Does it solve a specific, real-world problem?
- Can experienced users follow it without hand-holding?
- Are variations included for common scenarios?
- Is explanation kept minimal with links to explanation docs?

### Subtask T015 – Create reference-template.md

**Purpose**: Create template for information-oriented reference documentation following Divio reference principles.

**Divio Reference Principles** (from research):
- **Information-oriented**: Technical description of what exists
- **For all users**: Developers, operators, anyone needing details
- **Structured around code**: Mirrors code organization
- **Complete and accurate**: All public APIs, all options, all details
- **Consistent format**: Every entry follows same structure
- **Includes examples**: Show usage, not explanation

**Steps**:
1. Create `src/specify_cli/missions/documentation/templates/divio/reference-template.md`
2. Add YAML frontmatter:
   ```yaml
   ---
   type: reference
   audience: "all users"
   purpose: "Technical specifications for {component}"
   created: "{date}"
   component: "{api_module_cli}"
   auto_generated: "{true_if_generated_from_code}"
   ---
   ```
3. Add template structure (with sections for both manual and auto-generated reference):
   ```markdown
   # Reference: {Component Name}

   > **Type**: [API | CLI | Configuration | Data Format]
   >
   > **Status**: [Stable | Beta | Deprecated]
   >
   > **Source**: [Auto-generated from code | Manual]

   ## Overview

   [Brief description of what this component is - no explanation of why or how to use it, just what it is]

   ## API Reference (for auto-generated API docs)

   > **Note**: This section is auto-generated from code comments using [JSDoc | Sphinx | rustdoc].
   > To update, modify the source code comments and regenerate.

   [Auto-generated content appears here]

   ## CLI Reference (for command-line tools)

   ### Command: `command-name`

   **Synopsis**:
   ```bash
   command-name [options] <arguments>
   ```

   **Description**:
   [What this command does - factual description, no usage advice]

   **Options**:

   | Option | Type | Default | Description |
   |--------|------|---------|-------------|
   | `--flag` | boolean | false | [What this flag does] |
   | `--option` | string | none | [What this option controls] |
   | `--value` | number | 0 | [What this value sets] |

   **Arguments**:

   | Argument | Type | Required | Description |
   |----------|------|----------|-------------|
   | `<name>` | string | yes | [What this argument is] |
   | `<path>` | path | no | [What this argument specifies] |

   **Examples**:

   ```bash
   # Basic usage
   command-name --flag value

   # Advanced usage
   command-name --option=custom --value=100 name
   ```

   **Exit Codes**:

   | Code | Meaning |
   |------|---------|
   | 0 | Success |
   | 1 | General error |
   | 2 | Invalid argument |

   ### Command: `another-command`

   [Repeat structure for each command...]

   ## Configuration Reference (for config files)

   ### File: `config.yaml`

   **Location**: `~/.config/app/config.yaml`

   **Format**: YAML

   **Schema**:

   ```yaml
   # Top-level configuration
   setting_name: value          # Type: string, Default: "default", Description: [what it does]
   another_setting: 123         # Type: integer, Default: 0, Description: [what it controls]

   section_name:
     nested_setting: true       # Type: boolean, Default: false, Description: [what it enables]
     list_setting:              # Type: array of strings, Description: [what items represent]
       - item1
       - item2
   ```

   **Settings**:

   #### `setting_name`

   - **Type**: string
   - **Default**: `"default"`
   - **Valid values**: [list or pattern]
   - **Description**: [Technical description of what this setting controls]

   **Example**:
   ```yaml
   setting_name: "custom_value"
   ```

   #### `another_setting`

   [Repeat for each setting...]

   ## Data Format Reference (for data structures)

   ### Structure: `ObjectName`

   **Fields**:

   | Field | Type | Required | Description |
   |-------|------|----------|-------------|
   | `id` | string | yes | [What this field represents] |
   | `name` | string | yes | [What this field stores] |
   | `metadata` | object | no | [What this field contains] |

   **Constraints**:
   - `id` must be unique
   - `name` must match pattern: `^[a-z][a-z0-9-]*$`
   - `metadata` keys must be strings

   **Example**:
   ```json
   {
     "id": "example-123",
     "name": "example-name",
     "metadata": {
       "key": "value"
     }
   }
   ```

   ## Related

   - **Tutorial**: [Link to tutorial showing how to use this]
   - **How-To**: [Link to how-to guides solving problems with this]
   - **Explanation**: [Link to explanation of concepts behind this]

   ---

   ## Writing Guide for Reference Authors

   **✓ DO**:
   - Describe what exists, not how to use it
   - Be complete (document everything)
   - Be accurate (match actual behavior)
   - Be consistent (same format for similar items)
   - Include usage examples
   - Keep descriptions factual and concise
   - Structure around code organization

   **✗ DON'T**:
   - Explain concepts (that's for explanations)
   - Provide tutorials (that's for tutorials)
   - Solve problems (that's for how-tos)
   - Give opinions or recommendations
   - Skip items because they're "obvious"

   **Completeness Check**:
   - [ ] All public APIs documented
   - [ ] All CLI commands documented
   - [ ] All configuration options documented
   - [ ] All data structures documented
   - [ ] All fields/parameters have types
   - [ ] All fields/parameters have descriptions
   - [ ] Examples provided for each item

   **Consistency Check**:
   - [ ] Same format for all similar items
   - [ ] Same terminology throughout
   - [ ] Same level of detail for comparable items

   **Accessibility Checklist**:
   - [ ] Tables have headers
   - [ ] Code blocks have language tags
   - [ ] Lists are properly formatted
   - [ ] Clear, technical language

   **Auto-Generation Note**:
   If this reference is auto-generated from code:
   - Document the generation process
   - Note the source (which code files)
   - Explain how to regenerate
   - Keep manual additions separate from generated sections
   ```

**Files**: `src/specify_cli/missions/documentation/templates/divio/reference-template.md` (new file)

**Parallel?**: Yes (can be created alongside other Divio templates)

**Notes**:
- Reference is description, not instruction
- Must be complete (all APIs, all options, all details)
- Must be consistent (same format throughout)
- Examples show usage, not explanation
- Can mix auto-generated and manual content

**Quality Validation**:
- Is every public API/command/option documented?
- Is the format consistent across all items?
- Are descriptions factual (not instructional)?
- Do examples show usage without explaining?
- Is it organized around code structure?

### Subtask T016 – Create explanation-template.md

**Purpose**: Create template for understanding-oriented explanation documentation following Divio explanation principles.

**Divio Explanation Principles** (from research):
- **Understanding-oriented**: Clarify and illuminate concepts
- **For curious users**: Those wanting to understand "why"
- **Not instructional**: Not teaching how to do things
- **Conceptual discussion**: Ideas, background, context
- **Makes connections**: Links concepts to each other
- **Discusses alternatives**: Compares approaches, evaluates trade-offs

**Steps**:
1. Create `src/specify_cli/missions/documentation/templates/divio/explanation-template.md`
2. Add YAML frontmatter:
   ```yaml
   ---
   type: explanation
   audience: "{target_audience}"
   purpose: "Understand {concept}"
   created: "{date}"
   topic: "{topic_description}"
   concepts: "{key_concepts_covered}"
   ---
   ```
3. Add template structure:
   ```markdown
   # Explanation: {Concept or Topic}

   > **What this explains**: [The concept, design decision, or topic]
   >
   > **Why it matters**: [Why understanding this is valuable]
   >
   > **Who should read this**: [Curious users, contributors, architects, etc.]

   ## Overview

   [High-level introduction to the concept or topic - set context]

   ## Background

   [Historical context, why this exists, what problem it solves]

   ### The Problem

   [Describe the problem or need that led to this]

   ### Early Approaches

   [What was tried before? Why weren't those sufficient?]

   ### Current Solution

   [How does the current approach address the problem?]

   ## Core Concepts

   ### Concept 1: {Name}

   [Explain the concept clearly]

   **Why it's designed this way**:
   [The reasoning behind the design]

   **How it relates to {other concept}**:
   [Connections between concepts]

   ### Concept 2: {Name}

   [Repeat structure for each key concept...]

   ## Design Decisions

   ### Decision: {What was decided}

   **Context**: [What situation called for this decision?]

   **Options Considered**:
   1. **{Option A}**: [Description]
      - Pros: [Benefits]
      - Cons: [Drawbacks]
   2. **{Option B}**: [Description]
      - Pros: [Benefits]
      - Cons: [Drawbacks]
   3. **{Chosen Option}**: [Description]
      - Pros: [Why this was chosen]
      - Cons: [Accepted trade-offs]

   **Rationale**: [Why the chosen option was selected]

   **Implications**: [What this decision means for users/developers]

   ### Decision: {Another decision}

   [Repeat structure...]

   ## How It Works

   [Conceptual explanation of the mechanism - not implementation details]

   ### Component Interactions

   [How different parts relate and work together]

   ```
   [Conceptual diagram if helpful]
   ```

   ### Flow

   [Sequence of events or operations at a high level]

   ### Key Properties

   [Important characteristics or guarantees]

   ## Comparison with Alternatives

   ### vs. {Alternative Approach}

   **Similarities**:
   - [What they have in common]

   **Differences**:
   - [How they differ]

   **When to use {this approach}**:
   - [Scenarios where this is better]

   **When to use {alternative}**:
   - [Scenarios where alternative is better]

   ### vs. {Another Alternative}

   [Repeat structure...]

   ## Trade-offs and Limitations

   ### Advantages

   - [Benefit 1]
   - [Benefit 2]
   - [Benefit 3]

   ### Disadvantages

   - [Limitation 1]
   - [Limitation 2]
   - [Limitation 3]

   ### When to Use

   This approach works well when:
   - [Condition 1]
   - [Condition 2]

   This approach may not be suitable when:
   - [Condition 1]
   - [Condition 2]

   ## Further Reading

   ### Related Concepts

   - [Link to other explanation docs]

   ### See It in Action

   - [Link to tutorials using this concept]
   - [Link to how-tos applying this]

   ### Technical Details

   - [Link to reference docs for specifics]

   ### External Resources

   - [Academic papers, blog posts, videos]

   ---

   ## Writing Guide for Explanation Authors

   **✓ DO**:
   - Focus on understanding, not instruction
   - Explain "why" and "how it works" conceptually
   - Discuss alternatives and trade-offs
   - Make connections between concepts
   - Use analogies and examples to clarify
   - Provide historical context
   - Compare with other approaches

   **✗ DON'T**:
   - Give step-by-step instructions (that's tutorials)
   - Solve specific problems (that's how-tos)
   - List all technical details (that's reference)
   - Assume readers need to implement it
   - Make it required reading (it's for curious learners)

   **Structure Check**:
   - [ ] Introduces the topic clearly
   - [ ] Provides background and context
   - [ ] Explains core concepts
   - [ ] Discusses design decisions and rationale
   - [ ] Compares with alternatives
   - [ ] Identifies trade-offs and limitations
   - [ ] Links to related docs (tutorials, how-tos, reference)

   **Clarity Check**:
   - [ ] Concepts are explained clearly
   - [ ] Connections between ideas are explicit
   - [ ] Analogies help understanding
   - [ ] Diagrams illustrate concepts (if helpful)
   - [ ] Technical jargon is explained

   **Accessibility Checklist**:
   - [ ] Proper heading hierarchy
   - [ ] Diagrams have alt text or text description
   - [ ] Clear, thoughtful language
   - [ ] Concepts build logically

   **Inclusivity Checklist**:
   - [ ] Examples are diverse
   - [ ] Language is welcoming to all backgrounds
   - [ ] No assumptions about prior exposure to concepts
   ```

**Files**: `src/specify_cli/missions/documentation/templates/divio/explanation-template.md` (new file)

**Parallel?**: Yes (can be created alongside other Divio templates)

**Notes**:
- Explanation is about understanding, not doing
- Not required reading (for those curious about "why")
- Discusses concepts, design decisions, trade-offs
- Makes connections between ideas
- Compares with alternatives

**Quality Validation**:
- Does it explain "why" and "how it works"?
- Are design decisions and their rationale clear?
- Are alternatives discussed fairly?
- Are trade-offs and limitations identified?
- Does it help readers understand, not do?

### Subtask T017 – Add Write the Docs Guidance

**Purpose**: Ensure all four Divio templates include Write the Docs best practices for accessibility and bias-free language.

**Steps**:
1. Review all four templates (tutorial, how-to, reference, explanation)
2. Ensure each template includes:

**Accessibility Guidance**:
```markdown
**Accessibility Checklist**:
- [ ] Proper heading hierarchy (one H1, then H2, then H3 - no skipping levels)
- [ ] All images have descriptive alt text explaining what they show
- [ ] All code blocks have language tags for syntax highlighting
- [ ] Clear, plain language (avoid jargon or define technical terms)
- [ ] Links have descriptive text (not "click here")
- [ ] Tables have proper headers
- [ ] Lists are properly formatted (not paragraphs with commas)
```

**Bias-Free Language Guidance**:
```markdown
**Inclusivity Checklist**:
- [ ] Examples use diverse names (not just Western male names)
- [ ] Gender-neutral language ("they" not "he/she")
- [ ] No cultural assumptions (avoid idioms, religious references, cultural-specific examples)
- [ ] Welcoming tone (not intimidating or assuming knowledge)
- [ ] Avoid ableist language ("just", "simply", "obviously", "easy")
- [ ] Person-first language where appropriate
```

**Clear Language Guidance**:
```markdown
**Clarity Checklist**:
- [ ] Active voice ("run the command" not "the command should be run")
- [ ] Present tense ("returns" not "will return")
- [ ] Direct address ("you" addressing the reader)
- [ ] One idea per sentence
- [ ] Short paragraphs (3-5 sentences max)
- [ ] Concrete examples, not abstract descriptions
```

3. Add these sections to the "Writing Guide" at the bottom of each template
4. Include inline reminders in appropriate sections:
   - Before screenshot examples: reminder about alt text
   - Before example names: reminder about diverse names
   - Before code blocks: reminder about language tags

**Files**:
- `src/specify_cli/missions/documentation/templates/divio/tutorial-template.md` (modified)
- `src/specify_cli/missions/documentation/templates/divio/howto-template.md` (modified)
- `src/specify_cli/missions/documentation/templates/divio/reference-template.md` (modified)
- `src/specify_cli/missions/documentation/templates/divio/explanation-template.md` (modified)

**Parallel?**: Yes (can be done while creating templates or immediately after)

**Notes**:
- Write the Docs guidance should be woven throughout templates
- Checklists help authors verify their work
- Inline reminders catch issues early
- This is not optional - accessibility and inclusivity are requirements

**Quality Validation**:
- Are checklists present in all four templates?
- Are reminders placed at relevant points?
- Is guidance actionable (not vague)?
- Do examples in the templates themselves follow these guidelines?

### Subtask T018 – Add Content Placeholders

**Purpose**: Ensure all four Divio templates have appropriate placeholders that guide users on what content to provide.

**Steps**:
1. Review all four templates
2. Add placeholders in these formats:
   - `{placeholder_name}` - Simple replacement (e.g., {project_name})
   - `[Description of what goes here]` - Guidance for content blocks
   - `[EXAMPLE: ...]` - Show what good content looks like
3. Ensure placeholders cover:

**Common Placeholders** (all templates):
```markdown
{project_name}          # Project or product name
{component_name}        # Specific component being documented
{target_audience}       # Who this is for
{date}                  # Creation/update date
{author}                # Document author
```

**Tutorial-Specific Placeholders**:
```markdown
{goal}                  # What learner will accomplish
{duration}              # Estimated completion time
{prerequisites}         # Required knowledge/tools
{step_action}           # Action in each step
{expected_output}       # What learner should see
{concrete_accomplishment}  # What they've achieved
```

**How-To-Specific Placeholders**:
```markdown
{problem_description}   # Problem being solved
{solution_summary}      # Quick summary of approach
{required_knowledge}    # Assumed expertise
{action_step}           # Each step in solution
{variation_scenario}    # Alternative situations
```

**Reference-Specific Placeholders**:
```markdown
{api_module_cli}        # Type of reference (API/CLI/Config)
{component_status}      # Stable/Beta/Deprecated
{option_name}           # CLI option or config setting
{parameter_type}        # Data type
{default_value}         # Default setting
{description}           # Technical description
```

**Explanation-Specific Placeholders**:
```markdown
{concept}               # Concept being explained
{why_it_matters}        # Value of understanding
{problem_context}       # Problem that led to this
{design_rationale}      # Why designed this way
{alternative_approach}  # Other options considered
{trade_off}             # Accepted limitations
```

4. Add examples showing good vs. bad placeholder usage:
```markdown
## Example Placeholders

✓ Good:
```markdown
## Step 1: Install {project_name}

Download {project_name} from [link] and run:
```bash
npm install {project_name}
```
```

✗ Bad:
```markdown
## Step 1: Install the software

Download it and install.
```
(Too vague - doesn't guide the author)
```

**Files**:
- All four Divio templates (modified with placeholders)

**Parallel?**: Yes (can be done alongside template creation)

**Notes**:
- Placeholders make templates immediately useful
- Good placeholders guide authors on what content is needed
- Include examples of good content to set expectations
- Placeholders should be discoverable (obvious what to replace)

**Quality Validation**:
- Are all section

s that need content marked with placeholders?
- Are placeholders descriptive (clear what goes there)?
- Do examples show good content?
- Are common mistakes highlighted?

## Test Strategy

**Unit Tests** (to be implemented in WP09):

1. Test Divio templates exist:
   ```python
   def test_divio_templates_exist():
       mission = get_mission_by_name("documentation")
       templates = mission.list_templates()

       assert "divio/tutorial-template.md" in templates
       assert "divio/howto-template.md" in templates
       assert "divio/reference-template.md" in templates
       assert "divio/explanation-template.md" in templates
   ```

2. Test each template has frontmatter with type field:
   ```python
   @pytest.mark.parametrize("template_name,expected_type", [
       ("divio/tutorial-template.md", "tutorial"),
       ("divio/howto-template.md", "how-to"),
       ("divio/reference-template.md", "reference"),
       ("divio/explanation-template.md", "explanation"),
   ])
   def test_divio_template_frontmatter(template_name, expected_type):
       mission = get_mission_by_name("documentation")
       template = mission.get_template(template_name)
       content = template.read_text()

       # Parse frontmatter
       assert content.startswith("---")
       frontmatter = parse_yaml_frontmatter(content)
       assert frontmatter["type"] == expected_type
   ```

3. Test templates have required sections:
   ```python
   def test_tutorial_template_structure():
       mission = get_mission_by_name("documentation")
       template = mission.get_template("divio/tutorial-template.md")
       content = template.read_text()

       # Check for required sections
       assert "## What You'll Learn" in content
       assert "## Before You Begin" in content
       assert "## Step 1:" in content
       assert "## What You've Accomplished" in content
       assert "## Next Steps" in content
   ```

4. Test templates include Write the Docs guidance:
   ```python
   @pytest.mark.parametrize("template_name", [
       "divio/tutorial-template.md",
       "divio/howto-template.md",
       "divio/reference-template.md",
       "divio/explanation-template.md",
   ])
   def test_divio_template_accessibility_guidance(template_name):
       mission = get_mission_by_name("documentation")
       template = mission.get_template(template_name)
       content = template.read_text()

       assert "Accessibility Checklist" in content
       assert "Inclusivity Checklist" in content
       assert "alt text" in content.lower()
       assert "heading hierarchy" in content.lower()
   ```

**Manual Validation**:

1. Read each template as a documentation author:
   - Is it clear what type of documentation this is for?
   - Are the sections appropriate for this Divio type?
   - Do the placeholders guide you on what to write?
   - Is the guidance helpful?

2. Validate against Divio principles:
   - Tutorial: Learning-oriented, step-by-step?
   - How-To: Goal-oriented, problem-solving?
   - Reference: Information-oriented, complete?
   - Explanation: Understanding-oriented, conceptual?

3. Check accessibility guidance:
   - Are checklists comprehensive?
   - Are they actionable?
   - Are examples clear?

4. Test template loading:
   ```python
   from specify_cli.mission import get_mission_by_name

   mission = get_mission_by_name("documentation")

   # Load each Divio template
   for template_name in ["tutorial", "howto", "reference", "explanation"]:
       template_path = mission.get_template(f"divio/{template_name}-template.md")
       print(f"✓ {template_name} template loads successfully")
   ```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Templates too prescriptive | Medium - stifles creativity | Provide guidance but allow flexibility in content |
| Templates too vague | High - authors don't know what to write | Include examples and detailed placeholders |
| Mixing Divio types | High - confuses users | Clear distinctions, examples of what NOT to do |
| Missing accessibility guidance | High - inaccessible docs | Comprehensive checklists, inline reminders |
| Templates too long | Medium - intimidating | Sections are optional, core structure is minimal |
| Not following Divio principles | High - defeats purpose | Validate against research, test with users |

## Definition of Done Checklist

- [ ] `divio/` subdirectory created in `templates/`
- [ ] `tutorial-template.md` created with:
  - [ ] YAML frontmatter with `type: tutorial`
  - [ ] Learning-oriented structure (What You'll Learn, Steps, What You've Accomplished)
  - [ ] Checkpoints after each step
  - [ ] Writing guide emphasizing doing over explaining
  - [ ] Accessibility and inclusivity checklists
- [ ] `howto-template.md` created with:
  - [ ] YAML frontmatter with `type: how-to`
  - [ ] Goal-oriented structure (Problem, Solution, Steps, Verification)
  - [ ] Common variations section
  - [ ] Writing guide emphasizing problem-solving
  - [ ] Accessibility and inclusivity checklists
- [ ] `reference-template.md` created with:
  - [ ] YAML frontmatter with `type: reference`
  - [ ] Information-oriented structure (API/CLI/Config sections)
  - [ ] Consistent format for all entries
  - [ ] Examples for each item
  - [ ] Writing guide emphasizing completeness and consistency
  - [ ] Accessibility and inclusivity checklists
- [ ] `explanation-template.md` created with:
  - [ ] YAML frontmatter with `type: explanation`
  - [ ] Understanding-oriented structure (Background, Concepts, Design Decisions, Comparisons)
  - [ ] Trade-offs and limitations section
  - [ ] Writing guide emphasizing conceptual understanding
  - [ ] Accessibility and inclusivity checklists
- [ ] All templates include Write the Docs guidance
- [ ] All templates include appropriate placeholders
- [ ] Templates load successfully via `Mission.get_template()`
- [ ] Templates validated against Divio principles
- [ ] `tasks.md` in feature directory updated with WP03 status

## Review Guidance

**Key Acceptance Checkpoints**:

1. **Divio Type Compliance**:
   - Tutorial: Learning-oriented, step-by-step, for beginners?
   - How-To: Goal-oriented, problem-solving, for experienced users?
   - Reference: Information-oriented, complete, consistent format?
   - Explanation: Understanding-oriented, conceptual, discusses alternatives?

2. **Structure Appropriateness**:
   - Do sections match the Divio type?
   - Are required sections present?
   - Is guidance clear and actionable?

3. **Accessibility & Inclusivity**:
   - Are checklists comprehensive?
   - Are inline reminders present?
   - Do examples follow best practices?

4. **Usability**:
   - Can an author use these templates without reading external Divio docs?
   - Are placeholders helpful?
   - Is guidance specific enough?

5. **Quality**:
   - Are examples of good content included?
   - Are common mistakes highlighted?
   - Do templates themselves demonstrate good documentation?

**Validation Commands**:
```bash
# Check templates exist
ls -la src/specify_cli/missions/documentation/templates/divio/

# Test template loading
python -c "
from specify_cli.mission import get_mission_by_name
mission = get_mission_by_name('documentation')
for template in ['tutorial', 'howto', 'reference', 'explanation']:
    try:
        path = mission.get_template(f'divio/{template}-template.md')
        print(f'✓ {template} template loads successfully')
    except Exception as e:
        print(f'✗ {template} template failed: {e}')
"

# Check frontmatter
for file in src/specify_cli/missions/documentation/templates/divio/*.md; do
    echo "Checking $file..."
    head -20 "$file" | grep -A 5 "^type:"
done
```

**Review Focus Areas**:
- Divio type principles correctly applied
- Sections appropriate for each type
- Writing guidance is clear and actionable
- Accessibility and inclusivity checklists are comprehensive
- Placeholders guide authors effectively
- Examples demonstrate good practices
- Templates are usable without extensive Divio knowledge

## Activity Log

- 2026-01-12T17:18:56Z – system – lane=planned – Prompt created.
- 2026-01-13T08:01:22Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-13T09:04:01Z – agent – lane=doing – Started review via workflow command
- 2026-01-13T09:04:46Z – unknown – lane=done – Review passed
- 2026-01-14T16:44:30Z – test – shell_pid=71983 – lane=doing – Started implementation via workflow command
