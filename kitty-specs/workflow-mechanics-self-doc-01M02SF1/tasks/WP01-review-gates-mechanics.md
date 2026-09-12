---
work_package_id: WP01
title: Review-gate mechanics + issue-matrix discovery half
dependencies: []
requirement_refs:
- FR-001
- C-003
- NFR-001
- NFR-005
planning_base_branch: kitty/mission-workflow-self-doc
merge_target_branch: kitty/mission-workflow-self-doc
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-workflow-self-doc. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-workflow-self-doc unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-workflow-mechanics-self-doc-01M02SF1
base_commit: 2ea8f124cec22257f380f3cf4c16becd12407b3d
created_at: '2026-08-15T14:14:06.141036+00:00'
subtasks:
- T001
- T002
- T003
history: []
authoritative_surface: docs/development/how-to/
create_intent: []
execution_mode: code_change
owned_files:
- docs/development/how-to/review-gates.md
tags: []
tracker_refs: []
---

## Objective
Widen `review-gates.md` (retitle from pre-PR-hygiene scope) with a "Review-cycle artifacts and the merge gate" section + the genuinely-absent issue-matrix discovery half. CITE the already-home verdict vocabulary — do NOT restate it (C-003).

## Subtasks
- **T001** Review-cycle/merge-gate MECHANICS (derive from `src/specify_cli/post_merge/review_artifact_consistency.py`, C-005): `terminal_wp_latest_review_artifact_must_not_be_rejected`; the `move-task --review-feedback-file` two-file trap (verbatim copy w/o frontmatter + metadata wrapper — deleting the "duplicate" destroys the only parseable verdict); the `--skip-review-artifact-check --force` override (stamps `review_artifact_override_actor`; only over a genuinely-superseded rejection); no-hand-author MECHANICS (no CLI writer for an `approved` artifact; gate keys on highest-cycle verdict; write both primary+coord surfaces). The doctrine RATIONALE for no-hand-author is WP08's tactic — do NOT put it here (parallel-lane scope pin).
- **T002** Issue-matrix discovery half: `discover_issue_references` runs over ALL mission docs (`src/specify_cli/tasks/issue_reference_discovery.py`, `src/specify_cli/policy/merge_gates.py`); `issue-verdict --actor` required. CITE `src/specify_cli/cli/commands/review/ERROR_CODES.md` + `.agents/skills/spec-kitty-mission-review/SKILL.md` (C-008 block) for verdict vocabulary/schema/`.json`-canonical/`in-mission` semantics. Note ERROR_CODES.md ships under `src/` (a bare-system agent has it) but is outside `docs query` — a pointer is legitimate.
- **T003** Widen title/description to include review-cycle mechanics. Content anchor `terminal_wp_latest_review_artifact_must_not_be_rejected` present.

## Rules
Derive every mechanic from current code (C-005). Do NOT regenerate the docs rollups (WP06 owns the single regen) — skip `check_docs_freshness`; run only `tests/architectural/test_no_legacy_terminology.py`. Use `.venv/bin/python`, never bare `uv run`.

## Done
Terminology green; the mechanics are accurate to code; the already-home facts are cited, not restated.
