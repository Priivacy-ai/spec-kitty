---
title: "DRG writers and reachability — the third writer, and why wiring an orphan is not fixing it"
description: "Inventory of the field-by-field DRG write paths that silently drop new edge fields, plus measured proof that PR #3007's orphan remediation moved the pinned metric far more than the real one."
doc_status: active
updated: '2026-07-28'
related:
- kitty-specs/doctrine-delivery-reachability-01KYMXD6/spec.md
- docs/adr/3.x/2026-07-26-1-drg-edges-are-the-canonical-relationship-authority.md
---
# DRG Writers and Reachability — Findings

**Origin.** Pre-spec discovery for this mission, 2026-07-28, scoping
[#2977](https://github.com/Priivacy-ai/spec-kitty/issues/2977) and the residual of
[#3009](https://github.com/Priivacy-ai/spec-kitty/issues/3009).

Measured against the shipped DRG on both the pre-merge branch and `upstream/main` @ `ed470756e`.

> ## ⚠ Two figures superseded; the writer count is understated
>
> The post-spec squad reproduced the graph metrics **exactly** (310 nodes / 781 edges; 30→21, 80→72,
> 144→139; activated-orphan 8→1) but found three corrections. See
> [`squad-findings-and-corrections.md`](./squad-findings-and-corrections.md).
>
> - **"83 → 79 (-5%)" (§3) does not reproduce.** Actual post-state is **59**. A traversal sweep found
>   no variant yielding 79 (all-relations 59, scope+req+sugg+inst 59, scope+requires 101, scope-only
>   135, depth-1 135, depth-2 92, depth-3 73). The 79 appears to be 54 + 25 activated directives left
>   unmatched by an id-form mismatch. **The conclusion stands** on the reproduced M1/M2/M3 trio; the
>   specific pair does not, and it must not seed a ratchet.
> - **There are four write sites, not three.** `_dump_graph_document` (document-level keys) and
>   `DRGGraph`'s missing `model_config` are named by the canonical helper's own docstring. A fifth drop
>   point sits at a *bridge* — `_bridge_org_edge_to_drg_edge` (`merge.py:848-878`).
> - **Writer 2 is already guarded.** `test_model_strictness_roundtrip.py:520/557` assert field
>   completeness for `rewrite_opposed_by` and go red when B1 lands. Writer 3 (`project_drg`) is guarded
>   by nothing — proven by mutation. **US1's priority is inverted from this document's ordering.**
> - **§5's `_PROJECT_KIND_DIRS` count is two, not the four that exist**; two of the four are explicitly
>   exempted from the totality guard, so a partial fix goes green.
> - **Baseline "6 passed" (§6) is 10 passed**, with no diff to either test file since `ed470756e`.

---

## 1. There are three field-by-field DRG writers, not two

`DRGEdge.model_fields` = `[source, target, relation, when, reason, provenance]`.
`DRGNode.model_fields` = `[urn, kind, label, provenance, tags]`.

Hand-written writers that restate a subset, and therefore **silently delete any field they do not
know about**:

| # | Writer | Status |
|---|---|---|
| 1 | `src/doctrine/drg/migration/extractor.py:1210/1219` | **Fixed by PR #3007** — derived from `model_fields` with `_FIELDS_WITHHELD_FROM_GRAPH_OUTPUT`. This is the working precedent to copy. |
| 2 | `src/specify_cli/migration/rewrite_opposed_by.py:338/347` | **#2977** — open. |
| 3 | `src/charter/synthesizer/project_drg.py:65` `_serialize_graph` | **Unfiled.** Named in neither #2977 nor PR #3007's ownership map. Emits `{kind, urn, label}` / `{relation, source, target, when, reason}` — **drops `tags` and `provenance` today**, and would drop B1's `impacts`/`is_symmetric` and B2's `aliases`. It is the project-tier DRG write path. |

**This is the ordering constraint for the whole programme.** Mission B1
(`drg-relation-impacts-vocabulary-01KYFV87`) exists to add two new `DRGEdge` fields. Shipping it
while writers 2 and 3 still drop unknown fields reproduces constraint **C-010** — *the field ships
inert and the tests stay green* — in the programme's own second mission. The programme's "A before
B1" ordering was applied to writer 1 only.

Also verified: `DRGGraph` still carries `model_config == {}` on both branches. PR #3007 added
`extra="forbid"` to `DRGNode` / `DRGEdge` only. This is the open decision #2977 flags.

**Scoping note.** Anyone scoping from #2977's title fixes writer 2 and believes the class is
closed. That is #2977's own stated failure mode, reproduced.

---

## 2. Reachability metrics — reproduced exactly

Computed independently via `doctrine.drg.loader`, adjacency over
`{scope, requires, suggests, vocabulary, instantiates}`, seeded from all 24 `kind == action` nodes,
forward-closed. Zero dangling endpoints, so nothing hides in the difference.

| measure | prior assessment | reproduced |
|---|---|---|
| incident to no edge (the pinned metric) | 30 | **30** |
| zero **inbound** edges | 80 | **80** |
| unreachable from any `action` node | 144 / 311 (46%) | **144 / 311 (46%)** |
| outbound-only (non-orphan, unreachable in fact) | 50 | **50** |

One sub-claim is off: the assessment breaks the 50 down as "15 agent profiles, 4 mission types, 18
tactics"; the actual split is **14 agent_profile, 4 mission_type, 15 tactic** (plus 6 styleguide,
3 action, 3 procedure, 2 directive, 2 paradigm, 1 toolguide). Cosmetic — the headline 50 is right.

Relation distribution (pre-merge): `suggests` 332, `requires` 259, `scope` 157, `instantiates` 8,
`rejects` 8, `specializes_from` 4, `reconciles_tension` 3, `in_tension_with` 2, `applies` 1.

---

## 3. The finding that matters: wiring an orphan is not fixing it

Same computation against PR #3007's fragments (**310 nodes / 781 edges**): M1 30 -> **21**,
M2 80 -> **72**, M3 144 -> **139**.

The PR closed 9 activated orphans. **Only 4 became reachable from any action node.**

| artefact | disposition | inbound edge added | action-reachable after |
|---|---|---|---|
| `procedure:red-main-release-discipline` | wired | `DIRECTIVE_030 --suggests->` | **yes** |
| `tactic:decision-marker-capture` | wired | `DIRECTIVE_003 --requires->` | **yes** |
| `tactic:no-parallel-duplicate-test-runs` | wired | `DIRECTIVE_030 --suggests->` | **yes** |
| `toolguide:python-review-checks` | wired | `styleguide:python-conventions --suggests->` | **yes** |
| `paradigm:atomic-design` | wired | `tactic:atomic-design-review-checklist --suggests->` | **no** — source itself unreachable |
| `styleguide:reasons-canvas-writing` | wired | `paradigm:structured-prompt-driven-development --suggests->` | **no** — source itself unreachable |
| `tactic:occurrence-classification-workflow` | wired | `directive:DIRECTIVE_035 --requires->` | **no** — DIRECTIVE_035 has **zero inbound edges itself** |
| `directive:DIRECTIVE_035` | "wired" by becoming an edge *source* | none | **no** |
| `toolguide:rtk-search-tooling` | node deleted | — | n/a |
| `styleguide:deployable-skill-authoring` | left as tracked defect | none | **no** |

Aggregate: activated-and-orphan went **8 -> 1 (-88%)** while activated-and-action-unreachable went
**83 -> 79 (-5%)**.

The sharpest instance: `tactic:occurrence-classification-workflow` is the workflow behind
`DIRECTIVE_035`, the directive governing mission B2's own occurrence map. It is still unreachable
**after being declared fixed**.

**This is not a criticism of PR #3007** — its WP09 explicitly logged the incidence-vs-traversability
gap and declined to change the metric mid-mission, which was the right call. It is the evidence
that the metric change cannot wait, because remediation performed against incidence demonstrably
buys a 90% reduction in the pinned number and 5% in the real one.

### Consequence for triage

Any disposition rule of the form *"has an inbound edge -> done"* reproduces the defect. The honest
test is **reachability from an action node**, and it must be the assertion, not the commentary.

---

## 4. #3009 residual, precisely

PR #3007 already implemented **remedy 1** (`_INTENTIONAL_ORPHANS` frozenset, four-way partition,
`_ACTIVATED_BUT_UNREACHABLE` shrink-only) and **remedy 2** (8 wired, 1 deleted).

