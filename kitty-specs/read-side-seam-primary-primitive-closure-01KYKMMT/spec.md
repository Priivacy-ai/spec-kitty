# Mission Specification: Read-Side Seam: Placement-Authority Closure

**Mission Branch**: `fix/read-side-seam-primary-primitive-closure`
**Created**: 2026-07-28 · **Re-framed twice** (see Provenance)
**Slug/branch note**: the mission slug and branch are frozen at creation (`…primary-primitive-closure`); the title reflects the re-framed scope, of which closing that primitive is one part. Slug is immutable identity and is not renamed.
**Status**: Draft
**Input**: Close the #3013 residuals (#2886, #2824 comment) and discharge #3014 honestly — then **move the placement decision out of the call sites and into the resolver** for the last holdout primitive, via delegate-then-remove.

## Context & Motivation

Mission artifacts live on the **PRIMARY** partition (planning/metadata) or the
**COORD** partition (lifecycle surfaces on a coordination branch). The governing
principle:

> **Only the resolver decides *where* an artifact kind is routed, based on the chosen
> topology. A caller declares only *what* it is reading (the kind).**

`placement_seam(...).read_dir(kind)` is that resolver, and it is already the house
style — **88 compliant call sites**. Three leaf primitives remain where the caller
still decides *where*:

| Primitive | Shape | Live sites | Policed by |
|---|---|---|---|
| `primary_feature_dir_for_mission` | caller picks PRIMARY | **34 in scope** | handle-hygiene floors only |
| `candidate_feature_dir_for_mission` / `resolve_planning_read_dir` | caller picks "whatever topology says" | censused | read-side gate |
| `resolve_feature_dir_for_mission` | kind-blind, topology-routed | **8** | **nothing** |

### What the audit established (empirical, on `e97fc6ab9`)

1. **`primary_feature_dir_for_mission`'s 34 sites are semi-compliant, not compliant.**
   They pass a canonical *handle* — which is all the anchoring floors check
   (`CanonicalizerSite.is_canonical` = "was the handle folded") — while **hardcoding
   the partition at the call site**. Handle hygiene is not placement authority.
2. **The seam is answer-equivalent, and strictly better on one cell.** Across eight
   real-repo fixtures the blind composition and `read_dir(<PRIMARY kind>)` return the
   same path for flat, coord-materialized, coord-**husk**, deleted-coord, empty-coord,
   absent-mission and lane-worktree cases. On a **backfilled** mission (bare `<slug>`
   primary, composed `<slug>-<mid8>` coord) the blind composition returns a path that
   **does not exist** while the seam recovers it. Structurally guaranteed:
   `declared_read_surface` short-circuits to PRIMARY for any primary kind *before any
   coord probe*.
3. **The 33 compositions are hand-inlined resolver internals.** (34 sites are in scope: 33 semi-compliant compositions discharged by the migration, plus **one non-compliant site** — `status/aggregate.py:522` — discharged by FR-001, not by the 33 mechanical edits.)
   `resolve_planning_read_dir`'s PRIMARY leg *is* that composition verbatim — so the
   sites are not choosing a different answer, they are duplicating the resolver's body
   and keeping the decision in the caller.
4. **The six "the coord-aware resolver lands on the husk" comments do not survive.**
   They argue against the *kind-blind topology-routed* resolver; the fixtures show the
   *kind-aware seam* does not have those properties. Same defect class as #2824's
   comment: arguing against resolver A to justify not using resolver B.
5. **The census floors are bookkeeping, with in-tree precedent.** A prior WP routed
   exactly this composition onto `read_dir(...)` and lowered the floor 45→44, recorded
   as *"a genuine routing shrink, not a re-pin"*; five such shrinks are on record, and
   the doctrine is to record the honest before/after. **No test asserts the primitive
   must keep being used.**
6. **Two live gate holes.** `status/aggregate.py:522` passes a handle from a
   canonicalizer absent from the gate's fold set — neither routed nor allowlisted,
   passing by omission; and `test_gate_read_literal_ban.py`'s three allow-sets bless
   only the *blind* primitive, so migrated sites would silently stop being checked
   (**green-by-omission**).

### Method: delegate, then remove *(operator-prescribed)*

- **Step 1 — delegate.** Make the kind-unaware primitive call the kind-aware seam
  internally. Call sites are untouched, so the existing suite is the harness, the
  floors do not move, and the *one* hidden delta (backfill recovery) surfaces at all
  34 sites at once, attributably.
- **Step 2 — remove.** Push the decision to whoever owns the information: the
  **caller** declares the kind (it knows which artifact it reads), and the primitive
  becomes **module-private** — it cannot be deleted, because it is the terminal
  `KITTY_SPECS_DIR` constructor the resolver itself is built on. A private primitive
  with in-module callers is self-policing; a public one with 34 external callers needs
  two integer floors and a YAML allow-list to stay honest.

## Domain Language *(load-bearing)*

