---
title: "Post-spec squad findings and corrections to the discovery research"
description: "Four profile-loaded adversarial lenses on the draft spec: eleven blockers, the reproduction ledger, and the corrections that reshaped FR-012, US1's priority, and every headline count."
doc_status: active
updated: '2026-07-28'
related:
- kitty-specs/doctrine-delivery-reachability-01KYMXD6/spec.md
- kitty-specs/doctrine-delivery-reachability-01KYMXD6/research/activation-reachability-findings.md
- kitty-specs/doctrine-delivery-reachability-01KYMXD6/research/drg-writer-and-reachability-inventory.md
---
# Post-Spec Squad — Findings and Corrections

**Point-cut.** Post-`/spec-kitty.specify`, 2026-07-28, per the standing brownfield squad cadence.
Four profile-loaded lenses (`architect-alphonso`, `reviewer-renata`, `doctrine-daphne`,
`debugger-debbie`), read-only, each required to ground claims in code rather than in the discovery
prose. Measured on `feat/doctrine-delivery-reachability` @ `da6710aa8`; `git diff ed470756e HEAD -- src/`
is empty, so all findings hold for the base tree.

**Sharp question:** *does this spec commit us to work that is correctly scoped, coherent as one
mission, and buildable — or does it contain a requirement that cannot be satisfied as written, a
deferred item that is actually a prerequisite, or an acceptance criterion that can be faked?*

Answer: **all three were present.** Eleven blockers. The spec was revised before planning.

---

## 1. The finding that changed the mission

**D5 is refuted. The original FR-012 targeted the one call site that already works.**

The discovery research claimed `src/runtime/next/prompt_builder.py` calls `build_charter_context`
with no `feature_dir` and no `mission_type`, calling it *"the path agents actually take"* and *"the
most consequential single defect in the set"*.

`build_prompt` declares `feature_dir: Path` as **required**, and both call sites pass it.
`_governance_context` has no other caller in the tree. `build_with_scope` forwards the grain, which
resolves correctly (`resolve_mission_type_key(None, feature_dir) -> 'software-dev'`).

Measured on a fresh project through the real entry point:

```
first-load, feature_dir=YES: len=31556 surfaced=80
  SECOND load (steady state): len=6066  surfaced=0
first-load, feature_dir=NO:  len=5843  surfaced=9
  SECOND load (steady state): len=6069 surfaced=0
```

The payload is **not empty** on the runtime path. The harm is real but its cause is **bootstrap
exhaustion**, not a missing grain.

**Two callers do exhibit the D5 symptom and were named nowhere:**
`src/specify_cli/cli/commands/agent/workflow.py:738` and
`src/specify_cli/cli/commands/agent/workflow_executor.py:459`.

Left unrevised, FR-012 would have landed green and inert — the mission's own defect class.

## 2. A sixth delivery defect, previously unnamed

The action bundle **resolves** 5 styleguides and 3 toolguides; the renderer emits **zero**:

```
WITH pack_context: directive_ids=16 tactic_ids=53 styleguide_ids=5 toolguide_ids=3
  styleguides: 0 of 12 appear as literal ids -> []
  toolguides:  0 of 11 appear as literal ids -> []
  paradigms:   8 of 8 appear — but ONLY inside Reference Docs (dead _LIBRARY links)
```

The `Guidelines:` block is hand-authored mission-step prose, not the resolved styleguides. Fixing
`resolver.py`'s four `[]` literals will **not** surface them — the drop is one layer lower, in
`_render_bootstrap_text`.

Consequence: honest delivered content on the single first-load render is **69** (16 directives + 53
tactics), not the 78 the research reported. The research's `procedures: 2` were **prose substring
false positives** (`PROCEDURE:` tokens in the render: `[]`), which also made the research internally
inconsistent — §1 reported 2 procedures while §2's table reported 0 of 18.

## 3. US1's internal priority is inverted

