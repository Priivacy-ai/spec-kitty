---
name: spec-kitty-implement-review
description: >-
  Orchestrate the implement-review loop for Spec Kitty work packages using any
  configured agent. Covers agent dispatch, state transitions, rejection cycles,
  arbiter escalation, and dependency-aware sequencing across all 13 supported
  coding agents.
  Triggers: "implement and review WPs", "run the implement-review loop",
  "orchestrate WP implementation", "dispatch agents for WPs",
  "coordinate implement and review", "sprint through WPs".
  Does NOT handle: specify/plan/tasks phases, setup or repair, glossary
  maintenance, or direct code editing by the orchestrator.
argument-hint: "[WP_ID or 'all' for full feature sprint]"
---

# spec-kitty-implement-review

Orchestrate the implement-review loop for Spec Kitty work packages. This skill
teaches any agent how to dispatch implementation and review to the configured
agents, handle rejection loops, enforce cycle limits, and sequence WPs by
dependency graph.

## When to Use This Skill

- Implement one or more WPs through the full implement-review cycle
- Coordinate cross-agent workflows (different agents for implement vs review)
- Handle rejection feedback loops with cycle tracking
- Run a full feature sprint (WP01 through WP_N)

## Core Concepts

### Agent Selection

Spec-kitty selects agents from `.kittify/config.yaml`:

```yaml
agents:
  available: [claude, codex, opencode]
  selection:
    preferred_implementer: claude
    preferred_reviewer: codex
  auto_commit: true
```

The orchestrator does NOT hardcode agent names. Instead:

```bash
# Check which agents are configured
spec-kitty agent config list

# The workflow commands handle agent selection internally
spec-kitty agent action implement WP01 --agent <your-name>
spec-kitty agent action review WP01 --agent <reviewer-name>
```

### Agent Capabilities

Not all agents can be dispatched the same way. The dispatch method depends on
the agent's CLI capabilities:

| Agent | Config Key | CLI Dispatch | Can Run move-task | Tier |
|-------|-----------|--------------|-------------------|------|
| Claude Code | `claude` | `claude -p "prompt" --output-format json` | Yes | 1 |
| GitHub Codex | `codex` | `codex exec --full-auto -C <dir> -` (stdin) | Yes | 1 |
| Google Gemini | `gemini` | `gemini -p "prompt" --yolo --output-format json` | Yes | 1 |
| GitHub Copilot | `copilot` | `copilot -p "prompt" --yolo --silent` | Yes | 1 |
| OpenCode | `opencode` | `opencode run "prompt" --format json` | Yes | 1 |
| Qwen Code | `qwen` | `qwen -p "prompt" --yolo --output-format json` | Yes | 1 |
| Kilocode | `kilocode` | `kilocode -a --yolo -j "prompt"` | Yes | 1 |
| Augment Code | `auggie` | `auggie --acp "prompt"` | Yes | 1 |
| Cursor | `cursor` | `timeout 300 cursor agent -p --force "prompt"` | Yes (may hang) | 2 |
| Windsurf | `windsurf` | GUI only | No (orchestrator must) | 3 |
| Roo Cline | `roo` | No official CLI | No (orchestrator must) | 3 |
| Amazon Q | `q` | Transitioning | No (orchestrator must) | 3 |
| Antigravity | `antigravity` | Google agent framework | Varies | 1 |

**Tier 1**: Full headless CLI. Orchestrator dispatches and agent runs autonomously.
**Tier 2**: CLI exists but needs workarounds (timeout wrappers, retry).
**Tier 3**: GUI-only or no stable CLI. Orchestrator must run `move-task` after
the agent completes, because the agent cannot run shell commands.

---

## The Mandatory Workflow Pattern

Every WP MUST follow this state flow:

```
planned --> [workflow implement] --> in_progress --> [agent works] --> for_review --> [review] --> approved or planned
```

After review rejection (WP moves back to `planned` with `review_status: has_feedback`):

```
planned --> [workflow implement] --> in_progress --> [agent fixes] --> for_review --> [review] --> approved or planned
```

After ALL WPs are approved: `spec-kitty merge --mission <slug>` merges
everything and moves WPs to `done`.

**`approved` unblocks dependents immediately.** Do NOT wait for `done` before
starting dependent WPs. The `done` lane is only reached via feature merge.

