---
work_package_id: WP02
title: Coord-topology fixture + FR-009-isolated reachability reproduction (test-only)
dependencies: []
requirement_refs:
- FR-009
planning_base_branch: fix/runtime-advance-guard-3883
merge_target_branch: fix/runtime-advance-guard-3883
branch_strategy: "single_branch topology (per meta.json): this mission has no coordination branch, no per-WP branches, and no worktrees. All planning and implementation happen directly on fix/runtime-advance-guard-3883, the mission's one and only branch. planning_base_branch and merge_target_branch both name that same branch because there is no separate landing/merge step for this WP -- committed changes land on fix/runtime-advance-guard-3883 directly."
base_branch: kitty/mission-runtime-advance-guard-topology-wp-completion-01M1W6VZ
base_commit: ffa5012918af36d2793b825b58cc27f9ee2d49dc
created_at: '2026-09-07T01:37:43.429251+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
history: []
agent_profile: python-pedro
authoritative_surface: tests/runtime/next/
create_intent:
- tests/runtime/next/test_coord_topology_fixture.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- tests/runtime/next/test_coord_topology_fixture.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Build a reusable coord-topology test fixture (a primary-checkout directory holding a
real work-package file, plus a separate, coordination-worktree-shaped `feature_dir`
that never receives it — parameterized on which lane-transition events, if any, are
seeded on the coord side), resolve the `feature_dir.name`→`mission_slug` empirical
question, and write a red-first reproduction that isolates FR-009's coord-anchoring
bug from FR-004's separate `_wp_blocks_step` bug — against **unmodified** production
code.

## Context

**This mission was narrowed by operator ruling on 2026-09-07** from two issues
(#3883 + #3884) down to #3884 only. See `spec.md`'s "Scope Narrowing" section and
`plan.md`'s "Narrowing" section for the full evidence: draft PR #3923 already fixes
#3883 independently, in a file (`runtime_bridge_io.py`) this mission no longer
touches. **This WP is the direct successor of the pre-narrowing mission's own WP02**
(same id, same "test-only, no dependency on WP01" role, same underlying
coord-topology fixture shape) — repurposed to prove a different bug with that same
fixture shape, not a fresh design.

**Why a coord-topology fixture is still needed at all, for a mission that is now
entirely about `_wp_blocks_step`/`_should_advance_wp_step`.** `_should_advance_wp_step`
(`src/runtime/next/runtime_bridge.py:738-780`) does its own unanchored PRIMARY-partition
read — `tasks_dir = feature_dir / "tasks"` (`:753`) — before it ever reaches the
per-WP loop that calls `_wp_blocks_step` (where FR-004's `Lane.UNINITIALIZED` fix
lives). `tasks/WP*.md` is a PRIMARY-partition artifact (`MissionArtifactKind.
WORK_PACKAGE_TASK`); it is minted on the mission's PRIMARY checkout by `specify`/
`plan`/`tasks`, and for a COORD-topology mission the coordination branch is cut
before any of that runs (`src/specify_cli/missions/_create.py:195-259`), so the
coordination worktree never receives it. This means `_should_advance_wp_step`,
called with a coord-worktree `feature_dir` (as it genuinely is for a real
coord-topology mission's `implement` step advance), hits its own no-`tasks/`-dir
early return and returns `True` (permits advancement) **before the per-WP loop is
ever reached** — independent of whatever `_wp_blocks_step` itself would say. A
coord-topology fixture is the ONE fixture shape that can demonstrate this: a
non-coord fixture (`feature_dir` directly containing `tasks/`) never exercises the
unanchored read at all.

**Why this WP's reproduction uses an `in_progress`-claimed WP, not an uninitialized
one — a deliberate isolation choice, not an oversight.** An uninitialized WP would
ALSO make `_should_advance_wp_step` wrongly return `True` today on a coord fixture —
but for a reason that has nothing to do with the coord-anchoring bug this WP exists
to isolate: `_wp_blocks_step`'s own separate, already-known `Lane.UNINITIALIZED` gap
(FR-004, fixed in WP01, not here) ALSO returns `False`/"does not block" for an
uninitialized WP, even when the per-WP loop IS reached. Using an uninitialized WP
here would conflate two independent bugs in one assertion and prove neither
cleanly. An `in_progress`-claimed WP sidesteps this: `_wp_blocks_step("implement",
InProgressState(), ...)` already correctly returns `True` (blocks) **today**, with
no fix needed (`is_run_affecting=True`, lane not in `{FOR_REVIEW, APPROVED}`) — so
if `_should_advance_wp_step` still (wrongly) returns `True` for a coord fixture
seeded with an `in_progress` WP, the ONLY possible cause is the coord-anchoring gap,
never `_wp_blocks_step`'s own logic. This WP's reproduction is therefore genuinely
callable against **unmodified** production code (no new `_should_advance_wp_step`
signature is needed — the plain, current 2-arg call already demonstrates the bug)
and needs no dependency on WP01's own fix landing first.

**The mission's own #3884-only reproduction that DOES use an uninitialized WP (proving
FR-004 and FR-009 fire TOGETHER for the real production scenario) is WP01's job, not
this WP's** — it needs `_should_advance_wp_step`'s extended `repo_root=`/
`mission_slug=` signature, which does not exist until WP01 adds it. WP01 reuses THIS
WP's fixture builder (parameterized to seed zero coord-side events instead of an
`in_progress` claim) rather than rebuilding an equivalent one.

