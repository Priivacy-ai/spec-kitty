# Implementation Plan: Decompose `doctor.py` God-Module (Residual)

**Branch**: `prog/2059-doctor` (planning = merge base; lands on `main` via PR) | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/decompose-doctor-god-module-01KVXHFB/spec.md`

## Summary

Decompose the **residual** of `src/specify_cli/cli/commands/doctor.py` (3434 LOC, 16 subcommands, 11 helper clusters) into cohesive sibling modules plus a thin orchestration surface, **completing the doctrine-health collector seam #1623 left behind** and **mirroring the `_doctrine_health.py` sibling-module precedent**. This is a behavior-preserving refactor: the public `spec-kitty doctor` CLI surface stays byte-for-byte identical (all 16 subcommand names, flags, help text, exit codes). Technical approach (from research): thin `@app.command` shells stay in `doctor.py` and delegate to per-cluster sibling entrypoints; shared infra (`console`/guards/constants) is centralized in a new `_doctor_shared.py` extracted FIRST; the 11 test-facing private symbols are re-exported from the `doctor` shim. A golden CLI characterization harness is captured FIRST to prove byte-identity before each extraction. The six >15-CC mega-functions are decomposed into ≤15-CC tested helpers as part of their cluster's WP.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `typer`, `rich` (Console/Table); first-party `specify_cli.core`, `specify_cli.status`, `specify_cli.doctor.ops`, `specify_cli.tool_surface`, `specify_cli.git.sparse_checkout`, `specify_cli.skills`, `specify_cli.compat`, `specify_cli.state.doctor` (all consumed via the existing function-local import pattern).
**Storage**: N/A (CLI diagnostics; reads project state on disk, no new persistence).
**Testing**: `pytest` (+ `ruff check --select C901` complexity gate, `mypy --strict`). New per-sibling focused unit tests; golden CLI characterization test enumerating `app.registered_commands` and snapshotting per-subcommand `--help`.
**Target Platform**: Linux/macOS CLI (the `spec-kitty` tool).
**Project Type**: single (Python package `src/specify_cli/`).
**Performance Goals**: No regression; preserve the deliberate function-local import pattern that keeps `doctor` import cheap.
**Constraints**: `maxCC ≤ 15`; per-sibling coverage `≥ 90%`; `ruff` + `mypy --strict` clean with zero new suppressions; CLI surface byte-identical; one-way import graph; single `Console()` instance; `merge.path_is_under_worktrees` import stays function-local.
**Scale/Scope**: One 3434-LOC module → ~≤400-LOC orchestration shim + 9 new sibling modules (beside 2 existing #1623 siblings); 16 subcommands unchanged; 6 mega-functions decomposed.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Terminology Canon** — refactor touches no user-facing prose/domain objects; `Mission` vocabulary unaffected. No `feature*` aliases introduced. PASS.
- **Git workflow** — planning on `prog/2059-doctor`; lands on `main` via PR only; no direct push to `origin/main`. PASS.
- **Canonical sources** — extraction mirrors the canonical `_doctrine_health.py`/`_profile_health_render.py` sibling precedent (#1623); no improvised packaging convention; no `_misc` catch-all. PASS.
- **Sonar / complexity ceiling** — every function ≤15 CC post-extraction; mega-functions decomposed with focused tests in the same WP; no new suppressions. PASS by construction (NFR-001/003).
- **Behavior preservation** — no command/flag/name/output/exit-code change; proven by the WP01 golden harness. PASS.

**No constitution violations.** Complexity Tracking section below is empty (nothing to justify).

## Project Structure

### Documentation (this mission)

```
kitty-specs/decompose-doctor-god-module-01KVXHFB/
├── plan.md              # This file
├── research.md          # doctor.py seam map (16 subcommands, 11 clusters, hazards H1/H2)
├── data-model.md        # target module topology + invariants I-1..I-8
├── quickstart.md        # operator/maintainer verification steps
├── contracts/
│   └── cli-surface-contract.md   # frozen `doctor` CLI contract (all 16 subcommands)
├── checklists/
│   └── requirements.md
└── tasks.md             # WP chain (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/specify_cli/cli/commands/
├── doctor.py                  # ORCHESTRATION SHIM (target ≤ ~400 LOC): app + 16 thin
│                              #   @app.command shells → delegate to siblings; re-export
│                              #   block (11 private symbols + app + SlashCommandGap);
│                              #   import console/guards/constants from _doctor_shared
├── _doctor_shared.py          # NEW (WP02): canonical console/guards/constants home (H1)
├── _doctrine_health.py        # EXISTING (#1623): health MODEL — UNCHANGED
├── _profile_health_render.py  # EXISTING (#1623): doctrine RENDER + console — UNCHANGED
├── _doctrine_collect.py       # NEW (WP03): doctrine-health COLLECTORS — completes #1623 seam
├── _identity_audit.py         # NEW (WP04): identity + topology
├── _command_surface_doctor.py # NEW (WP05): tool-surface + command-skill + slash (skills CC20)
├── _mission_state_doctor.py   # NEW (WP06): mission-state audit/repair/teamspace-dry-run
├── _coordination_doctor.py    # NEW (WP07): git-version + worktree/sparse-drift health (H2)
├── _sparse_checkout_doctor.py # NEW (WP08): sparse-checkout remediation render/flow
├── _workspace_husk_doctor.py  # NEW (WP09): workspace-husk
└── _daemon_doctor.py          # NEW (WP10): orphan-daemons + restart-daemon bodies