To determine what to do next, always run:

```bash
spec-kitty next --agent <your-name> --mission <mission-slug>
```

> **Note:** `--feature` is the hidden deprecated alias for `--mission`.
> Always use `--mission` in new scripts.

This reads the dependency graph and current lane state and returns the exact
command. Do NOT reason about lane transitions yourself.

---

## Step 1: Dispatch Implementation

Implementation is a two-step process: claim the workspace, then dispatch an
agent to do the work.

### Step 1a: Claim the Workspace

```bash
OUTPUT=$(spec-kitty agent action implement WP## --mission <slug> --agent <tool>:<model>:<profile>:<role> 2>&1)
```

**Agent identity** — always provide the full compact form so the WP records who is working:

```
--agent <tool>:<model>:<profile>:<role>
```

Examples:
- `--agent opencode:o3:python-pedro:implementer`
- `--agent claude:sonnet:implementer:implementer`
- `--agent codex:gpt-4o:python-pedro:implementer`

Partial compact strings are accepted (missing fields default to `unknown`).
You may also use explicit flags instead:
- `--tool <tool>` — agent key (e.g. `opencode`, `claude`)
- `--model <model>` — AI model identifier (e.g. `o3`, `gpt-4o`)
- `--profile <profile-id>` — doctrine profile (e.g. `python-pedro`)
- `--role <role>` — role label (e.g. `implementer`, `reviewer`)

This command:
- Moves WP from `planned` to `in_progress`
- Creates or re-enters the worktree workspace
- Generates the implementation prompt file

Capture from output:
- **Workspace path**: line containing `Workspace: cd <path>`
- **Prompt file**: line containing `cat <path>`

```bash
WORKSPACE=$(echo "$OUTPUT" | grep 'Workspace: cd ' | sed 's/.*Workspace: cd //')
PROMPT_FILE=$(echo "$OUTPUT" | grep 'cat ' | sed 's/.*cat //')
```

### Step 1b: Dispatch the Implementing Agent

How you dispatch depends on your execution context.

**If you are a Claude Code agent orchestrating via subagents (Task tool):**

```python
Task(
    subagent_type="general-purpose",
    description="Implement WP##",
    prompt=f"""You are implementing WP## for feature <slug>.

**CRITICAL: Work in the worktree directory:**
cd {WORKSPACE}

**Read the full implementation prompt:**
cat {PROMPT_FILE}

The prompt contains all context, acceptance criteria, and review feedback
(if re-implementing after rejection).

**Your task:**
1. Read the implementation prompt (contains all details)
2. If re-implementing: Read review feedback, update review_status: "acknowledged"
3. Read existing code paths BEFORE implementing
4. Implement all subtasks
5. Write tests that verify the contract (what the spec says)
6. Integration verification (MANDATORY before moving to for_review):
   - Verify new code is ACTUALLY CALLED from live entry points (not just defined)
   - Grep for imports of your new module in the files that should call it
   - If you created a new function/class, grep the codebase for callers — zero callers means the feature is dead code
   - Verify old code paths are removed or redirected
   - Grep for old function/class names to confirm removal
   CRITICAL: A module with passing tests but no callers is NOT implemented.
   The most common review failure is dead code — tests pass but the feature
   is never invoked from the live command path.
7. Run the project's declared validation command before handoff
8. Commit: git add -A && git commit -m "feat(WP##): <description>"
9. Mark subtasks done: spec-kitty agent tasks mark-status T001 T002 ... --status done
10. Move to for_review: spec-kitty agent tasks move-task WP## --to for_review --note "Ready for review"
""",
    run_in_background=True
)
```

**If you are dispatching to an external CLI agent (Tier 1):**

Build a prompt file and pipe to the agent CLI:

