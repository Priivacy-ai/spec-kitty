---
work_package_id: WP02
title: 'DRG topology authoring: Family-A when + C4 template + anti-pattern REJECTS'
dependencies:
- WP01
requirement_refs:
- FR-007
- FR-008
- NFR-002
planning_base_branch: feat/doctrine-delivery-activation
merge_target_branch: feat/doctrine-delivery-activation
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-activation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-activation unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
phase: Phase 1 - Companion topology + shared goldens
history:
- at: '2026-07-30T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: src/doctrine/drg/migration/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/migration/hand_authored_overlay.py
- src/doctrine/action.graph.yaml
- src/doctrine/anti_pattern.graph.yaml
- src/doctrine/tactic.graph.yaml
- src/doctrine/drg/models.py
- docs/architecture/doctrine-relationships.md
- tests/doctrine/drg/migration/test_extractor_projection.py
- tests/doctrine/drg/test_unknown_kind_fails_loudly.py
- tests/architectural/test_no_authored_applies_edge.py
- tests/doctrine/test_relation_doc_parity.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – DRG topology authoring: Family-A when + C4 template + anti-pattern REJECTS

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any
user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `curator-carla`
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

WP02 authors the DRG-edge/node topology this mission adds **and owns every cardinality/histogram
golden it moves** — so no other WP has a parallel golden collision (R-M1/D15: WP03's terminal
reconciliation owns ONLY reachability goldens, not node/edge cardinality). Three independent
deliverables, all schema/validation-tier (no core `doctrine/drg/query.py` edit in this WP):

1. **Family-A `when` backfill** (T006) — the three `agent_profile:{architect-alphonso,paula-patterns,
   randy-reducer} → paradigm:domain-driven-design` `suggests` edges currently carry `reason=` only, no
   `when=`. Backfill a grounded `when` derived from each edge's existing `reason` text (D3/R-M6).
2. **C4 template topology completion** (T007) — author a `template:instantiates` edge (or edges) from
   `action:documentation/design` to the C4 mermaid template nodes, completing the canonical topology
   the wiring table's Family C asset assessment records (FR-007/C-005). **This edge is NOT the
   delivery vector** — the templates already deliver to the architect via WP01's suggests-walk
   reaching `tactic:c4-zoom-in-architecture-documentation` (whose own step-level `references:` field
   already mints `requires` edges to the three C4 templates — see grounding below). T007 is topology
   completion only (D13); do not attempt to make the profile channel walk `instantiates` — no
   `query.py`/`reachability.py` edit belongs in this WP.
3. **Refactoring anti-patterns + REJECTS edges** (T008/T009) — author `anti_pattern` nodes for the code
   smells each `refactoring-*` tactic solves and wire `tactic --REJECTS--> anti_pattern` edges (the
   existing canonical relation and direction — matching the 8 shipped REJECTS edges), grounded in each
   tactic's own attested problem/trigger text. `anti_pattern`s are deliberately NEVER delivered/
   activated (validation-tier only, D14) — the deliverable is the completed REJECTS topology + a green
   anti-pattern validator, not context delivery.
4. **All shared cardinality/histogram goldens this WP's own edits move** (T010): `_EXPECTED_NODE_COUNT`
   / `_EXPECTED_EDGE_COUNT` in both `tests/doctrine/drg/migration/test_extractor_projection.py` and
   `tests/doctrine/drg/test_unknown_kind_fails_loudly.py`, `HAND_AUTHORED_EDGES`/`HAND_AUTHORED_NODES`
   length deltas, the `Relation.INSTANTIATES` count claim in `RELATION_DESCRIPTIONS`
   (`src/doctrine/drg/models.py`) mirrored **verbatim** in `docs/architecture/doctrine-relationships.md`
   (parity enforced by `tests/doctrine/test_relation_doc_parity.py`), and
   `tests/architectural/test_no_authored_applies_edge.py::TestPositiveCountClaimsAreTrue` — each with a
   composition-ledger entry (NFR-002, no silent golden movement).
5. **ATDD** (T011) proving: templates reach the architect via the delivered C4 tactic's references
   (depends on WP01), and each anti_pattern is a REJECTS-target with the anti-pattern validator green.

## Context & Constraints

