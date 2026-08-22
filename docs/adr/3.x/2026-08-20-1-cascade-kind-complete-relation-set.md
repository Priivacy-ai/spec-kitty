---
title: 'ADR: The Charter Cascade Follows the Action Hop and Proposes Only Charter-Activatable Kinds'
description: 'The charter cascade follows the action hop (scope + instantiates) so activating a mission type reaches its governance, and proposes only charter-activatable kinds.'
status: Accepted
date: '2026-08-20'
---

## Context and Problem Statement

The charter **cascade** (`src/charter/cascade.py`) turns a single `charter
activate` into the set of artifacts that should activate alongside it, computed
as pure graph logic over the merged Doctrine Reference Graph (DRG). It walks the
DRG forward from the activation source along a fixed set of *reference relations*
and proposes the reachable artifact-kind nodes as cascade targets.

That followed set is `REFERENCE_RELATIONS = {requires, suggests, refines}`. It
has a structural dead-end for the single most natural activation an operator
performs — activating a **mission type**:

- A `mission_type` node carries only `requires → action:<mission>/<step>` edges.
- An `action` node carries `scope → {directive, tactic, styleguide, …}` and
  `instantiates → template` — it carries **no** `requires`/`suggests`/`refines`
  edges.
- So the forward closure reaches the `action` node and stops. The `action` node
  is not itself an artifact kind, so it is dropped, and the cascade returns
  nothing.

