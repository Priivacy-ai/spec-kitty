# Tasks: Runtime Mission Execution Extraction

**Mission**: `runtime-mission-execution-extraction-01KPDYGW`
**Mission ID**: `01KPDYGWKZ3ZMBPRX9RYMWPR1A`
**Planning branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
**Generated**: 2026-04-22
**Change mode**: `bulk_edit` — `occurrence_map.yaml` is a required artefact (WP01)

---

## Overview

Extract `src/specify_cli/next/` (1,944 lines, 4 modules) and `src/specify_cli/runtime/` (1,837 lines, 10 modules) to a single canonical top-level package at `src/runtime/`, following the charter extraction pattern. Convert both legacy paths to deprecation shims. Rewrite ~19 non-CLI source callers and ~30 test callers to the canonical path. Wire the `PresentationSink`, `StepContractExecutor` seam Protocols. Enforce the runtime dependency boundary in pytestarch. All existing CLI commands and their `--json` output stay bit-for-bit identical.

**Extraction surface**: ~3,781 lines across 14 modules → `src/runtime/` (6 subpackages + `seams/`)
**Shim paths**: `src/specify_cli/next/` (4 shims) and `src/specify_cli/runtime/` (10 shims)
**Affected callers**: ~19 non-CLI source files, ~30 test files (enumerated by WP01 occurrence map)

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Audit `runtime_bridge.py` sync imports for Rich/Typer transitive exposure | WP01 | No | [D] |
| T002 | Create reference mission fixture at `tests/regression/runtime/fixtures/reference_mission/` | WP01 | No | [D] |
| T003 | Capture baseline JSON snapshots for 4 CLI commands (pre-extraction) | WP01 | No | [D] |
| T004 | Generate `occurrence_map.yaml` — enumerate all `specify_cli.next.*` / `specify_cli.runtime.*` callers | WP01 | No | [D] |
| T005 | Create `src/runtime/` package skeleton — all `__init__.py` files for 7 subpackages | WP02 | No | [D] |
| T006 | Define `PresentationSink` Protocol at `src/runtime/seams/presentation_sink.py` | WP02 | No | [D] |
| T007 | Define `StepContractExecutor` Protocol at `src/runtime/seams/step_contract_executor.py` | WP02 | No | [D] |
| T008 | Document `ProfileInvocationExecutor` boundary at `src/runtime/seams/profile_invocation_executor.py` | WP02 | No | [D] |
| T009 | Wire `src/runtime/__init__.py` public API surface | WP02 | No | [D] |
| T010 | Move `src/specify_cli/next/decision.py` → `src/runtime/decisioning/decision.py` | WP03 | [D] |
| T011 | Move `src/specify_cli/next/runtime_bridge.py` → `src/runtime/bridge/runtime_bridge.py`; inject `PresentationSink` for sync/analytics | WP03 | [D] |
| T012 | Move `src/specify_cli/next/prompt_builder.py` → `src/runtime/prompts/builder.py` | WP03 | [D] |
| T013 | Verify WP03 modules: no `rich.*`/`typer.*` top-level imports; run mypy --strict | WP03 | No | [D] |
| T014 | Move `src/specify_cli/runtime/home.py` + `resolver.py` → `src/runtime/discovery/` | WP04 | [D] |
| T015 | Move `src/specify_cli/runtime/agent_commands.py` + `agent_skills.py` → `src/runtime/agents/` | WP04 | [D] |
| T016 | Move `src/specify_cli/runtime/bootstrap.py` + `doctor.py` + `merge.py` + `migrate.py` + `show_origin.py` → `src/runtime/orchestration/` | WP04 | [D] |
| T017 | Verify WP04 modules: no forbidden imports; run mypy --strict | WP04 | No | [D] |
| T018 | Rewrite `src/specify_cli/cli/commands/next_cmd.py` to import from `runtime.*` | WP05 | [D] |
| T019 | Rewrite `src/specify_cli/cli/commands/implement.py` to import from `runtime.*` | WP05 | [D] |
| T020 | Rewrite `src/specify_cli/cli/commands/merge.py` to import from `runtime.*` | WP05 | [D] |
| T021 | Rewrite `src/specify_cli/cli/commands/agent/workflow.py` to import from `runtime.*` | WP05 | [D] |
| T022 | Audit `advise.py` + `do_cmd.py` for any next/runtime direct imports; amend occurrence map | WP05 | No | [D] |
| T023 | Convert `src/specify_cli/next/` (4 files) to pure re-export shims per #615 contract | WP06 | [D] |
| T024 | Convert `src/specify_cli/runtime/` (10 files) to pure re-export shims per #615 contract | WP06 | [D] |
| T025 | Add 2 entries to `architecture/2.x/shim-registry.yaml` | WP06 | No | [D] |
| T026 | Validate registry: `spec-kitty doctor shim-registry`; fix any failures | WP06 | No | [D] |
| T027 | Extend `tests/architectural/conftest.py` landscape fixture — add `runtime` layer | WP07 | No | [D] |
| T028 | Extend `tests/architectural/test_layer_rules.py` — `_DEFINED_LAYERS`, `TestRuntimeBoundary` class | WP07 | No | [D] |
| T029 | Run architectural tests; confirm zero violations; fix violations | WP07 | No | [D] |
| T030 | Write `tests/regression/runtime/test_runtime_regression.py` (dict-equal harness) | WP08 | No | [D] |
| T031 | Run post-extraction regression assertions; verify snapshots match | WP08 | No | [D] |
| T032 | Run full `pytest tests/` suite; zero regressions; verify shim warnings are non-fatal | WP08 | No | [D] |
| T033 | Apply occurrence_map.yaml rewrites to `src/doctrine/resolver.py`, `src/kernel/__init__.py` | WP09 | [D] |
| T034 | Apply occurrence_map.yaml rewrites to remaining non-CLI `specify_cli.*` source callers | WP09 | [D] |
| T035 | Apply occurrence_map.yaml rewrites to upgrade migration modules | WP09 | [D] |
| T036 | Validate WP09 rewrites: `ruff check`, mypy --strict, `pytest tests/` partial run | WP09 | No | [D] |
| T037 | Apply occurrence_map.yaml rewrites to `tests/next/` (5 files) | WP10 | [D] |
| T038 | Apply occurrence_map.yaml rewrites to `tests/runtime/` (8 files) | WP10 | [D] |
| T039 | Apply occurrence_map.yaml rewrites to remaining test files (16 files across other test dirs) | WP10 | [D] |
| T040 | Validate WP10 rewrites: run full `pytest tests/` to confirm zero regressions | WP10 | No | [D] |
| T041 | Write `docs/migration/runtime-extraction.md` — import-path translation table + migration guide | WP11 | [D] |
| T042 | Update `CHANGELOG.md` with Unreleased/Changed entry citing mission and charter exemplar | WP11 | [D] |

