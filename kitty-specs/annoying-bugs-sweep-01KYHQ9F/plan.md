# Implementation Plan: Annoying Bugs Sweep

**Branch**: `fix/annoying-bugs-sweep` | **Date**: 2026-07-27 | **Spec**: [spec.md](./spec.md)
**Input**: Approved specification from `kitty-specs/annoying-bugs-sweep-01KYHQ9F/spec.md`

## Summary

Deliver two independent P0 fixes and three agent-facing corrections without joining their
ownership surfaces. The birth-cutover fix keeps `cutover_mission` as the sole writer, moves every
migration seed for an already-active WP below that WP's existing transition and annotation history,
and strengthens verification with legacy-reader witnesses for `shell_pid`,
`shell_pid_created_at`, and `agent`. The post-merge dead-code gate replaces the POSIX-only reference
search with a pure-Python scan and changes unsupported or failed discovery from a false clean result
to a structured `undeterminable` finding.

The remaining corrections update canonical doctrine sources and selected published documentation,
make the canonical profile-load skill self-sufficient through `references/`, and add a
`spec-kitty dispatch` pointer to the `profile-invocation` Typer epilog. Archived mission artifacts
and changelog history remain immutable.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Python stdlib (`pathlib`, `subprocess`, `re`, datetime handling), Typer,
Rich, and existing `specify_cli.migration`, `specify_cli.status`, doctrine skill, and review modules;
no new dependency
**Storage**: append-only `status.events.jsonl`, reduced status snapshot, mission `meta.json`, and
Markdown/YAML doctrine sources; no schema migration
**Testing**: pytest, red-first acceptance tests, focused unit/integration coverage, ruff, mypy, and
the architectural terminology/doctrine guards
**Target Platform**: Linux, macOS, and Windows 10+
**Project Type**: single Python CLI/library with canonical doctrine and published documentation
**Performance Goals**: preserve the normal accept/merge path; dead-code scanning remains linear in
the examined diff plus Python source bytes and completes inside the existing review budget
**Constraints**: no reducer precedence change; no seed suppression; no POSIX executable dependency;
no new top-level `status`; no `profile-invocation dispatch` alias; P0 file sets remain disjoint; no
direct push to `origin/main`
**Scale/Scope**: five issue slices (#2985, #2987, #1840, #2983, #2984), approximately five
implementation WPs plus planning/verification evidence

## Charter Check

Loaded with `spec-kitty charter context --action plan`.

| Gate | Plan treatment |
|---|---|
| Single canonical authority | `cutover_mission` remains the only cutover authority; doctrine edits land only under `src/doctrine/`; profile mechanics live in the canonical `spk-doctrine-profile-load` skill. |
| Architectural alignment | Migration ordering is fixed at seed construction, not in the global reducer. Review diagnostics extend the existing review diagnostic surface. |
| ATDD/red-first | #2985 and #2987 each start with a focused failing reproduction through their existing public entry path. |
| Tiered rigour | Both P0s receive acceptance, unit, integration, and non-vacuity coverage; prose-only slices receive scoped guards. |
| Campsite and Sonar | New helpers are deterministic and directly tested; touched functions stay at complexity 15 or below; repeated messages become constants. |
| Terminology | New canonical prose uses Mission/WP vocabulary; run `tests/architectural/test_no_legacy_terminology.py`. |
| Git/workflow | Work lands on `fix/annoying-bugs-sweep`; publication to `origin/main` requires a PR and operator merge. |
| Mission hygiene | Issue-matrix/tracker evidence is required before acceptance; implementation and review roles remain distinct. |

No charter exception is required. Re-check after Phase 1: the contracts below keep the same
authorities, preserve P0 separability, and introduce no new package boundary.

## Project Structure

### Mission artifacts

```text
kitty-specs/annoying-bugs-sweep-01KYHQ9F/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── birth-cutover-ordering.md
│   └── dead-code-verdict.md
└── traces/
    ├── tooling-friction.md
    ├── approach.md
    └── design-decisions.md
```

### Source and test surfaces

```text
src/specify_cli/
├── migration/
│   ├── backfill_runtime_state.py
│   └── runtime_state_cutover.py
├── cli/commands/
│   ├── accept.py
│   ├── migrate_cmd.py
│   ├── profile_invocation.py
│   └── review/
│       ├── _dead_code.py
│       ├── _diagnostics.py
│       └── ERROR_CODES.md
├── merge/executor.py
└── upgrade/migrations/m_zz_runtime_state_backfill.py

src/doctrine/
├── skills/{ad-hoc-profile-load,spk-doctrine-profile-load,adversarial-squad}/
├── procedures/built-in/adversarial-squad-deployment.procedure.yaml
└── styleguides/built-in/plain-language.styleguide.yaml

docs/{api,architecture,guides}/
tests/{unit/migration,integration,regression,specify_cli/cli/commands/review,architectural}/
```

**Structure Decision**: Modify existing owners only. No new runtime package or compatibility layer.
The profile reference content is the sole new source subdirectory; generated agent copies are not
edited.

## Complexity Tracking

| Deliberate choice | Why needed | Simpler alternative rejected because |
|---|---|---|
| Per-WP seed floor covers transitions and annotations | Lane and runtime slots have separate reducer passes; both can be superseded | Clamping only the claim transition leaves stale annotation seeds able to win |
| Deterministic append-only compatibility repair | Existing bad seed IDs deduplicate to the first persisted row and cannot be re-anchored in place | Reusing the seed ID is a no-op; rewriting the event stream violates append-only authority |
| Explicit `undeterminable` review finding | Polyglot/non-source-root analysis cannot honestly claim zero symbols | Treating empty discovery as clean repeats #2987 |
| Pure-Python reference scan | Cross-platform and preserves untracked/ignored Python behavior | `git grep` is unavailable outside Git, misses untracked files, and solves only FR-014 |

## Implementation Concern Map

### IC-01 - Birth-cutover red-first evidence and seed ordering

- **Purpose**: Reproduce the terminal-lane rewind and runtime-slot overwrite, make all new seeds sort
  before existing per-WP history, and repair already-persisted colliding seeds through a separate
  deterministic append-only compatibility identity without changing reducer precedence.
- **Relevant requirements**: FR-001 through FR-006, FR-010; NFR-001, NFR-002, NFR-004; C-001, C-002.
- **Affected surfaces**: `migration/backfill_runtime_state.py`, focused migration/regression tests,
  and caller-path tests for accept, merge, upgrade migration, and migrate single/corpus modes.
- **Sequencing/depends-on**: first P0 slice; tests precede code.
- **Risks**: raw timestamp strings are the reducer's comparator input; the helper must prove strict
  `(at, event_id)` precedence for both event kinds and remain deterministic/idempotent. Reusing an
  old seed ID cannot repair it because reducer deduplication preserves the first row.

### IC-02 - Independent cutover verification witness

- **Purpose**: Prevent builder/verify tautology and prove the legacy reader's three claim-borne
  values appear in raw seed evidence. Require snapshot equality only when no later legitimate writer
  owns that slot; otherwise prove the later value wins.
- **Relevant requirements**: FR-003, FR-005, FR-010; NFR-002.
- **Affected surfaces**: `migration/backfill_runtime_state.py`, unit/integration tests.
- **Sequencing/depends-on**: IC-01.
- **Risks**: `_has_snapshot_runtime` is an `any()` predicate and cannot be the oracle; exact
  per-slot comparisons are required.

### IC-03 - Portable, non-vacuous dead-code verdict

- **Purpose**: Remove the POSIX `grep` dependency, inspect Python references portably, and emit a
  structured undeterminable finding when diff/source discovery fails or is unsupported.
- **Relevant requirements**: FR-014 through FR-016; NFR-002; C-008, C-009.
- **Affected surfaces**: `review/_dead_code.py`, `_diagnostics.py`, `ERROR_CODES.md`,
  `test_dead_code_baseline.py`, and focused CLI review tests.
- **Sequencing/depends-on**: independent of IC-01/IC-02.
- **Risks**: preserve the current POSIX symbol set, the substring `"test" not in path` rule, and
  cwd-relative path comparison; an empty supported diff and an undeterminable scan are different.

### IC-04 - Resolver-backed profile-load doctrine

- **Purpose**: Make canonical instructions lead with `spec-kitty agent profile show`, retain the
  explicitly scoped read-only-harness fallback, and guard all tracked doctrine sources.
- **Relevant requirements**: FR-007 through FR-009, FR-011; NFR-003; C-006.
- **Affected surfaces**: canonical doctrine skills/procedure, new
  `spk-doctrine-profile-load/references/` content, architectural guard tests, and the #1840 ticket.
- **Sequencing/depends-on**: independent; external ticket edit occurs after source wording settles.
- **Risks**: do not edit generated agent directories; the guard denominator must be non-zero and
  list every offender.

### IC-05 - Command guidance and invocation discoverability

- **Purpose**: Replace nonexistent top-level `status` examples only where they intend a concrete
  command, and expose the standalone opener from the closer's help.
- **Relevant requirements**: FR-012, FR-013; C-003, C-004, C-007.
- **Affected surfaces**: plain-language styleguide, four scoped docs, `profile_invocation.py`, help
  tests, terminology guard.
- **Sequencing/depends-on**: independent.
- **Risks**: generic uses of “command” require judgment; changelog history is excluded; the Typer
  epilog must not alter the completion manifest.

## Delivery And Validation Strategy

1. Land IC-01/IC-02 as one P0 slice with baseline-red evidence and all five caller paths.
2. Land IC-03 as a file-disjoint P0 slice after coordinating with the #2987 reporter.
3. Land IC-04 and IC-05 independently; neither P0 depends on the papercuts.
4. Run targeted pytest packages per concern, `ruff check` on touched Python, focused mypy, the
   doctrine skill-pack guards, and `tests/architectural/test_no_legacy_terminology.py`.
5. Record node IDs, baseline commit, diagnostics, tracker links, and remaining Sonar UI work in the
   PR body.

## Phase 1 Outputs

- [research.md](./research.md) records the evaluated alternatives and decisions.
- [data-model.md](./data-model.md) defines the seed-ordering and review-verdict models.
- [birth-cutover-ordering.md](./contracts/birth-cutover-ordering.md) fixes the cutover invariants.
- [dead-code-verdict.md](./contracts/dead-code-verdict.md) fixes the portable verdict contract.
- [quickstart.md](./quickstart.md) provides the red-first implementation verification sequence.
