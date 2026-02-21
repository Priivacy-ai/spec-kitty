---
description: Generate grouped work packages with actionable subtasks and matching prompt files for the feature in one pass.
---

# /spec-kitty.tasks - Generate Work Packages

**Version**: 0.11.0+

## ⚠️ CRITICAL: THIS IS THE MOST IMPORTANT PLANNING WORK

**You are creating the blueprint for implementation**. The quality of work packages determines:
- How easily agents can implement the feature
- How parallelizable the work is
- How reviewable the code will be
- Whether the feature succeeds or fails

**QUALITY OVER SPEED**: This is NOT the time to save tokens or rush. Take your time to:
- Understand the full scope deeply
- Break work into clear, manageable pieces
- Write detailed, actionable guidance
- Think through risks and edge cases

**Token usage is EXPECTED and GOOD here**. A thorough task breakdown saves 10x the effort during implementation. Do not cut corners.

---

## 📍 WORKING DIRECTORY: Stay in planning repository

**IMPORTANT**: Tasks works in the planning repository. NO worktrees created.

```bash
# Run from project root (same directory as /spec-kitty.plan):
# You should already be here if you just ran /spec-kitty.plan

# Creates:
# - kitty-specs/###-feature/tasks/WP01-*.md → In planning repository
# - kitty-specs/###-feature/tasks/WP02-*.md → In planning repository
# - Commits ALL to target branch
# - NO worktrees created
```

**Do NOT cd anywhere**. Stay in the planning repository root.

**Worktrees created later**: After tasks are generated, use `spec-kitty implement WP##` to create workspace for each WP.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Location Check (0.11.0+)

Before proceeding, verify you are in the planning repository:

**Check your current branch:**
```bash
git branch --show-current
```

**Expected output:** the target branch (meta.json → target_branch), typically `main` or `2.x`
**If you see a feature branch:** You're in the wrong place. Return to the target branch:
```bash
cd $(git rev-parse --show-toplevel)
git checkout <target-branch>
```

Work packages are generated directly in `kitty-specs/###-feature/` and committed to the target branch. Worktrees are created later when implementing each work package.

## Outline

1. **Detect feature context** (mandatory in new sessions):
   - Resolve the feature slug from explicit user direction, current branch, or current directory path.
   - If context is ambiguous, run `check-prerequisites` once without `--feature`, parse the JSON candidate list, and pick one explicit feature slug before continuing.

2. **Setup**: Run `spec-kitty agent feature check-prerequisites --json --paths-only --include-tasks --feature <feature-slug>` from the repository root and capture `FEATURE_DIR` plus `AVAILABLE_DOCS`. All paths must be absolute.

   **CRITICAL**: The command returns JSON with `FEATURE_DIR` as an ABSOLUTE path (e.g., `/Users/robert/Code/new_specify/kitty-specs/001-feature-name`).

   **YOU MUST USE THIS PATH** for ALL subsequent file operations. Example:
   ```
   FEATURE_DIR = "/Users/robert/Code/new_specify/kitty-specs/001-a-simple-hello"
   tasks.md location: FEATURE_DIR + "/tasks.md"
   prompt location: FEATURE_DIR + "/tasks/WP01-slug.md"
   ```

   **DO NOT CREATE** paths like:
   - ❌ `tasks/WP01-slug.md` (missing FEATURE_DIR prefix)
   - ❌ `/tasks/WP01-slug.md` (wrong root)
   - ❌ `FEATURE_DIR/tasks/planned/WP01-slug.md` (WRONG - no subdirectories!)
   - ❌ `WP01-slug.md` (wrong directory)

3. **Load design documents** from `FEATURE_DIR` (only those present):
   - **Required**: plan.md (tech architecture, stack), spec.md (user stories & priorities)
   - **Optional**: data-model.md (entities), contracts/ (API schemas), research.md (decisions), quickstart.md (validation scenarios)
   - Scale your effort to the feature: simple UI tweaks deserve lighter coverage, multi-system releases require deeper decomposition.

