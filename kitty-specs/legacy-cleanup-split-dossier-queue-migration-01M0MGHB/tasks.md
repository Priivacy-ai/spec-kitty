# Work Packages: Legacy Cleanup — Split Dossier Queue Migration

**Inputs**: `spec.md` (11 FRs, 3 NFRs, 4 constraints), `plan.md` (Phasing, Red-First/ATDD
Test Mapping, PR Shape, Parallel Work Analysis, Gate Set — all already resolved; this
file materializes those sections into concrete work packages, it does not re-derive them)

**Mission**: `legacy-cleanup-split-dossier-queue-migration-01M0MGHB` (issue #1058)
**Target branch**: `refactor/dossier-emitters-canonical-only-1058` (current HEAD)

**Tests**: Required. Charter Standing Order #4 (test-remediation/red-first discipline)
and C-011 (ATDD-first) bind this mission; every FR below carries a named test in
plan.md's "Red-First / ATDD Test Mapping" table that this tasks.md carries forward
verbatim into the owning WP's Definition of Done — no test bar in that table is
weakened here.

**Organization**: 21 fine-grained subtasks (`T001`-`T021`) roll up into 4 work
packages (`WP01`-`WP04`), one per plan.md Phasing group (Phase 0+1+2, Phase 3,
Phase 4, Phase 5). Each work package is independently deliverable and testable,
and the chain is strictly linear (see "Dependency & Execution Summary" below) —
this mirrors plan.md's own "Parallel Work Analysis" conclusion that this mission
is not a good candidate for parallel-agent decomposition.

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** indicates the subtask can proceed in parallel (different files/components).
  **No subtask in this mission is marked `[P]`** — every subtask in a WP touches the
  same file(s) the WP owns, and every WP depends on the previous one; there is no
  safe parallelization opportunity anywhere in this mission (see plan.md "Parallel
  Work Analysis").
- Subtasks are **reference rows**, not checkboxes: record completion with
  `spec-kitty agent tasks mark-status <Txxx> --status done`. The reduced event-log
  snapshot is the sole subtask-completion authority — there is no `- [ ]` box to tick.

## Path Conventions

- Single project: `src/specify_cli/`, `tests/`.

---

## ⚠️ PR Shape Recommendation (carried forward from plan.md, not decided here)

plan.md's own "PR Shape" section estimates **~620-750 LOC changed across 9 files**
(3 source files + 6 test files, 1 brand-new) and explicitly recommends **one PR for
the whole mission**, reviewable in a single sitting, with sequential WP commits inside
it — not a PR split. The estimate holds after this WP decomposition (21 subtasks
across 4 WPs, none individually exceeding ~450 estimated prompt lines). This
tasks.md does not change that recommendation; it is restated here per this phase's
own instruction to flag rather than silently decide.

> **Correction (tasks-review remediation, closes TASKS-DECOMP-001):** plan.md's
> PR Shape LOC table, as this section originally restated it, silently omitted
> `tests/sync/test_events.py` — WP02 owns that file and its T012 subtask adds
> real new SC-005/FR-006 and FR-007 test content to it. The file count and LOC
> total above (9 files, ~620-750 LOC) are the corrected figures, recomputed
> directly from plan.md's own per-file row ranges; plan.md's PR Shape table
> has been updated in place with a matching row.

**If, during implementation, the
real diff meaningfully exceeds this estimate (e.g. WP02's coordinated
emitter.py/diagnose.py/tests change balloons past ~300 LOC), the orchestrator/operator
— not any single WP's implementer — should revisit the one-PR recommendation before
merge, not split unilaterally mid-mission.**

## ⚠️ Chokepoint Called Out Explicitly (binding constraint, not a nicety)

FR-006 and FR-011 both mutate consumers of the **same module-level `_PAYLOAD_RULES`
dict** (`src/specify_cli/sync/emitter.py` and `src/specify_cli/sync/diagnose.py`) via
the shared `is_dossier_delegate()` predicate. This is a genuine ordering/atomicity
constraint per plan.md's Phase 3 reasoning: landing the sentinel in `emitter.py`
without the coordinated `diagnose.py` fix in the **same commit** leaves
`diagnose_events()` crashing with an uncaught `AttributeError` on any dossier event in
the local offline queue, and leaves `tests/dossier/test_snapshot_emit.py`'s existing
subscript-based test red. **WP02 below is that atomic unit — its five owned files
(`emitter.py`, `diagnose.py`, `tests/sync/test_events.py`, `tests/dossier/test_snapshot_emit.py`,
`tests/sync/test_diagnose.py`) land in one commit. Do not split WP02's `emitter.py`
sentinel change from its `diagnose.py` coordinated fix into separate WPs that could
land independently — that would reintroduce exactly the broken intermediate state
plan.md's Phase 3 reasoning rules out.**

## ⚠️ Rebase-Check Note (prose only, not machine-enforced)

`src/specify_cli/sync/emitter.py` is also touched by the currently-open PR #3655,
which works `_emit()`'s routing region (~line 2350). This mission's WP02 works a
different region of the same file — the `_PAYLOAD_RULES` dossier entries (currently
`emitter.py:827-876`), `VALID_EVENT_TYPES` (`:897`), and `_validate_payload`
(`:2549-2587`). Line-range overlap risk is low, but **whoever implements WP02 should
re-check `emitter.py`'s diff against `main`/PR #3655 immediately before starting**,
since line numbers will have drifted by the time WP01 lands. This is a prose
reminder for implement-time, not an `owned_files` conflict — spec-kitty's ownership
validation only checks disjointness within this mission's own WPs, not against other
open PRs.

---

## Work Package WP01: Canonical Type Adoption & Legacy Bridge Removal (Priority: P1)

**Goal**: Delete the local Pydantic mirror from `dossier/events.py`, import the
canonical `spec_kitty_events` equivalents, remove the `*args`/`**kwargs` legacy
bridge from the two emitters that carry it while promoting the one live keyword
shape to explicit parameters, and drop the dead `last_known_*` parameters. Also
performs this mission's Phase 0 baseline capture as its first subtask, since no
later WP is earlier in the dependency chain.
**Independent Test**: `tests/dossier/test_events.py` (pre-FR-009, still importing
from `specify_cli.dossier.events` at this point) and `tests/sync/test_dossier_pipeline.py`
pass against the new canonical-only `events.py`; the new FR-004 regression test(s)
prove the legacy-bridge removal did not silently break `dossier_pipeline.py`'s
keyword calls.
**Prompt**: `tasks/WP01-canonical-type-adoption-and-legacy-bridge-removal.md`
**Requirement Refs**: FR-001, FR-002, FR-003, FR-004, FR-005
**Owned files**: `src/specify_cli/dossier/events.py`, `tests/sync/test_dossier_pipeline.py`
**Dependencies**: None (starting package; Phase 0 baseline runs inside this WP)

### Included Subtasks

T001 Phase 0 baseline capture: run the NFR-003 targeted test surface against pre-change HEAD, record red/error set, cross-reference against issue #3284's known 23+2 (WP01)
T002 Delete the 7 local mirror classes from `dossier/events.py` and import their canonical equivalents from `spec_kitty_events` (FR-001) (WP01)
T003 Confirm `_normalize_artifact_class`/`_LEGACY_ARTIFACT_CLASS_MAP` remap still runs ahead of every `ArtifactIdentity(...)` construction, ahead of the now-`Literal`-typed canonical field (FR-002) (WP01)
T004 Delete `_consume_legacy_values` and the `*args`/`**kwargs` bridge from `emit_artifact_indexed`; promote `wp_id`/`step_id`/`required_status` to explicit keyword-only parameters (FR-003, FR-004 half 1) (WP01)
T005 Delete the bridge from `emit_artifact_missing`; promote `reason_detail`/`blocking` to explicit keyword-only parameters; drop `last_known_content_hash_sha256`/`last_known_size_bytes` and the `ContentHashRef`-construction branch (FR-003, FR-004 half 2, FR-005) (WP01)
T006 Add the binding-per-plan.md FR-004 regression test(s) to `tests/sync/test_dossier_pipeline.py` — real, unmocked end-to-end call proving AC1 (diagnostics/step_id) and AC2 (blocking short-circuit) (FR-004) (WP01)

### Implementation Notes

- Phase 1 (FR-001/FR-002) and Phase 2 (FR-003/FR-004/FR-005) land in this **single**
  WP/commit per plan.md's explicit reasoning: both edit the same ~150 contiguous
  lines of `events.py`'s two bridged emitters, and an intermediate state with the
  mirror deleted but the bridge still referencing it (or vice versa) would be broken.
- T006's test bar is binding, not a suggestion: a plain (non-autospec) `Mock`-based
  test does **not** prove FR-004 — see the WP01 prompt file's Test Strategy section
  for the exact shape required (mirrors plan.md's "FR-004 raise/report/refuse
  contract" section verbatim).

### Parallel Opportunities

- None. All 6 subtasks touch the same file or its direct regression-test
  counterpart, in the order listed.

### Dependencies

- None (starting package).

### Risks & Mitigations

- Silent breakage of `dossier_pipeline.py`'s existing keyword calls if the
  parameter promotion (T004/T005) is skipped or reverted → mitigated by T006's
  binding real-call test bar, which is designed specifically to go red on that
  exact revert (see plan.md "FR-004 raise/report/refuse contract").
- Baseline miscounted → T001 must record test IDs, not just counts, and diff
  against issue #3284 before any later WP attributes a red test to this mission.

---

## Work Package WP02: `validate_event()` Delegation & Sentinel Coordination (Priority: P1)

**Goal**: Replace the four hand-maintained `_PAYLOAD_RULES` dossier entries with a
delegation to `spec_kitty_events.conformance.validate_event()`, behind a
reconciling sentinel that keeps the four dossier keys recognized by
`VALID_EVENT_TYPES`. Coordinate the same sentinel-recognition fix into
`sync/diagnose.py::_validate_payload` (a second, independent consumer of the same
dict) in the **same commit**, since a sentinel-only commit would crash
`diagnose_events()` on any dossier event and leave `test_snapshot_emit.py` red.
**Independent Test**: A hand-constructed invalid dossier payload run through
`EventEmitter._validate_payload()` returns `False` with a real violation detail in
the warning (SC-005); the same run through `diagnose_events()` reports the
violation in `DiagnoseResult.errors` without crashing (SC-006).
**Prompt**: `tasks/WP02-validate-event-delegation-and-sentinel-coordination.md`
**Requirement Refs**: FR-006, FR-007, FR-011
**Owned files**: `src/specify_cli/sync/emitter.py`, `src/specify_cli/sync/diagnose.py`,
`tests/sync/test_events.py`, `tests/dossier/test_snapshot_emit.py`, `tests/sync/test_diagnose.py`
**Dependencies**: WP01

### Included Subtasks

T007 Add the `_DOSSIER_VALIDATE_EVENT_DELEGATE` sentinel, `_DOSSIER_EVENT_TYPES` frozenset, and `is_dossier_delegate()` predicate to `emitter.py`, module-level alongside `_PAYLOAD_RULES` (WP02)
T008 Replace the four dossier entries in `_PAYLOAD_RULES` (`emitter.py:827-876`) with the sentinel; correct the module-level type annotation to `dict[str, dict[str, Any] | object]` (FR-006, FR-007) (WP02)
T009 Add `_validate_dossier_payload` and the early-return branch (calling `is_dossier_delegate()`) to `EventEmitter._validate_payload` (`emitter.py:2549`) (FR-006) (WP02)
T010 Add the `is_dossier_delegate()`-guarded branch to `diagnose.py::_validate_payload`, delegating to `validate_event()` and folding violations into the existing `errors` accumulator (FR-011) (WP02)
T011 Add the new dossier-event regression test(s) to `tests/sync/test_diagnose.py` driving `diagnose_events()` with valid and invalid payloads (FR-011) (WP02)
T012 Add the new SC-005/FR-006 regression test to `tests/sync/test_events.py` (hand-constructed invalid dossier payload through `EventEmitter._validate_payload()`) plus an FR-007 `VALID_EVENT_TYPES` membership test (WP02)
T013 Rewrite `tests/dossier/test_snapshot_emit.py::test_emit_rule_wires_canonical_validator_for_hash_fields` (`test_snapshot_emit.py:220-228`) to assert against the `ConformanceResult` delegation behavior instead of subscripting `_PAYLOAD_RULES[...]["validators"]` (WP02)

### Implementation Notes

- This WP is the mission's one genuine chokepoint — see "⚠️ Chokepoint Called Out
  Explicitly" above. All 5 owned files land in one commit.
- Re-check `emitter.py` against `main`/PR #3655 immediately before starting — see
  "⚠️ Rebase-Check Note" above.

### Parallel Opportunities

- None — see "⚠️ Chokepoint" above; this is the one phase touching different files
  from WP01, but it is still sequenced serially, not run in parallel with WP01.

### Dependencies

- Depends on WP01 (sequenced after it in plan.md's Phasing for a simpler linear
  reviewable commit history; not a hard file/symbol dependency).

### Risks & Mitigations

- Sentinel lands in `emitter.py` without the `diagnose.py` coordination →
  `diagnose_events()` crashes on any dossier event in the local offline queue,
  the normal case for any active mission using dossier tracking. Mitigated by
  keeping both changes in one commit (this WP) and by T011's regression test.
- `_PAYLOAD_RULES`'s corrected type annotation (T008) must land with the sentinel
  in the same subtask/commit — an un-updated `dict[str, Any]` annotation with a
  sentinel value inside it fails `mypy`/ruff cleanliness expectations even though
  mypy is CI-advisory-only (CLAUDE.md's Code Style bar still applies).

---

## Work Package WP03: Architectural Guard — AST Positional-Call Detector (Priority: P2)

**Goal**: Add a new AST-based guard test that fails if any production code calls
the four dossier emitters with a positional argument, including a planted-violation
positive control proving the detector actually fires.
**Independent Test**: The detector reports zero violations against the real `src/`
tree; the same detector run against a throwaway fixture containing a planted
6-positional-argument call reports exactly one violation.
**Prompt**: `tasks/WP03-architectural-guard-ast-positional-call-detector.md`
**Requirement Refs**: FR-008
**Owned files**: `tests/architectural/test_dossier_emitter_positional_guard.py` (new)
**Dependencies**: WP02

### Included Subtasks

T014 Write the AST detector function walking `src/**/*.py` for `ast.Call` nodes matching the four emitter names with non-empty positional args (FR-008) (WP03)
T015 Add the clean-tree assertion test — detector run against the real `src/` tree reports zero violations (FR-008) (WP03)
T016 Add the positive-control test — planted 6-positional-argument fixture call reports exactly one violation (FR-008) (WP03)
T017 Add docstring/comments matching `test_shared_package_boundary.py`'s established pattern; final structural review of the new file (WP03)

### Implementation Notes

- This phase's clean-tree assertion is expected to pass on day one regardless of
  WP01/WP02's changes (the 5 real call sites — `dossier_pipeline.py:101,126,175,230`,
  `drift_detector.py:419` — are already 100% keyword-only), but it is sequenced
  after WP02 anyway so its positive-control fixture's planted call matches the
  post-mission emitter signatures rather than going stale.

### Parallel Opportunities

- None — sequenced after WP02 per plan.md Phase 4, though it could in principle
  run standalone against the pre-mission tree (see Implementation Notes).

### Dependencies

- Depends on WP02.

### Risks & Mitigations

- A detector that vacuously passes because nothing in `src/` trips it → mitigated
  by T016's positive control, which is this WP's own red-first proof of being
  load-bearing (spec.md Acceptance Scenario 3).

---

## Work Package WP04: Test Import Re-Pointing & Final Validation (Priority: P1)

**Goal**: Re-point `tests/dossier/test_events.py`'s 7 mirror-type imports to
`spec_kitty_events`, confirm the PR #1056 positional-order regression test needs
zero edits, add explicit canonical-type identity assertions, and run this
mission's final targeted-surface validation against the Phase 0 baseline.
**Independent Test**: `tests/dossier/test_events.py` collects and passes with
imports sourced from `spec_kitty_events`; `test_preserves_legacy_positional_order`
passes unmodified; the full NFR-003 targeted surface shows no regressions beyond
the Phase 0 baseline.
**Prompt**: `tasks/WP04-test-import-repointing-and-final-validation.md`
**Requirement Refs**: FR-009, FR-010, FR-001 (secondary — T020 is a binding
regression/identity proof for WP01's FR-001; WP01 remains the implementing WP)
**Owned files**: `tests/dossier/test_events.py`
**Dependencies**: WP03

### Included Subtasks

T018 Re-point `test_events.py`'s 7 mirror-type imports (`ArtifactIdentity`, `ContentHashRef`, `LocalNamespaceTuple`, the 4 `MissionDossier*Payload` classes; lines 23-30) to `spec_kitty_events`; leave the 4 `emit_*` imports unchanged (FR-009) (WP04)
T019 Verify `TestEmitSnapshotComputed::test_preserves_legacy_positional_order` (lines 317-342) needs zero edits and still passes (FR-010) (WP04)
T020 Add isinstance/identity assertions to `TestEmitArtifactIndexed`/`TestEmitArtifactMissing` proving the emitted payload's runtime type is the `spec_kitty_events`-owned class (spec.md Acceptance Scenario 1) (WP04)
T021 Final targeted-surface re-run across all 4 WPs' combined changes; diff against the T001 Phase 0 baseline; confirm zero mission-introduced regressions; append final tracer-file entries (WP04)

### Implementation Notes

- This is necessarily the last phase (per plan.md): the canonical types must exist
  at the new import location (WP01) before this file can import them from there,
  and it validates the end-state of every prior WP.

### Parallel Opportunities

- None.

### Dependencies

- Depends on WP03 (this tasks.md sequences the full chain linearly, matching
  plan.md's "Parallel Work Analysis" conclusion; FR-009/FR-010's only real file
  dependency is on WP01, not WP03, but the linear chain is kept for a simple,
  reviewable commit history per the charter's "Linear" PR requirement).

### Risks & Mitigations

- Accidentally editing `test_preserves_legacy_positional_order` while re-pointing
  the file's imports → T019 is a dedicated "verify zero edits" subtask specifically
  to guard against incidental changes to this test during the import sweep.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02 → WP03 → WP04 (strictly linear; no parallel `[P]`
  work packages — see plan.md "Parallel Work Analysis").
- **Parallelization**: None. This mission is explicitly not a good candidate for
  parallel-agent decomposition (tight file-level coupling between phases, ~620-750
  LOC total — see the TASKS-DECOMP-001 correction above).
- **MVP Scope**: WP01 is the mission's core deliverable (removes the boundary
  violation's two structural halves — mirror + bridge — that motivate the whole
  mission) but is not independently mergeable/valuable without WP02-WP04, since
  FR-006/FR-007/FR-011 (WP02) and FR-008 (WP03) are all "High" priority per
  spec.md and this mission ships as one PR (see "PR Shape Recommendation" above).
  There is no meaningful partial-mission MVP cut; all 4 WPs are required for the
  one PR this mission produces.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01, WP04 (WP04's T020 adds a binding regression/identity proof; WP01 remains the implementing WP) |
| FR-002 | WP01 |
| FR-003 | WP01 |
| FR-004 | WP01 |
| FR-005 | WP01 |
| FR-006 | WP02 |
| FR-007 | WP02 |
| FR-008 | WP03 |
| FR-009 | WP04 |
| FR-010 | WP04 |
| FR-011 | WP02 |
| NFR-001 (no net-new dependency) | WP01, WP02 (both import more of an already-pinned package; neither bumps the version constraint) |
| NFR-002 (validation stays visible) | WP02 (both `emitter.py`'s warning-print contract and `diagnose.py`'s `errors`-accumulator contract) |
| NFR-003 (test scope stays bounded) | WP01 (T001 baseline), WP04 (T021 final validation) — binding on every WP's own test runs throughout |
| C-001 (queue-drain out of scope) | N/A — no WP touches `sync/queue.py` or `sync/migrate_journal.py`; this is a negative constraint, not implemented by any WP |
| C-002 (no deprecated wrapper) | WP01 (bridge removal is a deletion, not a shim) |
| C-003 (baseline before attributing red) | WP01 (T001) |
| C-004 (terminology canon) | All WPs (prose discipline, not code) |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Phase 0 baseline capture | WP01 | P1 | No |
| T002 | Delete local mirror classes, import canonical types (FR-001) | WP01 | P1 | No |
| T003 | Confirm legacy `artifact_class="other"` remap survives (FR-002) | WP01 | P1 | No |
| T004 | Bridge removal + kwarg promotion, `emit_artifact_indexed` (FR-003/FR-004) | WP01 | P1 | No |
| T005 | Bridge removal + kwarg promotion + `last_known_ref` drop, `emit_artifact_missing` (FR-003/FR-004/FR-005) | WP01 | P1 | No |
| T006 | FR-004 binding regression test(s) in `test_dossier_pipeline.py` | WP01 | P1 | No |
| T007 | Add sentinel + `is_dossier_delegate()` predicate | WP02 | P1 | No |
| T008 | Replace 4 dossier `_PAYLOAD_RULES` entries with sentinel; fix type annotation (FR-006/FR-007) | WP02 | P1 | No |
| T009 | Add `_validate_dossier_payload` + early-return branch (FR-006) | WP02 | P1 | No |
| T010 | Coordinated `diagnose.py::_validate_payload` fix (FR-011) | WP02 | P1 | No |
| T011 | New `test_diagnose.py` dossier regression test(s) (FR-011) | WP02 | P1 | No |
| T012 | New `test_events.py` SC-005/FR-006 + FR-007 tests | WP02 | P1 | No |
| T013 | Rewrite `test_snapshot_emit.py` subscript-based test (FR-006) | WP02 | P1 | No |
| T014 | AST detector function (FR-008) | WP03 | P2 | No |
| T015 | Clean-tree assertion test (FR-008) | WP03 | P2 | No |
| T016 | Positive-control test (FR-008) | WP03 | P2 | No |
| T017 | Guard-file docstring/structure polish | WP03 | P2 | No |
| T018 | Re-point `test_events.py` mirror-type imports (FR-009) | WP04 | P1 | No |
| T019 | Verify positional-order regression test unmodified (FR-010) | WP04 | P1 | No |
| T020 | Add canonical-type identity assertions | WP04 | P1 | No |
| T021 | Final targeted-surface validation vs. Phase 0 baseline | WP04 | P1 | No |

---

> Generated by `/spec-kitty.tasks`. All prompt files live flat under
> `kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/tasks/`.
