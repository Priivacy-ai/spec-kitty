# ADR-003 — SaaS read-model policy is a typed Python module, not operator-configurable YAML

**Mission**: `phase-4-closeout-host-surfaces-and-trail-01KPWA5X`
**Status**: Accepted
**Date**: 2026-04-23
**Relates to**: FR-010, NFR-005, NFR-007, SC-005, C-002, C-009
**Supersedes**: None

## Context

Phase 4 core runtime added `InvocationSaaSPropagator` and the sync-aware suppression in `_propagate_one`. Projection is currently unconditional once the sync-gate and authenticated client are confirmed — every `started` and `completed` event builds an envelope and calls `client.send_event(...)`. Issue #701 calls for an explicit SaaS read-model policy that tells operators — from the code/config alone — whether a given `(mode, event)` pair projects to the SaaS timeline, and what it includes.

The policy must also cover the new correlation events (`artifact_link`, `commit_link`) introduced by ADR-001.

## Decision

Implement the policy as a **typed Python module** at `src/specify_cli/invocation/projection_policy.py`. Not a YAML file. Not operator-configurable.

Module exports:

- `ModeOfWork` (re-exported from `modes.py`) — `advisory`, `task_execution`, `mission_step`, `query`.
- `EventKind` — `started`, `completed`, `artifact_link`, `commit_link`. (`glossary_checked` intentionally omitted — it is a local-only diagnostic.)
- `ProjectionRule` — frozen dataclass with `project: bool`, `include_request_text: bool`, `include_evidence_ref: bool`.
- `POLICY_TABLE: dict[tuple[ModeOfWork, EventKind], ProjectionRule]` — exhaustive 4×4 backing table.
- `resolve_projection(mode: ModeOfWork | None, event: EventKind) -> ProjectionRule` — single entry point for callers.

The full table and its lookup semantics are pinned in `data-model.md` §5 and `contracts/projection-policy.md`. The same table is mirrored, human-readable, in `docs/trail-model.md` under "SaaS Read-Model Policy".

## Rationale

- **Predictability (SC-005).** A single table, visible both in code and in the operator doc, lets operators predict projection without reading propagator internals.
- **Type safety (NFR-005).** `mypy --strict` verifies exhaustive handling of enum values at compile time; untyped dicts would silently accept typos.
- **No new dependency (C-009).** Existing charter mandates `typer`, `rich`, `ruamel.yaml`, `pytest`, `mypy`. Introducing a YAML-configurable override would add surface area and invite per-checkout policy drift.
- **Local-first preserved (C-002).** Policy evaluation is read-side and runs strictly after the existing sync-gate and authentication lookup — a policy bug cannot break Tier 1 writes.
- **Caller ergonomics.** The `resolve_projection(None, event)` fallback to `TASK_EXECUTION` defaults preserves today's projection behaviour exactly for pre-mission records with no `mode_of_work` field.

## Alternatives considered

| Option | Outcome | Why rejected |
|--------|---------|--------------|
| **A. Typed Python module** | **Accepted** | See Rationale. |
| B. Untyped dict in a Python module | Rejected | No mypy exhaustiveness; typos become silent misrouting. |
| C. YAML config file at `src/specify_cli/invocation/projection_policy.yaml` | Rejected | Requires new load machinery; no operator has asked to edit policy; per-checkout drift risk. |
| D. Operator-configurable via `.kittify/config.yaml::saas.projection` | Rejected | Policy drift across checkouts; SaaS dashboard coherence becomes non-deterministic; invites long-tail debugging when operators forget they overrode it. |
| E. Policy inlined into `_propagate_one` via `if`/`elif` branches | Rejected | Non-exhaustive; future event kinds forget to update; not introspectable from a single table. |

## Consequences

- `src/specify_cli/invocation/propagator.py::_propagate_one` gains a policy-lookup step between the authenticated-client check and the envelope build. The sync-gate short-circuit remains first (C-002, FR-012).
- The envelope building step consults `ProjectionRule.include_request_text` and `ProjectionRule.include_evidence_ref` to gate field inclusion. Fields are **omitted** (not sent empty) when the rule is `False`, so SaaS consumers can distinguish "policy excluded" from "field empty".
- Pre-mission records (`mode_of_work=None`) project exactly as today. No dashboard regression for active missions.
- Operators seeking predictability read a single table; no config to grep, no per-checkout surprises.
- Any future policy change (e.g. adding a new `EventKind`) requires a coordinated update to the enum, the `POLICY_TABLE`, and the table in `docs/trail-model.md`. Test suite will fail if any row is missing.

## Revisit trigger

Revisit if any of the following:

- Operators request per-checkout or per-organisation policy overrides and provide a concrete scenario. At that point, an operator-configurable override layer could be added **on top of** the typed module (not replacing it).
- A new `EventKind` or `ModeOfWork` value is introduced; each addition must extend the table.
- Regulatory or compliance constraints require a projection profile (e.g. request-text redaction for PII).

## References

- `src/specify_cli/invocation/propagator.py::_propagate_one` — consumer
- `src/specify_cli/invocation/emitter.py` precedents (contract-verified fields in `propagator.py` header)
- `docs/trail-model.md` — operator policy mirror
- Issue #701 — Minimal Viable Trail
- Data model: `data-model.md` §4, §5
- Contract: `contracts/projection-policy.md`
