---
work_package_id: WP04
title: Test Import Re-Pointing & Final Validation
dependencies: ["WP03"]
requirement_refs:
- FR-009
- FR-010
- FR-001
planning_base_branch: refactor/dossier-emitters-canonical-only-1058
merge_target_branch: refactor/dossier-emitters-canonical-only-1058
branch_strategy: Planning artifacts for this mission were generated on refactor/dossier-emitters-canonical-only-1058. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into refactor/dossier-emitters-canonical-only-1058 unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
phase: Phase 5 - test import re-pointing
history:
- at: '2026-08-22T12:25:40Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/dossier/test_events.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/dossier/test_events.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Test Import Re-Pointing & Final Validation

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

This is the mission's final WP — it closes the loop by re-pointing
`tests/dossier/test_events.py`'s type imports to the canonical
`spec_kitty_events` package (now that WP01 has made those types importable from
there), confirms the PR #1056 regression test needs zero edits, and runs this
mission's final validation pass against the Phase 0 baseline WP01 recorded.

- `tests/dossier/test_events.py`'s 7 mirror-type imports point at
  `spec_kitty_events` instead of `specify_cli.dossier.events` (FR-009); the 4
  `emit_*` function imports stay pointed at `specify_cli.dossier.events`
  unchanged (those functions still live there — only their internal type usage
  moved).
- `TestEmitSnapshotComputed::test_preserves_legacy_positional_order` (the live
  regression coverage for the PR #1056 snapshot positional-order bug) is
  preserved **unmodified** and still passes (FR-010).
- SC-001 through SC-006 all hold across the mission's combined diff — this WP's
  T021 is the final confirmation pass, not a new claim.
- T020's isinstance assertion — including its mandatory revert-and-confirm-red
  step — is a **binding** proof of FR-001/Acceptance Scenario 1's
  runtime-identity claim (tasks-review remediation, closes TASKS-VERIFY-001):
  it is not a judgment call or an optional addition, and this WP's scope is
  not complete without it.

## Context & Constraints

- Charter: `.kittify/charter/charter.md`.
- Spec: `kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/spec.md`
  — read FR-009, FR-010, and the Clarifications Q&A on "Do all three test files
  named in the issue need their imports re-pointed?" (answer: only
  `test_events.py` — `test_emitter_adapter.py` and `test_events_namespace.py`
  need zero changes, verified by reading their import blocks during
  specification; **do not touch either of those two files in this WP**).
- Plan: `kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/plan.md`
  — Phasing section's "Phase 5" entry explains why this is necessarily the last
  phase: the canonical types must exist at the new import location (WP01)
  before this file can import them from there, and this phase validates the
  end-state of every prior phase.
- This WP's only owned file is `tests/dossier/test_events.py`. Do not edit
  `tests/dossier/test_emitter_adapter.py` or `tests/sync/test_events_namespace.py`
  — both were verified during specification to need zero changes, and doing so
  would be an unscoped, out-of-map edit.

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

### Subtask T018 – Re-point `test_events.py` mirror-type imports (FR-009)

- **Purpose**: The test file that pins the four emitters' wire shape should
  import its expected types from the same place production code now does
  (`spec_kitty_events`, per WP01), so a future drift between "what the test
  asserts against" and "what production builds" cannot recur.
