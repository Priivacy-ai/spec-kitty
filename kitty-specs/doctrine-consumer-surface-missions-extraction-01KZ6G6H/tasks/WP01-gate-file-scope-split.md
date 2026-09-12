---
work_package_id: WP01
title: Gate-file scope split + shared-helper extraction
dependencies: []
requirement_refs:
- FR-001
- NFR-003
- NFR-004
planning_base_branch: research/doctrine-wheel-mission-types-public-api
merge_target_branch: research/doctrine-wheel-mission-types-public-api
branch_strategy: Planning artifacts for this mission were generated on research/doctrine-wheel-mission-types-public-api. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into research/doctrine-wheel-mission-types-public-api unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Gate preconditions
history:
- at: '2026-08-04T15:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/_dead_path_scan.py
- tests/architectural/test_no_dead_cli_paths.py
- tests/architectural/test_dead_builtin_doc_paths.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_no_dead_doctrine_paths.py
- tests/architectural/_dead_path_scan.py
- tests/architectural/test_no_dead_cli_paths.py
- tests/architectural/test_dead_builtin_doc_paths.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Gate-file scope split + shared-helper extraction

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

`tests/architectural/test_no_dead_doctrine_paths.py` (841 lines) currently mixes three distinct scopes behind one shared scanner. Split it by **actual** scope — not by the "Gate A vs Gates B/C" grouping an earlier draft of this mission's spec got wrong — and extract the shared scan helpers so nothing is duplicated.

This WP is done when:
- Every assertion currently in the file exists in exactly one post-split module.
- No gate's scan root is narrower than it is today (Gate B in particular must keep scanning `src/`, not narrow to `src/doctrine/`).
- The shared helpers land in one common module both new test modules import.
- Full `tests/architectural/` suite is green.

## Context & Constraints

Read `kitty-specs/doctrine-consumer-surface-missions-extraction-01KZ6G6H/spec.md` (FR-001, NFR-003, NFR-004, User Story 2/3), `plan.md` (IC-01), `research.md` (R1), and `contracts/architectural-gates.md` before starting — they contain the exact verified line numbers and function names below (re-verify against your own checkout, since this content may have shifted since planning).

**Verified pre-state** (re-confirm against your checkout — line numbers may have shifted since this was written):

| Gate | Function | Scope | Discriminator-proof tests |
|---|---|---|---|
| A | `scan_graph_monolith_paths` / `scan_graph_monolith_shipped` | `_SRC_ROOT` (`src/`, all of it) | `test_project_tier_graph_path_would_false_red_without_its_discriminator`, `test_forbidding_mention_would_false_red_without_its_discriminator` |
| B | `scan_shipped_pack_paths` / `scan_shipped_pack_shipped` | `_SRC_ROOT` (`src/`, **not** `_DOCTRINE_ROOT` — also CLI-wide) | `test_shipped_prose_would_false_red_without_the_path_shape_discriminator`, `test_frozen_seed_mirror_would_false_red_without_its_discriminator` |
| C | `scan_doctrine_cross_links` / `scan_doctrine_cross_links_shipped` | `_DOCTRINE_ROOT` (`src/doctrine/` — the only doctrine-scoped gate) | `test_code_example_links_would_false_red_without_their_discriminator`, `test_placeholder_links_would_false_red_without_their_discriminator` |
| D | `test_no_live_doc_names_a_pre_move_builtin_path` | `docs/` (a third, distinct scope) | (self-contained) |

Shared helpers used by Gates A, B, **and** C today: the `Site` dataclass, `_rel`, `_read_lines`, `_text_files` (an `lru_cache`-backed reader), and the `_REPO_ROOT`/`_SRC_ROOT`/`_DOCTRINE_ROOT`/`_PACKS_ROOT`/`_TEXT_SUFFIXES` constants.

**Do NOT** put Gate B in the same module as Gate C just because they share a filename convention — Gate B is CLI-wide, Gate C is doctrine-scoped, and narrowing Gate B's scan root as a side effect of the split is the exact regression NFR-003/NFR-004 forbid.

