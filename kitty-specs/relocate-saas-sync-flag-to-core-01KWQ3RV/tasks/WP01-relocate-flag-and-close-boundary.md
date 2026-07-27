---
work_package_id: WP01
title: Relocate the flag reader and close the CORE-INTEGRATION boundary
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
tracker_refs: []
planning_base_branch: feat/relocate-saas-sync-flag-to-core
merge_target_branch: feat/relocate-saas-sync-flag-to-core
branch_strategy: Planning artifacts for this mission were generated on feat/relocate-saas-sync-flag-to-core. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/relocate-saas-sync-flag-to-core unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Relocate and close boundary
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1318167"
history:
- at: '2026-07-04T18:15:54Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/saas_sync_config.py
create_intent:
- src/specify_cli/core/saas_sync_config.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/saas_sync_config.py
- src/specify_cli/saas/rollout.py
- src/specify_cli/readiness/coordinator.py
- src/specify_cli/sync/feature_flags.py
- src/specify_cli/tracker/feature_flags.py
- src/specify_cli/readiness/upgrade_ux.py
- tests/architectural/test_integration_boundary.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Relocate the flag reader and close the CORE↛INTEGRATION boundary

## ⚡ Do This First: Load Agent Profile
Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.
- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match.

---

## Objective

Remove the last CORE↛INTEGRATION import-boundary exemption. Move the pure
`SPEC_KITTY_ENABLE_SAAS_SYNC` reader from INTEGRATION `src/specify_cli/saas/rollout.py`
into a new CORE module `src/specify_cli/core/saas_sync_config.py` (the single
canonical *definition*), repoint the sole CORE caller, retain `saas/rollout.py`
as a thin re-export shim, empty the boundary `ALLOWLIST` and tighten its
count-ratchet to `== 0`, remove the now-stale positive-control assertion, and fix
three stale "canonical home" docstrings. **No behavior change** — the retained
shim preserves object identity so all existing tests pass unchanged.

**ATDD-first (charter C-011)**: land the RED commit first (T001), then the GREEN
implementation. The reviewer verifies red-on-base → green-on-final.

## Charter notes
- **Single canonical authority**: exactly one `def is_saas_sync_enabled` / `def saas_sync_disabled_message` post-WP, in `core/saas_sync_config.py`. Every other surface re-exports; never redefine.
- **Scoped testing**: run ONLY the bounding packages (below), never the full suite.
- **Terminology canon**: no new `feature*` identifiers.

## Subtasks

### T001 — RED commit (the ATDD pin)
In `tests/architectural/test_integration_boundary.py`, in ONE commit while
`readiness/coordinator.py:237` still imports `saas.rollout`:
1. Empty the allowlist: `ALLOWLIST: frozenset[tuple[str, str]] = frozenset()` (delete the single tuple at ~`:88-101`).
2. Delete the positive-control block in `test_allowlist_cannot_be_bypassed` (~`:264-272`) — the part that builds `allow_src = "from specify_cli.saas.rollout import is_saas_sync_enabled\n"` for `coordinator.py` and asserts `_scan_trees` suppresses it. (With the allowlist empty this asserts-and-stays-red; it is testing a mechanism you are deleting.) **Keep** the negative-control block (~`:246-262`) where a non-allowlisted `specify_cli.sync.*` import IS reported — that is what keeps the scanner honest.
Confirm the RED state: `PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/test_integration_boundary.py -p no:cacheprovider -q` → `test_no_core_imports_integration` is RED (the coordinator→saas.rollout edge is now unexempted), while `test_allowlist_count_ratchet` and `test_allowlist_cannot_be_bypassed` are GREEN. Commit as `test(WP01): red — empty CORE-INTEGRATION allowlist + drop stale positive-control`.

### T002 — Create the CORE module
Create `src/specify_cli/core/saas_sync_config.py` containing, **byte-for-byte** from the current `saas/rollout.py`: the module docstring (updated to say it is the canonical home; drop the "both feature_flags shims delegate here" line or keep it — it stays true), `SAAS_SYNC_ENV_VAR`, `_TRUTHY_VALUES`, `_DISABLED_MESSAGE`, `is_saas_sync_enabled()`, `saas_sync_disabled_message()`. Add `__all__ = ["SAAS_SYNC_ENV_VAR", "is_saas_sync_enabled", "saas_sync_disabled_message"]`. Imports: only `from __future__ import annotations` + `import os` (stdlib-only → no cycle, C-001).

