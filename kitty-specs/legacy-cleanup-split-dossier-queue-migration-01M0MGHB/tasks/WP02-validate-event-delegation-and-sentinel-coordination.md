---
work_package_id: WP02
title: validate_event() Delegation & Sentinel Coordination
dependencies: ["WP01"]
requirement_refs:
- FR-006
- FR-007
- FR-011
planning_base_branch: refactor/dossier-emitters-canonical-only-1058
merge_target_branch: refactor/dossier-emitters-canonical-only-1058
branch_strategy: Planning artifacts for this mission were generated on refactor/dossier-emitters-canonical-only-1058. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into refactor/dossier-emitters-canonical-only-1058 unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T013
phase: Phase 3 - validate_event delegation with sentinel reconciliation
history:
- at: '2026-08-22T12:25:40Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/emitter.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/sync/emitter.py
- src/specify_cli/sync/diagnose.py
- tests/sync/test_events.py
- tests/dossier/test_snapshot_emit.py
- tests/sync/test_diagnose.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – validate_event() Delegation & Sentinel Coordination

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the
frontmatter (or any user-defined profile), and behave according to its guidance
before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the
best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via
  `spec-kitty agent tasks status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items
  are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log
  explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in
the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

This WP bundles two sub-concerns that must land together, atomically, in one
commit (tasks-review remediation, closes TASKS-DECOMP-002): **(1)** the sentinel
delegation mechanism in `emitter.py` (FR-006/FR-007 — replacing the four
hand-maintained dossier `_PAYLOAD_RULES` entries with a reconciling sentinel),
and **(2)** the coordinated `diagnose.py` consumer fix (FR-011 — the second,
independent consumer of the same `_PAYLOAD_RULES` dict that would otherwise
crash on the sentinel alone).

- `src/specify_cli/sync/emitter.py`'s `_PAYLOAD_RULES` table replaces its four
  hand-maintained dossier validation rules with a delegation to
  `spec_kitty_events.conformance.validate_event(payload, event_type,
  strict=True)`, behind a reconciling sentinel — SC-005: a hand-constructed
  invalid dossier payload run through `EventEmitter._validate_payload()` returns
  `False` and the captured warning contains a real field/violation identifier
  sourced from `ConformanceResult`, not the old generic message.
- The four dossier event-type strings remain members of `VALID_EVENT_TYPES`
  (FR-007) — the sentinel does not remove them from `_PAYLOAD_RULES`, only
  changes what their dict *value* means.
- `src/specify_cli/sync/diagnose.py::_validate_payload` — a second, independent
  free-function consumer of the **same** `_PAYLOAD_RULES` dict — is coordinated
  in the same commit so it does not crash on a dossier event (SC-006:
  `diagnose_events()` no longer raises `AttributeError` on a dossier-typed
  queued event; the invalid case reports a real `ConformanceResult`-sourced
  violation in `DiagnoseResult.errors`).
- `tests/dossier/test_snapshot_emit.py`'s existing subscript-based test is
  rewritten to match the new delegation behavior (it would otherwise raise
  `TypeError: 'object' object is not subscriptable` the moment the sentinel
  lands).

**This is the mission's one genuine chokepoint** — see tasks.md's "⚠️ Chokepoint
Called Out Explicitly" section. All 5 files this WP owns land in **one commit**.
Do not split the `emitter.py` sentinel change from the `diagnose.py` coordinated
fix into separate commits/WPs — an intermediate state with only the sentinel
landed crashes `diagnose_events()` on any dossier event in the local offline
queue (the normal case for any active mission using dossier tracking).

## Context & Constraints

- Charter: `.kittify/charter/charter.md`.
- Spec: `kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/spec.md`
  — read FR-006, FR-007, FR-011, and the "Key Entities" section's
  "Reconciling FR-006 and FR-007" paragraph in full.
- Plan: `kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/plan.md`
  — read "FR-006/FR-007 sentinel shape (concrete design)" and "`diagnose.py`
  coordinated fix" sections in full; they give the exact code shape this WP
  implements, reproduced/adapted below but the plan is the canonical source if
  anything here is ambiguous.
- **⚠️ Rebase-check before starting**: `src/specify_cli/sync/emitter.py` is also
  touched by the currently-open PR #3655, which works `_emit()`'s routing region
  (~line 2350). This WP works a different region — `_PAYLOAD_RULES` (currently
  `emitter.py:827-876`), `VALID_EVENT_TYPES` (`:897`), `_validate_payload`
  (`:2549-2587`). Low collision risk, but re-diff `emitter.py` against `main`
  immediately before editing, since line numbers will have drifted since WP01
  landed.
- Depends on WP01: the canonical types WP01 imported are not directly used here,
  but this WP is sequenced after WP01 in plan.md's Phasing for a simpler linear
  reviewable commit history (charter's "Linear" PR requirement).

## Branch Strategy

- **Strategy**: Planning artifacts for this mission were generated directly on
  `refactor/dossier-emitters-canonical-only-1058` (this mission's own target
  branch — not `main`). Execution worktrees are allocated per computed lane from
  `lanes.json`; completed changes merge back into
  `refactor/dossier-emitters-canonical-only-1058`.
- **Planning base branch**: `refactor/dossier-emitters-canonical-only-1058`
- **Merge target branch**: `refactor/dossier-emitters-canonical-only-1058`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T007 – Add sentinel + `is_dossier_delegate()` predicate

- **Purpose**: `_validate_payload`'s single generic code path treats every
  `_PAYLOAD_RULES[event_type]` value uniformly as `{"required": set[str],
  "validators": dict[str, Callable]}`. FR-006 (delegate the 4 dossier types) and
  FR-007 (keep the 4 dossier keys recognized) cannot both hold without the
  generic loop misinterpreting the new dossier value shape — a sentinel resolves
  this.
- **Steps**:
  1. In `src/specify_cli/sync/emitter.py`, module-level, immediately before the
     `_PAYLOAD_RULES` dict definition (currently `emitter.py:523`), add:
     ```python
     _DOSSIER_VALIDATE_EVENT_DELEGATE = object()  # sentinel: see is_dossier_delegate() below

     _DOSSIER_EVENT_TYPES = frozenset({
         "MissionDossierArtifactIndexed",
         "MissionDossierArtifactMissing",
         "MissionDossierSnapshotComputed",
         "MissionDossierParityDriftDetected",
     })


     def is_dossier_delegate(rules: object) -> bool:
         """True if *rules* is the dossier validate_event() delegation sentinel."""
         return rules is _DOSSIER_VALIDATE_EVENT_DELEGATE
     ```
  2. This predicate is the **only** place in the whole mission's diff that
     references `_DOSSIER_VALIDATE_EVENT_DELEGATE` directly by identity — every
     other consumer (T009's `emitter.py::_validate_payload`, T010's
     `diagnose.py::_validate_payload`) calls `is_dossier_delegate(rules)`
     instead of re-implementing the `is` comparison. Keep it that way.
- **Files**: `src/specify_cli/sync/emitter.py`.
- **Parallel?**: No — every later subtask in this WP depends on this predicate
  existing.
- **Notes**: Why a sentinel object rather than a magic string or a
  `{"__delegate__": True}` dict marker — an `object()` sentinel is unambiguous
  under `is` identity comparison (no accidental collision with a real
  `{"required": ..., "validators": ...}` dict that happens to contain a
  similarly-named key), costs nothing, and needs no new imported type.

### Subtask T008 – Replace 4 dossier `_PAYLOAD_RULES` entries with sentinel; fix type annotation (FR-006, FR-007)

- **Purpose**: Physically swap the four dossier entries' dict values for the
  sentinel, while keeping the four keys present (so `VALID_EVENT_TYPES =
  frozenset(_PAYLOAD_RULES.keys())`, unchanged at `emitter.py:897`, still
  includes them — FR-007's unknown-event-type rejection check at
  `emitter.py:2514` keeps working identically).
- **Steps**:
  1. Replace the four dict entries currently at `emitter.py:827-876`
     (`"MissionDossierArtifactIndexed": {...}`, `"MissionDossierArtifactMissing":
     {...}`, `"MissionDossierSnapshotComputed": {...}`,
     `"MissionDossierParityDriftDetected": {...}`, each currently a
     `{"required": {...}, "validators": {...}}` dict) with:
     ```python
     "MissionDossierArtifactIndexed": _DOSSIER_VALIDATE_EVENT_DELEGATE,
     "MissionDossierArtifactMissing": _DOSSIER_VALIDATE_EVENT_DELEGATE,
     "MissionDossierSnapshotComputed": _DOSSIER_VALIDATE_EVENT_DELEGATE,
     "MissionDossierParityDriftDetected": _DOSSIER_VALIDATE_EVENT_DELEGATE,
     ```
     (all four keys point at the *same* sentinel object — there is nothing
     per-event-type left to carry in the dict value once delegation is the
     whole story; the event-type string itself is passed through to
     `validate_event(payload, event_type, strict=True)` at call time).
  2. Update the module-level `_PAYLOAD_RULES` type annotation from
     `_PAYLOAD_RULES: dict[str, dict[str, Any]] = {` to
     `_PAYLOAD_RULES: dict[str, dict[str, Any] | object] = {` — this repo's
     Code Style bar (`CLAUDE.md`) requires new code to pass `ruff`/`mypy` clean
     even though `mypy --strict` is CI-advisory-only; leaving the old annotation
     in place with a sentinel value inside it is a real type-checking violation.
  3. Delete the two now-unused validator helper functions referenced only by
     the deleted dossier entries, **if** they are not used elsewhere — check
     `_is_canonical_snapshot_hash` and any dossier-only lambdas' backing
     functions with `grep -rn "_is_canonical_snapshot_hash" src/` first (this
     symbol is also directly referenced by `tests/dossier/test_snapshot_emit.py`,
     which T013 rewrites — do not delete `_is_canonical_snapshot_hash` itself
     unless T013 confirms nothing needs it post-rewrite; if in doubt, leave the
     helper function defined and only remove its wiring into `_PAYLOAD_RULES`).
- **Files**: `src/specify_cli/sync/emitter.py`.
- **Parallel?**: No — depends on T007.
- **Notes**: Do not touch any non-dossier `_PAYLOAD_RULES` entry (e.g.
  `MissionOriginBound`, `WPStatusChanged`, etc.) — this mission's scope is the
  four dossier keys only.

### Subtask T009 – Add `_validate_dossier_payload` + early-return branch (FR-006)

- **Purpose**: Make `EventEmitter._validate_payload` recognize the sentinel and
  delegate to `validate_event()`, translating `ConformanceResult.valid` into the
  existing `bool` contract every other `_PAYLOAD_RULES` entry already has (per
  spec.md Clarifications — `validate_event` does not raise on an invalid
  payload; it returns a `ConformanceResult` with `.valid`/`.model_violations`/
  `.schema_violations`).
- **Steps**:
  1. In `EventEmitter` (class starts `emitter.py:945`), add a new private
     method, matching this file's existing lazy-import convention (e.g. `Event
     as EventModel` imported locally inside `_validate_event`, `emitter.py:2477`
     — there is no module-scope `spec_kitty_events` type import anywhere in
     `emitter.py` today):
     ```python
     def _validate_dossier_payload(self, event_type: str, payload: dict[str, Any]) -> bool:
         from spec_kitty_events.conformance import validate_event

         result = validate_event(payload, event_type, strict=True)
         if not result.valid:
             violations = [str(v) for v in (*result.model_violations, *result.schema_violations)]
             _console.print(f"[yellow]Warning: {event_type} payload invalid: {'; '.join(violations)}[/yellow]")
         return result.valid
     ```
  2. In `_validate_payload` (currently `emitter.py:2549`), add an early-return
     branch ahead of the existing generic `rules["required"]`/
     `rules["validators"]` access:
     ```python
     def _validate_payload(self, event_type: str, payload: dict[str, Any]) -> bool:
         rules = _PAYLOAD_RULES.get(event_type)
         if rules is None:
             return True
         if is_dossier_delegate(rules):
             return self._validate_dossier_payload(event_type, payload)
         # ... existing generic required/validators loop, unchanged ...
     ```
     Preserve every line of the existing generic loop below the new branch
     unchanged — this subtask only inserts the branch, it does not touch the
     non-dossier path.
- **Files**: `src/specify_cli/sync/emitter.py`.
- **Parallel?**: No — depends on T007/T008.
- **Notes**: `_console` is already the module's existing print target used
  throughout `_validate_event`/`_validate_payload` — reuse it, do not introduce
  a new logger/console instance.

### Subtask T010 – Coordinated `diagnose.py::_validate_payload` fix (FR-011)

- **Purpose**: `src/specify_cli/sync/diagnose.py::_validate_payload` (a
  module-level free function, distinct from but currently shape-compatible with
  `emitter.py`'s method — imported at `diagnose.py:51`, `from .emitter import
  _PAYLOAD_RULES, VALID_AGGREGATE_TYPES`) does `rules.get("required", set())` /
  `rules.get("validators", {})` with **no shape guard**. The moment T008 lands,
  any dossier event reaching this function crashes `diagnose_events()` (the
  entry point for the production `spec-kitty sync diagnose` CLI command) with
  `AttributeError: 'object' object has no attribute 'get'`.
- **Steps**:
  1. In `src/specify_cli/sync/diagnose.py`, update the import at `diagnose.py:51`
     to also pull in the predicate: `from .emitter import (_PAYLOAD_RULES,
     VALID_AGGREGATE_TYPES, is_dossier_delegate)`.
  2. In `diagnose.py::_validate_payload` (module-level free function, currently
     around `diagnose.py:289`), add the guarded branch **before** any
     dict-shaped access:
     ```python
     def _validate_payload(event_type, payload, errors):
         rules = _PAYLOAD_RULES.get(event_type)
         if rules is None:
             return
         if is_dossier_delegate(rules):
             from spec_kitty_events.conformance import validate_event

             result = validate_event(payload, event_type, strict=True)
             if not result.valid:
                 errors.extend(
                     str(v) for v in (*result.model_violations, *result.schema_violations)
                 )
             return
         # ... existing generic required/validators loop, unchanged ...
     ```
  3. Note the contract difference from `emitter.py`'s version: `diagnose.py`'s
     established shape is "return structured errors" (append to the `errors:
     list[str]` accumulator its caller passes in), **not** "print a warning."
     Do not add a `_console.print`/`print` call here — that would be a new,
     inconsistent side channel this function's contract does not have anywhere
     else (NFR-002's second half is explicit that this function's visibility
     contract is `DiagnoseResult.errors`, not a printed warning).
- **Files**: `src/specify_cli/sync/diagnose.py`.
- **Parallel?**: No — depends on T007 (`is_dossier_delegate` must exist to
  import).
- **Notes**: `diagnose_events()` reaches this unconditionally whenever
  `event_type in _PAYLOAD_RULES` (`diagnose.py:215`-ish, inside
  `_validate_event`'s "3. Payload validation" step) — this is why the fix must
  land in the same commit as T008, not a follow-up.

### Subtask T011 – New `test_diagnose.py` dossier regression test(s) (FR-011)

- **Purpose**: Close the coverage gap T010 fixes — zero existing tests in
  `tests/sync/test_diagnose.py` exercise a dossier event type today (grepped,
  zero `dossier` hits as of specification).
- **Steps**:
  1. Add a new test (or a small set) to `tests/sync/test_diagnose.py` that
     builds a dossier-typed event dict (e.g. `event_type="MissionDossierArtifactIndexed"`
     with a minimal valid `payload`) and drives it through `diagnose_events()`
     (the public entry point — do not call `_validate_payload` directly here;
     exercise the real integration path this function's coordination protects).
  2. Assert **(a) no crash**: the call completes and returns a `DiagnoseResult`
     (or list thereof, matching this file's existing return-shape convention)
     without raising `AttributeError`.
  3. Assert **(b) a valid payload reports no error**, and a **deliberately
     invalid** payload (e.g. omit a required field like `namespace`) reports a
     real violation string in `DiagnoseResult.errors`, sourced from
     `ConformanceResult` (i.e. it should name the actual missing/invalid field,
     not a generic message).
  4. Confirm this test goes red if T010's guarded branch is reverted (locally,
     temporarily) — the revert should reproduce the `AttributeError` this test
     exists to prevent. Revert your temporary change before finishing.
- **Files**: `tests/sync/test_diagnose.py` (existing file — this is new test
  content added to it, not a new file).
- **Parallel?**: No — depends on T010.
- **Notes**: Follow this file's existing fixture/helper conventions (event dict
  shape, `DiagnoseResult` construction pattern) rather than inventing a new
  style — read a few existing tests in this file first for the established
  idiom.

### Subtask T012 – New `test_events.py` SC-005/FR-006 + FR-007 tests

- **Purpose**: Prove SC-005 directly against `EventEmitter._validate_payload()`
  (the emitter-side half of the delegation, distinct from T011's diagnose-side
  coverage), and add a small FR-007 regression proving the sentinel change
  doesn't remove the dossier keys from `VALID_EVENT_TYPES`.
- **Steps**:
  1. In `tests/sync/test_events.py` (this file already has a `TestValidation`
     class at `test_events.py:642` and a `TestInternalValidation` class at
     `test_events.py:935` exercising `EventEmitter._validate_payload`/
     `_validate_event` for non-dossier event types — follow that established
     pattern rather than inventing a new one), add a test that:
     - Constructs an `EventEmitter` instance (mirror the existing
       `emitter`/`temp_queue` fixture usage in this file).
     - Hand-constructs an **invalid** dossier payload (e.g.
       `{"namespace": {...}, "artifact_id": {...}, "content_ref": {...}}`
       missing the required `indexed_at` field for
       `MissionDossierArtifactIndexed`).
     - Calls `emitter._validate_payload("MissionDossierArtifactIndexed", payload)`
       directly (this is a private method but is already the established
       testing seam other tests in this file use for internal validation paths
       — see `TestInternalValidation`).
     - Asserts it returns `False`, **and** captures the printed warning
       (`capsys`/`caplog`, matching whatever capture mechanism this file's
       existing warning-assertion tests already use) and asserts the warning
       text contains a real field/violation identifier (e.g. `indexed_at`),
       not the old generic "field has invalid value" phrasing.
  2. Add a second, small test confirming all four dossier event-type strings
     are still members of `VALID_EVENT_TYPES` after the sentinel change (import
     `VALID_EVENT_TYPES` from `specify_cli.sync.emitter` and assert
     `{"MissionDossierArtifactIndexed", "MissionDossierArtifactMissing",
     "MissionDossierSnapshotComputed", "MissionDossierParityDriftDetected"} <=
     VALID_EVENT_TYPES`), and that an unknown/typo'd event type
     (`"MissionDossierBogus"`) is still rejected via the existing
     unknown-event-type branch.
- **Files**: `tests/sync/test_events.py`.
- **Parallel?**: No — depends on T009.
- **Notes**: This is the emitter-side proof; T011 is the diagnose-side proof.
  Both are required — they exercise two independent code paths that both read
  the same `_PAYLOAD_RULES` dict.

### Subtask T013 – Rewrite `test_snapshot_emit.py` subscript-based test (FR-006)

- **Purpose**: `tests/dossier/test_snapshot_emit.py::test_emit_rule_wires_canonical_validator_for_hash_fields`
  (currently `test_snapshot_emit.py:220-228`) directly subscripts
  `_PAYLOAD_RULES["MissionDossierSnapshotComputed"]["validators"]` and
  `_PAYLOAD_RULES["MissionDossierParityDriftDetected"]["validators"]`, asserting
  the wired validator callable `is _is_canonical_snapshot_hash`. Once T008
  replaces those two entries with the sentinel, this raises `TypeError: 'object'
  object is not subscriptable` at test-run time.
- **Steps**:
  1. Delete (or fully rewrite) the current body of
     `test_emit_rule_wires_canonical_validator_for_hash_fields`.
  2. Replace it with an assertion against the new delegation behavior: construct
     a `MissionDossierSnapshotComputed` (and/or
     `MissionDossierParityDriftDetected`) payload with a malformed
     `snapshot_hash`/`expected_hash`/`actual_hash` value (i.e. something
     `_is_canonical_snapshot_hash` used to reject — reuse this file's existing
     `test_rejects_malformed`'s parametrized bad-hash values just above this
     test, at `test_snapshot_emit.py:202-218`, as your source of known-bad
     values) and assert it surfaces as a violation via
     `EventEmitter._validate_dossier_payload`'s `ConformanceResult` translation
     — the same real-violation-detail assertion shape as T012's FR-006 test.
  3. This may require importing `EventEmitter` (or reusing whatever fixture
     `tests/sync/test_events.py` uses, if this test file already has access to
     one — check imports first) into this test file if it doesn't already have
     that access; alternatively, call `validate_event()` directly against the
     malformed payload if that better matches this file's existing scope (this
     file currently tests `_is_canonical_snapshot_hash` directly, a lower-level
     unit than `EventEmitter` — prefer staying at that same altitude if
     possible, i.e. testing that the malformed hash is rejected by the
     canonical schema/model via `validate_event()`, rather than pulling in a
     full `EventEmitter` instance if this file doesn't already do that
     elsewhere).
- **Files**: `tests/dossier/test_snapshot_emit.py`.
- **Parallel?**: No — depends on T008 (must exist to trigger the
  `TypeError` this rewrite fixes) and pairs with T012 (same delegation
  behavior, exercised from a different starting fixture).
- **Notes**: This test is physically inside `tests/dossier/`, already in this
  mission's NFR-003 test scope — it is a required rewrite, not new test
  surface.

## Test Strategy

- **Scope** (NFR-003): run
  `PWHEADLESS=1 .venv/bin/python -m pytest tests/dossier/
  tests/sync/test_events_namespace.py tests/sync/test_events.py
  tests/sync/test_diagnose.py -q` after each
  subtask; the full `pytest tests/` run is reserved for pre-merge/post-merge
  validation.
- All 7 subtasks land in **one commit** (this WP's chokepoint constraint) — do
  not commit T007-T009 (`emitter.py` only) separately from T010-T011
  (`diagnose.py` + its test), even if your tooling would let you.
- Confirm T011's and T012's tests both go red against a temporary local revert
  of their respective guarded branch (T010, T009) before finishing, per this
  mission's charter-bound ATDD discipline.
- Baseline gate: after this WP's commit, re-run the T001 (WP01) targeted
  surface and diff against the recorded baseline — only newly-red tests beyond
  the baseline are this WP's own regressions to fix before WP03 starts.

## Risks & Mitigations

- **Landing the `emitter.py` sentinel without the `diagnose.py` coordination**
  → the single highest risk in this WP; mitigated by owning both files in this
  one WP/commit and by T011's regression test specifically targeting the crash.
- **`emitter.py`/PR #3655 rebase collision** → re-diff against `main` before
  starting (see "⚠️ Rebase-check before starting" above); the two changes touch
  different regions of the same file but confirm before assuming zero overlap.
- **Deleting a validator helper (`_is_canonical_snapshot_hash`) still needed by
  T013's rewritten test** → T008's step 3 explicitly flags this; do the
  `_PAYLOAD_RULES` wiring removal and T013's test rewrite in careful order, or
  verify usage with a full-repo grep before deleting anything.
- **`_console.print` in `diagnose.py`** — do not introduce one; this function's
  contract is `errors: list[str]`, not a printed warning (see T010 notes).

## Review Guidance

- Confirm `is_dossier_delegate()` is defined exactly once (T007) and every
  other consumer (`emitter.py::_validate_payload`, `diagnose.py::_validate_payload`)
  calls it rather than re-implementing the `is` comparison.
- Confirm `VALID_EVENT_TYPES` (`emitter.py:897`) is unchanged in definition
  (`frozenset(_PAYLOAD_RULES.keys())`) and still contains all four dossier keys
  after T008.
- Confirm `diagnose.py::_validate_payload`'s fix uses the `errors` accumulator,
  not a print statement.
- Confirm SC-005 and SC-006 both hold via the new tests (T011, T012), not just
  by inspection.
- Confirm T013's rewrite no longer references the sentinel-holding dict entries
  by subscript anywhere.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:

```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>
```

**Common mistakes (DO NOT DO THIS)**:

- Adding new entry at the top (breaks chronological order)
- Using future timestamps (causes acceptance validation to fail)
- Inserting in middle instead of appending to end

**Why this matters**: The acceptance system reads the LAST activity log entry as
the current state. If entries are out of order, acceptance will fail even when
the work is complete.

**Initial entry**:

- 2026-08-22T12:25:40Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use
`spec-kitty agent tasks move-task <WPID> --to <status>` to change WP status.

### Optional Phase Subdirectories

For large features, organize prompts under `tasks/` to keep bundles grouped
while maintaining lexical ordering.
