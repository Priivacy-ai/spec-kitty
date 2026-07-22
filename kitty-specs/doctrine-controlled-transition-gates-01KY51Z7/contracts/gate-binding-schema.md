# Contract: Gate-binding YAML schema

**Traces**: FR-005, FR-006, FR-007, FR-008, C-001, C-002, NFR-004, US3
**Home**: contract-level `gates: list[GateBinding]` on `MissionStepContract`
(`doctrine/missions/step_contracts.py:86`), authored in
`built_in_step_contracts/review.step-contract.yaml`

A gate binding is a **field on the review step-contract** (a relationship/configuration on an
existing artefact — the content-vs-relationship principle, C-001), NOT a standalone activatable
artefact. It is contract/action-level (a gate binds an action's transition, not an individual
step). It resolves through the existing `mission_step_contract` kind (FR-006) — the runtime-wired
surface the executor consumes (`executor.py:22-24,160,188`) — reconciling decisions #1 and #2.
No new `gate` kind; the unified `MissionStep` is not the home (`MissionType.steps` has no
gate-time reader).

## Schema

```yaml
# authored in review.step-contract.yaml (action: review), alongside the contract's steps
gates:
  - on_transition: "in_progress->for_review"   # required
    handler: "spec-kitty-pre-review"           # required
    handler_kind: "mission_step_contract"      # default; inert-in-half-A discriminator
    schema_version: "1.0"                       # required
    fail_open: true                             # default true
    provenance: "built-in"                      # optional
```

| Field | Type | Default | Rule |
|---|---|---|---|
| `on_transition` | `str` | required | `"<from_lane>-><to_lane>"`; both sides valid lanes |
| `handler` | `str` | required | `GATE_REGISTRY` key only (plain dict lookup at dispatch); NOT a DRG candidate — activation keys on the owning contract URN |
| `handler_kind` | `Literal["mission_step_contract","asset"]` | `"mission_step_contract"` | inert in half A; `asset` round-trips but is never executed (C-002) |
| `schema_version` | `str` | required | versioned; unversioned ⇒ reject |
| `fail_open` | `bool` | `true` | unresolved/inactive binding ⇒ advisory (never hard-fail) |
| `provenance` | `str \| None` | `None` | optional; round-trips byte-stable |

## Validation contract (`model_config = frozen + extra="forbid"`)

- **Unknown key ⇒ loud reject** at load (US3 AS3), never a silent drop.
- **Missing `schema_version` ⇒ reject** — an unversioned binding is invalid.
- **`handler_kind: asset` in half A** — validated, round-tripped **byte-stable**, and treated as
  **inert** (no attempt to execute an asset). This is the forward-compatible seam so #2599
  (half B, executable assets) needs no breaking `schema_version` bump on this frozen model
  (FR-005, C-002, NFR-004, US3 AS4).
- **`provenance`** round-trips byte-stable (NFR-004).

## Valid example (accepted)

```yaml
gates:
  - on_transition: "in_progress->for_review"
    handler: "spec-kitty-pre-review"
    schema_version: "1.0"
```
Accepted: `handler_kind` defaults to `mission_step_contract`, `fail_open` to `true`.

## Rejection examples

```yaml
# REJECTED — unknown key (extra="forbid")
- on_transition: "in_progress->for_review"
  handler: "spec-kitty-pre-review"
  schema_version: "1.0"
  retries: 3                    # <- not in schema

# REJECTED — missing schema_version
- on_transition: "in_progress->for_review"
  handler: "spec-kitty-pre-review"

# REJECTED — invalid handler_kind
- on_transition: "in_progress->for_review"
  handler: "spec-kitty-pre-review"
  handler_kind: "webhook"       # <- not in the Literal set
  schema_version: "1.0"
```

## Half-B round-trip example (accepted, inert)

```yaml
# ACCEPTED in half A; loaded, re-serialized byte-stable, NEVER executed
- on_transition: "in_progress->for_review"
  handler: "third-party-scanner"
  handler_kind: "asset"
  schema_version: "1.0"
  provenance: "org:acme-security-pack"
```

## Resolution contract (how a binding fires) — FR-007, FR-008

1. The hook maps the lane edge to its owning action/contract
   (`in_progress->for_review → the review action's review.step-contract.yaml`; see
   `data-model.md` §6) and reads that contract's `gates` via
   `load_gate_bindings(repo_root, mission, action)` →
   `MissionStepContractRepository.get_by_action(mission, action)` (`step_contracts.py:160`); the
   `mission` axis is resolved from `st.mission_slug` → `meta.json`. No `(mission, review)` contract
   or no `for_review` binding → a distinguishable `NO_COVERAGE` warn (§ no-contract path), not a
   silent vanish.
2. It computes the activated `mission_step_contract` URN set via `filter_graph_by_activation`
   (`charter/drg.py:433`). The gate is the **owning review contract's URN** (canonical form
   `mission_step_contract:<mission-type>/<id>`, e.g. `mission_step_contract:software-dev/review`,
   `drg.py:271`) — its presence in the activated set is what gates whether the contract's bindings
   fire at all.
3. A binding is **active** iff its `on_transition` matches the current edge AND the
   **owning-contract URN** ∈ activated set. The `handler` is then resolved by a plain
   `GATE_REGISTRY[b.handler]` dict lookup at dispatch (KeyError = misconfig); it is **NOT** matched
   against a DRG URN — a handler name is a registry key, and `_candidate_urn(handler)` would return
   `None`, permanently emptying `active`.
4. Contract-URN not activated (or no contract/binding) ⇒ `fail_open` advisory / distinguishable
   `NO_COVERAGE` warn (US3 AS2): the handler does not run, and the non-resolution is **detectable**
   (negative-control arm, NFR-003), not silent.

## Precedence (FR-008)

Multiple activated bindings on one edge all fire (no last-wins). Dispatch order is a stable sort
by `(declaration_index_within_step, handler)`; verdicts aggregate per `data-model.md` §7.

## Save round-trip / byte-stability (NFR-004)

`gates: list[GateBinding] = Field(default_factory=list)` — an absent `gates` key loads cleanly to
`[]` (no author burden on the 15 existing contracts). **But** `MissionStepContract.save()` does
`model_dump(mode="json", exclude_none=True)` (`step_contracts.py:206`), and `[]` is not `None`, so
a naive re-save would inject a spurious `gates: []` into previously-clean contracts. The save path
MUST NOT reintroduce `gates: []` into contracts that never declared it — use `exclude_defaults=True`
(or an equivalent empty-omit) so a default-empty `gates` is omitted on serialize. A **round-trip
byte-stability test** (load → save an unrelated contract → assert byte-identical, no `gates: []`
appears) guards this.

**No new schema/doctor surface.** The field needs **no** `src/doctrine/schemas/*.schema.yaml` and
**no** doctor update: step-contracts are pydantic `extra="forbid"` self-validating, so the model
IS the schema.
