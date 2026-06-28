---
work_package_id: WP03
title: Create-time topology choice
dependencies:
- WP02
requirement_refs:
- FR-004
- FR-005
tracker_refs: []
planning_base_branch: mission/lifecycle-tooling-friction
merge_target_branch: mission/lifecycle-tooling-friction
branch_strategy: Planning artifacts for this mission were generated on mission/lifecycle-tooling-friction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/lifecycle-tooling-friction unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
phase: Mission-Lifecycle Tooling Friction
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1908163"
history:
- at: '2026-06-27T00:00:00Z'
  actor: system
  action: Prompt created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/mission_creation.py
create_intent:
- tests/specify_cli/test_specify_topology_flag.py
execution_mode: code_change
owned_files:
- src/specify_cli/core/mission_creation.py
- src/specify_cli/cli/commands/lifecycle.py
- src/specify_cli/cli/commands/agent/mission_create.py
- src/specify_cli/missions/_create.py
- tests/specify_cli/test_specify_topology_flag.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Create-time topology choice

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile named in the frontmatter and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete.
- **Report progress**: update the Activity Log as you address each item.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``. Use language identifiers in code blocks: ` ```python `, ` ```bash `.

---

## Objectives & Success Criteria

- `spec-kitty specify <name> --topology <value>` lets the operator choose topology at creation, accepting **only** the 4 canonical `MissionTopology` enum values `single_branch | lanes | coord | lanes_with_coord` and rejecting any other value (notably NOT "flat").
- Coordination-branch minting (`ensure_coordination_branch`) is **conditional**: minted for `coord`/`lanes_with_coord`; skipped for `single_branch`/`lanes`.
- Omitting `--topology` defaults to `coord` and is **byte-identical** to today (meta + coord branch).
- A create-time `single_branch` mission completes `implement WP##` + `merge` end-to-end (the mandatory third-shape proof, T009).
- **SC-002** is satisfied. `ruff` + `mypy` clean; complexity ≤ 15.

## Context & Constraints

- Spec: [spec.md](../spec.md) — User Story 2, FR-004/005, SC-002, Edge Cases (`create-time lanes`, backward-compat).
- Plan: [plan.md](../plan.md) — IC-02.
- Research: [research.md](../research.md) — `core/mission_creation.py:416` unconditionally mints the coord branch → `:431` classifies COORD; the `classify_topology` SSOT is healthy; the defect is the unconditional mint. A create-time non-coord mission is a **third shape** the coord-or-legacy fallbacks across `implement.py`/merge must handle.
- **C-002 — canonical vocabulary**: the flag accepts ONLY the `MissionTopology` enum values; reuse the enum, do not introduce string aliases like "flat".
- **C-005 — depends on WP02 (load-bearing, not a preference)**: T009 claims TWO dependency-free WPs back-to-back under `auto_commit=False` in the `single_branch` mission — the second claim hits the first's uncommitted vcs-lock self-write, which without WP02's fix `Exit(1)`s. This concretely exercises WP02's dirty-tree-guard exclusion in the non-coord context, so `dependencies: [WP02]` is a real prerequisite, not a sequencing convenience.
- **NFR-001**: default-coord path byte-identical when the flag is omitted.
- **C-006**: red-first through `spec-kitty specify --json`. Persist the operator's explicit `MissionTopology` choice; do not hand-roll a NEW classifier. Note `classify_topology` can only corroborate `coord`/`single_branch` at create time — it cannot reproduce the `lanes` choice pre-`finalize-tasks`, so the stored enum is authoritative for the `lanes` case (see T008).

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

> Populated automatically by `spec-kitty agent mission tasks`. Do NOT edit manually.

## Subtasks & Detailed Guidance

### Subtask T007 – RED test: `--topology single_branch` + enum rejection

- **Purpose**: Reproduce #2218 through the pre-existing surface before wiring the flag.
- **Steps**:
  1. Create `tests/specify_cli/test_specify_topology_flag.py`.
  2. Assert `spec-kitty specify <name> --topology single_branch --json` yields `topology: single_branch` and NO `coordination_branch` in `meta.json`.
  3. Assert an invalid value (e.g. `--topology flat`) is rejected with a non-zero exit (enum validation).
  4. Confirm RED against current code (no `--topology` on `specify --help`).
