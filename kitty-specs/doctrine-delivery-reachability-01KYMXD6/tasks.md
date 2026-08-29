# Work Packages: Doctrine Delivery Reachability

**Mission**: `doctrine-delivery-reachability-01KYMXD6`
**Branch**: `feat/doctrine-delivery-reachability` (planning base and merge target; PR to `upstream/main` after consolidation)
**Generated**: 2026-07-28T19:48:12Z
**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md)

Completion is **event-sourced**. Record progress with
`spec-kitty agent tasks mark-status T001 T002 --status done`. There are no checkboxes to tick;
the reference rows below are references, not tracking surfaces.

---

## Landing order

**WP01 lands first and alone.** It is mission B1's unblock and carries no inbound dependency (C-005).

```
WP01 ──┬── WP02
       └── WP08 ──┬── WP09
                  ├── WP10 ── WP15 ── WP11
                  └── WP12
WP03 ──┬── WP04 ── WP05 ──┐
       └──────────────────┴── WP14
WP06 ── WP07 ──┬── WP08
               └── WP10
WP13  (independent — may land any time)
```

**WP15 sits between WP10 and WP11 by binding constraint (C-012).** WP11 switches on
delivery-on-every-load; WP15 makes links the default cadence. Landing WP11 first would ship 184
artefacts' worth of inlined bodies at every action boundary in every consumer project, with the
mitigation a mission away.

Genuinely parallel at the start: **WP01, WP03, WP06, WP13**.

## Subtask Index

