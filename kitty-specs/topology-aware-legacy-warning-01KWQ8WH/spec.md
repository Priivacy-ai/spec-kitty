# Mission Specification: Topology-Aware Legacy Warning

**Mission Branch**: `fix/topology-aware-legacy-warning`
**Created**: 2026-07-04
**Status**: Draft
**Input**: GitHub issue #2351 (bug) — the once-per-mission legacy-topology warning over-fires on intentional coordination-less (`single_branch`/`lanes`) missions because `_is_legacy_mission()` keys on `coordination_branch` absence instead of the stored `MissionTopology`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Coordination-less mission is not falsely called "legacy" (Priority: P1)

An operator creates or runs a mission whose topology is intentionally coordination-less (`single_branch` or `lanes`). Per #2218 these shapes deliberately never write a `coordination_branch`. Today the bookkeeping transaction warns "mission uses the legacy topology (no coordination branch)" and points them at a migration runbook for a migration they do not need. This mission removes that false warning by making the classification read the stored topology.

**Why this priority**: This is the reported defect and the daily friction — legitimate in-flight configurations told to migrate. Without this the mission delivers nothing.

**Independent Test**: create/simulate a mission whose `meta.json` carries `topology: single_branch` (and `lanes`) with no `coordination_branch`, run the bookkeeping seam, and confirm **no** legacy warning is emitted and bookkeeping still routes correctly.

**Acceptance Scenarios**:

1. **Given** a mission with stored `topology: single_branch` and no `coordination_branch`, **When** the bookkeeping transaction runs, **Then** no legacy-topology warning is emitted and no migration pointer is shown.
2. **Given** a mission with stored `topology: lanes` and no `coordination_branch`, **When** the bookkeeping transaction runs, **Then** no legacy-topology warning is emitted.

---

### User Story 2 - Genuinely legacy missions are still warned (Priority: P1)

An operator runs a genuinely pre-SSOT mission: `meta.json` has **no** stored `topology` **and** no `coordination_branch` (never backfilled). They must still receive the once-per-mission warning, pointing at both the migration runbook and `spec-kitty migrate backfill-topology`.

**Why this priority**: The warning has a real job — narrowing it must not silence the case it exists for. Over-correcting into silence would hide real legacy state.

**Independent Test**: with a `meta.json` lacking both `topology` and `coordination_branch`, run the seam and confirm the warning still fires exactly once with the migration + backfill pointers.

**Acceptance Scenarios**:

1. **Given** a mission with no stored `topology` and no `coordination_branch`, **When** the bookkeeping transaction runs, **Then** the legacy warning fires once, citing the migration runbook and `spec-kitty migrate backfill-topology`.

---

### User Story 3 - Flattened missions are not called legacy (Priority: P2)

An operator runs a mission carrying the `flattened` provenance flag (a deliberate was-coordinated-now-branch-dropped shape). This is distinct from legacy and from create-time coordination-less shapes; it must not draw the legacy warning.

**Why this priority**: The ADR frames `flattened` as a separate provenance; collapsing it into "legacy" is the same class of misclassification as US1.

**Independent Test**: with a `flattened` provenance flag set (and no `coordination_branch`), run the seam and confirm no legacy warning.

**Acceptance Scenarios**:

1. **Given** a mission with the `flattened` provenance flag set, **When** the bookkeeping transaction runs, **Then** no legacy-topology warning is emitted.

---

### Edge Cases

