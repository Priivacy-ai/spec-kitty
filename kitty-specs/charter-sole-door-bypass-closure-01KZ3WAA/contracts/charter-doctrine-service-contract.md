# Contract: `charter.activation.resolver.DoctrineService` public surface (post-mission)

This is the internal contract every in-scope call site (FR-001/002/003) must construct/consume against.
Not a network API — an internal Python object contract, enforced by the FR-007 gates.

## Construction

Exactly one path constructs the activation-aware instance: the unified builder (FR-008). No call site
outside `src/charter/activation/resolver.py` and that one builder constructs `doctrine.service.DoctrineService`
directly (NFR-001).

```
DoctrineService(inner: doctrine.service.DoctrineService, pack_context: PackContext | None)
```

- `pack_context` set (normal case) → every gated property below applies three-state filtering.
- `pack_context=None` (diagnostic case, FR-002/R4) → every gated property returns the raw inner catalog,
  unfiltered. Callers using this mode MUST carry an inline comment naming the diagnostic reason.

## Gated properties (9 of 10 kinds)

`paradigms`, `procedures`, `agent_profiles` (pre-existing) plus `directives`, `tactics`, `styleguides`,
`toolguides`, `mission_step_contracts`, `glossary_packs` (FR-005, new). Each follows the three-state
contract in `data-model.md`. None of these properties differ in filtering shape from each other — a
reviewer diffing any two of the 9 getters should see the same structure modulo the kind name.

## New resolution methods (FR-003)

Method names are an implementation choice for the tasks phase, but the contract is: every one of the 5
resolver tiers (OVERRIDE, LEGACY, GLOBAL_MISSION, GLOBAL, PACKAGE_DEFAULT) and the mission-config resolution
remains reachable ONLY via a method on this class from outside `src/charter/**`. `doctrine/resolver.py`'s
`_resolve_asset`/`resolve_mission` functions are the implementation these methods delegate to; they are not
moved, renamed, or duplicated.

## Explicitly NOT on this class

- `mission_types` — no property exists, and none is added. The `mission-type` token is gated separately by
  `charter.activation.mission_type_profiles.resolve_mission_type_context()` (see the sibling contract file — NOT by
  editing `MissionTypeProfileRepository`'s own file, per a post-tasks squad ownership-boundary correction).
  Do not add a `mission_types` property here as a shortcut; that would contradict R (D4)'s finding that the
  token has no matching raw-service property to filter.
- Lineage/mutation operations (`register_overlay()` and `get_provenance()`) on `agent_profiles` — these
  require the new `agent_profile_repository` accessor, a second, explicitly-named accessor, not a widening
  of the `agent_profiles` property's return type. (Post-tasks squad correction: `get_ancestors()` and
  `resolve_profile()` were named in earlier drafts of this contract but are not the verified surface —
  `get_ancestors()` is unused by any real call site; `resolve_profile()` is used only by
  `runtime_bridge_io.py`, not by the two `._inner`-reach-around sites this bullet originally described.)

## Non-regression obligations

- A bare project (no activated packs) must see its full built-in default catalog on every gated property.
  **Non-fakeable assertion shape** (post-plan squad correction — an existence check like `assert svc.
  directives` is satisfied even if 3 of 40 directives silently leaked away): the test asserts
  `wrapped.<prop> == unwrapped_inner.<prop>` for a bare `PackContext`, per kind — equality against the raw
  unwrapped inner service's output, not merely "returns something."
- `pack_context=None` construction must return the identical catalog a raw, unwrapped
  `doctrine.service.DoctrineService` would have returned — proven by the same equality regression shape,
  since this mode exists specifically to preserve pre-mission diagnostic behaviour.

## Lineage/mutation accessor semantics (pinned — post-plan squad, was previously under-specified)

The new public accessor `charter.activation.resolver.DoctrineService` gains for `projection.py`/`runtime_bridge_io.py`/
`registry.py`/`org_profiles.py` (FR-001, FR-010) has two semantic questions that do NOT have a default and
must not be left for tasks-time improvisation:

1. **Does `register_overlay()` of a non-activated profile become readable through the gated `agent_profiles`
   property afterward?** Pinned answer: **no** — `register_overlay()` mutates the underlying repository's
   lineage graph; the gated `agent_profiles` property still applies the same three-state activation filter
   on every read, including reads that follow a mutation. Mutation capability and activation filtering are
   orthogonal; the accessor does not create a way to read an unfiltered profile through the filtered surface.
2. **Does `resolve_profile()`'s `specializes_from` traversal cross into a deactivated parent profile?**
   Pinned answer: **yes, lineage traversal reads through the raw repository** — lineage composition is a
   below-the-activation-grain operation (it answers "what does this profile inherit from," not "is this
   profile enabled"), matching the existing precedent at `resolver.py:402-413`'s `resolve_governance_for_
   profile`, which already reads the raw inner repository for exactly this reason. The accessor returns the
   raw, lineage-capable repository object directly (not re-wrapped) — callers needing both lineage
   composition AND activation filtering call the gated property for the filtering decision and the accessor
   for the composition, as two separate questions, not one merged call.
