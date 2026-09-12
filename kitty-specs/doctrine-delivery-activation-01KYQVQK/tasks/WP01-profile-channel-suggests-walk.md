---
work_package_id: WP01
title: Profile-channel suggests walk + when delivery
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-006
planning_base_branch: feat/doctrine-delivery-activation
merge_target_branch: feat/doctrine-delivery-activation
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-activation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-activation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-doctrine-delivery-activation-01KYQVQK
base_commit: 9fc04f50717013c8aa50c3b5c65e32c0ec44d00e
created_at: '2026-07-30T05:16:51.369578+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Core delivery vector
history:
- at: '2026-07-30T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/
create_intent:
- tests/doctrine/drg/test_profile_suggests_delivery.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/reachability.py
- src/charter/progressive_disclosure.py
- src/doctrine/agent_profiles/repository.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Profile-channel suggests walk + when delivery

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any
user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this
work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent
  status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your
  implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what
  you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log
below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

This is **THE core delivery vector** of the mission (plan.md IC-01). PR #3070 authored A–E `suggests`
edges in the DRG (`hand_authored_overlay.py`), but the profile-channel walk still traverses only
`{requires, specializes_from}` — every authored edge is **inert**. WP01 makes the topology live.

By the end of this WP:

1. `PROFILE_CHANNEL_RELATIONS` includes `Relation.SUGGESTS` (`src/doctrine/drg/reachability.py:48-50`).
2. A charter-layer projection surfaces each `suggests` edge's `when` clause (or `STATED_DEFAULT_WHEN`
   when absent) for every artefact the profile channel reaches by `suggests` — reusing
   `link_references`, never re-walking the graph.
3. The profile render path (`_render_profile_sections` in `src/charter/context.py`, and its
   `context_renderers/profile_sections.py` siblings) delivers this suggests-reached doctrine — across
   the kinds it now reaches (paradigm/styleguide/directive/tactic/toolguide/procedure), not just
   procedures — as `when`-labelled **links**, never inlined bodies (NFR-003).
