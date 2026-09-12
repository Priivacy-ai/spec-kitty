---
work_package_id: WP03
title: Profile-skip diagnostics wired into pack validate (FR-002)
dependencies:
- WP02
requirement_refs:
- FR-002
- C-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: 30b8b506204c08c73e23edd98cdd229432bf4eda
base_commit: 30b8b506204c08c73e23edd98cdd229432bf4eda
created_at: '2026-08-14T01:14:22.174129+00:00'
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
history: []
authoritative_surface: src/specify_cli/doctrine/pack_validator.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/doctrine/pack_validator.py
- tests/specify_cli/doctrine/test_pack_validator.py
- tests/doctrine/test_agent_profile_model_field.py
tags: []
tracker_refs: []
---

## Objective

Wire `AgentProfileRepository.skipped_profiles()`'s existing post-merge skip diagnostics
directly into `pack validate`'s own output, so an author who fixes every schema error still
learns about a profile that silently fails to field-merge — without a separate, undocumented
`spec-kitty doctor doctrine --json` invocation.

## Context

**The residual gap this WP closes**: per Clarification 2 in `spec.md`, the acute case (a
misfielded profile with an undeclared key) is already closed —
`AgentProfile.model_config = ConfigDict(extra="forbid", ...)` makes `pack_validator.py`'s
existing generic per-file schema scan reject it as `schema_invalid`. The gap that remains:
`pack_validator.py` validates each profile YAML file *in isolation*, never through the real
load path `AgentProfileRepository` uses at runtime — which additionally field-merges an
org/project profile onto a same-ID built-in profile and can fail **post-merge** in ways a
single-file schema check cannot see. That failure is already recorded today via
`AgentProfileRepository._record_skip()`
(`src/doctrine/agent_profiles/repository.py:293-309`) into `skipped_profiles()` (`:311-320`),
but the only surface that exposes it is `spec-kitty doctor doctrine --json` — nothing in the
authoring guide or the `pack validate` / `pack assemble` / `doctrine fetch` loop tells an
author to run it.

**This is additive wiring, not a new validation engine** (AC-4): reuse
`AgentProfileRepository.skipped_profiles()` directly. Do not hand-roll a second
skip-detection heuristic.

**Chokepoint note for reviewers**: this WP and WP02 both list `pack_validator.py` and
`test_pack_validator.py` in `owned_files` — intentional, see WP02's Context section and
`plan.md`'s "Chokepoint" section. This WP depends on WP02 (`dependencies: [WP02]`) precisely
because both land in the same file within one lane, sequenced to avoid a same-file merge
collision — there is no logical/data dependency between FR-003 and FR-002 beyond the
same-file chokepoint.

