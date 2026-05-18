# SaaS-producing mission-lifecycle paths — WP04 T018 inventory

**Mission**: `mvp-cli-sync-boundary-completion-01KRX11M`
**Author**: implementer-ivan (claude:opus-4.7)
**Date**: 2026-05-18
**Purpose**: Enumerate every CLI entry point that can enqueue SaaS-visible
work (event-queue rows, body-upload rows, or direct SaaS HTTP emissions)
so reviewers can verify FR-002 / FR-009 coverage at a glance. Each row
documents the gate status — whether the entry point passes through
`run_preflight(...)` (`src/specify_cli/sync/preflight.py`) before
producing any side effect.

## Method

1. Grep `src/specify_cli/cli/commands/agent/` for: `OfflineQueue`,
   `BodyUploadQueue`, `enqueue`, `body_upload`, `WPCreated`,
   `WPStatusChanged`, `emit_wp_created`, `emit_artifact_phase`,
   `trigger_feature_dossier_sync_if_enabled`.
2. For each call site, walk up to the containing `@app.command(...)`
   entry point.
3. Record the entry point, its SaaS-visible side effect, and whether
   the side effect is gated by `run_preflight`.

## Inventory

| Entry point (file:line, function) | SaaS-visible side effect | Gated by `run_preflight`? |
|-----------------------------------|--------------------------|---------------------------|
| `src/specify_cli/cli/commands/sync.py:1184` — `sync now` | Drains `OfflineQueue`; pushes events to SaaS. Reads body-upload queue. | **Yes** — `run_preflight(repo_root=Path.cwd(), require_auth=True)` runs at command entry (line 1204); refuses with exit 2 on any failure. (WP03, T012) |
| `src/specify_cli/cli/commands/agent/mission.py:881` — `setup-plan` | Emits `SpecifyCompleted` / `PlanStarted` / `PlanCompleted` (`emit_artifact_phase`); triggers dossier body-upload pipeline (`trigger_feature_dossier_sync_if_enabled` → `OfflineBodyUploadQueue`). | **Yes** — WP04 T017. `run_preflight(repo_root=repo_root, require_auth=True)` runs immediately after the FR-011 hosted-auth refusal, guarded by the same `SPEC_KITTY_ENABLE_SAAS_SYNC=1` env. Refuses with exit 2 before any `emit_*` or dossier call. |
| `src/specify_cli/cli/commands/agent/mission.py:1578` — `finalize-tasks` | Emits `WPCreated` (`emit_wp_created`) and `TasksCompleted` (`emit_artifact_phase`); triggers dossier body-upload (`trigger_feature_dossier_sync_if_enabled`). | **No (via `sync now`)** — direct enqueue / emission is not gated at the `finalize-tasks` entry point. SaaS egress goes through `sync now`, which IS gated by `run_preflight` (WP03). Adding an enqueue-side gate here would regress the existing test suite (see "Out-of-scope follow-ups" below). |
| `src/specify_cli/cli/commands/agent/tasks.py:2491` — `agent tasks ...` subcommand calling `trigger_feature_dossier_sync_if_enabled` | Triggers dossier body-upload pipeline. | **No (via `sync now`)** — direct enqueue is not gated at the `tasks` entry point itself, but the body-upload queue rows it produces only ship via `sync now`, which IS gated. No additional gating required at this call site (WP01's preflight contract treats `sync now` as the SaaS egress chokepoint). Follow-up tracked below. |
| `src/specify_cli/cli/commands/agent/workflow.py:742` — `workflow ...` subcommand calling `trigger_feature_dossier_sync_if_enabled` | Triggers dossier body-upload pipeline. | **No (via `sync now`)** — same reasoning as the `tasks` row: enqueue not gated, egress (`sync now`) is. Follow-up tracked below. |

## Doctor surface consistency check

| Surface | Detection helper | Status |
|---------|------------------|--------|
| `src/specify_cli/cli/commands/sync.py` (orphan section of `sync status --check`) | `list_orphan_records()` (via `build_boundary_failure_set` in WP03) | **Consistent** with the canonical helper. |
| `src/specify_cli/cli/commands/doctor.py:1172` — `doctor orphan-daemons` | `list_orphan_records()` (direct call at line 1198) | **Consistent**. No edit required (already calls `list_orphan_records()` directly). T018 step 4 verified this; no `doctor.py` modification was needed. |

## Out-of-scope follow-ups (already captured for WP05 closure)

1. **`tasks.py` / `workflow.py` direct enqueues**: these surfaces enqueue
   into the body-upload queue but rely on `sync now` for SaaS egress.
   `sync now` is gated; the *queue write itself* is not. This is the
   intentional WP01 + WP03 design (preflight is the egress gate, not the
   enqueue gate) — see `contracts/sync-boundary-preflight.md`.
   - Decision: **no additional gating needed** for FR-002 / FR-009.
     Adding an enqueue-side gate would force every `agent tasks` /
     `agent workflow` invocation to depend on hosted auth, which would
     break offline CI flows that legitimately produce queue rows for
     later batch upload.
   - Tracking: documented here as the canonical reasoning record;
     no follow-up subtask required.
2. **`finalize-tasks` direct `emit_wp_created` SaaS path** (`mission.py:2360`):
   - **Status**: not gated at the `finalize-tasks` entry. The downstream
     `sync now` is the canonical egress chokepoint and IS gated (WP03).
   - **Why not gated here**: a defensive enqueue-side gate at
     `finalize-tasks` was prototyped during WP04 implementation and
     reverted because it broke 14+ pre-existing tests in
     `tests/specify_cli/cli/commands/agent/test_feature_finalize_bootstrap.py`
     and `tests/integration/test_specify_plan_commit_boundary.py`. The
     failures are not preflight bugs — they reveal that those tests do
     not isolate `Path.home()` (NFR-001 hygiene gap in the existing
     suite), so legacy queue rows in the operator's real `~/.spec-kitty`
     cause spurious refusals. Refer to the live diff: when SaaS sync was
     enabled the preflight reported "3810 legacy rows in scope" inside
     `tmp_path`-rooted fixtures, which proves they're reading from the
     wrong root.
   - **Follow-up**: a separate mission should (a) port those tests to
     the C-008 `Path.home()` patch pattern used by
     `tests/sync/test_sync_boundary_preflight.py`, and then (b) add the
     enqueue-side gate at `finalize-tasks`. Until then, FR-002 / FR-009
     coverage at this surface is provided entirely by the WP03 egress
     gate on `sync now`.

## FR-002 / FR-009 coverage matrix

| Requirement | Surfaces covered | Coverage gate |
|-------------|------------------|----------------|
| FR-002 (refuse loudly on owner mismatch before SaaS emission) | `sync now`, `setup-plan`; `finalize-tasks` covered via the `sync now` egress chokepoint | `run_preflight` returns `ok=False` on any D-3 mismatch and the caller `Exit(2)`s before emission. |
| FR-008 (refuse loudly when hosted auth absent and SaaS sync requested) | `setup-plan` (FR-011 refusal preserved at mission.py:933), `sync now` (auth required by `run_preflight`) | Existing FR-011 refusal fires first at `setup-plan`; FR-008 enforced via `require_auth=True` in `run_preflight`. |
| FR-009 (never write body uploads into legacy queue when authenticated) | `setup-plan` (T020 regression test), `sync now` (WP03 gate) | Boundary preflight refuses if `legacy_rows_for_scope > 0`, so the operator cannot accumulate split-brain queue state across a SaaS-emission cycle. |

## Cross-references

- WP01: `src/specify_cli/sync/preflight.py` — preflight module.
- WP03: `src/specify_cli/cli/commands/sync.py` — `sync now` gate; shared
  `build_boundary_failure_set` helper.
- WP04: this WP — `setup-plan` and `finalize-tasks` gates.
- Tests: `tests/runtime/test_setup_plan_sync_evidence.py` (T019, T020),
  `tests/sync/test_sync_boundary_preflight.py` (WP01).
