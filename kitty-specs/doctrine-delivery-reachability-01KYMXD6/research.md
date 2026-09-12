# Phase 0 Research — Doctrine Delivery Reachability

**Mission**: `doctrine-delivery-reachability-01KYMXD6` | **Date**: 2026-07-28
**Status**: complete — zero `NEEDS CLARIFICATION` markers remain; four planning decisions resolved.

The bulk of this mission's investigation happened **before** the spec, in a four-document discovery
pass and a four-lens adversarial squad. Those artefacts are the primary record and live in
[`research/`](research/). This file consolidates the decisions in Decision / Rationale / Alternatives
form and closes the unknowns that planning surfaced.

---

## D1 — The reachability traversal and depth

**Decision**: Reachability is defined by `doctrine.drg.query.resolve_context`, asserted at **both**
`d=1` (compact) and `d=2` (bootstrap), as two named sets.

**Rationale**: Four independent lenses measured four different unreachability values (91 / 88 / 78 /
59) because the draft named no traversal. The values were not contradictory — they were four
different walks. Naming one removes the ambiguity; naming *two depths* is required because **compact
is the steady state**. Bootstrap is consumed once per project; every load after that is compact, and
it is the stricter measure. Asserting only bootstrap would certify a delivery no agent receives.

**Alternatives considered**:
- *`resolve_context` at d=2 only* — one set to maintain, but leaves the path agents actually take
  unpinned. Rejected: that asymmetry is what let the original measurement read zero.
- *Action-doctrine bundle union across mission types* — closest to "what an agent receives", but
  couples the assertion to bundle internals, so it moves whenever classification changes for reasons
  unrelated to reachability. Rejected as an assertion target; retained as a delivery check under
  SC-001.

**Binding-method constraint**: the assertion **calls `resolve_context`**; it does not reimplement the
walk. `resolve_context` walks `scope` at depth 1, then `requires` transitively from *directly-scoped*
artefacts only, then `suggests` capped at depth, and never follows `instantiates`. Every hand-rolled
BFS in the discovery record diverges from it. Reimplementation is the defect that produced the
four-way split.

## D2 — The reachability seed set

**Decision**: Seed from **action nodes and activated agent profiles**.

**Rationale**: Profile activation is a genuine entry vector — a loaded profile carries directives and
tactics into an agent's working context independently of the action grain. Excluding it would also
have forced this mission to re-adjudicate a landed, gated PR #3007 fix:
`procedure:onboard-external-agent-to-pack` reaches nothing from an action but is reached from
`agent_profile:doctrine-daphne`.

**Measured effect** (indicative, hand-rolled walk — the binding numbers come from `resolve_context` at
pin time):

| seeds | d=1 | d=2 |
|---|---|---|
| actions only | 148 activated-unreachable | 108 |
| **actions + profiles** | **136** | **87** |

Profile seeding adds 43 reachable nodes at d=1 and 58 at d=2.

**Alternatives considered**:
- *Actions only, profile seeding filed* — smaller and avoids re-opening landed work, but leaves the
  measure describing less than half of how doctrine actually reaches agents. Rejected.
- *Actions only, and re-adjudicate #3007's edge in this mission* — honest but re-opens a decision
  carrying its own architectural gate (`test_no_dead_doctrine_paths.py`). Rejected as scope.

**Residual risk**: 17 of 18 agent-profile nodes are themselves action-unreachable, so profile seeding
mostly widens the *frontier* rather than the *root*. If the pinned d=1 set does not move materially
once `resolve_context` is used, that is a finding about profile wiring, not a reason to change the
decision.

## D3 — The shape of the writer class-closure

**Decision**: A **registry** every edge/node-serializing writer joins; the field-completeness test
iterates the registry.

**Rationale**: C-010 requires extending the mechanism rather than fixing instances. The repository
already proves the derivation half works (`_model_to_dict` + `_FIELDS_WITHHELD_FROM_GRAPH_OUTPUT`).
A registry is positive and discoverable — the test enumerates it, and the canonical helper's docstring
already reads as an informal registry naming four sites. Making that list executable is the smallest
honest step from where the code is.

**Alternatives considered**:
- *AST gate on dict-literal edge payloads* — catches the writer that never registers, which is
  precisely the registry's blind spot. Rejected as the primary mechanism because it needs an exemption
  list and will false-positive on unrelated dicts; **recorded as a follow-up** since the gap is real.
- *Both* — complete in both directions at roughly double the mechanism cost and about one extra work
  package. Rejected for this mission; the registry closes the four known sites and the bridge.

**Known gap, recorded deliberately**: a writer that never joins the registry is invisible to it. This
is a smaller residual than today's hand-written three-row list, and it is the tradeoff the AST
follow-up exists to close.

