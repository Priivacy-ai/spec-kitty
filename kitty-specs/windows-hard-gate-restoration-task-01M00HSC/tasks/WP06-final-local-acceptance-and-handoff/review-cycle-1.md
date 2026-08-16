---
affected_files: []
cycle_number: 1
mission_slug: windows-hard-gate-restoration-task-01M00HSC
reproduction_command:
reviewed_at: '2026-08-16T05:49:24Z'
reviewer_agent: user
wp_id: WP06
---

---
reviewer: codex
verdict: REQUEST_CHANGES
cycle: 2
---

**Issue**: полный architecture gate на immutable SHA `6cc416c42` обнаружил
новый failure, добавленный после предыдущего baseline: в
`test_resolution_authority_gates.py` assertion `len(target) == 1` является
легитимной cardinality-проверкой, но не имеет `golden-count`
marker. Сейчас `tests/architectural` даёт 25 non-escaped convert-sites при
ceiling 24 (`2119 passed, 1 failed`). WP06 нельзя принимать до отдельного
WP07 RED/GREEN/mutation follow-up и повторного полного gate.
