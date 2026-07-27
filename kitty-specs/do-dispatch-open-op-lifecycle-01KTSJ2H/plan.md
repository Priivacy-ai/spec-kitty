# Implementation Plan: Do Dispatch Open-Op Lifecycle

**Branch**: `kitty/mission-do-dispatch-open-op-lifecycle-01KTSJ2H` | **Date**: 2026-06-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/spec.md`

## Summary

`spec-kitty do` currently auto-closes its Op record with `outcome="done"` at dispatch time (`src/specify_cli/cli/commands/do_cmd.py:153`), producing false audit records. This mission converts `do` to the open→work→close lifecycle that `ask`/`advise` already follow: `do` opens the Op and prints the close contract; the host agent does the work and closes via `profile-invocation complete` with a real outcome; Claude Code session presence surfaces open Ops; `doctor ops --close-stale` sweeps stale orphans to `abandoned`. The `InvocationRecord` schema is split into distinct started/completed event models (completed requires a non-null outcome and carries a `closed_by` discriminator), legacy records are migrated (rewrite-or-delete), and `do` gains the SaaS propagator that `ask`/`advise` already have. The SaaS envelope changes shape freely with the new schema (decision 01KTSJEQANMNEV16WMSAJP6FR1) — SaaS handlers are unimplemented (#1720/#1693), so CLI behavior locks first.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), rich (console output), pydantic v2 (event models), existing `specify_cli.invocation` package (executor, router, writer, propagator)
**Storage**: Append-only JSONL files under `kitty-ops/` (one file per Op + `ops-index.jsonl`); evidence under `.kittify/evidence/<id>/`; no database
**Testing**: pytest (unit + CLI integration via typer runner), mypy --strict, ruff; ≥90% coverage on new code (charter policy)
**Target Platform**: CLI on macOS/Linux developer machines; 19 host harnesses consume the output, hook work scoped to Claude Code
**Project Type**: Single project (`src/specify_cli/` + `tests/`)
**Performance Goals**: `do` dispatch latency regression ≤10%; `doctor ops --close-stale` <5 s at 10,000 Op files (NFR-001/NFR-002)
**Constraints**: Append-only JSONL contract preserved (C-004); breaking changes allowed, no compat flags (C-001); canonical templates edited at source under `src/doctrine/` and `session_presence/content.py`, never generated agent copies (C-005); `dispatch` rename out of scope (C-002)
**Scale/Scope**: ~6 modules in `src/specify_cli/invocation/`, 2 CLI command files, doctor ops module, session-presence content, 1 upgrade migration, doctrine skill/template text

## Charter Check

*GATE: evaluated against `.kittify/charter/charter.md`.*

- **Stack compliance**: typer/rich/pydantic/pytest/mypy — all already in use by the touched modules. PASS.
- **DIRECTIVE_001 (Architectural Integrity)**: The change strengthens an existing boundary (record lifecycle owned by `invocation` package; CLI commands stay thin). No new packages or layers. PASS.
- **DIRECTIVE_003 (Decision Documentation)**: Lifecycle decision recorded in spec + decision 01KTSJEQANMNEV16WMSAJP6FR1 (SaaS envelope freedom). The schema split rationale is captured in research.md R2. PASS.
- **Coverage/typing**: ≥90% new-code coverage, mypy --strict, zero suppressions — carried as NFR-003. PASS (enforced at review).
- **Re-check after Phase 1**: design artifacts introduce no charter conflicts (no new dependencies, no new top-level packages).

## Project Structure

### Documentation (this mission)

```
kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── op-record-events.md      # Started/completed event schemas + JSONL file contract
│   ├── cli-do-output.md         # do command output contract (rich + JSON)
│   └── doctor-ops-close-stale.md # doctor ops sweep contract
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — not created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── invocation/
│   ├── record.py          # SPLIT: OpStartedEvent / OpCompletedEvent models (+ legacy parse helpers)
│   ├── writer.py          # write_completed gains closed_by; serialization drops blank defaults
│   ├── executor.py        # complete_invocation signature: closing actor; do gains propagator wiring
│   ├── propagator.py      # envelope builders follow new event shapes (free-form change)
│   └── modes.py           # unchanged (mode gate logic reused)
├── cli/commands/
│   ├── do_cmd.py          # remove auto-close; add propagator; new capsule close-contract text (rich+JSON)
│   └── advise.py          # shared close surface: `profile-invocation complete` outcome/evidence unchanged API
├── doctor/
│   └── ops.py             # list_orphan_ops + new close_stale_ops(threshold)
├── cli/commands/doctor*.py # `doctor ops --close-stale --threshold` flags (locate exact wiring in tasks)
├── session_presence/
│   └── content.py         # orientation text: open→work→close contract + open-Op listing at session start
├── upgrade/migrations/
│   └── m_<ver>_op_record_schema_v2.py  # legacy kitty-ops rewrite-or-delete migration
└── doctrine/ (src/doctrine/...)
    └── skills/spec-kitty.advise/SKILL.md + standalone command templates  # contract wording updates

