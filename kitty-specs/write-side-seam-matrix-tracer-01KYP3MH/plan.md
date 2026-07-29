# Implementation Plan: Write-Side Seam: Matrix & Tracer Writers

**Branch**: `feat/write-side-seam-matrix-tracer` | **Date**: 2026-07-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/write-side-seam-matrix-tracer-01KYP3MH/spec.md`

## Summary

Close the **write/gate side** of the artifact placement seam (the write twin of PR #3060's read-side closure) and, on top of it, make the acceptance/issue matrices **structured JSON** with deterministic write commands, a **row-aware merge driver**, a **lane-safe tracer writer**, and a **common-ancestor lane base** so mission state survives consolidation. This is primarily an **adoption** mission — `write_target`/`commit_for_mission` already exist (ADR `2026-06-24-1`) — plus the one genuine build (the tracer writer) and the matrix structural migration. Delivered across three isolated lanes: **A** (lane-base topology, ADR-first), **B** (coord-authority gate enabler, blocks C), **C** (writers + structured matrix tooling, one seam).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, requests (existing); git worktrees; internal surfaces to extend — `mission_runtime.resolution.PlacementSeam.write_target`, `coordination.commit_router.commit_for_mission`, `acceptance.matrix`, `tasks.issue_matrix`, `lanes.worktree_allocator`, `cli/commands/merge_driver`, `policy/merge_gates`, `status.emit`, `retrospective` (tracer read path)
**Storage**: JSON mission artifacts on the coord partition — `acceptance-matrix.json`, `issue-matrix.json` (new canonical; no markdown render), `status.events.jsonl`; git branches as partition surfaces (coord vs primary)
**Testing**: pytest — red-first ATDD (charter C-011); unit + integration + `tests/architectural/` gates; targeted node-ids locally, CI owns the full sweep; new-branch coverage in the same PR
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows), Python library
**Project Type**: single (CLI + library)
**Performance Goals**: each write command p95 < 3 s (NFR-002)
**Constraints**: cyclomatic complexity ≤ 15; mypy strict + ruff clean, zero new suppressions; NO seam bypass / no parallel write resolver (ADR `2026-06-24-1` C-006); coord-authority gate stays green; NO consolidation abort path (ADR `2026-07-23-2`); event-log remains the sole status authority
**Scale/Scope**: 13 FRs across 3 lanes; ~a dozen true write-bypass sites to route; one structured-schema migration with reader blast-radius (doctor/gates/review/dashboard); one lane-allocation topology change; one coord-authority gate ratchet; one new ADR + two `contracts/` docs

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present (`software-dev-default`). Binding items and this plan's compliance:

- **Single canonical authority / no improvisation** — extends the existing `write_target` seam; C-001 forbids a parallel resolver (ADR `2026-06-24-1` C-006). ✅
- **DDD + tiered rigour** — core seam/merge/lane logic gets full rigour + focused tests; thin CLI wrappers get glue-tier. ✅
- **ATDD-first / red-first** — every FR lands behind a failing test first; FR-010's four gate tests are its red-first surface. ✅
- **Architectural gate discipline** — read-side census, C-008 shards, and the coord-authority gate must stay green; FR-010 re-pins the census floor deliberately with rationale (ADR `2026-06-26-1` sanctions this). ✅
- **Terminology canon** — no `feature*`; name the `primary`/`merge`/`routing` sense. ✅
- **Git workflow** — coord topology; consolidate into `feat/…`; PR to `upstream/main` post-consolidation; no direct push to `main`. ✅
- **Complexity ≤ 15 / Sonar** — new helpers extracted + tested; repeated literals hoisted. ✅

**New decision requiring an ADR**: FR-009 lane-base change (amends `2026-04-03-1`). No other new architectural decision (FR-007/FR-010 implement `2026-06-24-1`). No unjustified gate violations → **PASS**.

## Project Structure

### Documentation (this mission)

```
kitty-specs/write-side-seam-matrix-tracer-01KYP3MH/
├── spec.md
├── plan.md                 # this file
├── pre-planning-ledger.md  # squad findings + census + lane shape
├── research.md             # Phase 0
├── data-model.md           # Phase 1
├── quickstart.md           # Phase 1
├── contracts/              # Phase 1 (command + adoption + gate contracts)
└── decisions/              # Decision Moment records
```

### Source Code (repository root) — surfaces this mission touches

```
src/mission_runtime/
├── resolution.py            # PlacementSeam.write_target (extend adoption; leaf guard)
└── artifacts.py             # kinds/partitions (ISSUE_MATRIX, ACCEPTANCE_MATRIX, TRACER_FILE)