4. **Derive fine-grained subtasks** (IDs `T001`, `T002`, ...):
   - Parse plan/spec to enumerate concrete implementation steps, tests (only if explicitly requested), migrations, and operational work.
   - Capture prerequisites, dependencies, and parallelizability markers (`[P]` means safe to parallelize per file/concern).
   - Maintain the subtask list internally; it feeds the work-package roll-up and the prompts.

5. **Roll subtasks into work packages** (IDs `WP01`, `WP02`, ...):

   **IDEAL WORK PACKAGE SIZE** (most important guideline):
   - **Target: 3-7 subtasks per WP** (results in 200-500 line prompts)
   - **Maximum: 10 subtasks per WP** (results in ~700 line prompts)
   - **If more than 10 subtasks needed**: Create additional WPs, don't pack them in

   **WHY SIZE MATTERS**:
   - **Too large** (>10 subtasks, >700 lines): Agents get overwhelmed, skip details, make mistakes
   - **Too small** (<3 subtasks, <150 lines): Overhead of worktree creation not worth it
   - **Just right** (3-7 subtasks, 200-500 lines): Agent can hold entire context, implements thoroughly

   **NUMBER OF WPs**: Let the work dictate the count
   - Simple feature (5-10 subtasks total): 2-3 WPs
   - Medium feature (20-40 subtasks): 5-8 WPs
   - Complex feature (50+ subtasks): 10-20 WPs ← **This is OK!**
   - **Better to have 20 focused WPs than 5 overwhelming WPs**

   **GROUPING PRINCIPLES**:
   - Each WP should be independently implementable
   - Root in a single user story or cohesive subsystem
   - Ensure every subtask appears in exactly one work package
   - Name with succinct goal (e.g., "User Story 1 – Real-time chat happy path")
   - Record metadata: priority, success criteria, risks, dependencies, included subtasks

6. **Write `tasks.md`** using the bundled tasks template (`.kittify/missions/software-dev/templates/tasks-template.md`):
   - **Location**: Write to `FEATURE_DIR/tasks.md` (use the absolute FEATURE_DIR path from step 1)
   - Populate the Work Package sections (setup, foundational, per-story, polish) with the `WPxx` entries
   - Under each work package include:
     - Summary (goal, priority, independent test)
     - Included subtasks (checkbox list referencing `Txxx`)
     - Implementation sketch (high-level sequence)
     - Parallel opportunities, dependencies, and risks
   - Preserve the checklist style so implementers can mark progress

7. **Generate prompt files (one per work package)**:
   - **CRITICAL PATH RULE**: All work package files MUST be created in a FLAT `FEATURE_DIR/tasks/` directory, NOT in subdirectories!
   - Correct structure: `FEATURE_DIR/tasks/WPxx-slug.md` (flat, no subdirectories)
   - WRONG (do not create): `FEATURE_DIR/tasks/planned/`, `FEATURE_DIR/tasks/doing/`, or ANY lane subdirectories
   - WRONG (do not create): `/tasks/`, `tasks/`, or any path not under FEATURE_DIR
   - Ensure `FEATURE_DIR/tasks/` exists (create as flat directory, NO subdirectories)
   - For each work package:
     - Derive a kebab-case slug from the title; filename: `WPxx-slug.md`
     - Full path example: `FEATURE_DIR/tasks/WP01-create-html-page.md` (use ABSOLUTE path from FEATURE_DIR variable)
     - Use the bundled task prompt template (`.kittify/missions/software-dev/templates/task-prompt-template.md`) to capture:
     - Frontmatter with `work_package_id`, `subtasks` array, `lane: "planned"`, `dependencies`, history entry
       - Objective, context, detailed guidance per subtask
       - Test strategy (only if requested)
       - Definition of Done, risks, reviewer guidance
     - Update `tasks.md` to reference the prompt filename
   - **TARGET PROMPT SIZE**: 200-500 lines per WP (results from 3-7 subtasks)
   - **MAXIMUM PROMPT SIZE**: 700 lines per WP (10 subtasks max)
   - **If prompts are >700 lines**: Split the WP - it's too large

   **IMPORTANT**: All WP files live in flat `tasks/` directory. Lane status is tracked ONLY in the `lane:` frontmatter field, NOT by directory location. Agents can change lanes by editing the `lane:` field directly or using `spec-kitty agent tasks move-task`.

