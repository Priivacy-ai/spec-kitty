---
work_package_id: "WP02"
subtasks:
  - "T008"
  - "T009"
  - "T010"
  - "T011"
title: "Core Mission Templates"
phase: "Phase 0 - Foundation"
lane: "done"
assignee: ""
agent: ""
shell_pid: ""
review_status: "acknowledged"
reviewed_by: "codex"
dependencies:
  - "WP01"
history:
  - timestamp: "2026-01-12T17:18:56Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Core Mission Templates

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

Please address the following before re-review:

1. `src/specify_cli/missions/documentation/templates/tasks-template.md` is still the generic software-dev sample (includes "SAMPLE CONTENT BELOW. MUST BE REPLACED."). It does not define documentation-specific work packages, subtasks, or MVP scope guidance required in T010. Replace with the doc-mission content (Structure, Tutorials, How-To, Reference, Explanation, Quality Validation) and include doc-specific subtasks/examples.
2. `src/specify_cli/missions/documentation/templates/task-prompt-template.md` is still generic and missing the documentation-specific Quality Validation Strategy and documentation-focused Definition of Done items (Divio compliance, accessibility, inclusivity, link checks, doc build). Update to match T011 requirements.

---

## ⚠️ Dependency Rebase Guidance

**This WP depends on**: WP01 (Mission Infrastructure)

**Before starting work**:
1. Ensure WP01 is complete and merged
2. Mission directory structure exists at `src/specify_cli/missions/documentation/`
3. `mission.yaml` file exists and is valid