| Term | Canonical sense | Do NOT confuse with |
|------|-----------------|---------------------|
| **Placement authority** | The resolver decides the partition from the kind + topology. | Handle hygiene (was the handle canonicalized) — what the existing floors check. |
| **Semi-compliance** | Canonical handle, caller-chosen partition: looks routed, authority still in the caller. | Compliance. |
| **Kind-blind resolver** | No `MissionArtifactKind`, so it cannot distinguish per-artifact partitions: `candidate_feature_dir_for_mission`, `resolve_planning_read_dir`, `resolve_feature_dir_for_mission`. | "Topology-blind". `resolve_feature_dir_for_mission` is kind-blind but topology-**routed**, which is why it can land on the husk. |
| **Husk** | A coord worktree that exists but carries no `meta.json`. | A deleted coordination branch (which raises for COORD kinds). |
| **Tier-1 idiom** | `placement_seam(...).read_dir(kind)` / `resolve_artifact_surface(root, slug, kind)` — kind named, partition delegated, fail-loud. | `resolve_planning_read_dir(..., kind=)`, which delegates the partition but is **lenient**, and is censused as a bypass on the leniency axis. |
| **Green-by-omission** | A migrated site that passes a gate only because the gate's allow/flag sets do not mention the new idiom. | Genuine compliance. |
| **Disposition** | The per-site verdict on the classification axis, one of exactly three values: **migrate-fail-loud** (route through the seam; a wrong partition must raise), **stay-lenient** (keep the lenient path and its degrade contract), **sanction-infra** (a seam-internal or named-foundation call site, asserted-sanctioned). Use these three names only. | Ad-hoc synonyms such as "fail-loud-classified", "raise-or-degrade", or "deliberate/lenient" — NFR-011's no-synonym rule applies inward to this spec too. |
| **Foundation site** | A call site *underneath* the seam (consumed by `resolve_placement_only` / peer branch resolvers), where routing through the seam risks recursion. | An ordinary consumer site. |

## User Scenarios & Testing *(mandatory)*

Primary actor: the **maintainer/agent** running lifecycle commands; **future
contributors** adding read sites; **future planners** reading the record.

### User Story 1 - The placement decision lives in one place (Priority: P1)

Today 34 call sites decide the partition themselves by naming a primary-only helper.
After this mission each declares only its artifact kind and the resolver decides
where, so a future change to a kind's placement propagates automatically instead of
leaving 34 sites silently pinned to PRIMARY.

**Why this priority**: This is the governing principle. Duplicated decisions are how
placement drift returns; the 88 already-compliant sites prove the target shape works.

**Independent Test**: For each migrated site, assert the resolved directory is
unchanged for a materialized mission, and that the site names a kind rather than a
partition. Assert no call site outside the resolver module names the primitive.

**Acceptance Scenarios**:

1. **Given** a materialized mission (flat or coord), **When** any migrated site resolves, **Then** the directory is identical to the pre-migration result.
2. **Given** a **backfilled** mission and a composed handle, **When** a migrated site resolves, **Then** it returns the existing bare-slug directory (the blind composition returned a non-existent path).
3. **Given** the completed migration, **When** the tree is censused, **Then** no consumer module outside the resolver/sanctioned set calls the primitive, and the primitive is absent from the module's public exports.

---

### User Story 2 - Step 1 surfaces the hidden decision before anything is rewritten (Priority: P1)

Before touching 33 call sites, the primitive itself is made to delegate to the seam.
The existing suite becomes the harness and every behavioural difference shows up
attributably, at one edit's cost.

**Why this priority**: This is the safety property of the sequence. It converts "we
believe these are equivalent" into observed evidence, and it isolates the single real
delta (backfill recovery) from the 33 mechanical edits that follow.

**Independent Test**: Land the delegation alone; run the targeted suites; every
divergence is attributed to anchoring / backfill-recovery / husk / raising, and the
anchoring floors are confirmed unmoved because no call site changed.

**Acceptance Scenarios**:

1. **Given** only the delegation change, **When** the targeted suites run, **Then** every failure is explained and attributed, with backfill recovery the only accepted behavioural delta.
2. **Given** only the delegation change, **When** the canonicalizer censuses run, **Then** both floor counts are unchanged (call sites untouched).
3. **Given** the delegation, **When** a PRIMARY-kind read runs against a coord mission with a husk worktree, **Then** it resolves the primary anchor and does not raise.

---

### User Story 3 - A gate cannot be satisfied by omission (Priority: P1)

A migrated site must be *affirmatively* sanctioned, not merely unmentioned. The
fold-prescription gate's allow/flag sets learn the tier-1 idiom, and the one site
passing today through a fold-set gap is closed.

**Why this priority**: Migrating into a gate's blind spot would trade a visible
semi-compliance for an invisible one — the same green-but-meaningless failure this
programme has already had to repair twice.

**Independent Test**: Plant a bad read in a migrated module → still flagged. Confirm
`status/aggregate.py:522`'s canonicalizer is recognised (or routed) so the site is no
longer passing by omission.

**Acceptance Scenarios**:

1. **Given** a module whose reads now come from the seam, **When** a non-compliant read is planted there, **Then** the fold-prescription gate still flags it.
2. **Given** `status/aggregate.py:522`, **When** the gate runs, **Then** the site is either routed through the recognised fold or its canonicalizer is in the fold set — it no longer passes unexamined.
3. **Given** `status/aggregate.py:543`'s `.name`-derived handle, **When** a backfilled mission is resolved, **Then** the composed-name divergence cannot silently return a non-existent path.

---

### User Story 4 - A PRIMARY artifact is never read off the coord husk (Priority: P1)

`resolve_feature_dir_for_mission` — kind-blind and topology-routed, policed by
nothing — can hand a caller the husk. Sites that genuinely read PRIMARY artifacts
route through the seam; sites that deliberately want the topology-routed answer are
recorded as such and policed thereafter.

**Why this priority**: This is the one genuinely unguarded silent-wrong-read path.

**Independent Test**: Drive a fail-loud-classified site on a husk mission — it must
resolve PRIMARY, not the husk. A planted call anywhere reds the read-side gate,
including via an alias.

**Acceptance Scenarios**:

