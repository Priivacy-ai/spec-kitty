---
name: spec-kitty-runtime-next
description: >-
  Drive the canonical spec-kitty next --agent <name> control loop for mission
  advancement.
  Triggers: "run the next step", "what should runtime do next", "advance the
  mission", "what is the next task", "continue the workflow", "what step comes
  next".
  Does NOT handle: setup or repair requests, purely editorial glossary or
  doctrine maintenance, or direct code review.
---

# spec-kitty-runtime-next

This skill teaches agents how to advance a Spec Kitty mission through the
canonical runtime control loop.

Terminology note:
- `Mission Type` = reusable blueprint
- `Mission` = concrete tracked item
- `Mission Run` = runtime/session instance
- Current `--feature` examples are legacy software-dev compatibility surfaces for the tracked mission

## When to Use This Skill

Use this skill when the user wants to:

- Advance a mission to its next step
- Understand what the runtime will do next
- Unblock a stalled mission
- Interpret runtime outcomes (step, blocked, decision_required, terminal)

---

## How the Runtime-Next System Works

The `spec-kitty next` command is the single entry point for agent-driven mission
execution. Each call returns a deterministic decision about what action the
agent should take next.

### Decision Algorithm

The runtime evaluates state in this order:

1. **Mission state machine** — Current phase and available transitions (from
   `mission-runtime.yaml` DAG)
2. **WP iteration check** — For `implement` and `review` steps, the CLI bridge
   manages WP-level iteration WITHOUT advancing the runtime. The runtime only
   advances when ALL WPs reach terminal/handoff lanes.
3. **Guard conditions** — Required artifacts, prerequisites, dependency graph
4. **Priority ordering** — Reviews before implementations, higher-priority WPs
   first, dependency-free WPs before dependent ones

### WP Iteration Logic (Critical)

The CLI bridge (not the runtime) manages WP-level iteration:

- If current step is `implement` or `review`
- AND there are WPs in `planned` or `in_progress` lanes
- THEN return a WP-level decision **without advancing the runtime step**
- The runtime step only advances when ALL WPs are in terminal/handoff lanes
  (`done`, `approved`, or `for_review`)

This means multiple calls to `spec-kitty next` during implementation will
return different WP IDs but the same `step_id` (e.g., "implement") until all
WPs are done.

### Mission Runtime YAML Schema

Missions define steps as a DAG (directed acyclic graph) with dependencies:

```yaml
mission:
  key: software-dev
  name: Software Dev Kitty
  version: "2.1.0"

steps:
  - id: discovery
    title: Discovery & Research
    depends_on: []
    prompt_template: research.md

  - id: specify
    depends_on: [discovery]
    prompt_template: specify.md

  - id: plan
    depends_on: [specify]
    prompt_template: plan.md

  - id: tasks_outline
    depends_on: [plan]
    prompt_template: tasks.md

  - id: tasks_packages
    depends_on: [tasks_outline]

  - id: tasks_finalize
    depends_on: [tasks_packages]

  - id: implement
    depends_on: [tasks_finalize]
    prompt_template: implement.md

  - id: review
    depends_on: [implement]
    prompt_template: review.md

  - id: accept
    depends_on: [review]
    prompt_template: accept.md
```

### The 4 Decision Kinds

Every call to `spec-kitty next` returns exactly one decision kind:

| Kind | Meaning | Agent Action |
|---|---|---|
| `step` | Normal action available | Read `prompt_file` and execute |
| `decision_required` | Runtime needs input | Answer with `--answer` and `--decision-id` |
| `blocked` | Guards failing, cannot proceed | Read `reason` + `guard_failures`, resolve blockers |
| `terminal` | Mission complete | Run `/spec-kitty.accept`, exit loop |

### Decision Output Fields

```json
{
  "kind": "step",
  "agent": "claude",
  "feature_slug": "042-test-feature",
  "mission": "software-dev",
  "mission_state": "implementing",
  "action": "implement",
  "wp_id": "WP02",
  "workspace_path": ".worktrees/042-test-feature-WP02",
  "prompt_file": "/tmp/spec-kitty-next-claude-042-test-feature-implement-WP02.md",
  "reason": null,
  "guard_failures": [],
  "progress": {
    "total_wps": 5,
    "done_wps": 1,
    "approved_wps": 0,
    "in_progress_wps": 1,
    "planned_wps": 3,
    "for_review_wps": 0
  },
  "run_id": "abc123",
  "step_id": "implement",
  "decision_id": null,
  "question": null,
  "options": null
}
```

