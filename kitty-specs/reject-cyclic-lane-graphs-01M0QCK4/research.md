# Phase 0 Research: Reject Cyclic Lane Graphs

## R-001 — Acceptance authority

**Decision**: `compute_lanes` unconditionally validates the complete post-collapse lane graph before calculating depths or returning a manifest.

**Rationale**: Mutating and `--validate-only` mission finalization already call this function through separate branches. Enforcing the postcondition at the construction door prevents current or future callers from forgetting a wrapper and matches the project's single-authority doctrine. The adversarial architecture, regression, and Python API reviewers independently reached the same conclusion.

**Alternatives considered**:

- Require every caller to invoke an exported validator: rejected because omission remains possible and recreates mode divergence.
- Validate in `write_lanes_json`: rejected because validate-only never writes and persistence should receive accepted manifests only.
- Rely on `_compute_lane_depths`: rejected because its recursion guard intentionally produces best-effort depths rather than a governed rejection.

## R-002 — Detector placement and algorithm

**Decision**: implement a pure lane-specific DFS helper in `src/specify_cli/lanes/compute.py`, invoked after `lane_deps` contains code and planning-lane edges.

**Rationale**: This is the first seam containing the authoritative post-collapse graph and its lane-to-WP membership. Sorted roots and neighbors give deterministic first-cycle selection in O(V + E) traversal time. A pure helper remains independently testable and benchmarkable without weakening enforcement.

**Alternatives considered**:

- Reuse the existing generic dependency cycle detector unchanged: rejected because its insertion-order traversal and multi-cycle collection do not meet the canonical selection contract.
- Validate the authored WP graph earlier: rejected because the defect is specifically introduced by ownership collapse after that graph is already valid.

## R-003 — Cycle normalization

**Decision**: return a closed directed path, rotate its unique members to start at the smallest lane ID, repeat that start ID at the end, and derive `cycle_lanes` from first appearance in the path with sorted `wp_ids`.

**Rationale**: This directly implements FR-005/FR-009 and makes equivalent inputs byte-comparable across insertion orders and hash seeds while preserving edge direction.

**Alternatives considered**:

- Sort all cycle members: rejected because arbitrary sorting can destroy directed adjacency.
- Report every cycle: rejected as unnecessary work; one canonical complete cycle is sufficient for remediation.

## R-004 — Error and presentation boundary

**Decision**: introduce a typed `LaneDependencyCycleError(LaneComputationError)` containing immutable normalized facts. The mission-finalization renderer maps it to human text or the governed JSON envelope.

**Rationale**: Structured domain data avoids string parsing or graph recomputation. Keeping JSON/Rich rendering in the CLI preserves layer boundaries, while inheriting from the current exception maintains compatibility with broad computation-error handling.

**Alternatives considered**:

- Put serialized dictionaries on the computation API: rejected because it couples domain code to a CLI wire format.
- Use only an exception string: rejected because automation requires stable structured fields.

## R-005 — Persistence and rollback boundary

**Decision**: reject before planning SHA capture and `write_lanes_json`; do not change the atomic writer or roll back earlier non-lane finalization effects.

**Rationale**: The current call order already makes the required lane-manifest integrity structural. Testing both file absence and byte-identical preservation proves the guarantee without broadening mission scope.

**Alternatives considered**:

- Write a diagnostic manifest: rejected by C-002.
- Add transactional rollback around all finalization: rejected by C-005 as a materially larger lifecycle redesign.

## R-006 — Regression and performance evidence

**Decision**: retain direct `_compute_lane_depths` recursion-safety tests, change public cyclic `compute_lanes` coverage to expect rejection, add mode-parity/persistence subprocess tests, and benchmark the pure detector using the fixed governed fixture.

**Rationale**: The old public acceptance assertion conflicts with the new contract, but its underlying stack-safety concern remains valuable. Isolation makes the 100-lane/500-edge p95 budget reproducible and avoids CLI startup noise.

**Alternatives considered**:

- Delete all old cycle-safety coverage: rejected because defensive helpers should still terminate safely.
- Benchmark the full CLI: rejected because process and filesystem overhead would measure unrelated work.

## Research conclusion

All planning unknowns are resolved. No new dependency, migration, external service, or separate API endpoint is required.
