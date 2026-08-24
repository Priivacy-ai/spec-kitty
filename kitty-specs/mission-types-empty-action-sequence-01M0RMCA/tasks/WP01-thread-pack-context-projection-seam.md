---
work_package_id: WP01
title: Thread pack_context through the mission-type projection seam
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- C-001
- C-002
- C-003
- C-004
- C-005
- C-006
- C-007
- C-008
planning_base_branch: fix/mission-types-empty-action-sequence-3701
merge_target_branch: fix/mission-types-empty-action-sequence-3701
branch_strategy: Planning artifacts for this mission were generated on fix/mission-types-empty-action-sequence-3701. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/mission-types-empty-action-sequence-3701 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
- T009
history: []
agent_profile: implementer-ivan
authoritative_surface: src/doctrine/missions/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/missions/mission_type_repository.py
- tests/doctrine/missions/test_mission_type_repository.py
- tests/runtime/test_runtime_seam.py
role: implementer
tags: []
tracker_refs: []
---

# WP01 — Thread `pack_context` through the mission-type projection seam

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Fix `_inject_projected_fields()` in `src/doctrine/missions/mission_type_repository.py`,
which today hardcodes `pack_context=None` when it derives a mission type's
`action_sequence` from that type's `mission-steps/<type>/<step>/step.yaml` files. Because
none of its three callers up the chain forward a real `pack_context` into it either, every
org/project mission type that relies on step-file projection (no explicit `action_sequence:`
authored in its own `<type>.yaml`) resolves `action_sequence = None`/`[]`, and every governed
entry point then raises `MissionTypeEmptyActionSequenceError`. This WP threads one
already-in-hand `pack_context` value through the existing four-function call chain
(`_inject_projected_fields` → `_load_layered_mission_type_file` → `scan_mission_types_dir` →
`resolve_layered_mission_types`) so every layer's own step-file projection sees the real,
fully-layered step set instead of a built-in-only one — without perturbing built-in
resolution or `MissionTypeRepository._load()`'s separate built-in-only cache.

## Context

This is a bug-fix mission with exactly **one** Implementation Concern (plan.md IC-01) and
exactly **one** WP — do not split this into multiple WPs or multiple PRs. `plan.md`'s own "PR
shape" section states this explicitly: the four touched functions are one call chain, not
independent architectural areas; a partial threading (e.g. fixing only
`_inject_projected_fields`) would leave the defect live end-to-end.

This seam is a chokepoint for three production `src/` callers —
`_resolve_action_slot` (`charter/mission_type_profiles.py:976`), `resolve_layered_roster`
(`specify_cli/cli/commands/charter/mission_type.py:87`), and `_resolve_layered_roster`
(`specify_cli/cli/commands/_mission_type_audit.py:170`) — all of which reach
`resolve_layered_mission_types` exclusively through this one seam; see plan.md's "Blast radius on
downstream workspaces" section for the full list and why T004's golden-parity test transitively
covers all three.

**Full requirements source**: read `spec.md` and `plan.md` in full before starting — both are
committed baselines and this prompt does not repeat everything in them, only the concrete
mechanics. `spec.md`'s Clarifications section records two binding decisions you must not
re-litigate: (1) thread `pack_context` into this seam, do NOT migrate `action_sequence` to
consumption-boundary sourcing the way `template_set` was retired (C-002); (2) do NOT touch the
activation-gate behavior (`charter activate mission-type` succeeding on an empty sequence) —
that is issue #3702's scope, not this WP's (C-003).

**This mission's target branch is `fix/mission-types-empty-action-sequence-3701` itself** — it
is a single-branch mission with no lane/coordination topology. There is no separate
protected-branch merge step for this WP to perform; do not attempt to merge to `main`.

### The four functions and exact current line numbers (re-verified live, 2026-08-24 — matches plan.md with zero drift)

All in `src/doctrine/missions/mission_type_repository.py`:

1. **`_inject_projected_fields`** — `def` at line 209. Hardcoded call at line 245:
   `.resolve_all_for_mission_type(mission_type_id, pack_context=None)`.
2. **`_load_layered_mission_type_file`** — `def` at line 313. Its call into
   `_inject_projected_fields` is at line 347: `_inject_projected_fields(raw,
   mission_type_id=yaml_file.stem)` — currently omits `pack_context` entirely.
3. **`scan_mission_types_dir`** — `def` at line 359. Its call into
   `_load_layered_mission_type_file` is inside its final list-comprehension return:
   `[_load_layered_mission_type_file(f) for f in yaml_files]`.