8. **Finalize tasks with dependency parsing and commit**:
   After generating all WP prompt files, run the finalization command to:
   - Parse dependencies from tasks.md
   - Update WP frontmatter with dependencies field
   - Validate dependencies (check for cycles, invalid references)
   - Commit all tasks to target branch

   **CRITICAL**: Run this command from repo root:
   ```bash
   spec-kitty agent feature finalize-tasks --json --feature <feature-slug>
   ```

   This step is MANDATORY for workspace-per-WP features. Without it:
   - Dependencies won't be in frontmatter
   - Agents won't know which --base flag to use
   - Tasks won't be committed to target branch

   **IMPORTANT - DO NOT COMMIT AGAIN AFTER THIS COMMAND**:
   - finalize-tasks COMMITS the files automatically
   - JSON output includes "commit_created": true/false and "commit_hash"
   - If commit_created=true, files are ALREADY committed - do not run git commit again
   - Other dirty files shown by 'git status' (templates, config) are UNRELATED
   - Verify using the commit_hash from JSON output, not by running git add/commit again

9. **Report**: Provide a concise outcome summary:
   - Path to `tasks.md`
   - Work package count and per-package subtask tallies
   - **Average prompt size** (estimate lines per WP)
   - **Validation**: Flag if any WP has >10 subtasks or >700 estimated lines
   - Parallelization highlights
   - MVP scope recommendation (usually Work Package 1)
   - Prompt generation stats (files written, directory structure, any skipped items with rationale)
   - Finalization status (dependencies parsed, X WP files updated, committed to target branch)
   - Next suggested command (e.g., `/spec-kitty.analyze` or `/spec-kitty.implement`)

Context for work-package planning: {ARGS}

The combination of `tasks.md` and the bundled prompt files must enable a new engineer to pick up any work package and deliver it end-to-end without further specification spelunking.

## Dependency Detection (0.11.0+)

**Parse dependencies from tasks.md structure**:

The LLM should analyze tasks.md for dependency relationships:
- Explicit phrases: "Depends on WP##", "Dependencies: WP##"
- Phase grouping: Phase 2 WPs typically depend on Phase 1
- Default to empty if unclear

**Generate dependencies in WP frontmatter**:

Each WP prompt file MUST include a `dependencies` field:
```yaml
---
work_package_id: "WP02"
title: "Build API"
lane: "planned"
dependencies: ["WP01"]  # Generated from tasks.md
subtasks: ["T001", "T002"]
---
```

**Include the correct implementation command**:
- No dependencies: `spec-kitty implement WP01`
- With dependencies: `spec-kitty implement WP02 --base WP01`

The WP prompt must show the correct command so agents don't branch from the wrong base.

## Work Package Sizing Guidelines (CRITICAL)

### Ideal WP Size

**Target: 3-7 subtasks per WP**
- Results in 200-500 line prompt files
- Agent can hold entire context in working memory
- Clear scope - easy to review
- Parallelizable - multiple agents can work simultaneously

**Examples of well-sized WPs**:
- WP01: Foundation Setup (5 subtasks, ~300 lines)
  - T001: Create database schema
  - T002: Set up migration system
  - T003: Create base models
  - T004: Add validation layer
  - T005: Write foundation tests

- WP02: User Authentication (6 subtasks, ~400 lines)
  - T006: Implement login endpoint
  - T007: Implement logout endpoint
  - T008: Add session management
  - T009: Add password reset flow
  - T010: Write auth tests
  - T011: Add rate limiting

### Maximum WP Size

**Hard limit: 10 subtasks, ~700 lines**
- Beyond this, agents start making mistakes
- Prompts become overwhelming
- Reviews take too long
- Integration risk increases

