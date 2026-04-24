# Implementation Plan: CLI Interview Decision Moments

**Branch**: `main` (landing directly) | **Date**: 2026-04-23 | **Spec**: [spec.md](spec.md)
**Mission**: `cli-interview-decision-moments-01KPWT8P` (mid8: `01KPWT8P`)

## Summary

Add a CLI-owned Decision Moment ledger to `spec-kitty`. New `spec-kitty agent decision {open, resolve, defer, cancel, verify}` subgroup mints ULID `decision_id`s at ask time, writes a flat paper trail under `kitty-specs/<mission>/decisions/` (`index.json` + `DM-<decision_id>.md`), and appends `DecisionPointOpened(interview)` / `DecisionPointResolved(interview)` events to existing `kitty-specs/<mission>/status.events.jsonl`. Charter's Q&A loop calls the new API directly. Specify/plan templates are updated so the LLM calls the same API at ask time and resolution time. Dep `spec-kitty-events` moves to `==4.0.0` (vendored copy refreshed). Local-first; no SaaS.

## Technical Context

**Language/Version**: Python 3.11+ (repo baseline).
**Primary Dependencies (existing):** typer, rich, ruamel.yaml, httpx, pyyaml, readchar. Dev/test: pytest, mypy, ruff.
**Dependency change:** `spec-kitty-events` 3.3.0 → 4.0.0. Refresh `src/specify_cli/spec_kitty_events/` vendored copy from 4.0.0 source.
**Storage**: Filesystem only. New files under `kitty-specs/<mission>/decisions/`. Events to existing `status.events.jsonl`. `python-ulid>=1.1.0` for decision_id minting.
**Testing**: pytest; new suites under `tests/specify_cli/decisions/` and extensions to `tests/specify_cli/cli/commands/`.
**Target Platform**: macOS/Linux CLI.
**Project Type**: Single CLI library.
**Performance Goals**: ≤200 ms p95 per decision op with index up to 1000 decisions (NFR-001).
**Constraints**: Atomic writes (tmp+rename). Deterministic JSON. mypy clean on changed modules. ruff clean. Full suite wall time +10% ceiling.
**Scale/Scope**:
- 6 new CLI subcommands under `decision`.
- ~4 new runtime modules under `src/specify_cli/decisions/`.
- 1 new CLI command module `src/specify_cli/cli/commands/decision.py`.
- ~2 existing files extended: `charter.py`, `main.py` (subgroup registration).
- 2 SOURCE templates updated: `specify.md`, `plan.md` under `missions/software-dev/command-templates/`.
- Vendored events copy refresh.
- pyproject.toml dep pin bump.
- New tests.

## Charter Check

**PASS**, no waivers.

- Intent (CLI for ordered spec/plan/tasks workflows): strengthened.
- Stack constraints (Python 3.11+, typer/rich/ruamel/pytest): satisfied.
- Testing gate (unit+integration, coverage): NFR-004 binds ≥90% coverage of new code; NFR-005 keeps full suite green.
- Quality gates (ruff + mypy + pytest): all bound by NFRs.
- DIRECTIVE_003 decision documentation: research.md records R-1..R-7.
- DIRECTIVE_010 spec fidelity: every FR maps to a concrete module/file in data-model + plan.

Will re-check after Phase 1 design.

## Project Structure

### Documentation (this feature)

```
kitty-specs/cli-interview-decision-moments-01KPWT8P/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── README.md
│   ├── cli-contracts.md
│   ├── index_entry.schema.json
│   ├── decision_open_response.schema.json
│   ├── decision_terminal_response.schema.json
│   └── decision_verify_response.schema.json
├── spec.md
├── checklists/
└── tasks.md            # created later by /spec-kitty.tasks
```

### Source Code (repository root)

```
src/specify_cli/
├── decisions/                                  # NEW module
│   ├── __init__.py
│   ├── models.py                               # DecisionMoment, IndexEntry, error enums
│   ├── store.py                                # index.json + DM-<id>.md atomic I/O
│   ├── emit.py                                 # wraps status emitter with DecisionPoint events
│   ├── verify.py                               # verify command logic
│   └── service.py                              # open/resolve/defer/cancel public API
├── cli/commands/
│   ├── decision.py                             # NEW — typer subgroup for `spec-kitty agent decision ...`
│   └── charter.py                              # EXTEND — wire decision calls into existing interview loop
├── cli/main.py                                 # EXTEND — register `decision` subgroup
├── missions/software-dev/command-templates/
│   ├── specify.md                              # EXTEND — LLM instructions for decision open/resolve
│   └── plan.md                                 # EXTEND — same for plan interview
└── spec_kitty_events/                          # REFRESH — vendored 4.0.0 copy

tests/specify_cli/
├── decisions/                                  # NEW
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_store.py
│   ├── test_emit.py
│   ├── test_service_idempotency.py
│   ├── test_service_terminal.py
│   └── test_verify.py
└── cli/commands/
    ├── test_decision.py                        # NEW — CLI integration
    └── test_charter.py                         # EXTEND — charter emits decision events

pyproject.toml                                  # EXTEND — spec-kitty-events==4.0.0
```

**Structure Decision**: Mirror the existing `src/specify_cli/status/` package pattern (models / store / emit / service split). Charter integration is a narrow edit in `charter.py` wrapping the existing Q&A loop. Specify/plan integration is template-only (per spec: CLI does NOT patch doc bodies). Vendored events copy replaced wholesale from 4.0.0.

## Complexity Tracking

No violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(none)_  | _(n/a)_    | _(n/a)_                             |

## Branch Strategy (final restatement)

- Current branch: `main`
- Planning/base branch: `main`
- Final merge target: `main`
- `branch_matches_target`: `true`
- No worktree created here; worktrees allocated by `/spec-kitty.tasks` → `spec-kitty next --agent <name> --mission 01KPWT8P`.

## Next Command

Run `/spec-kitty.tasks --mission 01KPWT8P` to generate work packages.
