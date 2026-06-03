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

## Legacy Alias

For detailed review command behavior, use `spec-kitty-runtime-review` when
available.
