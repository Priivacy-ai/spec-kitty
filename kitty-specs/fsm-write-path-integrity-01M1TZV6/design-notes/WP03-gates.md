# WP03 — Facade strip, `status/_unsafe.py`, and the two write gates

**Mission**: `fsm-write-path-integrity-01M1TZV6` · **WP**: WP03 (Facade Strip + Write Gates) · **Date**: 2026-09-06
**Governs**: FR-010 (facade strip / enumerated raw-append access), FR-011 (AST writes-gate), SC-004 (non-vacuity), R14 (lock-composition census). Contract: `contracts/write-gates.md`.
Line numbers are HEAD of the WP03 lane branch at hand-off.

---

## 1. The census-gate rule (first instance — this WP)

> **Every enumerated census of writers or callers that a mission fixes ships an architectural gate seeded from that census, with a non-vacuity floor.**

A census that lives only in a design note decays: this mission's own census corrected a stale in-code claim ("only 2 of 6") and dropped a false positive before WP01 had written a line. WP03 is the first instance of the rule. The two gate node ids:

- `tests/architectural/test_status_unsafe_allowlist.py` — the raw-append **door** census (`_unsafe.ALLOWED_CALLERS`, shrink-only against `BASELINE`).
- `tests/architectural/test_status_events_writes_gate.py` — the **write-site** census of `status.events.jsonl` (allowed only in `status/store.py`; resolved out-of-store sites are a shrink-only, per-site-justified ledger) plus the R14 `feature_status_lock(` composition census.

Both gates carry floors that feed synthetic sources to the *same* scanner function the gate uses and assert a violation is reported; both assert the real tree yields ≥ 1 positive match, so a scan that matches nothing fails.

### Text to post on #3895 (operator posts; do not paste the heading)

> **Census-gate rule (proposed standing order, first instance landed).** Every enumerated census of writers/callers that a mission fixes ships an architectural gate seeded from that census, with a non-vacuity floor. Rationale: a census recorded only in prose decays silently — `fsm-write-path-integrity-01M1TZV6` found its own in-code census claim stale ("only 2 of 6") and one entry false before implementation started. First instance: mission `fsm-write-path-integrity-01M1TZV6` WP03 —
> `tests/architectural/test_status_unsafe_allowlist.py` (raw `status.events.jsonl` append doors: every importer must be in `specify_cli.status._unsafe.ALLOWED_CALLERS`, which must stay a subset of the committed `BASELINE`; stale entries fail; synthetic-importer floor) and
> `tests/architectural/test_status_events_writes_gate.py` (AST scan of every write-mode `open`/`Path.open`/`write_text`/`write_bytes`/`os.open`/`os.replace` on a path resolving to `status.events.jsonl`; allowed only in `status/store.py` or a per-site-justified shrink-only ledger; unresolved event-named writes pinned; `feature_status_lock(` composition census pinned; synthetic-writer floor).
> Shape to copy: a `BASELINE` frozenset committed in the test, `ALLOWED ⊆ BASELINE`, a liveness check that every allowed entry is still found, and a floor that feeds a synthetic violator to the same scanner. Two follow-ups the gate surfaced are listed in the mission's `design-notes/WP03-gates.md` §5.

---

## 2. What moved (FR-010)

