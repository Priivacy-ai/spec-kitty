---
name: spk-run-implement-review
description: "Orchestrate Spec Kitty work-package implementation and review loops until all packages are done, approved, or correctly rejected."
---

# spk-run-implement-review

Use this skill when a mission is in implementation/review lanes or the user
wants the agent to coordinate implementers and reviewers.

## Flow

1. Use `spk-run-next` to identify the active WP and lane.
2. Dispatch implementation only from runtime-provided prompt context.
3. Review each WP independently with `spk-run-review-wp`.
4. On rejection, feed structured reviewer feedback back into the next
   implementation attempt.
5. Continue until runtime returns terminal or a blocker.

## Legacy Alias

For detailed orchestration mechanics, use `spec-kitty-implement-review` when
available.
