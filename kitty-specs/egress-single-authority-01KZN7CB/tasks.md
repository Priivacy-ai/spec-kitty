# Tasks: Single-Authority Tracker-Egress Verdict

**Mission**: `egress-single-authority-01KZN7CB` | **Branch**: `feat/egress-single-authority`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Design**: [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/egress-consent-contract.md), [quickstart.md](./quickstart.md)

## Overview

Three sequenced work packages. **ATDD-first**: WP01 lands the verification harness **red**; WP02 makes the atomic contract change (the `DENIED` split + decider — all `DENIED` consumers together, per the IC-01 slicing constraint); WP03 rewires the verdict, deletes the second evaluation, and turns WP01 green. Dependencies are strictly linear: **WP01 → WP02 → WP03**.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Enforcement-equivalence matrix (permit + precedence + 3 refusal states) | WP01 | |
| T002 | Hosted byte-identity + saas_client widen-string unchanged | WP01 | [P] |
| T003 | One-resolution count (routing + consent, exactly one each) | WP01 | [P] |
| T004 | NFR-003 fail-closed enumeration at OUTCOME_DEFER | WP01 | [P] |
| T005 | C-004 no-local-import pin + C-001 iterate-all-members + root-is-None | WP01 | [P] |
| T006 | sync doctor parity + degraded golden + `_classify_channel1` absence | WP01 | [P] |
| T007 | Split `EgressConsent.DENIED` into the three refusal members | WP02 | |
| T008 | `resolve_egress_consent` mapping (only grant permits; else refuse, never raise) + re-point `test_adapters` | WP02 | |
| T009 | Registered resolver: one `resolve_project_consent` + routing → member | WP02 | |
| T010 | `egress._egress_decision` (obtain via `resolve_egress_consent`; no local sync import) | WP02 | |
| T011 | Re-point `_refusal_for_verdict` DENIED branch; `project_egress_refusal` thin wrapper | WP02 | |
| T012 | Verify `saas_client` + `propagator` unaffected | WP02 | |
| T017 | Re-point `EgressConsent.DENIED` mocks in the 3 invocation suites (atomic with T007) | WP02 | |
| T013 | `_resolve_channel1` consumes the decider; absorb `_channel1_report` (state, generic) | WP03 | |
| T014 | Delete `_classify_channel1` + its two non-authoritativeness pins | WP03 | |
| T015 | Rebuild `TestReportingSplitNeverFlipsEnforcement` (one-resolution + symbol-absence) | WP03 | |
| T016 | Make the message composer total over channel1_state (generic path; no KeyError) | WP03 | |

## Work Packages

### WP01 — Acceptance & verification harness (red-first)

- **Goal**: Land the full SC-001…SC-005 + NFR-003 + C-001/C-004 verification as failing tests that define done.
- **Priority**: P1 (ATDD anchor). **Independent test**: the new suite runs and is red against current `main`, green only after WP03.
- **Prompt**: [tasks/WP01-verification-harness.md](./tasks/WP01-verification-harness.md)
- **Subtasks**: T001, T002, T003, T004, T005, T006
- **Dependencies**: none
- **Risks**: capturing the pre-change golden references (enforcement matrix, hosted string, degraded reported-state) before any product change — must be recorded now or SC-001/SC-002/SC-005 have no baseline.
- **Est. prompt size**: ~320 lines.

### WP02 — Decision-carrying contract & decider (atomic)

- **Goal**: Split `EgressConsent.DENIED`, give the registered resolver the decision-carrying return (one `resolve_project_consent`), and add `egress._egress_decision` + the thin `project_egress_refusal` wrapper — all `DENIED` consumers landing together.
- **Priority**: P1. **Independent test**: `test_adapters` (re-pointed) green; the tree imports; existing `test_tracker_egress_verdict_3108` still green (verdict unchanged — `_classify_channel1` still runs).
- **Prompt**: [tasks/WP02-decision-carrying-contract.md](./tasks/WP02-decision-carrying-contract.md)
- **Subtasks**: T007, T008, T009, T010, T011, T012, T017
- **Dependencies**: WP01
- **Also owns** (post-tasks BLOCK fix): `tests/specify_cli/invocation/test_propagator_policy.py`, `test_invocation_e2e.py`, `test_doctor_ops.py` — their `EgressConsent.DENIED` mocks are re-pointed by T017, atomic with the `DENIED` removal.
- **Risks**: the **atomic slicing constraint** — T007/T008/T011/T017 must land in one WP so no intermediate tree references a removed `DENIED` (incl. the invocation-suite mocks that pass collection but `AttributeError` at execution). `egress.py` must gain **no** `sync.consent`/`sync.routing` import (C-004).
- **Est. prompt size**: ~380 lines.

### WP03 — Single-authority verdict & delete second evaluation

- **Goal**: Rewire `egress_verdict._resolve_channel1` onto the decider, delete `_classify_channel1` + its pins, re-source the generic path, and rebuild the enforcement guarantee. Turns WP01 green.
- **Priority**: P1. **Independent test**: WP01's suite passes; one routing + one consent resolution per verdict.
- **Prompt**: [tasks/WP03-single-authority-verdict.md](./tasks/WP03-single-authority-verdict.md)
- **Subtasks**: T013, T014, T015, T016
- **Dependencies**: WP02
- **Also owns** (post-tasks BLOCK fix): `tests/sync/tracker/test_local_service.py` — its `test_fr017_five_docstrings_are_not_falsified` imports `_classify_channel1`; T014 retires that pin. Retain all six `CHANNEL1_*` constants (unowned `sync.py` + `test_sync_doctor_tracker_egress_3108.py` depend on them).
- **Risks**: the post-plan M2 never-raise gap — the degraded state must carry `generic=True` and the composer must be total, or a degraded state at `OUTCOME_DEFER` KeyErrors. `_classify_channel1` deletion invalidates ~10 references (not two) across the WP03-owned test files — retire them all (T014).
- **Est. prompt size**: ~300 lines.

## MVP / sequencing

Linear WP01 → WP02 → WP03; no parallel WPs (the change is one atomic contract move). WP01's subtasks are internally parallelizable `[P]` (independent test cells). The MVP is the whole mission — the value (single authority) only lands when WP03 completes.
