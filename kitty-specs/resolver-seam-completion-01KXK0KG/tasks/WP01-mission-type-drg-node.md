---
work_package_id: WP01
title: mission_type as a first-class DRG node + generator
dependencies: []
requirement_refs:
- FR-001
- NFR-002
tracker_refs:
- '2651'
planning_base_branch: feat/2651-resolver-seam-completion
merge_target_branch: feat/2651-resolver-seam-completion
branch_strategy: Planning artifacts for this mission were generated on feat/2651-resolver-seam-completion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/2651-resolver-seam-completion unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2966116"
shell_pid_created_at: "1784130887.65"
history:
- at: '2026-07-15T12:00:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-01/IC-02, DRG lane)
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/
create_intent:
- tests/doctrine/drg/test_mission_type_nodes.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/doctrine/drg/models.py
- src/doctrine/drg/migration/extractor.py
- src/doctrine/graph.yaml
- tests/doctrine/drg/migration/test_extractor.py
- tests/doctrine/drg/test_mission_type_nodes.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read, in order:
[plan.md](../plan.md) §IC-01/IC-02 + the DRG-generator research in [research.md](../research.md) §R1,
and [ADR 2026-07-15-1](../../../docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md)
Decision 2 (S0 — the four surfaces become first-class DRG nodes). The ADR/plan are the authority — do
not restate them; execute against live code. Always `uv run` for python/pytest.

## Objective

Make `mission_type` a first-class DRG node so mission-type availability runs *through the graph* like
the 8 existing kinds (ADR S0, first step). This is the DRG lane; it touches disjoint files from the
resolver lane (WP02/03) and runs in parallel. **Additive only** — no schema-version break, no migration.

## Context (grounded by post-plan feasibility, python-pedro)

- `NodeKind` is a single `StrEnum` at `src/doctrine/drg/models.py:27-45`; the URN regex `_URN_RE`
  (`models.py:19`, `^[a-z_]+:[A-Za-z0-9_/.\-]+$`) **already permits** `mission_type:software-dev`.
  `DRGNode._validate_urn` (`models.py:109-121`) asserts `prefix == kind.value`. Adding the enum member
  is all the validator needs — it is kind-agnostic.
- The generator does **not** read `missions/mission_types/*.yaml` today. `generate_graph`
  (`src/doctrine/drg/migration/extractor.py:768-842`) merges `extract_action_edges` + the 8 built-in
  artifact trees. You add **one** discovery pass mirroring `_discover_built_in_artifact_nodes`
  (`extractor.py:729`).
- `regenerate-graph --check` (`src/specify_cli/cli/commands/doctrine.py`) is a byte-for-byte diff vs the
  committed `graph.yaml` (test twin `tests/doctrine/drg/migration/test_extractor.py::test_shipped_graph_yaml_is_fresh`).
  Emit the nodes **and** regenerate in this WP to keep it green. Deterministic sort already exists at `extractor.py:822-826`.
- Adding a `NodeKind` member is **safe** (verified by the post-task squad): `test_nodekind_artifactkind.py:14`
  asserts only a **subset** relation (`artifact_values <= node_values`) — still holds; and the one
  `NodeKind`-keyed structure, `src/doctrine/drg/query.py:211`, is a comprehension `{k: [] for k in NodeKind}`
  that **auto-absorbs** the new member (not a literal to update). `NodeKind` stays a superset of `ArtifactKind`;
  do NOT touch `ArtifactKind` (`mission-type` deliberately raises `MissionTypeNotAnArtifactKind`).

### T001 — Register the `mission_type` NodeKind + node test
- Add `MISSION_TYPE = "mission_type"` to the `NodeKind` `StrEnum` (`models.py:27-45`), placed to keep any
  existing alpha/declared order.
- Add `tests/doctrine/drg/test_mission_type_nodes.py`: assert a `DRGNode(urn="mission_type:software-dev", kind=NodeKind.MISSION_TYPE, label="software-dev")` validates; assert a mismatched prefix (`urn="directive:x", kind=MISSION_TYPE`) raises.
- Verify `tests/doctrine/drg/test_nodekind_artifactkind.py` still passes (NodeKind ⊃ ArtifactKind); update it only if it pins the exact NodeKind member set.

### T002 — Extractor emits `mission_type` nodes
- Add `_discover_mission_type_nodes(...)` in `extractor.py` mirroring `_discover_built_in_artifact_nodes` (`:729`): read the 4 `src/doctrine/missions/mission_types/*.yaml` files, emit one node per type — `urn=f"mission_type:{id}"`, `kind=NodeKind.MISSION_TYPE`, `label=display_name`.
- Wire it into `generate_graph` (`:768-842`) so its nodes join the deterministic sort. **Nodes only — no edges** (edges are S0-continuation; do NOT add a `_KIND_MAP` entry — that is only needed once edges exist).
- Extend `test_mission_type_nodes.py`: generating the graph yields exactly 4 `mission_type` nodes with labels matching the `display_name`s.

### T003 — Regenerate graph.yaml + keep freshness green
- Run `uv run spec-kitty doctrine regenerate-graph` (or the project's regenerate entrypoint) to rewrite the committed `src/doctrine/graph.yaml` with the 4 new nodes.
- Confirm `uv run spec-kitty doctrine regenerate-graph --check` is fresh and `test_shipped_graph_yaml_is_fresh` passes. Confirm the surface-inequality test (`test_extractor.py`) is undisturbed (disconnected nodes don't change edge counts).
- One-line note (comment or commit msg): the pre-existing `org_pack_loader` `mission_type` universe (`src/doctrine/drg/org_pack_loader.py:100-149`) is now representable as real nodes — no code change here.

## Branch Strategy

Planning base and final merge target are both `feat/2651-resolver-seam-completion`. The execution
worktree is allocated from the computed lane in `lanes.json`; land back on the merge target.

## Definition of Done

- `MISSION_TYPE` NodeKind added; `graph.yaml` has exactly 4 `mission_type` nodes; `regenerate-graph --check` green.
- `test_mission_type_nodes.py` covers validation + generation; existing DRG/freshness/totality/superset tests green.
- `ruff` + `mypy --strict` clean on touched files. No edges added (S0-continuation).

## Risks / Reviewer guidance

- **Risk:** forgetting to regenerate `graph.yaml` → freshness gate red. DoD requires the regenerated file committed.
- **Reviewer:** confirm additive enum (no schema bump), 4 nodes present, `--check` green, no `_KIND_MAP`/edge changes, ArtifactKind untouched.

## Activity Log

- 2026-07-15T15:44:12Z – claude:sonnet:python-pedro:implementer – shell_pid=2935408 – Assigned agent via action command
- 2026-07-15T15:54:58Z – claude:sonnet:python-pedro:implementer – shell_pid=2935408 – WP01 done: mission_type DRG node + generator; 154 tests pass, freshness green, ruff/mypy clean (8b038d01d)
- 2026-07-15T15:55:06Z – claude:opus:reviewer-renata:reviewer – shell_pid=2966116 – Started review via action command
- 2026-07-15T16:00:26Z – user – shell_pid=2966116 – Review PASS (reviewer-renata:opus): additive MISSION_TYPE NodeKind, 4 fresh mission_type nodes, 154 DRG tests green, ruff+mypy clean, no edges/_KIND_MAP/ArtifactKind changes
- 2026-07-15T17:10:53Z – user – shell_pid=2966116 – Done override: Mission merged to feat/2651-resolver-seam-completion (298d0d4)
