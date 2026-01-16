---
work_package_id: "WP03"
subtasks:
  - "T008"
  - "T009"
  - "T010"
  - "T011"
title: "Tutorials"
phase: "Phase 1 - Content Creation"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "58186"
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

# Work Package Prompt: WP03 – Tutorials

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Create 4 learning-oriented tutorials for new spec-kitty users
- Tutorials must be step-by-step, testable end-to-end
- **Success**: A new user can follow getting-started.md and create their first feature within 30 minutes

## Context & Constraints

- **Spec**: `kitty-specs/014-comprehensive-end-user-documentation/spec.md`
- **Plan**: `kitty-specs/014-comprehensive-end-user-documentation/plan.md`
- **Target Audience**: End users new to spec-kitty
- **Divio Type**: Tutorial = learning-oriented, step-by-step guides

### Tutorial Principles (from Divio)
- Tutorials are **learning-oriented**
- Allow users to learn by doing
- Get the user started (not comprehensive)
- Ensure the user sees results immediately
- Tutorial must work (testable end-to-end)
- Focus on concrete steps, not explanations

## Subtasks & Detailed Guidance

### Subtask T008 – Create getting-started.md
- **Purpose**: Get users from zero to first spec in 30 minutes
- **Steps**:
  1. Create `docs/tutorials/getting-started.md`
  2. Structure:
     ```markdown
     # Getting Started with Spec Kitty

     In this tutorial, you'll install Spec Kitty and create your first feature specification.

     **Time**: ~30 minutes
     **Prerequisites**: Python 3.11+, Git, an AI coding agent (Claude Code, etc.)

     ## Step 1: Install Spec Kitty
     [pip/uv installation commands]

     ## Step 2: Initialize a Project
     [spec-kitty init commands]

     ## Step 3: Create Your First Specification
     [/spec-kitty.specify walkthrough]

     ## Step 4: Verify Your Work
     [Check kitty-specs/ directory]

     ## What's Next?
     [Links to your-first-feature.md, how-to guides]
     ```
  3. Include actual commands with expected output
  4. Add troubleshooting section for common errors
- **Files**: `docs/tutorials/getting-started.md`
- **Parallel?**: Yes - can run alongside T009-T011
- **Notes**: Test the tutorial yourself to verify it works

### Subtask T009 – Create your-first-feature.md
- **Purpose**: Walk through the complete 0.11.0 workflow
- **Steps**:
  1. Create `docs/tutorials/your-first-feature.md`
  2. Structure:
     ```markdown
     # Your First Feature: Complete Workflow

     This tutorial walks you through the entire spec-kitty workflow from specification to merge.

     **Time**: ~2 hours
     **Prerequisites**: Completed Getting Started tutorial

     ## Overview
     [Diagram: specify → plan → tasks → implement → review → accept → merge]

     ## Step 1: Create the Specification
     [/spec-kitty.specify with example]

     ## Step 2: Create the Technical Plan
     [/spec-kitty.plan with example]

     ## Step 3: Generate Work Packages
     [/spec-kitty.tasks - explain WP files]

     ## Step 4: Implement a Work Package
     [spec-kitty implement WP01 - explain worktree creation]

     ## Step 5: Review Your Work
     [/spec-kitty.review]

     ## Step 6: Accept and Merge
     [/spec-kitty.accept and /spec-kitty.merge]

     ## What's Next?
     [Links to missions, parallel development]
     ```
  3. Use a concrete example (e.g., "Build a task list app")
  4. Emphasize the 0.11.0 model: planning in main, worktrees on-demand
- **Files**: `docs/tutorials/your-first-feature.md`
- **Parallel?**: Yes
- **Notes**: Critical for user onboarding - must be accurate

