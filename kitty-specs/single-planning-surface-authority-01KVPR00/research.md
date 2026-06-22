# Research: MissionTopology SSOT + structural planning-surface coherence

Phase 0 decisions. This mission was **revised twice** after its first (band-aid) draft. The
revised design was driven by design ticket **#2069** and a 3-agent revision-mapping squad
(architect-alphonso / paula-patterns / debugger-debbie), then a follow-on alphonso sizing pass.
This record SUPERSEDES the original band-aid Phase-0 decisions.

## Lineage — why the design changed

The original mission *adopted* the existing write authority (`resolve_placement_only`) and
*band-aided* the read path (thread a `declares_coordination` signal into a disk-`stat`
heuristic). Design ticket #2069 proposed the structural alternative: name + STORE the mission
topology and resolve it once through a pure projection. The operator ruled **the new design
lands first**.

debbie (live-code) initially flagged a "re-opens #2062" trap (the enum excludes `FLATTENED`,
and the husk-trust read leg is upstream of the pure resolver). **The operator overrode this on
principle** (D-2): *"if storing topology re-opens #2062, that proves our prior #2062 fix was
non-structural."* The structural answer is to make the read path consult the **stored** topology
so the disk-`stat` husk is never the deciding signal.

## D-1 — New design first: store the topology, resolve once, pure (#2069)
- **Decision**: Add `MissionTopology {SINGLE_BRANCH, LANES, COORD, LANES_WITH_COORD}`, STORE it
  in `meta.json` (read, never re-inferred), and add a PURE
  `resolve_context_for_mission(mission_id, topology) -> ExecutionContext` projection over the
  existing `build_execution_context` door. Backfill legacy once (`migrate backfill-topology`).
- **Rationale**: a stored shape is parseable even after interruption / LLM tool-switch; the pure
  resolver is isolated-testable (feed id+topology, assert fields); one door (C-003), not a parallel
  resolver. Operator: STORE over derive (no inference); `FLATTENED` is a provenance flag, not a value.
- **Alternatives**: (a) derive-and-carry per call (ticket's original lean) — rejected (recomputes
  per call, drift vector); (b) a new unified resolver — rejected (C-003); (c) the original
  adopt+band-aid plan — superseded (symptomatic, D-2).

## D-2 — Structural, not symptomatic (binding operator principle, C-004)
- **Decision**: the #2062/#2063/#2064 fix is the read path consulting the STORED topology, never
  re-inferring shape from on-disk worktree existence.
- **Rationale**: a fix a stored-topology design can re-open was never structural. The band-aid
  (declares-coord threaded into a `stat` heuristic) treated the symptom; the structural fix removes
  disk-`stat` as a topology signal entirely.
- **Alternatives**: the declares-coordination gate (original D-2) — rejected as a symptom patch.

## D-3 — CommitTargetKind: predicate over the 9 decision sites; type eradication carved (#2070)
- **Decision (FR-005)**: introduce `routes_through_coordination(target)` (a `MissionTopology`-derived
  per-ref predicate) and route the **9** `.kind is COORDINATION` decision sites through it. The
  `CommitTargetKind` TYPE is left vestigial; its ~143 value-literal references eradication carves to
  Mission B (#2070).
- **Rationale (alphonso sizing)**: all 9 sites are trivial binary `is COORDINATION` reads (no
  three-way dispatch), all on touched surfaces — folding is cheap and avoids a new split-brain. The
  ~143 value-literal refs are not topology decisions (a constructor with an explicit kind can't drift),
  so carving them is principled cleanup.
- **Alternatives**: (a) delete the whole type in-mission — rejected (41-file churn, balloons a focused
  mission, zero correctness gain); (b) leave the 9 sites on the old enum — rejected (new split-brain).

## D-4 — Universal resolver adoption carved with a good reason (Mission B #2070)
- **Decision (C-007)**: the 14 real call sites of `resolve_placement_only`/`resolve_action_context`
  migrate to the topology-explicit API in Mission B, not here.
- **Rationale (alphonso)**: those call sites pass identity handles, not topology — they become correct
  UNCHANGED once this mission retires the two derivations. Migrating them is incremental adoption of a
  richer API over an ALREADY-CORRECT door (the #2065 read-side strangler pattern), behavior-neutral,
  zero correctness gain from folding. This is the operator's requested "good reason" to carve.

## D-5 — The runtime_bridge derivation gap is folded IN (alphonso scope-find, FR-004)
- **Decision**: retirement covers BOTH live `coordination_branch is None ⇒ FLATTENED` derivations —
  `resolution.py:705-718` AND the independent `runtime_bridge.py:144-211` ladder.
- **Rationale**: `runtime_bridge` is a second, hand-rolled inference keying on `_coord_path.exists()`
  (the disk-`stat` signal C-004 forbids), NOT behind the door. Leaving it is exactly the
  parallel-inference death-spiral; the original FR set named only `:705-718`. Folded in, gated under
  NFR-001 live proof.

## D-6 — Carve the independent block C to its own follow-up mission (C-008)
- **Decision**: the real `worktree repair` verb (#1890), the command-reference guard (#2008), the
  doctor/`mission.py` de-godding extractions (#2059/#2056), the charter-prompt migration, and the cheap
  folds (#2066/#1891/#2037/#2048) are a separate follow-up — NOT in this scope.
- **Rationale (operator)**: keep THIS mission a focused seam + structural fix; mixing a de-godding /
  verb / guard sweep into a behavioral refactor produces an un-reviewable diff and accidental-pass risk
  (cf. the tests-as-friction theory).

## D-7 — Transient on-disk×git states stay probe-discriminated (C-006)
- **Decision**: the create-window (#1718) and coord-deleted (#1848) states are orthogonal to the 4 enum
  cells and remain discriminated by `probe_coord_state` (with the branch signal); the stored topology
  does NOT subsume them.
- **Rationale (debbie)**: these are transient states, not shapes — `LANES_WITH_COORD` can be in any of
  MATERIALIZED/EMPTY/UNMATERIALIZED/DELETED at an instant. Collapsing them into the enum would regress
  #1718/#1848 (data-loss carve-out).

## D-8 — `is_committed` collapse is gated, not eager (FR-011)
- **Decision**: collapse the 3-leg OR to a single-surface check ONLY after the surface is structurally
  single (FR-006/FR-007 via stored topology) AND a live flattened-mission repro is green (NFR-001).
- **Rationale**: the 3-leg OR is a load-bearing workaround for the surface split; collapsing before
  convergence is proven would regress live missions mid-flight (live-evidence rule).

## Test-design note (tests-as-friction theory)
The differential gate's pure cell is a *weaker* proof than the live on-disk repro (debbie): a pure
input→output test can pass without exercising the disk-`stat` husk leg. FR-010 therefore KEEPS the live
on-disk row alongside the pure cell, and NFR-001/C-002 forbid close-on-static for #2062. New tests in
this mission assert contracts (not implementation details), avoid monkey-patch/accidental-pass, and
prefer real two-command/live sequences over tautological mocks.

## Open items
- None requiring a decision marker. All scope is pre-decided; #2062 carries C-002 (no close without
  live repro) — an acceptance constraint, not an open question.
