# Mission Specification: Doctrine Delivery Reachability

**Mission Branch**: `feat/doctrine-delivery-reachability`
**Created**: 2026-07-28
**Revised**: 2026-07-28 (post-spec adversarial squad — four profile-loaded lenses, 11 blockers folded)
**Status**: Draft
**Input**: User description: "wiring + activation + #2977" — selected during pre-spec discovery from three
scoped candidate slices. See [`research/slice-selection-and-programme-context.md`](research/slice-selection-and-programme-context.md).

---

## Context

Mission A (`doctrine-silence-guards-01KYFV7Q`, PR #3007, merged `ed470756e`) closed ten classes of
**declared-but-inert** failure at the **validation** layer — declarations that loaded and validated
cleanly while doing nothing.

This mission closes the same defect class one layer down, at the **delivery** layer:

> A declaration can pass every check and still reach nobody.

### The mechanism, named in code

The post-spec squad established that the three strands are not merely thematically related. They are
one mechanism:

> **A projection table narrower than the enumeration it projects, silenced by a `.get(…, default)`
> or a literal `[]`.**

- `_edge_to_dict`'s hand-listed keys vs `DRGEdge.model_fields`
- `_ACTION_BUNDLE_SLOT_BY_KIND`'s 4-of-16 verdict, and `resolver.py`'s four `[]` literals, vs the
  activated kind set
- `_PROJECT_KIND_DIRS`'s 4-of-12 vs `ArtifactKind`

**The repository already ships two mechanisms that close this class by construction:**
derivation-from-`model_fields` (`_FIELDS_WITHHELD_FROM_GRAPH_OUTPUT`) and
totality-or-explicit-exemption (`tests/doctrine/drg/test_kind_mapping_totality.py`).

**Operator ruling, 2026-07-28: this mission extends those two mechanisms rather than hand-fixing
instances.** Fixing instances would have added a fourth hand-maintained `_PROJECT_KIND_DIRS` entry to
a table the totality guard is already configured to ignore — the defect class reproduced by its own
remediation.

### Measurement discipline

Every count in this document is either **re-derived on `ed470756e`** or **replaced by a named set**.
The pre-spec research over-counted in one direction throughout (185→**184**, 91→**88**, 214→**213**,
78 delivered→**69**), and two figures did not reproduce at all. Corrections are recorded in
[`research/squad-findings-and-corrections.md`](research/squad-findings-and-corrections.md).

Because SC-005 and NFR-004 are shrink-only ratchets, **a ratchet seeded from a number that never
existed is this mission's own defect class one level up.** Hence C-009 and FR-016.

### Relationship to the programme

Of the seventeen issues PR #3007 filed, **none had an owning requirement** in A/B1/B2/C/D. Two sit
inside the mandated chain: **#2977 blocks B1**, and **#3037 blocks C**.

**Ordering obligation:** mission B1 adds two new `DRGEdge` fields. It cannot start clean until every
write path is derived (FR-001, FR-002). That work carries **no inbound dependency** inside this
mission so it can land first — see C-005 for the limit of that claim.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - New graph fields survive every write path (Priority: P1)

A doctrine author adds a field to the relationship graph model. Whether it survives currently depends
on which code path writes the graph: one derives its output from the model and keeps it; three
restate a hand-written subset and discard it silently.

**Why this priority**: The only piece with a hard external deadline. Mission B1's entire deliverable
is two new edge fields.

**Priority within the story is inverted from the obvious reading.** `rewrite_opposed_by` is **already
guarded** (`tests/doctrine/drg/test_model_strictness_roundtrip.py:520/557` assert field completeness
against `model_fields` and go red when B1 lands). `project_drg._serialize_graph` is guarded by
**nothing** — proven by mutation: deleting its `edge.reason` serialization leaves
`tests/charter/synthesizer/test_project_drg.py` at 23 passed, identical to baseline. **FR-002 leads.**

**Independent Test**: A test that extends the edge model *within the test* with a field no writer
knows about, round-trips it through every registered writer, and asserts survival.

**Acceptance Scenarios**:

1. **Given** an edge model carrying a field no writer was written against, **When** a graph is
   serialized through **each registered write path**, **Then** the field is present in every output.
2. **Given** a new write path is added that constructs an edge payload without the derived helper,
   **When** the suite runs, **Then** it fails naming the offending site — the writer set is derived,
   not enumerated.
3. **Given** an unknown top-level key in a graph document, **When** it is loaded, **Then** it is
   rejected rather than accepted and discarded.

---

### User Story 2 - A consumer can address a shipped asset (Priority: P1)

An operator follows the documented remedy for repo-coupled doctrine — "ship the executable logic as
an asset" — and finds it unreachable from anywhere except this repository's own test suite, which
reaches it by hard-coded path.

**Why this priority**: The documented remedy is not executable downstream, and mission C is scheduled
to author four more assets against the same missing surface. The payload already ships in the
distribution; only addressing is absent.

**Independent Test**: From a wheel installed into a clean environment with this repository absent
from resolution inputs, ask for an asset by identifier and receive a usable path.

**Acceptance Scenarios**:

1. **Given** a package installed into an environment where the repository root is not on any
   resolution path, **When** the operator asks for a shipped asset by identifier, **Then** a
   resolvable path is returned.
2. **Given** an asset declared at the organisation or project tier, **When** resolution runs, **Then**
   the more specific tier wins and the losing tier is reported rather than silently shadowed.
3. **Given** an asset manifest whose declared path escapes its own root by traversal or symlink,
   **When** resolution runs, **Then** it is refused with a typed error.
4. **Given** an organisation-pack asset nested below the type directory, **When** discovery runs,
   **Then** it is found — the overlay scan recurses.
5. **Given** the scaffold command creates an asset, **When** the service resolves that identifier,
   **Then** it reads the directory the scaffold wrote to.
6. **Given** this repository's own consumer of the shipped asset, **When** the mission completes,
   **Then** it reaches the asset through the resolution surface and no longer through a repository
   path.
7. **Given** the published asset how-to, **When** an operator executes its commands against a fresh
   project, **Then** each step succeeds.

---

### User Story 3 - An agent receives the doctrine its project activated (Priority: P1)

An operator activates governance. An agent starting a work package receives it — on every load, for
every kind the project activated, not only on the once-per-project first render.

**Why this priority**: The largest declared-versus-in-force gap measured anywhere in the system.

**Three findings reshape this story.** First, the delivery gap is **not** a missing mission-type grain
in the runtime prompt path — that path supplies the grain correctly and renders 31.5 KB with 80
activated ids on first load. The gap is **bootstrap exhaustion**: the second load renders zero. The
callers that genuinely omit the grain are `agent/workflow.py` and `agent/workflow_executor.py`.
Second, styleguides and toolguides are **resolved and then dropped by the renderer** — a defect one
layer below the resolver, which fixing the resolver alone will not close.

Third, and discovered post-plan: **there are two delivery channels, and both under-deliver.** The
profile channel — a loaded profile, which the implement loop uses on every work package — renders
only profile-cited *directives and tactics*. A profile that resolves a procedure, styleguide,
toolguide or asset reaches its agent with none of them. This is the same defect as the action
channel's, one entry vector across.

**Independent Test**: Activate an artefact, load context twice, and assert it is present both times;
deactivate and assert absence.

**Acceptance Scenarios**:

1. **Given** an activated artefact of any supported kind, **When** an agent loads context for an
   applicable action **twice**, **Then** it is present on both loads.
2. **Given** an activated artefact that is deactivated, **When** an agent loads context, **Then** it
   is absent.
3. **Given** a named (action, mission_type) pair, **When** context is built, **Then** the delivered id
   set **equals** `activated ∩ action_reachable` for that pair — non-empty for at least directives,
   tactics, styleguides, toolguides and procedures on `software-dev`/`implement`.
4. **Given** a resolved styleguide or toolguide id, **When** the context is rendered, **Then** the id
   appears in the rendered output, not merely in the resolved bundle.
5. **Given** a caller that omits the mission-type grain, **When** context is built, **Then** the grain
   is supplied from the resolvable mission scope.
6. **Given** activation resolution raises a typed error, **When** the runtime builds a prompt, **Then**
   the error propagates rather than being swallowed into a degraded legacy render.
7. **Given** a project whose charter omits an `activated_<kind>` key entirely, **When** context is
   built, **Then** it receives nothing for that kind — absence is not "all built-ins".
8. **Given** an agent working a work package under a loaded profile, **When** its context is built,
   **Then** every kind the profile resolves reaches it — not only directives and tactics.
9. **Given** the delivery is exercised through the shipped command surface rather than through the
   context builder directly, **When** an agent starts an action, **Then** the payload is non-empty —
   a test that supplies the grain itself does not demonstrate delivery.

---

### User Story 4 - Activated-but-unreachable artefacts are named, not counted (Priority: P2)

An operator activates an artefact that no action can reach. Nothing says so today.

**Why this priority**: Remediation performed against the incidence metric moved it by 88% while
moving reachability by a fraction of that. Until reachability is the asserted property **and the
asserted artefacts are named**, a later mission cannot tell a fixed artefact from a nominally-wired
one.

**Independent Test**: Assert set equality against a pinned named set; confirm a nominally-wired but
unreachable artefact is reported as unreachable.

**Acceptance Scenarios**:

1. **Given** an artefact wired only to a source that is itself unreachable, **When** the reachability
   check runs, **Then** it is reported as unreachable.
2. **Given** a newly unreachable artefact, **When** the suite runs, **Then** the failure names the
   artefact — membership, not cardinality.
3. **Given** the enumerated wiring table in FR-015, **When** the mission completes, **Then** every
   artefact in it is reachable from at least one action under the FR-016 measure, and no artefact
   outside it was banked as progress.
4. **Given** the activation-identifier form is normalized, **When** the reachability set is computed,
   **Then** the normalization is declared and its effect is excluded from the mission's progress
   claim.

---

### User Story 5 - Reference pointers resolve and are not order-rigged (Priority: P3)

Every pointer in the reference block names a directory that does not exist, and the block is
truncated by a fixed cap whose ordering guarantees the same handful of entries every time — the
first tactic sits at index 34 behind a cap of 10.

**Why this priority**: Real but lower-consequence. Included because leaving it makes newly-delivered
doctrine look present while remaining unopenable.

**Independent Test**: Render the block, follow every pointer, and compare composition across actions.

**Acceptance Scenarios**:

1. **Given** a rendered reference block, **When** each pointer is followed, **Then** it resolves.
2. **Given** two different actions, **When** both blocks are rendered, **Then** their emitted sets
   differ.
3. **Given** more eligible references than the block carries, **When** it is rendered, **Then**
   selection is distributed across kinds rather than exhausted by the first kind in a fixed order.

---

### Edge Cases

- An asset identifier present at two tiers — the more specific wins; the shadowed tier is reported.
- An asset path escaping its root by traversal or symlink — refused.
- An organisation-pack asset nested below the type directory — must still be discovered.
- An activated identifier in the store's form but not the fetch selector's form — resolves, or fails
  naming the accepted form.
- A charter omitting an `activated_<kind>` key — receives nothing for that kind after migration.
- A consumer upgrading with a divergent mirror (config and charter disagreeing) — the charter wins,
  demonstrably.
- An action with no applicable activated doctrine — renders an honest empty result, distinguishable
  from a delivery failure.
- A render path reachable only from the test suite — either deleted or owned, never left resident.

---

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Derived writer set, not an enumerated one | As a doctrine author, I want the set of graph write paths to be derived and joinable, so that a writer added later cannot silently drop a field. | High | Open |
| FR-002 | Project-tier serializer derived and guarded | As a doctrine author, I want the project-tier writer derived from the model and covered by a test, so that the one unguarded write path stops dropping fields. | High | Open |
| FR-003 | Asset repository with tiered resolution | As a consumer, I want assets resolved across built-in, organisation and project tiers with recursive overlay discovery, so that an asset can be overridden like any other kind. | High | Open |
| FR-004 | Asset path resolution with containment | As a consumer, I want an identifier to resolve to a filesystem path, with escaping paths refused by a typed error, so that shipped executable logic is usable and safe. | High | Open |
| FR-005 | Operator commands for assets | As an operator, I want to list assets and resolve one by identifier, so that I can use a shipped asset without reading source. | High | Open |
| FR-006 | Kind-directory mapping is total by construction | As a doctrine author, I want the project-tier kind mapping hosted once and covered by the totality guard, so that scaffold and resolver cannot disagree about where an artefact lives. | High | Open |
| FR-007 | Asset scaffolding parity | As a doctrine author, I want the scaffold command to know the asset kind the validate command already accepts, so that authoring is not asymmetric. | Medium | Open |
| FR-008 | Retire the hard-coded asset path | As a maintainer, I want this repository's own asset consumer to go through the resolution surface, so that the fix is proven by its first user. | High | Open |
| FR-009 | Resolved doctrine reaches the render | As an agent, I want every kind the bundle resolves to appear in the rendered context, so that resolution is not undone one layer below it. | High | Open |
| FR-010 | Activation reaches the boundary on every load | As an agent, I want activated doctrine offered on every context load, not only the first, so that governance is in force rather than declared. | High | Open |
| FR-011 | Procedures deliverable at actions | As an operator, I want activated procedures delivered where they are already graph-reachable, so that activating one is not inert by construction. | High | Open |
| FR-012 | Grain and error policy at the omitting callers | As an agent, I want the callers that omit the mission-type grain to supply it, and activation errors to propagate rather than degrade silently. | High | Open |
| FR-013 | Distributed, untruncated reference selection | As an agent, I want the reference block composed across kinds at both render sites, so that later kinds are reachable at all. | Medium | Open |
| FR-014 | Reference pointers resolve | As an agent, I want every pointer I am handed to open, so that the block is usable rather than decorative. | Medium | Open |
| FR-015 | Enumerated wiring table | As an operator, I want the artefacts to be wired named in advance with their sources' reachability shown, so that "obvious" is a computation rather than a judgement. | Medium | Open |
| FR-016 | Reachability is a named, pinned property per channel | As a maintainer, I want reachability asserted as a named set per delivery channel under a named traversal, so that a nominal wiring cannot pass as a fix and reach is never claimed without delivery. | High | Open |
| FR-020 | The profile channel delivers every kind it resolves | As an agent working a work package under a loaded profile, I want every kind the profile resolves to reach my context, so that profile activation is a real entry vector rather than one that carries two kinds. | High | Open |
| FR-021 | Context carries navigable references | As an agent, I want the artefacts I am not given inline to be **named** with the guidance that says when to fetch them, so that complete delivery does not mean an unaffordable payload. | High | Open |
| FR-022 | Fetch-everything escape hatch | As an operator, I want one command that materialises the entire reachable closure inline, so that progressive disclosure is never the reason governance failed to arrive. | High | Open |
| FR-017 | Single activation authority | As an operator, I want one activation store, with the existing gate repointed before the mirror is removed, so that no gate goes vacuously green. | High | Open |
| FR-018 | Absence resolves to empty | As an operator, I want an omitted `activated_<kind>` key migrated to an explicit empty list, so that absence never means "all built-ins" at a delivery boundary. | High | Open |
| FR-019 | Documentation matches behaviour | As an operator, I want the asset how-to, the kind reference and the CLI reference to describe what actually ships, so that the documented remedy is followable. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Bounded consumer mutation | The only consumer-project file this mission may modify on upgrade is the charter/config activation surface, and only to normalize absence (FR-018) and remove the retired mirror (FR-017). Zero files are installed into consumer repositories. | Compatibility | High | Open |
| NFR-002 | Zero added suppressions | `ruff` and `mypy --strict` pass with **zero** new `# noqa`, `# type: ignore`, or per-file ignore entries added by this mission. | Maintainability | High | Open |
| NFR-003 | Delivery is complete, not truncated | For each delivery channel and each kind, the **union of inlined and linked** ids equals `gate(kind) ∩ channel_reachable`, where `gate` is a **total function over `NodeKind`** — `activated(kind)` for activation-eligible kinds, `ALL` for delivered-but-ungated kinds. Completeness is satisfied by naming, not by inlining: a link keeps an artefact addressable, a cap makes it invisible. **Any cap on the union is a defect.** Inlined bodies carry a shrink-only ceiling; links do not, because they are cheap. Budget pressure uses the existing `BUDGET_DEFAULT = 32_000` degradation path, never truncation. | Performance | High | Open |
| NFR-007 | Steady-state latency is measured and recorded | The steady-state context render's latency is measured before and after FR-010 and **recorded in the plan with figures**. Operator ruling 2026-07-28: the measured ~2x regression (≈982 ms → ≈1.94 s per action per load) is **accepted, not gated**. No caching obligation is imposed; the acceptance is explicit so a later regression is distinguishable from this one. | Performance | Medium | Open |
| NFR-004 | Ratchets are named sets or ledgered goldens | Defect-ceiling gates move shrinking-only or become named-set assertions. Composition goldens (node/edge counts) are exempt from the shrink-only rule and instead require a composition-ledger row — including when only a relation moved and cardinality did not. | Reliability | High | Open |
| NFR-005 | New branches carry tests | Every new branch and extracted helper is executed by a focused test in the same work package. | Maintainability | High | Open |
| NFR-006 | Fail-closed delivery | Asset and activation resolution failures raise a typed, named error that propagates to the caller. No path silently returns an empty or partial result where a caller reads it as success, and no seam swallows the error into a degraded render. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Layer direction is binding, in full | The dependency direction is `kernel ← doctrine ← charter ← specify_cli`. Shared vocabulary is hosted at the lowest layer and imported downward. This binds FR-001 (which needs a charter facade for the derived helper) as much as FR-004. | Technical | High | Open |
| C-002 | No automatic install | Resolution and explicit operator-invoked access only. Automatic installation of assets into consumer projects on upgrade is out of scope. | Technical | High | Open |
| C-003 | Ordinary change mode | Schema change with a consumer migration, not a bulk edit. No occurrence map. Operator ruling, 2026-07-28. | Process | Medium | Open |
| C-004 | Vocabulary collapse deferred | Collapsing the remaining parallel activation stores beyond FR-017 is out of scope. | Scope | High | Open |
| C-005 | Writer work carries no **inbound** dependency | FR-001/FR-002 must be independently landable so B1 is unblocked. This is a build-order claim only: FR-010 **enlarges FR-002's blast radius**, because the project-tier graph is merged into the graph every agent's context traverses. FR-002's tests must therefore cover the merged-graph read path, not only the write path. | Process | High | Open |
| C-006 | Red-first with executable mutation | Binds FR-001, FR-002, FR-009, FR-010, FR-011, FR-013, FR-014, FR-016 and NFR-006. Each lands as a distinct failing commit preceding its green commit. Where the property is "a silent drop cannot happen", the mutation must be **executable and committed** — a fixture that extends the model or removes the derivation — never a narrated manual edit. Review confirms the red commit exists in history. | Process | High | Open |
| C-007 | Non-obvious wirings deferred | An artefact is **obvious** iff (a) the relationship is attested in the artefact's own text, not inferred from topic adjacency, **and** (b) the proposed source is itself action-reachable under FR-016, or the edge is a `scope` edge from an action node. Everything failing (b) is deferred to an after-mission operator interview. Operator ruling, 2026-07-28. | Scope | High | Open |
| C-008 | Reach is never claimed without delivery | A claim that an artefact is "wired" must be demonstrated as reachable **in a named channel** under FR-016 **and deliverable by that channel**. Cascade is insufficient: it walks outbound from the activation seed, so any inbound edge satisfies it, including one from an unreachable source. A channel that reaches an artefact it cannot render is this mission's own defect class, not a passing measure. | Technical | High | Open |
| C-009 | Identifier normalization is not progress | Normalizing the activation-identifier form changes the measured unreachable set by roughly twenty artefacts without making anything reachable. It must land as a separate, declared change and is explicitly excluded from SC-005. | Technical | High | Open |
| C-010 | Close the class, not the instances | Where the repository already ships a mechanism that closes this defect class by construction — derivation-from-`model_fields`, totality-or-explicit-exemption — this mission extends that mechanism rather than adding a hand-maintained site. Operator ruling, 2026-07-28. | Technical | High | Open |
| C-011 | Delivery cadence follows the relation | `requires` edges are followed **eagerly** and their targets delivered inline; `suggests` edges are emitted as **links** carrying the edge's `when` as fetch guidance. A link is not a truncation — the artefact stays named and addressable, which is the property NFR-003 protects. Governed by [ADR 2026-07-28-1](../../docs/adr/3.x/2026-07-28-1-progressive-disclosure-of-doctrine-context.md). | Technical | High | Open |
| C-012 | Progressive disclosure lands before every-load delivery | Links-not-bodies is the **default** cadence, and it must be in force **before** FR-010 switches on delivery-on-every-load. Shipping every-load delivery with bodies still inlined is the context explosion this mission would otherwise cause. Ordering is binding: the cadence rule precedes the every-load switch. Deferred to a follow-up: instructing agents to fetch (affects utilization, not payload safety) and backfilling `when` on 118 edges. | Scope | High | Open |

### Key Entities

- **Asset**: A doctrine artefact whose payload is a file rather than prose. Identified by a stable
  identifier, declared by a manifest, resolvable to a path. Not charter-activatable; reached by
  resolution.
- **Activation**: An operator's declaration that an artefact applies. Delivered only where the
  artefact is reachable from the action being performed — an intersection, not an entry vector.
- **Action grain**: The (action, mission_type) pair determining which activated doctrine applies.
- **Graph edge / node / document**: The relationship records and their container. The delivery
  property is that every write path preserves every declared field, at all three levels.
- **Delivery channel**: A path by which doctrine reaches an agent. There are **two**, and each has its
  own traversal, its own reachability set, and its own delivery obligation:
  - **Action channel** — `resolve_context` seeded from action nodes. Under-delivers styleguides and
    toolguides today.
  - **Profile channel** — a loaded profile's own resolution over `requires` / `specializes_from`,
    exercised by the implement loop when an agent works a work package. Under-delivers everything
    except directives and tactics today.
- **Reachability**: Attainability by the **named traversal of a named channel**. Distinct from
  **incidence** (touching any edge) and from **cascade** (outbound from the activation seed). Four
  lenses measured four different values because the traversal was unnamed; FR-016 names one per
  channel. **Reach is never claimed without delivery** — a channel that reaches an artefact it cannot
  render is the mission's own defect class, not a passing measure.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For the `software-dev` mission type, an operator can activate any supported kind and
  observe it in an agent's context on **both** the first and a subsequent load, for all six kinds
  including procedures. Coverage for other mission types is stated per-type rather than assumed;
  actions that resolve to zero artefacts of any kind are named as known gaps rather than passing
  silently.
- **SC-002**: Deactivating an artefact removes it from the agent's context — asserted at the surfaces
  where this is false today (procedures, styleguides, toolguides, the steady-state render), not only
  where it already holds.
- **SC-003**: A wheel installed into a clean environment, with this repository absent from resolution
  inputs, resolves a shipped asset identifier to a usable path.
- **SC-004**: A test that extends the edge model with an unknown field and round-trips it through
  **every registered writer** preserves it; adding a write path that bypasses the derived helper fails
  the suite naming that site.
- **SC-005**: The pinned named sets of activated-but-unreachable artefacts — **one per delivery
  channel** — shrink by **exactly the artefacts enumerated in FR-015**, under the FR-016 traversals,
  with the identifier normalization of C-009 excluded and the baseline commit declared. Membership,
  not cardinality. The pinned sets are **partitioned into `{not-a-node, node-but-unreachable}`**:
  roughly a quarter of today's unreachable count is activated identifiers that are not graph nodes at
  all, and C-009 bars that partition from counting as progress.
- **SC-006**: Every reference pointer emitted resolves, **and** at least a stated minimum number is
  emitted per action for `software-dev`, **and** the emitted sets differ across at least two actions.
- **SC-007**: After upgrade, a consumer project's activation surface has exactly one authority, no
  retired mirror, and explicit empty lists where keys were absent — demonstrated against a
  **divergent-mirror fixture** where the two stores disagree.
- **SC-008**: The published asset how-to executes end to end against a fresh project.
- **SC-009**: A committed test adds a relationship field within the test and asserts survival through
  every registered writer; B1 extends it rather than re-deriving it.
- **SC-010**: Every reachable artefact not delivered inline is **named** in the context's reference set
  with its fetch guidance, and is retrievable by that name — completeness is preserved without
  inlining. Verified by asserting the union of inlined ids and referenced ids equals the delivered set
  NFR-003 defines.
- **SC-011**: A single command materialises the entire reachable closure inline, and its output is a
  superset of every progressive-disclosure render for the same grain.

---

## Deferred with owners

Recorded so they are not rediscovered as surprises. None is a prerequisite of this mission.

Three rows from the first revision are **resolved and removed**: profile-seeded reachability (now two
channels, FR-016/FR-020), `_render_bootstrap` (ruled: delete), and agent-facing asset delivery (ruled:
delivered, FR-009).

| Item | Owner |
|---|---|
| `project_drg._KIND_TO_NODE_KIND` project-tier node projection | #3038 proper |
| The eight-site kind-vocabulary consolidation beyond the project-tier mapping | #2981 |
| Runtime→doctrine ratchet widening (61 function-local imports) | #2986 |
| `operating-procedures` field-vs-edge decision | #2994 |
| The four `action:plan/*` nodes resolving to zero artefacts of any kind | **Needs an issue** — no number yet |
| The AST gate on dict-literal edge payloads (the registry's conceded blind spot) | **Needs an issue** — no number yet |
| Agents *instructed* to fetch linked artefacts (prompt templates, 12 agent dirs, mission-steps) | Deferred by C-012 — affects link utilization, not payload safety. [ADR 2026-07-28-1](../../docs/adr/3.x/2026-07-28-1-progressive-disclosure-of-doctrine-context.md) |
| Backfilling `when` on the 118 uncovered `suggests` edges | Deferred — doctrine content authoring, mission B2 territory. Uncovered edges render a stated default so absence stays visible |

**Withdrawn from this table, 2026-07-28:** *links-not-bodies as the default payload*. It is now **in
scope** (C-011, C-012, WP15). Deferring it would have shipped delivery-on-every-load with bodies still
inlined — the context explosion the ADR exists to prevent, with its mitigation one mission away.
