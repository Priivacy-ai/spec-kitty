# Contracts — ci-suite-map-bind-01KWNPMP

Declared **N/A by design** in [plan.md](../plan.md): no data entities or API surfaces. The
executable contracts ARE the mission's deliverables — the invariant tests themselves:

| Contract | Executable surface |
|---|---|
| Marker→job completeness (3-state, unit/contract ineligibility) | `tests/architectural/test_marker_job_completeness.py` (FR-001) |
| Workflow coherence (needs/filter/glob/cov/workflow-set) | `tests/architectural/test_workflow_coherence.py` (FR-003/FR-005/FR-008) |
| Src-side filter coverage + fail-closed catch-all | src-coverage invariant (FR-010) |
| Skipped-suite fail-closed | quality-gate aggregator arm + its fixture tests (FR-011) |
| Guard self-mapping + --ignore mirrors | FR-012 invariants |
| Zero-orphan floor | `test_gate_coverage.py` ratchet + regenerated baseline (FR-006) |
