# Contract — Gate Execution Context

**Discharges**: FR-001, NFR-001, NFR-003, C-004
**Consumers**: acceptance negative-invariant gate, consolidation readiness preview gate, post-consolidation verification

This is a behavioural contract. It states what must be observably true, not which functions
exist. Tests written against it must assert behaviour on realistic fixtures (NFR-008).

---

## C1 — A gate judges the surface it was handed, not an ambient one

*Rewritten 2026-07-23. The prior form asserted "does not construct one from `repo_root`/cwd",
whose stated signal was a single-construction-site source scan — a code-shape assertion that
NFR-008 forbids, and one a gate constructing an identical context would pass anyway.*

**Given** a gate handed a context whose `surface` is a directory distinct from **both**
`repo_root` and the process working directory
**And** all three locations hold **different** seeded answers
**When** the gate runs
**Then** the verdict reflects the answer seeded at `context.surface`.

*Why this is stronger*: it kills the ambient-derivation mutant behaviourally, and it is
refactor-stable. Prior art to reuse rather than reinvent: the decoy-marker idiom in
`tests/integration/coord_topology_fixture.py` (a distinct marker seeded on the primary copy so a
wrong-leg read returns a wrong *value*, not merely a wrong path), and
`test_placement_partition_golden_path.py::test_cwd_independence_resolves_identical_authority`
for the cwd leg — already parametrised over coord and `SINGLE_BRANCH`, unpatched, with a
non-vacuity assertion.

---

## C2 — Refuse when the surface cannot hold the fact

**Given** a gate whose subject cannot exist in `context.surface` at `context.phase`
**When** it runs
**Then** it returns a distinguishable *cannot-evaluate* outcome naming the reason
**And** it returns neither a pass nor a fail.

*Failure this prevents*: an invariant asserting a file the mission adds, checked at `ACCEPT`
against the pre-consolidation primary surface, reported as violated.

---

## C3 — Four declared states, four declared answers

**Corrected twice.** The first form said "cannot be resolved → raises", collapsing distinct
states. The second form (2026-07-23) modelled **three** and omitted `EMPTY` — but the live
classifier `CoordState` (`missions/_read_path_resolver.py:278-281`) enumerates **four**
non-`NONE` states, and the data model, NFR-001 and the gate all reference four. Because this
contract is the behavioural test spec, an omitted state ships **untested**. All four below.

**Given** a mission declaring a coordination home whose branch is **absent from git** (DELETED)
**When** a gate builds a context for that kind
**Then** it raises `CoordinationBranchDeleted` (`error_code = "COORDINATION_BRANCH_DELETED"`)
**And** it does **not** read from the primary surface instead.

**Given** a mission declaring a coordination home whose branch **exists in git but whose worktree
is not yet materialised** (UNMATERIALIZED — the #1718 create-window)
**When** a gate builds a context for that kind
**Then** it resolves the primary mission directory **affirmatively**
**And** stamps `surface_kind = PRIMARY` on the verdict (C6)
**And** does **not** raise — this is a declared answer for that state, not a degradation.

**Given** a coordination worktree root that exists but whose mission directory is **absent**
(EMPTY — #1716)
**When** a gate builds a context for that kind
**Then** it resolves the primary mission directory **affirmatively** and stamps
`surface_kind = PRIMARY`
**And** does **not** raise, but this stamp is load-bearing: EMPTY is the split-brain-risk state
(#1589/#1821), so a gate judging a COORD-homed kind against this stamped-PRIMARY surface must
return cannot-evaluate (GEC-5 / C2), never a verdict.

*Reconciling the "one declared answer" rule with EMPTY's pinned topology-dependent behaviour.*
The live resolver (`surface_resolver.py`) treats EMPTY differently by topology: a solo (no-lanes)
coord mission gets a **quiet** primary fallback (the write self-materializes the worktree,
#2533 / WP08 T029-T031), while a `LANES_WITH_COORD` mission gets a **loud** primary fallback with
`_COORD_EMPTY_FALLBACK_WARNING` (pinned by WP08 T031, which NFR-004 forbids modifying). This does
**not** violate the one-answer rule and does **not** re-introduce topology-conditioning (C-004):
the *answer* is the same in both — resolve primary, stamp PRIMARY, GEC-5 governs the gate — and
the loud/quiet difference is **warning verbosity in the underlying resolver**, a diagnostic
concern orthogonal to the gate's verdict. The gate-execution-context layer must consume that
existing behaviour, not re-derive it, and must not condition its own verdict on which topology
produced the EMPTY. (This is the same reconciliation the UNMATERIALIZED correction made, one state
over — flagged by the second independent review so the collision is not repeated.)
*Note the live doc-level contradiction this contract must not inherit*: `CoordState`'s own
docstring calls EMPTY *"a fail-closed condition, never a silent primary fallback"*
(`_read_path_resolver.py:265-266`) while its consumer (`surface_resolver.py`) implements a **loud
primary fallback** (ADR 2026-06-19-1). The mission resolves this in favour of resolve-primary-and-
stamp, with GEC-5 supplying the fail-closed behaviour at the *consumer* (the gate refuses) rather
than at the resolver.

**Given** a materialised coordination worktree
**When** a gate builds a context
**Then** it resolves the coordination surface and stamps `surface_kind = COORD`.

*Relationship to NFR-001.* "No silent substitution" is satisfied because each of the four states
has a **declared** answer that the verdict names. What NFR-001 forbids is an *undeclared* fallback
— reading somewhere the caller never asked for and not saying so. Resolving UNMATERIALIZED or
EMPTY to primary and stamping it is declared and visible; that is the difference.

*This is what resolver totality means in practice*: four states, four defined answers, consuming
the existing `CoordState` classifier rather than a new one, and `None` retained for nothing.

---

## C4 — Total resolution, observed through the stamp

*Rewritten 2026-07-23. Two of the three original clauses ("not expressed as a `None`-fallback",
"no branch reads `flattened`") were assertions about source text, not behaviour.*

**Given** a mission on flat / `SINGLE_BRANCH` / `LANES` topology
**When** a home is resolved for any artifact kind
**Then** the primary mission directory is returned **affirmatively** as that topology's declared
home
**And** the resulting context carries `surface_kind = PRIMARY` (observed via C6's stamp, not by
reading the resolver's source).

*The two source-shape properties move to mission negative invariants*, where scoped
`grep_absence` over `src/specify_cli/acceptance/` and `src/mission_runtime/` is the right
instrument and is judgeable pre-consolidation (provenance contract C9): **no `None`-as-fallback
in home resolution**, and **no new read of the `flattened` flag**. That is the refactor-stable
negative form, rather than a positive assertion about how the code is written.

---

## C5 — Ref agreement

**Given** a context whose `surface` is not at `ref`
**When** a gate runs against it
**Then** it raises rather than judging.

---

## C6 — Every verdict names its surface

**Given** any gate verdict or recorded judgement
**When** it is emitted, recorded, or rendered in JSON output
**Then** it carries a resolvable identifier of the surface and ref it was derived from.

---

## C7 — Topology neutrality

**Given** the identical defect condition on a coordination mission and on a flat mission
**When** the gate runs in each
**Then** both produce the same outcome.

*Failure this prevents*: a coord-named fix that leaves the flat case broken. #1834 reproduces
on both.

---

## Non-goals

- Does not change which gates exist or when they run.
- Does not migrate `review/pre_review_gate.py` — explicitly out of scope this mission (see
  `research/sibling-mission-coordination.md`).
- Does not remove `flattened` from the codebase; only forbids **new** dependence on it.