- **Governing docs**: `.kittify/charter/charter.md`; mission `plan.md` (IC-03, IC-04), `tasks.md` (WP02
  row), `pre-planning-ledger.md` (D3, D13, D14, D15, R-M1, R-M5, R-M6 — grounding facts below
  independently re-verified against live code on 2026-07-30). Coordinate with issue **#2847**
  (promotes the inline anti-pattern corpus to first-class DRG nodes) — this WP **extends** the
  existing 6-node `anti_pattern.graph.yaml` corpus; do not introduce a competing shape #2847 would then
  have to migrate.
- **Dependency**: WP01 must land first for T011's C4-delivery ATDD (the tactic's profile-reachability is
  WP01's `suggests` walk); T006/T008/T009/T010's own topology-authoring work has no hard code
  dependency on WP01 and can start in parallel, but the **golden numbers T010 pins may need a rebase**
  if WP01's own Family-A `when` assertions land first and touch the same edge literals — coordinate via
  the Activity Log / a quick rebase before finalizing T010's numbers.

### T006 grounding — Family-A `when` backfill

- Location: `src/doctrine/drg/migration/hand_authored_overlay.py:534-564` (verified live). Three
  `DRGEdge` literals, `relation=Relation.SUGGESTS`, each with a `reason=` block but **no `when=`
  keyword argument** today:
  - `agent_profile:architect-alphonso → paradigm:domain-driven-design` — reason: "When designing and
    reviewing significant code changes, the architect should reach Domain-Driven Design."
  - `agent_profile:paula-patterns → paradigm:domain-driven-design` — reason: "When investigating or
    inspecting code, the pattern scout should reach Domain-Driven Design."
  - `agent_profile:randy-reducer → paradigm:domain-driven-design` — reason: "When investigating or
    inspecting code, the reducer should reach Domain-Driven Design."
- Add a `when=` argument to each, derived from (not copy-pasted verbatim from) the existing `reason`
  text — the `when` is the applicability *trigger* ("when designing and reviewing significant code
  changes" / "when investigating or inspecting code"), distinct from the `reason` (*why* the edge
  exists, which stays as-is). Compare the shape of Family B/C edges in the same file
  (`hand_authored_overlay.py:622-717`, `:878-1017`) which already carry both `when=` and `reason=` —
  match that convention exactly (short, imperative, lower-case "when ..." phrase for `when`; full
  sentence(s) for `reason`).
