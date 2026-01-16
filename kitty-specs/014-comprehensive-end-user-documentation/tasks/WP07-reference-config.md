---
work_package_id: "WP07"
subtasks:
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
title: "Reference - Configuration & Structure"
phase: "Phase 1 - Content Creation"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "57036"
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

# Work Package Prompt: WP07 – Reference - Configuration & Structure

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Create 5 reference documents for configuration, structure, and agents
- **Success**: All configuration options, file paths, and agents documented

## Context & Constraints

- **Spec**: `kitty-specs/014-comprehensive-end-user-documentation/spec.md`
- **Plan**: `kitty-specs/014-comprehensive-end-user-documentation/plan.md`
- **Divio Type**: Reference = information-oriented, complete

## Subtasks & Detailed Guidance

### Subtask T026 – Create configuration.md
- **Purpose**: Document all configuration files and options
- **Structure**:
  ```markdown
  # Configuration Reference

  ## docfx.json
  [DocFX build configuration]

  ## toc.yml
  [Table of contents structure]

  ## meta.json (Feature Metadata)
  ```json
  {
    "feature_number": "014",
    "slug": "014-feature-name",
    "friendly_name": "Feature Name",
    "mission": "software-dev",
    "source_description": "...",
    "created_at": "2026-01-16T..."
  }
  ```

  ## .kittify/active-mission (Legacy)
  [Note: Deprecated in 0.8.0+]

  ## WP Frontmatter
  ```yaml
  work_package_id: "WP01"
  lane: "planned"
  dependencies: ["WP00"]
  # ...
  ```
  ```
- **Files**: `docs/reference/configuration.md`
- **Parallel?**: Yes

### Subtask T027 – Create environment-variables.md
- **Purpose**: Document all environment variables
- **Structure**:
  ```markdown
  # Environment Variables Reference

  ## SPECIFY_FEATURE
  **Purpose**: Override feature detection for non-Git repositories
  **Example**: `export SPECIFY_FEATURE=001-photo-albums`

  ## SPEC_KITTY_TEMPLATE_ROOT
  **Purpose**: Local template source (for development)
  **Example**: `export SPEC_KITTY_TEMPLATE_ROOT=$(git rev-parse --show-toplevel)`

  ## SPECIFY_TEMPLATE_REPO
  **Purpose**: Override GitHub template repository
  **Example**: `export SPECIFY_TEMPLATE_REPO=org/custom-templates`

  ## CODEX_HOME
  **Purpose**: Point Codex CLI to project prompts
  **Example**: `export CODEX_HOME="$(pwd)/.codex"`

  ## GH_TOKEN / GITHUB_TOKEN
  **Purpose**: GitHub API authentication
  ```
- **Files**: `docs/reference/environment-variables.md`
- **Parallel?**: Yes

### Subtask T028 – Create file-structure.md
- **Purpose**: Document the complete directory structure
- **Structure**:
  ```markdown
  # File Structure Reference

  ## Project Root
  ```
  my-project/
  ├── .kittify/              # Spec Kitty configuration
  ├── kitty-specs/           # Feature specifications
  ├── .worktrees/            # Git worktrees (0.11.0+)
  ├── docs/                  # Documentation
  └── src/                   # Your source code
  ```

  ## .kittify/ Directory
  ```
  .kittify/
  ├── templates/             # Document templates
  │   ├── spec-template.md
  │   ├── plan-template.md
  │   ├── tasks-template.md
  │   └── task-prompt-template.md
  ├── missions/              # Mission configurations
  │   ├── software-dev/
  │   ├── research/
  │   └── documentation/
  └── memory/                # Project memory
      └── constitution.md
  ```

  ## kitty-specs/ Directory
  ```
  kitty-specs/
  └── 014-feature-name/
      ├── spec.md
      ├── plan.md
      ├── research.md
      ├── tasks.md
      ├── meta.json
      ├── checklists/
      └── tasks/
          ├── WP01-xxx.md
          └── WP02-xxx.md
  ```

  ## .worktrees/ Directory (0.11.0+)
  ```
  .worktrees/
  ├── 014-feature-name-WP01/  # WP01 workspace
  └── 014-feature-name-WP02/  # WP02 workspace
  ```

  [Explain: One worktree per WP, not per feature]
  ```
