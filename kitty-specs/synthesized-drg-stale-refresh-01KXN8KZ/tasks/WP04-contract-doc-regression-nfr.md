---
work_package_id: WP04
title: Contract doc + full regression + NFR verification (closeout)
dependencies:
- WP03
requirement_refs:
- C-001
- C-003
- FR-007
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- NFR-005
tracker_refs: []
planning_base_branch: fix/2681-synthesized-drg-stale
merge_target_branch: fix/2681-synthesized-drg-stale
branch_strategy: Planning artifacts for this mission were generated on fix/2681-synthesized-drg-stale. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/2681-synthesized-drg-stale unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
- T026
phase: Phase 4 - Contract doc + regression + NFR verification (mission close)
assignee: ''
agent: "claude"
shell_pid: "3014291"
shell_pid_created_at: "1784224785.66"
history:
- at: '2026-07-16T12:49:44Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/charter/synthesizer/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/charter/synthesizer/test_performance_envelopes.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Contract doc + full regression + NFR verification (closeout)

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

## ⚠️ This WP delivers NO new runtime behavior — C-011 red-first is N/A

WP04 is the verification/docs closeout. It adds no new runtime code path, so
the C-011 per-WP red→green discipline does **not** apply to it (there is no
behavior to author a failing test against — the behavior was delivered and
proven per-WP in WP01/WP02/WP03). **WP04's gate is the full regression suite
+ the NFR guards**, not a red-first behavior test. This is stated explicitly
so `/analyze` does not misread WP04 as a diluted behavior WP: it is
categorically a closeout WP, and its one new test (the NFR-002 perf guard) is
a performance ratchet, not a behavior red→green.

## ⚠️ Ownership metadata note

