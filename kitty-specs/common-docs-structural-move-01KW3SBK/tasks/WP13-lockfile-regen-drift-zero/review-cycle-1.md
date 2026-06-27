---
affected_files: []
cycle_number: 1
mission_slug: common-docs-structural-move-01KW3SBK
reproduction_command:
reviewed_at: '2026-06-27T17:54:13Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP13
---

**Issue**: WP13 must run on the assembled tree (its lane lacks WP10 shadow-deletes → lockfile would include deleted docs/3x). Deferred to the integration-branch endgame per operator decision.
