---
affected_files: []
cycle_number: 1
mission_slug: fsm-write-path-integrity-01M1TZV6
reproduction_command:
reviewed_at: '2026-09-06T13:13:50Z'
reviewer_agent: user
wp_id: WP02
---

# WP02 review feedback — round 1

**Mission**: `fsm-write-path-integrity-01M1TZV6` · **WP**: WP02 · **Reviewer**: claude-fable-5-1 (reviewer-renata) · **Date**: 2026-09-06
**Reviewed**: lane-b `aaf65f7f4` + `8768aa0d7` against base `kitty/mission-fsm-write-path-integrity-01M1TZV6`

**Verdict: changes requested** — one major finding (a live CI gate regresses on the lane), two minors, two informational notes. The substance of the WP is sound; see "What passed" at the bottom. Fix F1 (one `ruff format` invocation), address F2, re-commit, and resubmit.

## Findings

### F1 — `ruff format --check .` architectural gate is red on the lane (major)

- **Where**: `src/specify_cli/status/emit.py:890-892` (the `annotations` list comprehension in `emit_status_transition_batch`) and `tests/status/test_transition_pipeline.py:334-340` (the `poisoned = ast.parse(...)` literal in `test_ast_pins_are_non_vacuous`).
- **What is wrong**: `tests/architectural/test_ruff_format_enforcement.py::test_ruff_format_check_is_clean_on_whole_repo` FAILS on lane-b (`2 files would be reformatted, 1532 files already formatted`). It is green on the base: base `emit.py` is formatted (verified via `git show <base>:… | ruff format --check --stdin-filename`), `test_transition_pipeline.py` is a new file, and `tests/status/test_emit.py` is in the `[tool.ruff.format].exclude` ratchet (`pyproject.toml:2813`) so its pre-existing drift does not count. Both hunks are introduced by this WP. The gate is enforced in CI (`.github/workflows/ci-quality.yml:32`, `uv run --frozen ruff format --check .`) and inside `make test-full`; issue #473/#558 makes it explicitly "enforced, not advisory". CLAUDE.md: new code must pass ruff with zero issues. DIRECTIVE_030.
- **What satisfies it**: `.venv/bin/ruff format src/specify_cli/status/emit.py tests/status/test_transition_pipeline.py` (repo `line-length = 164`; both hunks collapse to one line), then `.venv/bin/pytest tests/architectural/test_ruff_format_enforcement.py -q` ⇒ 2 passed. Re-run ruff/mypy on the two files afterwards (no semantic change expected).

### F2 — Flaky assertion on ULID sort order in the D-3 pin (minor)

- **Where**: `tests/status/test_emit.py:2137` — `assert stream.annotations[0].event_id > events[0].event_id` in `TestBatchShellLock::test_batch_annotation_shares_its_transition_timestamp`. Same claim in prose at `src/specify_cli/status/transition_pipeline.py:288-289` ("ULID order: event first") and design note §6 D-3 ("ULID order (event < annotation) … unchanged").
- **What is wrong**: `_generate_ulid` uses python-ulid 3.1.0 `ULID()`, which is random within a millisecond, not monotonic. Measured on the exact mint path (`build_status_event` then `_annotation_for_request` with the same `at`): the annotation ULID sorts BEFORE its event in 5/20000 runs. The assertion will therefore go red roughly once per few thousand CI runs — a correctness flake by construction (docs/development/testing/testing-flakiness.md: fix at the root, never retry-to-green). The property is also not load-bearing: `spec_kitty_events.diary.reduce_parsed` folds annotations in a dedicated post-transition partition pass ("NOT a timestamp-interleaved single pass"; step 4), and every `(at, event_id)` sort in the tree (`diary.py` step 2, `reducer.py:80`, `_should_apply_event`) compares transitions with transitions only. So D-3 is benign for reduction — the design note's conclusion stands, its stated reason does not.
- **What satisfies it**: delete the `event_id >` assertion (tactic `delete-the-assertion-not-the-test`); keep the `at` equality and the snapshot-lane assertions, which are the actual D-3 pin. Optionally replace it with the durable ordering fact — the annotation row is appended after all transition rows (`[*events, *annotations]`, `emit.py:893`), i.e. `stream.annotations` is non-empty and the reducer applies it post-transition. Reword the pipeline comment at `transition_pipeline.py:288-289` to "minted after the event" (mint order, not sort order) and amend D-3 in the design note to cite the reducer's partition fold rather than ULID order.

### F3 — Lock-key split with `emit_inner_state_changed` (informational; merge coordination, not a WP02 defect)

- `emit.py:973` (`emit_inner_state_changed`) still locks on `mission_slug` while both transition doors now lock on `feature_dir.name` (FR-004). WP01's T006 Activity Log claims the corresponding hunk at `emit.py:1013` on lane-a, so the two lanes converge at merge; both lanes touch `emit.py`, so expect a textual conflict. Also: WP01's `tests/status/test_writer_serialization.py` marks the batch door `xfail(strict=True, reason="FR-018 lands in WP02")` — once lane-b's FR-018 lock lands alongside lane-a it will XPASS and fail strict; whichever lane merges second must flip it. Not verified here (lane-a is not on this branch).

