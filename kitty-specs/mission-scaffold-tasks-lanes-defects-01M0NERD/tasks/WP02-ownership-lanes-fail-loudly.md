---
work_package_id: WP02
title: FR-002/FR-003/FR-004 - ownership bootstrap, lane computation, and authoritative_surface validation fail loudly (mission_finalize.py)
dependencies: []
requirement_refs:
- FR-002
- FR-003
- FR-004
- FR-005
- NFR-001
- NFR-002
- NFR-004
- C-001
- C-002
- C-004
- C-005
planning_base_branch: fix/mission-scaffold-lanes-defects-3673
merge_target_branch: fix/mission-scaffold-lanes-defects-3673
branch_strategy: Planning artifacts for this mission were generated on fix/mission-scaffold-lanes-defects-3673. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/mission-scaffold-lanes-defects-3673 unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
- T014
- T015
- T016
- T017
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/mission_finalize.py
- tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py
- tests/tasks/test_finalize_tasks_json_output_unit.py
role: implementer
tags: []
tracker_refs: []
---

# WP02 - FR-002/FR-003/FR-004: ownership bootstrap, lane computation, and authoritative_surface validation fail loudly

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Make three failure points in `src/specify_cli/cli/commands/agent/mission_finalize.py` fail
loudly instead of degrading to silent success: (FR-002) a `code_change` WP with an explicit
`owned_files: []` is rejected at bootstrap, aggregated across all offenders in one run;
(FR-003) `_compute_and_write_lanes` raises instead of returning `(None, None)`, covering both
halves of its compound guard; (FR-004) `_validate_ownership_manifests` runs its
`authoritative_surface` checks unconditionally, not gated on `wp_manifests` being non-empty.

## Context

**No dependency on WP01.** WP01 and WP02 are independent write scopes (`mission_creation.py`
vs `mission_finalize.py`) with no shared production code and no ordering requirement between
them — see `tasks.md`'s Dependencies section for the explicit statement. Either WP may be
implemented first, second, or in parallel.

**PR shape**: this WP lands as part of the single mission PR (plan.md §12 — one PR, the diff
fits in one sitting). Do not open a separate PR for this WP.

