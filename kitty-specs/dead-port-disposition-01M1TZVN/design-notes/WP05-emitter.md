# WP05 design note — RuntimeEventEmitter ADR execution (FR-012)

**Mission** `dead-port-disposition-01M1TZVN` · **Lane** `kitty/mission-dead-port-disposition-01M1TZVN-lane-c`
(shared with WP03; WP03 approved at `d18b0c98c`) · **HEAD** `ec77ba471` · **ADR**
`docs/adr/3.x/2026-09-06-2-runtime-event-emitter-disposition.md` (Accepted 2026-09-06, PR #3898; option 1
"rewire-ready consolidation") · **Decision** `DM-01M1VS1KMB4M0RXR66RWA2GAKC` (WP05 minted; supersedes OD7) ·
**Inputs** `research/emitter-adr-inputs.md` (FR-011, WP03), `design-notes/WP03-residue.md` §6 (orphan-row hand-off).
Intended landing spot: `kitty-specs/dead-port-disposition-01M1TZVN/design-notes/WP05-emitter-adr-execution.md`
(the lane gate refuses `kitty-specs/` commits; the operator copies it in at consolidation).

## 1. Commits (RED before GREEN, charter C-011)

| # | Hash | Kind | Scope |
|---|---|---|---|
| 0a | `dc7ced3b1` | merge | Step 0: lane-d (`82523b2ab`, WP04's deletion of `decision::derive_mission_state` / `evaluate_guards`) merged into lane-c — 3 files, 357 deletions, no conflict |
| 0b | `6584186a5` | chore | Step 0: the two orphaned `_WIDENED_SCOPE_GRANDFATHERED_470` rows pruned (`test_no_dead_symbols.py:3217-3218`, not the prompt's `~:3244`) |
| 1 | `53339201f` | RED | `tests/runtime/test_decision_flush_target.py` (3 pins) + `tests/runtime/test_emitter_seam_consolidation.py` (3 structural pins) — **5 failed / 1 passed** raw on the base, then `xfail(strict=True)` |
| 2 | `388b0b243` | GREEN (T019/T021/T022) | seam consolidation: `events.py` promotion + registry, bridge/engine retype + factory construction, `DecisionGitLog.seed_from_snapshot`, `event_emitter.py` deleted, 10 test files repointed, 3 structural pins flipped, 12 new seam tests |
| 3 | `ec77ba471` | GREEN (T020) | flush target → `ctx.emitter_for_engine` on both paths; the 2 behaviour pins flipped; the composition-dispatch kwarg pin re-pinned |

## 2. ADR clause → change → test

| ADR clause | Change | Test (nodeid) |
|---|---|---|
| **(a) rewire target + registry** — bridge depends on the Protocol and a factory, never a concrete import; factory returns `NullEmitter` by default and under `SPEC_KITTY_SYNC_MINIMAL_IMPORT`; E3 registers here, mirroring `status/adapters.py:364-365` | `_internal_runtime/events.py`: `runtime_event_emitter_for_mission(*, mission_dir, mission_slug, mission_type)` + `RuntimeEventEmitterRegistry` (`register` / `reset` / `registered`, `ClassVar` slot; nothing registered in-tree). `runtime_bridge.py:195` imports the Protocol + factory; `:1552` and `:2739` construct through the factory (`mission_dir=feature_dir`). `runtime_bridge_engine.py:80` `TYPE_CHECKING` import targets the Protocol (the 16 engine + 13 bridge annotation sites are retyped by that one line) | `test_emitter_seam_consolidation.py::test_factory_returns_null_emitter_by_default`, `::test_factory_returns_registered_producer_with_resolved_identity`, `::test_factory_ignores_registered_producer_under_minimal_import[1|true|yes]`, `::test_registry_reset_restores_the_null_default`, `::test_no_producer_is_registered_in_tree`, `::test_bridge_and_engine_bind_the_protocol_and_the_factory_only` |
| **(b) missing surface** — `for_mission` (identity resolution) and `seed_from_snapshot` promoted onto the seam; `for_feature` only as a transitional alias if the two sites cannot rename together | Protocol gains `seed_from_snapshot`; `NullEmitter` gains `mission_slug/mission_type/mission_id`, `for_mission` (ports the retired `for_feature`'s fail-open `resolve_mission_identity` try/except, plus an `isinstance(str)` narrow), and a no-op `seed_from_snapshot`. **No `for_feature` alias** — both construction sites renamed in the same change; new keyword is `mission_dir`. `DecisionGitLog.seed_from_snapshot` pass-through so the wrapper satisfies the full seam (see §4) | `::test_for_mission_resolves_identity_like_the_retired_for_feature` (ULID resolved; missing dir → `None`; corrupt `meta.json` → `None`), `::test_null_emitter_seed_from_snapshot_is_a_noop`, `::test_null_emitter_positional_correlation_id_is_preserved`, `::test_decision_git_log_passes_seed_through_to_inner` |
| **(c) flush target — fixed, not frozen**; red-first with a strict-policy `decision_required` fixture; composition bypass in scope; refusal keeps discarding | `runtime_bridge.py` `_dn_decision_materialize`: `buffer.flush(ctx.sync_emitter)` → `buffer.flush(ctx.emitter_for_engine)`; `_dn_composition_dispatch`: `sync_emitter=ctx.sync_emitter` → `sync_emitter=ctx.emitter_for_engine` (fix at the seam; adapter signature untouched) | `test_decision_flush_target.py::test_strict_gated_decision_required_advance_reaches_decision_git_log`, `::test_composition_dispatch_decision_required_reaches_decision_git_log` (both RED → GREEN, real `DecisionGitLog`), `::test_refused_terminal_gate_discards_buffer_without_a_decision_git_log_write` (GREEN before and after); `test_bridge_decide_next.py::test_composition_dispatch_advances_run_state_on_success` re-pinned from the bypass to the wrap |
| **(d) name collision** — delete the duplicate; one `RuntimeEventEmitter` | `git rm src/runtime/next/event_emitter.py` (102 LOC incl. WP03's docstring); its `# noqa: ARG002` sites are gone with it | `::test_exactly_one_runtime_event_emitter_class_under_runtime_next`, `::test_concrete_event_emitter_module_is_deleted`, `::test_no_live_importer_of_the_retired_concrete_module` (import statements + quoted patch targets; prose may still name the module as history) |
| **Confirmation (4)** — `_BufferingRuntimeEmitter` stays (C-006) | untouched; only its flush TARGET changed at the call site | `::test_buffering_runtime_emitter_is_retained`; `tests/runtime/test_bridge_retrospective.py` unchanged, green |
| **Confirmation (5)** — parity + producer-conformance stay green; comments point at the consolidated seam; the one live importer updated | `tests/runtime/_bridge_oracle.py` spies the factory (not `for_feature`); `test_side_effect_sinks_are_actually_reached` untouched and green (the `sync_emitter` sink is still populated: the `DecisionGitLog` wrap delegates every emit to the inner proxy); `tests/status/test_producer_conformance.py:11-15` and `tests/contract/test_identity_contract_matrix.py:33-37` docstrings name `runtime.next._internal_runtime.events` / `RuntimeEventEmitterRegistry`; `tests/specify_cli/events/test_decision_log_coord.py:17` imports the Protocol | `tests/runtime/test_bridge_parity.py` (in the 779-pass `tests/runtime` run), `tests/status/test_producer_conformance.py`, `tests/contract/test_identity_contract_matrix.py` (in the 439-pass gate run) |
| **Docstring correction** | superseded: the corrected module is deleted; the seam's truth now lives in the `events.py` module docstring (points E3 at the registry; names `status/adapters.py` as the *other*, already-live seam) | `::test_no_live_importer_of_the_retired_concrete_module` tolerates the historical mention |
| **NOT in scope** — no live producer; no `status/adapters.py` change | `git diff --stat` carries no `status/adapters.py` hunk; `RuntimeEventEmitterRegistry.registered()` is `None` on a fresh import | `::test_no_producer_is_registered_in_tree` |

## 3. Flush-target fix — evidence

Raw RED (before markers) on `dc7ced3b1`+prune, `.venv/bin/pytest tests/runtime/test_decision_flush_target.py tests/runtime/test_emitter_seam_consolidation.py -q -p no:cacheprovider` → **5 failed, 1 passed**:

```
test_strict_gated_decision_required_advance_reaches_decision_git_log
  AssertionError: the buffered DecisionInputRequested was flushed into the plain no-op
  sync_emitter instead of the DecisionGitLog-wrapped emitter_for_engine
  assert [] == ['DecisionInputRequested']
test_composition_dispatch_decision_required_reaches_decision_git_log
  AssertionError: Run-state advancement after composition failed for software-dev/tasks-outline:
  AttributeError: 'NullEmitter' object has no attribute 'seed_from_snapshot'
  (the plain ctx.sync_emitter reached the adapter -- the bypass, manifesting as the
  pre-consolidation NullEmitter's missing seed surface)
test_refused_terminal_gate_discards_buffer_without_a_decision_git_log_write PASSED
```

After `ec77ba471`: `tests/runtime/test_decision_flush_target.py …` → 219 passed, **0 xfailed** (the `xfail(strict=True)` markers are gone; a
regression now fails outright). The fixtures use a REAL `DecisionGitLog(repo_root=tmp, worktree_root=tmp, inner=NullEmitter())` as
`emitter_for_engine` and assert on `kitty-specs/042-mission/decisions.events.jsonl` — the file the operator reads back, not a spy.

**Behaviour change, called out explicitly:** under the strict retrospective gate (`timing=before_completion`, `failure_policy=block`) every
`decision_required` advance through `runtime_next_step` now durably records its `DecisionInputRequested` in `decisions.events.jsonl` (before:
silently dropped into the inner no-op). On the composition dispatch path decision events reach the `DecisionGitLog` wrap regardless of policy
(before: never). `DecisionGitLog.emit_decision_input_requested` appends without committing (the answer commits), so no new git commit is
introduced by the request leg. Rollback semantics preserved: the gate at `_dn_terminal_retrospective_gate` runs before the flush and the
buffer is one-shot; the refusal pin proves no file is written. No double-emit: on the gated path the engine wrote only into the buffer.

**Third seed site.** The ADR lists two `seed_from_snapshot` sites (`:1614`, `:2745`); `runtime_bridge_engine.py:344`
(`advance_run_state_after_composition`) is a third, on the composition path. Passing `emitter_for_engine` there means the `DecisionGitLog`
wrapper is seeded — hence the pass-through (§4).

## 4. Deviations from the contract / prompt (each with reason)

1. **`DecisionGitLog.seed_from_snapshot` added** (`src/specify_cli/events/decision_log.py`, not in the WP file map). Required by (b)+(c)
   together: once `seed_from_snapshot` is on the seam and the composition path receives the wrap, the adapter's seed at engine `:344`
   would `AttributeError` → EDGE-003 blocked Decision. `events/decision_log.py` is neither a Non-goal-2 surface nor one of the four shared
   files; the ADR's "NOT in scope" names only `status/adapters.py`. Pass-through to `inner`, no log write.
2. **15 test doubles repointed, not one.** The ADR named `test_decision_log_coord.py:17`; in fact `test_runtime_bridge_unit.py` ×4,
   `test_runtime_bridge_blocked_paths.py` ×4, `test_runtime_bridge_composition.py` ×1, `test_bridge_decide_next.py` ×5 and the parity
   oracle all patched `bridge.RuntimeEventEmitter.for_feature` / `rb.RuntimeEventEmitter`. Stale → re-pin to the factory (charter
   standing order 4). Applied by a scratch script asserting each exact pattern's count.
3. **`test_composition_dispatch_advances_run_state_on_success` re-pinned** — it asserted the bypass (`sync_emitter is ctx.sync_emitter`);
   now asserts the wrap and its distinctness from the inner.
4. **E3 hook shape: a registry class, not `register_runtime_event_emitter_factory()`.** A module-level `register_*` function with no
   `src/` caller is an offender of the widened dead-symbol walk (`test_no_public_symbol_in_all_is_unimported`, #470) and could only be
   rescued by a vacuous self-call at the module tail. `RuntimeEventEmitterRegistry` is rescued by the factory's genuine own-module use;
   its classmethods are not module-level names. It is deliberately not in `__all__` (strict caller-only semantics there).
   `RuntimeEventEmitterFactory` (public alias) is rescued the same way.
5. **`sync_emitter` parameter name KEPT (T021 decision).** The retype is one import line per module (the annotation text
   `RuntimeEventEmitter` is unchanged at all 29 sites), so no one-pass rename co-rides it. Renaming would touch the frozen
   `DecideNextContext` field, the parity oracle's `sync_emitter_calls` sink, the FR-012 compat delegate's keyword
   (`_advance_run_state_after_composition`, `contracts/compat-surface.md`) and 10 test files — a ~40-file vocabulary sweep dwarfing the
   ADR execution. The ADR does not mandate it; any future rename remains a single pass because none of the sites moved.
6. **No `for_feature` alias** — both construction sites renamed in the same change (ADR (b) condition met), so the Terminology-Canon
   exception was not needed. The new keyword is `mission_dir`.
7. **Structural seam pins landed in the RED commit; factory/registry behaviour tests in the GREEN commit.** The three structural pins are
   honestly RED on the base without import contortions; the factory tests cannot be RED without `getattr`-shaped imports that would then
   be rewritten, so they land with the helpers they cover (CLAUDE.md "every new helper needs tests in the same PR").
8. **`test_no_live_importer_of_the_retired_concrete_module` narrowed** from "any mention" to import statements + quoted patch targets after
   it flagged the new `events.py` docstring's historical mention — the pin's intent is *live bindings*; prose history stays allowed (same
   rationale as the terminology gate's `docs/adr/` exemption).
9. **Line drift recorded:** grandfathered rows at `test_no_dead_symbols.py:3217-3218` (prompt: `~:3244-3245`); emitter anchors at
   `event_emitter.py:37/:57/:74` (WP03 docstring shift) — now moot, file deleted.
10. **Ruff `--force-exclude` skipped** `runtime_bridge.py`, `runtime_bridge_engine.py`, `_bridge_oracle.py`, `test_bridge_decide_next.py`
    and the other formatter-debt files ("5 files already formatted" for 15 inputs) — expected; the two NEW test files were `ruff format`ed.
11. **No `kitty-specs/` writes from the lane** — this note is delivered here for the operator to copy in; `research/emitter-adr-inputs.md`'s
    "executed by WP05" marker is likewise an operator copy-in (its lane copy in `wp03-c-planning-artifacts/` already carries "Execution of the
    ADR is WP05").

## 5. Step-0 prune evidence (campsite item from WP03 §6 / WP04)

| Where | Command | Result |
|---|---|---|
| scratch worktree at `d18b0c98c` (no lane-d), rows pruned | `.venv/bin/pytest tests/architectural/test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported -q -p no:cacheprovider` | **1 failed** — `- runtime.next.decision::derive_mission_state` / `- runtime.next.decision::evaluate_guards` listed as offenders (worktree removed afterwards) |
| lane-c at `dc7ced3b1` (lane-d merged), rows still present | same node | 1 passed (the set has no staleness ratchet — silent debris) |
| lane-c at `6584186a5` (merged + pruned) | `.venv/bin/pytest tests/architectural/test_no_dead_symbols.py -q -p no:cacheprovider` | **32 passed** |

## 6. Verification table (all foreground, `timeout 600`, `-p no:cacheprovider`, max `-n 3 --dist loadfile`, from inside the lane)

| After | Command | Result |
|---|---|---|
| RED (`53339201f`) | `.venv/bin/pytest tests/runtime/test_decision_flush_target.py tests/runtime/test_emitter_seam_consolidation.py -q` | 1 passed, 5 xfailed (raw before markers: 5 failed, 1 passed) |
| `388b0b243` | `.venv/bin/pytest tests/runtime/test_emitter_seam_consolidation.py tests/runtime/test_decision_flush_target.py tests/runtime/test_bridge_decide_next.py tests/runtime/test_bridge_engine.py tests/runtime/test_bridge_retrospective.py tests/next/test_runtime_bridge_unit.py tests/next/test_runtime_bridge_blocked_paths.py tests/next/test_internal_runtime_coverage.py tests/next/test_mission_run_back_reference.py tests/specify_cli/next/test_runtime_bridge_composition.py tests/specify_cli/events tests/status/test_producer_conformance.py tests/contract/test_identity_contract_matrix.py -q -n 3 --dist loadfile` | 451 passed, 2 xfailed, 1 failed → the scan narrowing (§4.8) → consolidation file **16 passed** |
| `388b0b243` | `.venv/bin/pytest tests/architectural/test_layer_rules.py tests/architectural/test_mission_runtime_surface.py tests/architectural/test_no_legacy_terminology.py tests/architectural/test_shared_package_boundary.py tests/architectural/test_cold_import_status_boundary.py tests/architectural/test_runtime_charter_doctrine_boundary.py tests/architectural/test_ruff_format_enforcement.py -q -n 3 --dist loadfile` | **131 passed** (C-007: `test_runtime_ledger_has_no_stale_entries` green — `mission_metadata` keeps live edges from `runtime_bridge_identity.py`, `runtime_bridge_retrospective.py`, `planner.py` and now `events.py`; no ledger edit) |
| `388b0b243` | `.venv/bin/pytest tests/runtime -q -n 3 --dist loadfile` | 777 passed, 1 skipped, 2 xfailed |
| `388b0b243` | `.venv/bin/pytest tests/next tests/specify_cli/next -q -n 3 --dist loadfile` | 755 passed, 1 skipped |
| `388b0b243` | `.venv/bin/pytest tests/architectural/test_no_dead_symbols.py -q` | 32 passed (new public names survive the widened walk) |
| `ec77ba471` | `.venv/bin/pytest tests/runtime/test_decision_flush_target.py tests/runtime/test_bridge_decide_next.py tests/runtime/test_bridge_retrospective.py tests/runtime/test_bridge_parity.py tests/runtime/test_bridge_composition.py tests/runtime/test_emitter_seam_consolidation.py tests/specify_cli/next/test_runtime_bridge_composition.py tests/integration/retrospective -q -n 3 --dist loadfile` | **219 passed, 0 xfailed** |
| `ec77ba471` | `.venv/bin/pytest tests/next tests/specify_cli/next -q -n 3 --dist loadfile` | 755 passed, 1 skipped |
| `ec77ba471` | `.venv/bin/pytest tests/runtime -q -n 3 --dist loadfile` | **779 passed, 1 skipped** |
| `ec77ba471` | `.venv/bin/pytest tests/architectural/test_layer_rules.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_mission_runtime_surface.py tests/architectural/test_no_legacy_terminology.py tests/architectural/test_shared_package_boundary.py tests/architectural/test_cold_import_status_boundary.py tests/status/test_producer_conformance.py tests/specify_cli/events tests/contract -q -n 3 --dist loadfile` | **439 passed, 10 skipped** |
| `ec77ba471` | 22 referrer files of the touched modules outside the dirs above (`tests/agent/test_implement_command.py … tests/unit/mission_loader/test_command.py`, list in the Activity Log run) `-q -n 3 --dist loadfile` | 315 passed |
| `ec77ba471` | `.venv/bin/pytest tests/perf/test_loader_perf.py -q -n0` (timing family, serial) | 2 passed |
| every commit | `ruff check <changed .py>`; `ruff check --select C901 <changed .py>`; `ruff format --check --force-exclude <changed .py>` | All checks passed; formatted (5 non-excluded files) |
| `388b0b243`, `ec77ba471` | `.venv/bin/mypy src/runtime/next/_internal_runtime/events.py src/runtime/next/runtime_bridge.py src/runtime/next/runtime_bridge_engine.py src/runtime/next/runtime_bridge_retrospective.py src/specify_cli/events/decision_log.py` | **21 errors in 3 files — identical to the pre-change tree** (`53339201f` in a scratch worktree: 21 errors; line-agnostic diff of messages: none new). One new `no-any-return` in `events.py` appeared mid-work and was fixed with an `isinstance` narrow, no suppression |

No baseline-red attribution was needed: every red seen was caused by (and fixed within) this WP. Known baseline reds in `tests/architectural/`
(`test_golden_count_ban`, six `test_execution_context_parity` nodes, `test_spec_kitty_home_pin_census`) were not in the run set.
`make test-*` / `uv` were not used (forbidden on the lane).

## 7. LOC delta and no-live-producer statement

Measured, `git diff --numstat d18b0c98c..ec77ba471 -- src/` (excluding lane-d's `decision.py`): `event_emitter.py` −102;
`events.py` +147/−4 (of which ~30 lines module docstring, ~35 registry class + comments, ~25 factory, ~30 `NullEmitter` identity +
`for_mission` + `seed`, ~10 `_resolve_mission_id`); `runtime_bridge.py` +24/−9 (three explanatory comment blocks; the code delta is
the import, two construction sites, and two one-token target changes); `runtime_bridge_engine.py` +1/−1; `decision_log.py` +10.
**Net `src/`: +66** — NOT the "net LOC still drops" the ADR's Consequences predicted. The concrete class's 88 code LOC are gone, but
the rewire-ready seam the ADR asked for (registry + env gate + identity-carrying null object + docstring honesty) costs more lines than
the no-op it replaced; the simplification is in *shape* (one class, one construction path, no duplicate name), not in line count.
Recorded here so the mission review does not have to rediscover it.
**No live producer is wired**: `RuntimeEventEmitterRegistry.registered()` is `None` on a fresh import (pinned); `status/adapters.py` untouched.

## 8. Spec Kitty tool frictions

- Commit guard: `ACTIVE_WP_CONTEXT_STALE: workspace context current_wp=WP03, canonical active_wp=WP05; lane_id=lane-c` on every commit — the
  lane's workspace context still says WP03 although WP05 is the canonical active WP; warning only.
- Commit guard: `ACTIVE_WP_SCOPE_VIOLATION` for `tests/architectural/test_no_dead_symbols.py`, `src/specify_cli/events/decision_log.py` and
  the ten repointed test files (out of the WP05 owned_files map) — warnings only, rationale in §4.
- The WP05 prompt's anchor `~:3244-3245` for the grandfathered rows was off by 27 lines (actual `:3217-3218`).
- `ruff format --check --force-exclude` silently skips formatter-debt files ("5 files already formatted" for 15 inputs) — expected but easy
  to misread as partial coverage.

> **Superseded (2026-09-07, operator decision):** PR #3921 (`feat/dead-port-disposition`, mission `dead-port-disposition-01M1VRA2`) executed the same ADR with `runtime_emitter_for_mission` / `register_runtime_emitter_factory` and was adopted as canonical; it was merged into this branch at `d8259dcae`, the ten conflicting files resolved toward it, and this WP's two test files replaced by #3921's `tests/architectural/test_runtime_emitter_seam.py` and `tests/runtime/test_bridge_decision_log_flush.py`. The step-0 lane-d merge and orphaned-row prune from this WP remain. The `sync_emitter` rename defer (deviation 4) therefore transfers to #3921's lineage (#3929).