### T003 — Repoint the sole CORE importer
`src/specify_cli/readiness/coordinator.py:237`: change the lazy
`from specify_cli.saas.rollout import is_saas_sync_enabled` →
`from specify_cli.core.saas_sync_config import is_saas_sync_enabled` (keep the `# noqa: PLC0415` if present; it stays a lazy import). Re-grep to confirm this is the ONLY CORE-set (`core|status|readiness|invocation`) importer of `specify_cli.saas.rollout`:
`grep -rn "specify_cli.saas.rollout" src/specify_cli/{core,status,readiness,invocation}/` → after the repoint, nothing.

### T004 — Retain `saas/rollout.py` as a thin re-export shim
Rewrite `src/specify_cli/saas/rollout.py` to:
```python
"""Backward-compat re-export shim. Canonical home: specify_cli.core.saas_sync_config."""
from __future__ import annotations
from specify_cli.core.saas_sync_config import (
    SAAS_SYNC_ENV_VAR,
    is_saas_sync_enabled,
    saas_sync_disabled_message,
)
__all__ = ["SAAS_SYNC_ENV_VAR", "is_saas_sync_enabled", "saas_sync_disabled_message"]
```
This preserves **object identity** (the same function objects), so `tests/saas/test_rollout.py`'s `is`-identity assertions pass unchanged. **Do NOT change the import wiring / behavior** of `saas/__init__.py`, `sync/feature_flags.py`, `tracker/feature_flags.py`, or the `sync`/`tracker` `__init__` facades — they import from `saas.rollout`, which still resolves. (The `sync`/`tracker` `feature_flags` docstring-only campsite edits in T006 are the ONLY permitted change to those two files; `git diff -- src/specify_cli/sync/feature_flags.py src/specify_cli/tracker/feature_flags.py` must show only docstring lines changed. `saas/__init__.py` gets NO edit.) Verify: `python -c "from specify_cli.saas import is_saas_sync_enabled; from specify_cli.sync.feature_flags import is_saas_sync_enabled as b; from specify_cli.core.saas_sync_config import is_saas_sync_enabled as c; assert b is c"`.

### T005 — Tighten the ratchet + sweep the stale prose (GREEN for the boundary)
In `tests/architectural/test_integration_boundary.py`: change `test_allowlist_count_ratchet`'s assertion `len(ALLOWLIST) <= 1` → `len(ALLOWLIST) == 0` (~`:289`), with an updated message ("exemption set is permanently closed; no CORE→INTEGRATION crossing is allowed"). Then sweep ALL the now-stale `<= 1` / "at most one" / "exactly one exemption" prose in this file — verified locations: lines **32, 34, 45, 98(gone with the entry), 276, 282, 284, 285**. After T002–T004 land, `test_no_core_imports_integration` goes GREEN.

### T006 — Fix the 3 stale docstrings `[P]`
- `src/specify_cli/sync/feature_flags.py:1` and `src/specify_cli/tracker/feature_flags.py:1`: the "canonical home is `specify_cli.saas.rollout`" wording → `specify_cli.core.saas_sync_config` (the home is now core; rollout is itself a shim).
- `src/specify_cli/readiness/upgrade_ux.py:77`: the docstring `"Stable truthy parser shared with saas.rollout."` is ALREADY false (it is a *divergent copy*, not shared). Reword to drop the false "shared" claim (e.g. `"Local truthy parser for upgrade env flags."`). Do NOT point it at `core.saas_sync_config` (it still does not consume that module). The 3-way truthy-parser unification is a tracked follow-up, out of scope here.

### T007 — Validate GREEN (scoped, objective gates)
```bash
PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/test_integration_boundary.py tests/saas/ -p no:cacheprovider -q
PWHEADLESS=1 .venv/bin/python -m pytest -k "feature_flag" -p no:cacheprovider -q
.venv/bin/python -m ruff check src/specify_cli/core/saas_sync_config.py src/specify_cli/saas/rollout.py src/specify_cli/readiness/coordinator.py src/specify_cli/sync/feature_flags.py src/specify_cli/tracker/feature_flags.py src/specify_cli/readiness/upgrade_ux.py
.venv/bin/python -m mypy --strict src/specify_cli/core/saas_sync_config.py
# single canonical definition — ASSERT exactly one def each (not eyeball):
test "$(grep -rc '^def is_saas_sync_enabled' src/ | awk -F: '{s+=$2} END{print s}')" = 1 && echo "one is_saas_sync_enabled def"
test "$(grep -rc '^def saas_sync_disabled_message' src/ | awk -F: '{s+=$2} END{print s}')" = 1 && echo "one saas_sync_disabled_message def"
# prose sweep GATE (mirrors WP02) — no stale <=1/at-most-one/exactly-one exemption prose remains:
grep -nzE "<= *1|at most one|exactly one exemption" tests/architectural/test_integration_boundary.py && echo "FAIL: stale prose" || echo "prose swept"
# test_rollout.py truly unchanged (objective):
test -z "$(git diff $(git merge-base HEAD feat/relocate-saas-sync-flag-to-core)..HEAD -- tests/saas/test_rollout.py)" && echo "test_rollout.py unchanged"
```
All green; `tests/saas/test_rollout.py` passes **unchanged** (git-diff empty). Commit the green work as `feat(WP01): relocate SPEC_KITTY_ENABLE_SAAS_SYNC reader to core.saas_sync_config; close the CORE-INTEGRATION boundary`.

