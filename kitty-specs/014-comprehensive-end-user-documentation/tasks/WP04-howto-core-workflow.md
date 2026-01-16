---
work_package_id: "WP04"
subtasks:
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
title: "How-To Guides - Core Workflow"
phase: "Phase 1 - Content Creation"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "58526"
review_status: "approved"
reviewed_by: "Robert Douglass"
dependencies: ["WP02"]
history:
  - timestamp: "2026-01-16T16:16:58Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – How-To Guides - Core Workflow

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Create 7 task-oriented how-to guides for the core spec-kitty workflow
- Each guide focuses on ONE specific task
- **Success**: User can follow any guide to accomplish the specific task

## Context & Constraints

- **Spec**: `kitty-specs/014-comprehensive-end-user-documentation/spec.md`
- **Plan**: `kitty-specs/014-comprehensive-end-user-documentation/plan.md`
- **Divio Type**: How-To = task-oriented, problem-solving

### How-To Principles (from Divio)
- How-tos are **goal-oriented**
- Focus on a specific, practical goal
- Don't explain concepts (link to explanations)
- Provide working solutions
- Be flexible for different situations

## Subtasks & Detailed Guidance

### Subtask T012 – Create install-and-upgrade.md
- **Purpose**: How to install spec-kitty and upgrade existing projects
- **Structure**:
  ```markdown
  # How to Install and Upgrade Spec Kitty

  ## Install from PyPI
  [pip install, uv tool install]

  ## Install from GitHub
  [Latest development version]

  ## One-Time Usage
  [pipx run, uvx]

  ## Upgrade Existing Projects
  [spec-kitty upgrade command]

  ## Verify Installation
  [spec-kitty --version]
  ```
- **Files**: `docs/how-to/install-and-upgrade.md`
- **Parallel?**: Yes

### Subtask T013 – Create create-specification.md
- **Purpose**: How to use /spec-kitty.specify
- **Structure**:
  ```markdown
  # How to Create a Feature Specification

  ## When to Use
  [Starting a new feature]

  ## The Command
  ```bash
  /spec-kitty.specify <description>
  ```

  ## The Discovery Interview
  [WAITING_FOR_DISCOVERY_INPUT explained]

  ## What Gets Created
  [kitty-specs/###-feature/spec.md]

  ## Example
  [Complete walkthrough]

  ## Troubleshooting
  [Common issues]
  ```
- **Files**: `docs/how-to/create-specification.md`
- **Parallel?**: Yes

### Subtask T014 – Create create-plan.md
- **Purpose**: How to use /spec-kitty.plan
- **Structure**:
  ```markdown
  # How to Create a Technical Plan

  ## Prerequisites
  [spec.md must exist]

  ## The Command
  ```bash
  /spec-kitty.plan
  ```

  ## The Planning Interview
  [WAITING_FOR_PLANNING_INPUT explained]

  ## What Gets Created
  [plan.md, research.md, etc.]

  ## Example
  [With tech stack specification]

  ## Troubleshooting
  ```
- **Files**: `docs/how-to/create-plan.md`
- **Parallel?**: Yes

### Subtask T015 – Create generate-tasks.md
- **Purpose**: How to use /spec-kitty.tasks
- **Structure**:
  ```markdown
  # How to Generate Work Packages

  ## Prerequisites
  [plan.md must exist]

  ## The Command
  ```bash
  /spec-kitty.tasks
  ```

  ## What Gets Created
  - tasks.md (overview)
  - tasks/WP01-xxx.md, tasks/WP02-xxx.md (prompt files)

  ## Understanding Work Packages
  [WP structure, dependencies]

  ## Finalizing Tasks
  ```bash
  spec-kitty agent feature finalize-tasks
  ```

  ## Example Output
  ```
- **Files**: `docs/how-to/generate-tasks.md`
- **Parallel?**: Yes

### Subtask T016 – Create implement-work-package.md
- **Purpose**: How to use spec-kitty implement and /spec-kitty.implement
- **Structure**:
  ```markdown
  # How to Implement a Work Package

  ## Prerequisites
  [tasks must be generated and finalized]

  ## Create the Workspace
  ```bash
  spec-kitty implement WP01
  ```

  ## With Dependencies
  ```bash
  spec-kitty implement WP02 --base WP01
  ```

  ## What Happens
  - Creates .worktrees/###-feature-WP01/
  - Creates git branch
  - Moves WP to "doing" lane

  ## Working in the Workspace
  ```bash
  cd .worktrees/###-feature-WP01
  # Your agent works here
  ```

  ## Completing Implementation
  [How to move to for_review]
  ```
- **Files**: `docs/how-to/implement-work-package.md`
- **Parallel?**: Yes
- **Notes**: Critical - must explain worktree model clearly

### Subtask T017 – Create review-work-package.md
- **Purpose**: How to use /spec-kitty.review
- **Structure**:
  ```markdown
  # How to Review a Work Package

  ## Prerequisites
  [WP must be in for_review lane]

  ## The Command
  ```bash
  /spec-kitty.review
  # or
  /spec-kitty.review WP01
  ```

  ## Review Process
  [What the reviewer checks]

  ## Providing Feedback
  [Review Feedback section in WP file]

  ## Passing Review
  [Move to done lane]

  ## Requesting Changes
  [Move back to planned with feedback]
  ```
- **Files**: `docs/how-to/review-work-package.md`
- **Parallel?**: Yes

### Subtask T018 – Create accept-and-merge.md
- **Purpose**: How to use /spec-kitty.accept and /spec-kitty.merge
- **Structure**:
  ```markdown
  # How to Accept and Merge a Feature

  ## Prerequisites
  [All WPs must be in done lane]

  ## Accept the Feature
  ```bash
  /spec-kitty.accept
  # or
  spec-kitty accept
  ```

  ## What Accept Checks
  [Kanban lanes, metadata, activity logs]

  ## Merge to Main
  ```bash
  /spec-kitty.merge --push
  # or
  spec-kitty merge --push
  ```

  ## Merge Strategies
  - Default (merge commit)
  - Squash
  - Keep branch

  ## Cleanup
  [Worktrees removed, branches deleted]
  ```
- **Files**: `docs/how-to/accept-and-merge.md`
- **Parallel?**: Yes

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Commands change | Generate from CLI --help |
| Outdated examples | Use realistic examples |
| Missing edge cases | Add troubleshooting sections |

## Definition of Done Checklist

- [ ] T012: install-and-upgrade.md complete
- [ ] T013: create-specification.md complete
- [ ] T014: create-plan.md complete
- [ ] T015: generate-tasks.md complete
- [ ] T016: implement-work-package.md complete
- [ ] T017: review-work-package.md complete
- [ ] T018: accept-and-merge.md complete
- [ ] All guides have working command examples
- [ ] All guides link to related reference docs

## Review Guidance

- Verify each command example works
- Check that 0.11.0 model is correctly described
- Ensure guides are focused on ONE task each

## Activity Log

- 2026-01-16T16:16:58Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-16T16:30:49Z – __AGENT__ – shell_pid=25069 – lane=doing – Started implementation via workflow command
- 2026-01-16T16:34:56Z – __AGENT__ – shell_pid=25069 – lane=for_review – Ready for review: add core workflow how-to guides
- 2026-01-16T17:49:51Z – claude – shell_pid=58526 – lane=doing – Started review via workflow command
- 2026-01-16T17:50:02Z – claude – shell_pid=58526 – lane=done – Review passed: All 7 core workflow how-to guides created
