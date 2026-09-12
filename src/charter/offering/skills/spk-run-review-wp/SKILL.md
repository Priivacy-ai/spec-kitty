---
name: spk-run-review-wp
description: "Review a Spec Kitty work package through the runtime review surface and approve or reject with structured feedback."
---

# spk-run-review-wp

Use this skill when the user asks to review a WP, approve/reject work, or
operate the review workflow surface.

## Flow

1. Claim or select the WP from the runtime/review output.
2. Compare implementation against WP scope, spec, plan, and acceptance checks.
3. Approve only when behavior and verification satisfy the WP.
4. Reject with concrete, actionable feedback and affected files or commands.
5. Let `spk-run-implement-review` continue the loop.

## Recording the verdict

Capture the approve/reject decision through the deterministic event-log seam described in
`spk-run-verdict-capture` — the `review_result` event in `status.events.jsonl` is the sole
authority (the `review-cycle-N.md` render is non-authoritative). In practice:
`spec-kitty agent tasks move-task <WP> --to approved` to approve, or `--to planned
--review-feedback-file <f>` to reject. Never hand-edit the `.md` render to change a verdict.

## Legacy Alias

For detailed review command behavior, use `spec-kitty-runtime-review` when
available.
