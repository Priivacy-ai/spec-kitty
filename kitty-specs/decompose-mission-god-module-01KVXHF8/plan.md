# Implementation Plan: Decompose `agent/mission.py` god-module (remainder) (#2056)

**Branch**: `prog/2056-mission` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)
**Input**: Mission specification from `kitty-specs/decompose-mission-god-module-01KVXHF8/spec.md`

## Summary

`src/specify_cli/cli/commands/agent/mission.py` is a 4125 LOC / 62-def god-module that hosts the
8-subcommand `agent mission` CLI. Three command functions are mega-functions (`finalize_tasks` 1227 LOC,
`setup_plan` 507, `create_mission` 281). The planning-commit pipeline was already extracted to
`coordination/commit_router.py` (mission 01KVMBD6). This mission decomposes the REMAINDER into 4 cohesive,
independently-testable seams behind a thin command-registration shim, internally decomposes the 3
mega-functions to `<=15` complexity, re-exports every test-patched symbol (~100) so existing patch targets
keep resolving with zero churn, and relocates the LIVE planning-commit residue
(`_planning_commit_worktree`/`_resolve_planning_placement`/`_stage_finalize_artifacts_in_coord_worktree`)
into `commit_router.py` with `tasks.py` repointed. Pure behavior-preserving refactor (profile
`randy-reducer`); CLI surface stays byte-for-byte. The technical approach is dictated by the resolved
research (seam map in research.md, topology in data-model.md): extract Seam D first (stable resolution
surface), then C, A, B-per-family, with each mega-function decomposed in the WP that moves its command.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `typer` (CLI), `rich` (console), `mission_runtime` (CommitTarget,
MissionArtifactKind, topology), `coordination.commit_router` (commit_for_mission pipeline),
`status` package, `core.*`, `sync.*`.
**Storage**: N/A (no persistent data structures change; this is a code-topology refactor).
**Testing**: `pytest` (≈50 existing mission-touching test files) + new focused unit tests per seam and
per phase helper + a NEW golden CLI characterization test (`typer.testing.CliRunner`).
**Target Platform**: Linux/macOS dev + CI.
**Project Type**: single (Python package `src/specify_cli`).
**Performance Goals**: N/A (no hot path changed). Import-time must not regress (keep lazy imports for
`commit_for_mission` / `CoordinationWorkspace`).
**Constraints**: maxCC `<=15` (ruff C901 / Sonar S3776); ≥90% new-code coverage; `ruff` + `mypy --strict`
clean; no new suppressions; CLI surface byte-for-byte frozen; no import cycles (seams → lower layers only;
`commit_router` never imports `mission`/seams).
**Scale/Scope**: 1 god-module (4125 LOC, 62 defs) → 1 thin shim + ~9 seam modules + relocation into 1
existing module (`commit_router.py`) + 1 import repoint (`tasks.py`). ~100 re-exports preserved.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Terminology Canon** — PASS. No new `feature*` aliases introduced; existing param name `feature`
  (alias surface for `--mission`) is preserved verbatim, not renamed (renaming would break the flag).
  Canonical "Mission" used in all new prose.
- **Canonical sources, never improvise** — PASS. The relocated planning-commit residue lands in the
  canonical `coordination/commit_router.py` (C-002), not a hand-rolled new module. Seams import canonical
  lower layers.
- **No new suppressions** — PASS by design (NFR-004 / C-004).
- **Complexity ceiling 15** — PASS by design (NFR-001 drives the mega-function decomposition).
- **Every new branch/helper needs tests in the same PR** — PASS by design (FR-004 / FR-005 / NFR-002).
- **Git workflow** — PASS. Planning on `prog/2056-mission`; merge target `main` (non-protected program
  branch flow); no direct origin/main push.