- **Steps**:
  1. In `tests/dossier/test_events.py`, locate the current import block
     (currently `test_events.py:23-30`):
     ```python
     from specify_cli.dossier.events import (
         ArtifactIdentity,
         ContentHashRef,
         LocalNamespaceTuple,
         MissionDossierArtifactIndexedPayload,
         MissionDossierArtifactMissingPayload,
         MissionDossierParityDriftDetectedPayload,
         MissionDossierSnapshotComputedPayload,
         emit_artifact_indexed,
         emit_artifact_missing,
         emit_parity_drift_detected,
         emit_snapshot_computed,
     )
     ```
  2. Split this into two import statements: the 7 type names
     (`ArtifactIdentity`, `ContentHashRef`, `LocalNamespaceTuple`,
     `MissionDossierArtifactIndexedPayload`,
     `MissionDossierArtifactMissingPayload`,
     `MissionDossierParityDriftDetectedPayload`,
     `MissionDossierSnapshotComputedPayload`) come from `spec_kitty_events` —
     use whichever concrete module path WP01's T002 confirmed via live
     introspection (do not guess a path independently here; match WP01's
     choice exactly, so both production and test code import from the same
     place). The 4 `emit_*` names stay imported from
     `specify_cli.dossier.events`, unchanged.
  3. Confirm the file collects and runs cleanly:
     `PWHEADLESS=1 .venv/bin/python -m pytest tests/dossier/test_events.py --collect-only -q`.
  4. **Named-test check (tasks-review remediation, closes TASKS-VERIFY-002):**
     run
     `PWHEADLESS=1 .venv/bin/python -m pytest tests/dossier/test_events.py::TestWirePayloadModelsRejectExtras::test_extras_rejected -v`
     and confirm it still passes, **unmodified**, against the canonical
     classes' `model_config` — plan.md's FR-001 Red-First row and spec.md's
     SC-003 both name this test explicitly as required to keep passing
     unmodified after this import-source edit (the canonical
     `spec_kitty_events` payload models must reject extra fields the same way
     the deleted local mirror classes did). This is the same dedicated,
     byte-for-byte treatment T019 gives the sibling named test
     `test_preserves_legacy_positional_order` — do not fold it into a generic
     "run the file" check.
- **Files**: `tests/dossier/test_events.py`.
- **Parallel?**: No — later subtasks in this WP depend on this import change
  being correct.
- **Notes**: This is purely an import-source edit — no other line in this test
  file's assertions should need to change as a result of this subtask alone
  (the canonical types have the same field names/shapes as the deleted mirror,
  by construction of WP01's FR-001).

### Subtask T019 – Verify positional-order regression test unmodified (FR-010)

- **Purpose**: `TestEmitSnapshotComputed::test_preserves_legacy_positional_order`
  (currently `test_events.py:317-342`) is the live regression coverage for the
  PR #1056 bug this whole file exists to guard against. `emit_snapshot_computed`
  never had the `*args`/`**kwargs` bridge this mission removes from the other
  two emitters (spec.md Clarifications), so its positional parameter order is
  untouched by every other WP in this mission — this subtask's job is to
  **confirm that stays true**, not to re-author the test.
- **Steps**:
  1. Diff `test_preserves_legacy_positional_order`'s body before and after
     T018's import-block edit — it must be byte-for-byte identical except for
     whatever whitespace/formatting your editor's auto-format might otherwise
     touch (avoid running a blanket formatter over the whole file; if your
     tooling reformats on save, revert unrelated formatting changes to this
     specific test).
  2. Run it standalone and confirm it passes:
     `PWHEADLESS=1 .venv/bin/python -m pytest tests/dossier/test_events.py::TestEmitSnapshotComputed::test_preserves_legacy_positional_order -q`.
  3. If it fails, this is a **stop-and-investigate** signal, not something to
     "fix" by adjusting the test — it means some other WP's change (most likely
     WP01) altered `emit_snapshot_computed`'s signature or behavior, which is
     out of this mission's scope per spec.md Clarifications. Escalate rather
     than silently patch the test to match new behavior.
