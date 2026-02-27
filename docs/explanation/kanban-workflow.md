# Kanban Workflow Explained

Spec Kitty uses a kanban-style workflow to track work package progress. This document explains how lanes work, why we track status this way, and what happens when work moves between lanes.

## The Four Lanes

Work packages move through four lanes during their lifecycle:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   PLANNED   │ →  │    DOING    │ →  │  FOR_REVIEW │ →  │    DONE     │
├─────────────┤    ├─────────────┤    ├─────────────┤    ├─────────────┤
│ Ready to    │    │ Agent is    │    │ Waiting for │    │ Reviewed    │
│ start       │    │ implementing│    │ review      │    │ and merged  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### planned

**Meaning**: Work package is defined and ready to start.

**How it gets here**:
- `/spec-kitty.tasks` creates WPs in `planned` lane

**What happens**:
- WP waits for an agent to claim it
- Dependencies are satisfied (or WP is independent)

### doing

**Meaning**: An agent is actively implementing this work package.

**How it gets here**:
- Agent claims WP with `spec-kitty agent tasks move-task WP01 --to doing`
- Or automatically when running `spec-kitty implement WP01`

**What happens**:
- Agent works in the WP's worktree
- Makes commits to the WP branch
- Only ONE agent should have a WP in `doing` at a time

### for_review

**Meaning**: Implementation is complete, waiting for review.

**How it gets here**:
- Agent moves WP with `spec-kitty agent tasks move-task WP01 --to for_review`

**What happens**:
- Review agent examines the implementation
- Compares against spec and acceptance criteria
- Either approves (→ done) or requests changes (→ planned with feedback)

### done

**Meaning**: Work package has been reviewed and accepted.

**How it gets here**:
- Reviewer moves WP after approval: `spec-kitty agent tasks move-task WP01 --to done`

**What happens**:
- WP branch is ready for merging
- No further changes expected
- Once ALL WPs are in `done`, run `/spec-kitty.accept` to validate the entire feature

## How Work Moves Between Lanes

### Normal Flow: planned → doing → for_review → done

```
1. WP created by /spec-kitty.tasks
   └── lane: planned

2. Agent claims WP
   └── spec-kitty agent tasks move-task WP01 --to doing --assignee claude
   └── lane: doing

3. Agent completes implementation
   └── spec-kitty agent tasks move-task WP01 --to for_review --note "Ready"
   └── lane: for_review

4. Reviewer approves and moves WP
   └── spec-kitty agent tasks move-task WP01 --to done
   └── lane: done
   └── (Once ALL WPs are done: /spec-kitty.accept validates entire feature)
```

### Review Feedback: for_review → planned (with feedback)

When review finds issues:

```
1. WP in for_review, reviewer examines code

2. Reviewer finds problems
   └── /spec-kitty.review WP01
   └── Writes feedback file and runs move-task with --review-feedback-file
   └── Feedback persisted to git common-dir as feedback://<feature>/<wp>/<artifact>.md
   └── lane: planned (reset)
   └── review_status: has_feedback
   └── review_feedback: feedback://<feature>/<wp>/<artifact>.md

3. Agent re-claims WP
   └── Reads review_feedback pointer from frontmatter
   └── Addresses issues
   └── lane: doing → for_review

4. Reviewer re-reviews
   └── If good: lane: done
   └── If issues remain: repeat
```

## Lane Status in Frontmatter

Lane status is stored in each work package's YAML frontmatter:

```yaml
---
work_package_id: "WP01"
title: "Database Schema"
lane: "doing"
assignee: "claude"
agent: "claude"
shell_pid: "12345"
review_status: ""
review_feedback: ""
---
```

### Key Fields

| Field | Purpose |
|-------|---------|
| `lane` | Current status (planned/doing/for_review/done) |
| `assignee` | Who is working on this WP |
| `agent` | Which AI agent claimed this |
| `shell_pid` | Process ID of the agent (for tracking) |
| `review_status` | Empty or `has_feedback` if returned from review |
| `review_feedback` | Pointer to persisted feedback artifact (`feedback://...`) |

### Not Directories, Just a Field

In many kanban systems, you move cards between columns (directories). In Spec Kitty, the WP file stays in the same place—only the `lane:` field changes.

```
kitty-specs/012-feature/tasks/
├── WP01-database.md      # lane: done
├── WP02-api.md           # lane: for_review
├── WP03-frontend.md      # lane: doing
└── WP04-tests.md         # lane: planned
```

This design keeps all WP files in one location for easier discovery.

## Who Moves Work?

### Agents Move Work Forward

Agents are responsible for:
- `planned → doing` - Claiming a WP to work on
- `doing → for_review` - Signaling completion

Commands:
```bash
# Claim a WP
spec-kitty agent tasks move-task WP01 --to doing --assignee claude

# Mark complete
spec-kitty agent tasks move-task WP01 --to for_review --note "Implementation complete"
```

