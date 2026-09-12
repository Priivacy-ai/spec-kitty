---
work_package_id: WP04
title: Landing stale-stack + history-compression how-to
dependencies:
- WP03
requirement_refs:
- FR-005
- C-003
- NFR-001
- NFR-005
planning_base_branch: kitty/mission-workflow-self-doc
merge_target_branch: kitty/mission-workflow-self-doc
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-workflow-self-doc. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-workflow-self-doc unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
history: []
authoritative_surface: docs/development/how-to/
create_intent:
- docs/development/how-to/compress-mission-history.md
execution_mode: code_change
owned_files:
- docs/development/how-to/pr-landing.md
tags: []
tracker_refs: []
---

## Objective
`pr-landing.md §4` gains the multi-WP true-base/lane-tip note (moved here from WP03 per the post-plan squad) + a stale-stack diagnostic; a new `compress-mission-history.md` how-to carries the concrete recipe (governance stays cited in `pr-landing.md`).

## Subtasks
- **T008** `pr-landing.md §4`: the lane-tip nuance — a dep-merged lane tip already contains earlier WPs, so classify reds against `git merge-base <mission-branch> upstream/main`, not the lane tip; and a stale-stack two-dot/three-dot diff diagnostic ("charter files in a small-fix PR = smuggled governance / stale stack").
- **T009** New `docs/development/how-to/compress-mission-history.md`: the path-bucket `git commit-tree` snapshot-chain recipe + a tree-parity proof (`git diff <old> <new>` empty) + the "never `rebase -i`" reasoning. Frontmatter matches how-to pages. Content anchor `git commit-tree`.

## Rules
Do NOT regenerate rollups (WP06). Terminology green. `.venv/bin/python`, never bare `uv run`.

## Done
True-base note in §4; stale-stack diagnostic; compress how-to runnable-as-written; terminology green.
