---
work_package_id: WP05
title: Run-State Hardening (mission_id key, atomic cursor, pure read)
dependencies: []
requirement_refs:
- C-003
- FR-015
- FR-016
- FR-017
planning_base_branch: missions/coreloop-proto-missions
merge_target_branch: missions/coreloop-proto-missions
branch_strategy: Planning artifacts for this mission were generated on missions/coreloop-proto-missions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into missions/coreloop-proto-missions unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-fsm-write-path-integrity-01M1TZV6
base_commit: 7b90adcfdaf4ab5ef5229fa466bb6091f5769a07
created_at: '2026-09-06T12:14:05.012956+00:00'
subtasks:
- T026
- T027
- T028
- T029
- T030
phase: Wave 0 - Independent (merge FIRST)
agent: claude
history:
- at: '2026-09-06T11:57:59Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/runtime/next/
create_intent:
- tests/runtime/test_run_state_hardening.py
execution_mode: code_change
model: ''
owned_files:
- src/runtime/next/_internal_runtime/engine.py
- src/runtime/next/runtime_bridge_io.py
- src/runtime/next/decision.py
- src/runtime/next/runtime_bridge.py
- tests/runtime/test_bridge_io.py
- tests/runtime/test_bridge_engine.py
- tests/runtime/test_run_state_hardening.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – Run-State Hardening

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent tasks status` or the Activity Log below).
- **You must address all feedback** before your work is complete.
- **Report progress**: update the Activity Log as you address each item.

## Review Feedback

*[Populated by the reviewer via the status event log.]*

---

## Objectives & Success Criteria

This WP closes User Story 5 (spec) and SC-006. It is deliberately sequenced **first** (decision `01M1V8HS2Q04T2VS1DCKHV2E1C`, Q10 rider): its four owned source files are exactly the files Mission B (`dead-port-disposition-01M1TZVN`) must not touch until Mission A's edits merge. Land small, land early.

Done means:

1. Two missions sharing a `mission_slug` but with distinct `mission_id`s resolve **distinct** runs (RED on main at `src/runtime/next/runtime_bridge_io.py:618`, `if mission_slug in index`).
2. A live `feature-runs.json` entry whose `state.json` is missing raises a **structured error**; it never silently starts a fresh run (`:617-627` today).
3. `_write_snapshot` and `_append_event` in `src/runtime/next/_internal_runtime/engine.py` can be killed at any instruction boundary and leave either the old or the complete new file, never a torn one.
4. The progress query in `src/runtime/next/decision.py:369-377` leaves tracked `status.json` byte-identical (it currently calls the *writing* `materialize`).
5. `tests/architectural/test_layer_rules.py` (runtime ledger) stays green; if you remove a ledgered lazy reach, edit the ledger in the same change.

## Context & Constraints

- Spec: `kitty-specs/fsm-write-path-integrity-01M1TZV6/spec.md` (US5, FR-015..017, C-003, SC-006).
- Contract: `kitty-specs/fsm-write-path-integrity-01M1TZV6/contracts/run-state-store.md` (read it fully; it has the code shape).
- Data model: `data-model.md` §8. Plan: `plan.md` (Technical Context, R13). Research: `research.md` §2 (Q9 deferred, Q10 rider).
- Charter: `.kittify/charter/charter.md` — smallest viable diff, close-defect-class-by-construction, tests for every new branch.
- **083 identity model (C-003)**: `mission_id` is the only runtime identity; slug is never a lookup key.
- **Deferred decision Q9** (`01M1V8J842E7CJR6MGZ0MW3DQF`): *you* decide the index migration shape (in-place rekey on first touch vs one-shot migrate) and the legacy key for missions without `mission_id`. Precedent for the legacy key is `f"legacy-{mission_slug}"` used as the transaction lock key at `src/specify_cli/coordination/status_transition.py:1360/:1543/:1606`. Record the decision and rationale in `design-notes/WP05-run-state.md` and reference the decision id.
- Atomic-write precedent: `src/specify_cli/status/reducer.py:273-278` (`tmp_path` + `os.replace`).
- Do NOT touch `runtime_bridge_engine.py` beyond what a call-site rename strictly requires (Mission B has 16 sites there).
- Complexity ceiling 15 (ruff C901); no `# noqa`, no `# type: ignore`.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on missions/coreloop-proto-missions; completed changes must merge back into missions/coreloop-proto-missions.
- **Planning base branch**: missions/coreloop-proto-missions
- **Merge target branch**: missions/coreloop-proto-missions