---

## Work Packages

---

### WP01 — Safety Baseline + Occurrence Map

**Priority**: Critical (must complete first — blocks all code movement)
**Estimated prompt size**: ~300 lines
**Execution mode**: `code_change`
**Profile**: `implementer-ivan`

**Goal**: Establish behavioural safety anchors and enumerate the full extraction scope before a single line of code moves. Audits the new `sync/` dependency in `runtime_bridge.py` for forbidden imports. Captures pre-extraction JSON regression snapshots. Generates the `occurrence_map.yaml` bulk-edit artefact.

**Subtasks**:
- [x] T001 Audit `runtime_bridge.py` sync imports for Rich/Typer transitive exposure (WP01)
- [x] T002 Create reference mission fixture at `tests/regression/runtime/fixtures/reference_mission/` (WP01)
- [x] T003 Capture baseline JSON snapshots for 4 CLI commands (WP01)
- [x] T004 Generate `occurrence_map.yaml` — enumerate all callers (WP01)

**Implementation sketch**:
1. Import-trace `runtime_bridge.py` → `sync/runtime_event_emitter` → check whether it pulls `rich.*` or `typer.*`; write finding to `research.md` addendum
2. Build a minimal reference mission (meta.json, spec.md, one WP, pre-baked status.events.jsonl) into `tests/regression/runtime/fixtures/reference_mission/`
3. Run `spec-kitty next --json`, `spec-kitty agent action implement WP01 --json`, `spec-kitty agent action review WP01 --json`, `spec-kitty merge <handle> --json` against the fixture; commit JSON snapshots to `tests/regression/runtime/fixtures/snapshots/`
4. `rg "specify_cli\.next|specify_cli\.runtime"` across `src/` and `tests/`; write `occurrence_map.yaml` categorising each caller into `cli_adapter`, `source_caller`, `test_caller`, or `migration_shim`

