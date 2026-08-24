# Design Decisions — legacy-cleanup-split-dossier-queue-migration

Seeded at spec phase; append during plan/tasks/implementation.

## Decision: topology
`coord` topology (context-derived default on primary branch `main`), NOT explicit
`--topology`. Ledger SK-57/SK-36/SK-09 document branch-flat topologies chosen on protected
`main` scaffolding "successfully" with no branch minted and no landing spot for
`safe-commit`. `coord` mints `kitty/mission-legacy-cleanup-split-dossier-queue-migration-01M0MGHB`
and gives bookkeeping the coordination-branch destination SK-60's guard requires.
Verified post-scaffold: `git branch --list` shows the coordination branch minted; HEAD
remains on `main` (expected for `coord` — the coordination branch is a bookkeeping
destination, not necessarily the author's checkout branch); `meta.json` fields:
`"topology": "coord"`, `"target_branch": "main"`, `"coordination_branch":
"kitty/mission-legacy-cleanup-split-dossier-queue-migration-01M0MGHB"`.

## Decision: no dependency bump for spec-kitty-events
Already pinned `>=6.0.0,<7.0.0`; 6.1.0 (installed) already exports `validate_event()` and
the typed payload models. `spec-kitty-events#50` is an open, unmerged, non-draft PR adding
fixtures — not new constraints. Do not couple this mission's landing to that PR merging.

## Decision: topology — SUPERSEDED, re-scaffolded to `single_branch`

The `coord` decision above was acted on and scaffolded successfully (coordination branch
minted, ref confirmed), but proved non-viable at commit time: `safe-commit --to-branch main`
refused (protected branch); `safe-commit --to-branch <coord-branch>` refused because HEAD
was never moved onto it (and moving HEAD by hand is forbidden); `spec-kitty spec-commit`
(the tool's own documented "materialize-then-retry" escape hatch for exactly this state)
materialized a coordination worktree but did not relocate the uncommitted mission files
into it, so the retry it prescribes still failed identically — first-hand confirmation
that ledger **SK-12** is not fixed on 3.2.6rc3 (see `tracer-tooling-friction.md`).

**Operator-authorized remedy**: re-scaffold via the entry point the refusals had been
naming all along — `spec-kitty agent mission create <slug> --mission-type software-dev
--start-branch refactor/dossier-emitters-canonical-only-1058 --json` — which switches
HEAD to a fresh **non-protected** feature branch *before* topology is derived. With HEAD
off `main`, `--topology`'s context-derived default (#2581) resolves to `single_branch`
instead of `coord`. This is NOT the SK-57/SK-36 trap (an explicit branch-flat topology
chosen while HEAD sits on protected `main`): here the branch-flat shape resolves onto an
already-non-protected branch, which is exactly the safe case those entries contrast
against.

Verified post-re-scaffold: HEAD = `refactor/dossier-emitters-canonical-only-1058`
(non-protected); `meta.json`: `"topology": "single_branch"`, `"target_branch":
"refactor/dossier-emitters-canonical-only-1058"`, `"coordination_branch": null`; the
`agent mission create` command's own auto-commit (`75d707d89`, `meta.json` only) landed
directly on that branch, demonstrating plain `safe-commit` (no `--to-branch`/
`--target-branch`) now has a working destination. New mission slug/ULID:
`legacy-cleanup-split-dossier-queue-migration-01M0MGHB` (old `...-01M0MF07` scaffold was
torn down after confirming it carried no unique commits — nothing committed was lost;
all authored content was preserved and ported).

We PR into `main` and never run `spec-kitty merge`, so `target_branch` pointing at the
feature branch rather than `main` has no downstream effect on this mission's merge path.

## Plan phase (2026-08-22)

Full rationale lives in `plan.md`'s "Mission-Specific Design Decisions" section;
this entry is a pointer plus the headline decisions, not a duplicate:

- **FR-006/FR-007 sentinel shape**: a single module-level `object()` sentinel
  (`_DOSSIER_VALIDATE_EVENT_DELEGATE`) is the value for all four dossier keys in
  `_PAYLOAD_RULES`; `_validate_payload` gains an `is`-identity early-return branch
  ahead of the generic `rules["required"]`/`rules["validators"]` access, dispatching
  to a new `_validate_dossier_payload` method that lazily imports and calls
  `spec_kitty_events.conformance.validate_event(payload, event_type, strict=True)`.
  `VALID_EVENT_TYPES` is untouched (still `frozenset(_PAYLOAD_RULES.keys())`) since
  the four dossier keys never leave the dict.
- **FR-004 contract**: parameter promotion (`wp_id`/`step_id`/`required_status` on
  `emit_artifact_indexed`; `reason_detail`/`blocking` on `emit_artifact_missing`) and
  bridge removal must land in the same commit (same functions, same file) — a naive
  bridge-only removal would silently regress `dossier_pipeline.py` behind its broad
  `except Exception` handlers. The regression test proving this must not reuse the
  existing plain-`MagicMock` `@patch` decorators in `test_dossier_pipeline.py`
  (verified during planning: neither uses `autospec=True`, so neither would go red on
  a reverted promotion) — a new `autospec=True`/real-call test is required.
- **Phasing**: 6 phases (baseline → mirror deletion+Literal remap → bridge
  removal+kwarg promotion+last_known_ref drop → validate_event delegation → guard
  test → test import re-pointing), sequenced by same-file/same-function dependency,
  not by parallel work streams (single sequential PR, ~500-700 LOC estimate,
  recommended NOT to split).
- **Campsite-clean scope**: read both touched files end-to-end for domain-matched
  debt beyond FR-001..FR-010's own scope; found none — no separate preceding
  campsite-clean step is proposed for this mission.

## Plan-review fix round (R1-R6, 2026-08-22)

An adversarial plan review (`reviews/plan.confirmed.yaml`) confirmed 6 findings
against the FR-006/FR-007 sentinel design and the Gate Set / FR-004 test-bar
sections; `plan.md` was revised in place. Headline decisions, full rationale
stays in `plan.md`:

- **`diagnose.py` was an unaccounted-for `_PAYLOAD_RULES` consumer
  (PLAN-ARCH-001, sev 5)**: `src/specify_cli/sync/diagnose.py::_validate_payload`
  imports `_PAYLOAD_RULES` directly (`diagnose.py:51`) and does
  `rules.get("required", set())`/`rules.get("validators", {})` with no shape
  guard — the sentinel would crash `spec-kitty sync diagnose` on any dossier
  event with an uncaught `AttributeError`. Fix mechanism chosen: a small shared
  predicate `is_dossier_delegate(rules) -> bool` exported alongside the sentinel
  in `emitter.py`; `diagnose.py::_validate_payload` calls it before any
  dict-shaped access and delegates to `validate_event()` the same way
  `emitter.py::_validate_dossier_payload` does, folding `ConformanceResult`
  violations into `diagnose.py`'s existing `errors` list rather than printing a
  warning (matches `diagnose.py`'s own return-structured-errors contract). A new
  regression test lands in `tests/sync/test_diagnose.py` driving a dossier event
  through `diagnose_events()`. This fix must land in the **same commit** as the
  sentinel (Phase 3), not a follow-up phase, so no intermediate commit leaves
  `diagnose.py` broken.
- **`tests/dossier/test_snapshot_emit.py` breaks under the sentinel
  (PLAN-ARCH-002, sev 4)**: `test_emit_rule_wires_canonical_validator_for_hash_fields`
  subscripts `_PAYLOAD_RULES["MissionDossierSnapshotComputed"]["validators"]` /
  `[...ParityDriftDetected"]["validators"]` directly — `TypeError: 'object' object
  is not subscriptable` once those keys hold the sentinel. Rewritten to assert
  against the `ConformanceResult` delegation behavior (malformed hash value ->
  violation surfaces via `_validate_dossier_payload`) instead of asserting a
  specific validator callable is wired into a dict that no longer exists for
  these two event types.
- **`_PAYLOAD_RULES` type annotation (PLAN-ARCH-003, sev 2)**: corrected from
  `dict[str, dict[str, Any]]` to `dict[str, dict[str, Any] | object]` in the
  same commit as the sentinel — a narrower `Literal`/sentinel-aware alias was
  considered and rejected as unnecessary ceremony for one private sentinel value.
- **Full `_PAYLOAD_RULES` blast radius (PLAN-ARCH-004, sev 3)**: re-ran
  `grep -rn "_PAYLOAD_RULES" src/ tests/` and classified every hit
  (read-only-safe / needs-code-change / needs-test-rewrite) in `plan.md`'s
  Scale/Scope section. Beyond `diagnose.py` and `test_snapshot_emit.py`, the
  remaining hits (`tests/contract/test_handoff_fixtures.py`,
  `tests/status/test_actor_boundary_normalize.py`,
  `tests/status/test_sync_lane_mapping.py`) only ever look up non-dossier keys
  (`WPStatusChanged`, `WPCreated`, etc.) and are read-only-safe;
  `tests/contract/test_identity_contract_matrix.py`'s hit is a source comment,
  not a real consumer.
- **Corrected CI shard names (PLAN-VERIFY-001, sev 3)**: this mission's touched
  tests are actually collected by `integration-tests-core-misc` (`tests/dossier/`,
  `tests/architectural/` via the misc path-filter group), the always-on
  `arch-adversarial` job (`tests/architectural/`), and
  `fast-tests-sync`/`integration-tests-sync` (`tests/sync/`) — NOT
  "fast-doctrine"/"slow", which don't exist as job names on this surface (an
  earlier plan draft misnamed them). None of these four jobs carries a
  `--cov-fail-under` floor; only `kernel-tests`/`mission-loader-coverage` (90%),
  `fast-tests-charter` (55%), and `fast-tests-agent` (10%) do, and none of those
  collect this mission's tests. The only coverage-floor-style protection this
  mission's new tests get is SonarCloud's project-level Quality Gate.
- **FR-004 test bar strengthened (PLAN-VERIFY-002, sev 4)**: `autospec=True`
  alone only proves the call *binds* to the real signature — since
  `dossier_pipeline.py`'s `_emit_artifact_events` wraps both emitter calls in a
  broad `except Exception`, an autospec mock cannot exercise AC1 (diagnostics
  folding into `context_diagnostics`/`step_id`) or AC2 (the `blocking`
  short-circuit), both of which live inside the mocked-away function bodies.
  Binding test bar is now explicit two-part: (a) at least one new test must call
  the real, unmocked emitters end-to-end and assert on the returned payload's
  `context_diagnostics`/`step_id` (AC1) and on the emit/no-emit outcome via
  `events_emitted` (AC2); (b) an `autospec=True` mock, if added, is supplementary
  only and must assert on a try/except-surviving observable (`events_emitted`
  count or `mock_emit.call_args`), never merely that the outer call didn't raise.

## Round 2 — fresh-sweep plan review (plan-fresh.yaml, 2026-08-22)

- **`diagnose.py` fix promoted to a real FR (PLAN-FRESH-001, sev 4)**: round 1's
  `diagnose.py` coordinated fix (predicate-guarded branch in
  `diagnose.py::_validate_payload` + new `tests/sync/test_diagnose.py`
  regression test) was real, necessary, verified work but had no owning FR in
  spec.md's FR-001..FR-010 table, and `tests/sync/test_diagnose.py` was
  missing from NFR-003's bounded test-scope list — leaving it at real risk of
  being silently dropped when tasks.md generates WPs from the FR table.
  **Fix**: added `FR-011` to spec.md naming the `diagnose.py::_validate_payload`
  coordinated fix and its `tests/sync/test_diagnose.py` regression test
  explicitly, added a cross-reference to FR-011 in spec.md's Key Entities
  "Reconciling FR-006 and FR-007" paragraph, and added
  `tests/sync/test_diagnose.py` to NFR-003's bounded scope list. Re-pointed
  every plan.md citation of this work (Technical Context, Scale/Scope, Seam
  Identification, the "diagnose.py coordinated fix" section, Phasing Phase 3,
  PR Shape table) from bare "plan-review remediation, closes PLAN-ARCH-001" to
  "FR-011". Split the Red-First/ATDD Test Mapping table's FR-006 row: the
  `test_diagnose.py` regression test now has its own FR-011 row with its own
  revert-behavior justification; FR-006's row keeps only the emitter-side test
  and the `test_snapshot_emit.py` rewrite (PLAN-ARCH-002), which stays
  correctly FR-006-scoped since it exercises the same sentinel change on the
  emitter side, not diagnose.py.
- **Predicate unification (PLAN-FRESH-002, sev 3)**: the plan's
  `emitter.py::_validate_payload` code sample in "FR-006/FR-007 sentinel
  shape" still checked the sentinel via a raw `rules is
  _DOSSIER_VALIDATE_EVENT_DELEGATE` identity comparison, while the
  `diagnose.py` remediation section defined and used a wrapped
  `is_dossier_delegate(rules)` predicate — claiming behavioral parity between
  the two files without actually sharing one implementation. **Fix**: moved
  the `is_dossier_delegate()` definition up to sit immediately after the
  sentinel's own definition (before its first use), updated
  `emitter.py::_validate_payload`'s code sample to call
  `is_dossier_delegate(rules)` instead of the raw `is` comparison, and removed
  the now-duplicate `is_dossier_delegate()` definition from the `diagnose.py`
  coordinated-fix section (it now just references the one definition above).
  Both consumers share one predicate; only the predicate's own body references
  `_DOSSIER_VALIDATE_EVENT_DELEGATE` directly. Also fixed a stray inline
  comment that referenced a nonexistent `_is_dossier_delegate` (underscore,
  private) name left over from spec.md's illustrative Key Entities sketch —
  the plan's actual, binding name is the public `is_dossier_delegate()`.

## Round 3 fixes (plan-fresh-2, FINAL fresh-sweep round; PLAN-FRESH2-001..004)

- **PLAN-FRESH2-001 (sev 2)**: round 2's PLAN-FRESH-002 fix (see above) renamed
  the predicate in plan.md's code samples but missed spec.md's own Key
  Entities "Reconciling FR-006 and FR-007" pseudocode, which still read `if
  _is_dossier_delegate(rules):` — the underscore-prefixed name plan.md never
  actually settled on. **Fix**: changed spec.md's snippet to `if
  is_dossier_delegate(rules):`, matching plan.md's public, no-underscore
  binding name everywhere else.
- **PLAN-FRESH2-002 (sev 3)**: FR-011 (the `diagnose.py` fix promoted to a
  real FR in round 1, see PLAN-FRESH-001 above) had no Acceptance Scenario in
  "User Scenarios & Testing" — every other FR traces to a Given/When/Then
  scenario, but FR-011's acceptance behaviour existed only as FR-table prose.
  **Fix**: added Acceptance Scenario 4 to User Story 1 (closest fit — payload
  validation correctness) covering `diagnose_events()` processing a
  dossier-typed event with a valid and an invalid payload: no crash, and the
  invalid case's violation lands in `DiagnoseResult.errors`.
- **PLAN-FRESH2-003 (sev 3)**: Success Criteria had SC-001..SC-005 but no
  measurable outcome for FR-011, even though FR-006 (the other High-priority
  FR in this pairing) has its own SC-005. **Fix**: added SC-006 stating
  FR-011's measurable outcome — `diagnose_events()` no longer raises
  `AttributeError` on a dossier-typed queued event, and a hand-constructed
  invalid dossier payload reports a real `ConformanceResult`-sourced
  violation in `DiagnoseResult.errors`.
- **PLAN-FRESH2-004 (sev 3)**: NFR-002's binding visibility contract (printed
  `[yellow]Warning...` + drop-not-queue) was written as if it governed *the*
  `_validate_payload` function, but FR-011 introduced a second function of
  that name (`diagnose.py`'s) with a genuinely different visibility
  mechanism — accumulate into `DiagnoseResult.errors`, not print a warning.
  Left unscoped, NFR-002 reads as contradicted by FR-011's own design.
  **Fix**: scoped NFR-002's spec.md row explicitly to
  `emitter.py::_validate_payload` and added a parallel sentence stating
  `diagnose.py::_validate_payload`'s (FR-011) contract — surface the
  violation in `DiagnoseResult.errors` — as separately binding. Applied the
  same scoping to plan.md's Technical Context "Constraints" line, which
  restated NFR-002 verbatim with no `diagnose.py` exception noted; the
  "`diagnose.py` coordinated fix" section elsewhere in plan.md already
  described the correct behaviour, so this was a cross-reference fix, not new
  design.
