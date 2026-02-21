---
work_package_id: "WP10"
subtasks:
  - "T077"
  - "T078"
  - "T079"
  - "T080"
  - "T081"
  - "T082"
  - "T083"
  - "T084"
  - "T085"
  - "T086"
title: "Documentation & Agent Updates"
phase: "Phase 2 - Polish"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "82623"
review_status: "approved"
reviewed_by: "Robert Douglass"
dependencies:
  - "WP01"
  - "WP02"
  - "WP03"
  - "WP04"
  - "WP05"
  - "WP06"
  - "WP07"
  - "WP08"
  - "WP09"
history:
  - timestamp: "2026-01-12T17:18:56Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP10 – Documentation & Agent Updates

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

**This WP depends on**: WP01-09 (All implementation and testing work packages)

**Before starting work**:

1. Ensure WP01-09 are complete and merged to main
2. Verify all features work (mission loads, templates exist, generators work, tests pass)
3. Pull latest from main to get all merged changes

**Critical**: This is the final polish work package. All implementation must be complete before documenting it. If features are incomplete, documentation will be incorrect.

---

## Objectives & Success Criteria

**Goal**: Create comprehensive user documentation for the documentation mission, update spec-kitty project docs, and update all 12 AI agent context files to include documentation mission guidance.

**Success Criteria**:

- User guide created at `docs/documentation-mission.md` explaining the feature
- Workflow phases documented with examples (discover, audit, design, generate, validate, publish)
- All 4 Divio types documented with characteristics and when to use
- Iteration modes explained (initial, gap-filling, feature-specific)
- Generator usage documented for JSDoc, Sphinx, rustdoc
- Troubleshooting section with common errors and solutions
- Two complete examples provided (initial project, gap-filling)
- All 12 agent context files updated with documentation mission patterns
- `CLAUDE.md` updated with documentation mission patterns (already done in planning)
- Documentation is clear, accurate, and actionable

## Context & Constraints

**Prerequisites**:

- All WP01-09 complete (features implemented and tested)
- Understanding of documentation mission workflow from implementation
- Access to all 12 agent directories for updates

**Reference Documents**:

- [spec.md](../spec.md) - Full feature requirements
- [plan.md](../plan.md) - Technical design
- [research.md](../research.md) - Write the Docs and Divio research
- [data-model.md](../data-model.md) - Entity definitions
- [quickstart.md](../quickstart.md) - Contributor guide
- CLAUDE.md - Agent context update location
- `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py` - AGENT_DIRS list (lines 53-66)

**Constraints**:

- Documentation must be accurate (reflects actual implementation)
- Must update all 12 agents consistently (use AGENT_DIRS constant)
- Must provide complete examples (users can follow them)
- Must include troubleshooting (common problems and solutions)
- Must follow existing spec-kitty documentation style

**Agent Directories** (from CLAUDE.md):

```python
AGENT_DIRS = [
    (".claude", "commands"),
    (".github", "prompts"),
    (".gemini", "commands"),
    (".cursor", "commands"),
    (".qwen", "commands"),
    (".opencode", "command"),
    (".windsurf", "workflows"),
    (".codex", "prompts"),
    (".kilocode", "workflows"),
    (".augment", "commands"),
    (".roo", "commands"),
    (".amazonq", "prompts"),
]
```

## Subtasks & Detailed Guidance

### Subtask T077 – Create User Guide for Documentation Missions

**Purpose**: Create comprehensive user guide explaining how to use documentation missions.

**Steps**:

1. Create `docs/documentation-mission.md`
2. Structure the guide:

   ```markdown
   # Documentation Mission Guide

   ## Overview

   The documentation mission helps teams create and maintain high-quality software
   documentation following industry best practices:
   - **Write the Docs** principles (docs as code, accessibility, inclusivity)
   - **Divio documentation system** (4 types: tutorial, how-to, reference, explanation)
   - **Automated generation** (JSDoc, Sphinx, rustdoc for API reference)

   ## Quick Start

   ### First-Time Documentation (Initial Mode)

   Create documentation for a new project:

   ```bash
   # 1. Create documentation feature
   /spec-kitty.specify --mission documentation

   # During discovery, you'll be asked:
   # - Iteration mode: Choose "initial"
   # - Target audience: e.g., "developers"
   # - Divio types: e.g., "tutorial, reference"
   # - Confirm generators: e.g., "JSDoc, Sphinx"

   # 2. Plan documentation structure
   /spec-kitty.plan

   # 3. Generate work packages
   /spec-kitty.tasks

   # 4. Implement documentation
   /spec-kitty.implement WP01  # Structure and generators
   /spec-kitty.implement WP02  # Tutorials (if selected)
   /spec-kitty.implement WP03  # Reference (if selected)

   # 5. Review and finalize
   /spec-kitty.review WP01
   /spec-kitty.accept
   ```

   ### Improving Existing Documentation (Gap-Filling Mode)

   Add missing documentation to an existing project:

   ```bash
   # 1. Create gap-filling feature
   /spec-kitty.specify --mission documentation

   # During discovery:
   # - Iteration mode: Choose "gap-filling"
   # - System will audit your docs/ directory
   # - Review gap analysis results
   # - Select which gaps to fill

   # 2. Plan gap-filling work
   /spec-kitty.plan
   # Will show prioritized gaps (HIGH: tutorials, reference; MEDIUM: how-tos; LOW: explanations)

   # 3. Generate work packages targeting gaps
   /spec-kitty.tasks

   # 4. Implement missing documentation
   /spec-kitty.implement WP01  # High-priority gaps
   /spec-kitty.implement WP02  # Medium-priority gaps

   # 5. Review
   /spec-kitty.review WP01
   /spec-kitty.accept
   ```

   ## Concepts

   [Will be detailed in T078-T081]

   ## Examples

   [Will be detailed in T085-T086]

   ## Troubleshooting

   [Will be detailed in T082]

   ```

**Files**: `docs/documentation-mission.md` (new file)

**Parallel?**: No (other subtasks add sections to this file)

**Notes**:

- User-facing documentation
- Clear, practical examples
- Assumes no prior Divio knowledge
- Links to external resources (Write the Docs, Divio)

