---
work_package_id: "WP08"
subtasks:
  - "T057"
  - "T058"
  - "T059"
  - "T060"
  - "T061"
title: "Documentation & Terminology Clarification"
phase: "Phase 5 - Polish"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "5975"
history:
  - timestamp: "2025-01-16T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 – Documentation & Terminology Clarification

## Objectives & Success Criteria

**Goal**: Establish clear, consistent terminology across all documentation distinguishing Project (codebase), Feature (unit of work), and Mission (domain mode).

**Success Criteria**:
- Glossary section added to README.md with clear definitions and examples
- All user-facing documentation uses consistent terminology
- CLI help text uses standard terms
- Error messages use consistent terminology
- Command prompts use consistent terminology
- Users can find term definitions within 1 minute
- All 5 subtasks (T057-T061) completed
- Zero inconsistent terminology in main documentation paths

## Context & Constraints

**Problem Statement**: Terminology confusion creates communication barriers:
- "Project" sometimes means entire codebase, sometimes means "feature"
- "Mission" confused with "feature" in user feedback
- No clear definitions in documentation
- Inconsistent usage across README, CLI, error messages

**User Feedback Examples**:
> "What's the difference between a mission and a project?"
> "Do I create a new project or a new feature?"
> "Is mission the same as task?"

**Supporting Documents**:
- Spec: `kitty-specs/005-refactor-mission-system/spec.md` (User Story 6, FR-024 through FR-026)
- Original Analysis: Identified this as terminology confusion issue

**Standard Definitions** (to enforce):

- **Project**: The entire codebase being developed
  - Examples: "spec-kitty project", "priivacy_rust project", "my-app project"
  - Usage: Top-level repository, contains all features and configuration

- **Feature**: A single unit of work tracked by spec-kitty
  - Examples: "001-mission-system-architecture feature", "042-auth-flow feature"
  - Usage: One spec.md + plan.md + tasks.md + implementation
  - Lifecycle: Created → Developed in worktree → Merged to main

- **Mission**: Domain adapter / workflow mode
  - Examples: "software-dev mission", "research mission", "writing mission"
  - Usage: Determines templates, validation rules, workflow phases
  - Scope: Project-wide (all features in a project use same mission)

**Terminology to AVOID**:
- "Project" when meaning "feature" (e.g., "start a new project" → "start a new feature")
- "Task" when meaning "feature" (reserved for subtasks within features)
- "Workflow" when meaning "mission" (workflow is a mission attribute)

## Subtasks & Detailed Guidance

### Subtask T057 – Add glossary to README.md

**Purpose**: Create definitive terminology reference in main documentation.

