# WP01 — Lock rules, writer census, and per-site decisions

**Mission**: `fsm-write-path-integrity-01M1TZV6` · **WP**: WP01 (Serialize the Out-of-Pipeline Writers) · **Date**: 2026-09-06
**Governs**: FR-001 (census), FR-002 (lock + atomic append), FR-003 (three lock rules), FR-004 (one lock key), NFR-001, NFR-003, C-002, C-003.
Line numbers are HEAD of the WP01 lane branch at hand-off.

---

## 1. Writer census (FR-001) — final

| # | Family | Entry point (module:line) | Before WP01 | After WP01 | Pin |
|---|---|---|---|---|---|
| ① | emit single + inner-state (flat shell) | `status/emit.py:634` (`emit_status_transition`), `:1013` (`emit_inner_state_changed`) | L1, keyed on `mission_slug` | L1, keyed on `feature_dir.name` (argument-only hunks) | `tests/status/test_writer_serialization.py` ids `1-emit-single`, `1-inner-state`; `tests/status/test_locking_key.py::test_emit_lock_key_is_the_directory_name_not_the_slug` |
| ② | lifecycle appender | `status/lifecycle_events.py:538` → `_lifecycle_write_lock:234` | L1, keyed on `mission_slug` | L1, keyed on `log_path.parent.name` (argument-only hunk) | id `2-lifecycle-appender` |
| ③ | `BookkeepingTransaction` | `coordination/transaction.py:290` (held for the txn lifetime; rollback truncate at `:944`) | L1, keyed on `mission_slug` | L1, keyed on `_mission_specs_dir_name(mission_slug, mid8)` = the `<slug>-<mid8>` dir it writes into (argument-only hunk) | `test_family_3_transaction_writes_only_while_holding_its_mission_lock`; SC-001 pin `test_retro_append_waits_for_rollback_and_lands_after_truncate` |
| ④ | retrospective run-terminus (superseded; "do not add new callers") | `retrospective/events.py:225` (`emit_retrospective_event`) | **none**, raw `open("a")` | L1 (`retro_status_lock`) + `append_raw_rows_atomic`; `materialize` stays outside the critical section | `tests/specify_cli/retrospective/test_events_locking.py`; id `4-retro-run-terminus` |
| ⑤ | retrospective lifecycle (live post-merge path) | `retrospective/lifecycle_events.py:321` (`_append_retro_lifecycle_event`), `:354` (`_locked_append`), Lamport read `:373` | **none**, raw `open("a")`; Lamport read outside any lock (TOCTOU) | L1 + `append_raw_rows_atomic`; Lamport read + build + append under ONE acquisition | `tests/specify_cli/retrospective/test_lifecycle_events_locking.py`; id `5-retro-lifecycle` |
| ⑥ | verdict-provenance backfill | `migration/verdict_provenance_backfill.py:414` | **none** (atomic only); `slot_present` event-log read outside any lock | L1 around discover → `slot_present` read → `append_events_atomic_verified` (`_collect_backfill_events` runs in-lock) | `tests/specify_cli/migration/test_backfill_writer_locking.py` (T004 block); id `6-verdict-backfill` |
| ⑦ | runtime-state backfill | `migration/backfill_runtime_state.py:1497` (lock), `:1551` (single append) | **none** (atomic ×2); `read_event_stream` idempotency read + claim-anchor read outside any lock; two-append window | ONE L1 acquisition covering `_claim_anchors`, `_build_seed_events`, `read_event_stream` and ONE `append_event_stream_atomic_verified` for the transition+annotation pair (`_backfill_runtime_state_locked`) | same file (T005 block); id `7-runtime-backfill` |
| — | batch door | `status/emit.py:808` (`emit_status_transition_batch`) | **none** | **WP02** (FR-018, research Q1) | `test_batch_door_writes_only_while_holding_its_mission_lock` — `xfail(strict=True)`, flipped by WP02 |

Excluded, unchanged: `core/mission_creation.py` (routes via ②; its direct touch is `touch(exist_ok=True)`).

