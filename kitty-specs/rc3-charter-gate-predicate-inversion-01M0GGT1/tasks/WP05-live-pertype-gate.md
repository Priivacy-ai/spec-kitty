---
work_package_id: WP05
title: Live per-type presence gate + stray-spec.md delete (surface C behavioral,
dependencies:
- WP04
requirement_refs:
- FR-011
- FR-012
- FR-013
planning_base_branch: pr/rc3-charter-gate-predicate-inversion
merge_target_branch: pr/rc3-charter-gate-predicate-inversion
branch_strategy: Planning artifacts for this mission were generated on pr/rc3-charter-gate-predicate-inversion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/rc3-charter-gate-predicate-inversion unless the human explicitly redirects the landing branch.
subtasks: []
history: []
agent_profile: python-pedro
authoritative_surface: src/runtime/next/runtime_bridge_io.py
create_intent:
- tests/runtime/next/test_pertype_presence_gate.py
execution_mode: code_change
owned_files:
- src/runtime/next/runtime_bridge_io.py
- src/specify_cli/core/worktree.py
- tests/runtime/next/test_pertype_presence_gate.py
- tests/git_ops/test_worktree.py
- tests/_next_shard_map.py
role: implementer
tags:
- artifact-seam
- presence-gate
- red-by-design
tracker_refs: []
---

# WP05 — Live per-type presence gate + stray-spec.md delete (#3597)

## Context (see plan.md §3 WP04b, ADR)
Make the presence gate per-type/data-driven and delete the stray empty `spec.md`. Depends on WP04's resolver seam (`resolve_configured_artifact_name` / `required_artifacts_for`).

**New test file MUST declare a routed `pytestmark` (CI collection gate):** `tests/runtime/next/test_pertype_presence_gate.py` → `pytestmark = [pytest.mark.unit, pytest.mark.fast]`. **Shared-contract note:** WP05 owns the `gather_artifact_presence` callee (per-type `path_pattern` behavior); WP06 owns the `runtime_bridge.py:797` caller — keep any signature change call-compatible (`mission_family` is already a param).

## Red-first (ATDD)
1. **AC-10 fail-closed both directions** (`test_pertype_presence_gate.py`): `gather_artifact_presence(feature_dir, mission_family="<custom>", step_id=...)` consults the custom type's `path_pattern` set — with the custom filename **present** the gate passes, **absent** it blocks. (The `evaluate_guards_strict` `UnregisteredMissionFamilyError` strict-raise stays for guard-table dispatch of a genuinely unregistered family — do not remove it.)
2. **Reverse AC-11** (`tests/git_ops/test_worktree.py::test_creates_empty_spec_when_no_template`): the empty `spec.md` is no longer created — reverse the assertion (reference the ADR). **Keep `test_copies_spec_template_when_exists` green.**

## Implementation
- **FR-011:** `_PRESENCE_FILE_TAGS` (`runtime_bridge_io.py:841`) becomes per-type — `gather_artifact_presence` consults the resolved per-type `path_pattern` set (from WP04's seam) instead of the closed 10-tuple. Preserve all 10 built-in filenames (NFR-003). Also convert the `_PRESENCE_FILE_TAGS`-contents call site + `validate_feature_structure` (`worktree.py:704`) to the resolved set.
- **FR-012:** delete ONLY the `else: spec_file.touch()` branch (`worktree.py:~609`). Keep the template-copy path in the same block.
- **FR-013:** the third-kind boundary stays pinned by WP04's characterization test (pin-and-defer) — no code change here.

## DoD / validation surface
`PWHEADLESS=1 pytest tests/runtime/next/ tests/git_ops/test_worktree.py -q` green; a custom family gates on a filename outside the built-in set (both directions); no empty `spec.md` created; built-in presence values unchanged; ruff + mypy clean. Note: real-port/daemon tests run serially (`-n0`) if touched.