- **Files**: `docs/reference/file-structure.md`
- **Parallel?**: Yes
- **Notes**: Critical for understanding the 0.11.0 model

### Subtask T029 – Create missions.md
- **Purpose**: Complete reference for all three missions
- **Structure**:
  ```markdown
  # Missions Reference

  ## software-dev (Default)
  **Domain**: Software development
  **Phases**: research → design → implement → test → review
  **Artifacts**: spec.md, plan.md, tasks.md, data-model.md, contracts/

  ## research
  **Domain**: Research and analysis
  **Phases**: question → methodology → gather → analyze → synthesize → publish
  **Artifacts**: spec.md, plan.md, tasks.md, findings.md, sources/

  ## documentation
  **Domain**: Documentation creation
  **Phases**: discover → audit → design → generate → validate → publish
  **Artifacts**: spec.md, plan.md, gap-analysis.md, divio-templates/

  ## Mission Configuration Files
  [Location: .kittify/missions/<key>/mission.yaml]

  ## Per-Feature Mission Selection
  [Selected during /spec-kitty.specify, stored in meta.json]
  ```
- **Files**: `docs/reference/missions.md`
- **Parallel?**: Yes

### Subtask T030 – Create supported-agents.md
- **Purpose**: Document all 12 supported AI agents
- **Structure**:
  ```markdown
  # Supported AI Agents Reference

  Spec Kitty supports 12 AI coding agents.

  | Agent | Directory | Commands Directory |
  |-------|-----------|-------------------|
  | Claude Code | `.claude/` | `commands/` |
  | GitHub Copilot | `.github/` | `prompts/` |
  | Google Gemini | `.gemini/` | `commands/` |
  | Cursor | `.cursor/` | `commands/` |
  | Qwen Code | `.qwen/` | `commands/` |
  | OpenCode | `.opencode/` | `command/` |
  | Windsurf | `.windsurf/` | `workflows/` |
  | GitHub Codex | `.codex/` | `prompts/` |
  | Kilocode | `.kilocode/` | `workflows/` |
  | Augment Code | `.augment/` | `commands/` |
  | Roo Cline | `.roo/` | `commands/` |
  | Amazon Q | `.amazonq/` | `prompts/` |

  ## Agent-Specific Notes

  ### Claude Code
  [Primary supported agent]

  ### Amazon Q
  [Does not support custom slash command arguments]

  ## Multi-Agent Setup
  ```bash
  spec-kitty init my-project --ai claude,codex
  ```
  ```
- **Files**: `docs/reference/supported-agents.md`
- **Parallel?**: Yes

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Configuration changes | Cross-reference source code |
| Missing env vars | Check codebase for all uses |
| File structure inaccurate | Verify against actual project |

## Definition of Done Checklist

- [ ] T026: configuration.md documents all config files
- [ ] T027: environment-variables.md lists all env vars
- [ ] T028: file-structure.md shows complete directory layout
- [ ] T029: missions.md covers all 3 missions in detail
- [ ] T030: supported-agents.md lists all 12 agents

## Review Guidance

- Verify file paths against actual project structure
- Check env vars against codebase
- Ensure missions match current implementation

## Activity Log

- 2026-01-16T16:16:58Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-16T16:31:33Z – claude – shell_pid=29749 – lane=doing – Started implementation via workflow command
- 2026-01-16T16:35:15Z – claude – shell_pid=29749 – lane=for_review – All 5 reference docs created: configuration.md, environment-variables.md, file-structure.md, missions.md, supported-agents.md
- 2026-01-16T17:48:00Z – claude – shell_pid=57036 – lane=doing – Started review via workflow command
- 2026-01-16T17:48:14Z – claude – shell_pid=57036 – lane=done – Review passed: All 5 reference docs complete with comprehensive coverage of configuration, env vars, file structure, missions, and agents