- This is a **content-only** edit inside existing `DRGEdge(...)` literals — it does NOT change node or
  edge cardinality (no `_EXPECTED_NODE_COUNT`/`_EXPECTED_EDGE_COUNT` delta), so it needs no ledger entry
  for those counts. It DOES NOT move the relation histogram either (still 3 `suggests` edges, unchanged
  count). No T010 golden work is needed for T006 itself — confirm this empirically (run the golden
  tests before/after and confirm they don't move) rather than assuming.

### T007 grounding — C4 `template:instantiates` topology

- The three C4 mermaid template DRG nodes already exist and are **not** mission-qualified:
  `template:c4-context-mermaid-template`, `template:c4-container-mermaid-template`,
  `template:c4-component-mermaid-template` (`src/doctrine/template.graph.yaml:11-15`, verified live),
  backed by files under `src/doctrine/templates/architecture/`.
- `tactic:c4-zoom-in-architecture-documentation`
  (`src/doctrine/tactics/built-in/architecture/c4-zoom-in-architecture-documentation.tactic.yaml`)
  already carries per-step `references:` blocks naming all three templates (`type: template, id:
  c4-context-mermaid-template, when: "Starting a new system context diagram from scratch."` and
  similarly for container/component) — **verified**: the extractor mints one `Relation.REQUIRES` edge
  per step-level reference by default (`src/doctrine/drg/migration/extractor.py:1022,1040` — "one
  `Relation.REQUIRES` edge per step to the matching..."), so `tactic:c4-zoom-in-architecture-
  documentation --requires--> template:c4-*-mermaid-template` edges **already exist today**,
  independent of this WP. This is the concrete mechanism behind D13: once WP01's suggests-walk makes
  the tactic itself profile-reachable (via the two-hop chain `agent_profile:architect-alphonso
  --suggests--> directive:USE_C4_MODEL_TECHNIQUES --suggests--> tactic:c4-zoom-in-architecture-
  documentation`, both edges already authored with `when=` in Family C,
  `hand_authored_overlay.py:878-1017`), the profile channel's unbounded walk (`max_depth=None`)
  continues over the tactic's own `requires` edges to the templates — no new code path needed for
  delivery itself.
- **Your job in T007 is narrower**: author the `action:documentation/design → template:c4-*-mermaid-
  template` `instantiates` edge(s) that the wiring table's Family C asset assessment names as the
  canonical topology path (parallel to the existing `action:documentation/design --instantiates-->
  template:documentation/documentation-plan-template.md` edge visible in `src/doctrine/action.graph.yaml`
  around the `documentation/design` block). **Before writing the edge, trace how that existing
  precedent edge was minted** — it is NOT in `hand_authored_overlay.py` (verified: no match for
  `documentation-plan-template` there) and is therefore extractor-derived, via
  `doctrine.missions.step_projection.iter_template_refs` (`src/doctrine/missions/step_projection.py:124`,
  consumed by `extractor.py:1049-1103 "Emit template:<mission>/<file> nodes + action --instantiates-->
  template edges"`). That mechanism mints **mission-qualified** template nodes/edges from a
  `MissionStep.template`-shaped field — check whether it is a fit for the pre-existing, non-mission-
  qualified C4 template nodes, or whether it only applies to templates scoped to one mission's own step
  contract. If it is **not** a natural fit (most likely, since the C4 templates are shared/general-
  purpose, not one mission's own step-output template), author the new `instantiates` edge(s) directly
  in `hand_authored_overlay.py`'s `HAND_AUTHORED_EDGES` tuple instead — that module's own docstring
  states its purpose is exactly content "the extractor has no frontmatter mechanism to mint"
  (`hand_authored_overlay.py:1-40`). Whichever path you choose, **document the choice and why** in a
  code comment beside the new edge(s), so a future regeneration/freshness run doesn't silently drop it.
- Decide whether to author one edge per template (3 edges, matching the existing one-edge-per-template
  convention for `documentation-plan-template.md`) or a single edge if the schema supports multi-target
  — the existing precedent is one-edge-per-target, follow it (3 new `instantiates` edges).

### T008/T009 grounding — anti-pattern nodes + `REJECTS` edges

- **Canonical relation confirmed**: `Relation.REJECTS`, direction **source (good artefact) → target
  (anti_pattern)** — `src/doctrine/drg/models.py` docstring: *"REJECTS is directional, from a good
  artefact to a marked anti-pattern"*. The 8 shipped REJECTS edges today are all sourced from
  **paradigm** nodes (`hand_authored_overlay.py:152-232`, e.g. `paradigm:domain-driven-design -->
  anti_pattern:anemic-domain-model`), not tactics — but the validator does **not** constrain source
  kind: `_validate_rejects_targets` (`src/doctrine/drg/validator.py:113-`) only requires the **target**
  resolve to `NodeKind.ANTI_PATTERN`; `_validate_anti_pattern_nodes_are_rejected`
  (`validator.py:` — the reverse-mirror check) only requires every `anti_pattern` node have >=1 inbound
  `rejects` edge from **any** source kind. So `tactic --REJECTS--> anti_pattern` (this mission's FR-008
  shape) is structurally valid and consistent with the existing corpus — you are extending the
  *source-kind* variety, not inventing a new relation or direction.
- **Existing anti_pattern corpus** (6 nodes, extend — do not replace): `anemic-domain-model`,
  `big-ball-of-mud`, `big-upfront-design`, `code-is-the-documentation`, `database-driven-design`,
  `single-diagram-architecture` — defined in **two places that must stay mirrored**:
  `src/doctrine/anti_pattern.graph.yaml` (the shipped fragment, `urn`/`kind`/`label`/`tags` shape) AND
  `HAND_AUTHORED_NODES` in `hand_authored_overlay.py:58-` (the Python-literal source of truth used by
  the freshness/regeneration comparison). **New anti_pattern nodes go in BOTH files**, same shape,
  same URN.
- **Grounding constraint (C-004, no invention)**: each new `anti_pattern` must be traceable to an
  attested `problem`/trigger text on the tactic that rejects it. Checked live:
  `src/doctrine/tactics/built-in/refactoring/refactoring-inline-temp.tactic.yaml` (and the sibling
  refactoring tactic files under that directory) carry **only** `purpose`/`steps`/`failure_modes`-style
  frontmatter — **no dedicated `problem`/`when` field on the tactic itself**. The actual attested
  trigger text for a smell lives on the **Family-B `suggests` edge** from `directive:
  DISCIPLINED_REFACTORING` (`hand_authored_overlay.py:622-717`), which today covers exactly **7** of
  the tactic module's **18** `refactoring-*` tactics (`src/doctrine/tactic.graph.yaml:224-275` lists
  all 18 URNs): `refactoring-encapsulate-record`, `refactoring-encapsulate-variable`,
  `refactoring-extract-first-order-concept`, `refactoring-move-field`, `refactoring-move-method`,
  `refactoring-state-pattern-for-behavior`, `refactoring-strangler-fig`. Each of those 7 already has an
  authored `when=` describing the exact smell (e.g. `refactoring-move-method`'s `when` is the "feature
  envy" description). **Treat these 7 as the grounded, author-now set.** The other 11 refactoring
  tactics (`change-function-declaration`, `combine-functions-into-transform`, `conditional-to-strategy`,
  `consolidate-conditional-expression`, `extract-class-by-responsibility-split`,
  `guard-clauses-before-polymorphism`, `inline-temp`, `introduce-null-object`,
  `replace-magic-number-with-symbolic-constant`, `replace-temp-with-query`, `retry-pattern`) have **no
  attested problem/when text anywhere in the shipped tree today** — per C-004, DEFER these (do not
  invent a smell description for them); record the deferral as an explicit note (in the Activity Log
  and, if there's a natural home, in a code comment near the new REJECTS edges) rather than silently
  omitting them. If, during implementation, you find attested text for some of the 11 that this
  grounding missed (e.g. in `failure_modes:` or `notes:` fields), you may include them — the bar is
  "traceable to attested text", not "exactly these 7".
- **Steps**:
  1. For each of the 7 grounded refactoring tactics, derive an `anti_pattern` node (urn, label, tags)
     naming the smell from that tactic's own Family-B `when` text (e.g.
     `anti_pattern:feature-envy` for `refactoring-move-method`,
     `anti_pattern:unencapsulated-record` for `refactoring-encapsulate-record`, etc. — pick clear,
     conventional smell names; check Fowler's refactoring catalog naming if you want an
     industry-standard label, but ground the description in the tactic's own `when` text, not an
     external source).
  2. Add each new node to BOTH `src/doctrine/anti_pattern.graph.yaml` and `HAND_AUTHORED_NODES`
     (`hand_authored_overlay.py`), same urn/kind/label/tags shape as the existing 6.
  3. Add one `tactic:refactoring-* --REJECTS--> anti_pattern:<new>` edge per pair to
     `HAND_AUTHORED_EDGES` (`hand_authored_overlay.py`), with a `reason=` grounded in the tactic's
     `when` text (mirroring the existing 8 REJECTS edges' `reason=` style — see
     `hand_authored_overlay.py:145-232`).
  4. Run `spec-kitty doctrine validate` (or the equivalent pytest wrapper — check
     `src/specify_cli/doctrine/pack_validator.py` for the CLI entry, or run the validator directly via
     `doctrine.drg.validator.validate_graph`) and confirm zero "Orphaned anti_pattern node" /
     "Rejects-edge target must be an anti_pattern node" errors for the new nodes/edges.

### T010 grounding — shared cardinality/histogram goldens

- **Two node/edge-count files, BOTH must move together** (verified live, current values before this
  WP): `tests/doctrine/drg/migration/test_extractor_projection.py:392-393` `_EXPECTED_NODE_COUNT = 311`,
  `_EXPECTED_EDGE_COUNT = 764` (the **pure extractor** count, before the hand-authored overlay is
  merged); `tests/doctrine/drg/test_unknown_kind_fails_loudly.py:105-106` `_EXPECTED_NODE_COUNT = 317`,
  `_EXPECTED_EDGE_COUNT = 882` (the **overlay-merged shipped graph** count — 317 = 311 + 6 anti_pattern
  nodes at the time this was last pinned; 882 = 764 + `len(HAND_AUTHORED_EDGES)` at that time). Compute
  your deltas precisely: T007 adds edges only (no new nodes, both C4 template nodes already exist) —
  moves `_EXPECTED_EDGE_COUNT` (both files) by however many `instantiates` edges you authored, and (if
  authored via `hand_authored_overlay.py`) `len(HAND_AUTHORED_EDGES)` by the same amount. T008/T009 adds
  N anti_pattern nodes + N REJECTS edges — moves `_EXPECTED_NODE_COUNT` (both files) by N, and
  `_EXPECTED_EDGE_COUNT` (both files) by N, and `len(HAND_AUTHORED_EDGES)` by N (REJECTS edges) —
  `HAND_AUTHORED_NODES` grows by N too (verify via `test_extractor_projection.py`'s own assertions,
  e.g. `_EXPECTED_NODE_COUNT + len(HAND_AUTHORED_EDGES)` style checks around line 784-787 — read the
  exact assertion shape before editing, do not guess).
  **Do not hand-compute these numbers from memory** — run the relevant test, read the actual failure
  diff (it names the measured vs claimed count), and set the golden to the measured value; then explain
  the delta in a ledger comment, following the numbered-entry convention already used above
  `_EXPECTED_NODE_COUNT`/`_EXPECTED_EDGE_COUNT` in `test_extractor_projection.py` (look at entries "(12)"
  and "(13)" immediately above the current constants for the exact prose format/level of detail
  expected — author your entry as the next number in that sequence, e.g. "(14)").
- **Relation histogram** (`RELATION_DESCRIPTIONS` in `src/doctrine/drg/models.py`): only
  `Relation.INSTANTIATES`'s description carries a literal count claim today — *"Emitted 8 times in the
  built-in graph, exclusively from `action` nodes to `template` nodes"*
  (`models.py:215-223`) — update the "8" to the new measured count if T007 lands its edges. `Relation.
  REJECTS`'s description carries **no** count claim (verified:
  `tests/architectural/test_no_authored_applies_edge.py:589` explicitly notes *"rejects 8"* is real but
  **unstated** in the registry text) — you do NOT need to add one, and adding one is optional, not
  required (if you do add one, it must then stay accurate under
  `TestPositiveCountClaimsAreTrue`, so only add it if you're prepared to maintain it — recommend leaving
  it unstated, consistent with the existing convention).
  Whichever description(s) you touch, the change must be **mirrored verbatim** in
  `docs/architecture/doctrine-relationships.md` (the "Instantiation — `instantiates`" section at
  approximately line 95-97, and/or the "Rejection — `rejects`" section around line 121-123) —
  `tests/doctrine/test_relation_doc_parity.py` enforces byte-for-byte content parity between the two.
- **`tests/architectural/test_no_authored_applies_edge.py::TestPositiveCountClaimsAreTrue`**
  (`:558-` verified live) — parses every relation description for a stated count and compares against
  `measured_edge_counts(shipped_graph)`. Run
  `test_every_positive_count_matches_the_measured_graph` after your edits; if it reds, the failure
  message names exactly which relation's claimed vs measured count mismatched — fix the registry text
  to match measured, not the other way around.

## Branch Strategy

- **Strategy**: Planning artifacts generated on feat/doctrine-delivery-activation; during implement
  this WP may branch from a dependency-specific base but merges back into
  feat/doctrine-delivery-activation unless the human redirects.
- **Planning base branch**: feat/doctrine-delivery-activation
- **Merge target branch**: feat/doctrine-delivery-activation

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T006 – Family-A `when` backfill

- **Purpose**: Give the architect/paula/randy → DDD `suggests` edges an authored applicability
  condition instead of falling back to `STATED_DEFAULT_WHEN` on every delivery (D3/R-M6) — makes WP01's
  A1 acceptance assert a real, meaningful `when` rather than the generic default.
- **Steps**: See "T006 grounding" above for exact anchors. Add `when=` to the three `DRGEdge` literals
  at `hand_authored_overlay.py:534-564`, derived from each edge's own `reason` text, matching Family
  B/C's `when=`/`reason=` shape convention.
- **Files**: `src/doctrine/drg/migration/hand_authored_overlay.py`.
- **Parallel?**: Fully parallel with T007/T008/T009 (different edges, same file — merge/rebase
  trivially if two people touch this file concurrently, but this WP is one implementer so sequence as
  convenient).
- **Notes**: Do not change the `reason=` text. Do not touch the fourth Family-C edge
  (`directive:USE_C4_MODEL_TECHNIQUES → paradigm:domain-driven-design`, which already has a `when=`) —
  T006 is scoped to exactly the three profile-sourced Family-A edges.

### Subtask T007 – Author C4 `template:instantiates` edge(s)

- **Purpose**: Complete the DRG topology recording that `action:documentation/design` instantiates the
  C4 mermaid templates (the wiring table's canonical Family-C path), matching the existing
  `documentation-plan-template.md` precedent. This is topology completion, not the delivery mechanism
  (see grounding above — delivery already rides the tactic's pre-existing `requires` edges once WP01
  lands).
- **Steps**: See "T007 grounding" above. First trace how the existing `documentation-plan-template.md`
  instantiates edge was minted (`iter_template_refs`/`step_projection.py:124`,
  `extractor.py:1049-1103`) and decide whether that mechanism naturally extends to the C4 templates
  (unlikely, since they're not mission-qualified) or whether a direct `HAND_AUTHORED_EDGES` entry is the
  right home (more likely, per that module's stated scope). Author 3 new `instantiates` edges (one per
  C4 template), `source=action:documentation/design`.
- **Files**: `src/doctrine/action.graph.yaml` (if extractor-derivable via a step-contract change — check
  which mission step contract file that would be) or `src/doctrine/drg/migration/
  hand_authored_overlay.py` (if hand-authored, the more likely path).
- **Parallel?**: Parallel with T006/T008/T009.
- **Notes**: Do NOT re-home the C4 templates as `asset` kind nodes (C-005 explicitly forbids this — the
  wiring table's Family C assessment already ruled the template path canonical). Do NOT add any
  `query.py`/`reachability.py` change to make `instantiates` walked by any channel — that is explicitly
  out of this WP's scope per D13 ("IC-03 stays schema-tier; NO core query.py edit").

### Subtask T008 – Author `anti_pattern` nodes for refactoring-* smells

- **Purpose**: Name the code smells the 7 grounded `refactoring-*` tactics solve, as first-class
  `anti_pattern` DRG nodes, extending (not replacing) the existing 6-node corpus (FR-008, C-004).
- **Steps**: See "T008/T009 grounding" above, steps 1-2. For each of the 7 grounded tactics, derive one
  new `anti_pattern` node from its Family-B `when` text; add it to both
  `src/doctrine/anti_pattern.graph.yaml` and `HAND_AUTHORED_NODES`
  (`hand_authored_overlay.py`).
- **Files**: `src/doctrine/anti_pattern.graph.yaml`, `src/doctrine/drg/migration/
  hand_authored_overlay.py`.
- **Parallel?**: Sequenced before T009 (T009's REJECTS edges target these nodes) but both can be
  authored in the same pass/commit.
- **Notes**: Explicitly record (Activity Log + a code comment near the new nodes) which of the 11
  ungrounded refactoring tactics you deferred and why (no attested problem/when text found) — this is
  the C-004 discipline the review gate will check for.

### Subtask T009 – Author `tactic --REJECTS--> anti_pattern` edges + validator check

- **Purpose**: Wire each new anti_pattern to the refactoring tactic that rejects it, and confirm the
  anti-pattern validator (`_validate_rejects_targets` / `_validate_anti_pattern_nodes_are_rejected`,
  `src/doctrine/drg/validator.py`) is green for the extended corpus.
- **Steps**: See "T008/T009 grounding" above, steps 3-4. Add one `REJECTS` edge per new anti_pattern to
  `HAND_AUTHORED_EDGES`, `reason=` grounded in the source tactic's `when` text. Run the validator (or
  its pytest wrapper) and confirm zero orphan/target-kind errors for both the new and the pre-existing
  6-node corpus (regression check).
- **Files**: `src/doctrine/drg/migration/hand_authored_overlay.py`.
- **Parallel?**: Depends on T008 (same commit is fine).
- **Notes**: Coordinate with #2847 — do not restructure the existing 6-node corpus's shape while
  extending it; if #2847's promotion work is in flight on another branch, flag a potential merge
  conflict in the Activity Log rather than silently reshaping shared files.

### Subtask T010 – Update cardinality/histogram goldens + composition-ledger entries

- **Purpose**: Every count this WP's edits move gets a matching golden update **and** a ledger entry —
  NFR-002's "no silent golden movement" bar, owned entirely by this WP for the counts it authored
  (R-M1/D15 — WP03 does NOT own these).
- **Steps**: See "T010 grounding" above in full. In order:
  1. Run `uv run pytest tests/doctrine/drg/migration/test_extractor_projection.py -q` and
     `uv run pytest tests/doctrine/drg/test_unknown_kind_fails_loudly.py -q` — read the actual failure
     diffs (measured vs claimed) rather than hand-computing deltas.
  2. Update `_EXPECTED_NODE_COUNT`/`_EXPECTED_EDGE_COUNT` in both files to the measured values.
  3. Author a new numbered composition-ledger comment entry directly above
     `test_extractor_projection.py`'s `_EXPECTED_NODE_COUNT`/`_EXPECTED_EDGE_COUNT` constants, following
     the exact prose format of the immediately-preceding numbered entries (they name exactly which
     edges/nodes moved the count and by how much, and cross-reference the wiring-table doc) — this is
     the ledger row NFR-002 requires.
  4. Run `uv run pytest tests/architectural/test_no_authored_applies_edge.py -q` and fix any
     `RELATION_DESCRIPTIONS` count-claim mismatch it reports (only `instantiates` should need a text
     change, per the grounding above).
  5. Mirror any `RELATION_DESCRIPTIONS` text change verbatim into
     `docs/architecture/doctrine-relationships.md`'s matching section, then run
     `uv run pytest tests/doctrine/test_relation_doc_parity.py -q` to confirm byte-for-byte parity.
  6. Re-run the full targeted suite (see Test Strategy) once all four golden surfaces agree.
- **Files**: `tests/doctrine/drg/migration/test_extractor_projection.py`,
  `tests/doctrine/drg/test_unknown_kind_fails_loudly.py`, `src/doctrine/drg/models.py`,
  `docs/architecture/doctrine-relationships.md`.
- **Parallel?**: Sequenced last, after T006/T007/T008/T009 are content-final (golden numbers depend on
  the final edge/node set).
- **Notes**: If a number surprises you (moves more or less than your hand-count predicted), trust the
  test's measured value and investigate the discrepancy before overriding it — a wrong golden that
  "just passes" is exactly the false-green NFR-002 exists to prevent.

### Subtask T011 – ATDD: C4 delivery via tactic references + REJECTS validator green

- **Purpose**: Prove both companion deliverables actually work, on the correct tier for each (delivery-
  tier for templates, validation-tier for anti-patterns — D13/D14).
- **Steps**:
  1. **C4 template delivery** (depends on WP01 landing): assert
     `profile_channel_reachable(graph, {"agent_profile:architect-alphonso"})` includes all three
     `template:c4-*-mermaid-template` URNs (via the tactic's pre-existing `requires` edges, once the
     tactic itself is suggests-reachable). If WP01 has not yet landed on your base when you write this
     test, write it against the **post-WP01** expectation and mark it `xfail`/skip with a clear reason
     until WP01 merges, rather than weakening the assertion.
  2. Assert the `action:documentation/design --instantiates--> template:c4-*-mermaid-template` edges
     exist in the merged graph (a direct `edges_from`/`edges_to` check — this part has no WP01
     dependency, it's pure topology you authored in T007).
  3. **Anti-pattern REJECTS validation**: for each new anti_pattern node, assert
     `graph.edges_to(urn, relation=Relation.REJECTS)` is non-empty (mirrors
     `_validate_anti_pattern_nodes_are_rejected`'s own check) and that the validator function itself
     (call it directly, or via the `doctrine validate` CLI path) reports zero errors for the extended
     corpus.
  4. Assert the anti_pattern nodes are NOT profile-channel-reachable and NOT action-channel-reachable
     (they must stay validation-tier only, never delivered — a regression here would silently violate
     D14/C-004's non-activatable-kind guarantee).
- **Files**: a new or existing doctrine test module — check whether
  `tests/doctrine/drg/migration/test_extractor_projection.py` or a fresh
  `tests/doctrine/drg/test_c4_and_anti_pattern_topology.py` is the better home (prefer a new focused
  file if the existing ones are already large, consistent with the mission's own test-file-per-concern
  pattern visible in `tests/doctrine/drg/`).
- **Parallel?**: The anti-pattern half (steps 3-4) has no WP01 dependency and can be written/run first;
  the C4 delivery half (steps 1-2, step 2 only) should be finalized once WP01 is available to test
  against for real (not just topology).
- **Notes**: Do not assert C4 template delivery via `resolve_context` (D10 applies mission-wide, not
  just to WP01) — use `profile_channel_reachable` + the render path, same as WP01's ATDD.

## Test Strategy

- **Framework**: pytest, `uv run pytest <nodeid>` — targeted node-ids only, never the full
  `tests/architectural/` suite locally.
- **Exact commands**:
  ```bash
  uv run pytest tests/doctrine/drg/migration/test_extractor_projection.py -q
  uv run pytest tests/doctrine/drg/test_unknown_kind_fails_loudly.py -q
  uv run pytest tests/architectural/test_no_authored_applies_edge.py -q
  uv run pytest tests/doctrine/test_relation_doc_parity.py -q
  uv run pytest tests/doctrine/drg/test_c4_and_anti_pattern_topology.py -q   # or wherever T011 lands
  uv run pytest tests/doctrine/drg/ -k "validator or anti_pattern" -q
  ```
- **Validator check**: run `doctrine.drg.validator.validate_graph` (or `spec-kitty doctrine validate`
  against the built-in pack) and confirm zero new errors/warnings for the extended anti_pattern corpus.
- **Lint/type**: `ruff check src/doctrine/drg/migration/hand_authored_overlay.py src/doctrine/drg/models.py`
  and `mypy --strict` over the same — zero new issues (NFR-005). YAML fragments
  (`anti_pattern.graph.yaml`, `action.graph.yaml`, `tactic.graph.yaml`) are not ruff/mypy targets but
  must stay schema-valid — the validator run above covers that.

## Risks & Mitigations

- **Inventing a smell for an ungrounded refactoring tactic** (C-004 violation) — mitigate by strictly
  limiting T008/T009 to the 7 grounded tactics unless you find new attested text; document every
  deferral explicitly rather than silently skipping.
- **Golden-number collision with a parallel WP** — mitigated structurally: this WP owns ALL the
  cardinality/histogram goldens its own edits move (R-M1/D15); WP03 only touches reachability-pin
  goldens. If a test you don't expect to move also reds, stop and investigate before editing it —
  you may have found a real cross-WP collision worth flagging to the mission owner.
- **`hand_authored_overlay.py` vs extractor-derivable mechanism for T007** — picking the wrong home
  risks a future `spec-kitty doctrine regenerate-graph --check` false-staleness report or a silently
  dropped edge on regeneration. Mitigate by tracing the precedent edge's actual mechanism before
  choosing (grounding above gives the exact functions to read) and documenting the choice inline.
- **#2847 collision** — extending the anti_pattern corpus while #2847's promotion work might also be
  touching `anti_pattern.graph.yaml`/`HAND_AUTHORED_NODES` — check for an open branch/PR before
  starting T008 and flag any overlap.
- **T010 sequencing** — updating goldens before T006-T009 are content-final produces numbers that go
  stale again immediately; do T010 last, and re-run the full check list after any late edit to
  T006-T009.

## Review Guidance

- Confirm every new `anti_pattern` node traces to a specific, quoted attested `when`/`reason` string on
  its rejecting tactic — reject any node whose grounding is "seems like a reasonable smell" without a
  cited source.
- Confirm the 11 ungrounded refactoring tactics are explicitly listed as deferred (Activity Log or code
  comment), not silently absent.
- Confirm `HAND_AUTHORED_NODES` and `anti_pattern.graph.yaml` stay mirrored (same URNs, same count) —
  a drift here is exactly the kind of split-brain this mission's own hygiene items (WP06/#3062) exist
  to prevent elsewhere; don't reintroduce the pattern here.
- Confirm every golden number change in T010 has a matching, specific composition-ledger comment (not
  a generic "updated counts" note) — verify the numbers in the comment match the actual diff.
- Confirm T011's C4-delivery assertion actually depends on WP01 (i.e., would fail if WP01's SUGGESTS
  addition were reverted) — a delivery test that passes even without WP01 is testing the wrong thing
  (it would mean the templates were already reachable some other way, undermining the D13 narrative).
- Confirm no `query.py`/`reachability.py` edits landed in this WP's diff — that boundary (schema-tier
  only) is load-bearing for the plan's Charter Check.

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
