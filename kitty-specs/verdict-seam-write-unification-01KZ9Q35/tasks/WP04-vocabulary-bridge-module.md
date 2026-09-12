---
work_package_id: WP04
title: Vocabulary bridge module + inline-equivalence arch-guard
dependencies:
- WP01
requirement_refs:
- FR-005
planning_base_branch: feat/verdict-seam-write-unification
merge_target_branch: feat/verdict-seam-write-unification
branch_strategy: Planning artifacts for this mission were generated on feat/verdict-seam-write-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verdict-seam-write-unification unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/verdict_vocab.py
create_intent:
- src/specify_cli/status/verdict_vocab.py
- tests/architectural/test_verdict_vocab_single_source.py
execution_mode: code_change
owned_files:
- src/specify_cli/status/verdict_vocab.py
- tests/architectural/test_verdict_vocab_single_source.py
- src/specify_cli/sync/emitter.py
- src/specify_cli/status/models.py
- src/specify_cli/status/reducer.py
- src/specify_cli/retrospective/generator.py
- src/specify_cli/proof/events.py
- src/specify_cli/orchestrator_api/commands.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned profile: run `/ad-hoc-profile-load python-pedro` (or
`spec-kitty charter context --action implement`). Do not start work until the profile is loaded.

## Objective

Create **one canonical** artifact↔event verdict vocabulary bridge beside `status/models.py`, sweep the
inline `rejected`↔`changes_requested` equivalences into it, and land a **non-vacuous architectural
guard** forbidding any other module from spelling that equivalence inline (today it is inline in **9**
modules). The bridge is what WP05's reader collapse and WP02's backfill call instead of re-inlining the
mapping.

## Context

- **Requirement**: FR-005 (single-sourced, complete vocabulary bridge).
- **Contract**: [contracts/vocabulary-bridge.md](../contracts/vocabulary-bridge.md) — total mapping
  both directions; G1 total over all four inbound artifact values; G2 no drift surface (arch-guard).
- **Decision**: **D-PLAN-14** — the bridge feeding an **emitted `review_result` event** is scoped to
  `{approved, rejected}`. `arbiter_override` / `approved_after_orchestrator_fix` are **NOT**
  verdict-bridge inputs to a `review_result` event — they resolve via `ReviewOverride` /
  orchestrator-fix records (the reducer separates override from verdict, `reducer.py:244-252`). The
  full four-value table is display-only (prose/render). A negative test: an `arbiter_override` must not
  produce an `approved` `review_result` event while its `ReviewOverride` slot carries provenance.
- **Ownership resolution (flagged to orchestrator)**: the plan's 9 inline-vocab sites are swept
  in-place by "whichever WP owns each file." Seven of the nine had **no owner** in the decomposition —
  they are assigned to this WP's `owned_files` so the guard has an owner for every swept site. The
  **remaining two** — `review/cycle.py:794` and `post_merge/review_artifact_consistency.py` — are owned
  by **WP05** and swept there. This WP's guard therefore carries a **named, shrinking allowlist** of
  exactly those two modules; **WP05 removes both entries** when it sweeps them (guard-lands-last,
  D-PLAN IC-02b). See tasks.md shared-file table.

The 9 sites (plan IC-02b): `sync/emitter.py`, `status/models.py`, `status/reducer.py`,
`post_merge/review_artifact_consistency.py` *(WP05)*, `review/cycle.py:794` *(WP05)*,
`retrospective/generator.py`, `proof/events.py`, `orchestrator_api/commands.py`,
`cli/commands/agent/tasks_move_task.py`.

## Subtasks

### T016 — Create the canonical bridge `status/verdict_vocab.py`
- **Purpose**: FR-005 single source. A total function `artifact_verdict → event_verdict` over
  `{approved, rejected, arbiter_override, approved_after_orchestrator_fix} → {approved,
  changes_requested}` and its inverse `{approved, changes_requested} → {approved, rejected}` for
  prose/render.
- **Steps**: Implement per [contracts/vocabulary-bridge.md](../contracts/vocabulary-bridge.md). Make it
  total (G1) — no inbound value falls through to "damaged". Type it strictly (Literal/enums). Add a
  clearly-marked helper for the **emission-scoped** subset `{approved, rejected}` (D-PLAN-14) so callers
  emitting a `review_result` cannot pass an override value.
- **Files**: `src/specify_cli/status/verdict_vocab.py`.
- **Validation**: unit test of all four inbound values + inverse; `mypy --strict` clean.