```bash
# Read the generated prompt
PROMPT_CONTENT=$(cat "$PROMPT_FILE")

# Dispatch to configured agent (examples for each CLI)

# Claude Code:
claude -p "$PROMPT_CONTENT" --output-format json -C "$WORKSPACE"

# GitHub Codex:
printf '%s' "$PROMPT_CONTENT" | codex exec --full-auto -C "$WORKSPACE" -

# Google Gemini:
gemini -p "$PROMPT_CONTENT" --yolo --output-format json -C "$WORKSPACE"

# OpenCode:
opencode run "$PROMPT_CONTENT" --format json -C "$WORKSPACE"

# Qwen Code:
qwen -p "$PROMPT_CONTENT" --yolo --output-format json -C "$WORKSPACE"

# Kilocode:
kilocode -a --yolo -j "$PROMPT_CONTENT" -C "$WORKSPACE"

# Augment Code:
auggie --acp "$PROMPT_CONTENT" -C "$WORKSPACE"

# Cursor (Tier 2 -- needs timeout wrapper):
timeout 600 cursor agent -p --force --output-format json "$PROMPT_CONTENT" -C "$WORKSPACE"
```

**If the agent is Tier 3 (GUI-only):**

The orchestrator cannot dispatch automatically. Instead:
1. Print the workspace path and prompt file for the human operator
2. Wait for the human to run the agent manually in the workspace
3. After the agent finishes, the orchestrator runs `move-task` on behalf of
   the agent (since GUI agents cannot execute CLI commands)

```bash
echo "Manual dispatch required for agent: <agent-name>"
echo "Workspace: cd $WORKSPACE"
echo "Prompt: cat $PROMPT_FILE"
echo "After agent completes, run:"
echo "  spec-kitty agent tasks move-task WP## --to for_review --note 'Ready'"
```

---

## Step 2: Monitor Progress

Check WP status at any time:

```bash
spec-kitty agent tasks status
```

This shows:
- Kanban board with WPs in lanes: planned, in_progress, for_review, approved, done
- Progress bar showing completion percentage
- Which WPs are ready for review, in progress, and planned

Use this frequently between dispatch and review steps.

---

## Step 3: Dispatch Review

When a WP reaches `for_review`, dispatch a review agent.

### Step 3a: Claim the Review

```bash
OUTPUT=$(spec-kitty agent action review WP## --mission <slug> --agent <tool>:<model>:<profile>:<role> 2>&1)
REVIEW_PROMPT=$(echo "$OUTPUT" | grep -o '/var/folders[^ ]*/spec-kitty-review-WP[0-9]*.md' || echo "$OUTPUT" | grep 'cat ' | sed 's/.*cat //')
WORKTREE=$(echo "$OUTPUT" | grep 'Workspace: cd ' | sed 's/.*Workspace: cd //')
```

### Step 3b: Dispatch the Review Agent

**If you are a Claude Code agent (Task tool):**

```python
Task(
    subagent_type="general-purpose",
    description="Review WP##",
    prompt=f"""You are reviewing WP## for feature <slug>.

**CRITICAL: Work in the worktree directory:**
cd {WORKTREE}

**Read the full review prompt:**
cat {REVIEW_PROMPT}

The review prompt contains:
- Acceptance criteria for this WP
- Git diff commands with the correct base branch
- Dependency warnings for downstream WPs
- Completion instructions (approve/reject commands)

**Your task:**
1. Read the review prompt (it is the source of truth)
2. Run the git diff commands listed in the prompt
3. Check each acceptance criterion against the diff
4. Check for unrelated changes outside WP scope
5. Issue exactly one verdict:

**If ALL acceptance criteria met:**
spec-kitty agent tasks move-task WP## --to approved --note "Review passed: <summary>"

**If criteria NOT met:**
Write structured feedback to a temp file, then:
spec-kitty agent tasks move-task WP## --to planned --force --review-feedback-file <feedback-path>
""",
    run_in_background=True
)
```

**If dispatching to an external CLI agent:**

Build a combined prompt and pipe to the agent. The mandatory instruction
ensures the agent runs the `move-task` command after reviewing.

```bash
# Build combined prompt with mandatory instruction
printf 'IMPORTANT: After reviewing, you MUST execute the appropriate spec-kitty agent tasks move-task command shown at the bottom of this prompt.\n---\n' > /tmp/review-prompt-WP##.md
cat "$REVIEW_PROMPT" >> /tmp/review-prompt-WP##.md

# Dispatch to configured reviewer (same CLI patterns as Step 1b)
# Example for codex:
cat /tmp/review-prompt-WP##.md | codex exec --full-auto \
  -C "$WORKTREE" --add-dir "$(pwd)" \
  -o "/tmp/review-result-WP##.md" -

# Example for claude:
claude -p "$(cat /tmp/review-prompt-WP##.md)" --output-format json -C "$WORKTREE"

# Example for gemini:
gemini -p "$(cat /tmp/review-prompt-WP##.md)" --yolo --output-format json -C "$WORKTREE"
```