- **Files**: `tests/specify_cli/test_specify_topology_flag.py` (new — in `owned_files` + `create_intent`).
- **Parallel?**: WP03 internal; the WP itself is sequenced after WP02.
- **Notes**: Use real-format mission names/ids (C-007).

### Subtask T008 – Thread `--topology` CLI→agent→core; conditional coord mint

- **Purpose**: Implement the flag end-to-end and make the coord-branch mint conditional.
- **Steps**:
  1. Add a `--topology` option (typed as the 4-value `MissionTopology` enum) to `specify` in `src/specify_cli/cli/commands/lifecycle.py`.
  2. Thread the chosen value through the agent layer (`src/specify_cli/cli/commands/agent/mission_create.py`) into core (`src/specify_cli/core/mission_creation.py` and `src/specify_cli/missions/_create.py`).
  3. In `mission_creation.py`, gate the `ensure_coordination_branch` mint on the topology: mint for `coord`/`lanes_with_coord`; skip for `single_branch`/`lanes`. **STORE the operator's explicit enum choice into meta directly** — do NOT re-derive it from `classify_topology`. At create time `classify_topology(None, has_lanes=False)` returns `single_branch` and CANNOT yield `lanes` (no `lanes.json` exists pre-`finalize-tasks`), so deriving the topology from the classifier would silently lose the operator's `lanes` choice. Use `classify_topology` only to **corroborate** the persisted value (e.g. assert `coord`/`single_branch` cases agree), never to re-derive the `lanes` case.
  4. Default to `coord` when the flag is omitted (backward-compat). Carry the value through `MissionCreationResult` (the dataclass at `core/mission_creation.py:40`, NOT "CreateMissionOutcome") if it surfaces topology.
- **Files**: `lifecycle.py`, `agent/mission_create.py`, `core/mission_creation.py`, `missions/_create.py`.
- **Parallel?**: After T007 red.
- **Notes**: Edge case — create-time `lanes` sets the `topology` field with no coord branch; `lanes.json` only materializes at `finalize-tasks`; `read_topology` must return `lanes` (because the explicit enum choice was stored, not re-classified). **DoD — extract the conditional-mint decision as a helper**: `create_mission_core` is large and un-waived (no `# noqa`), so hold complexity ≤ 15 by extracting the mint-or-skip decision into a small pure helper; add no new `# noqa` / `# type: ignore`.

### Subtask T009 – Mandatory end-to-end non-coord proof

- **Purpose**: Prove the create-time `single_branch` third shape survives the coord-or-legacy fallbacks across `implement`/`merge` (the hidden-depth risk, FR-005), AND genuinely exercises WP02's vcs-lock fix in the non-coord context.
- **Steps**:
  1. In the test file, create a `single_branch` mission with **TWO dependency-free WPs**, finalize tasks, then claim/`implement` **both WPs back-to-back under `auto_commit=False`** so the second claim hits the first claim's uncommitted vcs-lock self-write — this is the concrete exercise that makes WP02 load-bearing (without WP02's fix the second claim would `Exit(1)`). Then run `merge`.
  2. Replace any vague "completes coherently / no coord assumption fires" check with these FOUR observable post-merge assertions:
     - **(a)** the WP's actual file **content** is present on the merge-target branch after `merge` (read the merged file, assert its body — not just that the branch exists);
     - **(b)** the WP's **status event log reaches `done`/merged** via the lane reader (e.g. `lane_reader`/`materialize`), not a frontmatter peek;
     - **(c)** `read_topology(feature_dir) == single_branch` **AFTER** the full `specify → finalize → implement → merge` loop (the shape survives the loop, not just creation);
     - **(d)** **NO `coordination_branch` key was ever written** to `meta.json` at any point in the loop.
