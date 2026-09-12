# Tracer: Approach — ci-scoping-gate-reliability

What was tried, what worked, what to do differently. Append during implement.

## Planning phase (2026-08-10)

- **Pre-spec squad (worked well):** an analytical corpus-mapper + a breadth grep sweep enumerated the
  corpus-reading suites and surfaced the non-obvious two-gate structure (the trigger-allowlist omission
  was invisible without tracing `ci-quality.yml`). Grounded the spec instead of guessing globs.
- **Reuse canonical machinery:** dorny/paths-filter groups + the `fast-tests-docs` job shape +
  `doctrine-charter-tests.yml` prior art (path-filtered workflow, skip-with-green). Don't hand-roll.
- **Planned for implement:** an investigate-squad pass before coding (CI-config on blocking gates =
  high risk: base-ref false-green vectors, arch-invariant coverage). 2 WPs: #3008 (trigger+group+job+
  arch), #3147 (docs diff-scope).
- **To verify locally:** run `tests/architectural/test_ci_quality_path_filters.py` +
  `test_ci_collection_completeness.py` before pushing (these live in CI's integration-core-misc job,
  not the fast local suites — easy to miss).
