# Phase 1 Data Model — Doctrine Delivery Reachability

**Mission**: `doctrine-delivery-reachability-01KYMXD6` | **Date**: 2026-07-28

This mission adds one new entity and changes the **invariants** of five existing ones. Almost all of
its value is in invariants rather than in new fields — the defect class is "a projection narrower than
what it projects", so the model work is mostly about making narrowness impossible.

---

## New entities

### AssetRepository

Tiered resolver for `AssetManifest` records. Mirrors `BaseDoctrineRepository[T]` with two overrides.

| Field / behaviour | Description |
|---|---|
| `_schema` | `AssetManifest` (existing, frozen, `extra="forbid"`) |
| `_glob` | `*.asset.yaml` |
| `_project_scan` | **Overridden to `rglob`** — the base is non-recursive, which would miss org-pack manifests at the ADR-mandated nested path |
| `_source_paths` | Per-identifier source file, tracked like `AgentProfileRepository`. The base class records only a layer *label* in `_provenance`, never the file |
| `resolve_path(id) -> Path` | Resolves to an on-disk path with containment enforced |

**Invariants**

- **I-A1 — anchor asymmetry is explicit.** Built-in blob paths anchor at the *parent* of
  `<root>/assets/built-in`; org and project blob paths anchor at the directory itself. A single shared
  anchor rule produces `.../assets/built-in/built-in/...` and must not be written.
- **I-A2 — containment is fail-closed.** A declared path escaping its root by traversal or symlink
  raises a typed error. Enforced via `doctrine.drg.org_pack_config.resolve_relative_path_within_root`,
  never by joining paths, and never by importing the validator's helper (layer direction).
- **I-A3 — tier precedence is reported.** The more specific tier wins and the shadowed tier is
  reported, never silently dropped.
- **I-A4 — scaffold and resolver agree.** The directory `doctrine new --kind asset` writes to is the
  directory the repository reads from. Guaranteed structurally by IC-02's single mapping, not by
  matching two literals.

---

## Changed invariants on existing entities

### DRGEdge / DRGNode / DRGGraph

No field changes. Three invariant changes.

- **I-W1 — serialization is derived, not restated.** Every serializing site emits
  `set(model_fields) - _FIELDS_WITHHELD_FROM_GRAPH_OUTPUT`. A hand-listed key set is a defect.
- **I-W2 — the writer set is enumerable.** Every edge/node-serializing site is a member of the writer
  registry, and the field-completeness test iterates the registry. Today's four sites —
  `extractor`, `rewrite_opposed_by`, `project_drg._serialize_graph`, `_dump_graph_document` — plus the
  org-tier bridge `_bridge_org_edge_to_drg_edge`, which drops fields *before any writer runs*.
- **I-W3 — unknown top-level keys are rejected.** `DRGGraph` gains `model_config` with
  `extra="forbid"`, matching `DRGNode` and `DRGEdge`. Today unknown document keys are accepted and
  discarded.

### Activation store

The set of `activated_<kind>` declarations.

- **I-V1 — single authority.** `charter.yaml` is the authority; `.kittify/config.yaml` points at it via
  the **`charter:`** key, which already ships. The `activated_*` mirror in `config.yaml` is removed.
  **`charter_file:` is not the field name** and must not be introduced.
- **I-V2 — absence means empty.** An omitted `activated_<kind>` key resolves to `[]` at every
  boundary. The prior three-state contract (absence ⇒ all built-ins) is retired by migration.
- **I-V3 — no reader outside the canonical path.** `GovernanceResolution` is populated *from*
  `PackContext` / `resolve_config_activated_roots`, never by reading a store directly. A second reader
  is a defect, not an optimisation.
- **I-V4 — identifier form is normalized once.** The store's form (`025-boy-scout-rule`) and the
  selector form (`directive:DIRECTIVE_025`) reconcile at a single boundary. Per C-009 this
  normalization is **not** counted as reachability progress.

### `_ActionDoctrineBundle`

The per-(action, mission_type) resolved doctrine payload.

| Change | Description |
|---|---|
| `procedure_ids` | **New field.** Its absence is why all 18 activated procedures are undeliverable |
| `asset_ids` | **New field.** Per D4, assets are delivered but not activation-gated |
| `_ACTION_BUNDLE_SLOT_BY_KIND` | Every `NodeKind` maps to a slot **or to a recorded verdict**, never to a bare `None` |

- **I-B1 — resolution equals delivery.** Every id the bundle resolves appears in the rendered output.
  A resolved-then-dropped kind is the defect class, and it is live today for styleguides and
  toolguides.
- **I-B2 — the slot table records verdicts.** A kind excluded from delivery carries a stated reason at
  the table. A bare `None` is indistinguishable from an oversight.
- **I-B3 — delivery is complete, not truncated.** The delivered set **equals**
  `activated ∩ action_reachable`. Any cap is a defect; budget pressure is handled by the existing
  degradation-to-fetch-stanza path.

### Reachability set

Not a stored entity — a computed property that becomes an asserted artefact.

| Property | Value |
|---|---|
| Traversal | `doctrine.drg.query.resolve_context` — **called, never reimplemented** |
| Depths | Two named sets: `d=1` (compact, steady state) and `d=2` (bootstrap) |
| Seeds | Action nodes **and** activated agent profiles |
| Assertion | Set **membership**, not cardinality |

- **I-R1 — reachability, not incidence.** Touching an edge is not reaching. `_ACTIVATED_BUT_
  UNREACHABLE` currently measures incidence despite its name and is renamed in the same work package
  that lands the real set.
- **I-R2 — reachability, not cascade.** Cascade walks *outbound from the activation seed*, so any
  inbound edge satisfies it — including one from an unreachable source. Cascade is not evidence.
- **I-R3 — a wiring is obvious only if its source is reachable.** C-007's two-part test: the
  relationship is attested in the artefact's own text, **and** the proposed source is itself
  action-reachable (or the edge is a `scope` edge from an action node). Everything else is deferred.

---

## State transitions

Only one entity has a lifecycle worth stating.

**Activation key** — per kind, per project:

```
absent ──(FR-018 migration)──> explicit []
   │                                │
   │ (pre-migration read)           │ (operator activates)
   ▼                                ▼
all built-ins  [RETIRED]        populated list
                                     │
                                     │ (operator deactivates)
                                     ▼
                                explicit []
```

The `absent → all built-ins` edge is the one this mission removes. It is reachable today and is
unbounded once delivery works.

---

## Externally visible effects

- **Consumer upgrade** writes the `charter:` pointer where missing, normalizes absent activation keys
  to `[]`, and removes the retired mirror. This is the only consumer-file mutation permitted
  (NFR-001, as amended).
- **Agent context payload changes shape** for every action in every consumer project: additional kinds
  appear, and they appear on every load rather than once. This is the mission's intended outcome and
  its largest blast radius.
- **No files are installed** into consumer repositories. Assets are resolved from package data
  (C-002).
