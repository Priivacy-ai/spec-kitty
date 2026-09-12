---
work_package_id: WP02
title: Decision-carrying contract & decider (atomic)
dependencies:
- WP01
requirement_refs:
- C-001
- C-004
- FR-001
- FR-002
- FR-004
- NFR-002
- NFR-003
planning_base_branch: feat/egress-single-authority
merge_target_branch: feat/egress-single-authority
branch_strategy: Planning artifacts for this mission were generated on feat/egress-single-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/egress-single-authority unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T017
history:
- at: '2026-08-10T08:22:23Z'
  actor: claude
  note: authored by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/invocation/adapters.py
- src/specify_cli/egress.py
- src/specify_cli/sync/__init__.py
- tests/invocation/test_adapters.py
- tests/specify_cli/invocation/test_propagator_policy.py
- tests/specify_cli/invocation/test_invocation_e2e.py
- tests/specify_cli/invocation/test_doctor_ops.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile: `/ad-hoc-profile-load python-pedro`.

## Objective

Make the **atomic contract change**: split `EgressConsent.DENIED` into the three refusal members, give the registered resolver a decision-carrying return computed from **one** `resolve_project_consent`, and add `egress._egress_decision` + the thin `project_egress_refusal` wrapper. Per the IC-01 **slicing constraint**, every `DENIED` consumer (the adapter mapping, `_refusal_for_verdict`, and their tests) lands in **this** WP so no intermediate tree references a removed member. **`egress_verdict._classify_channel1` is untouched here** — it keeps working (redundantly); WP03 removes it.

## Context (read these first)

- `.../research.md` **Decision 1 & 2** (the locus — the split-mapping lives **once, in the resolver**; `egress.py` re-derives nothing locally, C-003/C-005) and **Decision 3** (the `generic` flag).
- `.../data-model.md` (member table, `ConsentLevel.UNDETERMINED` conscious mapping, `EgressDecision` fields).
- `.../contracts/egress-consent-contract.md` §1–§3.
- Current code: `invocation/adapters.py` (`EgressConsent`, `resolve_egress_consent:177-214`, `permits_egress:66-74`), `egress.py` (`project_egress_refusal:284`, `_refusal_for_verdict:273`, `_render_denied_refusal`, `_DENIED_TEMPLATE`, `_IMPORT_FAILURE_TEMPLATE`), `sync/__init__.py:327-371` (registered resolver), `sync/consent.py` (`resolve_project_consent`, `consented_project_uuids`).

## Subtasks

