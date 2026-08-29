# Tracer: Design Decisions — up-mission-type-seam

Seeded at planning (specify phase). Append during implementation; assess at close per the
`mission-tracer-files` procedure (charter Standing Order #3).

## DD-001 — Seam shape: option (c), a separate layered lookup

Considered three shapes for making mission-type resolution project-aware:

- **(a) Make `MissionTypeRepository.default()` itself project-dependent** by threading a
  `PackContext` into its existing process-wide, `cls`-keyed `functools.cache`. Rejected: a
  project-dependent value behind a project-blind cache key is a correctness bug by construction
  — whichever project resolves first in a process silently poisons the cache for every later
  project in the same process. This is not a hypothetical; the CLI and test suite both reuse
  process lifetime across projects routinely.
- **(b) Move the `action_sequence` projection out of `doctrine.missions.mission_type_repository`
  into the `charter` layer**, on the theory that projection is a charter-layer concern. Rejected
  on measured evidence, not a guess: `tests/architectural/test_no_inert_schema_slots.py` walks a
  specific directory tree (`src/doctrine/` + `packs/built-in/`) looking for the producer of the
  `action_sequence` schema slot. Moving the producer out of that tree reds two independent
  assertions in that gate — a "new" unaccounted-for inert slot, and a "stale" baseline row with
  no matching producer. Confirmed this would happen before rejecting the option, not assumed.
- **(c) Add a new, separate, module-level layered lookup**, entered at
  `resolve_mission_type_context` (`src/charter/activation/mission_type_profiles.py`), keyed on
  `(mission_types_dirs, pack_context)`, reusing the existing `_PackContextLike` structural
  `Protocol` already defined in `doctrine.missions.mission_step_repository` for exactly this
  purpose (it exists there specifically so a sibling module can build a project-scoped cache key
  without a new cross-layer import). **Chosen.** It keeps `default()`'s process-wide,
  built-in-only cache semantics completely untouched (no risk to (a)'s correctness class), keeps
  the `action_sequence` producer inside the architecturally-scanned tree (no risk to (b)'s gate),
  and costs only one new module-level cache plus its own `cache_clear()` test seam — mirroring a
  pattern (`MissionStepRepository.cache_clear`) that already exists in the same package for the
  same reason.

The load-bearing property of (c) is that it is *additive*: nothing about built-in resolution
changes at all. That is also why User Story 3 in the spec exists as its own acceptance path —
the design bet only pays off if built-in behavior is provably untouched, not just "probably
fine."

## DD-002 — Org-pack layout is flat: `<pack>/mission_types/*.yaml`

Two shapes were on the table for where an org (or project) pack declares its mission types:

- **Nested**, mirroring the eventual `#2468` ArtifactKind-promotion shape
  (`<pack>/missions/mission_types/`), which is what the built-in tier currently uses at
  `packs/built-in/missions/`.
- **Flat**, mirroring the *existing* sibling convention already used by `mission-steps/`:
  `<pack>/mission-steps/<type>/<step>/step.yaml` has no `missions/` wrapper directory; it hangs
  directly off the pack root. The equivalent flat shape is `<pack>/mission_types/*.yaml`.

**Chosen: flat.** Two independent reasons converged on this, not just consistency-for-its-own-
sake:

1. It matches the convention `mission-steps/` already established at the org/project pack tier —
   introducing a *second*, inconsistent convention for a sibling concept (`mission_types/`) in
   the same pack would itself be a new footgun, and the referenced ADR
   (`docs/adr/3.x/2026-08-05-1-mission-type-availability-before-kind-promotion.md`) explicitly
   flags "nested" as the built-in tier's own current inconsistency with the flat
   `built_in_dir(kind)` convention every *other* built-in kind uses — this mission should not
   propagate that inconsistency into the org/project tier while it is still unresolved at the
   built-in tier.
2. For the **project layer specifically**, the obvious nested-feeling candidate,
   `.kittify/doctrine/mission_types/`, has a concrete trap: if that directory were scanned
   recursively (the natural implementation for a "doctrine" subtree), it would descend into a
   per-type `governance-profile.yaml` subdirectory that some mission types carry, and mint a
   bogus available mission type literally named `governance-profile`. A flat
   `.kittify/missions/mission_types/*.yaml`, scanned **non-recursively**, has no such trap by
   construction — there is no subdirectory to wander into.

The ADR referenced above explicitly leaves "nested-vs-flat" as an *undecided* open sub-decision
for the future `#2468` ArtifactKind-promotion slice. This mission's WP01 ADR (spec CL-002) is
required to record the flat choice for *this* mission's org/project layers as its own short
decision record — it does not resolve or bind the built-in tier's separate nested-vs-flat
question, which stays with `#2468`.