**No charter violations.** Complexity Tracking table below is therefore empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/decompose-mission-god-module-01KVXHF8/
├── plan.md              # This file
├── spec.md              # Mission spec (FR-001..FR-007, NFRs, constraints)
├── research.md          # Seam map (62-def inventory, mega-functions, coupling)
├── data-model.md        # Target topology + invariants INV-1..INV-9
├── quickstart.md        # How to verify the refactor locally
├── contracts/
│   └── cli-surface-contract.md   # Frozen 8-command × all-flags contract
├── checklists/
│   └── requirements.md
├── tasks.md             # Work-package manifest (linear chain)
└── tasks/               # WP prompt files
```

### Source Code (repository root)

```
src/specify_cli/cli/commands/agent/
  mission.py                      # THIN SHIM: app=Typer(name="mission"), registers 8 commands,
                                  #   re-exports ~100 previously-importable / test-patched symbols.
                                  #   #2056 pointer comment. No business logic. (Final WP owns this file.)
  mission_feature_resolution.py   # Seam D — _find_feature_directory & friends, _safe_load_meta,
                                  #   _read_feature_meta, _build_setup_plan_detection_error,
                                  #   _list_feature_spec_candidates, _sole_mission_slug_or_none,
                                  #   _resolve_mission_dir_name_primary_anchored, _primary_anchored_feature_dir
  mission_parsing.py              # Seam C — tasks.md/spec.md parsers, owned-files validation,
                                  #   JSON emit shims (_emit_json/_with_cli_version/_with_mission_aliases/
                                  #   _emit_console_or_json_error/_utc_now_iso)
  mission_record_analysis.py      # Seam A — record_analysis + _enforce_analysis_report_write_preflight +
                                  #   _resolve_record_analysis_placement_ref
  mission_branch_context.py       # Seam B — branch_context + _inject_branch_contract + branch helpers
  mission_create.py               # Seam B — create_mission (internally decomposed to phase helpers)
  mission_check_prerequisites.py  # Seam B — check_prerequisites + emit helpers
  mission_setup_plan.py           # Seam B — setup_plan (internally decomposed) + _commit_to_branch +
                                  #   CommitToBranchResult + _kind_for_artifact + _artifact_* helpers
  mission_finalize.py             # Seam B — finalize_tasks (internally decomposed) + finalize helpers
                                  #   (_collect_finalize_artifacts etc.)
  mission_accept_merge.py         # Seam B — accept_feature, merge_feature, worktree helpers

src/specify_cli/coordination/
  commit_router.py                # EXISTING — RECEIVES relocated _planning_commit_worktree /
                                  #   _resolve_planning_placement / _stage_finalize_artifacts_in_coord_worktree;
                                  #   reconciles _stage_finalize_artifacts_in_coord_worktree against existing
                                  #   _stage_artifacts_in_coord_worktree. (commit_router-relocation WP owns this.)

src/specify_cli/cli/commands/agent/
  tasks.py                        # EXISTING — single function-local import line repointed from
                                  #   mission to commit_router. (commit_router-relocation WP touches this
                                  #   one line; out-of-map, documented.)
