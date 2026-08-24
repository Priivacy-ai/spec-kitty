---
work_package_id: WP01
title: Canonical Type Adoption & Legacy Bridge Removal
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
planning_base_branch: refactor/dossier-emitters-canonical-only-1058
merge_target_branch: refactor/dossier-emitters-canonical-only-1058
branch_strategy: Planning artifacts for this mission were generated on refactor/dossier-emitters-canonical-only-1058. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into refactor/dossier-emitters-canonical-only-1058 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 0+1+2 - Baseline, mirror deletion, bridge removal
history:
- at: '2026-08-22T12:25:40Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/dossier/events.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/dossier/events.py
- tests/sync/test_dossier_pipeline.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Canonical Type Adoption & Legacy Bridge Removal

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

This WP closes the mission's structural core: `src/specify_cli/dossier/events.py`
currently hand-maintains a ~24KB, 653-line local Pydantic mirror of types that
the external contract package `spec-kitty-events` (installed 6.1.0, pinned
`>=6.0.0,<7.0.0`) already owns, and two of its four emitters carry a legacy
`*args`/`**kwargs` compatibility parser. By the end of this WP:

- `dossier/events.py` contains **zero** locally-defined Pydantic model classes
  duplicating `spec_kitty_events` shapes (SC-001: `grep -c "^class.*BaseModel"
  src/specify_cli/dossier/events.py` returns `0`, down from `7`).
- `emit_artifact_indexed` and `emit_artifact_missing` have **zero**
  `*args`/`**kwargs`-style parameters (SC-002: `inspect.signature(...)` shows no
  `VAR_POSITIONAL`/`VAR_KEYWORD` parameter kind), while every existing production
  call site in `src/` (`dossier_pipeline.py` and `drift_detector.py`) continues to
  pass with **no code change to the caller**.
- The one live production behaviour the bridge currently carries — `wp_id`,
  `step_id`, `required_status` (indexed) and `reason_detail`, `blocking` (missing)
  landing correctly in the emitted payload/diagnostics — is preserved exactly,
  proven by a real, unmocked regression test (not a plain-`Mock`-patched one).
- The dead `last_known_content_hash_sha256`/`last_known_size_bytes` parameters and
  their `ContentHashRef`-construction branch are gone from `emit_artifact_missing`.
- This mission's Phase 0 baseline (the pre-change red/error set) is recorded
  before any of the above lands, so no later WP misattributes a pre-existing
  failure to this mission.

