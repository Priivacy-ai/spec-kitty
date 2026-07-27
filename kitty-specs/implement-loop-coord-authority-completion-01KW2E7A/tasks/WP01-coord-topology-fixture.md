---
work_package_id: WP01
title: Shared coord-topology test fixture
dependencies: []
requirement_refs:
- FR-014
- NFR-003
tracker_refs: []
planning_base_branch: design/coord-authority-remediation-2160
merge_target_branch: design/coord-authority-remediation-2160
branch_strategy: Planning artifacts for this mission were generated on design/coord-authority-remediation-2160. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/coord-authority-remediation-2160 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
phase: Phase 1 - Foundation
assignee: ''
agent: "claude:sonnet:python-pedro:implementer"
shell_pid: "3898818"
history:
- at: '2026-06-26T18:29:45Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/integration/
create_intent:
- tests/integration/coord_topology_fixture.py
- tests/integration/conftest_coord_topology.py
execution_mode: code_change
owned_files:
- tests/integration/coord_topology_fixture.py
- tests/integration/conftest_coord_topology.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Shared coord-topology test fixture

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

Build the **one shared, un-stubbed** test fixture every routing WP (WP03–WP06) uses to
prove the coord-topology read divergence is fixed. The fixture must reproduce the
**post-#2106** shape, which is latent on existing repo missions.

Done when:
- A fixture materializes a **coordination-topology** mission: real `meta.json` declaring
  the coord topology, a `-coord` worktree/husk carrying **STATUS only** (no `tasks/`, no
  `lanes.json`, no `meta.json`), and `tasks/WP*.md` + `lanes.json` on the **primary** surface.
- A parallel flat/single-branch materialization is available for the behavior-neutral leg.
- Dual-leg asserter helpers exist: `assert_reads_primary(...)` and
  `assert_status_from_coord(...)` so per-site tests assert BOTH legs in one call.
- A smoke test proves both topologies materialize and that a PRIMARY-kind read through a
  coord-aware resolver lands on the husk (the bug) while the seam lands on primary.
- **NO patching of the topology-resolution stack** anywhere in the fixture (FR-014).

## Context & Constraints

- Authoritative fact: the coord husk carries STATUS only — see `implement.py:1020-1028`.
- The anti-pattern to avoid is `tests/.../test_done_bookkeeping_seam.py:353`, which patches
  `candidate_feature_dir_for_mission` to a flat tmp dir and stubs the divergence away.
- Spec FR-014, NFR-003. Plan IC-06. Research.md "FR-008 sweep" for the artifact partition.
- This fixture is **used** by WP03–WP06 (they import it); they do **not** edit it.

## Branch Strategy

- **Strategy**: already-confirmed
- **Planning base branch**: design/coord-authority-remediation-2160
- **Merge target branch**: design/coord-authority-remediation-2160

Execution worktrees are allocated per computed lane from `lanes.json` after finalize-tasks.

## Subtasks & Detailed Guidance

### Subtask T001 – Build the coord-topology fixture
- **Purpose**: Materialize the post-#2106 coord shape without stubbing resolvers.
- **Steps**: Create a pytest fixture (`coord_topology_mission`) that: (1) inits a temp git
  repo + primary checkout; (2) creates a mission with `meta.json` declaring a coordination
  topology and a real `coordination_branch`; (3) writes `tasks/WP*.md` + `lanes.json` on
  primary; (4) materializes the `-coord` worktree carrying only `status.events.jsonl`/
  `status.json` (no planning artifacts). Reuse the real `CoordinationWorkspace`/worktree
  helpers — do not fake them.
- **Files**: `tests/integration/coord_topology_fixture.py`.
- **Notes**: Parameterize so a `flat_topology_mission` variant is available for neutrality tests.

### Subtask T002 – Dual-leg asserter helpers
- **Purpose**: Make per-site tests assert tasks-from-PRIMARY AND status-from-COORD in one place.
- **Steps**: `assert_reads_primary(resolved_path, fixture)` (resolved dir == primary mission
  dir, the WP files are present); `assert_status_from_coord(events_path, fixture)` —
  **(squad MED)** must assert the resolved status path **== the coord path** (or seed a
  differing primary-status decoy) so a wrong-leg read that finds nothing fails **loudly**,
  not merely "status readable". Provide a combined `assert_both_legs(...)`.
- **Files**: `tests/integration/coord_topology_fixture.py`.

### Subtask T003 – Fixture smoke test
- **Purpose**: Prove the fixture itself is correct before WPs depend on it.
- **Steps**: A test that (a) materializes both topologies; (b) shows a coord-aware resolver
  returns the husk (missing `tasks/`) under coord topology; (c) shows
  `resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)` returns primary; (d) confirms no
  resolver is patched.
- **Files**: `tests/integration/conftest_coord_topology.py` (registration) + smoke test.

## Test Strategy

This WP **is** test infrastructure. Run `PWHEADLESS=1 pytest tests/integration/ -k coord_topology -q`.
The smoke test is the acceptance gate; it must be green and stub-free.

## Risks & Mitigations

- **Stubbing creep** → the fixture silently green-washes downstream WPs. Mitigation: a
  meta-assertion / review check that no `monkeypatch`/`unittest.mock.patch` targets a
  topology resolver in the fixture module.
- **Real-port/daemon coupling** → keep the fixture filesystem+git only; run serial if it
  touches real ports.

## Review Guidance

- Verify zero patching of the resolution stack.
- Verify the husk truly lacks `tasks/`/`lanes.json`/`meta.json` and primary has them.
- Confirm the dual-leg asserters fail loudly on a wrong-surface read.

## Activity Log

- 2026-06-26T18:29:45Z – system – Prompt created.
- 2026-06-26T19:01:21Z – claude:sonnet:python-pedro:implementer – shell_pid=3898818 – Assigned agent via action command
- 2026-06-26T19:22:26Z – user – shell_pid=3898818 – Moved to planned
- 2026-06-26T19:24:06Z – user – shell_pid=3898818 – flat execution claim
- 2026-06-26T19:24:08Z – user – shell_pid=3898818 – flat execution; implementing on design branch
- 2026-06-26T19:42:25Z – claude:sonnet:python-pedro:implementer – shell_pid=3898818 – Fixture done (61b747071): 11/11 green, un-stubbed, decoy enforces resolved-path equality
- 2026-06-26T19:45:44Z – user – shell_pid=3898818 – reviewer-renata reviewing
- 2026-06-26T19:46:15Z – user – shell_pid=3898818 – Approved by reviewer-renata (flat execution). The review-cycle-1.md is a stale reset-feedback artifact (lane discarded due to stale base; re-implemented flat) — NOT a genuine rejection. Fixture re-built (61b747071), renata APPROVE: un-stubbed, decoy enforces resolved-path+content equality, both legs asserted, 11/11 green.