**If WP01 changes during your work**:
- No rebase needed (WP02 doesn't branch from WP01 in workspace-per-WP model)
- WP01 changes to main will be visible immediately since we're working in main repo for planning artifacts

---

## Objectives & Success Criteria

**Goal**: Create the core mission templates (spec, plan, tasks, task-prompt) that are used during documentation mission workflows. These templates should follow existing patterns from software-dev and research missions but be tailored for documentation-specific content.

**Success Criteria**:
- Four template files created in `src/specify_cli/missions/documentation/templates/`
- Templates load successfully via `Mission.get_template()`
- Each template has appropriate sections for documentation missions
- Templates reference documentation workflow phases (discover, audit, design, generate, validate, publish)
- Templates include placeholders for Divio types, generators, gap analysis results
- Templates follow existing spec-kitty template structure for consistency

## Context & Constraints

**Prerequisites**:
- WP01 complete: Mission directory structure and mission.yaml exist
- Existing mission templates as reference:
  - `src/specify_cli/missions/software-dev/templates/*.md`
  - `src/specify_cli/missions/research/templates/*.md`

**Reference Documents**:
- [plan.md](../plan.md) - Template hierarchy design (lines 192-199)
- [data-model.md](../data-model.md) - Documentation Template entity (lines 207-243)
- Existing templates:
  - `src/specify_cli/templates/spec-template.md` (base template)
  - Software-dev and research mission templates

**Constraints**:
- Must maintain compatibility with existing template loading system
- Must follow markdown format with YAML frontmatter where appropriate
- Must not break existing missions' template loading
- Templates should be documentation-specific but follow established patterns

## Subtasks & Detailed Guidance

### Subtask T008 – Create spec-template.md

**Purpose**: Provide template for documentation mission specifications generated during `/spec-kitty.specify`.

**Steps**:
1. Create `src/specify_cli/missions/documentation/templates/spec-template.md`
2. Copy structure from `src/specify_cli/templates/spec-template.md` as base
3. Adapt sections for documentation missions:
   - **Feature Name**: "Documentation Project: [PROJECT NAME]"
   - **Overview**: Include iteration mode (initial, gap-filling, feature-specific)
   - **User Scenarios**: Focus on documentation consumers (developers, end users, contributors)
   - **Requirements**: Include Divio type requirements, generator requirements, gap analysis requirements
   - **Success Criteria**: Documentation-specific metrics (coverage, accessibility, completeness)
   - **Key Entities**: Documentation Mission, Divio Types, Generators, Gap Analysis
4. Add documentation-specific placeholders:
   ```markdown
   ## Documentation Scope

   **Iteration Mode**: [initial | gap-filling | feature-specific]
   **Target Audience**: [developers | end users | contributors | operators]
   **Selected Divio Types**: [tutorial | how-to | reference | explanation]
   **Languages Detected**: [JavaScript, Python, Rust, etc.]
   **Generators to Use**: [JSDoc | Sphinx | rustdoc]

   ## Gap Analysis Results (for gap-filling mode)

   **Existing Documentation**:
   - [List current docs and their Divio types]

   **Identified Gaps**:
   - [Missing Divio types or outdated content]

   **Coverage Percentage**: [X%]
   ```

**Files**: `src/specify_cli/missions/documentation/templates/spec-template.md` (new file)

**Parallel?**: Yes (can be done alongside T009-T011)

**Notes**:
- Keep mandatory sections from base template (User Scenarios, Requirements, Success Criteria)
- Add documentation-specific sections for scope and gap analysis
- Include examples of good documentation requirements

**Example Content Snippet**:
```markdown
# Feature Specification: [DOCUMENTATION PROJECT NAME]

**Feature Branch**: `[###-feature-name]`
**Created**: [DATE]
**Status**: Draft
**Mission**: documentation
**Input**: User description: "$ARGUMENTS"

## Documentation Scope

**Iteration Mode**: [NEEDS CLARIFICATION: initial | gap-filling | feature-specific]
**Target Audience**: [NEEDS CLARIFICATION: developers integrating library | end users | contributors | operators]
**Selected Divio Types**: [NEEDS CLARIFICATION: Which of tutorial, how-to, reference, explanation?]
**Languages Detected**: [JavaScript, Python, Rust] (auto-detected during planning)
**Generators to Use**: [JSDoc, Sphinx, rustdoc] (based on languages)

## User Scenarios & Testing

### User Story 1 - Documentation Consumer (Priority: P1)

[Describe who needs the documentation and what they want to accomplish]

**Why this priority**: [Explain value]

**Independent Test**: [How to verify documentation achieves the goal]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [user accesses documentation], **Then** [they can accomplish goal]
2. **Given** [documentation exists], **When** [code changes], **Then** [documentation updates accordingly]

---

## Requirements

### Functional Requirements

#### Documentation Content

- **FR-001**: Documentation MUST include [tutorial | how-to | reference | explanation] for [feature/area]
- **FR-002**: Documentation MUST be accessible (proper headings, alt text, clear language)
- **FR-003**: Documentation MUST use bias-free language and inclusive examples

#### Generation Requirements

- **FR-004**: System MUST generate API reference from [JSDoc comments | Python docstrings | Rust doc comments]
- **FR-005**: Generated documentation MUST integrate with manually-written documentation

#### Gap-Filling Requirements (if gap-filling mode)

- **FR-006**: Gap analysis MUST identify missing Divio types
- **FR-007**: Gap analysis MUST detect outdated API documentation

### Key Entities

- **Divio Documentation Type**: One of tutorial, how-to, reference, explanation with distinct purpose
- **Documentation Generator**: Tool that creates reference docs from code (JSDoc, Sphinx, rustdoc)
- **Gap Analysis**: Assessment identifying missing or outdated documentation

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can find information they need within [X] clicks/searches
- **SC-002**: Documentation passes accessibility checks (proper heading hierarchy, alt text)
- **SC-003**: API reference is [X]% complete (all public APIs documented)
- **SC-004**: [X]% of users successfully complete tasks using documentation alone

## Assumptions

- **ASM-001**: Project has code comments/docstrings for reference generation to be valuable
- **ASM-002**: Users are willing to maintain documentation alongside code changes
- **ASM-003**: Documentation will be hosted on [platform] using [static site generator]

## Out of Scope

The following are explicitly NOT included in this documentation project:

- Documentation hosting/deployment (generates source files only)
- Documentation analytics (page views, search queries)
- AI-powered content generation (templates have placeholders, not auto-written prose)
- Interactive documentation features (try-it-now consoles, code playgrounds)
```

### Subtask T009 – Create plan-template.md

**Purpose**: Provide template for documentation mission implementation plans generated during `/spec-kitty.plan`.

**Steps**:
1. Create `src/specify_cli/missions/documentation/templates/plan-template.md`
2. Copy structure from `src/specify_cli/templates/plan-template.md` as base
3. Adapt Technical Context section for documentation missions:
   ```markdown
   ## Technical Context

   **Documentation Framework**: [Sphinx | MkDocs | Docusaurus | Jekyll | Hugo]
   **Generator Tools**: [JSDoc, Sphinx, rustdoc] (based on detected languages)
   **Output Format**: [HTML | Markdown | PDF]
   **Hosting Platform**: [Read the Docs | GitHub Pages | GitBook | Custom]
   **Build Tools**: [sphinx-build, npx jsdoc, cargo doc]
   **Theme**: [sphinx_rtd_theme | custom theme]
   ```
4. Add Phase 0: Research section specific to documentation:
   ```markdown
   ## Phase 0: Research

   ### Documentation Audit (for gap-filling mode)

   1. Scan existing documentation directory
   2. Classify docs into Divio types
   3. Build coverage matrix
   4. Identify gaps and priorities

   ### Generator Configuration Research

   1. Detect project languages
   2. Verify generator tools installed
   3. Research configuration options for detected generators
   4. Plan generator output integration with manual docs
   ```
5. Adapt Phase 1: Design for documentation structure:
   ```markdown
   ## Phase 1: Design

   ### Documentation Structure

   **Divio Organization**:
   ```
   docs/
   ├── tutorials/          # Learning-oriented
   ├── how-to/            # Problem-solving
   ├── reference/         # Technical specs (generated + manual)
   └── explanation/       # Understanding concepts
   ```

   ### Generator Configurations

   **Sphinx (Python)**:
   - Extensions: autodoc, napoleon, viewcode
   - Theme: sphinx_rtd_theme
   - Output: docs/reference/api/

   **JSDoc (JavaScript)**:
   - Config: jsdoc.json
   - Template: docdash
   - Output: docs/reference/api/js/
   ```

**Files**: `src/specify_cli/missions/documentation/templates/plan-template.md` (new file)

**Parallel?**: Yes (can be done alongside T008, T010, T011)

**Notes**:
- Planning for documentation is about structure and tooling, not code architecture
- Include sections for generator setup
- Add gap analysis workflow if iterating
- Reference existing project structure

**Example Content Snippet**:
```markdown
# Implementation Plan: [DOCUMENTATION PROJECT]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/kitty-specs/[###-feature-name]/spec.md`

## Summary

[Extract from spec: documentation goals, Divio types selected, generators needed]

## Technical Context

**Documentation Framework**: [Sphinx | MkDocs | Docusaurus | Jekyll | None (starting fresh)]
**Languages Detected**: [Python, JavaScript, Rust]
**Generator Tools**:
- JSDoc for JavaScript/TypeScript API reference
- Sphinx for Python API reference
- rustdoc for Rust API reference

**Output Format**: HTML (for web hosting)
**Hosting Platform**: [Read the Docs | GitHub Pages | GitBook]
**Build Commands**:
- `sphinx-build -b html docs/ docs/_build/html/`
- `npx jsdoc -c jsdoc.json`
- `cargo doc --no-deps`

**Theme**: sphinx_rtd_theme (for Sphinx), docdash (for JSDoc)

## Phase 0: Research

### Objective

[For gap-filling mode] Audit existing documentation, classify into Divio types, identify gaps.
[For initial mode] Research documentation best practices, plan structure from scratch.

### Research Tasks

1. **Documentation Audit** (gap-filling mode only)
   - Scan `docs/` directory for existing markdown files
   - Parse frontmatter to classify Divio type
   - Build coverage matrix: which areas have which types
   - Identify high-priority gaps (e.g., tutorials missing)

2. **Generator Setup Research**
   - Verify JSDoc installed: `npx jsdoc --version`
   - Verify Sphinx installed: `sphinx-build --version`
   - Verify rustdoc available: `cargo doc --help`
   - Research config options for each generator

3. **Divio Template Research**
   - Review Write the Docs guidance for each type
   - Identify examples of good tutorials, how-tos, reference, explanation
   - Plan section structure for each type

### Research Output

See [research.md](research.md) for detailed findings.

## Phase 1: Design

### Objective

Define documentation structure, configure generators, plan content outline.

### Documentation Structure

**Directory Layout**:
```
docs/
├── index.md                    # Landing page
├── tutorials/
│   └── getting-started.md     # Step-by-step for beginners
├── how-to/
│   ├── authentication.md      # Solve specific problems
│   └── deployment.md
├── reference/
│   ├── api/                   # Generated API docs
│   │   ├── python/            # Sphinx output
│   │   └── javascript/        # JSDoc output
│   └── cli.md                 # Manual reference
└── explanation/
    ├── architecture.md        # Design decisions
    └── concepts.md            # Core concepts
```

**Divio Type Mapping**:
- **Tutorials** (`tutorials/`): Learning-oriented, hands-on lessons
- **How-To Guides** (`how-to/`): Goal-oriented recipes
- **Reference** (`reference/`): Technical specs (mix of generated + manual)
- **Explanation** (`explanation/`): Understanding-oriented discussions

### Generator Configurations

**Sphinx Configuration** (Python):
```python
# docs/conf.py
project = 'MyProject'
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]
html_theme = 'sphinx_rtd_theme'
```

**JSDoc Configuration** (JavaScript):
```json
{
  "source": {
    "include": ["src/"],
    "includePattern": ".+\\.js$"
  },
  "opts": {
    "destination": "docs/reference/api/javascript",
    "template": "node_modules/docdash"
  }
}
```

**rustdoc Configuration** (Rust):
```toml
[package.metadata.docs.rs]
all-features = true
rustdoc-args = ["--document-private-items"]
```

### Work Breakdown

Will be detailed in Phase 2 (tasks.md). High-level work packages:

1. **WP01: Structure Setup** - Create docs/ directory, configure generators
2. **WP02: Tutorials** - Write getting-started tutorial
3. **WP03: How-To Guides** - Write problem-solving guides
4. **WP04: Reference** - Generate API docs, write manual reference
5. **WP05: Explanation** - Write architecture and concept docs
6. **WP06: Build & Deploy** - Set up build process, deploy to hosting

## Phase 2: Implementation

**Note**: Phase 2 (work package generation) is handled by the `/spec-kitty.tasks` command.

## Success Criteria Validation

Validating against spec.md success criteria:

- **SC-001** (findability): Structure enables quick navigation
- **SC-002** (accessibility): Templates include accessibility prompts
- **SC-003** (API completeness): Generators ensure coverage
- **SC-004** (task completion): Tutorials and how-tos guide users to success
```

### Subtask T010 – Create tasks-template.md

**Purpose**: Provide template for work package breakdown generated during `/spec-kitty.tasks`.

**Steps**:
1. Create `src/specify_cli/missions/documentation/templates/tasks-template.md`
2. Copy structure from `src/specify_cli/templates/tasks-template.md` as base
3. Adapt work package examples for documentation missions:
   - WP01: Documentation Structure Setup
   - WP02: Tutorial Creation (for selected tutorials)
   - WP03: How-To Guide Creation (for selected guides)
   - WP04: Reference Documentation (generated + manual)
   - WP05: Explanation Documentation (architecture, concepts)
   - WP06: Quality Validation (accessibility, completeness)
4. Include documentation-specific subtask examples:
   ```markdown
   - [ ] T001 Create `docs/` directory structure
   - [ ] T002 Configure Sphinx with autodoc extension
   - [ ] T003 Generate Python API reference from docstrings
   - [ ] T004 Write "Getting Started" tutorial
   - [ ] T005 Write "How to Deploy" guide
   - [ ] T006 Write "Architecture Overview" explanation
   - [ ] T007 Validate accessibility (heading hierarchy, alt text)
   - [ ] T008 Build documentation site and verify links
   ```
5. Adapt MVP scope guidance:
   ```markdown
   ## MVP Scope

   **Minimum Viable Documentation** = WP01 (Structure) + WP04 (Reference)

   This enables:
   - Basic API reference from code comments
   - Foundation for adding tutorials/guides later

   **Full Documentation Set** = All work packages for complete Divio coverage
   ```

**Files**: `src/specify_cli/missions/documentation/templates/tasks-template.md` (new file)

**Parallel?**: Yes (can be done alongside T008, T009, T011)

**Notes**:
- Work packages should align with Divio types (one WP per type often makes sense)
- Include generator invocation as specific subtasks
- Add quality validation as final work package
- Emphasize that reference can be MVP, other types add value

**Example Content Snippet**:
```markdown
# Work Packages: [DOCUMENTATION PROJECT]

**Inputs**: Design documents from `/kitty-specs/[###-feature-name]/`
**Prerequisites**: plan.md (required), spec.md (documentation goals)

**Tests**: Quality validation included (accessibility checks, link validation, completeness review).

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package must be independently deliverable and testable.

---

## Work Package WP01: Documentation Structure Setup (Priority: P0)

**Goal**: Create docs/ directory, configure generators, set up build system.
**Independent Test**: Documentation builds successfully, generators produce output.
**Prompt**: `/tasks/WP01-documentation-structure-setup.md`

### Included Subtasks
- [ ] T001 Create `docs/` directory with Divio subdirectories
- [ ] T002 [P] Configure Sphinx for Python (if applicable)
- [ ] T003 [P] Configure JSDoc for JavaScript (if applicable)
- [ ] T004 [P] Configure rustdoc for Rust (if applicable)
- [ ] T005 Create index.md landing page
- [ ] T006 Set up build script (Makefile or build.sh)
- [ ] T007 Test build process end-to-end

### Implementation Notes
- Generators run in parallel (different languages)
- Build script should invoke all applicable generators
- Landing page links to each Divio section

### Parallel Opportunities
- Generator configurations can proceed in parallel (T002-T004)

### Dependencies
- None (starting package)

---

## Work Package WP02: Tutorial Documentation (Priority: P1) 🎯 MVP Component

**Goal**: Create step-by-step tutorials for key user journeys.
**Independent Test**: Beginners can complete tutorial successfully.
**Prompt**: `/tasks/WP02-tutorial-documentation.md`

### Included Subtasks
- [ ] T008 Write "Getting Started" tutorial (installation, first use)
- [ ] T009 Write "Basic Usage" tutorial (core features)
- [ ] T010 [P] Write "Advanced Usage" tutorial (if applicable)
- [ ] T011 Add screenshots/code examples to tutorials
- [ ] T012 Test tutorials with fresh user (validation)

### Implementation Notes
- Tutorials are learning-oriented: step-by-step, for beginners
- Each step should show immediate result
- Minimize explanations, maximize doing
- Include exact commands and expected outputs

### Parallel Opportunities
- Multiple tutorials can be written in parallel (T008-T010)

### Dependencies
- Depends on WP01 (structure must exist)

---

## Work Package WP03: How-To Guide Documentation (Priority: P1)

**Goal**: Create problem-solving guides for specific tasks.
**Independent Test**: Experienced users can solve problems using guides.
**Prompt**: `/tasks/WP03-howto-documentation.md`

### Included Subtasks
- [ ] T013 Write "How to Deploy" guide
- [ ] T014 Write "How to Configure" guide
- [ ] T015 Write "How to Troubleshoot" guide
- [ ] T016 [P] Write additional task-specific guides
- [ ] T017 Add troubleshooting sections to each guide

### Implementation Notes
- How-tos are goal-oriented: solve specific problems
- Assume reader has basic knowledge (not for beginners)
- Provide steps, not explanations
- Link to explanation docs for "why"

### Parallel Opportunities
- All how-to guides can be written in parallel (T013-T016)

### Dependencies
- Depends on WP01 (structure must exist)

---

## Work Package WP04: Reference Documentation (Priority: P0) 🎯 MVP Component

**Goal**: Generate API reference from code, write manual reference for non-code items.
**Independent Test**: All public APIs documented, reference is complete.
**Prompt**: `/tasks/WP04-reference-documentation.md`

### Included Subtasks
- [ ] T018 Generate Python API reference (Sphinx autodoc)
- [ ] T019 Generate JavaScript API reference (JSDoc)
- [ ] T020 Generate Rust API reference (cargo doc)
- [ ] T021 Write CLI reference (manual)
- [ ] T022 Write configuration reference (manual)
- [ ] T023 Integrate generated + manual reference into unified structure
- [ ] T024 Validate all public APIs are documented

### Implementation Notes
- Reference is information-oriented: technical specifications
- Generated reference from code comments/docstrings
- Manual reference for CLIs, configs, data formats
- Structure around code organization
- Include usage examples for each API

### Parallel Opportunities
- Generator invocations can run in parallel (T018-T020)
- Manual reference writing can proceed alongside generation (T021-T022)

### Dependencies
- Depends on WP01 (generator configs must exist)

---

## Work Package WP05: Explanation Documentation (Priority: P2)

**Goal**: Write understanding-oriented docs explaining concepts and architecture.
**Independent Test**: Readers understand "why" decisions were made.
**Prompt**: `/tasks/WP05-explanation-documentation.md`

### Included Subtasks
- [ ] T025 Write "Architecture Overview" explanation
- [ ] T026 Write "Core Concepts" explanation
- [ ] T027 Write "Design Decisions" explanation
- [ ] T028 [P] Write "Comparison with Alternatives" explanation
- [ ] T029 Add diagrams illustrating architecture/concepts

### Implementation Notes
- Explanations are understanding-oriented: clarify and illuminate
- Not instructional (not how-to)
- Not technical reference (not what exists)
- Focus on context, background, and "why"

### Parallel Opportunities
- All explanation docs can be written in parallel (T025-T028)

### Dependencies
- Depends on WP01 (structure must exist)
- Can reference WP02-04 content (but not blocked by them)

---

## Work Package WP06: Quality Validation & Publishing (Priority: P1)

**Goal**: Validate accessibility, completeness, build for publishing.
**Independent Test**: Documentation passes all quality checks, builds successfully.
**Prompt**: `/tasks/WP06-quality-validation.md`

### Included Subtasks
- [ ] T030 Validate heading hierarchy (proper H1 → H2 → H3 nesting)
- [ ] T031 Validate all images have alt text
- [ ] T032 Validate no broken internal links
- [ ] T033 Validate no broken external links
- [ ] T034 Check for bias-free language and inclusive examples
- [ ] T035 Verify code examples are tested/valid
- [ ] T036 Build final documentation site
- [ ] T037 Deploy to hosting platform (if applicable)

### Implementation Notes
- Use automated tools where possible (link checkers, linters)
- Manual review for accessibility and inclusivity
- Build process should be reproducible
- Document deployment process for future updates

### Parallel Opportunities
- Validation checks can run in parallel (T030-T035)

### Dependencies
- Depends on WP02-05 (content must exist to validate)

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02-05 (parallel) → WP06
- **MVP Scope**: WP01 + WP04 (structure + reference) enables basic API documentation
- **Full Coverage**: All 6 work packages for complete Divio-compliant documentation

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001       | Create docs/ structure | WP01 | P0 | No |
| T002       | Configure Sphinx | WP01 | P0 | Yes |
| T003       | Configure JSDoc | WP01 | P0 | Yes |
| T008       | Write getting-started tutorial | WP02 | P1 | Yes |
| T013       | Write deployment guide | WP03 | P1 | Yes |
| T018       | Generate Python API reference | WP04 | P0 | Yes |
| T025       | Write architecture explanation | WP05 | P2 | Yes |
| T030       | Validate heading hierarchy | WP06 | P1 | Yes |
```

### Subtask T011 – Create task-prompt-template.md

**Purpose**: Provide template for individual work package prompt files generated during `/spec-kitty.tasks`.

**Steps**:
1. Create `src/specify_cli/missions/documentation/templates/task-prompt-template.md`
2. Copy structure from `src/specify_cli/templates/task-prompt-template.md` as base
3. Adapt sections for documentation work packages:
   - Keep standard sections (Objectives, Context, Subtasks, Risks, Definition of Done)
   - Adapt Test Strategy section for documentation quality checks:
     ```markdown
     ## Quality Validation Strategy

     **Manual Validation**:
     1. Read documentation as target audience
     2. Follow tutorial steps exactly - do they work?
     3. Use how-to guides to solve real problems - are they helpful?
     4. Reference API docs while coding - are they complete?
     5. Read explanations - do they clarify concepts?

     **Automated Checks**:
     - Heading hierarchy: `grep -E '^#+' docs/**/*.md` (verify proper nesting)
     - Broken links: `markdown-link-check docs/**/*.md`
     - Alt text: `grep -E '!\[.*\]\(' docs/**/*.md | grep -v '\[.*\]'` (should be empty)
     - Spelling: `aspell check docs/**/*.md`
     ```
4. Add documentation-specific Definition of Done items:
   ```markdown
   ## Definition of Done Checklist

   - [ ] All subtasks completed and validated
   - [ ] Documentation follows Divio type principles (tutorial/how-to/reference/explanation)
   - [ ] Accessibility guidelines met (headings, alt text, clear language)
   - [ ] Bias-free language and inclusive examples used
   - [ ] Code examples tested and verified to work
   - [ ] Internal links point to correct sections
   - [ ] External links are valid and relevant
   - [ ] Documentation builds without errors or warnings
   - [ ] Peer review completed (someone read it)
   - [ ] `tasks.md` updated with status change
   ```

**Files**: `src/specify_cli/missions/documentation/templates/task-prompt-template.md` (new file)

**Parallel?**: Yes (can be done alongside T008-T010)

**Notes**:
- Prompt files guide implementation of specific documentation work packages
- Should emphasize quality over quantity
- Include validation steps appropriate to documentation (not code tests)
- Reference Write the Docs and Divio principles

**Example Content Snippet**:
```markdown
---
work_package_id: "WPxx"
subtasks:
  - "Txxx"
title: "Replace with work package title"
phase: "Phase N - Replace with phase name"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "{{TIMESTAMP}}"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: {{work_package_id}} – {{title}}

## ⚠️ IMPORTANT: Review Feedback Status

[Standard review feedback section]

---

## Objectives & Success Criteria

- Deliver [specific documentation outcome] that enables [target audience] to [accomplish goal]
- Documentation follows [Divio type] principles: [characteristics of this type]
- Quality metrics: [accessibility, completeness, accuracy]

## Context & Constraints

**Target Audience**: [Beginners | Experienced users | Contributors | All users]
**Divio Type**: [tutorial | how-to | reference | explanation]
**Documentation Framework**: [Sphinx | MkDocs | Plain Markdown]
**Generator Tools**: [JSDoc | Sphinx | rustdoc | None (manual)]

**Reference Documents**:
- [../spec.md](../spec.md) - Documentation goals and requirements
- [../plan.md](../plan.md) - Structure and generator configuration
- [Divio Documentation System](https://docs.divio.com/documentation-system/) - Type definitions
- [Write the Docs Guide](https://www.writethedocs.org/guide/) - Best practices

**Divio Principles for [Type]**:

*[For Tutorial]*:
- Learning-oriented, not explanation-oriented
- Step-by-step progression
- Learner accomplishes something concrete at each step
- Minimal explanations (link to explanations instead)
- Assume beginner knowledge level

*[For How-To]*:
- Goal-oriented, solve specific problem
- Assume experienced user (not beginners)
- Practical steps, minimal explanation
- Flexible (reader adapts to their situation)
- Links to reference for details, explanation for "why"

*[For Reference]*:
- Information-oriented, technical description
- Structure around code organization
- Consistent format for all similar items
- Includes usage examples
- Complete and accurate

*[For Explanation]*:
- Understanding-oriented, clarify concepts
- Not instructional (not how-to)
- Provides context and background
- Discusses alternatives and trade-offs
- Makes connections between ideas

## Subtasks & Detailed Guidance

### Subtask TXXX – [Description]

**Purpose**: [Why this documentation piece exists]

**Steps**:
1. [Concrete action]
2. [Concrete action]
3. Validate against Divio principles for [type]

**Files**:
- `docs/[section]/[file].md` (documentation file)

**Divio Compliance**:
- [ ] Follows [tutorial/how-to/reference/explanation] characteristics
- [ ] Appropriate for target audience
- [ ] Achieves its purpose (teach/solve/describe/clarify)

**Accessibility**:
- [ ] Proper heading hierarchy (one H1, then H2, then H3)
- [ ] Images have alt text
- [ ] Clear, plain language (avoid jargon or define it)
- [ ] Code blocks have language tags for syntax highlighting

**Inclusivity**:
- [ ] Examples use diverse names (not just "John", "Bob")
- [ ] Language is gender-neutral where possible
- [ ] Examples avoid cultural assumptions

**Notes**: [Specific guidance for this documentation piece]

### Subtask TYYY – [Description]

[Repeat structure for each subtask]

## Quality Validation Strategy

**Self-Review Checklist**:
1. [ ] Read documentation as if you are [target audience]
2. [ ] Verify all Divio principles for [type] are followed
3. [ ] Check accessibility (headings, alt text, clear language)
4. [ ] Check inclusivity (diverse examples, neutral language)
5. [ ] Test code examples (run them, verify they work)
6. [ ] Verify all links (internal and external)
7. [ ] Run spell check
8. [ ] Build documentation (no errors/warnings)

**Automated Checks**:
```bash
# Heading hierarchy check
find docs/ -name "*.md" -exec grep -E '^#+' {} +

# Link checking
markdown-link-check docs/**/*.md

# Spell check
aspell check docs/**/*.md

# Build check
[sphinx-build / mkdocs build / etc.] --fail-on-warning
```

**Peer Review**:
- Have someone from target audience read and follow the documentation
- Ask: Did you accomplish the goal? What was confusing?
- Revise based on feedback

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Documentation is too technical for audience | High - users can't use it | Write for target audience explicitly, get peer review |
| Examples don't work | High - breaks trust | Test all code examples before committing |
| Documentation becomes outdated | Medium - misleads users | Document maintenance process, add "last updated" dates |
| Accessibility barriers | Medium - excludes users | Follow accessibility checklist, use automated tools |

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] Documentation follows Divio [type] principles
- [ ] Accessibility guidelines met:
  - [ ] Proper heading hierarchy (H1 → H2 → H3)
  - [ ] All images have descriptive alt text
  - [ ] Clear, plain language used
  - [ ] Code blocks have syntax highlighting
- [ ] Inclusivity guidelines met:
  - [ ] Diverse examples
  - [ ] Gender-neutral language
  - [ ] No cultural assumptions
- [ ] Quality checks passed:
  - [ ] Spell check clean
  - [ ] No broken links (internal or external)
  - [ ] All code examples tested and work
  - [ ] Build succeeds with no warnings
- [ ] Peer review completed
- [ ] `tasks.md` updated with status change

## Review Guidance

**For Reviewers**:

1. **Divio Type Compliance**:
   - Does this follow [tutorial/how-to/reference/explanation] characteristics?
   - Is it appropriate for the stated audience?

2. **Accessibility**:
   - Proper heading hierarchy?
   - Alt text for images?
   - Clear language?

3. **Completeness**:
   - Does it achieve its stated purpose?
   - Are there gaps or missing information?

4. **Accuracy**:
   - Are code examples correct?
   - Are technical details accurate?
   - Are links valid?

5. **Usability**:
   - Can target audience actually use this?
   - Is it findable (good title, clear purpose)?

## Activity Log

- {{TIMESTAMP}} – system – lane=planned – Prompt created.
```
- 2026-01-12T17:53:20Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-12T18:38:18Z – unknown – lane=planned – Changes requested
- 2026-01-12T18:40:12Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-12T18:41:39Z – unknown – lane=for_review – Ready for review
- 2026-01-12T18:42:43Z – agent – lane=doing – Started review via workflow command
- 2026-01-12T18:45:31Z – unknown – lane=for_review – Ready for review
- 2026-01-13T07:46:03Z – agent – lane=doing – Started review via workflow command
- 2026-01-13T07:46:03Z – unknown – lane=done – Review passed

## Test Strategy

**Unit Tests** (to be implemented in WP09):

1. Test templates load successfully:
   ```python
   def test_documentation_mission_templates_exist():
       mission = get_mission_by_name("documentation")
       templates = mission.list_templates()

       assert "spec-template.md" in templates
       assert "plan-template.md" in templates
       assert "tasks-template.md" in templates
       assert "task-prompt-template.md" in templates
   ```

2. Test template structure:
   ```python
   def test_spec_template_has_required_sections():
       mission = get_mission_by_name("documentation")
       template = mission.get_template("spec-template.md")
       content = template.read_text()

       # Check for documentation-specific sections
       assert "## Documentation Scope" in content
       assert "**Iteration Mode**:" in content
       assert "**Selected Divio Types**:" in content
       assert "**Generators to Use**:" in content
   ```

3. Test plan template references documentation phases:
   ```python
   def test_plan_template_references_doc_phases():
       mission = get_mission_by_name("documentation")
       template = mission.get_template("plan-template.md")
       content = template.read_text()

       # Check for documentation-specific phases
       assert "discover" in content or "audit" in content
       assert "Generator Configuration" in content
   ```

**Manual Validation**:
1. Load each template and verify it renders correctly
2. Check that placeholders are appropriate for documentation missions
3. Verify templates don't reference code/implementation concepts inappropriately
4. Confirm templates follow existing spec-kitty template conventions

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Templates too different from existing missions | Medium - confusing for users | Follow software-dev template structure closely, adapt content only |
| Missing documentation-specific placeholders | Medium - templates not useful | Review against data-model.md entity definitions |
| Template content quality | Medium - poor guidance | Reference Write the Docs and Divio research extensively |
| Template loading errors | High - blocks mission usage | Test template loading in WP09 |

## Definition of Done Checklist

- [ ] All four template files created in `templates/` directory
- [ ] spec-template.md includes Documentation Scope and Gap Analysis sections
- [ ] plan-template.md includes generator configuration and doc structure sections
- [ ] tasks-template.md includes documentation-specific work package examples
- [ ] task-prompt-template.md includes quality validation and Divio compliance sections
- [ ] Templates load successfully via `Mission.get_template()`
- [ ] Templates follow existing spec-kitty template structure
- [ ] Templates include appropriate placeholders for documentation missions
- [ ] Templates reference documentation workflow phases (not software-dev phases)
- [ ] Manual validation completed (templates render correctly)
- [ ] `tasks.md` in feature directory updated with WP02 status

## Review Guidance

**Key Acceptance Checkpoints**:

1. **Template Existence**: All four templates created in correct location
2. **Loading Success**: Templates load via `Mission.get_template()` without errors
3. **Structure Consistency**: Templates follow existing template patterns
4. **Documentation-Specific Content**: Templates adapted for documentation missions (not copy-paste from software-dev)
5. **Placeholder Appropriateness**: Placeholders match documentation mission needs
6. **Quality**: Clear guidance, good examples, references to research

**Validation Commands**:
```bash
# Check templates exist
ls -la src/specify_cli/missions/documentation/templates/

# Test template loading
python -c "
from specify_cli.mission import get_mission_by_name
mission = get_mission_by_name('documentation')
templates = mission.list_templates()
print('Templates:', templates)
for template in templates:
    try:
        path = mission.get_template(template)
        print(f'✓ {template} loads successfully')
    except Exception as e:
        print(f'✗ {template} failed: {e}')
"
```

**Review Focus Areas**:
- Templates adapted appropriately for documentation (not just copied)
- Documentation-specific sections present (Divio types, generators, gap analysis)
- Placeholders help users understand what to fill in
- Examples are relevant to documentation work
- Quality of guidance provided

## Activity Log

- 2026-01-12T17:18:56Z – system – lane=planned – Prompt created.
- 2026-01-12T18:40:21Z – codex – lane=doing – Acknowledged review feedback and starting fixes.
