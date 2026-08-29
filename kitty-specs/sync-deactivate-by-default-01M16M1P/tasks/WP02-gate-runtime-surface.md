---
work_package_id: WP02
title: Gate the runtime surface (registration/daemon/emission/local-capture)
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- FR-015
- FR-018
planning_base_branch: spike/3799-sync-deactivation-3798-accept-hermetic
merge_target_branch: spike/3799-sync-deactivation-3798-accept-hermetic
branch_strategy: Planning artifacts for this mission were generated on spike/3799-sync-deactivation-3798-accept-hermetic. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into spike/3799-sync-deactivation-3798-accept-hermetic unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
history:
- at: '2026-08-29T11:58:38Z'
  actor: claude
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
create_intent:
- tests/deactivation/test_seam_gating.py
execution_mode: code_change
owned_files:
- src/specify_cli/sync/__init__.py
- src/specify_cli/sync/daemon.py
- src/specify_cli/sync/events.py
- src/specify_cli/sync/emitter.py
- src/specify_cli/sync/sync_doctor_core.py
- tests/deactivation/test_seam_gating.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned agent profile via `/ad-hoc-profile-load python-pedro` (role: implementer). Then read the mission plan.md "Post-plan squad corrections (BINDING)" section and the relevant contracts/ file — they are authoritative over this prompt where they conflict.

## Objective

Route **every** arming site through the single `sync_active()` seam from WP01 so that on the default (inactive) path there is no handler registration, no daemon spawn, no event emission/fanout/publish, and no emitter local-capture — closing the asymmetry where `SPEC_KITTY_SYNC_DISABLE` alone does not stop registration. Add the deactivation guard tests (seam-not-reached spies) and the FR-018 doctor advisory.