The stale "only 2 of 6" comment at `orchestrator_api/commands.py:3568-3573` is re-labelled as history and points here.

**Lock-held evidence (SC-008).** Every store write funnels through `status/store.py::append_raw_rows_atomic` → `_fsync_directory(path.parent)`. `tests/status/test_writer_serialization.py::_HeldLocksAtWrite` patches that choke point and snapshots the calling thread's held locks (`locking._get_thread_locks()`), requiring `<feature_dir.name>.status.lock` among them for families ①–⑦ (①–③ are pins; ④–⑦ are the new behaviour). The batch-door case is the strict xfail WP02 flips.

---

## 2. The three lock rules (FR-003) and where the code encodes them

| Rule | Statement | Code site(s) | Test |
|---|---|---|---|
| (a) | Every L1 take reachable from an L3 (verdict-save-queue) scope is bounded | `review/cycle.py:804` `_in_queue_status_lock_timeout` → `feature_status_lock(..., timeout=...)` at `:878`, `:917`, `:969` (pre-existing, unchanged). **Nothing added in T002–T005 is reachable from `tasks_verdict_persistence.py` / `review/cycle.py` scopes**: the retrospective appenders are reached from `post_merge/retrospective_terminus.py`, `runtime/next/runtime_bridge_retrospective.py`, `cli/commands/retrospect.py`, `cli/commands/agent_retrospect.py`; the backfills from `upgrade/migrations/m_zz_verdict_provenance_backfill.py`, `migration/runtime_state_cutover.py`, the `backfill-runtime-state` CLI. None of those hold the verdict queue. | `tests/review/test_verdict_status_lock_bound.py` (existing); `tests/status/test_locking_key.py::test_bound_is_aligned_with_the_verdict_save_queue_bound` |
| (b) | The merge-path retrospective L1 take is finite | `post_merge/retrospective_terminus.py:124` `with bounded_lock_timeout(BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS)` scopes the whole capture (so `emit_captured`, reached through the runtime bridge, inherits the bound) and `:365` passes `lock_timeout=BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS` explicitly to `emit_capture_failed`. The scope is a `ContextVar` in `retrospective/lifecycle_events.py:70` (`bounded_lock_timeout`); an explicit keyword always wins (`_resolve_lock_timeout`). | `tests/specify_cli/retrospective/test_merge_path_lock_timeout.py` — contended lock ⇒ the terminus returns within the bound, logs a warning naming the lock file and holder, merge is not refused |
| (c) | One lock key | `status/locking.py:126` `feature_status_lock_path(repo_root, lock_key)` keyed on the mission directory name; root via `workspace/root_resolver.py:36` `resolve_status_lock_root`. Every `feature_status_lock(` call in `src/` (section 4) passes `feature_dir.name` or the transaction's composed dir name. | `tests/status/test_locking_key.py` — colliding slugs ⇒ distinct files; bare legacy dir ⇒ retro writer and emit path resolve one file |

### Timeout value for NFR-003: `BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS = 10.0` (`status/locking.py:55`)

- Reuses the bound the verdict-save queue already applies to its L1 takes (`review/verdict_commit_queue.py::DEFAULT_VERDICT_SAVE_TIMEOUT_SECONDS = 10.0`); pinned equal by test, **not imported** (`review` depends on `status`, not the reverse).
- Why not lift `_in_queue_status_lock_timeout` into `locking.py` as the prompt suggested: that helper is queue-aware — it returns `-1` (unbounded) whenever the verdict queue is not held, and the merge path never holds the queue, so lifting it would have left the merge-path take unbounded. The *value* is reused; the *predicate* is not.
- A status commit that holds L1 (`BookkeepingTransaction`) completes well inside 10 s; anything slower is an outage the merge path must surface as a failed retrospective step rather than wait out.
- The lock's own default stays `-1` (research Q2: a finite default is the #3893 follow-up).

### Structured timeout error