### T007 — Split `EgressConsent.DENIED`
Add `NO_RECORD`, `RECORDED_REFUSAL`, `NOT_CONSENTABLE` beside `GRANTED`/`NO_RESOLVER`/`UNANSWERABLE`; remove `DENIED`. Keep `permits_egress` returning `self is GRANTED` — every new member answers `False` (WP01's iterate-all-members guard pins this).

### T008 — `resolve_egress_consent` mapping + re-point `test_adapters`
Map the resolver's decision-carrying return to the member. **Only a recognized grant permits**; a bare `bool`, `None`, or any unrecognized value → `UNANSWERABLE` (refuse), **never** a permit and **never** a raise; a raw non-`EgressConsent` value must never reach `permits_egress`. Re-point `tests/invocation/test_adapters.py` (the `grants`/`denies`/`refuses-a-None-answer` tests + the iterate-all-members guard) to the split members.

### T009 — Registered resolver returns the member (one `resolve_project_consent`)
In `sync/__init__.py`, replace the bool-returning closure: call `resolve_project_consent` **once** (+ routing once) and map `ConsentDecision`→member per data-model — `granted→GRANTED`; `ABSENT→NO_RECORD`; recorded refusal / `ConsentLevel.UNDETERMINED`→`RECORDED_REFUSAL` (conscious, per data-model); no `project_uuid`→`NOT_CONSENTABLE`; unregistered→`NO_RESOLVER`; unrecognized→`UNANSWERABLE`. **Retain `consented_project_uuids`** — it has ~9 sibling drain/emit/commit callers; remove it only from *this* egress resolver's own use.

### T010 — `egress._egress_decision`
Add `_egress_decision(root, identifiers) -> EgressDecision(permits, refusal_message, channel1_state, generic)`. It **obtains** the member via `resolve_egress_consent` and derives all fields — it must add **no** `sync.consent`/`sync.routing` import to `egress.py` (C-004; WP01 T005 pins this). Degraded members set `generic=True`; the import-failure branch preserves `_IMPORT_FAILURE_TEMPLATE`'s `{exc}` text as `refusal_message`.

### T011 — Re-point `_refusal_for_verdict` + thin `project_egress_refusal` (ATOMIC with T007/T008)
Re-point the `DENIED` branch of `_refusal_for_verdict` so `NO_RECORD`/`RECORDED_REFUSAL`/`NOT_CONSENTABLE` all render `_DENIED_TEMPLATE` (no fall-through to `_UNRECOGNISED_VERDICT_TEMPLATE`). Make `project_egress_refusal` a thin wrapper returning `_egress_decision(...).refusal_message` — its `str | None` contract unchanged.

### T012 — Verify `saas_client` + `propagator` unaffected
`saas_client/client.py` consumes `project_egress_refusal`'s `str | None` — unchanged (WP01 T002 pins the string). `src/specify_cli/invocation/propagator.py:128` decides on `permits_egress` (unaffected); note its `:130` log token changes `denied → no_record/…` (harmless). No edits needed if verification passes; record the check.

### T017 — Re-point the `EgressConsent.DENIED` mocks in the invocation suites (ATOMIC with T007 — post-tasks BLOCK fix)
Removing `EgressConsent.DENIED` (T007) breaks five `patch(..., return_value=EgressConsent.DENIED)` mock bodies that pass **collection** but `AttributeError` at execution — so they are invisible to a "tree imports" check yet red for the rest of the mission. Re-point each to a refusing member (`EgressConsent.NO_RECORD`), preserving the "project has not consented" intent:
- `tests/specify_cli/invocation/test_propagator_policy.py:96, 281`
- `tests/specify_cli/invocation/test_invocation_e2e.py:252, 820`
- `tests/specify_cli/invocation/test_doctor_ops.py:192`
These land **in this WP** so no intermediate tree references a removed member (IC-01). Run each file after re-pointing to confirm green.

## Branch Strategy

Base/merge target: `feat/egress-single-authority`. Enter the workspace `spec-kitty implement WP02` resolves; it branches from WP01's lane per `lanes.json`.

## Definition of Done

- `DENIED` removed; the tree **imports** and `pytest tests/invocation/test_adapters.py` **plus the three re-pointed invocation suites (T017)** are green (run them — collection-passing mocks would otherwise hide an execution-time `AttributeError`); existing `tests/sync/tracker/test_tracker_egress_verdict_3108.py` still green (verdict behaviour unchanged — `_classify_channel1` still runs).
- `egress.py` has **no** `sync.consent`/`sync.routing` import (WP01 T005 green).
- **The unowned `_DENIED_TEMPLATE` behavioral dependents stay green** after the T011 re-point (a botched "all three members render `_DENIED_TEMPLATE`, no fall-through" would red them, and WP02's other DoD commands would miss it until WP03): run `tests/sync/tracker/test_saas_client_consent_gate_3030.py`, `tests/specify_cli/saas_client/test_client_consent_gate_3030.py`, `tests/specify_cli/test_egress_consolidation_3110.py`.
- `ruff` + `mypy --strict` clean on all owned files.

## Reviewer guidance

Verify the split-mapping exists in **one** place (the resolver), not also in `_egress_decision`; verify `egress.py` gained no local consent/routing import; verify `consented_project_uuids` is retained for its siblings; verify the fail-closed mapping refuses bool/None without raising.