### Subtask T078 – Document Workflow Phases

**Purpose**: Explain the 6 documentation mission workflow phases with examples.

**Steps**:

1. Add section to `docs/documentation-mission.md`:

   ```markdown
   ## Workflow Phases

   Documentation missions have 6 phases (different from software-dev):

   ### 1. Discover

   **Purpose**: Understand what documentation is needed

   **Questions asked**:
   - Is this initial documentation, gap-filling, or feature-specific?
   - What is the target audience (developers, end-users, contributors)?
   - Which Divio types are most important (tutorial, how-to, reference, explanation)?
   - What languages detected (for generator recommendations)?

   **Outputs**: Feature spec with documentation scope, selected Divio types, recommended generators

   **Command**: `/spec-kitty.specify --mission documentation`

   ---

   ### 2. Audit

   **Purpose**: Analyze existing documentation (gap-filling mode only)

   **Activities**:
   - Scan existing docs/ directory
   - Classify docs into Divio types (explicit frontmatter or content heuristics)
   - Build coverage matrix (which areas have which types)
   - Identify gaps (missing Divio types)
   - Prioritize gaps by user impact (HIGH: tutorials/reference, MEDIUM: how-tos, LOW: explanations)

   **Outputs**: gap-analysis.md with coverage matrix and prioritized gaps

   **When**: Automatically during `/spec-kitty.plan` for gap-filling mode

   ---

   ### 3. Design

   **Purpose**: Plan documentation structure and configure generators

   **Activities**:
   - Design docs/ directory structure (following Divio organization)
   - Configure generators (JSDoc, Sphinx, rustdoc) based on detected languages
   - Plan content outline for each selected Divio type
   - Create work breakdown (which docs to write, which to generate)

   **Outputs**: plan.md with structure design, generator configs, work packages

   **Command**: `/spec-kitty.plan`

   ---

   ### 4. Generate

   **Purpose**: Create documentation from templates and generators

   **Activities**:
   - Copy Divio templates to docs/ directory
   - Fill templates with project-specific content
   - Run generators for API reference (sphinx-build, npx jsdoc, cargo doc)
   - Integrate generated reference with manual docs
   - Populate all placeholders with real content

   **Outputs**: Complete documentation files in docs/, generated API reference

   **Command**: `/spec-kitty.implement WP##`

   ---

   ### 5. Validate

   **Purpose**: Review documentation quality

   **Activities**:
   - Check Divio compliance (each doc follows principles for its type)
   - Check accessibility (heading hierarchy, alt text, clear language)
   - Check inclusivity (diverse examples, bias-free language)
   - Check completeness (all selected types present, no gaps)
   - Check quality (tutorials work, how-tos solve problems, reference complete, explanations clarify)
   - Build documentation (no errors or warnings)

   **Outputs**: Review feedback (if issues), approved documentation (if passing)

   **Command**: `/spec-kitty.review WP##`

   ---

   ### 6. Publish

   **Purpose**: Prepare documentation for hosting (optional)

   **Activities**:
   - Build final documentation site
   - Deploy to hosting platform (Read the Docs, GitHub Pages, etc.)
   - Update documentation links in README

   **Outputs**: Published documentation site, release.md (optional publish guidance)

   **Note**: Publishing is often handled outside spec-kitty (via CI/CD or manual deployment). This phase is for preparation only.
   ```

**Files**: `docs/documentation-mission.md` (modified)

**Parallel?**: Yes (can write sections in parallel, then combine)

**Notes**:

- Each phase explained with purpose, activities, outputs
- Clear progression: discover → audit → design → generate → validate → publish
- Commands shown for each phase
- Examples of what happens in each phase

### Subtask T079 – Document Divio Types

**Purpose**: Explain the 4 Divio documentation types with characteristics and when to use.

**Steps**:

1. Add section to `docs/documentation-mission.md`:

   ```markdown
   ## Divio Documentation Types

   The Divio system organizes documentation into 4 types, each with distinct purpose and audience:

   ### Tutorial (Learning-Oriented)

   **Purpose**: Teach beginners by having them do something

   **Characteristics**:
   - Step-by-step progression
   - Assumes minimal prior knowledge
   - Each step shows immediate result
   - Focus on doing, not explaining
   - Learner accomplishes something concrete

   **When to use**:
   - Onboarding new users
   - Teaching a specific skill or capability
   - First exposure to your project

   **Example**: "Getting Started with Spec Kitty" - walks user through creating their first feature

   **Don't use for**:
   - Solving specific problems (use how-to)
   - Explaining concepts (use explanation)
   - Listing all options (use reference)

   ---

   ### How-To Guide (Goal-Oriented)

   **Purpose**: Help experienced users solve specific problems

   **Characteristics**:
   - Focused on a single goal/problem
   - Assumes basic familiarity with system
   - Practical steps with minimal explanation
   - Flexible (reader adapts to their situation)
   - Includes common variations

   **When to use**:
   - Solving a specific, practical problem
   - Addressing common user questions
   - Showing best practices for tasks

   **Example**: "How to Deploy Spec Kitty to Production" - solves deployment problem

   **Don't use for**:
   - Teaching basics (use tutorial)
   - Explaining why (use explanation)
   - Documenting all APIs (use reference)

   ---

   ### Reference (Information-Oriented)

   **Purpose**: Provide technical specifications and API details

   **Characteristics**:
   - Complete and accurate
   - Structured around code organization
   - Consistent format for similar items
   - Factual descriptions (no opinions)
   - Includes usage examples

   **When to use**:
   - Documenting APIs, CLIs, configuration options
   - Listing all available features/options
   - Providing technical specifications

   **Example**: "Spec Kitty CLI Reference" - documents all commands and options

   **Can be auto-generated**: Use JSDoc (JS/TS), Sphinx (Python), rustdoc (Rust) for API reference

   **Don't use for**:
   - Step-by-step instructions (use tutorial/how-to)
   - Conceptual explanations (use explanation)

   ---

   ### Explanation (Understanding-Oriented)

   **Purpose**: Help users understand concepts, design decisions, and architecture

   **Characteristics**:
   - Conceptual discussion (not instructional)
   - Provides context and background
   - Discusses alternatives and trade-offs
   - Makes connections between ideas
   - Explains "why" behind design

   **When to use**:
   - Explaining architecture or design decisions
   - Clarifying complex concepts
   - Discussing why certain approaches were chosen
   - Providing background and context

   **Example**: "Why Spec Kitty Uses Workspace-per-WP" - explains design rationale

   **Don't use for**:
   - Teaching how to do something (use tutorial/how-to)
   - Listing technical details (use reference)

   ---

   ### Quick Decision Guide

   **Ask yourself: What does the reader want?**

   - **"I want to learn this"** → Tutorial (teach them by doing)
   - **"I want to solve X"** → How-To (give them a recipe)
   - **"What are all the options?"** → Reference (list everything)
   - **"Why was it designed this way?"** → Explanation (clarify the reasoning)

   **Most projects need**:
   - At least 1 tutorial (get new users started)
   - At least 1 reference (document the API/CLI)
   - How-tos for common problems (based on user feedback)
   - Explanations for complex concepts (optional, but valuable)
   ```

**Files**: `docs/documentation-mission.md` (modified)

**Parallel?**: Yes (can write Divio section alongside other sections)

**Notes**:

- Clear distinctions between types
- Concrete examples from spec-kitty itself
- Decision guide helps users choose right type
- Emphasizes what NOT to use each type for

### Subtask T080 – Document Iteration Modes

**Purpose**: Explain the three iteration modes and when to use each.

**Steps**:

1. Add section to `docs/documentation-mission.md`:

   ```markdown
   ## Iteration Modes

   Documentation missions support three iteration modes, each with different workflows:

   ### Initial Mode

   **Use when**: Creating documentation for the first time (no existing docs)

   **Workflow**:
   1. **Discover**: Select target audience, choose Divio types, confirm generators
   2. **Design**: Plan docs/ structure from scratch, configure generators
   3. **Generate**: Create all selected documentation
   4. **Validate**: Review for quality and completeness

   **Characteristics**:
   - No gap analysis (nothing to audit)
   - Creates complete documentation structure
   - All selected Divio types generated
   - Generators configured for detected languages

   **Example**:
   ```bash
   /spec-kitty.specify --mission documentation
   # Choose: initial mode, audience=developers, types=[tutorial, reference], generators=[Sphinx]

   /spec-kitty.plan
   # Designs docs/ structure: tutorials/, reference/api/

   /spec-kitty.tasks
   # Creates WPs: WP01 (structure+Sphinx), WP02 (tutorials), WP03 (reference)

   /spec-kitty.implement WP01
   # Sets up docs/ directory, configures Sphinx, generates API reference

   /spec-kitty.implement WP02
   # Writes getting-started tutorial from template
   ```

   ---

   ### Gap-Filling Mode

   **Use when**: Improving existing documentation (some docs exist, need to add more)

   **Workflow**:
   1. **Discover**: Confirm gap-filling mode
   2. **Audit**: System analyzes existing docs, builds coverage matrix, identifies gaps
   3. **Design**: Plan work to fill high-priority gaps
   4. **Generate**: Create missing documentation
   5. **Validate**: Review new docs integrate with existing docs

   **Characteristics**:
   - Gap analysis runs automatically
   - Coverage matrix shows what exists vs what's missing
   - Gaps prioritized by user impact (HIGH: tutorials/reference, MEDIUM: how-tos, LOW: explanations)
   - Work focuses on filling specific gaps (not creating everything)

   **Example**:

   ```bash
   /spec-kitty.specify --mission documentation
   # Choose: gap-filling mode

   # System audits docs/ and shows:
   # Coverage Matrix:
   # | Area | Tutorial | How-To | Reference | Explanation |
   # |------|----------|--------|-----------|-------------|
   # | CLI  | ✗        | ✓      | ✓         | ✗           |
   # | API  | ✗        | ✗      | ✓         | ✗           |
   #
   # Gaps: [HIGH] CLI → Tutorial, [MEDIUM] API → How-To

   /spec-kitty.plan
   # Plans work packages targeting high-priority gaps

   /spec-kitty.tasks
   # Creates WPs: WP01 (CLI tutorial), WP02 (API how-tos)

   /spec-kitty.implement WP01
   # Writes CLI tutorial filling the gap
   ```

   ---

   ### Feature-Specific Mode

   **Use when**: Documenting a specific new feature or module

   **Workflow**:
   1. **Discover**: Identify which feature to document, which aspects need docs
   2. **Design**: Plan documentation for just that feature
   3. **Generate**: Create feature-specific docs across relevant Divio types
   4. **Validate**: Ensure feature docs integrate with existing docs

   **Characteristics**:
   - Narrow scope (just the feature)
   - May use multiple Divio types for one feature (tutorial + how-to + reference)
   - Integrates with existing documentation structure
   - May update existing docs (add feature to existing how-tos, reference)

   **Example**:

   ```bash
   /spec-kitty.specify --mission documentation
   # Choose: feature-specific mode, feature="authentication module"
   # Select types: tutorial, how-to, reference

   /spec-kitty.plan
   # Plans docs for authentication feature only

   /spec-kitty.tasks
   # Creates WPs: WP01 (auth tutorial), WP02 (auth how-tos), WP03 (auth API reference)

   /spec-kitty.implement WP01
   # Writes "Getting Started with Authentication" tutorial
   ```

   ---

   ### Choosing Iteration Mode

   | Situation | Mode | Reason |
   |-----------|------|--------|
   | Brand new project, no docs yet | Initial | Create complete documentation structure |
   | Have API docs, need tutorials | Gap-Filling | Audit identifies missing tutorials |
   | Just shipped new feature | Feature-Specific | Document just the new feature |
   | Users report confusion | Gap-Filling | Audit finds gaps, prioritizes by impact |
   | Annual doc review | Gap-Filling | Check for outdated docs, fill gaps |

   ```

**Files**: `docs/documentation-mission.md` (modified)

**Parallel?**: Yes (can write alongside other sections)

**Notes**:

- All three modes explained with workflows
- Examples show actual commands and outputs
- Decision guide helps users choose mode
- Emphasizes when each mode is appropriate

### Subtask T081 – Document Generator Usage

**Purpose**: Explain how to use JSDoc, Sphinx, and rustdoc generators for API reference.

**Steps**:

1. Add section to `docs/documentation-mission.md`:

   ```markdown
   ## Automated API Documentation Generators

   Documentation missions can automatically generate API reference from code comments/docstrings.

   ### Sphinx (Python Projects)

   **What it does**: Generates API reference from Python docstrings

   **Requirements**:
   - Python project with docstrings
   - Sphinx installed: `pip install sphinx sphinx-rtd-theme`

   **How it works**:
   1. System detects .py files or setup.py/pyproject.toml
   2. During planning, generates conf.py configuration
   3. During implementation, runs `sphinx-build` to generate HTML
   4. API reference appears in docs/reference/api/

   **Docstring format** (Google style recommended):
   ```python
   def greet(name: str) -> str:
       """Greet someone by name.

       Args:
           name: Person to greet

       Returns:
           Greeting message
       """
       return f"Hello, {name}!"
   ```

   **Output**: HTML documentation with API reference, navigation, search

   **Configuration** (auto-generated conf.py):
   - Extensions: autodoc (from docstrings), napoleon (Google/NumPy format), viewcode (source links)
   - Theme: sphinx_rtd_theme (Read the Docs style)
   - Options: Document all members, show inheritance

   **Regenerating**: Run documentation mission again in gap-filling mode to regenerate if code changed

   ---

   ### JSDoc (JavaScript/TypeScript Projects)

   **What it does**: Generates API reference from JSDoc comments

   **Requirements**:
   - JavaScript/TypeScript project with JSDoc comments
   - Node.js installed (for npx jsdoc)

   **How it works**:
   1. System detects .js/.ts files or package.json
   2. During planning, generates jsdoc.json configuration
   3. During implementation, runs `npx jsdoc` to generate HTML
   4. API reference appears in docs/reference/api/javascript/

   **JSDoc format**:

   ```javascript
   /**
    * Greet someone by name.
    * @param {string} name - Person to greet
    * @returns {string} Greeting message
    */
   function greet(name) {
       return `Hello, ${name}!`;
   }
   ```

   **Output**: HTML documentation with API reference, type information

   **Configuration** (auto-generated jsdoc.json):
   - Source: src/ directory
   - Template: docdash (clean theme)
   - Output: docs/reference/api/javascript/

   **For TypeScript**: TypeDoc is recommended (better TS support), but JSDoc works too

   ---

   ### rustdoc (Rust Projects)

   **What it does**: Generates API reference from Rust doc comments

   **Requirements**:
   - Rust project with doc comments
   - Cargo installed (comes with Rust toolchain)

   **How it works**:
   1. System detects Cargo.toml or .rs files
   2. During implementation, runs `cargo doc` to generate HTML
   3. API reference appears in docs/reference/api/rust/

   **Doc comment format**:

   ```rust
   /// Greet someone by name.
   ///
   /// # Arguments
   ///
   /// * `name` - Person to greet
   ///
   /// # Returns
   ///
   /// Greeting message
   pub fn greet(name: &str) -> String {
       format!("Hello, {}!", name)
   }
   ```

   **Output**: HTML documentation with API reference (rustdoc is very high quality)

   **Configuration**: rustdoc configured via Cargo.toml metadata:

   ```toml
   [package.metadata.docs.rs]
   all-features = true
   rustdoc-args = ["--document-private-items"]
   ```

   ---

   ### Multi-Language Projects

   If your project uses multiple languages (e.g., Python backend + TypeScript frontend):

   1. System detects all languages
   2. Recommends all applicable generators
   3. Configures each generator with separate output directories
   4. Generates unified reference documentation:

      ```
      docs/reference/api/
      ├── python/      # Sphinx output
      ├── javascript/  # JSDoc output
      └── rust/        # rustdoc output (if applicable)
      ```

   5. Landing page links to all language references

   **Example**: FastAPI (Python) + React (TypeScript) project
   - Sphinx documents Python backend API
   - JSDoc documents TypeScript frontend API
   - Both integrated into single documentation site

   ---

   ### Manual Reference (When Generators Can't Help)

   **Generators only work for**:
   - Code with good comments/docstrings
   - Public APIs (not internal implementation)
   - Supported languages (JS, Python, Rust initially)

   **You'll need manual reference for**:
   - CLI tools (command-line interface documentation)
   - Configuration files (config.yaml, .env, etc.)
   - Data formats (JSON schemas, CSV structures)
   - Languages without generators (Go, Java, C++, etc.)

   **Use the reference template**: `templates/divio/reference-template.md`
   - Provides structure for manual API/CLI/config documentation
   - Includes examples of tables, option lists, etc.
   - Ensures consistency with generated reference

   ```

**Files**: `docs/documentation-mission.md` (modified)

**Parallel?**: Yes (can write alongside other sections)

**Notes**:

- All three generators explained with examples
- Docstring/comment format shown for each
- Multi-language projects addressed
- Manual reference fallback explained
- Regeneration process mentioned

### Subtask T082 – Add Troubleshooting Section

**Purpose**: Document common errors and solutions for documentation missions.

**Steps**:

1. Add section to `docs/documentation-mission.md`:

   ```markdown
   ## Troubleshooting

   ### Problem: Mission not found

   **Symptoms**:
   ```

   MissionNotFoundError: Mission 'documentation' not found.
   Available missions: software-dev, research

   ```

   **Cause**: Documentation mission not installed in your project

   **Solution**:
   ```bash
   # Run upgrade to install documentation mission
   spec-kitty upgrade

   # Verify it's now available
   spec-kitty missions list
   # Should show: software-dev, research, documentation
   ```

   ---

   ### Problem: Generator not found

   **Symptoms**:

   ```
   GeneratorError: sphinx-build not found - install Sphinx to use this generator
   Visit: https://www.sphinx-doc.org/
   ```

   **Cause**: Generator tool (sphinx-build, npx, cargo) not installed

   **Solution**:

   **For Sphinx** (Python):

   ```bash
   pip install sphinx sphinx-rtd-theme
   sphinx-build --version  # Verify installation
   ```

   **For JSDoc** (JavaScript):

   ```bash
   npm install -g jsdoc
   npx jsdoc --version  # Verify installation
   ```

   **For rustdoc** (Rust):

   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   cargo doc --help  # Verify installation
   ```

   **Alternative**: Skip generators and write reference documentation manually using reference template

   ---

   ### Problem: Empty API reference

   **Symptoms**: Generator runs successfully but produces minimal/empty documentation

   **Cause**: Code lacks doc comments/docstrings

   **Solution**:

   1. Add doc comments to your code:

   **Python**:

   ```python
   def my_function(arg1: str) -> bool:
       """Short description.

       Longer description if needed.

       Args:
           arg1: Description of arg1

       Returns:
           Description of return value
       """
       pass
   ```

   **JavaScript**:

   ```javascript
   /**
    * Short description.
    * @param {string} arg1 - Description of arg1
    * @returns {boolean} Description of return value
    */
   function myFunction(arg1) {
       return true;
   }
   ```

   **Rust**:

   ```rust
   /// Short description.
   ///
   /// Longer description if needed.
   ///
   /// # Arguments
   ///
   /// * `arg1` - Description of arg1
   ///
   /// # Returns
   ///
   /// Description of return value
   pub fn my_function(arg1: &str) -> bool {
       true
   }
   ```

   2. Regenerate documentation:

   ```bash
   # For Sphinx
   sphinx-build -b html docs/ docs/_build/html/

   # For JSDoc
   npx jsdoc -c jsdoc.json

   # For rustdoc
   cargo doc
   ```

   ---

   ### Problem: Gap analysis shows wrong gaps

   **Symptoms**: System says you're missing tutorials, but you have them

   **Cause**: Documents not classified correctly (missing frontmatter or unclear content)

   **Solution**:

   Add explicit frontmatter to your docs:

   ```markdown
   ---
   type: tutorial
   audience: beginners
   ---
   # Your Tutorial

   [Content...]
   ```

   Valid types: `tutorial`, `how-to`, `reference`, `explanation`

   Re-run gap analysis:

   ```bash
   /spec-kitty.specify --mission documentation
   # Choose gap-filling mode
   # System will re-classify with updated frontmatter
   ```

   ---

   ### Problem: Documentation doesn't build

   **Symptoms**:

   ```
   Error: Build failed with warnings/errors
   ```

   **Common causes and solutions**:

   **Broken links**:

   ```bash
   # Check for broken links
   markdown-link-check docs/**/*.md

   # Fix: Update links to point to correct files
   ```

   **Invalid frontmatter**:

   ```bash
   # Validate YAML frontmatter
   python -c "
   from pathlib import Path
   from ruamel.yaml import YAML
   yaml = YAML()
   for file in Path('docs').rglob('*.md'):
       content = file.read_text()
       if content.startswith('---'):
           # Try to parse frontmatter
           yaml.load(content.split('---')[1])
   "

   # Fix: Correct YAML syntax in frontmatter
   ```

   **Missing theme** (Sphinx):

   ```bash
   # Install missing theme
   pip install sphinx-rtd-theme

   # Or choose different theme in conf.py
   html_theme = 'alabaster'  # Default Sphinx theme
   ```

   ---

   ### Problem: Divio types are confusing

   **Symptoms**: Not sure whether to write tutorial or how-to

   **Solution**: Use the decision guide:

   **Ask yourself**:
   1. **Is this for beginners or experienced users?**
      - Beginners → Tutorial
      - Experienced → How-To or Reference

   2. **What's the goal?**
      - Learn by doing → Tutorial
      - Solve specific problem → How-To
      - Look up details → Reference
      - Understand why → Explanation

   3. **What's the structure?**
      - Step-by-step learning → Tutorial
      - Problem + Solution → How-To
      - Technical specifications → Reference
      - Conceptual discussion → Explanation

   **Still confused?**: Start with what you have, the review process will help refine it

   ---

   ### Problem: Documentation mission commands not found

   **Symptoms**:

   ```
   Error: /spec-kitty.specify not found or mission not specified
   ```

   **Cause**: Using old spec-kitty version or wrong command syntax

   **Solution**:

   ```bash
   # Check spec-kitty version
   spec-kitty --version

   # Upgrade if needed
   pip install --upgrade spec-kitty-cli

   # Use correct syntax
   /spec-kitty.specify --mission documentation
   # Not: /spec-kitty.specify --type documentation
   # Not: spec-kitty doc specify
   ```

   ```