- **Files**: `tests/specify_cli/test_specify_topology_flag.py`.
- **Parallel?**: After T008.
- **Notes**: This is non-negotiable — a green `specify --json` does NOT prove the downstream implement/merge fallbacks handle the new shape. The two-WP back-to-back `auto_commit=False` claim is what makes `dependencies: [WP02]` load-bearing, not a sequencing preference.

### Subtask T010 – Regression: omitted flag = coord default byte-identical

- **Purpose**: Guard NFR-001.
- **Steps**:
  1. Assert that omitting `--topology` produces the same `meta.json` topology (`coord`) and mints the coord branch exactly as today.
- **Files**: `tests/specify_cli/test_specify_topology_flag.py`.
- **Parallel?**: After T008.
- **Notes**: Compare against a pre-change baseline shape.

## Test Strategy

- New test: `tests/specify_cli/test_specify_topology_flag.py`.
- Red-first via `spec-kitty specify --json`; T009 drives a full `specify → finalize → implement → merge` loop for a `single_branch` mission.
- Run: `PWHEADLESS=1 pytest tests/specify_cli/test_specify_topology_flag.py -q`. The implement/merge loop touches git — if it needs real ports/daemons, run that case with `-n0`.
- Realistic fixtures (C-007).

## Risks & Mitigations

- **HIDDEN-DEPTH**: the create-time non-coord shape is new to coord-or-legacy fallbacks — T009 e2e proof is mandatory; if a fallback site assumes a coord branch, fix it within the owned surfaces or escalate if it crosses into WP02's `implement.py` ownership.
- **Vocabulary drift**: only the 4 enum values; reject "flat" (C-002).
- **Default regression**: T010 guards byte-identical coord default (NFR-001).
- **Cross-file ownership**: this WP owns 4 source files plus the test — keep edits within them; the `implement.py` dirty-tree fix belongs to WP02.

## Review Guidance

- Confirm the flag accepts exactly the 4 enum values and rejects others.
- Confirm conditional mint (no coord branch for `single_branch`/`lanes`; coord branch for `coord`/`lanes_with_coord`).
- Confirm T009 runs implement + merge to completion for a `single_branch` mission with TWO back-to-back `auto_commit=False` claims, and that all four observable assertions hold: (a) merged file content present on the target branch, (b) status event log reaches `done`/merged via the lane reader, (c) `read_topology == single_branch` after the full loop, (d) no `coordination_branch` ever written.
- Confirm omitted-flag default is byte-identical (T010).
- Confirm the operator's explicit `MissionTopology` choice is persisted (the `lanes` case is not re-derived from `classify_topology`), the conditional-mint decision is an extracted helper with no new `# noqa`, the `MissionCreationResult` dataclass name is used; `ruff`/`mypy` clean, complexity ≤ 15.

## Activity Log

> **CRITICAL**: Append new entries at the END in chronological order. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-06-27T00:00:00Z – system – Prompt created.
- 2026-06-27T16:51:42Z – claude:opus:python-pedro:implementer – shell_pid=1811186 – Assigned agent via action command
- 2026-06-27T17:31:43Z – user – shell_pid=1811186 – lane/planning status desync recovery: WP03 implemented in lane-c (commit 9bf529107)
- 2026-06-27T17:31:44Z – user – shell_pid=1811186 – lane/planning status desync recovery: WP03 implemented in lane-c (commit 9bf529107)
- 2026-06-27T17:31:55Z – claude:opus:python-pedro:implementer – shell_pid=1811186 – Ready: --topology enum threaded; conditional coord mint; single_branch e2e implement+merge proves 4 observable facts; coord default byte-identical
- 2026-06-27T17:33:05Z – claude:opus:reviewer-renata:reviewer – shell_pid=1908163 – Started review via action command
- 2026-06-27T17:39:50Z – user – shell_pid=1908163 – Review APPROVE (reviewer-renata, isolated): explicit enum stored verbatim (classify corroborates fail-closed); conditional mint via topology_mints_coordination_branch helper; T009 GENUINE e2e (real implement+merge, WP02 exercise red-on-revert, 4 substantive post-merge facts); protected_branches:[] legit/orthogonal; out-of-lane re-pin strengthened; gates green