### Subtask T010 – Create missions-overview.md
- **Purpose**: Help users understand the mission system
- **Steps**:
  1. Create `docs/tutorials/missions-overview.md`
  2. Structure:
     ```markdown
     # Understanding Spec Kitty Missions

     Spec Kitty supports three types of projects through its mission system.

     ## What is a Mission?
     [Brief explanation]

     ## The Three Missions

     ### Software Dev Kitty
     [When to use, example]

     ### Deep Research Kitty
     [When to use, example]

     ### Documentation Kitty
     [When to use, example]

     ## Try It: Creating a Research Feature
     [Hands-on example with research mission]

     ## How Missions Affect Your Workflow
     [Different phases, templates, artifacts]
     ```
- **Files**: `docs/tutorials/missions-overview.md`
- **Parallel?**: Yes
- **Notes**: Link to reference/missions.md for complete details

### Subtask T011 – Create multi-agent-workflow.md
- **Purpose**: Teach users how to run multiple AI agents in parallel
- **Steps**:
  1. Create `docs/tutorials/multi-agent-workflow.md`
  2. Structure:
     ```markdown
     # Multi-Agent Parallel Development

     Learn how to coordinate multiple AI agents working on different work packages simultaneously.

     **Time**: ~1 hour
     **Prerequisites**: Completed Your First Feature tutorial

     ## Why Parallel Development?
     [Faster delivery, workspace isolation]

     ## Understanding Work Package Dependencies
     [Linear, fan-out, diamond patterns]

     ## Hands-On: Two Agents, Two WPs

     ### Setup
     [Create a feature with independent WPs]

     ### Terminal 1: Agent A on WP01
     ```bash
     spec-kitty implement WP01
     cd .worktrees/###-feature-WP01
     # Agent A works here
     ```

     ### Terminal 2: Agent B on WP02
     ```bash
     spec-kitty implement WP02
     cd .worktrees/###-feature-WP02
     # Agent B works here simultaneously
     ```

     ## Handling Dependencies with --base
     [When WP02 depends on WP01]

     ## Git Worktrees Explained
     [Brief explanation with link to explanation/git-worktrees.md]

     ## Tips for Coordinating Agents
     [Practical advice]
     ```
- **Files**: `docs/tutorials/multi-agent-workflow.md`
- **Parallel?**: Yes
- **Notes**: This is key for advanced users - include concrete examples

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Tutorials become outdated | Use CLI --help output as source |
| Commands don't work | Test tutorials end-to-end |
| Too long/complex | Focus on learning, not completeness |

## Definition of Done Checklist

- [ ] T008: getting-started.md created and testable
- [ ] T009: your-first-feature.md created with complete workflow
- [ ] T010: missions-overview.md covers all three missions
- [ ] T011: multi-agent-workflow.md explains parallel development clearly
- [ ] All tutorials have troubleshooting sections
- [ ] All tutorials link to related how-tos and references
- [ ] Committed to repository

## Review Guidance

- Actually run through each tutorial to verify it works
- Check that commands produce expected output
- Verify links to other docs are correct
- Ensure 0.11.0 model is accurately described

## Activity Log

- 2026-01-16T16:16:58Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-16T16:30:42Z – __AGENT__ – shell_pid=26746 – lane=doing – Started implementation via workflow command
- 2026-01-16T16:36:58Z – __AGENT__ – shell_pid=26746 – lane=for_review – Ready for review: added four tutorials with step-by-step workflows, troubleshooting, and cross-links.
- 2026-01-16T17:42:21Z – __AGENT__ – shell_pid=26746 – lane=doing – Resume: added tutorials to toc navigation.
- 2026-01-16T17:42:24Z – __AGENT__ – shell_pid=26746 – lane=for_review – Ready for review: added tutorials to toc navigation.
- 2026-01-16T17:43:31Z – __AGENT__ – shell_pid=26746 – lane=doing – Resume: added tutorials links to docs index.
- 2026-01-16T17:43:34Z – __AGENT__ – shell_pid=26746 – lane=for_review – Ready for review: added tutorial links to docs index and toc.
- 2026-01-16T17:49:30Z – claude – shell_pid=58186 – lane=doing – Started review via workflow command
- 2026-01-16T17:49:41Z – claude – shell_pid=58186 – lane=done – Review passed: All 4 tutorials created (getting-started, your-first-feature, missions-overview, multi-agent-workflow)
