---
work_package_id: WP03
title: Specify Command Integration
lane: done
history:
- timestamp: '2025-12-15T11:55:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude
assignee: ''
phase: Phase 2 - Core Workflow
review_status: ''
reviewed_by: ''
shell_pid: '41714'
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
---

# Work Package Prompt: WP03 – Specify Command Integration

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Update `/spec-kitty.specify` prompt to include mission inference step
- LLM analyzes feature description and suggests appropriate mission
- User confirms or overrides mission selection
- Script invocation includes `--mission` flag with selected mission

**Success Metrics** (from spec User Story 1):

- Given description "build a REST API", LLM suggests "software-dev" mission
- Given description "research best practices", LLM suggests "research" mission
- Given explicit "use research mission" in description, system uses research without confirmation
- Feature's meta.json contains `mission` field after specify completes

## Context & Constraints

**Reference Documents**:

- Spec: `kitty-specs/006-per-feature-mission/spec.md` (User Story 1, FR-008)
- Plan: `kitty-specs/006-per-feature-mission/plan.md` (Phase 2)
- Quickstart: `kitty-specs/006-per-feature-mission/quickstart.md` (User workflow)

**Existing Code**:

- `.kittify/missions/software-dev/command-templates/specify.md` - Main prompt template
- Lines 63-66: Script invocation section
- Discovery flow ends around line 60 with intent summary confirmation

**Constraints**:

- Mission selection happens AFTER discovery questions, BEFORE script invocation
- LLM should always confirm mission choice with user (except explicit override)
- Mission selection is conversational, not a rigid form

## Subtasks & Detailed Guidance

### Subtask T011 – Add mission inference section to specify.md

- **Purpose**: Guide LLM to analyze feature description and select mission
- **Files**: `.kittify/missions/software-dev/command-templates/specify.md`
- **Steps**:
  1. Find the section after Intent Summary confirmation (around line 60-62)
  2. Add new section before script invocation:

     ```markdown
     ## Mission Selection

     After the Intent Summary is confirmed, determine the appropriate mission for this feature:

     1. **Analyze the feature description** to identify the primary goal:
        - Building software, APIs, features, tools → **software-dev**
        - Research, investigation, literature review, analysis → **research**

     2. **Check for explicit mission requests** in the user's description:
        - If user says "use research mission" or "this is a research project", use that mission directly
        - If user says "use software-dev" or similar, use that mission directly

     3. **Confirm with user** (unless explicit):
        > "Based on your description, this sounds like a **[software-dev/research]** project.
        > I'll use the **[mission name]** mission which includes [brief phase description].
        > Does that work for you?"

     4. **Handle user response**:
        - If confirmed: proceed with selected mission
        - If user wants different mission: use their choice
        - Store the final mission selection for the script invocation

     **Available Missions**:
     - `software-dev`: For building features, APIs, CLI tools, applications
       - Phases: research → design → implement → test → review
     - `research`: For investigations, literature reviews, analysis
       - Phases: question → methodology → gather → analyze → synthesize → publish
     ```

  3. Ensure this section comes AFTER discovery but BEFORE script execution
- **Parallel?**: No (foundational for T012-T015)

### Subtask T012 – Add list of available missions with descriptions

- **Purpose**: Provide LLM with mission context for accurate inference
- **Files**: `.kittify/missions/software-dev/command-templates/specify.md`
- **Steps**:
  1. The mission list in T011 covers this, but ensure it includes:
     - Mission key (software-dev, research)
     - Brief description of what it's for
     - Workflow phases
  2. This helps LLM make accurate suggestions based on user's description
- **Parallel?**: No (part of T011)

### Subtask T013 – Add mission confirmation question to discovery flow

- **Purpose**: Ensure user explicitly agrees to mission selection
- **Files**: `.kittify/missions/software-dev/command-templates/specify.md`
- **Steps**:
  1. The confirmation is part of T011, but clarify the flow:

     ```
     Discovery Questions → Intent Summary → [USER CONFIRMS] → Mission Selection → [USER CONFIRMS] → Script Execution
     ```

  2. If user doesn't confirm mission, prompt:

     ```markdown
     If the user disagrees:
     > "Which mission would you prefer? Available options are:
     > - **software-dev** - for building software features
     > - **research** - for investigations and analysis"
     ```

  3. Wait for user response before proceeding