**The one previously-open empirical question this WP still resolves**: whether
`feature_dir.name` reliably equals the exact `mission_slug` string `placement_seam`
expects for a real coord-worktree layout (bare slug vs. the composed `<slug>-<mid8>`
form). The pre-narrowing draft's second empirical spike (which exception a
corrupt/missing `meta.json` read raises) is **already answered** by the narrowing
work itself — verified empirically against `MissionArtifactKind.WORK_PACKAGE_TASK`
specifically (the kind FR-009 actually uses, not `PRIMARY_METADATA`): a corrupt or
missing `meta.json` does **not** raise for this kind at all (resolving a
PRIMARY-partition kind's directory is pure path composition off the canonicalized
`mission_slug`, never a `meta.json` content read); the one exception that CAN fire
is the already-existing `MissionSelectorAmbiguous`, for a genuinely ambiguous
handle. This is now load-bearing design in `plan.md`'s "FR-010" section — you do not
need to re-spike it, only cite it.

**Tracer files.** `tracer-design-decisions.md` is owned by WP03 in `wps.yaml` (so the
mission's tracer entries land in one disjoint, non-overlapping file set across all
three WPs). Appending your empirical finding there is a small, well-justified
out-of-map edit under this repo's ownership-map leeway norm — record a one-line
rationale in your commit/PR notes when you do it. Do not add
`tracer-design-decisions.md` to this WP's own `owned_files`.