1. **Given** a coord mission whose worktree is a husk, **When** a fail-loud-classified site reads its PRIMARY artifact, **Then** it resolves the primary anchor.
2. **Given** a planted direct or **aliased** call in a non-sanctioned module, **When** the read-side gate runs, **Then** it reds; a prose mention stays green.
3. **Given** a site whose production comment documents that the topology-routed answer is required, **When** the classification pass runs, **Then** its behaviour is unchanged and its rationale is a ledger row.

---

### User Story 5 - The ledger is machine-checked and cannot go vacuous (Priority: P1)

The gate parses the ledger, and the parse cannot silently drop a primitive's rows.

**Why this priority**: The prescribed multi-primitive restructuring was *executed* and
shown to parse only the first sub-table while the reconciliation stayed green — the
exact vacuity a prior landing pass had to repair. Grammar comes before rows.

**Independent Test**: Mutate a row for **each** primitive independently → reds each
time. Parsed row count equals the summed per-primitive census.

**Acceptance Scenarios**:

1. **Given** a mutated ledger row for primitive *N*, **When** the gate runs, **Then** it reds — for every *N*.
2. **Given** the parsed sections, **When** the gate parses the ledger, **Then** parsed row count equals the summed census; a dropped table or shifted column reds loudly rather than parsing empty.
3. **Given** a module with several censused sites in one function, **When** the stay-lenient index is built and validated, **Then** the index addresses each distinctly and its uniqueness assertion holds.

---

### User Story 6 - The residuals are closed and the record stops misleading (Priority: P2)

Both `_run_documentation_wiring` reads are routed and the `#2214` pin retires with the
test that asserts it exists; the misleading comments in `acceptance/__init__.py` and
the six husk-conflating comments are corrected; every count in the ledger and gate
docstring matches a fresh census.

**Why this priority**: A wrong record manufactured #3014. Correcting it is what stops
a third re-derivation.

**Independent Test**: Read the corrected artifacts — every "unpoliced" claim names its
gate and axis, every count matches a fresh census, every residual gap is named with a
size.

**Acceptance Scenarios**:

1. **Given** both reads routed, **When** the pin and its pin-existence test are removed together, **Then** the closeout gate's clean scan is green with non-vacuity from its site floor.
2. **Given** the audit-metadata write following the read, **When** the documentation-wiring path runs, **Then** the `meta.json` write resolves through the same authority as the read; `gap-analysis.md` (which has **no** kind) anchors on that resolved directory and is recorded as an honest bound.
3. **Given** any count in the ledger or gate docstring, **When** it is compared against a fresh census, **Then** it matches; the stale figure is corrected in both places and the closeout gate's recorded census is exact.
4. **Given** the six husk comments, **When** a maintainer reads them, **Then** each states accurately that the *kind-blind* resolver selects the husk while the kind-aware seam does not.

---

### User Story 7 - A future mission is pointed at a design document, not a rediscovery (Priority: P1)

A planner picking up the next placement-related residual reads one architecture page
that states what "routing" means here, which layer owns the decision, and what
semi-compliance looks like — instead of re-running the multi-round discovery, audit and
operator-guidance cycle this mission needed to establish facts that were already true.

**Why this priority**: This is the durable deliverable. The misappropriation of the
seam as a "stable API to strangle through" has now cost three separate missions their
discovery budget: #3014 was filed on a false premise, this mission was re-framed twice,
and the governing decision (ADR `2026-06-24-1`, plus the `TopologySurface` vocabulary
in ADR `2026-07-23-1`) already forbade the exact anti-pattern in prose that nobody
found. Documented layering converts recurring archaeology into a citation.

**Independent Test**: Hand the new page to a reader who has not followed this
programme; they can state (a) what routing means in this context and how it differs
from branch-target routing, (b) which layer decides placement, (c) why a canonical
handle is not compliance. A future mission spec can cite the page instead of
re-deriving.

**Acceptance Scenarios**:

1. **Given** the new architecture page, **When** a reader looks for "who decides where an artifact lives", **Then** they find the three-layer split — callers/runtime declare *what*, the decision module maps kind + topology to a `TopologySurface`, path resolution assembles the concrete directory — with the code owners of each layer named.
2. **Given** the word "routing", **When** a reader consults the glossary or the page, **Then** the placement sense is distinguished from branch-target routing, commit routing, dispatch/profile routing, and sync fan-out, each with a "do NOT use when" guard.
3. **Given** ADR `2026-06-24-1` and ADR `2026-07-23-1`, **When** the page is read, **Then** it cites them as the governing decisions and restates the forbidden conditioning pattern, rather than introducing a competing vocabulary.
4. **Given** the semi-compliance shape this mission fixes, **When** a future reviewer reads the page, **Then** they can recognise it (canonical handle + caller-chosen surface) and know which gate does and does not catch it.

---

### User Story 8 - The suite states the destination, so red→green is the acceptance signal (Priority: P1)

Rather than retiring each defunct enforcement reactively — after the code it no longer
describes has already changed — an early work package re-expresses the suite's
expectations against the **target** design. The suite goes deliberately red, and that red
is the mission's specification: as each migration lands, specific nodes turn green, and
"done" is observable rather than argued.

**Why this priority**: it converts a scattered set of bookkeeping chores into a single
acceptance signal, and it dissolves two hazards structurally — the use-count floors are
gone *before* the fifth routed site can trip their strict bound, and the two
green-by-omission gates get positive assertions *before* anything can slip past them.

**The bar this depends on**: the signal is only worth having if the rewritten expectations
genuinely encode the design. A suite red-stated carelessly *hides* regressions instead of
revealing them, and a red that is a **collection error** (a missing symbol) is not
red-first evidence at all — the red must manifest in an assertion about behaviour.

**Independent Test**: after this WP alone, every red is either an expected assertion about
the target design (traceable to a named FR) or a foreign honest-red P0; no red is a
collection error caused by this WP; and the count of expected-red nodes is recorded so
later WPs can show the intended red→green transitions.

