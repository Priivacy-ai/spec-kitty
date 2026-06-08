# Implementation Plan: Execution-State Canonical Domain Surface

**Branch**: `feat/execution-state-strangler` | **Date**: 2026-06-07 (revised 2026-06-08, post-FSM rebase) | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/execution-state-canonical-surface-01KTG6P9/spec.md`
**Base**: rebased onto the WP-lane FSM branch `mission/wp-lane-state-machine-fsm` (`c03972531`). The FSM/status canonicalization and its Randy-Reducer reduction pass are now this mission's baseline — see [Post-FSM-Rebase Reconciliation](#post-fsm-rebase-reconciliation-2026-06-08).

## Summary

Stand up a net-new `mission_runtime/` umbrella package (Screaming Architecture + Strangler Fig, decided in `docs/engineering_notes/runtime_and_state_overhaul/06-proposed-domains-and-splits.md` §4) that owns execution-state resolution behind a lean public API over the context objects. Realize the **Stage C** ExecutionContext shape from doc 06 §5 — a stable `resolve_action_context` façade relocated into the umbrella that delegates to today's resolver — explicitly deferring the **Stage B** commit-owning operation service (it belongs to the out-of-scope CommitTarget step 7). Then strangle the residue into it: route the ~40 residue command surfaces and ~125 path-builders, collapse the 8 duplicate feature-dir resolvers, enforce the `status/` facade repo-wide (~225 deep `status.*` imports → facade/`MissionStatus`), and fold in the #1663 field-drop. The full `next→implement→move-task→review→status` parity ratchet across all three execution modes is built first as the regression gate. Two #1756-review follow-ups (IC-08 #1757, IC-09 #1754) extend the same one-owning-port discipline to the ownership-`scope`/finalize and legacy-migration-rebuild surfaces.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml (runtime CLI); pytest, pytestarch, mypy, ruff (quality); `spec_kitty_events`, `spec_kitty_tracker` (external contract packages, consume via public imports only)
**Storage**: Filesystem only — `kitty-specs/<mission>/`, `status.events.jsonl`, runtime `state.json`; no database
**Testing**: pytest (unit / integration / architectural); `pytestarch` for the layer meta-guard and the `status/` import-boundary rule; `mypy --strict` on touched modules; `ruff` clean; the e2e parity ratchet as the gating integration test
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows 10+)
**Project Type**: single (Python CLI library under `src/`)
**Performance Goals**: No runtime perf regression; repo-wide `status/` import scan ≤15 s wall-clock in CI (NFR-005)
**Constraints**: Behavior-preserving across all execution modes (NFR-001); layer meta-guard must stay green; never write mainline without explicit operator authorization (C-001); `coordination/transaction.py` internals unchanged (NFR-006)
**Scale/Scope** (re-measured 2026-06-08 on the post-FSM-rebase tree): **234** deep `status.*` submodule bypass imports vs **28** facade (`from specify_cli.status import …`) imports; ~125 path-builder occurrences across ~160 files; 8 duplicate feature-dir resolvers; ~40 residue command surfaces. The status-import count is unchanged in magnitude by the FSM pass — that pass consolidated *specific* consumers and removed status dead code (see reconciliation), it did not migrate the bulk. Folded-in surfaces (IC-08/IC-09): `ownership/` (scope/backfill/port) + `migration/backfill_ownership.py`; the migration runner/normalize/`mission_state`/`rebuild_state` rebuild path.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Architecture: Shared Package Boundaries / layer rules** — A net-new top-level `mission_runtime/` must be registered in `_DEFINED_LAYERS` (both `tests/architectural/conftest.py` and `test_layer_rules.py`) or `test_no_unregistered_src_packages` fails. Placement respects the spine (`kernel ← doctrine ← charter ← specify_cli`; `runtime`/`glossary` siblings at charter level). **PASS (planned)** via FR-002.
- **`__all__` Declaration Convention (binding, C-007 charter)** — the new umbrella's public API and any promoted `status/` symbols declare `__all__`. **PASS (planned)** via FR-001/FR-013.
- **ATDD-First Discipline (binding, C-011 charter)** — the parity ratchet and boundary tests are authored as the acceptance gate before the strangling changes. Each WP (incl. the IC-08/IC-09 fold-ins) authors its failing-first ATDD test as the first subtask and first (red) commit. **PASS (planned)** via IC-03 sequenced first.
- **Test and Typecheck Quality Gate (DIR)** — `ruff` + `mypy --strict` clean on touched modules (SC-008). **PASS (planned)**.
- **Burn-down Policy (binding, C-004 charter)** — no net new untested debt; deletions are real (no dead code left). **PASS (planned)** via FR-011/NFR-002.
- **Terminology Canon (Mission vs Feature)** — new code uses Mission vocabulary; no `feature*` aliases for the domain object. **PASS (planned)**.
- **Identifier Safety / Bulk-Edit (DIRECTIVE_035)** — the ~225-import migration runs under `change_mode: bulk_edit` with an `occurrence_map.yaml`. **PASS (planned)** via C-007 (spec).

No charter violations requiring Complexity Tracking justification.

## Project Structure

### Documentation (this mission)

```
kitty-specs/execution-state-canonical-surface-01KTG6P9/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (canonical API + boundary + ratchet contracts)
├── occurrence_map.yaml  # Bulk-edit classification (status import migration)
├── issue-matrix.md      # Issue→FR traceability (WP column filled at /tasks)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── mission_runtime/                 # NEW canonical execution-state umbrella (registered in layer meta-guard)
│   ├── __init__.py                  #   curated public API (__all__): resolve_action_context, ExecutionContext
│   ├── context.py                   #   ExecutionContext / ActionContext value object (relocated from core/)
│   └── resolution.py                #   resolve_action_context façade (Stage C: delegates to today's resolver)
├── specify_cli/
│   ├── core/execution_context.py    # → thin shim re-exporting from mission_runtime, or removed if unreferenced
│   ├── status/                      # facade hardened (promotions/demotions); MissionStatus is the entry point
│   ├── ownership/                   # IC-08: scope single-ported; new frontmatter_source.py port
│   ├── migration/                   # IC-09: mission_state canonical rebuild entry; rebuild_state retired
│   ├── runtime/next/runtime_bridge.py  # residue routed; #1663 field-drop fixed
│   └── cli/commands/agent/workflow.py  # fix-mode routed through canonical surface
└── runtime/next/                    # consumes mission_runtime API; no independent path derivation

