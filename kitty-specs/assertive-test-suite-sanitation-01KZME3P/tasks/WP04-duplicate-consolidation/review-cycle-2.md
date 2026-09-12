---
affected_files: []
cycle_number: 2
mission_slug: assertive-test-suite-sanitation-01KZME3P
reproduction_command:
reviewed_at: '2026-08-10T11:57:29Z'
reviewer_agent: user
wp_id: WP04
---

# WP04 cycle 2 — changes requested

Implementation accounting is now credible: 82/82 exact groups; 110/110 removed definitions;
706→602 collected nodes; exact net -104; frozen route memberships match; focused/head receipts pass;
the 300.011-second gate timeout and identical base/HEAD diagnostic red are properly attributed.

## HIGH-1 — KEEP divergence remains identifier-derived

All 25 KEEP rows use the same generic overlap sentence and every `node_rows[].oracle` is merely
`boundary:<member-id>`. Eighteen rows claim only oracle divergence because names differ, not because
a concrete input/asserted observable differs. Example: `WP04-05a174447421` labels present vs empty
`.kittify/doctrine` cases as different oracles while every other dimension is identical. Record the
actual input/boundary, asserted observable, and live callable for each member; populate divergence
only from differing concrete values; consolidate when no real dimension differs.

## HIGH-2 — causal receipts are neither replayable nor family-complete

The receipt commands invoke plain pytest; production perturbations exist only as prose, with no
executable injection/patch or authority diff/hash. Re-running them at HEAD cannot replay the fault.
Also, 22 deleting dispositions have no named replacement survivor in any campaign selection,
including `WP04-042f20c3dff2`, `WP04-60055e86229a`,
`WP04-S03-glossary-context-defaults-aliases`, and `WP04-S06-scoping-normalization`.
`WP04-80510e44483f` and `WP04-d06b68997031` still have no replacement and no explicit proved reason
why none is required, yet claim a retained representative failed. Persist a replayable perturbation;
select a named survivor per deleting family, or explicitly prove why a non-causal delete-all family
requires none. Do not transfer proof across different inputs/oracles merely because source cluster
matches.

## HIGH-3 — raw results duplicate semantic groups

`wp04-results.json.groups` has 109 rows but only 91 unique fingerprints: all nine semantic groups
appear three times. Actual row totals are 61 CONSOLIDATE / 23 DELETE / 25 KEEP, contradicting the
declared 57 / 9 / 25. Emit every group once, regenerate totals, and add a consistency rejection for
duplicate fingerprints/count drift.

Independent checks: WP01 validator valid (91 dispositions/222 members); recursive AST 677→573,
110 removed + six added; route memberships zero mismatches (222 full-collection, 222 full-parallel,
three architectural, two contract); 71 named survivors exist; receipt hashes valid; Ruff passes;
worktree clean. Cycle 3 is final. Keep remediation bounded to these evidence defects.

Anti-patterns: dead code PASS; synthetic fixture PASS; silent empty return N/A; FR coverage FAIL;
frozen surface PASS; locked decision FAIL; shared ownership PASS; production fragility N/A.
