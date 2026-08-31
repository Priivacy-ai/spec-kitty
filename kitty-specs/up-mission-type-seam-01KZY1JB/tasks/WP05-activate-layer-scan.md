---
work_package_id: WP05
title: charter activate mission-type scans org and project layers (flat, non-recursive)
dependencies:
- WP02
requirement_refs:
- C-003
- FR-003
- FR-005
- NFR-002
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
phase: Phase 3 - Activation layer scan (IC-03+IC-04, runs concurrently with WP03/WP04)
assignee: ''
agent: claude
history:
- at: '2026-08-13T00:00:00Z'
  actor: system
  action: Prompt generated during /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/pack_manager.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/charter/pack_manager.py
- tests/charter/test_pack_manager.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – charter activate mission-type scans org and project layers (flat, non-recursive)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` and behave according to its guidance
before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

`_scan_layout_for(None)` (`src/charter/pack_manager.py`, live-verify — plan.md cites `227-229`)
returns `("missions/mission_types", "*.yaml", False)` — `layered=False` — and
`_resolve_layer_candidate` (live-verify — plan.md cites `256-317`) only resolves a directory for
`layer == "built-in"` when `layered=False`; org and project layers fall through to `return None`.
This means `charter activate mission-type qa` can **never** find a non-built-in `qa` today.
Live-verify this by reading both functions' full bodies before making any change.

This WP combines two plan.md Implementation Concerns that are, per plan.md's own words, "one code
change, split here only for requirements traceability" — same file, same commit:

- **IC-03 (FR-003)**: add an explicit `kind is None` (mission-type) branch to
  `_resolve_layer_candidate` for `layer in ("org", "project")`, resolving to
  `<pack_root>/mission_types` (org) and `<repo_root>/.kittify/missions/mission_types` (project).
- **IC-04 (FR-005/CL-005)**: pin the project-layer location precisely at
  `.kittify/missions/mission_types/*.yaml`, scanned **non-recursively**, and confirm — not merely
  assert — this location has no live collision with the pre-existing
  `.kittify/missions/<mission_name>/` per-mission-instance directory convention.

**Success criteria**:

- `CharterPackManager.list_available(ctx, "mission-type", layer_roots=...)` includes a scratch
  org-pack's `"qa"` id post-fix (and — write the test to fail against the current code first —
  excludes it pre-fix).
- A scratch `.kittify/missions/mission_types/qa.yaml` resolves as a mission-type roster entry, not
  as a mission instance.
- `resolve_layer_roots` (`src/specify_cli/cli/commands/charter/_layer_roots.py`, live-verify —
  plan.md cites `10-36`) and `activate_cmd`
  (`src/specify_cli/cli/commands/charter/activate.py`, live-verify — plan.md cites lines
  `387,433,446`) already resolve and pass `layer_roots` generically for every kind including
  `"mission-type"` — **confirm this live and make NO change to either of those two files.** This
  WP is scoped entirely to `pack_manager.py`.

## Context & Constraints

- **This WP runs concurrently with WP03/WP04** — both this WP and WP03 depend only on WP02, and
  neither WP03 nor WP04 touches `pack_manager.py`. Confirm your `owned_files`
  (`src/charter/pack_manager.py`, `tests/charter/test_pack_manager.py`) stay disjoint from WP03's
  (`src/doctrine/missions/mission_type_repository.py`,
  `tests/doctrine/missions/test_mission_type_repository.py`,
  `tests/charter/test_charter_import_time_io.py`) and WP04's (`src/charter/mission_type_profiles.py`,
  `tests/charter/test_mission_type_profiles.py`, `tests/runtime/test_runtime_seam.py`). Per
  plan.md's own IC-03 note: "independent of IC-01/IC-02 per spec's own Q5 independence finding —
  `CharterPackManager.activate` validates purely against `available_ids`, no roster read." This WP
  does not need WP03's or WP04's factory to exist to do its own work.
- **The `rglob`-vs-`glob` trap is structurally neutralized, not fixed in code, by CL-005's own
  directory choice.** `list_available_detailed` (live-verify — plan.md cites `808-809`) uses
  `scan_dir.rglob(glob)` universally for every kind. `.kittify/missions/mission_types/` contains
  only flat `*.yaml` files with no per-type subdirectory (unlike the rejected
  `.kittify/doctrine/mission_types/<type>/governance-profile.yaml` shape), so `rglob("*.yaml")` and
  `glob("*.yaml")` are behaviorally identical there. **Do NOT change `rglob` to `glob` in
  `list_available_detailed`** — that would be an unrelated, broader-blast-radius change affecting
  every other charter-activatable kind, outside this mission's scope. Instead, write a regression
  test that proves the non-collision explicitly (T012) rather than relying on "obviously fine."
- **The real protection against the `.kittify/missions/mission_types/` vs
  `.kittify/missions/<mission_name>/` collision is pre-existing and structural, not a byproduct of
  this mission's own WP02 deletions.** `_mission_dir_if_valid`
  (`src/specify_cli/mission.py`, live-verify — plan.md cites `74-75`) only recognizes a
  subdirectory as a mission instance when it contains a file literally named `mission.yaml` — a
  roster directory of flat `*.yaml` files named after mission-type ids never satisfies that check,
  regardless of whether WP02's deleted `discover_missions()`/`list_cmd` still existed. State this
  in your test's docstring/comment so a future reader understands why the collision test passes
  even independent of WP02's deletions.
- **Terminology**: no `feature*` alias is introduced.

## Branch Strategy

- **Strategy**: Planning artifacts for this mission were generated on
  `kitty/mission-up-mission-type-seam-01KZY1JB`. During `/spec-kitty.implement` this WP may branch
  from a dependency-specific base, but completed changes must merge back into
  `kitty/mission-up-mission-type-seam-01KZY1JB` unless the human explicitly redirects the landing
  branch.
- **Planning base branch**: `kitty/mission-up-mission-type-seam-01KZY1JB`
- **Merge target branch**: `main`

## Subtasks & Detailed Guidance

### Subtask T011 – Add the org/project branch to `_resolve_layer_candidate` for `kind is None`

- **Purpose**: FR-003 — `charter activate mission-type <id>` must actually find a non-built-in
  `<id>`.
- **Steps**:
  1. Live-verify `_scan_layout_for(None)`'s return value and `_resolve_layer_candidate`'s full
     body, including exactly where it currently `return None`s for org/project layers.
  2. Add an explicit branch: for `kind is None` (mission-type) and `layer in ("org", "project")`,
     resolve to `<pack_root>/mission_types` (org) and `<repo_root>/.kittify/missions/mission_types`
     (project) respectively.
  3. Confirm `resolve_layer_roots` and `activate_cmd` need no change — they already resolve/pass
     `layer_roots` generically for every kind. If you find they DO need a change, STOP and report —
     that would mean this citation drifted since planning and needs a fresh look, not a silent
     workaround.
- **Files**: `src/charter/pack_manager.py`.
- **Parallel?**: Write test-first if practical (T012 constructs the fixture this depends on).

### Subtask T012 – Flat, non-recursive project-layer location + non-collision regression test

- **Purpose**: FR-005/CL-005 — pin the exact location and prove it structurally safe.
- **Steps**:
  1. Write a test constructing a scratch org pack with `mission_types/qa.yaml` and confirming
     `CharterPackManager.list_available(ctx, "mission-type", layer_roots=...)` includes `"qa"`
     post-fix — write this test to fail against the current (pre-T011) `_resolve_layer_candidate`
     body first, then confirm it passes after T011's fix.
  2. Write a test constructing a scratch `.kittify/missions/mission_types/qa.yaml` and confirming
     it resolves as a mission-type roster entry (via `list_available`), while a sibling
     `.kittify/missions/some-mission-instance/mission.yaml` (a real mission instance) is NOT
     misread as a mission-type roster entry, and `_mission_dir_if_valid` still correctly recognizes
     the latter as a mission instance and the former as not-a-mission-instance. This is the
     "confirm, not merely assert" requirement from IC-04.
  3. Add a one-line comment or docstring in the test explaining the `rglob`-vs-`glob` neutralization
     (why this location's flatness makes the trap moot here, without changing the general-purpose
     `list_available_detailed` code).
- **Files**: `src/charter/pack_manager.py` (if the location constant needs to be named/exported —
  check whether IC-03's branch already hardcodes the path inline, which is fine, or whether a
  named constant is cleaner; either is acceptable), `tests/charter/test_pack_manager.py`.
- **Parallel?**: Can proceed alongside T011; the two are one code change with two test angles.

## Test Strategy

- **Per-AC / per-SC**: User Story 1 AC1 ("the roster lookup resolves `qa` from the org layer" —
  this WP is what makes activation *find* `qa`; WP07 is what makes `charter mission-type list`
  *report* the correct layer for it). Spec.md's Edge Case "How does the system handle a
  project-layer `.kittify/missions/mission_types/` directory that does not exist at all?" — add a
  test confirming this resolves as "no project-layer contributions," not an error, not a crash,
  while org/built-in layers still resolve normally.
- **Test surface**: `tests/charter/test_pack_manager.py` (extended — this file already exists;
  confirm you are extending it, not creating a duplicate).
- **Commands**: `uv run pytest tests/charter/test_pack_manager.py -v`

## Risks & Mitigations

- **Risk**: reaching into `list_available_detailed` to "fix" the `rglob`/`glob` distinction as a
  side effect. **Mitigation**: explicit prohibition above — this is a materially larger,
  unrelated-blast-radius change outside this mission's scope; the flat CL-005 layout makes it
  structurally moot for this mission's own surface.
- **Risk**: the missing-project-layer-directory edge case is treated as an error rather than "no
  contributions." **Mitigation**: an explicit test for this edge case (Test Strategy above).
- **Risk**: file-collision with WP03/WP04 despite the concurrent-execution plan.
  **Mitigation**: `owned_files` disjointness is explicit in this WP's frontmatter and cross-checked
  in `wps.yaml`'s header comment; do not touch `mission_type_repository.py` or
  `mission_type_profiles.py` in this WP.

## Gate Set (this WP's Definition of Done)

- **`fast-tests-charter` + `integration-tests-charter`** (`--cov=charter --cov-fail-under=55`) —
  `pack_manager.py` is directly in scope.
- **`diff-coverage` (critical-path, 90%, `[ENFORCED]`)** over `src/charter/*`.
- **`arch-adversarial`** — must not regress any architectural gate.
- **`Typer 0.26 JSON error surface`, `patch() target validation`, `Bandit`, `pip-audit`,
  `commitlint`** — always-on in `lint`.
- `make lint` locally before handing off.

## Review Guidance

- Confirm `resolve_layer_roots` and `activate_cmd` were genuinely untouched — this WP's diff should
  be scoped entirely to `pack_manager.py` and its test file.
- Confirm the "before"/"after" framing of T012 step 1's test (excludes pre-fix, includes post-fix)
  is real, not merely asserted — ask the implementer to show the test failing against the
  pre-T011 code if not obvious from commit history.
- Confirm the non-collision test genuinely constructs both a mission-type roster file and a real
  mission-instance directory side by side, not just one or the other.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-13T00:00:00Z – system – Prompt created.