**Do not repeat WP02's baseline capture.** WP02's Subtask T003 already captured Lane B's
one-time local baseline over all four C-004-targeted files. This WP inherits that baseline;
your own validation is scoped to running `tests/specify_cli/doctrine/test_pack_validator.py`
and `tests/doctrine/test_agent_profile_model_field.py` (this WP's two targeted files) and
confirming no test that was green in WP02's baseline is now red for a reason other than this
WP's own new (red-by-design-until-implemented) test.

### Design decisions already made in `plan.md` (IC-03) — do not re-derive

- **New helper**: `_check_profile_skipped_diagnostics(pack_dir, already_flagged_files)` in
  `pack_validator.py`, constructing `AgentProfileRepository(org_dirs=[pack_dir /
  "agent_profiles"])` — treating the pack under validation as the sole org source, per the
  spec's requirement text — and calling `.skipped_profiles()`. Emits one
  `ValidationIssue(category="profile_skipped", severity="error", artifact_type="agent_profiles",
  artifact_id=<profile id when resolvable>, file=<skip.path>, message=<skip.error_summary>)`
  per skip **not already covered** by a `schema_invalid` error for the same file.
- **Severity is always `"error"`**, matching `schema_invalid`'s severity for the equivalent
  "profile unusable" outcome — `SkippedProfile` carries no severity field of its own; this is
  a plan-phase design decision (`plan.md` IC-03 Risks, "Severity choice"), not something to
  re-derive. Do not make it advisory.
- **Dedup mechanism**: build the "already flagged" set from
  `{issue.file for issue in errors if issue.artifact_type == "agent_profiles"}` immediately
  after the existing registry-scan loop, before calling the new helper. Both the generic
  scan's file paths (from `type_dir.glob(glob)`, rooted at `pack_dir / "agent_profiles"`) and
  the repository's own scan paths (from `org_dir.glob(...)`, rooted at the same directory) are
  unresolved `Path` objects built from the identical directory instance, so string equality
  should hold — but treat AC-2's regression test as the actual proof, not this assumption
  alone.
- **Call-site position**: one new call inside `validate_pack()`, positioned immediately after
  the main registry scan loop (i.e., after the `for plural, (glob, schema_cls) in
  registry.items(): ...` loop at `src/specify_cli/doctrine/pack_validator.py:372-385`, before
  the DRG validation block that follows it).
- **Absent-directory safety is already guaranteed** by `AgentProfileRepository`'s own
  `_load_layer` guard (`src/doctrine/agent_profiles/repository.py:392`:
  `if not directory.exists(): return loaded`) — constructing
  `AgentProfileRepository(org_dirs=[pack_dir / "agent_profiles"])` is already safe when that
  directory doesn't exist. **Do not add a defensive `if type_dir.is_dir()` guard before
  constructing the repository** (unlike FR-003's asset case in WP02) — the repository handles
  it internally. AC-5's regression test must prove this path actually executes, not merely
  that nothing crashes: the helper must not wrap construction in a swallow-everything
  `try/except` that would make that assertion vacuous.

### Subtask T008: Model-layer fixture — prove the AC-1 profile is valid standalone

**Purpose**: Per C-004's own annotation ("model-layer fixtures only, no new runtime code
there"), add a test to `tests/doctrine/test_agent_profile_model_field.py` proving the
synthetic profile content this WP's AC-1 fixture uses is schema-valid **standalone** — i.e.
`AgentProfile.model_validate(...)` succeeds on it in isolation, matching what
`pack_validator.py`'s existing generic per-file schema scan already checks. This is fixture
data only; it adds no runtime code to `tests/doctrine/`.

**The verified fixture** (confirmed empirically against this checkout before this WP was
written — do not substitute a different mechanism without re-verifying it the same way):
an org-layer agent-profile YAML using the **deprecated scalar `role:` field** (not the
canonical `roles:` list) sharing a `profile-id` with a real, shipped built-in profile, e.g.
`analyst-annie` (`packs/built-in/agent_profiles/analyst-annie.agent.yaml`, which already
declares `roles: [analyst, requirements-engineer]`). Concretely:

```yaml
profile-id: analyst-annie
role: implementer
name: Override
purpose: test purpose
specialization:
  primary-focus: test focus
```

Standing alone, `AgentProfile.model_validate(...)` on this dict **succeeds**: the model's
`_coerce_scalar_role` `@model_validator(mode="before")` (`src/doctrine/agent_profiles/profile.py:300-332`)
sees `role` present and `roles` absent, coerces `role: implementer` into `roles: [implementer]`
(emitting a `DeprecationWarning`, not an error), and validation passes. This is exactly what
`pack_validator.py`'s existing per-file schema scan would see — **no `schema_invalid` error is
produced for this file today**, which is the load-bearing premise of AC-1 ("a profile that
individually passes `AgentProfile.model_validate` in isolation").

**Steps**:
1. In `tests/doctrine/test_agent_profile_model_field.py`, add a test (in the existing
   `TestAgentProfileModelEffortField` class or a small new class following the file's existing
   style) asserting the deprecated-scalar-`role` dict above validates successfully via
   `AgentProfile.model_validate(...)` (or `AgentProfile(**data)`), producing `roles ==
   ["implementer"]`. Suppress/assert the expected `DeprecationWarning` per `pytest`'s standard
   `pytest.warns(DeprecationWarning)` context manager rather than letting it leak as noise.
2. This test is a **fixture-proof**, not part of the ATDD red/green pair (T009 owns that) — it
   documents and pins the standalone-valid half of the AC-1 scenario so a future reader does
   not have to re-derive why the merge-only failure in T009's pack-level test is legitimate.

**Files**: `tests/doctrine/test_agent_profile_model_field.py` (one new test function, ~10-15
lines).

**Validation**: the new test passes on the current checkout (it is not part of the red/green
pair — it is true both before and after this WP's implementation lands, since it tests the
domain model directly, not `pack_validator.py`).

### Subtask T009: ATDD red-first — AC-1's profile-skip regression test

**Purpose**: Commit the failing-first pack-level test that proves `pack validate` today has no
signal for a post-merge profile skip, before any implementation lands.

**Steps**:
1. In `tests/specify_cli/doctrine/test_pack_validator.py`, add a new test (a new small test
   class, e.g. `TestProfileSkippedDiagnostics`, following the file's existing per-concern
   class organization such as `TestAssetManifestValidation`) that:
   - Writes `agent_profiles/analyst-annie.agent.yaml` under `tmp_path` (the pack root) with
     exactly T008's fixture content (the deprecated `role: implementer` scalar, `profile-id:
     analyst-annie` — the same id as the real shipped built-in profile).
   - Calls `validate_pack(tmp_path)`.
   - Asserts the result includes a `ValidationIssue` with `category == "profile_skipped"` in
     `result.errors` (severity `"error"`), whose `file` names the written
     `agent_profiles/analyst-annie.agent.yaml` path, whose `artifact_id` is `"analyst-annie"`
     (the profile id — resolvable here since `SkippedProfile.profile_id` is populated for this
     failure mode), and whose `message` carries the recorded `error_summary` (the
     `role`/`roles` conflict message from `_coerce_scalar_role`).
   - This exercises the **real, shipped built-in `analyst-annie` profile** as the merge target
     — do not fabricate a fake built-in directory for this test; `AgentProfileRepository`'s
     default `built_in_dir` (via `_default_built_in_dir()`) already resolves to
     `packs/built-in/agent_profiles/`, which is what the new helper (T010) will use by
     constructing `AgentProfileRepository(org_dirs=[pack_dir / "agent_profiles"])` with no
     `built_in_dir` override.
2. **Primary RED check (C-011)** — run this new test id **in isolation** against Lane B's
   `planning_base_branch` (`main`'s tip at planning time, `meta.json`'s `target_branch:
   "main"`). Because this WP is **not** Lane B's first WP (WP02 landed before it), do this as
   a **separate ref/worktree checkout**, not merely "the tree immediately before this WP's
   implementation commit" — see this WP's Reviewer Guidance for the exact procedure and why
   the distinction matters here. Confirm RED: `pack_validator.py` at `planning_base_branch`
   does not call `AgentProfileRepository` or `skipped_profiles()` at all, so the assertion
   fails.
3. **Secondary check (attribution only, not a substitute)**: the same test id also fails at
   Lane B's running tip immediately after WP02's implementation commit landed, for the
   identical reason — useful for confirming WP03's own implementation commit (T010), not
   WP02's, is what turns it green, but this check alone does **not** satisfy C-011.
4. Commit this test addition as its own commit, separate from T010's implementation commit.

**Files**: `tests/specify_cli/doctrine/test_pack_validator.py` (new test class/function, ~25-35
lines).

**Validation**: the new test id fails both at `planning_base_branch` (primary check) and at
Lane B's tip immediately before T010 (secondary check), for the reasons above.

### Subtask T010: Implementation — `_check_profile_skipped_diagnostics` + call site

**Purpose**: Turn T009's red test green with the smallest, most direct diff matching the
design already fixed in `plan.md` IC-03.

**Steps**:
1. In `src/specify_cli/doctrine/pack_validator.py`, add a new helper function (place it near
   `_validate_asset_manifests`, following the same extract-a-helper discipline the file
   already uses):
   ```python
   def _check_profile_skipped_diagnostics(
       pack_dir: Path,
       already_flagged_files: set[str],
   ) -> list[ValidationIssue]:
       """Surface AgentProfileRepository's post-merge skip diagnostics.

       Reuses AgentProfileRepository.skipped_profiles() directly (AC-4) rather
       than a second skip-detection heuristic. Deduplicated against files
       already flagged schema_invalid by the generic per-file scan, so one
       root cause is not reported twice under two unrelated-looking
       categories.
       """
       from doctrine.agent_profiles.repository import AgentProfileRepository

       repo = AgentProfileRepository(org_dirs=[pack_dir / "agent_profiles"])
       issues: list[ValidationIssue] = []
       for skip in repo.skipped_profiles():
           if skip.path in already_flagged_files:
               continue
           issues.append(
               ValidationIssue(
                   severity="error",
                   artifact_type="agent_profiles",
                   artifact_id=skip.profile_id,
                   file=skip.path,
                   message=skip.error_summary,
                   category="profile_skipped",
               )
           )
       return issues
   ```
   (Adjust field/attribute names to match `SkippedProfile`'s actual shape at
   `src/doctrine/agent_profiles/diagnostics.py:22-37` — `layer`, `path`, `profile_id`,
   `error_summary` — verify against the live source before finalizing, do not assume this
   sketch is byte-exact.)
2. Wire it into `validate_pack()` immediately after the registry-scan loop
   (`src/specify_cli/doctrine/pack_validator.py:372-385`), before the `# DRG validation` block:
   ```python
   already_flagged_files = {
       issue.file for issue in errors if issue.artifact_type == "agent_profiles"
   }
   errors.extend(
       _check_profile_skipped_diagnostics(pack_dir, already_flagged_files)
   )
   ```
3. Confirm the lazy, function-local import pattern
   (`from doctrine.agent_profiles.repository import AgentProfileRepository` inside the helper,
   not at module scope) matches this file's existing precedent (`_artifact_schema_registry()`
   already imports its models lazily, inside the function body) — this also keeps
   `scripts/check_patch_targets.py`'s static analysis correct: any test that needs to
   substitute the repository must patch
   `"doctrine.agent_profiles.repository.AgentProfileRepository"` (the source location), never
   a nonexistent `"specify_cli.doctrine.pack_validator.AgentProfileRepository"` alias.
4. Re-run T009's test id — it should now pass (GREEN).
5. **AC-4 call-assertion (spec-mandated, not satisfiable by inspection)**: `spec.md` FR-002
   AC-4 requires this be "verified by test asserting the same function is called or the same
   dataclass shape is surfaced" — T009's end-to-end test is reasonable indirect evidence but
   does not assert the call itself. Add a small test to
   `tests/specify_cli/doctrine/test_pack_validator.py`, mirroring WP04's T016/T017(a)
   parameter-value-assertion technique, that patches
   `"doctrine.agent_profiles.repository.AgentProfileRepository.skipped_profiles"` (the source
   location the helper's lazy import binds to — see step 3 above) with a `MagicMock`, then
   calls `_check_profile_skipped_diagnostics(pack_dir, set())` directly (or
   `validate_pack(...)` against a minimal pack with an `agent_profiles/` directory) and asserts
   the mock was actually invoked. This proves the helper calls the real repository method
   rather than a hand-rolled heuristic, non-vacuously (the assertion fails if the call is
   removed or replaced with an inline reimplementation).
6. Update `ValidationIssue`'s class docstring (`src/specify_cli/doctrine/pack_validator.py:95-114`,
   the "Valid values" bullet list) to add a `` * ``profile_skipped`` — ...`` bullet documenting
   the new category, matching the existing bullets' format (backtick-quoted category name, em
   dash, one-line description) — e.g. placed alongside the other per-issue categories such as
   `asset_mime_invalid`. This docstring is the authoritative enumeration of valid `category`
   values; leaving it unupdated would make it silently disagree with the helper added in step 1.
7. Commit as its own commit, separate from T009's test commit.

**Files**: `src/specify_cli/doctrine/pack_validator.py` (one new ~20-line helper, one ~6-line
call site addition, and the `ValidationIssue` docstring's "Valid values" list updated with
`profile_skipped`); `tests/specify_cli/doctrine/test_pack_validator.py` (one additional small
test for step 5's call-assertion, ~10-15 lines).

**Validation**: T009's test id passes; step 5's call-assertion test passes and is non-vacuous.
`mypy --strict` and `ruff check` pass with zero new suppressions on the touched
`pack_validator.py`.

### Subtask T011: AC-2 — no double-report for the already-fixed acute case

**Purpose**: Prove the dedup logic actually works — a profile file with an undeclared key
(the schema-forbidden-extra case, already caught by the generic scan as `schema_invalid`)
must still produce exactly one diagnostic, not two.

**Steps**:
1. Add a test writing `agent_profiles/some-profile.agent.yaml` with an undeclared top-level
   key (triggering `extra="forbid"` — matches the pattern any existing schema-rejection test
   in this file already uses for other artifact kinds).
2. Call `validate_pack(tmp_path)` and assert exactly one issue exists for that file (filter
   `result.errors` by `file` matching the written path) — `category == "schema_invalid"`, and
   assert **no** `profile_skipped` issue exists for the same file. This is the load-bearing
   proof that `already_flagged_files` correctly suppresses the redundant report: since
   `AgentProfileRepository`'s own load of this same file would *also* fail schema validation
   (the extra key is forbidden at the pydantic level regardless of load path) and would
   therefore also appear in `skipped_profiles()`, the dedup must actually filter it out.

**Files**: `tests/specify_cli/doctrine/test_pack_validator.py` (one new test, ~15-20 lines).

**Validation**: the test passes; exactly one issue for the file, category `schema_invalid`,
no `profile_skipped` duplicate.

### Subtask T012: AC-3 — no false positive on a clean pack

**Purpose**: Confirm a pack with no profile problems produces no `profile_skipped` issue and
`ok` is unaffected.

**Steps**:
1. Add a test writing one or more valid `agent_profiles/*.agent.yaml` files (schema-valid,
   using a fresh `profile-id` that does not collide with any built-in profile, so no merge is
   even attempted) and asserting `validate_pack(tmp_path).ok is True` with no `profile_skipped`
   issue in either `errors` or `advisories`.

**Files**: `tests/specify_cli/doctrine/test_pack_validator.py` (one new test, ~10-15 lines).

**Validation**: the test passes; no regression to any currently-passing pack shape.

### Subtask T013: AC-5 — absent `agent_profiles/` directory is safe and provably exercised

**Purpose**: Prove the new check does not raise when `agent_profiles/` is entirely absent, and
that this is proven by actually exercising the check path — not merely by the absence of a
crash.

**Steps**:
1. Add a test constructing a pack with **no** `agent_profiles/` directory at all (e.g. only a
   `directives/` directory, or a genuinely empty pack) and asserting `validate_pack(tmp_path)`
   does not raise, and that no `profile_skipped` issue is present.
2. Per the spec's Edge Cases bullet 2 and AC-5's own text, this must prove the check path
   **actually executed** — e.g. by asserting the helper's return value is an empty list when
   called directly with a pack dir lacking `agent_profiles/`
   (`_check_profile_skipped_diagnostics(pack_dir_without_agent_profiles, set())  == []`), in
   addition to the end-to-end `validate_pack()` assertion — not solely "nothing crashed."
   Import the helper directly for this direct-call assertion (it is a module-level function in
   `pack_validator.py`, callable from the test file).

**Files**: `tests/specify_cli/doctrine/test_pack_validator.py` (one new test, ~15-20 lines).

**Validation**: the test passes; the direct-call assertion proves the absent-directory path
was actually exercised (not swallowed by a broad `try/except`), matching the "must not attempt
to instantiate `AgentProfileRepository` in a way that raises" requirement — verified because
it *doesn't need to*, since `_load_layer`'s own guard already handles this.

## Definition of Done

- [ ] T008's model-layer fixture proof passes, showing the AC-1 fixture profile is
      standalone-valid.
- [ ] T009's AC-1 regression test committed first, verified RED against `planning_base_branch`
      as a **separate ref/worktree checkout** (not merely the intra-lane tip — see Reviewer
      Guidance), as its own commit.
- [ ] T010's helper + call site committed second, as its own commit; T009's test now GREEN.
- [ ] `ValidationIssue`'s class docstring "Valid values" list (`pack_validator.py:95-114`) has a
      new `profile_skipped` bullet, added by T010 step 6, matching the existing bullets' format.
- [ ] AC-2 (dedup, no double-report), AC-3 (no false positive), AC-5 (absent directory, proven
      exercised) all covered by tests.
- [ ] AC-4 (reuse `AgentProfileRepository`/`skipped_profiles()` directly, no second heuristic)
      is proven by T010 step 5's `unittest.mock.patch`-based call-assertion test — not "true by
      construction" — confirming the helper actually invokes `.skipped_profiles()` on the
      constructed repository and does not reimplement any part of the skip-detection logic.
- [ ] `uv run pytest tests/specify_cli/doctrine/test_pack_validator.py tests/doctrine/test_agent_profile_model_field.py -q`
      is fully green.
- [ ] No file outside `owned_files` is touched.
- [ ] Severity for every `profile_skipped` issue is `"error"`.
- [ ] `ValidationResult.to_dict()`'s top-level shape remains exactly `{ok, errors, advisories}`
      — no new top-level JSON key was introduced.
- [ ] `ruff check src/specify_cli/doctrine/pack_validator.py` and
      `mypy --strict src/specify_cli/doctrine/pack_validator.py` (or the project's standard
      invocation) pass with zero new suppressions.

## Risks

- **Dedup correctness** (per `plan.md` IC-03 Risks): relies on path-string equality between
  the generic scan's paths and the repository's own scan paths. T011's test is the actual
  proof this holds — do not treat the equality as self-evident without that test passing.
- **Fixture fragility**: T008/T009's fixture depends on `analyst-annie` remaining a real
  shipped built-in profile with `roles:` declared and no `role:`/`roles:` conflict of its own.
  If a future, unrelated change to `packs/built-in/agent_profiles/analyst-annie.agent.yaml`
  removes or renames it, re-verify the fixture against whichever built-in profile is current,
  or pick a different built-in profile id — the underlying mechanism (deprecated `role:`
  scalar colliding with a same-id built-in's already-resolved `roles:` list) is what matters,
  not the specific chosen id.
- **Chokepoint continuation**: WP04 lands immediately after this WP in the same file — keep
  this WP's `pack_validator.py` diff to exactly the one new helper and its one call site, in
  the position specified above, to minimize friction for WP04's own addition.

## Reviewer Guidance

- **This WP is NOT first in Lane B** (WP02 precedes it). Per `plan.md`'s "Per-FR ATDD
  Sequencing" section's "Practical consequence for Lane B's sequencing": verifying T009's test
  RED against `planning_base_branch` requires checking out `planning_base_branch` (`main`)
  itself **as a separate ref or worktree**, applying **only T009's new test id(s)** on top of
  it (not the whole `test_pack_validator.py` file — by the time this WP's test commit lands,
  the file already carries WP02's own new test function(s) too, which would *also* show red
  against `planning_base_branch` for an unrelated reason and would muddy the signal), and
  running that specific test id there. **Do not substitute "the tree immediately before this
  WP's implementation commit" (Lane B's running tip) for this check** — that is a secondary,
  attribution-only aid (see T009 step 3), never a replacement for the `planning_base_branch`
  check. This is a real, easy-to-get-wrong operational detail specific to this WP's position
  in the lane, not boilerplate — an earlier draft of this mission's plan made exactly this
  substitution error and had to be corrected (`plan.md`, "Per-FR ATDD Sequencing," citing
  finding PLAN-V4-001).
- **Concrete mechanics for the separate ref/worktree check** — the paragraph above names the
  requirement; here is a runnable procedure for it:
  ```bash
  # Idempotent cleanup first, in case a prior run of this procedure left the worktree
  # registered (e.g. an earlier `git apply` or `pytest` step failed before reaching the
  # closing `git worktree remove` below):
  git worktree remove --force /tmp/pbb-check 2>/dev/null || true
  git worktree add /tmp/pbb-check main   # planning_base_branch is "main" per meta.json
  # Isolate only T009's new test function — do not apply the whole test-file diff, which
  # would also carry WP02's own new tests and muddy the RED signal. Either:
  #   (a) extract just the new test function's hunk from its own commit and apply it:
  git show <T009-test-commit-sha> -- tests/specify_cli/doctrine/test_pack_validator.py \
    | git -C /tmp/pbb-check apply
  #   (b) or, if the hunk doesn't apply cleanly (e.g. WP02's own test additions in the same
  #       file shift context lines), manually copy just T009's new test function's body into
  #       /tmp/pbb-check's copy of the file.
  cd /tmp/pbb-check && uv run pytest tests/specify_cli/doctrine/test_pack_validator.py \
    -k <T009's_new_test_id> -q   # confirm RED
  cd - && git worktree remove /tmp/pbb-check
  ```
- Confirm T009's test commit precedes T010's implementation commit.
- Confirm T008's fixture-proof test is present and passing — it documents why the AC-1
  scenario's premise ("passes schema validation individually") holds for the specific fixture
  chosen.
- Confirm severity is `"error"` for every `profile_skipped` issue (not advisory) — this is a
  plan-phase design decision, not optional.
- Confirm no new top-level JSON key was introduced to `ValidationResult.to_dict()` — the
  `profile_skipped` category rides the existing `errors`/`advisories` arrays.
- Do not flag the `pack_validator.py` / `test_pack_validator.py` ownership overlap with WP02
  as a violation — see this WP's Context section.
- Run only `tests/specify_cli/doctrine/test_pack_validator.py` and
  `tests/doctrine/test_agent_profile_model_field.py` for this WP's own gate (C-004) — never
  the full suite, and do not re-run WP02's four-file baseline capture (already done).

---

`spec-kitty agent action implement WP03 --agent <name>`