**Sibling test-file patterns to follow**: `tests/runtime/next/test_cli_guard_family.py`
(module docstring style, `DecideNextContext` hand-construction pattern at `:487`) and
`tests/runtime/next/test_presence_filenames.py` (fixture-building style).
`tests/runtime/next/test_pertype_presence_gate.py` is the existing `repo_root`-param
precedent (#3704) to mirror for how `repo_root` is threaded into a fixture-backed
call.

## Subtask T001: Build the coord-topology fixture builder

**Purpose**: Provide a single, reusable fixture-construction function that produces
(a) a primary-checkout directory with a real `tasks/WP01-sample.md` file, and (b) a
separate, coordination-worktree-shaped `feature_dir` holding only
`status.events.jsonl`, seeded with a caller-supplied list of lane-transition events
for that WP id (empty by default — i.e. folds to `UNINITIALIZED` — so WP01 can reuse
the default for its own uninitialized-WP reproduction without re-specifying it).

**Steps**:
1. In `tests/runtime/next/test_coord_topology_fixture.py`, add a `pytest` fixture
   (or plain helper function returning a small dataclass/tuple of `(primary_dir:
   Path, coord_feature_dir: Path, repo_root: Path, mission_slug: str)`) built on
   `tmp_path`. Signature sketch:
   `def build_coord_topology_fixture(tmp_path: Path, *, wp_events: list[dict] | None = None) -> CoordTopologyFixture: ...`
   — `wp_events` defaults to `None`/empty (zero events, folds to `UNINITIALIZED`).
2. Populate `primary_dir` with a minimal real `tasks/WP01-sample.md` (content can be
   minimal placeholder text — the guard only checks presence for the `tasks_dir.is_dir()`/
   glob step, and the WP-lane fold comes from `status.events.jsonl`, not this file's
   content).
3. Populate `coord_feature_dir` with a `status.events.jsonl` file containing exactly
   the `wp_events` the caller supplied (empty file/no lines when `wp_events` is
   `None` — this is the zero-events, `UNINITIALIZED`-folding shape WP01 will reuse
   by default).
4. Wire `repo_root` and `mission_slug` so that
   `mission_runtime.placement_seam(repo_root, mission_slug).read_dir(
   mission_runtime.MissionArtifactKind.WORK_PACKAGE_TASK)` resolves to `primary_dir`
   for this fixture. Inspect `src/mission_runtime/resolution.py` if the exact
   directory structure `placement_seam` expects is not obvious from
   `test_cli_guard_family.py`'s existing `repo_root`-fixture patterns.
5. Keep the builder importable at module scope, since WP01 will import it — check
   `tests/runtime/next/` for an existing cross-test-file import precedent before
   assuming a plain dotted import works; a `conftest.py` fixture may be more
   idiomatic if plain cross-module import proves awkward (see Risks below).

**Files**: `tests/runtime/next/test_coord_topology_fixture.py` (new, ~90 lines for
this subtask's portion).

**Validation**: A standalone test asserts the fixture builder itself produces a
`primary_dir` containing `tasks/WP01-sample.md` and a `coord_feature_dir` containing
only `status.events.jsonl`, with content matching whatever `wp_events` was passed.

## Subtask T002: Empirical spike — `feature_dir.name` → `mission_slug` reliability

**Purpose**: Resolve the one still-open empirical unknown: whether
`feature_dir.name` reliably equals the exact `mission_slug` string `placement_seam`
expects for a real coord-worktree layout (bare slug vs. the composed `<slug>-<mid8>`
form `_resolve_mission_read_path`/`_compose_mission_dir` can produce, per
`src/specify_cli/missions/_read_path_resolver.py:534-650`). This generalizes across
`MissionArtifactKind` values — `resolve_artifact_surface`'s own body resolves the
mission_slug→primary-directory mapping via `resolve_planning_read_dir(..., kind=
MissionArtifactKind.PRIMARY_METADATA, ...)` UNCONDITIONALLY, regardless of the
actual `kind` the caller asked for — so a finding against `WORK_PACKAGE_TASK` (this
mission's own kind) is representative, not merely analogous.

**Steps**:
1. Using T001's fixture (or a second coord-worktree-shaped fixture whose
   `feature_dir.name` is deliberately the composed `<slug>-<mid8>` form, if your
   first fixture used the bare slug), assert that
   `placement_seam(repo_root, feature_dir.name).read_dir(MissionArtifactKind.WORK_PACKAGE_TASK)`
   resolves to the SAME directory the primary fixture path denotes.
2. If it does NOT hold for the composed-name variant, write the assertion that
   demonstrates the mismatch instead, and record that finding plainly.
3. Record the finding as a new dated entry under `tracer-design-decisions.md`'s
   existing "Open item for WP1" note (do not delete that note; append your finding
   beneath it) — either "confirmed: `feature_dir.name` reliably resolves via
   `placement_seam` for both bare-slug and composed forms" or "confirmed mismatch
   for the composed form; reproductions must pass `mission_slug` explicitly."

**Files**: same test file, ~40 lines. `tracer-design-decisions.md` (append,
out-of-map edit per Context above).

**Validation**: The assertion runs and passes (whichever direction the finding
goes); the tracer entry is legible and dated.

## Subtask T003: Reproduction — FR-009's coord-anchoring bug, isolated from FR-004

**Purpose**: Prove the coord-topology reachability bug BY ITSELF, against
**unmodified** production code, using an `in_progress`-claimed WP so the assertion
cannot be explained by `_wp_blocks_step`'s separate, already-known
`Lane.UNINITIALIZED` gap (see Context above for the full isolation rationale — do
not substitute an uninitialized WP here).

**Steps**:
1. Using T001's builder, build a coord-topology fixture seeded with a claim +
   `in_progress` transition event for the WP id on the coord side (`wp_events=[...]`
   — construct a well-formed event matching this repo's `status.events.jsonl`
   schema; see `src/specify_cli/status/emit.py`/existing fixtures for the exact
   shape).
2. Call `_should_advance_wp_step("implement", coord_feature_dir)` — the function's
   **current, plain 2-arg signature**, no `repo_root`/`mission_slug` keywords (they
   do not exist yet).
3. Assert (pre-fix, RED): the call returns `True` — wrongly permitting advancement
   for an actively `in_progress` WP, because the unanchored `tasks_dir` read never
   even reaches the per-WP loop that would otherwise correctly call
   `_wp_blocks_step` and get `True`/blocks back.
4. Mark this assertion clearly as the RED state this reproduction starts with — a
   comment or docstring line noting "pre-fix: expected to wrongly return True; WP01
   flips this to `False` via FR-009's anchoring" is sufficient; do not write an
   inverted post-fix assertion here, since WP01 owns the production fix and its own
   test files, not this one.

**Files**: same test file, ~35 lines.

**Validation**: Run this test against the current, unmodified checkout and confirm
it demonstrates the RED failure exactly as described.

## Subtask T004: Regression pin — the parallel primary-dir call already returns correctly

**Purpose**: Confirm the already-working path is not touched by this WP's own
fixture work, and give WP01 a pre-existing-green baseline to diff against after its
fix lands — proving the bug T003 demonstrates is specifically about the
coord-worktree split, not about `_wp_blocks_step`'s handling of `in_progress`.

**Steps**:
1. Using the SAME `primary_dir` from T001 (not the coord worktree) and the SAME
   `in_progress` event content, call `_should_advance_wp_step("implement", primary_dir)`.
2. Assert `False` is returned (correctly blocks) — this already passes today; it is
   not a red-first assertion, it is a regression pin.

**Files**: same test file, ~15 lines.

**Validation**: Passes today, unmodified.

## Subtask T005: Finalize tracer entries, capture the NFR-001 pre-change baseline, and hand off the fixture for WP01

**Purpose**: Close out this WP's contribution to the mission's tracer trail, capture
the mission's own NFR-001 pre-change baseline BEFORE any production-code change
lands, and make the fixture builder discoverable for WP01's own reproductions.

**Steps**:
1. Confirm T002's `tracer-design-decisions.md` entry is present, dated, and legible
   (append-only — do not remove or rewrite the pre-existing seed content in that
   file, including its 2026-09-07 narrowing entry).
2. Add a short module-level docstring to `tests/runtime/next/test_coord_topology_fixture.py`
   naming this as WP02, the fixture builder's exact importable name
   (`build_coord_topology_fixture`), and the empirical finding T002 established, so
   WP01's own test files can cite it precisely when they import it — check
   `tests/runtime/next/` for an existing cross-test-file import precedent before
   assuming a plain dotted import works; a `conftest.py` fixture may be more
   idiomatic if plain cross-module import proves awkward (see Risks).
3. Run this WP's full test file once more, confirm all functional tests (T001's
   standalone fixture check, T002, T003's RED assertion, T004's regression pin)
   pass in their stated RED/pass state, and record the exact `pytest` invocation
   and pass count in your own WP completion notes.
4. **Capture the NFR-001 pre-change baseline, BEFORE any production-code change
   lands.** This WP makes no production-code change itself, and WP01 (`dependencies:
   [WP02]`) depends on this WP finishing first — so running the three exact
   invocations here, at the close of WP02, satisfies the "run FIRST" instruction for
   the mission as a whole. Run, and record the actual observed counts (even if they
   match exactly) as a new dated entry in `tracer-design-decisions.md`:
   ```
   pytest tests/runtime tests/next tests/specify_cli/next tests/specify_cli/status
   ```
   (fast/unit tier) — cited baseline: **1666 passed, 1 skipped, 325 deselected**.
   ```
   pytest tests/runtime/next tests/next
   ```
   (full) — cited baseline: **598 passed**.
   ```
   pytest tests/runtime --ignore=tests/runtime/next
   ```
   — cited baseline: **672 passed, 1 skipped** (673 collected; do NOT substitute the
   naive `pytest tests/runtime -q` without `--ignore`, which collects a different,
   larger 746/745 count). If any count differs from the stated baseline, classify it
   per the CLAUDE.md baseline-red gotcha (pre-existing known-P0 red #2736/#2772/#1834,
   CI-environment, stale-install, or stale-venv) before recording it — this entry is
   the mission's own "before" data point that WP03 diffs its "after" counts against.

**Files**: same test file (docstring only, ~10 lines); `tracer-design-decisions.md`
(verify T002's entry, and append the new NFR-001 pre-change baseline entry from
step 4).

**Validation**: `pytest tests/runtime/next/test_coord_topology_fixture.py -v` runs
clean with T003's RED assertion demonstrating the live bug and T004's regression pin
and T001's fixture check passing; the three NFR-001-exact baseline invocations have
been run and their counts recorded in `tracer-design-decisions.md` before WP01
begins.

## Definition of Done

- `tests/runtime/next/test_coord_topology_fixture.py` exists with a reusable
  `build_coord_topology_fixture` (or equivalent) fixture builder, T003's reproduction
  demonstrating RED against unmodified production code, and T004's primary-dir
  regression pin passing.
- T002's empirical unknown is resolved and recorded in `tracer-design-decisions.md`
  with a dated entry.
- The three NFR-001-exact baseline invocations have been run and their counts
  recorded in `tracer-design-decisions.md`, BEFORE any production-code change lands
  (T005) — this mission's own "before" data point for WP03 to diff against.
- No production code under `src/` is touched by this WP.
- **Baseline-red discipline**: before treating any test result here as this WP's own
  signal, confirm it is not one of the pre-existing known-red tests named in
  CLAUDE.md (#2736, #2772, #1834); if an unrelated collection error or failure
  appears while running this file, classify it per the CLAUDE.md baseline-red gotcha
  before assuming it is caused by this WP's new file.
- `spec-kitty agent tasks mark-status T00N --status done` recorded for each of
  T001–T005 (event-sourced; not a ticked checkbox).

## Risks

- **Fixture-shape risk**: `placement_seam`'s exact expected on-disk layout for a
  coord-worktree-vs-primary pair may not be obvious from reading `resolution.py`
  alone. Mitigation: lean on `test_cli_guard_family.py`'s existing `repo_root`-fixture
  patterns as the closest verified precedent before inventing a new layout from
  scratch.
- **T002's finding could go either way**: if `feature_dir.name` does NOT reliably
  yield the right `mission_slug` for the composed-name form, WP01's own reproductions
  must pass `mission_slug` explicitly rather than relying on the fallback — flag this
  clearly in your tracer entry so WP01's author does not have to re-derive it.
- **Cross-file import path**: if a plain Python import from one test module into
  another proves awkward in this repo's test-collection setup, prefer a
  `conftest.py`-based shared fixture instead — but note that doing so would make
  `conftest.py` a file BOTH WP01 and WP02 touch, which risks the exact file-level
  overlap the mission's repartitioning exists to avoid. If you hit this, prefer
  keeping the builder as a plain importable function in this WP's own file over
  adding a shared `conftest.py`, so `owned_files` stays disjoint. If a `conftest.py`
  addition turns out to be unavoidable, flag it explicitly in your completion notes
  rather than silently expanding scope.

## Reviewer Guidance

- Confirm T003's reproduction genuinely runs against **unmodified** production code
  (no accidental production edits crept into this WP) and demonstrates RED with the
  `in_progress` WP wrongly permitted through — NOT an uninitialized WP (that would
  conflate this WP's isolated FR-009 proof with FR-004's separate bug).
- Confirm T004's regression pin passes today, unmodified.
- Confirm T002's empirical-spike tracer entry is dated, legible, and does not
  overwrite the pre-existing seed content in `tracer-design-decisions.md`.
- Confirm the fixture builder is genuinely reusable (a plain function/fixture WP01
  can import or otherwise reference), parameterized on `wp_events` so WP01 can build
  its own uninitialized-WP variant without duplicating the fixture-construction
  logic.
- Confirm no file outside `tests/runtime/next/test_coord_topology_fixture.py` is
  modified except the sanctioned `tracer-design-decisions.md` append.
- Confirm the three NFR-001-exact baseline invocations (T005 step 4) were actually
  run and their counts recorded in `tracer-design-decisions.md` BEFORE WP01's first
  production-code commit — not merely re-cited from plan.md without being re-run.

**Implementation command**: `spec-kitty agent action implement WP02 --agent claude`
