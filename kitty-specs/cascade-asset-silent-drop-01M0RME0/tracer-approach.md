# Tracer — Approach

Read the charter, AGENTS.md, CONTRIBUTING.md, the readiness probe
(`_readiness/3705-cascade-asset-silent-drop.md`), ADR 2026-08-20-1, the SK-76 ledger entry,
and the live code at `src/charter/cascade.py` (`_referenced_artifacts`,
`CascadeActivationResult`, `NoCascadeReport`, `deactivation_plan`/`DeactivationPlan`) and its
two CLI callers (`activate.py`'s `_render_cascade_activation` /
`_render_no_cascade_warning`, `deactivate.py`'s `_render_cascade_deactivation`) before writing
a line of spec. Verified every line number the issue and the readiness probe cited is still
current on this checkout (`cascade.py:291-293`, `artifact_kinds.py:330-333`) rather than
trusting the prior citations.

Confirmed live that `deactivate.py` has no "no-cascade warning" equivalent (deactivation only
cascades when `--cascade` is explicitly supplied) but DOES share the same
`_referenced_artifacts` seam through `deactivation_plan`'s candidate-set computation — so the
ADR's symmetry requirement is real and testable, not just aspirational, and became User Story
3 / FR-007 / C-002 in the spec.

Read `test_instantiates_is_followed_but_template_dropped_at_candidacy` directly rather than
trusting the "does not need weakening" claim in the mission brief — confirmed it asserts only
`result.activated == {}`, nothing about console output or other result fields, so a new field
on `CascadeActivationResult` is additive and safe. Recorded this as C-004 with the exact test
name and line so a later reviewer can re-verify in one grep.

Replaced the scaffold `spec.md` in place (no new file, no `spec-kitty specify` invocation)
with a spec grounded entirely in what was read live: every requirement cites a real file and
line range on this checkout, not a remembered or assumed location.
