# Contract — Activation Authority, Delivery Rail, and Reachability

**Requirements**: FR-009 – FR-014, FR-015, FR-016, FR-017, FR-018 · **Criteria**: SC-001, SC-002,
SC-005, SC-006, SC-007 · **Constraints**: C-001, C-007, C-008, C-009, NFR-003, NFR-006

---

## 1. Activation authority

| # | Obligation |
|---|---|
| V-1 | `charter.yaml` is the single activation authority. `.kittify/config.yaml` points at it via **`charter:`** — the key that already ships. **`charter_file:` is not the field name and must not be introduced.** |
| V-2 | The `activated_*` mirror is removed from `config.yaml` **only after** `_charter_activated_urns` (`tests/doctrine/drg/migration/test_extractor_projection.py`) is repointed at the resolved source. Removing it first makes that gate's floor assertion fail and its stray guard vacuously true. |
| V-3 | An absent `activated_<kind>` key resolves to `[]` at every boundary. The three-state contract (absence ⇒ all built-ins) is retired by migration (FR-018). |
| V-4 | `GovernanceResolution` is populated **from** `PackContext` / `resolve_config_activated_roots`. Reading a store directly creates a fifth reader and is a defect. |
| V-5 | Identifier normalization between store form (`025-boy-scout-rule`) and selector form (`directive:DIRECTIVE_025`) happens at one boundary, lands as a **separate declared change**, and is excluded from SC-005 (C-009). |

**SC-007 acceptance**: a **divergent-mirror fixture** where the two stores disagree — the only case
that proves which store won. A no-op migration must fail it.

---

## 2. Delivery rail

```python
@dataclass
class _ActionDoctrineBundle:
    directive_ids: list[str]
    tactic_ids: list[str]
    styleguide_ids: list[str]
    toolguide_ids: list[str]
    procedure_ids: list[str]      # NEW — its absence made all 18 activated procedures undeliverable
    asset_ids: list[str]          # NEW — per D4; delivered, not activation-gated
```

**Revised 2026-07-28** after the post-plan squad. Two changes are load-bearing: B-1 is now a **total
gate function** (the old equality made `asset_ids = []` the conforming implementation), and delivery is
modelled per **channel** (there are two, and both under-deliver).

| # | Obligation |
|---|---|
| B-1 | For a named channel and a named (action, mission_type), the **delivered** id set for each kind equals `gate(kind) ∩ channel_reachable`, where `gate` is a **total function over `NodeKind`** — `activated(kind)` for activation-eligible kinds, `ALL` for delivered-but-ungated kinds. `gate` is a **column of the same NodeKind-keyed table as the slot**, not an enumerated exception. Stating this as `activated ∩ reachable` is a defect: `activated(asset)` is `∅` by construction, so a uniform reading ships `asset_ids = []` forever and passes. |
| B-1a | Because `gate` is total, `TEMPLATE`'s exclusion carries a stated reason rather than being `ASSET`'s untreated twin. |
| B-2 | Every id the bundle resolves appears in the **rendered output**. Fixing `resolver.py`'s four `[]` literals is insufficient: `_render_text` never reads those fields and the styleguide/toolguide drop is in `_render_bootstrap_text`. |
| B-3 | Delivery happens on **every** load, not only when `first_load` is true. This is a control-flow change — the compact returns fire *before* the bundle is computed. |
| B-4 | Every `NodeKind` in `_ACTION_BUNDLE_SLOT_BY_KIND` maps to a slot **or to a recorded verdict**. A bare `None` is indistinguishable from an oversight. |
| B-5 | No truncation. The cap is a defect, not a budget mechanism; budget pressure uses the existing `BUDGET_DEFAULT = 32_000` degradation-to-fetch-stanza path. Cardinality carries a shrink-only ceiling of 90 (NFR-003). |
| B-6 | Actions outside `BOOTSTRAP_ACTIONS` (currently `{specify, plan, implement, review}`) are explicitly ruled in or out. Today they return compact unconditionally. |
| B-7 | Activation resolution errors **propagate**. `prompt_builder`'s `except Exception: pass` is replaced; the pattern to copy sits immediately above it. |

**Assets are a third category** (D4): delivered through inbound `requires`/`suggests` edges from
reachable sources, never through an activation list — they remain excluded from
`_NON_AUGMENTATION_ELIGIBLE_KINDS`. The verdict is documented at the slot table.

