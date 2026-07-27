---
work_package_id: WP02
title: RETROSPECTIVE artifact kind + primary-anchored placement authority
dependencies:
- WP01
requirement_refs:
- FR-002
tracker_refs:
- '#2119'
planning_base_branch: fix/3.2.3-coord-surface-regressions
merge_target_branch: fix/3.2.3-coord-surface-regressions
branch_strategy: Planning artifacts for this mission were generated on fix/3.2.3-coord-surface-regressions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3.2.3-coord-surface-regressions unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
phase: Phase 1 - Placement authority (builds on the handle-safe seam)
assignee: ''
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "1727633"
history:
- at: '2026-06-25T19:36:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks (planner-priti)
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/artifacts.py
create_intent:
- tests/mission_runtime/test_retrospective_artifact_kind.py
execution_mode: code_change
model: ''
owned_files:
- src/mission_runtime/artifacts.py
- tests/mission_runtime/test_retrospective_artifact_kind.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 — RETROSPECTIVE kind + primary-anchored authority

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the best
match for `task_type: implement` on `authoritative_surface: src/mission_runtime/artifacts.py`.

---

## Objective

**Add a `RETROSPECTIVE` member to the primary-artifact partition** so that
`retrospective.yaml`'s placement is governed by the SAME single authority that already routes
`spec`/`tasks` to the durable PRIMARY home — modeled on the now-handle-safe (WP01)
`primary_feature_dir_for_mission` gated by `is_primary_artifact_kind`, **NOT** the
topology-aware `resolve_status_surface` (which would reproduce the coord-routing bug). This is
minimal-surface (NFR-001): a single enum member + a single set-membership addition.

## The change (live-verified on `e36547461`)

| Anchor | Line | Verified |
|--------|------|----------|
| `class MissionArtifactKind(enum.Enum)` | `src/mission_runtime/artifacts.py:24` | ✅ (members `SPEC@41`, `TASKS_INDEX@29`, …) |
| `_PRIMARY_ARTIFACT_KINDS: frozenset[...] = frozenset(` | `:85` | ✅ (contains `SPEC@87`, `TASKS_INDEX@92`, …) |
| `def is_primary_artifact_kind(kind)` | `:220` | ✅ `return kind in _PRIMARY_ARTIFACT_KINDS` |

`artifacts.py` is the **shared package** (`src/mission_runtime/`). It already imports
`from specify_cli.core.constants import KITTY_SPECS_DIR` (`:19`) — the boundary is established
and clean.

## Context & Constraints

Ground truth — read before editing:
- [spec.md](../spec.md) **FR-002** + **NFR-001** (minimal surface — a single set-membership add,
  no new resolver primitive).
- [data-model.md](../data-model.md) "Entity — `RETROSPECTIVE` artifact kind".
- [contracts/terminal-artifact-teardown-contract.md](../contracts/terminal-artifact-teardown-contract.md) **C1** (the placement authority exemplar; `resolve_status_surface` REJECTED).
- [research.md](../research.md) **Decision 1** (extend the existing partition; do not invent).

**Negative scope:**
- Do NOT add a new resolver primitive (NFR-001) — placement routes through the existing
  `primary_feature_dir_for_mission` (WP03 wires the call sites; WP02 only adds the kind).
- Do NOT model placement on `resolve_status_surface` (topology-aware — the rejected exemplar).
- Do NOT wire the resolution sites here — that is WP03 (this WP only adds the kind + the unit
  assertion).

## Branch Strategy

- **Strategy**: depends on WP01 (the handle-safe seam). Branch from a base containing WP01.
- **Planning base branch**: `fix/3.2.3-coord-surface-regressions`
- **Merge target branch**: `fix/3.2.3-coord-surface-regressions`

> WP02 OWNS `src/mission_runtime/artifacts.py` exclusively. No other WP touches it.

## Subtasks & Detailed Guidance

### Subtask T021 — Add the `RETROSPECTIVE` enum member

- **Purpose**: Introduce the kind that classifies `retrospective.yaml`.
- **Files**: `src/mission_runtime/artifacts.py:24` (the `MissionArtifactKind` enum body).
- **Steps**:
  1. Add `RETROSPECTIVE = "retrospective"` to `MissionArtifactKind`, placed alongside the other
     PRIMARY members (near `SPEC@41` / `TASKS_INDEX@29`) with a one-line comment noting it is a
     terminal PRIMARY-partition artifact.
  2. If there is a filename→kind map (e.g. the `"spec.md": MissionArtifactKind.SPEC` map at
     `~:115-122`), add `"retrospective.yaml": MissionArtifactKind.RETROSPECTIVE` ONLY if that map
     is consulted by the placement path — verify by tracing; do NOT add a dead map entry.
