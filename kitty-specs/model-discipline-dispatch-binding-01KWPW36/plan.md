# Implementation Plan: Model-Discipline Dispatch Binding

**Branch**: `design/model-discipline-dispatch-2364` | **Date**: 2026-07-04 | **Spec**: [spec.md](./spec.md) (rev 2, full-evaluator scope)
**Input**: `kitty-specs/model-discipline-dispatch-binding-01KWPW36/spec.md`

## Summary

Bind the authored-but-dead model-discipline rule at the governed dispatch seam. Build the full routing machinery: a **catalog loader** (activation→YAML→`ModelToTaskType`→freshness), an **action→task_type mapping**, a deterministic **objective-function evaluator** (`task_fit` × `weights` under `objective`, with `quality_first` as the capability lever, applying `tier_constraints` + `override_policy` precedence), surfaced as an **advisory recommendation** on the `InvocationPayload` returned by `ProfileInvocationExecutor.invoke()`. Add an optional per-profile `model`/`effort` field on the **`profile.py` domain model** (schema regenerated from `schema_models.py`) as the override anchor. Make the charter references real doctrine: a new `model-task-routing.tactic.yaml` + a directive `suggests` edge + repoint the snake_case charter token; a one-line `suggests` edge for the already-existing `autonomous-operation-protocol` tactic. Populate a starter catalog. Install a refactor-stable all-sections no-dangling-reference invariant. Advisory-only (the seam never spawns a model); interactive delegation + `gated`/`required` modes are out of scope.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pydantic (`ModelToTaskType`, `AgentProfile`), ruamel.yaml, existing `specify_cli.invocation` (executor/router/registry) + `charter`/`doctrine` packages, DRG (`graph.yaml`) + `reference_resolver`
**Storage**: Filesystem — catalog YAML shipped as package data at `src/doctrine/model_task_routing/catalog/model-to-task_type.yaml` (loader resolves via `importlib.resources`); `agent-profile.schema.yaml` (generated); `graph.yaml`; `references.yaml` (generated bundle)
**Testing**: pytest; red-first through `spec-kitty dispatch` / `ProfileInvocationExecutor.invoke()` payload contents (NOT the Pydantic model in isolation, NOT a stubbed recommendation). Evaluator unit-tested pure. Vary-with-catalog + load-via-DRG anti-fake assertions
**Target Platform**: CLI (`spec-kitty dispatch`) + library (`invoke()`)
**Project Type**: single (Python package)
**Performance Goals**: N/A — one small catalog read + a bounded scorer per dispatch; advisory, off the hot render path
**Constraints**: advisory-only (`executor.py:150,181` — no model spawn); DRG-driven reference resolution (C-002); generated schema — regenerate `schema_models.py`, never hand-edit the `.yaml` (C-005); `override_policy: advisory` only (C-004); boundary vs #1049 (C-003)
**Scale/Scope**: ~5-6 WPs; surfaces: `invocation/{executor,router}.py`, a new loader/evaluator module under `model_task_routing/`, `profile.py` + `schema_models.py`, `charter.md` + `graph.yaml` + a tactic file + a catalog instance, `test_no_dead_modules.py` allowlist, + tests

## Charter Check

*GATE: pass before Phase 0; re-check after design.*