What remains:

- **Remedy 3** — the `reachable_from_actions` companion assertion beside `_orphan_urns`, with the
  same membership-not-cardinality discipline the PR established for orphans.
- **Re-adjudication of the 4 nominal wirings** above.

Building a mission around "the nine orphans" would re-do landed work.

---

## 5. Related surfaces measured but deliberately out of scope

Recorded so a later mission does not re-derive them.

**The kind vocabulary is restated in at least 8 live places**, against
`doctrine/artifact_kinds.py`, whose module docstring (lines 30-32) declares that no second kind
enumeration may exist:

| Site | Entries | Failure mode |
|---|---|---|
| `doctrine/artifact_kinds.py` `_PLURALS` | 12 | canonical |
| `charter/activations.py:178` | 10 | most complete restatement |
| `charter/_activation_render.py:271` `_singular_kind` | 8 | **fails open** — `.get(k, k)` emits a plural selector |
| `charter/_activation_render.py:112` `_KIND_TO_PROPERTY` | 8 | same drift, separate table |
| `charter/drg.py:203` / `:220` | 10 / 10 | two more |
| `charter/consistency_check.py:89` | 9 | hyphen form; silent skip |
| `doctrine/service.py:19` `_PROJECT_KIND_DIRS` | **4** | #3038 — silent skip |
| `charter/kind_vocabulary.py:79` `_PROJECT_KIND_DIRS` | **4** | **second copy of the above**, enum-keyed, different package — named in neither #2981 nor #3038 |
| `charter/synthesizer/project_drg.py:44` `_KIND_TO_NODE_KIND` | **3** | #3038 — returns `None`, caller skips node + edges |

