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

## Sub-Agent Long-Gate Contract

`move-task --to for_review` runs the pre-review regression gate
synchronously as part of the transition (#2570/#2493/#2555): it derives the
affected test scope for the Mission's changed files and runs it at head
before the command returns. That scoped run is a real subprocess and can
take from seconds to a few minutes depending on scope size.

- A dispatched implement/review sub-agent MUST **poll the gate invocation to
  completion** — treat the `move-task --to for_review` command as still in
  flight until it exits, not as a fire-and-forget hand-back. Do not assume
  control returns immediately, and do not kill or retry the command while it
  is still running.
- To skip the gate for a single invocation, pass `--skip-pre-review-gate`.
  To disable it process-wide, set `SPEC_KITTY_SYNC_DISABLE` or
  `SPEC_KITTY_SYNC_MINIMAL_IMPORT` (the gate reuses the sync layer's
  existing disable toggles rather than adding a third env var). Either
  opt-out skips the gate before it resolves a workspace or spawns the
  subprocess.
- Absent an opt-out, the gate always enforces by default. An orchestrator
  observing a sub-agent that appears to hang on a `for_review` transition
  should first check whether the gate's scoped test subprocess is still
  running before treating the sub-agent as stuck.

## Legacy Alias

For detailed orchestration mechanics, use `spec-kitty-implement-review` when
available.
