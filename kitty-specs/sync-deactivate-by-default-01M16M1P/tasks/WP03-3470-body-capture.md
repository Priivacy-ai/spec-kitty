---
work_package_id: WP03
title: '#3470 body-capture short-circuit + anti-swallow'
dependencies:
- WP02
requirement_refs:
- FR-007
- FR-008
planning_base_branch: spike/3799-sync-deactivation-3798-accept-hermetic
merge_target_branch: spike/3799-sync-deactivation-3798-accept-hermetic
branch_strategy: Planning artifacts for this mission were generated on spike/3799-sync-deactivation-3798-accept-hermetic. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into spike/3799-sync-deactivation-3798-accept-hermetic unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
history:
- at: '2026-08-29T11:58:38Z'
  actor: claude
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/dossier_pipeline.py
create_intent:
- tests/deactivation/test_dossier_3470.py
execution_mode: code_change
owned_files:
- src/specify_cli/sync/dossier_pipeline.py
- tests/deactivation/test_dossier_3470.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned agent profile via `/ad-hoc-profile-load python-pedro` (role: implementer). Then read the mission plan.md "Post-plan squad corrections (BINDING)" section and the relevant contracts/ file — they are authoritative over this prompt where they conflict.

## Objective

Silence the #3470 body-outbox `RuntimeError` traceback on the default (sync-inactive) path — where it actually fires on a bare install, because no disable var is set — **without** turning the fix into a broad `try/except` that would swallow real errors when sync is on.

- **T009** — short-circuit `trigger_feature_dossier_sync_if_enabled` (`dossier_pipeline.py:471`) on `not sync_active()` with a **gated early-return before enqueue**. `_require_project_destination` (`body_queue.py:104`) stays UNTOUCHED (C-003).
- **T010** — anti-swallow test: under `SPEC_KITTY_ENABLE_SAAS_SYNC=1` on a LEGACY layout, a genuine `_require_project_destination` violation still **surfaces** — via `DossierSyncResult.errors`/log, NOT as a raised exception (the function is contractually "never raises").

## Context

Authoritative sources:

