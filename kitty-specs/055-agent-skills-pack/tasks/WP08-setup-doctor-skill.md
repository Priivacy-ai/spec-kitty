---
work_package_id: WP08
title: Author spec-kitty-setup-doctor Skill
lane: planned
dependencies: [WP01]
subtasks:
- T032
- T033
- T034
- T035
phase: Phase 1 - Core Implementation
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-21T07:39:56Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-009
- FR-010
- C-006
- C-007
---

# Work Package Prompt: WP08 – Author spec-kitty-setup-doctor Skill

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Write the first canonical shipped skill following PRD section 8 guidance
- Include SKILL.md with proper frontmatter, triggers, workflow, and negative scope
- Create reference documents for agent path matrix and common failure signatures
- Validate content quality against PRD design principles

**Success**: `spec-kitty-setup-doctor/SKILL.md` has valid frontmatter (`name`, `description`), clear positive triggers, explicit negative scope, and actionable setup/verify/recovery workflow.

## Context & Constraints

- **PRD reference**: Section 7 (skill table) and Section 8 (`spec-kitty-setup-doctor` details)
- **Constraint C-006**: Only 8 PRD-defined skills shipped
- **Constraint C-007**: Minimal frontmatter — `name` and `description` only
- **PRD Principle 5**: Keep SKILL.md concise; move long guidance to references/
- **PRD Principle 10**: Descriptions with specific positive triggers and explicit negative scope
- **Dependencies**: WP01 (directory structure exists)

**Implementation command**: `spec-kitty implement WP08 --base WP01`

## Subtasks & Detailed Guidance

### Subtask T032 – Write SKILL.md

- **Purpose**: Create the canonical setup/doctor skill that helps users install, verify, and recover Spec Kitty.
- **Steps**:
  1. Replace the placeholder in `src/doctrine/skills/spec-kitty-setup-doctor/SKILL.md`
  2. Frontmatter (PRD principle 9 — minimal):
     ```yaml
     ---
     name: spec-kitty-setup-doctor
     description: >-
       Install, verify, and recover the modern Spec Kitty 2.0.11+ operating surface.
       Triggers: "set up Spec Kitty", "skills missing", "next is blocked",
       "runtime is broken", "doctrine assets are missing", "my agent can't find the skills".
       Does NOT handle: generic coding questions with no Spec Kitty context,
       direct runtime loop advancement, or editorial glossary maintenance.
     ---
     ```
  3. Body structure (from PRD section 8):
     - **Step 1: Detect Environment** — identify active agent, repository state, working directory
     - **Step 2: Verify Installation** — check skill roots, wrapper roots, manifest state, generated artifacts
     - **Step 3: Check Prerequisites** — verify cwd, branch, worktree, dashboard, runtime
     - **Step 4: Diagnose Issues** — apply common failure pattern matching (see references)
     - **Step 5: Recover** — apply deterministic recovery steps for identified issues
     - **Step 6: Direct Next Action** — point user to correct `spec-kitty` command
  4. Each step should include:
     - What to check / what to do
     - CLI commands to run (e.g., `spec-kitty verify`, `spec-kitty init`, `spec-kitty sync`)
     - Expected outcomes
  5. Keep body under ~200 lines. Move detailed tables and failure patterns to references/
- **Files**: `src/doctrine/skills/spec-kitty-setup-doctor/SKILL.md` (replace placeholder)
- **Notes**:
  - No repo-specific absolute paths
  - No internal-only assumptions
  - Reference `references/agent-path-matrix.md` and `references/common-failure-signatures.md` for details

### Subtask T033 – Create agent-path-matrix reference

