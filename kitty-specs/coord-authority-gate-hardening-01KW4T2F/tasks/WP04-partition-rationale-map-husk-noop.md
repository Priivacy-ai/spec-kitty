---
work_package_id: WP04
title: Partition-stability rationale map + check_pre30_layout husk no-op
dependencies: []
requirement_refs:
- FR-006
- FR-007
tracker_refs: []
planning_base_branch: feat/coord-authority-gate-hardening
merge_target_branch: feat/coord-authority-gate-hardening
branch_strategy: Planning artifacts for this mission were generated on feat/coord-authority-gate-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/coord-authority-gate-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
phase: Phase 2 - Partition & husk coverage
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1877733"
history:
- at: '2026-06-27T15:59:26Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_write_surface_placement_guard.py
create_intent:
- tests/integration/test_pre30_layout_coord_husk_noop.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_write_surface_placement_guard.py
- tests/integration/coord_topology_fixture.py
- tests/integration/test_pre30_layout_coord_husk_noop.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Partition-stability rationale map + check_pre30_layout husk no-op

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks (```python`, ```bash`).

---

## Objectives & Success Criteria

Two independent, fully-parallel coverage additions:

- **FR-006 — partition-stability rationale map (#2198, net-new only).** Add a machine-read `PARTITION_RATIONALE: dict[MissionArtifactKind, (partition, rationale, load_bearing_consumer)]` cross-checked against the live `_PRIMARY_ARTIFACT_KINDS` / `_PLACEMENT_ARTIFACT_KINDS` frozensets, so re-homing a kind across the partition is a conscious CI-red decision.
- **FR-007 — husk no-op coverage (#2199).** Assert `check_pre30_layout` is a clean no-op against (a) a production-shaped STATUS-only husk and (b) a `tasks/`-present-but-non-legacy husk variant.

**This WP is fully parallel** — no dependency on WP01–WP03. It owns its own husk fixture variant (single consumer, no contention).

**Done means:**
- `PARTITION_RATIONALE` exists with one entry per `MissionArtifactKind` member; missing entry → RED (T014).
- The map's derived PRIMARY/STATUS split `==` the live frozensets; an all-load-bearing-kinds parametrized anti-mutant fires on re-home (T015). **No line-pins** (NFR-005).
- The `tasks/`-present-non-legacy husk fixture variant is added (T016).
- `check_pre30_layout` is a verified no-op against both husk shapes (T017).

## Context & Constraints

- **Design docs**: [spec.md](../spec.md) (FR-006, FR-007, SC-003, SC-004, C-004, NFR-005), [data-model.md](../data-model.md) §6 (partition + rationale map), §7 (fixtures), [contracts/gate-hardening-contracts.md](../contracts/gate-hardening-contracts.md) Contracts C + D.3.
- **The live partition** (`src/mission_runtime/artifacts.py`): `MissionArtifactKind` (14 members); `_PRIMARY_ARTIFACT_KINDS` (~:90) and `_PLACEMENT_ARTIFACT_KINDS` (~:112) partition it exactly once (exhaustive + disjoint — already asserted). Read these from `artifacts.py`; do NOT redefine them.
- **Net-new only (NFR-005 / C-004).** Exhaustive + disjoint + a SPEC anti-mutant already exist in `test_write_surface_placement_guard.py::test_full_partition_resolves_per_membership` (~:278). FR-006 is **verify-and-annotate**: the value is the machine-read rationale map + the all-kinds anti-mutant. Add NO line-pins; keep allowlist-free (CT7 exemplar). The real resolver `resolve_placement_only` (~:45 import) is already driven by the existing test — reuse it.
- **FR-007 must use the PRODUCTION-shaped husk (real status payload), not an empty dir.** An empty dir short-circuits `is_legacy_format` identically and proves nothing. `check_pre30_layout` lives in `src/specify_cli/upgrade/pre30_guard.py` (~:30); `is_legacy_format` / `LEGACY_LANE_DIRS` in `src/specify_cli/upgrade/legacy_detector.py` (LEGACY_LANE_DIRS = `["planned","doing","for_review","done"]`).
- **Fixture ownership (single consumer — no contention).** SC-002 (WP03) uses the EXISTING `coord_topology_mission` fixture read-only; the `tasks/`-present-non-legacy husk variant is consumed ONLY by FR-007(b), so **WP04 owns and adds it** to `coord_topology_fixture.py`. WP03 does NOT edit that file, so there is no overlap.
- **CT7 (NFR-001/NFR-002)**: content-anchor via `composite_key` where applicable; zero new `file.py:NNN` keys; the map keys on enum members (content-anchored).

## Branch Strategy

- **Strategy**: lane-based (allocated from `lanes.json` after finalize-tasks)
- **Planning base branch**: feat/coord-authority-gate-hardening
- **Merge target branch**: feat/coord-authority-gate-hardening

> Execution worktrees are allocated per computed lane from `lanes.json`. Do not change these fields manually.

## Subtasks & Detailed Guidance

### Subtask T014 – FR-006: add the machine-read `PARTITION_RATIONALE` map

- **Purpose**: A per-kind rationale that pins WHY each artifact kind sits where it does, machine-cross-checkable against the live frozensets.
- **Steps**:
  1. In `test_write_surface_placement_guard.py`, define `PARTITION_RATIONALE: dict[MissionArtifactKind, tuple[str, str, str]]` mapping every kind → `(partition, rationale, load_bearing_consumer)`. `partition` is `"PRIMARY"` / `"COORD"` (or reuse a small enum/Literal); `rationale` and `load_bearing_consumer` are short strings citing why.
  2. Source the kind list from `MissionArtifactKind` (iterate the enum) so a newly-added kind without an entry is detectable.
- **Files**: `tests/architectural/test_write_surface_placement_guard.py`
- **Notes**: Per [data-model.md §6], the current split is PRIMARY = {SPEC, DATA_MODEL, RESEARCH, CHECKLIST, FINALIZED_EXECUTION_PLAN, TASKS_INDEX, WORK_PACKAGE_TASK, LANE_STATE, PRIMARY_METADATA, RETROSPECTIVE}; COORD = {ACCEPTANCE_MATRIX, ISSUE_MATRIX, STATUS_STATE, ANALYSIS_REPORT}. Verify against `artifacts.py` at implementation time (the enum has 14 members).

### Subtask T015 – FR-006: exhaustive + split-equality + all-kinds anti-mutant

- **Purpose**: Turn re-homing a kind into a conscious CI-red decision (SC-003).
- **Steps**:
  1. **(a) Exhaustive**: assert every `MissionArtifactKind` member has a `PARTITION_RATIONALE` entry (missing → RED).
  2. **(b) Split equality**: assert the map's derived PRIMARY/COORD split `==` the live `_PRIMARY_ARTIFACT_KINDS` / `_PLACEMENT_ARTIFACT_KINDS` (re-home a kind in the frozensets without editing its rationale → RED).
  3. **(c) All-kinds anti-mutant**: parametrize across ALL load-bearing kinds (not just SPEC) — for each kind, forcing it into the opposite partition makes its `resolve_placement_only(...).ref` assertion go RED. Reuse the existing test's resolver-driving pattern.
  4. Run `PWHEADLESS=1 pytest tests/architectural/test_write_surface_placement_guard.py -q`.
- **Files**: `tests/architectural/test_write_surface_placement_guard.py`
- **Notes**: Net-new only — do not weaken or duplicate `test_full_partition_resolves_per_membership`; add the map + the broadened anti-mutant alongside it. No line-pins.
- **NON-FAKEABLE DoD (squad HIGH — extend, do not copy-paste)**: "reuse the existing resolver-driving pattern" means *factor and reuse* the resolver-driving helper, NOT copy `test_full_partition_resolves_per_membership`'s body into a new all-kinds function. A duplicate that mirrors the existing test body is "net-new" in name only and adds maintenance friction (NFR-005). The diff should show a small parametrized addition that drives `resolve_placement_only` over all load-bearing kinds, reusing the existing test's machinery — not a cloned function.

### Subtask T016 – FR-007: add the `tasks/`-present-non-legacy husk fixture variant

- **Purpose**: Exercise the `LEGACY_LANE_DIRS`/`.md` branch of `is_legacy_format` (a coord husk carrying a post-3.0 `tasks/` with WP `.md` files but no `planned/doing/...` lane subdirs).
- **Steps**:
  1. In `tests/integration/coord_topology_fixture.py`, add a fixture (mirroring `coord_topology_mission`) whose **coord husk** carries a post-3.0 `tasks/` (at least one `WPxx.md`, no `planned`/`doing`/`for_review`/`done` subdirs) alongside the real `status.events.jsonl` + `meta.json`.
  2. Follow the existing fixture's production-shaped construction (real git + filesystem state, realistic ids — see [[feedback_realistic_test_data]]); reuse helpers like `assert_reads_primary` / `assert_status_from_coord` if relevant.
- **Files**: `tests/integration/coord_topology_fixture.py`
- **Notes**: WP04 is the **sole** consumer of this variant (FR-007(b)). Do not touch the existing `coord_topology_mission` / `coord_topology_mission_sentinel_meta` fixtures beyond what's needed to add the new one.

### Subtask T017 – FR-007: `check_pre30_layout` no-op test against both husk shapes

- **Purpose**: Prove `check_pre30_layout` is a clean no-op on the realistic coord-husk shapes (SC-004).
- **Steps**:
  1. Create `tests/integration/test_pre30_layout_coord_husk_noop.py`.
  2. **(a)** Against the **existing** `coord_topology_mission` fixture's production-shaped STATUS-only husk (real `status.events.jsonl` + `meta.json`, no `tasks/`), assert `check_pre30_layout(husk_dir)` is a clean no-op (no raise / no mutation).
  3. **(b)** Against the T016 `tasks/`-present-non-legacy variant, assert `check_pre30_layout` is still a clean no-op (exercises the `LEGACY_LANE_DIRS`/`.md` branch in `is_legacy_format`).
  4. Make explicit that this is NOT an empty dir (which short-circuits identically and proves nothing) — assert the husk actually carries status payload.
  5. Run `PWHEADLESS=1 pytest tests/integration/test_pre30_layout_coord_husk_noop.py -q`.
- **Files**: `tests/integration/test_pre30_layout_coord_husk_noop.py`
- **Notes**: `check_pre30_layout` returns `None` on the no-op path — assert it does not raise and leaves the tree unchanged.
- **NON-FAKEABLE DoD (squad HIGH — prove "no mutation", not just "no raise")**: a test that only asserts no-exception proves nothing about no-op semantics. Snapshot the husk tree before the call (`before = set(husk_dir.rglob("*"))`), call `check_pre30_layout(husk_dir)`, then assert `set(husk_dir.rglob("*")) == before` AND that the call returned/raised nothing. Both halves (a) and (b) must carry the snapshot assertion.

## Test Strategy

- Tests REQUIRED. Run: `PWHEADLESS=1 pytest tests/architectural/test_write_surface_placement_guard.py tests/integration/test_pre30_layout_coord_husk_noop.py -q`.
- Confirm the full `tests/architectural/` suite stays green.
- Ruff + mypy clean on all touched files.

## Risks & Mitigations

- **Empty-dir trap (FR-007)**: an empty dir short-circuits `is_legacy_format` and proves nothing. **Mitigation**: use the production-shaped husk with real status payload; assert the payload is present.
- **Line-pin creep (NFR-005)**: adding `file:line` anchors to the partition guard. **Mitigation**: key the map on enum members; reuse the resolver-driven anti-mutant; add no line-pins.
- **Fixture contention**: editing the shared fixture file could collide with WP03. **Mitigation**: WP03 only reads the existing fixture; WP04 only ADDS a new variant — verify the existing fixtures are untouched in the diff.

## Review Guidance

- Confirm `PARTITION_RATIONALE` is exhaustive (drop an entry → RED) and its split equals the live frozensets (re-home in the frozensets without editing rationale → RED).
- Confirm the anti-mutant is parametrized across ALL load-bearing kinds, not just SPEC.
- Confirm FR-007 uses the production-shaped husk (real status payload), and both no-op assertions genuinely exercise distinct `is_legacy_format` branches.
- Confirm no new `file.py:NNN` anchors and no line-pins; ruff/mypy clean.

## Activity Log

- 2026-06-27T15:59:26Z – system – Prompt created.
- 2026-06-27T17:00:33Z – claude:opus:python-pedro:implementer – shell_pid=1827836 – Assigned agent via action command
- 2026-06-27T17:19:37Z – claude:opus:python-pedro:implementer – shell_pid=1827836 – FR-006 PARTITION_RATIONALE map (exhaustive+split-equality+all-kinds anti-mutant, net-new, no line-pins) + FR-007 tasks-husk fixture variant & check_pre30_layout no-op (no-raise+no-mutation, both husk shapes). Targeted+full tests/architectural/ green (1 unrelated pre-existing .worktrees-path failure in test_pytest_marker_convention). ruff+mypy exit 0 on changed files.
- 2026-06-27T17:20:11Z – claude:opus:reviewer-renata:reviewer – shell_pid=1877733 – Started review via action command
- 2026-06-27T17:25:52Z – user – shell_pid=1877733 – Review passed: FR-006 PARTITION_RATIONALE net-new (factored _patch_partition/_placement_ref helpers reused by all-kinds anti-mutant; existing test_full_partition_resolves_per_membership untouched); exhaustive==enum + derived split==live frozensets + parametrized all-kinds anti-mutant flips resolved ref via REAL resolve_placement_only. FR-007 production husk (real status payload asserted, not empty dir) with rglob before/after no-mutation proof on BOTH shapes exercising distinct is_legacy_format branches. CT7-clean (no .py:NNN, enum-keyed), no line-pins, conftest edits additive-only, existing fixtures untouched (builder gained additive write_husk_tasks flag). 23 passed; ruff+mypy clean. Pre-existing marker-convention failure confirmed .worktrees-path artifact (passes from primary repo, untouched by diff).