Execution worktrees are allocated per computed lane from `lanes.json`; enter yours with `spec-kitty implement WP05` (or `spec-kitty agent action implement WP05 --agent claude`). Do not create worktrees by hand.

## Subtasks & Detailed Guidance

### Subtask T026 – Red-first: slug collision resolves the same run

- **Purpose**: Prove the 083 violation before fixing it (ATDD-first, C-009 transitional).
- **Steps**:
  1. Read `src/runtime/next/runtime_bridge_io.py:600-660` (`_load_or_start_run` or the function containing `if mission_slug in index`) and `src/runtime/next/runtime_bridge.py` `_load_feature_runs` / `_build_run_ref`.
  2. In `tests/runtime/test_run_state_hardening.py`, build a `tmp_path` repo with `.kittify/runtime/feature-runs.json` containing one entry keyed by the slug `"dup-slug"` with `mission_id = "01AAA…"` and a valid `run_dir/state.json`.
  3. Call the resolver for mission B (`mission_slug="dup-slug"`, `mission_id="01BBB…"`). Assert the returned `run_id` differs from A's. On main this FAILS (same run returned).
  4. Mark the test `@pytest.mark.xfail(strict=True, reason="SC-006a RED on main; flips in T027")` only for the commit that introduces it; remove the marker in T027.
- **Files**: `tests/runtime/test_run_state_hardening.py` (new).
- **Parallel?**: No (T027 flips it).
- **Notes**: Find the actual resolver signature; the `mission_id` may arrive via `MissionRunRef`/identity plumbing rather than a bare kwarg. Do not invent a new parameter if identity is already available on the call path — trace `runtime_bridge_engine.py` callers first.

### Subtask T027 – Rekey `feature-runs.json` by `mission_id`; decide Q9

- **Purpose**: FR-016 / C-003 — close the collision class 083 already closed elsewhere.
- **Steps**:
  1. Change the lookup to `index.get(mission_id)`; store `mission_slug` inside the entry as a display field; keep `run_id`, `run_dir`, `mission_type`.
  2. Decide Q9. Recommended default: **in-place rekey on first touch** (when a slug-keyed entry is found whose stored `mission_id` matches the caller, rewrite the index under the `mission_id` key and drop the slug key; write atomically via tmp + `os.replace`). Legacy missions with no `mission_id`: key `legacy-<slug>` (the transaction precedent). Whatever you choose, it must be idempotent (run twice ⇒ same file) and lose no entries.
  3. Write `kitty-specs/fsm-write-path-integrity-01M1TZV6/design-notes/WP05-run-state.md`: decision, rationale, alternatives, decision id `01M1V8J842E7CJR6MGZ0MW3DQF`. Then resolve the deferred marker: `spec-kitty agent decision resolve 01M1V8J842E7CJR6MGZ0MW3DQF --mission fsm-write-path-integrity-01M1TZV6 --final-answer "<your choice>"` and remove the corresponding `[NEEDS CLARIFICATION: Q9 …]` line from `plan.md` (keep the diff to that one line).
  4. Tests: distinct runs (T026 flips green); legacy entry without `mission_id` still resolves; migration idempotency.
- **Files**: `src/runtime/next/runtime_bridge_io.py`, `src/runtime/next/runtime_bridge.py` (only if `_load_feature_runs`/`_save` need the atomic write), `tests/runtime/test_run_state_hardening.py`, `tests/runtime/test_bridge_io.py` (update any test asserting slug-keyed shape), design note, `plan.md` (one line).
- **Parallel?**: No.
- **Notes**: Search `tests/runtime/` for fixtures that hand-write `feature-runs.json` keyed by slug and update them; do not leave a mixed-key fixture that only passes because of the migration path.

### Subtask T028 – Loud missing-state error

