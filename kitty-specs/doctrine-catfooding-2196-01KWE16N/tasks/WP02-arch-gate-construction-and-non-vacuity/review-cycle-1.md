---
affected_files: []
cycle_number: 1
mission_slug: doctrine-catfooding-2196-01KWE16N
reproduction_command:
reviewed_at: '2026-07-01T10:37:24Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP02
---

# WP02 reopened — root-vs-step duplicate reference (found during WP03 review)

`test_root_references_not_repeated_in_steps[architectural-gate-non-vacuity]` FAILS: in
`src/doctrine/tactics/built-in/architectural-gate-non-vacuity.tactic.yaml`, the
`frozen-baseline-shrink-only-ratchet` reference is declared in BOTH step 2's `references:`
block AND the root-level `references:` block. The compliance rule
(`tests/doctrine/test_tactic_compliance.py`) forbids a step-level ref duplicating a
root-level ref. Same class of defect as WP07.

FIX: remove the redundant step-2 `references:` block (keep the root-level one; step 2's
prose already names the ratchet). Then re-run `pytest tests/doctrine/test_tactic_compliance.py -q`
and confirm the `architectural-gate-non-vacuity` case passes. Do not change anything else —
the directive 043, the 4-element mapping, and the ratchet tactic are all approved-correct.
