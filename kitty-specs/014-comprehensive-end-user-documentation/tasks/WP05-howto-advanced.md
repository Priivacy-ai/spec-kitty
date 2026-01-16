---
work_package_id: "WP05"
subtasks:
  - "T019"
  - "T020"
  - "T021"
  - "T022"
title: "How-To Guides - Advanced Workflow"
phase: "Phase 1 - Content Creation"
lane: "doing"
assignee: ""
agent: "__AGENT__"
shell_pid: "25767"
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

# Work Package Prompt: WP05 – How-To Guides - Advanced Workflow

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Create 4 how-to guides for advanced spec-kitty features
- Cover dependencies, missions, dashboard, and parallel development
- **Success**: User can accomplish advanced tasks following each guide

## Context & Constraints

- **Spec**: `kitty-specs/014-comprehensive-end-user-documentation/spec.md`
- **Plan**: `kitty-specs/014-comprehensive-end-user-documentation/plan.md`
- **Divio Type**: How-To = task-oriented, problem-solving

## Subtasks & Detailed Guidance

### Subtask T019 – Create handle-dependencies.md
- **Purpose**: How to work with WP dependencies and --base flag
- **Structure**:
  ```markdown
  # How to Handle Work Package Dependencies

  ## Understanding Dependencies
  [What dependencies mean in frontmatter]

  ## Declaring Dependencies
  ```yaml
  dependencies: ["WP01"]
  ```

  ## Implementing with Dependencies
  ```bash
  spec-kitty implement WP02 --base WP01
  ```

  ## Multiple Dependencies
  ```bash
  spec-kitty implement WP04 --base WP03
  cd .worktrees/###-feature-WP04
  git merge ###-feature-WP02  # Manual merge
  ```

  ## What --base Does
  [Branches from parent WP, includes code]

  ## Handling Rebase When Parent Changes
  [git rebase commands]

  ## Common Dependency Patterns
  - Linear chain
  - Fan-out
  - Diamond
  ```
- **Files**: `docs/how-to/handle-dependencies.md`
- **Parallel?**: Yes
- **Notes**: Include diagrams of dependency patterns

### Subtask T020 – Create switch-missions.md
- **Purpose**: How to select and work with different missions
- **Structure**:
  ```markdown
  # How to Switch Missions

  ## Understanding Per-Feature Missions
  [Missions selected during /spec-kitty.specify]

  ## Mission Selection
  ```bash
  /spec-kitty.specify "Research market viability"
  # → Infers "research" mission
  ```

  ## Listing Available Missions
  ```bash
  spec-kitty mission list
  ```

  ## Getting Mission Info
  ```bash
  spec-kitty mission info research
  ```

  ## Working with Different Missions

  ### Software Dev Mission
  [Workflow: specify → plan → tasks → implement]

  ### Research Mission
  [Workflow: question → methodology → gather → analyze]

  ### Documentation Mission
  [Workflow: audit → design → generate → validate]
  ```
- **Files**: `docs/how-to/switch-missions.md`
- **Parallel?**: Yes

### Subtask T021 – Create use-dashboard.md
- **Purpose**: How to use the real-time kanban dashboard
- **Structure**:
  ```markdown
  # How to Use the Spec Kitty Dashboard

  ## Starting the Dashboard
  ```bash
  spec-kitty dashboard
  # or
  /spec-kitty.dashboard
  ```

  ## Dashboard URL
  [Default port, accessing in browser]

  ## Dashboard Views

  ### Kanban Board
  [planned → doing → for_review → done]

  ### Feature Overview
  [Progress metrics, artifacts]

  ## Custom Port
  ```bash
  spec-kitty dashboard --port 8080
  ```

  ## Stopping the Dashboard
  ```bash
  spec-kitty dashboard --kill
  ```

  ## Dashboard Auto-Start
  [Starts with spec-kitty init]
  ```
- **Files**: `docs/how-to/use-dashboard.md`
- **Parallel?**: Yes

### Subtask T022 – Create parallel-development.md
- **Purpose**: How to run multiple agents on multiple WPs simultaneously
- **Structure**:
  ```markdown
  # How to Develop in Parallel with Multiple Agents

  ## Why Parallel Development?
  [Speed benefits, workspace isolation]

  ## Prerequisites
  - Feature with multiple WPs
  - Multiple terminals/agents available

  ## Identifying Parallel Opportunities
  [Check WP dependencies - independent WPs can run in parallel]

  ## Example: Two Independent WPs

  ### Terminal 1 - Agent A
  ```bash
  spec-kitty implement WP01
  cd .worktrees/###-feature-WP01
  # Agent A implements WP01
  ```

  ### Terminal 2 - Agent B (simultaneously)
  ```bash
  spec-kitty implement WP02
  cd .worktrees/###-feature-WP02
  # Agent B implements WP02
  ```

  ## Example: Fan-Out Pattern
  ```
       WP01
      /  |  \
   WP02 WP03 WP04
  ```
  [After WP01 completes, 3 agents can work in parallel]

  ## Example: Dependent WPs
  ```bash
  # Agent A completes WP01
  spec-kitty implement WP01
  # ...

  # Agent B starts WP02 after WP01 exists
  spec-kitty implement WP02 --base WP01
  ```

  ## Best Practices
  - Identify independent WPs before starting
  - Communicate when a base WP is complete
  - Use /spec-kitty.status to monitor progress

  ## Monitoring Parallel Work
  ```bash
  spec-kitty agent tasks status
  /spec-kitty.status
  ```
  ```
- **Files**: `docs/how-to/parallel-development.md`
- **Parallel?**: Yes
- **Notes**: **CRITICAL** - This is key for advanced users. Must be comprehensive.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Parallel workflow complex | Include diagrams |
| Dashboard port conflicts | Document --port flag |
| Dependency mistakes | Show error messages |

## Definition of Done Checklist

- [ ] T019: handle-dependencies.md complete with patterns
- [ ] T020: switch-missions.md covers all 3 missions
- [ ] T021: use-dashboard.md with screenshots if possible
- [ ] T022: parallel-development.md comprehensive with examples
- [ ] All guides have working command examples

## Review Guidance

- Test parallel-development.md by running multiple agents
- Verify dashboard commands work
- Check dependency examples are accurate

## Activity Log

- 2026-01-16T16:16:58Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-16T16:31:00Z – __AGENT__ – shell_pid=25767 – lane=doing – Started implementation via workflow command