- **Notes**: enum value is the lowercase string `"retrospective"` (mirrors `SPEC = "spec"`).

### Subtask T022 — Add `RETROSPECTIVE` to `_PRIMARY_ARTIFACT_KINDS`

- **Purpose**: Make the partition membership the single source of the primary-vs-coord decision.
- **Files**: `src/mission_runtime/artifacts.py:85`.
- **Steps**:
  1. Add `MissionArtifactKind.RETROSPECTIVE,` to the `_PRIMARY_ARTIFACT_KINDS` frozenset.
  2. Confirm `is_primary_artifact_kind(MissionArtifactKind.RETROSPECTIVE)` (`:220`) now returns
     True with no further change (it is `kind in _PRIMARY_ARTIFACT_KINDS`).
- **Notes**: single set-membership addition — NFR-001 minimal surface.

### Subtask T023 — Unit assertion (FR-002)

- **Purpose**: Lock the partition membership as an explicit unit fact (not an integration
  side-effect).
- **Files**: new `tests/mission_runtime/test_retrospective_artifact_kind.py`.
- **Steps**:
  1. Assert `MissionArtifactKind.RETROSPECTIVE in _PRIMARY_ARTIFACT_KINDS`.
  2. Assert `is_primary_artifact_kind(MissionArtifactKind.RETROSPECTIVE) is True`.
  3. Assert the enum value is `"retrospective"` (guards against a typo'd value).
- **Notes**: FR-002 explicitly requires the set-membership *unit* assertion.

## Test Strategy

- `PWHEADLESS=1 pytest tests/mission_runtime/test_retrospective_artifact_kind.py -q`.
- `ruff check src/mission_runtime/artifacts.py` + `mypy --strict` — zero issues, no suppressions.

## Definition of Done

- [ ] `MissionArtifactKind.RETROSPECTIVE` exists (value `"retrospective"`).
- [ ] `RETROSPECTIVE in _PRIMARY_ARTIFACT_KINDS` holds; `is_primary_artifact_kind(RETROSPECTIVE)`
  is True.
- [ ] The explicit unit assertion test (FR-002) passes.
- [ ] No new resolver primitive added (NFR-001); placement modeled on
  `primary_feature_dir_for_mission` (wired by WP03), NOT `resolve_status_surface`.
- [ ] ruff + `mypy --strict` clean; no suppressions.

## Risks & Mitigations

- **Dead filename-map entry:** if a filename→kind map exists, only add an entry the placement
  path actually consults. Mitigation: trace before adding; T021 step 2 is conditional.
- **Scope creep into WP03:** WP02 adds ONLY the kind + unit assertion; the resolution-site
  re-pointing is WP03. Mitigation: owned_files is `artifacts.py` + its test only.

## Review Guidance

- Confirm exactly ONE enum member + ONE set membership were added (minimal surface, NFR-001).
- Confirm the unit assertion is an explicit set-membership test, not an integration side-effect.
- Confirm placement is NOT modeled on `resolve_status_surface` (no such reference introduced).

## Activity Log

- 2026-06-25T19:36:37Z – system – Prompt created via /spec-kitty.tasks (planner-priti); FR-002.
</content>
- 2026-06-25T21:26:30Z – claude:opus:python-pedro:implementer – shell_pid=1717102 – Assigned agent via action command
- 2026-06-25T21:32:33Z – claude:opus:python-pedro:implementer – shell_pid=1717102 – WP02 impl complete + committed (7121074ad); tests/ruff/mypy green. move-task blocked: lane behind moving target fix/3.2.3-coord-surface-regressions by 53 commits; rebase conflicts on unrelated CHANGELOG/version-bump commits outside WP02 owned scope (artifacts.py + test only). Lane clean, 2 ahead of mission base. Using --force per documented flat-mission escape hatch.
- 2026-06-25T21:33:09Z – claude:opus:python-pedro:implementer – shell_pid=1717102 – Ready: RETROSPECTIVE kind in primary partition; classifier + gate wired; test green. Forced past behind-target check (lane behind moving target by 53 unrelated commits; rebase conflicts outside WP02 scope; lane clean + 2 ahead of mission base)
- 2026-06-25T21:34:51Z – claude:opus:python-pedro:implementer – shell_pid=1717102 – Code on lane-b (7121074ad): RETROSPECTIVE primary-artifact kind, 617 passed
- 2026-06-25T21:34:53Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=1727633 – Started review via action command
- 2026-06-25T21:40:08Z – user – shell_pid=1727633 – renata APPROVE: retrospective.yaml PRIMARY-not-residue (live), mutation-probed, NFR-001 minimal, gates clean
