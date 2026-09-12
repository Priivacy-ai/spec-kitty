---
work_package_id: WP03
title: Single-authority verdict & delete second evaluation
dependencies:
- WP02
requirement_refs:
- C-002
- C-003
- FR-002
- FR-003
- FR-005
- NFR-001
- NFR-003
- NFR-004
planning_base_branch: feat/egress-single-authority
merge_target_branch: feat/egress-single-authority
branch_strategy: Planning artifacts for this mission were generated on feat/egress-single-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/egress-single-authority unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
history:
- at: '2026-08-10T08:22:23Z'
  actor: claude
  note: authored by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tracker/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/tracker/egress_verdict.py
- tests/sync/tracker/test_tracker_egress_verdict_3108.py
- tests/sync/tracker/test_local_service.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile: `/ad-hoc-profile-load python-pedro`.

## Objective

Rewire `egress_verdict._resolve_channel1` onto WP02's `_egress_decision`, **delete** `_classify_channel1` and its second routing/consent resolution, re-source (not delete) the generic-render path, and rebuild the enforcement guarantee. When this WP lands, WP01's harness goes **green** and the verdict path resolves consent/routing exactly once.

## Context (read these first)

- `.../research.md` **Decision 3** (degraded states carry `generic=True`; `_channel1_report`'s `(state, generic)` is absorbed here; the generic-render path is re-sourced) and **Decision 4** (rebuild the pin).
- `.../data-model.md` (the `channel1_state` total mapping; `generic`).
- `.../contracts/egress-consent-contract.md` §4.
- Current code: `tracker/egress_verdict.py` — `_resolve_channel1:377-384`, `_classify_channel1:387-433` (+ its two non-authoritativeness pins), `_channel1_report:436-458` (owns the `GRANTED`-direct and `UNCLASSIFIED`-generic logic), `_channel1_decided_message:583-588` (checks `generic` **before** indexing `_CHANNEL1_DESCRIPTIONS`/`_REMEDIES`), the `OUTCOME_DEFER` branch `:740-750`, and the `root is None` handling `:690-700`. Pins to rebuild live in `tests/sync/tracker/test_tracker_egress_verdict_3108.py` (`TestReportingSplitNeverFlipsEnforcement:693`; the two non-authoritativeness pins).

## Subtasks

### T013 — `_resolve_channel1` consumes the decider; absorb `_channel1_report`
Have `_resolve_channel1` return `(permits, refusal_message, channel1_state, generic)` from WP02's `_egress_decision` (one evaluation). Absorb `_channel1_report`'s `(state, generic)` production — `GRANTED`→direct granted state; degraded members→`generic=True`. Keep `refused`/`refusing_channels` computed exactly as before from `permits` (NFR-001 — WP01 T001 pins it). **Retain all six `CHANNEL1_*` state constants** (`GRANTED`/`NO_RECORD`/`RECORDED_REFUSAL`/`NOT_CONSENTABLE`/`UNCLASSIFIED`/`UNDETERMINED`) — the degraded members **reuse** `CHANNEL1_UNCLASSIFIED`; do not drop it. Its production consumer `src/specify_cli/cli/commands/sync.py:79,1846` keys an **exhaustive six-member** wording map on it, and `tests/cli/commands/test_sync_doctor_tracker_egress_3108.py:59` imports it — dropping any name breaks unowned surfaces.

### T014 — Delete `_classify_channel1` + retire **all** its test references
Remove `_classify_channel1` and its independent `resolve_checkout_sync_routing_readonly` + `resolve_project_consent` calls ("delete, not migrate", C-002). Deletion invalidates **~10 references, not two** (a stale count reds the whole file at collection). Retire/rewrite in the WP03-owned `tests/sync/tracker/test_tracker_egress_verdict_3108.py`: the import (`:61`); the whole `TestChannel1Classifier` class (`:562-611`, 7 tests calling it directly); `test_classifier_docstring_carries_the_four_required_literals` (`:216`); `test_channel1_report_never_calls_classifier_when_permitting` (`:640`); and the two non-authoritativeness pins (rebuilt in T015). **Also (post-tasks BLOCK fix, now owned)**: `tests/sync/tracker/test_local_service.py::test_fr017_five_docstrings_are_not_falsified` (`:710` imports `_classify_channel1`, `:732` pins its `__doc__`) — drop the import and refresh the FR-017 five-docstring pin to the surviving surfaces after deletion. **Do not touch** the comment-only mention at `test_tracker_egress_refusal_3108.py:2059` (not owned, does not break).

### T015 — Rebuild `TestReportingSplitNeverFlipsEnforcement`
Replace it (its monkeypatch-a-disagreeing-classifier premise is deleted) with the structural assertion: exactly **one** `resolve_checkout_sync_routing_readonly` and one `resolve_project_consent` on the verdict path (NFR-004) + the `_classify_channel1` symbol-absence (SC-004). Keep the full enforcement matrix in WP01 as the C-001 certifier.

### T016 — Make the message composer total (no KeyError — post-plan M2)
Ensure `_channel1_decided_message` renders a degraded `channel1_state` via the `generic` branch **before** indexing the state-keyed `_CHANNEL1_DESCRIPTIONS`/`_REMEDIES` dicts — retained and re-sourced, not deleted. A degraded state reaching `OUTCOME_DEFER` must render generic wording and never `KeyError` (WP01 T004 pins it). Assert `undetermined` (root-is-None) is still produced after deletion (WP01 T005).

## Branch Strategy

Base/merge target: `feat/egress-single-authority`. Enter the workspace `spec-kitty implement WP03` resolves; it branches from WP02's lane per `lanes.json`.

## Definition of Done

- WP01's `tests/sync/tracker/test_egress_single_authority.py` is **fully green**.
- `_classify_channel1` absent from `src/`; one routing + one consent resolution per verdict.
- Existing `tests/sync/tracker/test_tracker_egress_verdict_3108.py` green (the ~10 `_classify_channel1` references retired/rewritten per T014, the guarantee rebuilt per T015); `tests/sync/tracker/test_local_service.py` green (FR-017 pin refreshed); the six `CHANNEL1_*` constants all still exported.
- `ruff` + `mypy --strict` clean; the tracker-egress guard suite and `test_egress_consent_boundary` green.

## Reviewer guidance

Verify enforcement (`refused`/`refusing_channels`) is unchanged across the full matrix; verify the never-raise path (degraded state at `OUTCOME_DEFER` → generic wording, no KeyError); verify only one routing/consent resolution remains; verify the hosted string is byte-identical.
