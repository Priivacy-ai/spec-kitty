---
affected_files: []
cycle_number: 1
mission_slug: test-suite-acceleration-01KV3H59
reproduction_command:
reviewed_at: '2026-06-14T18:16:46Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP04
review_artifact_override_at: "2026-06-14T18:29:03Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP04"
review_artifact_override_reason: "Cycle-2 re-review PASSED (architect-alphonso), overriding cycle-1 rejection (resolved) and base-ref check (work IS committed: tests/conftest.py + tests/test_worker_home_isolation.py present in diff b4724b6b..HEAD). Env-only isolation (HOME/USERPROFILE/XDG via monkeypatch.setenv + pytest_configure; NO Path.home setattr) fixes the ~16 tests/sync regressions WITHOUT weakening them: tests/sync -n0 = 1718 passed/6 skipped/0 failed; diff touches ONLY conftest + regression test (no tests/sync/* or src/ edits). Core guarantee independently verified: real ~/.spec-kitty unchanged under tests/agent -n auto --dist loadfile (1410 passed/23 skipped) — dir mtime+inode, queue.db mtime/size/md5(19f382bf...) byte-identical before/after. Import-time binding (daemon.py:94, queue.py:364) covered: pytest_configure sets HOME before collection; Path.home() resolves HOME via expanduser. Regression test 7/7. ruff clean; mypy errors pre-existing (outside WP04 region), regression test mypy-clean. Anti-pattern checklist all PASS/N-A. WP05/WP07 depend on WP04 — may rebase."
---

# WP04 Review Feedback — cycle 1 (post-approval regression)

## Blocking: the autouse home-isolation fixture breaks ~16 `tests/sync` tests

The `_isolated_worker_home` autouse fixture overrides `Path.home()` even for tests
that set up and assert their OWN home directory. Confirmed failure:

```
tests/sync/test_offline_queue.py::TestOfflineQueueDefaultPath::test_default_path_uses_home_directory
  expected: <test's own tmp home>/.spec-kitty/queue.db
  got:      .../spec-kitty-test-homes/serial/master/.spec-kitty/queue.db   <- WP04's fixture won
```

Other affected files reported: test_routing.py, test_sync_status_boundary_check.py,
test_daemon_owner_record.py, test_sync_action_gate.py (~16 tests total).

## Required fix
The isolation must provide a DEFAULT isolated home for tests that don't manage
their own, but MUST yield precedence to a test that explicitly patches its home
(via `monkeypatch.setattr(Path, "home", ...)` or `monkeypatch.setenv("HOME"/XDG, ...)`
inside the test/its fixtures). Concretely, one of:
  - Make the autouse fixture set the worker home only if the test hasn't already
    overridden it (detect via a sentinel / lower precedence), OR
  - Apply the worker home at a layer that a later in-test monkeypatch cleanly
    overrides for BOTH `Path.home()` AND the env vars `default_queue_db_path()` reads.

The real `~/.spec-kitty`-untouched guarantee MUST still hold (re-run the WP04
regression test + a `tests/agent -n auto` slice), AND `tests/sync` must be green
(run `tests/sync` serially with `-n0` for the real-port daemon tests).

## Acceptance
- `uv run pytest tests/sync -n0 -q` green (no regressions vs base).
- `uv run pytest tests/test_worker_home_isolation.py -q` still green.
- Real `~/.spec-kitty` still provably untouched under `-n auto`.
