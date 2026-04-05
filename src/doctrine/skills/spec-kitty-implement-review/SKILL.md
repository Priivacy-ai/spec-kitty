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

After ALL WPs are approved: `spec-kitty merge --feature <slug>` merges
everything and moves WPs to `done`.

**`approved` unblocks dependents immediately.** Do NOT wait for `done` before
starting dependent WPs. The `done` lane is only reached via feature merge.

To determine what to do next, always run:

```bash
spec-kitty next --agent <your-name> --feature <feature-slug>
```

This reads the dependency graph and current lane state and returns the exact
command. Do NOT reason about lane transitions yourself.

---

## Step 1: Dispatch Implementation

Implementation is a two-step process: claim the workspace, then dispatch an
agent to do the work.

### Step 1a: Claim the Workspace

```bash
OUTPUT=$(spec-kitty agent action implement WP## --agent <orchestrator-name> 2>&1)
```

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
   - Verify new code is called from live entry points
   - Verify old code paths are removed or redirected
   - Grep for old function/class names to confirm removal
7. Run tests: pytest tests/... -v
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
OUTPUT=$(spec-kitty agent action review WP## --agent <reviewer-name> 2>&1)
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

## Dependency-Aware Sequencing

### Linear Dependency Chain (Strict Sequence)

When each WP depends on the previous:

```
WP01 (approved) --> WP02 (approved) --> WP03 (approved) --> merge --> all done
```

1. Implement WP01, review, approve
2. THEN implement WP02, review, approve
3. THEN implement WP03, review, approve
4. `spec-kitty merge --feature <slug>`

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
spec-kitty next --agent <name> --feature <slug>

# 2. Dispatch implementation (two steps)
OUTPUT=$(spec-kitty agent action implement WP## --agent <name> 2>&1)
WORKSPACE=$(echo "$OUTPUT" | grep 'Workspace: cd ' | sed 's/.*Workspace: cd //')
PROMPT=$(echo "$OUTPUT" | grep 'cat ' | sed 's/.*cat //')
# Then dispatch agent (Task tool or CLI)

# 3. Monitor progress
spec-kitty agent tasks status

# 4. Dispatch review (two steps)
OUTPUT=$(spec-kitty agent action review WP## --agent <reviewer> 2>&1)
REVIEW_PROMPT=$(echo "$OUTPUT" | grep 'cat ' | sed 's/.*cat //')
WORKTREE=$(echo "$OUTPUT" | grep 'Workspace: cd ' | sed 's/.*Workspace: cd //')
# Then dispatch reviewer (Task tool or CLI)

# 5. After review: check outcome
spec-kitty agent tasks status
# If approved: next WP (repeat from step 1)
# If rejected: commit feedback, re-implement (cycle tracking)
# If 3 rejections: arbiter mode

# 6. After all WPs approved: merge
spec-kitty merge --feature <slug>
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
to the main repo where spec-kitty is on PATH. For codex, use `--add-dir "$(pwd)"`.
For others, verify the working directory.

**move-task fails with "Illegal transition"**: The reviewer may need `--force`.
Tier 1 agents typically retry with `--force` automatically. If not, the
orchestrator should run the force-move manually.

**Agent hangs (Tier 2 -- Cursor)**: Use timeout wrapper.
`timeout 600 cursor agent -p --force "prompt"`. If still hanging, kill and
re-dispatch to a different agent.

**Auto-commit warnings from sandboxed agents**: Some agents (codex) run in
sandboxes that cannot write to `.git/index.lock`. The lane change is written
to status files but needs manual commit from main:
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