4. At least the `agent_profile_seed_urns` forward-API symbol (and any other of the 9 that genuinely
   gains a cross-file `src/` consumer here) is left ready for WP03's allowlist sweep — **WP01 does NOT
   edit the `_CATEGORY_C_DELIVERY_RAIL_FORWARD_API` frozenset itself** (that edit is WP03's, per the
   plan's split ownership) but MUST leave a clear trail (docstring/Activity Log note) of exactly which
   symbols it wired.
5. A red-first ATDD suite proves delivery on the **profile channel**, never `resolve_context`.

**Success criteria (from contract `suggests-delivery-walk.md`, acceptances A0–A6)**:

- A0: `test_reachability.py:710
  TestProfileChannelReachability::test_profile_relations_are_requires_and_specializes_from` is RED
  before your change (it currently pins `{requires, specializes_from}` only) and GREEN after, updated
  to assert `{requires, specializes_from, suggests}`.
- A1: `profile_channel_reachable(graph, {agent_profile:architect-alphonso})` includes
  `paradigm:domain-driven-design` (Family A) and the profile render path surfaces its `when`.
- A2: an implementer profile's channel includes the `refactoring-*` tactics (Family B) with `when`.
- A3: a `suggests` edge with no authored `when` surfaces `STATED_DEFAULT_WHEN`.
- A4: a diamond artefact (reachable via both `requires` and `suggests`) is delivered once, eager
  (requires precedence).
- A5: suggested artefacts appear as references (links), not inlined bodies.
- A6: the action channel's delivered set (`resolve_context`) is unchanged by this WP.

## Context & Constraints

- **Governing docs**: `.kittify/charter/charter.md` (project charter); mission
  `kitty-specs/doctrine-delivery-activation-01KYQVQK/plan.md` (IC-01, IC-02); `tasks.md` (WP01 row);
  `contracts/suggests-delivery-walk.md` (the authoritative behavioural contract — read it in full
  before starting); `pre-planning-ledger.md` (D1–D19, especially D10/D11/D17/R-M6/R-M7 — the grounding
  facts below are extracted from there and independently re-verified against live code on
  2026-07-30).
- **D10 (BLOCKING — do not violate)**: assert delivery on
  `profile_channel_reachable(graph, {agent_profile:architect-alphonso})` **and the profile render
  path**. `doctrine.drg.query.resolve_context` (the ACTION channel) is FORBIDDEN as the ATDD entry
  point: DDD is already action-reachable there (vacuously green) and `resolve_context` seeded from a
  profile reaches **nothing** (`test_reachability.py:720
  test_resolve_context_from_a_profile_reaches_nothing` pins this — permanently red if misused).
- **D11 (BLOCKING seam fact)**: `when` lives on the **inbound** edge that reaches an artefact, and
  `profile_channel_reachable` returns `visited - seed_set` — it **strips the profile seeds**, which
  are exactly the sources of the first-hop Family A/B edges (`agent_profile:architect-alphonso →
  paradigm:domain-driven-design`, `agent_profile:python-pedro → directive:DISCIPLINED_REFACTORING`,
  etc.). A per-reached-node `edges_from(reached, SUGGESTS)` therefore **misses** those edges entirely
  and would surface no `when` for the headline families. You MUST instead reuse
  `link_references(merged, roots=profile_seeds, delivered=<kind-filtered reached set>,
  bridge_urns=reached ∪ seeds)` (`src/charter/progressive_disclosure.py:110-154`, verified live at
  time of writing). Note `reached ∪ seeds == visited` (the walk's own return value before you strip
  seeds) — so this is **no second walk**, just reusing values you already computed. Do NOT author a
  bespoke projection or a `reachability_delivery/`-style copy of `link_references` (C-002: the 10
  progressive_disclosure composition helpers — `link_references`, `edge_to_reference`,
  `requires_closure`, `partition_delivery`, `STATED_DEFAULT_WHEN`, etc. — are consumed as internal
  helpers of that module, not re-derived).
- **R-M7 (MANDATORY placement)**: the profile-channel `when`-projection function lands in
  `src/charter/progressive_disclosure.py` (a sibling function beside `link_references`) — **NOT**
  inline in `src/charter/context.py`. `context.py` is a 3528-line module already flagged for
  extraction (IC-08/WP04, sequenced *after* this WP); growing it further here works against that plan.
  A minimal `context.py` touch (a kind-delivery table entry + the call site) is acceptable and
  documented as an out-of-map edit below — do not go further than that.
- **Verified live code anchors** (re-confirmed 2026-07-30, cite these, don't re-derive):
  - `PROFILE_CHANNEL_RELATIONS = frozenset({Relation.REQUIRES, Relation.SPECIALIZES_FROM})` —
    `src/doctrine/drg/reachability.py:48-50`.
  - `profile_channel_reachable(graph, seeds)` — `reachability.py:99-125` — calls
    `walk_edges(graph, seed_set, set(PROFILE_CHANNEL_RELATIONS), max_depth=None)` then returns
    `visited - seed_set`.
  - `link_references(merged, roots, delivered_urns, *, bridge_urns=())` —
    `src/charter/progressive_disclosure.py:110-154` — iterates `sources = roots ∪ delivered ∪
    bridge_urns`, keeps `(bare_id(target), relation)` deduped, for every edge whose target is in
    `delivered`. This is your projection primitive.
  - `edge_to_reference(edge)` — `progressive_disclosure.py:52-68` — projects one `DRGEdge` to
    `{id, relation, when, reason}`, substituting `STATED_DEFAULT_WHEN` when `edge.when` is falsy and
    `edge.relation is Relation.SUGGESTS`.
  - `STATED_DEFAULT_WHEN` — `progressive_disclosure.py:33-36`.
  - `requires_closure(merged, roots)` / `partition_delivery(merged, roots, delivered_urns)` —
    `progressive_disclosure.py:81-107` — the requires-precedence split you must reuse for A4 (a
    diamond artefact inside the `requires` closure of the roots stays eager/inline; only the
    remainder renders as a link).
  - **Sole current consumer**, procedures-only: `profile_channel_procedure_ids(self, profile_id)` —
    `src/doctrine/agent_profiles/repository.py:855-877` — calls `profile_channel_reachable`, filters
    `urn.startswith("procedure:")`, returns bare sorted ids with **no relation/when surfaced**. This is
    the method you widen (or the method whose sibling you add) for C4 (kind delivery).
  - **Render-path precedent to extend**, `render_profile_procedures(profile, service)` —
    `src/charter/context_renderers/profile_sections.py:220-247` — the ONLY existing renderer that
    consumes the profile channel; it calls `profile_channel_procedure_ids` and renders via
    `render_profile_selector_refs(..., when_clause=<static string>, body_fn=format_inline_named_body)`.
    Note this reuses a **static** `when_clause` per selector kind, not a per-edge `when` — your new
    suggests-delivery rendering needs the **per-edge** `when` from the T002 projection, so plan to add
    a distinct renderer (or extend `render_profile_selector_refs` to accept a per-entry `when`
    override) rather than force-fitting the existing static-when path.
  - `_render_profile_sections(profile, service)` — `src/charter/context.py:3046-3072` — composes
    `(_render_profile_directives, _render_profile_tactics, _render_profile_styleguides,
    _render_profile_toolguides, _render_profile_procedures)`. Its own docstring says: *"Unattested
    kinds (asset/anti-pattern/paradigm) are C-007 deferrals and contribute no section."* **This is
    exactly the gap you close for `suggests`-reached paradigms** (Family A: `domain-driven-design`) —
    you are not contradicting that docstring's C-007 deferral (which is about *schema-attested inline
    citation* kinds), you are adding a new, distinct *channel-resolved* section, analogous to how
    `render_profile_procedures` already differs from `_render_profile_directives`
    (citation-list-driven) by being channel-driven.
  - `_ActionDoctrineBundle.bridge_urns` and the requires-closure "fetch + when-doing" render cadence
    (`context.py:1202-1253 _render_action_doctrine_lines`) is the **action-channel** precedent for
    "inline inside requires-closure, link outside it" — reuse the *pattern* (C-003), not the code
    (that function is action-channel-specific and out of scope here).
- **Family A/B/C when-authorship state** (grounds T002's A1/A3 acceptance): Family A edges
  (`agent_profile:{architect-alphonso,paula-patterns,randy-reducer} → paradigm:domain-driven-design`,
  `hand_authored_overlay.py:534-564`) currently carry `reason=` **only, no `when=`** — WP02 backfills
  `when` on these edges; until WP02 lands, A1's `when` assertion will read `STATED_DEFAULT_WHEN` for
  Family A specifically (a still-`when`-less Family A edge is exactly A3's proof case). Family B
  (`directive:DISCIPLINED_REFACTORING → tactic:refactoring-*`, `hand_authored_overlay.py:622-717`) and
  Family C (`directive:USE_C4_MODEL_TECHNIQUES → …`, `hand_authored_overlay.py:878-1017`) already
  carry authored `when=` text on every edge — use these for A2's assertion (they don't depend on WP02).
- **Out-of-map `context.py` touch (documented rationale)**: `context.py` is authoritatively owned by
  WP04 (context_renderers extraction, IC-08) and WP01 owns `progressive_disclosure.py` /
  `reachability.py` / `repository.py`. WP01 nonetheless needs ONE small `context.py` edit: registering
  the new suggests-delivery renderer into `_render_profile_sections`'s `section_renderers` tuple
  (`context.py:3057-3063`) — this is a one-line addition to an existing tuple literal, not a new
  helper body (the helper body lives in `context_renderers/profile_sections.py`, which you also own
  for this WP's purposes). This is a *documented, minimal, out-of-map edit* per the mission brief —
  record it explicitly in this WP's Activity Log so WP04's reviewer isn't surprised by a diff outside
  `owned_files`.
- **Out-of-map `test_reachability.py:710` touch (documented)**: adding `SUGGESTS` turns the A0 assertion
  `test_profile_relations_are_requires_and_specializes_from` (`tests/doctrine/drg/test_reachability.py:710`,
  owned by WP03) RED — that is the intended red-first signal. WP01 updates that single assertion to the new
  relation set to green it; `test_reachability.py` is otherwise WP03's file (the pins). Sequential-safe (WP03
  deps WP01 and rebases after). Record it in the Activity Log so WP03's reviewer isn't surprised.
- **Reciprocal touch note**: WP06 (schema-error UX) may make a verify-only/out-of-map touch to
  `agent_profiles/repository.py` (the `_source_paths` twin, predicted no-op). Different hunk from your
  `profile_channel_procedure_ids` widening; do NOT implement WP01 and WP06 concurrently on this file.
- **Constraints carried from spec.md**: C-001 (consume the forward API, never hand-roll a walk — you
  are calling `profile_channel_reachable`/`link_references`, not reimplementing them), C-002 (the 10
  progressive_disclosure helpers are module-private/internal — consume them as such), C-003 (build on
  `_ActionDoctrineBundle` cadence pattern, don't re-derive it for the profile channel — your projection
  is a new, profile-channel-scoped function, not a bolt-on to the action-channel bundle).

## Branch Strategy

- **Strategy**: Planning artifacts generated on feat/doctrine-delivery-activation; during implement
  this WP may branch from a dependency-specific base but merges back into
  feat/doctrine-delivery-activation unless the human redirects.
- **Planning base branch**: feat/doctrine-delivery-activation
- **Merge target branch**: feat/doctrine-delivery-activation

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T001 – Add `Relation.SUGGESTS` to `PROFILE_CHANNEL_RELATIONS`

- **Purpose**: Widen the profile-channel walk's relation set so it follows `suggests` edges in
  addition to `requires`/`specializes_from` — the single-line change that makes the A–E families
  reachable in principle (FR-001).
- **Steps**:
  1. In `src/doctrine/drg/reachability.py:48-50`, change
     `PROFILE_CHANNEL_RELATIONS: frozenset[Relation] = frozenset({Relation.REQUIRES,
     Relation.SPECIALIZES_FROM})` to include `Relation.SUGGESTS`.
  2. Update the module docstring (lines 1-25) and the inline comment directly above the constant
     (lines 44-47, which currently says *"deliberately a two-relation `walk_edges` set and **not** the
     `scope`/`requires`/`suggests` shape of `resolve_context`"*) — this sentence becomes stale/
     misleading once `suggests` is added to the profile channel too; rewrite it to state the profile
     channel is now `{requires, specializes_from, suggests}` while still explicitly NOT including
     `scope` (the fact that makes it distinct from `resolve_context` — R-3 in the module docstring
     still holds: profiles carry zero outbound `scope`, so folding channels would measure zero; that
     rationale is untouched, only the relation-set enumeration needs updating).
  3. Do not touch `action_channel_reachable`/`resolve_context` or anything in `doctrine/drg/query.py`
     — the action channel is a separate, unaffected walk (A6).
- **Files**: `src/doctrine/drg/reachability.py`.
- **Parallel?**: Do this first; T002/T003 depend on the walk actually reaching `suggests` targets to
  build against real data (though the projection function itself is separable in principle).
- **Notes**: This is the guaranteed mechanical red per A0 —
  `test_reachability.py:710 test_profile_relations_are_requires_and_specializes_from` currently pins
  `{"requires", "specializes_from"}`; update it to `{"requires", "specializes_from", "suggests"}` as
  part of T005 (not here — T001 is the production code change; the test update is the ATDD subtask).

### Subtask T002 – Profile-channel `when`-projection reusing `link_references`

- **Purpose**: Surface each `suggests` edge's `when` clause as the delivered artefact's applicability
  condition, without a second walk and without discarding the seed-sourced edges (D11).
- **Steps**:
  1. Add a new function to `src/charter/progressive_disclosure.py` — e.g.
     `profile_channel_references(merged, seeds, delivered_urns) -> list[dict[str, str | None]]` (name
     is your call; keep it consistent with the module's existing naming, and export it via `__all__`
     if `context_renderers/profile_sections.py` needs to import it directly — check whether the render
     layer can call `link_references` itself instead of adding a wrapper; prefer NOT adding a thin
     wrapper if the caller can just call `link_references(merged, roots=seeds, delivered=...,
     bridge_urns=reached ∪ seeds)` directly, per C-002's "consume as internal, don't grow the public
     surface" spirit).
  2. The call shape (per contract C2): `link_references(merged, roots=profile_seeds,
     delivered=<kind-filtered reached set>, bridge_urns=reached ∪ seeds)`. Concretely: call
     `walk_edges`'s result via `profile_channel_reachable` (or its raw `visited` before the seed-strip,
     if you need `bridge_urns` to include seeds — check whether you need to call `walk_edges` yourself
     one level down to get `visited` including seeds, or whether `reached | seed_set` reconstructs it
     losslessly — the ledger states `reached ∪ seeds == visited`, so reconstructing from the public
     `profile_channel_reachable` return value plus the seed set you already hold is sufficient; no need
     to touch `walk_edges` directly).
  3. `delivered` should be the artefact URNs you intend to actually render (post kind-filtering from
     T003) — `link_references` only emits a reference for `edge.target in delivered`, so filtering
     `delivered` to your kind allowlist naturally suppresses references to kinds you don't render,
     without needing a second pass.
  4. Verify `edge_to_reference`'s `STATED_DEFAULT_WHEN` substitution fires correctly for A3 (edge has
     no authored `when` AND `relation is SUGGESTS`) and does NOT fire for `requires` edges with no
     `when` (they have no applicability gate by design — `requires_closure`'s docstring: *"a required
     artefact is delivered inline with no `when` to evaluate"*).
  5. Confirm dedup: `link_references` already dedups on `(bare_id(target), relation.value)` — this
     satisfies C5 (dedup across diamonds/multiple source profiles) with no extra work; write a test
     (T005/A4) proving it rather than trusting the docstring blind.
- **Files**: `src/charter/progressive_disclosure.py`.
- **Parallel?**: Can be developed in parallel with T003's render-layer scaffolding, but T003's actual
  wiring depends on this function's final signature — coordinate within the same commit if convenient
  rather than sequencing as two separate commits.
- **Notes**: Do NOT create a `charter/reachability_delivery/` module or any copy of `link_references`'s
  logic (explicit contract prohibition, C2). If you find you need something `link_references` doesn't
  give you, that is a signal to re-read the contract before inventing a parallel path — the mission's
  own history includes multiple hand-rolled-walk incidents (see `reachability.py`'s docstring: "Every
  hand-rolled BFS in this mission's history produced a *different* wrong number").

### Subtask T003 – Widen kind delivery + profile-render consumer beyond procedures

- **Purpose**: Following `suggests` reaches non-procedure kinds (paradigm/styleguide/directive/tactic/
  toolguide) — someone has to decide which of those kinds actually deliver, and the render path has to
  grow a section that surfaces them as links with T002's `when` (FR-002, FR-003, C4).
- **Steps**:
  1. Decide (and document in a code comment) the kind delivery table for suggests-reached artefacts.
     Minimum bar to satisfy A1/A2: `paradigm` (Family A: `domain-driven-design`) and `tactic` (Family
     B: `refactoring-*`) MUST deliver. Recommend also including `directive`, `styleguide`, `toolguide`,
     `procedure` for consistency (Family B's hub is itself a `directive`;
     `procedure:drill-down-documentation` is Family-C-reachable) — but do NOT include `asset` or
     `anti_pattern` (non-activatable kinds per C-004/models.py:73; excluding them here is what keeps
     WP02's anti_pattern topology validation-tier-only, not accidentally delivered).
  2. Widen (or add a sibling to) `AgentProfileRepository.profile_channel_procedure_ids`
     (`src/doctrine/agent_profiles/repository.py:855-877`) so the profile channel's reached set is
     available beyond the procedure-only filter — e.g. a new method returning the raw reached URN set
     (or a kind-partitioned dict) that both the existing procedure consumer and your new renderer can
     use. Keep `profile_channel_procedure_ids` itself working unchanged (it may become a thin filter
     over the new method, or stay as-is if you add a parallel method — your call, but do not regress
     its existing behaviour or its callers).
  3. Add a new renderer in `src/charter/context_renderers/profile_sections.py` (sibling to
     `render_profile_procedures`) that: (a) gets the suggests-reached, kind-filtered URNs for the
     profile; (b) calls T002's projection to get `(id, relation, when, reason)` per artefact; (c)
     renders each as a link/fetch stanza carrying the **per-edge `when`** (NOT the static
     `_PROFILE_CODE_CHANGE_WHEN`/`when_clause` pattern `render_profile_selector_refs` uses today —
     either extend that helper to accept a per-entry `when` override, or write a focused new render
     loop; prefer extending `render_profile_selector_refs` if the diff stays small, since it already
     owns the catalog-miss/budget/fetch-stanza machinery you'd otherwise duplicate).
  4. Apply requires-precedence (A4): before rendering as a link, check whether the artefact is already
     inside the profile's `requires`-closure delivery (if the profile channel already delivers it
     eagerly via a `requires` path — check how/whether the existing directive/tactic renderers already
     cover this, since `profile.directive_references`/`tactic_references` are citation-driven, not
     walk-driven, so "eager via requires" for the profile channel specifically may need
     `partition_delivery`/`requires_closure` called against `profile_channel_reachable`'s own
     `{requires, specializes_from}` subset — reason through this carefully and document your resolution
     in a code comment, since the contract's diamond example (C5) is exactly this case).
  5. Register the new renderer in `_render_profile_sections`'s `section_renderers` tuple
     (`src/charter/context.py:3057-3063`) — this is the one documented out-of-map `context.py` edit
     (see Context & Constraints above).
- **Files**: `src/doctrine/agent_profiles/repository.py`, `src/charter/context_renderers/
  profile_sections.py`, `src/charter/context.py` (one-line tuple registration only, documented
  out-of-map edit).
- **Parallel?**: Sequenced after T001/T002 land (needs both the widened walk and the projection).
- **Notes**: `render_profile_selector_refs`'s catalog-miss / budget / fetch-stanza machinery
  (`profile_sections.py:88-153`) already handles the "artefact not found in catalog" and "body too
  large, degrade to link" cases correctly — reuse it rather than re-deriving budget/miss logic.

### Subtask T004 – Consume forward-API seed helpers cross-file

- **Purpose**: `agent_profile_seed_urns` (and possibly `PROFILE_CHANNEL_RELATIONS`,
  `partition_delivery` — D17 pre-classification, confirm per-symbol here) are currently forward API
  with zero `src/` consumers, allowlisted in `_CATEGORY_C_DELIVERY_RAIL_FORWARD_API`
  (`tests/architectural/test_no_dead_symbols.py:1089-1106`). This mission's delivery walk is exactly
  where they should get genuine cross-file consumers — feeds WP03's allowlist retirement (FR-006/C6).
- **Steps**:
  1. Wherever your T002/T003 code needs the set of activated agent-profile seed URNs, call
     `agent_profile_seed_urns(graph)` (`reachability.py:58-`) rather than re-deriving it (e.g. rather
     than filtering `graph.nodes` for `NodeKind.AGENT_PROFILE` inline in `context.py` or `repository.py`
     — that would be exactly the "manufactured importer" anti-pattern the gate warns against; only wire
     it where you have a **genuine** use, don't add a no-op call just to trip the counter).
  2. `PROFILE_CHANNEL_RELATIONS` already has one consumer (`profile_channel_reachable` itself, intra-
     module) — check whether your T002/T003 code needs to import it directly from a different module
     (e.g. to compute `bridge_urns` or to assert channel membership) — if so, that's a second,
     cross-file consumer worth noting.
  3. `partition_delivery` (`progressive_disclosure.py:93-107`) is the D17 "possibly" symbol — if your
     A4 diamond-precedence logic in T003 genuinely calls it (rather than re-deriving the inline/link
     split by hand), that's a real wire. Do not force a call to this function purely to retire it from
     the allowlist if `requires_closure` alone suffices for your logic — an artificial import that adds
     no real behaviour is worse than leaving it allowlisted (the gate's `_symbol_has_caller` only
     counts genuine cross-file `src/` importers, and a fabricated one defeats the gate's purpose, per
     NFR-004/FR-006's explicit "no manufactured importers" bar).
  4. **Do not edit `_CATEGORY_C_DELIVERY_RAIL_FORWARD_API` or `tests/architectural/_baselines.yaml`
     yourself** — that frozenset edit is WP03's (terminal, after WP01+WP02 land, per the plan's split
     ownership of consumption-edits-vs-frozenset-edits). Your job here is only to make the symbols
     genuinely `src`-consumed.
  5. In your Activity Log entry for this subtask, explicitly list which of the 9 symbols you gave a
     cross-file `src/` consumer to (name them), so WP03 doesn't have to re-derive this from a diff.
- **Files**: whichever of `reachability.py` / `progressive_disclosure.py` / `repository.py` /
  `context_renderers/profile_sections.py` end up importing these symbols cross-file as a natural
  consequence of T002/T003 (no dedicated new file for this subtask).
- **Parallel?**: Not a separate coding pass — this is a verification/bookkeeping lens applied while
  doing T002/T003, plus the Activity Log note.
- **Notes**: `test_no_dead_symbols`'s `_symbol_has_caller` counts ONLY cross-file `src/` importers;
  test imports (including your own T005 ATDD suite) do NOT count. This means your ATDD test importing
  `profile_channel_reachable` or `agent_profile_seed_urns` does not, by itself, retire anything from
  the allowlist — genuine `src/`-to-`src/` wiring is what matters.

### Subtask T005 – ATDD suite (A0–A6)

- **Purpose**: Prove the delivery vector actually delivers, red-first, on the correct channel (D10).
- **Steps**:
  1. Create `tests/doctrine/drg/test_profile_suggests_delivery.py` (new file — matches
     `create_intent`). Structure it to cover A1–A6 explicitly (one test or a small cluster per
     acceptance, named so a reviewer can map test → acceptance letter at a glance).
  2. **A1**: `profile_channel_reachable(graph, {"agent_profile:architect-alphonso"})` (using the real
     merged built-in graph — see how `tests/doctrine/drg/test_reachability.py`'s `graph` fixture is
     constructed and reuse the same fixture pattern) includes `"paradigm:domain-driven-design"`. Then
     assert the render path (call `_render_profile_sections` or your new
     `context_renderers.profile_sections` function directly with a resolved `architect-alphonso`
     profile + a `DoctrineService`) surfaces `domain-driven-design` with a `when` string present
     (either the authored one if WP02 has landed by the time this runs, or `STATED_DEFAULT_WHEN` if
     not — assert presence and non-emptiness, not the exact literal, so this test doesn't couple
     WP01→WP02 landing order more than necessary; RED before your change because
     `paradigm:domain-driven-design` is entirely absent from both the reached set and any render
     section today).
  3. **A2**: same shape for an implementer profile (e.g. `python-pedro`) — `refactoring-*` tactics
     reachable + rendered with `when` present and equal to (or derived from) the authored Family-B
     `when` text (`hand_authored_overlay.py:622-717` already carries real `when=` strings — assert one
     verbatim, e.g. the `refactoring-move-method` "feature envy" `when`).
  4. **A3**: pick a `suggests` edge you know is still `when`-less at WP01 time (Family A, before WP02's
     backfill — `agent_profile:architect-alphonso → paradigm:domain-driven-design`) and assert the
     projected reference's `when` equals `progressive_disclosure.STATED_DEFAULT_WHEN` exactly. **This
     test WILL need updating once WP02 backfills Family A's `when`** — leave an explicit comment saying
     so, so WP02's implementer/reviewer knows to either re-target this assertion at a still-when-less
     edge or accept the test moving to WP02's diff.
  5. **A4**: construct or find a real diamond (an artefact reachable via both `requires` and
     `suggests` from the same or different profiles) and assert it renders exactly once, eager/inline
     (not as a link). If no real diamond exists in the shipped graph, build a small synthetic
     `DRGGraph` fixture for this one assertion rather than skipping it — the acceptance is
     load-bearing (C5/NFR contract item).
  6. **A5**: assert the rendered profile-channel output contains reference/link markers (e.g. a fetch
     stanza / `--include <selector>` string, or your DTO's `delivery == "link"` marker if you exposed
     one) for a `suggests`-only artefact, and does NOT contain that artefact's full body text inline.
  7. **A6**: assert `action_channel_reachable`/`resolve_context`'s delivered set for a fixed action
     seed (e.g. `action:documentation/design`) is byte-identical before and after your change — a
     simple two-call diff test; this is your isolation guard against having accidentally touched
     `query.py`/`resolve_context`.
  8. Update `test_reachability.py:710`'s A0 assertion (the mechanical red) to
     `{"requires", "specializes_from", "suggests"}` as part of this subtask (T001 changed production
     code; this is the paired test update — keep it in the same commit as T001 for reviewability, or
     clearly cross-reference).
  9. Run the full targeted suite before calling this done — see Definition of Done below for exact
     node-ids.
- **Files**: `tests/doctrine/drg/test_profile_suggests_delivery.py` (new),
  `tests/doctrine/drg/test_reachability.py` (A0 update only — do not touch `_PROFILE_UNREACHABLE`/
  `_PROFILE_RESCUES`, those are WP03's terminal reconciliation).
- **Parallel?**: Write test skeletons alongside T002/T003 (red-first discipline), finalize once T001-
  T004 land.
- **Notes**: Do NOT assert on `resolve_context` anywhere in this file (D10, hard block). If you find
  yourself reaching for `resolve_context` to make an assertion "easier", that is the exact anti-pattern
  the contract forbids — go back to `profile_channel_reachable` + the render path.

## Test Strategy

- **Framework**: pytest, `uv run pytest <nodeid>` — targeted node-ids only, never the full
  `tests/architectural/` suite locally (it breaks the session; CI owns the sweep).
- **Red-first**: write T005's tests against pre-WP01 code first (or run them immediately after T001
  alone, before T002/T003) to confirm they fail for the *right* reason (missing delivery, not a typo/
  import error), then implement T002-T004 to turn them green.
- **Exact commands** (run after each subtask, and all together before marking done):
  ```bash
  uv run pytest tests/doctrine/drg/test_reachability.py -k "test_profile_relations_are_requires_and_specializes_from or test_resolve_context_from_a_profile_reaches_nothing" -q
  uv run pytest tests/doctrine/drg/test_profile_suggests_delivery.py -q
  uv run pytest tests/doctrine/drg/test_reachability.py -q
  uv run pytest tests/charter/test_every_load_delivery.py -q
  uv run pytest tests/charter/test_action_bundle_delivery.py -q
  uv run pytest tests/doctrine/agent_profiles/ -q
  ```
  (If `tests/charter/test_every_load_delivery.py` false-reds locally due to an ambient
  `context-state.json`, that is the known WP07 hermeticity issue — check whether WP07 has landed on
  your base; if not, note the false-red explicitly rather than treating it as your own regression, per
  the CLAUDE.md baseline-red gotcha.)
- **Lint/type**: `ruff check src/doctrine/drg/reachability.py src/charter/progressive_disclosure.py
  src/doctrine/agent_profiles/repository.py src/charter/context_renderers/profile_sections.py
  src/charter/context.py` and `mypy --strict` over the same files — zero new issues, zero new
  suppressions (NFR-005).

## Risks & Mitigations

- **Re-deriving the walk instead of reusing `link_references`** (D11's exact failure mode) — mitigate
  by re-reading contract C2 before writing T002, and by A4's diamond test catching a naive
  re-implementation that double-delivers.
- **Growing `context.py`** beyond the one documented tuple-registration line — mitigate by keeping all
  real renderer logic in `context_renderers/profile_sections.py`; if you find yourself writing more
  than ~5 lines in `context.py`, stop and move it to the sibling module.
- **Coupling T005's A1/A3 assertions to WP02's Family-A `when` backfill landing order** — mitigate by
  asserting presence/non-emptiness rather than the exact `when` literal for Family A specifically (A2's
  Family-B assertion can safely assert the literal, since Family B already has an authored `when`
  today, independent of WP02).
- **Manufacturing a forward-API importer just to shrink the allowlist** — explicitly forbidden by
  FR-006's "no manufactured importers" bar; only wire symbols you have a genuine use for (T004 guidance
  above).
- **Kind delivery table scope creep** — resist the temptation to also deliver `asset`/`anti_pattern`
  kinds through this path; that would pre-empt WP02's validation-tier design for anti-patterns (D14)
  and violate C-004.

## Review Guidance

- Confirm the ATDD suite (T005) asserts on `profile_channel_reachable` + the render path, **never**
  `resolve_context` — grep the new test file for `resolve_context` and reject if found outside A6's
  isolation check.
- Confirm `link_references` is reused (not re-implemented) — grep `progressive_disclosure.py`'s diff
  for a new function that duplicates its edge-iteration logic instead of calling it.
- Confirm `context.py`'s diff is limited to the one documented tuple-registration edit — anything
  larger should be flagged back to the implementer or explicitly renegotiated with WP04's owner.
- Confirm the Activity Log names which forward-API symbols got a genuine cross-file `src/` consumer
  (T004's deliverable is a fact, not code — verify it's recorded, not just implied).
- Confirm A4's diamond test is real (either found in the shipped graph or a clearly-labelled synthetic
  fixture) and actually exercises `requires`-precedence, not just asserting a single-delivery count
  that happens to pass for an unrelated reason.
- Confirm no edits landed in `tests/doctrine/drg/test_reachability.py`'s `_PROFILE_UNREACHABLE`/
  `_PROFILE_RESCUES` blocks (WP03's terminal reconciliation owns those) — only the A0 relation-set
  assertion should change here.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:

```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>
```

**Example (correct chronological order)**:

```
- 2026-01-12T10:00:00Z – system – Prompt created
- 2026-01-12T10:30:00Z – claude – Started implementation
- 2026-01-12T11:00:00Z – codex – Implementation complete, ready for review
- 2026-01-12T11:30:00Z – claude – Review passed, all tests passing  ← LATEST (at bottom)
```

**Common mistakes (DO NOT DO THIS)**:

- Adding new entry at the top (breaks chronological order)
- Using future timestamps (causes acceptance validation to fail)
- Inserting in middle instead of appending to end

**Why this matters**: The acceptance system reads the LAST activity log entry as the current state. If
entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- 2026-07-30T00:00:00Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task <WPID> --to
<status>` to change WP status.

### Optional Phase Subdirectories

For large features, organize prompts under `tasks/` to keep bundles grouped while maintaining lexical
ordering.
- 2026-07-30T05:45:36Z – unknown – shell_pid=1378716 – WP01 impl: T001-T005 complete. Wired forward-API cross-file (src->src): agent_profile_seed_urns (doctrine.drg.reachability -> doctrine.agent_profiles.repository:889, fail-closed seed-identity guard in profile_channel_reached). NOT wired (no genuine non-manufactured use, left allowlisted for WP03): PROFILE_CHANNEL_RELATIONS, partition_delivery, action_channel_reachable, action_seed_urns + the 4 pack_context symbols. Out-of-map edits (documented): test_reachability.py:710 A0 assertion greened to {requires,specializes_from,suggests}; context.py one-line renderer registration in _render_profile_sections tuple. EXPECTED WP03-OWNED REDS (do not treat as WP01 defects): (1) test_reachability.py::test_profile_unreachable_is_the_pinned_membership - _PROFILE_UNREACHABLE pin shrinks because delivery is now live (WP03 terminal reconciliation); (2) test_no_dead_symbols::test_no_public_symbol_in_all_is_unimported - agent_profile_seed_urns now has a caller (stale allowlist entry -> WP03 removes) AND PROFILE_CHANNEL_RELATIONS body hash changed by T001 (WP03 re-pins). A0-A6 all green; ruff+mypy clean on all changed files.
