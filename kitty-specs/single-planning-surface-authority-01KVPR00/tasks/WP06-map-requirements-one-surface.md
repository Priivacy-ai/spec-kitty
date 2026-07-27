---
work_package_id: WP06
title: map-requirements and finalize-tasks share one WP-frontmatter surface
dependencies:
- WP05
requirement_refs:
- FR-008
tracker_refs:
- "2064"
- "2069"
planning_base_branch: feat/single-planning-surface-authority
merge_target_branch: feat/single-planning-surface-authority
branch_strategy: Planning artifacts for this mission were generated on feat/single-planning-surface-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-planning-surface-authority unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "600113"
history:
- Created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/tasks.py
create_intent:
- tests/specify_cli/test_requirement_mapping_coord_surface.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks.py
role: implementer
tags: []
---

## Profile load (REQUIRED, do this first)

Adopt **python-pedro** (implementer) before touching code. Load the profile from
its doctrine YAML (`.kittify/doctrine/.../python-pedro` or via the governed
`spec-kitty agent` surface) — load the *profile*, not just the persona name —
and apply its identity, governance scope, boundaries, and initialization
declaration. python-pedro is implementer-only; do not self-review (reviews go to
reviewer-renata).

If the profile cannot be loaded, STOP and surface the gap — do not improvise an
implementer identity.

## Objective

Make `map-requirements` and `finalize-tasks` read/write WP `requirement_refs`
through the **same seam-resolved surface** so that a successful
`map-requirements` is immediately visible to the following
`finalize-tasks --validate-only` (zero `unmapped_functional_requirements`). This
is the **#2064 read-surface desync**: the two commands currently resolve the WP
`tasks/` directory through *different* read-path entry points, so on a
coord-topology (or flattened) mission they can disagree about where the WP
frontmatter lives.

**Scope is FR-008 only**, bounded to the read-surface consolidation in the file
you own (`cli/commands/agent/tasks.py`). Two explicit scope guards:

- **Do NOT chase the coverage math.** `compute_coverage`
  (`src/specify_cli/requirement_mapping.py:61`) is already single-source and is
  consumed by both surfaces unchanged. This WP touches *where the WP dir is
  resolved*, not *how coverage is computed*.
- **Do NOT touch `mission.py`.** WP05 owns the `mission.py` finalize read region
  and linearizes it first. You depend on WP05. You consolidate only the
  `tasks.py` read surface to consume the same seam-resolved directory WP05 has
  already settled.

## Context (verified ground truth — cite before editing)

Read `cli/commands/agent/tasks.py` and confirm these line numbers/symbols before
editing (they drift — re-verify against the live file):

**The desync, verified:**

- `map_requirements` (`@app.command(name="map-requirements")` at **:3519**,
  `def map_requirements` at **:3520**) resolves its read surface at **:3633**:
  ```python
  feature_dir = resolve_feature_dir_for_slug(main_repo_root, mission_slug)
  ```
  and derives `tasks_dir = feature_dir / "tasks"` at **:3680**. It then reads WP
  frontmatter via `read_all_wp_raw_requirement_refs(tasks_dir)` (**:3784**) and
  `read_all_wp_requirement_refs(tasks_dir)` (**:3816**), then
  `compute_coverage(all_wp_refs, functional_ids)` (**:3817**).

- `finalize_tasks` (`@app.command(name="finalize-tasks")` at **:3299**,
  `def finalize_tasks` at **:3300**) — the sibling in the SAME file — resolves
  its read surface at **:3329**:
  ```python
  feature_dir = resolve_feature_dir_for_mission(main_repo_root, mission_slug)
  ```
  and derives `tasks_dir = feature_dir / "tasks"` at **:3331**.

  **NOTE — two `finalize_tasks` exist:** there is also a `finalize_tasks` in
  `cli/commands/agent/mission.py:2665` (the mission.py finalize read region owned
  by WP05). You do NOT edit that. The desync you fix is between
  `tasks.py::map_requirements` and the `tasks.py::finalize_tasks` it is paired
  with (plus the mission.py finalize WP05 settles). The unifying constraint:
  every command in `tasks.py` resolves the WP dir through **one** resolver.