WP04's declared `owned_files` is
`tests/charter/synthesizer/test_performance_envelopes.py` (T023's NFR-002
guard) — it does NOT list the external contract doc
`kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/contracts/
charter-status-json.md` that T022 edits, because the `finalize-tasks`
ownership gate hard-rejects ANY `owned_files` entry under `kitty-specs/`
(any mission's tree), AND an empty `owned_files` is separately rejected by
lane computation (`compute_lanes` requires every dependent WP to have a real
ownership manifest). Owning the NFR-002 test file gives WP04 a genuine,
non-`kitty-specs/` owned surface with no overlap. T022's contract-doc edit is
still real work — it is simply reviewer-attested (no automated pin possible
for a prose doc) rather than owned.

## Objectives & Success Criteria

**Definition of Done**:

- [x] `kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/contracts/
      charter-status-json.md`'s "Staleness computation" section is corrected
      to the content-hash rule, matching this mission's
      `contracts/synthesized-drg-freshness-rule.md` "Corrected rule text".
      **Reviewer-attested** — the reviewer MUST open the doc (no automated
      pin for a `kitty-specs/` prose doc). FR-007 external half complete.
- [x] NFR-002 verified via a NEW permanent perf guard in
      `tests/charter/synthesizer/test_performance_envelopes.py`:
      `compute_freshness` completes in well under 2 seconds wall-clock.
      Observed ~3.7ms locally (2026-07-16); ~500x headroom under budget.
- [x] NFR-003 verified: `pyproject.toml` gains no new dependency; no new CLI
      command/flag; the `remediation=` strings in `computer.py` are the
      pre-existing ones (recorded audit, not a checkbox — see Activity Log).
- [x] Full regression green: no-op-stable guard, `mypy --strict`, `ruff`,
      coverage ≥90% on new/changed lines across the whole mission; the
      terminology guard passes.
- [x] issue-matrix close-out records the pre-settled verdicts (see T026);
      DIR-003 assignee caveat recorded; the three tracer files assessed.
- [x] C-001/NFR-001 re-confirmed: a synthesize→no-op→resynthesize→no-op cycle
      produces zero git modifications on the second run of each pair.

## Context & Constraints

**Read first**:

- `kitty-specs/synthesized-drg-stale-refresh-01KXN8KZ/plan.md` — WP04
  section + the FULL Charter Check table (this WP self-verifies every row).
- `kitty-specs/synthesized-drg-stale-refresh-01KXN8KZ/contracts/
  synthesized-drg-freshness-rule.md` — the exact corrected contract text +
  the "Relationship to `manifest.verify()`" section.
- `kitty-specs/synthesized-drg-stale-refresh-01KXN8KZ/spec.md` — NFR-002,
  NFR-003, C-001, C-003, and the Related Issues section (for T026 verdicts).
- The three tracer files — assess + append the close-out entry.
- `docs/guides/testing-parallel.md` / `docs/guides/testing-flakiness.md`.

## Branch Strategy

- **Strategy**: single-branch topology — no worktree/lane split.
- **Planning base branch**: `fix/2681-synthesized-drg-stale`
- **Merge target branch**: `fix/2681-synthesized-drg-stale`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T022 – Correct the external charter-status contract doc (FR-007 external)

- **Steps**:
  1. Open `kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/
     contracts/charter-status-json.md`. Locate the "Staleness computation"
     section by HEADING + defective-rule wording (references
     `synthesis-manifest.yaml.run_id` / mtime). It sits around lines 45-50
     with the defective bullet at ~L49 — find it by section, NOT by trusting
     line numbers (different mission's doc, numbers drift).
  2. Replace the defective bullet with the corrected text from
     `contracts/synthesized-drg-freshness-rule.md`'s "Corrected rule text"
     section, verbatim (adapted only to the target doc's prose style).
  3. Leave the `missing`/`built_in_only` bullets unchanged (FR-004/FR-006,
     C-002). Reconcile any "relationship to `manifest.verify()`" framing
     with the freshness-rule doc's section — do not introduce a competing
     explanation.
  4. Reviewer-attested: no test pins this; the reviewer opens the doc.
- **Files**: `kitty-specs/.../charter-status-json.md` (real edit; not
  declarable in `owned_files` — see the ownership note above)
- **Parallel?**: Yes, independent of T023-T026.

### Subtask T023 – NFR-002 perf guard (<2s freshness compute)

- **Steps**:
  1. In `tests/charter/synthesizer/test_performance_envelopes.py` (reuse the
     `repo_with_prior_synthesis` fixture + the `TestNfr002FullSynthesis` /
     `time.monotonic()` + `@pytest.mark.timeout` patterns already in this
     file), add a test measuring `specify_cli.charter_runtime.freshness.
     computer.compute_freshness` wall-clock time against a representative
     repo; assert `< 2.0` seconds with meaningful headroom.
  2. This is a PERMANENT regression ratchet (catches an accidental eager
     import or O(n²) helper bug), not a one-off measurement.
  3. Record the observed baseline in a code comment ("observed ~Xms on
     <date>").
- **Files**: `tests/charter/synthesizer/test_performance_envelopes.py`
- **Parallel?**: Yes, alongside T022/T024.

### Subtask T024 – NFR-003 audit (0 new manual steps/dependencies)

- **Steps**:
  1. `git diff planning_base_branch -- pyproject.toml` → empty / no new
     packages.
  2. Confirm no new CLI command/flag anywhere in the mission diff (no new
     `@app.command`/`typer.Typer` in the touched files).
  3. Confirm the `remediation=` strings in `computer.py` are the pre-existing
     `"spec-kitty charter synthesize"` — grep the diffed region; no new
     remediation string.
  4. Record the audit evidence (grep/diff output) in the Activity Log — not
     just a checkbox.
- **Files**: (verification only)
- **Parallel?**: Yes, alongside T022/T023.

### Subtask T025 – Full regression run

- **Steps**:
  1. Run every mission test file together in one pass (see Test Strategy).
  2. `mypy --strict` + `ruff check` across the full set of files this mission
     touched (WP01 3 src + 3 test; WP02 3 src + 3 test; WP03 1 src + 2 test;
     WP04 1 test).
  3. Coverage ≥90% on new/changed lines (esp. `compute_bundle_content_hash`
     `None`-branches incl. non-UTF-8, and the `verify_manifest_hash`
     `raw_field_names is None` guard).
  4. Run the terminology guard: `pytest tests/architectural/test_no_op_
     stable_writes.py tests/architectural/test_no_legacy_terminology.py -q`
     (the latter is the ~0.1s pre-push terminology gate the project's
     CLAUDE.md calls out for doctrine/prose-touching changes — T022
     qualifies).
- **Files**: (validation only)
- **Parallel?**: No — after T022 lands.

### Subtask T026 – issue-matrix close-out + tracer assessment + DIR-003 caveat

- **Steps**:
  1. **issue-matrix close-out (pre-settled verdicts)**: spec.md's Related
     Issues section already settles the verdicts — do not re-litigate. Record:
     #2681=fixed (this mission); #1914/#2157/#2373=out-of-scope (different
     umbrella / terminal state / code surface); #2009=explicitly-not-related;
     #1912/#1913=preserved regression-source (the no-op-stable write this
     mission keeps honoring, C-001). Note that the standard verdict vocabulary
     (fixed / verified-already-fixed / deferred / in-mission) has NO clean
     value for "not-related" (#2009) or "preserved-invariant" (#1912/#1913) —
     ANNOTATE these rather than shoehorn. Do not invent a code change to
     "close" #2009 or #1912/#1913; they are context, not work.
  2. **DIR-003 caveat**: the MOES-Media fork cannot assign the HiC on
     upstream Priivacy-ai #2681 — best-effort per the cross-fork contributor
     model; attempt where the tracker permits, note skipped otherwise. NOT a
     mission blocker.
  3. **Tracer assessment**: assess the three tracer files
     (`tracer-approach.md`, `tracer-design-decisions.md`,
     `tracer-tooling-friction.md`) and append a mission-close entry recording:
     the C-011 per-WP red→green sequence held (WP01 shim/helper red→green;
     WP02 writer field/BLOCKER-1 red→green reader-independent; WP03 AS-1/AS-5
     red→green); the deferred out-of-scope limitation (research.md Decision 2
     — the `charter activate`/`deactivate` config-drift blind spot); and the
     WP04 ownership-metadata note (owning the perf test rather than the
     `kitty-specs/` contract doc).
  4. Confirm no unresolved TODO/FIXME left behind in the mission diff.
- **Files**: mission tracer files + issue-matrix (per charter convention;
  consult `spec-kitty charter context --action review` if unfamiliar)
- **Parallel?**: No — final subtask.

## Test Strategy

```bash
pytest tests/charter/test_bundle_content_hash.py \
    tests/charter/synthesizer/test_manifest.py \
    tests/integration/test_charter_synthesize_fresh.py \
    tests/charter/synthesizer/test_write_pipeline.py \
    tests/charter/synthesizer/test_orchestrator_resynthesize.py \
    tests/integration/test_charter_synthesize_built_in_only.py \
    tests/specify_cli/charter_freshness/test_computer.py \
    tests/integration/test_charter_status_freshness.py \
    tests/charter/synthesizer/test_performance_envelopes.py \
    tests/architectural/test_no_op_stable_writes.py \
    tests/specify_cli/upgrade/test_charter_bundle_v2_migration.py \
    tests/doctrine/test_versioning.py \
    tests/specify_cli/upgrade/test_bundle_validate_fresh_seed.py -q
pytest tests/architectural/test_no_legacy_terminology.py -q
mypy --strict \
    src/charter/synthesizer/manifest.py src/charter/bundle.py \
    src/specify_cli/cli/commands/charter/_fresh_doctrine.py \
    src/charter/synthesizer/write_pipeline.py \
    src/charter/synthesizer/resynthesize_pipeline.py \
    src/charter/synthesizer/project_drg.py \
    src/specify_cli/charter_runtime/freshness/computer.py
```

For a broader confirmation: `PWHEADLESS=1 pytest tests/ -n auto --dist
loadfile -p no:cacheprovider`.

## Risks & Mitigations

- Contract-doc wording drifting from WP03's internal docstring correction.
  Mitigation: both trace to the SAME source
  (`synthesized-drg-freshness-rule.md`) — verbatim, only prose-style adapted.
- NFR-002/NFR-003 becoming rubber-stamps. Mitigation: T023 is a permanent
  test; T024 requires recorded grep/diff evidence.
- The ownership-metadata resolution mistaken for a bug and "fixed" by adding
  the `kitty-specs/` doc path → hard-fails finalize. Mitigation: the note
  above + the T026 tracer entry.

## Review Guidance

- Open the external contract doc (T022) — it is reviewer-attested, no test
  pins it.
- Confirm the NFR-002 perf test exists + passes with headroom.
- Confirm NFR-003 has concrete grep/diff evidence.
- Confirm the tracer files were assessed + a close-out entry appended.
- Confirm WP04 added no new runtime behavior (it is a closeout — its only new
  file is the perf test).

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
- 2026-07-16T17:59:54Z – claude – shell_pid=3014291 – Assigned agent via action command
- 2026-07-16T18:24:32Z – claude-sonnet-5 – T022: corrected `kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/contracts/charter-status-json.md`'s "Staleness computation" `synthesized_drg` bullet from the defective mtime rule to the content-identity rule (verbatim from `contracts/synthesized-drg-freshness-rule.md`, adapted to the target doc's terser one-bullet-per-line prose). Confirmed `computer.py`'s module docstring (WP03) already carries matching text. T023: added `TestNfr002FreshnessComputeUnder2Seconds` to `tests/charter/synthesizer/test_performance_envelopes.py` — seeds a representative `.kittify/charter/`+`.kittify/doctrine/` tree with a real `bundle_content_hash` via the canonical helper, asserts `compute_freshness` < 2.0s wall-clock (`@pytest.mark.timeout(2)` + `time.monotonic()`); observed ~3.7ms locally. T024: `git diff <mission-base>..HEAD -- pyproject.toml` empty (0 new deps); grep for `@app.command`/`typer.Typer`/`remediation=` across the mission's 7 touched src files (WP01 759d24fa6..WP03 fc679f573) found zero new CLI surface and the sole `remediation=` occurrence is the pre-existing `"spec-kitty charter synthesize"` string. Folded footgun fix: `tests/charter/synthesizer/test_orchestrator_synthesize.py::TestSynthesizeEntryPoint` (3 tests) called `synthesize()` without `repo_root=`, defaulting to `Path.cwd()` and polluting the real `.kittify/` tree on every broad run — added `tmp_path: Path` + `repo_root=tmp_path` to all three; verified `.kittify/` stays clean after a full-suite run from repo root. T025: affected-surface sweep (`tests/charter/ tests/specify_cli/charter/ tests/specify_cli/charter_freshness/ tests/specify_cli/charter_runtime/ tests/doctrine/test_versioning.py tests/integration/test_charter_status_freshness.py tests/integration/test_charter_synthesize_fresh.py tests/architectural/test_no_op_stable_writes.py`) = 1693 passed, 0 failed. Terminology guard (`test_no_legacy_terminology.py`) = 3 passed. `mypy --strict src/specify_cli src/charter src/doctrine` = 9 pre-existing/advisory `redundant-cast` findings (4 in mission-untouched files, 4 in WP02-owned `write_pipeline.py`/`resynthesize_pipeline.py` matching the pre-existing repo-wide `follow_imports=skip` cast pattern) — zero NEW hard errors from this mission's diff. `ruff check src/charter src/specify_cli/charter_runtime` + the two WP04 test files = clean. Coverage (dotted `--cov=`) on the 7 mission-touched src modules: manifest.py 95%, project_drg.py 95%, resynthesize_pipeline.py 93%, write_pipeline.py 83% (100% on the mission's own changed lines — the file total is dragged down by large pre-existing untouched regions), computer.py 90%, _fresh_doctrine.py 93%, bundle.py 65% file-total but `compute_bundle_content_hash` (the mission's new function, including its `None` fail-safe branches) is 100% covered — all comfortably clear NFR-005's ≥90%-on-new/changed-lines bar. C-001/NFR-001 re-confirmed via `test_charter_synthesis_is_no_op_stable` (synthesize no-op) + `test_orchestrator_resynthesize.py`'s write-side no-op-stability guards (resynthesize no-op), both green in the sweep; `.kittify/` stayed clean across the full 1693-test run. T026: issue-matrix #2681 flipped `in-mission` → `fixed` with the WP01/WP02/WP03 commit-chain evidence; confirmed all 7 rows now terminal; DIR-003 caveat recorded; appended mission-close entries to all three tracer files (approach, design-decisions D8/D9, tooling-friction F5/F6/F7 + close-out summary). No unresolved TODO/FIXME in the mission diff. Committed on `fix/2681-synthesized-drg-stale`.
- 2026-07-16T18:26:54Z – claude – shell_pid=3014291 – WP04 af22cdc13 closeout; mission regression 1693 passed 0 failed
- 2026-07-16T18:27:00Z – user – shell_pid=3014291 – WP04 af22cdc13 closeout; mission regression 1693 passed 0 failed
- 2026-07-16T19:27:12Z – user – shell_pid=3014291 – mission complete; adversarial gates passed; #2681 fixed