**Files**: `docs/documentation-mission.md` (modified)

**Parallel?**: Yes (can write alongside other sections)

**Notes**:

- Common real-world problems
- Clear symptoms, causes, solutions
- Code examples for fixes
- Links to external resources
- Addresses confusion about Divio types

### Subtask T084 – Update All 12 Agent Contexts

**Purpose**: Update all agent context files to mention documentation mission availability.

**Steps**:

1. Use AGENT_DIRS constant to update all agents:

   ```python
   # Script to update all agent contexts
   from pathlib import Path

   AGENT_DIRS = [
       (".claude", "commands"),
       (".github", "prompts"),
       (".gemini", "commands"),
       (".cursor", "commands"),
       (".qwen", "commands"),
       (".opencode", "command"),
       (".windsurf", "workflows"),
       (".codex", "prompts"),
       (".kilocode", "workflows"),
       (".augment", "commands"),
       (".roo", "commands"),
       (".amazonq", "prompts"),
   ]

   context_to_add = """
   ## Documentation Mission (New in v0.12.0)

   Spec Kitty now supports a documentation mission for creating and maintaining
   software documentation following Write the Docs and Divio principles.

   **Use when**: You need to create or improve project documentation

   **Key features**:
   - Follows Divio 4-type system (tutorial, how-to, reference, explanation)
   - Auto-generates API docs (JSDoc for JS/TS, Sphinx for Python, rustdoc for Rust)
   - Gap analysis identifies missing documentation
   - Iterative workflow (run multiple times as project evolves)

   **To use**:
   ```bash
   /spec-kitty.specify --mission documentation
   # Follow discovery questions
   # System guides you through documentation creation
   ```

   **Iteration modes**:
   - Initial: Create documentation from scratch
   - Gap-filling: Improve existing documentation
   - Feature-specific: Document a new feature

   **Learn more**: See docs/documentation-mission.md
   """

   for agent_dir, subdir in AGENT_DIRS:
       # Find the main context file (varies by agent)
       # For .claude: CLAUDE.md or README.md
       # For others: may be in subdirectory
       ...

   ```

