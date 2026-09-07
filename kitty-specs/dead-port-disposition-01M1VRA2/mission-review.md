# Mission Review Report: dead-port-disposition-01M1VRA2

**Reviewer**: Reviewer Renata (profile `reviewer-renata`, claude) — post-merge mission review per `spec-kitty-mission-review`
**Date**: 2026-09-06
**Mission**: `dead-port-disposition-01M1VRA2` — Dead-Port Disposition: RuntimeEventEmitter Seam Consolidation (mission_id `01M1VRA2VWSET7NAR2M5Z6TZ5M`, mission_number 198)
**Baseline commit**: `3a4f92b4146831275aaa76a668d97c3a11d9d5a9` (merge-base with origin/main; `meta.json.baseline_merge_commit` = `9281b6de8` is the acceptance commit, not the code baseline)
**HEAD at review**: `8c90227f7ae14fb199e883e4031e95f8733049fb` on `feat/dead-port-disposition`
**WPs reviewed**: WP01..WP04 — all `done` (`spec-kitty agent tasks status --mission …`: 4/4 completed, 100%)
**Governing ADR**: `docs/adr/3.x/2026-09-06-2-runtime-event-emitter-disposition.md` (Accepted, Option 1) — untouched by this mission (`git diff 3a4f92b41..HEAD --stat -- docs/adr/` → empty)

Review history signal (`status.events.jsonl`): zero rejection cycles, zero forced moves, no `ReviewerSelfApproval`; every WP went `for_review → in_review` under `reviewer-renata` and `in_review → approved` by `user`. Three `RetrospectiveCaptureFailed`/`RetrospectiveCaptured` events close the log (see Retrospective Reminder). Evidence already on record and **not re-run** here (operator narrowing rule): post-merge `make test-fast` 1642 passed; runtime+next 1289 passed/1 skipped; specify_cli next+events+conformance+arch subset 455 passed/1 skipped; ruff clean; retired-surface scan 0 hits / 3882 added lines (`scratchpad/postmerge-validation.txt`); the four per-WP verdicts (`tasks/WP0*/review-cycle-1.md`).

---

## Gate Results

### Gate 1 — Contract tests
- Command: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 PWHEADLESS=1 timeout 900 .venv/bin/pytest tests/contract/ -q -p no:cacheprovider -n 4 --dist loadfile`
- Exit code: **0** (summary line `245 passed, 10 skipped, 1 warning in 20.40s`; the shell did not render `PIPESTATUS`, the pytest summary is the evidence)
- Result: **PASS**
- Notes: `tests/contract/test_identity_contract_matrix.py` (comment-only change by WP04, T024) collects and passes.

### Gate 2 — Architectural tests
- Command: `PWHEADLESS=1 timeout 900 .venv/bin/pytest tests/architectural/ -q -p no:cacheprovider -n 4 --dist loadfile`
- Exit code: **1** (`3 failed, 1789 passed, 2 skipped, 2 xfailed in 358.89s`)
- Result: **FAIL** (two mission-attributable failures, one pre-existing red that the mission widened)
- Classification (each of the three re-run on HEAD with `-n0`, then on the baseline `3a4f92b41` in a scratch worktree with `PYTHONPATH=<wt>/src`; worktree removed and pruned afterwards — `git worktree list` shows only the main checkout):

| Test | HEAD | Baseline `3a4f92b41` | Attribution |
|---|---|---|---|
| `test_ruff_format_enforcement.py::test_ruff_format_check_is_clean_on_whole_repo` | FAIL — `Would reformat: tests/runtime/test_bridge_decision_log_flush.py` (1 of 1532 files) | PASS | **This mission (WP02).** The new file was never run through `ruff format`; WP02's Activity Log records `ruff check` only. The three other mission-touched test files that `ruff format --check` would also reformat (`tests/next/test_internal_runtime_coverage.py`, `tests/runtime/test_bridge_decide_next.py`, `tests/specify_cli/events/test_decision_log.py`) are in the `[tool.ruff.format].exclude` debt ratchet (`pyproject.toml:2013,2123,2526`) and are not counted by the gate. |
| `test_arch_shard_marker_completeness.py::test_every_group_root_node_has_exactly_one_shard_marker[next]` | FAIL — all 5 nodes of `tests/runtime/test_bridge_decision_log_flush.py` carry `[]` shard markers | PASS | **This mission (WP02).** `tests/runtime` is a root of the `next` shard group and shard markers are applied at collection from the whole-file assignment table in `tests/_next_shard_map.py` (`tests/conftest.py:333-343`); the new file was not added to that table. CI impact: none today — `pytest.ini:66-68` records that "no live CI job selects the shard"; this is a registry-completeness gate, not a lost-coverage defect. |
| `test_golden_count_ban.py::test_convert_sites_do_not_exceed_frozen_baseline` | FAIL — `tests/architectural 15>14`, `tests/next 7>6`, `tests/runtime 11>10` | FAIL — `tests/architectural 15>14` only | **Pre-existing red (category 1) for `tests/architectural`; mission-widened for `tests/next` and `tests/runtime`.** The two new un-annotated `convert`-classified sites are `tests/next/test_internal_runtime_coverage.py:316` (`assert len(emit_methods) == 8`, WP01) and `tests/runtime/test_bridge_decision_log_flush.py:346` (`assert len(buffers) == 1`, WP02). Both are genuinely cardinality-is-contract (eight Protocol `emit_*` methods; exactly one buffer per gated advance) and want the `# golden-count: cardinality-is-contract` escape-hatch annotation (`test_golden_count_ban.py:110`). Ceilings: `tests/architectural/_golden_count_baseline.json`. |