**If you need more than 10 subtasks**: SPLIT into multiple WPs.

### Number of WPs: No Arbitrary Limit

**DO NOT limit based on WP count. Limit based on SIZE.**

- ✅ **20 WPs of 5 subtasks each** = 100 subtasks, manageable prompts
- ❌ **5 WPs of 20 subtasks each** = 100 subtasks, overwhelming 1400-line prompts

**Feature complexity scales with subtask count, not WP count**:
- Simple feature: 10-15 subtasks → 2-4 WPs
- Medium feature: 30-50 subtasks → 6-10 WPs
- Complex feature: 80-120 subtasks → 15-20 WPs ← **Totally fine!**
- Very complex: 150+ subtasks → 25-30 WPs ← **Also fine!**

**The goal is manageable WP size, not minimizing WP count.**

### When to Split a WP

**Split if ANY of these are true**:
- More than 10 subtasks
- Prompt would exceed 700 lines
- Multiple independent concerns mixed together
- Different phases or priorities mixed
- Agent would need to switch contexts multiple times

**How to split**:
- By phase: Foundation WP01, Implementation WP02, Testing WP03
- By component: Database WP01, API WP02, UI WP03
- By user story: Story 1 WP01, Story 2 WP02, Story 3 WP03
- By type of work: Code WP01, Tests WP02, Migration WP03, Docs WP04

### When to Merge WPs

**Merge if ALL of these are true**:
- Each WP has <3 subtasks
- Combined would be <7 subtasks
- Both address the same concern/component
- No natural parallelization opportunity
- Implementation is highly coupled

**Don't merge just to hit a WP count target!**

## Task Generation Rules

**Tests remain optional**. Only include testing tasks/steps if the feature spec or user explicitly demands them.

1. **Subtask derivation**:
   - Assign IDs `Txxx` sequentially in execution order.
   - Use `[P]` for parallel-safe items (different files/components).
   - Include migrations, data seeding, observability, and operational chores.
   - **Ideal subtask granularity**: One clear action (e.g., "Create user model", "Add login endpoint")
   - **Too granular**: "Add import statement", "Fix typo" (bundle these)
   - **Too coarse**: "Build entire API" (split into endpoints)

2. **Work package grouping**:
   - **Focus on SIZE first, count second**
   - Target 3-7 subtasks per WP (200-500 line prompts)
   - Maximum 10 subtasks per WP (700 line prompts)
   - Keep each work package laser-focused on a single goal
   - Avoid mixing unrelated concerns
   - **Let complexity dictate WP count**: 20+ WPs is fine for complex features

3. **Prioritisation & dependencies**:
   - Sequence work packages: setup → foundational → story phases (priority order) → polish.
   - Call out inter-package dependencies explicitly in both `tasks.md` and the prompts.
   - Front-load infrastructure/foundation WPs (enable parallelization)

4. **Prompt composition**:
   - Mirror subtask order inside the prompt.
   - Provide actionable implementation and test guidance per subtask—short for trivial work, exhaustive for complex flows.
   - **Aim for 30-70 lines per subtask** in the prompt (includes purpose, steps, files, validation)
   - Surface risks, integration points, and acceptance gates clearly so reviewers know what to verify.
   - Include examples where helpful (API request/response shapes, config file structures, test cases)

5. **Quality checkpoints**:
   - After drafting WPs, review each prompt size estimate
   - If any WP >700 lines: **STOP and split it**
   - If most WPs <200 lines: Consider merging related ones
   - Aim for consistency: Most WPs should be similar size (within 200-line range)
   - **Think like an implementer**: Can I complete this WP in one focused session? If not, it's too big.

6. **Think like a reviewer**: Any vague requirement should be tightened until a reviewer can objectively mark it done or not done.

## Step-by-Step Process

### Step 1: Detect Feature Context

Resolve the feature slug from explicit user direction, current branch, or current directory path.

If ambiguous, run `check-prerequisites` once without `--feature`, parse the JSON candidate list, and select one explicit feature slug.

