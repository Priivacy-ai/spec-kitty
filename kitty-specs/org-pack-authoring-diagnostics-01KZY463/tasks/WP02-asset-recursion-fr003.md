---
work_package_id: WP02
title: Asset directory recursion widening (FR-003)
dependencies: []
requirement_refs:
- FR-003
- C-004
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T003
- T004
- T005
- T006
- T007
history: []
authoritative_surface: src/specify_cli/doctrine/pack_validator.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/doctrine/pack_validator.py
- tests/specify_cli/doctrine/test_pack_validator.py
tags: []
---

## Objective

Widen `pack_validator.py`'s `_scan_files()` so it recurses into `assets/` the same way it
already recurses into `styleguides/`, matching `AssetRepository._project_scan`'s existing
`rglob` behavior — closing the gap where a nested `assets/<pack>/x.asset.yaml` manifest loads
at runtime but is invisible to `pack validate`.

## Context

**Why this WP exists**: `AssetRepository._project_scan`
(`src/doctrine/assets/repository.py:130-132`) deliberately `rglob`s — its own docstring
(`:18-22`) names the reason: a non-recursive `glob` would never find an org-pack manifest at
`assets/<pack>/x.asset.yaml`. `pack_validator.py`'s `_scan_files`
(`src/specify_cli/doctrine/pack_validator.py:202-206`) recurses only when
`directory.name == "styleguides"` — every other kind, `"assets"` included, gets a
non-recursive `glob`. A nested asset sidecar therefore loads at runtime and is completely
invisible to validation: no schema check, no `asset_path_escape`/`asset_mime_invalid` check —
`pack validate` reports clean for content it never examined.

**This WP is Lane B's first WP** (per `plan.md`'s "Chokepoint" section: FR-002, FR-003, and
FR-004 all touch `pack_validator.py` and are sequenced into one lane — FR-003 → FR-002 →
FR-004, low-risk-to-high-risk — rather than three lanes that would collide on the same file).
Because this is Lane B's first WP, **you own two procedures no other Lane B WP repeats
identically**: (1) "The Baseline" — a one-time, mission-scoped pre-existing-red capture over
the four C-004-targeted files, run once here at Lane B's start, and (2) the Campsite check —
assessing whether `validate_pack()` needs a preparatory extraction before FR-003/FR-002/FR-004
pile new checks onto it. Both are detailed in their own subtasks below (T003, T004).