### F4 — NFR-004 pin scope (informational)

- `_ReadCounters` counts `_store.read_events` only. The `in_progress→for_review` evidence gate still performs a second full read through `_store.read_event_stream` (`emit.py:380`, `_infer_implementation_evidence`). That read exists on the base too and is outside NFR-004's derive-read scope, so nothing to change; recording it so WP06's delegation-equivalence work does not mistake it for a regression.

## What passed (verified, not inferred)

1. **Pipeline verbatim** — diffed `transition_pipeline.py::prepare_transition` + `_infer_review_gates` + `_annotation_for_request` by eye against `coordination/status_transition.py:842-961` (still present on the branch): TypeError guard, alias-resolve, workspace-context default, both gate conditions (`not force and in_progress→for_review`; `evidence is None and in_progress→for_review`), collapse arm (returns instruction, does not mirror — by design), `_build_done_evidence`, identical `GuardContext`, one `validate_transition`, `build_status_event` with `reason_source`/`policy_metadata`/`review_result`/`mission_id`. Only the D-1..D-5 divergences differ, all recorded.
2. **Purity/layering** — independent AST walk: no `coordination`/`subprocess` imports, no `open`/lock/append/materialize/`write_frontmatter`/`_mirror_phase1_frontmatter_lane` calls; importing the module loads zero `specify_cli.coordination.*` modules. `# noqa: ARG001` on `readiness` is narrow, justified inline, and non-vacuous (removing it triggers ARG001). No `# type: ignore` anywhere in the diff.
3. **Flat shell** — lock → `_load_mission_id` → derive once → `prepare_transition` → collapse-or-persist (append → materialize → mirror) → release → fan-out; lock keyed `canonical_feature_dir.name` (base: `mission_slug`); public signature byte-identical to the base plus keyword-only `fan_out: bool = True`. `_mirror_phase1_frontmatter_lane` remains the tree's only `write_frontmatter` of `lane` (grep + `test_2093_authority_invariant.py` green).
4. **Batch door** — identity checks for every member before the lock (NFR-001), then ONE `feature_status_lock` around derive → `_prepare_batch` (from_lane chained in memory) → single `append_event_stream_atomic_verified` → materialize → mirrors; fan-out after release; all-or-nothing pinned (`test_batch_mid_sequence_refusal_persists_nothing`); base `# noqa: C901` removed and C901 clean.
5. **NFR-004** — `test_emit_reads_log_once` / `test_batch_emit_reads_log_once_for_the_whole_batch`: derive == 1, `read_events` before append == 1.
6. **D-2** — the transactional `_prepare_event` never had the #946 skip, so the batch now matches both other doors; the only `src/` batch callers are the fallback arm at `coordination/status_transition.py:450/:458`, fed by `work_package_lifecycle.py` which always passes `workspace_context` for this edge. Pinned.
7. **Boy-scout mypy** — `_feature_status_lock_root` was red on the base (`emit.py:505: Returning Any from function declared to return "Path"`, verified by checking out the base file and running mypy); lane fix is a local annotation, no cast/ignore.
8. **Q6** — `spec-kitty agent decision verify --mission …` (main checkout) ⇒ `{"status": "clean", "marker_count": 1}` (only Q9 remains in `plan.md`); design note §3 records the decision.
9. **Scope** — diffstat is exactly `emit.py`, `transition_pipeline.py`, three owned test files; `coordination/status_transition.py`, `status/aggregate.py`, `status/__init__.py` untouched. Both commits carry the `Co-Authored-By` + `Claude-Session` trailers; Activity Log entry present on the main-checkout prompt copy.
10. **Dead code** — `prepare_transition` reached from both doors (`emit.py:747`, `:831`); every new helper has a caller (`_flat_subtasks_dir_resolver` / `_default_resolve_subtasks_dir` are passed/selected as values).

## Tests run (lane-b worktree, `.venv/bin/*`, foreground, no background processes left)

- `pytest tests/status tests/specify_cli/status tests/specify_cli/coordination -q -p no:cacheprovider -x` → **1853 passed, 1 skipped** (139.7 s)
- `pytest tests/architectural/test_status_module_boundary.py tests/architectural/test_2093_authority_invariant.py tests/architectural/test_no_legacy_status_emit_callers.py -q` → **15 passed**
- `pytest tests/specify_cli/cli/commands/agent tests/specify_cli/merge tests/specify_cli/lanes -q -p no:cacheprovider -x` → **2068 passed, 2 skipped, 2 xfailed** (487 s) — transactional callers unaffected
- `pytest tests/architectural/test_ruff_format_enforcement.py -q` → **1 failed, 1 passed** (F1)
- `ruff check` on the 5 changed files → clean; `ruff check --select C901 src/specify_cli/status` → clean; `ruff format --check` on the 5 files → **2 would reformat** (F1)
- `mypy src/specify_cli/status/transition_pipeline.py src/specify_cli/status/emit.py` → clean (base `emit.py` → 1 error, see item 7)