tests/specify_cli/cli/commands/
├── test_doctor_cli_surface_golden.py   # NEW (WP01): golden characterization harness
├── test_doctor_shared.py               # NEW (WP02)
├── test_doctrine_collect.py            # NEW (WP03)
├── test_identity_audit.py              # NEW (WP04)
├── test_command_surface_doctor.py      # NEW (WP05)
├── test_mission_state_doctor.py        # NEW (WP06)
├── test_coordination_doctor.py         # NEW (WP07)
├── test_sparse_checkout_doctor.py      # NEW (WP08)
├── test_workspace_husk_doctor.py       # NEW (WP09)
└── test_daemon_doctor.py               # NEW (WP10)
```

**Structure Decision**: **Orchestration shim + sibling modules.** `doctor.py` retains `app = typer.Typer(name="doctor", ...)`, every `@app.command` (as a thin shell), the re-export block, and the shared-infra import. All cluster logic moves to the nine new siblings listed above, beside the two existing #1623 siblings. This is research recommendation (a) — lowest CLI-surface risk, mirrors the existing `mission_state` dispatch-thin pattern. Small clusters that already thin-delegate to external packages (state-roots → `state.doctor`, shim-registry → `compat`, ops/invocation → `doctor.ops`) keep their thin shells in `doctor.py`; only cohesive private helpers move (the final WP decides per OQ2). No `_misc` catch-all.

## Complexity Tracking

*No constitution violations — section intentionally empty.*

## Implementation Concern Map

The WP chain is **strictly linear** (WP02 deps WP01, WP03 deps WP02, …, WP11 deps WP10) because every extraction shares the single owner `doctor.py` (each WP performs the in-place delegation edit + re-export touch) and every sibling imports the `_doctor_shared` surface that WP02 stabilizes. Linear ordering eliminates `doctor.py` write-contention between lanes.

| IC | Concern | WP | Siblings / functions | FRs | Hazard |
|----|---------|----|----|-----|--------|
| IC-00 | Golden CLI characterization harness (byte-identical proof) — lands FIRST | WP01 | `test_doctor_cli_surface_golden.py` (all 16 names/flags/help/exit-codes; covers `doctor skills`, `doctor restart-daemon`, `doctor sparse-checkout --fix`) | FR-001, FR-002 | C-005 |
| IC-01 | Shared-infra single home — extracted FIRST so siblings import a stable surface | WP02 | `_doctor_shared.py` (console/guards/constants/`_is_interactive_environment`) | FR-007 | **H1** |
| IC-02 | Doctrine-health COLLECTOR seam completion | WP03 | `_doctrine_collect.py` (Cluster J collectors) | FR-003, FR-004, FR-006 | — |
| IC-03 | Identity + topology | WP04 | `_identity_audit.py`; decompose `identity` CC19 | FR-003, FR-004, FR-005, FR-006 | — |
| IC-04 | Tool-surface + command-skill + slash | WP05 | `_command_surface_doctor.py`; decompose `skills` CC20 + `_repair_command_skill_state` CC16 | FR-003, FR-004, FR-005, FR-006 | — |
| IC-05 | Mission-state audit/repair/teamspace | WP06 | `_mission_state_doctor.py`; drop `mission_state` `# noqa: C901` if helpers move | FR-003, FR-004 | — |
| IC-06 | Coordination / git-health | WP07 | `_coordination_doctor.py`; decompose `_check_lane_sparse_checkout_drift` CC19 | FR-003, FR-004, FR-005, FR-007 | **H2** |
| IC-07 | Sparse-checkout remediation | WP08 | `_sparse_checkout_doctor.py`; decompose `sparse_checkout` cmd CC19 | FR-003, FR-004, FR-005 | — |
| IC-08 | Workspace-husk | WP09 | `_workspace_husk_doctor.py` | FR-003, FR-004 | — |
| IC-09 | Daemon (orphan + restart) | WP10 | `_daemon_doctor.py` | FR-003, FR-004 | — |
| IC-10 | Shim re-export sweep + pointer verify + state-roots CC17 decompose + full gate sweep | WP11 | `doctor.py` (sole owner): 11 re-exports, `state_roots` CC17 decompose, pointer-comment verify, ruff/mypy/golden green | FR-001, FR-002, FR-005, FR-006, FR-007 | — |