`FeatureStatusLockTimeoutError` (`status/locking.py:60`) now carries `lock_path`, `timeout`, `holder`. The holder is recorded on every outermost acquisition in a sidecar `<lock>.holder` (`_record_holder:158`, cleared on release) because `filelock` opens the lock file itself with `O_TRUNC` on every acquire *attempt*, so a contender would wipe anything written into the lock file. Message shape (prefix kept for the pre-existing pin in `tests/git_ops/test_atomic_status_commits_unit.py`):
`Timed out acquiring status lock <path> after <t>s: held by pid <pid> (thread <name>) since <iso>` / `... : holder unknown (no holder record)`.

---

## 3. Hierarchy (documentation; no inverse edges introduced)

```
L5  merge-global sentinel ──▶ L1 (bounded: rule b, 10 s)
L3  verdict-save queue    ──▶ L1 (bounded: rule a, 10 s)
L1  mission status lock (re-entrant per thread, 3 deep in production)
     └──▶ L4 (coord worktree) ──▶ git subprocess   ← BookkeepingTransaction (R9, unchanged)
                                                      and the coord-fallback arm (R9, bounded --
                                                      see amendment below)
```

- ~~No new code path takes L1 and then spawns git (NFR-001 / C-002).~~ **Amendment (2026-09-07, PR #3922 landing fold): this is no longer true.** `coordination/status_transition.py::_emit_on_coord_then_commit` (the coord-fallback arm shared by the single and batch doors, FR-004 row 7) holds `feature_status_lock` across `_commit_status_artifacts_to_coord`'s `safe_commit` git subprocesses -- a second L1-across-git path, sibling to the standing `BookkeepingTransaction` violation this section originally called out as the only one. It was added by the coord-fallback isolation fix (post-dates this census) and was missed by the per-site check below, which only covered families ④--⑦. It is accepted, not redesigned: releasing L1 before the commit/rollback would let a rollback erase a concurrent writer's successful append (the same rollback-safety property WP01 preserves for the transactional arm). What changed in the landing fold is the bound -- the take now passes `timeout=BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS` (`status/locking.py:55`) instead of the lock's unbounded `-1` default, so a stalled sibling git subprocess (blocked pre-commit hook, held `.git/index.lock`, credential prompt) surfaces as a structured `FeatureStatusLockTimeoutError` naming the holder, instead of wedging every status writer for the mission forever. See the corresponding NFR-001 amendment in `spec.md` and the red-first regression in `tests/specify_cli/coordination/` proving the bound. The per-site check below is otherwise unchanged and still accurate for families ④--⑦, which this WP did add and which genuinely never spawn git.
- Checked per site (unchanged from the original census): ④ appends then `materialize` (no git); ⑤ read + append; ⑥ artifact reads + event-log read + append; ⑦ frontmatter reads + event-log reads + one append. The git probe in `_git_common_dir` runs **before** the acquire, never while holding.
- **R9 note.** The standing L1-across-git violation is `BookkeepingTransaction` (`coordination/transaction.py:290` acquires; `commit()` runs `safe_commit` under it) **and, per the amendment above, the coord-fallback arm** (`status_transition.py` `_emit_on_coord_then_commit`). WP01 does not change either. WP01 *does* grow the victim population of a hung-git-under-L1 stall (families ④–⑦ now wait on that lock), which is exactly why rule (b) bounds the merge-path take and why a finite default remains the named follow-up on #3893.

---

## 4. Lock-key audit — every `feature_status_lock(` call in `src/`

| Site | Key passed | Status |
|---|---|---|
| `coordination/transaction.py:290` | `_mission_specs_dir_name(mission_slug, mid8)` | changed (WP01, argument only) |
| `status/emit.py:634` | `canonical_feature_dir.name` | changed (argument only; WP02 preserves) |
| `status/emit.py:1013` | `feature_dir.name` | changed (argument only) |
| `status/lifecycle_events.py:538` → `:254` | `log_path.parent.name` (mission logs); `None` ⇒ project lock | changed (argument only) |
| `status/work_package_lifecycle.py:143`, `:283` | `feature_dir.name` | changed (argument only) |
| `status/migrate_lifecycle_envelope.py:249` | `log_path.parent.name` | already compliant |
| `retrospective/lifecycle_events.py:111` | `feature_dir.name` | new (WP01) |
| `migration/verdict_provenance_backfill.py:414` | `feature_dir.name` | new (WP01) |
| `migration/backfill_runtime_state.py:1497` | `feature_dir.name` | new (WP01) |
| `cli/commands/agent/status.py:529` | `feature_dir.name` | changed (argument only) |
| `cli/commands/agent/workflow_executor.py:1673` | `feature_dir.name` | changed (argument only) |
| `cli/commands/agent/tasks_mark_status.py:329`, `tasks_move_task.py:2841` | `st.mission_slug` | compliant by construction: resolved through the canonical mission resolver (`_find_mission_slug` → `resolve_mission_handle`), i.e. the on-disk mission directory handle, and joined as `kitty-specs/<mission_slug>` at every read/write site in those commands. No `feature_dir` local in scope at the lock site; left untouched (not owned). |
| `review/cycle.py:878`, `:917`, `:969` | `mission_slug` | compliant by construction: validated as a single path segment and joined as `kitty-specs/<mission_slug>/tasks/...` (it IS the directory name). Left untouched (rule a site, not owned). |

---

## 5. Per-site `nullcontext()` decisions (spec edge case: conscious, never accidental)

| Site | Decision | Why |
|---|---|---|
| ④ `retrospective/events.py` | **no** `nullcontext()` | `resolve_status_lock_root` never raises; the lock degrades to a deterministic per-tree file (section 6). There is no "no root" case in which skipping the lock is safer. `FeatureStatusLockTimeoutError` propagates (outage signal). |
| ⑤ `retrospective/lifecycle_events.py::retro_status_lock` | **no** `nullcontext()` | same; documented in the helper docstring |
| ⑥ `verdict_provenance_backfill.py` | **no** `nullcontext()` | same; one-shot migration, lock cost irrelevant |
| ⑦ `backfill_runtime_state.py` | **no** `nullcontext()` | same |
| ② `status/lifecycle_events.py::_lifecycle_write_lock` (pre-existing) | `nullcontext()` **only** when `_repo_root_for_lifecycle_log` finds no git root | unchanged pre-existing best-effort/never-raise contract. Production mission trees always have a git root. The family-② pin therefore runs in a git-initialized sandbox (`_git_sandbox`), and this is the one site where a bare non-git tree is deliberately unlocked. |

---

## 6. Finding: the lock's non-git degrade minted a `.git/` directory

`locking._git_common_dir` fell back to `<repo_root>/.git` whenever the git probe failed, and `acquire_or_raise` `mkdir -p`s the lock directory — so taking the lock in a **non-git tree** created `<root>/.git/`, which `resolve_canonical_root` (rule 1: a `.git` directory ends the walk) then treated as a repo root. Adding L1 to ⑥/⑦ exposed this: two bare-tree migration tests broke because a lock take turned `tmp_path` into a fake canonical root (`tests/review/test_artifacts.py` already documents the same trap). Fix (`status/locking.py:92`): keep `<root>/.git` only when it already **is** a directory (real checkout, transient probe failure — the historical contract); otherwise degrade to `<root>/.kittify/spec-kitty-locks/`. Pinned by `tests/git_ops/test_atomic_status_commits_unit.py::test_lock_on_non_git_tree_never_mints_a_dot_git_directory` and `tests/specify_cli/migration/test_backfill_writer_locking.py::test_backfill_never_mints_a_git_dir_in_a_bare_tree`. Consumers in real checkouts see no path change.

---

## 7. Out-of-map edits (argument-only or comment-only unless stated)

- `status/emit.py:634`, `:1013` — lock key (FR-004). WP02 owns the file; hunks are the single argument each.
- `coordination/transaction.py:290` — lock key (FR-004); argument only.
- `status/lifecycle_events.py:538`, `status/work_package_lifecycle.py:143`/`:283`, `cli/commands/agent/status.py:529`, `cli/commands/agent/workflow_executor.py:1673` — lock key (FR-004); argument only.
- `status/__init__.py` — two facade exports (`append_raw_rows_atomic`, `BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS`): `tests/architectural/test_status_module_boundary.py` forbids deep `status.store`/`status.locking` imports from outside `status/`, so the prompt's "import from `specify_cli.status.store` directly" was not an option. WP03's `_unsafe.py` repoint stays mechanical (one facade name to move).
- `orchestrator_api/commands.py:3568-3573` — comment only (FR-001 history label).
- `tests/git_ops/test_atomic_status_commits_unit.py` — the non-git fallback pin refined (section 6) plus one new case.


---

## 8. WP07 census addendum — the two writers the WP03 gate found (families ⑧ and ⑨)

**Mission**: `fsm-write-path-integrity-01M1TZV6` · **WP**: WP07 (Writer Census Addendum) · **Date**: 2026-09-06
**Governs**: FR-001 (census completeness), FR-002 (lock + atomic write), FR-003 rules (a)/(b)/(c), FR-004 (one lock key), NFR-001, SC-008.
Line numbers are HEAD of the WP07 lane branch (`lane-g`, based on WP03's `264a83ae7`).

WP03's AST writes gate (`tests/architectural/test_status_events_writes_gate.py`) found two out-of-pipeline writers of `status.events.jsonl` that the research census and section 1 above (families ①–⑦) did not enumerate; `design-notes/WP03-gates.md` §5 ledgered them as **FINDING**, not blessed. WP07 hardens both the WP01 way. With this addendum the census is nine families and SC-008 ("0 unlocked writer families") holds for every writer the gate can see.

### 8.1 Census rows (extends the section 1 table)

| # | Family | Entry point (module:line) | Before WP07 | After WP07 | Pin |
|---|---|---|---|---|---|
| ⑧ | decision-point rows (`DecisionPointOpened` / `DecisionPointResolved`) | `decisions/emit.py:108` (`_append_raw_event`; lock take at `:136`), reached from `emit_decision_opened:240` and `emit_decision_resolved:322` | **none**, raw `open("a")` append + a separate `open("r")` readback (TOCTOU on the Lamport proxy); not atomic; PII stripped in-module | L1 keyed on `feature_dir.name` (root via `resolve_status_lock_root`) around `append_raw_rows_atomic(events_path, [row])` **and** the Lamport readback (one acquisition, so the count is this row's line number). The primitive strips PII (`sanitize_event_for_log` inside `store.append_raw_rows_atomic`), so the module-level call went away. | `tests/specify_cli/decisions/test_emit_locking.py` — rollback-truncate race (SC-001 shape), lock-held for both event types, Lamport-under-lock, NFR-001 spawn recorder, AST "no raw write-mode open"; `tests/status/test_writer_serialization.py` id `8-decision-point` |
| ⑨ | legacy whole-log rebuild (migration-only) | `migration/rebuild_state.py:541` (`rebuild_event_log`; lock take at `:581`) → `_rebuild_event_log_locked:585`; the durable step is `os.replace(str(tmp_file), str(events_file))` at `:802` | **none**; read at step 1 (`_read_existing_events`) and rewrite at step 6 in different windows, so a locked shell append landing in between was erased by the rewrite | L1 keyed on `feature_dir.name` around the **whole** read → reconcile → `tmp.open("w")` + `os.replace` (one acquisition; the body moved verbatim into `_rebuild_event_log_locked`). The `os.replace` shape is unchanged — it is a rewrite, not an append, so it stays a ledgered write site, not a store primitive. | `tests/specify_cli/migration/test_rebuild_state_locking.py` — a thread holding L1 blocks the rewrite; a locked append arriving mid-rebuild lands **after** the rewrite (red-first); `os.replace` sees L1 held; the skipped arms release the lock; NFR-001 spawn recorder + no `subprocess`/`git_ops` import; `test_writer_serialization.py` id `9-rebuild-state` |

**Why ⑨ locks the whole function rather than only `:758-766`.** The task text says "wrap the tmp write + `os.replace`"; locking only that region would leave the step-1-read → step-6-write window open — exactly the lost-append the finding describes (the red-first test `test_append_landing_during_the_rebuild_is_not_lost` triggers the append after the read and before the write, and it FAILS with a narrow lock just as it does with none). WP01's rule for ⑤/⑥/⑦ — "the idempotency / Lamport read moves INSIDE the lock, one acquisition" (`contracts/emit-pipeline.md` §4) — applies verbatim. The diff is a 3-line wrapper plus a rename; the pre-existing `# noqa: C901` travelled with the body unchanged (none added).

**Lock-held evidence (SC-008) for ⑨.** Family ⑨'s durable write is not a store append, so it never reaches the `_fsync_directory` choke point the section 1 recorder patches. `_HeldLocksAtWrite` now also snapshots every `os.replace` whose destination file name is `status.events.jsonl` (the store's own `os.replace` is captured too, harmlessly). The nine-family parametrized test is green.

### 8.2 Lock-key audit rows (extends section 4)

| Site | Key passed | Status |
|---|---|---|
| `decisions/emit.py:136` | `feature_dir.name` where `feature_dir = events_path.parent` and `events_path` comes from `placement_seam(...).read_dir(STATUS_STATE)` — the coord-partition mission dir under a coordination topology, `kitty-specs/<slug>` otherwise; `resolve_status_lock_root` resolves the canonical root through the worktree so the lock file is the transaction's (proven by the race test, which runs the append against the coord worktree dir the `BookkeepingTransaction` materialized) | new (WP07) |
| `migration/rebuild_state.py:581` | `feature_dir.name` | new (WP07) |

### 8.3 Per-site `nullcontext()` decisions (extends section 5)

| Site | Decision | Why |
|---|---|---|
| ⑧ `decisions/emit.py` | **no** `nullcontext()` | `resolve_status_lock_root` never raises; the lock degrades to a deterministic per-tree file (`.kittify/spec-kitty-locks/` in a bare tree — pinned: the bare-tree tests assert no `.git/` is minted). There is no "no root" case in which skipping the lock is safer; `FeatureStatusLockTimeoutError` cannot occur (unbounded) and any other lock failure propagates to the decision caller as an outage signal. Documented in the function docstring. |
| ⑨ `migration/rebuild_state.py` | **no** `nullcontext()` | same; one-shot migration, lock cost irrelevant. Documented in the function docstring. |

### 8.4 Timeout decisions (rule (a)/(b) reachability)

| Site | Timeout | Reachability check |
|---|---|---|
| ⑧ | lock default (`-1`, unbounded) | Callers of `emit_decision_opened/resolved`: `decisions/service.py` (`open_decision`, `_repair_missing_opened_event`, `_terminal_command`) ← `missions/plan/{plan,specify}_interview.py`, `widen/{review,interview_helpers}.py`, `orchestrator_api/commands.py` (1:1 wrappers), `cli/commands/decision.py`, `cli/commands/lifecycle.py`. No module under `src/specify_cli/{merge,post_merge,review,git_ops}` imports `specify_cli.decisions` (grep), so neither the verdict-save queue (L3, rule a) nor the merge sentinel (L5, rule b) can hold while a decision row is appended. `BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS` therefore does not apply; a finite *default* remains the #3893 follow-up (research Q2). |
| ⑨ | lock default (`-1`) | Sole caller: `migration/mission_state.py:2487` (the canonical per-mission rebuild entry, reached from the one-shot migration runner and the lifecycle normalizer). Not reachable from L3/L5. |

Nesting: L1 is re-entrant per thread, so a caller that already holds L1 (none found for either site) would nest without deadlock; no nesting test was added because no such caller exists.

### 8.5 NFR-001 (no git under L1)

- ⑧: the critical section is `append_raw_rows_atomic` + a read of the same file. `placement_seam(...)` and the fan-out (`_queue_decision_fanout`) run outside the lock. Pinned by a `subprocess.run/Popen` recorder asserting no spawn sees the lock held.
- ⑨: the module imports no `subprocess`/`git_ops` API (AST-pinned); the only spawn observed during a rebuild is the lock root's own `git` probe in `_git_common_dir` / `resolve_canonical_root`, which runs **before** the acquire (section 3 of this note) — the recorder asserts no spawn sees the lock held.

### 8.6 Gate deltas (out-of-map edits, one line each)

- `status/_unsafe.py` `ALLOWED_CALLERS` **+1** (`specify_cli.decisions.emit`, "Family 8 … decision-point rows"); `tests/architectural/test_status_unsafe_allowlist.py` `BASELINE` **+1** (same). 8 → 9 entries each; every entry is live.
- `tests/architectural/test_status_events_writes_gate.py`: the `decisions.emit` **FINDING** entry is **removed** (the gate now proves the raw write is gone — a stale entry would fail `test_allowed_out_of_store_sites_are_live`); the `rebuild_state` entry is **re-labelled** from "holds NO mission status lock — follow-up" to "family 9, locked atomic rewrite"; `EXPECTED_LOCK_COMPOSITION_SITES` **+2** (`specify_cli.decisions.emit`, `specify_cli.migration.rebuild_state`) — 13 → 15 modules. `design-notes/WP03-gates.md` §4 (the table row for `decisions/emit.py:110` and the R14 census count) and §5 items 1–2 should be marked closed by WP07 when this addendum lands.
- **Per-key counts (WP03 reviewer minor finding):** `ALLOWED_OUT_OF_STORE_WRITE_SITES` is now `Mapping[(module, kind, path_expr) -> allowed site count]` (all four remaining entries `: 1`). `out_of_store_violations` reports every site of a key that carries more sites than allowed (line-number independent; the message carries allowed/found), `ledger_shortfall` drives the live test (a vanished or under-counted key is stale), and the floor `test_writes_gate_counts_ledgered_sites` duplicates an allowed shape (`Path.open` truncate and `os.replace` rewrite) in a synthetic module under the allowed module's name and proves the duplicate is reported while the single copy is not.
- `tests/architectural/test_no_dead_symbols.py`: the content-tier `SymbolKey` hash for `_unsafe::ALLOWED_CALLERS` re-minted (the set's body changed); the entry's rationale is unchanged.
- `tests/specify_cli/status/test_store_sanitized.py::test_sanitizer_is_called_in_append_raw_event`: the tracker now patches the store's `sanitize_event_for_log` (where the one call per row lives after WP07) instead of a name `decisions/emit.py` no longer imports.

### 8.7 RED proofs (red-first discipline, C-009 — both tests stay as permanent pins)

- **T040** — `tests/specify_cli/decisions/test_emit_locking.py::test_decision_append_waits_for_rollback_and_lands_after_truncate` on the unchanged `emit.py`:
  ```
  tests/specify_cli/decisions/test_emit_locking.py:225: in test_decision_append_waits_for_rollback_and_lands_after_truncate
      assert opened, "SC-001: the DecisionPointOpened row was truncated away by the rollback"
  E   AssertionError: SC-001: the DecisionPointOpened row was truncated away by the rollback
  E   assert []
  1 failed, 5 deselected in 33.67s
  ```
- **T041** — `tests/specify_cli/migration/test_rebuild_state_locking.py` on the unchanged `rebuild_state.py`:
  ```
  test_append_landing_during_the_rebuild_is_not_lost
      assert '01EVT0000000000000000LATE' in ['01EVT00000000000000000001']
  AssertionError: the shell append was lost under the whole-log rewrite
  test_rewrite_runs_while_mission_lock_is_held
  AssertionError: [set()]          # os.replace ran with no lock held
  test_rewrite_blocks_while_another_thread_holds_the_mission_lock   # rebuild did not wait
  3 failed, 2 passed in 2.18s
  ```
  After the change: 5 passed; the nine-family serialization test + family 3 + the SC-001 pin: 16 passed, 1 xfailed (WP02's strict xfail, untouched).