- **Single canonical authority** ✅ — one loader + one evaluator; the catalog becomes the single routing source. No parallel routing path.
- **Architectural alignment / layering** ✅ — loader/evaluator live with the catalog model (`src/doctrine/model_task_routing/`); the dispatch seam (`specify_cli.invocation`) consumes them; charter references resolve via the DRG, not manual edits. Honors kernel←doctrine←charter←specify_cli.
- **ATDD-first / red-first** ✅ — NFR-001 mandates red-first through `dispatch`/`invoke()`; SC-001 pins the vary-with-catalog derivation check (anti-fake); NFR-004 pins evaluator determinism.
- **No new shadow paths** ✅ — this *adds the missing consumer* to an existing schema; it does not create a second routing surface (#1049 stays a separate track).
- **Catfooding** ✅ — converts the dangling charter rule into loadable activated doctrine (the tactic + DRG edge), catfooding the doctrine system.
- **Terminology** ✅ — no legacy terms; run the terminology guard (charter/doctrine prose touched).

No violations → Complexity Tracking omitted.

## Project Structure

```
src/doctrine/model_task_routing/
├── models.py                 # existing Pydantic model (remove from dead-module allowlist as loader lands)
├── loader.py                 # NEW — FR-001: activation→path→YAML→validate→freshness
└── evaluator.py              # NEW — FR-003: objective-function scorer + override_policy precedence
src/doctrine/
├── tactics/built-in/model-task-routing.tactic.yaml   # NEW — FR-006
└── graph.yaml                # + tactic node + 2 directive→tactic suggests edges (FR-006/007)
src/specify_cli/invocation/
├── executor.py               # FR-004: InvocationPayload recommendation slot + to_dict + wire in invoke()
└── task_class_map.py         # NEW — FR-002: action/verb → catalog task_type
src/specify_cli/cli/commands/dispatch.py  # FR-004: _render_rich_payload recommendation line
src/doctrine/agent_profiles/
├── profile.py                # FR-005: optional model/effort field (kebab alias) on AgentProfile
└── schema_models.py          # FR-005: schema source → regenerate agent-profile.schema.yaml
.kittify/charter/charter.md   # FR-006: repoint model_task_routing → model-task-routing token
src/doctrine/model_task_routing/catalog/model-to-task_type.yaml  # FR-008: populated catalog instance, shipped as package data at src/doctrine/model_task_routing/catalog/model-to-task_type.yaml (loader resolves via importlib.resources)

tests/
├── doctrine/test_model_task_routing_loader.py     # FR-001
├── doctrine/test_model_task_routing_evaluator.py  # FR-003/NFR-004 (pure scorer)
├── invocation/test_dispatch_recommendation.py     # FR-004/SC-001 (red-first through dispatch, vary-with-catalog)
├── doctrine/test_task_class_map.py                # FR-002
├── doctrine/test_agent_profile_model_field.py     # FR-005/NFR-003
├── charter/test_model_task_routing_resolves.py    # FR-006/007/SC-003 (load-via-DRG)
└── architectural/test_charter_references_resolve.py  # FR-009 (all-sections invariant)
```

**Structure Decision**: single Python package. Loader + evaluator co-locate with the catalog model under `src/doctrine/model_task_routing/` (doctrine layer owns routing data + logic); the dispatch seam consumes them. The no-dangling invariant is a behavioral architectural test (refactor-stable — parses `→ token` prose, asserts references.yaml resolution).

## Implementation Concern Map

> Concerns, not work packages. `/spec-kitty.tasks` translates these into WPs (expect ~5-6).

### IC-01 — Catalog loader + task-class mapping

- **Purpose**: turn the dead catalog into a loadable, freshness-checked runtime source, and bridge dispatch verbs to catalog task_type vocabulary.
- **Requirements**: FR-001, FR-002; C-002, C-004.
- **Surfaces**: `model_task_routing/loader.py` (new), `invocation/task_class_map.py` (new), `test_no_dead_modules.py:251` allowlist removal.
- **Depends-on**: none (foundation).
- **Risks**: catalog path resolution from activation config; the action→task_type map is a live maintenance seam (must stay in sync with `DEFAULT_ROLE_CAPABILITIES` verbs + the catalog vocabulary). Whole-file-invalid catalog → treated absent (non-fatal).

### IC-02 — Routing evaluator (objective-function scorer)

- **Purpose**: deterministic recommendation from `task_fit` × `weights` under `objective` (quality_first = capability), applying `tier_constraints` + `override_policy` precedence.
- **Requirements**: FR-003, NFR-004; C-004.
- **Surfaces**: `model_task_routing/evaluator.py` (new), pure/stub-testable.
- **Depends-on**: IC-01 (loaded catalog + task_type) + IC-04 (profile field for override precedence).
- **Risks**: precedence semantics under `advisory` must be deterministic (emit both catalog + profile candidates with provenance, enforce neither). Capability expressed via the quality objective — verify the scorer actually ranks strongest-fit for high-judgment task types.

### IC-03 — Advisory payload wiring at the dispatch seam

- **Purpose**: surface the recommendation on `InvocationPayload`, advisory + non-fatal, through `invoke()`.
- **Requirements**: FR-004; NFR-001, NFR-002; C-001.
- **Surfaces**: `executor.py` (`__slots__` slot + `to_dict()` + wire in `invoke()` at ~:196/205/273), `cli/commands/dispatch.py` (`_render_rich_payload`).
- **Depends-on**: IC-01, IC-02.
- **Risks**: must be non-fatal (missing/stale catalog → absent recommendation, dispatch succeeds); red-first must go through `dispatch`/`invoke()` payload (not the model in isolation). Runtime import discipline.

### IC-04 — Agent-profile model/effort field (override anchor)

- **Purpose**: optional per-profile tier declaration that reaches the evaluator.
- **Requirements**: FR-005; NFR-003; C-005.
- **Surfaces**: `profile.py` `AgentProfile` (`preferred_model`/`effort`, kebab-alias field, load-bearing), `schema_models.py` (schema source) + regenerate `agent-profile.schema.yaml`; consumed by the evaluator (IC-02). Note: `router.py` is untouched — the recommendation is computed in `executor.py`, not `router.py` (which does agent-selection only).
- **Depends-on**: none (can co-tenant if ownership disjoint); consumed by IC-02.
- **Risks**: schema-only add is a silent no-op (`extra='ignore'`) — MUST land on `profile.py`. Watch the `model_` protected namespace (alias if needed). Regenerate the schema; never hand-edit the `.yaml`.

### IC-05 — Doctrine artifact + DRG resolution + populated catalog

- **Purpose**: make the charter references real activated doctrine; ship catalog data.
- **Requirements**: FR-006, FR-007, FR-008; C-002.
- **Surfaces**: `model-task-routing.tactic.yaml` (new), `graph.yaml` (tactic node + 2 directive `suggests` edges), `charter.md` (token repoint), the populated catalog instance, `references.yaml`/bundle regeneration.
- **Depends-on**: none for authoring; SC-003 verified once edges land.
- **Risks**: resolution is DRG-driven — a references.yaml row without a `suggests` edge still dangles. The `_LIBRARY`/synthesis-manifest bundle regen is a generated-lockfile step that reds CI if skipped. Kind = tactic (confirmed). Repoint the token (cleaner than minting a snake_case artifact).

### IC-06 — No-dangling-reference invariant

- **Purpose**: durable guard so section-level dangling references cannot recur.
- **Requirements**: FR-009; SC-004.
- **Surfaces**: `tests/architectural/test_charter_references_resolve.py` (new).
- **Depends-on**: IC-05 (goes green once the tokens resolve; red on pre-fix HEAD).
- **Risks**: must be refactor-stable — parse `→ \`token\`` across ALL sections (exclude non-backticked prose), resolve to references.yaml id-suffix; no literal token list pinned.
