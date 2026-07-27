---
affected_files: []
cycle_number: 2
mission_slug: mission-lifecycle-dispatch-drg-closeout-01KV0S99
reproduction_command:
reviewed_at: '2026-06-13T17:44:12Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP02
review_artifact_override_at: "2026-06-13T17:51:42Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP02"
review_artifact_override_reason: "cycle1 re-review PASS: dead-symbol ratchet cleared (emit_mission_reopened/emit_follow_up_recorded now live callers in mission_type.py, _CATEGORY_C_WP_IN_FLIGHT_POST_MISSION_LIFECYCLE frozenset removed); dead constant _MERGE_FIELDS_FOR_REOPEN deleted; _safe_load_meta annotation added (type-only, behavior-preserving); 15/15 tests green; ruff exit 0; mypy --strict src/specify_cli/status/ shows 0 errors on views.py (the single-file no-any-return is a follow_imports=skip artifact, not WP02's); PathValidationError is unrelated pre-existing (paths.py untouched by this mission); cross-file coordination noted (test_no_dead_symbols.py + agent/status.py edits outside owned_files are rationale-backed)"
---

# WP02 Review — reviewer-renata — cycle 1

Verdict: **CHANGES REQUESTED** (one blocking gate failure caused by this WP's commit).

The command surface, fail-closed predicate, idempotency, handle resolution, and history
rendering are all correct and well-tested (15/15 new tests pass, status suite 329 pass,
ruff exit 0). One blocking issue: an architectural quality gate now fails *because of*
this WP's commit.

---

## BLOCKING — Issue 1: dead-symbol ratchet fails on this branch (stale allowlist)

`pytest tests/architectural/test_no_dead_symbols.py` **FAILS** on the WP02 lane branch:

```
Stale `_SYMBOL_ALLOWLIST` entries detected. The following symbols now have at least one
caller and must be removed from the allowlist:
  - specify_cli.status.lifecycle_events::emit_mission_reopened
  - specify_cli.status.lifecycle_events::emit_follow_up_recorded
```

Root cause (verified by checking the parent commit `732ce1aa1~1`): WP01 added these two
symbols to `_SYMBOL_ALLOWLIST` (commit `aff36e4fe`) while they had no callers yet. WP02's
`reopen`/`follow-up` commands correctly **wire** `emit_mission_reopened` and
`emit_follow_up_recorded` as live callers. The ratchet then (correctly) demands the now-stale
allowlist entries be removed. This failure did **not** exist before WP02's commit — WP02
introduced it and must close it.

**Fix:** remove the two stale lines at `tests/architectural/test_no_dead_symbols.py:633-634`:

```python
"specify_cli.status.lifecycle_events::emit_mission_reopened",
"specify_cli.status.lifecycle_events::emit_follow_up_recorded",
```

This file is not in WP02's `owned_files`, but the stale entries are a direct artifact of
WP02's wiring (rationale-backed cross-file leeway applies). Note the coordination in your
move-task reason. After removal, re-run `pytest tests/architectural/test_no_dead_symbols.py`
and confirm green (the remaining `PathValidationError` failure is pre-existing — see Note A).

---

## NON-BLOCKING — Issue 2: dead constant `_MERGE_FIELDS_FOR_REOPEN`

`mission_type.py:810` defines `_MERGE_FIELDS_FOR_REOPEN` but it has **zero usages** anywhere
in `src/` (the actual clearing uses `mission_metadata.clear_merge_metadata`, which has its own
`_MERGE_FIELDS`). It is dead code. It also silently drifts from the canonical list: it omits
`merged_push`, which the live `_MERGE_FIELDS` in `mission_metadata.py` includes — so it is both
dead and incorrect. Please delete it (preferred), or if you intended the command to own its own
field list, use it and reconcile it with `mission_metadata._MERGE_FIELDS` (a single source of
truth is better — just delete the duplicate).

While here, please address the unowned-file edit to `src/specify_cli/cli/commands/agent/status.py`
(the `lifecycle` command wiring): it is correct and necessary for T009 (the renderer must reach a
live surface), but it is outside `owned_files`. Keep it — just record the coordination note in your
move-task reason so the merge gate sees it acknowledged.

---

## Verified PASS items (no action needed)

- **Fail-closed predicate — conforms to the contract exactly.** `_branch_resolvable` checks
  `git rev-parse --verify refs/heads/<branch>` (local) then `git ls-remote --heads <remote>`
  per configured remote; predicate (a) meta.json absent/corrupt or no `mission_id`, (b) branch
  in neither local nor any remote. Missing worktree alone is recoverable (branch-only check). On
  unrecoverable: exit 1, structured error + remediation, **no event, no metadata change**. All
  paths covered in `test_mission_reopen.py`.
- **Re-open via the EVENT, no WP-lane cascade.** Emits `MissionReopened` (WP01 helper) and clears
  `merged_*` via `clear_merge_metadata`; actionability is the event, not the clear. WP01's
  classifier (`status/lifecycle.py`) is untouched by WP02's commit.
- **Idempotency** delegated to WP01's dedup `(mission_id, commit|pr)`; no-op exit 0. Tested.
- **Handle resolution** via `resolve_mission`; ambiguous → `MISSION_AMBIGUOUS_SELECTOR`, no silent
  slug guess. Tested.
- **History rendering** `format_post_mission_events` wired into the `lifecycle` command
  (`agent/status.py:687`) — live caller, not dead code.
- **views.py:64 mypy — does NOT require a cast (proven).** Isolated `mypy --strict
  src/specify_cli/status/views.py` reports `views.py:64 no-any-return` in the **untouched**
  `generate_status_view` (`return snapshot.to_dict()`). The canonical SC-6 gate
  `mypy --strict src/specify_cli/status/` does **not** report views.py at all (views.py = 0
  errors); the 17 errors it shows are WP06-owned files (emit/aggregate/progress/__init__) not
  merged into this lane. The line-64 error is purely a `follow_imports=skip` isolation artifact
  (`[[tool.mypy.overrides]] module=["specify_cli.*"] follow_imports="skip"`) — under the real gate
  `to_dict()` resolves to a concrete `dict[str,Any]`. Adding a `cast()` would mask a non-existent
  problem in an untouched function. **No fix required for views.py:64.**

## Note A — pre-existing failure (report, do not fix here)

`specify_cli.validators.paths::PathValidationError` is also flagged by the dead-symbol ratchet,
but `src/specify_cli/validators/paths.py` is untouched by the entire mission and the failure
pre-dates WP02's commit. Per the Pre-existing Failure Reporting Rule it is reported here, not
WP02's responsibility, and must not block this WP once Issue 1 is fixed.
