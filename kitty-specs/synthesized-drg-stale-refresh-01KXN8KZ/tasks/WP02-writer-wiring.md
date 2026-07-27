---
work_package_id: WP02
title: Writer wiring (self-contained red→green, reader-independent)
dependencies:
- WP01
requirement_refs:
- C-001
- C-004
- C-005
- C-006
- FR-001
- FR-003
- FR-005
- NFR-001
- NFR-004
- NFR-005
tracker_refs: []
planning_base_branch: fix/2681-synthesized-drg-stale
merge_target_branch: fix/2681-synthesized-drg-stale
branch_strategy: Planning artifacts for this mission were generated on fix/2681-synthesized-drg-stale. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/2681-synthesized-drg-stale unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
- T014
phase: Phase 2 - Writer wiring (real bundle_content_hash values)
assignee: ''
agent: "claude"
shell_pid: "2617245"
shell_pid_created_at: "1784217734.11"
history:
- at: '2026-07-16T12:49:44Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/synthesizer/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/charter/synthesizer/write_pipeline.py
- src/charter/synthesizer/resynthesize_pipeline.py
- src/charter/synthesizer/project_drg.py
- tests/charter/synthesizer/test_write_pipeline.py
- tests/charter/synthesizer/test_orchestrator_resynthesize.py
- tests/integration/test_charter_synthesize_built_in_only.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Writer wiring (self-contained red→green, reader-independent)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `<div>`, `<script>`
Use language identifiers in code blocks: ```python, ```bash

---

## Objectives & Success Criteria

WP02 makes every manifest-persist site write a correct non-`None`
`bundle_content_hash` via the one WP01 finalizer. It is **self-contained
red→green AND reader-INDEPENDENT**: its red-first tests assert on the
manifest FIELD value (and BLOCKER-1 field-survival), NOT on freshness state,
so they are RED on WP02's base (writers still emit `None`) and GREEN on
WP02's own final commit — with the reader (`computer.py`) still untouched.
This is the WP that gives the mission a genuine per-WP red→green gate that
does not wait for the reader swap.

**Definition of Done** (each item ties to the plan's traceability table):

- [ ] `SynthesisManifest.schema_version`'s default is `"3"` (out-of-map
      one-line edit to `manifest.py`, see below), landed ATOMICALLY with the
      writer conversion.
- [ ] `write_pipeline.promote` (`manifest_override is None` branch) builds a
      `SynthesisManifest` **instance** routed through `finalize_manifest`,
      computes a REAL `bundle_content_hash` via the WP01 helper, drops the
      hardcoded `"schema_version": "2"` dict literal. Satisfies FR-001
      (write), FR-003, C-005/C-006.
- [ ] `resynthesize_pipeline._rewrite_manifest` does the same, PLUS threads
      `repo_root` from `run()`'s existing `_repo_root`. Satisfies FR-001,
      FR-003 (`resynthesize` clears staleness — AS-3), FR-005/AS-5.
- [ ] **C-004**: BOTH `synthesize` and `resynthesize` are corrected to write
      a fresh `bundle_content_hash` — no new escape-hatch command is
      introduced, and neither remediation path is left broken behind a new
      command. The existing `remediation=` strings are unchanged (the WP04
      audit confirms no new command/flag). Satisfies C-004.
- [ ] `project_drg.apply_post_condition` builds its post-condition manifest
      via `manifest.model_copy(update={"built_in_only": ...})` +
      `finalize_manifest`, NOT the explicit-kwarg reconstruction that omits
      `bundle_content_hash` — closing BLOCKER-1 structurally. Satisfies
      C-005/C-006, AS-6.
- [ ] `write_pipeline._VOLATILE_MANIFEST_FIELDS` UNCHANGED (`bundle_content_
      hash` stays substantive). Satisfies C-001/NFR-001, AS-4.
- [ ] No-op-stability preserved (zero git modifications on a genuine no-op
      re-run, except the one-time self-heal on a pre-fix manifest).