- **Purpose**: FR-016 second half — a missing `state.json` with a live index entry must not orphan history.
- **Steps**:
  1. Define a structured error (subclass the runtime's existing structured-error base if one exists in `src/runtime/next/`; otherwise `RuntimeError` with `mission_id`, `run_id`, `run_dir` attributes and a recovery hint naming `spec-kitty doctor`).
  2. In the resolver: if the entry exists and `run_dir / STATE_FILE` does not, raise it. Remove the fall-through to "Start a new run".
  3. Test: entry present, `state.json` deleted ⇒ error raised, no new run directory created, index unchanged.
- **Files**: `src/runtime/next/runtime_bridge_io.py`, `tests/runtime/test_run_state_hardening.py`.
- **Parallel?**: No (same function as T027).
- **Notes**: Check whether any CLI path relied on the silent fresh run (grep `tests/runtime` for "start a new run" behaviour). If a test encodes the old behaviour, it is asserting the defect — replace it, and say so in the Activity Log.

### Subtask T029 – Atomic cursor and journal writes

- **Purpose**: FR-015 — no torn `state.json`.
- **Steps**:
  1. `_write_snapshot` (`engine.py:128-130`): write to `run_dir / "state.json.tmp"` (same directory), `flush()` + `os.fsync()`, then `os.replace(tmp, target)`.
  2. `_append_event` (`engine.py:110-119`): keep append semantics but make the write crash-safe — either write the full line with a single `write()` + `flush()` + `fsync` (whole-line append is atomic on POSIX for buffered single writes under `PIPE_BUF`) or route through the store's `append_raw_rows_atomic`-style shape. Document which and why in a two-line comment.
  3. Crash-window test: monkeypatch `os.replace` to raise after the tmp file is written; assert `state.json` still holds the previous content and a `.tmp` exists; then assert a subsequent successful write leaves exactly one `state.json` with new content and no `.tmp`.
- **Files**: `src/runtime/next/_internal_runtime/engine.py`, `tests/runtime/test_run_state_hardening.py`, `tests/runtime/test_bridge_engine.py` (if it asserts the raw write).
- **Parallel?**: Yes (independent of T026–T028).
- **Notes**: R13 — Windows CI runs `tests/runtime/`; keep the tmp file in the same directory.

### Subtask T030 – Pure progress read + ledger check

- **Purpose**: FR-017 — a progress query must never clobber tracked `status.json`.
- **Steps**:
  1. In `decision.py:369-377` replace `from specify_cli.status import materialize` with `materialize_snapshot` and call it (pure). Replace `except Exception: pass` with a logged warning (`logger.warning("weighted progress unavailable: %s", exc)`) — no effect-free handlers (Sonar).
  2. Test: create a mission dir with a committed `status.json`; run the progress-count function; assert file bytes identical.
  3. Run `.venv/bin/pytest tests/architectural/test_layer_rules.py -q`. If `test_runtime_ledger_has_no_stale_entries` reds because you removed the last live edge to a `specify_cli` subpackage, update `_RUNTIME_ALLOWED_SPECIFY_CLI` in the same commit (that file is NOT in your owned_files — record a one-line out-of-map rationale in the Activity Log).
- **Files**: `src/runtime/next/decision.py`, `tests/runtime/test_run_state_hardening.py`.
- **Parallel?**: Yes.
- **Notes**: Do not touch the dead DSL readers `derive_mission_state`/`evaluate_guards` in `decision.py:194-235` unless Mission B's Open Decision 9 has explicitly routed them here (it has not at plan time). Leave them.

## Test Strategy

```bash
uv sync --frozen --all-extras          # once
make test-fast
.venv/bin/pytest tests/runtime/test_bridge_io.py tests/runtime/test_bridge_engine.py tests/runtime/test_run_state_hardening.py tests/runtime/next -q
.venv/bin/pytest tests/architectural/test_layer_rules.py -q
.venv/bin/ruff check src/runtime tests/runtime && .venv/bin/mypy src/runtime/next/runtime_bridge_io.py src/runtime/next/_internal_runtime/engine.py src/runtime/next/decision.py
```

Record commands + pass/fail counts in the PR body (*Tests run*). Apply the baseline-red gotcha (CLAUDE.md) before attributing any red to yourself.

## Risks & Mitigations

- **Windows atomicity** — same-dir tmp + `os.replace`; the reducer precedent already passes Windows CI.
- **Hidden slug-keyed consumers** — grep `feature-runs` across `src/` and `tests/` before rekeying; dashboards or doctor checks may read the index.
- **Mission B interference** — keep the diff surgical in `runtime_bridge_io.py` (only the index function) and do not reorder imports around `NullEmitter` (`:95`).

## Review Guidance

- Verify the RED-first test actually failed on the base (ask for the commit that introduced it with the xfail marker, or re-run it against the merge-base).
- Confirm no silent fall-through remains for missing `state.json`.
- Confirm `status.json` byte-identity test reads the file bytes, not the parsed JSON.
- Confirm the design note resolves Q9 and the plan marker is gone; `spec-kitty agent decision verify --mission fsm-write-path-integrity-01M1TZV6` must be clean.
- Confirm the ledger test is green and any ledger edit is justified.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last). Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-09-06T11:57:59Z – system – Prompt created.