**Steps**:
1. Open README.md
2. Add glossary section (suggested location: after Quick Start, before detailed sections):
   ```markdown
   ## Terminology

   Spec Kitty uses specific terms to describe different aspects of development:

   ### Project
   **Definition**: The entire codebase you're developing.

   **Examples**:
   - "spec-kitty project" (this CLI tool)
   - "priivacy_rust project" (Rust application)
   - "my-web-app project" (your application)

   **Usage**: This is your top-level Git repository. A project contains:
   - One active mission (domain mode)
   - Multiple features (units of work)
   - Configuration in `.kittify/`

   **Commands**: Initialize with `spec-kitty init my-project`

   ---

   ### Feature
   **Definition**: A single unit of work tracked by spec-kitty.

   **Examples**:
   - "001-auth-system feature"
   - "042-payment-flow feature"
   - "005-refactor-mission-system feature" (this document)

   **Structure**: Each feature includes:
   - spec.md (requirements)
   - plan.md (technical design)
   - tasks.md (work packages)
   - Implementation in worktree (`.worktrees/###-feature-name/`)

   **Lifecycle**:
   1. Created: `/spec-kitty.specify "feature description"`
   2. Planned: `/spec-kitty.plan`
   3. Broken into tasks: `/spec-kitty.tasks`
   4. Implemented: `/spec-kitty.implement`
   5. Reviewed: `/spec-kitty.review`
   6. Accepted: `/spec-kitty.accept`
   7. Merged: `/spec-kitty.merge`

   **Commands**: Create with `/spec-kitty.specify`

   ---

   ### Mission
   **Definition**: Domain adapter that configures spec-kitty for different types of work.

   **Examples**:
   - "software-dev mission" (default - build software with TDD)
   - "research mission" (conduct systematic research)
   - "writing mission" (future - content creation)

   **What Missions Define**:
   - Workflow phases (software: design → implement → test | research: question → methodology → gather)
   - Templates (spec format, plan structure)
   - Validation rules (tests pass | sources cited)
   - Path conventions (src/ vs research/)

   **Scope**: Project-wide. All features in a project use the same mission. Switch missions between features using `spec-kitty mission switch`.

   **Commands**:
   - Select during init: `spec-kitty init my-project --mission research`
   - Switch missions: `spec-kitty mission switch research`
   - View current: `spec-kitty mission current`
   - List available: `spec-kitty mission list`

   ---

   ### Quick Reference

   | Term | Scope | Example | Command |
   |------|-------|---------|---------|
   | **Project** | Entire codebase | "spec-kitty project" | `spec-kitty init my-project` |
   | **Feature** | Unit of work | "001-auth-system feature" | `/spec-kitty.specify "auth"` |
   | **Mission** | Domain mode | "research mission" | `spec-kitty mission switch research` |

   ### Common Questions

   **Q: What's the difference between a project and a feature?**
   A: A **project** is your entire codebase (one Git repo). A **feature** is one unit of work within that project (one spec.md + implementation).

   **Q: Can I have multiple missions in one project?**
   A: No, but you can switch between missions. Example: Use research mission for investigation, switch to software-dev for implementation.

   **Q: Do I create a new project for each feature?**
   A: No! Create one project, then create multiple features within it using `/spec-kitty.specify`.

   **Q: What's a task?**
   A: Tasks (T001, T002, etc.) are subtasks within a feature's work packages. Don't confuse with "features."
   ```

3. Save README.md

**Files**: `README.md`

**Parallel?**: Yes (independent from other doc updates)

**Notes**: This is the authoritative definition source. Other docs should reference this.

---

### Subtask T058 – Update README terminology consistency

**Purpose**: Search and replace inconsistent terminology throughout README.

**Steps**:
1. Open README.md
2. Search for problematic patterns and fix:

   **Pattern 1**: "Create a new project" when meaning "feature"
   ```
   FIND: "create a new project"
   CONTEXT: If talking about /spec-kitty.specify
   REPLACE: "create a new feature"
   ```

   **Pattern 2**: "Project" in feature context
   ```
   FIND: "The project includes spec.md, plan.md, tasks.md"
   REPLACE: "The feature includes spec.md, plan.md, tasks.md"
   ```

   **Pattern 3**: Ambiguous "workflow"
   ```
   FIND: "Select a workflow"
   REPLACE: "Select a mission"
   ```

3. Review each section:
   - **Quick Start**: Should say "initialize a project", "create features"
   - **Commands**: `/spec-kitty.specify` creates a "feature", not a "project"
   - **Dashboard**: Shows "features" organized by lane
   - **Mission System**: Explains "missions" vs "features" clearly

4. Verify examples use consistent terminology:
   ```markdown
   # Good example
   spec-kitty init my-project                    # Create project
   cd my-project
   /spec-kitty.specify "auth system"            # Create feature
   spec-kitty mission switch research            # Switch mission
   /spec-kitty.specify "security review"        # Create another feature

   # Bad example (inconsistent)
   spec-kitty init my-project                    # Create project
   /spec-kitty.specify "auth system"            # Create project ❌
   ```

**Files**: `README.md`

**Parallel?**: No (should come after T057 for reference)

**Notes**: Use glossary as guide. Be thorough - README is first thing users see.

---

### Subtask T059 – Update CLI help text

**Purpose**: Ensure all CLI commands use consistent terminology in help strings.

**Steps**:
1. Locate CLI command definitions in `src/specify_cli/cli/commands/`
2. Review help strings in all commands:

   **Init command** (init.py):
   ```python
   def init(
       project_name: str = typer.Argument(None, help="Name for your new project directory"),
       mission_key: str = typer.Option(None, "--mission", help="Mission to activate (software-dev, research)"),
       ...
   ):
       """Initialize a new Spec Kitty project."""  # ✓ Correct - "project"
   ```

   **Mission commands** (mission.py from WP03):
   ```python
   @app.command("list")
   def list_cmd():
       """List all available missions."""  # ✓ Correct - "missions"

   @app.command("switch")
   def switch_cmd(...):
       """Switch to a different mission."""  # ✓ Correct - "mission"
   ```

3. Check for inconsistencies:
   - Commands that say "project" when they mean "feature"
   - Commands that confuse "mission" and "feature"
   - Ambiguous terms like "spec", "task", "work"

4. Update help text where needed
5. Test: Run `spec-kitty --help`, `spec-kitty mission --help`, etc. - verify clear

**Files**: `src/specify_cli/cli/commands/*.py`

**Parallel?**: Yes (can review different command files simultaneously)

**Notes**: Help text is user-facing - must be crystal clear.

---

### Subtask T060 – Update error messages

**Purpose**: Ensure error messages use consistent terminology.

**Steps**:
1. Search codebase for error messages:
   ```bash
   grep -r "Error:" src/specify_cli/
   grep -r "raise.*Error" src/specify_cli/
   ```

2. Review each error message for terminology:

   **Example issues to fix**:
   ```python
   # Before (inconsistent)
   raise MissionError("Cannot find project")  # ❌ Ambiguous

   # After (clear)
   raise MissionError("Cannot find mission directory")  # ✓ Clear
   ```

   ```python
   # Before
   print("Feature not found")  # ❌ Could mean mission or feature

   # After
   print("Feature '001-auth-system' not found")  # ✓ Explicit
   ```

3. Key error messages to review:
   - MissionNotFoundError messages (should say "mission", not "project")
   - Feature creation errors (should say "feature", not "project")
   - Worktree errors (should reference "feature worktree")
   - Path errors (should say which mission expects which paths)

4. Update errors to match glossary terminology
5. Test error scenarios to verify messages clear

**Files**: `src/specify_cli/mission.py`, `src/specify_cli/guards.py`, `src/specify_cli/cli/commands/*.py`

**Parallel?**: Yes (different modules can be reviewed in parallel)

**Notes**: Grep for common error patterns, review each for clarity.

---

### Subtask T061 – Update command prompts terminology

**Purpose**: Ensure command prompt files use consistent terminology.

**Steps**:
1. Search command prompts for terminology:
   ```bash
   grep -r "project" .kittify/missions/*/commands/*.md
   grep -r "workflow" .kittify/missions/*/commands/*.md
   grep -r "task" .kittify/missions/*/commands/*.md
   ```

2. Review each usage:

   **Correct usages** (preserve):
   - "project root" ✓ (filesystem term)
   - "project directory" ✓ (filesystem term)
   - "mission workflow" ✓ (mission attribute)
   - "subtask" ✓ (T001, T002, etc.)
   - "work package" ✓ (WP01, WP02, etc.)

   **Incorrect usages** (fix):
   - "Create a new project" → "Create a new feature" (when in feature context)
   - "This project includes" → "This feature includes" (when describing feature artifacts)
   - "project mission" → "active mission" or "mission"

3. Update prompts where needed
4. Verify examples in prompts use correct terminology

**Files**: `.kittify/missions/software-dev/commands/*.md`, `.kittify/missions/research/commands/*.md`

**Parallel?**: Yes (each prompt file can be reviewed independently)

**Notes**: May overlap with WP06 edits - coordinate if updating same files.

---

## Test Strategy

**Terminology Audit Approach**:

1. **Automated Search**:
   ```bash
   # Find all uses of key terms
   grep -rn "project" README.md src/ .kittify/ | grep -v ".git" > audit-project.txt
   grep -rn "feature" README.md src/ .kittify/ | grep -v ".git" > audit-feature.txt
   grep -rn "mission" README.md src/ .kittify/ | grep -v ".git" > audit-mission.txt
   ```

2. **Manual Review**:
   - Review each usage in context
   - Check if term used correctly per glossary
   - Flag inconsistencies

3. **Fix Verification**:
   ```bash
   # After updates, search for specific patterns that should be gone
   grep -r "create a new project" README.md src/  # Should NOT find in feature context
   grep -r "project workflow" .kittify/missions/  # Should be "mission workflow"
   ```

4. **User Testing**:
   - Read updated README as if new user
   - Try to find definitions of Project/Feature/Mission
   - Should find within 1 minute
   - Should be clear and unambiguous

**Documentation Review Checklist**:
- [ ] README.md - consistent terminology
- [ ] CLI help text - consistent terminology
- [ ] Error messages - consistent terminology
- [ ] Command prompts - consistent terminology
- [ ] Glossary clear and findable
- [ ] Examples use correct terms

---

## Risks & Mitigations

**Risk 1**: Breaking existing user mental models
- **Mitigation**: Definitions align with intuitive meanings, add glossary for clarity

**Risk 2**: Over-correcting, creating awkward phrasing
- **Mitigation**: Review in context, allow "project" where it's a filesystem term (project root, project directory)

**Risk 3**: Missing inconsistencies in less-visited docs
- **Mitigation**: Automated grep search finds all usages

**Risk 4**: Introducing new inconsistencies during updates
- **Mitigation**: Use glossary as reference, cross-check after each file update

---

## Definition of Done Checklist

- [ ] Glossary section added to README.md
- [ ] README.md reviewed for terminology consistency
- [ ] CLI help text reviewed and updated
- [ ] Error messages reviewed and updated
- [ ] Command prompts reviewed and updated
- [ ] Automated grep search shows no inconsistencies
- [ ] User testing: Can find definitions within 1 minute
- [ ] User testing: Definitions are clear and examples helpful
- [ ] All user-facing strings use standard terminology

**Automated Validation**:
```bash
# These searches should return zero problematic matches
grep -r "create a new project" README.md | grep -v "spec-kitty init"  # Should be empty
grep -r "project workflow" .kittify/missions/  # Should be "mission workflow"
grep -r "feature mission" src/  # Should be "active mission"
```

---

## Review Guidance

**Critical Checkpoints**:
1. Glossary must be clear, findable, and complete
2. Terminology must be consistent across all user-facing content
3. Definitions must align with actual system behavior
4. Examples must use terms correctly
5. No confusing or ambiguous usage

**What Reviewers Should Verify**:
- Open README.md → Find glossary → Can understand Project/Feature/Mission within 1 minute
- Read Quick Start → Terminology consistent
- Run `spec-kitty --help` → Help text uses correct terms
- Run commands from wrong location → Error messages clear and consistent
- Grep for "project" → All usages appropriate (filesystem terms or project initialization)

**Acceptance Criteria from Spec**:
- User Story 6, Scenarios 1-5 satisfied
- FR-024 through FR-026 implemented
- SC-014, SC-015 achieved (100% consistency, findable within 1 minute)

---

## Activity Log

- 2025-01-16T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-11-16T13:05:21Z – codex – shell_pid=63137 – lane=doing – Started implementation
- 2025-11-16T13:18:59Z – codex – shell_pid=63137 – lane=doing – Completed implementation
- 2025-11-16T13:19:22Z – codex – shell_pid=63137 – lane=for_review – Ready for review
- 2025-11-16T13:28:33Z – claude – shell_pid=5975 – lane=done – Code review complete: APPROVED. Comprehensive glossary added to README.md with clear Project/Feature/Mission definitions and examples. Terminology consistent across documentation. Quick Reference table helpful. FAQ answers common confusion points. Ready for users.