- [ ] Per-WP red→green: the WP02 red-first tests (a)-(c) below are RED on
      WP02's base and GREEN on WP02's final commit — commit red first,
      confirm red (esp. BLOCKER-1 against the pre-fix `apply_post_condition`),
      then land the fixes.
- [ ] The reader (`computer.py`) is untouched (`git diff --stat` shows only
      WP02's 6 owned files; the `manifest.py` one-line bump is the documented
      out-of-map exception).
- [ ] `mypy --strict` + `ruff check` clean; ≥90% new-line coverage.

**Independent Test** (WP02's reader-independent gate): after `synthesize` AND
`resynthesize`, the loaded manifest satisfies `bundle_content_hash is not
None and == compute_bundle_content_hash(repo_root)` (T011); and the BLOCKER-1
field survives the `apply_post_condition` flip + `verify_manifest_hash`
passes (T012). Both go GREEN at WP02, independent of the reader.

## Context & Constraints

**Read first**:

- `kitty-specs/synthesized-drg-stale-refresh-01KXN8KZ/plan.md` — WP02
  section + research fact #17's full explanation.
- `kitty-specs/synthesized-drg-stale-refresh-01KXN8KZ/data-model.md` — the
  "Complete set of manifest-persist consumers" table.
- `kitty-specs/synthesized-drg-stale-refresh-01KXN8KZ/research.md` — facts
  #7, #8, #9, #10, #11, #17, #18 + Decision 6.
- The three tracer files — append implementation notes as you work.

**Out-of-map edit (intentional, one line)**: this WP makes a ONE-LINE change
to `src/charter/synthesizer/manifest.py` — bumping `schema_version`'s default
`"2"`→`"3"` (the field + widened `Literal` were added in WP01). `manifest.py`
is NOT in WP02's `owned_files` (WP01 owns it). This edit is deliberately
out-of-map because it MUST land in the SAME commit as the
`promote`/`_rewrite_manifest` conversions (research fact #17 — landing either
alone desyncs the hardcoded `"2"` hashed-dict literal against the `"3"`
default → accidental `verify_manifest_hash` RED). Call it out explicitly in
your Activity Log.

**BLOCKER-1 needs its OWN non-vacuous test** (post-tasks squad finding): do
NOT assume "`apply_post_condition` runs after every synthesize, so the
synthesize tests cover it." That is FALSE — `apply_post_condition` takes a
fast-path early-return on a normal non-built-in synthesize
(`project_drg.py:305-310`: when `manifest.built_in_only == desired_built_in_
only and not (desired_built_in_only and graph_path.exists())`), so a normal
synthesize (project graph present → `desired_built_in_only=False`) NEVER
reaches the mutation branch (`project_drg.py:312-332`) where the field is
dropped. And the existing built_in_only tests seed `bundle_content_hash=None`
→ a re-dropped field is `None → None`, invisible. T012 is REQUIRED, not
"already covered."

## Branch Strategy

- **Strategy**: single-branch topology — no worktree/lane split.
- **Planning base branch**: `fix/2681-synthesized-drg-stale`
- **Merge target branch**: `fix/2681-synthesized-drg-stale`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T008 – Bump default `"2"`→`"3"` (out-of-map) + convert `promote` (atomic)

- **Purpose**: Make `synthesize` write a real `bundle_content_hash`; stop
  hand-maintaining a raw dict that can silently omit fields (BLOCKER-2).
- **Steps**:
  1. **Out-of-map**: in `manifest.py`, change `schema_version: Literal["2",
     "3"] = "2"` → `= "3"` (default only; the `Literal` is unchanged). Do
     this in the SAME commit as step 2.
  2. In `write_pipeline.py`'s `promote()` `manifest_override is None` branch
     (`:656-688`), replace the `manifest_data_without_hash` dict +
     `compute_manifest_hash` + explicit-kwarg `SynthesisManifest(...)` with:
     ```python
     from charter.bundle import compute_bundle_content_hash  # module-scope import
     from .manifest import finalize_manifest
     manifest = SynthesisManifest(
         mission_id=mission_id,
         created_at=datetime.now(tz=UTC).isoformat(),
         run_id=run_id,
         adapter_id=primary_adapter_id,
         adapter_version=primary_adapter_version,
         synthesizer_version=synthesizer_ver,
         manifest_hash="0" * 64,
         artifacts=sorted_artifacts,
         bundle_content_hash=compute_bundle_content_hash(repo_root),
     )
     manifest = finalize_manifest(manifest)
     ```
     — drop the `"schema_version": "2"` literal (model default `"3"` applies).
     `repo_root` is already resolved (`write_pipeline.py:494-497`).
  3. Add the two imports to the module import block (match the existing
     absolute-import style, e.g. `from charter.synthesizer._constants import
     GRAPH_FILENAME` at `write_pipeline.py:41`; use `from charter.bundle
     import compute_bundle_content_hash`).
  4. Leave the no-op-stability skip-write logic (`:692-711`,
     `_substantively_equal` vs `_VOLATILE_MANIFEST_FIELDS`) untouched.
- **Files**: `manifest.py` (out-of-map), `write_pipeline.py`
- **Parallel?**: No — T008's two edits are one atomic unit.

### Subtask T009 – Convert `_rewrite_manifest` + thread `repo_root`

- **Purpose**: Make `resynthesize` write a real `bundle_content_hash` too
  (AS-3/FR-003: BOTH remediation commands must clear staleness).
- **Steps**:
  1. In `resynthesize_pipeline.py`, add a `repo_root: Path` param to
     `_rewrite_manifest` (`:95-99`). Replace the hardcoded-dict pattern
     (`:186-208`) with the same instance-then-finalize shape as T008, adding
     `bundle_content_hash=compute_bundle_content_hash(repo_root)` and
     dropping the `"schema_version": "2"` literal; `return
     finalize_manifest(manifest)`.
  2. Add `finalize_manifest` (from `.manifest`) + `compute_bundle_content_
     hash` (from `charter.bundle`) to the import block (`:43-52`).
  3. Update the ONE call site in `run()` (`:447`): `new_manifest =
     _rewrite_manifest(existing_manifest, all_new_results, run_id,
     _repo_root)` — `_repo_root` is in scope at `:367`.
  4. Grep for any test calling `_rewrite_manifest` directly and update its
     arg list.
- **Files**: `src/charter/synthesizer/resynthesize_pipeline.py`
- **Parallel?**: Yes, alongside T010, once T008 sets the pattern.

### Subtask T010 – Fix `project_drg.apply_post_condition` (BLOCKER-1)

- **Purpose**: Close BLOCKER-1 structurally — the explicit-kwarg
  reconstruction omits `bundle_content_hash`, reverting it to `None` while
  the hash was computed over the real value.
- **Steps**:
  1. In `project_drg.py`, replace the post-condition construction
     (`:312-332`) with:
     ```python
     new_manifest = finalize_manifest(
         manifest.model_copy(update={"built_in_only": desired_built_in_only})
     )
     ```
     `model_copy` preserves every unlisted field (incl. `bundle_content_hash`
     and `schema_version`). Add `finalize_manifest` to the local import group
     (`:286-293`); confirm with `ruff` whether `SynthesisManifest`/
     `compute_manifest_hash` become unused here.
  2. Leave the fast-path no-mutation check (`:306-310`) and the atomic
     temp-file + `os.replace` mechanics untouched.
  3. Do NOT call `compute_bundle_content_hash` here (data-model.md — this
     site "preserves unchanged via `model_copy`"; recomputing would be dead
     work since the reader short-circuits on `built_in_only`).
- **Files**: `src/charter/synthesizer/project_drg.py`
- **Parallel?**: Yes, alongside T009.

### Subtask T011 – Red-first: writer-side field==helper assertion (WP02 gate)

- **Purpose**: WP02's reader-independent per-WP red→green gate.
- **Steps** — commit RED first (against WP02 base = writers emit `None`),
  confirm red, then T008/T009 turn it green:
  1. In `tests/charter/synthesizer/test_orchestrator_resynthesize.py` (reuse
     `repo_with_prior_synthesis`; extend it to SEED the 4 bundle files after
     `synthesize()` so `compute_bundle_content_hash` returns non-`None` —
     `synthesize()` alone does not write them), add: after a `synthesize`
     run, `load_yaml` the manifest and assert `manifest.bundle_content_hash
     is not None and == charter.bundle.compute_bundle_content_hash(repo_
     root)`. Add the parallel assertion after a `resynthesize` run (direct
     proof `repo_root` was threaded correctly into `_rewrite_manifest`).
  2. Add a companion `promote`-level assertion in `test_write_pipeline.py`
     if it fits the existing test shape (optional; the orchestrator-level
     assertion is the load-bearing one).
- **Files**: `tests/charter/synthesizer/test_orchestrator_resynthesize.py`,
  `tests/charter/synthesizer/test_write_pipeline.py`
- **Parallel?**: No — the core gate; author it before/alongside T008-T010.

### Subtask T012 – Red-first: BLOCKER-1 non-vacuous pin

- **Purpose**: The ONLY non-vacuous guard for BLOCKER-1 (see the Context
  note — the fast-path early-return means synthesize flows never cover it).
- **Steps** — commit RED first (against WP02 base = pre-T010
  `apply_post_condition`), confirm red, then T010 turns it green:
  1. In `tests/integration/test_charter_synthesize_built_in_only.py`, extend
     `_seed_manifest` with a `bundle_content_hash: str | None = None` param
     that, when non-`None`, is written into the seeded manifest with an
     internally-consistent `manifest_hash` (build via `finalize_manifest` so
     `verify_manifest_hash` would pass on the SEED). Keep the default
     backward-compatible (no field written when `None`).
  2. New test: seed a manifest with a REAL non-`None` `bundle_content_hash` +
     `built_in_only=False` + a project graph (`_seed_graph`) — the exact
     precondition that DRIVES the mutation branch (`apply_post_condition(
     tmp, has_project_graph=False)` → `desired_built_in_only=True` ≠ `False`
     → fast-path bypassed).
  3. After the call, `load_yaml` the on-disk manifest and assert (a)
     `bundle_content_hash == <original seeded value>` (SURVIVED the flip) and
     (b) `verify_manifest_hash(manifest)` does not raise.
  4. Confirm RED against the pre-T010 explicit-kwarg reconstruction (field
     dropped → `None` ≠ original; stored hash over real value vs persisted
     `None` → verify raises) and GREEN after T010.
- **Files**: `tests/integration/test_charter_synthesize_built_in_only.py`
- **Parallel?**: Yes, alongside T011.
- **Notes**: keep the file's existing tests unmodified except the backward-
  compatible `_seed_manifest` signature extension.

### Subtask T013 – Red-first: writer-recompute on genuine content drift (SC-003 writer half)

- **Purpose**: Prove the WRITER recomputes `bundle_content_hash` when the
  bundle content genuinely changes — reader-independent (asserts on the
  FIELD, not freshness state).
- **Steps** — commit RED first (writers emit `None` on base → field never
  changes), confirm red, then green after T008/T009:
  1. In `tests/charter/synthesizer/test_orchestrator_resynthesize.py`, seed a
     fresh synthesized DRG with the 4 bundle files; capture `manifest_1 =
     load_yaml(...).bundle_content_hash` after the first `synthesize`.
  2. GENUINELY edit the CONTENT of one bundle file (e.g. append a
     distinguishable line to `.kittify/charter/governance.yaml` — a change
     that survives `hash_content`'s BOM/CRLF/`.strip()` normalization).
  3. Re-run `synthesize`; capture `manifest_2 = load_yaml(...).bundle_content
     _hash`. Assert `manifest_2 is not None and manifest_2 != manifest_1 and
     manifest_2 == compute_bundle_content_hash(repo_root)` (the writer
     recomputed over the NEW content). Repeat the assertion for the
     `resynthesize` path.
- **Files**: `tests/charter/synthesizer/test_orchestrator_resynthesize.py`
- **Parallel?**: No — build on T011's fixture work in the same file.
- **Notes**: this is the reader-INDEPENDENT writer half of SC-003; the
  end-to-end freshness half (stale→remediate→fresh) is WP03's T019.

### Subtask T014 – WP02 regression validation

- **Purpose**: Confirm writer wiring correct + no-op-stability holds.
- **Steps**:
  1. Confirm T011/T012/T013 GREEN and were verified RED-first.
  2. Confirm `test_promote_writes_manifest_with_valid_self_hash`
     (`test_write_pipeline.py:349`) and `test_resynthesize_kind_slug_is_no_
     op_stable_when_content_unchanged` (`test_orchestrator_resynthesize.py:
     240`) still pass (fact #17's accidental-RED did NOT happen).
  3. Confirm `tests/architectural/test_no_op_stable_writes.py` shows zero git
     modifications on a genuine no-op re-run (this file is not WP02-owned —
     keep it green, no edit needed).
  4. Diff `_VOLATILE_MANIFEST_FIELDS` — must be unchanged.
- **Files**: (validation only)
- **Parallel?**: No — final subtask.

## Test Strategy

```bash
pytest tests/charter/synthesizer/test_orchestrator_resynthesize.py -q
pytest tests/charter/synthesizer/test_write_pipeline.py -q
pytest tests/integration/test_charter_synthesize_built_in_only.py -q
pytest tests/architectural/test_no_op_stable_writes.py -q   # keep green (not owned)
# reader untouched — these stay at their WP01-base state (no WP02 change):
pytest tests/specify_cli/charter_freshness/test_computer.py -q
mypy --strict src/charter/synthesizer/write_pipeline.py \
    src/charter/synthesizer/resynthesize_pipeline.py \
    src/charter/synthesizer/project_drg.py
ruff check src/charter/synthesizer/write_pipeline.py \
    src/charter/synthesizer/resynthesize_pipeline.py \
    src/charter/synthesizer/project_drg.py \
    tests/charter/synthesizer/test_write_pipeline.py \
    tests/charter/synthesizer/test_orchestrator_resynthesize.py \
    tests/integration/test_charter_synthesize_built_in_only.py
```

## Risks & Mitigations

- **Highest**: T008's default bump + `promote` conversion landing in
  separate commits (fact #17 accidental-RED). Mitigation: T008 scopes them
  as one atomic unit.
- `_VOLATILE_MANIFEST_FIELDS` gaining `bundle_content_hash` → breaks AS-4
  self-heal. Mitigation: DoD diff check.
- Forgetting to thread `repo_root` into `_rewrite_manifest`'s call site →
  `TypeError` at first resynthesize. Mitigation: T009 step 3.
- The BLOCKER-1 pin never actually red (vacuous) → confirm red against
  pre-T010 code before finishing.

## Review Guidance

- Confirm T008's default bump + `promote` conversion landed in ONE commit.
- Confirm `apply_post_condition` uses `model_copy` + `finalize_manifest`,
  NOT a new explicit-kwarg list.
- Confirm T011/T012/T013 were verified RED-first (a pin that was never red
  is vacuous — reject the WP if the red step was skipped).
- Spot-check `compute_bundle_content_hash` is called with the true repo root
  (not a staging path) in both writers.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Initial entry**:

- 2026-07-16T12:49:44Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task <WPID> --to <status>` to change WP status.
- 2026-07-16T16:02:20Z – claude – shell_pid=2617245 – Assigned agent via action command
- 2026-07-16T18:35:00Z – claude-sonnet-5 – Implemented T008-T014. Wrote red-first
  writer tests FIRST (T011/T012/T013) against unmodified source, confirmed all 5
  RED (`bundle_content_hash is None`/field dropped), then landed the fix.
  **Out-of-map edit**: bumped `manifest.py`'s `schema_version` default `"2"`→`"3"`
  (one line) atomically in the same change as converting `write_pipeline.promote`
  and `resynthesize_pipeline._rewrite_manifest` off the hardcoded `"2"` raw-dict
  literal — per data-model.md fact #17, landing either alone would desync the
  hashed literal against the model default and cause an accidental
  `verify_manifest_hash` RED. `project_drg.apply_post_condition` converted to
  `manifest.model_copy(update={"built_in_only": ...})` + `finalize_manifest`
  (closes BLOCKER-1 structurally). `repo_root` threaded into `_rewrite_manifest`.
  Also removed a vestigial dead `_ = dump_yaml  # noqa: F841` line in
  `project_drg.py` that would have raised `NameError` once the now-unused
  `dump_yaml` import was dropped, and fixed 3 pre-existing `no-any-return`
  mypy errors in `write_pipeline.py`/`resynthesize_pipeline.py` (confirmed via
  `git stash` to predate this WP) using the codebase's existing `cast(...)`
  pattern for the `charter.* follow_imports=skip` class of issue — required to
  satisfy the WP's own "mypy --strict clean" gate on these owned files.
  **Blocker found, NOT fixed (out of WP02 scope)**: a broader regression sweep
  across `tests/charter/` found `tests/charter/synthesizer/test_bundle_validate_extension.py::test_valid_synthesis_bundle_passes`
  and `tests/charter/test_bundle_validate_cli.py::test_validate_passes_complete_v2_bundle`
  fail `verify_manifest_hash` — confirmed via `git stash` this is a **pre-existing
  WP01 regression** (present identically with or without WP02's diff): each
  file's own hand-rolled manifest-seeding helper (`_make_v2_manifest` /
  `_add_synthesis_manifest`) computes its stored `manifest_hash` over a dict
  that includes `built_in_only` but never writes a `built_in_only:` line to the
  raw YAML text; this only worked before WP01 by coincidence (no extra model
  field existed to force the `verify_manifest_hash` legacy `_raw_field_names`
  fallback path). WP01's `bundle_content_hash` field addition exposes the
  latent inconsistency. Neither file is in WP02's `owned_files`; left
  unmodified for a WP01 follow-up / WP04 audit to resolve.
  **Repo-hygiene note**: the initial full-suite regression sweep left stray
  writes under the real `.kittify/` tree (`synthesis-manifest.yaml` mutated,
  new `provenance/`/`doctrine/` files) from an unrelated pre-existing test
  fixture that defaults `repo_root` to `Path.cwd()` when run serially outside
  `pytest-xdist`'s per-worker isolation — restored via `git checkout --
  .kittify/charter/synthesis-manifest.yaml` and deleted the untracked stray
  files before committing. Not caused by any WP02 test (all WP02 tests pass an
  explicit `repo_root=tmp_path`).
- 2026-07-16T17:13:33Z – claude – shell_pid=2617245 – WP02 d6bc124e7 + fixture-fix 60a3e012f; gate PASSED (renata+debbie, live-run+red-first probes, 0 blocker/major/medium)
- 2026-07-16T17:13:37Z – user – shell_pid=2617245 – WP02 d6bc124e7 + fixture-fix 60a3e012f; gate PASSED (renata+debbie, live-run+red-first probes, 0 blocker/major/medium)
- 2026-07-16T19:27:02Z – user – shell_pid=2617245 – mission complete; adversarial gates passed; #2681 fixed