2. For each agent, add documentation mission context:
   - `.claude/CLAUDE.md` - Already updated during planning
   - Other agents: Add similar context to their README or main context file

3. Alternative: Create migration task to update agent files:

   ```python
   # In a migration or setup script
   def update_agent_contexts_for_documentation_mission():
       """Update all agent context files with documentation mission info."""
       # Implementation to update all 12 agents
       pass
   ```

**Files**: All 12 agent directories (`.claude/`, `.github/prompts/`, etc.)

**Parallel?**: Yes (each agent update is independent)

**Notes**:

- Use AGENT_DIRS constant for consistency
- Each agent may have different context file location
- Keep update concise (2-3 paragraphs max)
- Link to full documentation
- T083 already done (CLAUDE.md updated during planning)

### Subtask T085 – Add Initial Project Example

**Purpose**: Provide complete walkthrough example for initial documentation.

**Steps**:

1. Add section to `docs/documentation-mission.md`:

   ```markdown
   ## Complete Example: Initial Documentation for Python Library

   This example shows creating documentation for a new Python library from scratch.

   ### Project Context

   **Project**: `awesome-lib` - A Python library for data processing
   **Goal**: Create complete documentation for first release
   **Audience**: Developers who will use the library

   ### Step 1: Create Documentation Feature

   ```bash
   cd awesome-lib/
   /spec-kitty.specify --mission documentation
   ```

   **Discovery conversation**:

   ```
   Q: Iteration mode?
   A: Initial (no existing docs)

   Q: Target audience?
   A: Developers integrating the library

   Q: Which Divio types?
   A: tutorial, how-to, reference, explanation

   Q: Detected Python. Use Sphinx for API reference?
   A: Yes

   ✓ Specification created: kitty-specs/013-doc-awesome-lib/spec.md
   ```

   ### Step 2: Plan Documentation Structure

   ```bash
   /spec-kitty.plan
   ```

   **Planning output**:

   ```
   ✓ Documentation structure designed:
     docs/
     ├── tutorials/
     ├── how-to/
     ├── reference/api/  # Sphinx generates here
     └── explanation/

   ✓ Sphinx configured (conf.py generated)
   ✓ Work packages created in plan.md

   Next: /spec-kitty.tasks
   ```

   ### Step 3: Generate Work Packages

   ```bash
   /spec-kitty.tasks
   ```

   **Work packages generated**:
   - WP01: Structure & Sphinx Setup
   - WP02: Tutorial Documentation (getting-started, basic-usage)
   - WP03: How-To Guides (installation, common-tasks)
   - WP04: API Reference (Sphinx generation)
   - WP05: Explanation (architecture, concepts)
   - WP06: Quality Validation

   ### Step 4: Implement (Using Parallel Agents)

   ```bash
   # Can run in parallel after WP01 completes
   /spec-kitty.implement WP01  # Agent 1: Setup

   # After WP01 done, run these in parallel:
   /spec-kitty.implement WP02  # Agent 2: Tutorials
   /spec-kitty.implement WP03  # Agent 3: How-Tos
   /spec-kitty.implement WP04  # Agent 4: Reference
   /spec-kitty.implement WP05  # Agent 5: Explanation

   # After all content done:
   /spec-kitty.implement WP06  # Agent 1: Validation
   ```

   **WP01 Output** (Structure & Sphinx):

   ```bash
   ✓ Created docs/ directory structure
   ✓ Generated docs/conf.py (Sphinx config)
   ✓ Ran sphinx-build successfully
   ✓ API reference generated at docs/_build/html/
   ✓ Created docs/index.md landing page
   ```

   **WP02 Output** (Tutorials):

   ```bash
   ✓ Wrote docs/tutorials/getting-started.md (from tutorial template)
   ✓ Wrote docs/tutorials/basic-usage.md
   ✓ Tested tutorials with fresh user
   ✓ All tutorials work end-to-end
   ```

   **WP04 Output** (Reference):

   ```bash
   ✓ Sphinx generated API docs for all public classes/functions
   ✓ Wrote docs/reference/cli.md (manual CLI reference)
   ✓ Integrated generated + manual reference
   ✓ All public APIs documented (100% coverage)
   ```

   ### Step 5: Review & Accept

   ```bash
   /spec-kitty.review WP01
   # ✓ Structure correct, Sphinx works, tests pass

   /spec-kitty.review WP02
   # ✓ Tutorials follow Divio principles, accessible, work correctly

   /spec-kitty.accept
   # ✓ All work packages complete
   # ✓ Documentation ready for v1.0 release
   ```

   ### Result

   **Documentation structure**:

   ```
   docs/
   ├── index.md                          # Landing page
   ├── tutorials/
   │   ├── getting-started.md           # From tutorial template
   │   └── basic-usage.md               # From tutorial template
   ├── how-to/
   │   ├── installation.md              # From how-to template
   │   └── common-tasks.md              # From how-to template
   ├── reference/
   │   ├── api/                         # Sphinx generated
   │   │   └── index.html
   │   └── cli.md                       # Manual reference
   └── explanation/
       ├── architecture.md              # From explanation template
       └── concepts.md                  # From explanation template
   ```

   **Time taken**: ~2-3 hours (vs. ~8-10 hours writing from scratch)

   **Quality**: Follows Write the Docs and Divio best practices, accessible, complete

   **Ready for**: Hosting on Read the Docs, GitHub Pages, or other platforms

   ```