4. **`resolve_layered_mission_types`** — `def` at line 410. Already receives `pack_context` as
   a required positional parameter, already typed `_PackContextLike | None` at line 412 — **no
   signature change needed here.** The fix is inside its **body**, at its three
   `scan_mission_types_dir(...)` calls (confirmed live at lines 515, 525, 530):
   - Line 515: `for mission_type in scan_mission_types_dir(base_dir):` (built-in-equivalent layer)
   - Line 525: `for mission_type in scan_mission_types_dir(org_dir):` (org layer, inside `if
     pack_context is not None:`)
   - Line 530: `for mission_type in scan_mission_types_dir(project_dir):` (project layer, same
     `if` block)

   All three currently call `scan_mission_types_dir` with a single positional directory
   argument and never forward `pack_context` — that is the actual root cause, one level deeper
   than "the top-level function doesn't take `pack_context`" (it already does).

`MissionTypeRepository._load()`'s call site (line 165:
`_inject_projected_fields(raw, mission_type_id=yaml_file.stem)`) is **deliberately NOT
touched** — FR-005/C-001. It stays a zero-argument call, which correctly resolves to
`pack_context=None` via `_inject_projected_fields`'s new keyword default. Do not add a
`pack_context` argument to this call site; doing so would poison `_load()`'s `cls`-keyed,
built-in-only cache for later-resolved, different projects in the same process.

### C-008 — the typing pin (load-bearing, cost two operator-authorized rounds during planning)

**All four of the above functions must type their `pack_context` parameter as
`_PackContextLike | None` — never the concrete `charter.pack_context.PackContext` class, not
even under `TYPE_CHECKING`.**

- `_PackContextLike` is the structural Protocol already defined at
  `src/doctrine/missions/mission_step_repository.py:41`, and it is **already imported** into
  `mission_type_repository.py` and **already used** by `resolve_layered_mission_types`'s
  existing signature at line 412. Reuse that same import — do not add a new one.
- The reason this bar applies even under `TYPE_CHECKING`: `src/doctrine/` importing
  `src/charter/` in ANY form (runtime or type-checking-only) is an illegal upward import. Tier
  order is `kernel <- doctrine <- charter`, pinned by `tests/architectural/conftest.py:90`. A
  `TYPE_CHECKING`-only import of `charter.pack_context.PackContext` would still violate this —
  `_PackContextLike` exists specifically to replace that import mode too, not just the runtime
  one. If you find yourself tempted to `from charter.pack_context import PackContext  #
  TYPE_CHECKING`, stop — use `_PackContextLike` instead.
- `functools.cache` on `resolve_layered_mission_types` is keyed on `(mission_types_dirs,
  pack_context)` — `_PackContextLike` declares `__hash__` explicitly for exactly this reason
  (mypy strict needs it to be a structural subtype of `Hashable`). Do not change the cache key
  shape.

### Existing test helpers to reuse (do not duplicate)

`tests/doctrine/missions/test_mission_type_repository.py` (around line 420 onward, class
`TestLayeredMissionTypesCacheKeyAndClear`):
- `_StubPackContext` (a frozen dataclass with `pack_roots: tuple[Path, ...]` and `repo_root:
  Path`) — reuse this for your new test fixtures; do not write a second stub.
- `_write_layered_yaml(directory, filename, content) -> Path` — reuse for writing
  `mission_types/<id>.yaml` files.
- `_mission_type_yaml(mission_type_id, *, action_sequence: list[str]) -> str` — this existing
  helper always writes an explicit `action_sequence:` key. **It does NOT fit NFR-001's
  steps-only fixture** (which must have NO `action_sequence:` key at all) — write a sibling
  helper (e.g. `_mission_type_yaml_steps_only(mission_type_id) -> str`, no `action_sequence`
  key in the YAML) rather than repurposing or mutating the existing one (other tests in that
  class depend on its current exact behavior).