The `create_intent` filenames above (`_dead_path_scan.py`, `test_no_dead_cli_paths.py`, `test_dead_builtin_doc_paths.py`) are **suggestions**, not mandates — pick names that read clearly, matching this directory's existing convention (`_gate_coverage.py`, `_sole_door_scan.py`). If you rename, update this WP's `owned_files`/`create_intent` accordingly before committing.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

> These fields are populated automatically by `spec-kitty agent mission tasks`. Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### T001 – Extract shared scan helpers into a new shared module

- **Purpose**: Avoid duplicating `Site`/`_rel`/`_read_lines`/`_text_files`/root constants across the post-split modules.
- **Steps**: Create the new shared module (e.g. `_dead_path_scan.py`). Move the helpers there verbatim (no behavior change). Update the original file's imports to pull from the new module as an interim step (before the split proper).
- **Files**: new shared module; `tests/architectural/test_no_dead_doctrine_paths.py`.
- **Parallel?**: No — foundation for T002–T004.

### T002 – Create the CLI-wide gate module for Gate A + Gate B

- **Purpose**: Give the two genuinely `src/`-wide gates their own correctly-scoped home.
- **Steps**: Create the new module. Move `scan_graph_monolith_paths`/`_shipped`, `scan_shipped_pack_paths`/`_shipped`, and their full test suites (discriminator-proof tests, planted-violation tests, e.g. `test_gate_a_rejects_a_planted_violation`, `test_gate_b_rejects_a_planted_violation`) there, importing the shared helpers from T001's module. Preserve every assertion verbatim.
- **Files**: new module (e.g. `test_no_dead_cli_paths.py`).
- **Parallel?**: Can run alongside T003/T004 once T001 lands.

### T003 – Narrow `test_no_dead_doctrine_paths.py` to Gate C only

- **Purpose**: The file's own name should mean what it says — doctrine-content-scoped only.
- **Steps**: Remove Gate A/B content (moved in T002) and Gate D content (moved in T004) from this file. What remains: `scan_doctrine_cross_links`/`_shipped` and its full test suite, importing shared helpers from T001's module.
- **Files**: `tests/architectural/test_no_dead_doctrine_paths.py` (narrowed in place).
- **Parallel?**: Can run alongside T002/T004 once T001 lands.

### T004 – Give Gate D its own named landing module

- **Purpose**: `docs/`-scoping is a third, distinct concern — don't leave it stranded in whichever file is convenient.
- **Steps**: Move `test_no_live_doc_names_a_pre_move_builtin_path` to a new, explicitly-named module.
- **Files**: new module (e.g. `test_dead_builtin_doc_paths.py`).
- **Parallel?**: Can run alongside T002/T003 once T001 lands.

### T005 – Verify NFR-003/NFR-004

- **Purpose**: Prove nothing was silently dropped or narrowed.
- **Steps**: Run the full `tests/architectural/` suite. Confirm the union of assertions across the three new modules equals the pre-split file's assertions exactly. If your changes touch `tests/architectural/_gate_coverage_baseline.json` (the shared coverage ratchet WP04 may also touch, in a parallel lane), regenerate it per its own `--update-baseline` command and note this in your Activity Log so WP04's implementer knows to re-check it.
- **Files**: n/a (verification).
- **Parallel?**: No — final gate for this WP.

## Test Strategy

```bash
PYTHONPATH=src python -m pytest tests/architectural/ -q
```
Confirm collected test count is unchanged before/after the split (a dropped assertion silently reduces the count).

## Risks & Mitigations

- **Risk**: Narrowing Gate B's scan root during the split. **Mitigation**: keep `_SRC_ROOT` as Gate B's root explicitly; do not "clean up" to `_DOCTRINE_ROOT` just because it now sits near Gate C conceptually — it doesn't, after this split.
- **Risk**: Gate D getting left in a leftover/convenient location. **Mitigation**: name its module explicitly for what it is (`docs/`-scope), not folded into either other module.

## Review Guidance

- Confirm the assertion-count invariant (T005) was actually checked, not assumed.
- Confirm Gate B's scan root is still `src/`, by reading the new module's own code, not by trusting the PR description.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last). Append new entries at the end.

- 2026-08-04T15:30:00Z – system – Prompt created.
