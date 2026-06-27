# Issue matrix — doctrine-governance-fidelity-01KW42KY

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue
referenced in spec.md. `in-mission` rows must reach a terminal verdict before
mission `done`.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2153 | charter generate discards `documentation_policy` answer | fixed | WP01 @ 207103462 — compiler.py:944 interpolation; reviewer-renata APPROVE |
| #2156 | Enable non built-in Doctrine agents in dispatch mode | fixed | WP02 @ 0251c0adc + WP03 @ e9f73e992 + WP05 @ 3759e0730 + WP06 @ f697d1c24 (charter-gated org dispatch); reviewer-renata APPROVE |
| #2166 | Agent-profile projection ignores the org-pack layer | fixed | WP04 @ 43e608551 — projection emits org source_layer; reviewer-renata APPROVE |
| #2082 | Wire built-in-override governance into doctor doctrine | fixed | WP07 @ d8d959c98 + WP08 @ 847ce823e + WP09 @ a3892eee1 (doctor diagnostics + allowlist retirement); reviewer-renata APPROVE |
| #1799 | Epic: Charter & Doctrine — governance configuration & docs | deferred-with-followup | Parent epic; children #2156/#2153/#2166 addressed in-mission; epic remains open |
| #1868 | Parent epic of #2166 (agent-profiles reliability) | deferred-with-followup | Parent epic; #2166 addressed in-mission |
| #2080 | DRG/doctrine audit + remediation epic | deferred-with-followup | Parent of #2082; broader daphne-led audit out of scope, deferred |
| #2049 | Shrink ratchet allowlists | deferred-with-followup | One burn-down item delivered via WP09 (`category_7` 7→6); full sweep deferred. Follow-up: #2049 |
| #2059 | Decompose `doctor.py` god-module | deferred-with-followup | Partial — override code landed by extraction in WP08; full de-godding deferred. Follow-up: #2059 |
| #1416 | Charter synthesis drops interview answers (key drift) | verified-already-fixed | CLOSED via PR #1419 (touched `synthesizer/` only); distinct from #2153 |
| #1419 | PR fixing #1416 (interview_mapping key drift) | verified-already-fixed | Merged; never touched `charter/compiler.py`, so #2153 stands as a distinct bug |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`,
`in-mission` (being fixed by a later WP in this mission; must reach a terminal
verdict before mission `done`).

## Disposition notes (non-table)

- **In-mission targets** (#2153/#2156/#2166/#2082): satisfied per-WP at `approved`;
  resolve to `fixed` before the mission `done`/merge transition.
- **Reference-by-checklist** (#2049/#2059): the mission delivers one concrete
  burn-down item each (the `category_7` 7→6 shrink; the doctor override-code
  extraction) — it does NOT adopt the full sweep / full de-godding. Verdict
  `deferred-with-followup` reflects the remaining work staying on those tickets.
- **Parent epics** (#1799/#1868/#2080): context only; remain open as parents.
- **Prior art** (#1416/#1419): cross-linked to show #2153 is a distinct
  interpolation bug, not a duplicate of the closed key-drift fix.
- **New (to file)**: the activation-vs-runtime org-pack layout split-brain
  (FR-013 / WP06) has no existing issue — file under #1799 at outbound-tracker time.
