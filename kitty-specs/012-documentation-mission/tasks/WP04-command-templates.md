---
work_package_id: "WP04"
subtasks:
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
title: "Command Templates"
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

# Work Package Prompt: WP04 – Command Templates

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

Resolved:

1. Added YAML frontmatter (`description:`) and `User Input` blocks to all five documentation mission command templates, matching the software-dev/research format and preserving `$ARGUMENTS` handling.
   - Files: `src/specify_cli/missions/documentation/command-templates/specify.md`, `src/specify_cli/missions/documentation/command-templates/plan.md`, `src/specify_cli/missions/documentation/command-templates/tasks.md`, `src/specify_cli/missions/documentation/command-templates/implement.md`, `src/specify_cli/missions/documentation/command-templates/review.md`

---

## ⚠️ Dependency Rebase Guidance

**This WP depends on**: WP01 (Mission Infrastructure)

**Before starting work**:

1. Ensure WP01 is complete
2. Mission directory exists: `src/specify_cli/missions/documentation/`
3. Command templates directory exists: `src/specify_cli/missions/documentation/command-templates/`

---

## Objectives & Success Criteria

**Goal**: Create command instruction templates (specify, plan, tasks, implement, review) that guide AI agents through documentation mission workflows with documentation-specific questions, checks, and guidance.

**Success Criteria**:

- Five command template files created in `command-templates/` subdirectory
- Each template provides clear, actionable instructions for documentation missions
- Templates reference documentation workflow phases (discover, audit, design, generate, validate, publish)
- Templates include documentation-specific questions and prompts
- Templates guide agents to generate appropriate documentation artifacts
- Commands integrate with Divio types, generators, and gap analysis concepts
- Templates load successfully via mission system

## Context & Constraints

**Prerequisites**:

- WP01 complete: Mission directory and command-templates/ directory exist
- Understanding of documentation mission workflow from research

**Reference Documents**:

- [plan.md](../plan.md) - Mission workflow design (lines 182-211)
- [data-model.md](../data-model.md) - Mission Configuration commands section (lines 73-90)
- [research.md](../research.md) - Mission phase design (lines 575-617)
- [spec.md](../spec.md) - Command requirements (FR-042 to FR-045, lines 161-165)
- Existing command templates:
  - `src/specify_cli/missions/software-dev/command-templates/*.md`
  - `src/specify_cli/missions/research/command-templates/*.md`

**Constraints**:

- Must follow existing command template format
- Must integrate with spec-kitty's agent execution model
- Commands must be documentation-specific (not generic)
- Must reference appropriate workflow phases
- Must guide agents to create correct artifacts

**Documentation Workflow Phases** (from research):

1. **discover** - Understand documentation needs and scope
2. **audit** - Analyze existing documentation (gap-filling mode)
3. **design** - Plan documentation structure and generators
4. **generate** - Create documentation from templates
5. **validate** - Review quality and completeness
6. **publish** - Prepare for hosting/deployment

## Subtasks & Detailed Guidance

### Subtask T019 – Create command-templates/ Subdirectory

**Purpose**: Create the subdirectory for command instruction templates.

**Steps**:

1. Verify `src/specify_cli/missions/documentation/command-templates/` directory exists (should be created in WP01)
2. If not, create it now
3. Verify directory structure:

   ```
   src/specify_cli/missions/documentation/
   ├── mission.yaml
   ├── templates/
   │   ├── spec-template.md
   │   ├── plan-template.md
   │   ├── tasks-template.md
   │   ├── task-prompt-template.md
   │   └── divio/
   └── command-templates/      # THIS DIRECTORY
       ├── specify.md
       ├── plan.md
       ├── tasks.md
       ├── implement.md
       └── review.md
   ```

**Files**: `src/specify_cli/missions/documentation/command-templates/` (directory)

**Parallel?**: Yes (can proceed immediately)

**Notes**: Simple directory verification/creation.

### Subtask T020 – Create specify.md Command Template

**Purpose**: Provide instructions for the `/spec-kitty.specify` command specific to documentation missions, including discovery questions for iteration mode, Divio types, target audience, and generators.

**Command Context**: The specify command runs during the discovery phase to gather requirements and create a specification for the documentation project.

**Steps**:

1. Create `src/specify_cli/missions/documentation/command-templates/specify.md`
2. Structure the template to guide discovery conversation
3. Include documentation-specific discovery questions
4. Reference the "discover" workflow phase

**Content Structure**:

```markdown
# Command Template: /spec-kitty.specify (Documentation Mission)

**Phase**: Discover
**Purpose**: Understand documentation needs, identify iteration mode, select Divio types, detect languages, recommend generators.

## Discovery Gate (mandatory)

Before running any scripts or writing to disk, conduct a structured discovery interview tailored to documentation missions.

**Scope proportionality**: For documentation missions, discovery depth depends on project maturity:
- **New project** (initial mode): 3-4 questions about audience, goals, Divio types
- **Existing docs** (gap-filling mode): 2-3 questions about gaps, priorities, maintenance
- **Feature-specific** (documenting new feature): 1-2 questions about feature scope, integration

### Discovery Questions

**Question 1: Iteration Mode** (CRITICAL)

Ask user which documentation scenario applies:

**(A) Initial Documentation** - First-time documentation for a project (no existing docs)
**(B) Gap-Filling** - Improving/extending existing documentation
**(C) Feature-Specific** - Documenting a specific new feature/module

**Why it matters**: Determines whether to run gap analysis, how to structure workflow.

**Store answer in**: `meta.json → documentation_state.iteration_mode`

---

**Question 2A: For Initial Mode - What to Document**

Ask user:
- What is the primary audience? (developers, end users, contributors, operators)
- What are the documentation goals? (onboarding, API reference, troubleshooting, understanding architecture)
- Which Divio types are most important? (tutorial, how-to, reference, explanation)

**Why it matters**: Determines which templates to generate, what content to prioritize.

---

**Question 2B: For Gap-Filling Mode - What's Missing**

Inform user you will audit existing documentation, then ask:
- What problems are users reporting? (can't get started, can't solve specific problems, APIs undocumented, don't understand concepts)
- Which areas need documentation most urgently? (specific features, concepts, tasks)
- What Divio types are you willing to add? (tutorial, how-to, reference, explanation)

**Why it matters**: Focuses gap analysis on user-reported issues, prioritizes work.

---

**Question 2C: For Feature-Specific Mode - Feature Details**

Ask user:
- Which feature/module are you documenting?
- Who will use this feature? (what audience)
- What aspects need documentation? (getting started, common tasks, API details, architecture/design)

**Why it matters**: Scopes documentation to just the feature, determines which Divio types apply.

---

**Question 3: Language Detection & Generators**

Auto-detect project languages:
- Scan for `.js`, `.ts`, `.jsx`, `.tsx` files → Recommend JSDoc/TypeDoc
- Scan for `.py` files → Recommend Sphinx
- Scan for `Cargo.toml`, `.rs` files → Recommend rustdoc

Present to user:
"Detected languages: [list]. Recommend these generators: [list]. Proceed with these?"

Allow user to:
- Confirm all
- Select subset
- Skip generators (manual documentation only)

**Why it matters**: Determines which generators to configure in planning phase.

**Store answer in**: `meta.json → documentation_state.generators_configured`

---

**Question 4: Target Audience (if not already clear)**

If not clear from earlier answers, ask:
"Who is the primary audience for this documentation?"
- Developers integrating your library/API
- End users using your application
- Contributors to your project
- Operators deploying/maintaining your system
- Mix of above (specify)

**Why it matters**: Affects documentation tone, depth, assumed knowledge.

**Store answer in**: `spec.md → ## Documentation Scope → Target Audience`