Reference table only. The `[P]` column marks parallel-safety, not status.

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Export the derived serialization helper from the extractor | WP01 | |
| T002 | Close the empty-value hole in the derived helper (W-1a) | WP01 | |
| T003 | Extract `project_drg`'s inline node/edge dicts into mapping functions | WP01 | [P] |
| T004 | Define `MappingWriter` / `DocumentWriter` / `ModelBridge` protocols and registries | WP01 | |
| T005 | Join the mapping writers to the registry; retire their hand-written dicts | WP01 | |
| T006 | Derive `_dump_graph_document`'s document-level keys from `DRGGraph.model_fields` | WP01 | |
| T007 | Red-first subclass mutation fixture across all registry shapes | WP01 | |
| T008 | Add `extra="forbid"` to `DRGGraph` | WP02 | |
| T009 | Typed error and named diagnostic for unknown top-level graph keys | WP02 | |
| T010 | Join the org-tier bridge to `ModelBridge` with field-coverage assertion | WP02 | [P] |
| T011 | Consumer-facing regression tests for the strictness break | WP02 | |
| T012 | Hoist the canonical project-tier kind mapping into `artifact_kinds.py` | WP03 | |
| T013 | Convert the CLI `_PROJECT_KIND_DIRS` copy to `ArtifactKind` keys | WP03 | |
| T014 | Retire the two charter copies onto the hoisted authority; drop their exemptions | WP03 | |
| T015 | Fold `_CANONICAL_KIND_SINGULAR_TO_PLURAL` into the hoisted authority | WP03 | |
| T016 | Replace the `_stub_template` if-chain with a kind-keyed mapping including `asset` | WP03 | |
| T017 | Extend the totality guard to the newly-discoverable copies | WP03 | |
| T018 | End-to-end: `doctrine new --kind asset` succeeds where the resolver reads | WP03 | |
| T019 | `AssetRepository` with recursive overlay discovery | WP04 | |
| T020 | Per-identifier source-path tracking | WP04 | [P] |
| T021 | `resolve_path` with containment enforced fail-closed | WP04 | |
| T022 | Anchor asymmetry: built-in parent vs org/project self | WP04 | |
| T023 | Convert `service.py` `_PROJECT_KIND_DIRS` to the hoisted authority | WP04 | |
| T024 | `DoctrineService.assets` property | WP04 | |
| T025 | Repository tests: tier precedence, rglob, containment negatives, missing id | WP04 | |
| T026 | `doctrine asset list` / `path` operator commands | WP05 | |
| T027 | Register the asset subapp on the CLI | WP05 | |
| T028 | Clean-environment wheel harness for SC-003 | WP05 | |
| T029 | Repoint the shipped-asset consumer off `_REPO_ROOT` | WP05 | |
| T030 | CLI reference entries for the new visible paths | WP05 | |
| T031 | Normalize the activation identifier form at one boundary | WP06 | |
| T032 | Declare the normalization and exclude it from progress claims (C-009) | WP06 | |
| T033 | Partition the measured set into `{not-a-node, node-but-unreachable}` | WP06 | |
| T034 | Red-first: an unnormalized identifier resolves or fails naming the accepted form | WP06 | |
| T035 | Repoint `_charter_activated_urns` at the resolved activation source | WP07 | |
| T036 | Remove the retired `activated_*` mirror from the config surface | WP07 | |
| T037 | Migration: normalize absent `activated_<kind>` keys to explicit `[]` | WP07 | |
| T038 | Retire the three-state absence contract at every read site | WP07 | |
| T039 | Divergent-mirror fixture proving which store won | WP07 | |
| T040 | Fail-closed: activation errors propagate rather than degrade | WP07 | |
| T041 | Reconcile the two prior migrations and record why the mirror survived | WP07 | |
| T042 | Action-channel reachability helper calling `resolve_context` | WP08 | |
| T043 | Profile-channel reachability helper over `{requires, specializes_from}` | WP08 | [P] |
| T044 | Rename the incidence set and land the named reachability sets beside it | WP08 | |
| T045 | Assert action-channel membership at d=1 and d=2 | WP08 | |
| T046 | Assert profile-channel membership | WP08 | |
| T047 | Red-first: a nominally-wired but unreachable artefact is reported unreachable | WP08 | |
| T048 | Build the FR-015 wiring table with measured source reachability | WP09 | |
| T049 | Author the edges that pass C-007's two-part test | WP09 | |
| T050 | Wire the `common-docs` cluster so the shipped asset can arrive | WP09 | |
| T051 | Ledger the graph composition deltas under NFR-004 | WP09 | |
| T052 | Record the deferred set for the operator interview | WP09 | |
| T053 | Return the per-kind mapping from `_classify_artifact_urns` | WP10 | |
| T054 | Add `procedure_ids` and `asset_ids` to the action bundle | WP10 | |
| T055 | Express the delivery gate as a total per-kind function | WP10 | |
| T056 | Flip the `PROCEDURE` and `ASSET` slot verdicts and record the reversal | WP10 | |
| T057 | Make the renderer emit every kind the bundle resolves | WP10 | |
| T058 | Populate `GovernanceResolution` from the canonical path only | WP10 | |
| T059 | Retire or repoint the overloaded `_EXTENDED_CONTEXT_DEPTH` gate | WP11 | |
| T060 | Deliver on every load at all four compact-return sites | WP11 | |
| T061 | Widen the compact rail to carry every kind | WP11 | |
| T062 | Supply the mission-type grain at the two omitting callers | WP11 | |
| T063 | Assert delivery through the shipped command surface, not the builder | WP11 | |
| T064 | Record the measured latency delta under NFR-007 | WP11 | |
| T065 | Red-first: an artefact present on load one is present on load two | WP11 | |
| T066 | Profile-channel kind coverage decision, attested not invented | WP12 | |
| T067 | Render every kind a loaded profile resolves | WP12 | |
| T068 | Deliver the exemplar procedure through the profile channel | WP12 | |
| T069 | Guard the conditional-profile fail-open shape | WP12 | |
| T070 | Red-first: a profile-resolved procedure reaches its agent | WP12 | |
| T071 | Replace the order-rigged cap with per-kind distribution | WP13 | |
| T072 | Delete the test-only `_render_bootstrap` renderer | WP13 | |
| T073 | Make every emitted reference pointer resolve | WP13 | |
| T074 | Non-vacuity floor and cross-action variation | WP13 | |
| T075 | Red-first: mutating the cap turns a test red | WP13 | |
| T076 | Correct the false "no built-in artifacts yet" claim | WP14 | |
| T077 | Write the asset how-to the review gates already cite | WP14 | |
| T078 | Document the delivery verdicts where the table records them | WP14 | |
| T079 | Refresh the kind-vocabulary reference for the hoisted authority | WP14 | |
| T080 | CHANGELOG entry and terminology guard pass | WP14 | |
| T081 | Emit `references[]` on the context DTO from edge `when` / `reason` | WP15 | |
| T082 | Deliver `requires` eagerly and `suggests` as links | WP15 | |
| T083 | `--include-all` escape hatch materialising the reachable closure | WP15 | |
| T084 | Red-first: a linked artefact is named, fetchable, and inlined by the hatch | WP15 | |

