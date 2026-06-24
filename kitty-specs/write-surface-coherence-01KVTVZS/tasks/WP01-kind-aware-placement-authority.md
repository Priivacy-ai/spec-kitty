---
work_package_id: WP01
title: Kind-aware placement authority + re-partition
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-004
- FR-010
tracker_refs: []
planning_base_branch: feat/write-surface-coherence
merge_target_branch: feat/write-surface-coherence
branch_strategy: Planning artifacts for this mission were generated on feat/write-surface-coherence. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-surface-coherence unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Placement authority
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2550877"
history:
- at: '2026-06-23T19:28:09Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/mission_runtime/artifacts.py
- src/mission_runtime/resolution.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Kind-aware placement authority + re-partition

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: src/mission_runtime/`.

---

## Objective

Make the **write-side** placement consult the existing `MissionArtifactKind` model
(the read side already does) and **re-partition** the planning + identity kinds onto
the primary `target_branch` for every topology shape. Introduce a
`_PRIMARY_ARTIFACT_KINDS` frozenset — the **single swappable locus** (NFR-004) — and
make `artifact_home_for` and `resolve_placement_only` route those kinds to primary.

This is the foundation: WP02–WP06 converge their write sites onto the partition this
WP establishes. **Do NOT add any migration logic** (FR-010 / C-003 — forward-only).

## Context & Constraints

Ground truth — read before editing:
- [spec.md](../spec.md) FR-001, FR-002, FR-004, NFR-003, NFR-004; [data-model.md](../data-model.md) "The swappable locus (NFR-004)"; [contracts/placement-bifurcation.md](../contracts/placement-bifurcation.md) G-1/G-5.
- [plan.md](../plan.md) IC-01.

The asymmetry (data-model.md): the **read** side is kind-aware via
`artifact_home_for(kind)` (`src/mission_runtime/artifacts.py:115-138`); the **write**
side (`resolve_placement_only`, `src/mission_runtime/resolution.py:1013-1106`) is
**kind-BLIND** — it routes purely by stored topology
(`_assemble_core_fragments` at `resolution.py:963-969`, which reads
`routes_through_coordination(topology)` and returns the coord ref for ALL artifacts).

Current partition (`artifacts.py:78-93`): `_PLACEMENT_ARTIFACT_KINDS` contains every
kind except `PRIMARY_METADATA`. We move the planning + identity kinds OUT to a new
`_PRIMARY_ARTIFACT_KINDS` so read and write agree (INV-5 full symmetry).

**Negative scope**: no migration logic, no reconciliation of already-split missions
(C-003). No new CLI command/flag (NFR-003 — the kind is an internal Python parameter).

## Branch Strategy

- **Strategy**: `shared-lane`
- **Planning base branch**: `feat/write-surface-coherence`
- **Merge target branch**: `feat/write-surface-coherence`

> `lanes.json` (written at finalize-tasks) governs the actual lane. WP02/WP05 share
> `commit_router.py`/`mission.py` surfaces with later WPs — overlaps are intentional
> and serialized by the dependency order (WP01 has no deps).

## Subtasks & Detailed Guidance

### Subtask T001 – Add `_PRIMARY_ARTIFACT_KINDS`; re-partition

- **Purpose**: Establish the single swappable partition (NFR-004).
- **Files**: `src/mission_runtime/artifacts.py`.
- **Steps**:
  1. Add a module-level frozenset above `_PLACEMENT_ARTIFACT_KINDS` (currently
     `artifacts.py:78-93`):
     ```python
     _PRIMARY_ARTIFACT_KINDS: frozenset[MissionArtifactKind] = frozenset(
         {
             MissionArtifactKind.SPEC,
             MissionArtifactKind.DATA_MODEL,
             MissionArtifactKind.RESEARCH,
             MissionArtifactKind.CHECKLIST,
             MissionArtifactKind.FINALIZED_EXECUTION_PLAN,
             MissionArtifactKind.TASKS_INDEX,
             MissionArtifactKind.WORK_PACKAGE_TASK,
             MissionArtifactKind.LANE_STATE,
             MissionArtifactKind.PRIMARY_METADATA,
         }
     )
     ```
  2. Remove those members (except `PRIMARY_METADATA`, which is never in
     `_PLACEMENT_ARTIFACT_KINDS`) from `_PLACEMENT_ARTIFACT_KINDS`, leaving only the
     COORD-partition kinds: `STATUS_STATE`, `ISSUE_MATRIX`, `ACCEPTANCE_MATRIX`,
     `ANALYSIS_REPORT`.
- **Notes**: `kind_is_coordination_residue` (`artifacts.py:57-75`) reads
  `_PLACEMENT_ARTIFACT_KINDS`. After the move, SPEC/DATA_MODEL/RESEARCH/CHECKLIST are
  **no longer coordination residue** — this is the correctness change. WP05 confirms
  the residue dirty-filter downstream; do NOT special-case it here.

### Subtask T002 – `artifact_home_for` routes primary kinds → primary

- **Purpose**: The read/write/commit home for a primary kind is the primary surface.
- **Files**: `src/mission_runtime/artifacts.py` (`artifact_home_for`, 115-138).
- **Steps**:
  1. Before the `_PLACEMENT_ARTIFACT_KINDS` branch, add a primary-kind branch:
     ```python
     if kind in _PRIMARY_ARTIFACT_KINDS:
         return MissionArtifactHome(
             kind=kind,
             read_surface="primary",
             write_surface="primary",
             commit_target=placement_ref,   # the primary target_branch ref the caller resolved
             ignores_primary_coord_residue=False,
         )
     ```
     `PRIMARY_METADATA` already returns a primary home (120-127) with
     `commit_target=None`. **Keep its existing arm VERBATIM** (`commit_target=None`)
     and add the new primary-kind branch AFTER it (do NOT fold the two arms — folding
     risks flipping `PRIMARY_METADATA` to a `commit_target=placement_ref` and breaking
     the read-anchored, never-committed-through-a-ref metadata contract). The new branch
     applies only to the other `_PRIMARY_ARTIFACT_KINDS` members.
- **Notes**: The returned `MissionArtifactHome` SHAPE and the `artifact_home_for`
  signature are unchanged (NFR-004 / G-5) — only WHICH surface/ref a primary kind
  carries changes. Callers stay blind to membership. `meta.json` itself needs NO
  partition/residue-map edit — `PRIMARY_METADATA` is already primary; only the
  write-caller (WP02 acceptance, `acceptance/__init__.py:1398`) changes to commit it
  on primary.

### Subtask T003 – `resolve_placement_only` becomes kind-aware

- **Purpose**: The planning-commit placement projection must route a primary kind to
  the primary `target_branch`, not the coordination ref.
- **Files**: `src/mission_runtime/resolution.py` (`resolve_placement_only`, 1013-1106).
- **Steps**:
  1. Add a **REQUIRED** keyword parameter (NO default):
     `def resolve_placement_only(repo_root, mission_slug, *, kind: MissionArtifactKind)`.
     **There is NO default kind** (operator decision). Rationale: a default would
     silently flip every un-threaded caller coord→primary the moment WP01 lands; a
     required param forces all 7 call sites (WP02/WP03) to declare intent atomically
     and makes the convergence a compile-time enumeration (the missing caller fails to
     import/typecheck rather than mis-routing at runtime).
  2. After `_assemble_core_fragments` returns `branch_ref` (1094), branch on the kind:
     - primary kind → return `CommitTarget(ref=target_branch)` (the primary ref already
       resolved at 1092 via `get_feature_target_branch`).
     - else → return `branch_ref.destination_ref` (the existing coord-vs-primary value).
  3. Keep the import-late style and the canonicalization block (1070-1083) unchanged.
- **Notes**: This is an **internal seam** change (NFR-003) — `resolve_placement_only`
  is imported by `commit_router`, `safe_commit_cmd`, `orchestrator_api` (two sites),
  `status_transition` (status), `tasks.py`, and `mission.py`. Making `kind` required
  **intentionally breaks the no-kind call signature** at all 7 sites — this WP only
  updates the resolver itself; WP02/WP03 thread the kind at every site. Expect a
  red typecheck/import across those callers until WP02/WP03 land (serialized by deps).
- **DoD (DECISION 1)**: `kind` is a REQUIRED keyword param. A `python -c` import of
  `resolve_placement_only` plus a test confirm that calling it **without** `kind`
  raises `TypeError` (not a silent default). The unit test in T005 must include this
  no-kind → `TypeError` assertion.

### Subtask T004 – Confirm partition membership of the three flagged kinds

- **Purpose**: Resolve the data-model.md "† confirm in tasks" markers.
- **Files**: `src/mission_runtime/artifacts.py` (membership only).
- **Steps**:
  1. `LANE_STATE` (`lanes.json`, finalize output, travels with `tasks.md`) → **PRIMARY**
     (placed in `_PRIMARY_ARTIFACT_KINDS` in T001).
  2. `ACCEPTANCE_MATRIX` (accept-time verification) → **COORD** (stays in
     `_PLACEMENT_ARTIFACT_KINDS`).
  3. `ANALYSIS_REPORT` (record-analysis) → **COORD** (stays).
  4. Add a one-line code comment next to each set citing FR-004 / data-model.md so the
     membership rationale is discoverable.
- **Notes**: The mechanism is unaffected by where these three land — only the frozenset
  membership differs (NFR-004). If a reviewer disputes a placement, it is a one-line
  move, not a code change.

### Subtask T005 – Red-first partition unit tests (DIRECTIVE_034)

- **Purpose**: Prove the bifurcation at the lowest level, red-first.
- **Files**: a new `tests/mission_runtime/test_artifact_partition.py` (or the nearest
  existing `tests/mission_runtime/` module — locate it; do not create a parallel tree).
- **Steps (red-first — DIRECTIVE_034)**:
  1. Write the failing test FIRST through the **pre-existing entry point**
     (`artifact_home_for` and `resolve_placement_only`), asserting:
     - `artifact_home_for(SPEC, placement_ref)` → `write_surface == "primary"`.
     - `resolve_placement_only(repo, slug, kind=SPEC)` on a **coord-topology fixture**
       → `ref == target_branch` (NOT the coordination branch).
     - `resolve_placement_only(repo, slug, kind=STATUS_STATE)` on the same fixture
       → `ref == coordination_branch`.
     - A **flattened** fixture: both kinds → `target_branch` (unchanged).
     - **Required-param (DECISION 1)**: `resolve_placement_only(repo, slug)` with NO
       `kind` raises `TypeError` (assert via `pytest.raises(TypeError)`). This pins the
       no-silent-default contract.
  2. Prove red: stash the `artifacts.py` + `resolution.py` edits (or run against a clean
     checkout of those two files) and confirm the SPEC→`target_branch` assertion FAILS
     (pre-fix it resolves coord). Restore and confirm green.
  3. Use realistic fixture data: a real 26-char ULID `mission_id`, real 8-char `mid8`,
     real-shaped `<slug>-<mid8>` dir — NEVER a short fake slug.

## Test Strategy

- `pytest tests/mission_runtime/test_artifact_partition.py -q` (or the located module).
- New branches/helpers MUST have tests in this WP (Sonar new-code coverage).
- `ruff check src/mission_runtime/ && mypy src/mission_runtime/` — zero issues, zero
  warnings, no suppressions.

## Risks & Mitigations

- **Shared resolver, status caller**: `resolve_placement_only` also serves the STATUS
  caller (`status_transition.py:332`). Mitigation: `kind` is REQUIRED (no default), so
  the status caller MUST pass `STATUS_STATE` explicitly (WP02 owns that edit) — it stays
  coord under coord topology (C-001). This WP leaves the 7 callers red until WP02/WP03
  thread the kind; that is the intended compile-time-enumeration behavior of DECISION 1.
- **`PRIMARY_METADATA` double-handling**: keep its existing `commit_target=None` arm to
  avoid changing the metadata read-anchor contract.
- **Residue meaning shift**: SPEC/etc. stop being coord residue — intended; WP05 confirms
  the dirty-filter. Do NOT patch the filter here.

## Review Guidance

- The partition is ONE frozenset; flipping a kind is a one-line move (NFR-004) — verify
  the `artifact_home_for` signature and returned shapes are unchanged, and that
  `resolve_placement_only` gained a **required** `kind` keyword (NOT a defaulted one).
- Verify the no-kind → `TypeError` test exists and passes (DECISION 1 contract).
- Verify the `PRIMARY_METADATA` arm is unchanged (`commit_target=None`) — not folded.
- Verify the red-first test genuinely failed pre-fix (ask for the red-run evidence).
- Verify NO migration logic was added (C-003).

## Activity Log

- 2026-06-23T19:28:09Z – system – Prompt created.
- 2026-06-23T20:11:09Z – claude:opus:python-pedro:implementer – shell_pid=2536173 – Assigned agent via action command
- 2026-06-23T20:23:20Z – claude:opus:python-pedro:implementer – shell_pid=2536173 – Kind-aware authority + partition; kind required (no default); red-first test green. _PRIMARY_ARTIFACT_KINDS frozenset added; planning+identity kinds moved to primary; COORD set = ISSUE_MATRIX/STATUS_STATE/ANALYSIS_REPORT/ACCEPTANCE_MATRIX. artifact_home_for primary-kind branch added AFTER verbatim PRIMARY_METADATA arm (commit_target=None kept). resolve_placement_only gained REQUIRED keyword 'kind' (no default); callers threaded in WP02/WP03 (intended type-break). RED-FIRST PROOF (pre-fix): test_artifact_home_for_spec_is_primary -> AssertionError 'placement'=='primary'; kind= call -> TypeError unexpected kwarg; no-kind call -> DID NOT RAISE. Post-fix: 7/7 new green, 65/65 mission_runtime green. ruff check (src/mission_runtime/artifacts.py resolution.py + tests/mission_runtime/) exit=0 'All checks passed'. mypy src/mission_runtime/artifacts.py resolution.py: 'Success: no issues'. SCOPE NOTE: edited 4 existing mission_runtime tests to thread now-required kind + reflect overturned residue contract; guard emitted advisory ACTIVE_WP_SCOPE_VIOLATION warnings (non-blocking). CONFLICT FLAGGED: test_artifact_home.py (landed 2026-06-23 by mission 01KVRJ6P) asserted spec.md/plan.md ARE coord residue; WP01 partition makes them PRIMARY -> overturned per T001 note; WP05 confirms downstream dirty-filter per prompt Risks.
- 2026-06-23T20:24:11Z – claude:opus:reviewer-renata:reviewer – shell_pid=2550877 – Started review via action command
- 2026-06-23T20:34:07Z – user – shell_pid=2550877 – Review passed (reviewer-renata; dirs 001/024/030/032/041). Re-ran tests MYSELF: 65/65 mission_runtime green; 7/7 new partition green; ruff All-checks-passed; mypy Success. RED-FIRST VERIFIED (revert+restore): pre-fix new test 5-failed/2-passed via PRE-EXISTING surface (SPEC home placement!=primary; no-kind DID NOT RAISE), unchanged-behavior 2 stayed green. INVARIANTS: _PRIMARY=9 / _PLACEMENT=4 coord zero-overlap; kind REQUIRED no-default; PRIMARY_METADATA arm verbatim commit_target=None then primary branch AFTER. RESIDUE-OVERTURN correct: 01KVRJ6P residue tests overturned to NOT-residue DRIVEN by partition; re-pointing PRESERVES path-residue+isolation (delete-assertion-not-test honored). 4 edits=legit kind-threading w/ STATUS_STATE parity-preserving. No migration (C-003); only 2 owned src. NIT: stale residue_path docstring -> WP05. Matrix: #2099/#1878/#2062 in-mission; #2100/#1891/#2085 deferred-with-followup.