---

### Intent Summary

After discovery questions answered, synthesize into Intent Summary:

```markdown
## Documentation Mission Intent

**Iteration Mode**: [initial | gap-filling | feature-specific]
**Primary Goal**: [Describe what user wants to accomplish]
**Target Audience**: [Who will read these docs]
**Selected Divio Types**: [tutorial, how-to, reference, explanation]
**Detected Languages**: [Python, JavaScript, Rust, etc.]
**Recommended Generators**: [JSDoc, Sphinx, rustdoc]

**Scope**: [Summary of what will be documented]
```

Confirm with user before proceeding.

---

## Outline

1. **Check discovery status**: If questions unanswered, ask one at a time (Discovery Gate above)

2. **Generate feature directory**: Run `spec-kitty agent feature create-feature "doc-{project-name}" --json --mission documentation`
   - Feature naming convention: `doc-{project-name}` or `docs-{feature-name}` for feature-specific

3. **Create meta.json**: Include `mission: "documentation"` and `documentation_state` field:

   ```json
   {
     "feature_number": "###",
     "slug": "doc-project-name",
     "friendly_name": "Documentation: Project Name",
     "mission": "documentation",
     "source_description": "...",
     "created_at": "...",
     "documentation_state": {
       "iteration_mode": "initial",
       "divio_types_selected": ["tutorial", "reference"],
       "generators_configured": [
         {"name": "sphinx", "language": "python"}
       ],
       "target_audience": "developers",
       "last_audit_date": null,
       "coverage_percentage": 0.0
     }
   }
   ```

4. **Run gap analysis** (gap-filling mode only):
   - Scan existing `docs/` directory
   - Classify docs into Divio types
   - Build coverage matrix
   - Generate `gap-analysis.md` with findings

5. **Generate specification**:
   - Use `templates/spec-template.md` from documentation mission
   - Fill in Documentation Scope section with discovery answers
   - Include gap analysis results if gap-filling mode
   - Define requirements based on selected Divio types and generators
   - Define success criteria (accessibility, completeness, audience satisfaction)

6. **Validate specification**: Run quality checks (see spec-template.md checklist)

7. **Report completion**: Spec file path, next command (`/spec-kitty.plan`)

---

## Key Guidelines

**For Agents**:

- Ask discovery questions one at a time (don't overwhelm user)
- Auto-detect languages to recommend generators
- For gap-filling, show audit results to user before asking what to fill
- Store iteration state in meta.json (enables future iterations)
- Emphasize Divio types in specification (tutorial/how-to/reference/explanation)
- Link to Write the Docs and Divio resources in spec

**For Users**:

- Discovery helps ensure documentation meets real needs
- Gap analysis (if iterating) shows what's missing
- Generator recommendations save manual API documentation work
- Iteration mode affects workflow (initial vs gap-filling vs feature-specific)

```

**Files**: `src/specify_cli/missions/documentation/command-templates/specify.md` (new file)

**Parallel?**: Yes (can be created alongside other command templates)

**Notes**:
- Discovery questions are documentation-specific
- Iteration mode is critical first question
- Language detection and generator recommendations are key value
- Gap analysis only for gap-filling mode
- Store state in meta.json for future iterations

**Quality Validation**:
- Are discovery questions clear and actionable?
- Does it handle all three iteration modes?
- Does it guide generator detection?
- Does it reference Divio types throughout?

### Subtask T021 – Create plan.md Command Template

**Purpose**: Provide instructions for the `/spec-kitty.plan` command specific to documentation missions, including documentation structure design, generator configuration, and gap prioritization.

**Command Context**: The plan command runs during the audit and design phases to create an implementation plan.

**Steps**:
1. Create `src/specify_cli/missions/documentation/command-templates/plan.md`
2. Structure template to guide planning workflow
3. Include documentation-specific planning tasks
4. Reference "audit" and "design" workflow phases

**Content Structure**:
```markdown
# Command Template: /spec-kitty.plan (Documentation Mission)

**Phases**: Audit (if gap-filling), Design
**Purpose**: Plan documentation structure, configure generators, prioritize gaps, design content outline.

## Location Pre-flight Check

Verify you are in the main repository (not a worktree). Documentation mission planning happens in main.

```bash
git branch --show-current  # Should show "main"
```

---

## Planning Interrogation

For documentation missions, planning interrogation is lighter than software-dev:

- **Simple projects** (single language, initial docs): 1-2 questions about structure preferences
- **Complex projects** (multiple languages, existing docs): 2-3 questions about integration approach

**Key Planning Questions**:

**Q1: Documentation Framework**
"Do you have a preferred documentation framework/generator?"

- Sphinx (Python ecosystem standard)
- MkDocs (Markdown-focused, simple)
- Docusaurus (React-based, modern)
- Jekyll (GitHub Pages native)
- None (plain Markdown)

**Why it matters**: Determines build system, theming options, hosting compatibility.

**Q2: Generator Integration Approach** (if multiple languages detected)
"How should API reference for different languages be organized?"

- Unified (all APIs in one reference section)
- Separated (language-specific reference sections)
- Parallel (side-by-side comparison)

**Why it matters**: Affects directory structure, navigation design.

---

## Outline

1. **Setup**: Run `spec-kitty agent feature setup-plan --json` to initialize plan.md

2. **Load context**: Read spec.md, meta.json (especially `documentation_state`)

3. **Phase 0: Research** (if gap-filling mode)

   ### Gap Analysis (gap-filling mode only)

   **Objective**: Audit existing documentation and identify gaps.

   **Steps**:
   1. Scan existing `docs/` directory (or wherever docs live)
   2. Detect documentation framework (Sphinx, MkDocs, Jekyll, etc.)
   3. For each markdown file:
      - Parse frontmatter for `type` field
      - Apply content heuristics if no explicit type
      - Classify as tutorial/how-to/reference/explanation or "unclassified"
   4. Build coverage matrix:
      - Rows: Project areas/features
      - Columns: Divio types (tutorial, how-to, reference, explanation)
      - Cells: Documentation files (or empty if missing)
   5. Calculate coverage percentage
   6. Prioritize gaps:
      - **High**: Missing tutorials (blocks new users)
      - **High**: Missing reference for public APIs
      - **Medium**: Missing how-tos for common tasks
      - **Low**: Missing explanations (nice-to-have)
   7. Generate `gap-analysis.md` with:
      - Current documentation inventory
      - Coverage matrix (markdown table)
      - Prioritized gap list
      - Recommendations

   **Output**: `gap-analysis.md` file in feature directory

   ---

   ### Generator Research (all modes)

   **Objective**: Research generator configuration options for detected languages.

   **For Each Detected Language**:

   **JavaScript/TypeScript → JSDoc/TypeDoc**:
   - Check if JSDoc installed: `npx jsdoc --version`
   - Research config options: output format (HTML/Markdown), template (docdash, clean-jsdoc)
   - Determine source directories to document
   - Plan integration with manual docs

   **Python → Sphinx**:
   - Check if Sphinx installed: `sphinx-build --version`
   - Research extensions: autodoc (API from docstrings), napoleon (Google/NumPy style), viewcode (source links)
   - Research theme: sphinx_rtd_theme (Read the Docs), alabaster (default), pydata-sphinx-theme
   - Plan autodoc configuration (which modules to document)
   - Plan integration with manual docs

   **Rust → rustdoc**:
   - Check if Cargo installed: `cargo doc --help`
   - Research rustdoc options: --no-deps, --document-private-items
   - Plan Cargo.toml metadata configuration
   - Plan integration with manual docs (rustdoc outputs HTML, may need linking)

   **Output**: research.md with generator findings and decisions

4. **Phase 1: Design**

   ### Documentation Structure Design

   **Directory Layout**:
   Design docs/ structure following Divio organization:

   ```
   docs/
   ├── index.md                    # Landing page
   ├── tutorials/                  # Learning-oriented
   │   ├── getting-started.md
   │   └── advanced-usage.md
   ├── how-to/                     # Problem-solving
   │   ├── authentication.md
   │   ├── deployment.md
   │   └── troubleshooting.md
   ├── reference/                  # Technical specs
   │   ├── api/                    # Generated API docs
   │   │   ├── python/             # Sphinx output
   │   │   ├── javascript/         # JSDoc output
   │   │   └── rust/               # rustdoc output
   │   ├── cli.md                  # Manual CLI reference
   │   └── configuration.md        # Manual config reference
   └── explanation/                # Understanding
       ├── architecture.md
       ├── concepts.md
       └── design-decisions.md
   ```

   **Adapt based on**:
   - Selected Divio types (only create directories for selected types)
   - Project size (small projects may flatten structure)
   - Existing docs (extend existing structure if gap-filling)

   ---

   ### Generator Configuration Design

   **For Each Generator**:

   **Sphinx (Python)**:

   ```python
   # docs/conf.py
   project = '{project_name}'
   author = '{author}'
   extensions = [
       'sphinx.ext.autodoc',      # Generate from docstrings
       'sphinx.ext.napoleon',     # Google/NumPy docstring support
       'sphinx.ext.viewcode',     # Link to source
       'sphinx.ext.intersphinx',  # Link to other projects
   ]
   html_theme = 'sphinx_rtd_theme'
   autodoc_default_options = {
       'members': True,
       'undoc-members': False,
       'show-inheritance': True,
   }
   ```

   **JSDoc (JavaScript)**:

   ```json
   {
     "source": {
       "include": ["src/"],
       "includePattern": ".+\\.js$"
     },
     "opts": {
       "destination": "docs/reference/api/javascript",
       "template": "node_modules/docdash",
       "recurse": true
     }
   }
   ```

   **rustdoc (Rust)**:

   ```toml
   [package.metadata.docs.rs]
   all-features = true
   rustdoc-args = ["--document-private-items"]
   ```

   **Output**: Generator config snippets in plan.md, templates ready for implementation

   ---

   ### Data Model

   Generate `data-model.md` with entities:
   - **Documentation Mission**: Iteration state, selected types, configured generators
   - **Divio Documentation Type**: Tutorial, How-To, Reference, Explanation with characteristics
   - **Documentation Generator**: JSDoc, Sphinx, rustdoc configurations
   - **Gap Analysis** (if applicable): Coverage matrix, prioritized gaps

   ---

   ### Work Breakdown

   Outline high-level work packages (detailed in `/spec-kitty.tasks`):

   **For Initial Mode**:
   1. WP01: Structure Setup - Create docs/ dirs, configure generators
   2. WP02: Tutorial Creation - Write selected tutorials
   3. WP03: How-To Creation - Write selected how-tos
   4. WP04: Reference Generation - Generate API docs, write manual reference
   5. WP05: Explanation Creation - Write selected explanations
   6. WP06: Quality Validation - Accessibility checks, link validation, build

   **For Gap-Filling Mode**:
   1. WP01: Gap Analysis Review - Review audit results with user
   2. WP02: High-Priority Gaps - Fill critical missing docs
   3. WP03: Medium-Priority Gaps - Fill important missing docs
   4. WP04: Generator Updates - Regenerate outdated API docs
   5. WP05: Quality Validation - Validate new and updated docs

   **For Feature-Specific Mode**:
   1. WP01: Feature Documentation - Document the specific feature across Divio types
   2. WP02: Integration - Integrate with existing documentation
   3. WP03: Quality Validation - Validate feature docs

   ---

   ### Quickstart

   Generate `quickstart.md` with:
   - How to build documentation locally
   - How to add new documentation (which template to use)
   - How to regenerate API reference
   - How to validate documentation quality

5. **Report completion**:
   - Plan file path
   - Artifacts generated (research.md, data-model.md, gap-analysis.md, quickstart.md, release.md when publish is in scope)
   - Next command: `/spec-kitty.tasks`

---

## Key Guidelines

**For Agents**:

- Run gap analysis only for gap-filling mode
- Auto-detect documentation framework from existing docs
- Configure generators based on detected languages
- Design structure following Divio principles
- Prioritize gaps by user impact (tutorials/reference high, explanations low)
- Plan includes both auto-generated and manual documentation

**For Users**:

- Planning designs documentation structure, doesn't write content yet
- Generator configs enable automated API reference
- Gap analysis (if iterating) shows what needs attention
- Work breakdown will be detailed in `/spec-kitty.tasks`

```

**Files**: `src/specify_cli/missions/documentation/command-templates/plan.md` (new file)

**Parallel?**: Yes (can be created alongside other command templates)

**Notes**:
- Planning includes both audit (gap analysis) and design phases
- Generator configuration is key design activity
- Structure follows Divio organization
- Work breakdown adapts to iteration mode
- Gap prioritization based on user impact

**Quality Validation**:
- Does it guide gap analysis for gap-filling mode?
- Does it cover all three supported generators?
- Does it design Divio-compliant structure?
- Does it adapt to iteration mode?

### Subtask T022 – Create tasks.md Command Template

**Purpose**: Provide instructions for the `/spec-kitty.tasks` command specific to documentation missions, guiding work package generation for documentation work.

**Command Context**: The tasks command runs after planning to break down documentation work into implementable packages.

**Steps**:
1. Create `src/specify_cli/missions/documentation/command-templates/tasks.md`
2. Structure template to guide task generation
3. Include documentation-specific task patterns
4. Reference appropriate workflow phases

**Content Structure**:
```markdown
# Command Template: /spec-kitty.tasks (Documentation Mission)

**Phase**: Design (finalizing work breakdown)
**Purpose**: Break documentation work into independently implementable work packages with subtasks.

## Location Pre-flight Check

Verify you are in the main repository (not a worktree). Documentation mission task generation happens in main.

```bash
git branch --show-current  # Should show "main"
```

---

## Outline

1. **Setup**: Run `spec-kitty agent feature check-prerequisites --json --paths-only --include-tasks`

2. **Load design documents**:
   - spec.md (documentation goals, selected Divio types)
   - plan.md (structure design, generator configs)
   - gap-analysis.md (if gap-filling mode)
   - meta.json (iteration_mode, generators_configured)

3. **Derive fine-grained subtasks**:

   ### Subtask Patterns for Documentation

   **Structure Setup** (all modes):
   - T001: Create `docs/` directory structure
   - T002: Create index.md landing page
   - T003: [P] Configure Sphinx (if Python detected)
   - T004: [P] Configure JSDoc (if JavaScript detected)
   - T005: [P] Configure rustdoc (if Rust detected)
   - T006: Set up build script (Makefile or build.sh)

   **Tutorial Creation** (if tutorial selected):
   - T010: Write "Getting Started" tutorial
   - T011: Write "Basic Usage" tutorial
   - T012: [P] Write "Advanced Topics" tutorial
   - T013: Add screenshots/examples to tutorials
   - T014: Test tutorials with fresh user

   **How-To Creation** (if how-to selected):
   - T020: Write "How to Deploy" guide
   - T021: Write "How to Configure" guide
   - T022: Write "How to Troubleshoot" guide
   - T023: [P] Write additional task-specific guides

   **Reference Generation** (if reference selected):
   - T030: Generate Python API reference (Sphinx autodoc)
   - T031: Generate JavaScript API reference (JSDoc)
   - T032: Generate Rust API reference (cargo doc)
   - T033: Write CLI reference (manual)
   - T034: Write configuration reference (manual)
   - T035: Integrate generated + manual reference
   - T036: Validate all public APIs documented

   **Explanation Creation** (if explanation selected):
   - T040: Write "Architecture Overview" explanation
   - T041: Write "Core Concepts" explanation
   - T042: Write "Design Decisions" explanation
   - T043: [P] Add diagrams illustrating concepts

   **Quality Validation** (all modes):
   - T050: Validate heading hierarchy
   - T051: Validate all images have alt text
   - T052: Check for broken internal links
   - T053: Check for broken external links
   - T054: Verify code examples work
   - T055: Check bias-free language
   - T056: Build documentation site
   - T057: Deploy to hosting (if applicable)

4. **Roll subtasks into work packages**:

   ### Work Package Patterns

   **For Initial Mode**:
   - WP01: Structure & Generator Setup (T001-T006)
   - WP02: Tutorial Documentation (T010-T014) - If tutorials selected
   - WP03: How-To Documentation (T020-T023) - If how-tos selected
   - WP04: Reference Documentation (T030-T036) - If reference selected
   - WP05: Explanation Documentation (T040-T043) - If explanation selected
   - WP06: Quality Validation (T050-T057)

   **For Gap-Filling Mode**:
   - WP01: High-Priority Gaps (tasks for critical missing docs from gap analysis)
   - WP02: Medium-Priority Gaps (tasks for important missing docs)
   - WP03: Generator Updates (regenerate outdated API docs)
   - WP04: Quality Validation (validate all docs, old and new)

   **For Feature-Specific Mode**:
   - WP01: Feature Documentation (tasks for documenting the feature across selected Divio types)
   - WP02: Integration (tasks for integrating feature docs with existing docs)
   - WP03: Quality Validation (validate feature-specific docs)

   ### Prioritization

   - **P0 (foundation)**: Structure setup, generator configuration
   - **P1 (critical)**: Tutorials (if new users), Reference (if API docs missing)
   - **P2 (important)**: How-Tos (solve known problems), Explanation (understanding)
   - **P3 (polish)**: Quality validation, accessibility improvements

5. **Write `tasks.md`**:
   - Use `templates/tasks-template.md` from documentation mission
   - Include work packages with subtasks
   - Mark parallel opportunities (`[P]`)
   - Define dependencies (WP01 must complete before others)
   - Identify MVP scope (typically WP01 + Reference generation)

6. **Generate prompt files**:
   - Create flat `FEATURE_DIR/tasks/` directory (no subdirectories!)
   - For each work package:
     - Generate `WPxx-slug.md` using `templates/task-prompt-template.md`
     - Include objectives, context, subtask guidance
     - Add quality validation strategy (documentation-specific)
     - Include Divio compliance checks
     - Add accessibility/inclusivity checklists
     - Set `lane: "planned"` in frontmatter

7. **Report**:
   - Path to tasks.md
   - Work package count and subtask tallies
   - Parallelization opportunities
   - MVP recommendation
   - Next command: `/spec-kitty.implement WP01` (or review tasks.md first)

---

## Documentation-Specific Task Generation Rules

**Generator Subtasks**:

- Mark generators as `[P]` (parallel) - different languages can generate simultaneously
- Include tool check subtasks (verify sphinx-build, npx, cargo available)
- Include config generation subtasks (create conf.py, jsdoc.json)
- Include actual generation subtasks (run the generator)
- Include integration subtasks (link generated docs into manual structure)

**Content Authoring Subtasks**:

- One subtask per document (don't bundle "write all tutorials" into one task)
- Mark independent docs as `[P]` (parallel) - different docs can be written simultaneously
- Include validation subtasks (test tutorials, verify how-tos solve problems)

**Quality Validation Subtasks**:

- Mark validation checks as `[P]` (parallel) - different checks can run simultaneously
- Include automated checks (link checker, spell check, build)
- Include manual checks (accessibility review, Divio compliance)

**Work Package Scope**:

- Each Divio type typically gets its own work package (WP for tutorials, WP for how-tos, etc.)
- Exception: Small projects may combine types if only 1-2 docs per type
- Generator setup is always separate (WP01 foundation)
- Quality validation is always separate (final WP)

---

## Key Guidelines

**For Agents**:

- Adapt work packages to iteration mode
- For gap-filling, work packages target specific gaps from audit
- Mark generator invocations as parallel (different languages)
- Mark independent docs as parallel (different files)
- Include Divio compliance in Definition of Done for each WP
- Quality validation is final work package (depends on all others)

**For Users**:

- Tasks.md shows the full work breakdown
- Work packages are independently implementable
- MVP often just structure + reference (API docs)
- Full documentation includes all Divio types
- Parallel work packages can be implemented simultaneously

```

**Files**: `src/specify_cli/missions/documentation/command-templates/tasks.md` (new file)

**Parallel?**: Yes (can be created alongside other command templates)

**Notes**:
- Task patterns specific to documentation work
- Work packages organized by Divio type or gap priority
- Subtasks are concrete, actionable documentation tasks
- Parallelization important (generators, independent docs)
- Quality validation always final work package

**Quality Validation**:
- Does it provide clear task patterns for documentation work?
- Does it adapt to all three iteration modes?
- Does it organize by Divio type?
- Does it mark parallelization opportunities?

### Subtask T023 – Create implement.md Command Template

**Purpose**: Provide instructions for the `/spec-kitty.implement` command specific to documentation missions, guiding template generation, generator invocation, and content authoring.

**Command Context**: The implement command runs during the generate phase to create actual documentation.

**Steps**:
1. Create `src/specify_cli/missions/documentation/command-templates/implement.md`
2. Structure template to guide implementation workflow
3. Include documentation-specific implementation guidance
4. Reference "generate" workflow phase

**Content Structure**:
```markdown
# Command Template: /spec-kitty.implement (Documentation Mission)

**Phase**: Generate
**Purpose**: Create documentation from templates, invoke generators for reference docs, populate templates with content.

## Implementation Workflow

Documentation implementation differs from code implementation:
- **No worktrees created** - Documentation work happens in main repository docs/ directory
- **Templates populated** - Use Divio templates as starting point
- **Generators invoked** - Run JSDoc/Sphinx/rustdoc to create API reference
- **Content authored** - Write tutorial/how-to/explanation content
- **Quality validated** - Check accessibility, links, build

---

## Per-Work-Package Implementation

### For WP01: Structure & Generator Setup

**Objective**: Create directory structure and configure doc generators.

**Steps**:
1. Create docs/ directory structure:
   ```bash
   mkdir -p docs/{tutorials,how-to,reference/api,explanation}
   ```

2. Create index.md landing page:

   ```markdown
   # {Project Name} Documentation

   Welcome to the documentation for {Project Name}.

   ## Getting Started

   - [Tutorials](tutorials/) - Learn by doing
   - [How-To Guides](how-to/) - Solve specific problems
   - [Reference](reference/) - Technical specifications
   - [Explanation](explanation/) - Understand concepts
   ```

3. Configure generators (per plan.md):
   - For Sphinx: Create docs/conf.py from template
   - For JSDoc: Create jsdoc.json from template
   - For rustdoc: Update Cargo.toml with metadata
4. Create build script:

   ```bash
   #!/bin/bash
   # build-docs.sh

   # Build Python docs with Sphinx
   sphinx-build -b html docs/ docs/_build/html/

   # Build JavaScript docs with JSDoc
   npx jsdoc -c jsdoc.json

   # Build Rust docs
   cargo doc --no-deps

   echo "Documentation built successfully!"
   ```

5. Test build: Run build script, verify no errors

**Deliverables**:

- docs/ directory structure
- index.md landing page
- Generator configs (conf.py, jsdoc.json, Cargo.toml)
- build-docs.sh script
- Successful test build

---

### For WP02-05: Content Creation (Tutorials, How-Tos, Reference, Explanation)

**Objective**: Write documentation content using Divio templates.

**Steps**:

1. **Select appropriate Divio template**:
   - Tutorial: Use `templates/divio/tutorial-template.md`
   - How-To: Use `templates/divio/howto-template.md`
   - Reference: Use `templates/divio/reference-template.md` (for manual reference)
   - Explanation: Use `templates/divio/explanation-template.md`

2. **Copy template to docs/**:

   ```bash
   # Example for tutorial
   cp templates/divio/tutorial-template.md docs/tutorials/getting-started.md
   ```

3. **Fill in frontmatter**:

   ```yaml
   ---
   type: tutorial
   audience: "beginners"
   purpose: "Learn how to get started with {Project}"
   created: "2026-01-12"
   estimated_time: "15 minutes"
   prerequisites: "Python 3.11+, pip"
   ---
   ```

4. **Replace placeholders with content**:
   - {Title} → Actual title
   - [Description] → Actual description
   - [Step actions] → Actual step-by-step instructions
   - [Examples] → Real code examples

5. **Follow Divio principles for this type**:
   - **Tutorial**: Learning-oriented, step-by-step, show results at each step
   - **How-To**: Goal-oriented, assume experience, solve specific problem
   - **Reference**: Information-oriented, complete, consistent format
   - **Explanation**: Understanding-oriented, conceptual, discuss alternatives

6. **Add real examples and content**:
   - Use actual project APIs, not placeholders
   - Test all code examples (they must work!)
   - Add real screenshots (with alt text)
   - Use diverse example names (not just "John")

7. **Validate against checklists**:
   - Divio compliance (correct type characteristics?)
   - Accessibility (heading hierarchy, alt text, clear language?)
   - Inclusivity (diverse examples, neutral language?)

**For Reference Documentation**:

**Auto-Generated Reference** (API docs):

1. Ensure code has good doc comments:
   - Python: Docstrings with Google/NumPy format
   - JavaScript: JSDoc comments with @param, @returns
   - Rust: /// doc comments
2. Run generator:

   ```bash
   # Sphinx (Python)
   sphinx-build -b html docs/ docs/_build/html/

   # JSDoc (JavaScript)
   npx jsdoc -c jsdoc.json

   # rustdoc (Rust)
   cargo doc --no-deps --document-private-items
   ```

3. Review generated output:
   - Are all public APIs present?
   - Are descriptions clear?
   - Are examples included?
   - Are links working?
4. If generated docs have gaps:
   - Add/improve doc comments in source code
   - Regenerate
   - Or supplement with manual reference

**Manual Reference** (CLI, config, data formats):

1. Use reference template
2. Document every option, every command, every field
3. Be consistent in format (use tables)
4. Include examples for each item

**Deliverables**:

- Completed documentation files in docs/
- All templates filled with real content
- All code examples tested and working
- All Divio type principles followed
- All accessibility/inclusivity checklists satisfied

---

### For WP06: Quality Validation

**Objective**: Validate documentation quality before considering complete.

**Steps**:

1. **Automated checks**:

   ```bash
   # Check heading hierarchy
   find docs/ -name "*.md" -exec grep -E '^#+' {} + | head -50

   # Check for broken links
   markdown-link-check docs/**/*.md

   # Check for missing alt text
   grep -r '!\[.*\](' docs/ | grep -v '\[.*\]' || echo "✓ All images have alt text"

   # Spell check
   aspell check docs/**/*.md

   # Build check
   ./build-docs.sh 2>&1 | grep -i error || echo "✓ Build successful"
   ```

2. **Manual checks**:
   - Read each doc as target audience
   - Follow tutorials - do they work?
   - Try how-tos - do they solve problems?
   - Check reference - is it complete?
   - Read explanations - do they clarify?

3. **Divio compliance check**:
   - Is each doc correctly classified?
   - Does it follow principles for its type?
   - Is it solving the right problem for that type?

4. **Accessibility check**:
   - Proper heading hierarchy?
   - All images have alt text?
   - Clear language (not jargon-heavy)?
   - Links are descriptive?

5. **Peer review**:
   - Have someone from target audience review
   - Gather feedback on clarity, completeness, usability
   - Revise based on feedback

6. **Final build and deploy** (if applicable):

   ```bash
   # Build final documentation
   ./build-docs.sh

   # Deploy to hosting (example for GitHub Pages)
   # (Deployment steps depend on hosting platform)
   ```

**Deliverables**:

- All automated checks passing
- Manual review completed with feedback addressed
- Divio compliance verified
- Accessibility compliance verified
- Final build successful
- Documentation deployed (if applicable)

---

## Key Guidelines

**For Agents**:

- Use Divio templates as starting point, not empty files
- Fill templates with real content, not more placeholders
- Test all code examples before committing
- Follow Divio principles strictly for each type
- Run generators for reference docs (don't write API docs manually)
- Validate quality at end (automated + manual checks)

**For Users**:

- Implementation creates actual documentation, not just structure
- Templates provide guidance, you provide content
- Generators handle API reference, you write the rest
- Quality validation ensures documentation is actually useful
- Peer review from target audience is valuable

---

## Common Pitfalls

**DON'T**:

- Mix Divio types (tutorial that explains concepts, how-to that teaches basics)
- Skip testing code examples (broken examples break trust)
- Use only Western male names in examples
- Say "simply" or "just" or "obviously" (ableist language)
- Skip alt text for images (accessibility barrier)
- Write jargon-heavy prose (clarity issue)
- Commit before validating (quality issue)

**DO**:

- Follow Divio principles for each type
- Test every code example
- Use diverse names in examples
- Use welcoming, clear language
- Add descriptive alt text
- Define technical terms
- Validate before considering complete

```

**Files**: `src/specify_cli/missions/documentation/command-templates/implement.md` (new file)

**Parallel?**: Yes (can be created alongside other command templates)

**Notes**:
- Implementation is about creating content, not code
- Uses Divio templates as starting point
- Generators create API reference automatically
- Quality validation is integral part of implementation
- No worktrees needed (docs/ in main repo)

**Quality Validation**:
- Does it guide use of Divio templates?
- Does it explain generator invocation?
- Does it emphasize quality validation?
- Does it list common pitfalls?

### Subtask T024 – Create review.md Command Template

**Purpose**: Provide instructions for the `/spec-kitty.review` command specific to documentation missions, guiding quality checks, Divio compliance validation, and completeness review.

**Command Context**: The review command runs during the validate phase to assess documentation quality.

**Steps**:
1. Create `src/specify_cli/missions/documentation/command-templates/review.md`
2. Structure template to guide review workflow
3. Include documentation-specific review criteria
4. Reference "validate" workflow phase

**Content Structure**:
```markdown
# Command Template: /spec-kitty.review (Documentation Mission)

**Phase**: Validate
**Purpose**: Review documentation for Divio compliance, accessibility, completeness, and quality.

## Review Philosophy

Documentation review is NOT code review:
- **Not about correctness** (code is about bugs) but **usability** (can readers accomplish their goals?)
- **Not about style** but **accessibility** (can everyone use these docs?)
- **Not about completeness** (covering every edge case) but **usefulness** (solving real problems)
- **Not pass/fail** but **continuous improvement**

---

## Review Checklist

### 1. Divio Type Compliance

For each documentation file, verify it follows principles for its declared type:

**Tutorial Review**:
- [ ] Learning-oriented (teaches by doing, not explaining)?
- [ ] Step-by-step progression with clear sequence?
- [ ] Each step shows immediate, visible result?
- [ ] Minimal explanations (links to explanation docs instead)?
- [ ] Assumes beginner level (no unexplained prerequisites)?
- [ ] Reliable (will work for all users following instructions)?
- [ ] Achieves concrete outcome (learner can do something new)?

**How-To Review**:
- [ ] Goal-oriented (solves specific problem)?
- [ ] Assumes experienced user (not teaching basics)?
- [ ] Practical steps, minimal explanation?
- [ ] Flexible (readers can adapt to their situation)?
- [ ] Includes common variations?
- [ ] Links to reference for details, explanation for "why"?
- [ ] Title starts with "How to..."?

**Reference Review**:
- [ ] Information-oriented (describes what exists)?
- [ ] Complete (all APIs/options/commands documented)?
- [ ] Consistent format (same structure for similar items)?
- [ ] Accurate (matches actual behavior)?
- [ ] Includes usage examples (not just descriptions)?
- [ ] Structured around code organization?
- [ ] Factual tone (no opinions or recommendations)?

**Explanation Review**:
- [ ] Understanding-oriented (clarifies concepts)?
- [ ] Not instructional (not teaching how-to-do)?
- [ ] Discusses concepts, design decisions, trade-offs?
- [ ] Compares with alternatives fairly?
- [ ] Makes connections between ideas?
- [ ] Provides context and background?
- [ ] Identifies limitations and when (not) to use?

**If type is wrong or mixed**:
- Return with feedback: "This is classified as {type} but reads like {actual_type}. Either reclassify or rewrite to match {type} principles."

---

### 2. Accessibility Review

**Heading Hierarchy**:
- [ ] One H1 per document (the title)
- [ ] H2s for major sections
- [ ] H3s for subsections under H2s
- [ ] No skipped levels (H1 → H3 is wrong)
- [ ] Headings are descriptive (not "Introduction", "Section 2")

**Images**:
- [ ] All images have alt text
- [ ] Alt text describes what image shows (not "image" or "screenshot")
- [ ] Decorative images have empty alt text (`![]()`)
- [ ] Complex diagrams have longer descriptions

**Language**:
- [ ] Clear, plain language (technical terms defined)
- [ ] Active voice ("run the command" not "the command should be run")
- [ ] Present tense ("returns" not "will return")
- [ ] Short sentences (15-20 words max)
- [ ] Short paragraphs (3-5 sentences)

**Links**:
- [ ] Link text is descriptive ("see the installation guide" not "click here")
- [ ] Links are not bare URLs (use markdown links)
- [ ] No broken links (test all links)

**Code Blocks**:
- [ ] All code blocks have language tags for syntax highlighting
- [ ] Expected output is shown (not just commands)
- [ ] Code examples actually work (tested)

**Tables**:
- [ ] Tables have headers
- [ ] Headers use `|---|` syntax
- [ ] Tables are not too wide (wrap if needed)

**Lists**:
- [ ] Proper markdown lists (not paragraphs with commas)
- [ ] Consistent bullet style
- [ ] Items are parallel in structure

**If accessibility issues found**:
- Return with feedback listing specific issues and how to fix

---

### 3. Inclusivity Review

**Examples and Names**:
- [ ] Uses diverse names (not just Western male names)
- [ ] Names span different cultures and backgrounds
- [ ] Avoids stereotypical name choices

**Language**:
- [ ] Gender-neutral ("they" not "he/she", "developers" not "guys")
- [ ] Avoids ableist language ("just", "simply", "obviously", "easy" imply reader inadequacy)
- [ ] Person-first language where appropriate ("person with disability" not "disabled person")
- [ ] Avoids idioms (cultural-specific phrases that don't translate)

**Cultural Assumptions**:
- [ ] No religious references (Christmas, Ramadan, etc.)
- [ ] No cultural-specific examples (American holidays, sports, food)
- [ ] Date formats explained (ISO 8601 preferred)
- [ ] Currency and units specified (USD, meters, etc.)

**Tone**:
- [ ] Welcoming to newcomers (not intimidating)
- [ ] Assumes good faith (users aren't "doing it wrong")
- [ ] Encouraging (celebrates progress)

**If inclusivity issues found**:
- Return with feedback listing examples to change

---

### 4. Completeness Review

**For Initial Documentation**:
- [ ] All selected Divio types are present
- [ ] Tutorials enable new users to get started
- [ ] Reference covers all public APIs
- [ ] How-tos address common problems (from user research or support tickets)
- [ ] Explanations clarify key concepts and design

**For Gap-Filling**:
- [ ] High-priority gaps from audit are filled
- [ ] Outdated docs are updated
- [ ] Coverage percentage improved

**For Feature-Specific**:
- [ ] Feature is documented across relevant Divio types
- [ ] Feature docs integrate with existing documentation
- [ ] Feature is discoverable (linked from main index, relevant how-tos, etc.)

**Common Gaps**:
- [ ] Installation/setup covered (tutorial or how-to)?
- [ ] Common tasks have how-tos?
- [ ] All public APIs in reference?
- [ ] Error messages explained (troubleshooting how-tos)?
- [ ] Architecture/design explained (explanation)?

**If completeness gaps found**:
- Return with feedback listing missing documentation

---

### 5. Quality Review

**Tutorial Quality**:
- [ ] Tutorial actually works (reviewer followed it successfully)?
- [ ] Each step shows result (not "do X, Y, Z" without checkpoints)?
- [ ] Learner accomplishes something valuable?
- [ ] Appropriate for stated audience?

**How-To Quality**:
- [ ] Solves the stated problem?
- [ ] Steps are clear and actionable?
- [ ] Reader can adapt to their situation?
- [ ] Links to reference for details?

**Reference Quality**:
- [ ] Descriptions match actual behavior (not outdated)?
- [ ] Examples work (not broken or misleading)?
- [ ] Format is consistent across similar items?
- [ ] Search-friendly (clear headings, keywords)?

**Explanation Quality**:
- [ ] Concepts are clarified (not more confusing)?
- [ ] Design rationale is clear?
- [ ] Alternatives are discussed fairly?
- [ ] Trade-offs are identified?

**General Quality**:
- [ ] Documentation builds without errors
- [ ] No broken links (internal or external)
- [ ] No spelling errors
- [ ] Code examples work
- [ ] Images load correctly

**If quality issues found**:
- Return with feedback describing issues and how to improve

---

## Review Process

1. **Load work package**:
   - Read WP prompt file (e.g., `tasks/WP02-tutorials.md`)
   - Identify which documentation was created/updated

2. **Review each document** against checklists above

3. **Build documentation** and verify:
   ```bash
   ./build-docs.sh
   ```

- Check for build errors/warnings
- Navigate to docs in browser
- Test links, images, navigation

4. **Test tutorials** (if present):
   - Follow tutorial steps exactly
   - Verify each step works
   - Confirm outcome is achieved

5. **Test how-tos** (if present):
   - Attempt to solve the problem using the guide
   - Verify solution works

6. **Validate generated reference** (if present):
   - Check auto-generated API docs
   - Verify all public APIs present
   - Check descriptions are clear

7. **Decide**:

   **If all checks pass**:
   - Move WP to "done" lane
   - Update activity log with approval
   - Proceed to next WP

   **If issues found**:
   - Populate Review Feedback section in WP prompt
   - List specific issues with locations and fix guidance
   - Set `review_status: has_feedback`
   - Move WP back to "planned" or "doing"
   - Notify implementer

---

## Review Feedback Format

When returning work for changes, use this format:

```markdown
## Review Feedback

### Divio Type Compliance

**Issue**: docs/tutorials/getting-started.md is classified as tutorial but reads like how-to (assumes too much prior knowledge).

**Fix**: Either:
- Reclassify as how-to (change frontmatter `type: how-to`)
- Rewrite to be learning-oriented for beginners (add prerequisites section, simplify steps, show results at each step)

### Accessibility

**Issue**: docs/tutorials/getting-started.md has image without alt text (line 45).

**Fix**: Add alt text describing what the image shows:
```markdown
![Screenshot showing the welcome screen after successful login](images/welcome.png)
```

### Inclusivity

**Issue**: docs/how-to/authentication.md uses only male names in examples ("Bob", "John", "Steve").

**Fix**: Use diverse names: "Aisha", "Yuki", "Carlos", "Alex".

### Completeness

**Issue**: Public API `DocumentGenerator.configure()` is not documented in reference.

**Fix**: Add entry to docs/reference/api.md or regenerate API docs if using auto-generation.

### Quality

**Issue**: Tutorial step 3 command fails (missing required --flag option).

**Fix**: Add --flag to command on line 67:

```bash
command --flag --other-option value
```

```

---

## Key Guidelines

**For Reviewers**:
- Focus on usability and accessibility, not perfection
- Provide specific, actionable feedback with line numbers
- Explain why something is an issue (educate, don't just reject)
- Test tutorials and how-tos by actually following them
- Check Divio type compliance carefully (most common issue)

**For Implementers**:
- Review feedback is guidance, not criticism
- Address all feedback items before re-submitting
- Mark `review_status: acknowledged` when you understand feedback
- Update activity log as you address each item

---

## Success Criteria

Documentation is ready for "done" when:
- [ ] All Divio type principles followed
- [ ] All accessibility checks pass
- [ ] All inclusivity checks pass
- [ ] All completeness requirements met
- [ ] All quality validations pass
- [ ] Documentation builds successfully
- [ ] Tutorials work when followed
- [ ] How-tos solve stated problems
- [ ] Reference is complete and accurate
- [ ] Explanations clarify concepts
```

**Files**: `src/specify_cli/missions/documentation/command-templates/review.md` (new file)

**Parallel?**: Yes (can be created alongside other command templates)

**Notes**:

- Review is about usability, not perfection
- Divio compliance is primary concern
- Accessibility and inclusivity are non-negotiable
- Completeness depends on iteration mode
- Quality means "does it help users?"

**Quality Validation**:

- Does it provide comprehensive review checklists?
- Does it cover all Divio types?
- Does it include accessibility and inclusivity?
- Does it guide actionable feedback?

## Test Strategy

**Unit Tests** (to be implemented in WP09):

1. Test command templates exist:

   ```python
   def test_documentation_command_templates_exist():
       mission = get_mission_by_name("documentation")
       commands = mission.list_commands()

       assert "specify" in commands
       assert "plan" in commands
       assert "tasks" in commands
       assert "implement" in commands
       assert "review" in commands
   ```

2. Test command templates reference documentation phases:

   ```python
   @pytest.mark.parametrize("command_name,expected_phase", [
       ("specify", "discover"),
       ("plan", "audit"),  # or "design"
       ("tasks", "design"),
       ("implement", "generate"),
       ("review", "validate"),
   ])
   def test_command_template_references_phase(command_name, expected_phase):
       mission = get_mission_by_name("documentation")
       template = mission.get_command_template(command_name)
       content = template.read_text()

       # Check that the template references the appropriate phase
       assert expected_phase.lower() in content.lower()
   ```

3. Test command templates mention Divio types:

   ```python
   def test_command_templates_mention_divio_types():
       mission = get_mission_by_name("documentation")

       for command in ["specify", "plan", "tasks", "implement", "review"]:
           template = mission.get_command_template(command)
           content = template.read_text().lower()

           # Should mention at least one Divio type
           assert any(dtype in content for dtype in ["tutorial", "how-to", "reference", "explanation"])
   ```

**Manual Validation**:

1. Read each command template as an AI agent:
   - Are instructions clear?
   - Are steps actionable?
   - Is guidance specific to documentation missions?
   - Do examples help understanding?

2. Verify command templates reference correct phases:
   - specify → discover
   - plan → audit, design
   - tasks → design
   - implement → generate
   - review → validate

3. Check for documentation-specific guidance:
   - Divio types mentioned?
   - Generators explained?
   - Gap analysis covered (for plan)?
   - Quality validation detailed (for review)?

4. Test template loading:

   ```python
   from specify_cli.mission import get_mission_by_name

   mission = get_mission_by_name("documentation")

   for command in ["specify", "plan", "tasks", "implement", "review"]:
       try:
           template = mission.get_command_template(command)
           print(f"✓ {command} template loads successfully")
       except Exception as e:
           print(f"✗ {command} template failed: {e}")
   ```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Command templates too generic | High - doesn't guide documentation-specific work | Include concrete examples, Divio references, generator commands |
| Command templates too prescriptive | Medium - stifles agent flexibility | Provide guidance but allow adaptation |
| Missing documentation workflow concepts | High - agents don't understand documentation mission | Reference Divio, generators, gap analysis throughout |
| Templates don't match mission.yaml commands | High - inconsistent experience | Validate command names match mission.yaml |
| Too similar to software-dev commands | High - agents treat docs like code | Emphasize differences, documentation-specific language |

## Definition of Done Checklist

- [ ] `command-templates/` subdirectory exists
- [ ] `specify.md` created with:
  - [ ] Discovery questions for iteration mode, Divio types, generators
  - [ ] References "discover" workflow phase
  - [ ] Includes language detection and generator recommendations
  - [ ] Guides gap analysis for gap-filling mode
  - [ ] Stores state in meta.json
- [ ] `plan.md` created with:
  - [ ] Planning questions for structure and generator integration
  - [ ] References "audit" and "design" workflow phases
  - [ ] Guides gap analysis (audit) for gap-filling mode
  - [ ] Guides documentation structure design (Divio organization)
  - [ ] Guides generator configuration (Sphinx, JSDoc, rustdoc)
  - [ ] Includes work breakdown patterns by iteration mode
- [ ] `tasks.md` created with:
  - [ ] Task generation guidance for documentation work
  - [ ] References "design" workflow phase
  - [ ] Provides subtask patterns (structure, content, generators, validation)
  - [ ] Provides work package patterns by iteration mode and Divio type
  - [ ] Marks parallelization opportunities
  - [ ] Adapts to iteration mode
- [ ] `implement.md` created with:
  - [ ] Implementation guidance for documentation creation
  - [ ] References "generate" workflow phase
  - [ ] Guides use of Divio templates
  - [ ] Guides generator invocation (Sphinx, JSDoc, rustdoc)
  - [ ] Guides content authoring per Divio type
  - [ ] Includes quality validation steps
  - [ ] Lists common pitfalls
- [ ] `review.md` created with:
  - [ ] Review guidance for documentation quality
  - [ ] References "validate" workflow phase
  - [ ] Provides Divio compliance checklists for all 4 types
  - [ ] Provides accessibility review checklist
  - [ ] Provides inclusivity review checklist
  - [ ] Provides completeness review criteria by iteration mode
  - [ ] Provides quality review criteria by Divio type
  - [ ] Guides actionable feedback format
- [ ] All command templates reference documentation mission concepts (Divio, generators, gap analysis)
- [ ] All command templates load successfully via mission system
- [ ] Command names match mission.yaml commands section
- [ ] `tasks.md` in feature directory updated with WP04 status

## Review Guidance

**Key Acceptance Checkpoints**:

1. **Command Existence**: All five command templates created
2. **Documentation-Specific**: Templates are NOT generic (mention Divio, generators, gap analysis)
3. **Workflow Phase References**: Each command references appropriate phase(s)
4. **Actionable Guidance**: Instructions are clear and specific
5. **Examples Included**: Concrete examples of questions, structure, validation

**Validation Commands**:

```bash
# Check command templates exist
ls -la src/specify_cli/missions/documentation/command-templates/

# Test loading
python -c "
from specify_cli.mission import get_mission_by_name
mission = get_mission_by_name('documentation')
commands = mission.list_commands()
print('Commands:', commands)
for cmd in ['specify', 'plan', 'tasks', 'implement', 'review']:
    try:
        path = mission.get_command_template(cmd)
        print(f'✓ {cmd} template loads successfully')
    except Exception as e:
        print(f'✗ {cmd} template failed: {e}')
"

# Check for documentation-specific content
for file in src/specify_cli/missions/documentation/command-templates/*.md; do
    echo "Checking $file for Divio references..."
    grep -i "divio\|tutorial\|how-to\|reference\|explanation" "$file" || echo "⚠️  No Divio references found"
done
```

**Review Focus Areas**:

- Commands are documentation-specific (not generic)
- Each command guides appropriate workflow phase
- Divio types, generators, and gap analysis are explained
- Discovery questions are clear and actionable (specify)
- Planning guidance covers structure and generators (plan)
- Task patterns match documentation work (tasks)
- Implementation guides template use and generators (implement)
- Review checklists are comprehensive (review)

## Activity Log

- 2026-01-12T17:18:56Z – system – lane=planned – Prompt created.
- 2026-01-13T09:10:28Z – codex – lane=planned – Added frontmatter/User Input blocks to documentation mission command templates and cleared review feedback.
- 2026-01-13T08:02:09Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-13T09:04:55Z – agent – lane=doing – Started review via workflow command
- 2026-01-13T09:05:28Z – codex – lane=doing – Review feedback added (frontmatter and User Input blocks required)
- 2026-01-13T09:05:56Z – unknown – lane=planned – Changes requested
- 2026-01-13T09:08:32Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-13T09:08:50Z – unknown – lane=for_review – Auto-moved to for_review after implement workflow
- 2026-01-13T09:08:57Z – agent – lane=doing – Started review via workflow command
- 2026-01-13T09:08:58Z – unknown – lane=planned – Changes requested
- 2026-01-13T09:17:30Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-13T09:17:30Z – unknown – lane=for_review – Auto-moved to for_review after implement workflow
- 2026-01-13T09:17:33Z – agent – lane=doing – Started review via workflow command
- 2026-01-13T09:17:33Z – unknown – lane=done – Review passed
