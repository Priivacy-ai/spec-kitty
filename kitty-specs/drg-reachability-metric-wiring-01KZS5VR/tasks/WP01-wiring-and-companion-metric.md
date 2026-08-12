---
work_package_id: WP01
title: Wiring + companion metric + pin reconciliation
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-010
planning_base_branch: fix/drg-reachability-metric-wiring
merge_target_branch: fix/drg-reachability-metric-wiring
branch_strategy: Planning artifacts for this mission were generated on fix/drg-reachability-metric-wiring. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/drg-reachability-metric-wiring unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
history:
- at: '2026-08-11T20:00:00+00:00'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/
create_intent: []
execution_mode: code_change
model: claude-sonnet-4-5
owned_files:
- src/doctrine/drg/migration/extractor.py
- packs/built-in/*.graph.yaml
- tests/doctrine/drg/test_reachability.py
- tests/doctrine/drg/migration/test_extractor_projection.py
- tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py
- docs/plans/doctrine/delivery-reachability-wiring-table.md
- docs/development/3-2-page-inventory.yaml
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile with `/ad-hoc-profile-load python-pedro`
(or read `packs/built-in/agent_profiles/python-pedro.agent.yaml` and state the directives/tactics you will
apply). You are the **implementer**. Apply TDD/ATDD discipline, type safety, and idiomatic Python. Do not
invent scope beyond `owned_files`.

## Objective

Author the six genuine, traced inbound edges that make the residual DRG orphans reachable; regenerate the
shipped graph deterministically; add the `_ACTION_UNREACHABLE_SHIPPED` **action-only reachability companion
guard** (the #3009 point-3 deliverable) with its asserted 34-dead / 41-profile-delivered partition; and
reconcile **every** moved golden pin with a wiring-table composition-ledger row — keeping all existing DRG
guards green. This is one atomic, tightly-coupled change (graph + both ledger test files + the wiring-table
doc); it is a single WP by design (see tasks.md rationale).

**Binding policy (D-C2 / C-001 / C-003):** an orphan is *unreferenced, not defective*. Wire only genuine
referents (each cited to artifact text); never manufacture an edge to shrink a metric; never delete a valid
artifact; reachability/incidence residual sets may only **shrink or hold**.

## Essential context

- **Graph load**: `from doctrine.drg.loader import load_built_in_graph` (reads `packs/built-in/`). Use
  `.venv/bin/python` for introspection (has deps). NEVER `uv run` (destroys the hand-built `.venv`).
- **Reachability helpers (canonical — MUST use, never re-implement a walk)**:
  `doctrine.drg.reachability.action_channel_reachable(graph, action_seeds, depth)` and
  `profile_channel_reachable(graph, profile_seeds)`. `PROFILE_CHANNEL_RELATIONS = {requires,
  specializes_from, suggests}` (3 relations). `resolve_context` (query.py:139): scope(d1) → requires(∞) +
  suggests(≤depth) from the scope set → vocabulary(d1).
- **Edge model**: construct edges via `doctrine.drg.models.DRGEdge(source=, target=, relation=Relation.X)`
  — NOT `dataclasses.replace` (it is a pydantic model).
- **Authoring site**: `src/doctrine/drg/migration/extractor.py` → `_CURATED_ARTIFACT_EDGES` tuple
  (`:264`, consumed `:866`). This is the operator-blessed #3009-remedy home (precedent: WP09 daphne fix,
  remedy-4 at `:374-386`). Do NOT author these in `hand_authored_overlay.py`.
- **Regenerate (⚠️ USE THE WORKING-DIR CLI)**: `.venv/bin/spec-kitty doctrine regenerate-graph` writes
  `packs/built-in/*.graph.yaml`; `--check` verifies byte-identical. **Do NOT use bare `spec-kitty`** — the
  `PATH` `spec-kitty` is a pyenv shim that resolves the pack root from a different checkout
  (`SHADOW_CLONES/spec-kitty_THREE`) and would write to the wrong tree. Only `.venv/bin/spec-kitty` (and
  `.venv/bin/python` for `load_built_in_graph()`) resolve THIS repo's `packs/built-in`. Verify with
  `.venv/bin/spec-kitty doctrine regenerate-graph --check` — the printed path must be under
  `.../fork/spec-kitty/packs/built-in`, not SHADOW_CLONES.
- Read `research.md`, `data-model.md`, and `contracts/reachability-companion-guard.md` for the full traced
  edge table, the move-set, and the guard contract. These are authoritative.

---

### Subtask T001 — Author the six curated edges

Add six tuples to `_CURATED_ARTIFACT_EDGES`, each with an inline comment citing the artifact text that
establishes the relationship (see research.md trace table):

1. `("procedure:refactoring", "directive:DISCIPLINED_REFACTORING", Relation.SUGGESTS)` — the procedure's
   step 2 selects Fowler tactics; the directive holds 7 disjoint ones. Action-reachable, cascades the
   `refactoring-*` family.
2. `("directive:DIRECTIVE_024", "directive:RECONCILE_CHANGE_SCOPE_TENSIONS", Relation.SUGGESTS)` — the
   reconciler's scope names 024 as its trigger.
3. `("directive:DIRECTIVE_025", "directive:RECONCILE_CHANGE_SCOPE_TENSIONS", Relation.SUGGESTS)` — same, 025.
4. `("directive:DIRECTIVE_030", "directive:USE_MUTATION_TESTING_TO_VALIDATE_TEST_QUALITY", Relation.SUGGESTS)`
   — 030 governs the coverage gate; the mutation directive deepens it. Cascades the mutation family.
5. `("agent_profile:researcher-robbie", "procedure:spike-timebox-policy", Relation.REQUIRES)` — robbie's
   structured `operating-procedures` field lists it.
6a. `("agent_profile:lexical-larry", "procedure:glossary-maintenance-workflow", Relation.SUGGESTS)` —
    **SUGGESTS, not requires**: larry is a "feeder into" the workflow; `curator-carla` owns its acceptance.
6b. `("agent_profile:minutes-maker-mahad", "procedure:meeting-minutes-pipeline", Relation.REQUIRES)` —
    mahad is the "primary agent for" it.

Verify each source URN and target URN exists in the graph before adding (a typo mints a phantom node).

### Subtask T002 — Regenerate the graph fragments

Run `.venv/bin/spec-kitty doctrine regenerate-graph`, then `.venv/bin/spec-kitty doctrine regenerate-graph
--check` to confirm byte-identical output on re-run (determinism). `git diff --stat packs/built-in/` should show only edge
additions in the affected per-kind fragments (`directive.graph.yaml`, `procedure.graph.yaml`,
`agent_profile.graph.yaml`), **zero new nodes** (the 6 edges add no nodes — the node-count inventory tests
must stay green untouched).

### Subtask T003 — Behavioral red-first reach assertions (the real ATDD — Renata F3)

For each wired node, add a **behavioral** assertion that proves the reachability transition via the
canonical helpers — NOT a frozenset-literal edit. Pattern (in `test_reachability.py`, near the existing
`test_ddd_family…` / nominal-wiring tests):

```python
def test_disciplined_refactoring_is_action_reachable_via_refactoring_procedure(shipped_graph):
    reach = action_channel_reachable(shipped_graph, action_seed_urns(shipped_graph), _ACTION_D2_DEPTH)
    assert "directive:DISCIPLINED_REFACTORING" in reach  # was unreachable pre-edge
```

Cover: DISCIPLINED_REFACTORING, RECONCILE, USE_MUTATION (action channel); spike-timebox-policy,
glossary-maintenance-workflow, meeting-minutes-pipeline (profile channel). Add the **delete-edge negative
test** (SC-001): remove one genuine edge from a copy of the graph, assert the companion guard's `measured`
set now contains that node's URN (the guard names it). Reuse the nominal-wiring harness pattern already in
the file (the positive/negative control tests near `:1001-1022`).

### Subtask T004 — Reconcile incidence pins + ceiling

In `tests/doctrine/drg/migration/test_extractor_projection.py`: `RECONCILE_CHANGE_SCOPE_TENSIONS` leaves
`_ACTIVATED_BUT_ORPHANED` (a **shrink** — C-003); `DISCIPLINED_REFACTORING` + `USE_MUTATION` leave
`_AWAITING_REFERENCES` (they now have incident edges); update `_INTENTIONAL_ORPHANS` / `_SHIPPED_ORPHANS`
and `_ORPHANS_RESOLVED_BY_OVERLAY` accordingly; add the numbered-ledger entry (entry 18) + the shipped-edge-
count prose. Keep the partition identity `sum(len(part)) == len(_INTENTIONAL_ORPHANS)` **total & disjoint**.
In `test_doctrine_regenerate_graph.py`: **ratchet `DOCUMENTED_ORPHAN_RESIDUAL` down** to the new value (no
leftover slack). Compute exact values against the regenerated graph — do not guess.

### Subtask T005 — Reconcile reachability pins (correct per-member accounting — Renata F1)

In `test_reachability.py` (verify each move empirically against the wired graph — do not trust this prose blindly):
- `_PROFILE_UNREACHABLE` (activated-only) shrinks by **2** (Debbie, verified): **`glossary-maintenance-workflow`**
  (the only activated one of the three procedures — `spike-timebox-policy`/`meeting-minutes-pipeline` are NOT
  activated, NOT members) **AND `directive:RECONCILE_CHANGE_SCOPE_TENSIONS`** (activated; edges 2/3 make it
  profile-channel reachable via the `suggests` web). Both are current members of the pinned set; both leave.
- **`glossary-maintenance-workflow` then ENTERS `_PROFILE_RESCUES`** (stays action-d2-unreachable but becomes
  profile-reachable). `RECONCILE` does NOT enter rescues (it leaves both D2 and `_PROFILE_UNREACHABLE`).
  ⚠️ Add `glossary-maintenance-workflow` to the **existing** `## Composition ledger (NFR-002) — profile-channel
  walk-activation` section of the wiring-table doc (the section-scoped matcher at `test_reachability.py:~897`),
  NOT only the new companion-metric section — else the pre-existing `test_every_profile_rescue_member_has_a_
  ledger_row` reds.
- `_ACTION_UNREACHABLE_D1/D2` (activated-only) shrink via the cascaded **activated tactics** (`refactoring-*`,
  `mutation-testing-workflow`) + `RECONCILE` (the only activated directive) — NOT DISC/USE (not activated).
- `_NORMALIZATION_DELTA` does **not** move. Every entering/leaving member (incl. RECONCILE's `_PROFILE_UNREACHABLE`
  departure) needs a wiring-table row (T007).

### Subtask T006 — The companion guard + partition + kind-filter

In `test_reachability.py` add (helper **in the test module** — Renata F7, dead-symbol gate):
- `_ACTION_UNREACHABLE_SHIPPED` (frozenset, ~75), `_DEAD_DOCTRINE_SHIPPED` (~34), `_PROFILE_DELIVERED_SHIPPED`
  (~41), `_BY_DESIGN_UNREACHABLE_KINDS = {mission_step_contract, asset, anti_pattern, template, mission_type,
  glossary_pack}`.
- The guard `test_shipped_graph_action_reachability_is_the_pinned_membership`: compute `measured`
  (action-only, excl by-design kinds + seeds) via canonical helpers at `_ACTION_D2_DEPTH`; assert
  `measured == _ACTION_UNREACHABLE_SHIPPED`; assert the partition (`dead == _DEAD_DOCTRINE_SHIPPED`,
  `profile_delivered == _PROFILE_DELIVERED_SHIPPED`, union==primary, disjoint). Failure reuses the existing
  `_describe` URN differ (name the offending URN).
- A **by-design-kind exclusion test** (Renata F4): assert a known-unreachable `mission_step_contract` node is
  absent from `measured` (proves the filter branch).
See `contracts/reachability-companion-guard.md` for the exact computation. Compute the exact membership
against the regenerated graph.

### Subtask T007 — Mechanical ledger coverage + wiring-table rows

- Add `test_action_unreachable_shipped_members_have_ledger_coverage` (analog to the existing
  `test_every_profile_rescue_member_has_a_ledger_row` at `test_reachability.py:936`): cross-check that every
  URN entering/leaving `_ACTION_UNREACHABLE_SHIPPED` is named (backtick-quoted) in a companion-metric section
  of the wiring-table doc.
- **Anti-null-delta forcing (Debbie Item 1 — REQUIRED):** the coverage test above is *vacuous* if the pin is
  left at the un-wired 88 baseline (empty delta → green without wiring). To make "the edges genuinely exist"
  CI-gated (not resting on self-authored behavioral tests), pin
  `_WIRED_THIS_MISSION` = the **13** URNs this mission makes action-reachable (the 3 directives +
  `refactoring-encapsulate-record/-encapsulate-variable/-extract-first-order-concept/-move-field/-move-method/
  -state-pattern-for-behavior/-strangler-fig` + `mutation-testing-workflow` + `python-mutation-tools` +
  `typescript-mutation-tools` — confirm the exact 13 against the wired graph) and assert **each is action-
  reachable (absent from `_ACTION_UNREACHABLE_SHIPPED`) AND named in a wiring-table row**. This reds if the
  edges are not actually authored.
- Add the composition-ledger rows in `docs/plans/doctrine/delivery-reachability-wiring-table.md` for every
  moved member (both channels). The wiring-table doc is **inventory-tracked** — after editing, run
  `.venv/bin/python scripts/docs/inventory_lockfile.py --write` (Renata F6), which writes
  `docs/development/3-2-page-inventory.yaml` (owned by this WP) so the docs-freshness gate stays green.

### Subtask T008 — Green gates + invariants

- `PWHEADLESS=1 .venv/bin/python -m pytest tests/doctrine/drg/ tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py -q` — green.
- `ruff check src/doctrine/drg/ tests/doctrine/drg/` + `mypy src/doctrine/drg/migration/extractor.py` — zero issues, no new suppressions.
- Verify **C-003**: no node newly enters any residual/defect set (diff the before/after unreachable sets;
  `after − before == ∅` for newly-unreachable).
- Verify regeneration determinism (`--check` byte-identical).

## Branch Strategy

Planning base + merge target: `fix/drg-reachability-metric-wiring`. Execution worktree is allocated per the
computed lane from `lanes.json` (single lane — this WP is the sequential root). Do not switch branches.

## Definition of Done

- [ ] 6 edges authored in `_CURATED_ARTIFACT_EDGES` with traced rationale comments; graph regenerated
      byte-identically; zero new nodes.
- [ ] Behavioral reach assertions green for all 6 targets; delete-edge negative test names the URN.
- [ ] `_ACTION_UNREACHABLE_SHIPPED` (88→~75) + partition (34 dead / 41 profile-delivered) asserted total &
      disjoint; by-design-kind exclusion test present; helper in test module.
- [ ] Every moved pin (incidence + reachability + ceiling) reconciled with correct per-member accounting +
      a wiring-table ledger row; mechanical ledger-coverage test for the new pin present; inventory freshened.
- [ ] All DRG guards + ruff + mypy green; C-003 no-new-orphan verified; determinism verified.

## Reviewer guidance (for the WP reviewer)

- **HARD-REJECT checklist (Debbie Item 1 — the pin-the-baseline laziness path):**
  - `_ACTION_UNREACHABLE_SHIPPED` is pinned at **75, not the un-wired 88** (a green suite at 88 means nothing
    was wired). Confirm the 6 edges are actually present in `_CURATED_ARTIFACT_EDGES` and in the regenerated
    fragments.
  - The behavioral reach tests (T003) are **non-tautological** — each asserts a specific URN `in` the
    canonical-helper result, not a trivially-true expression; the delete-edge negative test genuinely removes
    an edge and asserts the URN is named.
  - `_WIRED_THIS_MISSION` (13 URNs) is present and each is asserted action-reachable + ledger-named.
- Confirm every edge is genuine (cited to artifact text), not metric-gamed — spot-check the 6 rationale
  comments against the actual artifact YAMLs. **Explicitly confirm edge 6a relation is `SUGGESTS`** (larry
  feeds / carla owns — a silent "correction" to `requires` passes every test but is doctrinally wrong).
- Confirm each pin move has a matching wiring-table row (D18 discipline; use the wiring-table as the review
  index — every moved pin ⇒ one row ⇒ one check) — a pin edited without a row is a hard reject even if green.
  Confirm `_PROFILE_UNREACHABLE` shrank by **2** (glossary + RECONCILE) and glossary's row is in the
  **existing** NFR-002 profile-rescue section.
- Confirm the guard uses the canonical helpers (no re-implemented walk) and set-equality (not `<=`).
- Confirm `_ACTIVATED_BUT_ORPHANED` only shrank; no node was added to any residual/defect set (C-003).
- Re-run the behavioral reach + delete-edge tests; confirm the numbers (88→75, 38→34, action d2 153→166).