> **Superseding note (2026-08-22, #3633):** the "carries only `requires →
> action:<mission>/<step>`" bullet above is now stale — issue `#3604` (merged
> 2026-08-21, one day after this ADR's 2026-08-20 acceptance) added a second
> edge shape from `mission_type` nodes: `mission_type --scope-->
> {directive,tactic,paradigm,styleguide,toolguide,procedure,agent_profile,
> mission_step_contract}`, projecting each type's `governance-profile.yaml`
> `selected_*` selections directly (see
> [ADR 2026-07-26-1](2026-07-26-1-drg-edges-are-the-canonical-relationship-authority.md)'s
> own 2026-08-22 amendment on `Relation.SCOPE`'s two-grain overload). This does
> not change this ADR's decision: `#3604`'s `mission_type --scope-->` edges are
> still not `requires`/`suggests`/`refines`, so the dead-end this ADR fixes
> (widening `REFERENCE_RELATIONS` to include `scope` at the mission-type ⋈
> action hop) is unaffected — only the reason "the `mission_type` node has no
> other outgoing edges at all" no longer holds; the reason "the cascade's
> followed relation set does not include `scope`" still does, and is what this
> ADR actually fixes. Left in place above as the historical record rather than
> silently rewritten.

**Measured on the shipped graph: the cascade from every one of the four built-in
mission types (`documentation`, `plan`, `research`, `software-dev`) returns 0
activated artifacts.** Governance an operator switched on by activating a mission
type reaches nobody. This is issue #2829.

Widening the followed set to walk the action hop immediately raises a second
question. `action --scope--> …` reaches governance artifacts, but the same walk
(and, via `instantiates`, directly) reaches `template` and `asset` nodes — both
of which are **not charter-activatable** (`_NON_AUGMENTATION_ELIGIBLE_KINDS`;
`CHARTER_ACTIVATABLE_KINDS = frozenset(ArtifactKind) - {TEMPLATE, ASSET}`). The
cascade CLI (`activate.py:_render_cascade_activation`) attempts a real activation
per proposed id; for `template`/`asset` that attempt raises inside
`CharterPackManager._require_kind` and is caught into a yellow
"could not cascade-activate template/<id>" warning. This warning noise is
**pre-existing** — 137 sources already reach `template`/`asset` via
`requires`/`suggests` today — but widening the reach to mission types would
multiply it across every mission-type activation.

The decision this ADR records is therefore two-part and load-bearing: **which
relations join the followed set**, and **what the cascade is allowed to propose
as a target**.

## Decision Drivers

* **Close the #2829 dead-end for all built-in mission types** — the cascade from a
  mission type must reach the governance its action steps depend on.
* **Kind-completeness** — the cascade should propose only artifacts an operator
  can actually activate; proposing a non-activatable kind is a defect (it can
  only ever produce a caught-and-warned no-op).
* **Single canonical authority** — the activatable-kind decision must be read
  from the one existing authority (`CHARTER_ACTIVATABLE_KINDS`), not a re-declared
  exclusion list, and the engine must not grow a per-specific-kind branch.
* **No over-cascade** — a relation joins the followed set only if traversing it
  expresses "the source *references* the target as something that should activate
  with it". Lineage, overlay, runtime handoff, tension, and anti-pattern
  relations do not, and must stay excluded.
* **Activation/deactivation symmetry** — the followed set feeds both the
  activation closure and the shared-reference-safe deactivation exclusivity
  computation; the two must agree.

## Considered Options

1. **Add `scope` + `instantiates`; filter candidates to
   `CHARTER_ACTIVATABLE_KINDS`.** (Chosen.)
2. **Add `scope` only; filter candidates.** Reaches the same activatable set
   (templates would be filtered out anyway), but leaves the action hop
   half-followed and the engine inconsistent with the 137 sources that already
   reach templates through the graph.
3. **Add `scope` + `instantiates`; no candidate filter.** Smallest change to
   `cascade.py`, but every mission-type activation emits one
   "could not cascade-activate template/<id>" warning per reached template — poor
   operator UX and leaves the pre-existing noise in place.
4. **Also add `vocabulary`.** `vocabulary` targets `glossary_scope`, which is not
   an `ArtifactKind` and is dropped regardless; there are zero `vocabulary` edges
   in the shipped graph and `glossary_scope` is a leaf. Following it is provably
   inert for cascade, and glossary-scope delivery already lives in
   `resolve_context` (step 4) and the M4 delivery path. Rejected for principled
   minimality.

## Decision

**The cascade followed set becomes `{requires, suggests, refines, scope,
instantiates}`, and `_referenced_artifacts` filters its reached-node candidates
to `doctrine.artifact_kinds.CHARTER_ACTIVATABLE_KINDS`.**

- `scope` is the action → governance-artifact edge — the direct #2829 fix.
- `instantiates` is the action → template edge; it is followed so the action hop
  is complete and the engine treats mission-type actions the same way it treats
  the 137 existing sources that already reach templates. Its non-activatable
  targets are handled by the candidate filter, not by omitting the relation —
  **traversal reach and candidacy are separate concerns**.
- The candidate filter reuses the single canonical `CHARTER_ACTIVATABLE_KINDS`
  authority (all kinds minus `template` and `asset`). This is not a
  per-specific-kind branch; it is one membership test against the canonical set,
  so the cascade proposes only activatable artifacts and never emits a
  non-activatable-kind warning — for mission types and for the pre-existing 137
  sources alike.

### Relations deliberately kept out of the followed set

| Relation | Why excluded |
|---|---|
| `vocabulary` | Targets `glossary_scope` (non-artifact, dropped); 0 edges; leaf. Provably inert for cascade. Glossary-scope delivery is `resolve_context`/M4. |
| `applies` | Dead relation — no context walk, cascade, or reference walk follows it; authoring one is refused by an arch gate. |
| `replaces` | Supersession, not a forward reference; 0 edges by design. |
| `delegates_to` | Runtime work handoff between profiles, not a static reference. |
| `specializes_from` | Static profile/artifact lineage, resolved by the profile repository, never runtime reach. |
| `enhances` / `overrides` | Pack-overlay field-merge / replacement, only ever org/project-tier; never a built-in forward reference. |
| `in_tension_with` | Symmetric co-valid competitor; neither side references or activates the other. |
| `reconciles_tension` | Points from a reconciler to a tension side; not "activate this too". |
| `rejects` | Points at an anti-pattern/smell node — the opposite of "activate with". |

Following any of these would over-cascade (pull in lineage parents, overlay
sources, handoff partners, tension competitors, or anti-patterns as activation
targets).

### Symmetry

`REFERENCE_RELATIONS` feeds both `_forward_reference_closure` (activation, the
no-cascade warning) and `deactivation_plan` exclusivity. The expansion applies to
both; the excluded relations stay excluded in both; and the candidate filter,
applied in the shared `_referenced_artifacts` seam, keeps `template`/`asset` out
of activation proposals, no-cascade warnings, and deactivation candidates
consistently.

## Consequences

- **Positive**: cascade from every built-in mission type now returns a non-empty
  activatable set (measured 0 → non-zero). Cascade never proposes a
  non-activatable kind, removing the pre-existing template/asset warning noise
  for all 137 affected sources. The engine stays pure graph logic reading one
  canonical kind authority.
- **Neutral**: `instantiates` is followed but its only targets (templates) are
  filtered at candidacy, so it adds no activation target today. It is included
  for action-hop completeness and consistency, and documented as such.
- **Bounded blast radius**: no existing cascade test pinned template/asset in
  cascade output, so the filter is corrective, not a contract break. The change
  is validated by new red-first cascade tests (mission-type reach was 0; filter
  drops template/asset).
- **No golden-count movement from this ADR**: the extractor node/edge/orphan pins
  and the reachability metric measure `resolve_context` (action channel), the
  profile channel, and the graph edge set — not cascade `REFERENCE_RELATIONS`.
  The cascade change moves none of them. (The sibling orphan-wiring work in the
  same mission moves the orphan ledger once; that is out of scope for this ADR.)

## Related

- Issue #2829 (relation-set dead-end); #3009 residual (orphan wiring — sibling
  work package, not this ADR).
- Charter-resolution program brief:
  `docs/plans/charter-resolution/program-brief.md`.
- Mission: `kitty-specs/kind-complete-cascade-orphan-wiring-01M0FQCD/`.
