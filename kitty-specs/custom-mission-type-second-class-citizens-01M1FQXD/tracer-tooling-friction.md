# Tracer: Tooling Friction — custom-mission-type-second-class-citizens-01M1FQXD

Mission: Custom mission types are second-class citizens (#3830, #3831, #3832)
Phase: spec

Seeded at spec authoring per charter standing order #3 (mission tracer files).
Append friction encountered during plan/tasks/implement/review here; assess at
mission close.

## Spec phase

- No tooling friction encountered authoring this spec. All code citations
  (file paths, symbol names, line numbers) in the operator's brief were
  re-verified directly against the checkout via grep/sed rather than trusted
  on faith, per charter guidance to cite by symbol and verify every line
  number. All citations held up; only one detail needed correction (see
  tracer-design-decisions.md: `mission_setup_plan.py`'s three `is_substantive`
  call sites are not uniformly `kind="plan"` — line 553 is `kind="spec"`).
- GitHub issues #3830, #3831, #3832, #2660, and #3284 were all independently
  re-verified live via `gh issue view` rather than trusted from the brief;
  all matched.