**Chokepoint note for reviewers**: this WP, WP03, and WP04 all list
`src/specify_cli/doctrine/pack_validator.py` in `owned_files`, and this WP and WP03 both list
`tests/specify_cli/doctrine/test_pack_validator.py`. This is **intentional same-file
ownership**, not an overlap violation — the three WPs form a dependency chain within Lane B
specifically because they cannot run concurrently on the same file (`plan.md`'s "Chokepoint"
section). Do not flag this as an ownership-map conflict; the charter's "ownership-map leeway"
standing order (Standing Order #8) applies — no-overlap in the WPs' actual *execution order*
is the real guard, not disjoint file lists.

**C-004 targeted test surface only**: run exactly
`tests/specify_cli/doctrine/test_pack_validator.py` for this WP's own validation — never
`pytest tests/` in full. The Baseline subtask (T003) additionally runs the other three
C-004-named files once, as a one-time cross-file capture — see T003 for the exact command.

### Subtask T003: The Baseline — capture Lane B's local pre-existing-red set

**Purpose**: Establish, before any functional change lands in Lane B, which of the four
C-004-targeted files' tests are already red/erroring on `main` (the mission's
`planning_base_branch`, per `meta.json`'s `target_branch: "main"`) so that later red is
correctly attributed to the WP that introduced it, not misattributed to this mission as a
whole. This procedure runs **once**, here, because WP02 is Lane B's first WP — per plan.md's
"The Baseline" section, WP03 and WP04 do not repeat this cross-file capture; they instead
verify only their own new test id(s) against `planning_base_branch` (see their own WP files'
Reviewer Guidance).

**Steps**:
1. Before making any code edit in this WP, run the four C-004-targeted files together:
   ```bash
   uv run pytest tests/specify_cli/doctrine/test_pack_validator.py \
     tests/doctrine/test_agent_profile_model_field.py \
     tests/specify_cli/doctrine/test_pack_assembler.py \
     tests/cli/test_doctrine_org_commands.py -q
   ```
2. Record the full pass/fail/error output verbatim (paste it into your working notes or this
   WP's implementation commit message trailer) — this is the mission's **local baseline**,
   scoped to exactly these four files. It is distinct from and narrower than the repo-wide
   ~23-known-red/2-error figure cited in `plan.md`'s "The Baseline" section (issue #3284) —
   that figure is a fact about `main` as a whole, not this mission's scope.
3. Classify every failure/error in the captured output as **pre-existing** (not this
   mission's to fix, per C-003 "no fifth surface" — leave it red, do not attempt a fix).
4. This baseline is the reference point every later Lane B WP's "only a test green in step 1
   and red after the change is attributable to this mission" rule (`plan.md`, "The Baseline"
   step 3) measures against. Do not re-run this full four-file capture in WP03 or WP04 — they
   inherit this baseline and only need to verify their own new test id(s) in isolation against
   `planning_base_branch` (see each WP's Reviewer Guidance).

**Files**: none changed — this is a read-only capture step. Record the output as a note (e.g.
in your commit message or a scratch file outside `owned_files` — do not commit a new tracked
file for this).

**Validation**: the captured baseline accounts for every failing/erroring test in the
four-file run; nothing is silently dropped. If the repo-wide P0 issue #3284's ~23/2 figure and
your four-file subset disagree in a way that looks surprising, re-run once to rule out a flaky
collection error before treating it as a real baseline fact — do not spend more than one
re-run chasing it (per the charter's flakiness policy, never retry-to-green; this is a
one-time sanity check, not a retry loop).

### Subtask T004: Campsite check — assess `validate_pack()` against the complexity ceiling

**Purpose**: Per Charter Standing Order #2 (campsite cleaning) and `plan.md`'s
"Campsite-Clean Scope" section, decide — before FR-003's functional change lands — whether
`validate_pack()` (and `_scan_files()`/the DRG-validation region this mission is about to
extend) sits close enough to the ruff `C901`/Sonar `S3776` complexity-15 ceiling to warrant a
preparatory, behaviour-preserving extraction, in the same style as the existing
`_validate_drg`/`_validate_asset_manifests` split. This check is **conditional, not
automatic** — do not manufacture an extraction if none is warranted.

**Steps**:
1. Measure `validate_pack()`'s current cyclomatic complexity, e.g.:
   ```bash
   ruff check src/specify_cli/doctrine/pack_validator.py --select C901 --statistics
   ```
   or inspect the function directly (`validate_pack()` starts at
   `src/specify_cli/doctrine/pack_validator.py:340`) and count its branches/loops.
2. If `validate_pack()` is already at or very near 15, or if adding FR-003's one-clause
   `_scan_files` widening (a non-branching change to a helper function it calls, not to
   `validate_pack()` itself) would plausibly push a *later* WP's helper-call-site addition
   over the ceiling, do a preparatory mechanical extraction as its own **behaviour-preserving
   commit**, before FR-003's functional change: pull a self-contained region of
   `validate_pack()`'s body into a new small helper, mirroring the existing
   `_validate_drg(drg_dir, pack_artifact_urns)` / `_validate_asset_manifests(pack_dir,
   asset_manifests)` seam (both already extracted, both called once from `validate_pack()`).
   Add or extend a narrow test for the extracted helper's behaviour, and confirm the existing
   test suite for this file is unaffected (behaviour-preserving means no test's expected
   outcome changes).
3. If `validate_pack()` is comfortably under the ceiling and this WP's own change (a
   one-clause `_scan_files` widening, not a `validate_pack()` edit at all) does not move that
   needle, **state that explicitly in your implementation notes and move on** — do not extract
   preemptively. `plan.md`'s own "Complexity Tracking" section already anticipates this: "no
   Complexity Tracking entry needed" unless a genuine non-mechanical trade-off is required, and
   FR-003 itself is *not* a `validate_pack()`-body change at all (see T006) — it is extremely
   unlikely this WP is where an extraction becomes necessary, since WP03 and WP04 (not this
   WP) are the ones adding new call sites inside `validate_pack()`'s body.

**Files**: `src/specify_cli/doctrine/pack_validator.py` (only if an extraction is warranted —
otherwise no change from this subtask).

**Validation**: either (a) a preparatory extraction commit lands, behaviour-preserving, with
its own narrow test, and the existing test suite for this file is green before FR-003's own
change begins, or (b) your notes record that no extraction was warranted and why (e.g. "FR-003
touches only `_scan_files`, not `validate_pack()`'s body; complexity is unaffected").

### Subtask T005: ATDD red-first — AC-1's nested-asset regression test

**Purpose**: Per the charter's binding C-011 ATDD-First Discipline, commit a failing-first
test that pins the user-observable behaviour this WP delivers, **before** the implementation
commit that makes it pass.

**Steps**:
1. In `tests/specify_cli/doctrine/test_pack_validator.py`, inside `class TestValidatePack`
   (or add a focused nearby test — match the file's existing per-class organization), add a
   test that:
   - Writes an asset manifest one directory below `assets/`, e.g.
     `assets/acme-pack/logo.asset.yaml`, using the existing `_write_asset_manifest` helper
     (`tests/specify_cli/doctrine/test_pack_validator.py:61`) but writing directly under a
     nested subdirectory rather than the flat `pack_dir / "assets"` root the helper's default
     targets — either extend `_write_asset_manifest` with an optional nesting parameter, or
     write the nested file directly with `(tmp_path / "assets" / "acme-pack").mkdir(parents=True)`
     followed by the manifest content (mirror the YAML shape `_write_asset_manifest` already
     produces).
   - Gives the manifest a schema violation matching an existing, already-covered failure
     mode — e.g. an invalid `mime` value (mirror `test_path_escape_via_dotdot_rejected`'s or
     the mime-validation tests' fixture shape around `:647` onward) so the test asserts against
     the existing `asset_mime_invalid` or `schema_invalid` category, not a new one (FR-003
     introduces no new `ValidationIssue.category`).
   - Calls `validate_pack(tmp_path)` and asserts the violation IS reported against the nested
     file path (`result.ok is False`, and the matching issue's `file` string contains the
     nested path).
2. Run this one new test in isolation against Lane B's `planning_base_branch` (`main`'s tip at
   planning time — since WP02 is Lane B's first WP, `main` and Lane B's running tip coincide
   right now, so this is simply running the test on your current checkout before making the
   T006 implementation edit):
   ```bash
   uv run pytest tests/specify_cli/doctrine/test_pack_validator.py -k <new_test_name> -q
   ```
   Confirm it is **RED**: today's `_scan_files` never recurses into `assets/`
   (`directory.name == "styleguides"` is the only recursive case), so the nested manifest is
   never scanned and the assertion fails.
3. Commit this test addition as its **own commit**, separate from the T006 implementation
   commit that follows.

**Files**: `tests/specify_cli/doctrine/test_pack_validator.py` (new test function, ~20-30
lines, plus a nesting-capable fixture helper if you extend `_write_asset_manifest`).

**Validation**: the new test id fails when run alone against the pre-change checkout, with a
failure message showing the nested manifest was never scanned (e.g. `result.ok is True` when
the test expected `False`, or the expected issue is simply absent from `result.errors`).

### Subtask T006: Implementation — widen `_scan_files`'s recursion condition

**Purpose**: Turn T005's red test green with the smallest possible diff.

**Steps**:
1. In `src/specify_cli/doctrine/pack_validator.py`, locate `_scan_files`
   (`:202-206`):
   ```python
   def _scan_files(directory: Path, glob: str) -> list[Path]:
       """Return sorted files matching *glob*; recursive for styleguides."""
       if directory.name == "styleguides":
           return sorted(directory.rglob(glob))
       return sorted(directory.glob(glob))
   ```
2. Widen the condition to cover both kinds:
   ```python
   def _scan_files(directory: Path, glob: str) -> list[Path]:
       """Return sorted files matching *glob*; recursive for styleguides and assets."""
       if directory.name in {"styleguides", "assets"}:
           return sorted(directory.rglob(glob))
       return sorted(directory.glob(glob))
   ```
   Update the docstring's one-line summary to mention both kinds (as shown). This is the
   entire functional change for FR-003 — no other line in the file changes for this WP.
3. Re-run T005's test id — it should now pass (GREEN).
4. Commit this as its own commit, separate from T005's test commit.

**Files**: `src/specify_cli/doctrine/pack_validator.py` (one-clause condition widening plus a
docstring word, ~2 line delta).

**Validation**: T005's test id passes. No other test in the file regresses (see T007).

### Subtask T007: AC-2/AC-3/AC-4 coverage

**Purpose**: Close out FR-003's remaining acceptance criteria: a valid nested manifest passes
with no false positive (AC-2), existing top-level asset behavior is unchanged (AC-3), and an
absent `assets/` directory produces no error and is provably exercised, not merely
un-crashed (AC-4).

**Steps**:
1. **AC-2**: add (or extend T005's test class with) a test writing a *valid* nested
   `assets/acme-pack/logo.asset.yaml` (no schema violation) and asserting `validate_pack(...)`
   returns `ok is True` with no errors — the manifest participates in the existing
   containment/mime checks (`_validate_asset_manifests`) exactly as a top-level asset would.
2. **AC-3**: confirm the existing top-level asset test
   `test_multiple_assets_independent` (`tests/specify_cli/doctrine/test_pack_validator.py:715`)
   continues to pass **unmodified** — do not edit it. Run it explicitly:
   ```bash
   uv run pytest tests/specify_cli/doctrine/test_pack_validator.py -k test_multiple_assets_independent -q
   ```
3. **AC-4**: add a regression test that constructs a pack with **no** `assets/` directory at
   all and asserts `validate_pack(...)` does not raise and reports no asset-related error. The
   existing guard is `validate_pack()`'s registry loop:
   `if not type_dir.is_dir(): continue` — present before this WP and left alone. Per the
   spec's Edge Cases bullet 3, the test must prove this guard path **actually executed** for
   the absent-directory case, not merely that nothing crashed — e.g. assert the pack's overall
   `result.ok` matches what it would be with no `assets/` directory present at all (a
   comparison, or an explicit assertion that no issue has `artifact_type == "assets"`), rather
   than only asserting the call didn't raise.
4. Run the full targeted file once more:
   ```bash
   uv run pytest tests/specify_cli/doctrine/test_pack_validator.py -q
   ```
   Compare against T003's baseline — the only new red-to-green transition should be T005's
   test; nothing that was green in the baseline should now be red.

**Files**: `tests/specify_cli/doctrine/test_pack_validator.py` (2-3 additional small test
functions, ~15-25 lines each).

**Validation**: all three new/verified tests pass; `test_multiple_assets_independent` is
byte-for-byte unmodified and still passes; the full file's pass/fail set matches T003's
baseline plus exactly the tests this WP added.

## Definition of Done

- [ ] T003's baseline captured and recorded before any functional edit landed.
- [ ] T004's campsite check performed and its outcome (extraction or "not warranted, because
      ...") recorded.
- [ ] T005's AC-1 regression test committed first, verified RED against the pre-change
      checkout, as its own commit.
- [ ] T006's `_scan_files` widening committed second, as its own commit; T005's test now
      GREEN.
- [ ] AC-2 (valid nested manifest, no false positive), AC-3 (`test_multiple_assets_independent`
      unmodified and passing), AC-4 (absent `assets/` directory, guard-path-executed proof) all
      covered by tests.
- [ ] `uv run pytest tests/specify_cli/doctrine/test_pack_validator.py -q` is fully green,
      matching T003's baseline plus this WP's new tests.
- [ ] No file outside `owned_files` is touched.
- [ ] `ruff check src/specify_cli/doctrine/pack_validator.py` and
      `mypy --strict src/specify_cli/doctrine/pack_validator.py` (or the project's standard
      invocation) pass with zero new suppressions.

## Risks

- **Minimal functional risk** — the existing `if not type_dir.is_dir(): continue` guard in
  `validate_pack()`'s registry loop already handles an absent `assets/` directory (AC-4); this
  change does not touch that guard, only `_scan_files`'s internal glob choice.
- **Chokepoint risk, not a code risk**: WP03 and WP04 both edit `pack_validator.py` and (WP03
  also) `test_pack_validator.py` immediately after this WP lands. Keep this WP's diff to
  exactly the one-clause `_scan_files` widening plus its tests — do not incidentally touch
  code near where WP03/WP04 will add their own helpers, to minimize rebase friction for the
  next WP in the chain.
- **Baseline mis-scoping**: if T003's baseline capture is skipped or run after a code change
  has already landed, later red cannot be reliably attributed. Do T003 strictly first, before
  any edit.

## Reviewer Guidance

- **This WP is Lane B's first WP, so `planning_base_branch` and Lane B's running tip coincide
  for it** — verifying T005's test RED is simply confirming it fails on the checkout
  immediately before T006's implementation commit (no separate ref/worktree checkout needed,
  unlike WP03 and WP04, which must check out `planning_base_branch` as a distinct ref — see
  their own Reviewer Guidance sections for why).
- Confirm T005's test commit precedes T006's implementation commit, and that T005's test id
  is RED on the commit immediately before T006, GREEN on T006's own commit.
- Confirm T003's baseline was actually captured (check the implementation notes/commit
  trailer) before T004-T007's work began.
- Confirm T004's campsite-check outcome is recorded either way (extraction performed, or
  explicitly "not warranted, because...") — an implementer silently skipping this subtask is a
  finding.
- Confirm `test_multiple_assets_independent` is byte-for-byte unchanged in the diff (AC-3).
- Do not flag the `pack_validator.py` / `test_pack_validator.py` ownership overlap with WP03
  as a violation — see this WP's Context section and `plan.md`'s "Chokepoint" section.
- Run only `tests/specify_cli/doctrine/test_pack_validator.py` for this WP's own gate — never
  the full suite (C-004).

---

`spec-kitty agent action implement WP02 --agent <name>`