## D4 — Asset delivery

**Decision**: Assets are **delivered in the action bundle**, not merely resolvable.
`_ACTION_BUNDLE_SLOT_BY_KIND[ASSET]` gains a real slot with a recorded verdict.

**Rationale**: Making assets resolvable but not deliverable would leave them reachable only by
someone who already knows the identifier — the same dead end the activation half of this mission
exists to close. Delivering them closes it for assets too.

**The tension this creates, and how it is resolved**: assets are excluded from
`_NON_AUGMENTATION_ELIGIBLE_KINDS`, i.e. they are deliberately **not charter-activatable**. Delivering
them without activating them is therefore a *third category*: reached through inbound
`requires`/`suggests` edges from reachable sources, never through an activation list. That is coherent
with the doctrine's own stated mechanism for resolve-only nodes, and it must be documented at the slot
table, which is a recorded-verdict surface by design.

**Consequence that expands FR-015**: `asset:common-docs-structural-lint` has four inbound `requires`
edges and **all four sources are unreachable** — the `common-docs` cluster is a strongly-connected
island no action scopes. Delivering assets without wiring that cluster ships the delivery path while
the only shipped asset still fails to arrive, which is this mission's defect class reproduced. The
cluster is folded into FR-015's enumerated table under C-007's source-reachability precondition.

**Alternatives considered**:
- *Resolution-only with a recorded verdict* — bounded and consistent with the activation exclusion,
  but leaves the agent-facing path broken. Rejected by operator ruling.
- *Defer with a filed issue* — leaves a bare `None` reading as an oversight rather than a decision,
  which is the exact shape Mission A spent a hundred files removing. Rejected.

---

## Unknowns closed during planning

| Unknown | Resolution |
|---|---|
| Which pointer field names the charter from `.kittify/config`? | **`charter:`** — already ships and is honoured by `_load_charter_activation_source`. `charter_file:` exists nowhere in the codebase; the discovery record named it in error and following it would mint a competing pointer. |
| How does absence of an `activated_<kind>` key resolve? | Migrated to an explicit empty list (FR-018). The documented three-state contract (absence ⇒ *all built-ins*) is harmless only while the compact rail carries nothing; once delivery works it becomes unbounded fail-open. |
| Can the derived helper reach `specify_cli` without violating layer direction? | Yes, through a new `src/charter/drg.py` facade. The boundary ratchet's allowlist is empty, so a direct import is illegal; a function-local import is ratchet-legal but joins the 61 that already bypass the gate. |
| Is `_render_bootstrap` (`context.py:1531`) live? | No — called from nowhere in `src/`, only from `tests/charter/test_context.py:815`. **Ruling: delete it.** A live caller discovered during implementation is a finding, not a reason to keep it. |
| Does fixing `resolver.py`'s four `[]` literals surface styleguides and toolguides? | **No.** `_render_text` never reads those fields; the drop is one layer lower in `_render_bootstrap_text`. This was the sixth delivery defect, unnamed before the squad. |
| Is the #2977 writer unguarded? | **No — it is already guarded** (`test_model_strictness_roundtrip.py:520/557`) and goes red when B1 lands. `project_drg` is the unguarded one, proven by mutation. US1's internal priority was inverted. |
| Is the org-tier bridge a writer? | Functionally yes — `_bridge_org_edge_to_drg_edge` constructs a three-field `DRGEdge`, dropping fields **before any writer runs**. It must join the registry or SC-004 is false at the org tier. |
| Does SC-003 need a wheel? | Yes. In-repo, `resolve_doctrine_root()`'s dev-layout fallback means the criterion cannot fail. |

## Verification baseline

Recorded so a work package can tell its own red from inherited red.

- Graph on this branch: **310 nodes / 781 edges**; orphans 21; zero-inbound 72; dangling endpoints 0.
- Activated total: **184** (directives 25, tactics 110, procedures 18, styleguides 12, toolguides 11,
  paradigms 8) — identical in `charter.yaml` and the retired `config.yaml` mirror.
- Green at baseline: `tests/doctrine/drg/migration/test_extractor_projection.py` +
  `tests/architectural/test_runtime_charter_doctrine_boundary.py` (10 passed);
  `tests/doctrine/test_template_asset_e2e.py` + `test_extractor_asset.py` + `test_artifact_kinds.py`
  (50 passed); `tests/docs/test_docs_structural_lint.py` (29 passed);
  `tests/architectural/test_layer_rules.py` (17 passed).
- **Unprotected today, proven by mutation** — the reference cap (both sites), the project-tier
  serializer, and the mission-type grain forwarding all survive deliberate breakage with test counts
  identical to baseline. C-006 and NFR-005 carry the whole load here; there is no inherited net.