`tests/doctrine/missions/test_mission_step_resolver.py` (around lines 40–110) has the pattern
for writing a `mission-steps/<type>/<step>/step.yaml` tree:
- `_write_step`, `_write_org_step`, `_write_project_step` — these write minimal `step.yaml`
  files but **do not set `sequence_index` / `in_action_sequence`**, so they will project to an
  empty sequence as-is. For this WP's fixtures you need a variant that also writes
  `sequence_index: <int>` and `in_action_sequence: true` (see a built-in `step.yaml` for the
  field shape, e.g. `packs/built-in/missions/mission-steps/software-dev/*/step.yaml`) — write a
  new local helper in `test_mission_type_repository.py` (do not import test helpers across test
  files; each test file's helpers are local by convention here) rather than copying the
  existing under-specified ones verbatim.
- Path convention confirmed live: org-tier step tree is
  `<org_root>/mission-steps/<mission_type_id>/<step_id>/step.yaml`; project-tier step tree is
  `<repo_root>/.kittify/overrides/mission-steps/<mission_type_id>/<step_id>/step.yaml` (per
  `mission_step_repository.py`'s own resolution order, confirmed at
  `mission_step_repository.py:441`).
- Project-tier mission-*type* YAML (distinct from the step tree) lives at
  `<repo_root>/.kittify/missions/mission_types/<id>.yaml` — confirmed via
  `_PROJECT_MISSION_TYPES_RELATIVE = (".kittify", "missions", "mission_types")` at
  `mission_type_repository.py:310`. Org-tier mission-type YAML lives at
  `<pack_root>/mission_types/<id>.yaml` (`_ORG_MISSION_TYPES_SUBDIR = "mission_types"`, line
  303).

`tests/runtime/test_runtime_seam.py`, class `TestGoldenParityUnaffectedByPackContextThreading`
(line 184), method `test_builtin_type_unaffected_by_real_pack_context_with_org_root` (line
206): the existing pattern for asserting a built-in type's `action_sequence` is byte-identical
under `pack_context=None` vs. a real `pack_context` declaring an unrelated org pack. It patches
`"charter.pack_context.PackContext.from_config"` as a string target via `unittest.mock.patch` —
follow this exact pattern for any new/extended parity assertion (the `patch()` target
validation CI gate checks string targets are real, so do not invent a new patch shape).

## Subtask T001: Baseline capture (pre-implementation, before ANY production-code change)

**Purpose**: Establish the honest pre-fix baseline per spec.md SC-005 and plan.md's "Test
baseline" section, so pre-existing red is never confused with mission-introduced red.

**Steps**:
1. Before touching `mission_type_repository.py`'s production code (and before writing any new
   test — this is the very first action), run exactly:
   ```
   pytest tests/doctrine/missions/test_mission_type_repository.py tests/runtime/test_runtime_seam.py
   ```
   against the unmodified base commit.
2. Record the full pass/fail counts and any red test ids in `tracer-approach.md` or
   `tracer-design-decisions.md` (append, do not recreate).
3. Cross-check any red test id you observe against `gh issue view 3284` (and its comments, where
   the per-test breakdown lives) — the ~23 known-red / 2-error baseline on `main` — note
   explicitly whether it's already enumerated there or is new-but-pre-existing (log against a
   fresh tracked issue reference if genuinely new and not covered by #3284's own breakdown).
   SPEC-KITTY-LEDGER.md has no #3284 entry (verified: zero mentions of "3284" in the ledger) —
   `gh issue view 3284` and its comments are the real source, not the ledger.

**Files**: no code files touched — this is a read-only verification step whose output goes
into the tracer files.

**Validation**: the tracer entry names the exact command run and the exact result (pass/fail
counts, red test ids if any).

## Subtask T002: Red-first test (NFR-001) — steps-only-projection reproduction, committed BEFORE the fix

**Purpose**: Satisfy the charter's ATDD-First Discipline (C-011) and spec.md's SC-004: author
the regression test that pins this exact defect shape and commit it, on its own, before any
production-code change to `mission_type_repository.py`.