---

## WP01 — Derived serialization core and the writer registry

**Priority**: P1 · **Prompt**: [tasks/WP01-derived-serialization-core.md](tasks/WP01-derived-serialization-core.md) · **~380 lines**
**Depends on**: none — **this is mission B1's unblock and must stay dependency-free (C-005)**

**Goal**: Make the set of graph write paths derived and enumerable, so a field added later cannot be
silently dropped by a writer nobody remembered.

**Independent test**: Extend the edge model within a test with a field no writer was written against;
round-trip it through every registry member; assert survival.

T001 Export the derived serialization helper from the extractor (WP01)
T002 Close the empty-value hole in the derived helper — W-1a (WP01)
T003 Extract `project_drg`'s inline node/edge dicts into mapping functions (WP01)
T004 Define `MappingWriter` / `DocumentWriter` / `ModelBridge` protocols and registries (WP01)
T005 Join the mapping writers to the registry; retire their hand-written dicts (WP01)
T006 Derive `_dump_graph_document`'s document-level keys from `DRGGraph.model_fields` (WP01)
T007 Red-first subclass mutation fixture across all registry shapes (WP01)

**Risks**: three incompatible member shapes; the registry must be hosted in `specify_cli` or it reds
two layer gates; the derived helper drops `None` and empty-list values today.

---

## WP02 — Graph document strictness and the org-tier bridge

**Priority**: P1 · **Prompt**: [tasks/WP02-graph-document-strictness.md](tasks/WP02-graph-document-strictness.md) · **~260 lines**
**Depends on**: WP01

**Goal**: Close the two remaining field-loss surfaces — unknown top-level keys accepted and discarded,
and the org bridge that drops fields before any writer runs.

**Independent test**: An org-pack graph document with an unknown top-level key fails to load with a
typed, named error rather than loading degraded.

T008 Add `extra="forbid"` to `DRGGraph` (WP02)
T009 Typed error and named diagnostic for unknown top-level graph keys (WP02)
T010 Join the org-tier bridge to `ModelBridge` with field-coverage assertion (WP02)
T011 Consumer-facing regression tests for the strictness break (WP02)

**Risks**: **this is a consumer-facing read-path break** — it is deliberately split out of WP01 so it
does not ride the lane that lands first and alone.

---

## WP03 — Kind vocabulary hoist, totality, and scaffold parity

**Priority**: P1 · **Prompt**: [tasks/WP03-kind-vocabulary-hoist.md](tasks/WP03-kind-vocabulary-hoist.md) · **~400 lines**
**Depends on**: none

**Goal**: One project-tier kind mapping, hosted at the lowest layer and imported downward, with the
totality guard able to see every copy — and `doctrine new --kind asset` reaching the directory the
resolver reads.

**Independent test**: `doctrine new --kind asset foo` succeeds and `DoctrineService` resolves the
result; adding a partial copy fails the guard.

