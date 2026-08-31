---
work_package_id: WP06
title: Unify activation-CLI pack layout with runtime (FR-013)
dependencies: []
requirement_refs:
- FR-013
tracker_refs: []
planning_base_branch: mission/doctrine-governance-fidelity
merge_target_branch: mission/doctrine-governance-fidelity
branch_strategy: Planning artifacts for this mission were generated on mission/doctrine-governance-fidelity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/doctrine-governance-fidelity unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
phase: Lane B — org-pack profile consolidation
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "972852"
history:
- at: '2026-06-27T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/charter/
create_intent:
- tests/specify_cli/cli/commands/charter/test_activation_layout.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/charter/_layer_roots.py
- src/charter/pack_manager.py
- tests/specify_cli/cli/commands/charter/test_activation_layout.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Unify activation-CLI pack layout with runtime (FR-013)

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` via the `/ad-hoc-profile-load` skill (read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml`) and adopt its directives before implementing.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent**: `claude`

---

## Objectives & Success Criteria

- `spec-kitty charter activate/deactivate/list agent-profile <id>` resolves org packs from the **same canonical flat layout runtime uses** — `<pack>/agent_profiles/<id>.agent.yaml` — so activating a runtime-resolvable org profile no longer fails "Unknown agent-profile ID" (FR-013, closes the layout split-brain folded as IC-09).
- **Canonical layout = flat `<pack>/<plural>/`** (operator decision 2026-06-27). The charter activation subsystem's `<pack>/doctrine/<plural>/org/` nesting is the offending mess to remove — this is **unification, not parity**: fix the activation subsystem to match runtime; do NOT migrate packs to the nested layout.
- Regression coverage across **≥ 2 org-pack kinds** (agent-profile + one other) for `charter list/activate/deactivate`, because the org-layer scan convention is shared across all kinds (C-006).

**Done when**: `charter activate agent-profile <id>` succeeds against a flat-layout pack (RED today); the `doctrine/`-dir gate is dropped and the org-layer scan reads the flat layout; ≥ 2 kinds resolve under `charter list/activate/deactivate`; ruff + mypy clean, complexity ≤ 15.

## Context & Constraints

