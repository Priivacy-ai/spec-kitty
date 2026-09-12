---
work_package_id: WP01
title: Serialize the Out-of-Pipeline Writers
dependencies: []
requirement_refs:
- C-002
- C-003
- C-009
- C-010
- FR-001
- FR-002
- FR-003
- FR-004
- NFR-001
- NFR-003
planning_base_branch: missions/coreloop-proto-missions
merge_target_branch: missions/coreloop-proto-missions
branch_strategy: Planning artifacts for this mission were generated on missions/coreloop-proto-missions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into missions/coreloop-proto-missions unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-fsm-write-path-integrity-01M1TZV6
base_commit: 7b90adcfdaf4ab5ef5229fa466bb6091f5769a07
created_at: '2026-09-06T12:14:20.882265+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
phase: Wave 0 - Writer serialization
agent: claude
history:
- at: '2026-09-06T11:57:59Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/retrospective/
create_intent:
- tests/specify_cli/migration/test_backfill_writer_locking.py
- tests/status/test_locking_key.py
- tests/status/test_writer_serialization.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/retrospective/lifecycle_events.py
- src/specify_cli/retrospective/events.py
- src/specify_cli/migration/backfill_runtime_state.py
- src/specify_cli/migration/verdict_provenance_backfill.py
- src/specify_cli/status/locking.py
- src/specify_cli/post_merge/retrospective_terminus.py
- src/specify_cli/orchestrator_api/commands.py
- tests/specify_cli/retrospective/**
- tests/specify_cli/migration/test_backfill_writer_locking.py
- tests/status/test_locking_key.py
- tests/status/test_writer_serialization.py
- tests/status/test_journal_lock_unification.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Serialize the Out-of-Pipeline Writers

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log (`spec-kitty agent tasks status --feature fsm-write-path-integrity-01M1TZV6`). Address every item before completion and log what changed.

## Review Feedback

*[Populated by the reviewer via the status event log.]*

---

## Objectives & Success Criteria

User Story 1 (P1). After this WP:

- **SC-001**: a raw retrospective append that lands inside `BookkeepingTransaction._rollback`'s truncate window (`src/specify_cli/coordination/transaction.py:944`, `fh.truncate(self._pre_emit_size)`) **survives**. RED on main.
- **SC-006a**: two missions with colliding slugs but distinct `feature_dir.name` acquire distinct lock files; a bare/legacy slug dir serializes against that mission's ordinary writers. RED on main (`src/specify_cli/status/locking.py:57-60` keys on `mission_slug`).
- **SC-008 (partial)**: a lock-held assertion passes for writer families ①–⑦ (`data-model.md` §2). The batch door's assertion is added here as `xfail(strict=True)` and flipped by WP02.
- **NFR-003**: the merge-path retrospective L1 take and any L1 take reachable from the verdict-save queue use a finite timeout and raise a structured error naming the holder.
- **FR-001**: the stale "only 2 of 6" comment at `src/specify_cli/orchestrator_api/commands.py:3568-3570` is re-labelled as historical; the seven-family census is documented in `design-notes/WP01-lock-rules.md` with the three lock rules.

## Context & Constraints

- Spec `spec.md` US1, FR-001..004, NFR-001, NFR-003, C-002, C-003, C-009, C-010. Contract `contracts/emit-pipeline.md` §3 (lock rules) and §4 (hardening pattern). Data model §2 (writer census) and §3 (lock).
- Research `research.md` §2: Q1 = batch lock is **WP02's** (do not touch `status/emit.py`); Q2 = finite **default** timeout is a follow-up (only the two outage-shaped sites get finite timeouts); Q3 = harden **both** retrospective writers, live one first.
- **Reference pattern**: `src/specify_cli/status/lifecycle_events.py:234-254` (`_lifecycle_write_lock`) — mission-keyed `feature_status_lock`, `nullcontext()` only when `repo_root` is `None`, then the crash-safe `append_raw_rows_atomic`.
- **Lock root**: `resolve_status_lock_root(feature_dir, repo_root=None)` in `src/specify_cli/workspace/root_resolver.py:36` (not in `status/`).
- **Lock API**: `feature_status_lock(repo_root, mission_slug, *, timeout=-1)` at `src/specify_cli/status/locking.py:114`; re-entrant; raises `FeatureStatusLockTimeoutError`.
- **Store primitives** (`src/specify_cli/status/store.py`): `append_raw_rows_atomic(path, rows)` `:358`, `append_events_atomic_verified` `:530`, `append_annotations_atomic_verified` `:462`.
- **NFR-001 / C-002**: no NEW code holds L1 across a git subprocess. None of the four sites spawns git. The standing `BookkeepingTransaction` violation (`transaction.py:290`) is NOT yours — leave it, it is on the risk register (R9).
- **C-003**: never key a lock on slug after T006.
- WP03 will later move the raw `append_event*` names into `status/_unsafe.py`; import them from `specify_cli.status.store` directly for now so the repoint in WP03 is mechanical.
- Complexity ceiling 15; no suppressions; tests for every new helper.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on missions/coreloop-proto-missions; completed changes must merge back into missions/coreloop-proto-missions.
- **Planning base branch**: missions/coreloop-proto-missions
- **Merge target branch**: missions/coreloop-proto-missions

Execution worktrees are allocated per computed lane from `lanes.json`; enter yours with `spec-kitty implement WP01`.

## Subtasks & Detailed Guidance

### Subtask T001 – Red-first: the rollback-truncate race

- **Purpose**: The only reliably reproducible lost write (dossier R10). Do NOT write "two concurrent appends" — POSIX `O_APPEND` whole-line buffered writes land atomically and the test will not go red.
- **Steps**:
  1. Read `transaction.py:900-975` (`_rollback`) and `:280-300` (acquire). Note `_pre_emit_size` is captured at first `append_event`.
  2. In `tests/status/test_writer_serialization.py`, build a flat mission dir (`tmp_path` git repo with `kitty-specs/<slug>/status.events.jsonl` seeded with one event). Open a `BookkeepingTransaction` via its public `acquire` context (see `tests/specify_cli/coordination/test_status_transition.py` fixtures for a working recipe), append one event, then — **before** the commit — call `_append_retro_lifecycle_event(feature_dir, {...})` from `src/specify_cli/retrospective/lifecycle_events.py` on the same `feature_dir`. Force the commit to fail (monkeypatch the commit seam the fixtures already use) so `_rollback` runs.
  3. Assert the retro event's `event_id` is still present in the file after the rollback. On main it is truncated away.
  4. Mark `@pytest.mark.xfail(strict=True, reason="SC-001 RED on main; flips in T002")`; remove in T002. Also assert (positive control) the transaction's own event was removed.
- **Files**: `tests/status/test_writer_serialization.py` (new).
- **Parallel?**: No.
- **Notes**: The retro append runs in the same thread; because L1 is re-entrant within a thread, after T002 the append will block only if performed from another process/thread. To keep the test deterministic, run the retro append in a `threading.Thread` and give the lock a short `timeout` so the post-fix behaviour is "the append waits for the rollback, then lands after the truncate" — either ordering is a survival. Document the chosen ordering in the test docstring.

### Subtask T002 – Harden `retrospective/lifecycle_events.py` (live post-merge path)

- **Purpose**: Family ⑤ is the highest-priority unlocked writer (callers: `post_merge/retrospective_terminus.py` via `coordination/teardown.py:87`, and `runtime/next/runtime_bridge_retrospective.py`).
- **Steps**:
  1. `_append_retro_lifecycle_event(feature_dir, event_dict)` (`:250-256`): replace the raw `open("a")` with `append_raw_rows_atomic(events_path, [event_dict])`, wrapped in `feature_status_lock(resolve_status_lock_root(feature_dir), feature_dir.name, timeout=...)`.
  2. `_next_lamport(feature_dir)` (`:265`) is a TOCTOU read: the three public appenders at `:363`, `:432`, `:500` call `_next_lamport` then `_append_retro_lifecycle_event`. Restructure so the read AND the append happen under one acquisition (e.g., an internal `_locked_append(feature_dir, build_event: Callable[[int], dict])` that acquires, reads lamport, builds, appends). Keep the three public signatures unchanged except for an added keyword `lock_timeout: float = -1` (used by T007).
  3. `nullcontext()` degrade: only when `resolve_status_lock_root` cannot find a git root; add a one-line comment explaining this is a conscious choice (spec edge case).
  4. Unit tests in `tests/specify_cli/retrospective/test_lifecycle_events_locking.py` (new): lock is held during append (patch `feature_status_lock` with a recording wrapper), lamport increments monotonically under two threads, atomic primitive is used (no raw `open` — assert via `unittest.mock` on `Path.open` or by reading the AST of the module in the test).
- **Files**: `src/specify_cli/retrospective/lifecycle_events.py`, `tests/specify_cli/retrospective/test_lifecycle_events_locking.py`.
- **Parallel?**: No (establishes the helper shape T003–T005 copy).
- **Notes**: Keep the module's "best-effort, never-raise" contract for the no-repo case; but a `FeatureStatusLockTimeoutError` MUST propagate (it is a structured outage signal, not a best-effort failure).

### Subtask T003 – Harden `retrospective/events.py:213` (superseded path)

- **Purpose**: Family ④; Q3 says harden both. `run_terminus` is superseded ("do not add new callers", `post_merge/retrospective_terminus.py:79-81`) but still present, so the WP03 gate would otherwise have to allowlist a raw writer.
- **Steps**: same pattern as T002 for the append at `:209-214`; keep the existing `materialize` call **outside** the lock (it is a read-then-write of `status.json`, and `materialize` already takes its own lock — check `reducer.materialize` before nesting; re-entrancy makes nesting safe but keep the critical section small). Preserve the "do not add new callers" note. Test: lock-held + atomic primitive.
- **Files**: `src/specify_cli/retrospective/events.py`, `tests/specify_cli/retrospective/test_events_locking.py` (new).
- **Parallel?**: Yes (after T002).

### Subtask T004 – Harden `migration/verdict_provenance_backfill.py:419`

- **Purpose**: Family ⑥ — already atomic (`append_events_atomic_verified`), not locked.
- **Steps**: wrap the `if events: append_events_atomic_verified(feature_dir, events)` in the lock (root via `resolve_status_lock_root(feature_dir)`). The discovery loop above it reads review artifacts, not the event log, so it may stay outside the lock; but `event_sourced_review_result(feature_dir, wp_id).slot_present` IS an event-log read → move the whole loop inside the lock to close the TOCTOU (cheap; the backfill is a one-shot migration). Test in `tests/specify_cli/migration/test_backfill_writer_locking.py`.
- **Files**: `src/specify_cli/migration/verdict_provenance_backfill.py`, `tests/specify_cli/migration/test_backfill_writer_locking.py` (new; shared with T005).
- **Parallel?**: Yes.

### Subtask T005 – Harden `migration/backfill_runtime_state.py` (one lock, one window)

- **Purpose**: Family ⑦ — the `:1497` idempotency read (`read_event_stream`) and the two appends (`:1533` transitions, `:1535` annotations) form a two-append window with a TOCTOU read.
- **Steps**:
  1. Acquire the lock immediately before `stream = read_event_stream(feature_dir)` and hold it through both appends (the `dry_run` early return inside the lock is fine).
  2. Prefer a single combined append if the store offers one (`append_event_stream_atomic_verified` `:490` takes transitions + annotations) — check its signature; if it fits, replace the two calls with one so the pair lands in one atomic write.
  3. Tests: (a) lock held across read + append; (b) run the backfill twice ⇒ second run reports `skip` (idempotent); (c) a concurrent writer that appends between "read" and "append" cannot interleave (simulate with a thread holding the lock; assert the backfill waits).
- **Files**: `src/specify_cli/migration/backfill_runtime_state.py`, `tests/specify_cli/migration/test_backfill_writer_locking.py`.
- **Parallel?**: Yes.
- **Notes**: This function is long; extract the locked section into a helper to stay under C901=15.

### Subtask T006 – Lock key → `feature_dir.name`

- **Purpose**: FR-004 / C-003 / D4. Slug collision ⇒ over-serialization; bare legacy slug ⇒ serializes against nobody (`status/migrate_lifecycle_envelope.py:228-243` documents the trap).
- **Steps**:
  1. `feature_status_lock_path(repo_root, mission_slug)` (`locking.py:57`): rename the second parameter to `lock_key` in the signature docstring and make every caller pass `feature_dir.name`. Find callers: `grep -rn "feature_status_lock(" src --include='*.py'`. Callers that only have `mission_slug` (e.g. `status/lifecycle_events.py:_lifecycle_write_lock`, `coordination/transaction.py:290`) must derive `feature_dir.name` — for the transaction, `feature_dir` is known at acquire time; for the lifecycle appender, it has the log path.
  2. **Scope discipline**: `transaction.py` and `status/emit.py` are NOT in your owned files. If changing their `feature_status_lock(...)` argument is unavoidable (it is: both key on slug today), make exactly that one-line argument change in each, record an out-of-map rationale line in the Activity Log ("FR-004 uniform lock key; argument only"), and coordinate with WP02 (which owns `emit.py`) by keeping the hunk minimal and non-overlapping with the shell refactor (the lock call site is at `emit.py:634` — WP02 will preserve your argument).
  3. Tests in `tests/status/test_locking_key.py` (new): two missions `kitty-specs/foo-01AAAAAA/` and `kitty-specs/foo-01BBBBBB/` with `mission_slug="foo"` ⇒ distinct lock paths; a bare legacy dir `kitty-specs/017-foo/` ⇒ its retro writer and its emit path resolve the same lock path. Update `tests/status/test_journal_lock_unification.py` if it asserts the slug-keyed filename.
- **Files**: `src/specify_cli/status/locking.py`, `tests/status/test_locking_key.py`, `tests/status/test_journal_lock_unification.py`, one-line touches in `coordination/transaction.py` and `status/emit.py` (out-of-map, rationale logged).
- **Parallel?**: No.

### Subtask T007 – Finite timeouts on the outage-shaped takes (FR-003 a/b, NFR-003)

- **Purpose**: A new L1 take under the L5 merge-global sentinel with the default `-1` converts a slow status commit into a repo-wide merge refusal (R7).
- **Steps**:
  1. Merge path: `post_merge/retrospective_terminus.py` (called from `coordination/teardown.py:87` during `spec-kitty merge`) calls the lifecycle appenders — pass `lock_timeout=<finite>` there. Pick the value by reusing the existing bounded pattern `_in_queue_status_lock_timeout(main_repo_root)` in `src/specify_cli/review/cycle.py:804` (import it or lift it into `status/locking.py` as `bounded_status_lock_timeout(repo_root)` — the latter is cleaner; if you lift it, leave a re-export in `review/cycle.py` and note the out-of-map touch).
  2. Ensure `FeatureStatusLockTimeoutError`'s message names the lock path and, where the lock file records a holder PID, the holder — read `locking.py:114-160` to see what is available; if nothing records the holder, add the acquiring PID to the lock file contents (write on acquire, best-effort) so the error can name it.
  3. Rule (a): grep for L1 takes reachable from `tasks_verdict_persistence.py` / `review/cycle.py` scopes — the existing ones are already bounded; assert nothing you added in T002–T005 is reachable from those scopes (they are not; state that in the design note).
  4. Tests: contended lock (a thread holds it) ⇒ appender raises the structured timeout error within the bound; the merge path surfaces it as a structured failure of the retrospective step, not as a global merge refusal (find the merge test that exercises `_teardown_coord_worktree` in `tests/specify_cli/merge/` and add a case).
- **Files**: `src/specify_cli/post_merge/retrospective_terminus.py`, `src/specify_cli/status/locking.py`, `tests/status/test_locking_key.py`, a case in `tests/specify_cli/merge/` (out-of-map, rationale logged) or in `tests/specify_cli/retrospective/`.
- **Parallel?**: No.

### Subtask T008 – Lock-held assertions, census comment, lock-rules note

- **Purpose**: SC-008 evidence + FR-001 governance.
- **Steps**:
  1. `tests/status/test_writer_serialization.py`: parametrize over the seven families; each case exercises the family's public entry point with `feature_status_lock` wrapped by a recorder that asserts the lock for `feature_dir.name` is held at the moment the store primitive is called. For families ①②③ (already locked) this is a pin. Add the batch door (`emit_status_transition_batch`) as `xfail(strict=True, reason="FR-018 lands in WP02")`.
  2. `orchestrator_api/commands.py:3568-3570`: edit the comment to read as history ("As of <date> only 2 of 6 writers were locked; WP01 of fsm-write-path-integrity serialized all seven families — see design-notes/WP01-lock-rules.md"). Comment-only change.
  3. Write `kitty-specs/fsm-write-path-integrity-01M1TZV6/design-notes/WP01-lock-rules.md`: the census table (data-model §2 with final line numbers), the three lock rules (a)(b)(c) with the code sites that encode them, the hierarchy diagram (text), the per-site `nullcontext()` decisions, and the R9 note.
  4. C-009: convert T001's repro into a permanent functional test (it is a genuine regression pin for the rollback window) — drop the xfail, keep the test, rename it to describe behaviour not defect.
- **Files**: `tests/status/test_writer_serialization.py`, `src/specify_cli/orchestrator_api/commands.py` (comment), design note.
- **Parallel?**: No.

## Test Strategy

```bash
make test-fast
.venv/bin/pytest tests/status tests/specify_cli/status tests/specify_cli/coordination tests/specify_cli/retrospective tests/specify_cli/migration tests/specify_cli/merge -q
.venv/bin/pytest tests/architectural/test_status_module_boundary.py tests/architectural/test_no_legacy_terminology.py -q
.venv/bin/ruff check src tests && .venv/bin/mypy src/specify_cli/retrospective src/specify_cli/migration/backfill_runtime_state.py src/specify_cli/migration/verdict_provenance_backfill.py src/specify_cli/status/locking.py
```

Record commands + counts in the PR body. Baseline-red gotcha applies.

## Risks & Mitigations

- **Deadlock by nesting**: L1 is re-entrant per thread; none of the four sites is under an enclosing lock. If a caller of the lifecycle appender already holds L1 (e.g. inside a transaction), re-entrancy absorbs it — add a test that nests one appender inside `BookkeepingTransaction.acquire` to prove it.
- **`nullcontext()` accidental default**: assert in tests that a repo-backed `feature_dir` never takes the null path.
- **Shared-file friction with WP02**: keep `emit.py`/`transaction.py` touches to the single lock-argument line.

## Review Guidance

- Re-run T001 on the merge-base to confirm it was RED.
- Every raw `open(..., "a")` on `status.events.jsonl` in the four modules is gone (grep).
- Lock key: grep `feature_status_lock(` — every call passes `feature_dir.name` (or the transaction's known dir name), never a slug.
- Timeout: the merge-path call passes a finite value; the error names the lock path/holder.
- Design note present; census comment re-labelled; no `# noqa` added.

## Activity Log

> **CRITICAL**: chronological order, oldest first. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-09-06T11:57:59Z – system – Prompt created.
- 2026-09-06T13:06:25Z – claude – shell_pid=53806 – 2026-09-06T12:20:00Z – claude-fable-5-1 – Read prompt, contracts/emit-pipeline.md §3-5, data-model.md §2-3, research.md §2, spec US1/FR-001..004/NFR-001/NFR-003, charter, CLAUDE.md; read every code anchor and grepped all callers of feature_status_lock( / the retro+backfill entry points before editing.
- 2026-09-06T13:06:26Z – claude – shell_pid=53806 – 2026-09-06T12:31:00Z – claude-fable-5-1 – T001 RED: `.venv/bin/pytest tests/status/test_writer_serialization.py -q -p no:cacheprovider --runxfail` -> 1 failed: `AssertionError: SC-001: retro append was truncated away; assert '01RETROEVENT00000000000001' in ['01M1VB73VZYPT5V1XT6TBXC1DV']` (positive control held: doomed txn event absent, seed present). Repro shape: BookkeepingTransaction append, racing `_append_retro_lifecycle_event` in a thread, `safe_commit` monkeypatched to raise -> `_rollback` truncate.
- 2026-09-06T13:06:28Z – claude – shell_pid=53806 – 2026-09-06T12:38:00Z – claude-fable-5-1 – T002: retrospective/lifecycle_events.py -> `retro_status_lock` (L1 keyed on feature_dir.name via resolve_status_lock_root, no nullcontext), `_append_retro_lifecycle_event` via `append_raw_rows_atomic` under the lock, `_locked_append` (Lamport read + build + append under ONE acquisition), `lock_timeout` keyword on the three emitters, `bounded_lock_timeout` ContextVar scope. status imports made function-local (status.models -> retrospective.schema -> package __init__ -> this module cycle). T001 flipped to strict XPASS, xfail removed, test renamed to behaviour (C-009). Facade export `append_raw_rows_atomic` added to status/__init__.py (boundary gate forbids deep store imports).
- 2026-09-06T13:06:29Z – claude – shell_pid=53806 – 2026-09-06T12:44:00Z – claude-fable-5-1 – T003/T004/T005: retrospective/events.py append under `retro_status_lock` + atomic primitive, materialize outside the section; verdict_provenance_backfill.py loop+append under one lock (`_collect_backfill_events`); backfill_runtime_state.py one lock across anchors/idempotency read/append (`_backfill_runtime_state_locked`) and ONE `append_event_stream_atomic_verified` for the transition+annotation pair.
- 2026-09-06T13:06:31Z – claude – shell_pid=53806 – 2026-09-06T12:52:00Z – claude-fable-5-1 – Finding: the lock's non-git degrade minted `<root>/.git/` (acquire_or_raise mkdir) in bare trees, turning tmp trees into fake canonical roots (2 migration tests red). Fixed in status/locking.py `_git_common_dir`: keep `.git` only when it already is a directory, else `.kittify`. Pinned in tests/git_ops (refined existing pin + new case) and test_backfill_writer_locking.py.
- 2026-09-06T13:06:32Z – claude – shell_pid=53806 – 2026-09-06T12:58:00Z – claude-fable-5-1 – T006: `feature_status_lock_path(repo_root, lock_key)`; callers -> feature_dir.name. Out-of-map argument-only hunks (FR-004 uniform lock key): status/emit.py:634 (`canonical_feature_dir.name`) and :1013 (`feature_dir.name`) [WP02 file], coordination/transaction.py:290 (`_mission_specs_dir_name(mission_slug, mid8)`), status/lifecycle_events.py:538 (`log_path.parent.name`), status/work_package_lifecycle.py:143/:283, cli/commands/agent/status.py:529, cli/commands/agent/workflow_executor.py:1673. tasks_mark_status.py:329 / tasks_move_task.py:2841 / review/cycle.py x3 left as-is: `mission_slug` there is the resolver-produced dir handle joined as kitty-specs/<mission_slug> (compliant by construction; not owned).
- 2026-09-06T13:06:34Z – claude – shell_pid=53806 – 2026-09-06T13:05:00Z – claude-fable-5-1 – T007: `BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS = 10.0` (aligned with DEFAULT_VERDICT_SAVE_TIMEOUT_SECONDS, pinned equal, not imported); `_in_queue_status_lock_timeout` NOT lifted (queue-aware: returns -1 off-queue, which is exactly the merge path). Holder sidecar `<lock>.holder` (filelock O_TRUNCs the lock file on every attempt), structured `FeatureStatusLockTimeoutError(lock_path, timeout, holder)`, message keeps the pinned "Timed out acquiring status lock" prefix. post_merge/retrospective_terminus.py: capture wrapped in `bounded_lock_timeout(...)` (bridge-reached emit_captured inherits it) + explicit `lock_timeout=` on emit_capture_failed. Facade export `BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS`.
- 2026-09-06T13:06:35Z – claude – shell_pid=53806 – 2026-09-06T13:12:00Z – claude-fable-5-1 – T008: 7-family lock-held pins + batch-door strict xfail in tests/status/test_writer_serialization.py (recorder on store._fsync_directory + locking._get_thread_locks); orchestrator_api/commands.py:3568 comment re-labelled as history; design note written (design-notes/WP01-lock-rules.md, delivered via scratch per coordinator).
- 2026-09-06T13:06:37Z – claude – shell_pid=53806 – 2026-09-06T13:20:00Z – claude-fable-5-1 – Verification: `.venv/bin/pytest tests/status tests/specify_cli/status tests/specify_cli/coordination tests/specify_cli/retrospective tests/specify_cli/migration tests/specify_cli/merge -q -p no:cacheprovider` -> 2194 passed, 1 skipped, 1 xfailed (290.8s). `.venv/bin/pytest tests/architectural/test_status_module_boundary.py tests/architectural/test_no_legacy_terminology.py tests/architectural/test_no_dead_symbols.py -q` -> 47 passed; terminology guard re-run after the design note -> 10 passed. test-fast equivalent (`.venv/bin/pytest tests/unit tests/status tests/cli tests/specify_cli/runtime tests/architectural/test_no_retired_subsystems.py -m "<FAST_TIER_MARKERS>" -n auto --dist loadfile -p no:cacheprovider -q`, PWHEADLESS=1; `make test-fast` itself uses `uv run`, forbidden in the worktree) -> 1661 passed, 1 xfailed (150.8s). Extra blast radius run earlier (tests/retrospective, tests/migration/test_verdict_provenance_backfill.py, tests/unit/migration/test_backfill_runtime_state.py, upgrade/status/cli backfill tests, tests/integration/test_migration_backfill.py, tests/runtime/test_bridge_retrospective.py, tests/specify_cli/post_merge) -> 979 passed after the .git-fallback fix; lock suites (tests/git_ops/test_atomic_status_commits_unit.py, journal-lock-unification, hermetic-ambient-git, write_side lock-root, checkout_file_lock, verdict_status_lock_bound) -> 180 passed after the message-prefix fix. ruff over all changed .py files exit 0. mypy (specified modules) -> 0 errors in touched files; 22 pre-existing errors remain in src/runtime/next/_internal_runtime/engine.py (12), runtime_bridge_engine.py (8), _internal_runtime/schema.py (1), retrospective/summary.py (1) — identical count on the main checkout, files identical to the merge-base, not mine (baseline-red category 1); the one pre-existing locking.py Any-return is fixed.
- 2026-09-06T13:06:38Z – claude – shell_pid=53806 – 2026-09-06T13:25:00Z – claude-fable-5-1 – Integration verification: no raw `open("a")` left in the four modules (grep); every `feature_status_lock(` call in src/ audited (table in design note §4); hardened writers still reached from their live entry points (post_merge terminus -> emit_capture_failed / bridge -> emit_captured; cutover/CLI/migration -> backfills; doctrine_synthesizer + _internal_runtime terminus -> emit_retrospective_event).
