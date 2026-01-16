---
work_package_id: "WP08"
subtasks:
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
  - "T036"
  - "T037"
title: "Explanations"
phase: "Phase 1 - Content Creation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP02"]
history:
  - timestamp: "2026-01-16T16:16:58Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 – Explanations

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Create 7 understanding-oriented explanation documents
- Explain the "why" behind spec-kitty's design decisions
- **Success**: User understands the reasoning and can make informed decisions

## Context & Constraints

- **Spec**: `kitty-specs/014-comprehensive-end-user-documentation/spec.md`
- **Plan**: `kitty-specs/014-comprehensive-end-user-documentation/plan.md`
- **Divio Type**: Explanation = understanding-oriented

### Explanation Principles (from Divio)
- Explanations are **understanding-oriented**
- Explain background and context
- Discuss alternatives and why choices were made
- Help the reader understand "why"
- Not about doing (that's tutorials/how-tos)

## Subtasks & Detailed Guidance

### Subtask T031 – Create spec-driven-development.md
- **Purpose**: Explain the philosophy and methodology
- **Structure**:
  ```markdown
  # Spec-Driven Development Explained

  ## What is Spec-Driven Development?
  [Traditional development vs. spec-first]

  ## Why Spec-First?
  - AI agents need clear requirements
  - Specifications become executable
  - Reduces rework and misunderstanding

  ## The Spec-Kitty Workflow
  [High-level: specify → plan → tasks → implement → review]

  ## How It Differs from Traditional Development
  [Comparison table]

  ## When to Use Spec-Driven Development
  [Good fit vs. poor fit scenarios]
  ```
- **Files**: `docs/explanation/spec-driven-development.md`
- **Parallel?**: Yes

### Subtask T032 – Create divio-documentation.md
- **Purpose**: Explain why we use Divio 4-type documentation
- **Structure**:
  ```markdown
  # Why Divio Documentation System?

  ## The Problem with Traditional Documentation
  [Mixed concerns, hard to navigate]

  ## The Four Types
  - **Tutorials**: Learning-oriented
  - **How-To Guides**: Task-oriented
  - **Reference**: Information-oriented
  - **Explanations**: Understanding-oriented

  ## Why This Works
  [Different user needs at different times]

  ## How Spec Kitty Uses Divio
  [Our documentation structure]

  ## Further Reading
  [Link to Divio documentation site]
  ```
- **Files**: `docs/explanation/divio-documentation.md`
- **Parallel?**: Yes

### Subtask T033 – Migrate/update workspace-per-wp.md
- **Purpose**: Move existing workspace-per-wp.md to explanation/
- **Steps**:
  1. Move `docs/workspace-per-wp.md` → `docs/explanation/workspace-per-wp.md`
  2. Ensure content is current for 0.11.0
  3. Add cross-references to tutorials and how-tos
  4. Add link to git-worktrees.md for background
- **Files**: `docs/explanation/workspace-per-wp.md`
- **Parallel?**: Yes
- **Notes**: Content already exists - just needs migration and linking

### Subtask T034 – Create git-worktrees.md
- **Purpose**: Explain git worktrees for spec-kitty users
- **Structure**:
  ```markdown
  # Git Worktrees Explained

  ## What is a Git Worktree?
  [A worktree is a linked copy of your repo with a different branch checked out]

  ## Why Does Spec Kitty Use Worktrees?
  - Parallel development without branch switching
  - Each work package gets isolated workspace
  - Multiple agents can work simultaneously

  ## How Worktrees Work
  ```
  main-repo/           ← main branch
  .worktrees/
    ├── feature-WP01/  ← WP01 branch
    └── feature-WP02/  ← WP02 branch
  ```
  [All share same .git, but different working directories]

  ## Worktrees vs. Cloning
  [Worktrees share history, clones are independent]

  ## Git Commands for Worktrees
  ```bash
  git worktree list      # Show all worktrees
  git worktree add       # Create new worktree
  git worktree remove    # Remove worktree
  ```

  ## Sparse Checkouts
  [What they are, when spec-kitty might use them]

  ## Common Issues
  - "Worktree already exists"
  - "Branch is already checked out"
  - Cleanup after crashes

  ## Further Reading
  - [Git Worktree Documentation](https://git-scm.com/docs/git-worktree)
  - [Workspace-per-WP Model](workspace-per-wp.md)
  ```
- **Files**: `docs/explanation/git-worktrees.md`
- **Parallel?**: Yes
- **Notes**: **CRITICAL** - Users need to understand this for parallel development

### Subtask T035 – Create mission-system.md
- **Purpose**: Explain why missions exist and how they shape workflow
- **Structure**:
  ```markdown
  # The Mission System Explained

  ## Why Different Missions?
  [Software dev vs. research vs. documentation have different needs]

  ## How Missions Work
  - Selected per-feature during /spec-kitty.specify
  - Stored in feature's meta.json
  - Affects templates, phases, artifacts

  ## The Three Missions

  ### Software Dev Kitty
  [Focus: Building software features]

  ### Deep Research Kitty
  [Focus: Investigation and analysis]

  ### Documentation Kitty
  [Focus: Creating documentation]

  ## Mission Templates
  [How templates differ between missions]

  ## Per-Feature vs. Global
  [0.8.0+ change: missions are per-feature, not project-wide]
  ```
- **Files**: `docs/explanation/mission-system.md`
- **Parallel?**: Yes

### Subtask T036 – Create kanban-workflow.md
- **Purpose**: Explain the lane-based workflow
- **Structure**:
  ```markdown
  # Kanban Workflow Explained

  ## The Four Lanes
  - **planned**: Work ready to start
  - **doing**: Work in progress
  - **for_review**: Work awaiting review
  - **done**: Work completed

  ## How Work Moves Between Lanes
  [Diagram: planned → doing → for_review → done (or back to planned)]

  ## Lane Status in Frontmatter
  ```yaml
  lane: "doing"
  ```
  [Not directories - just a field in the WP file]

  ## Who Moves Work?
  - Agent moves to doing when starting
  - Agent moves to for_review when complete
  - Reviewer moves to done or back to planned

  ## Activity Log
  [Why we track lane transitions]
  ```
- **Files**: `docs/explanation/kanban-workflow.md`
- **Parallel?**: Yes

### Subtask T037 – Create ai-agent-architecture.md
- **Purpose**: Explain how slash commands work across agents
- **Structure**:
  ```markdown
  # AI Agent Architecture Explained

  ## How Slash Commands Work
  [Agent reads command files, executes instructions]

  ## The 12 Supported Agents
  [Why we support multiple agents]

  ## Agent-Specific Directories
  [.claude/, .codex/, .gemini/, etc.]

  ## Command Template System
  [How templates are shared across agents]

  ## Multi-Agent Collaboration
  [Different agents on different WPs]

  ## Why Agent-Agnostic?
  [Users choose their preferred agent]
  ```
- **Files**: `docs/explanation/ai-agent-architecture.md`
- **Parallel?**: Yes

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Explanations too technical | Focus on end-user perspective |
| Missing "why" | Review each section for rationale |
| Overlap with how-tos | Link to how-tos, don't duplicate |

## Definition of Done Checklist

- [ ] T031: spec-driven-development.md explains philosophy
- [ ] T032: divio-documentation.md explains 4-type system
- [ ] T033: workspace-per-wp.md migrated and updated
- [ ] T034: git-worktrees.md comprehensive with commands
- [ ] T035: mission-system.md covers all three missions
- [ ] T036: kanban-workflow.md explains lanes clearly
- [ ] T037: ai-agent-architecture.md covers multi-agent
- [ ] All explanations link to related tutorials and how-tos

## Review Guidance

- Check that each doc explains "why" not just "how"
- Verify git-worktrees.md is accessible to users unfamiliar with worktrees
- Ensure workspace-per-wp.md migration is complete

## Activity Log

- 2026-01-16T16:16:58Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