- **Independent of WP02–WP05** (no `dependencies`), but completes the #2156 end-to-end story for activation-list projects — verify it **before** Lane B's two-regime live proof so `charter activate` can materialise the explicit list.
- **Root cause 1 — the `doctrine/`-dir gate.** `src/specify_cli/cli/commands/charter/_layer_roots.py:24-26` registers an org root only when `(org_root / "doctrine").is_dir()`. A runtime-flat pack (`<pack>/agent_profiles/`) has no `doctrine/` subdir, so the org root is never registered → activation fails "Unknown agent-profile ID". (The project branch at `:20-22` has the same `doctrine/`-dir assumption — confirm whether it needs the same treatment, but the **org** branch is the FR-013 target.)
- **Root cause 2 — the nested org-layer scan.** `src/charter/pack_manager.py::_scan_layer_dirs` (`:563-567`) builds the project candidate as `root / "doctrine" / kind_dir` and the layered fallback as `root / base_dir / layer` — the org layer resolves to `<pack>/doctrine/<plural>/org/` rather than the flat `<pack>/<plural>/`. Re-point the org-layer branch to the flat `<pack>/<plural>/` layout.
- **Canonical reference contract (C-006).** Runtime resolves via `src/doctrine/drg/org_pack_config.py::resolve_org_roots` (`:263`) → `<pack>/agent_profiles/` (flat), consumed by `DoctrineService(org_roots=...)`. The activation subsystem must agree with this. Do NOT hand-roll a third resolution convention.
- **Decision required in this WP (research.md open-question #4): hard cutover vs layout-tolerant.** Either (a) hard cutover to flat `<pack>/<plural>/` (simplest, matches runtime, operator-preferred direction), or (b) a layout-tolerant resolver that accepts BOTH (flat preferred, nested as fallback) for backward-compat with any pack already shipping the nested layout. Default to flat-canonical; add layout-tolerance ONLY if evidence shows shipped nested packs. Record the choice + rationale in the Activity Log.
- **Shared-across-kinds risk.** The org-layer scan convention is shared across ALL org-pack kinds (directives/tactics/styleguides/agent_profiles/…). Flipping the layout affects every kind — hence the ≥ 2-kind regression (T018). Be careful: this file is owned by WP06 but its behaviour is mission-critical for all kinds.
- **C-005 red-first** through `charter activate agent-profile <id>` (the pre-existing CLI surface). **C-007** realistic pack fixtures. **NFR-003** ruff/mypy clean.

## Subtasks & Detailed Guidance

### Subtask T016 — RED activation-layout test

- **Purpose**: Witness "Unknown agent-profile ID" against a flat-layout pack before fixing.
- **Steps**: In `tests/specify_cli/cli/commands/charter/test_activation_layout.py`, build a real-format org pack laid out flat: `<pack>/agent_profiles/orgzilla-org-analyst.agent.yaml`, declared in `.kittify/config.yaml` `doctrine.org.packs[].local_path`. Drive `spec-kitty charter activate agent-profile orgzilla-org-analyst` (via CliRunner / the charter activate entry). Assert it SUCCEEDS (no "Unknown agent-profile ID"). Confirm RED today (currently fails because `_layer_roots.py` won't register the flat org root).
- **Files**: `tests/specify_cli/cli/commands/charter/test_activation_layout.py`.

### Subtask T017 — Move activation org-layer resolution to the flat layout

- **Purpose**: Unify the activation subsystem with the runtime flat layout.
- **Steps**:
  - In `src/specify_cli/cli/commands/charter/_layer_roots.py`, drop the `(<org_root>/doctrine).is_dir()` gate at `:24-26` so a flat org root (`<pack>/agent_profiles/` present, no `doctrine/`) is registered. Register the org root by the canonical `resolve_org_roots` contract, not the `doctrine/`-dir heuristic.
  - In `src/charter/pack_manager.py::_scan_layer_dirs` (`:563-567`), fix the **org-layer** branch so the candidate is the flat `<pack>/<plural>/` (e.g. `<pack>/agent_profiles/`) instead of `<pack>/doctrine/<plural>/org/`. Keep built-in and project behaviour intact (do not regress the project layer or the built-in flat-kind path at `:568-571`).
  - Implement the hard-cutover-vs-layout-tolerant decision from Context; if layout-tolerant, prefer flat and fall back to nested.
- **Files**: `src/specify_cli/cli/commands/charter/_layer_roots.py`, `src/charter/pack_manager.py`.
- **Notes**: `_layer_roots.py` imports `resolve_org_roots` from `specify_cli.doctrine.config` (its in-tree alias) — keep root resolution in `specify_cli` and hand resolved paths to `pack_manager` as data (the file's existing C-008 layer note). Keep complexity ≤ 15; extract a small layout-resolution helper if the branch grows.

### Subtask T018 — Multi-kind regression (≥ 2 kinds)

- **Purpose**: Prove the layout flip does not break other org-pack kinds.
- **Steps**: Add regression tests covering `charter list/activate/deactivate` for the agent-profile kind AND at least one other kind (e.g. a directive or tactic) laid out flat. Assert all resolve correctly and that `deactivate` round-trips (activate → list shows active → deactivate → list shows inactive). If layout-tolerant was chosen, add one nested-layout case proving backward-compat.
- **Files**: `tests/specify_cli/cli/commands/charter/test_activation_layout.py`.

## Test Strategy

- Run: `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/charter/test_activation_layout.py -q`.
- Prove T016 RED against pre-fix code, GREEN after T017. T018 exercises ≥ 2 kinds + the activate/deactivate round-trip.
- `ruff check` + `mypy` on `src/specify_cli/cli/commands/charter/_layer_roots.py` and `src/charter/pack_manager.py`.
- Because the org-layer scan is shared, run the broader charter/pack-manager test files locally to catch cross-kind fallout.

## Risks & Mitigations

- **Shared-across-kinds blast radius** → ≥ 2-kind regression (T018) + run the existing pack-manager/charter suites locally before handoff.
- **Backward-compat with nested packs** → layout-tolerant fallback option (decided + recorded in T017); default flat-canonical only if no shipped nested packs.
- **Project-layer regression** → keep the project and built-in branches of `_scan_layer_dirs` intact; only the org-layer branch moves.
- **Third resolution convention drift** → align to `resolve_org_roots` (C-006); do not invent a new path scheme.

## Review Guidance

- Verify `charter activate agent-profile <id>` succeeds against a flat pack (T016 green) and the `doctrine/`-dir org gate is gone.
- Verify the org-layer scan reads flat `<pack>/<plural>/` and built-in/project layers are unchanged.
- Verify ≥ 2 kinds resolve and activate/deactivate round-trips (T018); confirm the hard-cutover-vs-tolerant decision + rationale is recorded in the Activity Log.
- Verify alignment with `resolve_org_roots` (no hand-rolled layout) and ruff/mypy cleanliness.

## Post-Tasks Squad Remediations (BINDING)

- **Default to a LAYOUT-TOLERANT resolver (flat `<pack>/agent_profiles/` PREFERRED, nested `<pack>/doctrine/<plural>/org/` FALLBACK) — NOT a hard cutover.** Reason: `tests/charter/test_pack_manager_catalog.py` (≥6 fixtures at `<org_root>/doctrine/<plural>/org`) is NOT in this WP's owned_files; a hard cutover turns it RED out-of-ownership. Tolerant-default keeps existing nested fixtures green AND makes flat work (FR-013), with no ownership widening.
- If a hard cutover is ever required instead, add `tests/charter/test_pack_manager_catalog.py` (and verify `tests/charter/test_pack_manager.py`) to owned_files with a fixture-migration leeway note. Default path: tolerant resolver — do that.

---

## Activity Log

- 2026-06-27T00:00:00Z – system – Prompt created.
- 2026-06-27T09:51:08Z – claude:opus:python-pedro:implementer – shell_pid=918445 – Assigned agent via action command
- 2026-06-27T10:06:39Z – claude:opus:python-pedro:implementer – shell_pid=918445 – Flat-layout org packs now activate (FR-013); layout-tolerant resolver (flat preferred, nested fallback); un-owned nested catalog test green; full charter+pack-manager suites 1424 passed/1 skipped; ruff+mypy exit 0
- 2026-06-27T10:07:42Z – claude:opus:reviewer-renata:reviewer – shell_pid=972852 – Started review via action command
- 2026-06-27T10:11:12Z – user – shell_pid=972852 – reviewer-renata APPROVE: flat-preferred/nested-fallback tolerant resolver; FR-013; non-owned catalog test green; 26 passed