**This WP is the mission's core deliverable but is not independently mergeable**
— WP02/WP03/WP04 complete the one PR this mission produces (see tasks.md "PR
Shape Recommendation").

## Context & Constraints

- Charter: `.kittify/charter/charter.md` — binding governance; Architectural
  alignment / Shared Package Boundaries is the clause this WP directly satisfies.
- Spec: `kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/spec.md`
  — read the `## Clarifications` section in full before starting; every claim
  about which functions carry the bridge, which fields are incompatible, and
  which call sites exist was independently re-verified there. Do not re-litigate
  those decisions.
- Plan: `kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/plan.md`
  — read "Mission-Specific Design Decisions" → "FR-004 raise/report/refuse
  contract" and "FR-005 dormant-field handling" in full; both are walked through
  precisely there and this prompt does not repeat every line, only the parts you
  need to act on.
- tasks.md: `kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/tasks.md`
  — this WP's role in the overall sequencing.
- **Out of scope, do not touch**: `src/specify_cli/sync/queue.py`,
  `src/specify_cli/sync/migrate_journal.py` (C-001 — queue-drain half of #1058 is
  superseded by mission #3293), `emit_snapshot_computed`/`emit_parity_drift_detected`
  and `_snapshot_legacy_diagnostics` (spec.md Clarifications — these two emitters
  never had the bridge and are not part of this mission).

## Branch Strategy

- **Strategy**: Planning artifacts for this mission were generated directly on
  `refactor/dossier-emitters-canonical-only-1058` (this mission's own target
  branch, already checked out at mission start — not `main`). Execution
  worktrees are allocated per computed lane from `lanes.json`; completed changes
  merge back into `refactor/dossier-emitters-canonical-only-1058`.
- **Planning base branch**: `refactor/dossier-emitters-canonical-only-1058`
- **Merge target branch**: `refactor/dossier-emitters-canonical-only-1058`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T001 – Phase 0 baseline capture

- **Purpose**: Before any functional change lands, record the pre-mission
  red/error set so no later WP misattributes a pre-existing failure to this
  mission (charter Pre-existing Failure Reporting Rule; spec.md C-003).
- **Steps**:
  1. Run the mission's full targeted test surface (NFR-003 scope) against the
     current HEAD, which has no functional changes yet:
     ```bash
     PWHEADLESS=1 .venv/bin/python -m pytest \
       tests/dossier/ tests/sync/test_events_namespace.py \
       tests/sync/test_dossier_pipeline.py tests/sync/test_diagnose.py \
       tests/architectural/ -q
     ```
  2. Record the exact set of failing/erroring test IDs (not just counts).
  3. Cross-reference against issue #3284's known set (23 known-red tests + 2
     errors on `main`). Any test red here that is **not** in #3284's set is new
     information discovered by this mission — per the charter's Pre-existing
     Failure Reporting Rule, open a **new** GitHub issue (command run, failure
     summary, why it's judged pre-existing rather than mission-introduced)
     before continuing. Do not silently shrug or silently assume "known baseline."
  4. Also note issue #3283's shared test-venv lock timeout risk — if a run times
     out on a lock, that is an environment symptom, not a code defect; retry once
     before treating it as a real failure.
  5. Append the recorded baseline (test IDs, counts, cross-reference conclusion)
     to `kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/tracer-tooling-friction.md`
     (append — do not overwrite existing content).
- **Files**: `kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/tracer-tooling-friction.md`
  (append only; not in this WP's `owned_files` code-change list since it is a
  process note, not source/test code).
- **Parallel?**: No — this must happen first, before any code edit in this WP.
- **Notes**: This is the "before-picture" every later phase's regression check
  diffs against (plan.md "Baseline Red Policy" step 1).

### Subtask T002 – Delete local mirror classes, import canonical types (FR-001)

- **Purpose**: Close the Shared-Package-Boundary violation — `dossier/events.py`
  independently hand-writes 7 Pydantic classes that duplicate `spec_kitty_events`
  shapes by field name, with no import connecting them, so the existing
  import-based `test_shared_package_boundary.py` gate cannot flag them (see
  plan.md "Why the local mirror survived the existing boundary gate").
- **Steps**:
  1. Delete these 7 classes from `src/specify_cli/dossier/events.py`:
     `LocalNamespaceTuple` (currently `events.py:70`), `ArtifactIdentity`
     (`:86`), `ContentHashRef` (`:108`), `MissionDossierArtifactIndexedPayload`
     (`:139`), `MissionDossierArtifactMissingPayload` (`:158`),
     `MissionDossierSnapshotComputedPayload` (`:175`),
     `MissionDossierParityDriftDetectedPayload` (`:193`). (Line numbers are
     current as of mission specification; re-verify with
     `grep -n "^class" src/specify_cli/dossier/events.py` before editing, since
     WP-to-WP drift is expected.)
  2. Add an import of the canonical equivalents from `spec_kitty_events` at the
     package top level (verified importable at 6.1.0 during specification —
     confirm live with
     `python3 -c "import spec_kitty_events as ske; print(ske.LocalNamespaceTuple, ske.ArtifactIdentity, ske.ContentHashRef, ske.ProvenanceRef, ske.MissionDossierArtifactIndexedPayload, ske.MissionDossierArtifactMissingPayload, ske.MissionDossierSnapshotComputedPayload, ske.MissionDossierParityDriftDetectedPayload)"`
     before assuming any particular import path — use whatever module path that
     introspection confirms, and prefer the package's documented public surface).
  3. Every reference to the deleted local classes elsewhere in `events.py`
     (constructors, type hints, the `_build_artifact_identity`/
     `_build_content_ref`/`_coerce_namespace` helper functions) must now resolve
     to the imported canonical class — update type hints accordingly.
  4. Do **not** touch `emit_snapshot_computed`, `emit_parity_drift_detected`, or
     `_snapshot_legacy_diagnostics` beyond the type-import swap they need to keep
     compiling — their own logic is out of scope (spec.md Clarifications).
- **Files**: `src/specify_cli/dossier/events.py`.
- **Parallel?**: No — later subtasks in this WP depend on the canonical types
  being in scope.
- **Notes**: `ArtifactIdentity.artifact_class` is now `Literal`-constrained (no
  `"other"` member) in the canonical type — T003 handles preserving the legacy
  remap ahead of construction, do not construct `ArtifactIdentity` directly with
  an unmapped `artifact_class` value anywhere.

### Subtask T003 – Confirm legacy `artifact_class="other"` remap survives (FR-002)

- **Purpose**: The canonical `ArtifactIdentity.artifact_class` is `Literal`-typed
  with 6 members (`input`, `workflow`, `output`, `evidence`, `policy`,
  `runtime`) — no `"other"`. `_normalize_artifact_class`/`_LEGACY_ARTIFACT_CLASS_MAP`
  (currently `events.py:60-66`, `{"other": "runtime"}`) must keep running ahead of
  **every** `ArtifactIdentity(...)` construction call, not just the ones you
  happen to look at.
- **Steps**:
  1. Grep every call site inside `events.py` that constructs `ArtifactIdentity`
     (directly or via the `_build_artifact_identity` helper) and confirm
     `_normalize_artifact_class(artifact_class)` (or equivalent) runs on the
     `artifact_class` value before it reaches the constructor.
  2. If T002's type-import swap accidentally bypassed the remap call anywhere
     (e.g. if a helper function's body needs restructuring to keep calling it),
     fix it here — this subtask exists specifically to catch that class of
     regression.
  3. Confirm/keep the existing test proving this:
     `tests/dossier/test_events.py::TestEmitArtifactIndexed::test_legacy_other_class_maps_to_runtime`
     (exact class/test name — re-verify with
     `grep -n "test_legacy_other_class_maps_to_runtime\|other.*runtime" tests/dossier/test_events.py`
     since this file is not yet edited by this WP — its import re-point is
     WP04's job — but it must still **pass** against your changes here).
- **Files**: `src/specify_cli/dossier/events.py` (read `tests/dossier/test_events.py`
  for verification only — do not edit it in this WP; edits to that file are
  WP04's `owned_files`, not this WP's).
- **Parallel?**: No.
- **Notes**: This is a "given valid input, prove nothing changed" subtask — the
  behavior must be bit-for-bit identical to before T002, only the type it feeds
  differs.

### Subtask T004 – Bridge removal + kwarg promotion, `emit_artifact_indexed` (FR-003, FR-004 half 1)

- **Purpose**: Remove the legacy positional/keyword compatibility parser from
  `emit_artifact_indexed` while promoting the one live keyword shape
  `dossier_pipeline.py` actually calls with to explicit, first-class parameters
  — so the bridge's removal is invisible to that caller, not a silent break.
- **Steps**:
  1. In `emit_artifact_indexed` (currently `events.py:339` onward), delete the
     `*args: object` parameter and the `**kwargs: Any` parameter.
  2. Delete the `legacy = _consume_legacy_values(args, kwargs, names=("wp_id",
     "step_id", "required_status"), defaults={"wp_id": None, "step_id": None,
     "required_status": "optional"})` call and its three follow-up
     `_optional_str(legacy[...])`/`str(legacy[...])` lines.
  3. Add `wp_id: str | None = None`, `step_id: str | None = None`,
     `required_status: str = "optional"` as explicit **keyword-only** parameters
     (i.e. after the existing bare `*` — there already is one, from
     `namespace: ... | None = None,` onward; confirm placement keeps them
     keyword-only, matching every other named parameter in this signature).
  4. Confirm the rest of the function body is unchanged — it already reads
     `wp_id`, `step_id`, `required_status` as local names; those names now bind
     directly to the promoted parameters instead of to `legacy[...]` lookups.
  5. Do **not** delete `_consume_legacy_values` in this subtask. Grep-verify
     that `emit_artifact_missing` (T005, below) still has its own
     `_consume_legacy_values(...)` call site at this point — confirming both
     call sites are not yet gone — so the physical deletion is correctly left
     to T005 step 7, which runs after both call sites (this one and T005's)
     are actually removed. Deleting the helper here would break
     `emit_artifact_missing`'s still-unedited call to it.
- **Files**: `src/specify_cli/dossier/events.py`.
- **Parallel?**: No — T005 must land in the same commit; T005 step 7 deletes
  the shared `_consume_legacy_values` helper only after both this subtask's
  and T005's call sites are gone.
- **Notes**: `mission_slug`, `artifact_key`, `artifact_class`, `relative_path`,
  `content_hash_sha256`, `size_bytes` stay positional-or-keyword (unchanged) —
  only the promoted three plus the existing keyword-only block change shape.
  Do not accidentally make the six leading parameters keyword-only too; that
  would be a wider signature change than FR-003/FR-004 ask for and would break
  any positional caller (none exist today per C-002's readiness probe, but stay
  scoped to what the FRs actually require).

### Subtask T005 – Bridge removal + kwarg promotion + `last_known_ref` drop, `emit_artifact_missing` (FR-003, FR-004 half 2, FR-005)

- **Purpose**: Mirror T004 for `emit_artifact_missing`, and additionally drop the
  two dead `last_known_*` parameters since the canonical
  `MissionDossierArtifactMissingPayload.last_known_ref` field is typed
  `Optional[ProvenanceRef]` — incompatible with the local mirror's
  `ContentHashRef`-shaped construction (`ProvenanceRef.model_config =
  {"frozen": True, "extra": "forbid"}`; forcing a hash-shaped dict into it raises
  `pydantic.ValidationError`).
- **Steps**:
  1. In `emit_artifact_missing` (currently `events.py:424` onward), delete the
     `*args: object` parameter and the `**kwargs: Any` parameter.
  2. Delete the `legacy = _consume_legacy_values(args, kwargs,
     names=("reason_detail", "blocking"), defaults={"reason_detail": None,
     "blocking": True})` call and its two follow-up lookup lines.
  3. Add `reason_detail: str | None = None`, `blocking: bool = True` as explicit
     **keyword-only** parameters, in the same position the bridge's output
     currently feeds (ahead of the existing keyword-only block that begins at
     `namespace: ...`).
  4. Delete the `last_known_content_hash_sha256: str | None = None` and
     `last_known_size_bytes: int | None = None` parameters entirely.
  5. Delete the `last_known` construction branch (currently `events.py:476-481`
     — the `if last_known_content_hash_sha256: last_known =
     _build_content_ref(...)` block) and the `last_known=last_known` (or
     equivalent) argument passed into `MissionDossierArtifactMissingPayload(...)`.
     Replace it with `last_known_ref=None` (or simply omit the argument if the
     canonical constructor defaults it to `None`) — confirm via the canonical
     model's field default before choosing.
  6. Confirm the `if not blocking: ... return None` short-circuit (currently
     `events.py:455-457`, immediately after the promoted `blocking` local is
     computed) is unchanged in position and behavior — only the source of the
     `blocking` value changes (from `bool(legacy["blocking"])` to the promoted
     parameter directly).
  7. Now delete `_consume_legacy_values` (`events.py:288-306`) — its only two
     call sites (this one and T004's) are both gone.
- **Files**: `src/specify_cli/dossier/events.py`.
- **Parallel?**: No.
- **Notes**: Grep-verify (repeat the specification-phase check) that zero call
  sites anywhere in `src/` or `tests/` pass `last_known_content_hash_sha256=` —
  if implementation-time discovers a new one that specification missed, stop and
  flag it rather than silently dropping live behavior; spec.md's C-002 asserts
  this is dormant, but re-verify rather than trust blindly.

### Subtask T006 – FR-004 binding regression test(s) in `test_dossier_pipeline.py`

- **Purpose**: Prove T004/T005's parameter promotion actually preserves the one
  live production behaviour the bridge carried — `dossier_pipeline.py`'s
  existing keyword calls (`step_id=step_id, required_status=artifact.required_status`
  at `dossier_pipeline.py:107-108`; `blocking=artifact.required_status ==
  "required"` at `dossier_pipeline.py:130`) keep working and keep producing the
  same observable payload/diagnostics content.
- **Steps**:
  1. **Do not rely on the existing `@patch("specify_cli.dossier.events.emit_artifact_indexed")`
     / `@patch("specify_cli.dossier.events.emit_artifact_missing")` decorators
     as-is** (e.g. `tests/sync/test_dossier_pipeline.py:109-111`) — these use a
     plain `MagicMock` with no `autospec=True`/`spec=`, which accepts any keyword
     silently and would **not** go red if the parameter promotion were reverted.
     Leave those existing tests as-is for their own (unrelated) purpose; do not
     modify them to "fix" this.
  2. Add **at least one new test** that calls the real, unmocked
     `emit_artifact_indexed`/`emit_artifact_missing` end-to-end — via
     `_emit_artifact_events`/`sync_feature_dossier` (mock only unrelated
     collaborators such as `Indexer`/`ManifestRegistry`, matching the pattern
     the existing `test_happy_path` test already uses for those two) — and
     assert directly on:
     - **AC1** (indexed path): the fired payload's `context_diagnostics` contains
       `artifact_key` and `required_status`, and `step_id` lands in the payload's
       `step_id` field. Suggested name:
       `test_emit_artifact_indexed_keyword_promotion_preserves_diagnostics`.
     - **AC2** (missing path): the blocking-driven emit/no-emit outcome — when
       `blocking` evaluates `True`, the event fires (counted in
       `events_emitted`); when `False`, it does not (short-circuits, `None`
       returned, not counted). Suggested name:
       `test_emit_artifact_missing_blocking_short_circuit_survives_bridge_removal`.
  3. **Optionally**, add a supplementary `autospec=True`/`spec=emit_artifact_indexed`/
     `spec=emit_artifact_missing`-mocked test *in addition* to (2) — if you do,
     it must assert on a try/except-surviving observable (`events_emitted` count
     or `mock_emit.call_args`), **never** merely that the outer call did not
     raise, since `_emit_artifact_events` wraps each call in `except Exception`
     and would swallow a `TypeError` silently either way.
  4. Confirm both new test(s) actually go red if you locally, temporarily,
     revert T004/T005's parameter promotion (e.g. re-add `*args`/`**kwargs`
     without the explicit params) — this is the binding red-first proof
     plan.md's "FR-004 raise/report/refuse contract" section requires. Revert
     your temporary change before finishing.
- **Files**: `tests/sync/test_dossier_pipeline.py`.
- **Parallel?**: No — depends on T004/T005 being complete.
- **Notes**: See plan.md's "FR-004 raise/report/refuse contract" section for the
  exact mechanics of why a plain-Mock test doesn't catch this: `_emit_artifact_events`
  wraps each emitter call in its own `try: ... except Exception as e:
  logger.warning(...)`, so a reverted promotion raises `TypeError` inside that
  try block, gets caught and logged as a warning, and `events_emitted` stays
  under-counted — exactly the "silent success" failure mode the charter names as
  this repo's dominant defect class. Only a real-call or `events_emitted`/
  `call_args`-asserting test can observe that.

## Test Strategy

- **Scope** (NFR-003): run
  `PWHEADLESS=1 .venv/bin/python -m pytest tests/dossier/
  tests/sync/test_events_namespace.py tests/sync/test_dossier_pipeline.py -q`
  after each subtask; do not run the full `pytest tests/` (reserved for
  pre-merge/post-merge validation per the charter).
- `tests/dossier/test_events.py` is **not edited by this WP** (WP04's job — the
  import re-point) but must still **pass** against T002-T005's changes, since it
  is this mission's live pin on the emitters' wire shape. If it fails after your
  changes, that is a signal your change altered observable behavior beyond
  what FR-001..FR-005 authorize — investigate before proceeding, do not silently
  adjust the test to match.
- T006's binding test bar is restated in full above — do not weaken it. A test
  that only asserts "no exception raised" does not satisfy FR-004.
- Baseline gate: after this WP's commit, re-run the T001 targeted surface and
  diff against the recorded baseline (plan.md "Baseline Red Policy" step 3) —
  only newly-red tests beyond the baseline are this WP's own regressions to fix
  before WP02 starts.

## Risks & Mitigations

- **Silent breakage of production keyword calls** if T004/T005's promotion is
  incomplete or the default values drift from the bridge's originals →
  mitigated by T006's binding real-call test, matching plan.md's explicit
  reasoning for why a mock-based test is insufficient here.
- **Deleting `_consume_legacy_values` before both call sites are migrated** →
  do T004 and T005 in that order, delete the helper only after both emitters
  no longer reference it (see T005 step 7).
- **Baseline miscounted or skipped** → T001 is a hard prerequisite for every
  later WP's regression-diffing; do not skip it to save time, and record exact
  test IDs, not just pass/fail counts.
- **Sonar complexity** — `emit_artifact_indexed`/`emit_artifact_missing` gain a
  few more explicit parameters but no new branching from this WP; confirm
  neither function crosses the repo's complexity ceiling of 15
  (`ruff` `C901`/Sonar `S3776`) after your edits.

## Review Guidance

- Confirm SC-001 (`grep -c "^class.*BaseModel" src/specify_cli/dossier/events.py`
  returns `0`) and SC-002 (`inspect.signature(emit_artifact_indexed)` /
  `inspect.signature(emit_artifact_missing)` show no `VAR_POSITIONAL`/`VAR_KEYWORD`)
  directly, not just by reading the diff.
- Confirm T006's new test(s) are not plain-`Mock`-patched and actually assert on
  `context_diagnostics`/`step_id`/`events_emitted` content, not merely
  "did not raise."
- Confirm `_consume_legacy_values` no longer exists anywhere in `events.py`.
- Confirm `emit_snapshot_computed`/`emit_parity_drift_detected`/
  `_snapshot_legacy_diagnostics` are untouched beyond the necessary type-import
  swap from T002.
- Confirm the T001 baseline was actually recorded and appended to
  `tracer-tooling-friction.md` before functional edits began.

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
