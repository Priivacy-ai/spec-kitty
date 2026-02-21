---
description: Generate research work packages with subtasks aligned to methodology phases.
---

# Command Template: /spec-kitty.tasks (Research Mission)

**Phase**: Design (finalizing work breakdown)
**Purpose**: Break research work into independently executable work packages with subtasks.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Location Pre-flight Check

Verify you are in the planning repository (not a worktree). Task generation happens on the target branch for ALL missions.

```bash
git branch --show-current  # Should show the target branch (meta.json → target_branch)
```

**Note**: Task generation in the target branch is standard for all spec-kitty missions. Implementation happens in per-WP worktrees.

---

## Outline

1. **Setup**: Run `spec-kitty agent feature check-prerequisites --json --paths-only --include-tasks`

   **CRITICAL**: The command returns JSON with `FEATURE_DIR` as an ABSOLUTE path (e.g., `/Users/robert/Code/project/kitty-specs/015-research-topic`).

   **YOU MUST USE THIS PATH** for ALL subsequent file operations.

2. **Load design documents**:
   - spec.md (research question, scope, objectives)
   - plan.md (methodology, phases, quality criteria)
   - research.md (background, prior art)
   - data-model.md (entities, relationships)

3. **Derive fine-grained subtasks**:

   ### Subtask Patterns for Research

   **Literature Search & Source Collection** (Phase 1):
   - T001: Define search keywords and inclusion/exclusion criteria
   - T002: [P] Search academic database 1 (IEEE, PubMed, arXiv, etc.)
   - T003: [P] Search academic database 2
   - T004: [P] Search gray literature and industry sources
   - T005: Screen collected sources for relevance
   - T006: Populate source-register.csv with all candidate sources
   - T007: Prioritize sources by relevance rating

   **Source Review & Evidence Extraction** (Phase 2):
   - T010: [P] Review high-relevance sources (parallelizable by source)
   - T011: Extract key findings into evidence-log.csv
   - T012: Assign confidence levels to findings
   - T013: Document limitations and caveats
   - T014: Identify patterns/themes emerging from evidence

   **Analysis & Synthesis** (Phase 3):
   - T020: Code findings by theme/category
   - T021: Identify patterns across sources and confidence levels
   - T022: Assess strength of evidence supporting each claim
   - T023: Draw conclusions mapped to sub-questions
   - T024: Document limitations and threats to validity
   - T025: Write findings.md with synthesis and bibliography references

   **Quality & Validation** (Phase 4):
   - T030: Verify source coverage meets minimum requirements
   - T031: Validate evidence citations are traceable
   - T032: Check for bias in source selection
   - T033: Review methodology adherence
   - T034: External validation (if applicable)

4. **Roll subtasks into work packages**:

   ### Work Package Patterns for Research

   **Standard Research Flow**:
   - WP01: Literature Search & Source Collection (T001-T007)
   - WP02: Source Review & Evidence Extraction (T010-T014)
   - WP03: Analysis & Synthesis (T020-T025)
   - WP04: Quality Validation (T030-T034)

   **Empirical Research (if applicable)**:
   - WP01: Literature Review (background, prior art)
   - WP02: Study Design & Setup
   - WP03: Data Collection
   - WP04: Analysis & Findings
   - WP05: Quality Validation

   **Multi-Researcher Parallel**:
   - WP01: Search & Collect (foundation)
   - WP02a: [P] Source Review - Researcher 1 batch
   - WP02b: [P] Source Review - Researcher 2 batch
   - WP03: Synthesis (depends on WP02a, WP02b)
   - WP04: Validation

   ### Prioritization

   - **P0 (foundation)**: Literature search setup, source register initialization
   - **P1 (critical)**: Source review, evidence extraction
   - **P2 (important)**: Analysis, synthesis, findings
   - **P3 (polish)**: Quality validation, external review

