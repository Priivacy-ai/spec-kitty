---
work_package_id: WP14
title: Deduplicate _drop_* siblings into one _drop_if (IC-07d)
dependencies:
- WP13
requirement_refs:
- C-010
- FR-009
- NFR-006
planning_base_branch: remediation/coord-lifecycle-gates
merge_target_branch: remediation/coord-lifecycle-gates
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-lifecycle-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-lifecycle-gates unless the human explicitly redirects the landing branch.
subtasks:
- T072
- T073
- T074
- T075
phase: Phase 8 - Exemption Retirements
history:
- at: '2026-07-23T18:50:04Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/implement_cores.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/implement_cores.py
- src/specify_cli/frontmatter.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP14 – Deduplicate _drop_* siblings into one _drop_if (IC-07d)

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load `python-pedro` (role `implementer`, agent `claude`) before reading further.

---

## Objectives & Success Criteria

Deduplicate `_drop_vcs_lock_only_meta`, `_drop_runtime_frontmatter_only_wp` (+ its `_WP_FILENAME_PATTERN`/`_is_wp_filename` structural twin) and `_exclude_coord_owned` — all applied on the **same two call lines** — into ONE `_drop_if(paths, predicate)`. Do NOT retire sequentially.

**Done** = all three `_drop_*`/`_exclude_coord_owned` symbols + the filename-pattern twin are absent from `src/`; one `_drop_if` replaces them; behaviour preserved (C6/C-010).

## Context & Constraints

- Owner contract C5 (registry rows #5 + #8, deduplicated as structural twins). Plan IC-07(d).
- **Ownership resolution (decided during tasking)**: `_exclude_coord_owned` is retired **HERE (d)**, NOT in WP17 (g) — the plan double-listed it. WP17's group (g) covers only `ACCEPT_OWNED_PATHS`, the dirty_classifier bundle, and the dead `ignores_primary_coord_residue`.
- **Consumers (grep-confirmed)**: `frontmatter.py`, `cli/commands/implement.py`, `cli/commands/implement_cores.py`. The twin `_WP_FILENAME_PATTERN`/`_is_wp_filename` live in `implement_cores.py`.
- **IC-01 pre-emption**: if WP01's fix committed the VCS lock rather than dropping it, part of (d) is already done — re-check `implement.py`/`implement_cores.py` before slicing.

## Branch Strategy

- **Planning base branch**: `remediation/coord-lifecycle-gates`
- **Merge target branch**: `remediation/coord-lifecycle-gates`

## Subtasks & Detailed Guidance

### Subtask T072 – Deduplicate into `_drop_if`

- **Steps**: Replace `_drop_vcs_lock_only_meta`, `_drop_runtime_frontmatter_only_wp`, `_exclude_coord_owned` and the `_WP_FILENAME_PATTERN`/`_is_wp_filename` twin with a single `_drop_if(paths, predicate)` at the two shared call lines, delegating the predicate to the canonical churn classifier / owner.

### Subtask T073 – Check IC-01 pre-emption

- **Steps**: Inspect WP01's changes to `implement.py`/`implement_cores.py`; if the VCS lock is now committed rather than dropped, adjust scope accordingly.

### Subtask T074 – Delete registry rows (5 + 8)

- **Steps**: Delete both rows in the WP10 registry.

### Subtask T075 – Migrate tests; preserve behaviour

- **Steps**: Migrate mechanism-asserting tests; no previously-succeeding operation now fails.

## Test Strategy

- Run: `PWHEADLESS=1 uv run --extra test pytest tests/architectural/ tests/specify_cli/cli/ -q`.

## Risks & Mitigations

- Owns `implement_cores.py`, `frontmatter.py`. Leeway: `implement.py` (WP01). Serial after WP13 (shares `implement_cores.py`).

## Review Guidance

- Confirm all three symbols + the twin are gone and replaced by ONE `_drop_if`.
- Confirm `_exclude_coord_owned` is retired here (not left for WP17).

## Activity Log

- 2026-07-23T18:50:04Z – system – Prompt created.
