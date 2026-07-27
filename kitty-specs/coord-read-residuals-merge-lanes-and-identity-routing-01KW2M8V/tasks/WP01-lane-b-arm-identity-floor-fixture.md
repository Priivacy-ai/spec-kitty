---
work_package_id: WP01
title: Lane B — Call-shape arm + identity routing + canonicalizer floor + shared divergent fixture
dependencies: []
requirement_refs:
- C-003
- FR-004
- FR-005
- FR-007
- FR-009
- FR-010
- NFR-002
tracker_refs:
- '#2186'
planning_base_branch: mission/coord-read-residuals-2185-2186
merge_target_branch: mission/coord-read-residuals-2185-2186
branch_strategy: Planning artifacts for this mission were generated on mission/coord-read-residuals-2185-2186. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/coord-read-residuals-2185-2186 unless the human explicitly redirects the landing branch.
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
phase: Phase 1 - Lane B (self-contained foundation)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "922219"
history:
- at: '2026-06-27T11:00:00Z'
  actor: system
  action: Prompt regenerated via /spec-kitty.tasks (canonical regeneration from corrected spec/plan)
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/integration/test_identity_coord_read.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_gate_read_literal_ban.py
- tests/architectural/test_resolution_authority_gates.py
- tests/integration/coord_topology_fixture.py
- tests/integration/test_identity_coord_read.py
- src/specify_cli/cli/commands/next_cmd.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/agent/workflow.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Lane B — Call-shape arm + identity routing + floor + shared fixture

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer) before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

- The read gate gains a **call-shape arm** covering BOTH shapes the literal vocabulary cannot see: (a) **identity** — `resolve_mission_identity(dir)`/`get_mission_type(dir)`, scope `cli/commands/` **+ `agent_utils/status.py`** (so the `show_kanban_status` `:132` identity read is statically gated, not orphaned); and (b) **lanes.json** — `read_lanes_json(dir)`/`require_lanes_json(dir)`, scope `merge/`+`lanes/`+`core/worktree_topology.py` — whose `dir` is bound from a coord-aware resolver (`resolve_feature_dir_for_mission`/`candidate_feature_dir_for_mission`/`resolve_feature_dir_for_slug`) without a primary fold. Committed synthetic-AST non-vacuity self-test for **both** shapes (pre-fix snippet flagged, routed snippet not).
- The genuinely-owned #2186 identity sites (`next_cmd.py`, `implement.py`, `workflow.py` owned legs) route onto PRIMARY (`primary_feature_dir_for_mission` + `_canonicalize_primary_read_handle`, or `resolve_planning_read_dir`). **Arm + remediation co-land in this WP** (gate-unmask-cannot-self-validate).
- **WP01 owns the shared divergent-fixture extension (T001)** — every consumer (T009 here + WP02/WP03 per-site tests + WP04) imports ONE divergence definition.
- On the divergent fixture, lifecycle records carry the PRIMARY `mission_id` and `get_mission_type` returns the PRIMARY type.
- `ROUTED_CANONICALIZER_FLOOR` recomputed from the before/after census; **if seam-routing did not move the census, state that plainly** (no re-pinned-integer "gain").
- **No merge/lanes/core #2185 pin exists or is drained here** — that cluster is vocabulary-blind; the only ratchet-visible drain in the mission is #2187 (WP03/T021).

