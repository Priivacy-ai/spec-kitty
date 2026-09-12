---
affected_files: []
cycle_number: 6
mission_slug: per-project-sync-consent-ledgers-01KZKMQZ
reproduction_command:
reviewed_at: '2026-08-09T21:48:33Z'
reviewer_agent: user
wp_id: WP01
---

# WP01 Cycle-6 Independent Review — Traceability Changes Requested

## Verdict and Human-in-Charge scope ruling

Every exact cycle-5 blocker is closed, the production classifications are now
internally consistent, and all official gates pass. Independent adversarial
review found additional control-flow and mutation-shape limitations, but the
Human-in-Charge explicitly ruled that these variants must not extend WP01 into
another detector-implementation cycle. They are deferred to
[Priivacy-ai/spec-kitty#3280](https://github.com/Priivacy-ai/spec-kitty/issues/3280).

This transition requests **traceability only**. Do not change analyzer behavior
for the deferred variants in WP01. Add the `TODO(#3280)` comments identified
below and disclose the limitation plus follow-up issue in the eventual PR. Once
that documentation-only reroll is present, cycle 7 should confirm the comments,
rerun the same gates, and approve if nothing else changed.

## Exact cycle-5 closures confirmed

- Store reachability now resolves all three live function-local imports of
  `detect_legacy_rows_for_scope`; the production census reports `83 live`,
  `14 legacy-migration`, `1 read-only`, and only the genuinely unreferenced
  `_queue_db_has_content` as dead.
- Late global rebinding and parameter shadowing no longer produce SQLite-owner
  sites; a function-local SQLite import remains a positive control.
- The imported grant writer rebound to `safe` is excluded, while
  `setattr(record, "granted", answer)` remains discovered and the consent-named
  widget remains excluded.
- Two-hop and independently replayed three-hop sender aliases both resolve to
  `client.post`.
- Join-built INSERT is discovered, join-built SELECT is excluded, and unresolved
  plus stale-rebound SQL are surfaced as `UNRESOLVED` rather than disappearing
  or retaining the old INSERT.
- The exact unrelated DURABLE, DURABLE_FILE, and IN_MEMORY result mutations from
  cycle 5 are rejected.
- `context(a.uuid); a.uuid = b.uuid; attempt(...a.uuid...)` is rejected, along
  with the earlier tuple-path, audit-header/foreign-body, and local-name A→B
  specimens.
- The exact layout, sibling lock, ADR/#3030 supersession, retained egress
  defenses, and live EventJournal/TeamspaceReceiver/SqliteDeliveryLedger controls
  remain green. No production or mission-contract source changed.

## Deferred evidence captured in #3280

The following are **not WP01 remediation requests**. They explain why the
analyzers remain bounded static evidence rather than general Python semantic
proof and must be visible to later maintainers.

### Binding and control-flow variants

- Store: `owner = sqlite3.connect; if flag: owner = safe; owner(path)` produces
  no site even though the false branch opens SQLite.
- Grant: a module alias `writer = persist` is not propagated, and
  `writer = persist; if flag: writer = safe; writer(...)` loses the false-branch
  grant path.
- Sender: three-hop aliases work, but `wire = safe; if flag: wire = client.post;
  wire(...)` and tuple unpacking `wire, other = (client.post, safe)` produce no
  sink site.
- Layout: `sql = INSERT; if flag: sql = SELECT; execute(sql, ...)` is traversed as
  one final binding and misses the false-branch write.

### Result-relation and mutation-order variants

- DURABLE accepts `event_id` persisted into an unrelated column of the correct
  authority table.
- DURABLE_FILE accepts `save_sync_state(state)` before
  `state.last_saas_confirmed_hash = git_hash`, although the new result was not
  durably saved.
- IN_MEMORY accepts an unreachable `if False and result.outcome:` block mutating
  `report.success`.
- T005 catches direct `a.uuid = ...` anywhere, but misses equivalent mutation by
  `a.__dict__["uuid"]`, tuple target, or `setattr`; it also rejects a mutation
  performed only after a coherent `DeliveryAttempt` has already captured its
  values.

## Required reroll: TODO(#3280) comments and PR disclosure only

Insert concise comments at these precise analyzer seams. The comments should say
that branch/path merging, alternate assignment forms, and deeper identity/result
flow are intentionally deferred to #3280; they must not imply these analyzers
are complete semantic proofs.

1. `tests/architectural/test_project_store_boundary.py`
   - `_StoreVisitor._visit_function_scope()` immediately before its linear
     statement loop (currently around line 237).
   - `_StoreVisitor.visit_Assign()` / `visit_AnnAssign()` (around lines 283-290),
     noting that tuple targets and branch-state joins are tracked by #3280.
2. `tests/architectural/test_sync_writer_census.py`
   - `_import_bindings()` (around line 367), where module assignment aliases are
     invalidated but not propagated.
   - `_bindings_before_call()` before the `ast.walk()`/line-number collection
     (around lines 437-454), noting the absence of control-flow path merging.
3. `tests/architectural/test_egress_consent_boundary.py`
   - `_SinkFunctionAnalyzer._apply_binding()` (around lines 1570-1588), for tuple
     and other non-name targets.
   - `_SinkFunctionAnalyzer._inspect_block()` at its `ast.If` handling (around
     lines 1699-1720), for post-branch state joins.
   - `_LayoutWriteVisitor.visit_Assign()` (around lines 1996-2003), for alternate
     targets, and the visitor's lack of branch-state merging before
     `visit_Call()` (around lines 2013-2018).
   - `_durable_result_write()`, `_durable_file_result_write()`, and
     `_in_memory_result_write()` at their entry points (around lines 2213, 2247,
     and 2267), for column/value-flow, save ordering, and reachability limits.
4. `tests/sync/test_project_consent_incident_baseline.py`
   - `_attempt_context_is_coherent()` before `mutated_attributes` is assembled
     (around lines 310-317), for alternate attribute mutation forms and temporal
     ordering.

Use the literal form `# TODO(#3280): ...` so the source is searchable. The
eventual PR description must link #3280 and state that WP01 proves the enumerated
incident controls and exact mutation specimens, while general path-sensitive
Python analysis is follow-up scope. No new tests or analyzer changes are required
by this review.

## Independent commands and results

- Default-collector adversarial replay:
  `PYTHONPATH=src .venv/bin/python - <<'PY' ... PY`
  using reviewer-owned `TemporaryDirectory` source roots and the public/default
  `scan_store_sites`, `scan_grant_paths`, `_scan_project_sinks`,
  `_scan_layout_writers`, `_has_semantic_result_write`, and
  `mutation_violations` entry points. Exact closures and #3280 variants are
  recorded above.
- Focused warning-strict command:
  `PWHEADLESS=1 .venv/bin/python -m pytest -q tests/architectural/test_project_store_boundary.py tests/architectural/test_sync_writer_census.py tests/architectural/test_egress_consent_boundary.py tests/sync/test_project_consent_incident_baseline.py -W error`
  → `62 passed, 2 xfailed`.
- Full 22-path WP01/#3030 warning-strict command from the runtime review contract
  → `350 passed, 2 xfailed`.
- Documentation metadata plus isolated lifecycle command
  → `678 passed`; only the accepted #3130/#3237
  `spec-kitty-sync-async-loop` pin was emitted.
- Strict focused mypy → `Success: no issues found in 4 source files`.
- Ruff check → `All checks passed`; Ruff format → `4 files already formatted`.
- `git diff --check kitty/mission-per-project-sync-consent-ledgers-01KZKMQZ..HEAD`
  → clean. Lane worktree remained clean.

## WP-level anti-pattern checklist under the HiC-approved acceptance envelope

1. **Dead code — PASS**: no production code was added; the production store
   classification now has an exact one-item dead floor and traced live floor.
2. **Synthetic-fixture test — PASS**: production positive controls exercise live
   journal, transport, and ledger seams, and every agreed incident mutant bites.
   Generalized mutation forms are explicitly deferred to #3280.
3. **Silent empty return — N/A**: no production path was added.
4. **FR coverage — PASS WITH DEFERRED LIMIT**: the enumerated WP01 census and exact
   FR-023/FR-026/FR-029 mutations are covered; general path-sensitive completeness
   is disclosed and owned by #3280 per HiC ruling.
5. **Frozen surface — PASS**: no mission contract or production source changed.
6. **Locked decision — PASS**: ADR, UUID layout, #3030 supersession, and retained
   MUST/MUST NOT egress decisions remain aligned.
7. **Shared-file ownership — PASS**: all changed files are WP01-owned; no shared
   lane conflict exists.
8. **Production fragility — N/A**: no production raise or handler was added.

## Dependency impact

WP02 remains mechanically blocked only until this traceability-only reroll is
reviewed. #3280 owns the deferred analyzer work; WP02 must not silently widen
WP01's bounded evidence claims, but it is not required to wait for #3280 unless
its own implementation introduces one of the documented alias/control-flow
forms.