**Reflexivity warning (plan.md §6b, C-004, binding on THIS mission's own tasks-authoring):**
this mission's own `tasks.md`/WP files (the ones you are reading right now) were deliberately
authored WITHOUT any `execution_mode: code_change` WP carrying an explicit `owned_files: []` —
if you were to introduce such a WP anywhere in this mission's own authoring, it would trip the
very FR-002 reject this WP implements. This is a correct rejection if it happened, not a bug —
but it should not happen, because the tasks-authoring step got it right the first time. This
note is informational; you are the implementer, not the tasks-author, but keep it in mind if
you touch this mission's own WP frontmatter for any reason (you should not need to).

**Exact seam** (plan.md §1, verified against this checkout's HEAD on
`fix/mission-scaffold-lanes-defects-3673`, 2026-08-22 — re-verify all line numbers yourself
before editing; they may have drifted, and PR #3666 (open, touches this same file — see below)
may shift them further):

| Function | Lines | Change |
|---|---|---|
| `_apply_ownership_inference` | `def` at **1264**; `owned_files_explicitly_empty = _owned_files_yaml_is_explicit_empty_list(wp_raw_content)` at **1275**; `need_owned_files = not wp_meta.owned_files and not owned_files_explicitly_empty` at **1277**; body spans **1264-1295** | FR-002's reject is *detected* here (does not raise here). Return type changes from `tuple[bool, list[str]]` to **`tuple[bool, list[str], str \| None]`** — third element is the contradiction message (naming the WP ID) when `execution_mode == "code_change"` AND `owned_files_explicitly_empty` is `True`; `None` otherwise. `infer_warnings` (2nd element) is unchanged in meaning — do not conflate it with the contradiction data. |
| `_run_bootstrap_loop` | `def` at **1298**; per-WP `for wp_file in wp_files:` loop at **1324**; calls `_apply_ownership_inference` at **1365**; `return state` at **1394**; body spans **1298-1394** | This is where FR-002's reject is actually *resolved*. Extract the 3rd tuple element from `_apply_ownership_inference`'s return; when not `None`, append it to a new `state.ownership_contradictions: list[str]` field (add to the `_BootstrapState` dataclass at **1188**) and `continue` to the next WP file (do not abort mid-loop). After the loop finishes iterating ALL WP files, still inside `_run_bootstrap_loop`, before `return state` at line 1394: if `state.ownership_contradictions` is non-empty, raise **one** aggregated error naming every offending WP ID. |
| `_validate_ownership_manifests` | `def` at **1475**; guard `if not wp_manifests:` / `return` at **1484-1485** | FR-004: remove/narrow this short-circuit so `authoritative_surface` glob-match/overlap/audit-coverage checks run unconditionally, even when `wp_manifests` is empty. |
| `_compute_and_write_lanes` | `def` at **1820**; compound guard `if not (wp_manifests and wp_dependencies):` / `return None, None` at **1834-1835** | FR-003: replace `return None, None` with a raise naming which half of the compound guard tripped (empty `wp_manifests` vs. empty `wp_dependencies` with non-empty `wp_manifests`) — both halves must be covered. |

**`build_wp_manifests` (`src/specify_cli/ownership/validation.py:335`) is examined but NOT
diffed by this WP.** Its acceptance predicate at line 356 (`if fm.execution_mode and
fm.owned_files:`) is left unchanged — after FR-002's fix, it simply never sees the
`code_change` + explicit-`[]` combination reach it, because that WP already failed the run
upstream in `_run_bootstrap_loop`. Do not modify `validation.py` as part of this WP.

**Batch-vs-first-offense design, binding (plan.md §1, PLAN-ARCH-001):** collect-all-offenders-
then-raise-once, NOT raise-on-first-offense. `_apply_ownership_inference` must never itself
raise for the contradiction case — it only returns the descriptor. The raise happens exactly
once, in `_run_bootstrap_loop`, after the full loop over all WP files completes. This is
required so a single `finalize-tasks` run names every offending WP, not just the first one hit
(spec.md User Story 2 / Acceptance Scenario 4).

**Pipeline-ordering constraint (plan.md §5, binding — do not violate):** No WP may reorder
`_flush_frontmatter_writes` (`mission_finalize.py:2752`) or `_emit_local_canonical_events`
(`:2332`, inside `_run_commit_pipeline` at `:2789`) relative to the FR-003/FR-004 checks
(`_validate_ownership_manifests` at `:2766`, `_compute_and_write_lanes` called internally at
`:2342`). The residual gap this leaves — an FR-003/FR-004 reject may still leave WP frontmatter
already mutated on disk, and for FR-003 specifically may leave `TasksCompleted` already
persisted — is a **documented, operator-accepted known limitation** (NFR-004's narrowed scope,
ledger SK-71). Do not attempt to "improve" this ordering as part of this WP; it needs separate
operator sign-off and interacts with open PR #3666 in this same file.

**FR-003's return-type consequence, adopted resolution (plan.md §1, PLAN-ARCH-002, binding):**
once FR-003's raise lands, `_compute_and_write_lanes`'s declared return type
(`tuple[Path | None, LanesManifest | None]`) can never again produce `(None, None)`, making two
downstream `None`-handling guards permanently unreachable for this call path:
`_scaffold_acceptance_matrix_if_lane_based`'s `if lanes_manifest is None or validate_only:
return` (`:1951`) and `_collect_finalize_artifacts`'s `if lanes_path is not None:
candidates.append(lanes_path)` (`:270`). **Adopted: leave both guards in place as
harmless-but-now-unreachable defensive code, each with a short inline comment** (e.g.
"unreachable for the `_compute_and_write_lanes` call path since FR-003; kept as defensive
code, not dead-code cleanup"). Do NOT narrow the return-type annotation — that is explicitly
out of scope (a future mission's optional cleanup, not this one's).

**Rebase-watch, PR #3666 (plan.md §7) — not blocking, but scope your diff precisely.** PR #3666
("fix: preserve planning branch for legacy PR-bound missions") is open and also touches
`_run_bootstrap_loop` — its **signature** (adds `merge_target_branch: str | None = None`) and
one body line (a `merge_target_branch=merge_target_branch,` kwarg inserted into the existing
`_apply_bootstrap_fields(...)` call, three lines above the `_apply_ownership_inference(...)`
call site this WP instruments). **Your diff to `_run_bootstrap_loop` must be scoped to its BODY
only** — the new `state.ownership_contradictions` accumulation and the post-loop aggregated
raise — anchored strictly after the `_apply_ownership_inference(...)` call's return statement.
Do NOT touch `_run_bootstrap_loop`'s signature, and do NOT reformat, reorder, or otherwise touch
the `_apply_bootstrap_fields(...)` call block three lines above your instrumentation point —
that belongs to #3666. Also out of scope: `_apply_bootstrap_fields`, `_branch_strategy_text`,
`_resolve_target_branch`, `finalize_tasks`'s branch-resolution preamble. Before finalizing this
WP, re-run `gh pr view 3666 --json files,state` to catch drift (merged/amended/closed).

**No new CLI surface (C-001/FR-005, binding).** No new command, subcommand, flag, or disguised
escape hatch anywhere in `src/specify_cli/`. **This WP owns the authoritative SC-005
verification**: after implementing, run the `registered_commands`/`registered_groups` walk
(see T016 below) — NOT merely the git-diff grep, which is a known-incomplete fast pass only
(plan.md §4, PLAN-GOV-001 — the grep's `@.*\.command\(\)` alternative only matches literal
empty-parens decorators and misses every real sub-app command registration in this codebase).

**C-005 baseline-red protocol (plan.md §9) — run BEFORE your first implementation change:**
1. Run the specific test file/test you are about to extend against the current branch.
2. Run the same test against the merge-base / `upstream/main`.
3. Classify: red-on-branch+green-on-base = your regression; red-on-both = pre-existing, out of
   scope, note it; only failures red on your branch and green on base are yours to fold in.
4. Record the classification in your WP validation notes.

**Campsite-clean note (plan.md §10):** none of the four touched functions are over or near the
complexity ceiling (15) today (`_apply_ownership_inference`=5, `_run_bootstrap_loop`=11,
`_validate_ownership_manifests`=11, `_compute_and_write_lanes`=8, via
`ruff check --select C901`) — no preceding campsite-clean WP is warranted. BUT
`_run_bootstrap_loop` is the tightest margin (11/15) and this WP's own change adds at least one,
likely two, new branches — **you must re-run the complexity check after your change** (see T016)
and extract a helper if it lands at or above 15.

### Subtask T008: Establish the C-005 baseline-red protocol for this WP's test surface

**Purpose**: Confirm, before writing any test or implementation change, which tests in this
WP's target files are already red on the merge-base.

**Steps**:
1. Run `.venv/bin/python -m pytest tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py -q`
   and `.venv/bin/python -m pytest tests/tasks/test_finalize_tasks_json_output_unit.py -q` on
   the current branch; record pass/fail counts.
2. Run the same two files against the merge-base commit.
3. Classify per the C-005 protocol. Note the result in your WP validation summary.
4. Also note: PR #3666 independently touches `test_mission_finalize_phases.py` (adds tests near
   line ~459-484, before `test_apply_bootstrap_fields_noop_when_already_set` at line 462) — if
   your baseline run shows unfamiliar tests already present in that region, that is #3666's
   content already landed or being concurrently authored; do not treat it as your own
   pre-existing red without checking `gh pr view 3666 --json files,state` first.

**Files**: none changed — read-only verification.
**Validation**: written classification for every relevant test.

### Subtask T009: Red-first tests — FR-002 direct-seam contradiction descriptor shape

**Purpose**: Prove `_apply_ownership_inference`'s new 3-tuple return shape, both the
contradiction case and the unaffected planning-artifact case, at the seam level (bypassing
`_run_bootstrap_loop`).

**Steps**:
1. In `tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py`, following the
   existing `test_apply_ownership_inference_skips_when_present` pattern (verified at line
   ~487: builds a `WPMetadata`, calls `seam._apply_ownership_inference(bld, meta, "body",
   "001-m", {})` directly), add a test with `execution_mode="code_change"` and a raw
   frontmatter body carrying an explicit `owned_files: []`. Assert the call does **NOT** raise
   — it returns `changed, warnings, descriptor = seam._apply_ownership_inference(...)` with
   `descriptor` a non-`None` `str` naming the WP ID (Acceptance Scenario 1's detection, but the
   raise itself is asserted in T010, not here — this test is specifically about the
   direct-call, non-raising, descriptor-returning behavior).
2. Add a sibling test with `execution_mode="planning_artifact"` and the same explicit
   `owned_files: []` body (the existing, legitimate escape hatch — Acceptance Scenario 3).
   Assert `_apply_ownership_inference` returns `descriptor is None` — the "absent" case is
   `None`, not an empty string or empty list slot.
3. Confirm both are RED (or, for the planning-artifact case, confirm it currently doesn't even
   have a 3rd return value to assert on — i.e. RED because the current signature is a 2-tuple)
   against current (pre-implementation) code.
4. Also drive the full pipeline for the `planning_artifact` + explicit-`owned_files: []` case,
   not just the direct seam call from step 2: call `_run_bootstrap_loop` **only** (this file's
   own module docstring states end-to-end `finalize_tasks` coverage is owned by
   `test_mission_finalize_tasks.py`/`test_feature_finalize_bootstrap.py`/the validate-only
   readonly suite/the WP01 golden harness, not here — mirroring how T011 step 1 cites plan.md's
   PLAN-VERIFY-002 to pin which file owns end-to-end coverage; this file has zero
   `CliRunner`/`runner.invoke` usage, so there is no existing convention here to defer to for a
   `finalize_tasks` alternative) with that fixture. Assert `wp_id in
   state.inmemory_frontmatter` (or that `state.inmemory_frontmatter[wp_id].owned_files == []`
   and `.execution_mode == "planning_artifact"` are preserved) **AND** assert `wp_id not in
   state.ownership_contradictions` (the field T015 adds). **Do not assert on
   `state.work_packages`** — `state.work_packages.append(...)` runs unconditionally for every
   readable WP file at line ~1351, strictly before `_apply_ownership_inference` is even called
   at line ~1365, so `wp_id in state.work_packages` would be `True` identically whether this WP
   is correctly accepted or incorrectly treated as a contradiction and `continue`d away —
   it cannot discriminate the two outcomes this step exists to distinguish.
   `state.inmemory_frontmatter[wp_id]` and `state.ownership_contradictions`, by contrast, are
   only populated (or only omitted) after the contradiction check runs, so they do discriminate.
   Step 2's direct-seam assertion only proves `_apply_ownership_inference` itself returns
   `descriptor=None`; it does not exercise `_run_bootstrap_loop` end-to-end, so it does not, on
   its own, verify spec.md User Story 2 Acceptance Scenario 3's literal claim that the WP "is
   accepted exactly as it is today" (a full-pipeline claim). This step closes that gap.
5. Note the caveat plan.md flags (PLAN-VERIFY-001): `tests/specify_cli/cli/commands/test_finalize_tasks_explicit_empty_owned_files.py`
   already exists but its 6 tests call ONLY the pure helper `_owned_files_yaml_is_explicit_empty_list`
   — none construct a `WPMetadata` or call `_apply_ownership_inference`. It is a useful
   supporting regression check (run it in T017), not a substitute for this subtask's coverage.

**Files**: `tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py` (extend,
~65-95 new lines — step 4's `_run_bootstrap_loop` fixture (`wp_files`, `dep_resolution`,
`wps_manifest`, `mission_slug`, `repo_root`, `target_branch`, `concern_coverage_warnings`,
`requirement_extraction_warnings`, `validate_only`, `json_output`) plus its
`state.inmemory_frontmatter`/`state.ownership_contradictions` assertions are materially
heavier than steps 1-2's direct `WPMetadata`-construction calls).
**Validation**: red before implementation (T015), green after.

### Subtask T010: Red-first tests — FR-002 aggregated raise via `_run_bootstrap_loop`

**Purpose**: Prove the collect-all-then-raise-once design end to end, including the batch case
naming every offender in one run.

**Steps**:
1. In `test_mission_finalize_phases.py`, add a test driving `_run_bootstrap_loop` **only**
   (this file's own module docstring reserves end-to-end `finalize_tasks` coverage for
   `test_mission_finalize_tasks.py`/`test_feature_finalize_bootstrap.py`/the validate-only
   readonly suite/the WP01 golden harness — mirroring how T011 step 1 cites plan.md's
   PLAN-VERIFY-002 to pin which file owns end-to-end `finalize-tasks --json` coverage; this
   file has zero `CliRunner`/`runner.invoke` usage, so there is no existing convention here to
   defer to for a `finalize_tasks` end-to-end alternative) with a WP-file list containing ONE
   offending WP (`code_change` + explicit `owned_files: []`). Assert the run raises once the
   loop completes, naming the WP ID and stating "code_change WP declares no owned files" (or
   the exact message you implement — keep it consistent and actionable per NFR-001).
2. Add a second test (Acceptance Scenario 4 — the batch case) with a mission fixture containing
   2+ WPs sharing the same contradiction PLUS at least one valid WP. Assert the single run fails
   **once** and names **every** offending WP ID in that one aggregated error — not just the
   first — and does NOT silently drop only the bad WPs and proceed to compute lanes for the
   rest.
3. Confirm both RED against current (pre-T013) code.

**Files**: `test_mission_finalize_phases.py` (extend, ~60-80 new lines).
**Validation**: red before T015, green after.

### Subtask T011: Red-first test — FR-002 `--json` payload (Acceptance Scenario 2)

**Purpose**: Confirm the `--json` error payload carries a stable machine-readable field for one
or more offending WP IDs, distinguishable from other `finalize-tasks` failure modes.

**Steps**:
1. In `tests/tasks/test_finalize_tasks_json_output_unit.py` (already drives the full command via
   `runner.invoke(app, ["finalize-tasks", "--json"])` and asserts JSON schema shape for the
   success path — verified, per plan.md's PLAN-VERIFY-002 correction, that
   `test_mission_finalize_tasks.py` and `test_mission_close.py` are NOT the right homes for
   this), add a sibling test following its existing `CliRunner`/mock-patch pattern, driving a
   fixture that trips the FR-002 reject.
2. Assert the JSON payload includes a stable machine-readable field naming one-or-more
   offending WP IDs (singular when one WP contradicts, plural when aggregated) plus a stable
   error code for this specific contradiction.
3. Confirm RED against current code.

**Files**: `tests/tasks/test_finalize_tasks_json_output_unit.py` (extend, ~30-40 new lines).
**Validation**: red before T015, green after.

### Subtask T012: Red-first tests — FR-003 raises on both halves of the compound guard

**Purpose**: Prove `_compute_and_write_lanes` raises rather than returning `(None, None)`,
covering both the empty-`wp_manifests` half and the non-empty-`wp_manifests`-but-empty-
`wp_dependencies` half (Acceptance Scenario 5 — the compound guard is
`not (wp_manifests and wp_dependencies)`).

**Steps**:
1. In `test_mission_finalize_phases.py`, add a direct-seam test calling
   `_compute_and_write_lanes` (no existing direct-seam test for this function was found per
   plan.md — follow the file's established direct-call conventions used for
   `_apply_ownership_inference`/`_flush_frontmatter_writes`) with a fixture where
   `wp_manifests` is empty. Assert it raises (not returns `(None, None)`) and that `lanes.json`
   is confirmed absent afterward.
2. Add a sibling test with `wp_manifests` non-empty but `wp_dependencies` empty. Assert it also
   raises — this proves the whole compound guard is covered, not just the `wp_manifests`-empty
   half.
3. Confirm both RED against current code.

**Files**: `test_mission_finalize_phases.py` (extend, ~50-60 new lines).
**Validation**: red before T016, green after.

### Subtask T013: Red-first tests — FR-003 `--json` failure surfaced + residual-gap test

**Purpose**: Cover Acceptance Scenario 2/SC-003 (JSON failure surfaced) and Acceptance Scenario
6/§5 (the residual, operator-accepted gap — `lanes.json` absence guaranteed, frontmatter/event
absence explicitly NOT guaranteed).

**Steps**:
1. In `tests/tasks/test_finalize_tasks_json_output_unit.py`, add a failure-path test using the
   existing `runner.invoke(app, ["finalize-tasks", "--json"])` pattern with the empty-manifest
   fixture from T012. Assert the payload reports failure (not `"result": "success"`) with a
   machine-readable indication lane computation did not run.
2. Add a test in `test_mission_finalize_phases.py`, following that file's own established
   `pytest.raises(...)`-around-a-direct-call pattern (e.g. the pattern at its existing lines
   ~137, 162, 174, 186, 337, 380, 433, 557, 582), covering the FR-003 reject with the
   empty-`wp_manifests` fixture from T012. This test MUST wrap the direct-seam call to
   `_compute_and_write_lanes` in `pytest.raises(...)` and assert on the raised exception
   FIRST — this is the actual revert-sensitive assertion: pre-fix, the function returns
   `(None, None)` without ever calling `write_lanes_json`, so `lanes.json` is already absent
   both before and after the fix, and an absence-only assertion would be vacuous (pre-fix ==
   post-fix). **Do NOT place this `pytest.raises(...)`-wrapped assertion in
   `tests/tasks/test_finalize_tasks_json_output_unit.py`, and do NOT wrap a
   `runner.invoke(app, ["finalize-tasks", ...])` call in `pytest.raises(...)` anywhere** — that
   file drives `finalize-tasks` exclusively through Typer's `CliRunner.invoke()` (all 8 existing
   call sites; none pass `catch_exceptions=False`), which catches any exception raised inside the
   invoked command into `result.exception` instead of propagating it to the caller, so a
   `pytest.raises(...)` wrapped around `runner.invoke(...)` there would report "DID NOT RAISE"
   both before AND after the fix — permanently red, never reaching green. THEN, after the
   `pytest.raises` block, assert `lanes.json` is confirmed absent as a secondary, defense-in-depth
   check. **The test's docstring/comment must state explicitly that it does NOT assert
   frontmatter/event-log absence** — that guarantee is not provided by this mission (plan.md §5,
   NFR-004's narrowed scope, ledger SK-71) and asserting it would be a false claim a future reader
   might otherwise "fix" the test into making. Optionally, as a SEPARATE, additional assertion
   (never a substitute for the direct-seam test above), you may also add a
   `runner.invoke(app, ["finalize-tasks", ...])`-based test in
   `test_finalize_tasks_json_output_unit.py` that asserts `result.exception is not None` (or
   inspects `result.exit_code` / the JSON payload) following that file's actual convention — but
   that assertion must never be wrapped in `pytest.raises(...)`.
3. Confirm RED against current code: the failure-surfaced JSON assertion (step 1) is RED
   pre-fix as expected; the residual-gap test's direct-seam `pytest.raises(...)` assertion (step
   2, in `test_mission_finalize_phases.py`) is also RED pre-fix (no exception is raised yet, so
   `pytest.raises` itself fails), confirming the test is genuinely revert-sensitive rather than
   vacuous.

**Files**: `tests/tasks/test_finalize_tasks_json_output_unit.py` (step 1's mandatory
`runner.invoke`-based failure-surfaced test, plus step 2's optional non-`pytest.raises`
full-command assertion) and `test_mission_finalize_phases.py` (step 2's mandatory direct-seam
`pytest.raises(...)` residual-gap test) (extend, ~40-50 new lines total).
**Validation**: red before T016, green after; residual-gap test does not overclaim.

### Subtask T014: Red-first tests — FR-004 `authoritative_surface` validation runs unconditionally

**Purpose**: Cover Acceptance Scenarios 3 and 4 — a malformed value is now caught even when
`wp_manifests` is empty, AND a valid value still passes cleanly (both directions required, not
just the rejection path).

**Steps**:
1. In `test_mission_finalize_phases.py`, add a direct-seam call to
   `seam._validate_ownership_manifests(...)` (following the file's established pattern) with
   `wp_manifests` empty AND at least one WP frontmatter carrying a malformed
   `authoritative_surface` (bare `src/`, empty string, or a path with a spurious trailing
   slash). Assert validation still runs and rejects the malformed value with a specific error
   identifying the WP and the field — not the old silent `if not wp_manifests: return`.
2. Add a sibling test with `wp_manifests` empty but all `authoritative_surface` values valid
   prefixes that genuinely match the project layout. Assert the mission still passes exactly as
   it would with a non-empty manifest map — this proves the fix does not turn a
   legitimately-empty, legitimately-valid mission into a spurious failure.
3. Confirm the rejection test is RED against current code; the acceptance test should already
   pass today in the sense that it's currently short-circuited to a silent no-op "success" —
   note whichever framing is accurate once you've read the current code.

**Files**: `test_mission_finalize_phases.py` (extend, ~50-60 new lines).
**Validation**: rejection test red before T016, green after; acceptance test green both before
and after (proves no spurious over-rejection).

### Subtask T015: Implement FR-002 — bootstrap contradiction detection + aggregated raise

**Purpose**: The actual production-code fix for FR-002.

**Steps**:
1. In `src/specify_cli/cli/commands/agent/mission_finalize.py`, change
   `_apply_ownership_inference`'s return type from `tuple[bool, list[str]]` to
   `tuple[bool, list[str], str | None]`. After the existing
   `owned_files_explicitly_empty = _owned_files_yaml_is_explicit_empty_list(wp_raw_content)`
   computation (line ~1275), add the contradiction check: if `execution_mode == "code_change"`
   (accounting for however `execution_mode` is about to be inferred/confirmed at this point in
   the function — read the surrounding code before assuming) AND `owned_files_explicitly_empty`
   is `True`, set the third return element to a message naming the WP ID and stating the
   contradiction ("code_change WP declares no owned files" or equivalent); otherwise `None`.
   **Do not raise here.**
2. Add a new `ownership_contradictions: list[str]` field to the `_BootstrapState` dataclass
   (line ~1188).
3. In `_run_bootstrap_loop`'s per-WP `for` loop (line ~1324, calling
   `_apply_ownership_inference` at ~1365), extract the third tuple element. When not `None`,
   append it to `state.ownership_contradictions` and `continue` to the next WP file — do not
   abort the loop. **Anchor this new code strictly after the `_apply_ownership_inference(...)`
   call's return** (the statement(s) immediately following that call) — do not touch or
   reformat the `_apply_bootstrap_fields(...)` call block three lines above it (PR #3666's
   territory).
4. After the loop finishes iterating all WP files, still inside `_run_bootstrap_loop`, before
   `return state` at line ~1394: if `state.ownership_contradictions` is non-empty, raise one
   aggregated error naming every offending WP ID (join the list into the error message/exit).
5. Update every existing caller of `_apply_ownership_inference` (both production and test code
   outside your owned test files, if any exist — check with a repo-wide grep) for the new
   3-tuple unpacking. **Do not modify test files outside your `owned_files` list** — if such a
   caller exists in a file you don't own, flag it in your validation notes rather than silently
   editing outside scope; coordinate via the review loop instead.
6. Verify this raise fires strictly before `_flush_frontmatter_writes` (`:2752`) and
   `_run_commit_pipeline` (`:2789`) — it should, since `_run_bootstrap_loop` completes before
   either is reached in `finalize_tasks`'s flow, but confirm by reading the call sequence rather
   than assuming.

**Files**: `src/specify_cli/cli/commands/agent/mission_finalize.py` (the `_BootstrapState`
dataclass, `_apply_ownership_inference`'s return statements, `_run_bootstrap_loop`'s loop body
and post-loop block — a moderate, scoped diff).
**Validation**: T009, T010, T011's tests pass.

### Subtask T016: Implement FR-003 and FR-004; run post-change validation

**Purpose**: The production-code fixes for FR-003 and FR-004, plus the mandatory post-change
complexity re-check and the authoritative SC-005 CLI-surface verification.

**Steps**:
1. **FR-003**: replace the `return None, None` at line ~1834-1835 (inside the `if not
   (wp_manifests and wp_dependencies):` guard) with a raise that names which half tripped —
   distinguish "empty `wp_manifests`" from "non-empty `wp_manifests` but empty
   `wp_dependencies`" in the message, per Acceptance Scenario 5's explicit requirement that both
   halves be distinguishable, not just detected.
2. Add the two inline "unreachable... kept as defensive code" comments at
   `_scaffold_acceptance_matrix_if_lane_based`'s `if lanes_manifest is None or validate_only:
   return` (`:1951`) and `_collect_finalize_artifacts`'s `if lanes_path is not None:
   candidates.append(lanes_path)` (`:270`) — per PLAN-ARCH-002's adopted resolution (plan.md
   §1). **Do not narrow the return-type annotation** — that stays
   `tuple[Path | None, LanesManifest | None]`.
3. **FR-004**: remove or narrow the `if not wp_manifests: return` short-circuit at
   `_validate_ownership_manifests` line ~1484-1485 so the `authoritative_surface`
   glob-match/overlap/audit-coverage checks run unconditionally.
4. **Post-change complexity re-check (mandatory, plan.md §10)**: run
   `ruff check --select C901 --config "lint.mccabe.max-complexity=1"` against
   `_run_bootstrap_loop` specifically. If it measures at or above 15, extract a small helper
   (e.g. a `_process_bootstrap_wp_file` helper for the per-WP loop body, or a
   `_raise_ownership_contradictions_if_any` post-loop helper) — do not defer this to a future
   mission.
5. **Authoritative SC-005 verification (mandatory, this WP's responsibility per plan.md §4)**:
   promote the `registered_commands`/`registered_groups` walk already used by
   `tests/architectural/test_docs_cli_reference_parity.py` (`_build_live_app()` +
   `scripts.docs._typer_walker.walk(app)`) to verify zero new CLI commands/subcommands/flags.
   Either invoke `walk()` directly in a small script comparing the merge-base checkout's
   command-path set against this branch's, or add a temporary assertion comparing
   `len(walk(app))` / the full path set before and after. Do NOT rely solely on the git-diff
   grep (plan.md's secondary, known-incomplete fast pass) as your SC-005 evidence — run the walk
   and report its result in your validation notes.

**Files**: `src/specify_cli/cli/commands/agent/mission_finalize.py` (the
`_compute_and_write_lanes` raise + two inline comments, the `_validate_ownership_manifests`
short-circuit removal, and possibly a small extracted helper if the complexity re-check
requires it — a small-to-moderate diff on its own; potentially expanding to a moderate diff if
step 4's mandatory complexity re-check forces the helper extraction).
**Validation**: T012, T013, T014's tests pass; complexity re-check result recorded; SC-005 walk
result recorded (must show zero new command paths).

### Subtask T017: Final validation pass

**Purpose**: Confirm the WP is done — tests green, no regressions, no scope drift, C-005
classification honest.

**Steps**:
1. Run the full targeted test surface:
   `.venv/bin/python -m pytest tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py tests/tasks/test_finalize_tasks_json_output_unit.py -q`
   and confirm all pass (except any pre-existing red from T008, unchanged).
2. Run the supporting regression check:
   `.venv/bin/python -m pytest tests/specify_cli/cli/commands/test_finalize_tasks_explicit_empty_owned_files.py -q`
   and confirm FR-002's change does not regress the `_owned_files_yaml_is_explicit_empty_list`
   detection helper's existing 6 tests (this file is read-only for this WP — do not modify it
   unless a genuine regression forces a fix, in which case flag it explicitly).
3. Re-run the C-005 classification from T008 post-implementation.
4. Self-check `ruff check` and `mypy --strict` cleanliness on
   `src/specify_cli/cli/commands/agent/mission_finalize.py` locally.
5. Confirm T016's SC-005 walk result and complexity re-check are both recorded.
6. Re-check PR #3666's live state (`gh pr view 3666 --json files,state`) one more time before
   calling this WP done, to catch any drift from when T008 first checked it.
7. Record a one-paragraph validation summary covering all of the above.

**Files**: none (validation only).
**Validation**: all of the above pass or are explained.

## Definition of Done

- `_apply_ownership_inference` returns `tuple[bool, list[str], str | None]`; the third element
  is a contradiction descriptor only for `code_change` + explicit-empty `owned_files`, `None`
  otherwise; it never raises.
- `_run_bootstrap_loop` accumulates contradictions in `state.ownership_contradictions` and
  raises one aggregated error after the full loop, before `return state`, naming every offending
  WP ID — strictly before `_flush_frontmatter_writes`/`_run_commit_pipeline`.
- `_compute_and_write_lanes` raises (naming which half of the compound guard tripped) instead of
  returning `(None, None)`; the two now-unreachable downstream guards carry inline "kept as
  defensive code" comments; the return-type annotation is unchanged.
- `_validate_ownership_manifests` runs its `authoritative_surface` checks unconditionally,
  regardless of whether `wp_manifests` is empty.
- All ten subtasks' red-first tests pass post-implementation; the supporting regression check
  (`test_finalize_tasks_explicit_empty_owned_files.py`) is unregressed.
- Post-change `_run_bootstrap_loop` complexity is confirmed under 15 (extracted a helper if not).
- The `registered_commands`/`registered_groups` walk confirms zero new CLI command paths.
- No new CLI command, subcommand, or flag introduced anywhere.
- C-005 baseline-red classification recorded for every test in this WP's target files.
- Each subtask's completion is recorded via
  `spec-kitty agent tasks mark-status <Txxx> --status done` (event-sourced; not a checkbox).

## Risks

- **PR #3666 rebase collision**: both PRs touch `_run_bootstrap_loop`. If #3666 merges first,
  your line-number references will shift — re-check the actual diff context at that point, not
  just the line numbers cited above. If you rebase onto #3666, re-verify your instrumentation
  point is still anchored strictly after `_apply_ownership_inference(...)`'s call, not inside
  #3666's `_apply_bootstrap_fields(...)` block.
- **`_run_bootstrap_loop` complexity margin**: it measures 11/15 today and this WP's change adds
  branches — do not skip the mandatory post-change re-check (T016).
- **Test-file-ownership boundary**: if `_apply_ownership_inference`'s signature change breaks a
  caller in a test file outside this WP's `owned_files`, do not silently edit outside scope —
  flag it.
- **Residual NFR-004 gap (FR-003/FR-004)**: do not let a red-first test over-assert a guarantee
  this mission does not provide (frontmatter/event-log absence on FR-003/FR-004 reject) — this
  is a documented, operator-accepted limitation (ledger SK-71), not something to "fix" here.

## Reviewer Guidance

Focus on: (1) `_apply_ownership_inference` never raises directly, only returns the descriptor;
(2) the aggregated raise in `_run_bootstrap_loop` fires exactly once, after the full loop, naming
every offender, not just the first; (3) the diff to `_run_bootstrap_loop` touches only its body,
never its signature or the `_apply_bootstrap_fields(...)` call block (PR #3666's territory); (4)
`_compute_and_write_lanes`'s return-type annotation is unchanged, both downstream guards carry
their inline comments; (5) `_validate_ownership_manifests`'s short-circuit is genuinely removed,
not merely narrowed to a different-but-still-skippable condition; (6) the SC-005 walk result is
present and shows zero new command paths — do not accept the grep alone as sufficient evidence;
(7) the residual NFR-004 gap test does not overclaim; (8) C-005 classification is honestly
reported.

Implementation command: `spec-kitty agent action implement WP02 --agent claude`
