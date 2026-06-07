# Execution-State Canonical Domain Surface — #1666 Strangler Slice 2

**Mission ID:** 01KTG6P99C3ZGDT2Z97S7ZN5VE
**Mission Slug:** execution-state-canonical-surface-01KTG6P9
**Mission Type:** software-dev
**Target Branch:** feat/execution-state-strangler
**Status:** Draft

---

## Purpose

**TL;DR:** Stand up one canonical, lean execution-state domain module with a clean public API over the context objects, then strangle the ~225 status-facade bypasses, ~125 duplicated path-builders, and the residue command surfaces into it — deleting the parallel code paths rather than re-masking them.

The execution-state redesign (#1666, blocks #1619) established that mission commands today re-derive execution context, paths, and work-package status independently, so the same command behaves differently depending on the working directory it is invoked from. The predecessor mission (`execution-state-domain-remediation-01KT6HVH`) landed the foundations — the `MissionStatus` aggregate (#1667), the `resolve_action_context` resolver (#1673), a status-read/write parity ratchet (#1672, narrowed), and a WP03-scoped status boundary test (#1664, narrowed). It explicitly deferred the bulk of the remediation: the full command-sequence ratchet, the repo-wide facade enforcement, and the ~225 path-builder residue (tracked in the now-closed #1681).

This mission is the next slice. It applies the **Strangler Fig** method properly: build a stable, well-abstracted canonical execution-state domain surface (per doc 06 §4 / doc 17 — Screaming Architecture), register it in the layer meta-guard with architectural tests, then incrementally route the scattered call sites and status-facade bypasses through the canonical surface and the `MissionStatus` aggregate while deleting the duplicated path-builders. Leanness is a first-class acceptance dimension, enforced via explicit Randy-Reducer and Paula-Patterns implementation contracts on the shaping work packages.

---

## Source Issues

| Issue | Title | Role in this slice |
|-------|-------|--------------------|
| #1666 | Execution-state & context domain-boundary redesign (parent epic) | Design authority; this slice is its next implementation front |
| #1672 | e2e parity ratchet | Extend from status-only slice to the full `next→implement→move-task→review→status` sequence across all execution modes |
| #1673 | Harden ExecutionContext — route residue surfaces | Stand up canonical surface; route residue; delete duplicated path-builders |
| #1664 | `status/` public API not enforced (~225 bypass imports) | Promote/demote facade symbols; fix all bypasses repo-wide; widen boundary test to all of `src/specify_cli` |
| #1667 | `MissionStatus` aggregate (landed) | Make it the consistent read+write entry point; rework bypasses onto it |
| #1663 | `MissionRun → Mission` back-reference (field-drop) | Carry `mission_id`/`mission_slug` through `runtime_bridge.py` reconstructions; close it |
| #1681 | Closed continuation tracker for the path-builder residue | Historical context; residue is inherited here |

---

## Domain Language

| Canonical term | Meaning in this mission | Synonyms to avoid |
|----------------|-------------------------|-------------------|
| Execution-state domain surface | The single canonical module (expected `mission_runtime/`, final name ratified in the design ADR) owning execution-context, path, and workspace resolution behind a published API | "core helpers", "path utils", ad-hoc resolvers |
| Canonical entry point | `resolve_action_context` (relocated/wrapped into the canonical surface) as the only sanctioned way to resolve mission execution context | "the resolver function", per-surface re-derivation |
| Status facade | The `specify_cli.status` public package API (`__init__.__all__`) | deep `status.*` submodule imports |
| `MissionStatus` aggregate | The authoritative status read+write owner consumers must use | direct `emit`/`lane_reader`/`store` calls |
| Execution mode | One of: planning (coordination branch), direct-to-target (target branch, no worktree), worktree (lane worktree) | "worktree vs main" binary |
| Mode-correct target branch | The authorized write branch for the active execution mode | "main", "the default branch" |

---

## User Scenarios & Testing

### Scenario A — CWD-invariant full command sequence
**Actor:** spec-kitty agent or developer
**Trigger:** Runs the full `next → implement → move-task → review → status` sequence from (1) the main-checkout root, (2) the lane worktree, and (3) a direct-to-target mission run with no worktree.
**Expected outcome:** Resolved WP identity, lane transitions, and status output are identical across all three modes.
**Exception path:** If any surface re-derives context independently, the extended ratchet fails CI.

### Scenario B — Status submodule import rejected anywhere in the tree
**Actor:** Developer adds `from specify_cli.status.emit import build_status_event` in `cli/commands/`.
**Trigger:** CI runs the repo-wide status boundary test.
**Expected outcome:** Test fails identifying the violation and instructing use of the facade or `MissionStatus`. (Previously this was only enforced for 6 WP03 packages.)

### Scenario C — Path resolution routes through the canonical surface
**Actor:** A residue command surface (e.g. `runtime_bridge.py` query-mode, `workflow.py` fix-mode).
**Trigger:** Needs the mission feature dir / workspace / branch.
**Expected outcome:** It obtains them from the canonical surface; no `main_repo_root / "kitty-specs" / mission_slug` construction exists outside the canonical module and `status/`.

### Scenario D — Mission identity survives snapshot reconstruction
**Actor:** Runtime reconstructs a `MissionRunSnapshot` on the auto-complete path.
**Trigger:** Passes through `runtime_bridge.py:1723` / `:1860`.
**Expected outcome:** `mission_id` and `mission_slug` are carried through, not reset to `None`. Regression test proves it.

### Scenario E — Direct-to-target mode never touches mainline unauthorized
**Actor:** A direct-to-target mission run.
**Trigger:** Resolves its write branch via the canonical surface.
**Expected outcome:** It uses the declared target branch directly with no worktree; a write resolving to mainline (main/master) without explicit operator authorization is refused.

### Scenario F — Leanness: no parallel code path reintroduced
**Actor:** Reviewer (Paula Patterns / Randy Reducer lens).
**Trigger:** Reviews the canonical surface and the strangled call sites.
**Expected outcome:** Each resolution concern has exactly one implementation; deleted path-builders are gone (not dead code); no duplicated/parallel resolver remains.

---

## Functional Requirements

### Canonical execution-state domain surface (#1666 doc 06 §4 / #1673)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | A new canonical execution-state domain module (expected `src/mission_runtime/`; final name ratified in the design ADR) exists with an `__init__.py` exposing a curated public API (`__all__`) over execution-context resolution | Proposed |
| FR-002 | The new module is registered in the layer meta-guard: added to `_DEFINED_LAYERS` in `tests/architectural/test_layer_rules.py` and to the landscape fixture in `tests/architectural/conftest.py`, with `test_no_unregistered_src_packages` passing | Proposed |
| FR-003 | `resolve_action_context` and the `ExecutionContext`/`ActionContext` type are relocated into (or re-exported as the canonical entry point of) the new module; `core/execution_context.py` retains at most a thin deprecation shim or is removed if no longer referenced | Proposed |
| FR-004 | The canonical API is expressed in terms of the per-domain context objects at the correct abstraction level (callers receive a resolved context object, not raw path fragments) | Proposed |
| FR-005 | Architectural tests assert the canonical surface is the only sanctioned execution-context resolver: no `import`-level access to relocated internals from outside the module | Proposed |
| FR-006 | A design/decision record under `architecture/3.x/adr/` records the canonical module name, its public API shape, the context-object abstraction, and the Strangler migration order | Proposed |

### Strangle the path-builder residue (#1673 / inherited #1681)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-007 | `runtime_bridge.py` query-mode derives `feature_dir`/workspace/branch through the canonical surface rather than constructing them from the mission slug | Proposed |
| FR-008 | `cli/commands/agent/workflow.py` fix-mode routes its `repo_root`/`target_branch` resolution through the canonical surface | Proposed |
| FR-009 | No surface outside the canonical module and `src/specify_cli/status/` constructs `main_repo_root / "kitty-specs" / mission_slug` (or equivalent feature-dir path) directly; the ~125 current occurrences across ~160 files are routed or deleted | Proposed |
| FR-010 | The 8 duplicated `_resolve_feature_dir`/feature-dir resolver implementations are collapsed to a single canonical resolver; the redundant copies are deleted (not left as dead code) | Proposed |
| FR-011 | Duplicated path-builder functions made unreachable by this work are deleted from the codebase | Proposed |
| FR-012 | The execution-context gate observes the mode-correct authorized target branch (coordination branch for planning, declared target for direct-to-target, lane branch for worktree mode) — not a fixed always-main or always-worktree surface | Proposed |

### Repo-wide status facade enforcement (#1664)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-013 | Symbols with genuine external consumers are promoted to the `status/__init__.py` public API; symbols with no external consumers are renamed private with a `_` prefix | Proposed |
| FR-014 | All ~225 deep `status.*` submodule imports from outside `status/` are fixed to use the public facade or the `MissionStatus` aggregate | Proposed |
| FR-015 | The status boundary test (`tests/architectural/test_status_module_boundary.py`) is widened from the 6 WP03 packages to enforce all of `src/specify_cli`, with the documented internal-plumbing exemptions (`coordination/status_transition.py`, `coordination/transaction.py`) preserved | Proposed |
| FR-016 | No new direct submodule imports of `status.*` are introduced outside `status/` after this mission lands | Proposed |

### `MissionStatus` consistent usage (#1667 consumption)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-017 | Status read paths that currently call `lane_reader`/`store`/`reducer` directly are reworked to go through `MissionStatus.load()` / `.claim()` where they represent mission-level status access | Proposed |
| FR-018 | Status write/transition paths that currently call `emit`/`BookkeepingTransaction` directly (outside the internal plumbing exemption) are reworked to go through `MissionStatus.transition()` | Proposed |
| FR-019 | No consumer outside `status/` and the documented coordination plumbing calls `BookkeepingTransaction` directly | Proposed |

### Full e2e parity ratchet (#1672)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-020 | `tests/architectural/test_execution_context_parity.py` is extended to exercise the full `next → implement → move-task → review → status` command sequence (not only `agent tasks status` + `agent status emit`) | Proposed |
| FR-021 | The ratchet exercises all three execution modes: main-checkout CWD, lane-worktree CWD, and direct-to-target (no worktree) | Proposed |
| FR-022 | The ratchet asserts identical resolved WP identity, lane transitions, and status output across modes, and includes a negative control proving it catches independent re-derivation (non-vacuous) | Proposed |
| FR-023 | The ratchet test docstring is corrected to state its real coverage (de-overclaim); it no longer implies coverage it does not have | Proposed |
| FR-024 | The ratchet is registered as a required gate for PRs touching the canonical module, `status/`, `runtime/next/`, or `cli/commands/agent/` | Proposed |

### Mission-identity field-drop fold-in (#1663)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-025 | `MissionRunSnapshot` reconstructions at `runtime/next/runtime_bridge.py:1723` and `:1860` carry `mission_id` and `mission_slug` through (currently dropped to `None`) | Proposed |
| FR-026 | A regression test asserts that a snapshot's mission identity survives the auto-complete reconstruction path | Proposed |
| FR-027 | #1663 is closeable on the strength of FR-025/FR-026 (all snapshot construction and reconstruction sites preserve mission identity) | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Behavior preservation: the strangling is behavior-preserving for all execution modes | Zero behavioral regressions on the existing integration + architectural suites | Proposed |
| NFR-002 | Leanness (Randy Reducer IC): each execution-context/path resolution concern has exactly one implementation path | Zero duplicated/parallel resolver functions remain; verified by review + grep | Proposed |
| NFR-003 | Single ownership (Paula Patterns IC): the canonical surface and status facade are the sole owners of their concerns | Zero boundary-leak bypasses outside documented exemptions; architectural tests bite | Proposed |
| NFR-004 | Backward-compatibility: legacy (pre-coord-topology) missions and existing on-disk `state.json` files load and operate unchanged | 100% of existing files load; legacy integration tests pass unmodified | Proposed |
| NFR-005 | Boundary-test performance: the repo-wide `status/` import scan completes quickly in CI | ≤15 s wall-clock on the full `src/` tree | Proposed |
| NFR-006 | No internals churn: `coordination/transaction.py` (`BookkeepingTransaction`) internals are unchanged | Zero diff to `coordination/transaction.py` internals | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | Mainline (main/master) is never bypassed or committed to without explicit operator authorization; user/charter guidance to create a branch before mission work always applies (operator ruling 2026-06-07) | Accepted |
| C-002 | Planning happens on the coordination branch; a direct-to-target mission run may use the target branch directly with no worktree (worktree is unneeded overhead for that mode) | Accepted |
| C-003 | The full e2e parity ratchet (FR-020..FR-024) must be green before any FR-007..FR-019 strangling change is considered complete; the ratchet is the regression gate | Accepted |
| C-004 | `coordination/status_transition.py` and `coordination/transaction.py` are internal domain plumbing; they remain exempt from the status boundary test (not fixed) | Accepted |
| C-005 | `mission_number` must never be used as a selector or identity in new or modified code; lookup is by `mission_id` (ULID) or `mission_slug` only | Accepted |
| C-006 | The new module name and public API shape must be ratified in a design ADR (FR-006) before the bulk of the strangling lands (DIRECTIVE_032 — vocabulary/contract before mass code) | Accepted |
| C-007 | Bulk-edit guardrail: the #1664 status import-path migration changes the same `specify_cli.status.<sub>` strings across many files; the mission runs in `change_mode: bulk_edit` and produces an `occurrence_map.yaml` (DIRECTIVE_035) covering the import-path and path-builder migrations | Accepted |
| C-008 | Out of scope: actor-kind vocabulary normalization, Effector type materialization, CommitTarget atomicity (step 7), and communication-artefact consolidation (step 5) | Accepted |
| C-009 | Shaping work packages MUST carry explicit Randy-Reducer and Paula-Patterns implementation contracts (persona ICs) governing leanness and single-ownership | Accepted |

---

## Key Entities

| Entity | Description |
|--------|-------------|
| Canonical execution-state module | New domain umbrella (expected `mission_runtime/`) owning execution-context/path/workspace resolution behind a published API; registered in the layer meta-guard |
| `resolve_action_context` | The canonical entry point, relocated/wrapped into the new module; the only sanctioned execution-context resolver |
| `ExecutionContext` / `ActionContext` | The resolved per-domain context object callers receive |
| Status facade | `specify_cli.status` public package API; the only sanctioned way to reach status behavior from outside `status/` |
| `MissionStatus` | Authoritative status read+write aggregate (#1667); consumers route mission-level status access through it |
| e2e parity ratchet | Extended `test_execution_context_parity.py` proving CWD/mode-invariant behavior across the full command sequence |
| `MissionRunSnapshot` | Run snapshot whose `mission_id`/`mission_slug` must survive all reconstruction sites |
| occurrence_map.yaml | Bulk-edit classification artifact covering the status import-path + path-builder migrations |

---

## Success Criteria

| # | Criterion | Measurable threshold |
|---|-----------|----------------------|
| 1 | A single canonical execution-state module exists and is layer-registered | New module present; `test_no_unregistered_src_packages` + new architectural tests green |
| 2 | The full-sequence ratchet passes across all three execution modes | `next→implement→move-task→review→status` parity green for main, lane, and direct-to-target; negative control fails when re-derivation is injected |
| 3 | Repo-wide `status/` boundary is enforced with zero violations | `grep -rn "from specify_cli\.status\." src/ --include="*.py"` outside `status/` (excluding exemptions) returns zero; boundary test green over all of `src/specify_cli` |
| 4 | Path-builder residue is eliminated | Zero `main_repo_root / "kitty-specs" / mission_slug`-class constructions outside the canonical module and `status/`; the 8 duplicate feature-dir resolvers collapsed to one |
| 5 | `MissionStatus` is the consistent status entry point | Zero direct `BookkeepingTransaction`/`emit` calls outside `status/` and documented plumbing |
| 6 | Mission identity survives reconstruction | `runtime_bridge.py:1723/:1860` carry `mission_id`/`mission_slug`; regression test green; #1663 closeable |
| 7 | Leanness holds | Zero duplicated/parallel resolvers remain; Randy-Reducer + Paula-Patterns review sign-off on shaping WPs |
| 8 | No regressions | Full existing integration + architectural suite passes; `ruff` + `mypy` clean on touched modules |

---

## Assumptions

- The execution-state domain model in #1666 (docs 01–17, esp. doc 06 §4 and doc 17) is the authoritative design basis; this spec does not reproduce that analysis.
- The predecessor mission `01KT6HVH` landed `MissionStatus` (#1667), `resolve_action_context` (#1673 entry point), the narrowed status ratchet, and the WP03-scoped boundary test; this mission continues from that state.
- The current counts (225 status bypass imports; ~125 path-builders across ~160 files) were measured 2026-06-07 and must be re-verified at implementation time; they will drift as work lands.
- The canonical module name `mission_runtime/` from doc 06 §4 is the expected name; the design ADR (FR-006) may ratify a different name, and the spec requirements are written to that ADR's outcome rather than hardcoding the name.
- `runtime/next/runtime_bridge.py` is both the primary #1673 residue surface and the #1663 field-drop site, so the two are remediated together over the same hotspot.
- Run-through time and token cost are explicitly secondary to thorough remediation (operator direction).
