---
work_package_id: WP04
title: Authored/generated split + pack_version relocation
dependencies:
- WP01
- WP02
requirement_refs:
- FR-006
- FR-007
- FR-008
planning_base_branch: feat/pack-metadata-manifest-unification
merge_target_branch: feat/pack-metadata-manifest-unification
branch_strategy: Planning artifacts for this mission were generated on feat/pack-metadata-manifest-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/pack-metadata-manifest-unification unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
history:
- at: '2026-08-16'
  note: Authored at /spec-kitty.tasks. Parallel with WP03 after WP02.
agent_profile: python-pedro
authoritative_surface: packs/built-in/
create_intent:
- packs/built-in/pack.yaml
- packs/built-in/pack.md
- tests/architectural/test_pack_manifest_no_author_edit.py
- tests/doctrine/test_pack_version_relocation.py
execution_mode: code_change
owned_files:
- packs/built-in/pack.yaml
- packs/built-in/pack.md
- src/specify_cli/doctrine/pack_assembler.py
- src/specify_cli/cli/commands/_doctrine_collect.py
- tests/architectural/test_pack_manifest_no_author_edit.py
- tests/doctrine/test_pack_version_relocation.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile first: `/ad-hoc-profile-load python-pedro` (or `spec-kitty agent profile show python-pedro` + `spec-kitty charter context --action implement --json`).

## Objective

Complete the two-file split: create the authored `pack.yaml`/`pack.md` for the **built-in** pack, and make `pack_version` consumers **derive-else-fallback** — read the authored descriptor when present (built-in), else the generated value (fetched/org packs, where `pack_version` is genuine fetch-time provenance). Pin the no-author-edit contract.

## Context

Design: [plan.md](../plan.md) IC-06 + [data-model.md](../data-model.md). **`pack_version` is NOT a wholesale relocation** (post-tasks squad, paula-MF-3): for fetched/org packs it is genuine fetch-time provenance (`snapshot.py:172`, `pack_assembler.py:357`) and is a **required** key of `_has_recognisable_pack_manifest` (`pack_assembler.py:377`) — stripping it wholesale breaks pack recognition. So: the **built-in** pack's `pack_version` becomes authored (`pack.yaml`); fetched/org packs keep it as generated provenance. The built-in generator (`builtin_manifest.py`, WP01) simply never emits it; `snapshot.py`'s fetched-pack writer is unchanged. The real `pack_version` resolver is **`_doctrine_collect.py:81` (`_resolve_pack_version`, call site `:423`)** — `doctor.py:1098` is only a re-export shell (paula-MF-2). The pack-layout contract forbids authoring the generated file (`pack-layout.md:104`).

## Subtasks

### T014 — Authored `pack.yaml` / `pack.md` for the built-in pack
Write `packs/built-in/pack.yaml` (authored `PackDescriptor` from WP02's model: `pack_id`, `pack_version`, `parent_pack`, `accompanies_doctrine_pack`, `name`) and `packs/built-in/pack.md` (human-readable pack description). These are the authored half of the split, for the built-in pack only (org/fetched backfill deferred, Q2).

### T015 — `pack_version` derive-else-fallback; switch the real consumers
Switch the `pack_version` consumers to read the **authored descriptor when present, else the generated value**: `_doctrine_collect.py:81` (`_resolve_pack_version`) and `pack_assembler.py:390`. This preserves fetched/org packs (which keep generated `pack_version`) — do **not** strip `pack_version` from `snapshot.py`'s general writer, and do **not** break `_has_recognisable_pack_manifest`'s required-keys check (`pack_assembler.py:377`). Genuine generated provenance (`source_url`/`source_type`/`fetched_at`) stays on the generated file. Test: `test_pack_version_relocation.py` — the built-in pack resolves the authored value; a fetched-pack fixture still resolves the generated value and stays recognisable.

### T016 — No-author-edit contract test [P]
Create `tests/architectural/test_pack_manifest_no_author_edit.py`: regenerate the built-in pack's manifest and assert `packs/built-in/pack.yaml` and `pack.md` are **byte-unchanged** (NFR-004); assert the generator writes only `pack-manifest.yaml`.

## Definition of Done
- Authored `pack.yaml`/`pack.md` exist for the built-in pack; `pack_version` resolves **authored-when-present, else generated** for both real consumers (`_doctrine_collect.py`, `pack_assembler.py`); fetched/org packs keep generated `pack_version` and stay recognisable (`_has_recognisable_pack_manifest` still passes); the built-in generated manifest no longer carries `pack_version`; regen leaves authored files byte-unchanged; `ruff`/`mypy` clean; new branches tested.

## Reviewer guidance
Confirm the consumer-switch is **derive-else-fallback** (not wholesale removal); confirm a fetched-pack fixture still resolves generated `pack_version` and passes recognition; confirm the byte-unchanged assertion is real (regenerate and diff); confirm generated provenance fields stay put; confirm the edit landed in `_doctrine_collect.py` (the real resolver), not `doctor.py` (re-export shell).