src/specify_cli/
├── acceptance/matrix.py           # acceptance schema + write; persist-on-accept (FR-001)
├── tasks/issue_matrix.py          # structured schema, multi-file discovery (FR-002/003/004)
├── coordination/commit_router.py  # materialization authority (route consumers)
├── lanes/worktree_allocator.py    # lane base ref (FR-009, Lane A)
├── lanes/auto_rebase.py           # merge-base reasoning (FR-009 blast radius)
├── merge/{executor,ordering}.py   # consolidation (FR-009 blast radius)
├── policy/merge_gates.py          # add issue-matrix completeness gate (FR-004)
├── cli/commands/merge_driver.py   # row-aware matrix merge driver (FR-008)
├── cli/commands/review/__init__.py# zero-reference not_applicable (FR-005)
├── decisions/emit.py              # route off coord-authority allowlist (FR-010, Lane B)
├── status/emit.py                 # route status write via seam (FR-007, #2966 slice)
└── retrospective/                 # tracer read path; add TRACER_FILE writer (FR-006)

tests/{unit,integration,architectural}/   # red-first coverage per FR
docs/adr/3.x/                              # NEW ADR: lane-origin base ref (FR-009)
```

**Structure Decision**: Single project. Changes are concentrated in `src/mission_runtime/` and `src/specify_cli/` with matching tests; one new ADR under `docs/adr/3.x/`. No new top-level package.

## Complexity Tracking

*No Charter Check violations.* The one structural change (FR-009 lane base) is governed by a dedicated ADR rather than an unjustified deviation, so no complexity-exception rows are required.

## Implementation Concern Map

> Concerns, not work packages. `/spec-kitty.tasks` translates these into WPs. The three lanes below encode the hard sequencing: **Lane B blocks Lane C**; **Lane A** is independent but must land before Lane C's consolidation-durability regression is meaningful.

### IC-01 — Lane-base common ancestor (Lane A)

- **Purpose**: Branch execution lanes from the recorded planning-artifact commit so lane writes share a common ancestor with the consolidation base and are not reverted at merge.
- **Relevant requirements**: FR-009 (SC-003).
- **Affected surfaces**: `lanes/worktree_allocator.py` (base ref), `lanes/auto_rebase.py`, `merge/executor.py`, `merge/ordering.py`; dependent-lane invariant #1684; **new ADR** under `docs/adr/3.x/`.
- **Sequencing/depends-on**: none (ADR authored first). Must land before IC-08's consolidation regression is meaningful.
- **Risks**: P0 git-topology; must pin a **recorded SHA** (in `lanes.json`/`meta.json`), never a moving tip; must resolve the coord-status-lineage question in the ADR; add merge/ancestor tests; add NO consolidation abort path.

### IC-02 — Coord-authority gate seam idiom (Lane B, enabler)

- **Purpose**: Route `decisions/emit.py` off the coord-authority allowlist and (only if a seam-routed writer still resolves via the kind-blind resolver) teach the gate the `write_target(<COORD>)` idiom, so routing COORD writes is unblocked.
- **Relevant requirements**: FR-010 (#3055).
- **Affected surfaces**: `decisions/emit.py`, `tests/architectural/test_resolution_authority_gates.py`, `resolution_gate_allowlist.yaml`, census floor/baseline.
- **Sequencing/depends-on**: none. **Blocks all writer-routing concerns (IC-03…IC-07).**
- **Risks**: interlocking ratchet — census floor 4→3, allowlist + by-design removal, baseline re-pin (four named tests are the red-first surface). Any gate-predicate widen must be def-use gated with an alias-bite non-vacuity test (never a name proxy).

### IC-03 — Write-seam adoption core + true-bypass route (Lane C)

- **Purpose**: One parameterized write-surface resolution (`write_target`) + one materialization authority (`commit_for_mission`); route the true bypass set onto it.
- **Relevant requirements**: FR-007, FR-011, FR-012 (C-001).
- **Affected surfaces**: caller-resolved-`feature_dir` matrix writers, the four coord-authority-gate write sites, #2663 (`implement.py::_partition_files_for_commit`), `status/emit.py` (#2966 slice); Ledger-M16 leaf guard.
- **Sequencing/depends-on**: IC-02.
- **Risks**: routing the seam's own engine is circular — target only the true bypasses; FR-011 must be a **zero-write refusal** (never fall back to writing `main`).

### IC-04 — Acceptance-matrix verdict command + persist-on-accept (Lane C)

- **Purpose**: A command that fronts `write_acceptance_matrix` via the seam and keeps the computed verdict authoritative; canonical acceptance persists the recomputed `overall_verdict`.
- **Relevant requirements**: FR-001 (#2318 + comment 5102989064); campsite #2743.
- **Affected surfaces**: `acceptance/matrix.py`, `cli/commands/accept.py`, `_evaluate_acceptance_matrix`.
- **Sequencing/depends-on**: IC-02, IC-03.
- **Risks**: must not re-author the computed verdict or clobber invariant provenance.

### IC-05 — Structured matrix schema + JSON migration + reader migration (Lane C)

- **Purpose**: Migrate the issue-matrix from markdown to `issue-matrix.json` (single canonical artifact, per-item statuses); migrate every consumer to JSON; provide failover-read + migrate-on-write + a bulk-migration command via a shared sub-module.
- **Relevant requirements**: FR-002, FR-013, C-008, NFR-006.
- **Affected surfaces**: `tasks/issue_matrix.py` (schema), consumers `status/doctor.py`, `policy/merge_gates.py`, `cli/commands/review/`, dashboard reader; a migration sub-module + CLI command.
- **Sequencing/depends-on**: IC-02.
- **Risks**: reader blast-radius — C-008 requires *every* consumer moved; no `issue-matrix.md` emitted going forward; back-compat only via failover-read.

### IC-06 — Issue-matrix verdict command + multi-file discovery + gates (Lane C)

- **Purpose**: A verdict/per-item-status command on `issue-matrix.json`; generalize `detect_issue_references` to all mission artifacts; add the missing merge-time completeness gate; record Gate 4 `not_applicable` on zero references.
- **Relevant requirements**: FR-003, FR-004 (#1738), FR-005 (#3035).
- **Affected surfaces**: `tasks/issue_matrix.py`, `status/doctor.py:374`, `cli/commands/agent/tasks.py:159`, `cli/commands/agent/mission.py:2140`, `policy/merge_gates.py`, `cli/commands/review/__init__.py`.
- **Sequencing/depends-on**: IC-05 (structured schema first), IC-02, IC-03.
- **Risks**: use the *same* canonical-reference definition across finalization, approval, merge, and review (avoid a fourth definition).

### IC-07 — Tracer finding writer (Lane C)

- **Purpose**: The one genuine must-build — a lane-origin tracer-append command routed to the coord surface via `commit_for_mission`, leaving the lane branch unblocked with correct attribution.
- **Relevant requirements**: FR-006 (#2980/#2549; attribution guard #2960).
- **Affected surfaces**: `retrospective/` (writer beside the existing reader), `commit_router`; must NOT use the `read_dir(RETROSPECTIVE)` short-circuit (Ledger-M16).
- **Sequencing/depends-on**: IC-02, IC-03.
- **Risks**: attribution blanking (#2960) — guard `agent` presence.

### IC-08 — Row-aware matrix merge driver (Lane C)

- **Purpose**: Replace the whole-file "more-filled-side" acceptance/issue-matrix drivers with row-aware drivers over the structured JSON so disjoint concurrent-row writes union without clobber.
- **Relevant requirements**: FR-008 (#2482 + disjoint-row gap).
- **Affected surfaces**: `cli/commands/merge_driver.py`, `.gitattributes`, `lanes/merge.py` registry.
- **Sequencing/depends-on**: IC-05 (structured rows first).
- **Risks**: row-identity/key stability; ensure the driver satisfies the disjoint-row union AND the stale-residue case.