- **Parallel?**: No (part of T011)

### Subtask T014 – Update script invocation to include --mission

- **Purpose**: Pass selected mission to create-new-feature.sh
- **Files**: `.kittify/missions/software-dev/command-templates/specify.md`
- **Steps**:
  1. Find the script invocation section (lines 63-66):

     ```markdown
     2. When discovery is complete..., run the script `{SCRIPT}` from repo root, inserting `--feature-name "<Friendly Title>"` ...
     ```

  2. Update to include mission:

     ```markdown
     2. When discovery is complete and the intent summary **and title and mission** are confirmed, run the script `{SCRIPT}` from repo root, inserting `--feature-name "<Friendly Title>"` and `--mission "<selected-mission>"` immediately before the feature description argument. For example:

        - **bash/zsh**: `.kittify/scripts/bash/create-new-feature.sh --json --feature-name "Checkout Upsell Flow" --mission "software-dev" "$ARGUMENTS"`
        - **PowerShell**: `.kittify/scripts/powershell/create-new-feature.ps1 -Json -FeatureName "Checkout Upsell Flow" -Mission "software-dev" "$ARGUMENTS"`
     ```

  3. Update the variable capture section to include MISSION from the confirmation
- **Parallel?**: No (depends on T011)

### Subtask T015 – Handle explicit mission override via flag

- **Purpose**: Support `--mission` flag passed to specify command
- **Files**: `.kittify/missions/software-dev/command-templates/specify.md`
- **Steps**:
  1. Check the frontmatter scripts section:

     ```yaml
     scripts:
       sh: .kittify/scripts/bash/create-new-feature.sh --json "{ARGS}"
     ```

  2. Add handling for `--mission` in ARGS:

     ```markdown
     ### Mission Override

     If the user provides `--mission <key>` as part of their command arguments:
     - Extract the mission key from the arguments
     - Skip the mission inference and confirmation step
     - Use the provided mission directly
     - Validate the mission exists before proceeding

     Example: `/spec-kitty.specify --mission research I want to investigate caching strategies`
     ```

  3. The prompt should detect `--mission` in `$ARGUMENTS` and handle accordingly
- **Parallel?**: No (depends on T011, T014)

### Subtask T016 – Update research mission's specify.md

- **Purpose**: Ensure research mission has same mission selection capability
- **Files**: `.kittify/missions/research/command-templates/specify.md`
- **Steps**:
  1. Check if research mission has its own specify.md:

     ```bash
     ls -la .kittify/missions/research/command-templates/
     ```

  2. If it exists and differs from software-dev, add the same mission selection section
  3. If it doesn't exist or symlinks to software-dev, no action needed
  4. The mission selection should work the same regardless of which mission's specify.md is used
- **Parallel?**: Yes (once T011-T015 establish the pattern)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| LLM makes wrong inference | Always confirm with user; user can override |
| User confused by mission concept | Provide clear descriptions of each mission |
| Prompt too long/complex | Keep mission section concise; single confirmation |
| Research mission specify.md out of sync | Check if it's symlinked or needs separate update |

## Definition of Done Checklist

- [ ] Mission selection section added to specify.md
- [ ] LLM analyzes description and suggests mission
- [ ] User confirmation required before proceeding
- [ ] Script invocation includes `--mission` flag
- [ ] Explicit `--mission` override works
- [ ] Research mission specify.md updated (if needed)
- [ ] meta.json contains mission field after specify completes

## Review Guidance

- Run `/spec-kitty.specify` with software description → should suggest software-dev
- Run `/spec-kitty.specify` with research description → should suggest research
- Run `/spec-kitty.specify --mission research "build an API"` → should use research despite description
- Verify meta.json in created feature has `mission` field
- Check the conversation flow feels natural, not robotic

## Activity Log

- 2025-12-15T11:55:00Z – system – lane=planned – Prompt created.
- 2025-12-15T11:05:40Z – claude – shell_pid=41714 – lane=doing – Started implementation
