# Mission Specification: Planning-artifact WPs Own kitty-specs Paths

**Mission Branch**: `feat/3222-2643-kitty-specs-ownership`
**Created**: 2026-08-18
**Status**: Draft
**Input**: Closes #3222 (primary) and #2643 — narrow the finalize-tasks "owned_files cannot include paths under kitty-specs/" ban so it exempts `execution_mode: planning_artifact` work packages while staying fail-closed for `code_change`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Finalize a planning checkpoint that owns its kitty-specs deliverable (Priority: P1)

A mission author decomposes a mission that includes a first-class planning checkpoint — a decision moment, a freeze/measurement snapshot, or a bulk-edit occurrence map — whose only deliverable lives under the mission's canonical `kitty-specs/<mission>/` directory. They declare the work package as `execution_mode: planning_artifact` and list that deliverable in `owned_files`, then run `finalize-tasks`.

**Why this priority**: This is the defect. Today the author has no legal declaration for such a work package: listing the `kitty-specs/` path is hard-rejected, and emptying `owned_files` fails later at lane computation. The checkpoint cannot be represented in the finalized dependency graph, so it degrades into an undeclared orchestrator handoff — weakening dependency and ownership auditability. Restoring this shape is the whole point of the mission.

**Independent Test**: Author a `planning_artifact` work package owning `kitty-specs/<mission>/disposition-matrix.md`, run `finalize-tasks --validate-only`, and confirm it succeeds and the work package is placed in the planning lane. Delivers value on its own — planning checkpoints become finalizable.

**Acceptance Scenarios**:

1. **Given** a work package with `execution_mode: planning_artifact` whose `owned_files` are all under `kitty-specs/<mission>/`, **When** `finalize-tasks --validate-only` runs, **Then** it completes without error and the work package is assigned to the planning lane.
2. **Given** that same mission, **When** a full (non-validate-only) `finalize-tasks` runs, **Then** it finalizes and lane computation does not raise "has no ownership manifest".
3. **Given** a `planning_artifact` work package owning `kitty-specs/<mission>/` paths together with `docs/` paths, **When** `finalize-tasks` runs, **Then** it is accepted (both are recognized planning surfaces).

---

### User Story 2 - Keep planning artifacts off implementation lanes (Priority: P2)

A maintainer relies on the guarantee that a `code_change` work package — which runs on a `.worktrees/` lane branch that cannot commit `kitty-specs/` — can never declare ownership of a `kitty-specs/` path. Loosening the rule for planning checkpoints must not loosen it here.

**Why this priority**: The ban exists for a real hazard: an implementer discovering a planning-artifact contract conflict only at `move-task`. That protection must remain fail-closed for `code_change`. This guardrail is what makes the P1 change safe rather than a blanket removal.

**Independent Test**: Author a `code_change` work package owning any `kitty-specs/` path and confirm `finalize-tasks` still rejects it with `INVALID_WP_OWNED_FILES_KITTY_SPECS`.

**Acceptance Scenarios**:

1. **Given** a work package with `execution_mode: code_change` that owns a `kitty-specs/` path, **When** `finalize-tasks` runs, **Then** it is rejected with error code `INVALID_WP_OWNED_FILES_KITTY_SPECS` before any write or commit.
2. **Given** a work package with no declared `execution_mode` whose ownership is inferred as `code_change`, **When** it owns a `kitty-specs/` path, **Then** it is still rejected (the exemption is not granted by default).

---

### User Story 3 - Signal, don't block, a mis-scoped planning package (Priority: P3)

A mission author declares a `planning_artifact` work package but lists a deliverable outside the recognized planning surfaces (neither `kitty-specs/` nor `docs/`, e.g. a `scripts/` helper). The author should be nudged, not blocked.

**Why this priority**: Preserves the existing soft-signal behavior so the change is purely additive at this boundary — it neither removes an existing warning nor promotes it to a hard error.

