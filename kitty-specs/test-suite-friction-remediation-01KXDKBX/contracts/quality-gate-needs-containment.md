# Contract — quality-gate.needs ⊇ pytest-jobs containment (IC-11 / FR-012, #2622)

## Behaviour
- GIVEN the CI workflow model (`_gate_coverage.WorkflowModel`),
  LET `pytest_jobs = { job : any step run-cmd matches \bpytest\b }`,
  WHEN the guard runs,
  THEN it asserts `pytest_jobs - NON_BLOCKING_ALLOWLIST ⊆ quality_gate.needs`.
- GIVEN a new `pytest`-invoking job is added without a `quality-gate.needs` edge and without an allowlist entry,
  WHEN the guard runs,
  THEN it FAILS (the un-gated suite job is caught).
- EACH `NON_BLOCKING_ALLOWLIST` entry MUST carry a why-non-blocking rationale string (mirroring the CI_INVISIBLE ledger pattern).

## Non-fakeable evidence
- A regression adds a fake pytest job to the parsed model and asserts the guard fails.
- `slow-tests` and `mutation-testing` are resolved to an explicit state: either added to `quality-gate.needs`, or added to `NON_BLOCKING_ALLOWLIST` with a rationale — never left silently absent.

## Anti-goals
- Do NOT hard-code the current job list; derive `pytest_jobs` from the workflow model so a future job is covered automatically.
- Do NOT match `pytest` inside comments/strings — anchor on the run-command token.