**The root of the split (verified):** the two resolvers route through *different*
seam entry points (`src/specify_cli/missions/_read_path_resolver.py`):

- `resolve_feature_dir_for_slug` (**:937**) → `_resolve_mission_read_path(...)`.
- `resolve_feature_dir_for_mission` (**:959**) → `resolve_action_context(action="tasks", ...)`.

`map_requirements` is the **only** read path in `tasks.py` still on
`resolve_feature_dir_for_slug`; every other command (`finalize_tasks` :3329,
`list_tasks` :3161/:3167, `mark_status`, `move_task`, `_resolve_wp_slug` :1013
which uses `candidate_feature_dir_for_mission`, etc.) is on
`resolve_feature_dir_for_mission`. That single divergent call is the #2064
read-surface split: on a coord/flattened mission the two entry points can return
different `tasks/` dirs, so `map-requirements` writes to one and finalize reads
the other → spurious `unmapped_functional_requirements`.

**Seam dependency (WP05):** by the time WP06 runs, WP05 has linearized the
mission.py finalize read region and the structural read path (WP04/FR-006)
resolves from the stored `MissionTopology`. WP06's job is to make `tasks.py`'s
`map-requirements` read surface consume the **same** seam-resolved directory the
rest of `tasks.py` (and WP05's finalize) already use — one resolver, not two.

**The `.kind is COORDINATION` decision site (FR-005, this WP's share):** at
**:359** inside `_review_currency_check_branch`:
```python
if placement.kind is CommitTargetKind.COORDINATION:
    return placement.ref
```
`placement` comes from `resolve_placement_only(main_repo_root, mission_slug)` at
**:354**. FR-005 spans multiple WPs; the `tasks.py:359` site belongs to WP06
because WP06 owns `tasks.py`. Route it through WP01's
`routes_through_coordination` predicate (`mission_runtime.context`) instead of
reading `.kind` directly. Behavior MUST be identical:
`routes_through_coordination(placement)` is `True` exactly when
`placement.kind is CommitTargetKind.COORDINATION` today. Do NOT delete the
`CommitTargetKind` type (that is Mission B / C-007) — only stop *reading `.kind`
to decide* at this one site.

**Documented invariant (honor it):** planning INPUT artifacts (`spec.md`, WP
frontmatter) are authored on **PRIMARY** and staged to coord at commit-time. Note
`map_requirements` already reads `spec.md` from `primary_dir` (`primary_feature_dir_for_mission`,
**:3634** / **:3640**). This WP does NOT change spec.md placement; it consolidates
only the WP `tasks/` read surface so the WP-frontmatter read agrees with finalize.

## Subtasks

### T031 — Consolidate the WP-dir read surface to one resolver
Replace the lone `resolve_feature_dir_for_slug` call in `map_requirements`
(**:3633**) so the WP `tasks/` directory is resolved through the **same**
seam-resolved entry point `finalize_tasks` (and the rest of `tasks.py`) use —
`resolve_feature_dir_for_mission` (the `resolve_action_context(action="tasks")`
seam) — OR, if WP04/WP05 have introduced a single canonical
`tasks.py`-internal helper for the WP read dir, route through that helper. The
goal is a **demonstrably single** read-surface function for the WP `tasks/` dir
shared by `map-requirements` and `finalize-tasks`. After this change, `grep` for
`resolve_feature_dir_for_slug` in `tasks.py` must show map_requirements no longer
the odd one out (or zero call sites if no other consumer remains).

Keep the `spec.md` read on `primary_dir` (PRIMARY-input invariant) untouched —
only the WP `tasks/` dir resolution changes. Verify `tasks_dir = feature_dir / "tasks"`
(**:3680**) now derives from the unified resolver, and `all_wp_raw` (**:3784**),
`all_wp_refs` (**:3816**), and the `tasks_dir.glob(...)` write loop (**:3749**)
all see the same directory finalize reads.

### T032 — Route the `.kind is COORDINATION` site through the predicate (FR-005)
Replace the `placement.kind is CommitTargetKind.COORDINATION` read at **:359**
(`_review_currency_check_branch`) with WP01's
`routes_through_coordination(placement)` predicate imported from
`mission_runtime` (mirror the existing `from mission_runtime import ...` at
**:60**). Behavior-identical: same branch taken in the same cases. Do not delete
`CommitTargetKind` or its `CommitTarget` construction elsewhere in the file
(`CommitTarget(ref=..., kind=CommitTargetKind.PRIMARY)` at **:3614** stays — only
the **read of `.kind` to decide** is replaced).

### T033 — Non-fakeable regression test: map → finalize agree on a coord topology
Add a focused test in a **new** file beside the existing requirement-mapping
tests — `tests/specify_cli/test_requirement_mapping_coord_surface.py` (declared in
this WP's `create_intent`; mirrors the location of
`tests/specify_cli/test_requirement_mapping.py`). If you extend the existing
`test_requirement_mapping.py` instead, that is fine — drop the new file from
`create_intent` so the frontmatter stays honest. The test reproduces the #2064
desync and proves it is gone:

1. Build a **coord-topology** mission fixture (stored topology `COORD` /
   `LANES_WITH_COORD`, i.e. a mission with a coordination worktree) using
   production-shaped identifiers (full 26-char ULID `mission_id`, real
   `<slug>-<mid8>` form) — NOT a handcrafted short slug. Reuse the mission /
   coord fixtures the seam WPs (WP04/WP05) introduce; do not hand-roll a parallel
   topology fixture.
2. Run `map-requirements` (CLI/typer invocation or the `map_requirements`
   function) to map every functional requirement so coverage is full.
3. Immediately run `finalize-tasks --validate-only` against the SAME mission and
   assert the result reports **zero** `unmapped_functional_requirements` (and the
   command does not fail with a "Tasks directory not found" divergence).
4. **Prove the red precondition — a comment is NOT proof.** The test MUST
   demonstrate the bug is real, not merely assert it. A "confirm by
   reasoning/comment that the divergent `resolve_feature_dir_for_slug` path is
   what the test exercises" is **explicitly INSUFFICIENT**: the test could pass on
   the post-fix tree *and also* pass on `main` (e.g. the fixture's two resolvers
   happen to return the same dir, or the assertion degrades into a
   coverage-number check in disguise). Satisfy this with **one** of:

   - **(a) Structural divergence assertion (preferred).** Assert that on the
     coord-topology fixture the two read surfaces — `map-requirements`'
     `read_all_wp_requirement_refs(tasks_dir)` source dir (the
     `resolve_feature_dir_for_slug` path) vs the `tasks.py` finalize dir
     resolution (the `resolve_feature_dir_for_mission` /
     `resolve_action_context(action="tasks")` path) — return **DIFFERENT** `Path`
     objects when computed via the **PRE-fix resolver pair**, and the **SAME**
     `Path` after T031 unifies them. This pins the precondition that makes #2064
     real: if the two resolvers ever return the same dir for this fixture, the
     test is not exercising the bug and must fail loudly. (Compute the pre-fix
     pair directly from the resolver functions on the fixture — you do not need
     `main` checked out to assert they diverge for this topology.)
   - **(b) Witnessed pre-fix failing run.** Run the regression test against the
     pre-WP06 tree (or against `map_requirements` still wired to
     `resolve_feature_dir_for_slug`), capture the actual FAILURE output, and paste
     it into the review notes as red→green evidence. A reasoned claim is not a
     witnessed run.

   After the precondition is established, assert `map_requirements` and the
   `tasks.py` finalize resolve to the **same** `tasks/` Path post-T031 (one read
   surface), not only an end-to-end coverage number, so the test cannot pass by an
   unrelated coverage shortcut.

This is the FR-008 / SC-005 non-fakeable gate. A test asserting only that
`compute_coverage` returns full coverage in isolation is INSUFFICIENT (coverage
math was never the bug). The test MUST exercise the cross-command directory
agreement on a coord/flattened mission AND demonstrate the divergent-Path
precondition (a) or a witnessed red run (b) — a bare comment does not satisfy the
gate.

### T034 — Predicate-routing test + static gates (NFR-004)
Add/extend a unit test proving `_review_currency_check_branch` returns
`placement.ref` exactly when `routes_through_coordination(placement)` is true and
the `target_branch` fallback otherwise — directly exercising the T032 branch (do
not rely solely on an integration path). Then run `ruff check .` and `mypy` on
the changed file with **zero** new issues/warnings; keep cyclomatic complexity
≤15 (extract a small helper if the consolidation pushes `map_requirements` over);
hoist any literal that now appears ≥3× (no new S1192). No `# noqa` / `# type: ignore`.

## Branch Strategy

Planning artifacts for this mission were generated on
`feat/single-planning-surface-authority`. During `/spec-kitty.implement` this WP
may branch from a dependency-specific base (it depends on WP05, so its base
includes WP05's linearized `mission.py` finalize read region and the WP04/WP05
seam adoption). Completed changes merge back into
`feat/single-planning-surface-authority` unless the human explicitly redirects
the landing branch. Never push to `origin/main`; share only via a PR branch on
explicit operator instruction.

## Definition of Done (non-fakeable)

- [ ] `map_requirements` resolves the WP `tasks/` directory through the **same**
      seam-resolved read surface as `finalize_tasks` (in `tasks.py`); the
      divergent `resolve_feature_dir_for_slug` call at the old :3633 is gone, and
      `grep` shows `map-requirements` no longer uses a different WP-dir resolver
      than the rest of `tasks.py`. The read surface is **demonstrably one
      function** (cite the unified call site in the PR).
- [ ] The `spec.md` PRIMARY-input read is unchanged (still via `primary_dir` /
      `primary_feature_dir_for_mission`) — the invariant is preserved.
- [ ] `compute_coverage` is untouched (scope guard honored — no coverage-math edits).
- [ ] The `.kind is COORDINATION` site (old :359) reads through
      `routes_through_coordination(placement)`, not `placement.kind is …`;
      behavior identical; `CommitTargetKind` type NOT deleted.
- [ ] **T033 live-evidence test exists and is non-fakeable:** a coord-topology
      mission where `map-requirements` (full coverage) is immediately followed by
      `finalize-tasks --validate-only` reporting **zero**
      `unmapped_functional_requirements`; the test exercises the cross-command
      directory agreement (#2064 witnessed), uses production-shaped IDs, and
      would have failed pre-WP06.
- [ ] T032 branch is covered by a focused unit test (T034).
- [ ] `ruff` + `mypy` clean on `tasks.py` (zero new issues/warnings); complexity
      ≤15; no new S1192; no suppressions added (NFR-004).
- [ ] `mission.py` is NOT touched (WP05 owns the finalize read region there).
- [ ] #1970 campsite: only touched lines cleaned; no opportunistic edits beyond
      the consolidated read surface and the predicate site.

## Risks

1. **Behavioral skew between the two resolvers.** `resolve_feature_dir_for_slug`
   (no existence assertion) and `resolve_feature_dir_for_mission` (raises on
   missing, via `resolve_action_context`) differ in error semantics.
   `map_requirements` already guards `if not feature_dir.exists()` (**:3636**) and
   `if not spec_md.exists()` (**:3641**), so switching to the
   asserting/`resolve_action_context` path could change the *error class* on a
   missing dir. Preserve `map-requirements`' existing user-facing error
   (`Mission directory not found: …`) — wrap/translate if the unified resolver
   raises a different typed error so the message contract is unchanged.
2. **Coord-window / coord-deleted transients (C-006).** The unified resolver must
   still honor the create-window (#1718) and coord-deleted (#1848) probe
   semantics that WP04/WP05 preserve. Do NOT add a disk-`stat` inference of your
   own; consume the seam. Keep `CoordinationBranchDeleted` / typed errors intact.
3. **WP05 linearization dependency.** If WP05's mission.py finalize edits change
   the canonical resolver name/signature, align to whatever WP05 settled rather
   than introducing a third resolver. If WP05 is not yet merged into your base,
   STOP — do not pre-empt the linearized chain.
4. **Predicate import cycle.** `routes_through_coordination` lives in
   `mission_runtime.context`; mirror the existing top-level
   `from mission_runtime import …` import (**:60**) and confirm no new import
   cycle (`tasks.py` already imports from `mission_runtime`).

## Reviewer Guidance (reviewer-renata)

- Confirm there is now exactly **one** WP `tasks/`-dir read resolver shared by
  `tasks.py::map_requirements` and `tasks.py::finalize_tasks` — diff the old
  :3633 `resolve_feature_dir_for_slug` line and verify it routes through the same
  seam as :3329. Reject if `map-requirements` still resolves the WP dir
  independently.
- Verify the #2064 test is a **real cross-command** repro on a coord-topology
  mission (production-shaped IDs), not a `compute_coverage`-only assertion, and
  that it would fail on the pre-WP06 code (ask for the red→green evidence).
- Verify the `.kind is COORDINATION` site is routed through
  `routes_through_coordination` with identical behavior and `CommitTargetKind` is
  NOT deleted (that is Mission B).
- Verify `spec.md` PRIMARY-input placement and `compute_coverage` are untouched,
  `mission.py` is untouched, and `ruff`/`mypy` are clean with no suppressions.
- Incorrect doc paths / fabricated line citations are **blocking**, not warnings.

## Activity Log

- 2026-06-22T17:10:37Z – claude:opus:python-pedro:implementer – shell_pid=574851 – Assigned agent via action command
- 2026-06-22T17:20:59Z – claude:opus:python-pedro:implementer – shell_pid=574851 – FR-008 #2064 fix: map_requirements now resolves the WP tasks/ dir via _map_requirements_feature_dir -> resolve_feature_dir_for_mission (the resolve_action_context(action=tasks) seam finalize uses); the divergent resolve_feature_dir_for_slug call site is gone. spec.md PRIMARY-input read + compute_coverage untouched. FR-005: tasks.py:359 .kind-is-COORDINATION read routed through routes_through_coordination(placement); CommitTargetKind preserved. T033 non-fakeable: structural divergence test (pre-fix resolvers return DIFFERENT Paths on coord topology, unified agree) + WITNESSED pre-fix red run -- agreement test fails when divergent resolver restored: map=.../kitty-specs/<slug> vs finalize=.../.worktrees/<slug>-01KVPR00-coord/kitty-specs/<slug>-01KVPR00. 5/5 new tests pass; requirement_mapping 28/28. ruff exit 0, mypy no issues, complexity OK. Forced from PRIMARY: tasks.py byte-identical between lane base and feat (empty diff).
- 2026-06-22T17:26:42Z – claude:opus:reviewer-renata:reviewer – shell_pid=600113 – Started review via action command
- 2026-06-22T17:31:40Z – user – shell_pid=600113 – FR-008/#2064 read-surface consolidated (map_requirements -> resolve_feature_dir_for_mission seam, divergent resolve_feature_dir_for_slug gone); FR-005/#2069 .kind read routed via routes_through_coordination (CommitTargetKind preserved). T033 non-fakeability RED reproduced independently (restored divergent resolver -> agreement test failed map=PRIMARY vs finalize=COORD). Risk#1 error-message preserved. ruff/mypy clean, complexity<=15, no suppressions, mission.py untouched, compute_coverage untouched. 5/5 new + 23 existing tests green.
