---
affected_files: []
cycle_number: 1
mission_slug: common-docs-structural-move-01KW3SBK
reproduction_command:
reviewed_at: '2026-06-27T14:56:21Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP06
---

**Issue**: WP06 blocked on an upstream WP05 converter gap (not a WP06 defect).

WP05's ADR converter (approved on 3 representative dialects) hard-fails on 32/117 real ADRs:
- Missing dialect: `**Status**: X` (colon outside bold) — 26 files.
- Missing dialect: `- **Status:** X` (dash+bold hybrid) — 1 file.
- Non-MADR status values (~9) needing a normalization table; 2 ambiguous (operator: both → Superseded).
- Date edge cases (3 era-less files): broken-header Date + 1 with no Date (derive from filename prefix).

**Action**: WP05 is being reopened to extend the converter; re-run WP06 once WP05 re-approves.
WP06 made no commit (clean worktree) — pure reset to planned to await the fixed converter.
