# Implementation Plan: Read-Side Placement-Seam Migration

**Branch**: `fix/read-side-placement-seam-migration` | **Date**: 2026-07-27 | **Spec**: [spec.md](./spec.md)
**Input**: `kitty-specs/read-side-placement-seam-migration-01KYHP67/spec.md`

## Summary

Close the read-side of the placement port (#2922, parent #1878): ~60 production
modules bypass the kind-aware, fail-loud read seam (`PlacementSeam.read_dir`) by
calling the kind-blind `candidate_feature_dir_for_mission` (~33 files) or the
lenient `resolve_planning_read_dir` (~44 files) directly. Classify every site,
migrate the fail-loud-appropriate ones onto the seam, keep diagnostic/audit
paths lenient by design (sanctioned), sanction the resolution infrastructure,
and add a **structural read-side AST gate** symmetric to the write-side ratchet
(reusing the shared whole-tree scanner) so new bypasses cannot land. Fold in the
#2921 `repair_lane_mismatch` frontmatter-corruption fix.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `mission_runtime` (`resolution.py::PlacementSeam.read_dir:1404`, `resolve_artifact_surface:1634`, `placement_seam:1754`), `specify_cli/missions/_read_path_resolver.py` (`candidate_feature_dir_for_mission:1148`, `resolve_planning_read_dir:1349`), `coordination/surface_resolver.py`; `tests/architectural/_placement_whole_tree_scan.py`, `_ratchet_keys.py`, `test_no_write_side_rederivation.py` (mirror)
**Storage**: n/a (reads over partitioned branches)
**Testing**: pytest; red-first; whole-tree AST gate with bite + symmetry meta-tests; behavior-preservation tests for the healthy case; audit-path leniency tests
**Project Type**: single (CLI internals + arch gate)
**Performance Goals**: gate runs within the existing arch-suite budget (reuses the shared scanner, no second walk)
**Constraints**: reuse the seam + `CoordinationBranchDeleted` (no new authority/exception); gate seeded-red/last; site-level (not file-blanket) allow-list; healthy-case behavior-preserving
**Scale/Scope**: ~60 bypass modules across 2 resolver families; +1 gate; +#2921 bugfix

## Charter Check

*GATE: passes.*
- **Single canonical authority** (#2160 / brownfield-dup-consolidation): migrate onto the one seam; sanction its implementation modules; one shared scanner. No forked read authority, no second tree walk (NFR-003).
- **ATDD/red-first**: #2921 red-first through `repair_lane_mismatch`; gate bite test; behavior-preservation + audit-leniency tests land with their WPs.
- **Refactor-stable arch tests**: the gate pins the negative invariant ("no direct kind-blind/lenient read outside the seam") via the ratchet, not code shape.
- **No green-washing**: shrink-only content-descriptor allow-list with staleness twin-guard (NFR-004); no blanket file exemptions (C-003).

## Project Structure

```
kitty-specs/read-side-placement-seam-migration-01KYHP67/
├── plan.md · research.md · data-model.md · contracts/ · tasks.md
```

### Source touch-set (anchors)

```
src/mission_runtime/resolution.py                         # seam (REUSE; likely sanctioned)
src/specify_cli/missions/_read_path_resolver.py           # kind-blind/lenient primitives (SANCTION — the authority)
src/specify_cli/coordination/surface_resolver.py          # infra self-consumer (SANCTION)
src/mission_runtime/write_target_degrade.py               # infra self-consumer (SANCTION)
<~57 consumer modules>                                    # MIGRATE or STAY-LENIENT (per classification) — e.g. cli/commands/agent/workflow.py(17), workspace/context.py(7), merge/executor.py(6), coordination/status_transition.py(6), lanes/recovery.py, dashboard/scanner.py, status/aggregate.py, review/cycle.py, ...
tests/architectural/test_no_read_side_bypass.py           # NEW structural gate (mirror write gate)
tests/architectural/_placement_whole_tree_scan.py         # REUSE scan_scope() (no fork)
tests/architectural/_ratchet_keys.py                      # REUSE content-descriptor allow-list machinery
src/specify_cli/task_metadata_validation.py               # #2921 fix (:127, :178)
```

**Structure Decision**: single project. No new packages; migrate consumers onto
the existing seam, add one arch-gate module, fix one bug module.

## Implementation Concern Map

### IC-01 — Classification ledger of all bypass sites
- **Purpose**: Triage every one of the ~60 sites into migrate-fail-loud / stay-lenient / sanction-infra, with the target `MissionArtifactKind` for kind-blind sites.
- **Relevant requirements**: FR-001.
- **Affected surfaces**: a committed classification ledger (data-model.md / a mission doc); reads across the 60 modules.
- **Sequencing/depends-on**: none (first).
- **Risks**: getting a kind wrong flips the partition; mis-classifying an audit path as fail-loud regresses tooling. This ledger is the mission's spine.

### IC-02 — Sanction resolution infrastructure
- **Purpose**: Mark the read-primitive authority + infra self-consumers sanctioned (not migrated).
- **Relevant requirements**: FR-003.
- **Affected surfaces**: `_read_path_resolver.py`, `surface_resolver.py`, `write_target_degrade.py`; the gate's sanctioned set.
- **Sequencing/depends-on**: IC-01.
- **Risks**: over-sanctioning hides real bypasses; keep it to genuine infra with rationale.

### IC-03 — Migrate fail-loud-appropriate kind-aware callers
- **Purpose**: Route the ~44 `resolve_planning_read_dir(kind=...)` sites classified fail-loud-appropriate to `read_dir(kind)`.
- **Relevant requirements**: FR-002, NFR-002.
- **Affected surfaces**: the kind-aware consumer subset (batched).
- **Sequencing/depends-on**: IC-01. Batched into multiple WPs by module cluster.
- **Risks**: lenient→fail-loud behavior change; healthy-case behavior-preservation tests required per batch.

### IC-04 — Adjudicate + migrate kind-blind callers
- **Purpose**: Give each of the ~33 `candidate_feature_dir_for_mission` sites a declared kind and route to the seam (where fail-loud-appropriate).
- **Relevant requirements**: FR-002, NFR-002.
- **Affected surfaces**: the kind-blind consumer subset (batched); the god-module `cli/commands/agent/workflow.py` (17 sites) is its own WP.
- **Sequencing/depends-on**: IC-01. Batched.
- **Risks**: multi-kind readers need splitting; retrospective reads route to `resolve_retrospective_home`.

### IC-05 — Keep diagnostic/audit paths lenient (allow-list)
- **Purpose**: Record must-stay-lenient callers (doctor/dashboard/cutover/status readers) as sanctioned allow-list entries with rationale, not migrations.
- **Relevant requirements**: FR-004, NFR-001.
- **Affected surfaces**: the gate allow-list; audit-leniency tests.
- **Sequencing/depends-on**: IC-01.
- **Risks**: the correctness trap — migrating these to fail-loud breaks audit tooling; NFR-001 tests guard it.

### IC-06 — Structural read-side gate + shrink-only allow-list
- **Purpose**: Whole-tree AST gate reds on new direct kind-blind/lenient reads; deferred residuals in a content-descriptor allow-list with staleness twin-guard.
- **Relevant requirements**: FR-005, FR-006, NFR-003, NFR-004.
- **Affected surfaces**: `tests/architectural/test_no_read_side_bypass.py` (new), reusing `_placement_whole_tree_scan.scan_scope()` + `_ratchet_keys`.
- **Sequencing/depends-on**: IC-02..IC-05 (lands seeded-red with a shrinking allow-list, or last, per C-002).
- **Risks**: forking the scanner (NFR-003 forbids); vacuous allow-list (staleness twin-guard forbids); must include a bite test + symmetry meta-test.

### IC-07 — Fix repair_lane_mismatch (#2921)
- **Purpose**: Stop feeding raw frontmatter text into `build_document`'s padding slot.
- **Relevant requirements**: FR-007, SC-005.
- **Affected surfaces**: `src/specify_cli/task_metadata_validation.py` (:127 destructure, :178 build call) + new behavioral test.
- **Sequencing/depends-on**: none (independent; can land any time).
- **Risks**: none significant; red-first through the pre-existing `repair_lane_mismatch` entry point.

Suggested sequencing: **IC-07 anytime** ∥ **IC-01 → IC-02 → (IC-03 ∥ IC-04 batches) → IC-05 → IC-06 (gate last/seeded-red)**.

## Key Risks (grounding squad)

- **Lenient→fail-loud is a per-site behavior change** — classify before migrating; audit paths stay lenient (IC-01/IC-05, NFR-001).
- **~60 files, not a sed sweep** — kind-blind bucket needs per-caller kind decisions; batch and adjudicate (IC-04).
- **Gate could block its own migration** — seed it red with a shrinking allow-list, land last (C-002).
- **Fork/vacuous-gate hazards** — reuse the shared scanner; shrink-only ratchet with staleness twin-guard (NFR-003/NFR-004).
- **Infra self-consumers** — sanction, don't migrate (IC-02).
- **Shared-package boundary** — `src/runtime/next/runtime_bridge_identity.py` needs a boundary-compatible route (edge case).

## Complexity Tracking

*No Charter Check violations.* Large surface (~60 files) but no new architecture — migration onto an existing seam + one gate mirroring an existing one + one bugfix.

## Out of Scope

Write-side (done), #2966 write-target consolidation, #2964 terminology, collapsing `resolve_planning_read_dir` into the seam (Directive-044), and primary-tree enumeration reads.