All layer-rule, public-import, package-boundary, retired-subsystem, terminology and the mission's own `test_runtime_emitter_seam.py` tests **passed** inside this run (NFR-005 holds). None of the three failures is a runtime-behaviour defect; all three are fixable by file-local edits to test files (see Open items). Under the skill's rule (non-zero Gate 2 exit ⇒ hard fail, no exception path) this gate is recorded as FAIL.

### Gate 3 — Cross-repo E2E
- Command: not runnable — no `spec-kitty-end-to-end-testing` checkout exists on this machine.
- Result: **NOT RUN** (environmental; no `mission-exception.md` authored because no scenario was attempted).
- Assessment: I agree no new e2e scenario is owed. The mission is a runtime-internal consolidation; the only behaviour change is that `DecisionInputRequested` now reaches the local coordination-branch `decisions.events.jsonl` on two in-process paths. No hosted egress, no tracker/SaaS surface, no CLI contract, and no cross-repo behaviour is claimed in `spec.md` (C-002 explicitly keeps the seam no-op end to end; `register_runtime_emitter_factory` has zero callers under `src/` besides its definition and the `emitter.py` re-export shim). The four floor scenarios are not touched by this diff.

### Gate 4 — Issue Matrix
- File: `kitty-specs/dead-port-disposition-01M1VRA2/issue-matrix.json` — absent (no `issue-matrix.md` failover either).
- `grep -nE "#[0-9]{3,5}|issues/[0-9]+" spec.md` → no hits; `spec.md` references no GitHub issues.
- Result: **N/A** (matrix is only scaffolded for missions whose spec references issues). Process issue #3926 (merge teardown ordering) is a tooling defect filed by the orchestrator, not a mission requirement.

---

## FR Coverage Matrix