**Parallel opportunities**: None — steps are strictly sequential.

**Risks**: The sync import audit (T001) may reveal that `runtime_bridge.py` transitively pulls in `rich.*` via `SyncEmitter`. If so, PresentationSink in WP02 must route that output. Document the finding clearly; WP02 and WP03 depend on it.

**Dependencies**: None (first WP).

**Prompt file**: `tasks/WP01-safety-baseline-and-occurrence-map.md`

---

### WP02 — Runtime Package Skeleton + Seam Protocols

**Priority**: Critical (unblocks all moves)
**Estimated prompt size**: ~380 lines
**Execution mode**: `code_change`
**Profile**: `architect-alphonso`
**Dependencies**: WP01 (needs sync-import audit result before PresentationSink shape is final)

**Goal**: Create the empty `src/runtime/` package tree and define the three seam Protocols that the rest of the mission depends on.

**Subtasks**:
- [x] T005 Create `src/runtime/` package skeleton (WP02)
- [x] T006 Define `PresentationSink` Protocol at `src/runtime/seams/presentation_sink.py` (WP02)
- [x] T007 Define `StepContractExecutor` Protocol at `src/runtime/seams/step_contract_executor.py` (WP02)
- [x] T008 Document `ProfileInvocationExecutor` integration boundary at `src/runtime/seams/profile_invocation_executor.py` (WP02)
- [x] T009 Wire `src/runtime/__init__.py` public API surface (WP02)

**Implementation sketch**:
1. `mkdir` + `__init__.py` for: `runtime/`, `runtime/decisioning/`, `runtime/bridge/`, `runtime/prompts/`, `runtime/discovery/`, `runtime/agents/`, `runtime/orchestration/`, `runtime/seams/`
2. Define `PresentationSink(Protocol)` with `write_line(text: str) → None` and any additional methods revealed by the T001 sync-import audit
3. Define `StepContractExecutor(Protocol)` stub — no implementation; #461 Phase 6 fills this
4. At `seams/profile_invocation_executor.py`, write a typed alias `from specify_cli.invocation.executor import ProfileInvocationExecutor as ProfileInvocationExecutor` — documents the seam boundary without moving the implementation
5. Wire `__init__.py` with `__all__` covering the key public symbols implementers in WP03/WP04 will re-export

**Dependencies**: WP01

**Prompt file**: `tasks/WP02-runtime-package-skeleton-and-seam-protocols.md`

---

### WP03 — Move `next/` Subtree to Runtime

**Priority**: High
**Estimated prompt size**: ~350 lines
**Execution mode**: `code_change`
**Profile**: `implementer-ivan`
**Dependencies**: WP02

**Goal**: Relocate the 3 implementation modules from `src/specify_cli/next/` to `src/runtime/`. Inject `PresentationSink` wherever `runtime_bridge.py` surfaces output. Verify no forbidden imports remain.

**Subtasks**:
- [x] T010 Move `decision.py` → `src/runtime/decisioning/decision.py` (WP03)
- [x] T011 Move `runtime_bridge.py` → `src/runtime/bridge/runtime_bridge.py`; inject PresentationSink (WP03)
- [x] T012 Move `prompt_builder.py` → `src/runtime/prompts/builder.py` (WP03)
- [x] T013 Verify: no `rich.*`/`typer.*` top-level imports; mypy --strict on moved modules (WP03)

