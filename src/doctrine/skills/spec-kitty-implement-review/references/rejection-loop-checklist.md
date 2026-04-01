# Rejection Loop Checklist

Operational checklist for handling review rejections and re-implementation cycles.

## On Rejection (WP moved to planned with has_feedback)

- [ ] Confirmed WP lane is `planned` with `review_status: has_feedback`
- [ ] Committed status change from main: `git add kitty-specs/ && git commit -m "chore: Review feedback for WP## from <reviewer> (cycle X/3)"`
- [ ] Noted current cycle count (1, 2, or 3)

## Re-Implementation Dispatch

- [ ] Ran `spec-kitty agent workflow implement WP## --agent <name>`
- [ ] Captured workspace path and prompt file from output
- [ ] Dispatched implementing agent with cycle info in prompt
- [ ] Included note: "This is cycle X/3" so agent knows urgency

## Re-Implementation Agent Checklist

- [ ] Read review feedback section in WP file FIRST
- [ ] Updated `review_status: "acknowledged"` in frontmatter
- [ ] Addressed EVERY feedback item (treat as mandatory TODOs)
- [ ] Added regression tests for each issue
- [ ] Verified integration (new code wired into live entry points)
- [ ] Ran all tests
- [ ] Committed with descriptive message: `fix(WP##): <what was fixed>`
- [ ] Moved to for_review: `spec-kitty agent tasks move-task WP## --to for_review`

## Re-Review

- [ ] Dispatched review agent (same or different reviewer)
- [ ] Verified outcome: approved or planned

## Cycle Limits

| Cycle | Action |
|-------|--------|
| 1/3 | Normal re-implementation |
| 2/3 | Flag urgency in dispatch prompt |
| 3/3 | STOP. Enter arbiter mode (see SKILL.md Step 5) |

## Arbiter Mode (After Cycle 3)

- [ ] Read ALL 3 sets of review feedback
- [ ] Compared implementation attempts across cycles
- [ ] Identified root disagreement
- [ ] Made arbitration decision (approve / escalate / accept-and-move-on)
- [ ] Documented rationale in `--note`
