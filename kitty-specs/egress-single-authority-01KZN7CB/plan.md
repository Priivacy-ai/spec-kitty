# Implementation Plan: Single-Authority Tracker-Egress Verdict

**Branch**: `feat/egress-single-authority` | **Date**: 2026-08-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/egress-single-authority-01KZN7CB/spec.md`

## Summary

The tracker egress verdict enforces Channel-1 consent from one authority (`project_egress_refusal`) but re-derives the refusal *reason* and remedy from a second, independent lookup (`egress_verdict._classify_channel1`), which can drift and repeats a full checkout-routing / consent resolution per verdict. This mission gives the egress-consent port a **decision-carrying return** (splitting `EgressConsent.DENIED` into `no_record` / `recorded_refusal` / `not_consentable`, keeping `no_resolver` / `unanswerable`), sources the diagnostic from the **same** `ConsentDecision` (`resolve_project_consent`) that enforces the outcome, and **deletes** `_classify_channel1` and its second resolution — without changing what the gate allows or denies (NFR-001), the hosted refusal string (NFR-002), or the never-raise contract (NFR-003).

**Technical approach** (see [research.md](./research.md) for the threading decision): a single internal decider in `egress.py` computes the `EgressConsent` member **once** from one `resolve_project_consent` + routing resolution, and exposes both the byte-identical refusal string (for `project_egress_refusal`'s existing `str | None` consumers, incl. the widen SaaS transport) and the diagnostic state (for `egress_verdict`). `_classify_channel1`'s independent resolution is deleted, closing #3287 and removing #3291-item2's redundant work as a consequence.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: internal only — `specify_cli.invocation.adapters` (`EgressConsent`, `resolve_egress_consent`, `permits_egress`), `specify_cli.egress` (`project_egress_refusal`, `_refusal_for_verdict`, `_render_denied_refusal`), `specify_cli.tracker.egress_verdict`, `specify_cli.sync.consent` (`resolve_project_consent`, `consented_project_uuids`), `specify_cli.sync.routing`, `specify_cli.sync.__init__` (registered resolver). Tooling: `pytest`, `ruff`, `mypy --strict`.
**Storage**: N/A — reads the existing `.kittify/config.yaml` + machine consent index; no new persistence.
**Testing**: `pytest` (unit + the `tests/architectural/test_egress_consent_boundary.py` and `test_adapters.py` guards); red-first for any behavior change; the enforcement-equivalence matrix and one-resolution count are the load-bearing tests.
**Target Platform**: Linux / macOS CLI.
**Project Type**: single.
**Performance Goals**: exactly one `resolve_checkout_sync_routing_readonly` and one `resolve_project_consent` per gated verdict (down from two each).
**Constraints**: fail-closed / never-raise (NFR-003); hosted refusal byte-identity (NFR-002); the confidentiality seam must not widen (C-001 — `permits_egress` stays the single grant gate, True only for `GRANTED`).
**Scale/Scope**: ~4 source modules + `sync/__init__.py` resolver wiring + tests. No public CLI surface change.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter mode: compact, `software-dev-default` (git, mypy, pytest, ruff). No paradigm packs active. Relevant standing orders: ATDD-first (enforcement-equivalence + byte-identity tests land before the refactor), canonical-sources (change the port/authority, not a mirror), red-first for behavior. No charter violations — the mission tightens an existing seam without adding surface. **PASS.**

## Project Structure

### Documentation (this mission)

```
kitty-specs/egress-single-authority-01KZN7CB/
├── plan.md              # This file
├── research.md          # Phase 0 — the threading + degraded-state design decisions
├── data-model.md        # Phase 1 — EgressConsent members, ConsentDecision, state mapping
├── contracts/           # Phase 1 — the internal function contracts (resolver, decider, verdict)
├── quickstart.md        # Phase 1 — how to verify SC-001..SC-005
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── invocation/adapters.py     # EgressConsent (split DENIED), resolve_egress_consent mapping, permits_egress (unchanged gate)
├── egress.py                  # single decider: one ConsentDecision -> (byte-identical string, channel1_state); project_egress_refusal thin wrapper; _refusal_for_verdict re-pointed
├── tracker/egress_verdict.py  # _resolve_channel1 sources state from the decider; _classify_channel1 DELETED
├── sync/__init__.py           # registered resolver returns the decision-carrying member (one resolve_project_consent)
└── sync/consent.py            # resolve_project_consent (the single consent authority — unchanged)