- **contracts/no-op-emission.md** — INV-2 anti-swallow (gated early-return, not try/except).
- **plan.md → BINDING** items 3 (keyed on inactive, before enqueue, gated early-return NOT try/except; `_require_project_destination` untouched — C-003) and 7 (SC-005 uses the LEGACY fixture; assert via `DossierSyncResult.errors`).
- **spec.md** — FR-007 (silence body-outbox traceback), FR-008 (anti-swallow), C-003 (preserve the destination invariant), SC-005; Edge Cases (LEGACY-layout host is exactly where #3470 fired).

**Why keyed on inactive, not the disable vars** (FR-007): the disable vars never fire on a bare install, so keying the short-circuit on them would leave the traceback live on the default path — the very path this mission must quiet. Key on `not sync_active()`.

**Why a gated early-return, not `try/except`** (FR-008 / C-003): a broad `try/except` around the enqueue would hide a genuine `_require_project_destination` violation when sync is *active*. A gated early-return only bypasses the body-capture when *inactive*; when active, the real path (and its real error surfacing) is untouched.

WP03 depends on WP02 because both edit `sync/*` and WP03 relies on `sync_active()` being the established seam. Owned file is strictly `dossier_pipeline.py` (+ the new test) — no overlap with WP02's `emitter.py`/`daemon.py`/`events.py`/`__init__.py`.

**The #3470 failure shape (what "fixed" looks like)**: on a LEGACY-layout bare install, `trigger_feature_dossier_sync_if_enabled` currently reaches the body-outbox enqueue, which calls `_require_project_destination` (`body_queue.py:104`); with no project destination resolvable on that layout, it raises a `RuntimeError` that propagates as a printed traceback even though the function is contractually "never raises" to its caller. The disable vars are unset on a bare install, so any guard keyed on them never fires — which is precisely why FR-007 re-keys the short-circuit onto `not sync_active()`. "Fixed" = the enqueue is never reached on the default path (no traceback), while the active path still reaches it and still surfaces a genuine violation.

## Per-Subtask Guidance

### T009 — Short-circuit body-capture before enqueue

**Steps**
1. In `src/specify_cli/sync/dossier_pipeline.py`, at the top of `trigger_feature_dossier_sync_if_enabled` (~:471), insert a gated early-return:
   ```python
   if not sync_active():
       return  # or the module's "no-op" DossierSyncResult, matching the existing return type
   ```
   Place it BEFORE any enqueue / body-capture work. Match the function's existing return contract (if it returns a `DossierSyncResult`, return an empty/no-op one; if it returns `None`, return `None`).
2. Import `sync_active` from `specify_cli.core.saas_sync_config` (INV-4).
3. Do **not** touch `_require_project_destination` (`body_queue.py:104`) — C-003. Do not add a `try/except`. This is a gate, not a widen.

**Files**: `src/specify_cli/sync/dossier_pipeline.py`.

**Validation**: on a bare install (sync inactive), invoking the body-capture path prints **no** `RuntimeError` traceback (FR-007). Covered by T010's default-path arm.

### T010 — Anti-swallow test (SC-005)

**Steps**
1. Create `tests/deactivation/test_dossier_3470.py` (runs on the default path, alongside WP02's `test_seam_gating.py`). Two arms:
   - **Default path (FR-007)**: sync inactive, LEGACY layout — invoke `trigger_feature_dossier_sync_if_enabled`; assert it returns cleanly and prints no body-outbox `RuntimeError` traceback.
   - **Anti-swallow (FR-008 / SC-005)**: set `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, use the LEGACY fixture at `tests/sync/test_body_integration.py:46-65`; trigger a genuine `_require_project_destination` violation (`body_queue.py:104`). Assert the violation **surfaces via `DossierSyncResult.errors`/log** — the function never raises. Do NOT assert `pytest.raises`.
2. Reuse the fixture/setup shape from `tests/sync/test_body_integration.py:46-65` for the LEGACY layout.

**Files**: `tests/deactivation/test_dossier_3470.py` (new).

**Validation**: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/python -m pytest tests/deactivation/test_dossier_3470.py -q` green (anti-swallow arm); `.venv/bin/python -m pytest tests/deactivation/test_dossier_3470.py -q` green (default-path arm — no traceback).

**Test skeleton (shape, not literal — adapt to the real signatures)**:
```python
import pytest
from specify_cli.sync import dossier_pipeline

def test_bare_install_no_body_outbox_traceback(sync_disabled, legacy_layout_repo, capsys):
    result = dossier_pipeline.trigger_feature_dossier_sync_if_enabled(...)
    captured = capsys.readouterr()
    assert "RuntimeError" not in captured.err
    # short-circuited: no enqueue attempted

def test_active_real_violation_surfaces(sync_enabled, legacy_layout_repo):
    # reuse the LEGACY fixture from tests/sync/test_body_integration.py:46-65
    result = dossier_pipeline.trigger_feature_dossier_sync_if_enabled(...)  # genuine dest violation
    assert result.errors  # surfaces via DossierSyncResult.errors — NOT a raised exception
```
`sync_disabled` / `sync_enabled` are the WP04 fixtures; if WP04 has not landed in the shared branch yet, set the env directly with `monkeypatch` and document the temporary coupling.

## Branch Strategy

- Planning base branch == merge target branch == `spike/3799-sync-deactivation-3798-accept-hermetic`; `branch_strategy: already-confirmed`.
- `spec-kitty implement WP03` allocates the execution worktree from the computed lane in `lanes.json`. Consume the resolved path.
- WP03 serializes after WP02 (shared `sync/*` files). WP08 depends on WP03.

## Test Strategy

- **Test-first / red-first (DIR-034)**: write the two-arm test in T010 first. The default-path arm is red on current code (traceback fires); the anti-swallow arm pins the behavior the T009 gate must preserve. Then land the T009 gate.
- The test lives in `tests/deactivation/` so it runs on the default path (not skipped by WP05).
- **Anti-swallow is the crux**: assert the error surfaces via `DossierSyncResult.errors`/log, NEVER via a raised exception (BINDING item 7 — the function is contractually "never raises"). A `pytest.raises` here would be wrong.
- **ruff + mypy clean**, complexity ≤ 15.
- **Targeted pytest only**; never the full suite. **Env footguns**: `.venv/bin/python -m pytest`, never `uv run`; `SPEC_KITTY_ENABLE_SAAS_SYNC=1` for the anti-swallow arm.

## Definition of Done

- `trigger_feature_dossier_sync_if_enabled` short-circuits on `not sync_active()` before enqueue; no body-outbox traceback on the default LEGACY-layout path (**FR-007**).
- The fix is a gated early-return, not a `try/except`; `_require_project_destination` untouched (**FR-008**, C-003).
- Under opt-in, a genuine destination violation still surfaces via `DossierSyncResult.errors` (**SC-005**, anti-swallow).
- ruff + mypy clean; both test arms green.

## Risks

| Risk | Mitigation |
|------|------------|
| Broad `try/except` swallows real errors when active | Use a gated early-return keyed on `not sync_active()`; anti-swallow arm proves the active path still surfaces (FR-008/SC-005). |
| Keying on disable vars leaves traceback live on bare install | Key on `not sync_active()` (FR-007) — disable vars never fire on a default install. |
| Weakening `_require_project_destination` to "fix" #3470 | C-003 forbids it — `body_queue.py:104` stays untouched; fix at the caller only. |
| Return type mismatch on the early-return | Match the function's existing return contract (no-op `DossierSyncResult` vs `None`). |
| Anti-swallow test asserts a raised exception | The function never raises — assert via `DossierSyncResult.errors`/log (BINDING item 7). |

## Reviewer Guidance

- Confirm the short-circuit is a gate (early return) and NOT a `try/except`; confirm `body_queue.py` is not in the diff (C-003).
- Confirm the gate is keyed on `not sync_active()`, not on the disable vars.
- Confirm the anti-swallow arm sets `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, uses the LEGACY fixture, and asserts on `DossierSyncResult.errors`/log — not `pytest.raises`.
- Confirm the new test lives in `tests/deactivation/` (default path), so it is not silently skipped by WP05.
