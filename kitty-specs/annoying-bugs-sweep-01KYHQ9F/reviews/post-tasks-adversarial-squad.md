# Post-Tasks Adversarial Squad

**Date**: 2026-07-27
**Question**: Do WP01-WP05 form non-fakeable, dependency-correct, file-disjoint implementation
slices satisfying every approved requirement, especially P0 #2985 and #2987, without shortcuts that
pass tests while leaving defects?

## Profile And Model Discipline

All three reviewers used `gpt-5.6-sol` with high or xhigh reasoning. Each resolved its profile through
`spec-kitty agent profile show <profile-id>` and loaded
`spec-kitty charter context --action review --json`; no raw profile YAML was used.

| Lens | Profile | Verdict |
|---|---|---|
| Architecture | `architect-alphonso` | BLOCK |
| Debugging | `debugger-debbie` | BLOCK |
| Requirements/review | `reviewer-renata` | BLOCK |

## Confirmed Findings And Corrections

| Severity | Finding | Adjudication and correction |
|---|---|---|
| Critical | Existing bad seed IDs cannot be repaired by re-append because deduplication keeps the first row. | Confirmed by all lenses. Spec, plan, data model, contract, and WP01 now require a distinct deterministic append-only repair identity plus a persisted-old-seed fixture and byte-identical convergence. |
| High | WP01's claim-slot oracle conflicted with legitimate later writers. | Confirmed. Raw seed equality is unconditional; snapshot equality applies only when no later legitimate writer owns the slot. |
| High | WP02's helper-only `FileNotFoundError` test could miss the real post-merge CLI path or retained external `grep`. | Confirmed by two lenses. WP02 now requires a valid Git repository, real CLI invocation, an executable spy/PATH boundary, a deliberate dead-symbol verdict, and proof that only Git is spawned. |
| High | FR-006 lacked proof that the #2985 node reaches blocking CI. | Confirmed by all lenses. WP01 now requires `pytest.mark.regression` and collection through the `regression-tests` job's exact `-m regression` selector. |
| High | Addressed tracker tickets lacked uniform HiC claim and mission-comment preflight. | Confirmed against charter mission hygiene. Every WP now opens with claim/comment evidence for its addressed ticket. |
| High | The issue matrix omitted seven contextual issue references. | Confirmed. The matrix now has all 18 unique issue references, with addressed, deferred, or verified dispositions. |
| Medium | C-005 was not carried into any WP requirement set or actual-diff audit. | Confirmed. Every WP references C-005, rechecks its intended/actual diff, and must stop before undeclared ownership. |
| Medium | Binding campsite cleaning was not a distinct opening step. | Confirmed. Each WP now starts with a bounded domain-matched scout and tidy-first-or-clean-finding requirement. |
| Medium | WP01 omitted malformed/lower-bound timestamp coverage. | Confirmed. The floor failure matrix now covers both and prohibits partial append/status flip. |
| Medium | WP04 permitted a hand-maintained command inventory to self-certify. | Confirmed. The gate must resolve the real Typer tree and include a failing mutation fixture. |
| Medium | WP03/WP04 validation omitted exact lint commands. | Confirmed in scope. Exact Ruff and Markdownlint commands were added; mypy is not applicable because these WPs add no typed Python production module. |

## Residual Review Notes

- The squad did not prototype the compatibility repair. WP01 deliberately owns that implementation,
  but the planning contract now makes the previously impossible invariants coherent and testable.
- Tracker assignment/comment state is implementation-time external evidence and remains open until
  each WP begins.
- The squad is advisory. Its blocking verdict applied to the pre-revision package; the corrections
  above are subject to Spec Kitty validation and implementation review.