- **Files**: `tests/dossier/test_events.py` (verification only — this subtask
  should produce **zero** diff to this specific test's body).
- **Parallel?**: No.
- **Notes**: This subtask exists specifically as a dedicated "did anything
  incidentally touch this" guard, separate from T018's mechanical import
  change, because it is easy for an import-sweep edit to accidentally reflow
  or touch nearby code without noticing.

### Subtask T020 – Add canonical-type identity assertions (binding, FR-001/Acceptance Scenario 1)

- **Purpose**: Prove FR-001/Acceptance Scenario 1's isinstance claim directly:
  after WP01 deletes the local mirror, the payload each emitter builds is
  actually an instance of the `spec_kitty_events`-owned class, not merely "a
  dict that happens to look the same." **This is a binding requirement, not
  optional** (tasks-review remediation, closes TASKS-VERIFY-001): plan.md's
  FR-001 Red-First row requires an isinstance/identity check specifically
  because a jsonschema shape-only check cannot distinguish the canonical class
  from a local mirror class that duplicates the same field names by
  construction (see plan.md "Why the local mirror survived the existing
  boundary gate") — a reverted FR-001 that reintroduces a mirror-shaped class
  would still pass every existing `_assert_valid`/`jsonschema.validate`
  assertion in this file unchanged, so those assertions alone cannot catch the
  revert.
- **Steps**:
  1. In `TestEmitArtifactIndexed` and `TestEmitArtifactMissing` (the existing
     test classes in this file exercising `emit_artifact_indexed`/
     `emit_artifact_missing`), add a test seam that captures the
     **pre-serialization payload object** — not the already-serialized dict
     `captured_emissions` records. Both emitters build a
     `MissionDossierArtifactIndexedPayload`/`MissionDossierArtifactMissingPayload`
     instance and immediately call `payload.model_dump(exclude_none=True)` on
     it before handing the dict to `fire_dossier_event`; `captured_emissions`
     only ever sees the resulting dict. Capture the object itself by
     monkeypatching the canonical payload class's `model_dump` method
     (matching this file's existing `monkeypatch.setattr` idiom already used
     by the `captured_emissions` fixture) to record `self` before delegating
     to the original method, e.g.:
     ```python
     captured_payload_objects: list[object] = []
     original_model_dump = MissionDossierArtifactIndexedPayload.model_dump

     def _capturing_model_dump(self, *args, **kwargs):
         captured_payload_objects.append(self)
         return original_model_dump(self, *args, **kwargs)

     monkeypatch.setattr(
         MissionDossierArtifactIndexedPayload, "model_dump", _capturing_model_dump
     )
     ```
     (mirror the same pattern for `MissionDossierArtifactMissingPayload` in
     `TestEmitArtifactMissing`). This is a test-side seam only — no production
     code changes. **Note for step 3**: this patches `model_dump` on the
     canonical class object specifically. Step 3's revert-and-confirm-red swap
     rebinds the name inside `specify_cli.dossier.events`'s module namespace to
     a *different* class object, so `emit_artifact_indexed`/
     `emit_artifact_missing` construct an instance of that swapped-in class
     instead — the canonical class's patched `model_dump` above would never
     fire and `captured_payload_objects` would stay empty. Step 3 extends this
     same `_capturing_model_dump` wrapper to the swapped-in mirror class too,
     so the capture seam keeps recording whichever class is actually bound at
     call time.
  2. Assert `isinstance(captured_payload_objects[0], MissionDossierArtifactIndexedPayload)`
     — and the `MissionDossierArtifactMissingPayload` equivalent in
     `TestEmitArtifactMissing` — directly, on at least one emitted payload per
     emitter under test in this subtask's scope (`emit_artifact_indexed`,
     `emit_artifact_missing`). This isinstance assertion is the binding proof
     of FR-001/Acceptance Scenario 1; it must be present in the diff, not
     merely considered and skipped.
  3. **Mandatory revert-and-confirm-red step** (matching the pattern already
     required by T006/WP01, T011/T012/WP02, and T016/WP03 — do not skip this):
     temporarily stub/reintroduce a mirror-shaped class in place of the
     canonical import — a class with identical field names/types to
     `MissionDossierArtifactIndexedPayload` but a distinct identity (e.g.
     define it inline in the test module and
     `monkeypatch.setattr(specify_cli.dossier.events, "MissionDossierArtifactIndexedPayload", <mirror class>)`,
     or temporarily edit the production import). **Also apply the same
     `_capturing_model_dump` wrapper from step 1 to this mirror class's
     `model_dump`** (patch it at definition time, before swapping it in) — the
     emitters construct whichever class is currently bound to the name in
     `specify_cli.dossier.events`'s module namespace, so without this the
     canonical class's step-1 patch never fires post-swap and
     `captured_payload_objects` stays empty, producing an `IndexError` at step
     2 instead of a real isinstance comparison. With both classes' `model_dump`
     patched, confirm:
     - the new isinstance assertion (step 2) goes **red** — it evaluates
       against the captured mirror-class instance and `isinstance(...)`
       returns `False`, not an `IndexError` from an empty capture list — and
     - this file's existing `jsonschema.validate`/`_assert_valid` assertions
       stay **green** against the same mirror-shaped payload.
     That divergence is the concrete demonstration that the isinstance check,
     not the shape-only schema check, is what actually detects an FR-001
     revert. Revert your temporary change (including the mirror class's
     `model_dump` patch) before finishing.
- **Files**: `tests/dossier/test_events.py`.
- **Parallel?**: No — depends on T018.
- **Notes**: This file's existing `jsonschema.validate`-based assertions
  (already present per this file's own docstring: "These tests pin the wire
  shape produced by the four dossier event emitters against the canonical
  spec_kitty_events>=5.0.0 server schemas") are shape proof, not identity
  proof — they do not substitute for the isinstance check this subtask adds.
  There is no "minimal addition or none" option: the isinstance assertion and
  its red-first proof (step 3) are both required for this subtask to be done.

### Subtask T021 – Final targeted-surface validation vs. Phase 0 baseline

- **Purpose**: This mission's closing regression check — confirm the combined
  diff from all 4 WPs introduces zero regressions beyond the Phase 0 baseline
  WP01's T001 recorded.
- **Steps**:
  1. Run the full NFR-003 targeted surface:
     ```bash
     PWHEADLESS=1 .venv/bin/python -m pytest \
       tests/dossier/ tests/sync/test_events_namespace.py \
       tests/sync/test_dossier_pipeline.py tests/sync/test_diagnose.py \
       tests/architectural/ -q
     ```
  2. Diff the resulting red/error set against WP01's T001 baseline (recorded in
     `kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/tracer-tooling-friction.md`).
  3. Confirm every SC-001 through SC-006 measurable outcome in spec.md holds
     (re-read spec.md's "Success Criteria" section and check each one
     concretely — most already have dedicated tests from prior WPs; this is a
     final cross-check, not new test-writing, unless a gap surfaces).
  4. If any newly-red test beyond the baseline is found, it is this mission's
     own regression — fix it before considering the mission done, do not defer
     it silently.
  5. Append a final entry to
     `kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/tracer-tooling-friction.md`
     (design decisions made during implementation that differed from plan.md's
     sketch, if any; tooling friction encountered) per the charter's "assess at
     close" step for mission tracer files (Standing Order #3) — append, do not
     overwrite existing content.
- **Files**: `kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/tracer-tooling-friction.md`
  (append only).
- **Parallel?**: No — final subtask of the final WP.
- **Notes**: Do **not** run the full `pytest tests/` here — NFR-003 explicitly
  reserves that for pre-merge/post-merge validation, a separate step outside
  this mission's WP scope (handled by `/spec-kitty.review`/CI, not this WP).

## Test Strategy

- **Scope** (NFR-003): `tests/dossier/`, `tests/sync/test_events_namespace.py`,
  `tests/sync/test_dossier_pipeline.py`, `tests/sync/test_diagnose.py`,
  `tests/architectural/`. Do not broaden to `pytest tests/`.
- T019 must produce zero diff to `test_preserves_legacy_positional_order`'s
  body — treat any diff there as a bug to investigate, not a formatting
  nicety.
- T021 is a diff-against-baseline exercise, not a fresh green-field pass —
  compare against WP01's recorded T001 baseline explicitly.

## Risks & Mitigations

- **Wrong import path guessed for the canonical types** (T018) → do not guess
  independently; match whatever concrete module path WP01's T002 already
  confirmed via live introspection, so production and test code stay
  consistent.
- **Accidental edit to the PR #1056 regression test during the import sweep**
  → T019 is a dedicated verification subtask for exactly this risk.
- **Declaring victory without actually diffing against the Phase 0 baseline**
  → T021 requires the explicit diff step, not just "tests pass now."

## Review Guidance

- Confirm the 4 `emit_*` function imports in `test_events.py` are unchanged
  (still from `specify_cli.dossier.events`).
- Confirm `test_preserves_legacy_positional_order` has zero body diff.
- Confirm `test_extras_rejected` (`TestWirePayloadModelsRejectExtras`) was run
  after T018's import swap and passes unmodified against the canonical
  classes, per SC-003 / plan.md's FR-001 row (closes TASKS-VERIFY-002).
- Confirm T020's isinstance/identity assertion is present and binding — not
  satisfied by a jsonschema-only shape check — and that its revert-and-confirm-
  red step was actually performed (mirror-shaped class swapped in, isinstance
  assertion observed red, existing jsonschema assertions observed still green)
  and reverted afterward. FR-001/Acceptance Scenario 1's isinstance claim must
  be proven directly by this new assertion, not only via schema validation
  (closes TASKS-VERIFY-001).
- Confirm the final targeted-surface run's red/error set was actually diffed
  against WP01's recorded baseline, and that any surplus red found was fixed
  (not deferred).
- Confirm `tests/dossier/test_emitter_adapter.py` and
  `tests/sync/test_events_namespace.py` were not touched by this WP.
- Confirm the final tracer-file entry was appended, not used to overwrite
  prior mission-phase entries.

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