```

**Structure Decision**: **Sibling-module layout** (not a `mission/` package). `mission.py` stays the
import anchor `specify_cli.cli.commands.agent.mission` and becomes a thin shim re-exporting from sibling
`mission_*.py` modules. This preserves the import path and every `mission.<name>` patch target with the
smallest diff (no `__init__.py` redirection, no package-relative import rewrites). Each seam is one module
with one matching test module under `tests/specify_cli/cli/commands/agent/`. The planning-commit residue
relocates into the canonical `coordination/commit_router.py`; `tasks.py`'s import line is repointed there.

## Complexity Tracking

*No charter violations — table intentionally empty.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into a
> STRICTLY-LINEAR WP chain (WP02 deps WP01, …). One concern may fold the relevant mega-function
> decomposition into its seam WP.

### IC-01 — Frozen CLI contract & golden characterization harness

- **Purpose**: Capture the byte-for-byte `agent mission` CLI surface (8 commands × all flags + JSON
  envelopes for success/error) as an executable golden test BEFORE any extraction, so every later WP can
  prove byte-for-byte preservation.
- **Relevant requirements**: FR-001, C-001, C-005, INV-1, INV-2.
- **Affected surfaces**: NEW `tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py`;
  reads `contracts/cli-surface-contract.md`. Extends `tests/integration/test_json_envelope_strict.py`.
- **Sequencing/depends-on**: none (must run first).
- **Risks**: Missing a flag/default in the golden snapshot would let a later regression slip — derive the
  snapshot directly from `CliRunner` `--help` output for `app` and each subcommand, not from memory.

### IC-02 — Feature-dir resolution seam (Seam D)

- **Purpose**: Extract the shared, most-patched (`_find_feature_directory` 39×) resolution surface FIRST so
  Seams A/B/C import a stable surface rather than each other.
- **Relevant requirements**: FR-003, FR-004, FR-006, NFR-001, NFR-005, INV-3, INV-8.
- **Affected surfaces**: NEW `mission_feature_resolution.py` + test; small documented out-of-map import
  edits in `mission.py` (shim re-export) deferred to the final WP.
- **Sequencing/depends-on**: IC-01.
- **Risks**: `_build_setup_plan_detection_error` is also imported by `lifecycle.py` — must remain
  re-exported at `mission.<name>` (INV-4).

### IC-03 — Parsing & validation seam (Seam C)

- **Purpose**: Extract the (mostly pure) tasks.md/spec.md parsers, owned-files validation, and JSON emit
  shims; give the pure parsers DIRECT unit tests (current gap — only indirect coverage via finalize).
- **Relevant requirements**: FR-003, FR-004, FR-006, NFR-001, NFR-002, INV-3.
- **Affected surfaces**: NEW `mission_parsing.py` + test. `tasks.py` imports
  `_parse_requirement_refs_from_tasks_md` — must remain resolvable (via shim re-export).
- **Sequencing/depends-on**: IC-02.
- **Risks**: JSON emit shims (`_emit_json`/`_with_cli_version`/`_with_mission_aliases`) are central to the
  envelope contract — extraction must not alter envelope keys (INV-2).

### IC-04 — Record-analysis seam (Seam A)

- **Purpose**: Extract `record_analysis` + its 2 dedicated helpers — the lowest-risk command slice.
- **Relevant requirements**: FR-003, FR-004, FR-006, NFR-001, INV-1, INV-3.
- **Affected surfaces**: NEW `mission_record_analysis.py` + test. Imports Seam C/D surfaces +
  `commit_router.commit_for_mission` (lazy) + `analysis_report.write_analysis_report`.
- **Sequencing/depends-on**: IC-03.
- **Risks**: low — 2 dedicated test files already exist; extend, don't replace.

### IC-05 — Lifecycle command families (Seam B) + mega-function decomposition

- **Purpose**: Split the 7 lifecycle commands per family into per-command modules, and internally
  decompose the 3 mega-functions (`finalize_tasks` 1227, `setup_plan` 507, `create_mission` 281) into
  `<=15`-CC phase helpers as they move. Each phase helper gets a focused test.
- **Relevant requirements**: FR-003, FR-004, FR-005, FR-006, NFR-001, NFR-002, INV-1, INV-3, INV-6.
- **Affected surfaces**: NEW `mission_branch_context.py`, `mission_create.py`,
  `mission_check_prerequisites.py`, `mission_setup_plan.py`, `mission_finalize.py`,
  `mission_accept_merge.py` + tests.
- **Sequencing/depends-on**: IC-04 (and each family WP depends linearly on the prior family WP).
- **Risks**: `finalize_tasks --validate-only` zero-mutation invariant (INV-6) must survive phase
  extraction — pin with existing readonly test + assert the write phase is unreachable when validate_only.
  `accept`/`merge` are thin delegators (INV — A-3) and must not pull the full accept/merge graph at module
  top level.

### IC-06 — Planning-commit residue relocation (LIVE → commit_router) + tasks.py repoint

- **Purpose**: Relocate `_planning_commit_worktree`, `_resolve_planning_placement`,
  `_stage_finalize_artifacts_in_coord_worktree` into `coordination/commit_router.py`, reconcile against the
  existing near-duplicate `_stage_artifacts_in_coord_worktree`, and repoint `tasks.py`'s import. These are
  LIVE on this base — relocate, never delete.
- **Relevant requirements**: FR-007, C-002, NFR-005, INV-5, INV-7, INV-8.
- **Affected surfaces**: `coordination/commit_router.py` (owned by this WP) + test;
  `tasks.py` single import line (out-of-map, documented).
- **Sequencing/depends-on**: IC-05 (after the finalize seam moves, so the residue's last in-mission
  references are gone and the move targets a clean boundary).
- **Risks**: import cycle if `commit_router` imports back from `mission`/seams (INV-8) — keep one-way;
  reconcile the staging helper rather than forking a duplicate (research O-2).

### IC-07 — Shim finalization: #2056 pointer comment + ~100 re-export sweep + full gate sweep

- **Purpose**: Reduce `mission.py` to a thin shim: `app` + 8 command registrations + the complete
  re-export block (every test-patched name) + the #2056 pointer comment; run the full ruff/mypy/coverage
  gate sweep.
- **Relevant requirements**: FR-001, FR-002, FR-006, NFR-001..004, SC-1..SC-8, INV-1..INV-9.
- **Affected surfaces**: `mission.py` (SOLE owner of this file across the whole mission).
- **Sequencing/depends-on**: IC-06.
- **Risks**: a missed re-export breaks `@patch("...mission.<name>")` somewhere — enumerate the full set
  from the patch survey (research §5) and assert it with a re-export presence test.