T012 Hoist the canonical project-tier kind mapping into `artifact_kinds.py` (WP03)
T013 Convert the CLI `_PROJECT_KIND_DIRS` copy to `ArtifactKind` keys (WP03)
T014 Retire the two charter copies onto the hoisted authority; drop their exemptions (WP03)
T015 Fold `_CANONICAL_KIND_SINGULAR_TO_PLURAL` into the hoisted authority (WP03)
T016 Replace the `_stub_template` if-chain with a kind-keyed mapping including `asset` (WP03)
T017 Extend the totality guard to the newly-discoverable copies (WP03)
T018 End-to-end: `doctrine new --kind asset` succeeds where the resolver reads (WP03)

**Risks**: two of four copies are string-keyed and **invisible to the guard's AST scan**, not merely
exempted; the scaffold rejects two dicts upstream of the one the plan first named; the if-chain is a
kind projection no dict-scanning guard can see.

---

## WP04 — Asset repository and service wiring

**Priority**: P1 · **Prompt**: [tasks/WP04-asset-repository.md](tasks/WP04-asset-repository.md) · **~400 lines**
**Depends on**: WP03

**Goal**: An asset identifier resolves to a filesystem path across all three tiers, fail-closed.

**Independent test**: Resolve a shipped asset by identifier; resolve an org-tier override; refuse a
path that escapes its root.

T019 `AssetRepository` with recursive overlay discovery (WP04)
T020 Per-identifier source-path tracking (WP04)
T021 `resolve_path` with containment enforced fail-closed (WP04)
T022 Anchor asymmetry: built-in parent vs org/project self (WP04)
T023 Convert `service.py` `_PROJECT_KIND_DIRS` to the hoisted authority (WP04)
T024 `DoctrineService.assets` property (WP04)
T025 Repository tests: tier precedence, rglob, containment negatives, missing id (WP04)

**Risks**: the base overlay scan is non-recursive; built-in blob paths anchor at the parent while
org/project anchor at self; the containment helper lives in a layer this code may not import.

---

## WP05 — Asset operator surface and the wheel proof

**Priority**: P1 · **Prompt**: [tasks/WP05-asset-operator-surface.md](tasks/WP05-asset-operator-surface.md) · **~300 lines**
**Depends on**: WP03, WP04

**Goal**: An operator resolves a shipped asset from a clean installation, and this repository's own
consumer stops reaching through a repo path.

**Independent test**: A wheel installed into a fresh environment, with the repository absent from
resolution inputs, resolves the shipped asset identifier.

T026 `doctrine asset list` / `path` operator commands (WP05)
T027 Register the asset subapp on the CLI (WP05)
T028 Clean-environment wheel harness for SC-003 (WP05)
T029 Repoint the shipped-asset consumer off `_REPO_ROOT` (WP05)
T030 CLI reference entries for the new visible paths (WP05)

**Risks**: in-repo verification **cannot fail** because of the dev-layout fallback — the harness is the
requirement, not a convenience; new visible Typer paths trip the CLI-reference freshness gate.

---

## WP06 — Activation identifier normalization

**Priority**: P1 · **Prompt**: [tasks/WP06-identifier-normalization.md](tasks/WP06-identifier-normalization.md) · **~230 lines**
**Depends on**: none

**Goal**: Reconcile the activation store's identifier form with the selector form at a single
boundary, as a **separate declared change** that cannot be banked as reachability progress.

**Independent test**: An identifier in the store's form resolves; the measured set is partitioned so
the normalization's effect is visible and excluded.

T031 Normalize the activation identifier form at one boundary (WP06)
T032 Declare the normalization and exclude it from progress claims — C-009 (WP06)
T033 Partition the measured set into `{not-a-node, node-but-unreachable}` (WP06)
T034 Red-first: an unnormalized identifier resolves or fails naming the accepted form (WP06)