**If the reviewer is Tier 3 (GUI-only) or cannot run move-task:**

After the reviewer completes, the orchestrator must:
1. Read the reviewer's output to determine pass/fail
2. Run `move-task` on behalf of the reviewer

```bash
# Read reviewer output, then:
# If approved:
spec-kitty agent tasks move-task WP## --to approved --note "Review passed (by <agent>): <summary>"

# If rejected:
spec-kitty agent tasks move-task WP## --to planned --force \
  --review-feedback-file /tmp/feedback-WP##.md
```

### Step 3c: Verify the Outcome

After review completes:

```bash
# Check the WP lane
spec-kitty agent tasks status

# If reviewer output was captured to a file:
cat /tmp/review-result-WP##.md
```

---

## Step 4: Handle Review Rejection

When a reviewer moves a WP back to `planned` with feedback, the orchestrator
must re-dispatch implementation.

### What Happens on Rejection

1. The reviewer runs `move-task WP## --to planned --force --review-feedback-file <path>`
2. The WP prompt file is updated:
   - `lane: "planned"` in frontmatter
   - `review_status: "has_feedback"` in frontmatter
   - The **Review Feedback** section is populated with change requests
   - An activity log entry records the rejection

### Re-Implementation Steps

1. **Commit the status change** from main:
   ```bash
   git add kitty-specs/ && git commit -m "chore: Review feedback for WP## from <reviewer> (cycle X/3)"
   ```

2. **Re-dispatch implementation** using the same two-step pattern from Step 1:
   ```bash
   OUTPUT=$(spec-kitty agent action implement WP## --agent <orchestrator-name> 2>&1)
   WORKSPACE=$(echo "$OUTPUT" | grep 'Workspace: cd ' | sed 's/.*Workspace: cd //')
   PROMPT_FILE=$(echo "$OUTPUT" | grep 'cat ' | sed 's/.*cat //')
   ```
   Then dispatch the implementing agent (Step 1b). The prompt file now
   includes the review feedback.

3. **Wait for re-implementation to complete** (WP reaches `for_review`)

4. **Re-dispatch review** (Step 3)

5. **Track the cycle count** (max 3):
   - Cycle 1: First rejection
   - Cycle 2: Second rejection
   - Cycle 3: Third rejection triggers **ARBITER MODE**

### Example Rejection Loop

```bash
# 1. Reviewer rejected WP03 -- verify status
spec-kitty agent tasks status
# Shows: WP03 in planned (review_status: has_feedback)

# 2. Commit status change
git add kitty-specs/ && git commit -m "chore: Review feedback for WP03 from <reviewer> (cycle 1/3)"

# 3. Re-dispatch implementation (two-step pattern)
OUTPUT=$(spec-kitty agent action implement WP03 --agent coordinator 2>&1)
WORKSPACE=$(echo "$OUTPUT" | grep 'Workspace: cd ' | sed 's/.*Workspace: cd //')
PROMPT_FILE=$(echo "$OUTPUT" | grep 'cat ' | sed 's/.*cat //')

# 4. Dispatch fixing agent (Task tool or CLI -- see Step 1b)
# Include cycle info: "This is cycle 2/3"

# 5. Wait for WP to reach for_review, then re-dispatch review (Step 3)
```

---

## Step 5: Arbiter Mode (After 3 Rejections)

If a WP is rejected 3 times, the orchestrator steps in as arbiter.

### Arbiter Decision Options

**Option A -- Approve with notes** (implementation is correct, reviewer is too strict):
```bash
spec-kitty agent tasks move-task WP## --to approved --force \
  --note "Arbiter decision: Approved after 3 cycles. Meets acceptance criteria. Rationale: <explain>"
```

**Option B -- Escalate to human** (disagreement is substantial):
```bash
spec-kitty agent tasks move-task WP## --to blocked --force \
  --note "Escalated to human after 3 cycles. Conflict: <summarize>"
```

