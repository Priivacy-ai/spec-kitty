# Implementation Plan: Write-Side Seam: Matrix & Tracer Writers

**Branch**: `feat/write-side-seam-matrix-tracer` | **Date**: 2026-07-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/write-side-seam-matrix-tracer-01KYP3MH/spec.md`

## Summary

Close the **write/gate side** of the artifact placement seam (the write twin of PR #3060's read-side closure) and, on top of it, make the acceptance/issue matrices **structured JSON** with deterministic write commands, a **row-aware merge driver**, a **lane-safe tracer writer**, and a **common-ancestor lane base** so mission state survives consolidation. This is primarily an **adoption** mission — `write_target`/`commit_for_mission` already exist (ADR `2026-06-24-1`) — plus the one genuine build (the tracer writer) and the matrix structural migration. Delivered across three isolated lanes: **A** (lane-base topology, ADR-first; governs PRIMARY-partition planning durability — independent of the matrix durability regression per the E-B adjudication), **B** (coord-authority gate enabler; blocks only the `decisions/emit.py` gate-route slice of Lane C — the `write_target`-routed writers are gate-invisible), **C** (writers + structured matrix tooling, one seam).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, requests (existing); git worktrees; internal surfaces to extend — `mission_runtime.resolution.PlacementSeam.write_target`, `coordination.commit_router.commit_for_mission`, `acceptance.matrix`, `tasks.issue_matrix`, `lanes.worktree_allocator`, `cli/commands/merge_driver`, `policy/merge_gates`, `status.emit`, `retrospective` (tracer read path)
**Storage**: JSON mission artifacts on the coord partition — `acceptance-matrix.json`, `issue-matrix.json` (new canonical; no markdown render), `status.events.jsonl`; git branches as partition surfaces (coord vs primary)
**Testing**: pytest — red-first ATDD (charter C-011); unit + integration + `tests/architectural/` gates; targeted node-ids locally, CI owns the full sweep; new-branch coverage in the same PR
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows), Python library
**Project Type**: single (CLI + library)
**Performance Goals**: each write command p95 < 3 s (NFR-002)
**Constraints**: cyclomatic complexity ≤ 15; mypy strict + ruff clean, zero new suppressions; NO seam bypass / no parallel write resolver (ADR `2026-06-24-1` C-006); coord-authority gate stays green; NO consolidation abort path (ADR `2026-07-23-2`); event-log remains the sole status authority
**Scale/Scope**: 13 FRs across 3 lanes; ~a dozen true write-bypass sites to route; one structured-schema migration with reader blast-radius (doctor, post-merge review, move-task/approval, finalize-lint, `kind_for_mission_file` recognition, merge-driver registration, doctrine skills — NOT dashboard/gates, which are net-new not migration); one lane-allocation topology change; one coord-authority gate ratchet; one new ADR + three `contracts/` docs

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present (`software-dev-default`). Binding items and this plan's compliance:

- **Single canonical authority / no improvisation** — extends the existing `write_target` seam; C-001 forbids a parallel resolver (ADR `2026-06-24-1` C-006). ✅
- **DDD + tiered rigour** — core seam/merge/lane logic gets full rigour + focused tests; thin CLI wrappers get glue-tier. ✅
- **ATDD-first / red-first** — every FR lands behind a failing test first; FR-010's four gate tests are its red-first surface. ✅
- **Architectural gate discipline** — read-side census, C-008 shards, and the coord-authority gate must stay green; FR-010 re-pins the census floor deliberately with rationale (ADR `2026-06-26-1-single-authority-seam-and-call-site-gate` sanctions this; the by-design floor stays non-vacuous at 3). ✅
- **Terminology canon** — no `feature*`; name the `primary`/`merge`/`routing` sense. ✅
- **Git workflow** — coord topology; consolidate into `feat/…`; PR to `upstream/main` post-consolidation; no direct push to `main`. ✅
- **Complexity ≤ 15 / Sonar** — new helpers extracted + tested; repeated literals hoisted. ✅

**New decision requiring an ADR**: FR-009 lane-base change (amends `2026-04-03-1`). No other new architectural decision (FR-007 implements `2026-06-24-1` C-006; FR-010 implements `2026-06-26-1-single-authority-seam-and-call-site-gate` — cite by slug, two ADRs share the `2026-06-26-1` date). No unjustified gate violations → **PASS**.

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

> Concerns, not work packages. `/spec-kitty.tasks` translates these into WPs. Sequencing (corrected post-plan squad + E-B investigation): **Lane B blocks only the `decisions/emit.py` gate-route slice of IC-03** — `write_target`-routed writers are gate-invisible (D-6), so IC-04/05/06/07 depend on the IC-03 **core**, NOT on Lane B. **Lane A (IC-01) is independent** and — per the 2026-07-29 topology-resolved-`%O` adjudication (E-B) — is **NOT** a predecessor of IC-08's matrix-durability regression: matrices are COORD-partitioned and serialize onto the coord surface (`commit_router.py:248-306`), so FR-008's `%O` comes from the seam-resolved matrix lineage per topology, not IC-01's PRIMARY lane base. The former IC-08 → IC-01 hard edge is **dropped**.

### IC-01 — Lane-base common ancestor (Lane A)

- **Purpose**: Branch execution lanes from the recorded planning-artifact commit so lane writes share a common ancestor with the consolidation base and are not reverted at merge.
- **Relevant requirements**: FR-009 (SC-003).
- **Affected surfaces**: `lanes/worktree_allocator.py` (base ref), `lanes/auto_rebase.py`, `merge/executor.py`, `merge/ordering.py`; dependent-lane invariant #1684; lane-hygiene guard **#2274** (compares `kitty-specs/` by commit-history not content → false-positive after the FR-009 planning-rebase; coordinate #2273/#2626/#2570); **new ADR** under `docs/adr/3.x/`.
- **Sequencing/depends-on**: none (ADR authored first). Independent of IC-08 — the E-B adjudication established that FR-008 matrix durability draws `%O` from the coord-resolved surface, not this PRIMARY lane base, so the former IC-08 → IC-01 edge is dropped. This WP governs PRIMARY-partition (planning) durability only.
- **Risks**: P0 git-topology; must pin a **recorded SHA** (in `lanes.json`/`meta.json`), never a moving tip; must resolve the coord-status-lineage question in the ADR **in light of ADR `2026-06-24-1` §5 (planning artifacts on PRIMARY, matrix/tracer/status on COORD) and FR-007's routing of those writes OFF the lane onto coord — which moots part of the coord-lineage question**; disentangle **FR-009 ancestry (primary partition)** from **FR-008 row-aware-merge durability (coord partition)** — SC-003 bundles both but they own different partitions; add merge/ancestor tests; add NO consolidation abort path.

### IC-02 — Coord-authority gate seam idiom (Lane B, enabler)

- **Purpose**: Route `decisions/emit.py` off the coord-authority allowlist and (only if a seam-routed writer still resolves via the kind-blind resolver) teach the gate the `write_target(<COORD>)` idiom, so routing COORD writes is unblocked.
- **Relevant requirements**: FR-010 (#3055).
- **Affected surfaces**: `decisions/emit.py`, `tests/architectural/test_resolution_authority_gates.py`, `resolution_gate_allowlist.yaml`, census floor/baseline.
- **Sequencing/depends-on**: none. **Blocks ONLY the `decisions/emit.py` gate-route slice of IC-03.** The other writer-routing concerns (IC-04/05/06/07) route purely via `write_target`, are gate-invisible (D-6), and do NOT depend on Lane B.
- **Risks**: interlocking ratchet — census floor 4→3, allowlist + by-design removal, baseline re-pin (four named tests are the red-first surface). **Only `decisions/emit.py` is routed off; the other three write sites (`widen/state.py:63`, `agent_tasks_ports.py:322`, `lanes/recovery.py:765`) are by-design sanctioned coord writes that MUST stay on the kind-blind resolver so the floor stays non-vacuous.** Any gate-predicate widen (Move B) is an ADR amendment of `2026-06-26-1-single-authority-seam-and-call-site-gate`, def-use gated, with an alias-bite non-vacuity test (never a name proxy).

### IC-03 — Write-seam adoption core + true-bypass route (Lane C)

- **Purpose**: One parameterized write-surface resolution (`write_target`) + one materialization authority (`commit_for_mission`); route the true bypass set onto it.
- **Relevant requirements**: FR-007, FR-011, FR-012 (C-001).
- **Affected surfaces**: caller-resolved-`feature_dir` matrix writers; the **core helper** `coordination/write_seam.py` (delivered WP03). Ledger-M16 leaf guard. NOTE: the `decisions/emit.py:71` routing landed wholly in **WP02** (atomic Move A) — it is not an IC-03/WP03 surface; the other three gate write sites stay by-design (IC-02). **DEFERRED → #3071 (2026-07-29):** ~~#2663 (`implement.py::_partition_files_for_commit`)~~ and ~~`status/emit.py` (#2966 slice)~~ are out of this mission — WP03 found them colliding with pinned #2160/#2966 invariants C-006 marks out-of-scope (see spec FR-007 + contracts/write-seam-adoption.md).
- **Sequencing/depends-on**: the `emit.py` slice depends on IC-02; the rest of the core is Lane-B-independent.
- **Risks**: routing the seam's own engine is circular — target only the true bypasses; FR-011 must be a **zero-write refusal** (never fall back to writing `main`).

### IC-04 — Acceptance-matrix verdict command + persist-on-accept (Lane C)

- **Purpose**: A command that fronts `write_acceptance_matrix` via the seam and keeps the computed verdict authoritative; canonical acceptance persists the recomputed `overall_verdict`.
- **Relevant requirements**: FR-001 (#2318 + comment 5102989064); **FR-002 acceptance-schema half** (the structured acceptance schema is homed here); campsite #2743.
- **Affected surfaces**: `acceptance/matrix.py`, `cli/commands/accept.py`, `_evaluate_acceptance_matrix`.
- **Sequencing/depends-on**: IC-03 core.
- **Risks**: must not re-author the computed verdict or clobber invariant provenance.

### IC-05a — Issue-matrix structured schema + canonical writer + recognition map + finalize scaffold (Lane C)

- **Purpose**: Define the `issue-matrix.json` schema and the single canonical writer routed via `write_target(ISSUE_MATRIX)`; teach the basename→kind recognition map about `.json`; migrate the finalize scaffold off `.md`-on-PRIMARY.
- **Relevant requirements**: FR-002 (issue half), C-008 (schema anchor).
- **Affected surfaces**: `tasks/issue_matrix.py` (schema + writer); **`artifacts.py:200 _MISSION_FILE_KIND_BY_BASENAME`** — add `"issue-matrix.json" → ISSUE_MATRIX` (keep `.md` for failover) with positive+negative recognition assertions (**B2 linchpin**: without it `kind_for_mission_file(".json")` → None → not staged to coord / not row-merged); **`cli/commands/agent/mission_finalize.py:355 _scaffold_issue_matrix_if_present` → `tasks/issue_matrix.py:94`** — author `issue-matrix.json` via `write_target(ISSUE_MATRIX)` (COORD), not `.md` on the planning dir (**B3**: else greenfield split-brain, FR-013 migrate-on-write never fires).
- **Sequencing/depends-on**: IC-03 core. **First red-first WP of the structured-matrix work** (B2/B3 are its opening tests).
- **Risks**: split-brain if the recognition map or scaffold lags the writer; assert recognition both ways.

### IC-05b — Issue-matrix reader migration (C-008 blast-radius) (Lane C)

- **Purpose**: Move every live consumer of the issue-matrix from markdown to `issue-matrix.json`.
- **Relevant requirements**: FR-002 (reader migration), C-008, NFR-005.
- **Affected surfaces** (the real live migration consumers — NOT dashboard/gates, which are net-new): `status/doctor.py`, post-merge review (`cli/commands/review/`), move-task/approval blocker, finalize-lint, `kind_for_mission_file` recognition consumers (`auto_rebase`/`commit_router`/coherence); **doctrine/skills (M8)**: `spec-kitty-mission-review/SKILL.md:581/695`, `spec-kitty-implement-review/SKILL.md:499`, `mission-wrap-up-sequence.procedure.yaml:19/50`, `spec-kitty-core.glossary-pack.yaml:679/690/693` (incl. `ISSUE_MATRIX_SCHEMA_DRIFT` + mission-review gate def), `planning-and-tracking.styleguide.yaml:18` — `.md`→`.json`, then run `test_no_legacy_terminology.py`; **test fallout (m3)**: ~10 `.md`-shaped test files judged each (re-pin `.json` / migrate / delete obsolete markdown-parser tests) as explicit fallout, not ad-hoc.
- **Sequencing/depends-on**: IC-05a (schema + writer first).
- **Risks**: C-008 requires *every* live consumer moved; no `issue-matrix.md` emitted going forward; back-compat only via failover-read.

### IC-05c — Issue-matrix migration sub-module + one canonical reader (Lane C)

- **Purpose**: A shared migration sub-module providing failover-read + migrate-on-write + a bulk-migration command, hosting the **single canonical `load_issue_matrix() → rows`** (M7) that every read site calls.
- **Relevant requirements**: FR-013, NFR-006.
- **Affected surfaces**: new migration sub-module + CLI command; **the markdown parser `validate_issue_matrix` (`review/_issue_matrix.py:194`)** — shared by doctor/review/finalize-lint/move-task — must be re-pointed at the one canonical `load_issue_matrix()` (failover-read inside), so migration is not whack-a-field across 5 sites.
- **Sequencing/depends-on**: IC-05a (schema); IC-05b consumes the canonical reader.
- **Risks**: a second reader definition drifting from the canonical one.

### IC-06a — Issue-matrix verdict command (Lane C)

- **Purpose**: A verdict/per-item-status command on `issue-matrix.json`, routed via `write_target(ISSUE_MATRIX)`.
- **Relevant requirements**: FR-003.
- **Affected surfaces**: `tasks/issue_matrix.py`, new CLI command.
- **Sequencing/depends-on**: IC-05a (structured schema first), IC-03 core.
- **Risks**: keep the computed/derived fields authoritative; idempotent (FR-012).

### IC-06b — Multi-file issue-reference discovery + merge-time gate (Lane C)

- **Purpose**: Generalize `detect_issue_references` from single-`spec.md` to all mission artifacts across the three enforcement sites; add the missing merge-time completeness gate.
- **Relevant requirements**: FR-004 (#1738).
- **Affected surfaces**: `tasks/issue_matrix.py`, the three enforcement sites `status/doctor.py:374`, `cli/commands/agent/tasks.py:159`, `cli/commands/agent/mission.py:2140`, and **net-new** reader/gate in `policy/merge_gates.py`.
- **Sequencing/depends-on**: IC-05a, IC-03 core.
- **Risks**: use the *same* canonical-reference definition across finalization, approval, merge, and review (avoid a fourth definition — IC-05c's canonical reader).

### IC-06c — Zero-reference Gate 4 = not_applicable (Lane C)

- **Purpose**: Record Gate 4 `not_applicable` when the spec declares no canonical references (same definition as finalization); retain fail-closed when references exist.
- **Relevant requirements**: FR-005 (#3035).
- **Affected surfaces**: `cli/commands/review/__init__.py`, gate evaluation; both-branch regression.
- **Sequencing/depends-on**: IC-06b (shared discovery definition).
- **Risks**: the zero-ref and has-ref branches both need regression.

### IC-07 — Tracer finding writer (Lane C)

- **Purpose**: The one genuine must-build — a lane-origin tracer-append command routed to the coord surface via `commit_for_mission`, leaving the lane branch unblocked with correct attribution.
- **Relevant requirements**: FR-006 (#2980/#2549; attribution guard #2960).
- **Affected surfaces**: `retrospective/` (writer beside the existing reader), `commit_router`; must NOT use the `read_dir(RETROSPECTIVE)` short-circuit (Ledger-M16).
- **Sequencing/depends-on**: IC-03 core.
- **Risks**: attribution blanking (#2960) — guard `agent` presence.

### IC-08 — Row-aware matrix merge driver (Lane C)

- **Purpose**: Replace the whole-file "more-filled-side" acceptance/issue-matrix drivers with row-aware drivers over the structured JSON so disjoint concurrent-row writes union without clobber.
- **Relevant requirements**: FR-008 (#2482 + disjoint-row gap); **#2970 (5 S2083 path-injection BLOCKERs in `merge_driver.py`) folded here — red-first repro before the fix, do NOT regress the driver contract** (E1, Sonar attack-vector-campsite doctrine). Coordinate #2555/#2228 (adjacent).
- **Affected surfaces**: `cli/commands/merge_driver.py` (incl. #2970 path-injection hardening); **driver registration is 3 sites (M6)** — `.gitattributes` / `lanes/merge.py` registry, **`cli/commands/init.py:73,194`** (new-repo `.gitattributes` pattern), and a **NEW forward migration** repointing `**/issue-matrix.md` → `issue-matrix.json` (do NOT mutate historical `m_3_2_6`) — else upgraded repos bind a driver to a filename that no longer exists and FR-008 clobber-protection is silently absent.
- **Sequencing/depends-on**: IC-05a (structured rows first) only. **No IC-01 edge** — the SC-003 durability regression seeds `%O` from the seam-resolved matrix surface for the active topology (coord lineage here), which is independent of IC-01's PRIMARY lane base (E-B adjudication). The unit driver (T039-T042) and the durability-integration test (T045) both live in this WP.
- **Risks**: row-identity/key stability; the driver must satisfy the disjoint-row union AND the stale-residue case; #2970 fix must not weaken the driver's merge contract.