> **Ownership note (Directive 003):** the `agent_utils/status.py:132` identity read (a #2186 site) is **routed in WP03** (T021), not here — it shares the `show_kanban_status` function with the #2187 `:126` `tasks/` drain, so single-file ownership keeps it in WP03. This WP does **not** edit `agent_utils/status.py`; it only adds the FR-007 identity arm whose scope **includes** `agent_utils/status.py`, statically gating that `:132` leg.

## Context & Constraints

- Spec [spec.md](../spec.md) (US2, US3; FR-004/005/007/009/010; Lane B table), [plan.md](../plan.md) IC-01/IC-05, [research.md](../research.md).
- **C-002**: consume the resolver seam; do not edit `_read_path_resolver` internals; never remove `candidate_feature_dir_for_mission` (C-005 STATUS primitive).
- **C-003**: identity routing matches the implement-loop seam model — handle-blind primitive + caller-side canonicalization; no silent fallback.
- **C-009-mirror**: touch only the OWNED `workflow.py` identity legs — never the implement-loop ROUTE legs. T004 produces the authoritative ownership table FIRST.
- **C-SEQ**: re-resolve `workflow.py`/`implement.py`/`next_cmd.py` citations against post-implement-loop-merge `main` (the sibling rewrites those functions). Lane B's arm is net-new, so this WP is otherwise not blocked on the sibling.
- **NFR-002**: ambiguous/coord-deleted handles keep the structured hard-fail (`MissionSelectorAmbiguous`, #1848) — no new best-effort swallow.

## Branch Strategy

- **Planning base branch**: `mission/coord-read-residuals-2185-2186`
- **Merge target branch**: `mission/coord-read-residuals-2185-2186`

## Subtasks & Detailed Guidance

### T001 – Shared divergent-fixture extension (FOUNDATIONAL — do first)
- **File**: `tests/integration/coord_topology_fixture.py`. **Reuse** the merged sibling's already-divergent husk (STATUS-only: no `tasks/`/`lanes.json`/`meta.json`; primary has `lanes.json`+`tasks/`+a decoy events file, resolved primary `mission_id = 01KW2E7AFC0000000000000001`). **ADD a sentinel-husk-meta variant** (distinct fixture/parametrization) that **writes** a husk `meta.json` that is **present-but-wrong**: `mission_id = "6KERGF2ZNFBPR91YEZMARG99KS"` (26-char sentinel ULID) ≠ the fixture's actual resolved PRIMARY id, with `lanes.json`+`tasks/` seeded PRIMARY-only. This **OVERRIDES the base invariant `assert not (coord_mission_dir / "meta.json").exists()`** — making the identity proof a *silent-wrong-value*, not a missing-file.
- **HARD precondition (the triad)**, asserted before any routed-path drive: `assert not (coord_husk / "lanes.json").exists()`, `assert not (coord_husk / "tasks").exists()`, and `assert <husk meta mission_id> == "6KERGF2ZNFBPR91YEZMARG99KS"` **and `!= ctx.mission_id`** (bind to the fixture's actual resolved primary id — NOT a hard-coded `01KW2M8V…` literal).
- **Do NOT** retrofit `write_side/topology_fixtures.py::build_coord` (non-divergent husk mirrors primary, ~26 consumers). Define divergence in ONE place; T009/T016/T022/T023 import it.

### T002 – Call-shape scan arm (lanes.json + identity)
- **File**: `tests/architectural/test_gate_read_literal_ban.py`. Add an `ast.Call` arm covering **two shapes**: (a) `resolve_mission_identity`/`get_mission_type` (scope `cli/commands/` **+ `agent_utils/status.py`**); (b) `read_lanes_json`/`require_lanes_json` (scope `merge/`+`lanes/`+`core/worktree_topology.py`). Flag a call whose first arg is a `Name` bound (in the same function) from a coord-aware resolver (`resolve_feature_dir_for_mission`/`candidate_feature_dir_for_mission`/`resolve_feature_dir_for_slug`) and NOT passed through `_canonicalize_primary_read_handle`/`primary_feature_dir_for_mission`/`resolve_planning_read_dir`. Keep each shape's scope bounded so it does not red-CI on out-of-scope strangers (`sync/`, `acceptance/`, `policy/`, `orchestrator_api/` — follow-on).

### T003 – Non-vacuity self-test (both shapes) [P]
- Mandatory synthetic-AST self-test for **BOTH** shapes: a pre-fix snippet (coord-aware → identity read; coord-aware → lanes.json read) is flagged; the routed snippet is not. Mirror the existing gate self-test pattern so the arm's teeth are an automated regression, not a manual ritual.

### T004 – ROUTE/KEEP ownership table
- Produce a definitive per-site table: every Lane B site → ROUTE / KEEP / owned-by-implement-loop, cross-checked against the sibling's actual ROUTE+KEEP list and re-resolved on merged main. **No site left in the gap between the two missions** (FR-005). Record it in this WP's notes / the mission's data-model so review can verify completeness.

### T005 – Route `next_cmd.py:187/:253`
- Primary-anchor the `resolve_mission_identity` reads so the lifecycle `started`/`completed` records are written on coord topology (no silent swallow). (Citations `:187`/`:253` are exact on merged main.)

### T006 – Route `next_cmd.py:619` *(was `:631` pre-merge)*
- `get_mission_type` via primary fold → fixes **wrong-run-type routing** (`get_or_start_run` no longer starts with the default `software-dev` type on a husk miss).

### T007 – Route `implement.py:1394` + owned `workflow.py` legs *(citations re-resolved on merged main)*
- `implement.py:1394` (was `:1389`): give it its OWN primary anchor (do not rely on the `:1018` fallback — C-EXCL-FALLBACK guards so the fallback can be retired later). `workflow.py:1282`/`:2739` (were `:1274`/`:2732`) are clean standalone anchors; `:1644` (was `:1636`) is a **shared-variable** site needing its OWN anchored variable (NOT a `feature_dir` re-point). **Re-confirm all citations before editing** (C-SEQ). NFR-004: no primary-dir stub.

### T008 – Floor recompute (honest)
- Record the before/after canonicalizer census **and** the explicit list of newly-added DIRECT `primary_feature_dir_for_mission(_canonicalize_primary_read_handle(...))` call sites; set `ROUTED_CANONICALIZER_FLOOR` = after-census − MARGIN in `test_resolution_authority_gates.py` (current floor 31, MARGIN 4, live 35 on the merged base — re-measure). **If the routed sites call the `resolve_planning_read_dir` seam (not the primitive directly), the census does NOT move — state plainly the floor did not move and adds no new protection; do NOT re-pin the same integer as a gain.**

### T009 – RED-first identity tests
- On the divergent fixture (T001; sentinel husk meta ≠ PRIMARY), assert each routed site returns the PRIMARY id/type **on a returned domain value** (the resolved `mission_id` / mission type), NOT a resolved-path equality and NOT the fixture's `assert_reads_primary`/`assert_both_legs` helpers. Reverting a routed read to coord-aware surfaces the sentinel/default and FAILS the test. Restate NFR-004 inline: no primary-dir stub.

## Test Strategy

- Arm self-test for both shapes (T003) + per-site RED-first identity tests (T009) on the divergent fixture (T001). `ruff` + `mypy` clean; touched functions ≤ 15.

## Definition of Done

- T001 fixture variant present with the HARD triad precondition; one divergence definition.
- Arm (both shapes) committed with non-vacuity self-tests; arm scope bounded (no stranger red-CI).
- `next_cmd.py`/`implement.py`/`workflow.py` owned identity legs routed onto PRIMARY; ownership table complete.
- Floor recomputed honestly (or recorded as un-moved with rationale).
- RED-first identity tests pass GREEN after routing and FAIL on revert (returned domain value).
- `ruff` + `mypy` clean on all touched files.

## Risks & Mitigations

- Arm scope creep → red-CI on strangers. Keep identity scope to `cli/commands/` + `agent_utils/status.py` and lanes.json scope to `merge/`+`lanes/`+`core/worktree_topology.py`.
- A site in the gap between the two missions → the T004 table accounts for every site.
- Fixture-divergence drift → T001 defines divergence in ONE place; all consumers import it.

## Review Guidance

- Reviewer (`reviewer-renata`): verify the arm has teeth (self-test, both shapes), the ownership table is complete, no implement-loop ROUTE leg touched, the floor is strictly-below census (or honestly recorded as un-moved), and the identity tests assert returned domain values (not path equality).

## Activity Log

- 2026-06-27T11:00:00Z – system – Prompt regenerated (canonical /spec-kitty.tasks from corrected spec/plan).
- 2026-06-27T09:08:14Z – claude:opus:python-pedro:implementer – shell_pid=839051 – Assigned agent via action command
- 2026-06-27T09:52:29Z – claude:opus:python-pedro:implementer – shell_pid=839051 – WP01 foundation: dual-shape arm + sentinel-divergent fixture + Lane B identity routing + floor honesty; 64 gate tests + 550 arch pass
- 2026-06-27T09:52:48Z – claude:opus:reviewer-renata:reviewer – shell_pid=922219 – Started review via action command
- 2026-06-27T10:04:10Z – user – shell_pid=922219 – Review passed (reviewer-renata): C-001 verified legitimate shrink (not #2155 re-opener); arm live teeth; floor census genuinely moved; RED-first falsification proven; 64 tests + 550 arch pass
