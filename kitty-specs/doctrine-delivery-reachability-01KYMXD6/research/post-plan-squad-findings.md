---
title: "Post-plan squad findings — the measurement was wrong and the registry was unbuildable"
description: "Three profile-loaded lenses on the implementation plan: nine blockers, the withdrawn reachability figures, and the two-channel delivery model that replaced the seed-union."
doc_status: active
updated: '2026-07-28'
related:
- kitty-specs/doctrine-delivery-reachability-01KYMXD6/plan.md
- kitty-specs/doctrine-delivery-reachability-01KYMXD6/research/squad-findings-and-corrections.md
---
# Post-Plan Squad — Findings

**Point-cut.** Post-`/spec-kitty.plan`, 2026-07-28. Three profile-loaded lenses —
`planner-priti` (scope, sequencing, tracker hygiene), `paula-patterns` (decomposition, boundaries),
`python-pedro` (implementer feasibility) — read-only, each required to ground claims in code.

**Sharp question:** *is this plan executable as decomposed, or does an IC hide a dependency, a
foldable duplicate, or work that cannot be done in the order stated?*

Answer: **all three.** Nine blockers. The plan was revised before tasks.

---

## 1. The measurement was produced by the forbidden method

The plan's binding-method note says the assertion must call `resolve_context` and warns that
reimplementing the walk is how four lenses produced four numbers. **The plan then published figures
from a hand-rolled BFS anyway.**

| claim | withdrawn | correct |
|---|---|---|
| activated-and-unreachable, d=1 | 136 | **103** |
| activated-and-unreachable, d=2 | 87 | **96** |
| profile-seed contribution | +43 / +58 | **0 at both depths** |
| d=1↔d=2 spread | 49 | **7** |

**Why profile seeding contributes zero.** `resolve_context` step 1 walks `scope` edges only from the
seed. `agent_profile` nodes have **97 outbound `requires`, 4 `specializes_from`, zero outbound
`scope`**. Measured independently by two lenses: `resolve_context(agent_profile:doctrine-daphne, d=2)`
returns 0 artefacts, and the union over all 18 profiles moves reachability 111→111 at d=1 and 118→118
at d=2.

The 7-node spread also withdrew Complexity Tracking row 3, whose justification for two named sets was
that the spread is large. And **25 of the 184 activated identifiers are not graph nodes at all**, so
roughly a quarter of any unreachable count is C-009 normalization that must not be banked as progress.

## 2. The two-channel model — what replaced the seed union

Three lenses rejected the seed union for three different reasons: profile artefacts are not
*delivered* (paula), profile seeds are not *reached* by the binding traversal (priti), and the
contribution measures zero (pedro).

**Operator ruling 2026-07-28:** *"profiles are loaded by the implementation loop when working on WPs.
they ARE an entrypoint."*

That is correct and it reframes the finding. There are **two delivery channels**:

| channel | traversal | delivers today | gap |
|---|---|---|---|
| **action** | `resolve_context` from action nodes | directives, tactics | styleguides, toolguides resolved then dropped |
| **profile** | `walk_edges` over `{requires, specializes_from}` from activated profiles | profile-cited directives and tactics only | procedures, styleguides, toolguides, assets reach nobody |