tests/
├── specify_cli/invocation/        # record/writer/executor/propagator unit + e2e updates
├── specify_cli/invocation/cli/    # test_do.py rewritten for open-Op behavior
├── specify_cli/invocation/test_doctor_ops.py  # close-stale coverage
└── upgrade/                        # migration idempotency tests
```

**Structure Decision**: Single-project layout; all changes land inside existing packages (`invocation`, `cli/commands`, `doctor`, `session_presence`, `upgrade/migrations`, `src/doctrine`). No new top-level modules.

## Complexity Tracking

No charter violations to justify.

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Event schema split

- **Purpose**: Replace the single frozen `InvocationRecord` doing double duty with distinct `OpStartedEvent` / `OpCompletedEvent` models so completed events require a real outcome and cannot carry blank-default started fields.
- **Relevant requirements**: FR-004, FR-005
- **Affected surfaces**: `src/specify_cli/invocation/record.py`, `writer.py` (serialization), readers (`invocations list`, doctor, lifecycle tooling)
- **Sequencing/depends-on**: none (foundation)
- **Risks**: Many readers parse the old shape; grep all `InvocationRecord` consumers. Keep `artifact_link`/`commit_link`/`glossary_checked` event shapes unchanged.

### IC-02 — `do` lifecycle change

- **Purpose**: Remove auto-close from `do`, add the SaaS propagator, and emit the close contract in both rich and JSON output.
- **Relevant requirements**: FR-001, FR-002, FR-008
- **Affected surfaces**: `src/specify_cli/cli/commands/do_cmd.py` (executor builder, lines ~39–42 and ~150–167), capsule rendering shared with `advise.py`
- **Sequencing/depends-on**: IC-01 (new started-event shape)
- **Risks**: JSON consumers (orchestrators) must get a machine-readable close contract; pin with integration tests.

### IC-03 — Close surface and closing actor

- **Purpose**: `profile-invocation complete` records who closed the Op (`closed_by`: agent vs doctor sweep) on the completed event; idempotent double-close preserved; auto-commit at close (including sweep closes).
- **Relevant requirements**: FR-003, FR-012
- **Affected surfaces**: `executor.py` (`complete_invocation`, `_commit_op_record`), `advise.py` (`complete_invocation` CLI), `writer.py`
- **Sequencing/depends-on**: IC-01
- **Risks**: Auto-commit on protected branches uses the documented exception path — keep `allow_completed_op_on_protected_branch` semantics.

### IC-04 — Doctor stale sweep

- **Purpose**: `doctor ops --close-stale [--threshold HOURS]` closes open Ops older than the threshold (default 24 h; 0 = all) with `outcome=abandoned`, `closed_by=doctor_sweep`; report-only behavior unchanged without the flag.
- **Relevant requirements**: FR-006, FR-007, NFR-002
- **Affected surfaces**: `src/specify_cli/doctor/ops.py`, doctor CLI wiring, reuses `executor.complete_invocation` for the close path
- **Sequencing/depends-on**: IC-03
- **Risks**: Race with a concurrent manual close → must surface the idempotent error gracefully, not crash the sweep.

### IC-05 — Legacy record migration

- **Purpose**: Upgrade migration rewrites old-schema `kitty-ops/` records to the new event shapes; unsalvageable records (no recoverable started identity) are deleted; idempotent.
- **Relevant requirements**: FR-011, NFR-004
- **Affected surfaces**: `src/specify_cli/upgrade/migrations/` (new migration; use `get_agent_dirs_for_project` pattern only where applicable — this migration touches `kitty-ops/`, not agent dirs)
- **Sequencing/depends-on**: IC-01
- **Risks**: Migration is the sole sanctioned in-place mutation of records (C-004 exception); must be byte-careful and idempotent.

### IC-06 — Session presence + contract prose

- **Purpose**: Claude Code orientation lists open Ops with close commands at session start; canonical doctrine/skill/template text states the open→work→close contract and stops describing `do` as single-shot; commit-hint text replaced by close-contract text.
- **Relevant requirements**: FR-009, FR-010
- **Affected surfaces**: `src/specify_cli/session_presence/content.py`, `src/doctrine/skills/spec-kitty.advise/SKILL.md`, standalone command templates, CHANGELOG entry (C-001)
- **Sequencing/depends-on**: IC-02 (final capsule wording), IC-04 (doctor command name/flags referenced in prose)
- **Risks**: Edit source templates only (C-005); run `pytest tests/architectural/test_no_legacy_terminology.py` before push. Stop-hook feasibility resolved in research.md R5 — session-start listing is in scope; Stop hook documented as follow-up if the surface needs new harness work.

### IC-07 — SaaS propagator parity and envelope update

- **Purpose**: Wire the existing `InvocationSaaSPropagator` into `do`'s executor; rebuild envelope dicts from the new event models (shape changes freely per decision 01KTSJEQANMNEV16WMSAJP6FR1).
- **Relevant requirements**: FR-008, NFR-001
- **Affected surfaces**: `do_cmd.py` builder, `propagator.py` event builders, sync-gate behavior unchanged
- **Sequencing/depends-on**: IC-01, IC-02
- **Risks**: Keep propagation async/best-effort; do not add latency to dispatch (NFR-001).
