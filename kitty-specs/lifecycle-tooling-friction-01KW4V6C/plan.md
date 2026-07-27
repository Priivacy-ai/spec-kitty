# Implementation Plan: Mission-Lifecycle Tooling Friction

**Branch**: `mission/lifecycle-tooling-friction` | **Date**: 2026-06-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/lifecycle-tooling-friction-01KW4V6C/spec.md`

## Summary

Reconcile seven spec-kitty mission-lifecycle tooling/DX frictions (#2217–#2223) across six
file-disjoint lanes. Pre-planning squad (priti/alphonso/debbie/paula, live-repro'd on
`upstream/main c44a4fa82`) reshaped scope: #2219 verify-and-close (already fixed upstream);
#2220+#2221 folded into one WP-authoring-contract SSOT with a golden round-trip ratchet;
#2223 re-scoped to a finalize-tasks lint reusing the existing rule-engine; #2218 is the one
hidden-depth item (coord-branch lifecycle) and causally amplifies #2222 (sequence C before B).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml; internal `specify_cli.*`, `mission_runtime`, `doctrine.*`
**Storage**: Filesystem — `kitty-specs/<mission>/` (meta.json, traces/, issue-matrix.md), `.kittify/`, doctrine templates under `src/doctrine/missions/`
**Testing**: pytest (`tests/` unit/contract/integration + `tests/architectural/`); live CLI repro via scratch missions; diff-coverage critical-path gate
**Target Platform**: CLI (Linux/macOS), distributed to consumers via `spec-kitty init`/`upgrade`
**Project Type**: single (Python CLI)
**Performance Goals**: N/A — DX/correctness mission
**Constraints**: ruff + mypy zero issues, complexity ≤ 15, no `# type: ignore`; no regression on default paths (coord default, auto_commit=True); reuse existing authorities (don't fork); `topology: lanes`, no coord branch
**Scale/Scope**: 6 lanes / 7 issues (1 verify-close), 6 implementation concerns; ~8–12 source/doctrine files + tests; one new architectural/round-trip ratchet test

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Reuse-don't-rebuild (NFR-002, C-006)**: #2217 extends the existing ingestor seam; #2223 = one rule-engine / two call-sites; #2219 not re-implemented; #2220 fixes doctrine text (not the validator). ✅
- **No regression (NFR-001)**: `--topology` omitted → coord default byte-identical; `auto_commit=True` claim path unchanged. ✅ guarded by tests.
- **Quality gates (NFR-003)**: ruff/mypy clean, complexity ≤ 15, focused test per branch, diff-coverage ≥ 90% on critical paths. ✅
- **Canonical sources**: `--topology` uses the `MissionTopology` enum (C-002); the ownership validator is the path-form authority (C-004). ✅
- **No charter violations needing justification.** Complexity Tracking empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/lifecycle-tooling-friction-01KW4V6C/
├── spec.md / plan.md / research.md / issue-matrix.md
├── traces/  (approach / design-decisions / tooling-friction)
└── tasks.md (Phase 2)
```

### Source Code (repository root)

```
src/
├── doctrine/missions/software-dev/
│   ├── actions/tasks/guidelines.md          # IC-01 (#2220) — repo-relative
│   ├── mission-steps/software-dev/tasks/guidelines.md  # IC-01 (#2220) — 2nd copy
│   └── templates/task-prompt-template.md     # IC-01 (#2221) — frontmatter completion
├── specify_cli/
│   ├── core/mission_creation.py              # IC-02 (#2218) — conditional coord-branch mint
│   ├── cli/commands/lifecycle.py (+ agent/mission_create.py, missions/_create.py)  # IC-02 — --topology flag thread
│   ├── cli/commands/implement.py             # IC-03 (#2222) — exclude vcs-lock from dirty-tree guard
│   ├── mission_metadata.py                   # IC-03 — set_vcs_lock (reference)
│   ├── retrospective/generator.py            # IC-04 (#2217) — _load_traces ingestor + conditional data-model gap
│   ├── cli/commands/review/_issue_matrix.py  # IC-05 (#2223) — extract rule-engine
│   └── cli/commands/agent/mission_finalize.py# IC-05 — advisory lint call-site
└── (migration/backfill_topology.py — IC-06 #2219: reference/verify only, no change)

tests/   # per-lane red-first + the IC-01 golden round-trip ratchet + IC-06 blast-radius regression
```

**Structure Decision**: Single Python CLI project. Six file-disjoint lanes map onto existing
surfaces; no new modules except tests. The IC-05 rule-engine extraction stays within
`review/_issue_matrix.py` (export the engine; second caller imports it — no duplication).

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns, NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — WP-authoring contract SSOT (Lane A: #2220 + #2221)

- **Purpose**: Make the WP-frontmatter contract agree across doctrine-prose, template, and the validator; guard it with a round-trip test so it can't re-drift.
- **Relevant requirements**: FR-001, FR-002, FR-003, C-004.
- **Affected surfaces**: both `tasks/guidelines.md` copies (→ repo-relative); `templates/task-prompt-template.md` frontmatter (+ `owned_files`/`authoritative_surface`/`execution_mode`/`create_intent`); new golden round-trip test.
- **Sequencing/depends-on**: none.
- **Risks**: the two doctrine copies must stay aligned; the round-trip test must exercise the REAL validator + finalize path (not just template-exists), per paula.

### IC-02 — Create-time topology choice (Lane B: #2218)

- **Purpose**: `spec-kitty specify --topology <enum>` lets the operator choose topology at creation; coord-branch minting becomes conditional.
- **Relevant requirements**: FR-004, FR-005, C-002, NFR-001.
- **Affected surfaces**: `core/mission_creation.py` (conditional `ensure_coordination_branch`), the CLI→agent→core parameter funnel (`lifecycle.py`/`mission_create.py`/`missions/_create.py`), the `CreateMissionOutcome` dataclass; classify via the existing `classify_topology` SSOT.
- **Sequencing/depends-on**: pairs with IC-03 (C-005 — sequence C with/before B so create-time non-coord missions don't hit the lock friction).
- **Risks**: HIDDEN-DEPTH — a create-time `single_branch`/`lanes` mission is a third shape the coord-or-legacy fallbacks across implement/merge must handle; **requires an end-to-end non-coord implement+merge proof** (FR-005). Default coord (backward-compat).

### IC-03 — vcs-lock claim friction (Lane C: #2222)

- **Purpose**: Back-to-back claims under `auto_commit=False` aren't blocked by the first claim's vcs-lock self-write.
- **Relevant requirements**: FR-006, C-003, NFR-001.
- **Affected surfaces**: `implement.py` (the dirty-tree guard `_ensure_planning_artifacts_committed_git`) — exclude the lock-only meta change; `mission_metadata.py:set_vcs_lock` (reference).
- **Sequencing/depends-on**: land with/before IC-02 (C-005).
- **Risks**: the lock is in-process VCS-TYPE state, NOT the concurrency guard — excluding it opens no race; keep `auto_commit=True` byte-identical.

### IC-04 — Retrospect tracer ingestion (Lane D: #2217)

- **Purpose**: `retrospect` sources findings/proposals from `traces/*.md`; absent `data-model.md` is N/A for no-entity missions.
- **Relevant requirements**: FR-007, FR-008, NFR-002.
- **Affected surfaces**: `retrospective/generator.py` — add a `_load_traces` reader to the existing ingestor seam (`_build_ingestor_findings`); make the data-model gap conditional on domain entities.
- **Sequencing/depends-on**: none.
- **Risks**: best-effort ingest (malformed/empty tracers must not crash); extend the seam, do not fork the generator.

### IC-05 — Issue-matrix finalize-tasks lint (Lane E: #2223)

- **Purpose**: An advisory issue-matrix lint at finalize-tasks time, reusing the approve-gate rule engine (one engine, two callers).
- **Relevant requirements**: FR-009, NFR-002.
- **Affected surfaces**: `review/_issue_matrix.py` (export the rule engine `validate_issue_matrix` + the completeness scan); `agent/mission_finalize.py` (advisory call-site).
- **Sequencing/depends-on**: none.
- **Risks**: must NOT reimplement rules (drift); the tasks-time lint is advisory (never blocks finalize).

### IC-06 — Backfill-topology verify + regression + close (Lane F: #2219)

- **Purpose**: Prove `migrate backfill-topology --mission X` touches only X; close #2219 `verified-already-fixed`.
- **Relevant requirements**: FR-010, C-006.
- **Affected surfaces**: new regression test asserting single-mission scope leaves siblings byte-identical (the 203-file blast-radius guard). No production change (fix already upstream).
- **Sequencing/depends-on**: none.
- **Risks**: confirm via cross-check the upstream fix (`--mission` scope + `read_topology`) is wired into the planning/inspection paths; do not re-implement.
