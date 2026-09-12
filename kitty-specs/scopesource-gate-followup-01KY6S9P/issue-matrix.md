# Issue matrix — scopesource-gate-followup-01KY6S9P

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2873 | ScopeSource gate follow-ups (dead census tier + port decoupling + baseline↔head correctness) | fixed | Delivered by this mission — WP01–WP05 all approved (dead census tier retired FR-001/002; port decoupled FR-005/006/007; baseline↔head correctness + `SOURCE_MISMATCH` FR-008/009/010/011; config selection FR-014; coverage-parity inventory FR-004d) |
| #2871 | Doctrine-controlled transition gates — half A | verified-already-fixed | Shipped predecessor; half-A gate surfaces (`scope_source.py`, `ScopeSource`/`DeclaredCommandScopeSource`, parity harness) present in base `eb06ca176` |
| #2535 | Doctrine-controlled transition gates (design epic) | deferred-with-followup | Parent epic; remains open, follow-up tracked as half B (#2599). This mission delivers the #2873 follow-ups only |
| #2599 | Doctrine-controlled gates — half B (executable gate assets) | deferred-with-followup | Out of scope per spec C-001; this mission makes the half-A gate correct+clean first. Follow-up: #2599 (the half-B mission tracks the deferred work) |
| #2874 | Coord commit integrity (base prerequisite) | verified-already-fixed | Landed in the merged base `eb06ca176`; consumed (not modified) via `_resolve_workflow_read_dir` kind-aware seam (FR-009) |
| #2820 | Dossier parity reconciler (base prerequisite) | verified-already-fixed | Landed in the merged base `eb06ca176`; disjoint from this mission (dossier `BaselineSnapshot` ≠ `BaselineTestResult`) |
| #2741 | Pre-review gate diffs the working tree | verified-already-fixed | Fold/boyscout squad verified already fixed by merge-base-diff-ssot commit `55d060016`; not re-opened by this mission |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

**Note:** `#2873` resolved `in-mission → fixed` on 2026-07-23 once all five WPs reached `approved` (terminal-verdict obligation satisfied ahead of `done`/merge). The GitHub issue closes when the upstream PR lands (closing keyword in the PR body).