So the profile channel is a first-class entry vector that **resolves artefacts it cannot render** —
the same defect as the action channel's, one entry vector across. `procedure:onboard-external-agent-to-pack`
(PR #3007's exemplar, reached from `agent_profile:doctrine-daphne` by a `requires` edge) is the live
instance, and it is now **in scope** under FR-020 rather than being smuggled into the action set by a
union that asserted reach no channel delivers.

## 3. The writer registry was unbuildable as contracted

**Three of five members cannot satisfy one Protocol.** `project_drg._serialize_graph` is
`(DRGGraph) -> str` with dicts built inline; `_dump_graph_document` is `(DRGGraph, Path) -> None`;
`_bridge_org_edge_to_drg_edge` **constructs** a `DRGEdge` from a fragment edge — its input is not a
`DRGEdge`, its output is not a mapping, and W-1's predicate is not type-correct against it. Now three
shapes: `MappingWriter`, `DocumentWriter`, `ModelBridge`.

**And it cannot be hosted in `doctrine`.** A tuple naming charter and specify_cli members reds
`test_layer_rules.py:282` and `:293` — two of this mission's own named gates. `charter` reds `:311`.
Hosted in `specify_cli`; tests are not layered and the precedent exists.

**The derived helper is not total.** Proven by execution: `_render_for_yaml` returns `None` for `None`
*and for an empty list*, so a novel `impacts: str|None = None` or `impacts: list[str] = []` field is
dropped by **both** derived writers, while `is_symmetric: bool = False` survives. Since B1's `impacts`
is plausibly list-shaped, the flagship gate would be vacuous for the field it exists to protect.

**Good news:** the mutation-as-fixture mechanism **works**, via subclassing. Models are not frozen
(only `extra="forbid"`), attribute injection and extra kwargs are rejected, and `DRGGraph` preserves
the subclass all the way to the writers.

## 4. FR-010's cost, measured

```
build_charter_context (compact):   982 ms   <- today's steady state
_load_action_doctrine_bundle:      961 ms   <- what FR-010 moves onto that path
  filter_graph_by_activation:      517 ms   <- 552 ruamel YAML loads per call, uncached
  resolve_context d=1 / d=2:         0.2 ms
```

`resolve_context` is free; the cost is entirely the load+filter. **Operator ruling: accepted, not
gated** (NFR-007). Recorded with figures so a later regression is distinguishable, and with the
memoization option on the record as available rather than unknown.

## 5. Structural findings folded into the plan

- **`charter/drg.py` already exists** — 532 lines, 24-entry `__all__`, and `rewrite_opposed_by.py:97`
  already imports through it. Complexity row 2 was spurious; IC-01 is *cheaper*.
- **The slot table is already total and guarded.** The work is flipping two verdicts, not building the
  guard — and doing so **reverses PR #3007 WP03's recorded position** for two of twelve exclusions,
  which now carries a recorded criterion.
- **`depth` means two things.** `_EXTENDED_CONTEXT_DEPTH = 3` gates styleguide/toolguide rendering, and
  `resolve_context`'s docstring confirms depth "also controls extended artifact inclusion" — so at the
  pinned depths, I-B1 is structurally unachievable for exactly the two kinds called the sixth defect.
  IC-06 now owns it.
- **"The compact returns" is four sites in two functions**, including the `--json` payload builder the
  quickstart uses to *observe* the defect — absent from the first revision's surfaces.
- **Five parallel per-kind projections already exist** in one call path, and `_classify_artifact_urns`
  builds the mapping then destroys it at the return boundary. The plan was about to create a sixth.
- **Scaffold parity targeted the wrong surface** — `doctrine new` rejects two dicts upstream of the one
  IC-02 named, and one of them is an `if`-chain the totality guard cannot see.
- **Two of the four kind-map copies are string-keyed** and therefore invisible to the guard's AST scan
  entirely — worse than exempted.
- **Three dependency edges were spurious** (IC-05→IC-04, IC-07→IC-06, IC-08→IC-06) and **two genuine
  ones were undeclared** (IC-04→IC-01 through regenerated fragments; IC-09→IC-02/IC-06).
- **IC-07 was a leftovers bin** — grain to IC-06, fail-closed policy to IC-05, and the number reused
  for the profile channel.
- **Size was ~30% light** — 65-85 files, not 45-60, and SC-003's clean-env wheel harness had no home.
- **Two prior migrations already fought over the activation surface in opposite directions**, and the
  mirror survived both. FR-017 is the third pass.

## 6. Calibration note

Pedro probed every file:line anchor in the plan and found **no drift**; named gates ran 57 passed. The
plan's *facts* were sound. What failed was its contracts, its sequencing, and — most consequentially —
one measurement it produced by the method it had itself forbidden two paragraphs earlier.

## 7. Verdicts

- **planner-priti**: sequenceable, but not in the order stated, and the scope is not honest about its
  size. Fix the two blockers and the issue ledger before tasks.
- **paula-patterns**: the cut lines are mostly right; failures cluster where a boundary was drawn
  around a *file* instead of a *contract*.
- **python-pedro**: well-anchored, but three things would stop an implementer on day one, two of them
  in the contracts rather than the prose.