`rewrite_opposed_by` (#2977) is **already guarded**:
`tests/doctrine/drg/test_model_strictness_roundtrip.py:520` and `:557` assert
`set(_edge_to_dict(edge)) == set(DRGEdge.model_fields) - _FIELDS_WITHHELD_FROM_GRAPH_OUTPUT`. They
are green today and go red the moment B1 adds `impacts`/`is_symmetric`.

`project_drg._serialize_graph` is guarded by **nothing**, proven by mutation:

```
### M2: project_drg._serialize_graph drops edge 'reason' ###
  tests/charter/synthesizer/test_project_drg.py   23 passed
  BASELINE                                        23 passed
```

`grep -n "tags|provenance|model_fields" tests/charter/synthesizer/test_project_drg.py` → no matches.

**FR-002 leads FR-001.**

## 4. There are four write sites, not three

The canonical helper's own docstring (`extractor.py:1356-1368`) enumerates them and names one the
draft spec dropped:

> *"`_dump_graph_document` below, for the five document-level keys; `DRGGraph` also declares no
> `model_config`, so unknown top-level keys are accepted and discarded rather than rejected […]
> Anyone adding a model field should check all four sites, not just this one."*

Confirmed: `DRGGraph` (`models.py:390`) declares no `ConfigDict`; `DRGNode:330` and `DRGEdge:366` both
carry `extra="forbid"`. A fifth drop point exists at a **bridge** rather than a writer —
`_bridge_org_edge_to_drg_edge` (`merge.py:848-878`) constructs a three-field `DRGEdge`, so org-tier
fields are lost before any writer runs.

This is why FR-001 became "derived writer set, not an enumerated one": a three-row table is exactly
the scoping failure #2977 itself warns about.

## 5. Fakeable acceptance — six of nine original criteria

| Criterion | Lazy implementation that closes it green |
|---|---|
| SC-005 (original: "the count decreases") | **Normalize an identifier.** The store holds `025-boy-scout-rule`; the DRG holds `directive:DIRECTIVE_025`. Counting unmatched ids as unreachable gives 54+25 = **79**; normalizing gives **59** — a 20-unit swing with zero reachability change. Also falls to wiring one edge, or to deactivating the artefacts. |
| FR-015 (original) | Declare PR #3007's already-landed four to be "the obvious ones"; route the rest to C-007. Green acceptance on landed work, zero new reachability. |
| FR-009 / FR-011 (original) | Add an always-empty `procedure_ids` field and remove the four `[]` literals, feeding them nothing. A declaration that reaches nobody, inside the mission about declarations that reach nobody. |
| SC-006 (original) | Filter the reference list to pointers that resolve. Today that is zero, so the block renders the missing-references message and the criterion passes vacuously. |
| SC-003 (original) | Verified in-repo, where `resolve_doctrine_root()`'s dev-layout fallback means it cannot fail. |
| SC-007 (original) | A migration that does nothing satisfies "no change beyond the pointer migration". |

All six were rewritten. SC-005 became a named set with a declared normalization; FR-015 became an
enumerated table; FR-009/FR-011 acquired non-empty-delivery acceptance; SC-006 gained a non-vacuity
floor; SC-003 pinned to a wheel in a clean environment; SC-007 gained a positive postcondition and a
divergent-mirror fixture.

## 6. Corrections to the discovery research

| # | Prior claim | Correct value |
|---|---|---|
| 1 | 185 activated | **184** — `toolguide:rtk-search-tooling` was deleted by PR #3007 along with its activation entry; toolguides are 11, not 12. True at `ed470756e` too, so 185 was never true on the stated measurement commit. |
| 2 | 91 activated-and-action-unreachable | **88** (union of the action-doctrine walk across every mission type × action, strict id match) |
| 3 | 78 surfaced on first load | **69** delivered as usable content; 80 by token match. The 8 paradigms arrive only as dead links; the 2 procedures were substring false positives. |
| 4 | 214 references | **213** (post-RTK removal) |
| 5 | "83 → 79 (-5%)" | **Does not reproduce.** Actual post-state is **59**. A traversal sweep found no variant yielding 79: all-relations 59, scope+req+sugg+inst 59, scope+requires 101, scope-only 135, depth-1 135, depth-2 92, depth-3 73. The **conclusion** stands on the reproduced M1/M2/M3 trio; the specific pair does not. |
| 6 | Baseline "6 passed" | **10 passed** (9+1), with no diff to either test file since `ed470756e`. |
| 7 | One `[:10]` reference cap | **Two** — `context.py:1169` (live) and `:1531` inside `_render_bootstrap`, which is called from nowhere in `src/` and only from `tests/charter/test_context.py:815`. That dead renderer is itself an instance of this mission's thesis. |
| 8 | `charter_file:` pointer field | **`charter:`** — already ships and is honoured (`pack_context.py`). `charter_file:` exists nowhere in the codebase. Following the research literally would have minted a second competing pointer, the exact defect FR-017 removes. |
| 9 | Line anchors in the fix-sizing table | Four of them drifted: `_load_doctrine_selection` :819→**:884**; `_render_selection_block` :1040→**:2464**; the cap :1103→**:1169**; `_filter_references_for_action` :1419→**:1484**. Function names are correct. Prefer symbol anchors. |
| 10 | `references.yaml` as a live "sixth store" | Retired — its body now lives in `charter.yaml`'s `catalog` (#2773). The file on disk is a corpse, which strengthens the point while mislabelling it. |
| 11 | Two `_PROJECT_KIND_DIRS` copies | **Four** — `doctrine/service.py:19`, `charter/kind_vocabulary.py:79`, `charter/pack_manager.py:136`, `cli/commands/doctrine.py:442`. **Two are explicitly exempted from the totality guard as "intentionally partial"**, so adding `asset` to some but not all goes green — `doctrine new --kind asset` would write where `DoctrineService` never reads. |

## 7. Divergence, adjudicated from source

**The unreachability count split four ways: 91 / 88 / 78 / 59.** These are not contradictory results.
They are four different traversals, because the draft FR-016 named none:

| lens | measure | value |
|---|---|---|
| discovery research | `{scope,requires,suggests,vocabulary,instantiates}` unbounded, unnormalized ids | 91 (of 185) |
| debugger-debbie | union of the action-doctrine walk over every mission type × action | 88 (of 184) |
| doctrine-daphne | `resolve_context` d=2 (bootstrap) | 78 · at d=1 (compact, the steady state) it is worse |
| reviewer-renata | research relation set with ids normalized | 59 |

**Adjudication: do not pick a number — remove the dependence on one.** All four lenses independently
converged on this remedy. FR-016 now names the traversal and depth; SC-005 asserts membership of a
pinned set rather than a cardinality.

**Procedures 13-of-18 versus 0-of-18 reconciles cleanly.** Daphne measured *graph* reachability — 13
of the 18 activated procedures are reachable under `resolve_context` d=2. Debbie measured *bundle
delivery* — 0, because `_ACTION_BUNDLE_SLOT_BY_KIND[PROCEDURE] = None` drops them at classification.
Both are correct and they feed one fix: adding the bundle slot delivers 13 immediately, and only
**five** procedures need authored edges (`documentation-gap-prioritization`,
`drill-down-documentation`, `event-storming-discovery`, `example-mapping-workshop`,
`migrate-project-guidance-to-spec-kitty-charter`). FR-011 is smaller than the draft assumed.

## 8. Coverage reality — proven by mutation, not by reading

**Would catch a regression:** `test_model_strictness_roundtrip.py:520/557` — the only real net in
this defect set.

**Would not catch — each mutation produced counts identical to its own baseline:**

| Mutation | Result |
|---|---|
| reference cap `[:10] → [:1]`, both sites | `test_context.py` 33P, `test_compact.py` 6P, contract 4S — unchanged; whole-directory counts byte-identical |
| `project_drg._serialize_graph` drops `edge.reason` | 23 passed vs baseline 23 passed |
| `scope_router.py:71` grain forwarding removed | four named test files, all identical to baseline |

Nothing pins the reference cap, the project-tier serializer, or the mission-type grain. C-006's
red-first discipline and NFR-005 are doing all the work — there is no inherited net to lean on.

## 9. Structural findings that reshaped the constraints

- **The class-closing charge (D-043).** The three strands share one mechanism — *a projection table
  narrower than the enumeration it projects, silenced by a `.get(…, default)` or a literal `[]`* —
  and the repo already ships two mechanisms against it. No FR extended either; FR-007 would have
  added a fourth hand-maintained entry to a table the totality guard already ignores. **Operator
  ruling: extend the mechanisms.** Now C-010.
- **NFR-006 versus a binding fail-open contract.** Every `_read_activated_*` is documented
  three-state: absence means *all built-ins available*. Harmless today only because the compact rail
  carries nothing; once delivery works, a project omitting `activated_procedures` would receive all
  18 at every boundary. **Operator ruling: migrate absence to explicit `[]`.** Now FR-018, with
  NFR-001 amended to permit the consumer-config mutation it requires.
- **C-005 is true as build order and false as risk mitigation.** `load_validated_graph` merges
  `.kittify/doctrine` — what `project_drg.persist` writes — into the graph the action bundle
  traverses. Today a project-tier serialization regression degrades charter synthesis only; after
  FR-010 it degrades every agent's context. C-005 now says "no **inbound** dependency" and requires
  FR-002's tests to cover the merged-graph read path.
- **FR-017 would have broken the only reachability-adjacent gate.** `_charter_activated_urns`
  (`test_extractor_projection.py:394-432`) reads the dead `config.yaml` mirror. Deleting the mirror
  makes its floor assertion fail and its stray guard **vacuously true**. The gate must be repointed
  first — now explicit in FR-017.
- **FR-015 justified itself by cascade, which any inbound edge satisfies.** Cascade walks outbound
  from the activation seed, so a source that is itself unreachable still satisfies it — precisely the
  PR #3007 shape. C-008 now rejects cascade as evidence, and C-007 carries the source-reachability
  precondition that makes "obvious" computable.
- **PR #3007's own exemplar is not action-reachable.** `procedure:onboard-external-agent-to-pack` —
  the ledgered `applies`→`requires` retype — attaches to `agent_profile:doctrine-daphne`, and only 1
  of 18 agent-profile nodes is action-reachable. Whether profile-seeded reachability counts is now a
  named FR-016 planning decision rather than a WP-review surprise.

## 10. Verdicts

- **architect-alphonso**: thesis real as a diagnosis, absent as a design; two blockers; would not send
  to plan without adjudicating them.
- **reviewer-renata**: unusually well-evidenced, not yet safe from the defect it exists to close; six
  of nine criteria fakeable; do not enter plan until SC-005 is a pinned set.
- **doctrine-daphne**: diagnoses the nominal-wiring failure correctly and reproduces it in its own
  requirement text; gap closable and cheap.
- **debugger-debbie**: direction sound, measurement layer ~60% verified; ship as-is and FR-012 lands
  green and inert.

All four objections are folded into the revised spec. The squad is advisory and gates nothing.
