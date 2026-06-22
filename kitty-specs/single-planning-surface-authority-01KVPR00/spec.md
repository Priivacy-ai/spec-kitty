# Spec: MissionTopology SSOT + structural planning-surface coherence

**Mission**: `single-planning-surface-authority-01KVPR00`
**Type**: software-dev (architectural seam + structural convergence)
**Driver issues**: #2069 (MissionTopology SSOT seam — *the design, goes first*), #1716 (single surface authority) · structurally closes #2062, #2063, #2064 · parent epic #2007 / execution-context epic #1619

> **REVISION NOTE (2026-06-22).** This spec was revised twice. (1) After design ticket
> **#2069** finalized, the operator ruled the **new design lands first** and the
> #2062/#2063/#2064 family is fixed **structurally** — the read path consults an explicitly
> **stored** mission topology, not a re-inference from on-disk worktree existence (C-004).
> Operator's binding principle: *"if storing topology re-opens #2062, that proves our prior
> #2062 fix was non-structural."* (2) The operator then **carved the independent block C**
> (the real `worktree repair` verb #1890, the command-reference guard #2008, the
> doctor/`mission.py` de-godding extractions #2059/#2056, the doctrine-prompt migration, and
> the cheap campsite folds #2066/#1891/#2037/#2048) **out to a separate follow-up mission**,
> so THIS mission is a focused **seam + structural-fix** scope (FR-001..FR-011). The
> codebase-wide `CommitTargetKind` eradication + universal resolver adoption remain a further
> follow-on **Mission B** (C-007).

## Overview

Spec Kitty decides *where* a mission's planning artifacts live (PRIMARY checkout vs
COORDINATION worktree) by **re-inferring the mission's shape, ad-hoc, at many seams** from
scattered on-disk and git signals. A mission can take one of four shapes across the
orthogonal **coordination × lanes** grid, but **no shape is a first-class, stored value**:
each consumer re-derives a slice (`coordination_branch is None ⇒ FLATTENED`,
`read_lanes_json(...)`, `CoordState.MATERIALIZED` from a `stat`), the slices drift, and the
artifact written through one inference is read back through another. That drift **is** the
#2062/#2063/#2064 coord/primary desync class.

This mission lands the **#2069 design** as the structural fix:

1. **Name the shape.** A mission-level `MissionTopology` enum makes the coord×lanes
   cross-product four named values.
2. **Store it, don't guess it.** `topology` is minted into `meta.json` at mission create
   and **read** thereafter — never re-inferred from disk. Legacy missions are backfilled once.
3. **One resolver, pure.** `resolve_context_for_mission(mission_id, topology) ->
   ExecutionContext` is a **pure projection** over the existing single construction door
   (`build_execution_context`); the imperative shell parses/persists `meta.json` and passes
   `id + topology`. **Both** hand-rolled derivations are retired (`resolution.py:705-718` AND
   the independent `runtime_bridge.py:144-211` disk-`stat` ladder); the 9 `.kind is COORDINATION`
   decision sites adopt a `routes_through_coordination` predicate (the `CommitTargetKind` *type*
   eradication is the behavior-neutral Mission B).
4. **Adopt structurally.** The planning read/write commands resolve their surface through the
   seam, so a flattened mission resolves PRIMARY because its **stored** topology says so —
   *not* because a band-aid out-voted an on-disk husk. #2062/#2063/#2064 close at the root.

**Campsite-cleaning directive #1970 stays ACTIVE** (operator mandate): adjacent debt on a
touched surface is remediated in-slice, bounded to mission goals (C-001). The *named*
de-godding extractions (doctor/`mission.py`) and the cheap fold tickets moved to the carved
follow-up mission; opportunistic in-slice cleanup of touched lines still applies here.

## Domain Language