| FR ID | Description (brief) | WP Owner | Test File(s) | Test Adequacy | Finding |
|-------|---------------------|----------|--------------|---------------|---------|
| FR-001 | Exactly one `RuntimeEventEmitter` class under the runtime tree; duplicate removed | WP04 | `tests/architectural/test_runtime_emitter_seam.py::test_exactly_one_runtime_event_emitter_class` (S7); `::test_deleted_event_emitter_module_is_not_imported` | ADEQUATE — source-text scan of `src/runtime/next/`; independently: `grep -rn "^class RuntimeEventEmitter" src/runtime/next/` → 1 hit (`_internal_runtime/events.py:78`, the Protocol); `src/runtime/next/event_emitter.py` does not exist | — |
| FR-002 | Bridge obtains the seam from a factory returning `NullEmitter` by default and under the minimal-import gate | WP01, WP03 | `tests/next/test_internal_runtime_coverage.py` S1–S4 (`test_factory_returns_null_emitter_by_default`, `_honors_registered_factory`, `_reset_restores_default`, `_minimal_import_gate_wins[1,true,yes]`, `_gate_off_value_does_not_shadow_registered_factory`); guard S8 `test_bridge_obtains_seam_only_through_factory` | ADEQUATE — S2 registers a factory that raises `AssertionError` if called and toggles the env with `monkeypatch.setenv`, which only works because the gate is read at call time (`events.py:229`); bridge call sites `runtime_bridge.py:1552`, `:2742` verified | — |
| FR-003 | Constructor promoted as `for_mission`; `for_feature` removed, no alias | WP01, WP03 | `test_internal_runtime_coverage.py::test_null_emitter_for_mission_not_on_protocol` (asserts `classmethods == {"for_mission"}`), `::test_for_mission_resolves_mission_id_from_meta`, `::test_for_mission_degrades_on_corrupt_meta` | ADEQUATE — `grep -rn for_feature src/ tests/` returns only unrelated pre-existing names (`get_mission_for_feature`, `_repo_root_for_feature`, …); zero emitter-scoped hits | — |
| FR-004 | Snapshot seeding on the null emitter (no-op) | WP01 | `test_internal_runtime_coverage.py::test_null_emitter_seed_and_emits_never_raise` (S6); bridge seed sites `runtime_bridge.py:1614`, `:2747` exercised by `tests/next/test_runtime_bridge_unit.py` / `test_runtime_bridge_composition.py` fixtures now using bare `NullEmitter()` | ADEQUATE | — |
| FR-005 | Strict-policy `decision_required` request reaches the decision log after gate pass | WP02 | `tests/runtime/test_bridge_decision_log_flush.py::test_strict_policy_decision_required_reaches_decision_log` (F1) | ADEQUATE — drives the **real** `_dn_decision_materialize` with a real `_BufferingRuntimeEmitter` (spied only in F4) and a **real** `DecisionGitLog` writing a real `decisions.events.jsonl` (only `safe_commit` is patched); only `runtime_next_step` is faked. Reverting `:2190` to `flush(ctx.sync_emitter)` makes the count assertion fail `0 == 1` (WP02 reviewer reproduced the red). Also asserts F5 order on `inner` and that the plain seam receives nothing. | — |
| FR-006 | Composition-path request reaches the decision log | WP02 | `::test_composition_dispatch_decision_required_reaches_decision_log` (F2) | ADEQUATE for the bridge argument (asserts `seen["emitter"] is h.ctx.emitter_for_engine` — a real `DecisionGitLog` — and 1 log line). PARTIAL for helper integration: `_advance_run_state_after_composition` is replaced by a spy, so the real `advance_run_state_after_composition → _seed_emitter → DecisionGitLog.seed_from_snapshot` chain is not exercised end-to-end anywhere (see RISK-1). | RISK-1 |
| FR-007 | Refused terminal gate writes nothing; rollback clean | WP02 | `::test_strict_policy_refused_terminal_gate_writes_nothing` (F3) | ADEQUATE — real gate path with `_run_retrospective_learning_capture` raising; asserts 0 log lines, rollback args, no `emit_mission_run_completed` on any sink | — |
| FR-008 | Exactly-once flush | WP02 | `::test_gated_flush_does_not_duplicate` (F4) + F1 count | ADEQUATE — re-flushing the one-shot buffer into the log keeps the count at 1 | — |
| FR-009 | Seam docstring + two conformance comments point at the factory/registry and at `status/adapters.py` | WP01, WP04 | Docstring `events.py:172-195` (names `specify_cli.status.adapters.ensure_zeitgeist_moment_handlers` as the live seam and `register_runtime_emitter_factory` as the E3 point); comments `tests/status/test_producer_conformance.py:11-15`, `tests/contract/test_identity_contract_matrix.py:34-37`. Guard regex `_DELETED_MODULE_IMPORT_RE` scans source text incl. comments, so a reverted comment naming `runtime.next.event_emitter` fails S7. | ADEQUATE (documentation requirement, verified by inspection; regression-guarded by the text scan) | — |
| FR-010 | Last live importer updated | WP04 | `tests/specify_cli/events/test_decision_log_coord.py:17` now imports the Protocol from `_internal_runtime.events`; file collects and passes (63 passed in my direct run of the four mission test files) | ADEQUATE | — |
| FR-011 | CHANGELOG entry under Unreleased | WP04 | `docs/changelog/CHANGELOG.md:22` (one `### Fixed` entry); docs lint 35 passed per WP04 | ADEQUATE — disclosure text matches observable behaviour (see §Invisible holes) | — |

**Legend**: ADEQUATE = test constrains the required behavior; PARTIAL = test exists but does not reach the production path end-to-end; MISSING = no test found; FALSE_POSITIVE = test passes even when implementation is deleted.