**Risks**: this moves the measured set by roughly 25 artefacts. It **must land before WP08 pins any
set**, or the pin is immediately stale — and it must never be counted as progress.

---

## WP07 — Activation authority, absence semantics, and fail-closed delivery

**Priority**: P1 · **Prompt**: [tasks/WP07-activation-authority.md](tasks/WP07-activation-authority.md) · **~420 lines**
**Depends on**: WP06

**Goal**: One activation authority; absence means empty; activation failures propagate.

**Independent test**: A divergent-mirror fixture where the two stores disagree proves which won; a
project omitting a key receives nothing for that kind; an activation error reaches the operator.

T035 Repoint `_charter_activated_urns` at the resolved activation source (WP07)
T036 Remove the retired `activated_*` mirror from the config surface (WP07)
T037 Migration: normalize absent `activated_<kind>` keys to explicit `[]` (WP07)
T038 Retire the three-state absence contract at every read site (WP07)
T039 Divergent-mirror fixture proving which store won (WP07)
T040 Fail-closed: activation errors propagate rather than degrade (WP07)
T041 Reconcile the two prior migrations and record why the mirror survived (WP07)

**Risks**: **T035 must precede T036** or the gate's floor assertion fails and its stray guard goes
vacuously true; the pointer key is `charter:`, not `charter_file:`; two prior migrations already fought
over this surface in opposite directions and the mirror survived both.

---

## WP08 — Reachability as named sets, per channel

**Priority**: P1 · **Prompt**: [tasks/WP08-reachability-named-sets.md](tasks/WP08-reachability-named-sets.md) · **~360 lines**
**Depends on**: WP01, WP06

**Goal**: Reachability becomes an asserted named set per delivery channel, computed by calling the
canonical traversal rather than reimplementing it.

**Independent test**: An artefact wired only to an unreachable source is reported unreachable; a new
unreachable artefact fails the suite by name.

T042 Action-channel reachability helper calling `resolve_context` (WP08)
T043 Profile-channel reachability helper over `{requires, specializes_from}` (WP08)
T044 Rename the incidence set and land the named reachability sets beside it (WP08)
T045 Assert action-channel membership at d=1 and d=2 (WP08)
T046 Assert profile-channel membership (WP08)
T047 Red-first: a nominally-wired but unreachable artefact is reported unreachable (WP08)

**Risks**: **do not reimplement the walk** — every hand-rolled BFS in this mission's history produced a
wrong number, including one that reached the plan; the incidence set shares a file and a similar name
with the real set; profiles have zero outbound `scope` edges so they are a separate traversal, not a
seed set.

---

## WP09 — Wiring edges that actually reach

**Priority**: P2 · **Prompt**: [tasks/WP09-wiring-edges.md](tasks/WP09-wiring-edges.md) · **~300 lines**
**Depends on**: WP08

**Goal**: Author the edges that make activated artefacts genuinely reachable, with each proposed
source's own reachability measured rather than assumed.

**Independent test**: Every artefact in the wiring table is reachable under the WP08 measure after the
edges land; nothing outside the table moved.

T048 Build the FR-015 wiring table with measured source reachability (WP09)
T049 Author the edges that pass C-007's two-part test (WP09)
T050 Wire the `common-docs` cluster so the shipped asset can arrive (WP09)
T051 Ledger the graph composition deltas under NFR-004 (WP09)
T052 Record the deferred set for the operator interview (WP09)

**Risks**: an inbound edge from an unreachable source is not a fix — this is the exact trap that fired
inside the predecessor mission; authoring edges regenerates up to 14 graph fragments; the destination
table is one mission B2 retires, so the handoff must be recorded.

---

## WP10 — The delivery rail carries every kind

**Priority**: P1 · **Prompt**: [tasks/WP10-delivery-rail.md](tasks/WP10-delivery-rail.md) · **~420 lines**
**Depends on**: WP07, WP08

