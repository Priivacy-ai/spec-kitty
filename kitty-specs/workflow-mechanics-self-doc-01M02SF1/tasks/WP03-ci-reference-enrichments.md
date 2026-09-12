---
work_package_id: WP03
title: CI reference enrichments
dependencies:
- WP02
requirement_refs:
- FR-004
- C-003
- NFR-001
- NFR-005
planning_base_branch: kitty/mission-workflow-self-doc
merge_target_branch: kitty/mission-workflow-self-doc
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-workflow-self-doc. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-workflow-self-doc unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
history: []
authoritative_surface: docs/development/reference/
create_intent: []
execution_mode: code_change
owned_files:
- docs/development/reference/coverage-signals.md
- docs/development/reference/known-friction-points.md
tags: []
tracker_refs: []
---

## Objective
Enrich the CI reference docs with the two genuinely-absent traps. The multi-WP true-base note lives in WP04's `pr-landing.md §4` — CITE it, do NOT restate here.

## Subtasks
- **T006** `coverage-signals.md`: the "git mv into a critical-path dir + non-`fast` tests → the FAST-only diff-coverage job needs a `fast` mocked test module" remedy (fresh, PR #3437). The allowlist + 90% gate are already there — add only the move remedy.
- **T007** `known-friction-points.md`: the `pr:deferred`/`pr:skip-ci` CI job-skip guard; the `charter lint` gitignored-`graph.yaml` input trap (confirm the lint input is tracked + in-diff before filing).

## Rules
Verify against current CI workflows / code (C-005). Do NOT regenerate rollups (WP06). Terminology green. `.venv/bin/python`, never bare `uv run`.

## Done
Both traps documented + accurate; true-base cited to WP04; terminology green.
