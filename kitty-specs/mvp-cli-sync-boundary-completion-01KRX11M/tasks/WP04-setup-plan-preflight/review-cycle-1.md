---
affected_files: []
cycle_number: 1
mission_slug: mvp-cli-sync-boundary-completion-01KRX11M
reproduction_command:
reviewed_at: '2026-05-18T12:25:00Z'
reviewer_agent: claude:opus-4.7:reviewer-rita:reviewer
verdict: approved
wp_id: WP04
---

# WP04 review cycle 1 — approved

## Summary

WP04 (setup-plan preflight integration) is implemented faithfully against
FR-002 / FR-008 / FR-009 / NFR-001 / NFR-002. The boundary preflight
`run_preflight(repo_root=..., require_auth=True)` is wired into
`setup_plan()` in the correct slot — after the FR-011 hosted-auth refusal
(which preserves FR-008's auth-absent-first ordering) and before any
side-effecting code (`_enforce_git_preflight`, `_find_feature_directory`,
the lifecycle `emit_artifact_phase` calls, `trigger_feature_dossier_sync_if_enabled`,
or any `emit_wp_created` egress). The new gate is itself guarded by
`SPEC_KITTY_ENABLE_SAAS_SYNC=1` for symmetry with the FR-011 gate directly
above it, which preserves the existing offline / CI behavior unchanged.

## Verification performed

1. **Diff inspection** — `git show 36f1b774` touches only the three owned
   files (`mission.py`, `tests/runtime/test_setup_plan_sync_evidence.py`,
   and the `evidence/saas-producing-paths.md` inventory). A subsequent
   chore commit (`5a698312`) removed the inventory file from the lane
   branch with the stated rationale that it belongs on the planning
   branch. Verified the inventory file IS present on
   `kitty/pr/mvp-sync-boundary-cli-01KRVCQS` (the WP05-owned planning
   tree). No edits to `src/specify_cli/sync/`, `sync.py`, or `doctor.py`.
2. **Call ordering in `setup_plan()`** — at mission.py:951-1024 the order
   is: argument parsing → FR-011 SaaS-sync auth refusal (line 959-985) →
   `locate_project_root()` (pure read) → boundary `run_preflight` (line
   1014-1024) → `_enforce_git_preflight` (line 1026). No side effects
   between the auth refusal and the boundary gate.
3. **FR-008 ordering** — confirmed by reading
   `test_setup_plan_preflight_runs_after_auth_preflight` (lines 676-729):
   stages no credentials + stubs `get_token_manager` to return no session
   + writes a mismatched daemon record. Asserts the FR-011 phrase
   "SaaS sync cannot be guaranteed" appears in output, which proves the
   auth gate fired first (the boundary refusal would emit the "Refusing
   setup-plan" banner instead).
4. **FR-009 regression** — `test_setup_plan_never_writes_legacy_queue`
   (lines 792-895) authenticates, runs `setup_plan`, drives an explicit
   body-upload enqueue through `OfflineBodyUploadQueue()` to prove
   scoped-path resolution, then asserts zero rows in the legacy queue
   across all three tables (`queue`, `sync_events`, `body_upload_queue`)
   and ≥1 row in the scoped `body_upload_queue`. Sanity check at
   line 822-823 also asserts `default_queue_db_path() != legacy_path`.
5. **C-008 cross-platform fixtures** — all 5 new tests call
   `_scope_home_classmethod(monkeypatch, tmp_path)` (defined at lines
   447-452), which patches `pathlib.Path.home` via classmethod AND
   sets HOME / USERPROFILE / LOCALAPPDATA together. Bare
   `monkeypatch.setenv("HOME", ...)` is NOT used in the new tests.
6. **Test execution** — `uv run --with pytest python -m pytest
   tests/runtime/test_setup_plan_sync_evidence.py -q` → 10 passed.
   `uv run --with pytest python -m pytest
   tests/sync/test_sync_status_boundary_check.py
   tests/sync/test_daemon_owner_record.py
   tests/sync/test_sync_boundary_preflight.py
   tests/sync/test_queue_row_level_migration.py -q` → 82 passed.
7. **mypy --strict** — `doctor.py` is clean; `mission.py` shows the 3
   disclosed pre-existing `no-any-return` errors. Verified pre-existing
   by mypy'ing the base-branch file (`kitty/mission-mvp-cli-sync-boundary-completion-01KRX11M`),
   which yields the same 3 errors at lines 396 / 1315 / 2503 (just
   shifted to 396 / 1371 / 2573 after the WP04 insert). No new errors
   introduced by WP04.
8. **Doctor consistency check** — `doctor.py:1198` calls
   `list_orphan_records()` directly (the canonical helper imported from
   `specify_cli.sync.owner`). T018 step 4 is correctly recorded as
   "no edit needed" in the inventory.
9. **Inventory rationale** — the `finalize_tasks` skip is honestly
   documented in the inventory under "Out-of-scope follow-ups" with
   reproduction details (14+ pre-existing tests in
   `test_feature_finalize_bootstrap.py` and
   `test_specify_plan_commit_boundary.py` lack `Path.home()` isolation;
   adding the gate would trigger spurious refusals on stale
   `~/.spec-kitty` state). The architectural contract — "preflight
   protects egress, not enqueue" — is consistent with WP01's design
   (`contracts/sync-boundary-preflight.md`). `emit_wp_created` routes
   through `_publish_event_via_sync_daemon` which queues to the
   daemon → `sync now` chokepoint, which IS gated. The skip is
   defensible.

## Verdict

**APPROVED.** All four subtasks (T017–T020) are complete; all tests
green; mypy delta is zero; C-008 hygiene observed; FR-008 ordering
preserved; FR-009 regression locked. The architectural decision to
not gate `finalize_tasks` at the enqueue surface is justified by the
documented egress-chokepoint contract and by an honest accounting of
the test-isolation gap that would otherwise force a regression.