### Caller grain

| # | Obligation |
|---|---|
| B-8 | `agent/workflow.py:738` and `agent/workflow_executor.py:459` supply the mission-type grain. |
| B-9 | `prompt_builder` is **not** in scope for grain — it already forwards correctly via `build_with_scope`. Only its exception policy changes. Removing `scope_router.py:71`'s forwarding currently breaks no test; coverage is added, not assumed. |

---

## 3. Reachability

There are **two delivery channels**, each with its own traversal, its own named set, and its own
delivery obligation. Reach is never claimed without delivery (C-008).

| # | Obligation |
|---|---|
| R-1 | **Action channel** reachability is computed by **calling** `doctrine.drg.query.resolve_context`. Reimplementing the walk is forbidden — every hand-rolled BFS in this mission's history produced a wrong number, including one that reached the first revision of the plan. |
| R-2 | Two named action-channel sets are asserted: **`d=1`** (compact, the steady state, the stricter measure) and **`d=2`** (bootstrap). The measured spread between them is **7 nodes**, not the 49 first claimed. |
| R-3 | **Profile channel** reachability is a **separately named** `walk_edges` over `{requires, specializes_from}` from activated agent profiles. It is **not** a `resolve_context` seed set: `resolve_context` step 1 walks `scope` edges only, and `agent_profile` nodes have 97 outbound `requires`, 4 `specializes_from`, and **zero outbound `scope`** — so seeding profiles into it contributes exactly **0 artefacts at every depth**. |
| R-3a | The profile channel carries a **delivery** obligation (FR-020), not only a measure. Today `_render_profile_directives` / `_render_profile_tactics` are the only profile render paths, so a profile-resolved procedure, styleguide, toolguide or asset reaches nobody. `procedure:onboard-external-agent-to-pack` is the live instance. |
| R-3b | `profile` is `str \| None`, so the channel is **conditional on caller configuration**. Measuring it as unconditional repeats the fail-open shape FR-018 retires. |
| R-4 | Assertions are **set membership**, not cardinality. A failure names the artefact. |
| R-5 | `_ACTIVATED_BUT_UNREACHABLE` measures edge **incidence** despite its name; it is renamed in the same work package that lands the real set. |
| R-6 | Cascade is not evidence of reachability (C-008). Cascade walks outbound from the activation seed, so any inbound edge satisfies it — including one from an unreachable source. |

### FR-015 wiring table

Each row must carry the proposed source's **own** reachability, measured, not asserted:

| artefact | proposed inbound source | source action-reachable? | disposition |
|---|---|---|---|
| *(enumerated during implementation)* | | **measured value** | wire / defer |

C-007's two-part test decides membership: the relationship is attested in the artefact's own text
**and** the proposed source is itself reachable (or the edge is a `scope` edge from an action node).
Everything failing the second half is deferred to the operator interview.

**In scope by consequence of D4**: the `common-docs` cluster. `asset:common-docs-structural-lint` has
four inbound `requires` edges and all four sources are unreachable — a strongly-connected island no
action scopes. Delivering assets without wiring it ships the delivery path while the only shipped
asset still fails to arrive.

**Destination**: edges land in `_CURATED_ARTIFACT_EDGES`, which mission **B2 retires**. The handoff is
recorded so B2 does not inherit an unknown migration.

---

## 4. Reference block

| # | Obligation |
|---|---|
| F-1 | Every emitted pointer resolves. Today all ten are dead — `.kittify/charter/_LIBRARY/` does not exist. |
| F-2 | Selection is distributed across kinds. `_filter_references_for_action` is a **no-op for every doctrine kind** (213 → 213), so filtering is not the fix. |
| F-3 | Emitted sets differ across at least two actions. |
| F-4 | **Both** cap sites are addressed: `context.py:1169` (live) and `:1531` in `_render_bootstrap`. |
| F-5 | `_render_bootstrap` is **deleted** — it is called from nowhere in `src/`, only from `tests/charter/test_context.py:815`, making it an instance of this mission's own thesis. A live caller found during implementation is a finding, not a reason to keep it. |
| F-6 | SC-006 carries a **non-vacuity floor** — a stated minimum emitted per action for `software-dev`. Without it the criterion passes over an empty set, which is the current state. |

No test pins either cap today (proven by mutation), so F-1 through F-4 need new coverage rather than
an adjusted assertion.