### Reviewers Make Accept/Reject Decisions

Reviewers are responsible for:
- `for_review → done` - Approving work
- `for_review → planned` - Requesting changes (adds feedback)

Commands:
```bash
# Review a WP (opens review workflow)
/spec-kitty.review WP01

# Move WP to done after review passes
spec-kitty agent tasks move-task WP01 --to done

# Request changes with feedback file
spec-kitty agent tasks move-task WP01 --to planned --review-feedback-file /tmp/spec-kitty-review-feedback-WP01.md

# Once ALL WPs are done, validate entire feature
/spec-kitty.accept
```

### Users and External Orchestrators Can Override

Users can override lane transitions when needed:
```bash
# Force move (e.g., to un-block stuck work)
spec-kitty agent tasks move-task WP01 --to planned
```

External orchestrators should request equivalent transitions through `spec-kitty orchestrator-api transition ...` so host validation and audit history stay consistent.

## Activity Log

Every lane transition is logged in the WP file's `history` field:

```yaml
history:
  - timestamp: "2026-01-15T10:00:00Z"
    lane: "planned"
    agent: "system"
    action: "Prompt generated via /spec-kitty.tasks"

  - timestamp: "2026-01-15T11:00:00Z"
    lane: "doing"
    agent: "claude"
    shell_pid: "12345"
    action: "Claimed for implementation"

  - timestamp: "2026-01-15T14:00:00Z"
    lane: "for_review"
    agent: "claude"
    shell_pid: "12345"
    action: "Implementation complete, ready for review"

  - timestamp: "2026-01-15T15:00:00Z"
    lane: "done"
    agent: "reviewer"
    action: "Approved and moved to done"
```

### Why Track Activity?

**Debugging**: If something goes wrong, you can trace what happened.

**Metrics**: Calculate time-in-lane, cycle time, throughput.

**Audit trail**: Know who did what and when.

**Coordination**: Multiple agents can see what others are doing.

## Kanban Board Visualization

Use `/spec-kitty.status` to see the current board state:

```
Feature: 012-user-authentication
═══════════════════════════════════════════════════════════════════════════════
 PLANNED         │ DOING           │ FOR_REVIEW      │ DONE
─────────────────┼─────────────────┼─────────────────┼─────────────────
 WP04-tests      │ WP03-frontend   │ WP02-api        │ WP01-database
                 │ (claude)        │                 │
─────────────────┴─────────────────┴─────────────────┴─────────────────
Progress: ████████░░░░░░░░ 25% (1/4 done)
```

## Rules and Constraints

### One Agent Per WP in Doing

When a WP is in `doing`:
- Only the assigned agent should work on it
- Other agents should work on different WPs
- This prevents conflicts and wasted work

### Dependencies Must Be Satisfied

Before moving a WP to `doing`:
- All dependencies must be in `done` lane (or at least `for_review`)
- If WP02 depends on WP01, WP01 should be complete first

The implement command enforces this:
```bash
spec-kitty implement WP02 --base WP01  # Ensures WP01 code is available
```

### Review Before Done

WPs cannot skip directly to `done`:
- Must pass through `for_review`
- Even self-review requires the transition
- This ensures all work is validated

### Subtask Validation

Before moving to `for_review`:
- All subtasks in the WP must be marked `[x]`
- The system blocks moves if subtasks are unchecked
- Ensures nothing is forgotten

## Common Patterns

### Linear Workflow

```
WP01 → WP02 → WP03 → WP04
```

Each WP moves through lanes sequentially. One agent handles everything.

### Parallel Workflow

```
        WP01 (done)
       /    \
WP02 (doing)  WP03 (doing)
```

Multiple WPs in `doing` simultaneously. Different agents work in parallel.

### Review Feedback Loop

```
planned → doing → for_review → planned → doing → for_review → done
                                   ↑                            ↑
                              (feedback)                   (approved)
```

Work returned from review goes back to `planned` with feedback.

## See Also

- [Spec-Driven Development](spec-driven-development.md) - The methodology that creates work packages
- [Workspace-per-WP](workspace-per-wp.md) - How parallel development works
- [AI Agent Architecture](ai-agent-architecture.md) - How agents claim and process work

---

*This document explains how lanes work. For practical steps on moving work, see the how-to guides.*

## Try It
- [Claude Code Integration](../tutorials/claude-code-integration.md)

## How-To Guides
- [Use the Dashboard](../how-to/use-dashboard.md)
- [Sync Workspaces](../how-to/sync-workspaces.md)
- [Non-Interactive Init](../how-to/non-interactive-init.md)

## Reference
- [CLI Commands](../reference/cli-commands.md)
- [Slash Commands](../reference/slash-commands.md)