- **Purpose**: Detailed table of all 13 agents with their skill roots, wrapper roots, and installation classes.
- **Steps**:
  1. Create `src/doctrine/skills/spec-kitty-setup-doctor/references/agent-path-matrix.md`
  2. Content:
     ```markdown
     # Agent Path Matrix

     Reference: Framework capability matrix for Spec Kitty 2.0.11+

     | Agent | Installation Class | Skill Root(s) | Wrapper Root |
     |-------|-------------------|---------------|--------------|
     | Claude Code | native-root-required | `.claude/skills/` | `.claude/commands/` |
     | GitHub Copilot | shared-root-capable | `.agents/skills/` | `.github/prompts/` |
     ...
     ```
  3. Include all 13 agents from `AI_CHOICES` / PRD section 6
  4. Add notes about shared root behavior and wrapper-only agents
- **Files**: `src/doctrine/skills/spec-kitty-setup-doctor/references/agent-path-matrix.md` (new, ~60 lines)

### Subtask T034 – Create common failure signatures reference

- **Purpose**: Catalog of known failure patterns and their recovery steps.
- **Steps**:
  1. Create `src/doctrine/skills/spec-kitty-setup-doctor/references/common-failure-signatures.md`
  2. Content:
     ```markdown
     # Common Failure Signatures

     ## Missing Skill Root

     **Symptom**: Agent cannot find skills; `spec-kitty verify` reports missing skill files.
     **Cause**: Init was run before skill pack was available, or skill root was deleted.
     **Recovery**: Run `spec-kitty sync --repair-skills` or re-run `spec-kitty init --here`.

     ## Missing Wrapper Root

     **Symptom**: Slash commands not found by agent.
     **Cause**: Agent directory was deleted or init was interrupted.
     **Recovery**: Re-run `spec-kitty init --here` with the affected agent.

     ## Manifest Drift

     **Symptom**: `spec-kitty verify` reports drifted skill files.
     **Cause**: Managed skill files were manually edited.
     **Recovery**: Run `spec-kitty sync --repair-skills` to restore canonical content.

     ## Runtime Not Found

     **Symptom**: "next is blocked", "runtime can't find missions".
     **Cause**: .kittify/ directory missing or corrupted.
     **Recovery**: Run `spec-kitty init --here` to reinitialize in current directory.

     ## Dashboard Not Starting

     **Symptom**: Dashboard URL not accessible after init.
     **Cause**: Port conflict or dashboard process crashed.
     **Recovery**: Run `spec-kitty dashboard` to restart.
     ```
  3. Include 5-8 common failure patterns with symptom/cause/recovery format
- **Files**: `src/doctrine/skills/spec-kitty-setup-doctor/references/common-failure-signatures.md` (new, ~80 lines)

### Subtask T035 – Validate skill content quality

- **Purpose**: Ensure the skill meets PRD quality standards.
- **Steps**:
  1. Validate against PRD section 7 trigger table:
     - Positive triggers match: "set up Spec Kitty", "skills missing", "next is blocked", "runtime is broken"
     - Negative scope: "generic coding questions with no Spec Kitty context"
  2. Validate against PRD design principles:
     - Principle 5: SKILL.md is concise, detail in references
     - Principle 8: No repo-specific absolute paths
     - Principle 9: Frontmatter has only `name` and `description`
     - Principle 10: Description has positive triggers and negative scope
     - Principle 11: Local-first operation
  3. Check that recovery steps reference real `spec-kitty` commands
  4. Document validation results as comments in a review note
- **Files**: No file changes — validation only
- **Parallel?**: Yes (after T032-T034)

## Risks & Mitigations

- **Trigger precision**: Vague triggers may cause false activations → include explicit negative scope in description
- **Stale commands**: Referenced CLI commands may change → use only commands that exist in 2.0.11+
- **Content bloat**: SKILL.md growing too large → enforce ~200 line limit, move detail to references

## Review Guidance

- Verify frontmatter has ONLY `name` and `description` (no extra fields)
- Verify positive trigger phrases match PRD section 7
- Verify negative scope boundaries are explicit
- Verify SKILL.md body is concise (<200 lines)
- Verify references contain detailed tables and patterns
- Verify no absolute paths or repo-specific assumptions

## Activity Log

- 2026-03-21T07:39:56Z – system – lane=planned – Prompt created.