**NFRs**: NFR-001 red-first — on record (WP02 Activity Log + reviewer reproduction: F1 `assert 0 == 1`, F2 `is DecisionGitLog` + seed `AttributeError`; not re-run). NFR-002 — on record (1289 + 455). NFR-003 — **NOT MET**, see DRIFT-1. NFR-004 — F4. NFR-005 — layer rules green inside Gate 2; `events.py` imports `specify_cli.core.env.is_truthy` and `specify_cli.mission_metadata.resolve_mission_identity`, both already on the runtime outbound ledger (R-5; `_internal_runtime/planner.py:46` precedent). NFR-006 — `git diff 3a4f92b41..HEAD -- src/ tests/ | grep '^+' | grep -i feature | grep -v feature_dir` → empty. NFR-007 — `ruff check` on all mission source/test files: clean; `mypy` on `events.py`, `emitter.py`, `decision_log.py`: 0 errors; `runtime_bridge_engine.py`: 8 pre-existing `call-arg` errors at `:158,:186,:216,:268` (payload `mission_id`/`mission_slug`), identical count base→HEAD per WP03 (category 1, not this mission's).

**ADR Confirmation (1)–(4) on the merged tree**
1. `grep -rn "^class RuntimeEventEmitter" src/runtime/next/` → exactly `src/runtime/next/_internal_runtime/events.py:78` ✔
2. `grep -n "runtime_emitter_for_mission(" src/runtime/next/runtime_bridge.py` → `:1552`, `:2742`; factory default path returns `NullEmitter.for_mission(...)` (`events.py:229-241`); `NullEmitter.for_mission` (`:127-140`) and `NullEmitter.seed_from_snapshot` (`:142-144`) present; bridge seed sites `:1614`, `:2747` intact ✔
3. `PWHEADLESS=1 .venv/bin/pytest tests/runtime/test_bridge_decision_log_flush.py tests/architectural/test_runtime_emitter_seam.py tests/specify_cli/events/test_decision_log.py tests/specify_cli/events/test_decision_log_coord.py -n0` → `63 passed`, exit 0 — F1 (strict-policy request appended after flush), F2 (composition path), F3 (refused gate, no write) all present and green ✔
4. Bridge-parity and producer-conformance green on record (1289 passed runtime+next; 455 passed incl. `test_producer_conformance.py`, `test_identity_contract_matrix.py`; Gate 1 here 245 passed) ✔

---

## Drift Findings

### DRIFT-1: NFR-003 (net LOC decrease) not met; governing ADR now carries a false consequence with no tracked follow-up

**Type**: NFR-MISS + deferred-item documentation gap
**Severity**: MEDIUM
**Spec reference**: NFR-003; ADR §Consequences/Positive ("Net LOC still drops (~88 LOC …)")
**Evidence**:
- `git diff 3a4f92b41..HEAD --numstat -- src/runtime/next/` → `+161 −105 net=+56` (my computation matches the spec's recorded deviation).
- `spec.md` NFR-003 row: "Not met — deviation recorded 2026-09-06 … ADR consequence text to be corrected in a follow-up."
- `gh issue list -R spec-kitty/EXPERIMENTAL-spec-kitty --search "2026-09-06-2 OR NFR-003 OR \"net LOC\" OR dead-port" --state all` → no matching issue; `--search emitter` → none referencing this ADR. The only records of the deferral are `spec.md` and the PR body (`scratchpad/pr3921-body.md:54`).

**Analysis**: The intent behind NFR-003 (one seam class, no collision, no dead duplicate) is met and the +56 is the factory/registry/docstring the ADR itself mandates, so the LOC miss is not a code defect. The drift is governance: the accepted ADR states a consequence that is now false, and the promised correction has no issue handle — per the skill, an undocumented deferral is a silent hole. Recommend filing a follow-up issue (title e.g. "ADR 2026-09-06-2: correct 'net LOC still drops' consequence; consolidation is +56 under src/runtime/next") and amending the ADR's Consequences/Positive bullet; the ADR's Decision and Confirmation sections need no change.

### DRIFT-2: Mission record inconsistencies from the manual merge repair

**Type**: process/record drift (not code)
**Severity**: LOW
**Spec reference**: n/a (mission identity model, CLAUDE.md §Mission Identity)
**Evidence**:
- `meta.json:35` `"mission_number": 198` (commit `8c90227f7`, hand-propagated via the canonical writer after #3926); `status.json:5` `"mission_number": ""`; `retrospective.yaml:4` `mission_number:` (empty).
- Working tree is **not clean** at HEAD: `git status --short` → ` M kitty-specs/dead-port-disposition-01M1VRA2/status.events.jsonl` — one uncommitted appended line, `type: RetrospectiveCaptured`, `at: 2026-09-06T20:57:21`, actor `spec-kitty retrospect` (matches `retrospective.yaml.created_at`; predates this review session by ~2.5 h, so it is not a side-effect of my read-only commands). Commit `0956bbe1a` recorded `retrospective.yaml` but not the event line; the two earlier `RetrospectiveCaptureFailed` lines were committed (`3e3e0762f`, `fd8551bdf`).

**Analysis**: `mission_number` is display-only and never used for lookup (CLAUDE.md), so nothing observable in the code changes; but the mission's own artefacts now disagree, and the `RetrospectiveCaptured` event — the record that the merge-time capture failure was remediated — is not in git. The orchestrator commits: the event line should land, and `status.json`/`retrospective.yaml` should either be regenerated or the discrepancy noted.

---

## Risk Findings

### RISK-1: The composition-path seeding chain is not exercised end-to-end

**Type**: CROSS-WP-INTEGRATION (WP02 `DecisionGitLog.seed_from_snapshot` × WP03 `_seed_emitter`)
**Severity**: LOW
**Location**: `src/runtime/next/runtime_bridge_engine.py:312-322` (`_seed_emitter`), `:357`; `src/specify_cli/events/decision_log.py:192-196`
**Trigger condition**: a future registered producer whose factory product lacks `seed_from_snapshot`, or a future edit that changes which emitter the real helper seeds/emits into.

**Analysis**: F2 replaces `_advance_run_state_after_composition` with a spy that itself calls `seed_from_snapshot` and `emit_decision_input_requested` on whatever it is handed. `_seed_emitter` is covered only by `tests/runtime/test_bridge_decide_next.py::test_seed_emitter_*` (SimpleNamespace / `MagicMock(spec=Protocol)`), and `DecisionGitLog.seed_from_snapshot` by `MagicMock(spec=NullEmitter)`. No test runs the real helper against a real `DecisionGitLog`. Consequence for the "delete the implementation" probe: deleting `_seed_emitter` and restoring the direct `sync_emitter.seed_from_snapshot(snapshot)` leaves every test green, because all three live products (`NullEmitter`, `DecisionGitLog`, `_BufferingRuntimeEmitter`) carry the method — `_seed_emitter` is load-bearing only for Protocol-only products, of which none exist (no live producer). Not a delivery gap for FR-006 (the bridge-argument fix is what the FR requires and F2 constrains it), but the integration seam between WP02's and WP03's tolerance layers is proven only by composition, not by a test. A one-test follow-up (real helper, real `DecisionGitLog` over `NullEmitter`, assert one log line) would close it.

### RISK-2: Three stacked silent-tolerance layers around seeding; registry accepts an unvalidated product

**Type**: ERROR-PATH
**Severity**: LOW
**Location**: `runtime_bridge.py:1611-1616` (`except Exception: current_step_id = None`, pre-existing), `decision_log.py:192-196`, `runtime_bridge_engine.py:319-322`, `events.py:200-209` (`register_runtime_emitter_factory` stores any callable; `runtime_emitter_for_mission` returns its product unmodified, S3)
**Trigger condition**: E3 registers a producer that misnames/omits `seed_from_snapshot` or does not satisfy the Protocol.

**Analysis**: By contract (`contracts/emitter-seam.md` §Registration: product *should* provide seeding; bridge tolerates absence) this is intended, and the producer-conformance test is the designed net. The residual risk is that a mis-shaped producer degrades to "no seeding, no error" at three points and to `AttributeError` at emit time only when the engine first emits. Acceptable for a mission that wires no producer; worth a one-line note in the E3 work item that the registry performs no conformance check.

### RISK-3: Text-only architectural guard is evadable; `_THIS_FILE` self-exclusion is benign

**Type**: BOUNDARY-CONDITION
**Severity**: LOW
**Location**: `tests/architectural/test_runtime_emitter_seam.py:39,44,83`
**Trigger condition**: a future bridge edit that aliases (`plain = ctx.sync_emitter; buffer.flush(plain)`), adds whitespace, or constructs `NullEmitter(` directly (S8's needle is only `"RuntimeEventEmitter("`).

**Analysis**: F7/S8 are substring checks and cannot see aliasing; the by-construction closure for the defect class is really F1/F2 (behavioural), which the guard complements. The `_THIS_FILE` exclusion exists because the guard's own docstring names the deleted module; it creates no material blind spot — S7's class scan is rooted at `src/runtime/next/`, and the import scan's roots are `src/` and `tests/`, so the only unscanned file is the guard itself, which defines no seam class. `.venv` is excluded by path part; `.worktrees/` is not under either root. Verified the negative check on record (WP04: scratch bridge copy with both bypasses reintroduced fails at `:2190`/`:1978`).

### RISK-4: Behaviour-change blast radius on the strict-gated path is a git commit inside `next`

**Type**: BOUNDARY-CONDITION (disclosed behaviour change, assessed not flagged)
**Severity**: LOW (informational)
**Location**: `runtime_bridge.py:2190` → `DecisionGitLog.emit_decision_input_requested` → `_append_decision_event` (`decision_log.py:230-243`) → `_trigger_commit` (`:244-268`)
**Trigger condition**: strict retrospective policy (`enabled ∧ before_completion ∧ block`) and a `decision_required` advance; or any composition-dispatch `decision_required`.

**Analysis**: Every such advance now appends to `decisions.events.jsonl` and calls `safe_commit` on the coordination branch where previously nothing was written. Both failure modes are caught and logged at WARNING (`_append_decision_event` catches `Exception`; `_trigger_commit` catches `SafeCommitError`), matching the spec's assumption ("commit-failure handling … adequate and not changed"). On coord-less topologies where `_wrap_with_decision_git_log` falls back to the plain emitter (`runtime_bridge.py:383-395`), `emitter_for_engine is sync_emitter` and the flush target is byte-for-byte what it was — no change. Re-poll of an already-pending decision is guarded in the engine adapter (`_emit_decision_required` early-returns, `runtime_bridge_engine.py:200-202`), so F4's exactly-once holds across polls. F5: `DecisionGitLog` implements all eight `emit_*` (`decision_log.py:147-190`), so `_BufferingRuntimeEmitter.flush`'s "skip missing target methods" branch (`runtime_bridge_retrospective.py:143-146`) never fires for the wrap; non-decision moments reach `inner` in original order exactly as on the non-gated path (F1 asserts the order).

### Cross-WP integration check (the thing no WP review saw)

`git diff 3a4f92b41..HEAD -- src/runtime/next/runtime_bridge.py` is exactly the union of WP02 and WP03: one import line (`:195`, now also importing the Protocol name so annotations at `:293/:1215/:1472` bind to it), two factory construction sites (`:1552`, `:2742`, keyword args unchanged), two `emitter_for_engine` fixes (`:1978`, `:2190`) and their comment blocks. Nothing from either WP was lost in the squash merge; `git diff -- src/specify_cli/status/adapters.py` and `-- src/specify_cli/__init__.py` are empty (C-003; no version bump); the Protocol body is byte-identical (eight `emit_*`, `events.py:85-99`; the diff touches no `emit_*` line of the Protocol). Seeding semantics on the composition path are consistent across WP02/WP03: `_seed_emitter(DecisionGitLog)` → `DecisionGitLog.seed_from_snapshot` → `inner.seed_from_snapshot` (`NullEmitter` no-op); the inner is seeded once at bootstrap (`:1614`, directly) and once via the wrap in the helper — the same two seeds the pre-mission code performed on the same object, so no behaviour change. `runtime_emitter_for_mission` reads `SPEC_KITTY_SYNC_MINIMAL_IMPORT` at call time (`events.py:229`), as R-4 requires. `register_runtime_emitter_factory` is reachable from no import tail (`grep -rn register_runtime_emitter_factory src/` → definition and shim only) — no live producer, C-002 holds. The 15 test-site migrations were spot-checked by reading before/after: `test_bridge_decide_next.py:672` (`is ctx.sync_emitter` → `is ctx.emitter_for_engine`) is an intentional, declared inversion coupled to the `:1978` fix; `test_runtime_bridge_unit.py` (`LocalOnlyEmitter` subclass → bare `NullEmitter()`) and `test_runtime_bridge_blocked_paths.py` (`sync_cls.for_feature.return_value` → `sync_factory.return_value`) lose no assertion; the raising `seed_from_snapshot` sentinel in `test_bootstrap_defaults_current_step_id_to_none_when_snapshot_read_fails` is retained.

The post-merge "stale assertion" analyzer's flags on tests referencing `emit_*`/`seed_from_snapshot` as "renamed/removed in event_emitter.py" are **false positives**: the analyzer keyed on the deleted file's symbol set, but every one of those names lives on the Protocol (`events.py:85-99`), `NullEmitter` (`:142-167`), `DecisionGitLog` (`decision_log.py:147-196`) and `_BufferingRuntimeEmitter` (`runtime_bridge_retrospective.py:95-125`).

---

## Silent Failure Candidates

| Location | Condition | Silent result | Spec impact |
|----------|-----------|---------------|-------------|
| `src/runtime/next/_internal_runtime/events.py:135-138` (`NullEmitter.for_mission`) | `resolve_mission_identity` raises (`MissionMetaReadError` on corrupt `meta.json`, or any exception) | `mission_id = None` | None — S5 mandates it; `mission_id` is stored and never read (R-1); byte-identical tolerance to the deleted `for_feature`. The `# noqa: BLE001` carries an inline rationale and is the one suppression in the diff — acceptable per contract S5. |
| `src/specify_cli/events/decision_log.py:192-196` | inner sink lacks `seed_from_snapshot` | no-op | F6 mandates it; see RISK-2 |
| `src/runtime/next/runtime_bridge_engine.py:319-322` (`_seed_emitter`) | product lacks `seed_from_snapshot` | no seeding | contract "should"; see RISK-1/2 |
| `src/runtime/next/runtime_bridge_retrospective.py:143-146` (`flush`, pre-existing) | target lacks a buffered method | that event dropped | never fires for `DecisionGitLog` (all eight present); would fire for a mis-shaped future producer |
| `src/runtime/next/runtime_bridge.py:1611-1616` (pre-existing) | seed or snapshot read raises | `current_step_id = None` | pre-existing; unchanged |
| `src/specify_cli/events/decision_log.py:230-243`, `:244-268` (pre-existing) | append or `safe_commit` fails | WARNING log, event possibly unrecorded | spec Assumption 3 accepts this; now reachable from the strict-gated and composition paths (RISK-4) |

---

## Security Notes

| Finding | Location | Risk class | Recommendation |
|---------|----------|------------|----------------|
| No new subprocess, shell, path-composition, HTTP, credential or lock code in the diff (`git diff 3a4f92b41..HEAD -- src/ \| grep -n "subprocess\|shell=True\|Popen\|httpx\|requests\|open(\|token\|secret"` → only pre-existing context lines). The only new I/O is the pre-existing `meta.json` read inside `resolve_mission_identity` (now also called under the minimal-import gate, exactly as `for_feature` did) and the pre-existing `safe_commit` path newly reachable from two more call sites. `safe_commit` is invoked with `GuardCapability.STANDARD` (`decision_log.py:255`), so a protected destination is refused, not waived. | — | — | No security findings. |

---

## Final Verdict

**PASS WITH NOTES**

*Resolved 2026-09-07, same PR (maintainer landing pass on #3921):* the three Gate 2 blockers below were the sole reason this report originally read FAIL; all three are confirmed resolved on the current tip — `ruff format --check tests/runtime/test_bridge_decision_log_flush.py` reports "1 file already formatted"; `tests/_next_shard_map.py:119` carries the file; and both cardinality assertions (`tests/next/test_internal_runtime_coverage.py:377`, `tests/runtime/test_bridge_decision_log_flush.py:337`) carry `# golden-count: cardinality-is-contract`. The report's own text already said these edits would convert the verdict to PASS WITH NOTES, so the verdict is flipped here rather than left stale. DRIFT-1, DRIFT-2, and RISK-1 remain open per the original findings below.

### Verdict rationale

The delivery itself is sound: all eleven FRs trace spec → WP → test → code with adequate tests (F1/F3/F4 drive the real materialize path with a real `DecisionGitLog`; the seam contract S1–S8 is pinned by non-vacuous tests; the merged bridge is exactly the WP02 ∪ WP03 union); every ADR-BLOCKED boundary holds (no pure port deletion, constructor and seed capability survive on the seam, both flush bugs fixed not frozen, no live producer, `status/adapters.py` untouched, Protocol body unchanged, no `for_feature`, `docs/adr/` and `__init__.py` untouched); ADR Confirmation (1)–(4) each verify on the merged tree; no locked decision is violated; no security finding exists; Gate 1 passes. Gate 2 (architectural) originally exited non-zero with two failures this mission introduced and one it widened — `test_ruff_format_enforcement`, `test_arch_shard_marker_completeness[next]`, and `test_golden_count_ban` — none a runtime-behaviour defect and none touching `src/`; all three are now resolved (see above).

### Open items (non-blocking unless marked)

1. DRIFT-1: file a follow-up issue and amend ADR 2026-09-06-2 §Consequences/Positive ("Net LOC still drops") to record +56 under `src/runtime/next/`; the spec's NFR-003 row already records the deviation.
2. ~~DRIFT-2: commit the uncommitted `RetrospectiveCaptured` line in `kitty-specs/dead-port-disposition-01M1VRA2/status.events.jsonl` (working tree at HEAD is dirty); reconcile `status.json`/`retrospective.yaml` `mission_number` with `meta.json` (198) or note the discrepancy.~~ **Resolved 2026-09-07 (PR #3983):** the `RetrospectiveCaptured` line landed with the mission merge (`d6e8fe4238`), and `status.json` + `retrospective.yaml` now both carry `mission_number: 198`, matching `meta.json`.
3. RISK-1: consider one integration test running the real `advance_run_state_after_composition` against a real `DecisionGitLog` over `NullEmitter` (asserting one `DecisionInputRequested` line), so the WP02/WP03 seeding chain is proven by a test rather than by composition. Suitable as part of the E3 producer work.
4. RISK-2: note in the E3 work item that `register_runtime_emitter_factory` performs no Protocol-conformance check; the producer-conformance test is the intended net.
5. Category-1 pre-existing: 8 `mypy` `call-arg` errors in `runtime_bridge_engine.py:158,186,216,268` (payload `mission_id`/`mission_slug`), identical base→HEAD; not this mission's.

## Retrospective Reminder

Canonical post-merge sequence: **mission review → author or verify retrospective → surface findings**.

- The retrospective record for this mission exists at **`kitty-specs/dead-port-disposition-01M1VRA2/retrospective.yaml`** (113 lines, `provenance.kind: explicit_create`, `command: spec-kitty retrospect create`, `findings_status: has_findings`, 4 `helped` / 1 `not_helpful` / 0 gaps / 0 proposals). It was authored via `retrospect create` because the merge-time capture failed twice — `status.events.jsonl` carries two `RetrospectiveCaptureFailed` events at `20:55:12` and `20:55:15` (`remediation_hint`: "Run `spec-kitty agent retrospect synthesize --mission <slug>` to retry…"; the orchestrator attributes the failure to a stale module view) followed by the `RetrospectiveCaptured` event at `20:57:21` that is **still uncommitted** in the working tree (DRIFT-2 / open item 5).
- The skill's stated path `.kittify/missions/01M1VRA2VWSET7NAR2M5Z6TZ5M/retrospective.yaml` does **not** exist on this checkout; the record lives mission-side under `kitty-specs/`. Do not re-run `retrospect create` — the record is present; verify it, commit the event line, then surface findings:
  - `spec-kitty retrospect summary` (cross-mission aggregation; read-only)
  - `spec-kitty agent retrospect synthesize --mission dead-port-disposition-01M1VRA2` (inspect proposals; dry-run by default; `--apply` mutates)
- The record's `mission_number:` is empty because it was written before `8c90227f7` propagated 198 to `meta.json`; this does not affect the record's findings.

---

*Process hygiene*: all commands ran in the foreground; the two scratch worktrees used for baseline classification (`scratchpad/baseline-wt`, `baseline-wt2`) were removed and pruned (`git worktree list` → main checkout only); no repo file was modified by this review (the one dirty file, `status.events.jsonl`, was dirty before the session began — its uncommitted line is timestamped `20:57:21`).

---

## Orchestrator addendum (post-review remediation, 2026-09-06)

The three Gate 2 items that produced the FAIL verdict were fixed on the integration branch in commit `c028ef2a4`: `ruff format` on `tests/runtime/test_bridge_decision_log_flush.py`; the file registered in `tests/_next_shard_map.py`; golden-count escape-hatch annotations on `tests/next/test_internal_runtime_coverage.py` (emit_* count) and the flush test (buffer count). Re-run: `test_ruff_format_enforcement`, `test_arch_shard_marker_completeness`, the two mission test files → green. `test_golden_count_ban::test_convert_sites_do_not_exceed_frozen_baseline` still reports `tests/architectural: 15 > 14`; that count is identical on the baseline `3a4f92b41` (verified by the reviewer in a scratch worktree) and is a pre-existing red, not folded. Mission-caused Gate 2 failures after remediation: 0. Effective verdict: **PASS WITH NOTES** (DRIFT-1 NFR-003 and the LOW items remain open as follow-ups).