- **Pre-backfill legacy**: no `topology`, no `coordination_branch` → warn (US2).
- **Malformed / unknown `topology` value**: a stored value that is neither a recognized shape nor absent → must not crash; the resolution (warn vs. treat as a chosen shape) is pinned during plan against the SSOT type.
- **Coordinated mission** (`topology: coord`, has `coordination_branch`) → no warning (unchanged; never warned).
- **`lanes_with_coord`** (the fourth enum member; carries a `coordination_branch`) → no warning (unchanged).
- **Warning cadence**: whatever the classification, the warning still fires at most once per mission.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Topology-aware classification | As an operator, I want the legacy warning to read the stored `MissionTopology` from `meta.json`, so classification reflects the chosen shape rather than a proxy signal. | High | Open |
| FR-002 | No warning for coordination-less shapes | As an operator on a `single_branch`/`lanes` mission, I want no legacy warning or migration pointer, so I am not told to migrate a legitimate configuration. | High | Open |
| FR-003 | No warning for flattened provenance | As an operator on a `flattened` mission, I want no legacy warning, so a deliberate flatten is not mislabeled legacy. | Medium | Open |
| FR-004 | Genuine legacy still warns | As a maintainer, I want a mission with no stored `topology` and no `coordination_branch` to still warn (migration runbook + `backfill-topology`), so real legacy state stays visible. | High | Open |
| FR-005 | Write-path routing unchanged | As a maintainer, I want the bookkeeping write-path routing (which correctly keys coordination-less shapes on `coordination_branch` absence) to remain unchanged, so only the classification/warning changes. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Once-per-mission cadence preserved | The warning, when it does fire, still emits at most once per mission (no change to emission cadence). | Reliability | Medium | Open |
| NFR-002 | Quality gate | New/changed code passes `mypy --strict` and `ruff` with zero issues and no new suppressions; every new classification branch is covered by a focused test. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Read the SSOT via the canonical reader | Classification reads the stored `MissionTopology` from `meta.json` (the SSOT per `docs/adr/3.x/2026-06-22-1-mission-topology-ssot.md`) by consuming the **existing canonical reader `stored_topology_from_meta`** (`src/specify_cli/missions/_read_path_resolver.py`) plus the canonical `flattened` key — NOT a fresh inline `meta.json` parse inside `transaction.py`. Exact readers are pinned in plan. It must NOT re-introduce a `coordination_branch is None` topology-inference site (ADR SC-001 requires zero live such sites). | Technical | High | Open |
| C-002 | Narrow only the warning | Keep the write-path routing keyed on `coordination_branch` absence (correct for coordination-less shapes); change only the warning-classification trigger. | Technical | High | Open |
| C-003 | Coupled runbook update | Update the "two neighbouring states are not legacy" paragraph in `docs/migrations/legacy-to-coordination.md` so it no longer describes a warning that will no longer fire for `single_branch`/`lanes`. | Documentation | High | Open |
| C-004 | Terminology guard | Doctrine/prose changes must pass `tests/architectural/test_no_legacy_terminology.py` and the terminology canon. | Technical | Medium | Open |
| C-005 | Do not repurpose the shared routing predicate | `_is_legacy_mission()` is a SHARED predicate that also drives worktree routing (`transaction.py:~719-729`) and write-contract selection (`~:909`, `self._legacy_mode`). Keep it **unchanged**. Introduce a SEPARATE warning-only classifier for the topology-aware decision and re-point only `_emit_legacy_warning_once()` at it, so routing/write-contract for `single_branch`/`lanes` missions is provably unaffected (FR-005). | Technical | High | Open |

### Key Entities

- **`MissionTopology`**: the stored SSOT shape enum with **four** members — `single_branch`, `lanes`, `coord`, `lanes_with_coord` (the latter two carry a `coordination_branch` and never warn). `flattened` is a **separate provenance flag**, not an enum member. All read from `meta.json`.
- **`coordination_branch`**: a per-mission field written only for coordinated shapes; its absence is a routing signal, **not** a legacy signal.
- **`_is_legacy_mission()`**: a SHARED predicate in `src/specify_cli/coordination/transaction.py` driving THREE things — worktree routing (`~:719-729`), write-contract selection (`~:909`), and the warning (`~:730`). Keyed on `coordination_branch` absence; **stays unchanged** (routing/write-contract must not shift — FR-005/C-002/C-005). It is **not** the surface to change.
- **New warning-only classifier** (to add): a topology-aware function reading the stored `MissionTopology` (via `stored_topology_from_meta`) + the `flattened` flag, deciding *only* whether the warning fires.
- **`_emit_legacy_warning_once()`**: the once-per-mission emitter; its trigger is switched from `_is_legacy_mission()` to the new warning-only classifier.
- **`legacy-to-coordination.md` runbook**: the migration doc the warning cites; its "not legacy" paragraph is coupled to this trigger.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `single_branch`, `lanes`, and `flattened` missions emit **zero** legacy-topology warnings.
- **SC-002**: a mission with no stored `topology` and no `coordination_branch` still emits the warning exactly once, with migration + backfill pointers.
- **SC-003**: no `coordination_branch is None` topology-inference site is reintroduced (a grep for that pattern on the changed seam finds zero live decision sites, per ADR SC-001).
- **SC-004**: the `legacy-to-coordination.md` "not legacy" paragraph matches the new behavior.
- **SC-005**: `mypy --strict` + `ruff` clean; each new classification branch covered by a focused test.

## Assumptions

- The canonical trigger (from the debugger-debbie squad refinement recorded on the issue) is: warn only when `coordination_branch` is absent **AND** stored `topology` is null/absent **AND** `flattened` is not set. Plan verifies this against the live `_is_legacy_mission` seam and the `MissionTopology` type.
- Handling of malformed/unknown `topology` values is deferred to plan (pin against the SSOT enum): the default leans toward *not* warning when an affirmative stored shape is present, and warning only on genuinely absent/legacy metadata.
- Write-path routing **and** write-contract selection both flow through the shared `_is_legacy_mission()` predicate; the issue confirms routing is correct. This mission keeps that predicate unchanged and adds a separate warning-only classifier (C-005), so routing/write-contract are provably untouched.