**Option C -- Accept and move on** (feedback is contradictory):
```bash
spec-kitty agent tasks move-task WP## --to approved --force \
  --note "Arbiter decision: Proceeding after 3 cycles with inconsistent feedback. <explain>"
```

### Arbiter Guidelines

- Favor functional correctness over style preferences
- If all acceptance criteria are met, lean toward approval
- Look for genuine blocker bugs vs cosmetic complaints
- Consider diminishing returns of another full cycle
- Document your decision clearly in the `--note`

---

## Parallel Sprint Pattern

When multiple independent WPs can execute simultaneously, dispatch them all at
once instead of processing sequentially. This is the fastest path for features
with mixed dependency graphs.

### Identifying Parallel Opportunities

```bash
# lanes.json shows which WPs are independent (different lanes)
cat kitty-specs/<mission>/lanes.json
```

Independent WPs are in separate lanes. WPs in the same lane have a dependency
chain and must execute sequentially within that lane.

### Parallel Dispatch

Claim all workspaces first (sequential — each modifies git state), then
dispatch all agents in parallel:

```bash
# 1. Claim workspaces (must be sequential — git state mutations)
for wp in WP01 WP03 WP04 WP05 WP06; do
  spec-kitty agent action implement $wp --mission <slug> --agent <tool>:<model>
done

# 2. Dispatch agents in parallel (method depends on orchestrator)
#    - CLI orchestrator: launch background processes
#    - Claude Code: use Agent tool with run_in_background=True
#    - CI/CD: parallel matrix jobs
#    - Human operator: open multiple terminals
```

The dispatch mechanism is orchestrator-dependent. The key constraint is that
workspace claiming must be sequential, but agent execution can be fully parallel.

### Completion-Driven Review Scheduling

As each implementation agent completes (notified asynchronously):
1. Check which WP reached `for_review`
2. Dispatch a review agent for that WP immediately
3. If the reviewed WP unblocks a dependent (e.g., WP01 approval unblocks WP02),
   dispatch the dependent's implementation immediately
4. Continue until all WPs are approved

This pattern sustains maximum parallelism throughout the sprint. Do NOT wait for
all implementations to complete before starting reviews.

### Tracking Parallel State

Maintain a status table of the current state. Update after each agent
completion:

```
| WP   | Stage                | Agent         |
|------|----------------------|---------------|
| WP01 | Review in progress   | <reviewer>    |
| WP03 | Approved             | --            |
| WP04 | Implementation       | <implementer> |
| WP05 | Review in progress   | <reviewer>    |
| WP06 | Fix cycle 1/3        | <implementer> |
| WP02 | Blocked on WP01      | --            |
```

Use `spec-kitty agent tasks status --mission <slug>` as the authoritative
source. The table above is the orchestrator's working copy for scheduling
decisions between status checks.

---

## Dependency-Aware Sequencing

### Linear Dependency Chain (Strict Sequence)

When each WP depends on the previous:

```
WP01 (approved) --> WP02 (approved) --> WP03 (approved) --> merge --> all done
```

1. Implement WP01, review, approve
2. THEN implement WP02, review, approve. The implementation workspace base is inferred automatically from the approved dependency graph.
3. THEN implement WP03, review, approve. The implementation workspace base is inferred automatically from the approved dependency graph.
4. `spec-kitty merge --mission <slug>`

### Parallel Opportunities (Independent WPs)

For WPs with no cross-dependencies:

```
WP01 --> Review WP01       WP02 --> Review WP02       WP03 --> Review WP03
```

Dispatch in parallel. Each must complete its review cycle before feature merge.

### Mixed Dependencies

```
        WP01
       /    \
    WP02    WP03
       \    /
        WP04
```

1. Implement and approve WP01
2. Implement WP02 and WP03 in parallel only if task finalization assigned them to separate lanes
3. After both approved, implement WP04 in its computed lane

### Decision Tree

- **Always use `spec-kitty next`** to determine sequencing
- Linear dependencies: process sequentially
- Independent WPs: dispatch in parallel
- Mixed: coordinate using dependency graph

---

## Orchestrator Cheat Sheet

