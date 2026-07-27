# Research: Merge Abort, Review, and Status Hardening Sprint

**Mission ID**: 01KQFF35BPH2H8971KR0TEY8ST
**Date**: 2026-04-30

All unknowns resolved by codebase archaeology. No external research required.

---

## Finding 1 — Lock file location and constant (#903)

**Decision**: Use the existing `_GLOBAL_MERGE_LOCK_ID = "__global_merge__"` constant
in `src/specify_cli/cli/commands/merge.py` to derive the lock path. Do not hardcode
the string elsewhere.

**Rationale**: The constant already exists at line ~L130 of merge.py. Reusing it
means the path stays consistent if it ever changes.

**Location confirmed**: `src/specify_cli/cli/commands/merge.py` contains both
`_GLOBAL_MERGE_LOCK_ID = "__global_merge__"` and the `--abort` handler.

---

## Finding 2 — move_task function signature (#904)

**Decision**: Extend `move_task()` at `src/specify_cli/cli/commands/agent/tasks.py:1110`
with a `--skip-review-artifact-check` option (bool, default False). Add the verdict
check before the status transition emit.

**Rationale**: The function already handles `--force` and other guard bypasses using
Typer options. This follows the established pattern.

**Review-cycle artifact path pattern**:
`kitty-specs/<slug>/tasks/<WP-dir>/review-cycle-N.md`
where N is an integer suffix. Highest N is the most recent cycle.

---

## Finding 3 — BLE001 suppressions audit (#907)

**Decision**: Add inline justification comments to all bare `# noqa: BLE001` in
`src/specify_cli/auth/` and `src/specify_cli/cli/commands/`. Auth suppressions
already have justifications. CLI command suppressions require annotation.

**Auth directory** — already justified (no changes needed):
- `src/specify_cli/auth/token_manager.py:112` — "never crash on stale credentials" ✓
- `src/specify_cli/auth/token_manager.py:126` — "logout must not raise on storage quirks" ✓
- `src/specify_cli/auth/secure_storage/file_fallback.py:170` — "cryptography raises InvalidTag / others" ✓

**CLI commands directory** — require justification comments (partial list of patterns found):
- `cli/helpers.py` — defensive guards around optional metadata reads
- `cli/commands/charter.py` — multiple interview/synthesis infrastructure boundaries
- `cli/commands/materialize.py`, `tracker.py`, `mission_type.py`, `merge.py`,
  `charter_bundle.py` — various fail-open / infrastructure-boundary patterns

**Alternatives considered**: Option B (custom ruff rule) — rejected as over-engineering
for this scope. Option A (per-file-ignores) — not needed since suppressions already
exist; the work is adding justification text to existing comments.

---

## Finding 4 — Lane guard error location (#905)

**Decision**: Modify line ~1003 of `src/specify_cli/cli/commands/agent/tasks.py`
where `"Lane branch contains forbidden planning changes under kitty-specs/!"` is
constructed.

**Rationale**: The function already has access to the WP context. `planning_base_branch`
can be read from `meta.json` via the mission resolver already used in that module.

**Fallback strategy**: If `meta.json` is missing or the field is absent (legacy
mission), fall back to the original message with a parenthetical note.

---

## Finding 5 — Status event log shape for stall detection (#909)

**Decision**: Use `at` field from each `StatusEvent` in `status.events.jsonl`.
Compare the most recent event for each `in_review` WP against `datetime.now(UTC)`.

**Rationale**: The event log is append-only and authoritative. Computing time-since-
last-event is purely read-only arithmetic — no new state needed.

**Config key**: `review.stall_threshold_minutes` — not currently in config schema.
Will be added as an optional integer key. Default: 30.

**`spec-kitty next` location**: `src/specify_cli/cli/commands/next_cmd.py`
(imports and calls `show_kanban_status`-related logic via the agent_utils module).

---

## Finding 6 — New review command registration pattern (#908)

**Decision**: Create `src/specify_cli/cli/commands/review.py` with a single
`review_mission()` function registered as `app.command(name="review")` in
`src/specify_cli/cli/commands/__init__.py`.

**Rationale**: All single-function commands (accept, implement, research, merge)
follow this pattern exactly.

**baseline_merge_commit field**: Present in `meta.json` for missions created/merged
after the mission identity migration. Missions without it skip the dead-code step
with a warning.

**Dead-code scan approach**: Parse `git diff {baseline}..HEAD` added lines for
`def ` and `class ` patterns, then grep `src/` excluding `tests/`. This is a
heuristic (not perfect AST analysis) but sufficient for the MVP.

---

## Finding 7 — WP review template location (#906)

**Decision**: Edit `src/specify_cli/missions/software-dev/command-templates/review.md`
only. Do not touch any files in `.claude/commands/`, `.amazonq/prompts/`, or any
other agent directory.

**Rationale**: CLAUDE.md is explicit: agent directories are generated copies.
The deletion-test checklist item will propagate to all agents on next `spec-kitty upgrade`.
