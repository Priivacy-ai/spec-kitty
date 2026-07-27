---
affected_files: []
cycle_number: 2
mission_slug: release-320-workflow-reliability-01KQKV85
reproduction_command:
reviewed_at: '2026-05-03T12:28:45Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP01
---

**Issue 1**: Review artifact fixture does not match the production review-cycle contract.

`tests/reliability/fixtures/mission.py` writes review artifacts to `mission.mission_dir / spec.file_name`, and `ReviewArtifactSpec.file_name` produces names like `review-cycle-wp01-01.md`. Production code and existing tests expect review-cycle artifacts under the work-package sub-artifact directory with numeric names: `kitty-specs/<mission>/tasks/<WP-slug>/review-cycle-N.md`, referenced as `review-cycle://<mission>/<WP-slug>/review-cycle-N.md`.

This blocks WP01 because later WPs are instructed to consume these review artifact helpers for review artifact consistency checks. A fixture with the wrong location and filename will either miss stale rejected artifacts or force downstream tests to reimplement the real contract.

Requested fix: update the review artifact helper to create/use the WP sub-artifact directory and numeric filename shape, for example `tasks/WP01-regression-harness/review-cycle-1.md`; expose enough WP slug/path information for callers; and strengthen the smoke test to assert the artifact path and name match the production contract.

Tests run by reviewer: `uv run pytest tests/reliability -q` passed.

Downstream impact: WP02, WP03, WP04, WP05, and WP06 depend on WP01. After this fix lands, those agents should rebase their lane workspace with `git fetch && git rebase kitty/mission-release-320-workflow-reliability-01KQKV85-lane-a` or restart from the updated WP01 base, depending on their current state.
