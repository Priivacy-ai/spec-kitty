# Tasks — phase-4-cli-blockers-1141-1142-01KS0H5Y

## WP01 — Land #1141 and #1142 in a single CLI-internal patch

**Status**: in_progress
**Dependencies**: none
**Owned files**:
- `src/specify_cli/audit/shape_registry.py`
- `src/specify_cli/status/adapters.py`
- `tests/audit/test_detectors_row_family.py` (or peer)
- `tests/status/test_emit_backward_transition.py` (NEW)

**Subtasks**:
- [x] Read existing `is_mission_lifecycle_row` and grep all callers.
- [x] Broaden the predicate to accept `{Mission, Project, WorkPackage, MissionDossier}`. Update module and function docstrings to enumerate the four accepted aggregate types and reference the contract doc.
- [x] Extend `tests/audit/` with parametrized cases for the new aggregate types AND keep the negative case for an unknown `aggregate_type`.
- [x] Instrument `fire_saas_fanout` in `src/specify_cli/status/adapters.py` with an `INFO`-level entry breadcrumb that includes `wp_id`, `from_lane`, `to_lane`, `force` so silent handler failures surface in operator logs.
- [x] Add `tests/status/test_emit_backward_transition.py`: register a fake SaaS handler, drive the forward chain (`planned → claimed → in_progress → for_review → in_review`), then a forced backward `in_review → planned` with `reason="review_rejected"`, and assert the captured calls.
- [x] Run `uv run pytest tests/audit tests/sync tests/status -q` and fix anything red.
- [x] Run `uv run ruff check src/specify_cli/audit src/specify_cli/status src/specify_cli/sync`.
- [x] Run `uv run mypy --strict src/specify_cli/audit src/specify_cli/status src/specify_cli/sync` and document any pre-existing findings unrelated to this WP in the PR body.
- [x] Push the branch and open the PR via `gh pr create` per the operator brief.
