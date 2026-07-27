# Contracts — merge-squash-provenance-and-rollback-coherence-01KXRRB7

**No new external API/interface contract.** This is a merge-core bug-fix mission
(#2709/#2711); it changes internal reconciliation behavior, not a published surface.

The behavioral contracts this mission delivers are pinned as executable regression tests,
not contract documents:

- **#2709** — `tests/regression/test_issue_2709_squash_provenance.py` (+ `test_issue_2709_projection_union.py`):
  squash merge preserves target-newer `meta.json` acceptance/VCS provenance + `traces/*.md`;
  the coord→target projection unions the event log and rematerializes `status.json`.
- **#2711** — `tests/regression/test_issue_2711_merge_rollback_resume_coherence.py`:
  rollback leaves committed==working per-WP status coherent; `--resume` is idempotent
  (committed `done` `event_id` byte-stable).
- **Class closure** — `tests/architectural/test_merge_reconciliation_class_guard.py`,
  `tests/architectural/test_resume_non_reemission_guard.py`.

New CLI surface (internal git merge drivers, not a stable user API):
`spec-kitty merge-driver-meta`, `spec-kitty merge-driver-traces`.