**Implementation sketch**:
1. Copy `decision.py` to `src/runtime/decisioning/decision.py`; update any relative imports; verify `from specify_cli.next.decision import decide_next` becomes `from runtime.decisioning.decision import decide_next` in callers (handled later in WP05/WP09/WP10 — for now leave the copy)
2. Copy `runtime_bridge.py` to `src/runtime/bridge/runtime_bridge.py`; replace any direct Rich console calls with `sink.write_line()` per the PresentationSink API; inject `sink: PresentationSink` as a parameter where needed
3. Copy `prompt_builder.py` to `src/runtime/prompts/builder.py`; update internal imports
4. Run `python -c "import runtime.decisioning; import runtime.bridge; import runtime.prompts"` to confirm import chain; run `mypy --strict src/runtime/`

**Parallel with**: WP04 (different modules, no shared state)

**Risks**: `runtime_bridge.py` is the largest module (1,113 lines). If it pulls in Rich indirectly, PresentationSink injection may be non-trivial. The T001 audit result in WP01 research addendum is the guide.

**Dependencies**: WP02

**Prompt file**: `tasks/WP03-move-next-subtree-to-runtime.md`

---

### WP04 — Move `runtime/` Subtree to Runtime

**Priority**: High
**Estimated prompt size**: ~330 lines
**Execution mode**: `code_change`
**Profile**: `implementer-ivan`
**Dependencies**: WP02

**Goal**: Relocate 9 implementation modules from `src/specify_cli/runtime/` to `src/runtime/discovery/`, `src/runtime/agents/`, and `src/runtime/orchestration/`. Verify no forbidden imports.

**Subtasks**:
- [x] T014 Move `home.py` + `resolver.py` → `src/runtime/discovery/` (WP04)
- [x] T015 Move `agent_commands.py` + `agent_skills.py` → `src/runtime/agents/` (WP04)
- [x] T016 Move `bootstrap.py` + `doctor.py` + `merge.py` + `migrate.py` + `show_origin.py` → `src/runtime/orchestration/` (WP04)
- [x] T017 Verify: no forbidden imports; mypy --strict on all moved modules (WP04)

**Implementation sketch**:
1. Copy `home.py` → `src/runtime/discovery/home.py` and `resolver.py` → `src/runtime/discovery/resolver.py`; update internal references
2. Copy `agent_commands.py` → `src/runtime/agents/commands.py` and `agent_skills.py` → `src/runtime/agents/skills.py`; update internal references
3. Copy the 5 orchestration modules with renamed `merge.py`→`merge.py`, `migrate.py`→`migrate.py`, etc.; verify no cyclic imports after the move
4. Run `mypy --strict src/runtime/discovery/ src/runtime/agents/ src/runtime/orchestration/`; confirm clean

**Parallel with**: WP03

**Dependencies**: WP02

**Prompt file**: `tasks/WP04-move-runtime-subtree-to-runtime.md`

---

### WP05 — CLI Adapter Conversion

**Priority**: High
**Estimated prompt size**: ~370 lines
**Execution mode**: `code_change`
**Profile**: `implementer-ivan`
**Dependencies**: WP03, WP04

**Goal**: Rewrite the 4 primary CLI command modules to import from `runtime.*`. Audit Phase 4 additions (`advise.py`, `do_cmd.py`) to confirm they do not bypass the extraction surface.

**Subtasks**:
- [x] T018 Rewrite `next_cmd.py` — all imports from `runtime.*`; confirm thin adapter (WP05)
- [x] T019 Rewrite `implement.py` — imports from `runtime.*`; confirm thin adapter (WP05)
- [x] T020 Rewrite `merge.py` (CLI) — imports from `runtime.*`; confirm thin adapter (WP05)
- [x] T021 Rewrite `agent/workflow.py` — imports from `runtime.*`; confirm thin adapter (WP05)
- [x] T022 Audit `advise.py` + `do_cmd.py`; amend occurrence map if they import from old paths (WP05)

**Implementation sketch**:
1. For each file: search for `from specify_cli.next` and `from specify_cli.runtime` imports; replace with `from runtime.*` equivalent
2. Confirm each command module contains only: Typer argument parsing, a single runtime service call, Rich/JSON rendering, and exit-code mapping — no inline `if lane == "planned":` style decisioning
3. For `advise.py` and `do_cmd.py` (Phase 4): check if they call `decide_next()` or other runtime-extracted functions; if yes, add to occurrence_map.yaml under `cli_adapter` category