Subtasks:
- **T005** — gate `register_default_handlers` at call-time.
- **T006** — route daemon spawn + events emit/publish through `sync_active()` (replace, don't stack).
- **T007** — gate the emitter at `_emit` (return the envelope, skip capture/route/queue).
- **T008** — deactivation guard tests across the 9 surfaces + FR-018 doctor advisory.

## Context

Authoritative sources:

- **contracts/sync-active-seam.md** — the consumer table (exact line numbers + the "REPLACE prior scattered checks" rule) and INV-1..INV-4.
- **contracts/no-op-emission.md** — INV-1 (0 spawns / 0 enqueues / 0 warnings across all listed surfaces, verified by spies not log text).
- **plan.md → BINDING** items 2 (emitter `_emit`, return envelope), 3 (registration call-time), 6 (spy reuse), and the blast-radius note (all emission entrypoints reach the emitter).
- **spec.md** — FR-003/004/005/006, FR-015, NFR-001, SC-001, C-006, C-008, FR-018.

**Replace, don't stack (C-008)**: at each daemon/emission site, `sync_active()` *replaces* the existing `is_saas_sync_enabled()` / disable-var check. Do not layer a second gate on top — that re-creates the inconsistent precedence this mission removes.

**Late-bind seam (C-006)**: gating must preserve the `sync_module.<name>` late-bind seam so existing monkeypatch co-gate tests stay valid. That is exactly why registration is gated at CALL-TIME, not import-time (see T005).

## Per-Subtask Guidance

### T005 — Gate `register_default_handlers` at call-time

**Steps**
1. In `src/specify_cli/sync/__init__.py` (:455/:458), gate the **body** of `register_default_handlers` on `sync_active()`: when inactive, return early WITHOUT registering handlers. Keep the function unconditionally callable (do not guard at import-time, do not conditionally define it) — this preserves C-006's late-bind seam and lets tests re-call it after toggling env.
2. Import `sync_active` from `specify_cli.core.saas_sync_config` (INV-4 — do not re-implement).

**Files**: `src/specify_cli/sync/__init__.py`.

**Validation**: with sync inactive, calling `register_default_handlers()` registers zero handlers; with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` it registers as before (FR-015). Covered by T008 spies.

### T006 — Route daemon spawn + events emit/publish through the seam

**Steps**
1. In `src/specify_cli/sync/daemon.py` (:1131 and :1154), **replace** the prior disable-first + `is_saas_sync_enabled()` check with `sync_active()`. The implicit-spawn function at :1131/:1154 has **no existing spy** — give it a stable, importable name (or confirm its name) so T008 can `assert_not_called` on it, and record that name in the test.
2. In `src/specify_cli/sync/events.py` (:109 and :182), **replace** `is_saas_sync_enabled()` with `sync_active()`. Note (BINDING item 4): these are machine-arming; the real egress refusal lives in `SyncRuntime.publish_event`, so `sync_active()` is strictly *stricter* — INV-2 (arming ⊂ upstream of consent) holds.

**Files**: `src/specify_cli/sync/daemon.py`, `src/specify_cli/sync/events.py`.

**Validation**: inactive path → daemon-spawn fn not called, emit/publish no-op (FR-004/FR-005). Covered by T008.

### T007 — Gate the emitter at `_emit` (return envelope)

**BINDING item 2 — this is the load-bearing correction.** The direct `get_emitter().emit_*()` path (`init.py:151`, merge, etc.) flows `_emit → _capture_to_journal (~2280) / missing-uuid branch (~2308) → _queue_event_locally (2651)`, all of which **bypass** `_route_event`. Gating `_route_event` alone MISSES the direct emit path.

**Steps**
1. In `src/specify_cli/sync/emitter.py`, at the **top of `_emit`, AFTER envelope construction**, insert:
   ```python
   if not sync_active():
       return envelope
   ```
   This must sit BEFORE `_capture_to_journal (~2280)`, the missing-uuid branch (~2308), `_route_event (2633)`, and `_queue_event_locally (2651)`.
2. Returning the constructed envelope (not `None`) keeps `tests/contract/test_event_envelope.py` (asserts `emit_*` non-None) and its siblings (`test_machine_facing_canonical_fields`, `test_handoff_fixtures`, `test_identity_contract_matrix`) green, while enqueue/persist/warn are skipped.
3. This single gate covers the direct `emit_*` path AND silences the `project sync store is locked` / `Event routing failed` warnings (FR-006) — the local-capture path is never reached when inactive.
4. Import `sync_active` from `specify_cli.core.saas_sync_config`.

**Files**: `src/specify_cli/sync/emitter.py`.

**Validation**: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/python -m pytest tests/contract/test_event_envelope.py -q` stays green (envelope still non-None under opt-in); with sync inactive, `_capture_to_journal` / `_queue_event_locally` are never reached (T008 spies).

### T008 — Deactivation guard tests + FR-018 doctor advisory

**Steps**
1. Create `tests/deactivation/test_seam_gating.py` — a NEW directory that runs on the **default path** (NOT `tests/sync/`, which WP05 skips). Use spies to `assert_not_called` on the inactive path across the **9 surfaces** (`create`, `mark-status`, `move-task`, `issue-verdict`, `accept`, `implement`, `merge`, `doctor`, `next`):
   - `_queue_event_locally`
   - `register_default_handlers`
   - the implicit daemon-spawn fn (the one you named in T006)
   Reuse the spy patterns from `tests/sync/test_emitter_observability.py:135/157/224/252` (`monkeypatch.setattr(emitter, "_queue_event_locally", _boom)`). Assert seam-**not-reached** (NFR-001/SC-001) — not absence of log text.
2. Add an opt-in arm: with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, the same seams ARE reached (FR-015 lossless re-enable).
3. **FR-018 doctor advisory** in `src/specify_cli/sync/sync_doctor_core.py`: emit an advisory string when sync is inactive (explaining sync is now opt-in via `SPEC_KITTY_ENABLE_SAAS_SYNC`) plus an orphaned-daemon cleanup hint (deactivation prevents *implicit* spawn but does not kill a daemon left by a prior opted-in session — spec Edge Cases). Copy is verified against docs in WP08.

**Files**: `tests/deactivation/test_seam_gating.py` (new), `src/specify_cli/sync/sync_doctor_core.py`.

**Validation**: `.venv/bin/python -m pytest tests/deactivation/test_seam_gating.py -q` green on the default path (seams not reached); the opt-in arm green under `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. Doctor advisory renders when inactive.

## Branch Strategy

- Planning base branch == merge target branch == `spike/3799-sync-deactivation-3798-accept-hermetic`; `branch_strategy: already-confirmed`.
- `spec-kitty implement WP02` allocates the execution worktree from the computed lane in `lanes.json`. Consume the resolved path; do not reconstruct it.
- WP02→WP03 serialize (both edit `sync/*`). WP05 and WP07 depend on WP02 (they validate its gating), so land WP02 cleanly before those pick up.

## Test Strategy

- **Test-first / red-first (DIR-034)**: write the T008 seam-not-reached spies first (red — seams still fire on the ungated code), then land the gates in T005/T006/T007 until the spies go green.
- Guard tests live in `tests/deactivation/` on purpose — they must run on the **default (inactive)** path, so they must NOT be under `tests/sync/` (which WP05 gates off).
- **ruff + mypy clean**, complexity ≤ 15. If a gated function nears the ceiling, extract a small helper rather than nesting.
- **Targeted pytest only** — the node-ids under each Validation, plus `tests/contract/test_event_envelope.py` for the envelope-non-None regression. Never the full suite.
- **Env footguns**: `.venv/bin/python -m pytest`, never `uv run`. Use `SPEC_KITTY_ENABLE_SAAS_SYNC=1` for the opt-in arms.

## Definition of Done

- `register_default_handlers` gated at call-time; zero handlers on default path, full registration under opt-in (**FR-003**, C-006).
- Daemon spawn + events emit/publish routed through `sync_active()` as a replacement (**FR-004/FR-005**, C-008, INV-2).
- Emitter gated at `_emit` returning the envelope; capture/route/queue skipped; store-lock/routing warnings silent (**FR-005/FR-006**); `test_event_envelope.py` still green.
- Seam-not-reached spies green across the 9 surfaces (**NFR-001/SC-001**); opt-in arm proves lossless re-enable (**FR-015**).
- FR-018 doctor advisory implemented (**FR-018** code half; copy verified in WP08).
- ruff + mypy clean.

## Risks

| Risk | Mitigation |
|------|------------|
| Gating `_route_event` instead of `_emit` misses the direct `emit_*` path | BINDING item 2 — gate at `_emit` top, after envelope construction, before all four downstream sites. |
| Returning `None` from `_emit` breaks envelope-non-None contract tests | Return the constructed envelope, not `None` (BINDING item 2). |
| Import-time registration guard breaks the late-bind co-gate tests | Gate the body at call-time (C-006), keep the function unconditionally callable. |
| Stacking `sync_active()` on top of the old check re-creates precedence drift | Replace the old expression, do not layer (C-008). |
| Daemon-spawn fn has no spy handle | Name it stably in T006 and record the name in T008. |
| Guard tests placed under tests/sync get skipped by WP05 | Put them in `tests/deactivation/` so they run on the default path. |

## Reviewer Guidance

- Grep `sync/__init__.py`, `daemon.py`, `events.py`, `emitter.py` for any remaining bare `is_saas_sync_enabled()` at a gate site — every gate must now be `sync_active()` (replace, not stack).
- Confirm the `_emit` gate sits after envelope construction and before `_capture_to_journal` / missing-uuid / `_route_event` / `_queue_event_locally`, and returns the envelope.
- Confirm the guard tests assert *seam-not-reached* (spies), not absence of log text (NFR-001 wording).
- Confirm the opt-in arm restores full behavior (FR-015) — otherwise the replacement is over-broad.
- Confirm the doctor advisory copy matches what WP08 documents.

---
## Post-tasks squad correction (BINDING)
**T008 test-first infeasibility fix:** the suite conftest (`tests/conftest.py:427`) has an autouse fixture that **unconditionally** sets `SPEC_KITTY_ENABLE_SAAS_SYNC=1` per test (this is only de-masked in WP04, which WP02 does not depend on). Therefore the default-path guard tests in `tests/deactivation/test_seam_gating.py` MUST force sync-inactive **in-test** — `monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)` (and delenv SYNC_DISABLE / SYNC_MINIMAL_IMPORT to normalize) — so `sync_active()` is False and the `assert_not_called` spies are meaningful. Do NOT rely on the conftest default (it lands in WP04). Also confirm tracker emission (`tracker/origin.py`) routes through `_emit` — if it constructs its own path, gate it too (FR-005 names dashboard/finalize/retrospective/init/tracker).
