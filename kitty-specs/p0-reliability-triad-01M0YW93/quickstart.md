# Quickstart: reproduce (RED) and verify (GREEN)

Run targeted, serially where the test touches real git/ports:
`PWHEADLESS=1 pytest <path> -n0 -q`

## WP01 — #3282
- RED entry point: `tests/specify_cli/upgrade/test_upgrade_provisions_mission_type_activations.py` — add a pointer-charter fixture (config.yaml with `charter:` pointer + charter.yaml lacking `mission_type_activations`), drive the `upgrade` CLI via `_run_upgrade([...])`.
- GREEN assertions: `PackContext.from_config(project).activated_mission_types` non-empty; key landed in `charter.yaml` not `config.yaml`; `mission create` / `setup-plan` succeed.

## WP02 — #3579
- RED entry point: `tests/lanes/test_stale_check.py` — drive `check_lane_staleness()` → `_stale_remediation()` for a planning lane.
- GREEN assertions: remediation string names `spec-kitty agent status materialize`; existing raw-git assertions (lines ~132, ~174) updated in lockstep; no `status.json` driver added (arch guard still green).

## WP03 — #3281
- RED entry points:
  - `tests/specify_cli/cli/commands/agent/test_implement_single_resolution.py` — leftover lane worktree that `exists` but lacks the recorded planning SHA / an approved dep tip must re-enter allocator self-heal (not early-return).
  - `tests/lanes/test_worktree_allocator_atomicity.py` — a conflicting `planning_commit_sha` fails closed AND leaves no registered worktree.
  - `tests/integration/test_wp_integrity_p0_repro.py` — end-to-end retry-then-claim ancestry assertion.
- GREEN: propagation runs on retry; no leftover worktree on conflict; claim refused until ancestry holds; correct-ancestry retry is a no-op resume.

## Full gate before hand-off
- `ruff check .` and `mypy` clean on changed files.
- `pytest tests/architectural/test_no_legacy_terminology.py` (terminology guard) if any prose/doctrine touched.
- Targeted suites for the three owned-file sets green.