- **MissionTopology** (canonical) — the mission-level enum naming the four shapes of the
  **coordination × lanes** grid as one stored value:
  `SINGLE_BRANCH` (no coord, no lanes), `LANES` (no coord, lanes), `COORD` (coord, no lanes),
  `LANES_WITH_COORD` (coord, lanes). It classifies the *whole mission shape*, unlike the
  per-ref `CommitTargetKind`.
- **FLATTENED** — a **historical/metadata flag**, NOT a topology value. A mission that *was*
  coord and had its `coordination_branch` dropped is now `SINGLE_BRANCH`/`LANES` with a
  `flattened` provenance mark; the residual `-coord` husk is the carved verb's prune concern.
- **Stored topology** — the `topology` field in `meta.json`: authoritative, read at resolve
  time, never re-inferred from worktree existence or `coordination_branch is None`.
- **`resolve_context_for_mission`** — the pure SSOT resolver
  `(mission_id, topology: MissionTopology) -> ExecutionContext`; a thin projection over
  `build_execution_context` (the sole construction door), with no filesystem I/O.
- **ExecutionContext / ActionContext** — the real op-composite value object
  (`src/mission_runtime/context.py:177`) bundling the branch refs, primary/coord surfaces,
  status surfaces, artifact placement, and identity fragments. (#2069 corrected the operator's
  working name "MissionContext" — that type does not exist.)
- **Orphaned coord worktree / husk** — a `.worktrees/<slug>-<mid8>-coord/` directory left on
  disk after flatten/teardown; must NEVER be a read authority. With stored topology it simply
  isn't consulted.

## User Scenarios & Testing

### Primary — a mission's shape is a stored value, resolved once
At `mission create`, the mission's `MissionTopology` is recorded in `meta.json`. Every later
read/write resolves the surface by calling `resolve_context_for_mission(mission_id,
stored_topology)` and reading the returned `ExecutionContext` — no command re-infers the shape
from `coordination_branch is None`, `lanes.json` presence, or a worktree `stat`.

### Primary — a flattened mission never reads a stale coord worktree (#2062, structural)
A mission flattened mid-flight (its `meta.json` topology is now `SINGLE_BRANCH`/`LANES`, with a
`flattened` provenance flag) with a stale `-coord` worktree still on disk resolves its status
from the **PRIMARY** surface on **all read legs** for **every** handle form (`<slug>-<mid8>`,
bare-mid8, full ULID, bare human slug) — because the **stored** topology drives the read path,
so the on-disk husk is structurally irrelevant. The dep-gate, kanban, and review-claim never
report a stale `planned` lane.

### Primary — planning artifacts read back from the surface they were written to (#2063)
An operator runs `/spec-kitty.specify` then `/spec-kitty.tasks` on a coord-topology mission.
`spec.md` is committed through the seam-resolved placement and lands on the surface the next
command reads. `/tasks` and `finalize-tasks --validate-only` both see `spec.md` and the WP
files — no "spec.md not found" / "Tasks directory not found" divergence.

### Primary — requirement coverage agrees across commands (#2064)
`map-requirements` (reports full coverage) and the following `finalize-tasks --validate-only`
read and write WP `requirement_refs` through the same seam-resolved surface, so finalize
reports **zero** `unmapped_functional_requirements` — the two commands never disagree about
where the WP frontmatter lives.

### Exception / edge cases
- **create→first-write window** (topology `COORD`/`LANES_WITH_COORD` declared, coord worktree
  not yet materialized) still resolves PRIMARY on every leg — the #1718 contract is preserved
  (regression-guarded). The stored topology says "coord", but the transient not-yet-materialized
  state is discriminated by the existing probe, NOT by the enum.