**Goal**: Everything the bundle resolves reaches the rendered output, with the delivery gate expressed
as a total function over kinds rather than an enumerated exception.

**Independent test**: For a named (action, mission_type), the delivered set per kind equals
`gate(kind) ∩ reachable`, non-empty for at least five kinds.

T053 Return the per-kind mapping from `_classify_artifact_urns` (WP10)
T054 Add `procedure_ids` and `asset_ids` to the action bundle (WP10)
T055 Express the delivery gate as a total per-kind function (WP10)
T056 Flip the `PROCEDURE` and `ASSET` slot verdicts and record the reversal (WP10)
T057 Make the renderer emit every kind the bundle resolves (WP10)
T058 Populate `GovernanceResolution` from the canonical path only (WP10)

**Risks**: five parallel per-kind projections already exist — **do not create a sixth**; an equality
stated as `activated ∩ reachable` makes `asset_ids = []` the conforming implementation; unhardcoding
the resolver's empty literals changes nothing observable on its own.

---

## WP11 — Delivery on every load

**Priority**: P1 · **Prompt**: [tasks/WP11-delivery-every-load.md](tasks/WP11-delivery-every-load.md) · **~430 lines**
**Depends on**: **WP15** (which depends on WP10). The direct WP10 edge is superseded — WP15 must
interpose, because this package is the one that switches on every-load delivery and it must not
precede the cadence rule that makes that affordable (C-012).

**Goal**: Governance is in force on every context load, not once per project, and the callers that
omit the grain supply it.

**Independent test**: An activated artefact present on the first load is present on the second, and
the payload is non-empty through the shipped command surface.

T059 Retire or repoint the overloaded `_EXTENDED_CONTEXT_DEPTH` gate (WP11)
T060 Deliver on every load at all four compact-return sites (WP11)
T061 Widen the compact rail to carry every kind (WP11)
T062 Supply the mission-type grain at the two omitting callers (WP11)
T063 Assert delivery through the shipped command surface, not the builder (WP11)
T064 Record the measured latency delta under NFR-007 (WP11)
T065 Red-first: an artefact present on load one is present on load two (WP11)

**Risks**: **four compact-return sites in two functions**, including the `--json` builder the
reproduction uses; `depth` means two things and gates the very kinds this mission delivers; a test that
supplies the grain itself proves nothing about the shipped CLI; the ~2x latency is **accepted** but
must be measured and recorded.

---

## WP12 — Profile channel delivery

**Priority**: P1 · **Prompt**: [tasks/WP12-profile-channel-delivery.md](tasks/WP12-profile-channel-delivery.md) · **~300 lines**
**Depends on**: WP08

**Goal**: A loaded profile delivers every kind it resolves — profiles are how the implement loop hands
governance to an agent working a work package.

**Independent test**: An agent under a loaded profile receives a profile-resolved procedure.

T066 Profile-channel kind coverage decision, attested not invented (WP12)
T067 Render every kind a loaded profile resolves (WP12)
T068 Deliver the exemplar procedure through the profile channel (WP12)
T069 Guard the conditional-profile fail-open shape (WP12)
T070 Red-first: a profile-resolved procedure reaches its agent (WP12)

**Risks**: only directives and tactics render today; the channel is conditional on caller
configuration; deciding *which* kinds a profile should deliver is a doctrine question — where the
schema does not attest it, defer under C-007 rather than inventing it.

---

## WP13 — Reference block distribution and resolvable pointers

**Priority**: P3 · **Prompt**: [tasks/WP13-reference-block.md](tasks/WP13-reference-block.md) · **~280 lines**
**Depends on**: none — independent, may land any time

**Goal**: Every pointer an agent is handed opens, and the block's composition varies by action instead
of being exhausted by a fixed kind order.

**Independent test**: Follow every emitted pointer; compare emitted sets across two actions.