### Step 2: Setup

Run `spec-kitty agent feature check-prerequisites --json --paths-only --include-tasks --feature <feature-slug>` and capture `FEATURE_DIR`.

### Step 3: Load Design Documents

Read from `FEATURE_DIR`:
- spec.md (required)
- plan.md (required)
- data-model.md (optional)
- research.md (optional)
- contracts/ (optional)

### Step 4: Derive ALL Subtasks

Create complete list of subtasks with IDs T001, T002, etc.

**Don't worry about count yet - capture EVERYTHING needed.**

### Step 5: Group into Work Packages

**SIZING ALGORITHM**:

```
For each cohesive unit of work:
  1. List related subtasks
  2. Count subtasks
  3. Estimate prompt lines (subtasks × 50 lines avg)

  If subtasks <= 7 AND estimated lines <= 500:
    ✓ Good WP size - create it

  Else if subtasks > 10 OR estimated lines > 700:
    ✗ Too large - split into 2+ WPs

  Else if subtasks < 3 AND can merge with related WP:
    → Consider merging (but don't force it)
```

**Examples**:

**Good sizing**:
- WP01: Database Foundation (5 subtasks, ~300 lines) ✓
- WP02: User Authentication (7 subtasks, ~450 lines) ✓
- WP03: Admin Dashboard (6 subtasks, ~400 lines) ✓

**Too large - MUST SPLIT**:
- ❌ WP01: Entire Backend (25 subtasks, ~1500 lines)
  - ✓ Split into: DB Layer (5), Business Logic (6), API Layer (7), Auth (7)

**Too small - CONSIDER MERGING**:
- WP01: Add config file (2 subtasks, ~100 lines)
- WP02: Add logging (2 subtasks, ~120 lines)
  - ✓ Merge into: WP01: Infrastructure Setup (4 subtasks, ~220 lines)

### Step 6: Write tasks.md

Create work package sections with:
- Summary (goal, priority, test criteria)
- Included subtasks (checkbox list)
- Implementation notes
- Parallel opportunities
- Dependencies
- **Estimated prompt size** (e.g., "~400 lines")

### Step 7: Generate WP Prompt Files

For each WP, generate `FEATURE_DIR/tasks/WPxx-slug.md` using the template.

**CRITICAL VALIDATION**: After generating each prompt:
1. Count lines in the prompt
2. If >700 lines: GO BACK and split the WP
3. If >1000 lines: **STOP - this will fail** - you MUST split it

**Self-check**:
- Subtask count: 3-7? ✓ | 8-10? ⚠️ | 11+? ❌ SPLIT
- Estimated lines: 200-500? ✓ | 500-700? ⚠️ | 700+? ❌ SPLIT
- Can implement in one session? ✓ | Multiple sessions needed? ❌ SPLIT

### Step 8: Finalize Tasks

Run `spec-kitty agent feature finalize-tasks --json --feature <feature-slug>` to:
- Parse dependencies
- Update frontmatter
- Validate (cycles, invalid refs)
- Commit to target branch

**DO NOT run git commit after this** - finalize-tasks commits automatically.
Check JSON output for "commit_created": true and "commit_hash" to verify.

### Step 9: Report

Provide summary with:
- WP count and subtask tallies
- **Size distribution** (e.g., "6 WPs ranging from 250-480 lines")
- **Size validation** (e.g., "✓ All WPs within ideal range" OR "⚠️ WP05 is 820 lines - consider splitting")
- Parallelization opportunities
- MVP scope
- Next command

## Dependency Detection (0.11.0+)

**Parse dependencies from tasks.md structure**:

The LLM should analyze tasks.md for dependency relationships:
- Explicit phrases: "Depends on WP##", "Dependencies: WP##"
- Phase grouping: Phase 2 WPs typically depend on Phase 1
- Default to empty if unclear

**Generate dependencies in WP frontmatter**:

Each WP prompt file MUST include a `dependencies` field:
```yaml
---
work_package_id: "WP02"
title: "Build API"
lane: "planned"
dependencies: ["WP01"]  # Generated from tasks.md
subtasks: ["T001", "T002"]
---
```

