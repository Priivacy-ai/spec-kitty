# Execution-State Domain Remediation — #1619 Strangler Fig

**Mission ID:** 01KT6HVH3QND4Q3KCGH2419N4J  
**Mission Slug:** execution-state-domain-remediation-01KT6HVH  
**Mission Type:** software-dev  
**Target Branch:** main  
**Status:** Draft

---

## Purpose

**TL;DR:** Eliminate CWD-dependent execution-context re-derivation across ~40 command surfaces by establishing authoritative domain boundaries and routing all surfaces through a single canonical resolver.

The spec-kitty runtime has accumulated ~40 command surfaces that independently re-derive execution context (workspace path, feature dir, branch), causing divergent behavior when the same command is invoked from the main checkout versus a lane worktree. Prior symptom fixes (#1615, #1616, #1617, #1618, #1627) treated individual surfaces without installing a single domain owner. This mission implements the complete Strangler Fig sequence documented in #1619 and ratified in #1666: lock the domain model in ADRs, build an e2e parity ratchet to gate all changes, introduce `MissionStatus` as the authoritative status owner, enforce the `status/` module boundary, add mission identity back-references to run snapshots, and route all residue path-building surfaces through `resolve_action_context`.

---

## Source Issues

| Issue | Title | Role in sequence |
|-------|-------|-----------------|
| #1674 | ADRs: domain model, ExecutionContext owner, Effector/Actor | Gate — must land before implementation |
| #1672 | e2e parity ratchet | Strangler step 1 — gates all subsequent steps |
| #1664 | `status/` public API enforcement | Strangler step 2a |
| #1667 | `MissionStatus` aggregate | Strangler step 2b |
| #1663 | `MissionRun → Mission` back-reference | Strangler step 2c (parallelizable) |
| #1673 | ExecutionContext hardening — route residue surfaces | Strangler step 3 |

---

## User Scenarios & Testing

### Scenario A — CWD-invariant status query

**Actor:** spec-kitty agent or developer  
**Trigger:** Invokes `spec-kitty agent status WP01 --mission <slug>` or `spec-kitty next` from two different working directories: (1) main checkout root, (2) the lane worktree for the active WP.  
**Expected outcome:** Both invocations return identical resolved WP identity, lane state, and status output.  
**Exception path:** If invocation from the lane worktree previously returned stale or wrong data, the ratchet test would catch it and fail CI.

### Scenario B — Status module boundary violated by a new import

**Actor:** Developer adds a new file that imports `from specify_cli.status.emit import build_status_event` directly.  
**Trigger:** CI runs the architectural boundary test.  
**Expected outcome:** Test fails with a clear message identifying the violation and instructing the developer to use `from specify_cli.status import ...` instead.

### Scenario C — Mission run identity lookup

**Actor:** spec-kitty runtime component holding a `MissionRunSnapshot`  
**Trigger:** Needs to resolve which concrete mission a run belongs to without an external index scan.  
**Expected outcome:** The snapshot's `mission_id` and `mission_slug` fields provide the back-reference directly. Existing on-disk `state.json` files with no `mission_id` field load without error (fields default to `None`).

### Scenario D — Status read from coord-topology mission, coord unavailable

**Actor:** spec-kitty agent invoking `MissionStatus.load()` for a coord-topology mission  
**Trigger:** Coord authority path is unavailable (network or worktree missing).  
**Expected outcome:** Fails closed with a clear error — does not silently fall back to a stale primary-checkout read.

### Scenario E — Legacy mission unaffected after remediation

**Actor:** Developer working on a pre-coord-topology (legacy) mission  
**Trigger:** Runs any status command or implements a WP.  
**Expected outcome:** All legacy mission paths continue to work; no behavioral regression.

---

## Functional Requirements

### ADR Gate (#1674)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | ADR 1 (`2026-06-03-1-execution-state-domain-model.md`) exists in `architecture/3.x/adr/` recording the four-bounded-module domain model, status ownership by Mission Management, context per-domain, and keeper invariants (Mission ≠ MissionRun) | Proposed |
| FR-002 | ADR 2 (`2026-06-03-2-executioncontext-owner-and-committarget.md`) exists in `architecture/3.x/adr/` recording `resolve_action_context` as the canonical OHS entry point and the `CommitTarget` atomicity decision | Proposed |
| FR-003 | ADR 3 (`2026-06-03-3-effector-actor-model.md`) exists in `architecture/3.x/adr/` recording Effector as a named concept in docs only (no code type until a concrete actor-kind-mismatch bug triggers materialization) | Proposed |
| FR-004 | Glossary entries for GovernanceContext, ExecutionContext, InfraContext, Effector, and communication-artefact are added or updated in the project glossary | Proposed |
| FR-005 | All three ADR files are merged to `main` before any implementation PR for #1663, #1664, #1667, or #1673 is merged | Proposed |

### e2e Parity Ratchet (#1672)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-006 | An integration or architectural test exists in `tests/` covering the full `next → implement → move-task → review → status` command sequence | Proposed |
| FR-007 | The ratchet test exercises both invocations: (a) from main-checkout CWD and (b) from the lane worktree CWD | Proposed |
| FR-008 | The ratchet test asserts that resolved WP identity, lane state, and status output are identical between both CWD invocations | Proposed |
| FR-009 | The ratchet test is registered in CI and is required to pass for every PR touching execution-context resolution | Proposed |
| FR-010 | The ratchet test fails when a surface re-derives context independently (i.e., it catches real regressions, not just structural presence) | Proposed |

### `status/` Module Boundary (#1664)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-011 | An architectural boundary test in `tests/architectural/` enforces that no code outside `src/specify_cli/status/` imports any `status.*` submodule directly (only `from specify_cli.status import ...` is permitted) | Proposed |
| FR-012 | All ~245 existing direct submodule imports of `status.*` from outside `status/` are fixed: symbols that have genuine external consumers are promoted to the `status/__init__.py` public API; symbols with no external consumers are renamed private with a `_` prefix | Proposed |
| FR-013 | No new direct submodule imports of `status.*` are introduced outside `status/` after this mission lands | Proposed |
| FR-014 | `coordination/status_transition.py` (which is internal domain plumbing) may continue to import `status/` internals; the boundary test must correctly identify it as an internal caller and exempt it | Proposed |

### `MissionStatus` Aggregate (#1667)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-015 | `ActiveWPStatus` dataclass exists in `src/specify_cli/status/` with fields `wp_id: str`, `current_lane: Lane`, and `last_event: StatusEvent | None` | Proposed |
| FR-016 | `MissionStatus` frozen dataclass exists in `src/specify_cli/status/` with fields `mission_slug`, `mission_id`, `mid8`, `topology` (literal `"legacy"` or `"coordination"`), and `read_dir` | Proposed |
| FR-017 | `MissionStatus.load(repo_root, mission_slug)` resolves topology exactly once and returns the authoritative status aggregate | Proposed |
| FR-018 | `MissionStatus.claim(wp_id)` returns `ActiveWPStatus` with the correct lane from the coord-aware read path | Proposed |
| FR-019 | `MissionStatus.transition(request)` validates the lane transition and applies it, calling `BookkeepingTransaction` internally; callers do not call `BookkeepingTransaction` directly | Proposed |
| FR-020 | `MissionStatus.save(operation=...)` persists staged transitions via `BookkeepingTransaction` and returns a `CommitReceipt` from `coordination/types.py` | Proposed |
| FR-021 | Coord-topology missions where the coord authority path is unavailable fail closed rather than silently falling back to a stale primary-checkout read | Proposed |
| FR-022 | `cli/commands/agent/status.py` no longer constructs raw `main_repo_root / "kitty-specs" / mission_slug` paths; it uses `MissionStatus.load()` and `MissionStatus.claim()` instead | Proposed |
| FR-023 | Domain lane-transition invariants (currently in `status/transitions.validate_transition()`) are enforced by the aggregate, not by `BookkeepingTransaction` | Proposed |

### `MissionRun → Mission` Back-Reference (#1663)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-024 | `MissionRunSnapshot` gains optional `mission_id: str | None` and `mission_slug: str | None` fields, defaulted so existing on-disk `state.json` files load without error | Proposed |
| FR-025 | `MissionRunRef` gains optional `mission_id: str | None` and `mission_slug: str | None` fields with the same backward-compat defaults | Proposed |
| FR-026 | `start_mission_run` in `engine.py` plumbs `mission_id` (read from `meta.json` via `_resolve_mission_ulid`) and `mission_slug` into the snapshot at run creation | Proposed |
| FR-027 | All ~6 in-engine snapshot-copy sites that reconstruct `MissionRunSnapshot` carry the new fields through (no silent field drop) | Proposed |
| FR-028 | The `feature-runs.json` write site in `runtime_bridge.py` is updated to include `mission_id` and `mission_slug` | Proposed |
| FR-029 | An additive on-disk legacy migration handles existing `state.json` files that predate these fields, backfilling `None` without error | Proposed |
| FR-030 | The previously write-only `inputs["mission_slug"]` in `engine.py:216` is either wired to the new field or removed as dead code | Proposed |

### ExecutionContext Hardening (#1673)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-031 | No surface outside `core/execution_context.py` and `src/specify_cli/status/` constructs `main_repo_root / "kitty-specs" / mission_slug` (or equivalent path) directly | Proposed |
| FR-032 | `runtime_bridge` query-mode derives `feature_dir` through `resolve_action_context` rather than constructing it independently from the mission slug | Proposed |
| FR-033 | `workflow.py` fix-mode routes its `repo_root` / `target_branch` resolution through `resolve_action_context` rather than resolving independently | Proposed |
| FR-034 | Duplicated path-builder functions that are made unreachable by this work are deleted from the codebase (not left as dead code) | Proposed |
| FR-035 | The e2e parity ratchet (#1672) remains green throughout and after all ExecutionContext hardening changes | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Legacy mission backward-compatibility: all pre-coord-topology missions work without modification after remediation | Zero behavioral regressions on existing integration test suite | Proposed |
| NFR-002 | `MissionRunSnapshot` backward-compatibility: on-disk `state.json` files missing `mission_id`/`mission_slug` load without raising an exception | 100% of existing on-disk files load cleanly | Proposed |
| NFR-003 | `BookkeepingTransaction` isolation: the aggregate calls `BookkeepingTransaction` internally; no change is made to `BookkeepingTransaction` internals | Zero changes to `coordination/transaction.py` | Proposed |
| NFR-004 | CI gate: the e2e ratchet test runs on every PR that touches any file under `src/specify_cli/core/execution_context.py`, `src/specify_cli/status/`, `src/runtime/next/`, or `src/specify_cli/cli/commands/agent/` | 100% CI coverage for targeted paths | Proposed |
| NFR-005 | Import boundary test performance: the architectural boundary scan for `status/` completes in under 10 seconds on the full `src/` tree | ≤10 s wall-clock in CI | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | ADR files (#1674) must be merged to `main` before any implementation PR for #1663, #1664, #1667, or #1673 is merged — DIRECTIVE_032 requires vocabulary ratification before code | Accepted |
| C-002 | The e2e parity ratchet (#1672) must exist and be green before #1664, #1667, or #1673 can be considered complete; it is Strangler step 1 and gates all subsequent steps | Accepted |
| C-003 | `MissionStatus` aggregate (#1667) should land before or concurrently with #1673, because #1667 handles `agent/status.py` and #1673 handles the broader residue — landing order matters for test coverage | Accepted |
| C-004 | `BookkeepingTransaction` internals (`coordination/transaction.py`) must not be modified as part of this mission | Accepted |
| C-005 | The external `MissionRunStartedPayload` event type in `spec_kitty_events` is out of scope for the #1663 fix — only `MissionRunSnapshot` and `MissionRunRef` in `src/runtime/next/` are changed | Accepted |
| C-006 | `mission_number` must not be used as a selector or identity anywhere in the new or modified code; all lookup is by `mission_id` (ULID) or `mission_slug` | Accepted |
| C-007 | ADRs must follow the existing naming convention and format in `architecture/3.x/adr/` (e.g., `2026-06-03-N-<kebab-title>.md` with Status/Context/Decision/Consequences sections) | Accepted |
| C-008 | The `coordination/status_transition.py` module is internal domain plumbing; it is correct for it to import `status/` internals and must be exempted (not fixed) by the boundary enforcement test | Accepted |

---

## Key Entities

| Entity | Description |
|--------|-------------|
| `MissionStatus` | New aggregate root in `src/specify_cli/status/` — owns the status read path and write path for a given mission |
| `ActiveWPStatus` | Read projection returned by `MissionStatus.claim()` — current lane state for a single WP |
| `MissionRunSnapshot` | Existing schema in `src/runtime/next/_internal_runtime/schema.py` — gains optional `mission_id` + `mission_slug` |
| `MissionRunRef` | Existing struct in `src/runtime/next/_internal_runtime/engine.py` — gains optional `mission_id` + `mission_slug` |
| `resolve_action_context` | Canonical OHS entry point in `core/execution_context.py` — all residue surfaces route through this |
| `BookkeepingTransaction` | Infrastructure coordinator in `coordination/transaction.py` — called only internally by `MissionStatus`; unchanged |
| e2e parity ratchet | New integration/architectural test in `tests/` — proves CWD-invariant behavior for the full `next→implement→move-task→review→status` sequence |
| ADR files | Three architecture decision records in `architecture/3.x/adr/` — ratify domain model before any implementation |

---

## Success Criteria

| # | Criterion | Measurable threshold |
|---|-----------|----------------------|
| 1 | All three ADRs exist and are merged to `main` before any implementation code | 3 ADR files in `architecture/3.x/adr/` merged; verified by PR gate |
| 2 | e2e parity ratchet passes in CI for both main-checkout and lane-worktree invocations | Test green on every subsequent PR; zero flake rate |
| 3 | `status/` import boundary is enforced with zero violations | Architectural test passes; `grep -r "from specify_cli.status\." src/ --include="*.py"` outside `status/` returns zero hits (excluding exempted internal callers) |
| 4 | `agent/status.py` no longer constructs raw feature-dir paths | Zero occurrences of `main_repo_root / "kitty-specs"` in `cli/commands/agent/status.py` |
| 5 | `MissionRunSnapshot` carries mission identity | `state.json` files written after this mission include `mission_id` and `mission_slug`; existing files load without error |
| 6 | No surface outside `core/execution_context.py` and `status/` constructs feature-dir paths independently | `grep` for `kitty-specs.*mission_slug\|main_repo_root.*kitty\|feature_dir.*slug` in `src/` (excluding exempted modules) returns zero hits |
| 7 | All legacy mission integration tests pass without modification | Full existing test suite passes on `main` after all Strangler steps land |

---

## Assumptions

- The execution-context domain model documented in #1666 (docs 01–17, especially doc 17 and doc 06) is the authoritative design basis; this spec does not reproduce that analysis.
- `_resolve_mission_ulid` already exists in `runtime_bridge.py` and can be called at `start_mission_run` time to populate `mission_id` on the new snapshot fields.
- `coordination/status_transition.py`'s internal `status/` imports are intentional and correct; they should be counted as exempt from the boundary test, not fixed.
- The ~245 bypass import count from #1664 was accurate at issue-filing time (2026-06-03); the actual count may differ slightly by implementation time and should be re-verified with the grep in the issue.
- `workflow.py` fix-mode and `runtime_bridge` query-mode are the primary residue surfaces after #1667 lands; the investigation command in #1673 should be re-run after #1667 merges to confirm remaining targets.
