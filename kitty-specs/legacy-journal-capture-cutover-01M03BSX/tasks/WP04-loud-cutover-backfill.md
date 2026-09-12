---
work_package_id: WP04
title: Loud cutover / backfill failures (#3476)
dependencies:
- WP03
- WP05
requirement_refs:
- FR-007
- FR-010
planning_base_branch: fix/legacy-journal-capture-cutover
merge_target_branch: fix/legacy-journal-capture-cutover
branch_strategy: Planning artifacts for this mission were generated on fix/legacy-journal-capture-cutover. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/legacy-journal-capture-cutover unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
- T031
history:
- at: '2026-08-15T00:00:00Z'
  actor: claude
  note: WP authored by tasks phase
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/sync/test_backfill_loud_failure.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/migrate_cmd.py
- src/specify_cli/migration/runtime_state_cutover.py
- src/specify_cli/migration/backfill_runtime_state.py
- tests/sync/test_backfill_loud_failure.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before touching any file, load the implementer profile so identity, boundaries,
and governance scope are in force for this work package:

```
/ad-hoc-profile-load implementer-ivan
```

Do not begin the subtasks until the profile is loaded.

## Objective

Make the `backfill-runtime-state` cutover path **loud** when a write cannot land
(#3476). The backfill command is the intended remediation path for the #3425
silent-zero-capture defect: it seeds legacy runtime state into the event log and
flips `status_phase` to snapshot-authority. Today, on a legacy capture layout the
seed write is refused deep in the stack and the refusal is swallowed — the command
reports success while backfilling nothing, so the fix for #3425 is itself
unobservable.

This WP closes IC-04 / FR-007: a cutover write that **cannot land** must surface
the failure at the command boundary (non-zero exit + an actionable message),
while a **legitimate already-migrated no-op** (nothing to seed, or a re-run that
is byte-stable) must stay quiet and continue to exit `0`. The load-bearing work
is the *distinction* between those two states — not just "exit non-zero more
often."

## Context

WP03 (dependency) lands the layout-resolution + crash-safe auto-cutover work
(IC-02): fresh roots resolve to `project_only` before any LEGACY persist, and
legacy-with-data roots auto-migrate via the canonical engines. This WP04 sits
downstream at the operator-facing `backfill-runtime-state` command boundary.

Confirmed today, the seed write flows:

- `backfill_runtime_state_cmd` (`src/specify_cli/cli/commands/migrate_cmd.py:816`)
  drives `cutover_mission` / `cutover_repo` from
  `specify_cli.migration.runtime_state_cutover` (`:235` / `:371`).
- Each mission's seed events are appended by
  `backfill_runtime_state` → `append_events_atomic_verified`
  (`src/specify_cli/migration/backfill_runtime_state.py:99`).
- On a legacy layout that append is refused by `_require_project_destination`
  (`ProjectLayoutRequiredError`, `src/specify_cli/event_journal/journal.py:117-119`
  per data-model.md), which can be swallowed rather than propagated into
  `CutoverResult.error`.
- The command epilogue (`migrate_cmd.py:882-883`) only exits non-zero when
  `_cutover_failed(...)` (`migrate_cmd.py:965-978`) is True — i.e. a real
  `result.error` or a live not-ok verify. A swallowed "write did not land" leaves
  `error is None` and can leave verify looking ok, so the command exits `0` on a
  genuine failure: **the exact #3476 silent no-op.**

The discriminator that must NOT regress: `_cutover_failed` already treats a
`--dry-run` preview (seeds intentionally unwritten → verify "not ok" pre-seed) as
a healthy would-seed state, and a re-run as byte-stable. Those legitimate no-ops
must remain quiet.

## Surface confirmation

- **Command / function located:** `backfill_runtime_state_cmd`, decorated
  `@app.command(name=_RUNTIME_STATE_CMD)` where `_RUNTIME_STATE_CMD =
  "backfill-runtime-state"`, at **`src/specify_cli/cli/commands/migrate_cmd.py:816`**.
  It is in `migrate_cmd.py` as the frontmatter `owned_files` assumes — no path
  mismatch on the command itself.
- **Command-boundary seam (in-scope, owned):** the loud-vs-quiet decision is
  concentrated in `_cutover_failed` (`migrate_cmd.py:965-978`), `_cutover_detail`
  (`:981-987`), and the epilogue exit (`:882-883`). Surfacing a
  "write-cannot-land" as a genuine failure at the boundary can and should be done
  here, in the owned file.
- **⚠ Scope-boundary flag (root signal may originate deeper):** IC-04's affected
  surfaces are recorded as "backfill-runtime-state path **+ `layout_generation.py`
  cutover write**", and the swallowed-refusal originates below `migrate_cmd.py` —
  in `runtime_state_cutover.py` / `backfill_runtime_state.py`'s append, or the
  `journal.py` guard. `owned_files` intentionally scopes this WP to
  `migrate_cmd.py` + the new test. If, once red-first tests exist, surfacing the
  failure honestly **requires** propagating a "write did not land" signal into
  `CutoverResult.error` from `runtime_state_cutover.py` (a file this WP does not
  own), do **not** silently edit it: raise a scope note and coordinate with WP03
  (IC-02 owns the layout/cutover write). Prefer a fix that reads the existing
  `CutoverResult` signals at the command boundary; only widen scope with an
  explicit hand-off.

## Subtasks

### T018 — Red-first: write-cannot-land surfaces as a failure

Author a failing test in `tests/sync/test_backfill_loud_failure.py` that drives
the backfill/cutover path against a layout where the seed write **cannot land**
(a legacy layout that refuses the journal append via `ProjectLayoutRequiredError`,
`journal.py:117-119`). Invoke the real command entry point
(`backfill_runtime_state_cmd`, `migrate_cmd.py:816`) — via the Typer app / a
`CliRunner`, not by calling internal helpers — against an **isolated temp root**
(see Test Strategy). Assert:

- the command **exits non-zero** (the write could not be persisted), and
- the operator-facing output names the failing mission and the reason (an
  actionable message, not a bare traceback).

This test MUST be red against the pre-fix code (it will currently exit `0` /
report success while capturing nothing). Record in the test docstring the exact
#3476 shape it pins: "seed write refused on a legacy layout is swallowed and the
command reports success." Keep the assertion behavioral (exit code + surfaced
detail), not an assertion over internal enum values, so the fix cannot be gamed
by re-labeling.

### T019 — Red-first: a legitimate no-op is NOT flagged

Author the companion failing/guard test that pins the false-positive boundary: a
**legitimate already-migrated no-op** must stay quiet. Two shapes, both against
isolated temp roots:

1. an **already-migrated** mission (`status_phase` already snapshot-authority /
   nothing left to seed) — a re-run seeds zero, flips nothing, and the command
   exits `0` with no failure surfaced; and
2. a **`--dry-run` preview** over a healthy legacy corpus — verify is "not ok"
   only because seeds are intentionally unwritten (`_cutover_failed` dry-run
   branch, `migrate_cmd.py:976-977`), and the command still exits `0`.

Assert exit `0` **and** the absence of any "failed" / loud-failure signal in the
output for both. This test guards NFR-001's inverse: the loud path must not
warning-storm on healthy roots. It should pass today for the no-op shapes and
must **stay** passing after T020/T021 — it is the regression fence around the
distinction, so any T020 change that reddens a legitimate no-op is a defect.

### T020 — Implement the loud-failure path

Make a cutover/backfill write that cannot land surface as a genuine failure at
the command boundary, turning T018 green. Work within `owned_files`
(`migrate_cmd.py`) first:

- Ensure a swallowed / refused seed write is reflected as a real failure the
  epilogue can see — either because `CutoverResult.error` is now populated
  (preferred; if this requires a deeper-file change, follow the Surface
  confirmation scope-flag and coordinate with WP03), or because `_cutover_failed`
  (`migrate_cmd.py:965-978`) is taught to treat a "seeded but did-not-land" result
  as a failure on a live run.
- Route the surfaced failure through the existing epilogue (`migrate_cmd.py:882-883`)
  so it `raise typer.Exit(1)`s, and through `_cutover_detail` (`:981-987`) so the
  message is actionable (mission slug + reason).

Do not weaken the never-raises contract of the underlying emitter/append (IC-05
owns that seam); surface at the command boundary, do not crash the host. Keep
`ruff` + `mypy` clean; if `_cutover_failed` grows a branch, keep the function's
complexity ≤ 15 by extracting a small predicate rather than nesting.

### T021 — Distinguish no-op vs failure + actionable message

Cement the discriminator so T019 stays green while T018 goes green. Confirm the
three states are cleanly separated at the boundary and each carries the right
signal:

- **legitimate no-op** (already-migrated / byte-stable re-run) → exit `0`, no
  loud failure, no misleading "would seed" noise;
- **dry-run preview** (seeds intentionally unwritten) → exit `0`, reported as a
  preview, never as a failure (preserve the `_cutover_failed` dry-run branch);
- **write-cannot-land** (refused on the current layout) → exit non-zero with an
  actionable message naming the mission and telling the operator what to do
  (e.g. that the root needs the layout cutover / WP03 auto-migration to complete
  first, per data-model.md's state machine).

Hoist any repeated message literal to a module constant (Sonar S1192) if it
appears ≥ 3 times. Add focused assertions in the test for the message content so
the "actionable" requirement is executed, not merely asserted structurally.

### T031 — Deep honest error + consume WP05's capture-failure flag at the boundary (FR-010)

This subtask closes the two post-tasks ownership seams. WP04 now **owns** the
deeper cutover files, so make the honest signal originate where the write actually
fails, and consume WP05's process-level flag at the cutover command boundary:

- **Populate `CutoverResult.error` at the source** in `src/specify_cli/migration/runtime_state_cutover.py` / `backfill_runtime_state.py`: when the runtime-state cutover write cannot land (the `journal.py:117-119 ProjectLayoutRequiredError` / refusal path), record the real reason on the result object instead of returning a bland success. `cutover_mission` today catches only `MigrationOrderingError` — widen it to carry the layout-refusal reason so `_cutover_failed`/`_cutover_detail` in `migrate_cmd.py` can surface it (T018/T020 consume this).
- **Consume WP05's capture-failure flag at the cutover epilogue** (`migrate_cmd.py`, the epilogue near `:882-883`): after the command body runs, query WP05's public capture-failure summary helper (from `emitter.py`); if any genuinely-unrecoverable capture failure was recorded, surface it at the boundary (report + non-zero where appropriate) — **non-fatal to the command's own success semantics**. This is the concrete command-boundary consumer for FR-010/NFR-001 (the mechanism is WP05; the demonstrated consumer is here). Because WP04 now `depends_on` WP05, the helper exists when this runs.
- **Isolation**: red-first coverage in `tests/sync/test_backfill_loud_failure.py` uses temp roots (`SPEC_KITTY_HOME`+`HOME`), never the live `~/.spec-kitty`.

Validation: (a) a cutover write that cannot land yields a populated `CutoverResult.error` and a non-zero, actionable boundary exit; (b) a run with a recorded unrecoverable capture failure surfaces it at the epilogue without crashing the command; (c) a clean run stays silent.

## Branch Strategy

- **Base branch:** `fix/legacy-journal-capture-cutover`.
- **Merge target:** `fix/legacy-journal-capture-cutover` (this mission's integration
  branch — NOT `main`; the operator lands the mission branch to origin/main via PR
  later).
- **Lane execution:** `branch_strategy: lane` — per-lane worktree, resolved by the
  runtime resolver. Do not hand-construct the worktree path.
- **Prepare the workspace with the canonical command** (the only supported way):

  ```
  spec-kitty agent action implement WP04 --agent <name>
  ```

- **Dependency gate:** WP04 depends on **WP03**. WP03 must be `approved` or `done`
  before WP04 can be claimed/implemented (dependency-readiness gating). Do not
  start until `spec-kitty agent tasks status` shows WP03 satisfied.

## Test Strategy

- **Red-first (C-011):** T018 and the write-cannot-land shape of T019 must be
  authored and observed **red** before any `migrate_cmd.py` change (T020/T021).
  Capture the red output in the WP notes.
- **Isolation is mandatory (plan Testing note / risk MINOR-8):** every test runs
  against an **isolated temp root** via `SPEC_KITTY_HOME` / `HOME` fixtures. This
  dev box's real `~/.spec-kitty` is a live machine-global legacy root — a test or
  step that runs cutover against it is a defect. Seed legacy layout state and
  refusal conditions inside the temp root only.
- **Drive the real entry point:** invoke `backfill-runtime-state` through the
  Typer app (`CliRunner`) so exit code and surfaced output are exercised as an
  operator sees them — not by calling `_cutover_failed` in isolation (that may be
  a helper unit test in addition, but the behavioral pin is the command boundary).
- **New test file:** `tests/sync/test_backfill_loud_failure.py` (create-intent).
- **Targeted runs only** (full suite is ~1h and off-limits in-session):
  `PWHEADLESS=1 .venv/bin/python -m pytest tests/sync/test_backfill_loud_failure.py -q`.

## Definition of Done

- `backfill-runtime-state` **exits non-zero with an actionable message** when a
  cutover/backfill write cannot land on the current layout (FR-007 / #3476).
- A **legitimate already-migrated no-op** and a **`--dry-run` preview** remain
  **quiet and exit `0`** — no false-positive loud failure (NFR-001 inverse).
- T018 (write-cannot-land) and T019 (no-op-not-flagged) both green; both authored
  red-first where applicable.
- All tests run against isolated temp roots; the real `~/.spec-kitty` is never
  touched.
- `ruff check .` and `mypy` clean on the diff — zero new issues, no new
  `# noqa` / `# type: ignore`; `_cutover_failed` (and any extracted helper) stays
  ≤ 15 complexity.
- If honest surfacing required a change outside `owned_files`, that scope widening
  was raised as an explicit note and coordinated with WP03 — not slipped in.

## Risks & Reviewer Guidance

- **Primary risk — false positive on a legitimate no-op.** The single most likely
  regression is making the command loud on a healthy already-migrated / byte-stable
  re-run, or on a `--dry-run` preview. Reviewer: run T019 and confirm both no-op
  shapes still exit `0` with no "failed" signal; confirm the `_cutover_failed`
  dry-run branch (`migrate_cmd.py:976-977`) is untouched or preserved in intent.
- **Scope creep into a non-owned file.** If the fix reached into
  `runtime_state_cutover.py` / `backfill_runtime_state.py` / `journal.py` /
  `layout_generation.py`, verify it was a coordinated hand-off with WP03 and
  flagged per Surface confirmation — not a silent edit of a file this WP does not
  own.
- **Never-raises contract (IC-05).** Confirm the loud path surfaces at the command
  boundary (epilogue exit + message) and does **not** make the underlying emitter/
  append start raising into ~30 callers; that seam belongs to IC-05, not WP04.
- **Actionable message.** Confirm the surfaced text names the mission and tells the
  operator the recovery (layout cutover must complete first), rather than dumping a
  raw `ProjectLayoutRequiredError` traceback.