**Include the correct implementation command**:
- No dependencies: `spec-kitty implement WP01`
- With dependencies: `spec-kitty implement WP02 --base WP01`

The WP prompt must show the correct command so agents don't branch from the wrong base.

## ⚠️ Common Mistakes to Avoid

### ❌ MISTAKE 1: Optimizing for WP Count

**Bad thinking**: "I'll create exactly 5-7 WPs to keep it manageable"
→ Results in: 20 subtasks per WP, 1200-line prompts, overwhelmed agents

**Good thinking**: "Each WP should be 3-7 subtasks (200-500 lines). If that means 15 WPs, that's fine."
→ Results in: Focused WPs, successful implementation, happy agents

### ❌ MISTAKE 2: Token Conservation During Planning

**Bad thinking**: "I'll save tokens by writing brief prompts with minimal guidance"
→ Results in: Agents confused during implementation, asking clarifying questions, doing work wrong, requiring rework

**Good thinking**: "I'll invest tokens now to write thorough prompts with examples and edge cases"
→ Results in: Agents implement correctly the first time, no rework needed, net token savings

### ❌ MISTAKE 3: Mixing Unrelated Concerns

**Bad example**: WP03: Misc Backend Work (12 subtasks)
- T010: Add user model
- T011: Configure logging
- T012: Set up email service
- T013: Add admin dashboard
- ... (8 more unrelated tasks)

**Good approach**: Split by concern
- WP03: User Management (T010-T013, 4 subtasks)
- WP04: Infrastructure Services (T014-T017, 4 subtasks)
- WP05: Admin Dashboard (T018-T021, 4 subtasks)

### ❌ MISTAKE 4: Insufficient Prompt Detail

**Bad prompt** (~20 lines per subtask):
```markdown
### Subtask T001: Add user authentication

**Purpose**: Implement login

**Steps**:
1. Create endpoint
2. Add validation
3. Test it
```

**Good prompt** (~60 lines per subtask):
```markdown
### Subtask T001: Implement User Login Endpoint

**Purpose**: Create POST /api/auth/login endpoint that validates credentials and returns JWT token.

**Steps**:
1. Create endpoint handler in `src/api/auth.py`:
   - Route: POST /api/auth/login
   - Request body: `{email: string, password: string}`
   - Response: `{token: string, user: UserProfile}` on success
   - Error codes: 400 (invalid input), 401 (bad credentials), 429 (rate limited)

2. Implement credential validation:
   - Hash password with bcrypt (matches registration hash)
   - Compare against stored hash from database
   - Use constant-time comparison to prevent timing attacks

3. Generate JWT token on success:
   - Include: user_id, email, issued_at, expires_at (24 hours)
   - Sign with SECRET_KEY from environment
   - Algorithm: HS256

4. Add rate limiting:
   - Max 5 attempts per IP per 15 minutes
   - Return 429 with Retry-After header

**Files**:
- `src/api/auth.py` (new file, ~80 lines)
- `tests/api/test_auth.py` (new file, ~120 lines)

**Validation**:
- [ ] Valid credentials return 200 with token
- [ ] Invalid credentials return 401
- [ ] Missing fields return 400
- [ ] Rate limit enforced (test with 6 requests)
- [ ] JWT token is valid and contains correct claims
- [ ] Token expires after 24 hours

**Edge Cases**:
- Account doesn't exist: Return 401 (same as wrong password - don't leak info)
- Empty password: Return 400
- SQL injection in email field: Prevented by parameterized queries
- Concurrent login attempts: Handle with database locking
```

## Remember

**This is the most important planning work you'll do.**

A well-crafted set of work packages with detailed prompts makes implementation smooth and parallelizable.

A rushed job with vague, oversized WPs causes:
- Agents getting stuck
- Implementation taking 2-3x longer
- Rework and review cycles
- Feature failure

**Invest the tokens now. Be thorough. Future agents will thank you.**
