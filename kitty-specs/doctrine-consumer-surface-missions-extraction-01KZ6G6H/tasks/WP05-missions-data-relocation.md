---
work_package_id: WP05
title: missions/ data relocation + reader repoint (one atomic change)
dependencies:
- WP03
- WP04
requirement_refs:
- FR-005
- NFR-001
planning_base_branch: research/doctrine-wheel-mission-types-public-api
merge_target_branch: research/doctrine-wheel-mission-types-public-api
branch_strategy: Planning artifacts for this mission were generated on research/doctrine-wheel-mission-types-public-api. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into research/doctrine-wheel-mission-types-public-api unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
phase: Phase 2 - Relocation
history:
- at: '2026-08-04T15:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/
create_intent:
- packs/built-in/missions/mission_types/software-dev.yaml
- packs/built-in/missions/mission_types/documentation.yaml
- packs/built-in/missions/mission_types/research.yaml
- packs/built-in/missions/mission_types/plan.yaml
- packs/built-in/missions/mission-steps/software-dev
- packs/built-in/missions/mission-steps/documentation
- packs/built-in/missions/mission-steps/research
- packs/built-in/missions/mission-steps/plan
- packs/built-in/missions/built_in_step_contracts
- packs/built-in/missions/documentation
- packs/built-in/missions/plan
- packs/built-in/missions/research
- packs/built-in/missions/software-dev
- packs/built-in/missions/README.md
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/missions/mission_types/**
- src/doctrine/missions/mission-steps/**
- src/doctrine/missions/built_in_step_contracts/**
- src/doctrine/missions/documentation/**
- src/doctrine/missions/plan/**
- src/doctrine/missions/research/**
- src/doctrine/missions/software-dev/**
- src/doctrine/missions/README.md
- packs/built-in/missions/**
- packs/built-in/mission_type.graph.yaml
- packs/built-in/mission_step_contract.graph.yaml
- src/kernel/paths.py
- src/doctrine/missions/repository.py
- src/doctrine/missions/mission_type_repository.py
- src/doctrine/missions/mission_step_repository.py
- src/doctrine/missions/step_contracts.py
- src/doctrine/drg/migration/extractor.py
- src/charter/pack_manager.py
- src/charter/catalog.py
- src/specify_cli/runtime/home.py
- src/specify_cli/skills/command_installer.py
- src/specify_cli/template/manager.py
- src/specify_cli/cli/commands/init.py
- src/specify_cli/upgrade/migrations/m_2_1_4_enforce_command_file_state.py
- src/specify_cli/upgrade/migrations/m_2_1_3_restore_prompt_commands.py
- src/specify_cli/runtime/agent_commands.py
- src/specify_cli/migration/rewrite_shims.py
- src/specify_cli/runtime/bootstrap.py
- src/charter/neutrality/lint.py
- src/charter/compiler.py
- src/specify_cli/core/config.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – missions/ data relocation + reader repoint (one atomic change)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: `owned_files` is a starting set, not final

This WP's `owned_files` above covers the confirmed data subdirectories, the DRG extractor, and the two generated graph fragments — but the **complete** set of reader files to repoint is WP03's own deliverable (`missions-reader-inventory.md`), which did not exist yet when this prompt was generated. **Before claiming this WP**, read that inventory and update this WP's frontmatter `owned_files` to include every file WP03 identified with `decision: repoint` (expected: some `specify_cli`/`runtime`/upgrade-migration files). Do not skip this step — an incomplete `owned_files` list here risks an out-of-map edit finding during review, or worse, a silently-missed repoint.

## Objectives & Success Criteria

Relocate `src/doctrine/missions/`'s **data subdirectories only** to `packs/built-in/missions/`, and repoint every reader WP03 identified — **as one atomically-reviewed change**, not split across separate commits/WPs. A post-plan review found that splitting "move" from "repoint" leaves a genuinely broken intermediate state (readers pointing at a deleted path), which violates NFR-001 and contradicts this mission's own bulk-edit `occurrence_map.yaml` (its `moves:` block already treats this as one diff).

This WP is done when:
- The data subdirectories no longer exist at `src/doctrine/missions/`; equivalent content resolves from `packs/built-in/missions/` in both an editable checkout and a built wheel.
- The 11 `.py` logic modules in `src/doctrine/missions/` are unchanged in location, still importable as `doctrine.missions.*`, repointed only in their *internal* data-reading logic.
- Every reader WP03 identified is repointed — no reader silently left on the old path.
- `packs/built-in/mission_type.graph.yaml`/`mission_step_contract.graph.yaml` are regenerated and byte-identical to their pre-change committed state (or the diff is reviewed and intentional).
- Full existing suite is green, including `tests/doctrine/drg/test_regen_roundtrip.py`.

## Context & Constraints

Read `spec.md` (FR-005, SC-001/SC-007/SC-008, User Story 1/AS1/AS3), `plan.md` (IC-05), `research.md` (R6, R8, R9), `data-model.md`, and **`occurrence_map.yaml`** (this mission's `change_mode: bulk_edit` governs this WP specifically) in full before starting.

**Governance — this is a bulk-edit WP.** `occurrence_map.yaml`'s `moves:` block names the exact data subdirectories to relocate and its `exceptions:` list the `.py` modules (`do_not_change` — stay in place, repointed internally not moved) and the DRG extractor + `MissionTemplateRepository.default_missions_root()` (`manual_review`). Do not claim a file this WP touches that isn't covered by the map without first updating the map and getting it re-approved — that is the whole point of the bulk-edit gate.

**Verified pre-state directory listing** (re-confirm against your checkout): `src/doctrine/missions/` top level is `mission_types/` (per-type `.yaml` profiles), `mission-steps/` (step-prompt directories), `built_in_step_contracts/` (step-contract YAML), four per-type content directories (`documentation/`, `plan/`, `research/`, `software-dev/`), `README.md`, plus the 11 `.py` logic modules (`repository.py`, `mission_type_repository.py`, `mission_step_repository.py`, `step_projection.py`, `models.py`, `action_index.py`, `primitives.py`, `step_contracts.py`, `step_offer_seam.py`, `glossary_hook.py`, `__init__.py`) and `__pycache__` (build artifact, ignore).

**DRG regeneration is a stated task, not a surprise.** `src/doctrine/drg/migration/extractor.py::_missions_root()`'s own docstring currently asserts "missions were not relocated... they still live inside the doctrine package" — this WP falsifies that. `packs/built-in/mission_type.graph.yaml`/`mission_step_contract.graph.yaml` are **generated**, not hand-authored, from this resolver's output. `tests/doctrine/drg/test_regen_roundtrip.py`'s byte-identical-regeneration assertions are your backstop, but regenerate deliberately (e.g. via the repo's `doctrine regenerate-graph` command or equivalent) rather than discovering the need only via a test failure.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

## Subtasks & Detailed Guidance

### T021 – Move the data subdirectories

- **Purpose**: The physical relocation.
- **Steps**: `git mv` each data subdirectory listed above from `src/doctrine/missions/` to `packs/built-in/missions/`. Do **not** move the 11 `.py` modules or `README.md` unless WP03's inventory says otherwise for a specific file.
- **Files**: per `occurrence_map.yaml`'s `moves:` block.
- **Parallel?**: No — must land before T022 in the same commit (not split into separate reviewed increments).

### T022 – Repoint every identified reader

- **Purpose**: No reader silently broken.
- **Steps**: For every row in WP03's `missions-reader-inventory.md` with `decision: repoint`, update that reader to resolve content from `packs/built-in/missions/` — via WP04's kernel primitive where the reader is kernel/doctrine-layer, or whatever each other layer's own existing resolution seam is otherwise.
- **Files**: whichever `specify_cli`/`runtime`/upgrade-migration files WP03's inventory names (update `owned_files` per the warning at the top of this prompt).
- **Parallel?**: Must land in the same reviewed change as T021, not a separate one.

### T023 – Repoint the DRG extractor

- **Purpose**: `_missions_root()`'s current assumption is false after T021.
- **Steps**: Update `src/doctrine/drg/migration/extractor.py::_missions_root()` to resolve `missions/` content from its new location.
- **Files**: `src/doctrine/drg/migration/extractor.py`.
- **Parallel?**: Same atomic change as T021/T022.

### T024 – Regenerate DRG fragments

- **Purpose**: Keep the generated graph fragments honest.
- **Steps**: Regenerate `packs/built-in/mission_type.graph.yaml` and `packs/built-in/mission_step_contract.graph.yaml`. Diff against their pre-change committed state; if the diff isn't empty, verify it's an intentional/expected consequence of the relocation (e.g. a path field), not a content regression.
- **Files**: `packs/built-in/mission_type.graph.yaml`, `packs/built-in/mission_step_contract.graph.yaml`.
- **Parallel?**: After T023.

### T025 – Verify

- **Purpose**: Prove NFR-001 and SC-008.
- **Steps**: Run the full existing suite, specifically including `tests/doctrine/drg/test_regen_roundtrip.py`. Confirm every `.py` module in `src/doctrine/missions/` is still importable exactly as before.
- **Files**: n/a (verification).
- **Parallel?**: No — final gate.

## Test Strategy

```bash
PYTHONPATH=src python -m pytest tests/doctrine tests/architectural tests/charter tests/specify_cli -q
PYTHONPATH=src python -m pytest tests/doctrine/drg/test_regen_roundtrip.py -q
```

## Risks & Mitigations

- **Risk**: Landing the move (T021) and the repoint (T022) as separate commits/reviews. **Mitigation**: this is the single highest-priority risk this WP exists to avoid — do not split them, even under time pressure.
- **Risk**: Moving a `.py` module by mistake. **Mitigation**: `occurrence_map.yaml`'s `do_not_change` exception for `src/doctrine/missions/*.py` is the guard; the bulk-edit review gate should catch this, but verify manually too.
- **Risk**: Forgetting DRG regeneration. **Mitigation**: T024 is a named subtask, not left to `test_regen_roundtrip.py`'s failure to surprise you.

## Review Guidance

- Confirm T021+T022 landed as one commit/one review, not two.
- Confirm the `.py` modules are unmoved (check `git log --follow` or a directory diff).
- Confirm the DRG regeneration diff (T024) was reviewed, not just regenerated and committed blindly.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last). Append new entries at the end.

- 2026-08-04T15:30:00Z – system – Prompt created.
