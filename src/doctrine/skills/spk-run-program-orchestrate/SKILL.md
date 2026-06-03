---
name: spk-run-program-orchestrate
description: "Orchestrate multi-repo, multi-mission Spec Kitty programs across dependencies, parallel agents, review gates, merge, and post-merge closeout."
---

# spk-run-program-orchestrate

Use this skill when a user wants to coordinate several related Spec Kitty
missions or repositories as one program.

## Flow

1. Build the mission dependency order before launching work.
2. Use `spk-run-next` for each mission's authoritative next action.
3. Coordinate parallel implementation only where dependencies allow.
4. Keep review, accept, merge, mission-review, and retrospective gates per
   mission.
5. Surface blockers as program risks without bypassing mission-level gates.

## Legacy Alias

For detailed program orchestration mechanics, use
`spec-kitty-program-orchestrate` when available.