**Acceptance Scenarios**:

1. **Given** the suite rewritten to the target design, **When** it runs before any migration lands, **Then** each red traces to a named requirement, and no red is an import/collection error introduced by this WP.
2. **Given** a later migration WP lands, **When** the suite runs, **Then** the specific nodes that WP was expected to green **are** green, and nothing previously green went red.
3. **Given** a red that is neither expected-by-design nor a foreign honest-red P0, **When** it is triaged, **Then** it is treated as a load-bearing regression and the product is fixed.
4. **Given** the retired use-count floors, **When** the migration passes its fifth routed site, **Then** no strict-bound assertion breaks mid-drain (the floors are already gone).

---

### Edge Cases

- **Backfilled mission + composed handle** — the one real behavioural delta; must be pinned by test, per site where it applies.
- **Coord husk** and **deleted coord branch** — PRIMARY kinds must not raise; COORD kinds must.
- **Foundation sites under the seam** — `core/paths.py:727` feeds `resolve_placement_only`; routing it risks recursion.
- **Multiple censused sites in one function** — `status/aggregate.py::_find_meta_path` carries four.
- **Wrapper laundering** — `resolve_subtasks_gate_dir` wraps a censused primitive with a pinned kind; invisible to a callee-name census.
- **Aliased / re-exported imports**; **wrong-`kind` argument** (census-invisible by construction); **artifacts with no kind** (`gap-analysis.md`).
- **Flat / coord-less topologies** — no behaviour change anywhere.
- **Latent sibling** — `resolve_feature_dir_for_slug`, zero live sites; would re-open the gap the moment it is imported.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | Story | Requirement (user-value statement) | Priority | Status |
|----|-------|-------|------------------------------------|----------|--------|
| FR-001 | Close the gate holes before migrating | US3 | As a maintainer, I want `status/aggregate.py:522`'s unrecognised canonicalizer closed and the fold-prescription gate's allow/flag sets widened to know the tier-1 seam idiom, so migrated sites are affirmatively checked rather than green-by-omission. | High | Open |
| FR-002 | Step 1 — delegate the primitive to the seam | US2 | As a maintainer, I want `primary_feature_dir_for_mission` to resolve through the kind-aware seam internally, with call sites untouched, so the existing suite surfaces every behavioural delta at one edit's cost and the anchoring floors stay unmoved. | High | Open |
| FR-003 | Attribute and pin the delegation's deltas | US2 | As a maintainer, I want each divergence Step 1 surfaces attributed (anchoring / backfill recovery / husk / raising) and the accepted one — backfill recovery — pinned by test, so the delta is documented rather than absorbed. | High | Open |
| FR-004 | Step 2 — callers declare the kind | US1 | As a maintainer, I want each consumer site to pass its artifact kind to the seam instead of naming a primary-only helper, so the placement decision lives in the resolver. | High | Open |
| FR-005 | Keep foundation sites out, by name | US1 | As a maintainer, I want the sites that sit *beneath* the seam (`core/paths.py:727`, `:780`, `core/git_ops.py:444`, `coordination/surface_resolver.py:739`) left unrouted and recorded as named sanctioned foundation sites with their recursion rationale, so authority tidiness does not buy a resolution cycle. | High | Open |
| FR-006 | Delete the public wrapper; keep the private assembler | US1 | As a maintainer, I want the **public** `primary_feature_dir_for_mission` wrapper **deleted** once its consumers are routed — the terminal `KITTY_SPECS_DIR` assembler surviving as a module-private leaf — so the invariant is structural: the public name ceases to exist and cannot be re-imported, and no renamed private name needs re-blessing in the trio gate. | High | Open |
| FR-023 | Re-express suite expectations against the target design, early | US8 | As a maintainer, I want an early work package that rewrites the affected gates' expectations to describe the **target** design — retiring the use-count floors, replacing the two green-by-omission exemptions with positive assertions, and re-authoring the stale content descriptors — so the suite becomes the mission's acceptance signal (red→green per landing WP) instead of a trail of reactive bookkeeping. Every red it leaves must be an **assertion** about behaviour traceable to a requirement, never a collection error, and the expected-red set must be recorded. | High | Open |
| FR-024 | Ground execution in the cited refactoring doctrine | US8 | As an implementer, I want each work package body to carry the doctrine that governs it as executable citations (`Run: spec-kitty charter context --include <kind>:<id>`) with a when-doing trigger, so the mission's refactoring intent reaches the execution run — because spec/plan prose is **not** composed into a WP prompt, and a new frontmatter field would be rejected outright. | High | Open |
| FR-021 | Extract the terminal assembler first (tidy-first) | US1 | As a maintainer, I want the pure `KITTY_SPECS_DIR` assembly extracted into a module-private leaf and the seam's own PRIMARY leg (plus the 11 resolver-internal callers) re-pointed at it **before** any delegation, because the seam reaches the primitive through its PRIMARY leg — delegating without this extraction is an **infinite recursion**, not a refactor. | High | Open |
| FR-022 | Drain and privatise the co-drained canonicalizer | US1 | As a maintainer, I want `_canonicalize_primary_read_handle` (86 references / 22 `src/` files) treated as a peer of the primary primitive: the seam canonicalizes internally, so every routed site drains it too — it must be censused, drained, and privatised/deleted in this cycle, so no public leaf is left propped up by an integer floor. | High | Open |
| FR-007 | Retire the use-count floors and transfer the guarantee (with doctrinal adjudication) | US1 | As a maintainer, I want the two canonicalizer floors retired (or honestly re-pinned with recorded before/after) and their guarantee transferred to the read-side census as a censused callee with an explicit sanctioned set, so no gate obliges the primitive to keep being used. **This must be adjudicated explicitly against `DIRECTIVE_043` (`enforcement: required`, "a gate that trivially passes when the relevant call-site count is zero is non-compliant — the gate must have a concrete floor") and against `tactic:architectural-gate-non-vacuity`, whose step 4 prescribes the very routed-count floor being retired**: non-vacuity is *preserved by transfer* — the bypass census carries its own concrete floor and per-primitive non-vaciuty proof — not abandoned. Silence here would read as violating a required directive. | High | Open |
| FR-008 | Fix the ledger's machine-parse grammar first | US5 | As a maintainer, I want the parsed sections constrained (one table per parsed heading, verbatim headings, verdict/path/qualname at fixed leading positions, any primitive discriminator appended as a trailing column) **before** rows are added, so a multi-primitive ledger cannot parse silently-empty. | High | Open |
| FR-009 | Give the index a per-site discriminator | US5 | As a maintainer, I want the stay-lenient index able to address several censused sites in one qualname, with its uniqueness assertion updated in the same change. | High | Open |
| FR-010 | Census and classify the unpoliced resolver, with per-disposition counts | US4 | As a maintainer, I want an AST census (aliases resolved) of `resolve_feature_dir_for_mission` and every site classified with disposition **and both axes** — raise-or-degrade, anchoring root (verbatim argument plus its semantic class with provenance), handle form, target kind, idempotence under the seam's output — and I want the census to record the **count per disposition**, so a zero-fail-loud outcome is an explicit, reviewable finding rather than a silently satisfied requirement. | High | Open |
| FR-011 | Route its PRIMARY-artifact reads; justify the rest | US4 | As a maintainer, I want each of its sites that reads a PRIMARY artifact routed onto the seam, and each site that genuinely needs the topology-routed answer preserved as a rationale-bearing allow-list entry reusing its production comment. | High | Open |
| FR-012 | Police it in the read-side gate | US4 | As a maintainer, I want `resolve_feature_dir_for_mission` added to the censused callees with sanctioned modules asserted **per primitive** and residuals allow-listed shrink-only under the staleness twin-guard. | High | Open |
| FR-013 | Route both `_run_documentation_wiring` reads | US6 | As a maintainer, I want **both** metadata reads routed through the partition-aware authority, so routing one does not leave the other reading off a coord-bound directory. | Medium | Open |
| FR-014 | Retire the `#2214` pin with its pin-existence test | US6 | As a maintainer, I want the allow-list entry **and** the test asserting that pin exists retired together, so the gate does not red by construction. | Medium | Open |
| FR-015 | Correct every misleading comment | US6 | As a maintainer, I want the two `acceptance/__init__.py` comments **and** the six husk-conflating comments corrected, so no reader concludes the seam has the kind-blind resolver's failure modes or that `lanes.json` belongs on COORD. | Medium | Open |
| FR-016 | Correct the false and stale record | US6 | As a maintainer, I want the ledger's Known-gap text to name the anchoring-axis authority and axis rather than claiming "policed by nothing", the stale site count corrected in **both** the ledger and the gate docstring, the closeout gate's off-by-one census fixed, and the drifted definition-line reference updated. | High | Open |
| FR-017 | Enumerate the honest bounds | US6 | As a maintainer, I want the gate's advertised bounds to name, with sizes, what it does not cover: the wrong-`kind` class, wrapper laundering, the zero-site latent sibling, the sanctioned foundation and resolver-internal sites, and artifacts with no kind (`gap-analysis.md`, which anchor on a resolved directory rather than being routed) — so no planner repeats #3014. | High | Open |
| FR-018 | Document the placement seam and its verified layering | US7 | As a future mission planner, I want an explanation page (`docs/architecture/artifact-placement-seam.md` — not a third `*-routing.md`) that defines **routing** in the placement sense and formalises the layering **as the code actually is**: (L0) the caller declares a `MissionArtifactKind` through `PlacementSeam`; (L1) the kind→partition classification, topology-blind (`artifacts.py` kind frozensets + `assert_partition_invariant`); (L2) the decision layer, which is **two functions whose divergence is load-bearing** — `declared_read_surface` (materialization-**blind**, so it can disagree with a resolved stamp, which is what makes the `surface_cannot_hold` / #2906 guard possible) and `_classify_artifact_surface` (materialization-**aware**, consuming coord-state probing); (L3) candidate discovery and path **assembly** (`_read_path_resolver`); (L4) `translate_surface`, which **selects** an already-discovered location off `SurfaceLocations` and refuses when absent — it does **not** assemble a path. It must show **both** composition roots (`resolve_artifact_surface` for reads, `resolve_placement_only` for writes) reached through one seam, record the compliant / semi-compliant / non-compliant idioms, and carry the honest bounds: `LANE`/`CONSOLIDATED`/`TEMP` have no production producer, and `_PLACEMENT_ARTIFACT_KINDS` still carries the retired `PLACEMENT` word as residual rename debt (named, not laundered). | High | Open |
| FR-020 | Retire the competing placement authority | US7 | As a maintainer, I want `docs/architecture/branch-target-routing.md` narrowed to the *branch* sense in the same slice as the new page — its per-artifact-kind placement claims and its pre-`TopologySurface` "How the routing decision is made" section removed or reduced to a link — because it currently asserts normative placement content in retired vocabulary ("primary target branch", an alias the glossary explicitly retires), so publishing a new page without narrowing it would create two authorities answering one question. | High | Open |
| FR-019 | Disambiguate "routing" in the prose glossary | US7 | As a maintainer, I want a `Routing` disambiguation added to `docs/context/orchestration.md` **plus** a Terminology Canon line in `CLAUDE.md` — exactly how the `primary`/`merge` footgun is actually implemented — extending (not restating) the existing `PRIMARY partition` / `COORD partition` / `Topology Surface` entries, which already frame partition as an artifact-kind routing concept. It must **govern** the senses that appear in governed prose — placement, branch-target, commit, dispatch/profile, sync fan-out, model/task routing (`src/doctrine/model_task_routing/`, the highest-collision sense in agent-authored text) and scope routing — each with a "do NOT use when" guard, and **explicitly scope out by name** the infrastructural senses (event routing, HTTP request routing, significance routing bands) rather than passing over them in silence. It must NOT edit `src/doctrine/glossary_packs/built-in/spec-kitty-core.glossary-pack.yaml` or `.kittify/glossaries/spec_kitty_core.yaml` (byte-frozen by a seed SHA + term-count pin and a parity gate), and must not reword or renumber existing headings that ADRs deep-link. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Behaviour-preserving except one named delta | Every routed site resolves an identical directory for a materialized, non-backfilled mission. The **only** permitted delta is the seam's bare-`<slug>` backfill recovery, named per site and pinned by test. | Reliability | High | Open |
| NFR-002 | No new raises where leniency is the contract | Zero deliberate/lenient sites and zero flat or coord-less executions begin raising. PRIMARY kinds must not raise on husk, empty, or deleted-coord states. | Reliability | High | Open |
| NFR-003 | Red-first per behavioural change | Each behavioural change ships a test failing before and passing after (verified by reverting the product file), including husk and composed-vs-bare handle cases. | Safety | High | Open |
| NFR-004 | Gate bite, per-primitive non-vacuity, authority parse | The extended gate reds on planted direct and **aliased** calls, stays green on prose, reds when a parsed ledger row disagrees **per primitive**, reds on a stale entry, proves each sanctioned module carries a real finding **for that primitive**, and asserts parsed row count equals the summed census. | Safety | High | Open |
| NFR-005 | No green-by-omission | After migration, a non-compliant read planted in any migrated module is still flagged; the fold-prescription gate's sets recognise the tier-1 idiom affirmatively. | Safety | High | Open |
| NFR-006 | Single scanner authority | The read-side gate keeps consuming the shared whole-tree scan scope; the write-side gate stays green. | Maintainability | High | Open |
| NFR-007 | Honest floor accounting | Any floor that moves records its before/after integers and the reason (a routing shrink), per the floors' own doctrine; no floor is relaxed without a recorded census. | Maintainability | High | Open |
| NFR-008 | Census reconciliation, correctly scoped | Reconciliation covers the **live residual/lenient** totals per primitive — the figures the gate parses — not the historical pre-migration totals, which are preserved and labelled as an audit record. | Maintainability | High | Open |
| NFR-009 | No resolution cycle | No change introduces a cycle in the `read_dir` call graph; the foundation sites named in FR-005 stay outside it. | Reliability | High | Open |
| NFR-010 | Docs hygiene for the new page | The page is registered in `docs/architecture/index.md` (mandatory — the curated `explanation-index.md` / `explanation-toc.yml` are ungated subsets and are a judgement call, not a requirement), the two **gated** registries `docs/development/3-2-page-inventory.yaml` and `docs/development/3-2-docs-retrieval-index.yaml` are regenerated, relative links resolve, and `check_docs_freshness --ci` reports zero errors. | Maintainability | High | Open |
| NFR-011 | Explanatory only; vocabulary consistent, not competing | The page and glossary use the canonical `TopologySurface` vocabulary and extend the existing entries; no new synonym for an already-named concept. The page is **explanatory**: it links to ADR `2026-06-24-1` / `2026-07-23-1` for normative rules (the placement invariant, the forbidden-conditioning rule, alias retirement) rather than restating them, and **every code-shape claim carries a `module:symbol` citation** so drift is detectable. The terminology, glossary-canonical-terms, and glossary-pack parity/no-regression gates all stay green. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | `LANE_STATE` stays PRIMARY | `lanes.json` is PRIMARY and `acceptance-matrix.json` is placement-resolved; the partition sets are disjoint and exhaustive, so no "covers both" kind is possible. | Technical | High | Open |
| C-002 | One ledger, extended | The classification extends the existing machine-parsed ledger; no second authority document. | Technical | High | Open |
| C-003 | No file-scoped blanket exemptions | Allow-list entries are per-site descriptors with individual rationale. | Technical | High | Open |
| C-004 | Private assembler permanent; public wrapper deleted | The terminal `KITTY_SPECS_DIR` assembler is module-private and permanent (the resolver is built on it, and it is the sanctioned owner of that assembly). The **public wrapper** is a transitional shim and is **deleted** at the end of the migration — it is not merely renamed. Operator-decided 2026-07-28, superseding the earlier "privatise, never delete" framing. | Technical | High | Open |
| C-005 | Sequence is extract → delegate → remove | **Step 0** extracts the terminal assembler and re-points the seam's PRIMARY leg (FR-021) — without it Step 1 recurses. **Step 1** delegates the public wrapper and is verified with call sites untouched. **Step 2** rewrites call sites, then deletes the wrapper. The use-count floors are retired at the **start** of Step 2, not after it: their strict bound breaks mid-drain. | Technical | High | Open |
| C-009 | Grammar before rows | The ledger's parse grammar (FR-008) and the index discriminator (FR-009) land and are verified **before** any classification row is written for a newly censused primitive; a row added under the old grammar can parse silently-empty. This is the second hard sequencing gate alongside C-005. | Technical | High | Open |
| C-010 | Foreign honest-red P0s are out of scope | Missions landing on `upstream/main` carry **deliberately red** red-first P0 pins (e.g. `tests/sync/test_sync_consent_default_deny.py`, hosted-sync consent #3031, red by design per ADR `2026-07-17-1` and marked `fast`, so it appears in fast lanes). This mission does **not** remediate them. Classification is by **surface**: a red is this mission's business only if it touches a placement/read-path surface this mission owns, or is a demonstrable product regression from this mission's diff. Never green-wash a foreign P0; never treat its presence as a reason to widen scope. | Technical | High | Open |
| C-011 | Doctrine citations live in the WP body | Doctrine references reach an implementer **only** through the WP task-file body (composed verbatim into the prompt) as `Run: spec-kitty charter context --include <kind>:<id>` stanzas with a when-doing trigger, plus the validated `agent_profile` field. Citations in `spec.md`/`plan.md` are for reviewers and the accept gate, **not** a propagation mechanism. A new frontmatter key (`doctrine_refs:`, `directives:`, …) is **forbidden** — the WP schema is `extra="forbid"`, so it raises and breaks workspace resolution, dependency gating and status emission. Do not add to the mission-type action index (over-broadcasts permanently and is inert on this route). | Technical | High | Open |
| C-006 | Scope boundary | The authoritative list is the **Out of Scope** section at the end of this spec; in summary: the #2966 remainder, the #2964 terminology migration, re-fixing #2824's landed defect, new `MissionArtifactKind` members, extending the pinned scan-scope prefix set, and the ~14 hand-assembled `KITTY_SPECS_DIR` paths outside sanctioned constructors (tracked separately). | Technical | High | Open |
| C-007 | Not a bulk edit | Each site needs an individual semantic decision (which kind, which disposition, which anchoring class); the machine-parsed ledger is the guardrail of record. Operator-confirmed 2026-07-28. | Technical | Medium | Open |
| C-008 | Targeted verification only | The exhaustive architectural sweep is CI's responsibility. Locally named gates: read-side census, closeout, anchoring-authority floors, fold-prescription, trio-seam, write-side, plus the mission suites. | Technical | Medium | Open |

### Key Entities

- **Classification ledger** — the machine-parsed authority; gains a constrained multi-primitive grammar, rows for the newly censused resolver, and a corrected Known-gap section.
- **Read-side census gate** — gains censused callees, per-primitive non-vacuity, honest bounds, and the guarantee transferred from the retired floors.
- **Anchoring-authority floors + allow-list YAML** — the handle-hygiene guard whose subject population this mission drains; retired or honestly re-pinned.
- **Fold-prescription gate** — blesses the primary-fold call shape; its allow/flag sets must learn the tier-1 idiom (FR-001) or migration is green-by-omission.
- **Coord-read closeout gate** — loses the `#2214` pin and its pin-existence test; keeps its site floor.
- **Leaf primitives** — the privatised primary constructor, the two censused kind-blind resolvers, `resolve_feature_dir_for_mission` (newly policed), and the zero-site latent sibling.
- **Routing/decisioning architecture page** (new, `docs/architecture/`) — the durable explanation of the three-layer split and the meaning of "routing" in the placement context; the artifact future missions cite instead of re-running discovery. Governed by ADR `2026-06-24-1` (kind-and-topology-aware placement) and ADR `2026-07-23-1` (`TopologySurface` vocabulary + the forbidden conditioning pattern); cross-referenced with `docs/architecture/branch-target-routing.md`, which owns the *branch* sense of the word.
- **Canonical glossary** (`docs/context/orchestration.md`, alongside the doctrine glossary pack) — already carries `PRIMARY partition`, `COORD partition`, `Topology Surface`; gains the `Routing` disambiguation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The public `primary_feature_dir_for_mission` **no longer exists**; the private assembler has only in-module and named-sanctioned callers; and `_canonicalize_primary_read_handle` is likewise drained and non-public (FR-022).
- **SC-002**: Every migrated site resolves an identical directory for a materialized mission; the only recorded behavioural delta is backfill recovery, pinned by test.
- **SC-003**: Step 1 lands with the anchoring floor counts unchanged, and every divergence it surfaces is attributed in writing.
- **SC-004**: A non-compliant read planted in a migrated module is still flagged, and `status/aggregate.py:522` no longer passes by omission.
- **SC-005**: For all *N* fail-loud-classified `resolve_feature_dir_for_mission` sites, a husk mission resolves the primary anchor — zero husk substitutions; a planted direct or aliased call reds the gate. **Zero-case discharge:** if the census yields *N* = 0, that is recorded as an honest bound under FR-017 (with its per-disposition counts from FR-010) and the husk guarantee is pinned by a synthetic-site regression instead — the criterion is never satisfied by an empty set.
- **SC-006**: Mutating a ledger row for **each** primitive independently reds the gate; parsed row count equals the summed per-primitive census.
- **SC-007**: The `#2214` pin and its pin-existence test are both absent, both `_run_documentation_wiring` reads are routed, and the closeout gate is green.
- **SC-008**: Every count claimed in the ledger and the gate docstring matches a fresh census; the previously stale figure is corrected in both places.
- **SC-009**: All eight misleading comments (two acceptance, six husk) state what the code does.
- **SC-010**: Any floor that moved records its before/after integers and reason; no floor obliges the primitive to remain in use.
- **SC-011**: **At mission terminus (after WP08 and WP09 land)** the named targeted gates and mission suites are green on the rebased tip; `ruff` and project-mode `mypy` report zero new findings. This criterion is deliberately **not** evaluated per-WP: FR-023/US8 require the suite to be red by design from the suite-expectations WP until the wrapper is deleted, so a mid-mission red is the acceptance signal rather than a failure of this criterion.
- **SC-012**: The new page structurally carries: a named section per layer with that layer's owning module path; a `Routing` disambiguation table covering every **governed** sense, each with a "do NOT use when" guard, plus the infrastructural senses named as out of scope; a compliant / semi-compliant / non-compliant idiom table; citations to both governing ADRs; both composition roots; and the honest bounds (unwired surface members, the residual `PLACEMENT` rename debt). Asserted by a docs test alongside the SC-013 hygiene checks. (The comprehension intent lives in User Story 7's Independent Test, where a human check belongs.)
- **SC-014**: The foundation sites of FR-005 are recorded by name with their recursion rationale, and remain unrouted — verified by census.
- **SC-015**: The index discriminator (FR-009) admits a module with several censused sites in one qualname — demonstrated by the known four-site case — and its uniqueness assertion holds.
- **SC-016**: The classification's per-disposition counts (FR-010) are published in the ledger, and the honest bounds enumeration (FR-017) matches the live tree item-for-item with sizes.
- **SC-013**: Docs hygiene is green (page registered in `docs/architecture/index.md`; both gated registries regenerated; relative links resolve; `check_docs_freshness --ci` zero errors), the terminology and glossary-canonical-terms guards pass, and the glossary-pack parity + no-regression gates are **untouched-green** (proving neither frozen store was edited).
- **SC-020**: After the suite-expectations WP, every red is either an expected assertion traceable to a named requirement or a listed foreign honest-red P0 — zero collection errors introduced by that WP — and the expected-red set is recorded so later WPs demonstrate their red→green transitions.
- **SC-021**: Each WP body carries its governing doctrine as `--include` citations with when-doing triggers; every cited id resolves (the command exits non-zero on a bad id); no WP frontmatter carries an unschema'd doctrine key.
- **SC-018**: The extraction (FR-021) is behaviour-neutral and lands with zero call-site changes; a PRIMARY-kind read through the seam completes without recursion.
- **SC-019**: Every red observed during the migration is classified *stale → re-pin/retire* · *scaffold → delete* · *valid → fix product*, and the classification is recorded; no product change is made to satisfy a gate that encodes the retired shape.
- **SC-017**: `docs/architecture/branch-target-routing.md` no longer asserts per-artifact-kind placement rules and no longer uses the retired `primary target branch` alias; it links to the new page for the placement sense.

## Assumptions

- The audit's numbers are re-derived, not trusted: 46 total primitive sites (7 resolver-internal, 4 `resolution.py` internal, 1 sanctioned single-authority — `coordination/surface_resolver.py:739` — and **34 in scope**, of which 33 semi-compliant + 1 non-compliant). **Routable = 31**: the 34 in-scope sites include **three** of FR-005's foundation sites (`core/paths.py` ×2, `core/git_ops.py`), which are recorded rather than routed; FR-005's **fourth** foundation site is the separately-counted sanctioned single-authority one, so it is *not* inside the 34. Do not read "four foundation sites" as four subtractions from 34. `resolve_feature_dir_for_mission` = 8 sites / 7 files; live canonicalizer census 46 scanned / 43 routed against recorded floors 44 / 40; the ledger and gate docstring both carry a stale 40 where the live consumer census is 39.
- All PRIMARY kinds resolve to the same anchor, so Step 1's delegation can use a single PRIMARY kind and remain answer-equivalent.
- ~24 sites have an unambiguous kind (`PRIMARY_METADATA`, plus `WORK_PACKAGE_TASK` and `ANALYSIS_REPORT` where named); the remainder are the foundation sites of FR-005 plus any genuinely ambiguous site, to be adjudicated in the classification WP.
- #2824's functional defect is already fixed and regression-covered; only comments are in scope.
- PR #3007 is clear of every surface this mission touches.

## Provenance

Re-framed twice on 2026-07-28. The first draft inherited #3014's premise; a two-lens
post-spec squad returned **10 MAJOR findings**, three falsifying it (the primitive is
already policed on the anchoring axis; its fail-loud surface is zero; a *fourth*
kind-blind resolver is the real gap) and two proving the prescribed ledger and index
grammar would have been silently vacuous. The operator then asked whether the
"already policed" sites route through the seam or are semi-compliance with a
hardcoded target; a placement-authority audit established they are semi-compliant,
that the seam is answer-equivalent (and better on backfilled missions), that the six
justifying comments conflate two resolvers, and that the floor collision is
bookkeeping with in-tree precedent. The operator prescribed the delegate-then-remove
sequence and chose to carry both steps in this mission. Issue #3014's premise is
superseded; the corrected findings are posted there.

## Note for the Plan Phase

FR-018/FR-019 are the operator-requested **new implementation concern**: *"update the
architecture docs to describe the routing/decisioning seam, and formalize the split
between runtime, decision module, path resolution"*. It is deliberately a first-class
deliverable of this mission rather than a follow-up, because the discovery cost it
removes has already been paid three times. Plan should carry it as its own IC and its
own work package — it has no code dependency on the migration WPs and can run in
parallel, but it must be authored **after** the classification WP so the page documents
the layering as landed rather than as intended.

## Out of Scope

- The #2966 remainder, the #2964 terminology migration, re-fixing #2824's landed defect.
- New `MissionArtifactKind` members; extending the pinned scan-scope prefix set.
- The ~14 hand-assembled `KITTY_SPECS_DIR` paths outside sanctioned constructors, and the duplicated coord-dir grammar in `coordination/surface_resolver.py:528` — real findings, tracked separately.
- Routing the named foundation sites (FR-005) or deleting the primitive (C-004).
