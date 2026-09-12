---
work_package_id: WP04
title: Compat planner, remediation, notifier, freshness wiring
dependencies:
- WP03
requirement_refs:
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
tracker_refs: []
planning_base_branch: feat/oss-fork-packaging-hooks
merge_target_branch: feat/oss-fork-packaging-hooks
branch_strategy: Planning artifacts for this mission were generated on feat/oss-fork-packaging-hooks. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/oss-fork-packaging-hooks unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
agent: "cursor"
shell_pid: "3890"
history:
- at: '2026-07-21T15:03:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/compat/
create_intent:
- tests/specify_cli/compat/test_planner_distribution_profile.py
- tests/specify_cli/compat/test_remediation_index_url.py
- tests/specify_cli/compat/test_upgrade_hint_chk028.py
execution_mode: code_change
owned_files:
- src/specify_cli/compat/planner.py
- src/specify_cli/compat/remediation.py
- src/specify_cli/compat/upgrade_hint.py
- src/specify_cli/compat/cache.py
- src/specify_cli/core/version_checker.py
- tests/specify_cli/compat/test_planner_distribution_profile.py
- tests/specify_cli/compat/test_remediation_index_url.py
- tests/specify_cli/compat/test_upgrade_hint_chk028.py
- tests/core/test_upgrade_probe_and_notifier.py
role: implementer
tags: []
---

# Work Package Prompt: WP04 – Compat / Remediation / Notifier

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` via `/ad-hoc-profile-load` before continuing.

## Objectives & Success Criteria

Consume `DistributionProfile` at remaining hardcode sites:

1. Planner uses resolved provider + package name; optional `data_freshness_seconds` for `has_fresh_data` only (display throttle unchanged).
2. Remediation + upgrade_hint use profile package name and append index URL args; CHK028 allowlist length ≥ 512 (shared constant).
3. `maybe_emit_no_upgrade_notice` gated by `disable_public_pypi_notifier`.
4. Alias-aware installed version lookup in planner/compat paths (`package_name` then `package_aliases`). Prefer a shared helper in `specify_cli.distribution` if one does not yet exist — do **not** edit `version_utils.py` (owned by WP02); if aliases are missing there, add a distribution helper and leave a one-line follow-up note.
5. Integration tests cover private-index profile + stock notifier path.

## Context

Read FR-011–015, IC-04, remediation CHK028 comments. Keep character class unchanged when raising length. Prefer a shared constant used by both remediation and upgrade_hint.

## Branch Strategy

Depends on WP03. `spec-kitty agent action implement WP04 --agent <name>`.

## Subtasks

- **T017**: Planner + freshness wiring + tests.
- **T018**: Remediation/upgrade_hint index argv + CHK028=512.
- **T019**: Notifier gate.
- **T020**: Alias-aware version lookup.
- **T021**: Integration tests for profile scenario vs stock.

## Definition of Done

FR-011–015 green; stock path unchanged; no fork URLs in defaults; complexity ≤15 on touched functions (extract helpers if needed).

## Reviewer Guidance

Verify display throttle ≠ data freshness. Confirm CHK028 regex class unchanged. Confirm notifier only suppressed when profile flag is true.

## Activity Log

- 2026-07-21T15:55:32Z – cursor – shell_pid=88697 – Assigned agent via action command
- 2026-07-21T16:24:09Z – cursor – shell_pid=88697 – Ready for review: FR-011–015 wired; 96 focused tests green.
- 2026-07-21T16:25:03Z – cursor – shell_pid=3890 – Started review via action command
- 2026-07-21T16:26:03Z – user – shell_pid=3890 – Review passed: profile drives planner/freshness/remediation/CHK028=512/notifier gate; stock parity preserved when package pinned; 96 tests green.
