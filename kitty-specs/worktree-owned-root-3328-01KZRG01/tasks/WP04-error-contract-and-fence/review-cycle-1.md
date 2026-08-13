---
affected_files: []
cycle_number: 1
mission_slug: worktree-owned-root-3328-01KZRG01
reproduction_command:
reviewed_at: '2026-08-11T18:52:41Z'
reviewer_agent: implement-command
wp_id: WP04
---

# WP04 planning gap

The cross-surface RED test proves all three ownership refusal codes and exit statuses match, but `mission create --json` omits the contract-required `success: false` field that `next --json` emits.

Evidence: `tests/architectural/test_no_production_worktree_guard_bypass.py` → 3 failed, 3 passed in 111.33s; `/tmp/core-3328-wp04-red.xml`.

The minimal production fix is in `src/specify_cli/cli/commands/agent/mission_create.py`, which remains assigned to approved WP02 and is outside WP04's owned files. Amend planning canonically: transfer that file from WP02 to WP04 for this reconciliation pass, add the T013 mapping, finalize/analyze, then reclaim WP04 and apply only the one-line refusal-envelope fix.
