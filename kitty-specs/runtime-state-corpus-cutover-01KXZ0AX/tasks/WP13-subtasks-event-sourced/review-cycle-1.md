---
affected_files: []
cycle_number: 1
mission_slug: runtime-state-corpus-cutover-01KXZ0AX
reproduction_command: null
reviewed_at: '2026-07-20T21:37:09Z'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP13
---

# WP13 Review — APPROVED (IC-10 subtasks event-sourced + doctrine templates)

Commit 3fe51c3ba (net 501+/537- reduction). Verified.

- **Guard reroute (fail-closed, non-vacuous):** core/subtask_rows.py gains authored_subtask_roster (roster from frontmatter subtasks: list) + unchecked_subtask_ids_from_snapshot (completion from the snapshot slot, fail-closed on silent). tasks_shared._check_unchecked_subtasks rerouted; _legacy_unchecked_subtask_ids deleted (checkbox roster retired in favor of the frontmatter roster). Backfill/rollback/gate checkbox readers KEPT (C-010 seed source). 14 tests drive REAL snapshot state (never mocked), assert zero checkbox rows in fixtures, cover block/unblock/force/empty/fail-closed-silent/dashboard-snapshot.
- **Doctrine templates (SOURCE only, 0 agent-copy edits — verified):** 52 checkbox rows stripped from software-dev/documentation/research tasks-templates + prompt rewrites -> mark-status. grep source doctrine = 0 remaining checkbox rows.
- **Dashboard finalize:** _wp_subtask_progress snapshot-only; residual checkbox count + tasks_md_text threading removed.
- Terminology guard + docs-freshness + cli-reference = 69 pass. Clean mypy 68 = base (zero new). ruff clean; zero suppressions; cx<=15.
- **Correctly deferred** the live-mission/corpus tasks.md checkbox physical strip to closeout (avoids self-interference with the running mission's mark-status); guard reroute makes existing checkboxes inert.

**CLOSEOUT reconciliation items (WP13 flagged, base-relative artifacts — not regressions):**
1. Door consistency: WP13's CLI door uses frontmatter-roster+snapshot (fail-closed for future checkbox-free missions); WP06's emit door (_infer_subtasks_complete) uses a checkbox fallback. For checkbox-free missions these DIVERGE (emit allows, CLI blocks). Reconcile the emit door onto WP13's frontmatter-roster model at closeout so both doors are consistent + fail-closed for the final event-sourced state. (WP13 could not edit emit.py — WP06's code not in its lane base.)
2. Corpus checkbox strip + backfill-seed verification: defer to closeout on the merged feat state (where WP03's seeds + Phase-1 are present); verify seed BEFORE any corpus checkbox strip (C-010 data-loss).

**Verdict: APPROVED.** IC-10 delivers the event-sourced subtask guard + checkbox-free templates; the emit-door consistency + corpus strip are closeout reconciliations on the merged state.