**Dependencies**: WP03, WP04

**Prompt file**: `tasks/WP05-cli-adapter-conversion.md`

---

### WP06 — Shim Installation + Registry

**Priority**: High
**Estimated prompt size**: ~360 lines
**Execution mode**: `code_change`
**Profile**: `implementer-ivan`
**Dependencies**: WP03, WP04

**Goal**: Collapse `src/specify_cli/next/` and `src/specify_cli/runtime/` to pure re-export shims per the #615 contract. Register both shims in `architecture/2.x/shim-registry.yaml`.

**Subtasks**:
- [x] T023 Convert `src/specify_cli/next/` (4 files) to pure re-export shims (WP06)
- [x] T024 Convert `src/specify_cli/runtime/` (10 files) to pure re-export shims (WP06)
- [x] T025 Add 2 entries to `architecture/2.x/shim-registry.yaml` (WP06)
- [x] T026 Validate: `spec-kitty doctor shim-registry`; fix failures (WP06)

**#615 shim contract** (every shim file must have):
```python
__deprecated__ = True
__canonical_import__ = "runtime.<subpackage>.<module>"
__removal_release__ = "3.4.0"
__deprecation_message__ = "specify_cli.next.X is deprecated; use runtime.X instead"

import warnings
warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)

from runtime.<subpackage>.<module> import *  # noqa: F401, F403
```

**Implementation sketch**:
1. Replace each `src/specify_cli/next/*.py` body with the shim template above; keep the `__all__` re-export via `from runtime.* import *`
2. Repeat for all 10 `src/specify_cli/runtime/*.py` files
3. Write 2 YAML entries in `shim-registry.yaml` following the existing schema (see `architecture/2.x/06_migration_and_shim_rules.md`)
4. Run `spec-kitty doctor shim-registry --json`; confirm `passed: true`

**Parallel with**: WP05

**Dependencies**: WP03, WP04

**Prompt file**: `tasks/WP06-shim-installation-and-registry.md`

---

### WP07 — Architectural Boundary Tests

**Priority**: High
**Estimated prompt size**: ~280 lines
**Execution mode**: `code_change`
**Profile**: `implementer-ivan`
**Dependencies**: WP06

**Goal**: Extend `tests/architectural/` to enforce the runtime dependency boundary. Runtime must not import from `specify_cli.cli.*`, `rich`, or `typer`. Only `cli_shell` may import from `runtime`.

**Subtasks**:
- [x] T027 Extend `conftest.py` landscape fixture — add `runtime` module (WP07)
- [x] T028 Extend `test_layer_rules.py` — add `runtime` to `_DEFINED_LAYERS` + `TestRuntimeBoundary` class (WP07)
- [x] T029 Run architectural tests; confirm zero violations; fix violations (WP07)

**Implementation sketch**:
1. In `conftest.py`, add `runtime` to the `EvaluableModules` list in the `landscape` fixture (match pattern of existing `charter`, `doctrine`, `kernel`, `specify_cli` entries)
2. In `test_layer_rules.py`: add `"runtime"` to `_DEFINED_LAYERS`; add `TestRuntimeBoundary` with:
   - `test_runtime_does_not_import_from_cli_shell()`: runtime must not access `specify_cli.cli`
   - `test_runtime_does_not_import_rich_or_typer()`: runtime must not access `rich` or `typer`
   - `test_only_cli_shell_imports_runtime()`: only `specify_cli` layer may import from `runtime`
3. Run `pytest tests/architectural/ -v`; fix any violations before marking done

**Dependencies**: WP06 (shims must be in place so pytestarch sees a clean import graph)

**Prompt file**: `tasks/WP07-architectural-boundary-tests.md`

---

### WP08 — Regression Harness + Full Suite Verification

**Priority**: High
**Estimated prompt size**: ~290 lines
**Execution mode**: `code_change`
**Profile**: `implementer-ivan`
**Dependencies**: WP06, WP07