**#3038's proposed fix would make this worse**: it proposes hand-extending two of these tables
without knowing the third exists.

**The runtime->doctrine boundary ratchet (#2986) is currently enforcing an empty set.**
Module-level `from doctrine.*` under `src/specify_cli/` = **0**; function-local = **61 across 30
files** (worst: `cli/commands/_doctrine_collect.py` 10, `invocation/executor.py` 6,
`cli/commands/profiles_cmd.py` 5). Widening the ratchet is not tightening a working gate — it is
switching one on for the first time.

**`collaboration.operating-procedures` (#2994) is worse than filed.** Across 16 profiles, 50
declarations: **6** resolve to a procedure node, **8** resolve to a node of the wrong kind (7x
`tactic`, e.g. `tdd-red-green-refactor`, `bug-fixing-checklist`), **36** resolve to no node at all.
It needs the field-vs-edge decision made first and is the bulk graph mutation WP09 refused.

**Architectural constraint that shapes any fix here.** `doctrine` may not import `charter`
(`tests/architectural/test_layer_rules.py`); `org_pack_loader.py` carries an explicit comment that
it re-declares rather than imports for exactly this reason. Any "just import the one table"
instinct dies on this rule — the authority must sit in `doctrine/artifact_kinds.py` and charter
must import *down*.

---

## 6. Method

Ran against the real graph, not against prose: `doctrine.drg.loader.load_built_in_graph()` /
`load_graph_or_dir()` on both branches; an AST walk for function-local `from doctrine.*` imports
under `src/specify_cli/`; a YAML walk of `src/doctrine/agent_profiles/**/*.agent.yaml` resolved
against graph node ids. Baseline green:
`pytest tests/doctrine/drg/migration/test_extractor_projection.py tests/architectural/test_runtime_charter_doctrine_boundary.py -q`
-> **6 passed**. Per standing instruction the full architectural suite was **not** run.
