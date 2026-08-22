# Mission Specification: Project-Tier DRG Node Emission

**Mission Branch**: `spec/project-tier-drg-node-emission`
**Created**: 2026-08-19
**Status**: Draft
**Input**: Charter-resolution program mission **M6** (seed: `docs/plans/charter-resolution/seeds/seed-m6-project-tier-nodes.md`). Closes the **agent_profile half** of issue **#3038**; the asset half stays deferred behind **#3037**. Depends on **M1** (single-authority resolution parity, landed via PR #3588); reuses M1's derive-don't-restate discipline and its totality/parity gate.

## Overview

A project can author its own governance artefacts under `.kittify/doctrine/`. Spec Kitty already **loads and validates** a hand-authored project-tier `agent_profile`, and (post-M1) `DoctrineService` reads it from the project tier. But the project doctrine tier admits only **three** kinds (`directive` / `tactic` / `styleguide`) as **Doctrine Reference Graph (DRG) nodes**, so a hand-authored project-tier `agent_profile` **never becomes a graph node** — it is invisible to the charter **cascade**. The operator sees green health checks while the authored profile silently reaches no dispatched agent.

This is a **kind-admission** defect on a different axis from the recursion/scanning divergence M1 fixed. The fix has two load-bearing halves that must ship together:

1. **Kind-admission** — admit `agent_profile` as a project-tier node kind, expressed as an `ArtifactKind`-keyed mapping that the M1 totality gate can see (closing the string-keyed escape).
2. **Artefact-driven emission** — the current project-DRG emitter is **answer-driven** (it emits nodes only for synthesis interview targets). A profile authored **by hand** produces no interview answer, so extending the kind map **alone** reproduces the defect. A **filesystem-walk** emission path must land the hand-authored profile as a node in the graph file the cascade actually walks (`.kittify/doctrine/graph.yaml` / root-level `*.graph.yaml`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Hand-authored project agent profile reaches the cascade (Priority: P1)

A project maintainer (or a governed agent acting for the project) hand-authors an agent profile under `.kittify/doctrine/agent_profiles/<name>.agent.yaml` to specialise how their project runs missions. They activate it and expect the charter cascade to reach it like any built-in profile.

**Why this priority**: This is the whole mission. Without it, authored project governance loads green but silently reaches no agent — the exact fake-green failure the charter-resolution program exists to close. It is the MVP: on its own it delivers the fix.

**Independent Test**: Author a project-tier `agent_profile` file on disk (no synthesis interview answer), run the project-DRG emission path, and assert the resulting project `graph.yaml` contains a matching `agent_profile:<id>` node. The same assertion is **RED** on the pre-fix base (node absent) and **GREEN** after the fix.

**Acceptance Scenarios**:

1. **Given** a hand-authored `.kittify/doctrine/agent_profiles/reviewer-rhonda.agent.yaml` and **no** matching synthesis interview answer, **When** project-DRG emission runs, **Then** the project overlay graph the cascade walks contains an `agent_profile:reviewer-rhonda` node of kind `agent_profile`.
2. **Given** that emitted node, **When** the charter cascade traverses from an artefact that references it, **Then** the profile node is reachable (no longer cascade-invisible).
3. **Given** the same profile is **not** activated / not present on disk, **When** emission runs, **Then** no such node is emitted (emission tracks the authored files, no phantom nodes).

---

### User Story 2 - Kind-admission is honest and gate-guarded (Priority: P1)

A maintainer extending the doctrine kind system expects the kind→node-kind admission to be a **single, gate-visible authority**, not a hand-copied string map that silently drifts (the #2981 class M1 closed for other tables).

**Why this priority**: The seed and program brief make the totality-gate reconciliation a hard constraint: converting the map to `ArtifactKind`-keyed brings it under M1's totality guard, so a future kind cannot be silently dropped from project-tier admission. Shipping the emitter without this leaves the escape open.

**Independent Test**: The kind→node-kind map is `ArtifactKind`-keyed; the totality suite (`tests/doctrine/drg/test_kind_mapping_totality.py`) treats it as total-or-explicitly-exempt, and the retired string-keyed coverage witness no longer references it. The full totality suite is green.

**Acceptance Scenarios**:

1. **Given** the kind→node-kind map is `ArtifactKind`-keyed, **When** the enum-keyed totality guard scans `src/`, **Then** the map is either total over `ArtifactKind` or listed in the guard's `.get`-partial exemption with a written rationale — never an un-exempted partial.
2. **Given** the map left the string-keyed scan, **When** the totality suite runs, **Then** the string-keyed coverage witness entry for it is removed and no test asserts its discovery as a string map.
3. **Given** a hypothetical future `ArtifactKind` added without an admission decision, **When** the totality guard runs, **Then** it fails loudly (the map is gate-visible) rather than silently omitting the new kind.

---

### User Story 3 - Scope boundaries hold: asset deferred, cascade/org paths untouched (Priority: P2)

A reviewer verifying the mission expects the change to be a clean, explained kind-admission re-ledger for `agent_profile` only — asset stays deferred, and the cascade relation set (M5) and org read-path bridge (M2) are not touched.

**Why this priority**: This mission emits **new** project-tier nodes, so golden DRG counts may legitimately move. The movement must be bounded to `agent_profile` emission and explained, never an accidental ripple from touching adjacent seams.

**Independent Test**: No `asset:*` project node is emitted; the cascade relation set and the org fragment→cascade bridge are byte-unchanged; any golden-fixture movement is attributable solely to `agent_profile` node emission.

**Acceptance Scenarios**:

1. **Given** a hand-authored project-tier `asset` file, **When** emission runs, **Then** no `asset:*` node is emitted (asset stays reference-only, deferred behind #3037).
2. **Given** the mission diff, **When** a reviewer inspects it, **Then** the cascade relation-set definition and the org read-path bridge are unchanged, and every golden-count delta is explained as `agent_profile` emission.

### Edge Cases

- **Malformed project profile file**: a project `agent_profile` file that fails to parse/validate surfaces a **loud** error at emission, never a silent skip (fail-loud thesis; NFR-002).
- **URN collision with a built-in profile**: a project profile whose URN would shadow a built-in `agent_profile` URN is **rejected** additive-only (existing `emit_project_layer` FR-020/EC-6 discipline), not silently overwritten.
- **Profile authored AND also produced by a synthesis answer**: the node is emitted exactly once — no duplicate `agent_profile:<id>` node (overlay-internal duplicate guard).
- **No project profiles on disk**: emission is a no-op for the profile walk; the built-in-only post-condition is unaffected.
- **`procedure` / other non-admitted project kinds present**: unchanged behaviour — not emitted (out of scope; see C-005).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Emit hand-authored project agent profiles as DRG nodes | As a project maintainer, I want a hand-authored project-tier `agent_profile` to become a DRG node so that the charter cascade can reach my authored governance. | High | Open |
| FR-002 | Node lands in the graph the cascade walks | As a project maintainer, I want the emitted profile node written into the project `graph.yaml` / root-level `*.graph.yaml` the cascade reads, so that a mapped-but-ungraphed node cannot stay cascade-invisible. | High | Open |
| FR-003 | Artefact-driven (filesystem-walk) emission | As a project maintainer, I want emission to walk the authored project-tier profile files on disk, so that a profile with **no** synthesis interview answer is still emitted. | High | Open |
| FR-004 | Admit `agent_profile` in the project kind→node-kind mapping | As a doctrine maintainer, I want `agent_profile` admitted as a project-tier node kind via the canonical `ArtifactKind`→`NodeKind` relationship, so that admission derives from the single kind authority rather than a hand-restated string. | High | Open |
| FR-005 | Emission is additive-only and duplicate-safe | As a project maintainer, I want an emitted project profile node to never shadow a built-in URN and to appear at most once, so that overlay emission preserves the existing additive-only invariants. | High | Open |
| FR-006 | Asset emission stays deferred | As a reviewer, I want no `asset:*` project node emitted, so that the asset half stays deferred behind #3037 (asset has no resolution/install path). | High | Open |
| FR-007 | Malformed profile fails loud | As an operator, I want a malformed project `agent_profile` file to raise a loud, file-naming error at emission, so that authoring mistakes are visible instead of silently dropped. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Emission latency | The project-tier profile filesystem walk plus node emission adds no user-perceptible regression; charter emission/context CLI operations stay under the charter budget of **< 2 s** for a typical project (≤ 50 authored project profiles). | Performance | Medium | Open |
| NFR-002 | Fail-closed on malformed input | A project `agent_profile` file that fails schema validation produces a **loud** error naming the file at emission time; **zero** silent skips. | Reliability | High | Open |
| NFR-003 | Zero lint/type debt & no gate escape | New code passes `ruff` and `mypy --strict` with zero issues; the kind→node-kind map is `ArtifactKind`-keyed and covered by the totality gate (no string-keyed escape remains). | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Layering: charter must not import specify_cli | The `charter` package must derive its kind vocabulary only from `doctrine.artifact_kinds` (`ArtifactKind` / `PROJECT_KIND_DIRS`); it must not import `specify_cli`. | Technical | High | Open |
| C-002 | Derive, don't restate (M1 discipline) | Node-kind admission derives from the canonical `ArtifactKind`↔`NodeKind` superset relationship; the map is a gate-visible authority, and the retired string-keyed coverage witness is removed atomically. | Technical | High | Open |
| C-003 | Bounded golden re-ledger | Any golden DRG fixture / count movement is attributable **solely** to `agent_profile` node emission and is explained; no cascade relation-set change (M5) and no org read-path bridge change (M2). | Technical | High | Open |
| C-004 | Red-first / ATDD | A failing-first test proves a hand-authored project-tier `agent_profile` is cascade-**invisible** on the pre-fix base and reaches the project `graph.yaml` after the fix (committed before implementation). | Process | High | Open |
| C-005 | Scope: agent_profile only | Only project-tier `agent_profile` emission is in scope. `asset` stays deferred (#3037); project-tier `procedure` node emission is a deliberate out-of-scope boundary (record any residual gap as a follow-up, do not fix here). | Technical | High | Open |

### Key Entities

- **Project-tier agent_profile artefact**: a hand-authored `*.agent.yaml` under the project overlay (`.kittify/doctrine/agent_profiles/`). Loaded and validated today, but not graphed.
- **DRG node (`agent_profile:<id>`)**: an addressable Doctrine Reference Graph node of `NodeKind.AGENT_PROFILE`. Its presence in the project graph is what makes an artefact cascade-reachable.
- **Project overlay graph (`graph.yaml`)**: the project-tier `graph.yaml` (`.kittify/doctrine/graph.yaml`) / root-level `*.graph.yaml` that the charter cascade traversal reads. A node that never reaches this file stays cascade-invisible.
- **Kind→node-kind admission map**: the mapping that decides which project-tier artefact kinds become nodes and of what `NodeKind`. Today `charter.synthesizer.project_drg._KIND_TO_NODE_KIND`, string-keyed and 3-kind partial.
- **Totality gate**: `tests/doctrine/drg/test_kind_mapping_totality.py`, extended in M1, which enforces total-or-exempt on kind-keyed maps and currently carries a string-keyed coverage witness for this map.

### Domain Language *(overloaded-term discipline)*

- **cascade** — here means the charter activation/reference **cascade** traversal that walks the DRG (`charter activate --cascade`), not sync fan-out or any routing sense.
- **project tier** — the project-local doctrine overlay under `.kittify/doctrine/`, distinct from built-in (`packs/built-in/`) and org packs.
- **emit / emission** — producing a DRG **node** and writing it into the graph document; distinct from *load* (read + validate into memory) and *activate* (turn on as a live rule).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A hand-authored project-tier `agent_profile` file with no synthesis answer yields exactly **one** `agent_profile:<id>` node in the project graph the cascade reads — a measured **0 → 1** transition versus the pre-fix base.
- **SC-002**: The kind→node-kind map is `ArtifactKind`-keyed and total-or-exempt under the totality gate; the string-keyed coverage witness for it is removed; the full `test_kind_mapping_totality.py` suite and the DRG test package pass.
- **SC-003**: Zero `asset:*` project nodes are emitted; the cascade relation-set definition and the org read-path bridge are byte-unchanged in the mission diff.
- **SC-004**: Every golden DRG fixture / count delta in the diff is explained in the mission notes as attributable to `agent_profile` emission — no unexplained ripple.
- **SC-005**: A malformed project `agent_profile` file produces a loud, file-naming error at emission (demonstrated by a test), with zero silent skips.