```bash
# 1. Determine what to do next
spec-kitty next --agent <name> --mission <slug>

# 2. Dispatch implementation (two steps)
#    --agent compact form: <tool>:<model>:<profile>:<role>
OUTPUT=$(spec-kitty agent action implement WP## --mission <slug> --agent <tool>:<model>:<profile>:<role> 2>&1)
WORKSPACE=$(echo "$OUTPUT" | grep 'Workspace: cd ' | sed 's/.*Workspace: cd //')
PROMPT=$(echo "$OUTPUT" | grep 'cat ' | sed 's/.*cat //')
# Then dispatch agent (Task tool or CLI)

# 3. Monitor progress
spec-kitty agent tasks status --mission <slug>

# 4. Dispatch review (two steps)
OUTPUT=$(spec-kitty agent action review WP## --mission <slug> --agent <tool>:<model>:<profile>:<role> 2>&1)
REVIEW_PROMPT=$(echo "$OUTPUT" | grep 'cat ' | sed 's/.*cat //')
WORKTREE=$(echo "$OUTPUT" | grep 'Workspace: cd ' | sed 's/.*Workspace: cd //')
# Then dispatch reviewer (Task tool or CLI)

# 5. After review: check outcome
spec-kitty agent tasks status --mission <slug>
# If approved: next WP (repeat from step 1)
# If rejected: commit feedback, re-implement (cycle tracking)
# If 3 rejections: arbiter mode

# 6. After all WPs approved: merge
spec-kitty merge --mission <slug>
```

---

## Step 6: Merge All Lanes

After all WPs are approved, merge the lanes into the mission branch, then
merge the mission branch into the mission's target branch.

### Run the Merge Command

```bash
# From the repository root checkout (NOT from a worktree)
spec-kitty merge --mission <mission-slug>
```

This command:
1. Validates all WPs have review approval (gate check)
2. Merges each lane branch into the mission branch sequentially
3. Merges the mission branch into the target branch
4. Cleans up worktrees and lane branches

### Handling Stale Lane Conflicts

When lanes modify overlapping files (e.g., `__init__.py`, shared modules),
the merge command will fail with a "stale lane" error:

```
✗ lane-c: Lane lane-c is stale: overlapping files ['src/review/__init__.py'].
  Run: cd .worktrees/*-lane-c && git merge kitty/mission-<slug>
```

**Resolution pattern** (repeat for each stale lane):

```bash
# 1. Enter the stale lane worktree
cd .worktrees/<mission>-lane-<X>

# 2. Merge the mission branch (which has earlier lanes merged)
git merge kitty/mission-<mission-slug> --no-edit

# 3. If conflicts occur, resolve them:
#    - __init__.py conflicts: combine all imports from both sides
#    - Shared module conflicts: keep both changes (they modify different sections)
#    - Test __init__.py: usually take the incoming version

# 4. Commit the resolution
git add -A && git commit -m "merge: resolve lane-<X> conflicts"

# 5. Return to the repository root checkout and retry
cd /path/to/repository-root
spec-kitty merge --mission <mission-slug>
```

**Common conflict patterns:**
- `__init__.py` in new modules: Each lane creates its own version with different
  exports. Combine all exports into one file.
- Shared files (`tasks.py`, `workflow.py`): Multiple lanes modify different
  sections. Git usually auto-merges; manual resolution needed only for
  overlapping edits.
- Test `__init__.py`: Empty files — take either version.

### Post-Merge Validation

After merge completes, the git index may show stale state from worktree
operations. If `git status` shows unexpected deletions:

```bash
# Restore working tree to match HEAD
git checkout HEAD -- src/ tests/

# Verify merge landed correctly
git log --oneline -3
git show --stat HEAD
```

Run the full test suite on the mission's target branch after merge to catch cross-lane integration issues:

```bash
# Run the validation command declared by this project or mission.
```

This is the only point where all WP code from all lanes coexists — earlier
lane-specific test runs only verify each WP in isolation.

### Post-Merge Done Transition

After merge completes, WPs move to `done` automatically. If they remain in
`approved`, move them manually:

```bash
for wp in WP01 WP02 WP03 WP04 WP05 WP06; do
  spec-kitty agent tasks move-task $wp --to done --force \
    --done-override-reason "Feature merged to target branch" \
    --mission <mission-slug>
done
```

---

## Key Rules

