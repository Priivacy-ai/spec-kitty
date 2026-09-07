# WP04 design note — dependency readiness as a tri-state, fail-open guard field

**Mission**: `fsm-write-path-integrity-01M1TZV6` · **WP**: WP04 · **Author**: claude-fable-5-1 (python-pedro, implementer) · **Date**: 2026-09-06 · **Base**: lane-d `596396b7d` (WP01+WP03 ⊕ WP02+WP06)

Binding inputs: `contracts/dependency-guard.md` §1–§7; `data-model.md` §6; `research.md` §2 (decision Q8 `01M1V8HVDQH36X06JDK22SZV02`); spec US4, FR-012..FR-014, C-004, C-005, NFR-002, NFR-004; `design-notes/WP02-pipeline.md` §4 (the inert `readiness` seam); `design-notes/WP06-convergence.md` §2 (the transactional shell helpers).

## 1. Polarity decision (Q8) — fail-OPEN on `None`

`GuardContext.dependency_ready: bool | None = None` (models.py; the same field on `TransitionContext` and on the `TransitionInputs` Protocol so both concrete contexts keep satisfying the FSM's structural type).

| value | `planned→claimed`, `claimed→in_progress` | every other edge |
|---|---|---|
| `None` | pass — **no verdict supplied** | pass |
| `True` | pass | pass |
| `False` | refuse: `Transition <from> -> <to> blocked: unsatisfied dependencies (force with reason to override)`; `force` + actor + reason bypasses at `check_transition._check_force` (unchanged path) | pass |

**Why fail-open, recorded so nobody "fixes" it to match `subtasks_complete`'s `is not True` (`wp_state.py:370`):** two live callers build bare contexts on exactly the guarded edges — the crash-recovery progression probe (`lanes/recovery.py::_get_recovery_transitions`, `GuardContext(actor=RECOVERY_ACTOR, workspace_context="recovery")`) and the FR-015 force-free backward-edge probe (`agent/tasks_transition_core.py`). Fail-closed on `None` silently breaks both (R4). It is sound because after WP03 no durable write bypasses the two shells, and the shells **always** supply a verdict — `None` therefore only ever reaches `validate_transition` from direct guard-level callers. Both probe shapes are pinned in `tests/status/test_dependency_guard.py::TestProbeSitesFailOpen`, plus `tests/specify_cli/status/test_wp_state.py::TestDependencyReadinessGuard::test_none_is_not_treated_like_subtasks_complete`.

The guard never reads `ctx.force` (#1775 M2). Pinned: `test_guard_never_consults_force_itself` (`can_transition_to` + `guard_for` refuse while `check_transition` passes with actor+reason).

## 2. Resolution-site rule (FR-013) — inside the lock, against the shell's write surface

Each shell reduces its write surface **once**, after acquiring L1 / the transaction, and takes both `from_lane` and the dependency verdict from that one snapshot:

| shell | lock | write surface reduced | planning surface for the WP file |
|---|---|---|---|
| flat single `emit.emit_status_transition` | `feature_status_lock(canonical_feature_dir.name)` | `canonical_feature_dir` | `canonical_feature_dir` (primary) |
| flat batch `emit.emit_status_transition_batch` | same, once for the batch | `feature_dir` | `feature_dir` |
| transactional single `emit_status_transition_transactional` | `_acquire_status_transaction` | `txn.feature_dir` (coord worktree) | `identity.feature_dir` (canonical primary) |
| transactional batch `emit_status_transition_batch_transactional` | same | `txn.feature_dir` | `identity.feature_dir` |

Never before the lock (that reproduces the pre-flight TOCTOU); never against primary when the write surface is coord (stale state). Pins: `test_verdict_reflects_state_written_by_a_writer_that_held_the_lock_first` (a real second thread holds `feature_status_lock`, regresses the dependency, releases; the waiting emitter is refused) and `TestCoordSurfaceResolution` (primary and coord disagree in both directions; the verdict follows `txn.feature_dir`; an order pin asserts acquire → one `read_events` → readiness → release, with the reduced dir == `txn.feature_dir` ≠ primary and the WP-file dir == primary).

**Batch members.** A batch moves one WP; the verdict depends only on the *dependencies'* lanes, which a same-WP batch cannot change. The verdict resolved at acquisition is therefore the verdict for every member (including those reached through the chained in-memory `from_lane`), so it is computed once and threaded per `prepare_transition` call — equivalent to "per request against the accumulated state" at zero extra cost.

## 3. NFR-004 — no second full-log read

`emit._reduce_write_surface(feature_dir)` is the one `store.read_events` + `reducer.reduce` per emit. `_derive_from_lane(feature_dir, wp_id, *, snapshot=None)` gained a keyword: with a snapshot it derives without reading; without one it behaves exactly as before (its seven direct test callers are untouched). Declared dependencies are read from the WP prompt file's **raw frontmatter** (`specify_cli.frontmatter.read_frontmatter`) — deliberately not `read_wp_frontmatter`/`parse_wp_dependencies`, because that reader re-points runtime fields from a reduced snapshot (`wp_metadata._resolve_runtime_fields_from_snapshot`), i.e. a hidden second full-log read on the emit path. `test_emit_reads_log_once` / `test_batch_emit_reads_log_once_for_the_whole_batch` stay green unchanged (`_derive_from_lane == 1`, `read_events` before append == 1).

## 4. Helper location

- `src/specify_cli/status/dependency_verdict.py` (new, pure, zero I/O): `wp_lanes_from_snapshot(snapshot)` and `readiness_from_snapshot(snapshot, wp_id, dependencies) -> DependencyReadiness`. It calls `core.dependency_graph.dependency_readiness_for_wp` (lazy import — that module imports the `status` facade at load) with `provenance=snapshot.work_packages`, so gating semantics stay single-sourced (FR-014: approved OR done OR canceled-with-operator-provenance). No `None` is ever returned: a WP with no declared dependencies gets a *satisfied* verdict.
- `src/specify_cli/status/emit.py` (shell read concerns, Q6 shape): `_reduce_write_surface`, `_declared_dependencies(planning_feature_dir, wp_id)`, `_coerce_declared_dependencies`, `_resolve_dependency_readiness(planning_feature_dir, wp_id, snapshot)`. The transactional shell consumes them through `_emit.` exactly as it consumes `_derive_from_lane`.
- `transition_pipeline.prepare_transition` threads `dependency_ready=None if readiness is None else readiness.satisfied` into `GuardContext`; the `# noqa: ARG001` on the seam is gone.

**Declared-deps read policy.** Missing WP file ⇒ declares nothing. Only the `dependencies` key is read: whole-model `WPMetadata` validation would refuse status writes for defects unrelated to dependencies (found live: `tests/status/test_journal_lock_unification.py` uses `TWP00` ids, which `WPMetadata.validate_wp_id` rejects). Unparseable frontmatter or a `dependencies` value that is not a list of strings refuses the transition (`TransitionError`, fail-closed) — the gate must not be silently disabled by a corrupt planning artifact, and the same file already fails the pre-flight sites.

**Contract deviation.** Contract §2 shows the refusal message ending in `<ids>`; the data-model §6 field is a bare `bool | None`, so the guard cannot name the ids. The WP prompt's message form (no ids, "force with reason to override") was implemented; the shell-side `DependencyReadiness.unsatisfied` is available to any caller that wants to render them.

## 5. Replay purity (C-005 / NFR-002)

`reducer.py` gained nothing; `TestReplayPurity` AST-scans it for `validate_transition`, `GuardContext`, `dependency_ready`, `dependency_readiness_for_wp`, `readiness_from_snapshot` and any import of `wp_state`/`transitions`/`dependency_verdict`/`transition_pipeline` (with a non-vacuity mutation check), and replays a history containing a now-dep-illegal claim: `reduce()` folds it, `validate_transition_legality` returns no finding.

## 6. Demoted pre-flight sites (FR-014) — comments only

`cli/commands/implement.py::_ensure_wp_claim_preconditions`, `cli/commands/agent/workflow_executor.py`, `cli/commands/agent/tasks_status_view.py`, `orchestrator_api/commands.py` (the ready-list at `:1115` and the start-implementation gate at `:1440`), `runtime/next/discovery.py`. Two-line comment each; no logic change. Note for the caller-migration mission: `implement`'s pre-flight still runs unconditionally, so a regressed dependency is refused there **before** the lifecycle layer's no-op resume — that is the pre-flight's own UX policy, not the guard's. The lifecycle-level pin `tests/status/test_work_package_lifecycle.py::test_start_implementation_resume_is_not_regated_when_dependency_regresses` proves the guard itself cannot re-gate a resume (no entry edge is emitted).

## 7. What did NOT change (non-goal 6)

No edge added or removed; `force` semantics untouched (still `_check_force` at `check_transition`); terminal rules untouched; `ALLOWED_TRANSITIONS` untouched; `status/__init__.py` untouched (no facade widening, no version bump).

## 8. Out-of-map edits (declared leeway)

| file | why |
|---|---|
| `status/transition_pipeline.py` | FR-013 consumer: threads the verdict into `GuardContext`; drops the inert-seam `noqa`. |
| `status/emit.py` | FR-013 verdict supplier (flat shells) + the NFR-004 single-reduce helpers. |
| `coordination/status_transition.py` | FR-013 verdict supplier (transactional shells) against `txn.feature_dir`. |
| `status/transition_context.py` | Protocol conformance: `TransitionInputs` gained the field, so both concrete contexts must carry it. |
| `orchestrator_api/commands.py` | FR-014 demotion comments at the two sites. |
| `tests/status/test_work_package_lifecycle.py` | the no-op-resume pin lives beside the existing `no_op` tests. |


---

# WP04 design note — review cycle 1 addendum

**Mission**: `fsm-write-path-integrity-01M1TZV6` · **WP**: WP04 · **Author**: claude-fable-5-1 (implementer) · **Date**: 2026-09-06 · **Lane**: lane-d, cycle-0 head `9ca89428b` on base `596396b7d` · **Feedback**: `tasks/WP04-dependency-readiness-guard/review-feedback-1.md` (reviewer-renata)

This addendum amends `design-notes/WP04-guard.md` §4 ("Declared-deps read policy") and §6. Everything else in the note stands.

## A1. Finding 1 (MAJOR) — one canonical parser for the legacy `dependencies:` string forms

**Was**: `emit._coerce_declared_dependencies` accepted only `None` or `list[str]` and raised `TransitionError` for everything else — including the legacy string forms `"[]"`, `"WP01, WP02"` and bare `WP01` that `WPMetadata._normalize_legacy_fields` deliberately coerces (and that `core.dependency_graph.parse_wp_dependencies`, the parser behind every FR-014 pre-flight site, therefore accepts). Three live files carry `dependencies: "[]"` today (`kitty-specs/062-fix-doctrine-migration-test-failures/tasks/WP07`, `WP10`, `WP11`).

**Now**: the coercion is extracted, unchanged, into a pure module-level helper `status.wp_metadata.coerce_legacy_dependencies(raw: object) -> object` (exported). `WPMetadata._normalize_legacy_fields` calls it; `emit._coerce_declared_dependencies` calls it before its list-of-strings check. Rules were **moved, not duplicated** (charter: single canonical authority; FR-014: the shell's *inputs* now match the pre-flight's inputs, not only its gating semantics). Only a value `WPMetadata` would also refuse (`3`, `[1, 2]`, `{"a": 1}`) stays fail-closed — pinned by asserting the same `raw` raises `pydantic.ValidationError` on `WPMetadata.model_validate`.

Pins: `tests/status/test_dependency_guard.py::TestVerdictHelpers::test_legacy_string_dependencies_coerce_like_wpmetadata` (`"[]"→()`, `"WP01, WP02"→("WP01","WP02")`, `"WP01"→("WP01",)`), `::test_declared_dependencies_agree_with_the_pre_flight_parser` (writes the file, asserts `_declared_dependencies(...) == tuple(parse_wp_dependencies(wp_file))` for all three forms — the single-parser contract itself), `TestLegacyAndCorruptWpFiles::test_legacy_empty_string_dependencies_can_be_claimed` (shell-level `planned→claimed` on `dependencies: "[]"`), `::test_bare_scalar_dependency_is_honoured_when_the_dep_is_approved`, `::test_bare_scalar_dependency_still_gates_when_the_dep_is_in_flight` (the coercion is load-bearing, not noise). `tests/specify_cli/status/test_wp_metadata.py::TestCoerceLegacyDependencies` covers the helper directly (string forms, non-string passthrough by identity, model == helper).

Read-only probe of the three live files (reviewer's checklist item): `_declared_dependencies(<062 dir>, WP07|WP10|WP11)` → `()` each; `parse_wp_dependencies` on the same files → `[]` each. No raise.

## A2. Finding 2 (Minor) — decision: **shape (b)**, unresolvable ⇒ *unsatisfied verdict*, not an error

**Was**: an unparseable WP file (or a malformed value) raised `TransitionError` from `_declared_dependencies` inside `_resolve_dependency_readiness`, i.e. before `validate_transition`, on every edge, with no `force` escape — the whole write path was locked for that WP, including `→blocked` and a forced `→canceled`.

**Now**: `emit._resolve_dependency_readiness` catches that `TransitionError`, logs a `WARNING` (`"Dependency readiness of %s is unresolvable; refusing the guarded entry edges: %s"`), and returns `dependency_verdict.unresolvable_readiness(wp_id, reason)` — a `DependencyReadiness(wp_id, dependencies=(), unsatisfied=("<unresolvable> <reason>",))`. Consequences, exactly as the guard already defines them:

| edge | corrupt / unresolvable WP file |
|---|---|
| `planned→claimed`, `claimed→in_progress` | refused by `PlannedState`/`ClaimedState.guard_for` (`dependency_ready is False`) with the guard's message; **`force` + actor + reason bypasses** at `check_transition._check_force` (unchanged path) |
| `→blocked`, `→canceled`, `for_review`/`in_review`/`approved`/`done` edges | **never affected** — the guard has no opinion on them |

Why (b) over (a): (a) would need every one of the four shells to inspect the target lane (and the batch doors to scan members) before resolving; (b) is contained in one helper, keeps `_resolve_dependency_readiness` at trivial complexity, keeps NFR-004 (no extra log read — the file read is the same one as before), and keeps the shells' contract "always supply a verdict, never `None`" (C-004/Q8) intact. The `_declared_dependencies` helper still raises (its tests are unchanged); the shell is the layer that decides the raise is a *verdict*.

**Verdict shape, stated honestly.** `DependencyReadiness.unsatisfied` is documented as WP ids. `unresolvable_readiness` puts a single self-describing marker there (`UNRESOLVABLE_MARKER = "<unresolvable>"` + the reason) because `satisfied` is derived (`not self.unsatisfied`), `core.dependency_graph` is not this WP's to widen, and `dependency_verdict.py` cannot subclass `DependencyReadiness` at module level (that module imports the `status` facade at load — the same cycle that already forces the lazy import in `readiness_from_snapshot`). `dependencies=()` stays truthful (nothing could be read); the reason travels with the verdict for any caller that renders `unsatisfied`. The refusal message operators see is the guard's generic one ("unsatisfied dependencies (force with reason to override)"); the specific cause is in the WARNING log line. Surfacing `DependencyReadiness.unsatisfied` in the shell refusal (reviewer note 5) is left to the caller-migration follow-up — it needs a message-shape decision the contract §2 deviation already records.

Pins: `TestVerdictHelpers::test_resolve_dependency_readiness_unresolvable_file_is_an_unsatisfied_verdict` (no raise; `satisfied is False`; `dependencies == ()`; marker present; WARNING logged), `TestLegacyAndCorruptWpFiles::test_corrupt_frontmatter_refuses_the_entry_edge_without_force` (nothing persisted), `::test_corrupt_frontmatter_entry_edge_is_force_bypassable`, `::test_corrupt_frontmatter_never_affects_non_guarded_edges` (`planned→blocked` OK, then forced `blocked→canceled` OK, reduced lane `canceled`).

## A3. Finding 3 (Minor) — RED-proof provenance

No code change (C-009: red-first repros are transitional). The Activity Log is amended via `add-history` to state that the RED run on `596396b7d` used the pre-`dependency_verdict` revision of the test (the committed file imports `specify_cli.status.dependency_verdict` and so errors at collection on the base), and to record the reviewer's standalone repro shape: seed WP01 + WP02 `planned`, drive WP01 to `in_progress` through the flat shell, claim WP02 through the flat shell → `Failed: DID NOT RAISE TransitionError` on the base; the same repro raises on the lane.

## A4. Finding 4 (Note) — carried to the caller-migration follow-up

`cli/commands/implement.py::_ensure_wp_claim_preconditions` (`implement.py:1869`) runs unconditionally, so `implement` re-invoked on an `in_progress` WP whose dependency regressed is refused by the pre-flight before the lifecycle no-op is reached. Pre-existing on the base (WP04's diff there is comments-only); FR-014 leaves the sites in place. Follow-up item for the caller-migration mission: make the pre-flight skip the gate when the WP is already `in_progress` (resume), matching the lifecycle no-op, then add the CLI-level variant of `test_start_implementation_resume_is_not_regated_when_dependency_regresses` that T025.2 asked for.

## A5. Test-helper defect found and fixed while re-verifying

`tests/status/test_dependency_guard.py::_event` stamped `at` as `00:00:{n % 60}`, wrapping every 60 events. The reducer orders by `(at, event_id)` (`reducer.py:80`), so once the added tests shifted the module counter, `TestCoordSurfaceResolution::test_verdict_follows_coord_surface_when_primary_is_stale_blocked`'s WP01 chain straddled a minute boundary and `approved` sorted before `in_progress` (deterministic in file order; green in isolation). The stamp is now monotonic over hours:minutes:seconds. Not a guard defect; recorded so nobody attributes the earlier red to the shells.

## A6. Verification (cycle 1)

- `tests/status/test_dependency_guard.py tests/status/test_transition_pipeline.py tests/status/test_emit.py tests/specify_cli/status/test_wp_metadata.py` → 280 passed (guard file alone: 65).
- Blast radius `tests/status tests/specify_cli/status tests/specify_cli/coordination tests/specify_cli/lanes tests/unit/status -n 3 --dist loadfile` → 2199 passed, 2 skipped.
- Gates `test_status_module_boundary test_2093_authority_invariant test_status_unsafe_allowlist test_status_events_writes_gate` → 55 passed. `test_no_legacy_terminology` → see Activity Log.
- `tests/specify_cli/cli/commands/agent -n 3 --dist loadfile` → see Activity Log.
- `ruff check` / `--select C901` / `ruff format --check --force-exclude` per changed file: all clean; whole-repo format gate remains baseline-red only on WP01's files (none from this diff).
- `mypy` on `emit.py dependency_verdict.py transition_pipeline.py wp_state.py models.py wp_metadata.py` → no issues.
- Hand probes (flat shell, tmp mission): `dependencies: "[]"` → `planned→claimed` OK; bare `WP01` with WP01 `approved` → OK; corrupt frontmatter → `planned→claimed` REFUSED (guard message), `planned→blocked` OK, forced `blocked→canceled` OK, forced `planned→claimed` OK.
