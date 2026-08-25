# Phase 0 Research: Canceled Work-Package Eligibility

## Scope and sources

Research is grounded in issue #3432, the accepted Mission specification, `mission_finalize.py`, `tasks_finalize_validation.py`, the canonical status readers, `lanes/compute.py`, and the merged #3431 cycle-detection regression surface. No unresolved clarification remains.

## Decision 1: Place cancellation policy at the finalization boundary

**Decision**: Resolve canonical lifecycle lanes once in `finalize-tasks`, then build one immutable projection consumed by ownership validation and execution-lane computation.

**Rationale**: `mission_finalize.py` already owns filesystem/status orchestration, while `compute_lanes` is a pure function of dependencies and ownership. Keeping lifecycle I/O out of the allocator preserves deterministic unit behavior and prevents each downstream helper from re-reading or reinterpreting status.

**Alternatives rejected**: Reading status inside `compute_lanes` would couple allocation to coordination topology and filesystem errors. Filtering separately in every validation helper would duplicate policy. Encoding cancellation in work-package frontmatter would compete with append-only event authority.

## Decision 2: Read through the coordination-aware canonical surface

**Decision**: Use `resolve_status_surface_with_anchor` to find the authoritative read directory, verify/read its event log, and obtain current lifecycle lanes with `get_all_wp_lanes`. Do not reuse `_execution_has_begun`, because that helper intentionally degrades status-read failures to `False` for a provenance gate.

**Rationale**: Cancellation eligibility is correctness-critical and must fail closed. A fresh Mission may have known work-package files before per-package lifecycle events are seeded; missing entries are therefore eligible, while an explicit current `Lane.CANCELED` entry is excluded.

**Alternatives rejected**: `status.json` is derived; `lanes.json` is prior allocation output; graceful degradation violates NFR-004 for cancellation.

## Decision 3: Reject cut edges before filtering

**Decision**: Before removing canceled nodes, enumerate every direct dependency where the dependent is eligible and the prerequisite is canceled. Sort by dependent ID then canceled dependency ID and reject the entire finalization attempt.

**Rationale**: Filtering first would erase evidence and make a required predecessor appear satisfied. Reporting all direct cut edges lets the operator repair the graph in one pass. Canceled-to-canceled and canceled-to-active declarations leave with their canceled source and do not block.

**Alternatives rejected**: Treating cancellation as satisfaction changes workflow semantics; auto-canceling or rewriting makes policy decisions for the operator; stopping at the first edge creates repair loops.

## Decision 4: Guard before all finalization mutation

**Decision**: Reorder the command so dependency/status reads and stale-edge validation precede target-branch persistence, matrix scaffolding, frontmatter writes, event emission/bootstrap, generated planning artifacts, dossier sync, and commits.

**Rationale**: The agreed contract is fail-before-mutation, not merely fail-before-`lanes.json`. The current command performs several writers before execution-lane computation, so a late check would leave partial residue.

**Alternatives rejected**: Checking only in `_compute_and_write_lanes` is too late. Rolling back earlier writers is riskier than ordering the guard first.

## Decision 5: Preserve raw-input failures while allowing all-canceled success

**Decision**: Validate the unprojected Mission inputs first. If eligible work remains, retain the existing empty-manifest/empty-graph refusal. If the projection proves zero eligible work from a nonempty known Mission, call the allocator with empty maps and persist its normal empty manifest.

**Rationale**: `compute_lanes` already has a deterministic empty result; the rejection is in the finalizer's compound input guard. Eligibility metadata distinguishes valid zero executable work from malformed inputs.

**Alternatives rejected**: Removing the guard unconditionally would turn invalid planning-artifact cases into silent success. Skipping `lanes.json` would preserve false-success ambiguity.

## Decision 6: Extract a small pure module

**Decision**: Add `finalization_eligibility.py` beside `mission_finalize.py` for immutable value objects, projection, cut-edge detection, and keyed-map filtering.

**Rationale**: `mission_finalize.py` is already 2,996 lines and `tasks_finalize_validation.py` owns broader dependency/frontmatter validation. A focused module is easier to test and avoids expanding either authority.

## Performance conclusion

Projection is `O(V + E)` over work packages and direct dependencies, with `O(E log E)` worst-case ordering for diagnostics. At 100 work packages this is negligible compared with existing filesystem, ownership, Git, and status operations. Tests use deterministic in-process fixtures rather than timing sleeps.