**Steps**:
1. In `tests/doctrine/missions/test_mission_type_repository.py`, add a new test (sibling to
   `TestLayeredMissionTypesCacheKeyAndClear`, e.g. a new class
   `TestLayeredProjectionThreadsPackContext` or an added method on the existing class — your
   call, but keep it in this file, not a new file) that:
   - Writes an org-tier `mission_types/<id>.yaml` with **no `action_sequence:` key** (use your
     new `_mission_type_yaml_steps_only` helper from Context above).
   - Writes a matching `mission-steps/<id>/<step>/step.yaml` tree for that org pack — several
     steps, each carrying `sequence_index` (0, 1, 2, ...) and `in_action_sequence: true` — using
     your new step-tree helper.
   - Builds a real `_StubPackContext` pointing at that org pack root (via `pack_roots`) and a
     `repo_root` that has no conflicting project-layer override.
   - Calls `resolve_layered_mission_types(mission_types_dirs, pack_context)` (remember to
     `resolve_layered_mission_types.cache_clear()` in `setup_method`/`teardown_method`, matching
     the existing class's pattern, since this is a `functools.cache`-decorated function).
   - Asserts the returned `MissionType` for that id has `action_sequence` equal to the exact
     step order your fixture defines (e.g. `['discovery', 'specify', 'plan', ...]`) — matching
     spec.md's Acceptance Scenario 1 shape (`qa -> ['discovery', 'specify', 'plan', 'tasks',
     'implement', 'review', 'accept']` is the issue's own repro transcript; your fixture does
     not need those exact step names, but should be similarly concrete, not a single-step
     fixture that could pass trivially).
   - **Also closes spec.md's Acceptance Scenario 2** (the governed entry point does not raise):
     using the same org-tier steps-only fixture, additionally call the governed seam
     `charter.mission_type_profiles.resolve_mission_type_context(repo_root, mission_type=<id>)`
     — following the `_resolve_via_seam` pattern already in
     `tests/runtime/test_runtime_seam.py` (patch `"charter.mission_type_profiles.existing_mission_types"`
     to return a list including your fixture's mission type id, and patch
     `"charter.pack_context.PackContext.from_config"` to return your fixture's `pack_context`,
     the same two-patch shape `TestGoldenParityUnaffectedByPackContextThreading` already uses)
     — and assert it succeeds (returns a bundle) without raising
     `MissionTypeEmptyActionSequenceError`. Do not import the helper function itself across test
     files; write this call locally in this file, following the pattern, per this WP's own
     no-cross-file-helper-import convention.
2. Run this new test now, against the still-unfixed production code. **It must fail** on both
   assertions — the direct `resolve_layered_mission_types` assertion on `None`/`[]`, and the
   governed-entry-point assertion (which should observe `MissionTypeEmptyActionSequenceError`
   being raised, not absent) — reproducing today's defect at both the low-level function and the
   governed entry point; this is expected and required at this point (the fix has not landed
   yet).
3. Commit this test file change as its own, separate commit — a conventional-commit-shaped
   message (commitlint is an enforced CI gate), e.g. `test(doctrine): add red-first
   steps-only-projection reproduction for #3701`. **Do not combine this commit with any
   production-code change.**

**Files**: `tests/doctrine/missions/test_mission_type_repository.py` (~70–120 new lines: helper
functions + one test class/method, including the governed-entry-point assertion above).

**Validation**: `pytest tests/doctrine/missions/test_mission_type_repository.py -k
<your_new_test_name>` fails — the `resolve_layered_mission_types` assertion on `None`/`[]`, and
the governed-entry-point call raising `MissionTypeEmptyActionSequenceError` — not an
error/collection failure unrelated to either (a collection error means the fixture itself is
broken, not that it's pinning the defect).

## Subtask T003: The fix — four signature edits + three call-site edits (one coherent change)

**Purpose**: Thread `pack_context` end-to-end through the seam. This is one atomic logical
change across one file — make all seven edits together, then commit as the fix commit(s)
separate from T002's red-first test commit.

**Steps**:
1. `_inject_projected_fields` (line 209): add a keyword-only parameter `pack_context:
   _PackContextLike | None = None` to the signature. Change the call at line 245 from
   `.resolve_all_for_mission_type(mission_type_id, pack_context=None)` to
   `.resolve_all_for_mission_type(mission_type_id, pack_context=pack_context)`.
2. `_load_layered_mission_type_file` (line 313): add a keyword-only parameter `pack_context:
   _PackContextLike | None = None` to the signature. Change the call at line 347 from
   `_inject_projected_fields(raw, mission_type_id=yaml_file.stem)` to
   `_inject_projected_fields(raw, mission_type_id=yaml_file.stem, pack_context=pack_context)`.
3. `scan_mission_types_dir` (line 359): add a keyword-only parameter `pack_context:
   _PackContextLike | None = None` to the signature. Change the final list-comprehension return
   from `[_load_layered_mission_type_file(f) for f in yaml_files]` to
   `[_load_layered_mission_type_file(f, pack_context=pack_context) for f in yaml_files]`.
4. `resolve_layered_mission_types` (line 410): **no signature change** (already takes
   `pack_context` typed correctly). Edit its body's three call sites (confirmed live at 515,
   525, 530):
   - `scan_mission_types_dir(base_dir)` → `scan_mission_types_dir(base_dir,
     pack_context=pack_context)`
   - `scan_mission_types_dir(org_dir)` → `scan_mission_types_dir(org_dir,
     pack_context=pack_context)`
   - `scan_mission_types_dir(project_dir)` → `scan_mission_types_dir(project_dir,
     pack_context=pack_context)`
5. Do **not** touch `MissionTypeRepository._load()` (line 157–174) or its call site at line 165
   — verify after your edit that it still compiles with zero source change (its zero-argument
   call now resolves to `pack_context=None` via the new defaults you just added).