tests/
├── architectural/
│   ├── test_layer_rules.py                    # + mission_runtime registered
│   ├── test_status_module_boundary.py         # widened repo-wide
│   ├── test_execution_context_parity.py       # extended to full sequence × 3 modes
│   └── test_mission_runtime_surface.py         # NEW: sole-resolver enforcement
├── integration/
└── unit/
```

**Structure Decision**: Single Python project. The one structural addition is the net-new top-level `src/mission_runtime/` umbrella (doc 06 §4 decision), registered in the layer meta-guard. `ExecutionContext` and `resolve_action_context` migrate into it under Strangler; `core/execution_context.py` becomes a thin shim (or is deleted once unreferenced).

## Complexity Tracking

*No Charter Check violations.* The new top-level package is an explicitly ratified architecture decision (doc 06 §4), not a complexity exception — it is registered in the layer meta-guard rather than justified as a deviation.

## Post-FSM-Rebase Reconciliation (2026-06-08)

This mission was rebased onto `mission/wp-lane-state-machine-fsm` (`c03972531`), so the WP-lane FSM canonicalization and its Randy-Reducer reduction pass are now the baseline. That pass already touched several surfaces this strangler targets. `/spec-kitty.tasks` must re-derive the WPs from the IC map below; the deltas here keep the new WPs from redoing — or fighting — work already landed. **Reference symbols by name, not line number** (e.g. `runtime_bridge.py` grew to 3623 lines; the plan's old `:1723/:1860` citations are stale).

- **IC-04 (path-builder residue / dead-code):** the FSM reduction already deleted *status-side* dead code (`discovery._load_wp_lanes` no-op branches, `validate` `STATUS_BLOCK_*`/`_extract_tasks_status_lines`, the `doctor` no-op call-site, `lifecycle._TERMINAL_LANES`, `wp_state` shim wrappers, `agent_utils` dead `sum()`), and consolidated `_exclude_coord_owned`. **The path-builder/feature-dir-resolver scope is intact** (those weren't touched). WPs must not re-flag the already-removed status dead code as residue.
- **IC-05 (status facade enforcement):** the facade gained a new public symbol, **`COORD_OWNED_STATUS_FILES`** (in `status/__init__.py` `__all__`, derived from `EVENTS_FILENAME`/`SNAPSHOT_FILENAME`) — already a *promotion* this IC would have made; include it in the inventory as **done**, don't re-promote. Current counts: **234** deep submodule imports vs **28** facade imports remain to migrate.
- **IC-06 (`MissionStatus`/canonical-reader consumption):** the canonical-reader routing **pattern is now established and demonstrated** — `runtime/next/decision.py::_get_wp_lanes` was collapsed onto `lane_reader.get_all_wp_lanes` (with `CanonicalStatusNotFoundError` fallback). Treat that as the reference exemplar; this consumer is **already ported** (drop it from the to-do set). The genesis read/write-parity defaults in `lane_reader`/`views`/`progress`/`lifecycle`/`aggregate` are also canonicalized — consumers should read through those, not re-add local lane defaults.
- **IC-07 (#1663 field-drop):** confirmed still live — the rebased parity snapshot shows `mission_id: null` / `mission_slug: null` (the exact drop). The reconstruction sites moved (now ~`runtime_bridge.py:1834/1854`); cite them by the `OperationalContext(...)` call, not the stale line numbers.
- **IC-03 (parity ratchet):** `tests/architectural/test_execution_context_parity.py` exists with 4 tests; on this branch some fail locally due to subprocess `PYTHONPATH` env (not behavior) and the `test_internal_runtime_parity` snapshot carries the IC-07 drift. IC-03's full-sequence × 3-mode extension and de-overclaim still stand; fold the IC-07 fields into the snapshot when fixed.
- **FSM-7 note:** `orchestrator_api/commands.py::_is_run_affecting` was renamed to **`_transition_requires_policy`** (distinct from `WPState.is_run_affecting`). IC-06 touches orchestrator-api status consumers — use the new name and do not conflate the two.
- **IC-08 / IC-09:** disjoint ownership/migration surfaces — unaffected by the FSM pass; scope unchanged.

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Canonical `mission_runtime/` umbrella + layer registration

- **Purpose**: Create the owned execution-state domain home with a lean public API and register it in the layer meta-guard, so there is a single legal destination to strangle into.
- **Relevant requirements**: FR-001, FR-002, FR-005, FR-006
- **Affected surfaces**: `src/mission_runtime/` (new), `tests/architectural/test_layer_rules.py`, `tests/architectural/conftest.py`, `tests/architectural/test_mission_runtime_surface.py` (new), `architecture/3.x/adr/`
- **Sequencing/depends-on**: none (foundational)
- **Persona IC**: **Paula Patterns** — single-ownership; the umbrella is the sole sanctioned resolver, the architectural test must actually bite (no allowlist escape).
- **Risks**: Layer-guard registration must be exact in both files; ADR (FR-006) must land before mass code (C-006).

### IC-02 — ExecutionContext relocation as Strangler façade (Stage C)

- **Purpose**: Relocate `resolve_action_context` + the context value object into the umbrella as a stable façade that delegates to today's resolver; leave a thin shim at `core/execution_context.py`. **Also relocate the `runtime_bridge.py` operational-context builders** — `build_operational_context_for_claim`, `_build_operational_context_for_decision`, `_resolve_tech_stack_for_profile` — into the umbrella (they *are* execution-state resolution); `runtime_bridge` then consumes the umbrella API. (Bounded `runtime_bridge` decomposition: operator decision 2026-06-08 — extract only the exec-state/path/operational-context clusters; the decision-engine / composition / parsing / retrospective clusters stay put for a possible later god-module split.)
- **Relevant requirements**: FR-003, FR-004
- **Affected surfaces**: `src/mission_runtime/context.py`, `src/mission_runtime/resolution.py`, `src/specify_cli/core/execution_context.py`, `src/runtime/next/runtime_bridge.py` (operational-context builders moved out; import shim if needed)
- **Sequencing/depends-on**: IC-01
- **Persona IC**: **Randy Reducer** — behavior-preserving relocation; the façade is the only resolution path; no parallel resolver retained; shim is minimal and temporary.
- **Risks**: Import cycles; must keep the parity ratchet green throughout; `runtime_bridge` is 3623 LOC with many call sites — extractions need import-compat shims and the IC-03 ratchet as the safety net.

### IC-03 — Full-sequence parity ratchet across execution modes (the gate)

- **Purpose**: Extend `test_execution_context_parity.py` to the full `next→implement→move-task→review→status` sequence across main / lane / direct-to-target, with a non-vacuous negative control; de-overclaim its docstring.
- **Relevant requirements**: FR-020, FR-021, FR-022, FR-023, FR-024
- **Affected surfaces**: `tests/architectural/test_execution_context_parity.py`, CI gate config
- **Sequencing/depends-on**: none (built first per ATDD; gates IC-04..IC-07)
- **Persona IC**: **Paula Patterns** — the ratchet must catch re-derivation, not structural presence.
- **Risks**: Direct-to-target fixture realism; ratchet must fail when re-derivation is injected.

### IC-04 — Path-builder residue strangling + dup-resolver collapse + mode-correct branch

- **Purpose**: Route the residue surfaces (`runtime_bridge` query-mode, `workflow.py` fix-mode, …) through the umbrella; collapse the 8 duplicate feature-dir resolvers to one; delete dead path-builders; make the gate observe the mode-correct target branch. **Within `runtime_bridge.py`, the mission/path-resolution cluster is part of the collapse** — `_primary_runtime_feature_dir`, `_resolve_runtime_feature_dir`, `_resolve_run_dir_for_mission`, `_resolve_coordination_branch`, `_resolve_mission_ulid` re-derive feature dirs / coord branch / ULID independently; route them through the umbrella's single resolver (operator decision 2026-06-08, bounded scope).
- **Relevant requirements**: FR-007, FR-008, FR-009, FR-010, FR-011, FR-012
- **Affected surfaces**: `runtime/next/runtime_bridge.py` (path/feature-dir/coord-branch/ULID resolvers collapsed into the umbrella), `cli/commands/agent/workflow.py`, `workspace/context.py`, `task_utils/support.py`, `cli/commands/verify.py`, `cli/commands/agent/status.py`, `dashboard/scanner.py`, `missions/feature_dir_resolver.py`, ~160 files with raw path constructions
- **Sequencing/depends-on**: IC-02 (destination), IC-03 (gate)
- **Persona IC**: **Randy Reducer** (collapse to one resolver, delete dups) + **Paula Patterns** (no boundary leak survives).
- **Risks**: Large blast radius; mode-correct branch logic must honor C-001 (never mainline unauthorized).

### IC-05 — Repo-wide status facade enforcement (bulk-edit)

- **Purpose**: Promote/demote `status/` symbols, migrate ~225 deep imports to the facade or `MissionStatus`, and widen the boundary test to all of `src/specify_cli`.
- **Relevant requirements**: FR-013, FR-014, FR-015, FR-016
- **Affected surfaces**: `src/specify_cli/status/__init__.py`, `tests/architectural/test_status_module_boundary.py`, ~225 import sites; `occurrence_map.yaml`
- **Sequencing/depends-on**: IC-03 (gate)
- **Persona IC**: **Paula Patterns** — the facade is the sole owner; exemptions limited to documented plumbing (C-004).
- **Risks**: Bulk-edit guardrail (C-007); avoid promoting internals that should stay private.
- **Post-FSM delta**: `COORD_OWNED_STATUS_FILES` is **already promoted** into the facade `__all__` (FSM pass) — record as done, do not re-promote. Re-measured: 234 deep imports vs 28 facade imports to migrate.

### IC-06 — Consistent `MissionStatus` usage

- **Purpose**: Rework direct `emit`/`lane_reader`/`BookkeepingTransaction` callers onto `MissionStatus.load()/.claim()/.transition()`.
- **Relevant requirements**: FR-017, FR-018, FR-019
- **Affected surfaces**: status read/write consumers across `cli/`, `orchestrator_api/`, `core/`
- **Sequencing/depends-on**: IC-05 (facade promotions in place)
- **Persona IC**: **Randy Reducer** — one status entry point; no parallel write surface.
- **Risks**: Distinguish mission-level access (route to aggregate) from internal plumbing (exempt).
- **Post-FSM delta**: the canonical-reader routing pattern is **already demonstrated** — `runtime/next/decision.py::_get_wp_lanes` now delegates to `lane_reader.get_all_wp_lanes` (use as the reference exemplar; this consumer is **done**). Genesis read/write-parity defaults are canonicalized in `lane_reader`/`views`/`progress`/`lifecycle`/`aggregate` — consume them, don't re-add local lane defaults. Note FSM-7: `orchestrator_api/commands.py::_is_run_affecting` → `_transition_requires_policy`.

### IC-07 — Mission-identity field-drop fold-in (#1663)

- **Purpose**: Carry `mission_id`/`mission_slug` through the `runtime_bridge.py:1723/:1860` reconstructions; regression test; close #1663.
- **Relevant requirements**: FR-025, FR-026, FR-027
- **Affected surfaces**: `runtime/next/runtime_bridge.py`
- **Sequencing/depends-on**: IC-04 (same hotspot — edit once)
- **Persona IC**: **Randy Reducer** — minimal carry-through, no new branch.
- **Risks**: None significant; ensure all six `engine.py` sites remain correct.

### IC-08 — Ownership `scope` backfill-awareness + frontmatter-source port (#1757)

- **Purpose**: Make the ownership `scope` flag flow through one canonical owner on every path (read / backfill / inference) and push the finalize ownership IO boundary through a single frontmatter-source port — the same one-owning-port theme as IC-05/IC-06, applied to the ownership surface. Folded in from the #1756 (#1753) review that unblocked this mission's own `finalize-tasks`.
- **Relevant requirements**: FR-028, FR-029, FR-030, FR-031
- **Affected surfaces**: `src/specify_cli/ownership/models.py` (`from_frontmatter` dict-path symmetry), `ownership/inference.py` (no-inference contract), `ownership/validation.py` (`build_wp_manifests`), `ownership/frontmatter_source.py` (new port), `migration/backfill_ownership.py` (scope-aware guard+write), `cli/commands/agent/mission.py` (finalize caller routed through the port), `tests/specify_cli/ownership/`
- **Sequencing/depends-on**: none (disjoint surface; runs in parallel with the strangler/facade tracks)
- **Persona IC**: **Paula Patterns** — `from_frontmatter` is the sole owner; no parallel `scope` path; the port removes the reader-stub from the resolve→validate test.
- **Risks**: behavior-preserving port (prove with existing finalize tests); three `scope` representations must not fork.

### IC-09 — Legacy migration event-rebuild single-port (#1754)

- **Purpose**: Route the two live legacy-migration callers (`runner.py` Step 4, `normalize_mission_lifecycle.py`) onto a single canonical per-mission `mission_state` event-rebuild entry that returns event counts, retiring the deprecated `rebuild_event_log` (`repair_repo` is repo-level, not a per-feature drop-in). Same one-owning-port theme on the migration surface.
- **Relevant requirements**: FR-032, FR-033, FR-034
- **Affected surfaces**: `src/specify_cli/migration/mission_state.py` (canonical entry), `migration/runner.py`, `migration/normalize_mission_lifecycle.py`, `migration/rebuild_state.py` (retire/shim), `migration/__init__.py` (`__all__` cleanup), `tests/specify_cli/migration/`
- **Sequencing/depends-on**: none (disjoint surface)
- **Persona IC**: **Randy Reducer** — exactly one rebuild path; deprecated symbol removed or thin-shimmed with no live callers.
- **Risks**: behavioral change to legacy-project migration — fixture-backed (NFR-004); the canonical entry must preserve the per-feature event-count reporting contract `repair_repo` lacks.

## Phases

- **Phase 0 — Research** (`research.md`): resolve the carried-forward decisions (module name, ExecutionContext shape, migration order, import-classification strategy, shim approach). All resolved from doc 06/17 — see research.md.
- **Phase 1 — Design** (`data-model.md`, `contracts/`, `quickstart.md`, `occurrence_map.yaml`): the umbrella's public API surface, the context objects, the boundary + ratchet contracts, and the bulk-edit occurrence map.
- **Phase 2 — Tasks** (`/spec-kitty.tasks`): translate IC-01..IC-09 into work packages with persona ICs, applying the [Post-FSM-Rebase Reconciliation](#post-fsm-rebase-reconciliation-2026-06-08) deltas (drop already-done items, fix renamed/moved references). **Not produced by this command.**