**Goal**: Write the dict-equal regression assertion harness. Run it against the pre-captured snapshots from WP01. Run the full `pytest tests/` suite and confirm zero regressions.

**Subtasks**:
- [x] T030 Write `tests/regression/runtime/test_runtime_regression.py` (WP08)
- [x] T031 Run post-extraction regression assertions (WP08)
- [x] T032 Run full `pytest tests/`; zero regressions; shim warnings non-fatal (WP08)

**Implementation sketch**:
1. Write `test_runtime_regression.py` with 4 parametrised test cases (one per snapshot); each test: invokes the CLI command against the fixture mission, loads the snapshot JSON, asserts `actual_dict == snapshot_dict` (key-order normalized); asserts exit code matches; asserts stderr matches (normalized for timestamps and absolute paths)
2. Run the regression tests; if diffs appear, investigate root cause — do NOT update snapshots without understanding the delta
3. Run `pytest tests/` (full suite) with `-W error::DeprecationWarning` disabled for the shim paths; confirm all currently-passing tests still pass

**Dependencies**: WP06, WP07

**Prompt file**: `tasks/WP08-regression-harness-and-suite-verification.md`

---

### WP09 — Source File Occurrence Migration

**Priority**: Medium (shims provide a grace period, but canonical imports are cleaner)
**Estimated prompt size**: ~300 lines
**Execution mode**: `code_change`
**Profile**: `implementer-ivan`
**Dependencies**: WP06

**Goal**: Apply `occurrence_map.yaml` rewrites to all non-CLI, non-test source callers of `specify_cli.next.*` / `specify_cli.runtime.*`. Includes `src/doctrine/`, `src/kernel/`, `src/specify_cli/core/`, `src/specify_cli/migration/`, `src/specify_cli/upgrade/`, and `src/specify_cli/mission.py` etc.

**Subtasks**:
- [x] T033 Apply rewrites to `src/doctrine/resolver.py` + `src/kernel/__init__.py` (WP09)
- [x] T034 Apply rewrites to remaining non-CLI `specify_cli.*` source callers (WP09)
- [x] T035 Apply rewrites to upgrade migration modules (WP09)
- [x] T036 Validate WP09: `ruff check`, mypy --strict, partial `pytest tests/` run (WP09)

**Known callers from occurrence_map.yaml** (confirmed by scan; verify against actual map):
- `src/doctrine/resolver.py`
- `src/kernel/__init__.py`
- `src/specify_cli/cli/commands/agent/status.py`, `config_cmd.py`, `doctor.py`, `init.py`, `migrate_cmd.py`
- `src/specify_cli/core/project_resolver.py`
- `src/specify_cli/__init__.py`
- `src/specify_cli/mission.py`, `src/specify_cli/state/doctor.py`, `src/specify_cli/migration/rewrite_shims.py`, `src/specify_cli/upgrade/compat.py`
- Upgrade migrations: `m_2_0_6_`, `m_2_0_7_`, `m_2_1_3_`, `m_2_1_4_`, `m_3_1_2_`

**Note**: Upgrade migrations often reference runtime for asset path resolution — verify each migration's use of `specify_cli.runtime.home` is semantically equivalent to `runtime.discovery.home` before rewriting.

**Dependencies**: WP06

**Prompt file**: `tasks/WP09-source-file-occurrence-migration.md`

---

### WP10 — Test File Occurrence Migration

**Priority**: Medium
**Estimated prompt size**: ~310 lines
**Execution mode**: `code_change`
**Profile**: `implementer-ivan`
**Dependencies**: WP06

**Goal**: Apply `occurrence_map.yaml` rewrites to all ~30 test files that import from `specify_cli.next.*` or `specify_cli.runtime.*`. Run full suite to verify zero regressions.

