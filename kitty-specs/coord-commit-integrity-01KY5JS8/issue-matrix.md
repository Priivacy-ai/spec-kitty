# Issue matrix — coord-commit-integrity-01KY5JS8

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2861 | agent action review actor leak + coord-commit refused (manual review blocked) | fixed | WP01 (917137eab) diagnosed block = FR-002 coord-commit empty-second-commit (NOT actor); WP04 eliminated it via idempotent commit + flipped test_2861_causation_repro.py to exit 0 (renata empirically confirmed red-on-revert); WP02 (3f4c1b8a7) fixed the actor-shape fidelity (FR-005/006). Manual coord review claim now SUCCEEDS. |
| #2841 | coordination-branch split-brain / unenforced write-placement + staleness | fixed | WP01 misroute fail-loud guard + WP03 (dd4573566) review-cycle write-in-home + analysis-report re-home COORD→PRIMARY + WP04 single status write-authority + WP05 (1f8f3e77f) gate exemption + WP06 (bd5f3d293) coord staleness detector/safe-FF. Placement contract now enforced; all 6 WPs approved. |
| #2803 | lane .venv missing pytest → uv run pytest tests PRIMARY src | deferred-with-followup | OUT of scope (C-007); Follow-up: #2803 tracked by the separate sibling mission (docs/plans/engineering-notes/review-loop-integrity-remediation-research.md) |
| #2853 | frozen-baseline ratchet/allowlist gate toll | deferred-with-followup | OUT of scope (C-007); Follow-up: #2853 tracked separately under epic #2071 |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