### T017 — Red-first: the two-part inline-equivalence guard (positive + negative)
- **Purpose**: G2. The guard must fail while the inline equivalence still exists outside the bridge —
  and it must not be gameable by splitting the literals across lines (squad #5).
- **Steps**: In `tests/architectural/test_verdict_vocab_single_source.py`, implement **two** checks:
  1. **Negative (absence)**: no module other than `status/verdict_vocab.py` spells the co-occurring
     `rejected`↔`changes_requested` equivalence literals.
  2. **Positive (import/call)**: **each of the 7 swept modules must import and call
     `status.verdict_vocab` on its verdict-mapping path** — assert the AST shows a `verdict_vocab`
     import + a call, not merely the *absence* of literals. This defeats the "split the literals to
     dodge the grep" evasion: a module that maps verdicts must route through the canonical surface.
  Seed a **named allowlist** = `{review/cycle.py, post_merge/review_artifact_consistency.py}` (the two
  WP05-owned sites not yet swept — exempt from the positive check until WP05 sweeps them). Confirm the
  guard is RED against the 7 unswept sites before T018 and GREEN (2-entry allowlist) after.
- **Files**: `tests/architectural/test_verdict_vocab_single_source.py`.
- **Validation**: red before T018; a synthetic re-inline that splits the literals across lines still
  reds it (positive-check non-vacuity); a module that maps verdicts without importing `verdict_vocab`
  reds it.

### T018 — Sweep the 7 owned inline sites onto the bridge (behaviour-preserving)
- **Purpose**: Adopt-in-place. Replace inline `rejected`↔`changes_requested` mapping with a call to
  `verdict_vocab` in the 7 files this WP owns.
- **Steps**: Edit `sync/emitter.py`, `status/models.py`, `status/reducer.py`,
  `retrospective/generator.py`, `proof/events.py`, `orchestrator_api/commands.py`,
  `cli/commands/agent/tasks_move_task.py`. Each must **import and call** `status.verdict_vocab` on its
  verdict-mapping path (satisfies the T017 positive check). Mark each as true-equivalence vs
  single-value before replacing (some spell only one direction). **Behaviour-preserving** — no verdict
  changes. Note: `orchestrator_api/commands.py::_parse_review_result_json` parses injected JSON (stays a
  reader-of-JSON, ruled in by plan §Corrected-serialization) — only its inline vocab is swept, not its
  role.
- **Files**: the 7 owned source files above.
- **Validation**: the guard (T017) — both checks — is green with only the 2-entry WP05 allowlist
  remaining; existing tests for each module stay green.

### T019 — Negative test: override never synthesizes a `review_result` verdict
- **Purpose**: D-PLAN-14 separation. The emission-scoped bridge must not let an override become an
  emitted `approved` `review_result`.
- **Steps**: Add a test asserting `arbiter_override` / `approved_after_orchestrator_fix` cannot be
  passed to the emission-scoped helper (type or runtime refusal), and that the reducer keeps override
  provenance in `ReviewOverride`, not in a synthesized `review_result` (`reducer.py:244-252`).
- **Files**: `tests/architectural/test_verdict_vocab_single_source.py` (or a sibling unit test).
- **Validation**: green; a scratch attempt to emit `approved` from an override reds.

### T020 — Census interaction check (read-only; WP04 does NOT edit the census)
- **Purpose**: Confirm `verdict_vocab.py` does not spuriously enter the census. **WP04 never edits the
  census test** (squad F8): WP01 already authored the `status/verdict_vocab.py`
  `_EXCLUDED_MODULE_REASONS` entry (WP01 T004), so there is no concurrent-edit race with WP02.
- **Steps**: Run `pytest tests/architectural/test_verdict_seam_census.py -q` and confirm green.
  `verdict_vocab.py` is a pure mapping (not a review-cycle record ctor/resolver/reader) and is excluded
  by WP01's named reason. If the census unexpectedly reds on `verdict_vocab.py`, **do not** edit the
  census test here — file it back to WP01 (its exclusion list) rather than taking an out-of-map edit.
- **Files**: (read-only) `tests/architectural/test_verdict_seam_census.py`.
- **Validation**: census green; no census-test edit in this WP's diff.

## Branch Strategy note

`already-confirmed`; base == target. Prepare with `spec-kitty implement WP04`. Depends on WP01 only;
runs parallel to WP02/WP03 (no shared source files with them — the reducer/models edits here are the
*inline vocab*, which WP02/WP03 do not touch). **The guard is intentionally not fully closed here**:
its 2-entry allowlist is emptied by WP05 — that is the guard-lands-last design.

## Definition of Done

- FR-005: one canonical bridge; the guard is non-vacuous (red pre-sweep) and green post-sweep with a
  **2-entry** allowlist (the WP05 sites). All four inbound values map totally (G1). Override never
  synthesizes a `review_result` verdict (D-PLAN-14, T019).
- Gate: `pytest tests/architectural/test_verdict_vocab_single_source.py -q` +
  the touched modules' existing tests green; `ruff` + `mypy --strict` clean (NFR-003);
  `pytest tests/architectural/test_no_legacy_terminology.py -q` (CLI/prose text touched).

## Risks

- **Guard-red-with-no-owner** — avoided by owning the 7 sites here and handing the last 2 to WP05 via a
  named allowlist WP05 empties. If WP05 forgets to empty it, the guard stays *loosely* green (2 modules
  exempt) — WP05's DoD calls this out.
- **Behaviour drift during the sweep** — some sites spell only one direction; classify before replacing.
- **tasks_move_task.py double-touch** — WP07 later threads the arbiter call site here (different
  region, strictly downstream). Keep your vocab edit localized so WP07's out-of-map edit stays clean.

## Reviewer guidance

Confirm the guard was red-first (T017 before T018). Confirm the emission-scoped helper cannot accept an
override value (D-PLAN-14). Confirm the sweep is behaviour-preserving (no verdict semantics changed).
Confirm the allowlist contains **exactly** the two WP05-owned modules and nothing else.