**Files**: `docs/documentation-mission.md` (modified)

**Parallel?**: Yes (can write examples in parallel)

**Notes**:

- Complete end-to-end example
- Shows actual commands and outputs
- Demonstrates parallel implementation
- Shows time savings
- Realistic project scenario

### Subtask T086 – Add Gap-Filling Example

**Purpose**: Provide complete walkthrough example for gap-filling iteration.

**Steps**:

1. Add section to `docs/documentation-mission.md`:

   ```markdown
   ## Complete Example: Gap-Filling for Existing Project

   This example shows improving documentation for a project that has basic API docs but is missing tutorials.

   ### Project Context

   **Project**: `spec-kitty` - This very project!
   **Current docs**: Reference documentation exists (commands, APIs)
   **Problem**: New users report confusion, struggle to get started
   **Goal**: Add tutorials and how-tos to help new users

   ### Step 1: Create Gap-Filling Feature

   ```bash
   cd spec-kitty/
   /spec-kitty.specify --mission documentation
   ```

   **Discovery conversation**:

   ```
   Q: Iteration mode?
   A: Gap-filling (improving existing docs)

   Q: What problems are users reporting?
   A: Can't get started, don't know how to create features

   Q: Which Divio types to add?
   A: tutorials, how-to

   ✓ Specification created
   ```

   ### Step 2: Plan with Gap Analysis

   ```bash
   /spec-kitty.plan
   ```

   **Gap analysis runs automatically**:

   ```
   Auditing existing documentation...
   Detected framework: Plain Markdown

   Coverage Matrix:
   | Area      | Tutorial | How-To | Reference | Explanation |
   |-----------|----------|--------|-----------|-------------|
   | CLI       | ✗        | ✗      | ✓         | ✗           |
   | Missions  | ✗        | ✗      | ✓         | ✓           |
   | Templates | ✗        | ✗      | ✓         | ✗           |

   Coverage: 4/12 cells = 33.3%

   Identified Gaps:
   [HIGH] CLI → Tutorial (new users need step-by-step getting started)
   [HIGH] Missions → Tutorial (users don't understand mission system)
   [MEDIUM] CLI → How-To (solve common problems)
   [MEDIUM] Templates → How-To (customizing templates)

   ✓ Gap analysis saved to gap-analysis.md
   ✓ Plan created focusing on high-priority gaps
   ```

   ### Step 3: Generate Work Packages

   ```bash
   /spec-kitty.tasks
   ```

   **Work packages targeting gaps**:
   - WP01: CLI Tutorial (HIGH priority gap)
   - WP02: Mission System Tutorial (HIGH priority gap)
   - WP03: Common Tasks How-Tos (MEDIUM priority gaps)
   - WP04: Quality Validation

   ### Step 4: Implement Gap-Filling Work

   ```bash
   /spec-kitty.implement WP01  # CLI tutorial
   ```

   **WP01 Output**:

   ```bash
   ✓ Created docs/tutorials/getting-started-with-spec-kitty.md
   ✓ Follows tutorial template (step-by-step, for beginners)
   ✓ Tested with fresh user (they successfully created a feature)
   ✓ Integrated with existing docs (linked from index)
   ```

   ```bash
   /spec-kitty.implement WP02  # Mission tutorial
   ```

   **WP02 Output**:

   ```bash
   ✓ Created docs/tutorials/understanding-missions.md
   ✓ Explains mission system by having user try it
   ✓ Tested tutorial (user understands software-dev vs research missions)
   ```

   ### Step 5: Review & Accept

   ```bash
   /spec-kitty.review WP01
   # Feedback: Tutorial is great! One typo in step 3.

   # Fix typo, re-submit
   /spec-kitty.review WP01
   # ✓ Approved

   /spec-kitty.accept
   # ✓ Gap-filling complete
   ```

   ### Result

   **Before gap-filling**:
   - Coverage: 33.3%
   - No tutorials (new users confused)
   - No how-tos (users can't solve problems)

   **After gap-filling**:
   - Coverage: 58.3% (+25%)
   - 2 tutorials (new users can get started)
   - 2 how-tos (users can solve common problems)
   - User satisfaction improved (fewer "how do I start?" questions)

   **Next iteration**: Can run another gap-filling mission later to add explanations, more how-tos, etc.

   ---

   ## Example: Feature-Specific Documentation

   **Scenario**: You added a new "dashboard" feature to spec-kitty, need to document it.

   ```bash
   /spec-kitty.specify --mission documentation
   # Mode: feature-specific
   # Feature: dashboard
   # Types: tutorial (how to use dashboard), how-to (customize dashboard), reference (dashboard API)

   /spec-kitty.plan
   # Plans docs for dashboard feature only

   /spec-kitty.tasks
   # Creates WPs for dashboard tutorial, how-tos, reference

   /spec-kitty.implement WP01
   # Writes dashboard tutorial

   /spec-kitty.review WP01
   /spec-kitty.accept
   # Dashboard now fully documented
   ```

   **Output**:
   - docs/tutorials/using-dashboard.md (new)
   - docs/how-to/customize-dashboard.md (new)
   - docs/reference/dashboard-api.md (new, or added to existing reference)
   - Integrated with existing documentation structure

   ```

**Files**: `docs/documentation-mission.md` (modified)

**Parallel?**: Yes (can write examples alongside other sections)

**Notes**:

- Two complete examples (initial + gap-filling)
- Shows actual outputs and results
- Demonstrates iteration (gap-filling can run multiple times)
- Feature-specific example is brief (simpler workflow)

## Test Strategy

**Documentation Quality Checks**:

1. **Accuracy**: Does documentation match actual implementation?
   - Verify commands shown actually work
   - Verify outputs match what system produces
   - Test all code examples

2. **Completeness**: Does documentation cover all features?
   - All workflow phases explained
   - All Divio types explained
   - All generators documented
   - All iteration modes covered
   - Troubleshooting for common issues

3. **Clarity**: Can users follow the documentation?
   - Have someone unfamiliar with documentation mission read it
   - Ask: Can you create documentation following this guide?
   - Revise based on feedback

4. **Accessibility**:
   - Proper heading hierarchy
   - Code blocks have syntax highlighting
   - Clear, plain language
   - No jargon or defined technical terms

**Agent Context Validation**:

1. Verify all 12 agents updated:

   ```bash
   for agent_dir in .claude .github .gemini .cursor .qwen .opencode .windsurf .codex .kilocode .augment .roo .amazonq; do
       echo "Checking $agent_dir..."
       grep -r "documentation mission" $agent_dir/ || echo "⚠️ Not updated"
   done
   ```

2. Verify updates are consistent:
   - Same core message across all agents
   - Adapted to each agent's context file format
   - No copy-paste errors or outdated information

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Documentation becomes outdated | Medium - misleads users | Document actual implementation (WP01-09 complete first) |
| Examples don't work | High - breaks user trust | Test all examples before committing |
| Agent context inconsistent | Medium - confusing experience | Use AGENT_DIRS, update all 12 agents atomically |
| Documentation too technical | Medium - beginners can't use it | Write for target audience, get peer review |
| Missing troubleshooting scenarios | Medium - users get stuck | Collect common issues during dogfooding |

## Definition of Done Checklist

- [ ] `docs/documentation-mission.md` created with comprehensive content
- [ ] Overview section explains documentation mission purpose and value
- [ ] Quick Start section shows both initial and gap-filling workflows
- [ ] T078: Workflow phases documented:
  - [ ] Discover phase explained with example questions
  - [ ] Audit phase explained with gap analysis example
  - [ ] Design phase explained with structure planning
  - [ ] Generate phase explained with template and generator usage
  - [ ] Validate phase explained with quality checks
- [ ] Publish phase explained with deployment guidance (including release.md when in scope)
- [ ] T079: Divio types documented:
  - [ ] Tutorial characteristics and when to use
  - [ ] How-to characteristics and when to use
  - [ ] Reference characteristics and when to use
  - [ ] Explanation characteristics and when to use
  - [ ] Quick decision guide for choosing type
- [ ] T080: Iteration modes documented:
  - [ ] Initial mode workflow and example
  - [ ] Gap-filling mode workflow and example
  - [ ] Feature-specific mode workflow and example
  - [ ] Decision guide for choosing mode
- [ ] T081: Generator usage documented:
  - [ ] Sphinx documentation (Python)
  - [ ] JSDoc documentation (JavaScript)
  - [ ] rustdoc documentation (Rust)
  - [ ] Multi-language project handling
  - [ ] Manual reference fallback
  - [ ] Docstring/comment format examples
  - [ ] Regeneration process
- [ ] T082: Troubleshooting section added:
  - [ ] Mission not found error
  - [ ] Generator not found error
  - [ ] Empty API reference problem
  - [ ] Gap analysis wrong gaps issue
  - [ ] Build failures (broken links, invalid frontmatter, missing theme)
  - [ ] Divio type confusion guidance
  - [ ] Command syntax issues
- [ ] T083: CLAUDE.md updated (already done in planning)
- [ ] T084: All 12 agent contexts updated:
  - [ ] .claude/CLAUDE.md or equivalent
  - [ ] .github/prompts/ context
  - [ ] .gemini/commands/ context
  - [ ] .cursor/commands/ context
  - [ ] .qwen/commands/ context
  - [ ] .opencode/command/ context
  - [ ] .windsurf/workflows/ context
  - [ ] .codex/prompts/ context
  - [ ] .kilocode/workflows/ context
  - [ ] .augment/commands/ context
  - [ ] .roo/commands/ context
  - [ ] .amazonq/prompts/ context
  - [ ] All agents mention documentation mission consistently
- [ ] T085: Initial project example added:
  - [ ] Complete walkthrough from start to finish
  - [ ] Shows actual commands and outputs
  - [ ] Demonstrates parallel implementation
  - [ ] Shows time savings
- [ ] T086: Gap-filling example added:
  - [ ] Shows gap analysis output
  - [ ] Demonstrates prioritized gap filling
  - [ ] Shows before/after coverage
  - [ ] Demonstrates iterative improvement
- [ ] Feature-specific example added (brief)
- [ ] Documentation builds successfully
- [ ] All examples tested and work
- [ ] All code blocks have syntax highlighting
- [ ] All links are valid
- [ ] Documentation peer-reviewed
- [ ] `tasks.md` in feature directory updated with WP10 status

## Review Guidance

**Key Acceptance Checkpoints**:

1. **Accuracy**: Documentation matches actual implementation
2. **Completeness**: All features covered (phases, types, modes, generators, troubleshooting)
3. **Examples**: Complete, tested, realistic examples
4. **Clarity**: Clear for target audience (users, not just contributors)
5. **Agent Updates**: All 12 agents updated consistently

**Validation Commands**:

```bash
# Check documentation exists
ls -la docs/documentation-mission.md

# Build documentation (if spec-kitty has build)
# Or validate markdown
markdown-link-check docs/documentation-mission.md

# Check agent updates
for agent_dir in .claude .github .gemini .cursor .qwen .opencode .windsurf .codex .kilocode .augment .roo .amazonq; do
    echo "=== $agent_dir ==="
    grep -i "documentation mission" $agent_dir/**/* 2>/dev/null | head -3
done

# Test examples manually
# Follow initial project example step-by-step
# Follow gap-filling example step-by-step
# Verify outputs match documentation
```

**Review Focus Areas**:

- Documentation is accurate (matches WP01-09 implementation)
- Examples are complete and tested (actually work)
- All sections present (phases, types, modes, generators, troubleshooting, examples)
- Agent contexts updated consistently across all 12 agents
- Links are valid (internal and external)
- Code examples have syntax highlighting
- Language is clear and accessible

**Special Focus**:

- Have a new user (unfamiliar with documentation mission) read the guide
- Ask: Can you create documentation following this guide?
- Revise based on their feedback

## Activity Log

- 2026-01-12T17:18:56Z – system – lane=planned – Prompt created.
- 2026-01-13T09:21:59Z – explicit-feature-test – lane=doing – Moved to doing
- 2026-01-13T09:22:47Z – success-test – lane=doing – Moved to doing
- 2026-01-13T09:23:26Z – victory-test – lane=for_review – Moved to for_review
- 2026-01-13T10:47:28Z – victory-test – lane=planned – Reset to planned (was test activity)
- 2026-01-13T11:36:22Z – claude – shell_pid=82623 – lane=doing – Started implementation via workflow command
- 2026-01-13T16:13:47Z – claude – shell_pid=82623 – lane=done – Complete user documentation and agent context created. 884-line user guide covers all workflow phases, Divio types, generators, and iteration modes.