tests/
├── invocation/test_adapters.py                 # resolve_egress_consent mapping + iterate-all-members permits_egress guard (re-pointed)
├── sync/tracker/test_tracker_egress_verdict_3108.py  # enforcement-equivalence matrix, byte-identity, one-resolution count, _classify_channel1 absence (rebuilt from TestReportingSplitNeverFlipsEnforcement)
└── architectural/test_egress_consent_boundary.py     # sink-keyed boundary gate (must stay green)
```

**Structure Decision**: Single project. All changes live in `src/specify_cli/` across the four modules above plus the `sync/__init__.py` resolver wiring; no new packages, no new storage, no CLI surface change.

## Complexity Tracking

*No charter violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are architectural areas, not work packages. `/spec-kitty.tasks` translates them into WPs.

### IC-01 — Decision-carrying consent contract

- **Purpose**: Widen the port so consent state travels as data, not a bare bool, without opening a grant path.
- **Relevant requirements**: FR-001, C-001, NFR-003.
- **Affected surfaces**: `invocation/adapters.py` (`EgressConsent` split into `NO_RECORD`/`RECORDED_REFUSAL`/`NOT_CONSENTABLE` beside `GRANTED`/`NO_RESOLVER`/`UNANSWERABLE`; `resolve_egress_consent` mapping keeps "only a recognized grant permits, malformed/bool/None refuses, never raises"; `permits_egress` unchanged), `sync/__init__.py` (registered resolver returns the member from one `resolve_project_consent` + routing).
- **Sequencing/depends-on**: none (foundation).
- **Risks**: a mid-migration resolver returning bool/None must refuse and never reach `permits_egress` (AttributeError at the `propagator` sink). Every new member must answer `permits_egress is False` — pin with the iterate-all-members guard.
- **Slicing constraint (post-plan m3)**: removing/splitting `DENIED` instantly breaks its three consumers — the `resolve_egress_consent` mapping (`adapters.py:208`), `egress._refusal_for_verdict` (`egress.py:273`), and their tests. `/spec-kitty.tasks` must keep those atomic in one WP; no intermediate WP may land a non-importable tree.

### IC-02 — Single-authority threading into the verdict

- **Purpose**: Source `channel1_state` from the same `ConsentDecision` that enforces, resolving consent/routing once.
- **Relevant requirements**: FR-002, FR-003, NFR-004.
- **Affected surfaces**: `egress.py` — a single internal decider `_egress_decision` **obtains** the `EgressConsent` member via the existing `resolve_egress_consent` seam (it performs **no** local consent/routing resolution and adds **no** `sync.consent`/`sync.routing` import — the C-004 invariant; the split-mapping lives once, in the resolver, per research Decision 1) and derives `(permits, refusal_message, channel1_state, generic)` from it; `project_egress_refusal` becomes a thin `str | None` wrapper over it. `tracker/egress_verdict.py` — `_resolve_channel1` consumes the decider's tuple; `_classify_channel1` and its independent routing/consent resolution are deleted; `_channel1_report`'s `(state, generic)` production is **absorbed into the decider** and its generic-rendering path is re-sourced (not deleted).
- **Sequencing/depends-on**: IC-01.
- **Risks**: the post-spec M2 crux (no second resolution, no byte-string perturbation) **and** the post-plan M2 symmetric never-raise gap — a degraded `channel1_state` must carry `generic = True` so the composer's generic branch renders it and the state-keyed `_CHANNEL1_DESCRIPTIONS`/`_REMEDIES` dicts are never indexed (else `KeyError`, an NFR-003 violation). `consented_project_uuids` is **retained** (≈9 sibling drain/emit/commit callers) and removed only from the egress resolver.

### IC-03 — Consumer audit & re-point

- **Purpose**: Ensure every consumer of the changed contract is correct after the `DENIED` split.
- **Relevant requirements**: FR-004, FR-005, NFR-002.
- **Affected surfaces**: `egress.py::_refusal_for_verdict` (the `DENIED` branch re-pointed so all three refusal members render `_DENIED_TEMPLATE` — preserving hosted byte-identity and the `not_consentable` carried-but-not-rendered carve-out), `saas_client/client.py` (widen transport refusal string verified unchanged), `src/specify_cli/invocation/propagator.py` (uses `permits_egress` only — verified unaffected), tracker `sync doctor` renderer (per-destination state/remedy parity, incl. degraded states).
- **Sequencing/depends-on**: IC-01, IC-02.
- **Risks**: an unmapped new member falling through to `_UNRECOGNISED_VERDICT_TEMPLATE` would change the hosted string (NFR-002 break) though not widen the seam. `saas_client`'s refusal string is not covered by NFR-002's pin — verify it explicitly. `propagator.py:130` **logs** the member value (`"…egress consent is %s"`), so the logged token changes `denied → no_record/recorded_refusal/not_consentable` — harmless (enforcement is via `permits_egress` at `:128`), noted so it is not mistaken for a regression (post-plan n1).

### IC-04 — Delete the second evaluation & rebuild the guarantee

- **Purpose**: Remove `_classify_channel1` and replace the now-unbuildable disagreement pin with the single-resolution invariant.
- **Relevant requirements**: C-002, C-003, FR-003, SC-004.
- **Affected surfaces**: `tracker/egress_verdict.py` (delete `_classify_channel1` + its two non-authoritativeness pins), `tests/sync/tracker/test_tracker_egress_verdict_3108.py` (`TestReportingSplitNeverFlipsEnforcement` rebuilt as "exactly one routing/consent resolution on the path" (NFR-004) + `_classify_channel1` symbol-absence).
- **Sequencing/depends-on**: IC-02.
- **Risks**: the old pin injected a disagreeing classifier; that premise is gone. The rebuilt pin must assert the property structurally (one resolution) rather than by injection.

### IC-05 — Verification matrix

- **Purpose**: Prove enforcement, byte-identity, and the one-resolution efficiency all hold across the full state space.
- **Relevant requirements**: NFR-001, NFR-002, NFR-004, SC-001, SC-002, SC-003, SC-005.
- **Affected surfaces**: `tests/sync/tracker/test_tracker_egress_verdict_3108.py`, `tests/invocation/test_adapters.py`, `tests/cli/.../sync doctor` tests.
- **Sequencing/depends-on**: IC-01..IC-04.
- **Risks**: SC-001 must include the **permit** row and consent precedence levels (project-local / machine-index / env), not only the three refusal sub-states, or C-001 goes unmeasured (post-spec M5).
- **Checks the tasks phase must land as concrete tests (post-plan)**: (a) an NFR-003 fail-closed enumeration — each degraded input (bare `bool`, `None`, unrecognized, resolver-import-failure) at the `OUTCOME_DEFER` branch → refuses, renders generic wording, and never raises at any `permits_egress` sink (closes M2, renata MINOR-1); (b) the `saas_client/client.py` widen-transport refusal string verified unchanged (renata MINOR-2); (c) a C-004 pin that `egress.py` holds **no** `sync.consent`/`sync.routing` import (post-plan M1 — the invariant that has no test today); (d) `undetermined` is still produced for `root is None` after `_classify_channel1` deletion (renata NOTE-2).
