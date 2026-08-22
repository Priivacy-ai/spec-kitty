# Mission Specification: DRG Read-Path Bridge

**Mission Branch**: `spec/charter-resolution-parity`
**Created**: 2026-08-19
**Status**: Draft
**Input**: Second enabling mission of the charter-resolution program (rolls up to reach epic #3530). Closes #3572, #3573.

## Overview

An org pack can declare `requires`/`suggests` dependency edges in its canonical `drg/fragment.yaml` (the `OrgDRGFragment` shape established by #3387). Those edges are parsed **only** by a separate diagnostic path (`doctor doctrine` / `charter list`) and are **never bridged into the graph that charter cascade walks** — which reads root-level `*.graph.yaml` only. So activating an artifact silently cascades nothing for any org-authored dependency, even though diagnostics show the edge as present. A companion validator (`drg_root_graph_missing`) globs `*.graph.yaml` and never flags a `fragment.yaml`-only pack, so `pack validate` exits 0 on the same silent gap.

This mission bridges org `drg/fragment.yaml` edges into the cascade graph via the existing merge machinery, re-scopes the graphless-pack warning so it fires only when a pack ships **no** dependency graph in **any** form, and flips the validator and its pinning regression test **atomically** so the tool never simultaneously says "this edge won't cascade" while cascading it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Org fragment edges drive cascade (Priority: P1)

An operator activates an artifact from an org pack whose `requires`/`suggests` edges live in `drg/fragment.yaml`, and expects `--cascade` to reach the declared dependencies.

**Why this priority**: This is the core defect (#3572). Org-authored dependency governance is currently inert at activation time. Every downstream reach mission that depends on org-authored edges (M3, M4) is blocked until this bridge exists.

**Independent Test**: Author an org pack declaring `A --requires--> B` **only** in `drg/fragment.yaml`; activate A with `--cascade`; assert B is cascade-activated.

**Acceptance Scenarios**:

1. **Given** an org pack with `A requires B` authored only in `drg/fragment.yaml`, **When** A is activated with `--cascade`, **Then** B is cascade-activated (the fragment edge is walked).
2. **Given** a healthy pack A and a second pack B in the chain, **When** the merged graph is built, **Then** fragment edges are canonicalised and de-duplicated by the same machinery the diagnostic path already uses (no double-counting, endpoints resolved).
3. **Given** the existing `TestGraphlessPackWithFragmentEdgeIsInvisibleToCascade` regression, **When** the bridge lands, **Then** that test is flipped to assert the edge **does** cascade.

### User Story 2 - The graphless-pack warning stays honest (Priority: P1)

An operator with an org pack that ships a `drg/fragment.yaml` should not be warned that the pack "contributes no dependency graph."

**Why this priority**: The D-005 graphless-degrade warning added during the #3534 landing fires for any pack with no root-level `*.graph.yaml`. Once fragments cascade, a fragment-bearing pack is no longer graphless — warning it would be a lie.

**Independent Test**: A pack with only `drg/fragment.yaml` produces **no** graphless warning; a pack with neither a root graph nor a fragment still warns.

**Acceptance Scenarios**:

1. **Given** a pack shipping only `drg/fragment.yaml`, **When** the graph loads, **Then** no graphless warning fires and its edges cascade.
2. **Given** a pack shipping neither a root graph nor a fragment, **When** the graph loads, **Then** the graphless warning still fires (degrade path preserved).

### User Story 3 - `pack validate` and the runtime tell one story (Priority: P2)

A pack author runs `pack validate` and the result matches what the runtime actually does with `drg/fragment.yaml`.

**Why this priority**: #3573 — today `pack validate` never flags a `fragment.yaml`-only pack; its silence is only "correct" while the runtime can't read fragments. When the runtime starts reading them, the validator's premise inverts, so the two must change together.

**Independent Test**: With the bridge in place, `pack validate` on a `fragment.yaml`-only pack no longer reports it as uncascaded/unread.

**Acceptance Scenarios**:

1. **Given** the bridge landed, **When** `pack validate` runs on a `fragment.yaml`-only pack, **Then** the validator does not claim the DRG "will not be read" (the check is inverted or removed in the same change).

### Edge Cases

- A pack declaring the **same** edge in both a root `*.graph.yaml` and `drg/fragment.yaml` → deduplicated to one edge (existing collector identity), no double-activation.
- A fragment edge whose endpoint resolves to no node → surfaced by the existing endpoint-resolution/validation, not silently dropped.
- A malformed `drg/fragment.yaml` → fails loud via the existing fragment parse/schema errors, not swallowed.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Bridge org fragment edges into cascade | As an operator, I want `requires`/`suggests` edges authored in an org pack's `drg/fragment.yaml` to be present in the graph charter cascade walks, so that activating an artifact cascades its org-authored dependencies. | High | Open |
| FR-002 | Reuse existing merge/dedup machinery | As a maintainer, I want fragment edges bridged through the same endpoint-resolution and de-duplication path the diagnostic merge already uses, so that edge canonicalisation is not re-implemented. | High | Open |
| FR-003 | Build-time callers stay inert | As a maintainer, I want charter-build-time callers that pass no org roots to remain unaffected, so that the bridge is purely additive to runtime cascade. | High | Open |
| FR-004 | Re-scope the graphless warning | As an operator, I want the graphless-pack warning to fire only when a pack ships neither a root graph nor a `drg/fragment.yaml`, so that a fragment-bearing pack is not falsely warned. | High | Open |
| FR-005 | Flip the pinning regression test | As a maintainer, I want `TestGraphlessPackWithFragmentEdgeIsInvisibleToCascade` updated to assert the fragment edge cascades, so that the mission's own regression proves the new behavior. | High | Open |
| FR-006 | Reconcile the validator (#3573) | As a pack author, I want `pack validate`'s fragment-related finding inverted or removed in the same change that makes the runtime read fragments, so that validation and runtime never contradict each other. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No diagnostic-path regression | The diagnostic merge consumers (`doctor doctrine`, `charter list`, lint/status collectors) produce identical output before and after the bridge; the bridge adds a consumer, it does not change the diagnostic path. | Reliability | High | Open |
| NFR-002 | Deterministic golden re-ledger | Any change in cascade reach caused by newly-visible fragment edges is captured in a single, reviewed golden-count update; no unexplained count drift. | Correctness | High | Open |
| NFR-003 | Atomic validator/runtime flip | The validator finding and the runtime bridge land in the same change; at no commit does `pack validate` state a claim the runtime contradicts. | Correctness | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Fold #3573 into this mission (decision) | #3573 (validator fragment-awareness) is resolved **inside** this mission so the validator and runtime flip atomically, not as a standalone check that would become a lie the moment the bridge lands. | Technical | High | Open |
| C-002 | Reuse, don't re-implement | The bridge routes through the existing `OrgDRGFragment` merge machinery; it must not fork a second edge-canonicalisation/dedup implementation. | Technical | High | Open |
| C-003 | Preserve the degrade posture | The D-005 "degrade, never silent" behavior for genuinely graphless packs is preserved; only its trigger condition narrows. | Technical | High | Open |
| C-004 | Scope boundary | Cascade traversal completeness (relation set / kind-complete cascade, #2829) is **out of scope** — this mission only makes fragment `requires`/`suggests` edges visible through the existing followed relations. | Technical | High | Open |
| C-005 | Zero new suppressions; layer boundary | New code passes `ruff` + `mypy --strict` with zero suppressions; `charter` must not import `specify_cli` (the runtime caller supplies the resolved fragments). | Technical | High | Open |

### Key Entities

- **OrgDRGFragment**: the `drg/fragment.yaml` unit carrying an org pack's nodes and `requires`/`suggests`/… edges.
- **Cascade graph**: the merged, validated DRG that charter cascade walks (today: built-in + root-level `*.graph.yaml` + project overlay).
- **Merge/dedup machinery**: the existing endpoint-resolution + edge-identity path used by the diagnostic three-layer merge.
- **Graphless-pack warning**: the D-005 degrade signal whose trigger this mission narrows.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Activating an artifact whose org-pack dependency edge lives only in `drg/fragment.yaml` cascades that dependency — **0 silently-dropped org fragment edges**.
- **SC-002**: A `fragment.yaml`-only pack produces **no** graphless warning; a pack with no dependency graph in any form still warns.
- **SC-003**: `pack validate` and the runtime agree on `fragment.yaml` handling — **no** contradictory validator finding after the bridge.
- **SC-004**: Diagnostic-path output (`doctor doctrine` / `charter list`) is unchanged; any cascade-reach delta is captured in one reviewed golden update.

## Assumptions & Dependencies

- **Enabling for M3/M4:** the reach missions' *org-authored* acceptance depends on this bridge; sequence M3/M4 org acceptance after this mission (their built-in/project reach can proceed independently).
- The existing three-layer merge already owns endpoint resolution and cross-fragment edge dedup — this mission reuses it rather than re-implementing.
- Independent of M1 (single-authority resolution parity); the two enabling missions can land in either order.

## Technical Context *(non-normative — informs planning, not acceptance)*

Seams surfaced by the charter-resolution investigation (against `main` @ post-#3534):

- **Bridge point:** `charter/_drg_helpers.py::load_validated_graph` currently folds only root-level `*.graph.yaml` via `merge_layers`. Route the org layer through `doctrine/drg/merge.merge_three_layers(built_in, org_fragments, project)`; add an `org_fragments` param populated by `specify_cli` runtime callers via `charter.drg.load_org_drg(repo_root)` alongside the `org_roots` they already resolve.
- **Warning re-scope:** the D-005 branch in `load_validated_graph` (added #3534) — narrow its trigger to "neither root graph nor `drg/fragment.yaml`."
- **Test flip:** `tests/specify_cli/cli/commands/charter/test_org_cascade_chain.py::TestGraphlessPackWithFragmentEdgeIsInvisibleToCascade`.
- **Validator (#3573):** `src/specify_cli/doctrine/pack_validator.py` `_check_drg_root_graph_missing` (~L667-688).

This section is guidance; the normative contract is the FR/NFR/C tables above.