### 6 Guard Primitives

Guards block step transitions by returning failure descriptions:

| Guard | Syntax | Checks |
|---|---|---|
| `artifact_exists` | `artifact_exists("spec.md")` | File exists relative to feature dir |
| `gate_passed` | `gate_passed("review_gate")` | Gate event in mission-events.jsonl |
| `all_wp_status` | `all_wp_status("done")` | All WPs in specific lane |
| `any_wp_status` | `any_wp_status("for_review")` | At least one WP in lane |
| `input_provided` | `input_provided("architecture")` | Input exists in runtime model |
| `event_count` | `event_count("review", 1)` | Minimum event count threshold |

Guards never raise exceptions — they return `false` on missing context.

### Prompt File Generation

The runtime generates a temp file at:
`/tmp/spec-kitty-next-{agent}-{feature_slug}-{action}[-{wp_id}].md`

**Template actions** (specify, plan, tasks): Feature context header + governance
context + action-specific template content.

**WP actions** (implement, review): Full isolation-aware prompt containing:
1. WP header with workspace path
2. Governance context (paradigms, directives, tools)
3. **WP Isolation Rules** — DO only modify this WP's status, DO NOT change
   other WPs or react to their status changes
4. Working directory and review commands
5. WP file content (from `tasks/WP##.md`)
6. Completion instructions

**Decision prompts**: Question text, options, and the `--answer` command to run.

### Run Persistence

Runtime state is persisted between calls:

```
.kittify/runtime/
├── feature-runs.json       # Index: {"feature-slug": {"run_id": "...", "run_dir": "..."}}
└── runs/
    └── <run_id>/
        └── state.json      # Runtime snapshot (current step, inputs, etc.)
```

### Feature Detection

When `--feature` is omitted, the runtime detects the feature via (in order):
1. `SPECIFY_FEATURE` environment variable
2. Git branch name (strips `-WP##` suffix for worktree branches)
3. Current directory path (walks up looking for `###-feature-name`)
4. Single feature auto-detect (only if exactly one feature exists)
5. Error with guidance if ambiguous

**NOTE:** Always use `--feature <slug>` in multi-feature repositories.

---

## Step 1: Load Runtime Context

Before invoking the runtime, gather the current state.

**Commands:**

```bash
# Check WP status for a feature
spec-kitty agent tasks status --feature <feature-slug>

# Check current context for an action
spec-kitty agent context resolve --action implement --feature <feature-slug> --json
```

**What to look for:**

- Active feature slug and mission type
- Current WP lane status (planned, claimed, in_progress, for_review, approved, done, blocked, canceled)
- Whether there are WPs ready for implementation or review
- Any blocked WPs that need attention first

---

## Step 2: Run the Next Command

```bash
# Run the next step
spec-kitty next --agent <agent> --feature <feature-slug> --json

# After completing a step successfully
spec-kitty next --agent <agent> --feature <feature-slug> --result success --json

# After a step failed
spec-kitty next --agent <agent> --feature <feature-slug> --result failed --json

# After a step was blocked
spec-kitty next --agent <agent> --feature <feature-slug> --result blocked --json
```

The `--result` flag tells the runtime the outcome of the previous step.
Defaults to `success` if omitted.

---

## Step 3: Interpret the Result

See `references/runtime-result-taxonomy.md` for the complete taxonomy.

| Kind | Next Action |
|------|-------------|
| `step` | Check `prompt_file` is not null, then read and execute |
| `decision_required` | Answer with `--answer` and `--decision-id` |
| `blocked` | Read `reason` + `guard_failures`, resolve blockers |
| `terminal` | Run `/spec-kitty.accept` for final validation |

**Always check `guard_failures`** — this field may appear on any decision kind,
not just `blocked`.

