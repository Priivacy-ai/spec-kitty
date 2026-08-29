---
work_package_id: WP05
title: Skipif bulk rollout (occurrence-map-driven)
dependencies:
- WP02
- WP04
requirement_refs:
- FR-011
- FR-012
planning_base_branch: spike/3799-sync-deactivation-3798-accept-hermetic
merge_target_branch: spike/3799-sync-deactivation-3798-accept-hermetic
branch_strategy: Planning artifacts for this mission were generated on spike/3799-sync-deactivation-3798-accept-hermetic. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into spike/3799-sync-deactivation-3798-accept-hermetic unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
history:
- at: '2026-08-29T11:58:38Z'
  actor: claude
  action: created
agent_profile: python-pedro
authoritative_surface: tests/sync/
create_intent: []
execution_mode: code_change
owned_files:
- tests/sync/**
- tests/specify_cli/sync/**
- tests/delivery/**
- tests/dossier/**
- tests/stress/**
- tests/status/**
- tests/integration/test_offline_queue_overflow.py
- tests/cli/commands/test_sync_*.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned agent profile via `/ad-hoc-profile-load python-pedro` (role: implementer). Then read the mission plan.md "Post-plan squad corrections (BINDING)" section and the relevant contracts/ file — they are authoritative over this prompt where they conflict.

## Objective

Bulk-apply a module-level `skipif`-on-opt-in guard to every sync-coupled test module so they **skip, not fail** on the default (sync-off) path — and fold in #2809's two named tests. This is a **bulk edit** (`change_mode: bulk_edit`); the diff MUST comply with `occurrence_map.yaml → tests_fixtures`.

- **T014** — module-level skipif across `tests/sync/` (187) + `tests/specify_cli/sync/` (7).
- **T015** — same for the scattered coupled clusters.
- **T016** — fold #2809's two named tests.

## Context

Authoritative sources:

- **occurrence_map.yaml → tests_fixtures** (action: transform; `keep_lane_markers: true`) — the exact file set and the "extend the existing pytestmark list" rule.
- **plan.md → BINDING** items — WP05 depends on WP02 (validates its gating) and WP04 (default-off must be real first).
- **spec.md** — FR-011 (extend gating to scattered clusters), FR-012 (#2809 fold), NFR-003 (completeness gate + census), User Story 3, SC-003.
- **Bulk-edit gate (DIR-035)**: the WP05 diff is checked against `occurrence_map.yaml`. Invoke the `spec-kitty-bulk-edit-classification` guardrail discipline.

**The load-bearing rule (occurrence_map + BINDING)**: `keep_lane_markers: true`. The CI collection-completeness gate selects files by their existing lane markers. So you must **EXTEND** the existing `pytestmark` list with the skipif — never replace the lane markers. Pattern:
```python
import pytest
from specify_cli.core.saas_sync_config import sync_active

pytestmark = [
    pytest.mark.fast,  # or whatever lane marker(s) already present — KEEP them
    pytest.mark.skipif(not sync_active(), reason="sync inactive by default; opt-in via SPEC_KITTY_ENABLE_SAAS_SYNC (#3799)"),
]
```
Where a module already has a scalar `pytestmark = pytest.mark.X`, convert to a list and append; where it has a list, append. Do NOT drop existing markers (completeness gate depends on them).

**Depends on WP04**: the conftest must be de-masked first, or every skipif is inert (the flag is forced on). Verify one sync module actually skips (the WP04 coordination point) before rolling out.

## Per-Subtask Guidance

### T014 — Bulk skipif across `tests/sync/` + `tests/specify_cli/sync/`

**Steps**
1. For each module under `tests/sync/**` (187) and `tests/specify_cli/sync/**` (7), add/extend the module-level `pytestmark` skipif per the pattern above.
2. Ensure the `sync_active`/`pytest` imports exist at module top (occurrence_map `import_paths: extend` — import `sync_active` from `specify_cli.core.saas_sync_config`; note the occurrence_map's stale `core.env` mention is superseded by the BINDING correction).
3. KEEP every existing lane marker.

**Files**: `tests/sync/**`, `tests/specify_cli/sync/**`.

**Validation**: `.venv/bin/python -m pytest tests/sync tests/specify_cli/sync -q` → **skipped, 0 failed** on the default path. `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/python -m pytest tests/sync tests/specify_cli/sync --collect-only -q` still selects the same non-skipped node-ids as the WP01 baseline (opt-in parity — validated formally in WP07 T020).

### T015 — Skipif for the scattered coupled clusters

**Steps**
1. Apply the same module-level skipif (extending pytestmark, keeping lane markers) to the clusters in FR-011 / occurrence_map:
   - `tests/delivery/**`
   - `tests/dossier/test_snapshot_emit.py`
   - `tests/stress/test_concurrent_emits.py`
   - `tests/status/**` fanout modules (only the sync-coupled ones)
   - `tests/integration/test_offline_queue_overflow.py`
   - `tests/cli/commands/test_sync_*.py`
2. Scope precisely: within `tests/status/**` and `tests/dossier/**`, gate only the modules that are genuinely sync-coupled (emit/fanout/snapshot-emit) — do not over-skip unrelated status/dossier tests. Cross-check against the WP01 census SET (`sync_deactivate_test_census.txt`).

**Files**: `tests/delivery/**`, `tests/dossier/**`, `tests/stress/**`, `tests/status/**`, `tests/integration/test_offline_queue_overflow.py`, `tests/cli/commands/test_sync_*.py`.

**Validation**: `.venv/bin/python -m pytest tests/delivery tests/dossier tests/stress tests/status tests/integration/test_offline_queue_overflow.py -q` → the sync-coupled modules skip, 0 failed; non-coupled modules still run.

### T016 — Fold #2809's two named tests

**Steps**
1. Add the skipif guard so these two stop redding on the default path (FR-012):
   - `test_daemon_sync_disable_env.py::test_sync_disable_env_skips_daemon_spawn`
   - `test_strict_json_stdout.py::test_mission_create_json_strict_when_sync_skips_ingress`
2. If these live in modules that also hold non-sync tests, prefer a targeted per-test `@pytest.mark.skipif` rather than a module-level guard, so only the two named tests are gated. If the whole module is sync-coupled, module-level is fine. Ensure both files are in the WP01 census SET.

**Files**: whichever modules host the two named tests (within the owned globs / documented if elsewhere — coordinate with WP01's census entries).

**Validation**: `.venv/bin/python -m pytest -q` targeting just those two node-ids on the default path → skipped; under `SPEC_KITTY_ENABLE_SAAS_SYNC=1` → they run.

## Branch Strategy

- Planning base branch == merge target branch == `spike/3799-sync-deactivation-3798-accept-hermetic`; `branch_strategy: already-confirmed`.
- `spec-kitty implement WP05` allocates the execution worktree from the computed lane in `lanes.json`.
- WP05 depends on WP02 (gating exists) AND WP04 (default-off is real). WP06's census locks the WP05 file set — keep the two in agreement.

## Test Strategy

- **Test-first is inverted here**: WP05 makes existing tests skip. The "red-first" signal is that on the de-masked default path these modules would FAIL (import/collect) before the skipif; after, they SKIP. Confirm the WP04 coordination point (one module skips) before bulk rollout.
- **Bulk-edit discipline (DIR-035)**: every edited file must map to an `occurrence_map.yaml → tests_fixtures` category (action: transform). Run the bulk-edit classification guardrail; the diff must comply.
- **Keep lane markers** — extend `pytestmark`, never replace. The completeness gate selects by marker (NFR-003).
- **Opt-in parity**: after rollout, `--collect-only` under opt-in must still match the WP01 baseline (no net coverage loss — NFR-004; formal check in WP07).
- **ruff + mypy clean** for every touched module (the added imports + pytestmark must lint).
- **Targeted pytest only**; never the full suite (187+ files — run cluster by cluster). **Env footguns**: `.venv/bin/python -m pytest`, never `uv run`; `SPEC_KITTY_ENABLE_SAAS_SYNC=1` to confirm they run under opt-in.

## Definition of Done

- `tests/sync/**` + `tests/specify_cli/sync/**` skip on default, run under opt-in (**FR-011**, SC-003).
- Scattered clusters gated with lane markers kept; only sync-coupled modules skipped (**FR-011**).
- #2809's two named tests folded and no longer red on the default path (**FR-012**).
- Diff complies with `occurrence_map.yaml → tests_fixtures` (DIR-035).
- Edited file set agrees with the WP01 census SET (feeds WP06).
- ruff + mypy clean; clusters report skipped/0-failed on default; opt-in parity preserved.

## Risks

| Risk | Mitigation |
|------|------------|
| Replacing lane markers breaks the completeness gate | EXTEND pytestmark, keep lane markers (`keep_lane_markers: true`). |
| Over-skipping unrelated status/dossier tests | Scope to genuinely sync-coupled modules; cross-check the WP01 census SET. |
| skipif inert because conftest still forces opt-in | Depends on WP04 — verify one module skips before bulk rollout. |
| Bulk diff drifts from occurrence_map | Run the bulk-edit classification guardrail; every file maps to `tests_fixtures`. |
| File set diverges from WP06 census | Keep the edited set == WP01 census SET; WP06 asserts equality. |
| Opt-in parity lost (a previously-green test newly skipped) | Confirm `--collect-only` under opt-in matches WP01 baseline. |

## Reviewer Guidance

- Confirm every edit EXTENDS `pytestmark` (lane markers intact), never replaces.
- Confirm the imports use `specify_cli.core.saas_sync_config.sync_active` (not the stale `core.env` from occurrence_map).
- Confirm #2809's two tests are gated (per-test if the module is mixed).
- Confirm the edited file set matches the WP01 census SET exactly (WP06 will red otherwise).
- Confirm default-path run is skipped/0-failed and opt-in run still collects the WP01 baseline node-ids.
- Confirm the diff complies with `occurrence_map.yaml` (DIR-035 bulk-edit gate).

---
## Post-tasks squad correction (BINDING)
**Canonical skipif reason string (shared with WP06 census):** every skip added by this WP — module-level `pytestmark` AND the per-test skips for #2809's two named tests (T016) — MUST use the EXACT reason string:
```
sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run
```
WP06's census matches on this TEXT marker (not on module-level `pytestmark` AST), so per-test skips are counted. Do not paraphrase the reason.