6. Do **not** touch `charter/pack_manager.py:865`'s `scan_mission_types_dir(scan_dir)` call
   (FR-008) — it keeps passing no `pack_context`, which remains valid because of the new
   default, and is safe because that call site only reads `.id`/`.layer`, never
   `.action_sequence`.
7. Re-run T002's red-first test now — confirm it **passes**.
8. Commit this production-code change as its own commit(s), separate from T002's test commit.
   Conventional-commit-shaped message, e.g. `fix(doctrine): thread pack_context through
   mission-type projection seam (#3701)`.

**Files**: `src/doctrine/missions/mission_type_repository.py` (~4 signature edits, ~4 call-site
edits — a small, surgical diff).

**Validation**: T002's test now passes. `mypy`/`ruff` show zero new issues on this file (advisory
in CI but must be clean per this repo's own Code Style rule — no `# type: ignore` /
`# noqa` additions).

## Subtask T004: Golden-parity extension (NFR-002 / FR-007)

**Purpose**: Prove the fix introduces zero observable change to built-in mission-type
resolution, even now that the built-in-equivalent layer's `scan_mission_types_dir` call also
receives the real `pack_context` for the first time.

**Steps**:
1. In `tests/runtime/test_runtime_seam.py`, extend
   `TestGoldenParityUnaffectedByPackContextThreading` (line 184). Confirm — or add an explicit
   assertion if not already present — that `test_builtin_type_unaffected_by_real_pack_context_with_org_root`
   (or a new sibling test) asserts, specifically for `action_sequence`: for **every** built-in
   mission type (all four shipped in `packs/built-in/missions/mission_types/`), the value
   resolved with `pack_context=None` is byte-identical to the value resolved with a real,
   non-`None` `pack_context` that declares an **unrelated** org pack (a pack that does not
   override any built-in type's steps) — matching spec.md Acceptance Scenario 3 exactly.
2. **Read the plan's IC-01 Risk note before writing this test**: FR-007/NFR-002's parity claim
   is "byte-identical under an *unrelated* org pack," not "byte-identical under any org pack
   whatsoever." A pack that genuinely overrides a built-in type's steps is *expected*,
   correctly, to change that type's resolution post-fix — that is the fix working as intended,
   not a regression. Do not write a test that asserts no org pack can ever affect a built-in
   type; that would be testing for the wrong invariant and would fail once someone adds a
   legitimate override pack in the future.
3. Follow the existing `unittest.mock.patch("charter.pack_context.PackContext.from_config", ...)`
   pattern already in this class for constructing the "real, non-`None` pack_context" — do not
   invent a new patch target string (the `patch()` target validation CI gate checks these).
4. **NFR-004 evidence (no new filesystem walk)**: in the same test, wrap
   `doctrine.missions.mission_step_repository.MissionStepRepository.resolve_all_for_mission_type`
   with `unittest.mock.patch(..., wraps=MissionStepRepository.resolve_all_for_mission_type)` (a
   call-count spy, not a value replacement) around one `resolve_layered_mission_types` /
   `_resolve_via_seam` invocation for a single built-in type, and assert the call count is
   exactly what it was pre-fix (one call for that type's resolution) — closing the "no new
   filesystem walk" claim with evidence rather than architectural assertion alone.
5. **Vacuity self-check (mirrors T005 step 2's methodology)**:
   `test_builtin_type_unaffected_by_real_pack_context_with_org_root` — the exact test this
   subtask extends — has a documented prior finding of being vacuous (its own sibling test's
   docstring, `test_org_root_content_actually_resolves_through_the_seam`, records that the org
   root previously had no YAML content and so always scanned to `[]`, meaning the test held
   identically whether the fix under test existed or not). Before considering this subtask done,
   temporarily revert just the built-in-equivalent layer's `pack_context` forward — the
   `scan_mission_types_dir(base_dir, pack_context=pack_context)` edit at
   `mission_type_repository.py:515` (revert to `scan_mission_types_dir(base_dir)`) — and confirm
   the extended/new `action_sequence` parity assertion in
   `test_builtin_type_unaffected_by_real_pack_context_with_org_root` would actually **fail** in
   that state. This is a manual verification step only, matching T005's own methodology — do not
   commit the temporary revert.

**Files**: `tests/runtime/test_runtime_seam.py` (~25–50 new/modified lines).

**Validation**: new/extended test passes against the post-fix code; run it also against a
temporary revert of T003's fix to confirm the test only asserts parity (should still pass
pre-fix too, since NFR-002 is explicitly NOT a red-first pin — built-in types already resolve
correctly pre-fix, per the existing class's own docstring).

## Subtask T005: Project-tier acceptance-scenario-5 dedicated test case

**Purpose**: spec.md's Acceptance Scenario 5 (line 62) is a separate, mandatory,
project-tier-specific requirement — it needs its own named test regardless of which tier
T002's NFR-001 case happens to use. Do not fold it silently into T002's case even if T002
happens to also use project-tier.

**Steps**:
1. In `tests/doctrine/missions/test_mission_type_repository.py`, add a dedicated test (e.g.
   `test_project_tier_steps_only_projection_resolves`) that:
   - Points `_StubPackContext.repo_root` at a synthetic project root carrying its own
     `.kittify/missions/mission_types/<id>.yaml` override (no `action_sequence:` key — steps-only).
   - Writes a sibling `mission-steps/<id>/<step>/step.yaml` tree — confirm the exact project-tier
     step-tree path convention against `mission_step_repository.py`'s own resolution order before
     writing the fixture (do not assume; verify).
   - Calls `resolve_layered_mission_types` and asserts the correct non-empty, correctly-ordered
     `action_sequence` — exercising the **project layer** specifically (`pack_context.repo_root`
     / `.kittify/missions/mission_types/*.yaml`), not the org layer.
2. This test may be similar in shape to T002's case but must be traceable specifically to
   Acceptance Scenario 5, not merged into T002's docstring/name.

**Files**: `tests/doctrine/missions/test_mission_type_repository.py` (~40–60 new lines).

**Validation**: passes against post-fix code; confirm it targets the project layer specifically
(temporarily comment out the project-dir branch in `resolve_layered_mission_types` locally, or
otherwise confirm this test would fail if only the org-layer path were fixed — do not commit
that temporary check, it is a manual verification step only).

## Subtask T006: Explicit non-explicit-`action_sequence` regression case (FR-006 / Acceptance Scenario 4)

**Purpose**: Confirm the pre-existing "C-007-retained" raw-YAML fallback still works — an
org/project type that DOES author an explicit `action_sequence:` list directly must keep that
value unchanged; the projection fallback must not silently override an explicitly-authored,
non-empty value with something else, and must still defer to it whenever the projection itself
is empty.

**Steps**:
1. Add or confirm a test case using the existing `_mission_type_yaml(mission_type_id, *,
   action_sequence=[...])` helper (which already authors an explicit `action_sequence:` key) —
   confirm that when this type is resolved (with a real `pack_context`, no matching step tree
   authored, so projection is empty), its explicit `action_sequence` is preserved unchanged.
2. If an equivalent case already exists in the pre-fix test suite and merely needs re-running
   post-fix to confirm no regression, note that explicitly rather than duplicating a test.

**Files**: `tests/doctrine/missions/test_mission_type_repository.py` (small addition or
confirmation, ~15–25 lines if new).

**Validation**: passes; confirms `projected_sequence or raw.get("action_sequence")` fallback
behavior is unchanged by this WP's edits.

## Subtask T007: Red-first witness — the SC-004 stash/rerun/stash-pop sequence

**Purpose**: This is not optional polish. Per spec.md SC-004 and plan.md's "Red-first/ATDD and
SC-004's concrete stash/rerun/stash-pop moment" section, you must literally witness T002's test
fail without the fix and pass with it, and record both runs.

**Steps**:
1. By this point in the WP's own sequence, T002's test commit and T003's fix commit(s) are both
   already committed (T002 step 3, T003 step 8) — the working tree is therefore already clean,
   so a bare `git stash` has nothing to stash and would silently no-op. Use `git revert
   --no-commit <fix-commit-sha>` (the exact SHA(s) of T003's fix commit(s)) to remove the fix
   from the working tree while leaving T002's test commit's changes in place.
2. Rerun T002's test (and T005's, if it also exercises the same code path). Confirm it/they
   **fail**, reproducing today's `None`/`[]` result.
3. Restore the fix: `git revert --abort` (discards the in-progress revert, restoring the working
   tree to the fix-applied state) — or, if the revert was already committed rather than left
   staged, `git reset --hard <fix-commit-sha>`.
4. Rerun the same test(s). Confirm they now **pass**.
5. Record **both runs** — exact command, exact observed result (pass/fail, and ideally the
   specific `action_sequence` value observed in each run, e.g. `None` vs.
   `['discovery', 'specify', ...]`) — in `tracer-approach.md` or `tracer-design-decisions.md`
   (append, do not recreate), so the pre-merge (`sk-review`) squad can verify the claim was
   witnessed, not re-derive it independently.
6. **If the test still passes with the fix reverted, it does not pin the defect.** This is a
   severity-4 finding, not coverage, per charter Standing Order #4. Strengthen the fixture or
   assertion and repeat this subtask until the stash/pop cycle genuinely fails-then-passes.

**Files**: no new code files; append to `tracer-approach.md` or `tracer-design-decisions.md`.

**Validation**: the tracer entry itself, containing both run transcripts.

## Subtask T008: Full targeted-suite run + baseline triage (SC-005)

**Purpose**: Confirm the full scoped test run is clean post-fix, with any red individually
triaged against T001's baseline — never waved through as "the suite is red."

**Steps**:
1. Run exactly:
   ```
   pytest tests/doctrine/missions/test_mission_type_repository.py tests/runtime/test_runtime_seam.py
   ```
   against the post-fix code (all commits from T002–T006 applied).
2. Compare test-by-test against T001's baseline recording:
   - A test id red on **both** runs is pre-existing — leave it red, confirm it's logged (per
     T001's triage), never "fix" it as part of this WP's scope.
   - A test id green on baseline and red post-fix is **mission-introduced** and must be fixed
     before this WP is done.
3. Record the final pass/fail counts and triage outcome in the same tracer file as T001/T007.

**Files**: no new code files; tracer update only (unless T008 reveals a mission-introduced red,
in which case fix it in the relevant owned file and re-run).

**Validation**: zero mission-introduced red remains; tracer entry states this explicitly.

## Subtask T009: SC-006 diff-scope check + gate-set self-check + final tracer sweep

**Purpose**: Confirm the mission's diff stays inside C-007's bound (checkable, not prose-only),
and self-check against the full CI gate set plan.md names, before marking this WP done.

**Steps**:
1. Run `git diff --name-only <base>...HEAD` (or the equivalent your harness exposes) and confirm
   every changed path is either one of C-007's three named files
   (`src/doctrine/missions/mission_type_repository.py`,
   `tests/doctrine/missions/test_mission_type_repository.py`,
   `tests/runtime/test_runtime_seam.py`) or under this mission's own
   `kitty-specs/mission-types-empty-action-sequence-01M0RMCA/**` directory (the one explicit
   carve-out for mission bookkeeping — spec/plan/tracer/tasks/status files). Any other path is a
   C-002/C-003/C-007 violation and must be justified or removed before this WP is marked done.
2. **FR-005/C-001 line-scoped self-check**: the file-level check in step 1 confirms
   `mission_type_repository.py` is a touched file (it is — that's expected) but cannot by itself
   confirm `_load()` specifically has zero diff, since the whole file is one of this WP's owned
   files. Run `git diff <base>...HEAD -- src/doctrine/missions/mission_type_repository.py` and
   confirm no hunk's line range overlaps `_load()`'s body (lines 157–174, call site line 165) —
   every hunk in this file's diff must fall outside that range. If any hunk does overlap, this is
   an FR-005/C-001 violation and must be fixed before this WP is marked done.
3. Self-check against plan.md's "The gate set" section (transcribed summary — see plan.md for
   full detail, do not re-derive independently):
   - commitlint: every commit conventional-commit-shaped. ✓/❌
   - Generated doctrine schemas up to date: no-op here (no model change). ✓ (verify by not
     touching `models.py`)
   - Contextive glossary: does not run against this diff (`src/doctrine/**` outside its path
     filter). N/A
   - Banned-API lint (TID251): `ruff check src tests --select TID251` clean. ✓/❌
   - `patch()` target validation: any new `patch()` calls use real, validated target strings
     (T004's pattern). ✓/❌
   - Bandit + pip-audit: no new dependency, no subprocess/eval/pickle pattern introduced. ✓/❌
   - `uv.lock` check: no-op, no dependency change. ✓ (verify `pyproject.toml`/`uv.lock`
     untouched)
   - **`diff-coverage` critical-path 90% floor on `src/doctrine/*`** — the real applicable
     coverage gate here (NOT the differently-scoped `mission-loader-coverage` job). Confirm your
     new/changed branches (the `pack_context is not None` forward at each of the three call
     sites, the keyword-default-`None` path) each have a direct unit-test assertion from
     T002/T004/T005, not merely incidental coverage.
   - `clean-install-verification`: not expected to interact with this change; still a required
     gate.
   - Markdown lint, kernel-90% coverage: do not apply (verified in plan.md; no re-derivation
     needed).
   - SonarCloud does NOT run on PRs — do not wait for or promise a Sonar verdict.
4. Run `ruff check` and `mypy` locally on the touched files (advisory in CI, but this repo's own
   Code Style rule requires zero issues on new code — no `# noqa`/`# type: ignore` additions).
5. Final sweep of `tracer-tooling-friction.md`, `tracer-approach.md`, `tracer-design-decisions.md`
   — confirm all decisions/observations from T001–T008 are recorded (append, never recreate).

**Files**: tracer files only, plus fixes to owned files if the gate self-check surfaces an
issue.

**Validation**: SC-006 diff-scope check passes cleanly; gate-set self-check has no unresolved
❌; tracer files are complete and internally consistent with the actual git history.

## Definition of Done

- T001's baseline is captured and recorded, before any production-code change.
- T002's red-first test is committed as its own commit, before any production-code commit, and
  was witnessed to fail pre-fix (T007) and pass post-fix.
- T003's four signature edits and three call-site edits are complete, all typed
  `_PackContextLike | None` (never the concrete `PackContext` class, never under
  `TYPE_CHECKING`) — C-008 satisfied.
- `MissionTypeRepository._load()` (line 157–174, call site line 165) is untouched — FR-005/C-001
  satisfied.
- `charter/pack_manager.py:865` is untouched — FR-008 satisfied.
- T004's golden-parity extension passes, correctly scoped to "unrelated org pack" parity, not
  an overbroad "no org pack can ever affect a built-in type" claim.
- T005's project-tier acceptance-scenario-5 case exists as its own named test and passes.
- T006 confirms the explicit-`action_sequence` fallback (FR-006) is unaffected.
- T007's stash/rerun/stash-pop sequence was actually performed and both runs are recorded in a
  tracer file (not merely asserted).
- T008's full targeted-suite run is clean, with any red individually triaged against the T001
  baseline — no mission-introduced red remains.
- T009's SC-006 diff-scope check confirms the diff touches only C-007's three named files plus
  this mission's own `kitty-specs/mission-types-empty-action-sequence-01M0RMCA/**` bookkeeping.
- Per-subtask completion is recorded via `spec-kitty agent tasks mark-status <Txxx> --status
  done` (event-sourced), not a ticked checkbox in this file.

## Risks

- **Built-in-equivalent layer receiving a real `pack_context` for the first time**: previously
  this layer's own projection was always effectively unthreaded (since
  `_inject_projected_fields` hardcoded `None` regardless of what was passed down). Post-fix, a
  built-in type whose steps are genuinely overridden by an *active* org/project pack could see a
  *different*, correctly-layered `action_sequence`. This is the **intended** fix, not a
  regression — but it is exactly the place T004's golden-parity test must be precise about
  scope ("unrelated org pack" parity, not "any org pack" parity). Misreading this risk as a bug
  and trying to suppress it would itself be the bug.
- **Cache staleness is unrelated and pre-existing**: `resolve_layered_mission_types`'s
  `functools.cache` does not detect on-disk edits to an already-cached org/project YAML after
  first resolution for that key — this is documented, accepted, pre-existing behavior
  (`TestLayeredMissionTypesCacheKeyAndClear.test_same_key_is_a_cache_hit` already pins it). Do
  not "fix" this as part of this WP; it is out of scope (NFR-003 only requires the cache key
  itself stays correctly keyed, which this WP's argument-threading does not change).
- **Scope creep into `_load()`'s near-duplicated validation logic**: plan.md's Campsite-clean
  section identifies real duplication between `_load()` and `_load_layered_mission_type_file`
  but explicitly declines to fold it (would touch `_load()`'s cache-safety-sensitive body,
  becoming a fifth touched function under C-007). Do not "clean this up while you're in there" —
  it is flagged for a future, separately-scoped mission.

## Reviewer Guidance

- Confirm all four functions type `pack_context` as `_PackContextLike | None` — grep for any
  stray `PackContext` (the concrete class) import into `mission_type_repository.py`; there
  should be none, not even under `TYPE_CHECKING`.
- Confirm `MissionTypeRepository._load()` (lines 157–174) has zero diff.
- Confirm `charter/pack_manager.py` has zero diff.
- Confirm the red-first test (T002) is in a separate commit from the production fix (T003), in
  that order, per `git log`.
- Confirm the tracer files actually contain the stash/rerun/stash-pop transcript (T007) — a
  claim without the recorded transcript is not sufficient per SC-004's own "not merely asserted"
  requirement.
- Confirm `git diff --name-only` against the mission's base is exactly C-007's three files plus
  `kitty-specs/mission-types-empty-action-sequence-01M0RMCA/**` — nothing else.
- Confirm T004's golden-parity test is scoped to "unrelated org pack," not an overbroad claim
  that would break the first time a legitimate override pack is introduced.

Run implementation via: `spec-kitty agent action implement WP01 --agent claude`