T071 Replace the order-rigged cap with per-kind distribution (WP13)
T072 Delete the test-only `_render_bootstrap` renderer (WP13)
T073 Make every emitted reference pointer resolve (WP13)
T074 Non-vacuity floor and cross-action variation (WP13)
T075 Red-first: mutating the cap turns a test red (WP13)

**Risks**: **two cap sites, not one**; the filter is a no-op for every doctrine kind so filtering is
not the fix; no test pins either cap today, proven by mutation; a criterion of "every pointer resolves"
passes vacuously over an emitted set of zero.

---

## WP14 — Documentation and CLI reference

**Priority**: P2 · **Prompt**: [tasks/WP14-documentation.md](tasks/WP14-documentation.md) · **~260 lines**
**Depends on**: WP03, WP05, WP10

**Goal**: The documented remedy becomes followable, and the delivery verdicts are recorded where the
table records verdicts.

**Independent test**: An operator executes the published asset how-to end to end against a fresh
project.

T076 Correct the false "no built-in artifacts yet" claim (WP14)
T077 Write the asset how-to the review gates already cite (WP14)
T078 Document the delivery verdicts where the table records them (WP14)
T079 Refresh the kind-vocabulary reference for the hoisted authority (WP14)
T080 CHANGELOG entry and terminology guard pass (WP14)

**Risks**: the how-to is cited by the review gates and contains the word "asset" zero times; the
freshness gate compares against a 4,950-line reference; the terminology guard runs in a CI job the fast
suites do not cover.

---

## WP15 — Progressive disclosure: navigable references and the fetch-everything hatch

**Priority**: P1 · **Prompt**: [tasks/WP15-progressive-disclosure.md](tasks/WP15-progressive-disclosure.md) · **~300 lines**
**Depends on**: WP10 · **Blocks WP11 — this is a binding ordering constraint (C-012)**

**Goal**: Make complete delivery affordable. Everything reachable is either delivered inline or
**named with the guidance that says when to fetch it** — never silently absent. This is the **default
cadence**, not an opt-in mode: it must be in force before WP11 switches on delivery-on-every-load, or
that switch ships 184 artefacts' worth of inlined bodies at every action boundary.

**Independent test**: The union of inlined ids and referenced ids equals the delivered set NFR-003
defines; `--include-all` output is a superset of the progressive render for the same grain.

T081 Emit `references[]` on the context DTO from edge `when` / `reason` (WP15)
T082 Deliver `requires` eagerly and `suggests` as links (WP15)
T083 `--include-all` escape hatch materialising the reachable closure (WP15)
T084 Red-first: a linked artefact is named, fetchable, and inlined by the hatch (WP15)

**Risks**: **a link an agent never follows is a declaration that reaches nobody** — this mission's own
defect class one level up, which is why the escape hatch is part of the decision rather than an
afterthought. `when` covers 219 of 337 `suggests` edges; the uncovered 118 must render a stated
default so absence is visible rather than blank. Governed by
[ADR 2026-07-28-1](../../docs/adr/3.x/2026-07-28-1-progressive-disclosure-of-doctrine-context.md),
status **Accepted**.

---

## MVP scope

**WP01** alone is a shippable increment: it unblocks mission B1, which is the mission's only hard
external deadline, and it is provable in isolation by the mutation fixture.

The smallest coherent user-visible slice is **WP03 → WP04 → WP05**: an operator can address a shipped
asset from a clean install, which makes the documented remedy executable for the first time.

## Parallelization

Four packages can start immediately with no inbound dependency: **WP01, WP03, WP06, WP13**.

Files claimed by more than one package — assign one lane or serialize:

| File | Packages |
|---|---|
| `src/charter/activation/context.py` | WP10, WP11, WP12, WP13 |
| `tests/doctrine/drg/migration/test_extractor_projection.py` | WP08, WP09 |
| `src/specify_cli/cli/commands/doctrine.py` | WP03, WP05 |