**Known test files** (confirmed by scan; verify against occurrence_map.yaml):
- `tests/next/` (5 files): test_decision_unit.py, test_next_command_integration.py, test_prompt_builder_unit.py, test_query_mode_unit.py, test_runtime_bridge_unit.py
- `tests/runtime/` (8 files): test_agent_skills.py, test_bootstrap_unit.py, test_config_show_origin_integration.py, test_doctor_command_file_health.py, test_doctor_unit.py, test_e2e_runtime_integration.py, test_global_runtime_convergence_unit.py, test_home_unit.py, test_resolver_unit.py, test_show_origin_unit.py
- Mixed dirs (17 files): tests/agent, tests/audit, tests/concurrency, tests/contract, tests/init, tests/kernel, tests/merge, tests/specify_cli/cli/commands, tests/specify_cli/next, tests/specify_cli/runtime, tests/specify_cli/status, tests/status, tests/upgrade

**Subtasks**:
- [x] T037 Apply occurrence_map.yaml rewrites to `tests/next/` (5 files) (WP10)
- [x] T038 Apply occurrence_map.yaml rewrites to `tests/runtime/` (8 files) (WP10)
- [x] T039 Apply occurrence_map.yaml rewrites to remaining 17 test files (WP10)
- [x] T040 Validate WP10: run full `pytest tests/` to confirm zero regressions (WP10)

**Dependencies**: WP06

**Prompt file**: `tasks/WP10-test-file-occurrence-migration.md`

---

### WP11 — Migration Documentation + CHANGELOG

**Priority**: Low (can run in parallel with WP07–WP10)
**Estimated prompt size**: ~220 lines
**Execution mode**: `planning_artifact`
**Profile**: `architect-alphonso`

**Goal**: Write the user-facing migration guide for external callers and record the mission in CHANGELOG.md.

**Subtasks**:
- [x] T041 Write `docs/migration/runtime-extraction.md` (WP11)
- [x] T042 Update `CHANGELOG.md` Unreleased/Changed entry (WP11)

**Implementation sketch**:
1. `runtime-extraction.md`: follow the charter-extraction migration doc as template; include: motivation, import-path translation table (`specify_cli.next.decision → runtime.decisioning.decision`, etc.), code examples (before/after), deprecation timeline (removal in 3.4.0), contact/links
2. `CHANGELOG.md`: add under Unreleased/Changed: "Extracted runtime execution core (`specify_cli.next`, `specify_cli.runtime`) to canonical top-level `runtime` package. Legacy import paths emit `DeprecationWarning`; removal in 3.4.0. See `docs/migration/runtime-extraction.md`." Cite mission ID and charter exemplar.

**Dependencies**: None (can start as soon as WP01 establishes the translation table from occurrence_map.yaml)

**Prompt file**: `tasks/WP11-migration-documentation.md`

---

## Dependency Graph

```
WP01 (baseline + occurrence map)
  └─► WP02 (package skeleton + seams)
        ├─► WP03 (move next/)  ─────┐
        └─► WP04 (move runtime/) ───┤
                                    ├─► WP05 (CLI adapters)    ─┐
                                    └─► WP06 (shims + registry) ─┤
                                                                  ├─► WP07 (arch tests) ─► WP08 (regression + suite)
                                                                  ├─► WP09 (source migration)
                                                                  └─► WP10 (test migration)

WP11 (docs + changelog) — independent; can start after WP01
```

**Execution lanes**:
- **Lane A**: WP01 → WP02 → WP03 → WP05 → WP06 → WP07 → WP08
- **Lane B**: (after WP02) WP04 [parallel with WP03]
- **Lane C**: (after WP06) WP09 [parallel with WP07/WP08]
- **Lane D**: (after WP06) WP10 [parallel with WP09]
- **Lane E**: WP11 [independent]

**Critical path**: WP01 → WP02 → WP03+WP04 → WP05+WP06 → WP07 → WP08

---

## Success Criteria (from spec)

1. All 4 regression-fixture CLI commands produce identical `--json` output pre/post extraction
2. `tests/architectural/` reports zero forbidden edges for the `runtime` layer
3. Every CLI command module is a thin adapter — no inline state-transition decisioning
4. Every legacy import path emits `DeprecationWarning`; shim-registry CI check passes
5. `ProfileInvocationExecutor` boundary documented at `src/runtime/seams/`; `StepContractExecutor` Protocol scaffold in place
6. Full test suite passes; zero regressions
7. `docs/migration/runtime-extraction.md` exists; PR cites charter exemplar and ownership-map slice
