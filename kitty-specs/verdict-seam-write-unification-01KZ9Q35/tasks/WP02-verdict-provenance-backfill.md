---
work_package_id: WP02
title: Verdict-provenance backfill + provenance gate
dependencies:
- WP01
requirement_refs:
- FR-012
planning_base_branch: feat/verdict-seam-write-unification
merge_target_branch: feat/verdict-seam-write-unification
branch_strategy: Planning artifacts for this mission were generated on feat/verdict-seam-write-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verdict-seam-write-unification unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/migration/verdict_provenance_backfill.py
create_intent:
- src/specify_cli/migration/verdict_provenance_backfill.py
- tests/migration/test_verdict_provenance_backfill.py
execution_mode: code_change
owned_files:
- src/specify_cli/migration/verdict_provenance_backfill.py
- tests/migration/test_verdict_provenance_backfill.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned profile: run `/ad-hoc-profile-load python-pedro` (or
`spec-kitty charter context --action implement`). Do not start work until the profile is loaded.

## Objective

Populate the event authority for **every** existing mission **before** any reader flips. Deliver an
idempotent migration that reduces each existing **terminal `.md` verdict** into `status.events.jsonl`,
plus a **provenance predicate** (a pure function: "terminal `.md` verdict + no event `review_result`
slot") that WP05's SC-008 interlock imports and calls. Scope is **backfill + provenance predicate
only** — the authoritative durability write (FR-008 add-leg) is **WP03's** (it owns `status/emit.py`);
this WP does **not** wire the recording path.

## Context

- **Requirements**: FR-012 (backfill + provenance predicate); SC-008 (no stranded history), SC-003
  (partial). The FR-008 add-leg is **WP03/T013** (owns `emit.py`) — removed from this WP (squad F6:
  the recording path is WP03/WP05-owned and may already exist via the #3211 render path, so WP02 had
  no owned landing surface for it).
- **Contract**: [contracts/provenance-backfill.md](../contracts/provenance-backfill.md) — G1
  idempotent on `(mission_id, wp_id, verdict, cycle)`, G2 provenance ≠ location, G3 blocks reader
  deletion.
- **Decisions**: **D-PLAN-10** — use `append_events_atomic_verified` with a **hand-constructed event**
  (repo precedent: `migration/backfill_runtime_state.py:1507`), **NOT** `emit_status_transition`
  (it derives `from_lane` from the WP's *current* lane and runs `validate_transition`, so it cannot
  replay a historical `in_review→…` edge onto a settled WP). The event's `at` **MUST** be the
  **historical** verdict timestamp from the `.md`/git record, never `now()` — a late-stamped rejection
  would sort last and resurrect over a real later approval. **D-PLAN-15** — the provenance predicate
  ("terminal `.md` verdict + no event slot") is **new and distinct** from the reconcile doctor's
  *location* classes (`deleted_coord_branch_absorption`, `live_coord_pre_adr_primary_record`).
- **Census**: this WP adds a `verdict_seam_census.yaml` **row** for the new module — an **out-of-map**
  edit to WP01's census **fixture** only. The matching `_EXCLUDED_MODULE_REASONS` entry in
  `test_verdict_seam_census.py` is **authored by WP01** (forward-declared in T004), so WP02 never
  touches the census *test* — no concurrent-edit race with WP04 (paula F2). Rationale: the backfill
  *writes* the event authority; it is not a frontmatter verdict reader. Safe because WP02 depends on
  WP01 (serial; no concurrent census-fixture writer).

## Subtasks

### T006 — Red-first: SC-008 hermetic pin (pre-event `.md`-only rejection still refuses after backfill)
- **Purpose**: The load-bearing safety anchor (US6). Seed a mission whose **only** rejection record is
  a pre-event `review-cycle-N.md` with no `review_result` event slot; assert that **after** the
  backfill the reducer snapshot carries the rejection and the approval guard still refuses. Red-first:
  before the migration exists, the event slot is empty and the guard would fail open once readers flip.
- **Steps**: Build the fixture in `tests/migration/test_verdict_provenance_backfill.py`. Red against
  the absent migration.
- **Files**: `tests/migration/test_verdict_provenance_backfill.py`.
- **Validation**: fails before T008; green after.

### T007 — Define "terminal verdict" + the historical timestamp source
- **Purpose**: Pin the semantics D-PLAN-10 requires before writing the reducer.
- **Steps**: In the module, define **terminal verdict** = the latest `review-cycle-N.md` for the WP
  (highest cycle N). Extract its verdict and its **historical `at`** (frontmatter timestamp, else the
  git commit time of the `.md`). Handle supersession: a `.md` rejection superseded by a later
  lane-only approval must **not** resurrect — the reducer ordering (by `at`) resolves it.
- **Files**: `src/specify_cli/migration/verdict_provenance_backfill.py`.
- **Validation**: covered by the ordering test (T009).

### T008 — Idempotent backfill via `append_events_atomic_verified`
- **Purpose**: FR-012 core. Reduce each qualifying terminal `.md` verdict into `status.events.jsonl`.
- **Steps**: For each mission/WP with a terminal `.md` verdict and **no** event `review_result` slot,
  hand-construct a `review_result` event (verdict bridged via the WP04 surface once available; until
  then map `rejected→changes_requested`, `approved→approved` locally with a `# TODO(WP04)` pointer —
  **do not** invent a second permanent bridge, C-001) with `at` = historical timestamp, and append via
  `append_events_atomic_verified`. Idempotency key includes temporal identity `(mission_id, wp_id,
  verdict, cycle)` (G1) — a re-run adds nothing.
- **Files**: `src/specify_cli/migration/verdict_provenance_backfill.py`.
- **Validation**: T006 green; re-running the migration in the test appends zero events (US6 scenario 1).

### T009 — Reducer ordering test (historical rejection + later approval → approved)
- **Purpose**: Prove the `at`-timestamp discipline (D-PLAN-10): a WP whose history is `.md` rejection
  **then** a later approval reduces to `approved`, not `changes_requested`.
- **Steps**: Seed both records; run backfill; assert `event_sourced_review_result` == approved. Add the
  inverse (later rejection wins). This is the anti-resurrection guard.
- **Files**: `tests/migration/test_verdict_provenance_backfill.py`.
- **Validation**: green; flipping `at` to `now()` in a scratch experiment reds it (sanity of the guard).

### T010 — Provenance predicate as a PURE FUNCTION in the owned module (no CLI)
- **Purpose**: FR-012 predicate / G3. Add the **provenance** predicate distinct from the doctor's
  location classes (D-PLAN-15): "any WP with a terminal `.md` verdict and no event `review_result`
  slot".
- **Steps**: Implement it as a **pure function inside** `verdict_provenance_backfill.py` (squad F7 /
  paula F1) — e.g. `stranded_verdict_findings(feature_dir) -> list[ProvenanceFinding]` returning
  `{wp_id, has_md_verdict, has_event_slot}` rows. **Do not** add a `--json`/CLI surface: WP02 owns only
  the migration module, not `_coordination_doctor.py`/the reconcile-doctor CLI, so a CLI gate would be
  unowned. WP05's SC-008 interlock (T021) **imports and calls** this function directly.
- **Files**: `src/specify_cli/migration/verdict_provenance_backfill.py`.
- **Validation**: US6 scenario 2 — the function returns non-zero findings before backfill, zero after.

## Branch Strategy note

`already-confirmed`; base == target == `feat/verdict-seam-write-unification`. Prepare with
`spec-kitty implement WP02` (coord-topology lane worktree from `lanes.json`). Serial in the census
chain: merge **after** WP01, **before** WP05.

## Definition of Done

- SC-008: a mission whose only rejection is a pre-event `.md` still refuses approval after backfill
  (T006); the provenance predicate (pure function, T010) returns zero stranded findings after a run.
- G1 idempotent; the ordering test (T009) proves the `at` discipline; the census **row** lands in the
  same change (out-of-map to WP01's `verdict_seam_census.yaml` fixture; the exclusion is WP01's).
- Gate: `pytest tests/migration/test_verdict_provenance_backfill.py tests/status/test_reducer.py -q`
  green; `ruff` + `mypy --strict` clean (NFR-003).

## Risks

- **Temporal correctness of `at`** — the whole anti-resurrection guarantee rides on it (T009).
- **Idempotency across re-runs** — the key must include cycle + verdict, not just `(mission, wp)`.
- **Bridge duplication** — the local rejected↔changes_requested map is a `# TODO(WP04)` stopgap; do not
  let it become a second permanent bridge (C-001; WP04 is the canonical surface).

## Reviewer guidance

Verify `append_events_atomic_verified` is used, **not** `emit_status_transition`, for the historical
replay (D-PLAN-10). Verify `at` is the historical timestamp (grep for `now()`/`utcnow()` on the event
path — should be absent). Verify the provenance predicate is genuinely distinct from the location
classes (D-PLAN-15). Confirm the `.md` commit is **still hard-error** here (demote is WP05).