- **coord-deleted** (declared coord branch deleted from git) still hard-fails
  `CoordinationBranchDeleted` (#1848 data-loss carve-out) — unchanged. These transient
  on-disk×git states are **orthogonal to the 4 enum cells** and are NOT subsumed by stored
  topology (C-006).
- **Legacy / no-`mid8` / no-`topology` missions** are backfilled once; until backfilled, the
  shell falls back to the legacy derivation exactly once to *compute and persist* the topology,
  then reads the stored value (FR-003).

## Functional Requirements

### A. Topology SSOT seam — the foundation (lands first, #2069)

| ID | Requirement | Status |
| --- | --- | --- |
| FR-001 | **`MissionTopology` enum.** Add a mission-level enum `MissionTopology {SINGLE_BRANCH, LANES, COORD, LANES_WITH_COORD}` in `src/mission_runtime/context.py`, naming the orthogonal **coordination × lanes** 2×2 grid as one value. `FLATTENED` is NOT an enum member — it is a separate historical/metadata flag (provenance), never a shape value. The enum is the single place the lanes-vs-coord cross-product is named. | proposed |
| FR-002 | **Store the topology in `meta.json`.** `topology` MUST be minted into `meta.json` at `mission create` (`src/specify_cli/core/mission_creation.py`) and READ thereafter — never re-inferred from disk/git at resolve time. The stored value is authoritative; a `flattened` provenance flag records history without changing the shape value. | proposed |
| FR-003 | **Backfill legacy missions once.** Add `spec-kitty migrate backfill-topology` (mirroring the `backfill-identity` precedent) that computes each legacy mission's topology from the current signals and PERSISTS it to `meta.json`, plus a `spec-kitty doctor topology --json` audit. **Sequencing landmine (dogfooding):** THIS mission's own `meta.json` MUST be backfilled with its `topology` BEFORE any caller reads the stored field. Until a mission is backfilled, the shell computes-and-persists the topology exactly once via the legacy derivation, then reads the stored value. | proposed |
| FR-004 | **Pure `resolve_context_for_mission` SSOT resolver + retire BOTH live derivations.** Add `resolve_context_for_mission(mission_id: str, topology: MissionTopology) -> ExecutionContext` on the canonical `mission_runtime` seam as a **PURE** projection over the existing single construction door `build_execution_context` (functional core / imperative shell): it performs NO filesystem or git I/O; the shell parses/persists `meta.json` and passes `id + topology`. `topology` is an authoritative input (optional input-assertion: fail-closed on a supplied-vs-resolved mismatch). Retirement MUST cover **BOTH** hand-rolled `coordination_branch is None ⇒ FLATTENED` derivations: (a) `_resolve_coordination_branch` / `resolution.py:705-718` (behind the door); AND (b) the **second, independent** ladder in `src/runtime/next/runtime_bridge.py:144-211` (`_mission_declares_coordination_branch` + the `_coord_path.exists() ⇒ COORDINATION` branch — keying on the disk-`stat` signal C-004 forbids). Leaving EITHER alive is the parallel-inference death-spiral; both route through the stored topology under the same NFR-001 live proof. | proposed |
| FR-005 | **Introduce `routes_through_coordination` + route the 9 decision sites.** Add a `MissionTopology`-derived per-ref predicate `routes_through_coordination(target)` and re-express the **9** `.kind is COORDINATION` branch-decision sites (`coordination/commit_router.py:118,193`, `cli/commands/implement.py:604`, `cli/commands/agent/mission.py:776,858`, `cli/commands/agent/tasks.py:359`, `orchestrator_api/commands.py:1283`, `missions/_substantive.py:379`, `mission_runtime/artifacts.py:50`) against it — so no site re-infers the per-ref topology. The `CommitTargetKind` **TYPE itself is NOT deleted in this mission**: its ~143 value-literal references (≈63 constructions + ≈24 imports + ≈56 test refs, 41 files) are behavior-neutral and CARVED to Mission B (C-007). This mission stops *reading* `.kind` for decisions, leaving the constructor field vestigial until Mission B eradicates the type. | proposed |

### B. Structural surface-coherence adoption (closes #2062/#2063/#2064 at the root)

| ID | Requirement | Status |
| --- | --- | --- |
| FR-006 | **Read path consults the STORED topology (structural #2062).** `missions/_read_path_resolver._resolve_existing_for_slug` (and the read-path legs it feeds) MUST resolve the surface from the seam / stored topology, so `CoordState.MATERIALIZED` (a disk `stat`) is NO LONGER the deciding signal. A mission whose stored topology is `SINGLE_BRANCH`/`LANES` resolves PRIMARY regardless of a stale `-coord` husk on disk. This REPLACES the prior declared-coord band-aid: the on-disk husk is structurally not consulted, so #2062 cannot re-open (C-004). The stale `:263` comment ("No branch is supplied here") documenting the defect as intentional MUST be corrected/removed. **This coverage is NOT limited to `_read_path_resolver`: ALL read-surface resolvers that feed the `ExecutionContext` status fragment MUST likewise classify the surface from the stored topology, never from a fresh `coordination_branch is None` re-inference — specifically `coordination/surface_resolver.resolve_status_surface_with_anchor` (`:600`, consumed by `_assemble_core_fragments` → `StatusSurfaceFragment`) and `coordination/status_transition._read_contract_from_transaction_target` (`:558`). Both keep `probe_coord_state` ONLY for the C-006 transient discrimination (DELETED hard-fail / EMPTY loud-primary), so SC-001's zero-live-inference-sites grep is genuinely satisfied and the whole resolved `ExecutionContext` (placement AND status fragments) derives from one stored authority — no parallel surface derivation survives.** | proposed |
| FR-007 | **Single write-surface authority.** Every planning-phase artifact commit (`spec.md`, `plan.md`, `tasks/`, WP `requirement_refs` frontmatter, lifecycle status events) MUST resolve its write destination through the seam (`resolve_context_for_mission` placement projection). No planning command may resolve a write target from the current `HEAD` branch independently (`safe-commit._resolve_commit_target` is the #2063 root). `safe-commit`'s two responsibilities are SEPARATED: mission-aware planning commits resolve via the seam; generic operator-file commits keep their existing behavior (NFR-002). | proposed |
| FR-008 | **`map-requirements` and `finalize-tasks` share one WP-frontmatter surface.** Both commands MUST read/write WP `requirement_refs` through the SAME seam-resolved surface (honoring the documented invariant: planning INPUT artifacts authored on PRIMARY, staged to coord at commit-time). A successful `map-requirements` MUST be visible to the immediately-following `finalize-tasks --validate-only` (zero `unmapped_functional_requirements`). The READ surface (`map-requirements`' `read_all_wp_requirement_refs` vs finalize's own dir resolution) MUST be consolidated to one place; `compute_coverage` is already single-source — do NOT chase the coverage math. | proposed |
| FR-009 | **Status-event emission resolves its write surface from the seam.** Every `status.emit.emit_status_transition` call site MUST pass a `feature_dir` resolved by the seam, not an ad-hoc per-caller path — so dep-gate / kanban / review-claim status reads and `move-task` writes converge on one surface (the #2062 status-read leg). | proposed |
| FR-010 | **Differential gate: stored-topology equivalence + retained on-disk legs.** `tests/missions/test_surface_resolution_equivalence.py` MUST (a) add a **pure** input→output cell feeding `(mission_id, topology)` for all four `MissionTopology` values and asserting the returned `ExecutionContext` surface fields; AND (b) RETAIN the on-disk `flattened-stale-coord` topology × every handle form (primary meta `SINGLE_BRANCH`/`LANES` + a stale `-coord` worktree on disk) asserting all legs return PRIMARY — until those legs are deleted. The existing `type(a) is type(b)` AND `error_code` assertion MUST NOT be weakened. The pure cell is an ADDITIONAL proof, never a REPLACEMENT for the live on-disk proof (C-002, NFR-001). | proposed |
| FR-011 | **(Campsite #1970) Collapse `is_committed` 3-leg OR.** Once the read/write surface is structurally single (FR-006/FR-007 via stored topology), `missions/_substantive.is_committed` (`:317-412`) MUST reduce from a 3-surface OR to a single-surface check on the resolved placement ref; the multi-surface diagnostics workaround is removed. Gated on the FR-010 live convergence proof (NFR-001/C-002) — the 3-leg OR is a load-bearing workaround for the surface split and must not be collapsed before the split is structurally gone. | proposed |

## Non-Functional Requirements

| ID | Requirement | Status |
| --- | --- | --- |
| NFR-001 | **Live-evidence convergence proof.** The write/read convergence MUST be proven on a REAL flattened-mid-flight mission repro (the #2062 topology), not by static reading and not solely by the FR-010 pure cell. The differential equivalence gate (incl. the on-disk `flattened-stale-coord` row) MUST be green at every WP boundary. #2062 is NOT marked fixed without a witnessed live repro. | proposed |
| NFR-002 | **No regression of generic `safe-commit`.** `safe-commit`'s legitimate non-mission operator-file commit path MUST remain functional and tested (the two responsibilities are separated, not overloaded). | proposed |
| NFR-003 | **Behavior-preserving adoption.** The seam adoption (FR-006/FR-007/FR-009) and the `CommitTargetKind` derivation (FR-005) are behavior-preserving for already-correct topologies (coord-fresh, create-window, single-branch, coord-deleted) — proven by the equivalence gate + the preserved #1718/#1848 guards. | proposed |
| NFR-004 | **Clean static analysis.** All new/changed code passes `ruff` and `mypy` with zero issues/warnings; cyclomatic complexity ≤15; repeated non-trivial literals hoisted (no new S1192). No suppression added to pass. | proposed |
| NFR-005 | **Resolver isolation.** `resolve_context_for_mission` MUST be unit-testable with zero filesystem/git fixtures — feed `(mission_id, topology)`, assert the returned `ExecutionContext` fields. Any FS/git access lives in the imperative shell, never in the resolver. | proposed |

## Constraints

| ID | Constraint | Status |
| --- | --- | --- |
| C-001 | **#1970 campsite-cleaning stays ACTIVE (opportunistic).** Adjacent debt on a touched surface is remediated in-slice, bounded to mission goals — never deferred with "pre-existing, out of scope" for lines this mission actually edits. **NOTE:** the *named* de-godding extractions (doctor coord-recovery cluster #2059 → `_coord_recovery.py`; `mission.py` placement/commit helpers #2056 → `commit_router.py`) and the cheap fold tickets (#2066/#1891/#2037/#2048) were CARVED to the block-C follow-up mission — they are NOT in this mission's scope; only opportunistic cleanup of touched lines applies here. | active |
| C-002 | **No close-on-static for #2062.** #2062 stays OPEN until a live flattened-mission repro witnesses all read legs resolving PRIMARY. The FR-010 pure cell ADDS a proof; it does NOT replace the live repro. | active |
| C-003 | **Project over the door, do not rebuild.** `resolve_context_for_mission` MUST be a thin projection over the existing `build_execution_context` construction door (the way `resolve_placement_only` already is — "one authority, two projections"). Do NOT introduce a parallel resolver that re-reads `meta.json`/`lanes.json`/git independently. | active |
| C-004 | **Structural, not symptomatic (binding).** The #2062/#2063/#2064 fix MUST be structural: the read path consults the STORED topology, never re-inferring the shape from on-disk worktree existence. If storing the topology would re-open #2062, that proves a prior fix was a symptom patch — the resolution is to make the read path stop inferring from disk, NOT to re-add a band-aid. | active |
| C-005 | **Linearize shared anchors.** `mission_runtime/context.py` (enum), `mission_runtime/resolution.py` (seam + derivation retirement), `missions/_read_path_resolver.py` (read leg), `core/mission_creation.py` (mint), and `cli/commands/agent/mission.py` (write path) are shared surfaces — land them on a linearized chain before the disjoint lanes; expected refactor overlap. | active |
| C-006 | **Transient on-disk×git states are NOT subsumed by the enum.** The create-window (#1718, topology=COORD but worktree not yet materialized) and coord-deleted (#1848, declared branch gone) states are orthogonal to the 4 enum cells and MUST stay discriminated by the existing probe (`probe_coord_state` with the branch signal) — the stored topology does not replace them. Preserve `CoordAuthorityUnavailable` / typed errors / `CoordinationBranchDeleted` and the #2065 read-side contract intact. | active |
| C-007 | **Scope split — Mission B carve (confirmed, behavior-neutral, alphonso-sized).** Mission B = (a) `CommitTargetKind` TYPE eradication — the ~143 value-literal references (≈63 constructions + ≈24 imports + ≈56 test refs across 41 files); and (b) richer-API adoption of `resolve_context_for_mission` at the **14** real call sites of `resolve_placement_only`/`resolve_action_context`. Both are BEHAVIOR-NEUTRAL: the 14 call sites pass identity handles (NOT topology) and become correct UNCHANGED once THIS mission retires the two derivations (FR-004); migrating them to the topology-explicit API is incremental adoption over an already-correct door (the #2065 read-side strangler pattern), with zero correctness gain — a principled carve, not duct-tape. THIS mission closes the death spiral entirely (both live derivations + all 9 decision sites + the two status-surface re-inference sites on stored topology); Mission B is pure cleanup + richer-API uptake. **Mission B = tracker #2070** (created 2026-06-22, behavior-neutral, blocked-by this mission's landing). **Randy-reducer note (research, 2026-06-22):** post-mission `CommitTargetKind.FLATTENED` is provably a write-only dead value — zero live `is/== FLATTENED` decision reads remain (produced at `runtime_bridge.py:211`, `resolution.py:716`, `upgrade.py:214`, consumed by no decision). Mission B SHOULD eradicate the member with that evidence — but FIRST verify no string-literal `"flattened"` serialization consumer (meta.json / event readers) string-matches it, before removal. | active |
| C-008 | **Block-C carve.** The independent verb/guard/de-godding/doctrine/campsite-fold work (the real `worktree repair` verb #1890, the command-reference guard #2008, the #2059/#2056 de-godding extractions, the charter-prompt `safe-commit`→`spec-commit` migration, and folds #2066/#1891/#2037/#2048) is a SEPARATE follow-up mission. It is NOT in this mission's scope; a carve ticket is created when this mission's spec is final. | active |
| C-009 | **No version prescription.** The PO assigns release/patch numbers at release time; frame work as focus/milestone, not a version. | active |

## Success Criteria

- **SC-001** `MissionTopology` exists as a stored `meta.json` value (minted at create,
  backfilled for legacy via `migrate backfill-topology`); no resolve-time path re-infers the
  shape from `coordination_branch is None` or a worktree `stat` — the `resolution.py:705-718`
  derivation, the `runtime_bridge.py:144-211` ladder, **and the two status-surface re-inference
  sites `surface_resolver.py:600` + `status_transition.py:558`** are all retired (a `grep` for the
  `coordination_branch is None` / `_coord_path.exists()` inference pattern finds zero live decision
  sites — the only surviving `coordination_branch`/`coord_branch is None` reads are the C-006
  transient-discrimination arms, not topology/surface decisions).
- **SC-002** `resolve_context_for_mission(mission_id, topology)` returns a correct
  `ExecutionContext` for all four topology values in a **pure** unit test with **zero** FS/git
  fixtures (NFR-005), and is a projection over `build_execution_context` (no parallel resolver — C-003).
- **SC-003** A flattened mission with a stale `-coord` worktree resolves status from the PRIMARY
  surface on **all read legs × all 4 handle forms** (witnessed live; #2062), because the stored
  topology drives the read path (C-004). "All read legs" includes the `_read_path_resolver` leg,
  the `surface_resolver.resolve_status_surface_with_anchor` leg, and the `status_transition`
  read-contract leg — all three derive from the stored topology, not a parallel `coordination_branch
  is None` inference.
- **SC-004** For a coord-topology mission, `spec.md` committed through the planning flow is
  visible to the immediately-following `/spec-kitty.tasks` and `finalize-tasks --validate-only`
  reads — no "spec.md not found" divergence (#2063, witnessed).
- **SC-005** After `map-requirements` reports full coverage, `finalize-tasks --validate-only`
  reports **zero** `unmapped_functional_requirements` for the same mission (#2064, witnessed).
- **SC-006** All **9** `.kind is COORDINATION` decision sites route through the
  `routes_through_coordination(target)` predicate (no site reads `.kind` to decide); the
  `CommitTargetKind` type itself is left vestigial (eradication is Mission B). The differential
  gate includes both the pure stored-topology cell and the on-disk `flattened-stale-coord` row,
  with the type+error_code assertion unweakened.
- **SC-007** `is_committed` is reduced to a single-surface check; the full test suite is green
  including the preserved #1718/#1848 guards (NFR-003); the Mission-B carve ticket (#2070) exists
  (the block-C carve ticket is created when its scope is sliced).

## Key Entities

- **MissionTopology** — `src/mission_runtime/context.py`; the stored 4-cell mission-shape enum.
- **`topology` (meta.json field)** — the stored, authoritative shape value (+ `flattened`
  provenance flag).
- **`resolve_context_for_mission`** — the pure SSOT resolver projecting `build_execution_context`.
- **ExecutionContext / ActionContext** — `context.py:177`; the returned op-composite VO.
- **`routes_through_coordination(target)`** — the new `MissionTopology`-derived per-ref predicate
  the 9 decision sites adopt; replaces `.kind is COORDINATION` reads. The `CommitTargetKind` type
  itself survives (vestigial) until Mission B eradicates it.
- **Differential equivalence gate** — `test_surface_resolution_equivalence.py`; extended with the
  pure stored-topology cell + the retained on-disk flattened-stale-coord row.

## Assumptions

- `build_execution_context` / `_assemble_core_fragments` is genuinely the single construction
  door (verified by mission `01KVGCE8`/`01KVN754`); `resolve_context_for_mission` projects it,
  it does not redesign it.
- The four `MissionTopology` cells exhaustively cover the coord×lanes grid; FLATTENED is
  representable as `SINGLE_BRANCH`/`LANES` + a provenance flag without information loss.
- The transient create-window (#1718) and coord-deleted (#1848) states require a probe the
  stored topology does not encode — they remain the probe's responsibility (C-006).
- The PR-bound coordination topology of THIS mission is itself a dogfooding hazard for the exact
  bugs under fix; its `meta.json` MUST be topology-backfilled before any caller reads the field
  (FR-003) — flatten/coord-friction is expected during implement (carry NFR-001).

## Issue Matrix References

#2069 (design driver — MissionTopology seam, goes first), #1716 (single surface authority epic
facet), #2062 (read-path leg — OPEN, no close without live repro; closed STRUCTURALLY here),
#2063, #2064, #2007 (parent epic), #1619 (execution-context epic), #1970 (campsite directive —
process reference). **Carved to Mission B — tracker #2070 (C-007):** `CommitTargetKind` TYPE eradication (~143
value-literal refs / 41 files) + richer-API `resolve_context_for_mission` adoption at the 14
real `resolve_placement_only`/`resolve_action_context` call sites (behavior-neutral; alphonso-sized).
**Carved to the block-C follow-up mission (C-008):** #1890 (worktree-repair verb), #2008
(command-reference guard), #2059 (doctor coord-recovery de-godding), #2056 (mission.py
placement/commit de-godding), the charter-prompt `safe-commit`→`spec-commit` migration, and the
cheap folds #2066/#1891/#2037/#2048. **Explicitly left out** (own efforts): #1357 (lock redesign),
#2049 (broad audit), #1887 (merge path), #2031, the full `doctor.py`/`mission.py`/`tasks.py`
decompositions, the v3.3 `--to-branch` / `next/` shim deprecations (not due at 3.2.x).