## Definition of Done
- New `core/saas_sync_config.py` holds the single definition (+ `__all__`); stdlib-only.
- `readiness/coordinator.py` imports from core; NO CORE-set module imports `specify_cli.saas.rollout` (or any INTEGRATION module).
- `saas/rollout.py` is a re-export shim; `tests/saas/test_rollout.py` identity tests pass **unchanged**.
- `test_integration_boundary.py`: `ALLOWLIST` empty, ratchet `== 0`, positive-control removed, negative-control retained, all `<= 1` prose swept; `test_no_core_imports_integration` GREEN.
- The 3 stale docstrings corrected.
- Scoped tests + ruff + mypy-strict green.

## Risks
- **Deleting rollout.py** (tempting) breaks `test_rollout.py` identity tests → NFR-001 violation. Mitigation: this WP mandates retain-as-shim (T004).
- **Impure red** if the positive-control removal is split from the allowlist emptying. Mitigation: T001 bundles both in the red commit.
- **Missed CORE importer**: T003 re-greps the CORE set; the boundary scan is the backstop.

## Reviewer guidance
Verify: (1) red-on-base — `test_no_core_imports_integration` was RED at the WP's planning base with the T001 commit, GREEN at the final commit; (2) `saas/rollout.py` still exists and re-exports the SAME objects (identity); (3) exactly one `def` for each function, in core; (4) the negative-control injection proof still passes (scanner not vacuous); (5) `tests/saas/test_rollout.py` unchanged; (6) no new `feature*` identifier. Reject if rollout.py was deleted, if the ratchet stayed `<= 1`, or if the positive-control was left in (boundary suite would be red).

## Activity Log

- 2026-07-04T18:30:41Z – claude:opus:python-pedro:implementer – shell_pid=1269175 – Assigned agent via action command
- 2026-07-04T18:39:26Z – claude:opus:python-pedro:implementer – shell_pid=1269175 – Ready for review: relocated SPEC_KITTY_ENABLE_SAAS_SYNC reader to core/saas_sync_config.py (single def), saas/rollout.py now a re-export shim (identity preserved), coordinator repointed to core, ALLOWLIST emptied + ratchet ==0, positive-control removed/negative-control kept, 3 stale docstrings fixed. Gates: scoped pytest 56 passed + feature_flag 33 passed; ruff exit=0; mypy --strict exit=0; def-count is_saas_sync_enabled=1 & saas_sync_disabled_message=1; prose swept; test_rollout.py unchanged (empty diff). RED commit f4e6f0c2e, GREEN commit 04a96715e.
- 2026-07-04T18:39:59Z – claude:opus:reviewer-renata:reviewer – shell_pid=1318167 – Started review via action command
- 2026-07-04T18:48:20Z – user – shell_pid=1318167 – Review passed: red-on-base independently reproduced (at RED f4e6f0c2e test_no_core_imports_integration FAILED 1/4 while ratchet==0 + negative-control stayed GREEN; coordinator still imported saas.rollout, core module absent -> non-vacuous ATDD). saas/rollout.py retained as re-export shim, object identity preserved (saas.rollout/saas/sync.feature_flags/tracker.feature_flags all 'is' core); tests/saas/test_rollout.py diff empty. Exactly one def is_saas_sync_enabled + one def saas_sync_disabled_message, both in core/saas_sync_config.py. No CORE-set module imports specify_cli.saas (grep clean). ALLOWLIST empty, ratchet asserts ==0, positive-control removed, negative-control injection proof retained. Core module stdlib-only (os+__future__) with __all__. Campsite clean: sync/tracker feature_flags docstring-only, upgrade_ux dropped false 'shared' claim, saas/__init__ untouched, no new feature* identifiers, changed set==owned_files. Gates: boundary+saas 56 passed, -k feature_flag 33 passed, ruff clean, mypy --strict clean. Gate-4 issue-matrix recorded: #2172 verified-already-fixed, #2252 in-mission (terminal pending WP02).