| Before (`status/__init__.py:46-73`, `:519-547`) | After |
|---|---|
| Facade exported `append_event`, `append_event_verified`, `append_event_stream_atomic_verified`, `append_events_atomic_verified`, `append_primary_checkout_event_verified`, `append_primary_checkout_events_atomic_verified`, `append_annotations_atomic_verified`, `append_raw_rows_atomic` | None exported. `from specify_cli.status import append_event` raises `ImportError` (pinned by `test_facade_no_longer_exports_raw_appends`). A provenance note on the import block records the two promotions this reverses (verdict-seam-boundary-hardening WP02; this mission's WP01). |
| — | `src/specify_cli/status/_unsafe.py` re-exports those eight from `.store` and declares `ALLOWED_CALLERS`. `BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS` stays on the facade (a lock constant, not a writer). |

`append_events_atomic` (the unverified batch helper) is **not** re-exported: no `src/` module outside the store calls it (tests reach it via `status.store` directly). The allowlist gate still counts an import of it as a door (`STORE_APPEND_PRIMITIVES` pins the store's full `def append_*` surface so a new primitive cannot appear un-enumerated).

### `ALLOWED_CALLERS` (8) — seeded from the real importers, one census family each

| Module | Family / shell | Door it uses |
|---|---|---|
| `specify_cli.status.emit` | ① flat shell, batch door, inner-state | `from . import store as _store` (module object) |
| `specify_cli.status.lifecycle_events` | ② lifecycle appender | `from .store import append_raw_rows_atomic` |
| `specify_cli.coordination.status_service` | ③ coord write funnel | `_unsafe.append_annotations_atomic_verified / append_event_verified / append_event_stream_atomic_verified` |
| `specify_cli.coordination.transaction` | ③ `BookkeepingTransaction` | `status_service.append_event_stream_log` (wrapper door) |
| `specify_cli.retrospective.events` | ④ run-terminus (superseded) | `_unsafe.append_raw_rows_atomic` |
| `specify_cli.retrospective.lifecycle_events` | ⑤ retro lifecycle | `_unsafe.append_raw_rows_atomic` |
| `specify_cli.migration.verdict_provenance_backfill` | ⑥ | `_unsafe.append_events_atomic_verified` |
| `specify_cli.migration.backfill_runtime_state` | ⑦ | `_unsafe.append_event_stream_atomic_verified` |

Differences from the contract §1 expectation ("families ②③⑤⑥⑦ + `status/emit.py` + `coordination/status_transition.py`"): family ④ (`retrospective/events.py`) is a live raw importer and is listed; `coordination/status_transition.py` imports **no** primitive (it routes through `emit_status_transition`) and is therefore not in the allowlist — it appears instead in the writes-gate ledger for its rollback truncate (§4).

### Analysis finding I1 — how it is closed

At HEAD, `coordination/transaction.py:36` does **not** import from `status.store`; it imports the wrapper `append_event_stream_log` from `coordination/status_service.py`, and it is `status_service.py` (also boundary-exempt) that reached the primitives — through the *facade*, not the store. The bypass class I1 describes is real, so the scanner counts four door shapes, not just `_unsafe` importers:

1. `status._unsafe` (any name, module object, or `import specify_cli.status._unsafe`);
2. `status.store` — any `append_*` primitive by name, or the module object (`from specify_cli.status import store`, `import specify_cli.status.store`), absolute or relative;
3. `specify_cli.status` — any primitive by name (the retired facade shape; re-promoting one makes the facade package itself an importer and fails);
4. `coordination.status_service.append_event_log` / `append_event_stream_log` (the wrapper doors).

`status_service.py` was repointed to `_unsafe` and both coordination modules are enumerated. `transaction.py` was **not** edited (the prompt's one-line repoint would have been a no-op: it never imported from the store). The floor test exercises all ten synthetic shapes, including a boundary-exempt module gaining a direct `status.store` append import.

### Out-of-map edits (rationale "FR-010 repoint to `_unsafe`", one line each)

`coordination/status_service.py:310,311,329`; `retrospective/events.py:223`; `retrospective/lifecycle_events.py:335`; `migration/verdict_provenance_backfill.py:81`; `migration/backfill_runtime_state.py:111`. Plus:

- `tests/architectural/test_status_module_boundary.py` — `_is_bypass_import` / `_is_status_submodule_name` carve out `specify_cli.status._unsafe` as the sanctioned door (otherwise SR-2 would have forced all five writers onto its exemption ledger for a door another gate owns); one pin test added.
- `tests/architectural/test_no_dead_symbols.py` — new category `_CATEGORY_C_FSM_WRITE_PATH_UNSAFE_DOOR` for `_unsafe::ALLOWED_CALLERS` (gate-facing by design) and `_unsafe::append_event` (contract-mandated re-export whose only importers are tests; escalated module-path tier because its alias text collides with `glossary`'s `append_event`). Judgment call recorded: dropping `append_event` from the door would have been cleaner for the dead-code gate but contradicts the contract's "every raw primitive" rule and the 14 tests now seeding logs through the door.
- 14 test files repointed from the facade to `specify_cli.status._unsafe` (tests may import the door freely; the gate scans `src/` only).

---

## 3. Writes gate — scanner rules as built (FR-011)

Write kinds: `open`/`io.open` (mode from arg or `mode=`; default `r`), `<recv>.open(mode)`, `.write_text`, `.write_bytes`, `os.open` (flags text containing `O_WRONLY|O_RDWR|O_APPEND|O_TRUNC|O_CREAT`), and **`os.replace`/`os.rename`/`shutil.move` destinations** (added beyond the contract list: the atomic-rename landing is the durable write in this codebase — `append_raw_rows_atomic` never opens the target path). A non-constant mode is fail-closed (counted as a write).

Path resolution (static, tail-only): constants; f-strings; `a / b` → `b`; `Path(x)`/`str(x)`; `.resolve()/.absolute()/.expanduser()` pass-through; `.joinpath/.with_name`; `EVENTS_FILENAME` under any alias imported from `specify_cli.status(.store|._unsafe)`; module constants; last same-function assignment; `self.<attr>` assigned anywhere in the module; same-module function returns (all must agree); and **parameters resolved through every same-module call site** (`name(...)`, `self.name(...)`, `Class(...)`/`cls(...)` for `__init__`; all callers must agree, keyword-only supported). The parameter rule is what resolves the `BookkeepingTransaction` rollback (`self._events_path` ← ctor param ← factory local `feature_dir / _EVENTS_FILENAME`) and the `decisions/emit.py` append (§5).

"Unresolved is not a pass": every unresolved write whose path **expression** is event-named is pinned (`EXPECTED_UNRESOLVED_EVENT_NAMED_WRITE_SITES`, 3 entries), and the dynamic event-log writers that rule cannot name are pinned as `KNOWN_DYNAMIC_EVENT_LOG_WRITE_SITES` (3 entries, each must stay live-unresolved). A module-level "mentions the filename anywhere" predicate was tried first and rejected: it pinned 30–39 unrelated writes (config files, artifacts) in modules that merely reference the log in a docstring.

Positive census: the store yields exactly `{("Path.open","a"), ("os.replace","replace")}` — `append_event:302` and `append_raw_rows_atomic:401`.

---

## 4. The write surface the gate actually found (all `status.events.jsonl` write sites outside `store.py`)

| Site (module:line at HEAD) | Kind | Classification | Where pinned |
|---|---|---|---|
| `coordination/transaction.py:943` | `self._events_path.open("ab")` + truncate | family ③ rollback truncate (in-lock) | ledger |
| `coordination/status_transition.py:361` | `events_path.open("ab")` + truncate | coord fallback-arm rollback truncate (WP06 may retire → ledger shrinks) | ledger |
| `cli/commands/agent/workflow.py:297` | `events_path.open("ab")` + truncate | workflow-commit rollback truncate (kw-only param, unresolved) | event-named pin |
| `lanes/auto_rebase.py:382` | `events_path.write_text(index_text)` | sparse-checkout hydration from the git index (checkout materialization, not an append) | ledger |
| `migration/rebuild_state.py:766` | `os.replace(tmp, events_file)` | legacy whole-log rebuild; **holds no mission status lock** | ledger + §5 |
| `decisions/emit.py:110` | `events_path.open("a")` | **raw, unlocked, non-atomic append** of `DecisionPointOpened` rows — a writer the WP01 census did not enumerate | ledger (marked FINDING) + §5 |
| `merge/bookkeeping_projection.py:339` | `trusted_target_events_path.write_bytes(union)` | merge-time union projection onto the target checkout | event-named pin |
| `status/event_log_merge.py:97` | `target.open("w")` | three-way merge-driver output | known-dynamic pin |
| `status/migrate_lifecycle_envelope.py:274` | `os.replace(tmp, path)` | envelope migration whole-file replace | known-dynamic pin |
| `merge/executor.py:233` | `path.write_bytes(original)` | #2804 gate-artifact restore after squash | known-dynamic pin |
| `glossary/events.py:172` | `event_log_path.open("a")` | the glossary's **own** log, not the status log | event-named pin (documented) |

Not classified as writes by design: `core/mission_creation.py:697` `touch(exist_ok=True)` (creation, no rows — WP01 exclusion) and `unlink()` calls.

### R14 lock-composition census (`EXPECTED_LOCK_COMPOSITION_SITES`, 13 modules, built from the tree)

`status.emit` ①, `status.lifecycle_events` ②, `coordination.transaction` ③, `retrospective.lifecycle_events` ⑤ (④ composes through `retro_status_lock`), `migration.verdict_provenance_backfill` ⑥, `migration.backfill_runtime_state` ⑦, `status.work_package_lifecycle`, `status.migrate_lifecycle_envelope`, `review.cycle` (rule-a bounded takes), and the CLI shells `cli.commands.agent.{status, workflow_executor, tasks_mark_status, tasks_move_task}`. Matches WP01's lock-key audit (§4 of `WP01-lock-rules.md`) exactly; `retrospective/events.py` and `tasks_verdict_persistence.py` do not call the lock directly (they compose through `retro_status_lock` / `review/cycle.py`). Both bare and attribute (`_tasks.feature_status_lock(`) call shapes are counted.

---

## 5. Findings surfaced by the gate (follow-ups; not fixed in WP03 — files not owned)

1. **`src/specify_cli/decisions/emit.py:100-112` (`_append_raw_event`)** — raw `open("a")` append of `DecisionPointOpened` rows to `kitty-specs/<mission>/status.events.jsonl` with no `feature_status_lock`, no atomic write, no readback. This is an out-of-pipeline writer of exactly the kind FR-001/FR-002 targeted; it was not in the WP01 census (families ①–⑦). Recommended fix: take L1 keyed on the mission directory name and append via `append_raw_rows_atomic` behind `status/_unsafe` (adds `specify_cli.decisions.emit` to `ALLOWED_CALLERS` and `BASELINE`, and removes its ledger entry from `ALLOWED_OUT_OF_STORE_WRITE_SITES`), or route through the FSM. Until then the ledger entry is labelled FINDING, not blessed.
2. **`src/specify_cli/migration/rebuild_state.py:758-766`** — whole-log rewrite (`tmp.open("w")` + `os.replace`) with no mission status lock. Migration-only, but a concurrent shell append during the rewrite would be lost. Recommended: wrap in `feature_status_lock(resolve_status_lock_root(feature_dir), feature_dir.name)`.
3. **Merge-time materializations** (`merge/bookkeeping_projection.py`, `status/event_log_merge.py`, `merge/executor.py`, `lanes/auto_rebase.py`) rewrite the log wholesale outside any status lock. They are git-materialization steps, not FSM appends, and are pinned/ledgered rather than blessed; whether they should hold L1 is a question for the mission's R9/R14 owners.

---

## 6. Transitional markers

None. No `xfail`/red-first markers exist in the WP03 files; the WP01 strict `xfail` in `tests/status/test_writer_serialization.py` is WP02's to flip and is untouched.


---

## Closure (WP07)

The two FINDING sites in §4/§5 (`decisions/emit.py:100-112`, `migration/rebuild_state.py:758-766`) were hardened by WP07 (families ⑧/⑨; lock + atomic primitive; ledger entries removed/relabelled; per-key counts added to the writes-gate ledger). See `WP01-lock-rules.md` addendum.

## PR3922 adversarial follow-up — coord fallback composition

`specify_cli.coordination.status_transition` now holds the same mission-directory
L1 around fallback snapshot, flat-shell emit, tail capture, commit and rollback.
The flat shell re-enters L1. This prevents rollback from truncating another
writer's rows and freezes each operation's outbound rows before releasing the
lock. Fan-out consumes the captured stream after commit and lock release. The
lock-composition census adds this existing fallback shell; the write allowlist
and its shrink-only bounds are unchanged.

## spec-kitty #3960 follow-up — the two rollback truncates close (DRIFT-2)

The post-merge mission review (DRIFT-2) found the two rollback truncates this
WP ledgered but did not close: the coord fallback arm's
`coordination/status_transition.py::_restore_coord_status_artifacts` and its
`cli/commands/agent/workflow.py::_restore_status_artifacts` twin both
truncated `status.events.jsonl` back to a pre-emit byte size without
verifying the tail they cut. Both migrated onto one status-owned, lock-held,
tail-verified helper — `specify_cli.status.rollback.rollback_events_log_tail`
(raw truncate primitive `store.truncate_events_log`; the helper re-acquires
the same per-mission `feature_status_lock` the pipeline uses and refuses to
cut a tail that is not exactly the rows the operation appended). Gate effect:
the `ALLOWED_OUT_OF_STORE_WRITE_SITES` entry for the coord fallback arm and
the `EXPECTED_UNRESOLVED_EVENT_NAMED_WRITE_SITES` pin for the workflow twin
are REMOVED (ledger −2, shrink-only honored); the `_LEDGERED_SHAPES`
path-open-truncate floor case is re-keyed to the transactional arm's own
`self._events_path` entry, which stays ledgered (its truncate runs inside the
transaction's own L1); the store's positive census gains the
`("Path.open", "ab")` rollback-restore shape; and the R14 lock-composition
census adds `specify_cli.status.rollback`.
