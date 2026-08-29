# Implementation Plan: Doctrine Delivery Reachability

**Branch**: `feat/doctrine-delivery-reachability` | **Date**: 2026-07-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/doctrine-delivery-reachability-01KYMXD6/spec.md`

**Branch contract**: current branch `feat/doctrine-delivery-reachability`; planning/base branch
`feat/doctrine-delivery-reachability`; final merge target `feat/doctrine-delivery-reachability`
(the reconciliation target — a PR to `upstream/main` is raised after consolidation).
`branch_matches_target: true`.

## Summary

Close the **delivery layer** of the declared-but-inert defect class: a declaration that passes every
check and still reaches nobody. Three strands share one mechanism — *a projection table narrower than
the enumeration it projects, silenced by a `.get(…, default)` or a literal `[]`*.

Per C-010 the mission **extends the two class-closing mechanisms the repository already ships**
(derivation-from-`model_fields`; totality-or-explicit-exemption) rather than hand-fixing three
instances. Concretely: a **writer registry** the field-completeness test iterates, and the
**totality guard** extended over the project-tier kind mapping.

Delivery is then made real end to end — assets become resolvable *and* bundle-delivered, activated
doctrine reaches the render on every load for every kind, and reachability becomes a **named set
under a named traversal at two named depths** rather than a count that four independent lenses
measured four different ways.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pydantic v2 (`model_fields`, `ConfigDict`), ruamel.yaml, typer, rich, pytest
**Storage**: On-disk YAML/JSONL — sharded DRG fragments (`src/doctrine/*.graph.yaml`),
`.kittify/charter/charter.yaml`, `.kittify/config.yaml`, `status.events.jsonl`
**Testing**: pytest; ATDD red-first per C-006 with **executable, committed** mutation proofs
(model-extension fixtures, not narrated manual edits); named gate files only — never the full
architectural suite in a WP loop
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows), distributed as a PyPI wheel; built-in
doctrine ships as package data resolved via `importlib.resources`
**Project Type**: single
**Performance Goals**: Steady-state context render stays within the existing
`BUDGET_DEFAULT = 32_000` budget, handled by the degradation-to-fetch-stanza path — **never by
truncation** (NFR-003). Delivered id set per boundary carries a shrink-only ceiling of 90.
**Constraints**: Layer direction `kernel ← doctrine ← charter ← specify_cli` (C-001) — the derived
serializer lives in `doctrine` and must reach `specify_cli` through a charter facade, not a
function-local import. Zero new `# noqa` / `# type: ignore` (NFR-002). Complexity ceiling 15.
Consumer mutation bounded to the activation surface (NFR-001).
**Scale/Scope**: 310 DRG nodes / 781 edges; 184 activated artefacts; 24 action nodes; 18 agent
profiles. Estimated 45–60 files across nine concerns.

### Planning decisions taken (2026-07-28)

Recorded via the Decision Moment protocol; all four resolved, none deferred.

| Decision | Outcome |
|---|---|
| Action-channel traversal | `resolve_context` asserted at **both** d=1 (compact, the steady state) and d=2 (bootstrap) |
| Delivery channels | **Two** — the action channel and the **profile channel**. Each carries its own named reachability set *and* its own delivery obligation (FR-020). Reach is never claimed without delivery (C-008) |
| Writer class-closure shape | **Registry** every edge-serializing writer joins — but in **three shapes**, not one (see IC-01) |
| Asset delivery | Assets are **delivered**, not activation-gated. Expressed as a **total per-kind gate function**, not an enumerated exception |
| FR-010 latency | The measured ~2x steady-state regression is **accepted and recorded**, not gated (NFR-007) |

### Corrected measurements (post-plan squad, re-derived with `resolve_context`)

The pre-squad figures in this plan were produced by a hand-written BFS — **the method this plan's own
binding-method note forbids**. They are withdrawn. Re-derived:

| measure | withdrawn figure | **correct figure** |
|---|---|---|
| activated-and-unreachable, action channel, d=1 | 136 | **103** |
| activated-and-unreachable, action channel, d=2 | 87 | **96** |
| contribution of profile seeds to `resolve_context` | +43 / +58 | **0 at both depths** |

**Why profile seeding contributes zero to `resolve_context`**: that function's step 1 walks **`scope`
edges only** from the seed, and `agent_profile` nodes have **97 outbound `requires`, 4
`specializes_from`, and zero outbound `scope`**. The profile channel is therefore **not** expressible
as a seed set for `resolve_context` — it is a **separate traversal** over `requires` /
`specializes_from`, which is why it is modelled as its own channel rather than folded into the walk.

**This does not make profiles irrelevant — the opposite.** Profiles are loaded by the implement loop
on every work package, so they are a first-class entry vector. What the measurement shows is that the
profile channel resolves artefacts it **cannot render**: `_render_profile_directives` and
`_render_profile_tactics` are the only profile render paths, so a profile-resolved procedure,
styleguide, toolguide or asset reaches nobody. `procedure:onboard-external-agent-to-pack` — PR
#3007's exemplar, reached from `agent_profile:doctrine-daphne` by a `requires` edge — is a live
instance. FR-020 owns it.

Two further corrections: the d=1↔d=2 spread is **7 nodes, not 49** (which withdraws Complexity row 3's
original justification), and **25 of the 184 activated identifiers are not graph nodes at all**, so
roughly a quarter of any "unreachable" count is C-009 normalization that must not be banked as
progress. SC-005 now partitions the pinned sets accordingly.

**Binding-method note (unchanged and now proven necessary).** The assertion MUST call
`doctrine.drg.query.resolve_context` for the action channel and a named `walk_edges` for the profile
channel. Every hand-rolled BFS in this mission's history has produced a wrong number, including the
one in this plan's first revision.

### Recorded performance acceptance (NFR-007)

Measured on this branch:

```
build_charter_context (compact):   982 ms   <- today's steady state
_load_action_doctrine_bundle:      961 ms   <- what FR-010 moves onto that path
  filter_graph_by_activation:      517 ms   <- 552 ruamel YAML loads per call, uncached
  resolve_context d=1 / d=2:         0.2 ms
```

FR-010 takes the steady-state render from ≈982 ms to ≈1.94 s, per action, per agent load, in every
consumer project. **Operator ruling 2026-07-28: accepted, not gated.** No caching obligation is
imposed. The figures are recorded here so a later regression is distinguishable from this one, and so
the memoization option (`_resolve_activated_urns_by_kind` per `PackContext`; the merged+filtered graph
per `(repo_root, org_root, pack_context)`) is on the record as available rather than unknown.

**Consequence of the asset-delivery choice.** `asset:common-docs-structural-lint` has four inbound
`requires` edges and **all four sources are unreachable** — the `common-docs` cluster is a
strongly-connected island no action scopes. Building bundle delivery for assets without wiring that
cluster ships the delivery path while the only shipped asset still fails to arrive. The cluster is
therefore folded into FR-015's enumerated table, subject to C-007's source-reachability precondition.

## Charter Check

*GATE: passed before Phase 0. Re-checked after Phase 1 — see below.*

| Charter gate | Status |
|---|---|
| ATDD-first discipline (binding, C-011 of the charter) | **Satisfied by design** — C-006 binds nine requirements to red-first with executable mutation proofs |
| Canonical sources, never improvise | **Satisfied** — C-010 mandates extending the shipped mechanisms; FR-016 mandates calling `resolve_context` rather than reimplementing it |
| Single canonical authority | **Directly served** — FR-017 collapses the activation stores to one |
| No direct pushes to `origin/main` | **Satisfied** — lane work consolidates into the reconciliation branch; a PR follows |
| Complexity ceiling 15 / no suppressions | **NFR-002**; `context.py` is 3,227 lines and several concerns land in it — see Complexity Tracking |
| Terminology canon (Mission, not Feature) | No new user-facing vocabulary; the terminology guard runs before push |
| Tiered rigour + tracer files | Nine concerns carry explicit sequencing; mission tracer maintained per standing orders |

**Post-Phase-1 re-check**: no new violations. The one pre-existing tension (module size) is recorded
in Complexity Tracking with a bounded response rather than a refactor this mission does not own.

## Project Structure

### Documentation (this mission)

```
kitty-specs/doctrine-delivery-reachability-01KYMXD6/
├── plan.md              # This file
├── spec.md              # Revised post-squad
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
├── checklists/          # requirements.md (run 2, post-squad)
├── research/            # Discovery + squad artefacts (5 documents)
└── tasks.md             # Phase 2 — NOT created by /spec-kitty.plan
```

### Source Code (repository root)

```
src/
├── doctrine/                          # lowest layer — hosts shared vocabulary
│   ├── artifact_kinds.py              # kind enumeration + project-tier dir mapping (hoisted here)
│   ├── assets/
│   │   ├── models.py                  # AssetManifest (exists)
│   │   └── repository.py              # NEW — tiered resolution, rglob overlay, resolve_path
│   ├── service.py                     # + assets property; _PROJECT_KIND_DIRS retired to artifact_kinds
│   └── drg/
│       ├── models.py                  # + DRGGraph model_config
│       ├── merge.py                   # org-tier edge bridge joins the registry
│       ├── query.py                   # resolve_context — the FR-016 authority (read-only here)
│       └── migration/extractor.py     # derived helper + the writer registry it anchors
├── charter/
│   ├── drg.py                         # facade so specify_cli reaches the derived helper (C-001)
│   ├── pack_context.py                # activation authority; absence semantics
│   ├── resolver.py                    # the four hardcoded [] literals
│   ├── compact.py                     # steady-state rail — must carry all kinds
│   ├── context.py                     # bundle, slot table, render, reference block
│   └── synthesizer/project_drg.py     # writer 3 — joins the registry
├── specify_cli/
│   ├── migration/rewrite_opposed_by.py    # writer 2 — joins the registry
│   ├── cli/commands/doctrine.py           # asset subcommands + scaffold kind map
│   ├── cli/commands/agent/workflow.py     # FR-012 grain
│   ├── cli/commands/agent/workflow_executor.py
│   └── upgrade/migrations/                # NEW — activation authority + absence normalization
└── runtime/next/prompt_builder.py     # exception policy only (grain already correct)

tests/
├── doctrine/drg/                      # registry field-completeness, kind totality, reachability
├── charter/                           # bundle delivery, render, compact rail, reference block
├── docs/                              # asset consumer repointed off _REPO_ROOT
└── architectural/                     # named gate files only
```

**Structure Decision**: Single project, existing four-layer structure preserved. The only new module
is `src/doctrine/assets/repository.py`; the only new facade is `src/charter/drg.py`. Two mappings are
**hoisted downward** to `src/doctrine/artifact_kinds.py` — the module whose docstring already declares
that no second kind enumeration may exist — and imported down by charter and specify_cli, which is
C-001-legal in all three directions.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Four concerns land in `src/charter/activation/context.py` (3,227 lines) | The bundle, the slot table, the render and the reference block all live there; splitting the module is a different mission with its own blast radius | Extracting a resolution surface first would double this mission's diff and put a refactor on the critical path of B1's unblock. **Bounded response**: no concern may *grow* `context.py` net — each extracts the logic it touches into a named helper, so the module shrinks or holds flat |
| The writer registry is hosted in `specify_cli`, the top layer, rather than beside the derived helper in `doctrine` | A registry naming charter and specify_cli members cannot live in `doctrine` — it reds `test_layer_rules.py:282` and `:293`, two of this mission's own named gates. `charter` fares no better (`:311`). Only the top layer can statically hold all members | Import-time self-registration is the obvious alternative and is **worse**: membership becomes import-order-dependent, which re-opens the "a writer that never joins is invisible" gap the contract already concedes. Tests are not layered, and the precedent exists — `tests/doctrine/.../test_model_strictness_roundtrip.py:542` already imports `specify_cli.migration` |
| Four named sets rather than one: two channels × two depths on the action side | Reach without delivery is this mission's defect class (C-008), so each channel must be measured where it delivers. Compact is the steady state and the stricter action-channel depth | A single unioned set was the original plan and is **unsound** — three independent lenses showed it certifies artefacts that no channel renders. The d=1↔d=2 spread turned out to be 7 nodes rather than 49, so the two *depths* are cheap; the two *channels* are what carry the cost, and they are not optional |

## Implementation Concern Map

> **Note**: Implementation concerns are NOT work packages and are NOT executable units.
> `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Writer registry and derived serialization

- **Purpose**: Close the graph-serialization defect class by construction — a registry every
  edge/node-serializing site joins, with the field-completeness test iterating the registry rather
  than a hand-written list.
- **Relevant requirements**: FR-001, FR-002; SC-004, SC-009; C-006, C-010
- **Affected surfaces**: `src/doctrine/drg/migration/extractor.py` (derived helper + registry anchor),
  `src/doctrine/drg/models.py` (`DRGGraph.model_config`), `src/doctrine/drg/merge.py`
  (`_bridge_org_edge_to_drg_edge`), `src/charter/activation/synthesizer/project_drg.py`,
  `src/specify_cli/migration/rewrite_opposed_by.py`, `src/charter/drg.py` (new facade),
  `tests/doctrine/drg/test_model_strictness_roundtrip.py`,
  `tests/charter/synthesizer/test_project_drg.py`
- **Sequencing/depends-on**: none — this is the B1 unblock and must carry **no inbound dependency**
  (C-005)
- **Risks** (revised post-squad):
  - **The registry needs three shapes, not one.** Three of the five named members cannot satisfy a
    single `edge_to_mapping` Protocol: `project_drg._serialize_graph` is `(DRGGraph) -> str` with the
    dicts built inline (extracting them is a *prerequisite task*, not a registry join);
    `_dump_graph_document` is `(DRGGraph, Path) -> None` and owns document-level keys; and the org
    bridge **constructs** a `DRGEdge` from a fragment edge rather than serializing one. Model as
    `MappingWriter`, `DocumentWriter`, `ModelBridge`.
  - **Host the registry in `specify_cli`.** See Complexity Tracking — a `doctrine`-layer tuple naming
    charter and specify_cli members reds two of this mission's own gates.
  - **`charter/drg.py` already exists** (532 lines, 24-entry `__all__`) and `rewrite_opposed_by.py:97`
    already imports through it. No facade is created; the work is exporting the derived helper.
  - **The derived helper is not yet total.** `_render_for_yaml` returns `None` for `None` *and for an
    empty list*, and `_model_to_dict` drops the key — proven: a novel `impacts: str|None = None` or
    `impacts: list[str] = []` field is dropped by **both** derived writers, while
    `is_symmetric: bool = False` survives. Since B1's `impacts` is plausibly list-shaped, W-1 must
    assert over a **fully-populated** instance and carry a separate obligation for empty values, or
    the flagship gate is vacuous for the field it exists to protect.
  - **`extra="forbid"` on `DRGGraph` is an unowned consumer break.** It converts any org-pack graph
    document with an unknown top-level key from silently-accepted to a hard load failure on upgrade.
    NFR-001 bounds file *mutation* and is silent on pack *rejection*. Either give it a typed
    error + migration, or move it off the lane that lands first and alone.
  - `project_drg` is the unguarded writer and leads; `rewrite_opposed_by` is **already guarded** and
    needs membership, not a new test. Per C-005, FR-002's tests must cover the **merged-graph read
    path**, because the project-tier graph is merged into the graph every agent's context traverses
    once IC-06 lands.
  - **The mutation fixture works via subclassing** — models are not frozen (only `extra="forbid"`),
    attribute injection and extra kwargs are both rejected, and `DRGGraph` preserves the subclass all
    the way to the writers. Name this in the contract so three WPs do not each rediscover it.

### IC-02 — Kind mapping totality

- **Purpose**: Extend the totality-or-explicit-exemption guard over the project-tier kind mapping,
  hosting it once in `artifact_kinds.py` instead of four hand-maintained copies.
- **Relevant requirements**: FR-006, FR-007; C-001, C-010
- **Affected surfaces**: `src/doctrine/artifact_kinds.py`, `src/doctrine/service.py:19`,
  `src/charter/activation/kind_vocabulary.py:79`, `src/charter/activation/pack_manager.py:136`,
  `src/specify_cli/cli/commands/doctrine.py:442`, `tests/doctrine/drg/test_kind_mapping_totality.py`
- **Sequencing/depends-on**: none
- **Risks** (revised post-squad):
  - **The four copies are not four of a kind, and two are worse than exempted — they are invisible.**
    `charter/kind_vocabulary.py:79` and `charter/pack_manager.py:136` are `dict[ArtifactKind, str]` and
    are explicitly exempted. But `doctrine/service.py:19` is `dict[str, str]` keyed by **plural**
    strings and `cli/commands/doctrine.py:442` is `dict[str, str]` keyed by singular — the totality
    guard's AST scan matches only `EnumName.MEMBER` attribute keys, so it **never discovers them at
    all**. Converting those two call sites to `ArtifactKind` keys is part of the definition of done, or
    the hoist leaves the guard blind at precisely the two sites #3038 names.
  - **The hoist is the obligation; the guard is the ratchet.** The guard checks each dict independently
    against the enum and can never detect that two copies *disagree* — which is the actual defect
    (I-A4). A work package could satisfy "extend the totality guard" by adding `asset` to all four
    copies and never hoisting, and go green.
  - **Scaffold parity targets the wrong surface.** `doctrine new --kind asset` is rejected at `:606`
    against `_CANONICAL_KIND_SINGULAR_TO_PLURAL` (`:431`, 8 of 12 kinds), and then needs a stub from
    `_stub_template` (`:464`) — an eight-arm `if`-chain over kind strings ending in `raise ValueError`.
    `:442` is consulted only at `:626`, after both gates. So IC-02 and IC-03 can land fully green and
    `doctrine new --kind asset foo` still exits 2. The if-chain is a kind projection **the totality
    guard cannot see** because it is not a dict. `_CANONICAL_KIND_SINGULAR_TO_PLURAL` also duplicates
    `ArtifactKind._PLURALS` eleven lines above the dict this concern edits.
  - The three copies use three different key/value conventions and three different `.get` fallbacks;
    the hoist must declare the canonical form and the adapter at each call site.

### IC-03 — Asset resolution and operator surface

- **Purpose**: Make a shipped asset addressable by identifier from a consumer installation.
- **Relevant requirements**: FR-003, FR-004, FR-005, FR-008; SC-003; C-002
- **Affected surfaces**: `src/doctrine/assets/repository.py` (new), `src/doctrine/assets/__init__.py`,
  `src/doctrine/service.py`, `src/specify_cli/cli/commands/doctrine.py`,
  `tests/docs/test_docs_structural_lint.py`
- **Sequencing/depends-on**: IC-02 (the project-tier directory for assets is part of the hoist)
- **Risks**: **Anchor asymmetry** — `_built_in_dir("assets")` returns `<root>/assets/built-in` and blob
  paths anchor at its *parent*, while org/project dirs anchor at themselves; getting it wrong yields
  `.../assets/built-in/built-in/...`. `BaseDoctrineRepository._project_scan` is **non-recursive**, so
  an org-pack manifest at the ADR-mandated nested path is never found — override to `rglob`.
  Containment must call `doctrine.drg.org_pack_config.resolve_relative_path_within_root` directly,
  because the validator's helper lives in `specify_cli` and C-001 forbids the import. SC-003 must run
  against a **built wheel in a clean environment**, since in-repo the dev-layout fallback cannot fail —
  and **that harness has no home in this plan**. Name the test path and the CI job before tasks; a
  criterion with no artefact is this mission's own defect class.
  The `_project_scan` override must return `list[Path]`, not `Iterable[Path]` — the base declares
  `list[Path]` and widening a return type in an override is a Liskov violation mypy will flag, which
  NFR-002 forbids silencing.

### IC-04 — Reachability as a named, pinned property

- **Purpose**: Replace incidence counting with named-set assertions under a named traversal at two
  named depths, seeded from actions **and** activated agent profiles.
- **Relevant requirements**: FR-015, FR-016; SC-005; C-007, C-008, C-009
- **Affected surfaces**: `tests/doctrine/drg/migration/test_extractor_projection.py`
  (`_INTENTIONAL_ORPHANS`, `_ACTIVATED_BUT_UNREACHABLE`, `_orphan_urns`), a reachability helper,
  `_CURATED_ARTIFACT_EDGES` or authored `*.graph.yaml` fragments
- **Sequencing/depends-on**: **IC-01** — undeclared in the first revision. Authoring FR-015's edges
  regenerates up to 14 `src/doctrine/*.graph.yaml` fragments through `_dump_graph_document`, the exact
  function IC-01 rewrites, and `test_shipped_graph_is_fresh_and_byte_identical` pins them. Landing
  IC-04 first regenerates them twice, with a changed serializer in between. Ledger both regeneration
  events under NFR-004.
- **Expected split**: this is three concerns and will become three work packages — (a) rename the
  incidence set to a named reachability set, (b) build the per-channel assertions, (c) author FR-015's
  edges. (c) is a production-data change with a 14-file regeneration side effect; (a) and (b) are gate
  changes with different red-first shapes.
- **Risks**: The assertion **must call `resolve_context`**, not reimplement the walk. `_ACTIVATED_BUT_
  UNREACHABLE` currently measures **edge incidence** despite its name — landing a genuine reachability
  set beside it is a readability trap; rename in the same WP. FR-015's table must show each proposed
  source's own reachability (C-007b) or "obvious" collapses into implementer taste. C-009 forbids
  banking the id-normalization swing (~20 artefacts) as progress. **The `common-docs` cluster is in
  scope here** because IC-06 delivers assets and the only shipped asset sits behind it. Edges land in
  `_CURATED_ARTIFACT_EDGES`, which mission **B2 retires** — the destination and handoff must be
  recorded.

### IC-05 — Activation authority and absence semantics

- **Purpose**: One activation store; absence means empty, not "all built-ins".
- **Relevant requirements**: FR-017, FR-018; SC-007; NFR-001, NFR-006
- **Affected surfaces**: `src/charter/activation/pack_context.py` (`_read_activated_*`,
  `_load_charter_activation_source`), `.kittify/config.yaml` surface, a new upgrade migration,
  `tests/doctrine/drg/migration/test_extractor_projection.py::_charter_activated_urns`
- **Also owns (moved from the dissolved IC-07)**: the **fail-closed policy** (FR-012's error half,
  NFR-006). This is an *authority* invariant — the surface that raises owns the guarantee that the
  error surfaces — so splitting raise and catch across two concerns left nobody owning the end-to-end
  assertion. IC-05 carries it, including `prompt_builder`'s `except Exception: pass`, with an
  end-to-end test that an activation failure reaches an operator.
- **Sequencing/depends-on**: **none.** The first revision claimed IC-04, justified by "the gate must
  be repointed before the mirror is deleted" — but that is IC-05's *own* work, not a dependency. The
  real coupling is a **file collision**: IC-04 renames `_ACTIVATED_BUT_UNREACHABLE` while IC-05
  rewrites `_charter_activated_urns`, both in the same 604-line test file, with
  `test_activated_but_unreachable_orphans_are_really_activated` consuming both. Assign to one lane or
  serialize — they are otherwise parallel, which shortens the critical path.
- **Ordering caveat that is real**: IC-05 owns `activated`, and the delivery predicate is
  `gate ∩ reachable`. Identifier normalization (I-V4 / C-009) moves the set by ~25 artefacts, so
  **extract normalization as its own slice landing before IC-04's pin**, and give IC-04 an explicit
  re-pin obligation if IC-05 moves the set.
- **Risks**: **The pointer field is `charter:`, which already ships and is honoured — not
  `charter_file:`, which exists nowhere.** Minting the second name reintroduces the defect FR-017
  removes. `_charter_activated_urns` reads the dead mirror; deleting it first makes that gate's floor
  assertion fail and its stray guard **vacuously true**. SC-007 requires a **divergent-mirror
  fixture** — the only case that proves which store won. The absence migration mutates consumer
  configs, which is why NFR-001 was amended.
  - **Two prior migrations already fought over this surface, in opposite directions**, and the mirror
    survived both. `m_unify_charter_activation.py` made `config.activated_<kind>` the single
    authority; `m_unify_charter_activation_finalize.py` folded it into `charter.yaml` and minted the
    `charter:` pointer — yet `.kittify/config.yaml` on this checkout **still carries** the
    `activated_*` keys alongside the pointer. FR-017 is the third pass. IC-05's definition of done
    must include reading both, stating why the finalize migration did not take, and declaring the
    ordering constraint its docstring already carries.

### IC-06 — Delivery rail carries every kind, to the render

- **Purpose**: Make resolution and delivery the same thing — every kind the bundle resolves appears in
  the rendered context, on every load.
- **Relevant requirements**: FR-009, FR-010, FR-011; SC-001, SC-002; NFR-003, NFR-006
- **Affected surfaces**: `src/charter/activation/context.py` (`_ActionDoctrineBundle`,
  `_ACTION_BUNDLE_SLOT_BY_KIND`, `_render_bootstrap_text`, the compact returns), `src/charter/activation/compact.py`,
  `src/charter/activation/resolver.py`
- **Also owns (moved from the dissolved IC-07)**: the **mission-type grain** at `workflow.py:738` and
  `workflow_executor.py:459`. It selects the bundle IC-06 delivers and is inert without it, exactly as
  `resolver.py`'s `[]` literals are. Keeping it downstream would let IC-06 pass SC-001 through a test
  that supplies the grain itself while the shipped CLI still emits an empty bundle on every real
  invocation — `_load_action_doctrine_bundle` degrades to empty when `resolved_type is None`. US3
  scenario 9 exists to close that hole.
- **Expected split**: two work packages — FR-009 (render carries every resolved kind; a payload
  change) and FR-010 (delivery on every load; a control-flow change, and the mission's only NFR-007
  exposure).
- **Sequencing/depends-on**: IC-04, IC-05
- **Risks**:
  - FR-010 is a **control-flow** change, not a payload change — the compact returns fire *before* the
    bundle is computed. Cost is measured and **accepted** under NFR-007.
  - **"The compact returns" is four sites in two functions**, not one: `context.py:208` (action not in
    `BOOTSTRAP_ACTIONS`, returning before state is prepared), `:237` (depth below minimum), and
    `:3201` / `:3207` in the **`--json` payload builder**, which has its own `mode` handling and its
    own bundle call at `:3213`. The `--json` path is what `quickstart.md` uses to *observe* the defect
    and where SC-001/SC-002 will be measured — it was absent from the first revision's surfaces.
  - **`depth` means two things.** `_EXTENDED_CONTEXT_DEPTH = 3` gates styleguide and toolguide
    rendering (`:1149-1157`), and `resolve_context`'s docstring confirms depth "also controls extended
    artifact inclusion". At the pinned depths d=1 and d=2, I-B1 is **structurally unachievable for
    exactly the two kinds** this mission calls the sixth delivery defect. IC-06 owns retiring or
    repointing that gate, and splitting the overloaded parameter (a `suggests` hop cap and a render
    verbosity tier are two concepts on one integer).
  - **`CompactView` carries two kinds** (`compact.py:38`) and its docstring calls them "the contract
    surface"; `_render_compact_governance` (`:2788`) accepts only `directive_ids`/`tactic_ids`.
    Widening the steady-state rail is a signature change and a documented-contract widening, not only
    a payload change. Assertions must read the **rendered compact text**, not the bundle.
  - **Do not create a sixth per-kind projection.** `_classify_artifact_urns` (`:729`) already builds
    `dict[str, list[str]]` and destroys it at the return boundary (`:748`) into a positional 4-tuple.
    There are already five parallel per-kind projections in this path with five different subsets, and
    every subset difference is a live delivery defect. Return the mapping — `ids_by_slot:
    Mapping[str, tuple[str, ...]]` with the slot set derived from `_ACTION_BUNDLE_SLOT_BY_KIND` — so
    totality and delivery become one statement and the compact rail widens for free. If this is
    deferred, **record the deferral**: a sixth projection is the tax the next mission pays.
  - **The slot table is already total and already guarded**, with a verdict comment per group and
    `action_bundle_bucket` raising on unmapped kinds. The work is flipping `PROCEDURE` and `ASSET`
    from `None` to real slots, plus per-kind rationale — not building the guard. **This reverses PR
    #3007 WP03's recorded verdict** ("state them, not start rendering them") for two of twelve
    exclusions; record the reversal and the criterion, or the next mission flips two more by the same
    unstated reasoning.
  - **Express the asset carve-out as a total gate function.** `activated(asset)` is `∅` by
    construction, so an equality stated as `activated ∩ reachable` makes `asset_ids = []` the
    conforming implementation. `gate(kind)` must be a column of the same NodeKind-keyed table —
    `activated(kind)` for activatable kinds, `ALL` for delivered-but-ungated ones. `TEMPLATE`'s `None`
    then acquires a stated reason instead of being ASSET's untreated twin.
  - Populating `GovernanceResolution` from anywhere but the canonical `PackContext` path creates a
    **fifth activation reader**. It also still lacks an asset field while the bundle gains one — a
    narrower projection is this mission's defect class.

### IC-07 — Profile channel delivery

> **Replaces the first revision's "Caller grain and error propagation"**, which was a leftovers bin:
> two call sites and one `except` clause sharing only the word "caller", splitting an authority
> invariant across the surface that raises and the surface that catches. Grain moved to IC-06,
> fail-closed policy to IC-05, and the concern number was reused for the defect the squad surfaced.

- **Purpose**: Make the profile channel deliver every kind it resolves. Profiles are loaded by the
  implement loop on every work package, so they are a first-class entry vector — but only
  profile-cited **directives and tactics** render today.
- **Relevant requirements**: FR-020, FR-016 (profile-channel set); SC-001, SC-005; C-008
- **Affected surfaces**: `src/charter/activation/context.py:2745-2764` (`_render_profile_sections`),
  `_render_profile_directives` / `_render_profile_tactics` (`:2757-2758`), the profile resolution path
  in `AgentProfileRepository`, and the profile-channel reachability helper
- **Sequencing/depends-on**: IC-04 (the channel's named set); parallel with IC-06 — different render
  surface, same file, so treat as a **file collision** rather than an ordering dependency
- **Risks**:
  - The profile channel is **not expressible as a `resolve_context` seed set** — `agent_profile` nodes
    have zero outbound `scope` edges, so `resolve_context` from a profile returns 0 artefacts at every
    depth. Its traversal is a separately-named `walk_edges` over `{requires, specializes_from}`. Any
    attempt to fold it into `resolve_context` will silently measure nothing.
  - `procedure:onboard-external-agent-to-pack` — PR #3007's exemplar, reached from
    `agent_profile:doctrine-daphne` by a `requires` edge — is the live instance of this defect. It is
    **in scope here**, and it is why the first revision's plan to "rescue" it via seed-union was
    unsound: the union asserted reach that no channel delivers.
  - `profile` is `str | None` at `context.py:137`, so the channel is **conditional on caller
    configuration**. Measuring it as unconditional repeats the fail-open shape FR-018 retires.
  - Deciding *which* kinds a profile should deliver is a doctrine question, not only a render one.
    Where the answer is not attested by the profile schema, defer under C-007 rather than inventing it.

### IC-08 — Reference block distribution and resolvable pointers

- **Purpose**: Every emitted pointer opens; composition varies by action instead of being exhausted by
  a fixed kind order.
- **Relevant requirements**: FR-013, FR-014; SC-006
- **Affected surfaces**: `src/charter/activation/context.py:1169` and `:1531`,
  `_filter_references_for_action:1484`, `_LIBRARY` path resolution
- **Sequencing/depends-on**: **none — parallel with IC-06.** The first revision declared IC-06, but
  `references` is sourced from the `charter.yaml` catalog and passed in, not derived from the bundle
  (`context.py:1166-1172`). Retain a **file-collision** note only: both edit `context.py` under the
  no-net-growth constraint.
- **Risks**: **Two cap sites, not one.** `:1531` sits in `_render_bootstrap`, which is called from
  nowhere in `src/` and only from `tests/charter/test_context.py:815` — a render path reachable only
  from the test suite, i.e. an instance of this mission's own thesis. **Ruling: delete it**; if a WP
  finds a live caller, that is a finding, not a reason to keep it. `_filter_references_for_action` is
  a **no-op for every doctrine kind** (213 → 213), so "filtering" is not the fix — distribution is.
  **No test pins either cap** (proven by mutation), so SC-006 needs a non-vacuity floor or it passes
  over an empty set.

### IC-09 — Documentation and CLI reference

- **Purpose**: Make the documented remedy followable.
- **Relevant requirements**: FR-019; SC-008
- **Affected surfaces**: `docs/doctrine/doctrine-kinds.md:50-52`,
  `docs/doctrine/create-a-doctrine-artifact.md`, `docs/api/cli-commands.md`, `CHANGELOG.md`
- **Sequencing/depends-on**: IC-03, **IC-02** (`doctrine-kinds.md` *is* the kind-vocabulary reference
  IC-02 changes) and **IC-06** (D4 requires the asset bundle-slot verdict be documented where the table
  records verdicts). The first revision named IC-05, which owns no surface this concern documents.
- **Risks**: `doctrine-kinds.md` states asset has "no built-in artifacts yet" — false, one ships.
  `create-a-doctrine-artifact.md` contains "asset" **zero** times while `review-gates.md` cites it as
  the asset how-to. New visible Typer paths from IC-03 trip `REF-MISSING` in the CLI-reference
  freshness gate against a 4,950-line reference. Run the terminology guard before push — it lives in a
  CI job the fast suites do not cover. Cite the *sentence*, not the line — this plan's own quickstart
  records that four discovery anchors drifted.

---

## Issue ledger

Added post-squad. The first revision cited ten issues and named none as closed, which reads as closure
to a reviewer.

| Disposition | Issues |
|---|---|
| **Closes** | **#2977** (`rewrite_opposed_by` still declares its own `_node_to_dict`/`_edge_to_dict`; IC-01 removes them) · **#3037** (`DoctrineService` exposes 9 repositories, none `assets`; IC-03 adds the resolution path) |
| **Advances, does NOT close** | **#3038** — IC-02 fixes the `_PROJECT_KIND_DIRS` half; `project_drg._KIND_TO_NODE_KIND` stays deferred · **#2981** — this mission touches only the project-tier mapping; the headline `_activation_render.py` 8-vs-10 drift is out of scope under C-004 · **#3009** — `_ACTIVATED_BUT_UNREACHABLE` **is** its nine artefacts; IC-04 renames and re-measures, but closure depends on FR-015's table covering all nine, which is not yet asserted |
| **Cited, not touched** | #2986, #2994, #3026, #3036, #3039 — no concern names `_inert_slots.py` or `test_no_dead_doctrine_paths.py`. Listed so a reviewer does not read a citation as a closure |

## Corrected size estimate

The first revision's 45-60 files is ~30% light. Realistic: **65-85**, concentrated in two concerns.

| Concern | Named surfaces | Realistic |
|---|---|---|
| IC-04 | 3 | **18-22** — authoring FR-015's edges regenerates up to 14 `*.graph.yaml` fragments, plus the helper, the renamed/partitioned sets, NFR-004 ledger rows, and the `common-docs` sources |
| IC-03 | 5 | **12-16** — new repository, `__init__`, service property, the `rglob` override, containment call, two CLI subcommands, the test repoint, new unit tests, **and SC-003's wheel harness, which still has no named home** |

## File ownership — declare the lane, or serialize

Four files are claimed by two or more concerns. This is how lane execution splits its brain.

| File | Claimants | Resolution |
|---|---|---|
| `src/charter/activation/context.py` | IC-06, IC-07, IC-08 | Three concerns in a 3,227-line module under a shared no-net-growth constraint. Assign one lane or serialize |
| `src/doctrine/service.py` | IC-02 (`_PROJECT_KIND_DIRS`), IC-03 (`assets` property) | Land IC-02 wholly first, or give IC-03 only the `asset` rows |
| `src/specify_cli/cli/commands/doctrine.py` | IC-02 (`:431`, `:442`, `:464`), IC-03 (asset subcommands) | Same |
| `tests/doctrine/drg/migration/test_extractor_projection.py` | IC-04 (renames the set), IC-05 (repoints `_charter_activated_urns`) | One 604-line file, one lane |

## Deferrals still needing a home

Recorded rather than filed — filing is outward-facing and awaits operator confirmation.

| Deferral | Current state |
|---|---|
| Agent-facing asset delivery | **Stale row** in `spec.md` — says "Filed" with no number, and D4 has since reversed it into scope. Delete the row |
| The four `action:plan/*` nodes resolving to zero artefacts of any kind | Verified real and exact at d=2. No issue number. SC-001 requires such gaps be *named*; without an issue it is invisible work |
| The AST gate on dict-literal edge payloads | No owner, no number — and it is the compensating control for the registry's one conceded blind spot. Deferring the compensating control with no home is this mission's defect class applied to its own governance |