**Always check `prompt_file` before acting on a `step` decision.** If it is
`null`, the runtime could not generate a prompt for this step (known issue
#336). Treat a null `prompt_file` as a blocked state — do not attempt to
execute without a prompt.

**Always check `progress` for completion.** If `progress.done_wps` equals
`progress.total_wps` but `kind` is not `terminal`, the mission is actually
complete (known issue #335). The runtime may not detect completion when no
prior run state exists. Treat this as terminal and run `/spec-kitty.accept`.

---

## Step 4: Handle decision_required

When the runtime needs input:

```bash
# The decision includes question, options, and decision_id
# Answer using:
spec-kitty next --agent <agent> --feature <feature-slug> \
  --answer "<choice>" --decision-id "<decision_id>" --json
```

If the agent cannot determine the answer, escalate to the user with the
question and options.

---

## Step 5: Handle Blocked States

See `references/blocked-state-recovery.md` for detailed recovery patterns.

**Quick diagnostic:**

```bash
# Check WP status and dependency graph
spec-kitty agent tasks status --feature <feature-slug>

# Check specific WP dependencies
spec-kitty agent tasks list-dependents WP## --feature <feature-slug>
```

**Common blockers:**

| Blocker | Recovery |
|---|---|
| Missing artifacts (spec.md, plan.md) | Run the planning workflow first |
| Upstream WP not done | Implement or review the upstream WP |
| Review feedback not addressed | Re-implement, address feedback, move to for_review |
| Stale agent (WP in doing, no activity) | Move WP to planned with `--force` |
| Circular dependencies | Break cycle in WP frontmatter, re-run finalize-tasks |

---

## Step 6: The Agent Loop

The complete agent loop pattern:

```bash
# 1. Start the loop
DECISION=$(spec-kitty next --agent claude --feature 042-feature --json)
KIND=$(echo "$DECISION" | jq -r '.kind')

# 2. Loop until terminal or unresolvable block
while [ "$KIND" = "step" ] || [ "$KIND" = "decision_required" ]; do

  # Workaround #335: check progress for completion even if kind != terminal
  DONE=$(echo "$DECISION" | jq -r '.progress.done_wps // 0')
  TOTAL=$(echo "$DECISION" | jq -r '.progress.total_wps // 0')
  if [ "$TOTAL" -gt 0 ] && [ "$DONE" -eq "$TOTAL" ]; then
    break  # Mission is actually complete
  fi

  if [ "$KIND" = "step" ]; then
    PROMPT=$(echo "$DECISION" | jq -r '.prompt_file')

    # Workaround #336: treat null prompt as blocked
    if [ "$PROMPT" = "null" ] || [ -z "$PROMPT" ]; then
      break  # Cannot execute without a prompt
    fi

    # Read and execute the prompt...
    RESULT="success"  # or "failed" or "blocked"
  elif [ "$KIND" = "decision_required" ]; then
    # Answer the question...
    RESULT="success"
  fi

  DECISION=$(spec-kitty next --agent claude --feature 042-feature --result "$RESULT" --json)
  KIND=$(echo "$DECISION" | jq -r '.kind')
done

# 3. Handle terminal state
if [ "$KIND" = "terminal" ] || [ "$DONE" -eq "$TOTAL" ]; then
  # Run /spec-kitty.accept
fi
```

**The loop continues until:**

- `terminal` — mission complete, exit loop
- `blocked` — cannot proceed without external resolution
- `decision_required` — only if the agent cannot answer (escalate to user)

---

## Important: Runtime Precedence Rules

1. **Always use `spec-kitty next`** rather than manually sequencing phases
2. **Always pass `--feature`** in multi-feature repositories
3. **Respect mission state machine transitions** — do not skip steps
4. **Read the `prompt_file`** — it contains the full context the agent needs
5. **Check `guard_failures`** on every decision, not just blocked ones
6. **Reviews before implementations** — the runtime prioritizes unblocking
   downstream work
7. **WP isolation** — only modify the WP you were assigned, ignore other WPs

---

## Known Issues

**#335 — Completed features return `step` instead of `terminal`.** When
`spec-kitty next` is called on a feature with all WPs done but no prior
runtime run state, it creates a new run starting at `discovery` instead of
recognizing the mission is complete. **Workaround:** Check
`progress.done_wps == progress.total_wps` as a secondary completion signal.

**#336 — `prompt_file` can be `null` on `step` decisions.** Some steps
(e.g., `discovery`) lack command templates, so the runtime returns a step
decision with no prompt to execute. **Workaround:** Check `prompt_file`
for null before acting; treat null as blocked.

---

## References

- `references/runtime-result-taxonomy.md` -- Decision kinds, output fields, and precedence rules
- `references/blocked-state-recovery.md` -- 6 blocked state patterns with diagnosis and recovery
