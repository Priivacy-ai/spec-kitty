# ADR-002 — `mode_of_work` is derived from the CLI entry command, not from the routed action

**Mission**: `phase-4-closeout-host-surfaces-and-trail-01KPWA5X`
**Status**: Accepted
**Date**: 2026-04-23
**Relates to**: FR-008, FR-009, SC-004, C-003
**Supersedes**: None

## Context

`docs/trail-model.md` defines four modes of work — `advisory`, `task_execution`, `mission_step`, `query` — as a documentation-level taxonomy. The shipped runtime does not derive mode at invocation time and does not enforce any behaviour based on mode. Issue #701 calls out this gap: "Runtime enforcement and automatic mode detection are deferred to Phase 5."

To enforce `advisory`/`query` invocations cannot promote Tier 2 evidence (FR-009), the runtime needs a deterministic mode derivation that cannot drift with internal router changes.

## Decision

Derive `mode_of_work` from the **CLI entry command** — the subcommand the operator or host LLM invoked.

Mapping:

| Entry command | `ModeOfWork` |
|---------------|--------------|
| `advise` | `advisory` |
| `ask`, `do` | `task_execution` |
| `profile-invocation complete` | `task_execution` (used as enforcement site, not as the source of a new `started` event) |
| mission-step drivers (`specify`, `plan`, `tasks`, `implement`, `review`, `merge`, `accept`) | `mission_step` |
| `profiles list`, `invocations list` | `query` |

The mapping is a private dict in `src/specify_cli/invocation/modes.py` with a `derive_mode(entry_command: str) -> ModeOfWork` helper. Unknown `entry_command` raises `KeyError` at the CLI layer so that the error surfaces before any invocation is opened.

The derived value is passed into `ProfileInvocationExecutor.invoke(...)` as a new keyword argument `mode_of_work: ModeOfWork | None` (default `None` to preserve backward compatibility with internal callers that bypass the CLI). The executor records the value on the `started` event as an additive optional field.

## Rationale

- **Deterministic.** The operator / host can predict the mode from the command they typed. No hidden router logic.
- **Resilient to router drift.** The router's `action` taxonomy is finer-grained and is expected to evolve as new profiles are added. Deriving mode from `action` would couple the mode taxonomy to router internals.
- **One source of truth.** The CLI layer is already the natural boundary for capturing operator intent; mode derivation lives there alongside profile-hint parsing.
- **Mypy-strict testable.** Enum-to-enum mapping is a parameterised table test (WP06).

## Alternatives considered

| Option | Outcome | Why rejected |
|--------|---------|--------------|
| **A. Derive from CLI entry command** | **Accepted** | See Rationale. |
| B. Derive from router `action` | Rejected | Router action taxonomy is finer-grained and will drift; coupling modes to it introduces maintenance cost without operator benefit. |
| C. Hybrid — entry command primary, action secondary | Rejected | Two sources of truth → drift risk; no scenario in which the secondary signal would override the primary. |
| D. Leave mode as documentation only; do not enforce | Rejected | FR-009 requires enforcement; documentation-only is the status quo that #701 is asking us to improve. |

## Consequences

- `InvocationRecord` gains an optional `mode_of_work: str | None` field on the `started` shape — additive (C-003).
- Pre-mission records have no `mode_of_work` field; enforcement paths treat this as "unknown, skip enforcement" so historical invocations are not retroactively rejected.
- `derive_mode` is the single choke point for mapping; adding a future entry command (e.g. `spec-kitty benchmark`) requires adding a row to the mapping dict, and the CLI test suite catches missing rows.
- SaaS projection now varies by `mode_of_work` (see ADR-003). Pre-mission records project under `TASK_EXECUTION` defaults via `resolve_projection(None, event)` — the existing projection behaviour is preserved exactly for legacy records.

## Revisit trigger

Revisit this decision if:

- A new invocation entry point is added that does not fit the four existing modes. Add the mode (e.g. `benchmarking`) only if the distinction is load-bearing for policy or enforcement; otherwise, reuse `task_execution` or `query`.
- Automatic mode detection from routed action becomes feasible and useful (e.g. in Phase 5 when the router gains a mode-hint field).

## References

- `docs/trail-model.md` — mode taxonomy
- `src/specify_cli/invocation/executor.py` — `ProfileInvocationExecutor.invoke` (extension point)
- Issue #701 — Minimal Viable Trail
- Data model: `data-model.md` §1, §2
- Contract: `contracts/profile-invocation-complete.md` (mode enforcement)
