---
affected_files: []
cycle_number: 1
mission_slug: coord-commit-integrity-01KY5JS8
reproduction_command:
reviewed_at: '2026-07-22T21:57:51Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP03
---

# WP03 Review Feedback — Cycle 1 (reviewer-renata/opus)

**VERDICT: REJECT — one blocking gap, test-only fix. Production code is correct; do NOT change it.**

## What passed (do not touch)
- Landmine 1: `_COORD_RESIDUE_FILENAMES["analysis-report.md"]→ANALYSIS_REPORT` KEPT. ✅
- Landmine 2: coord-pinning tests inverted to the PRIMARY truth positively, no reversal, no xfail, exemplar swaps preserve coord coverage. ✅
- Landmine 3: `PARTITION_RATIONALE[ANALYSIS_REPORT]` flipped COORD→PRIMARY. ✅
- One frozenset move only; copy-drop narrow with coord-caller regression; 3 readers aligned; ruff/mypy/C901/suite green. ✅

## The one BLOCKING gap (T009 / DoD line 141)
The FR-001 review-cycle-PRIMARY **committed-ref e2e is ABSENT**. The production code (`review/cycle.py:300` `_review_cycle_wp_dir` unifying read+write on `resolve_planning_read_dir(WORK_PACKAGE_TASK)→PRIMARY`, and the merge-gate reader `post_merge/review_artifact_consistency.py:57`) is CORRECT — but there is no non-fakeable test that would go RED against the coord-husk bug it fixes. The nearest existing test `tests/review/test_cycle.py:46` runs on a FLAT repo (plain `git init`, no coord branch) where the pre-fix `candidate_feature_dir_for_mission` and the new resolver return the IDENTICAL dir — so it cannot catch the regression. Per DoD line 141 ("config-only does NOT satisfy") and DIRECTIVE_041, this is required.

## Required fix (test-only, production code UNCHANGED)
Add ONE test — mirror `tests/coordination/test_analysis_report_rehome.py::test_analysis_report_commits_to_primary_ref_and_is_absent_on_coord`:
1. Build a REAL coord-topology git fixture (`_build_coord_topology` / the coord fixture the rehome test uses).
2. Drive `create_rejected_review_cycle` (the real write site) so `review-cycle-1.md` is authored + committed.
3. Assert `git show <primary_ref>:kitty-specs/<slug>/tasks/<wp>/review-cycle-1.md` SUCCEEDS.
4. Assert `git show <coord_ref>:.../review-cycle-1.md` FAILS (absent) — proving no coord copy via committed trees, not a config assertion.
5. It must be RED against the pre-move code (coord-husk) and GREEN after — direction pinned by the committed ref, not by "green".

Place it in `tests/coordination/test_analysis_report_rehome.py` (or a sibling WP03-owned test file). This is within WP03's owned scope (the review-cycle placement is FR-001, WP03's).

## Non-blocking (do NOT act unless trivial) — operator awareness only
C-008 split-surface: `review-cycle-N.md` now lands PRIMARY while its co-located sub-artifact `baseline-tests.json` stays COORD (pre-existing C-008 contract, outside WP03 owned files). Not a WP03 defect — flagged for a possible future follow-up, no action this cycle.

## Handoff after fix
Run the WP03 gate foreground (`uv run --extra test pytest tests/coordination tests/review/test_cycle.py -q` + the new test), commit, `mark-status` (already done — just move), then `move-task WP03 --to for_review`.