### Circular-import hazard handling

- **H1 (shared console/guards):** WP02 extracts `_doctor_shared.py` FIRST as the single canonical home for `console`, `_json_output_guard`, `_json_error`, and constants. Every later sibling (WP03–WP10) and the orchestrator import from `_doctor_shared` — never re-instantiate `Console()`. This makes the import direction strictly one-way (orchestrator → sibling → `_doctor_shared` → external) and prevents a sibling↔orchestrator cycle. Enforced by a grep gate + the byte-pinned doctrine-selections snapshot.
- **H2 (`merge` cross-import):** WP07 (`_coordination_doctor.py`) keeps the `from specify_cli.cli.commands.merge import path_is_under_worktrees` import **inside `_check_tracked_worktrees_content`** (function-local). Hoisting it to module scope reintroduces the `doctor↔merge` module-load cycle. The WP body and reviewer guidance explicitly forbid the hoist; an import-graph check guards it.

## Parallel Work Analysis

### Dependency Graph

```
WP01 → WP02 → WP03 → WP04 → WP05 → WP06 → WP07 → WP08 → WP09 → WP10 → WP11
(golden) (shared) (doctrine-collect) (identity) (cmd-surface) (mission-state)
         (coordination=WP07) (sparse=WP08) (husk=WP09) (daemon=WP10) (shim sweep=WP11)
```

Strictly linear — single sequential chain, no parallel waves.

### Work Distribution

- **Sequential work**: All 11 WPs run in order. WP01 (golden harness) gates everything; WP02 (`_doctor_shared`) gates every sibling extraction; the final WP11 owns the `doctor.py` re-export sweep + pointer verify + full gate run.
- **Parallel streams**: None — the shared `doctor.py` owner and the `_doctor_shared` dependency force linearization.
- **Agent assignments**: `randy-reducer` profile (semantic-compression / behavior-preserving reduction) for every WP.

### Coordination Points

- **Sync schedule**: each WP merges back to `prog/2059-doctor` before the next claims; the golden harness (WP01) re-runs at the end of every extraction WP to prove byte-identity.
- **Integration tests**: the WP01 golden characterization test + the existing 58 doctor test files + `tests/cli_gate/test_doctor_modes.py` / `test_safe_commands.py` run green after each WP; `ruff check --select C901` clean; `mypy --strict` clean.