**Independent Test**: Author a `planning_artifact` work package owning a `scripts/` path and confirm `finalize-tasks` still emits the existing "owns files outside planning paths" warning and does not hard-fail on that basis.

**Acceptance Scenarios**:

1. **Given** a `planning_artifact` work package owning a path outside `kitty-specs/`+`docs/`, **When** `finalize-tasks` runs, **Then** a warning is surfaced and finalization is not hard-failed by that condition.

### Edge Cases

- **File-less planning package**: a `planning_artifact` work package that genuinely owns nothing (`owned_files: []`) is **out of scope** — it remains unsupported at lane computation (documented as a tracked follow-up, not fixed here). The supported shape declares at least one real `kitty-specs/`/`docs/` deliverable.
- **Unset execution mode**: a work package that omits `execution_mode` and owns a `kitty-specs/` path is only accepted if ownership inference classifies it as `planning_artifact`; if inferred as `code_change`, it is rejected fail-closed and the author must declare `execution_mode: planning_artifact` explicitly. The rejection message should make that remedy discoverable.
- **Authoritative surface mismatch**: a hand-authored `planning_artifact` work package whose `authoritative_surface` does not prefix its `kitty-specs/` owned file still fails the pre-existing authoritative-surface check; inference normally sets a consistent surface. This check is unchanged.
- **Mislabelled planning package owning code**: a `planning_artifact` work package that owns both a `kitty-specs/` path and a `src/`/`tests/` path is **not** exempted — it is still rejected (confinement, FR-004), so mislabeling cannot become a backdoor to owning code on the repo-root planning lane.
- **Deliverable durability at merge is filename-scoped**: a legitimized `kitty-specs/` deliverable survives lane merges only when its filename is not a rebase-managed kind. Deliverables named `analysis-report.md` or `tasks/WP*.md` are reconciled ("take theirs") by auto-rebase; the durability guarantee holds for non-managed filenames (e.g. `disposition-matrix.md`, `occurrence_map.yaml`) and the managed-kind carve-out is documented and asserted rather than left implicit.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Accept planning-artifact kitty-specs ownership | As a mission author, I want `finalize-tasks` to accept a `planning_artifact` work package that owns `kitty-specs/` deliverables so that decision/measurement checkpoints are first-class. | High | Draft |
| FR-002 | Place accepted planning package in the planning lane | As a mission author, I want an accepted `planning_artifact` work package owning `kitty-specs/` paths to route into the planning lane so that lane computation does not raise "has no ownership manifest". | High | Draft |
| FR-003 | Preserve fail-closed ban for code_change | As a maintainer, I want `kitty-specs/` ownership still rejected (`INVALID_WP_OWNED_FILES_KITTY_SPECS`) for `code_change` work packages so that lane branches never carry planning artifacts. | High | Draft |
| FR-004 | Confine the exemption to planning ownership | As a maintainer, I want the exemption granted only when `execution_mode == planning_artifact` AND every owned file is under a planning surface (`kitty-specs/`/`docs/`), so that a planning-labelled work package that also owns code (`src/`/`tests/`) is still rejected rather than silently permitted to own code. | High | Draft |
| FR-005 | Preserve the out-of-planning-paths warning | As a mission author, I want a `planning_artifact` work package that owns paths outside `kitty-specs/`+`docs/` to still produce a warning (not a hard error) so that mis-scoping is signalled without blocking. | Medium | Draft |
| FR-006 | Reproduction parity | As a maintainer, I want issue #2643's exact reproduction to finalize cleanly, and the same declaration switched to `code_change` to be rejected, so that the fix and its guardrail are both demonstrated. | High | Draft |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No regression to planning-artifact lifecycle | The pre-existing planning-artifact and kitty-specs-ban test suites (`tests/lanes/test_compute_planning_artifact.py`, `tests/integration/test_planning_artifact_wp.py`, `tests/next/test_prompt_builder_unit.py`, the `tests/tasks/` + `tests/agent/` finalize-ban suites, `tests/policy/test_commit_guard.py`) pass at 100% after the change. | Reliability | High | Draft |
| NFR-002 | Clean, contained implementation | Changed source passes `ruff` and `mypy --strict` with zero issues; every changed/added function stays at cyclomatic complexity ≤ 15; no new public API surface is introduced. | Maintainability | High | Draft |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Preserve the predicate seam | The dynamic alias `_invalid_kitty_specs_owned_files` and existing monkeypatch/shim re-export targets must keep resolving unchanged (no rename of the ban predicate's identity). | Technical | High | Draft |
| C-002 | One direction only | The alternative "support `owned_files: []` end-to-end for executable work packages" direction must not be implemented; the fix legitimizes real kitty-specs ownership instead. | Technical | High | Draft |
| C-003 | Deliverable durability (filename-scoped) | `authoritative_surface` inference must cover the kitty-specs owned file (no surface hard-error), and a legitimized `kitty-specs/` deliverable must survive rebase reconciliation **when its filename is not a managed kind** — the managed-kind carve-out (`analysis-report.md`, `tasks/WP*.md`) is asserted by a negative test, not left implicit. | Technical | Medium | Draft |
| C-004 | Scope containment | Scope is limited to #3222 and #2643. #3214 (validators exported but never called) and #3432 (P0, shared lane-computation locus) are out of scope; note the adjacency but do not fold them. | Business | Medium | Draft |

### Key Entities *(include if feature involves data)*

- **Work Package**: a unit of mission work carrying `execution_mode` (`planning_artifact` | `code_change` | codebase-wide), `owned_files`, and an inferred/authored `authoritative_surface`. The execution mode determines its execution surface and which ownership rules apply.
- **Ownership manifest**: the per-work-package record of write scope and execution mode, built from frontmatter and consumed by lane computation.
- **Planning lane vs execution lane**: `planning_artifact` work packages route to the single planning lane that resolves to the repository-root checkout; `code_change` work packages route to execution lanes that resolve to `.worktrees/` branches.
- **Mission specs directory**: `kitty-specs/<mission>/` — the canonical home for a mission's planning deliverables (spec, plan, contracts, decision matrices, occurrence maps).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A `planning_artifact` work package owning only `kitty-specs/<mission>/` (and/or `docs/`) deliverables finalizes with **zero errors** and lands in the planning lane, where the current behavior is a hard rejection.
- **SC-002**: **100%** of the pre-existing planning-artifact and kitty-specs-ban test suites named in NFR-001 remain green after the change.
- **SC-003**: A `code_change` work package owning any `kitty-specs/` path is rejected **100%** of the time with `INVALID_WP_OWNED_FILES_KITTY_SPECS` (fail-closed protection unchanged).
- **SC-004**: Issue #2643's exact reproduction transitions from **rejected → accepted**, while the identical declaration with `execution_mode: code_change` stays **rejected** — both demonstrated by a new regression test that fails on pre-fix code.

## Assumptions

- `planning_artifact` work packages resolve to the repository-root/primary checkout and never to a `.worktrees/` lane branch; the lane commit guard and move-task lane-hygiene guard therefore do not apply to them (verified during research). Exempting their `kitty-specs/` ownership is safe at every lane-scoped guard.
- The `kitty-specs/` ownership shape is already the blessed shape for `planning_artifact` in the ownership consistency validator; this mission aligns `finalize-tasks` to that existing model rather than inventing new semantics.
- Ownership inference sets a consistent `authoritative_surface` for kitty-specs-owning planning packages in the common (non-hand-authored) path.

## Out of Scope

- Supporting a genuinely file-less (`owned_files: []`) executable/planning work package end-to-end (tracked as a follow-up).
- The planning-lane intra-lane overlap behavior of the no-overlap validator (pre-existing; only relevant for parallel planning packages with overlapping scopes).
- Any change to the lane-branch `kitty-specs/` guards addressed separately by the #3271/#2274/#2980 work — a disjoint surface.
- Issues #3214 and #3432 (companion / shared-locus, coordinated separately).
