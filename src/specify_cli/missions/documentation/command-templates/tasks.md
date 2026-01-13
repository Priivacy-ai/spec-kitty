---
description: Generate documentation work packages and subtasks aligned to Divio types.
---

# Command Template: /spec-kitty.tasks (Documentation Mission)

**Phase**: Design (finalizing work breakdown)
**Purpose**: Break documentation work into independently implementable work packages with subtasks.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Location Pre-flight Check

Verify you are in the main repository (not a worktree). Task generation happens in main for ALL missions.

```bash
git branch --show-current  # Should show "main"
```

**Note**: Task generation in main is standard for all spec-kitty missions. Implementation happens in per-WP worktrees.

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
- If publish is in scope, add a release WP to produce `release.md`

**For Users**:
- Tasks.md shows the full work breakdown
- Work packages are independently implementable
- MVP often just structure + reference (API docs)
- Full documentation includes all Divio types
- Parallel work packages can be implemented simultaneously