5. **Write `tasks.md`**:
   - Location: `FEATURE_DIR/tasks.md`
   - Use `templates/tasks-template.md` from research mission
   - Include work packages with subtasks
   - Mark parallel opportunities (`[P]`)
   - Define dependencies (Phase 2 depends on Phase 1, etc.)
   - Reference evidence tracking requirements (source-register.csv, evidence-log.csv)

6. **Generate prompt files**:

   **CRITICAL PATH RULE**: All work package files MUST be created in a FLAT `FEATURE_DIR/tasks/` directory, NOT in subdirectories!

   - Create flat `FEATURE_DIR/tasks/` directory (no subdirectories!)
   - For each work package:
     - Derive a kebab-case slug from the title; filename: `WPxx-slug.md`
     - Full path: `FEATURE_DIR/tasks/WP01-literature-search.md`
     - Use `templates/task-prompt-template.md` to capture:
       - **YAML frontmatter with `lane: "planned"`** (CRITICAL - this is how review finds WPs!)
       - `work_package_id`, `subtasks` array, `dependencies`, history entry
       - Objectives, context, methodology guidance per subtask
       - Evidence tracking requirements
       - Quality validation criteria

   **IMPORTANT**: All WP files live in flat `tasks/` directory. Lane status is tracked ONLY in the `lane:` frontmatter field, NOT by directory location. Agents can change lanes by editing the `lane:` field directly or using `spec-kitty agent tasks move-task`.

7. **Finalize tasks with dependency parsing and commit**:

   **CRITICAL**: Run this command from repo root:
   ```bash
   spec-kitty agent feature finalize-tasks --json
   ```

   This step is MANDATORY. Without it:
   - Dependencies won't be in frontmatter
   - Tasks won't be committed to target branch

8. **Report**:
   - Path to tasks.md
   - Work package count and subtask tallies
   - Parallelization opportunities (different sources, databases)
   - MVP recommendation (typically WP01 Literature Search)
   - Next command: `/spec-kitty.implement WP01`

---

## Research-Specific Task Generation Rules

**Evidence Tracking**:
- Every subtask that produces findings MUST specify output to evidence-log.csv
- Every subtask that identifies sources MUST specify output to source-register.csv
- Include subtasks for evidence validation and citation verification

**Parallel Opportunities**:
- Database searches are parallel (`[P]`) - different databases can be searched simultaneously
- Source reviews are parallel (`[P]`) - different sources can be reviewed simultaneously
- Researcher batches are parallel (`[P]`) - work can be split across reviewers

**Quality Subtasks**:
- Include confidence level assignment for findings
- Include bias checking for source selection
- Include methodology adherence verification

**Work Package Scope**:
- Each methodology phase typically gets its own work package
- Phase transitions are natural dependency boundaries
- Quality validation is always the final work package

---

## YAML Frontmatter Format (CRITICAL)

**Every WP prompt file MUST use this frontmatter format**:

```yaml
---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
title: "Literature Search & Source Collection"
phase: "Phase 1 - Literature Review"
lane: "planned"  # DO NOT EDIT - use: spec-kitty agent tasks move-task <WPID> --to <lane>
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []  # Added by finalize-tasks
history:
  - timestamp: "2026-01-19T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---
```

**DO NOT use markdown status fields like `**Status**: planned`**. The `lane:` field in YAML frontmatter is the ONLY status tracking mechanism. The review command (`/spec-kitty.review`) searches for `lane: "for_review"` in frontmatter to find WPs ready for review.

---

## Key Guidelines

**For Agents**:
- Use methodology phases as natural WP boundaries
- Mark parallel subtasks (database searches, source reviews)
- Include evidence tracking in every WP prompt
- Quality validation depends on all content WPs
- Use `spec-kitty agent tasks move-task` to change lanes

**For Users**:
- Tasks.md shows the full research work breakdown
- Work packages follow methodology phases
- MVP is typically the literature search phase
- Parallel database searches speed up Phase 1
- Evidence artifacts (CSV files) are tracked throughout
