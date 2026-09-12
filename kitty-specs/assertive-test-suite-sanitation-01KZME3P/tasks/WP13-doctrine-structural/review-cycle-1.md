---
affected_files: []
cycle_number: 1
mission_slug: assertive-test-suite-sanitation-01KZME3P
reproduction_command:
reviewed_at: '2026-08-10T16:44:14Z'
reviewer_agent: reviewer-renata
wp_id: WP13
---

# WP13 review cycle 1 — changes requested

## Blocking finding 1 — restore the protected-branch single-authority gate

`tests/architectural/test_protection_resolver_call_sites.py` is not an obsolete call-site count. The accepted ADR `docs/adr/3.x/2026-06-26-1-single-authority-seam-and-call-site-gate.md` explicitly identifies this exact test as the shipped, trusted precedent for enforcing the `ProtectionPolicy.resolve` single-authority boundary, and its Decision Outcome requires the seam-plus-AST-gate pattern. The deleted test scans the live `src/` corpus and would catch a newly copied bare `protected_branches(...)` bypass outside the resolver/delegate. No surviving WP13 test owns that boundary. Deleting it contradicts current authority and reduces unique plausible-fault coverage (FR-003/FR-007/NFR-007).

Restore this gate (reduce incidental prose/shape if useful), retain its live-corpus assertion plus a realistic prohibited/compliant bite, and update WP13 disposition/results arithmetic and the WP07 handoff as applicable. Its ledger row must cite the accepted ADR rather than the generic no-authority deletion anchor.

## Blocking finding 2 — preserve the resolver-first profile-guidance boundary

`tests/architectural/test_profile_load_resolver_guidance.py` also has current authority: `src/doctrine/skills/spk-doctrine-profile-load/SKILL.md` and `references/profile-load-mechanics.md` require resolver-backed loading and prohibit primary raw `.agent.yaml` reads except the explicitly bounded CLI-less read-only fallback. The deleted guard scans the nonzero shipped doctrine corpus and can catch a real agent-guidance regression. The current DELETE row's claim that there is “no runtime consumer oracle” ignores agents as the live consumer and provides no successor.

Restore a minimal version of this guard. The historical numeric floor and brittle exact prose may stay deleted, but preserve the current semantic prohibition, non-vacuous live corpus, realistic prohibited guidance, and compliant bounded-fallback control. Update the ledger/results/counts accordingly and give this family its own authority/corpus/fault evidence.

## Evidence and checklist

- Reproduced focused survivor run: `131 passed, 0 skipped`, one expected warning.
- Reproduced collection: `131 tests collected`.
- Reproduced `ruff`, focused `mypy`, `git diff --check`, and layer gate (`17 passed`).
- Independently reconciled WP01 census hash and all 42 owned paths: base `526`, head `131`; 18 deleted files, 24 reduced files; 15,590 → 7,018 LOC.
- Scope/ownership is exact: 42 owned test paths plus the two declared evidence artifacts; no production or shard-map edits.
- Anti-patterns: dead code N/A; synthetic-fixture PASS for retained behavior overall; silent empty return N/A; FR coverage **FAIL** for the two unique current boundaries above; frozen surface PASS; locked decision **FAIL** because the accepted ADR's named gate is removed; shared-file ownership PASS; production fragility N/A.

This is a finite correction: restore/reduce the two current-authority guards, replace their generic inherited DELETE proof with family-specific evidence, rerun the same gates, and keep the rest of the reduction unchanged.