1. **Always use `spec-kitty agent action implement WP##`** before dispatching
2. **Always use `spec-kitty agent action review WP##`** before dispatching review
3. **Use `spec-kitty next`** to determine sequencing -- do not guess
4. **Commit after every review**: `git add kitty-specs/ && git commit`
5. **Track rejection cycles** (max 3) in commit messages
6. **The orchestrator does not implement** -- it dispatches and monitors
7. **`approved` unblocks dependents** -- do not wait for `done`
8. **Never manually move WPs to `done`** -- that happens during feature merge
9. **For Tier 3 agents**: orchestrator runs `move-task` on the agent's behalf
10. **Parallel reviews are safe** -- each WP operates in its own worktree

---

## Troubleshooting

**Agent cannot find spec-kitty CLI**: Ensure the dispatched agent has access
to the repository root checkout where spec-kitty is on PATH. For codex, use `--add-dir "$(pwd)"`.
For others, verify the working directory.

**move-task fails with "Illegal transition"**: The reviewer may need `--force`.
Tier 1 agents typically retry with `--force` automatically. If not, the
orchestrator should run the force-move manually.

**Agent hangs (Tier 2 -- Cursor)**: Use timeout wrapper.
`timeout 600 cursor agent -p --force "prompt"`. If still hanging, kill and
re-dispatch to a different agent.

**Auto-commit warnings from sandboxed agents**: Some agents (codex) run in
sandboxes that cannot write to `.git/index.lock`. The lane change is written
to status files but needs manual commit from the repository root checkout:
`git add kitty-specs/ && git commit -m "chore: status update"`

**Stale WP (in_progress but no agent activity)**: Force back to planned and
re-dispatch:
```bash
spec-kitty agent tasks move-task WP## --to planned --force --note "Stale agent recovery"
```

**Cross-worktree visibility**: Each agent only sees its own WP worktree.
Cross-WP verification must be documented in deliverables so reviewers
understand the verification method.

**Parallel review commit batching**: When running multiple reviews in parallel,
commit all status changes from main in one batch after all reviews complete.

**Stale git index after merge**: After `spec-kitty merge` completes and cleans
up worktrees, `git status` may show files from the merged lanes as "deleted"
in the staging area. This is a git worktree cleanup artifact, not real data loss.
Fix with `git checkout HEAD -- src/ tests/` to restore the working tree to match
HEAD.

**Dead code after implementation**: If a WP creates a new module with tests that
pass but the module is never imported from the live command path, the feature
does not work. This is the most common post-merge defect. Run
`grep -r "from.*<new_module>" src/` to verify at least one live caller exists
for every new module.

**Test-DB collisions across parallel lane worktrees (Django-backed
projects)**: When multiple implementer agents run tests concurrently in
separate lane worktrees of the same project, they collide on the shared
default test database, producing errors like `psycopg2.errors.DuplicateColumn`
or `must be owner of table <name>`. Workaround that sub-agents commonly
rediscover:
```bash
DJANGO_TEST_DATABASE_NAME=test_<project>_lane_<letter> <project-test-command> --create-db
```
Include this pattern in your dispatch prompts for Django-backed WPs so each
implementer knows to use a lane-scoped DB up front. Tracked upstream as
https://github.com/Priivacy-ai/spec-kitty/issues/770 for built-in support.

**Lane staleness on merge**: After `spec-kitty merge` completes lane A, lane B
can become stale against the updated mission branch on shared files
(`pyproject.toml`, `uv.lock`, module `__init__.py`, `urls.py`). The merge
halts on the stale lane with a manual-merge prompt. For multi-lane missions
the rote work can be significant (~30 min for 8+ lanes). The pattern is:
`cd .worktrees/<slug>-lane-X && git merge kitty/mission-<slug> --no-edit`,
resolve any conflicts (usually union-merge on TOML / import-line / comment
additions), commit, then retry the outer merge. Tracked upstream as
https://github.com/Priivacy-ai/spec-kitty/issues/771 for auto-rebase support.

**Running multi-repo or multi-mission programs**: The implement-review loop
in this skill is scoped to a single mission. When orchestrating across
multiple missions and repos (e.g., a cross-repo feature release), you will
need a layer above this one that handles: inter-repo dependency sequencing,
pulse-heartbeat safety nets when running many agents for long stretches,
and post-merge mission-review + remediation chaining. See the companion
skill `spec-kitty-program-orchestrate` for that pattern.
