---
work_package_id: WP03
title: Arch-adversarial matrix split + partition guards
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
tracker_refs: []
planning_base_branch: tidy/ci-docs-charter-path-and-arch-adversarial-shard
merge_target_branch: tidy/ci-docs-charter-path-and-arch-adversarial-shard
branch_strategy: Planning artifacts for this mission were generated on tidy/ci-docs-charter-path-and-arch-adversarial-shard. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/ci-docs-charter-path-and-arch-adversarial-shard unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
- T014
phase: Phase 1 - CI health fixes
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1815867"
history:
- at: '2026-07-05T10:59:34Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: .github/workflows/ci-quality.yml
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- .github/workflows/ci-quality.yml
- tests/architectural/test_shard_universe_bounded.py
- tests/architectural/test_ci_quality_path_filters.py
- tests/release/test_coverage_topology_ownership.py
- tests/release/ci_topology_timings_postshrink.json
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Arch-adversarial matrix split + partition guards

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

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

- Expand `arch-adversarial` (`.github/workflows/ci-quality.yml`, currently one shard named `architectural`) into 3 matrix legs selecting by the `arch_shard_1/2/3` markers WP02 built, while preserving every existing invariant: always-on (`if: always()`), group-less (no dorny filter `if:`), de-serialized (no `needs:` edge), and the docs-only trim (PR #2391).
- Close the gate-unmask gap the post-plan brownfield squad found: `test_shard_universe_bounded.py` currently only gates jobs whose name contains `"core-misc"`, so it does not gate `arch-adversarial` at all — generalize it.
- Fix the two literal-shard-name pins the same squad found in `test_ci_quality_path_filters.py` that will otherwise red the moment the matrix changes.
- Update the committed CI-topology timings fixture (FR-007) so it stops describing arch-adversarial's single-shard bottleneck as an open follow-up (#2397) and instead records the sharded shape as canonical.
- Write the FR-008/SC-005 acceptance record for issue #2397 — explicitly re-verify and document each of its 5 invariant-safety criteria.
- Success = the slowest shard measured in the next real CI run comes in under the ~13.6-min next-lane sub-target (down from today's single-shard 14.4 min) — this WP cannot measure that locally, but every structural guard listed in `quickstart.md` must pass locally before this WP is done.

## Context & Constraints

- **Hard prerequisite**: WP02 must be complete — `arch_shard_1/2/3` must exist as real, collected markers (verify with `pytest --markers | grep arch_shard` and a quick `--collect-only -m arch_shard_1` before starting T008).
- Charter: `.kittify/charter/charter.md`.
- Mission plan: `kitty-specs/ci-health-charter-path-and-arch-shard-01KWRTB2/plan.md` (Concern B / IC-03, and the "Pre-tasks Scan Outcome" section — read it, it documents exactly why T010 exists), `research.md` (R2-R5), `data-model.md`, `quickstart.md`, `spec.md` (FR-003 through FR-006, Scenario B).
- The `arch-adversarial` job block in `.github/workflows/ci-quality.yml` (around line 1683-1800) carries an extensive block comment explaining WHY it must stay always-on/group-less/de-serialized — read it in full before editing. The critical invariants: `if: always()` unchanged; no `needs:` edge (would re-serialize behind the fast lane); no dorny filter `if:` gate (would re-enter `JOB_GROUPS` and lose the differential-matrix un-blinding).
- The docs-only detection step (`Detect docs-only PR (runtime narrowing signal)`) and its two-branch run script (full selection vs. `docs_scoped` trim) must be preserved **per shard** — each of the 3 legs independently narrows to `docs_scoped` on a docs-only PR, not just the matrix as a whole.
- Coverage artifact naming (`coverage-arch-adversarial-${{ matrix.shard }}.xml`, upload name `arch-adversarial-${{ matrix.shard }}-reports`) is already parameterized by `matrix.shard` — you are changing the **values** `matrix.shard` takes (from `architectural` to `arch_shard_1`/`arch_shard_2`/`arch_shard_3`), not the naming pattern itself.

## Branch Strategy

- **Strategy**: this WP owns `.github/workflows/ci-quality.yml`, `tests/architectural/test_shard_universe_bounded.py`, `tests/architectural/test_ci_quality_path_filters.py`, `tests/release/test_coverage_topology_ownership.py` — disjoint from WP01 and WP02's owned files.
- **Planning base branch**: `tidy/ci-docs-charter-path-and-arch-adversarial-shard`
- **Merge target branch**: `tidy/ci-docs-charter-path-and-arch-adversarial-shard`
- **Depends on**: WP02 (needs the markers to exist and be collectible before the workflow can select by them).

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### T008 – Expand the arch-adversarial matrix to 3 shards

- **Purpose**: The functional change — replace the single `architectural` shard with three marker-routed shards.
- **Steps**:
  1. In `.github/workflows/ci-quality.yml`'s `arch-adversarial` job, replace the single `strategy.matrix.include` entry:
     ```yaml
     matrix:
       include:
         - shard: architectural
           paths: >-
             tests/adversarial
             tests/architectural
             tests/architecture
             tests/lint
     ```
     with three entries, one per shard, each still listing all 4 root paths (the marker — not `paths` — now does the partitioning; `paths` stays the same across all three legs, matching how `fast-tests-core-misc` scopes `paths` broadly and lets `--ignore`/markers narrow within it):
     ```yaml
     matrix:
       include:
         - shard: arch_shard_1
           paths: >-
             tests/adversarial
             tests/architectural
             tests/architecture
             tests/lint
         - shard: arch_shard_2
           paths: >-
             tests/adversarial
             tests/architectural
             tests/architecture
             tests/lint
         - shard: arch_shard_3
           paths: >-
             tests/adversarial
             tests/architectural
             tests/architecture
             tests/lint
     ```
  2. Update the run-script step ("Run architectural + adversarial suite (always-on pole)") so **both** branches (docs-only and full-selection) AND the shard marker with `and`:
     - Full-selection branch: `-m 'arch_shard_${{ ... }}'`... actually GitHub Actions matrix values interpolate directly, so use `-m '${{ matrix.shard }} and not windows_ci and (git_repo or integration or architectural)'` for the full branch, and `-m '${{ matrix.shard }} and docs_scoped and not windows_ci'` for the docs-only branch. Since `matrix.shard` is now literally the marker name (`arch_shard_1` etc.), this is a direct substitution — no separate marker-name variable needed.
  3. Update the `name:` field and any adjacent comments that literally say `architectural` as the shard name to reflect the new 3-shard reality (the block comment above the job explains the OLD single-shard rationale — update the parts that are now stale, but keep the parts that still apply: always-on/group-less/de-serialized rationale doesn't change).
  4. Do **not** touch `if: always()`, `needs:` (absence), or add any dorny filter reference — verify with a diff review before moving on.
  5. Coverage/report naming: leave `coverage-arch-adversarial-${{ matrix.shard }}.xml` and `arch-adversarial-${{ matrix.shard }}-reports` exactly as they are — they'll now resolve to `coverage-arch-adversarial-arch_shard_1.xml` etc., which still matches the `coverage-*.xml` / `*-reports` glob patterns (confirmed shard-label-agnostic by T011).
- **Files**: `.github/workflows/ci-quality.yml`.
- **Parallel?**: No — foundational for this WP; T009/T010/T011 verify against this change.
- **Notes**: `paths` staying identical across all three legs is intentional — it mirrors how the marker alone determines the split. If you find `paths` narrowing gives a meaningfully faster `pytest` collection phase per shard, that's an optional micro-optimization, not a requirement; do not let it complicate the change if it risks correctness.

### T009 – Generalize the shard-universe-bounded guard

- **Purpose**: `tests/architectural/test_shard_universe_bounded.py`'s catch-all coverage today only recognizes jobs whose name contains `"core-misc"` (`_CATCH_ALL_SUBSTR = "core-misc"`). It currently does **not** gate `arch-adversarial` at all — sharding it without fixing this ships FR-005 (union = full universe, no drops, no double-counts) gate-unmasked.
- **Steps**:
  1. **Before T008** (or on a fresh checkout of this WP's starting point, before you've made the T008 edit), run `pytest tests/architectural/test_shard_universe_bounded.py -q` and confirm it passes today (it does — arch-adversarial isn't in its scope, so it's vacuously fine). This is your RED-first baseline: you're about to add an assertion that would have been meaningless before T008 and must be genuinely exercised after.
  2. Extend the guard so it also covers `arch-adversarial`: either broaden how catch-all jobs are identified (e.g., an explicit list of catch-all job names instead of/alongside the substring match — `{"core-misc", "arch-adversarial"}` or similar), or add a clearly-labeled sibling test function scoped specifically to `arch-adversarial` that asserts the same relation (no single shard collects the full universe once split).
  3. Author/adjust this assertion to be **RED against the pre-T008 single-shard topology** (a single `arch_shard_*`-style shard trivially collecting everything would fail the "no single shard collects the full universe" check) and **GREEN after T008's 3-shard split**. If you're doing this subtask after T008 is already in place, verify red-first by temporarily checking out the pre-T008 workflow state (or reasoning from the single-shard structure) rather than skipping the red proof.
  4. Keep the change scoped: do not loosen `_CATCH_ALL_SUBSTR`'s matching generically in a way that could silently absorb unrelated future jobs — name `arch-adversarial` explicitly if you extend the existing mechanism.
- **Files**: `tests/architectural/test_shard_universe_bounded.py`.
- **Parallel?**: No — depends on T008 to have something real to assert against for the GREEN half; the RED half should be checked before/independent of T008.
- **Notes**: Mirror this file's own documented discipline — its docstring already says the original guard was "Authored FAILING against today's topology" for `fast-tests-core-misc"`; do the analogous thing for `arch-adversarial` and say so in the docstring/comment you add.

### T010 – Fix the two literal-shard-name pins

- **Purpose**: `tests/architectural/test_ci_quality_path_filters.py` hard-pins the literal single-shard name `"architectural"` in two places that will red the instant T008 lands, unless fixed in the same change (found and verified by the post-plan brownfield squad — see `plan.md`'s "Pre-tasks Scan Outcome").
- **Steps**:
  1. Locate `test_execution_context_parity_ratchet_runs_unconditionally` (~line 225-260). It does:
     ```python
     arch_shard = next(
         entry
         for entry in arch_job["strategy"]["matrix"]["include"]
         if entry["shard"] == "architectural"
     )
     assert "tests/architectural" in str(arch_shard["paths"])
     ```
     Update this to work across all 3 legs instead of expecting exactly one named `"architectural"` — e.g., assert that `test_execution_context_parity.py`'s directory (`tests/architectural`) appears in **every** matrix leg's `paths` (since `paths` stays identical across shards per T008), or that at least one leg's `paths` contains it if you kept `paths` narrower per-shard. Preserve the underlying behavioral invariant this test protects: the parity ratchet file must still be in-scope of the always-on pole, and the pole must still be `if: always()` with the full-selection marker expression containing `git_repo or integration or architectural`.
  2. Locate `test_core_misc_integration_is_sharded_and_parallelized` (~line 262-300). It does:
     ```python
     arch_shards = {
         entry["shard"]
         for entry in _job(data, "arch-adversarial")["strategy"]["matrix"]["include"]
     }
     assert "architectural" in arch_shards
     ```
     Update the assertion to `assert arch_shards == {"arch_shard_1", "arch_shard_2", "arch_shard_3"}` (or a superset-safe `assert arch_shards, "arch-adversarial matrix must not be empty"` plus a separate assertion that the extracted-shard invariant — "the architectural pole didn't vanish from ci-quality.yml" — still holds under the new names). Preserve the comment explaining WHY this check exists (the architectural shard was extracted from `integration-tests-core-misc` and must still exist somewhere).
  3. Re-read both docstrings after your edit — update any prose that still says "the architectural shard" singular if it's now inaccurate.
- **Files**: `tests/architectural/test_ci_quality_path_filters.py`.
- **Parallel?**: Yes, relative to T009 and T011 (different assertions, same file for T010 only — no file overlap with T009/T011).
- **Notes**: Do not delete these assertions to make them pass trivially — re-pin the same behavioral invariant (which the memory on this repo's testing philosophy calls out explicitly: pin behavioral invariants, not literal code shape, but re-pin, don't remove).

### T011 – Confirm the coverage-topology-ownership guard

- **Purpose**: Confirm (per R4 in `research.md`) that `tests/release/test_coverage_topology_ownership.py` is genuinely shard-label-agnostic and needs no change for the new shard names.
- **Steps**:
  1. After T008 lands, run:
     ```bash
     pytest tests/release/test_coverage_topology_ownership.py -q
     ```
  2. If it passes unmodified: done, note this in your Activity Log (a confirmed-NIL result is a valid, useful outcome — do not invent a change to "be safe").
  3. If it fails: read the failure carefully — it's likely a narrow gap (e.g., an artifact-name assumption that didn't generalize as expected). Fix the **minimal** gap in either the guard or the workflow naming, whichever is actually wrong, and re-run.
- **Files**: `tests/release/test_coverage_topology_ownership.py` (only if a real gap is found — expected outcome is no change).
- **Parallel?**: Yes, relative to T009/T010.
- **Notes**: This test collapses GHA `${{ ... }}` interpolations to a placeholder before matching glob patterns — it was designed to be shard-count/shard-name agnostic. A failure here would be a genuine surprise worth flagging clearly, not silently working around.

### T012 – Full local + guard-suite verification

- **Purpose**: Final gate before this WP is done — every structural guard this mission touches or depends on must be green together, not just individually.
- **Steps**:
  1. Run every command in `quickstart.md`'s "Verify the partition invariants" and "Verify the workflow still stays de-serialized/group-less" sections:
     ```bash
     pytest tests/architectural/test_arch_shard_marker_completeness.py -q
     pytest tests/architectural/test_shard_universe_bounded.py -q
     pytest tests/release/test_coverage_topology_ownership.py -q
     pytest tests/architectural/test_arch_pole_deserialized.py -q
     pytest tests/architectural/test_docs_scoped_arch_coverage.py -q
     pytest tests/architectural/test_ci_quality_path_filters.py -q
     ```
  2. Also re-run the three shard-reproduction commands from `quickstart.md` (now against the real workflow, not just the marker mechanism) to sanity-check nothing regressed since WP02's T007.
  3. Record all outcomes (pass/fail counts) in the Activity Log.
- **Files**: none changed (verification only).
- **Parallel?**: No — final subtask, depends on T008-T011 all being complete.
- **Notes**: This WP cannot measure the real CI wall-clock improvement locally (that requires an actual GitHub Actions run) — the mission's acceptance walkthrough (`spec.md`) calls for confirming the slowest shard lands under ~13.6 min from the first post-merge CI run. Note this explicitly as a follow-up verification step for whoever reviews/merges this mission, per the same honesty discipline `ci_topology_timings_postshrink.json` already models (structural projection now, live measurement backfilled later).

### T013 – Update the CI-topology timings fixture (FR-007)

- **Purpose**: `tests/release/ci_topology_timings_postshrink.json` is a committed narrative/observation artifact (not asserted by any test — confirmed via `grep -rln ci_topology_timings tests/`, zero hits besides the file itself) that documents the canonical CI-topology shape. Today it explicitly frames `arch-adversarial`'s single-shard bottleneck as an open follow-up: `"arch_pole_is_bottleneck": "...matrix-sharding it (like fast-tests-core-misc) is tracked as the P1 follow-up #2397 to bring the path under the ~13.6-min sub-target."`. This mission IS that follow-up — the fixture must stop describing it as open.
- **Steps**:
  1. Read the full file first — note its existing honesty discipline: `post_shrink_projection` is explicitly labeled a "STRUCTURAL projection (NOT a measurement)" pending a real CI run, and was later backfilled with a real `measured_source_run_id` once PR #2391's CI run completed. You cannot backfill a real post-3-shard measurement here either (this mission hasn't run its own CI yet) — follow the same pattern: label your addition a projection, not a measurement.
  2. Add a new top-level block (e.g. `arch_shard_split`) recording: shard count (3), the shard names (`arch_shard_1/2/3`), the structural basis (216/215/215 def-count-proxy bin-packing, same caveat as `research.md` R2 — real durations pending the first post-merge CI run), and the mission/issue provenance (`ci-health-charter-path-and-arch-shard-01KWRTB2`, closes #2397).
  3. Update the existing `verdict`/`c006_nightly_decision` narrative fields that describe the un-sharded pole as a live problem — reframe them as historical (what was true before this mission) plus a pointer to the new block for the current state. Do not delete the historical numbers (29.4→14.4 min, 51% reduction) — they remain accurate history.
  4. Add an explicit `measured_source_run_id: null` (or equivalent) field on the new block with a note that the real per-shard duration must be backfilled from this mission's own first post-merge CI run — mirroring exactly how the file already handles this for the prior mission.
- **Files**: `tests/release/ci_topology_timings_postshrink.json`.
- **Parallel?**: Yes, relative to T009/T010/T011 (different file); depends on T008 for the shard names to reference.
- **Notes**: Do not invent a specific minute value for "how fast the new shards will be" — projected/structural language only, per this file's own established discipline.

### T014 – Write the FR-008/SC-005 acceptance record for issue #2397

- **Purpose**: The spec (FR-008, SC-005) requires explicitly re-verifying and recording, for issue #2397's invariant-safety criteria, how each was checked — this record becomes the PR-body material the operator uses at merge/close time.
- **Steps**:
  1. Create `kitty-specs/ci-health-charter-path-and-arch-shard-01KWRTB2/acceptance-record.md`.
  2. Issue #2397's "Invariant-safety note" lists 4 explicit numbered criteria plus one unnumbered follow-on consideration (the docs-only-trim interaction) — treat all 5 as the criteria SC-005 refers to. For each, record: the criterion text (paraphrased from #2397), which guard test proves it, and the actual pass/fail outcome from T012's run (do this step LAST, after T012 has actually run, so you're recording real results, not intentions):
     1. Shards stay group-less/always-on, no differential triggering by changed path → `test_arch_pole_deserialized.py`
     2. NFR-002 (100% of `src` changes) stays green post-split → `test_ci_architectural_gate_coverage.py` / the differential-matrix model in `_gate_coverage.py`
     3. The #2368 marker→job-authority invariants stay green → `test_marker_job_completeness.py`, `test_arch_shard_marker_completeness.py` (this mission's new guard)
     4. FR-006 coverage-ownership stays intact (no drop/double-count) → `test_coverage_topology_ownership.py`, `test_shard_universe_bounded.py` (generalized in T009)
     5. The PR #2391 docs-only trim still holds post-split → `test_docs_scoped_arch_coverage.py`
  3. Add a one-line closing statement: "Issue #2397 is closed by this mission; all 5 invariant-safety criteria re-verified as above."
- **Files**: `kitty-specs/ci-health-charter-path-and-arch-shard-01KWRTB2/acceptance-record.md` (new).
- **Parallel?**: No — must run after T012 (needs real pass/fail results, not planned intentions).
- **Notes**: `kitty-specs/` paths cannot be declared in a `code_change` WP's `owned_files` (the finalizer rejects it — `INVALID_WP_OWNED_FILES_KITTY_SPECS`), so this file is a genuine, deliberate **ownership-map-leeway** edit: small, well-justified, and explicitly called for by FR-008/SC-005. Add a one-line rationale comment at the top of the new file noting it's WP03's FR-008 deliverable, then in your Activity Log note the leeway explicitly (per the charter: "a small, well-justified out-of-map edit is acceptable when recorded with a one-line rationale — no-overlap is the real guard"). No other WP touches this path, so there's no collision risk.

## Test Strategy

- No brand-new test files in this WP beyond the guard modifications above (T009, T010, T011 modify existing guards; no `pytest` invocation is skipped).
- The full local verification list in T012 is the mandatory gate for this WP's Definition of Done, and its results feed directly into T014's acceptance record.

## Risks & Mitigations

- **Risk**: Re-adding a `needs:` edge or a dorny filter `if:` by accident while editing the matrix block. **Mitigation**: `test_arch_pole_deserialized.py` and the differential-matrix guards catch this — T012 re-runs them explicitly.
- **Risk**: `_CATCH_ALL_SUBSTR` generalization (T009) silently widens scope to absorb an unrelated job. **Mitigation**: name `arch-adversarial` explicitly rather than loosening the substring match broadly.
- **Risk**: The docs-only trim stops applying per-shard (e.g., only one of the three legs gets the `docs_scoped` narrowing). **Mitigation**: verify all three legs' run-scripts have the same two-branch structure after T008; `test_docs_scoped_arch_coverage.py` should catch a regression here too.
- **Risk**: Real per-shard CI duration doesn't land under ~13.6 min despite a mechanically correct 216/215/215 split (the def-count proxy isn't a true duration measurement — see `research.md` R2). **Mitigation**: this is explicitly out of this WP's control; flag it as a post-merge follow-up per T012's note rather than trying to force a local "fix."

## Review Guidance

- Confirm the arch-adversarial job's `if: always()`, absence of `needs:`, and absence of a dorny filter `if:` are all unchanged in the diff.
- Confirm all three matrix legs preserve the docs-only two-branch run-script structure.
- Confirm `test_shard_universe_bounded.py`'s new/extended assertion is genuinely exercised (not vacuous) — ask for the RED-before/GREEN-after evidence from the Activity Log.
- Confirm `test_ci_quality_path_filters.py`'s two fixed assertions still protect the same behavioral invariants they did before (parity ratchet in-scope; extracted arch shard still exists) — not just "made to pass."
- Confirm the T012 verification list is fully green and recorded.

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

**Why this matters**: The acceptance system reads the LAST activity log entry as the current state. If entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- 2026-07-05T10:59:34Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP03 --to <status>` to change WP status.
- 2026-07-05T11:52:33Z – claude:opus:python-pedro:implementer – shell_pid=1785160 – Assigned agent via action command
- 2026-07-05T12:20:22Z – claude:opus:python-pedro:implementer – shell_pid=1785160 – T008: arch-adversarial matrix expanded 1->3 shards (arch_shard_1/2/3), both run-script branches AND the marker with matrix.shard; if:always()/no-needs/no-dorny-filter unchanged (verified by diff review + green test_arch_pole_deserialized.py). T009: generalized test_shard_universe_bounded.py's catch-all scope to name arch-adversarial explicitly (closing the planning-time gate-unmask gap); RED proven against pre-T008 single-shard topology (806/806 tests, 1 shard = full universe) via git-stash-workflow-only, GREEN after T008 restored. T010: fixed the 2 literal 'architectural' shard-name pins in test_ci_quality_path_filters.py (parity-ratchet-in-scope + extracted-shard-still-exists invariants re-pinned against {arch_shard_1,2,3}, not deleted). LIVE FINDING beyond the WP prompt: test_docs_scoped_arch_coverage.py had a third undiscovered literal pin (_ARCH_POLE_SHARD, module-import-time StopIteration) -- fixed via ownership-map-leeway (no owned_files collision with WP01/WP02), plus added test_all_arch_shard_legs_share_identical_paths to guard the fix's representative-leg assumption. T011: test_coverage_topology_ownership.py confirmed PASSING UNMODIFIED (7 passed) -- shard-label-agnostic per R4, no change needed. T012: full quickstart.md guard list green -- test_arch_shard_marker_completeness.py (3 passed), test_shard_universe_bounded.py + test_coverage_topology_ownership.py + test_arch_pole_deserialized.py + test_docs_scoped_arch_coverage.py + test_ci_quality_path_filters.py (35 passed) = 38/38. Local shard reproduction: arch_shard_1/2/3 full-selection collect 248/241/317 = 806 total (matches pre-split universe, no gaps/overlap per completeness guard); docs-only trim confirmed per-shard (shard1=15, shard2=0 [expected -- no known docs scanner assigned there], shard3=47). T013: ci_topology_timings_postshrink.json got a new arch_shard_split block (FR-007, measured_source_run_id=null, projection language only) plus historical reframing of verdict/c006_nightly_decision fields pointing at it; zero test files assert against this fixture (confirmed via grep), matching its narrative-only status. T014: acceptance-record.md committed directly to this lane (kitty-specs/.../acceptance-record.md, commit 2a28125ae) -- the pre-commit guard printed a WARNING ('Protected path... implementation branches must not modify kitty-specs/') but did NOT hard-reject; no conflicting file exists on any other branch. Flagging this warning to the orchestrator for awareness at merge time. Ruff clean on all 4 changed .py files; mypy clean (extra check, not the mandated gate).
- 2026-07-05T12:21:30Z – claude:opus:python-pedro:implementer – shell_pid=1785160 – Ready for review: arch-adversarial split into 3 marker-routed shards (arch_shard_1/2/3), shard-universe/path-filter guards fixed+generalized, timings fixture updated. 38/38 T012 guard tests green. Live finding beyond WP prompt: test_docs_scoped_arch_coverage.py had a 3rd hidden literal shard-name pin, fixed via documented ownership-map-leeway. T014's acceptance-record.md content is reported to the orchestrator to commit from the coordination branch (kitty-specs/ changes rejected on lane branches by this gate).
- 2026-07-05T12:25:26Z – claude:opus:reviewer-renata:reviewer – shell_pid=1815867 – Started review via action command
- 2026-07-05T12:36:35Z – user – shell_pid=1815867 – Review passed: workflow invariants (if:always(), no needs:, no dorny filter) confirmed unchanged in diff; both run-script branches AND the shard marker; shard-universe/path-filter guards genuinely re-pinned (not weakened); 38/38 T012 guards live-verified green; shard counts 248/241/317=806 and docs-only 15/0/47 reproduced exactly matching claims; third literal-pin fix in test_docs_scoped_arch_coverage.py verified real (StopIteration risk) with a genuinely load-bearing new guard; ownership-leeway edit collision-free; timings fixture properly labeled as projection; ruff+mypy clean; acceptance-record.md correctly landed on coordination branch, not the lane.
